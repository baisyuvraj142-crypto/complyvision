"""
ComplyVision - Field Mapping Module
Implements FR-4: Map raw OCR text to expected declaration fields:
MRP, net quantity, manufacturing date, manufacturer name, consumer-care details.
"""
import re
from typing import List, Dict, Any, Optional

class FieldMapper:
    def __init__(self):
        # Keyword triggers for targeted line association
        self.keywords = {
            "mrp": [r"\bmrp\b", r"\bm\.r\.p\b", r"\brs\b", r"₹", r"price", r"max(?:imum)?\s*retail\s*price"],
            "net_quantity": [r"\bnet\s*wt\b", r"\bnet\s*qty\b", r"\bnet\s*quantity\b", r"\bweight\b", r"\bvolume\b"],
            "mfg_date": [r"\bmfg\b", r"\bmfd\b", r"\bpkd\b", r"\bpacked\b", r"\bdate\s*of\s*mfg\b", r"\bbatch\b", r"\bmfg\s*date\b"],
            "manufacturer_name": [r"\bmfg\s*by\b", r"\bmanufactured\s*by\b", r"\bmarketed\s*by\b", r"\bpacked\s*by\b", r"\bmade\s*in\b", r"\bunit\b"],
            "consumer_care": [r"\bconsumer\s*care\b", r"\bcustomer\s*care\b", r"\bcare\s*cell\b", r"\btoll\s*free\b", r"\bfeedback\b", r"\bemail\b", r"\bhelpline\b"]
        }

        # Value regex extractors
        self.value_patterns = {
            "mrp": re.compile(r"(?:(?:MRP|M\.R\.P\.?|Rs\.?|₹)\s*[:.]?\s*)?((?:₹|Rs\.?\s*)?\d+(?:\.\d{1,2})?)", re.IGNORECASE),
            "net_quantity": re.compile(r"(\d+(?:\.\d+)?\s*(?:g|kg|ml|l|gm|gms|KG|ML|G|L))\b", re.IGNORECASE),
            "mfg_date": re.compile(r"(\b(?:\d{1,2}[/-])?\d{2}[/-]\d{2,4}\b|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s.-]+\d{2,4})", re.IGNORECASE),
            "manufacturer_name": re.compile(r"(?:(?:mfg|manufactured|marketed|packed)\s*by\s*[:.]?\s*)([A-Za-z0-9\s,.-]+)", re.IGNORECASE),
            "consumer_care": re.compile(r"(\b\d{10}\b|1800\s*\d{3,4}\s*\d{3,4}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", re.IGNORECASE)
        }

    def map_fields(self, ocr_items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Takes raw OCR items and maps them to target declaration fields.
        Returns a dict mapping field_key -> {
            'value': str or None,
            'raw_text': str,
            'box': [x1, y1, x2, y2] or None,
            'height': int or None,
            'confidence': float,
            'detected': bool
        }
        """
        mapped: Dict[str, Dict[str, Any]] = {
            "mrp": {"value": None, "raw_text": "", "box": None, "height": 0, "confidence": 0.0, "detected": False},
            "net_quantity": {"value": None, "raw_text": "", "box": None, "height": 0, "confidence": 0.0, "detected": False},
            "mfg_date": {"value": None, "raw_text": "", "box": None, "height": 0, "confidence": 0.0, "detected": False},
            "manufacturer_name": {"value": None, "raw_text": "", "box": None, "height": 0, "confidence": 0.0, "detected": False},
            "consumer_care": {"value": None, "raw_text": "", "box": None, "height": 0, "confidence": 0.0, "detected": False}
        }

        # 1. First pass: Examine each item for specific keyword + value combinations
        for item in ocr_items:
            text = item.get("text", "").strip()
            if not text:
                continue

            conf = item.get("confidence", 0.0)
            box = item.get("box", None)
            height = item.get("height", 0)

            # Check MRP
            if not mapped["mrp"]["detected"]:
                is_mrp_kw = any(re.search(kw, text, re.IGNORECASE) for kw in self.keywords["mrp"])
                if is_mrp_kw:
                    m = self.value_patterns["mrp"].search(text)
                    if m:
                        val = m.group(1) or text
                        mapped["mrp"] = {
                            "value": val.strip(),
                            "raw_text": text,
                            "box": box,
                            "height": height,
                            "confidence": conf,
                            "detected": True
                        }

            # Check Net Quantity
            if not mapped["net_quantity"]["detected"]:
                is_qty_kw = any(re.search(kw, text, re.IGNORECASE) for kw in self.keywords["net_quantity"])
                m = self.value_patterns["net_quantity"].search(text)
                if is_qty_kw and m:
                    mapped["net_quantity"] = {
                        "value": m.group(1).strip(),
                        "raw_text": text,
                        "box": box,
                        "height": height,
                        "confidence": conf,
                        "detected": True
                    }
                elif m and not is_qty_kw:
                    # Candidate even without explicit keyword
                    if mapped["net_quantity"]["confidence"] < conf:
                        mapped["net_quantity"] = {
                            "value": m.group(1).strip(),
                            "raw_text": text,
                            "box": box,
                            "height": height,
                            "confidence": conf * 0.9,
                            "detected": True
                        }

            # Check Manufacturing Date
            if not mapped["mfg_date"]["detected"]:
                is_mfg_kw = any(re.search(kw, text, re.IGNORECASE) for kw in self.keywords["mfg_date"])
                m = self.value_patterns["mfg_date"].search(text)
                if is_mfg_kw and m:
                    mapped["mfg_date"] = {
                        "value": m.group(1).strip(),
                        "raw_text": text,
                        "box": box,
                        "height": height,
                        "confidence": conf,
                        "detected": True
                    }
                elif is_mfg_kw and not m:
                    # Sometimes the date is right in the text line
                    mapped["mfg_date"] = {
                        "value": text,
                        "raw_text": text,
                        "box": box,
                        "height": height,
                        "confidence": conf * 0.8,
                        "detected": True
                    }

            # Check Manufacturer Name
            if not mapped["manufacturer_name"]["detected"]:
                is_mfr_kw = any(re.search(kw, text, re.IGNORECASE) for kw in self.keywords["manufacturer_name"])
                if is_mfr_kw:
                    m = self.value_patterns["manufacturer_name"].search(text)
                    val = m.group(1).strip() if m else text
                    mapped["manufacturer_name"] = {
                        "value": val,
                        "raw_text": text,
                        "box": box,
                        "height": height,
                        "confidence": conf,
                        "detected": True
                    }

            # Check Consumer Care
            if not mapped["consumer_care"]["detected"]:
                is_care_kw = any(re.search(kw, text, re.IGNORECASE) for kw in self.keywords["consumer_care"])
                m = self.value_patterns["consumer_care"].search(text)
                if is_care_kw or m:
                    val = m.group(1).strip() if m else text
                    mapped["consumer_care"] = {
                        "value": val,
                        "raw_text": text,
                        "box": box,
                        "height": height,
                        "confidence": conf,
                        "detected": True
                    }

        # 2. Second pass fallback: Multi-line proximity search if some fields missed
        # e.g., line 1 says "MFD:" and line 2 says "09/2026"
        for i, item in enumerate(ocr_items):
            text = item.get("text", "").strip()
            # If MRP was missed
            if not mapped["mrp"]["detected"]:
                if any(re.search(kw, text, re.IGNORECASE) for kw in [r"\bmrp\b", r"\bm\.r\.p\b"]):
                    # Look at next line
                    if i + 1 < len(ocr_items):
                        next_text = ocr_items[i+1].get("text", "").strip()
                        m = self.value_patterns["mrp"].search(next_text)
                        if m:
                            mapped["mrp"] = {
                                "value": m.group(1),
                                "raw_text": f"{text} {next_text}",
                                "box": ocr_items[i+1].get("box"),
                                "height": ocr_items[i+1].get("height", 0),
                                "confidence": (item.get("confidence", 0.5) + ocr_items[i+1].get("confidence", 0.5)) / 2,
                                "detected": True
                            }

        return mapped
