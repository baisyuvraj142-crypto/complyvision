"""
ComplyVision - Compliance Report Generator Module
Implements FR-8: Generates structured compliance report and visual bounding-box overlays.
"""
import os
import cv2
import time
from typing import Dict, Any, List

class ReportGenerator:
    def __init__(self):
        pass

    def annotate_image(
        self,
        image_path: str,
        field_reports: Dict[str, Any],
        output_path: str
    ) -> str:
        """
        Draws colored bounding boxes and field tag badges on the image:
        - Green for PASS
        - Red for FAIL
        - Yellow/Amber for REVIEW
        """
        if not os.path.exists(image_path):
            return ""

        img = cv2.imread(image_path)
        if img is None:
            return ""

        # Colors (BGR)
        color_map = {
            "PASS": (46, 204, 113),      # Emerald Green
            "FAIL": (41, 41, 231),       # Vibrant Red
            "REVIEW": (11, 156, 245)     # Warm Amber
        }

        h, w = img.shape[:2]

        for field_key, report in field_reports.items():
            box = report.get("bounding_box")
            if not box:
                continue

            verdict = report.get("verdict", "PASS")
            color = color_map.get(verdict, (255, 255, 255))
            x1, y1, x2, y2 = box

            # Clamp coordinates
            x1, y1 = max(0, int(x1)), max(0, int(y1))
            x2, y2 = min(w - 1, int(x2)), min(h - 1, int(y2))

            # Draw outer rectangle
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 3)

            # Draw label tag above box
            tag = f"{field_key.upper()}: {verdict}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.55
            thickness = 2
            (tw, th), baseline = cv2.getTextSize(tag, font, font_scale, thickness)

            # Tag background
            tag_y1 = max(0, y1 - th - 8)
            tag_y2 = y1
            cv2.rectangle(img, (x1, tag_y1), (x1 + tw + 10, tag_y2), color, -1)
            cv2.putText(
                img, tag, (x1 + 5, tag_y2 - 5),
                font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA
            )

        cv2.imwrite(output_path, img)
        return output_path

    def build_report(
        self,
        scan_id: str,
        image_filename: str,
        annotated_filename: str,
        preprocess_meta: Dict[str, Any],
        validation_result: Dict[str, Any],
        start_time: float
    ) -> Dict[str, Any]:
        """Assembles the final structured compliance report."""
        elapsed_seconds = round(time.time() - start_time, 2)
        field_reports = validation_result.get("field_reports", {})

        # Count statistics
        total_fields = len(field_reports)
        pass_count = sum(1 for f in field_reports.values() if f.get("verdict") == "PASS")
        fail_count = sum(1 for f in field_reports.values() if f.get("verdict") == "FAIL")
        review_count = sum(1 for f in field_reports.values() if f.get("verdict") == "REVIEW")

        compliance_score = round((pass_count / total_fields) * 100, 1) if total_fields > 0 else 0

        return {
            "scan_id": scan_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "processing_time_sec": elapsed_seconds,
            "image_filename": image_filename,
            "annotated_filename": annotated_filename,
            "overall_verdict": validation_result.get("overall_verdict"),
            "badge_type": validation_result.get("badge_type"),
            "summary_message": validation_result.get("summary_message"),
            "compliance_score_pct": compliance_score,
            "stats": {
                "total": total_fields,
                "passed": pass_count,
                "failed": fail_count,
                "review": review_count
            },
            "field_reports": field_reports,
            "preprocessing": preprocess_meta,
            "ruleset_version": validation_result.get("ruleset_version")
        }
