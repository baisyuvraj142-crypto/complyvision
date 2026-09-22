import unittest
from rules.mapper import FieldMapper
from rules.engine import RuleEngine
from font_checker.ratio_checker import FontRatioChecker

class TestRulesAndFontRatio(unittest.TestCase):
    def setUp(self):
        self.mapper = FieldMapper()
        self.engine = RuleEngine()
        self.font_checker = FontRatioChecker(default_min_ratio=1.0)

    def test_field_mapping_valid(self):
        sample_ocr = [
            {"text": "MRP Rs. 150.00", "box": [10, 10, 200, 40], "height": 30, "confidence": 0.95},
            {"text": "Net Qty: 500 g", "box": [10, 50, 180, 80], "height": 30, "confidence": 0.92},
            {"text": "Date of Mfg: 10/2026", "box": [10, 90, 220, 120], "height": 30, "confidence": 0.90},
            {"text": "Mfg by: ABC Foods Ltd, Mumbai", "box": [10, 130, 350, 160], "height": 30, "confidence": 0.94},
            {"text": "Consumer Care: 1800112233", "box": [10, 170, 300, 200], "height": 30, "confidence": 0.91}
        ]

        mapped = self.mapper.map_fields(sample_ocr)
        self.assertTrue(mapped["mrp"]["detected"])
        self.assertIn("150", mapped["mrp"]["value"])
        self.assertTrue(mapped["net_quantity"]["detected"])
        self.assertEqual(mapped["net_quantity"]["value"], "500 g")
        self.assertTrue(mapped["mfg_date"]["detected"])
        self.assertEqual(mapped["mfg_date"]["value"], "10/2026")

        result = self.engine.validate(mapped, sample_ocr)
        self.assertEqual(result["overall_verdict"], "COMPLIANT (PASS)")

    def test_missing_mfg_date_failure(self):
        sample_ocr = [
            {"text": "MRP Rs. 150.00", "box": [10, 10, 200, 40], "height": 30, "confidence": 0.95},
            {"text": "Net Qty: 500 g", "box": [10, 50, 180, 80], "height": 30, "confidence": 0.92},
            # Missing mfg_date!
            {"text": "Mfg by: ABC Foods Ltd, Mumbai", "box": [10, 130, 350, 160], "height": 30, "confidence": 0.94},
            {"text": "Consumer Care: 1800112233", "box": [10, 170, 300, 200], "height": 30, "confidence": 0.91}
        ]

        mapped = self.mapper.map_fields(sample_ocr)
        result = self.engine.validate(mapped, sample_ocr)
        self.assertEqual(result["overall_verdict"], "NON-COMPLIANT (FAIL)")
        self.assertEqual(result["field_reports"]["mfg_date"]["verdict"], "FAIL")

    def test_font_ratio_checker_violation(self):
        # MRP height is 12px, baseline is 24px -> ratio 0.50x < 1.0x required
        mrp_item = {"detected": True, "height": 12, "box": [10, 10, 100, 22]}
        all_items = [
            {"text": "MRP 50", "height": 12, "box": [10, 10, 100, 22]},
            {"text": "Net Qty 200g", "height": 24, "box": [10, 30, 150, 54]},
            {"text": "Mfg by XYZ Corp", "height": 24, "box": [10, 60, 250, 84]},
            {"text": "Date 09/2026", "height": 24, "box": [10, 90, 200, 114]}
        ]

        ratio_eval = self.font_checker.evaluate(mrp_item, all_items, min_required_ratio=1.0)
        self.assertFalse(ratio_eval["passed"])
        self.assertLess(ratio_eval["computed_ratio"], 1.0)

if __name__ == '__main__':
    unittest.main()
