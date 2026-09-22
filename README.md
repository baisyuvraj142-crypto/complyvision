# ComplyVision — Compliance Checker for Packaged Commodities (MVP)

**Smart India Hackathon 2026 (PS ID 26034)**  
**Target Legal Framework**: *Legal Metrology (Packaged Commodities) Rules, 2011*  
**Developer**: [baisyuvraj142-crypto](https://github.com/baisyuvraj142-crypto)

---

## 📌 Project Overview

ComplyVision is an end-to-end automated compliance checker for packaged goods. Regulators, enforcement officers, and consumers can upload a photo of any packaged commodity label and receive an instant statutory compliance report in **under 2 seconds**.

The system extracts mandatory declarations via high-performance OCR, computes font-height ratio checks against packaging baseline text, evaluates declarations against a dynamically reloadable `rules.json` configuration, logs every audit trail record persistently to SQLite, and highlights compliance evidence with visual bounding-box overlays.

---

## 🚀 Standout Technical Differentiators

1. **Font-Height Ratio Checker (FR-6)**:
   Under Legal Metrology Rules, declarations like MRP must not be disguised in unreadable, tiny typography. ComplyVision measures the bounding-box height of the MRP declaration against the median baseline body text of the packaging and flags font-ratio violations automatically.
2. **"Law Amendment Without Redeploy" (FR-11, NFR-5)**:
   The rule set is governed by an external `rules/rules.json` file. Through the built-in web editor, a legal officer can amend statutory rules (e.g. adjust required font ratios or format patterns) and immediately re-evaluate labels without restarting the application or redeploying code.
3. **Graceful Degraded / Blurry Image Handling (NFR-3)**:
   Computes the Laplacian variance of the uploaded image before OCR. If an image is degraded or blurred, the system returns a helpful *"Re-capture required"* alert instead of crashing.
4. **Sub-5 Second Local Processing (NFR-1, NFR-2)**:
   Runs entirely on local, free, open-source computer vision & deep learning OCR engines with zero external paid API dependencies.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.x, Flask REST API
- **Computer Vision**: OpenCV (CLAHE contrast boost, deskewing, Laplacian blur detection)
- **OCR Engine**: RapidOCR (DBNet + CRNN) with unified Tesseract fallback
- **Rule Engine**: Dynamic JSON config (`rules.json`) + Regex pattern matching
- **Database**: Persistent SQLite audit trail (`scan_audit_trail`)
- **Frontend**: Clean stage-presentation HTML5/CSS3/JavaScript responsive dashboard

---

## ⚡ Quick Start

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/baisyuvraj142-crypto/complyvision.git
cd complyvision
pip install -r requirements.txt
```

### 2. Run the Application
```bash
python app.py
```
Open your browser at `http://127.0.0.1:5000`.

### 3. Run Automated Tests
```bash
python -m unittest discover tests
```

---

## 🎯 Demo Scenarios Built-In

The application includes 5 pre-packaged demo scenarios for instant 1-click live testing:
1. **Clean Compliant Label (Pass)**: Almond cookies label with all mandatory declarations compliant.
2. **Missing Mfg Date (Fail)**: Tomato ketchup label violating Rule 6(1)(d) by omitting manufacturing date.
3. **Undersized MRP Font (Fail - Font Ratio Check)**: Herbal shampoo label with tiny 14px MRP font violating font height ratio requirements (FR-6).
4. **Missing Consumer Care Contact (Fail)**: Wafer bars with no consumer redressal contact.
5. **Blurry Label Image (Re-capture Warning)**: Out-of-focus capture triggering NFR-3 blur detection.
