"""
ComplyVision - Persistent Audit Trail Database Module
Implements FR-9, FR-10: SQLite persistent storage of scan logs, verdicts, and evidence.
"""
import sqlite3
import json
import os
from typing import Dict, Any, List, Optional

class AuditDatabase:
    def __init__(self, db_path: str = None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            db_path = os.path.join(base_dir, "data", "complyvision.db")
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Initializes the SQLite schema per SRS specifications."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scan_audit_trail (
                    scan_id TEXT PRIMARY KEY,
                    image_filename TEXT NOT NULL,
                    annotated_filename TEXT,
                    overall_result TEXT NOT NULL,
                    badge_type TEXT,
                    compliance_score REAL,
                    extracted_fields TEXT NOT NULL,
                    verdicts TEXT NOT NULL,
                    confidence_scores TEXT NOT NULL,
                    font_ratio_data TEXT,
                    summary_message TEXT,
                    processing_time_sec REAL,
                    timestamp TEXT NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON scan_audit_trail (timestamp DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_verdict ON scan_audit_trail (overall_result)")
            conn.commit()

    def log_scan(self, report: Dict[str, Any]) -> None:
        """Persists an end-to-end scan report into the audit trail."""
        scan_id = report.get("scan_id")
        image_filename = report.get("image_filename", "")
        annotated_filename = report.get("annotated_filename", "")
        overall_result = report.get("overall_verdict", "UNKNOWN")
        badge_type = report.get("badge_type", "secondary")
        compliance_score = report.get("compliance_score_pct", 0.0)
        summary_message = report.get("summary_message", "")
        proc_time = report.get("processing_time_sec", 0.0)
        timestamp = report.get("timestamp", "")

        field_reports = report.get("field_reports", {})
        extracted_fields = {k: v.get("extracted_value") for k, v in field_reports.items()}
        verdicts = {k: v.get("verdict") for k, v in field_reports.items()}
        confidences = {k: v.get("confidence") for k, v in field_reports.items()}
        
        mrp_font_data = field_reports.get("mrp", {}).get("font_ratio_result", {})

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO scan_audit_trail (
                    scan_id, image_filename, annotated_filename, overall_result,
                    badge_type, compliance_score, extracted_fields, verdicts,
                    confidence_scores, font_ratio_data, summary_message,
                    processing_time_sec, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                scan_id,
                image_filename,
                annotated_filename,
                overall_result,
                badge_type,
                compliance_score,
                json.dumps(extracted_fields),
                json.dumps(verdicts),
                json.dumps(confidences),
                json.dumps(mrp_font_data),
                summary_message,
                proc_time,
                timestamp
            ))
            conn.commit()

    def list_scans(self, limit: int = 50, filter_verdict: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves scan history with optional filtering and search."""
        query = "SELECT * FROM scan_audit_trail WHERE 1=1"
        params = []

        if filter_verdict:
            query += " AND overall_result LIKE ?"
            params.append(f"%{filter_verdict}%")

        if search:
            query += " AND (scan_id LIKE ? OR image_filename LIKE ? OR summary_message LIKE ?)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            rows = cursor.execute(query, params).fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["extracted_fields"] = json.loads(item["extracted_fields"])
                item["verdicts"] = json.loads(item["verdicts"])
                item["confidence_scores"] = json.loads(item["confidence_scores"])
                item["font_ratio_data"] = json.loads(item["font_ratio_data"]) if item["font_ratio_data"] else {}
                results.append(item)
            return results

    def get_scan(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves full scan details by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            row = cursor.execute("SELECT * FROM scan_audit_trail WHERE scan_id = ?", (scan_id,)).fetchone()
            if not row:
                return None
            item = dict(row)
            item["extracted_fields"] = json.loads(item["extracted_fields"])
            item["verdicts"] = json.loads(item["verdicts"])
            item["confidence_scores"] = json.loads(item["confidence_scores"])
            item["font_ratio_data"] = json.loads(item["font_ratio_data"]) if item["font_ratio_data"] else {}
            return item
