/**
 * ComplyVision - Frontend Controller
 * Implements interactive UI, 1-click sample scanning, bounding box overlays,
 * audit history filtering, and live rules.json editing.
 */

document.addEventListener('DOMContentLoaded', () => {
  // State
  let currentReport = null;
  let defaultRulesJson = "";

  // DOM Elements
  const tabs = document.querySelectorAll('.nav-tab');
  const panels = document.querySelectorAll('.tab-panel');
  const samplesGrid = document.getElementById('samples-grid');
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');
  const progressCard = document.getElementById('progress-card');
  const progressBar = document.getElementById('scan-progress-bar');
  const resultsSection = document.getElementById('results-section');

  // Verdict elements
  const verdictBanner = document.getElementById('verdict-banner');
  const verdictBadge = document.getElementById('verdict-badge');
  const verdictTitle = document.getElementById('verdict-title');
  const verdictSummary = document.getElementById('verdict-summary');
  const metricTime = document.getElementById('metric-time');
  const metricScore = document.getElementById('metric-score');
  const metricStats = document.getElementById('metric-stats');
  const metricBlur = document.getElementById('metric-blur');
  const metricBlurStatus = document.getElementById('metric-blur-status');

  // Font ratio elements
  const fontRatioCard = document.getElementById('font-ratio-card');
  const ratioBadge = document.getElementById('ratio-badge');
  const ratioBigValue = document.getElementById('ratio-big-value');
  const ratioBarFill = document.getElementById('ratio-bar-fill');
  const diagMrpH = document.getElementById('diag-mrp-h');
  const diagBaseH = document.getElementById('diag-base-h');
  const diagRatio = document.getElementById('diag-ratio');
  const diagVerdict = document.getElementById('diag-verdict');
  const ratioExplanation = document.getElementById('ratio-explanation');

  // Image viewer
  const displayImage = document.getElementById('display-image');
  const btnShowAnnotated = document.getElementById('btn-show-annotated');
  const btnShowOriginal = document.getElementById('btn-show-original');

  // Table
  const fieldBreakdownBody = document.getElementById('field-breakdown-body');

  // Audit
  const auditTableBody = document.getElementById('audit-table-body');
  const auditSearch = document.getElementById('audit-search');
  const auditFilter = document.getElementById('audit-filter');
  const btnRefreshAudit = document.getElementById('btn-refresh-audit');

  // Rule Editor
  const rulesEditor = document.getElementById('rules-json-editor');
  const btnSaveRules = document.getElementById('btn-save-rules');
  const btnResetRules = document.getElementById('btn-reset-rules');
  const rulesSaveStatus = document.getElementById('rules-save-status');

  // Modal
  const scanModal = document.getElementById('scan-modal');
  const modalClose = document.getElementById('modal-close');
  const modalTitle = document.getElementById('modal-title');
  const modalBody = document.getElementById('modal-body');

  // 1. Tab Switching
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      panels.forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      const targetId = tab.getAttribute('data-tab');
      const targetPanel = document.getElementById(targetId);
      if (targetPanel) targetPanel.classList.add('active');

      if (targetId === 'tab-audit') {
        loadAuditHistory();
      } else if (targetId === 'tab-rules') {
        loadRulesEditor();
      }
    });
  });

  // 2. Load Quick Demo Samples
  async function loadSamples() {
    try {
      const res = await fetch('/api/samples');
      const data = await res.json();
      if (data.status === 'success') {
        renderSamples(data.samples);
      }
    } catch (err) {
      samplesGrid.innerHTML = '<div class="text-danger">Failed to load demo samples.</div>';
    }
  }

  function renderSamples(samples) {
    samplesGrid.innerHTML = '';
    samples.forEach(s => {
      const btn = document.createElement('div');
      btn.className = 'sample-btn';
      let badgeClass = 'sample-pass';
      if (s.expected === 'FAIL') badgeClass = 'sample-fail';
      if (s.expected === 'BLURRY') badgeClass = 'sample-blurry';

      btn.innerHTML = `
        <div>
          <span class="sample-badge ${badgeClass}">${s.expected}</span>
          <div class="sample-title">${s.title}</div>
          <div class="sample-desc">${s.description}</div>
        </div>
      `;
      btn.addEventListener('click', () => {
        scanSample(s.filename);
      });
      samplesGrid.appendChild(btn);
    });
  }

  // 3. Scan Sample Trigger
  async function scanSample(filename) {
    const formData = new FormData();
    formData.append('sample_filename', filename);
    await executeScan(formData);
  }

  // 4. File Upload & Drag-and-Drop
  dropzone.addEventListener('click', () => fileInput.click());
  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      handleFileUpload(e.target.files[0]);
    }
  });

  async function handleFileUpload(file) {
    const formData = new FormData();
    formData.append('image', file);
    await executeScan(formData);
  }

  // 5. Execute Scan Pipeline
  async function executeScan(formData) {
    resultsSection.classList.add('hidden');
    progressCard.classList.remove('hidden');
    progressBar.style.width = '15%';

    // Step ticker animation
    const progressTitle = document.getElementById('progress-title');
    const progressSub = document.getElementById('progress-sub');

    progressTitle.innerText = "Step 1/4: Preprocessing & Contrast Boost...";
    progressSub.innerText = "Applying OpenCV CLAHE, deskewing, and checking Laplacian blur variance";

    let stepTimer = setTimeout(() => {
      progressBar.style.width = '45%';
      progressTitle.innerText = "Step 2/4: Extracting Visible Text...";
      progressSub.innerText = "Extracting words, coordinates, and bounding box heights via OCR";
    }, 400);

    let stepTimer2 = setTimeout(() => {
      progressBar.style.width = '75%';
      progressTitle.innerText = "Step 3/4: Calculating MRP Font Ratio...";
      progressSub.innerText = "Measuring declaration height relative to packaging baseline body text (FR-6)";
    }, 900);

    try {
      const res = await fetch('/api/scan', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      clearTimeout(stepTimer);
      clearTimeout(stepTimer2);
      progressBar.style.width = '100%';

      setTimeout(() => {
        progressCard.classList.add('hidden');
        if (data.status === 'success' || data.status === 'warning') {
          currentReport = data.report;
          renderReport(data.report);
        } else {
          alert('Scan failed: ' + (data.message || 'Unknown error'));
        }
      }, 350);
    } catch (err) {
      clearTimeout(stepTimer);
      clearTimeout(stepTimer2);
      progressCard.classList.add('hidden');
      alert('Error communicating with scan service: ' + err.message);
    }
  }

  // 6. Render Compliance Report
  function renderReport(report) {
    resultsSection.classList.remove('hidden');
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // Verdict Banner Styling
    verdictBanner.className = 'verdict-banner';
    const badgeType = report.badge_type || 'secondary';
    verdictBanner.classList.add('banner-' + badgeType);

    verdictBadge.className = 'verdict-badge badge-' + badgeType;
    verdictBadge.innerText = report.overall_verdict;
    verdictTitle.innerText = report.overall_verdict;
    verdictSummary.innerText = report.summary_message;

    // Metrics
    metricTime.innerText = report.processing_time_sec + 's';
    metricScore.innerText = (report.compliance_score_pct || 0) + '%';
    if (report.stats) {
      metricStats.innerText = `${report.stats.passed} of ${report.stats.total} Passed`;
    }

    const prep = report.preprocessing || {};
    metricBlur.innerText = (prep.blur_score || 0).toLocaleString();
    metricBlurStatus.innerText = prep.is_blurry ? '⚠️ Degraded (Re-capture)' : '✓ Clear & Sharp';

    // Image Setup
    const baseUploadUrl = '/uploads/';
    const baseSampleUrl = '/samples/';
    const isSample = !report.image_filename.startsWith('scan_');
    const origUrl = isSample ? baseSampleUrl + report.image_filename : baseUploadUrl + report.image_filename;
    const annotUrl = report.annotated_filename ? baseUploadUrl + report.annotated_filename : origUrl;

    displayImage.src = annotUrl;
    btnShowAnnotated.classList.add('btn-active');
    btnShowOriginal.classList.remove('btn-active');

    btnShowAnnotated.onclick = () => {
      displayImage.src = annotUrl;
      btnShowAnnotated.classList.add('btn-active');
      btnShowOriginal.classList.remove('btn-active');
    };
    btnShowOriginal.onclick = () => {
      displayImage.src = origUrl;
      btnShowOriginal.classList.add('btn-active');
      btnShowAnnotated.classList.remove('btn-active');
    };

    // Font Ratio Card (FR-6)
    const fieldReports = report.field_reports || {};
    const mrpData = fieldReports.mrp || {};
    const fontRatio = mrpData.font_ratio_result;

    if (fontRatio && fontRatio.evaluated) {
      fontRatioCard.classList.remove('hidden');
      ratioBigValue.innerText = fontRatio.computed_ratio + 'x';

      if (fontRatio.passed) {
        ratioBadge.className = 'badge badge-success';
        ratioBadge.innerText = 'Pass (Compliant)';
        ratioBigValue.style.color = '#34d399';
      } else {
        ratioBadge.className = 'badge badge-danger';
        ratioBadge.innerText = 'Violation (Undersized)';
        ratioBigValue.style.color = '#f87171';
      }

      // Meter bar position (1.0x threshold is mapped to 40% on scale 0-2.5x)
      const pct = Math.min(100, Math.max(5, (fontRatio.computed_ratio / 2.5) * 100));
      ratioBarFill.style.width = pct + '%';

      diagMrpH.innerText = fontRatio.mrp_height + ' px';
      diagBaseH.innerText = fontRatio.baseline_height + ' px';
      diagRatio.innerText = fontRatio.computed_ratio + 'x';
      diagVerdict.innerText = fontRatio.passed ? 'PASS' : 'FAIL';
      diagVerdict.className = 'diag-val ' + (fontRatio.passed ? 'text-success' : 'text-danger');

      ratioExplanation.innerHTML = `<strong>Legal Rule 5 / Section 7 Readability Standard:</strong> ${fontRatio.details}`;
    } else {
      fontRatioCard.classList.add('hidden');
    }

    // Table Breakdown
    fieldBreakdownBody.innerHTML = '';
    if (Object.keys(fieldReports).length === 0) {
      fieldBreakdownBody.innerHTML = `
        <tr>
          <td colspan="6" class="text-center py-4 text-warning">
            ${report.summary_message}
          </td>
        </tr>
      `;
      return;
    }

    for (const [key, field] of Object.entries(fieldReports)) {
      const tr = document.createElement('tr');
      const v = field.verdict || 'PASS';
      let pillClass = 'pill-pass';
      if (v === 'FAIL') pillClass = 'pill-fail';
      if (v === 'REVIEW') pillClass = 'pill-review';

      const reasonsHtml = field.reasons ? field.reasons.map(r => `<div>• ${r}</div>`).join('') : '';

      tr.innerHTML = `
        <td><strong>${field.field_name}</strong></td>
        <td><small class="text-muted">${field.legal_rule}</small></td>
        <td><span class="code-snippet">${field.extracted_value || '<em>[NOT DETECTED]</em>'}</span></td>
        <td>${field.confidence ? Math.round(field.confidence * 100) + '%' : '0%'}</td>
        <td><span class="status-pill ${pillClass}">${v}</span></td>
        <td><small>${reasonsHtml}</small></td>
      `;
      fieldBreakdownBody.appendChild(tr);
    }
  }

  // 7. Load Audit History
  async function loadAuditHistory() {
    auditTableBody.innerHTML = '<tr><td colspan="9" class="text-center py-4 text-muted">Loading audit history...</td></tr>';
    const query = auditSearch.value.trim();
    const verdict = auditFilter.value;
    let url = '/api/history?limit=50';
    if (query) url += `&search=${encodeURIComponent(query)}`;
    if (verdict) url += `&verdict=${encodeURIComponent(verdict)}`;

    try {
      const res = await fetch(url);
      const data = await res.json();
      if (data.status === 'success') {
        renderAuditRows(data.scans);
      }
    } catch (err) {
      auditTableBody.innerHTML = '<tr><td colspan="9" class="text-center py-4 text-danger">Failed to fetch audit records.</td></tr>';
    }
  }

  function renderAuditRows(scans) {
    if (!scans || scans.length === 0) {
      auditTableBody.innerHTML = '<tr><td colspan="9" class="text-center py-4 text-muted">No scan records found in persistent audit trail.</td></tr>';
      return;
    }

    auditTableBody.innerHTML = '';
    scans.forEach(s => {
      const tr = document.createElement('tr');
      let pillClass = 'pill-pass';
      if (s.overall_result.includes('FAIL')) pillClass = 'pill-fail';
      if (s.overall_result.includes('REVIEW') || s.overall_result.includes('BLURRY')) pillClass = 'pill-review';

      const fields = s.extracted_fields || {};

      tr.innerHTML = `
        <td><code>#${s.scan_id}</code></td>
        <td><small class="text-muted">${s.timestamp}</small></td>
        <td><small>${s.image_filename}</small></td>
        <td><span class="status-pill ${pillClass}">${s.overall_result}</span></td>
        <td><strong>${s.compliance_score || 0}%</strong></td>
        <td><span class="code-snippet">${fields.mrp || '-'}</span></td>
        <td><span class="code-snippet">${fields.net_quantity || '-'}</span></td>
        <td><span class="code-snippet">${fields.mfg_date || '-'}</span></td>
        <td><button class="btn btn-sm btn-secondary btn-view-scan" data-id="${s.scan_id}">View</button></td>
      `;
      auditTableBody.appendChild(tr);
    });

    document.querySelectorAll('.btn-view-scan').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const id = e.target.getAttribute('data-id');
        openScanModal(id);
      });
    });
  }

  btnRefreshAudit.addEventListener('click', loadAuditHistory);
  auditSearch.addEventListener('input', () => {
    clearTimeout(window._searchTimer);
    window._searchTimer = setTimeout(loadAuditHistory, 300);
  });
  auditFilter.addEventListener('change', loadAuditHistory);

  // 8. Open Scan Modal Detail View
  async function openScanModal(scanId) {
    try {
      const res = await fetch(`/api/history/${scanId}`);
      const data = await res.json();
      if (data.status === 'success') {
        const s = data.scan;
        modalTitle.innerText = `Scan Audit Record #${s.scan_id}`;
        modalBody.innerHTML = `
          <div class="d-flex justify-between align-center mb-3">
            <div>
              <div class="text-muted">Timestamp: ${s.timestamp}</div>
              <div class="text-muted">Image: ${s.image_filename}</div>
            </div>
            <div>
              <span class="status-pill ${s.overall_result.includes('FAIL') ? 'pill-fail' : 'pill-pass'}">${s.overall_result}</span>
            </div>
          </div>
          <div class="mt-3">
            <h5>Extracted Declarations & Verdicts:</h5>
            <pre class="code-snippet mt-2" style="white-space: pre-wrap; font-size: 0.8rem; padding: 1rem;">${JSON.stringify({
              fields: s.extracted_fields,
              verdicts: s.verdicts,
              confidences: s.confidence_scores,
              font_ratio: s.font_ratio_data,
              execution_time_sec: s.processing_time_sec
            }, null, 2)}</pre>
          </div>
        `;
        scanModal.classList.remove('hidden');
      }
    } catch (err) {
      alert('Failed to load scan record: ' + err.message);
    }
  }

  modalClose.addEventListener('click', () => scanModal.classList.add('hidden'));
  scanModal.addEventListener('click', (e) => {
    if (e.target === scanModal) scanModal.classList.add('hidden');
  });

  // 9. Live Rules Editor (FR-11, NFR-5)
  async function loadRulesEditor() {
    try {
      rulesSaveStatus.innerText = "Loading active rules...";
      const res = await fetch('/api/rules');
      const data = await res.json();
      if (data.status === 'success') {
        const jsonStr = JSON.stringify(data.config, null, 2);
        rulesEditor.value = jsonStr;
        if (!defaultRulesJson) defaultRulesJson = jsonStr;
        rulesSaveStatus.innerText = "Active rules loaded (Live)";
      }
    } catch (err) {
      rulesSaveStatus.innerText = "Failed to load rules.";
    }
  }

  btnSaveRules.addEventListener('click', async () => {
    try {
      rulesSaveStatus.innerText = "Saving & applying live...";
      const parsed = JSON.parse(rulesEditor.value);
      const res = await fetch('/api/rules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsed)
      });
      const data = await res.json();
      if (data.status === 'success') {
        rulesSaveStatus.innerText = "✓ Law amendment live! No server restart needed.";
        rulesSaveStatus.className = "text-success font-semibold";
        setTimeout(() => {
          rulesSaveStatus.className = "text-muted";
          rulesSaveStatus.innerText = "Ready";
        }, 4000);
      } else {
        alert('Save failed: ' + data.message);
      }
    } catch (err) {
      alert('Invalid JSON syntax: ' + err.message);
      rulesSaveStatus.innerText = "Error: Invalid JSON syntax";
    }
  });

  btnResetRules.addEventListener('click', () => {
    if (defaultRulesJson && confirm("Reset rules configuration back to default Legal Metrology specifications?")) {
      rulesEditor.value = defaultRulesJson;
      btnSaveRules.click();
    }
  });

  // Initial Boot
  loadSamples();
});
