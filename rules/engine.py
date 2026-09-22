"""
ComplyVision - Rule Engine Module
Implements FR-5, FR-7, FR-11, NFR-4, NFR-5:
Validates extracted fields against dynamic JSON config, evaluates font ratio,
and assigns Pass / Fail / Review verdicts.
"""
import os
import json
import re
from typing import Dict, Any, List
from font_checker.ratio_checker import FontRatioChecker

class RuleEngine:
    def __init__(self, rules_path: str = None):
        if rules_path is None:
            rules_path = os.path.join(os.path.dirname(__file__), "rules.json")
        self.rules_path = rules_path
        self.font_checker = FontRatioChecker()
        self.rules_config = self.load_rules()

    def load_rules(self) -> Dict[str, Any]:
        """Loads or reloads the JSON rule configuration file dynamically."""
        if not os.path.exists(self.rules_path):
            raise FileNotFoundError(f"Rules file not found at {self.rules_path}")
        with open(self.rules_path, "r", encoding="utf-8") as f:
            self.rules_config = json.load(f)
        return self.rules_config

    def save_rules(self, updated_rules_dict: Dict[str, Any]) -> None:
        """Saves updated rules to the JSON file to demonstrate live law amendments."""
        with open(self.rules_path, "w", encoding="utf-8") as f:
            json.dump(updated_rules_dict, f, indent=2)
        self.rules_config = updated_rules_dict

    def validate(
        self,
        mapped_fields: Dict[str, Dict[str, Any]],
        all_ocr_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validates mapped fields against the dynamic rule set.
        Reloads rules dynamically from file to guarantee zero-redeploy rule updates.
        """
        # Always reload to pick up live config changes
        self.load_rules()
        rules = self.rules_config.get("rules", {})

        field_reports = {}
        has_failure = False
        has_review = False

        for field_key, rule_def in rules.items():
            mapped = mapped_fields.get(field_key, {
                "value": None,
                "raw_text": "",
                "box": None,
                "height": 0,
                "confidence": 0.0,
                "detected": False
            })

            field_name = rule_def.get("field_name", field_key)
            legal_rule = rule_def.get("legal_rule", "Legal Metrology Rules 2011")
            required = rule_def.get("required", True)
            pattern_str = rule_def.get("pattern", "")
            conf_threshold = rule_def.get("confidence_threshold", 0.5)

            value = mapped.get("value")
            raw_text = mapped.get("raw_text", "")
            confidence = mapped.get("confidence", 0.0)
            box = mapped.get("box")

            verdict = "PASS"
            reasons = []

            # 1. Presence check
            if required and (not mapped.get("detected") or not value):
                verdict = "FAIL"
                reasons.append("Mandatory declaration is missing from label.")
                has_failure = True
            elif not required and (not mapped.get("detected") or not value):
                verdict = "PASS"
                reasons.append("Optional declaration; not present.")

            # 2. Format & Pattern check
            if mapped.get("detected") and value and pattern_str:
                pattern = re.compile(pattern_str, re.IGNORECASE)
                # Check against extracted value or raw line
                if not pattern.search(str(value)) and not pattern.search(str(raw_text)):
                    verdict = "FAIL"
                    reasons.append(f"Format mismatch: '{value}' does not satisfy statutory format pattern.")
                    has_failure = True
                else:
                    reasons.append("Valid format matching statutory standard.")

            # 3. Special Font-Height Ratio check for MRP (FR-6)
            font_ratio_result = None
            if field_key == "mrp" and mapped.get("detected"):
                min_font_ratio = rule_def.get("min_font_ratio", 1.0)
                font_ratio_result = self.font_checker.evaluate(
                    mrp_mapped=mapped,
                    all_ocr_items=all_ocr_items,
                    min_required_ratio=min_font_ratio
                )
                if not font_ratio_result["passed"]:
                    verdict = "FAIL"
                    reasons.append(font_ratio_result["details"])
                    has_failure = True
                else:
                    reasons.append(f"Font height ratio: {font_ratio_result['computed_ratio']}x (compliant)")

            # 4. Confidence check (FR-7)
            # If verdict is not already FAIL, but confidence is low, assign REVIEW
            if verdict != "FAIL" and mapped.get("detected"):
                if confidence < conf_threshold:
                    verdict = "REVIEW"
                    reasons.append(
                        f"Low OCR confidence ({confidence * 100:.1f}% < {conf_threshold * 100:.1f}%). "
                        "Flagged for human verification per FR-7."
                    )
                    has_review = True

            field_reports[field_key] = {
                "field_key": field_key,
                "field_name": field_name,
                "legal_rule": legal_rule,
                "extracted_value": value,
                "raw_text": raw_text,
                "bounding_box": box,
                "confidence": round(confidence, 3),
                "verdict": verdict,
                "reasons": reasons,
                "font_ratio_result": font_ratio_result
            }

        # Overall verdict calculation
        if has_failure:
            overall_verdict = "NON-COMPLIANT (FAIL)"
            badge_type = "danger"
            summary_message = "Violations detected against Legal Metrology (Packaged Commodities) Rules, 2011."
        elif has_review:
            overall_verdict = "REQUIRES MANUAL REVIEW"
            badge_type = "warning"
            summary_message = "All declarations present, but low-confidence text requires human officer inspection."
        else:
            overall_verdict = "COMPLIANT (PASS)"
            badge_type = "success"
            summary_message = "All statutory declarations are fully compliant with Legal Metrology 2011 specifications."

        return {
            "overall_verdict": overall_verdict,
            "badge_type": badge_type,
            "summary_message": summary_message,
            "field_reports": field_reports,
            "ruleset_version": self.rules_config.get("ruleset_version", "1.0")
        }
