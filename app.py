"""
ComplyVision - Compliance Checker for Packaged Commodities
Smart India Hackathon 2026 (PS ID 26034)
Flask Application Entrypoint & REST API
"""
import os
import time
import uuid
import json
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename

from ocr.preprocessor import ImagePreprocessor
from ocr.engine import OCREngine
from rules.mapper import FieldMapper
from rules.engine import RuleEngine
from report.generator import ReportGenerator
from db.database import AuditDatabase

app = Flask(__name__)
app.config['SECRET_KEY'] = 'complyvision-sih-2026-secret'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
SAMPLE_FOLDER = os.path.join(BASE_DIR, 'static', 'samples')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SAMPLE_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'bmp', 'tiff'}

# Initialize components
preprocessor = ImagePreprocessor(blur_threshold=65.0)
ocr_engine = OCREngine()
field_mapper = FieldMapper()
rule_engine = RuleEngine()
report_gen = ReportGenerator()
audit_db = AuditDatabase()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/samples', methods=['GET'])
def get_samples():
    """Returns the list of preloaded demo sample images for quick testing."""
    samples = [
        {
            "id": "sample_1",
            "filename": "sample_1_clean_pass.png",
            "title": "Clean Compliant Label (Pass)",
            "description": "Standard packaged almond cookies with all mandatory declarations present and valid.",
            "expected": "PASS"
        },
        {
            "id": "sample_2",
            "filename": "sample_2_fail_missing_mfg.png",
            "title": "Missing Mfg Date (Fail)",
            "description": "Tomato ketchup label deliberately omitting Rule 6(1)(d) month/year of manufacture.",
            "expected": "FAIL"
        },
        {
            "id": "sample_3",
            "filename": "sample_3_fail_small_mrp_font.png",
            "title": "Undersized MRP Font (Fail - Ratio Violation)",
            "description": "Herbal shampoo label with tiny 14px MRP font violating font height ratio requirements (FR-6).",
            "expected": "FAIL"
        },
        {
            "id": "sample_4",
            "filename": "sample_4_fail_missing_care.png",
            "title": "Missing Consumer Care Contact (Fail)",
            "description": "Wafer bar packaging with no helpline/email for consumer grievance redressal.",
            "expected": "FAIL"
        },
        {
            "id": "sample_5",
            "filename": "sample_5_blurry_recapture.png",
            "title": "Blurry Label Image (Re-capture Warning)",
            "description": "Low-quality camera capture triggering NFR-3 blur detection threshold.",
            "expected": "BLURRY"
        }
    ]
    return jsonify({"status": "success", "samples": samples})

