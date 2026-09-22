"""
ComplyVision - Font-Height Ratio Checker Module
Implements FR-6: Standout technical differentiator.
Computes the MRP font-height ratio relative to baseline label text and flags violations.
"""
import statistics
from typing import List, Dict, Any

class FontRatioChecker:
    def __init__(self, default_min_ratio: float = 1.0):
        self.default_min_ratio = default_min_ratio

    def evaluate(
        self,
        mrp_mapped: Dict[str, Any],
        all_ocr_items: List[Dict[str, Any]],
        min_required_ratio: float = None
    ) -> Dict[str, Any]:
        """
        Calculates the ratio of MRP font height to the baseline font height of the packaging label.
        
        Args:
            mrp_mapped: The mapped MRP item containing bounding box and height.
            all_ocr_items: All extracted OCR lines with bounding boxes and heights.
            min_required_ratio: Minimum ratio threshold (loaded dynamically from rules.json).

        Returns:
            Dict containing ratio analysis, baseline comparison, and pass/fail verdict.
        """
        threshold = min_required_ratio if min_required_ratio is not None else self.default_min_ratio

        if not mrp_mapped.get("detected") or not mrp_mapped.get("height"):
            return {
                "evaluated": False,
                "passed": False,
                "mrp_height": 0,
                "baseline_height": 0,
                "computed_ratio": 0.0,
                "min_required_ratio": threshold,
                "details": "MRP declaration was not detected on label; font ratio cannot be evaluated."
            }

        mrp_height = float(mrp_mapped["height"])

        # Collect text line heights, excluding tiny artifacts (<6px)
        other_heights = [
            float(item["height"]) for item in all_ocr_items
            if item.get("height", 0) >= 8 and item.get("box") != mrp_mapped.get("box")
        ]

        if not other_heights:
            # Only one line detected or no other text lines
            baseline_height = mrp_height
        else:
            # Use median to avoid skew from giant brand titles or tiny footnotes
            baseline_height = statistics.median(other_heights)

        if baseline_height <= 0:
            baseline_height = 1.0

        ratio = round(mrp_height / baseline_height, 2)
        passed = ratio >= threshold

        details = (
            f"MRP font height is {int(mrp_height)}px vs baseline label font of {int(baseline_height)}px "
            f"(Ratio: {ratio:.2f}x, Required minimum: {threshold:.2f}x). "
            f"{'Compliant with font height requirements.' if passed else 'VIOLATION: MRP font is undersized and violates Legal Metrology readability rules.'}"
        )

        return {
            "evaluated": True,
            "passed": passed,
            "mrp_height": round(mrp_height, 1),
            "baseline_height": round(baseline_height, 1),
            "computed_ratio": ratio,
            "min_required_ratio": threshold,
            "details": details
        }