@app.route('/api/scan', methods=['POST'])
def scan_label():
    """
    Main pipeline endpoint:
    Accepts file upload OR sample_filename.
    Preprocesses -> Extracts OCR -> Maps fields -> Evaluates rules -> Persists to DB -> Returns report.
    """
    start_time = time.time()
    scan_id = str(uuid.uuid4())[:8]

    target_image_path = None
    original_filename = None

    # Check if a sample was selected
    sample_name = request.form.get('sample_filename')
    if sample_name:
        safe_sample = secure_filename(sample_name)
        candidate = os.path.join(SAMPLE_FOLDER, safe_sample)
        if os.path.exists(candidate):
            target_image_path = candidate
            original_filename = safe_sample

    # Check if file was uploaded
    if not target_image_path:
        if 'image' not in request.files:
            return jsonify({"status": "error", "message": "No image file provided"}), 400
        file = request.files['image']
        if file.filename == '':
            return jsonify({"status": "error", "message": "Empty filename"}), 400
        if file and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            original_filename = f"scan_{scan_id}_{secure_filename(file.filename)}"
            target_image_path = os.path.join(UPLOAD_FOLDER, original_filename)
            file.save(target_image_path)
        else:
            return jsonify({"status": "error", "message": "Invalid file format. Allowed: PNG, JPG, JPEG, WEBP"}), 400

    # 1. Preprocessing (FR-2, NFR-3)
    try:
        prep_out_path = os.path.join(UPLOAD_FOLDER, f"prep_{scan_id}.png")
        prep_meta = preprocessor.process(target_image_path, output_path=prep_out_path)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Preprocessing failed: {str(e)}"}), 500

    # Check if blurry (NFR-3)
    if prep_meta.get("is_blurry", False):
        elapsed = round(time.time() - start_time, 2)
        blurry_report = {
            "scan_id": scan_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "processing_time_sec": elapsed,
            "image_filename": original_filename,
            "annotated_filename": original_filename,
            "overall_verdict": "RE-CAPTURE REQUIRED (BLURRY)",
            "badge_type": "warning",
            "summary_message": (
                f"Image quality is too degraded/blurry for statutory OCR validation "
                f"(Blur score: {prep_meta['blur_score']} < threshold {preprocessor.blur_threshold}). "
                "Please hold the camera steady and re-capture the label photo under clear lighting."
            ),
            "compliance_score_pct": 0.0,
            "stats": {"total": 5, "passed": 0, "failed": 0, "review": 5},
            "field_reports": {},
            "preprocessing": prep_meta,
            "ruleset_version": rule_engine.rules_config.get("ruleset_version")
        }
        # Still log attempt to audit trail for traceability
        audit_db.log_scan(blurry_report)
        return jsonify({"status": "warning", "report": blurry_report})

    # 2. OCR Extraction (FR-3, NFR-1, NFR-2)
    ocr_source = prep_meta.get("preprocessed_path", target_image_path)
    try:
        ocr_items = ocr_engine.extract(ocr_source)
    except Exception as e:
        return jsonify({"status": "error", "message": f"OCR Extraction failed: {str(e)}"}), 500

    # 3. Field Mapping (FR-4)
    mapped_fields = field_mapper.map_fields(ocr_items)

    # 4. Rule Validation & Font Ratio Check (FR-5, FR-6, FR-7, FR-11)
    validation_result = rule_engine.validate(mapped_fields, ocr_items)

    # 5. Generate Visual Bounding Box Annotations (FR-8)
    annotated_filename = f"annotated_{scan_id}.png"
    annotated_path = os.path.join(UPLOAD_FOLDER, annotated_filename)
    report_gen.annotate_image(
        image_path=target_image_path,
        field_reports=validation_result.get("field_reports", {}),
        output_path=annotated_path
    )

    # 6. Build Final Report
    report = report_gen.build_report(
        scan_id=scan_id,
        image_filename=original_filename,
        annotated_filename=annotated_filename,
        preprocess_meta=prep_meta,
        validation_result=validation_result,
        start_time=start_time
    )

    # 7. Persistent Logging to Audit Database (FR-9, FR-10)
    audit_db.log_scan(report)

    return jsonify({"status": "success", "report": report})

@app.route('/api/history', methods=['GET'])
def get_history():
    """Returns historical scan audit trail."""
    limit = request.args.get('limit', default=50, type=int)
    verdict = request.args.get('verdict', default=None, type=str)
    search = request.args.get('search', default=None, type=str)
    scans = audit_db.list_scans(limit=limit, filter_verdict=verdict, search=search)
    return jsonify({"status": "success", "count": len(scans), "scans": scans})

@app.route('/api/history/<scan_id>', methods=['GET'])
def get_scan_detail(scan_id):
    """Returns a specific scan record."""
    record = audit_db.get_scan(scan_id)
    if not record:
        return jsonify({"status": "error", "message": "Scan not found"}), 404
    return jsonify({"status": "success", "scan": record})

@app.route('/api/rules', methods=['GET'])
def get_rules():
    """Returns active rules configuration (FR-11)."""
    rules = rule_engine.load_rules()
    return jsonify({"status": "success", "config": rules})

@app.route('/api/rules', methods=['PUT', 'POST'])
def update_rules():
    """
    Updates rule configuration live (FR-11, NFR-5).
    Allows demonstration of 'Law amendment without redeploy' during live judging!
    """
    try:
        new_config = request.get_json(force=True)
        if not new_config or "rules" not in new_config:
            return jsonify({"status": "error", "message": "Invalid rules payload structure"}), 400
        rule_engine.save_rules(new_config)
        return jsonify({
            "status": "success",
            "message": "Rules updated successfully! Law amendments are now live without server restart.",
            "config": new_config
        })
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to save rules: {str(e)}"}), 500

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/samples/<path:filename>')
def serve_sample(filename):
    return send_from_directory(SAMPLE_FOLDER, filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting ComplyVision server on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
