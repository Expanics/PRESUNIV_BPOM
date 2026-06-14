"""
BPOM Compliance System — Step 8: Gradio UI (Redesigned)

Purpose:
    Provide an interactive web interface for the compliance system.
    UI design inspired by Figma redesign with modern navy + blue palette,
    Inter font, card-based layout, and color-coded compliance table.

    3-tab workflow:
    1. Input Dokumen (Upload PDF/DOCX or paste text)
    2. Review Hasil AI (Editable results, category override, narration)
    3. Laporan Final (Markdown preview, PDF download)

Usage:
    cd bpom_compliance && python src/app.py
"""

import os
import sys
import logging
from pathlib import Path

# Ensure project root is in python path regardless of CWD
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import gradio as gr

from src.extractor import extract_and_parse
from src.classifier import classify_product
from src.rule_engine import run_full_compliance_check
from src.rag_query import query_for_violations
from src.llm_narrator import narrate_violations, generate_report_narration
from src.report_generator import generate_pdf_report, generate_markdown_report

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ─── Event Handlers ──────────────────────────────────────────────────────────


def handle_analyze(file_obj, text_input):
    """Step 1: Extract data, classify category, run rule engine."""
    logger.info("=" * 50)
    logger.info("🚀 NEW ANALYSIS REQUEST")
    
    # Resolve file path from Gradio's file object
    file_path = None
    if file_obj is not None:
        file_path = str(file_obj) if isinstance(file_obj, str) else getattr(file_obj, 'name', str(file_obj))

    if not file_path and not text_input:
        return (
            gr.update(value="⚠️ Silakan upload file atau masukkan teks."),
            None, None, None, None, None,
            gr.update(visible=False),
            gr.update(visible=False)
        )
    
    # Extract
    try:
        extracted = extract_and_parse(file_path=file_path, raw_text=text_input)
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return (f"⚠️ Gagal mengekstrak data: {e}", None, None, None, None, None, gr.update(), gr.update())

    if not extracted:
        return ("⚠️ Tidak ada data yang berhasil diekstrak.", None, None, None, None, None, gr.update(), gr.update())
    
    # Classify
    try:
        class_result = classify_product(extracted)
        category = class_result["kategori"]
    except Exception as e:
        logger.error(f"Classification failed: {e}")
        category = "SUPLEMEN"  # Fallback

    # Run Rule Engine
    try:
        compliance = run_full_compliance_check(extracted, category)
    except Exception as e:
        logger.error(f"Rule Engine failed: {e}")
        return (f"⚠️ Rule Engine error: {e}", None, None, None, None, None, gr.update(), gr.update())

    # Build Dataframe for UI
    df_data = _build_results_table(compliance)

    # Determine narration based on results
    narration_text = _determine_narration(extracted, category, compliance)
    rag_results = []
    
    if compliance.get("violations"):
        try:
            rag_results = query_for_violations(category, compliance["violations"])
            narration_text = narrate_violations(extracted, category, compliance["violations"], rag_results)
        except Exception as e:
            logger.error(f"RAG/LLM failed: {e}")
            narration_text = f"⚠️ Gagal membuat narasi otomatis: {e}"

    # Return updates to UI components
    return (
        "✅ Analisis Selesai! Silakan cek tab 'Review Hasil AI'.",
        extracted,          # state_extracted
        category,           # state_category
        compliance,         # state_compliance
        rag_results,        # state_rag
        category,           # category_dropdown value
        gr.update(value=df_data, visible=True),  # results_df
        gr.update(value=narration_text, visible=True)  # ai_narration
    )


def _format_dasar_hukum(item: dict) -> str:
    """Combine regulation name + pasal into a readable reference."""
    regulation = item.get("regulation", "")
    pasal = item.get("pasal", "")
    if regulation and pasal:
        return f"{regulation}, {pasal}"
    return regulation or pasal or "-"


def _build_results_table(compliance: dict) -> list[list]:
    """Build table data from compliance result with full regulation references."""
    df_data = []
    for v in compliance.get("violations", []):
        df_data.append([
            v.get("param", ""), 
            str(v.get("found", "")), 
            str(v.get("threshold_max", v.get("required", ""))), 
            "❌ FAIL", 
            _format_dasar_hukum(v)
        ])
    for p in compliance.get("passed", []):
        df_data.append([
            p.get("param", ""), 
            str(p.get("found", "")), 
            str(p.get("threshold_max", p.get("required", ""))), 
            "✅ PASS", 
            _format_dasar_hukum(p)
        ])
    for m in compliance.get("missing", []):
        df_data.append([
            m.get("param", ""), 
            "-", 
            "-", 
            "⚠️ MISSING", 
            _format_dasar_hukum(m)
        ])
    return df_data


def _determine_narration(extracted: dict, category: str, compliance: dict) -> str:
    """Determine the default narration text based on compliance results."""
    has_violations = bool(compliance.get("violations"))
    has_passed = bool(compliance.get("passed"))
    has_missing = bool(compliance.get("missing"))
    
    if has_violations:
        return "⏳ Memproses narasi AI..."
    elif has_passed and not has_missing:
        return "✅ Semua parameter memenuhi standar BPOM yang berlaku."
    elif has_passed and has_missing:
        n_passed = len(compliance.get('passed', []))
        n_missing = len(compliance.get('missing', []))
        return (
            f"✅ {n_passed} parameter memenuhi standar BPOM.\n"
            f"⚠️ {n_missing} parameter tidak memiliki data (MISSING). "
            f"Lengkapi data lab untuk pengecekan lengkap."
        )
    elif not has_passed and has_missing:
        return (
            "⚠️ TIDAK ADA parameter yang berhasil diekstrak dari input.\n"
            "Data lab tidak terdeteksi. Pastikan format input sesuai contoh:\n"
            "- ALT: 250000 CFU/g\n"
            "- E.coli: negatif\n"
            "- Timbal (Pb): 0.5 mg/kg\n\n"
            "Atau upload file PDF/DOCX laporan lab."
        )
    else:
        return "⚠️ Tidak ada data untuk diperiksa."


def handle_category_change(new_category, extracted_data):
    """If user manually overrides category, re-run rule engine and LLM."""
    if not extracted_data:
        return None, None, None, None, None

    logger.info(f"🔄 User changed category to {new_category}. Re-running checks...")
    
    compliance = run_full_compliance_check(extracted_data, new_category)
    df_data = _build_results_table(compliance)

    narration_text = _determine_narration(extracted_data, new_category, compliance)
    rag_results = []
    if compliance.get("violations"):
        try:
            rag_results = query_for_violations(new_category, compliance["violations"])
            narration_text = narrate_violations(extracted_data, new_category, compliance["violations"], rag_results)
        except Exception as e:
            logger.error(f"RAG/LLM failed during category change: {e}")
            narration_text = f"⚠️ Gagal membuat narasi otomatis: {e}"

    return (
        new_category,
        compliance,
        rag_results,
        gr.update(value=df_data),
        gr.update(value=narration_text)
    )


def handle_generate_report(extracted_data, category, compliance, edited_narration):
    """Step 3: Generate Final Markdown and PDF Reports."""
    if not extracted_data or not compliance:
        return "⚠️ Tidak ada data untuk di-generate. Lakukan analisis dulu.", None

    logger.info("📄 Generating Final Reports...")
    
    md_report = generate_markdown_report(extracted_data, category, compliance, edited_narration)
    
    pdf_path = str(PROJECT_ROOT / "laporan_compliance_bpom.pdf")
    generate_pdf_report(extracted_data, category, compliance, edited_narration, pdf_path)
    
    return md_report, gr.update(value=pdf_path, visible=True)


# ─── HTML Snippets ────────────────────────────────────────────────────────────

HEADER_HTML = """
<header class="bpom-header">
  <div class="bpom-header-brand">
    <div class="bpom-header-logo">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
        <path d="m9 12 2 2 4-4"/>
      </svg>
    </div>
    <div>
      <p class="bpom-header-title">BPOM Compliance AI</p>
      <p class="bpom-header-subtitle">Sistem Pengecekan Kepatuhan Pangan Otomatis</p>
    </div>
  </div>
  <div class="bpom-header-actions">
    <div class="bpom-engine-badge">
      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#fde047" stroke-width="2.5"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
      <span>AI Engine v2.4</span>
    </div>
  </div>
</header>
"""

STEP_INDICATOR_HTML = """
<div class="bpom-steps" id="bpom-step-indicator">
  <ol class="bpom-steps-list">
    <li class="bpom-step bpom-step-completed" id="step-1-indicator">
      <div class="bpom-step-circle bpom-step-circle-completed">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
      </div>
      <div class="bpom-step-label">
        <p>Input Dokumen</p>
        <span>Upload atau tempel teks</span>
      </div>
    </li>
    <div class="bpom-step-connector bpom-step-connector-active"></div>
    <li class="bpom-step" id="step-2-indicator">
      <div class="bpom-step-circle bpom-step-circle-active">2</div>
      <div class="bpom-step-label">
        <p>Review Hasil AI</p>
        <span>Periksa hasil analisis</span>
      </div>
    </li>
    <div class="bpom-step-connector"></div>
    <li class="bpom-step" id="step-3-indicator">
      <div class="bpom-step-circle bpom-step-circle-inactive">3</div>
      <div class="bpom-step-label">
        <p>Laporan Final</p>
        <span>Download laporan PDF</span>
      </div>
    </li>
  </ol>
</div>
"""

TAB1_INFO_HTML = """
<div class="bpom-section-header">
  <h2>Input Dokumen</h2>
  <p>Upload laporan uji laboratorium produk pangan atau tempel teks secara manual untuk dianalisis.</p>
</div>
"""

TAB2_INFO_HTML = """
<div class="bpom-section-header">
  <h2>Review Hasil AI</h2>
  <p>Periksa hasil analisis kepatuhan dan narasi AI sebelum membuat laporan final.</p>
</div>
"""

TAB3_INFO_HTML = """
<div class="bpom-section-header">
  <h2>Laporan Final</h2>
  <p>Laporan kepatuhan telah dibuat. Tinjau dan unduh dalam format PDF.</p>
</div>
"""

UPLOAD_HINT_HTML = """
<div class="bpom-hint-box">
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
  <span>Pastikan dokumen berisi data uji laboratorium lengkap termasuk parameter, nilai, dan satuan ukuran. Format yang didukung: <strong>PDF</strong> dan <strong>DOCX</strong>, maks. 25 MB.</span>
</div>
"""

REPORT_FOOTER_HTML = """
<div class="bpom-report-footer">
  <span>Dibuat oleh BPOM Compliance AI System — bukan pengganti konsultasi regulasi resmi.</span>
  <span class="bpom-mono">v2.4.1</span>
</div>
"""

# ─── Custom CSS ───────────────────────────────────────────────────────────────

CUSTOM_CSS = """
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

/* ── Design Tokens ── */
:root {
  --bpom-primary:       #1E3A5F;
  --bpom-primary-dark:  #162d4a;
  --bpom-accent:        #2563EB;
  --bpom-accent-light:  #EFF6FF;
  --bpom-bg:            #F8FAFC;
  --bpom-card:          #FFFFFF;
  --bpom-border:        #E2E8F0;
  --bpom-border-light:  #F1F5F9;
  --bpom-text:          #0F172A;
  --bpom-muted:         #64748B;
  --bpom-success:       #16A34A;
  --bpom-success-bg:    #F0FDF4;
  --bpom-error:         #DC2626;
  --bpom-error-bg:      #FEF2F2;
  --bpom-warning:       #D97706;
  --bpom-warning-bg:    #FFFBEB;
  --bpom-radius:        10px;
  --bpom-radius-lg:     14px;
}

/* ── Base Reset ── */
*, *::before, *::after { box-sizing: border-box; }

body, .gradio-container, #root {
  font-family: 'Inter', ui-sans-serif, system-ui, sans-serif !important;
  background-color: var(--bpom-bg) !important;
  color: var(--bpom-text) !important;
}

.gradio-container {
  max-width: 1200px !important;
  margin: 0 auto !important;
  padding: 0 !important;
}

/* Hide default Gradio title if any */
.gradio-container > .main > .wrap > .panel > h1 { display: none; }

/* ── Header ── */
.bpom-header {
  background: var(--bpom-primary);
  color: white;
  padding: 12px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  top: 0;
  z-index: 100;
}

.bpom-header-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.bpom-header-logo {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background: rgba(255,255,255,0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.bpom-header-title {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: -0.01em;
  margin: 0;
  line-height: 1.3;
}

.bpom-header-subtitle {
  font-size: 10px;
  color: #93c5fd;
  font-weight: 400;
  margin: 0;
  line-height: 1.3;
}

.bpom-header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.bpom-engine-badge {
  display: flex;
  align-items: center;
  gap: 5px;
  background: rgba(255,255,255,0.1);
  padding: 5px 10px;
  border-radius: 8px;
  font-size: 11px;
  color: #bfdbfe;
  font-weight: 500;
}

/* ── Step Indicator ── */
.bpom-steps {
  background: white;
  border-bottom: 1px solid var(--bpom-border);
  padding: 14px 24px;
}

.bpom-steps-list {
  display: flex;
  align-items: center;
  justify-content: center;
  list-style: none;
  margin: 0;
  padding: 0;
  gap: 0;
}

.bpom-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
}

.bpom-step-connector {
  width: 48px;
  height: 1px;
  background: var(--bpom-border);
  margin: 0 6px;
  margin-top: -16px;
  transition: background 0.3s;
}

.bpom-step-connector-active { background: var(--bpom-primary); }

.bpom-step-circle {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  transition: all 0.2s;
}

.bpom-step-circle-completed {
  background: var(--bpom-primary);
  color: white;
}

.bpom-step-circle-active {
  background: var(--bpom-accent);
  color: white;
  box-shadow: 0 0 0 4px #dbeafe;
}

.bpom-step-circle-inactive {
  background: #F1F5F9;
  color: #94a3b8;
  border: 1px solid var(--bpom-border);
}

.bpom-step-label {
  text-align: center;
}

.bpom-step-label p {
  font-size: 12px;
  font-weight: 600;
  color: var(--bpom-primary);
  margin: 0;
  line-height: 1.3;
}

.bpom-step-label span {
  font-size: 10px;
  color: var(--bpom-muted);
  display: block;
}

/* ── Section Header ── */
.bpom-section-header {
  margin-bottom: 20px;
}

.bpom-section-header h2 {
  font-size: 20px;
  font-weight: 700;
  color: var(--bpom-text);
  margin: 0 0 4px 0;
  line-height: 1.3;
}

.bpom-section-header p {
  font-size: 13px;
  color: var(--bpom-muted);
  margin: 0;
}

/* ── Hint Box ── */
.bpom-hint-box {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 14px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: var(--bpom-radius);
  font-size: 12px;
  color: #92400e;
  line-height: 1.5;
  margin-top: 12px;
}

.bpom-hint-box svg { flex-shrink: 0; margin-top: 1px; }

/* ── Report Footer ── */
.bpom-report-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  font-size: 10px;
  color: var(--bpom-muted);
  border-top: 1px solid var(--bpom-border-light);
  margin-top: 16px;
}

.bpom-mono { font-family: 'JetBrains Mono', monospace; }

/* ── Gradio Tabs ── */
.tab-nav {
  background: white !important;
  border-bottom: 2px solid var(--bpom-border) !important;
  padding: 0 24px !important;
  gap: 0 !important;
}

.tab-nav button {
  font-family: 'Inter', sans-serif !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  color: var(--bpom-muted) !important;
  padding: 12px 18px !important;
  border: none !important;
  border-bottom: 2px solid transparent !important;
  border-radius: 0 !important;
  background: transparent !important;
  transition: all 0.2s !important;
  margin-bottom: -2px !important;
}

.tab-nav button:hover {
  color: var(--bpom-primary) !important;
  background: var(--bpom-accent-light) !important;
}

.tab-nav button.selected {
  color: var(--bpom-primary) !important;
  font-weight: 700 !important;
  border-bottom-color: var(--bpom-accent) !important;
  background: transparent !important;
}

.tabitem { 
  padding: 24px !important;
  background: var(--bpom-bg) !important;
}

/* ── Cards / Panels ── */
.panel, .block {
  border: 1px solid var(--bpom-border) !important;
  border-radius: var(--bpom-radius-lg) !important;
  background: var(--bpom-card) !important;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04) !important;
}

/* ── Labels ── */
label .svelte-1gfkn6j,
.block label span,
span.svelte-1gfkn6j {
  font-family: 'Inter', sans-serif !important;
  font-size: 12px !important;
  font-weight: 600 !important;
  color: var(--bpom-muted) !important;
  text-transform: uppercase !important;
  letter-spacing: 0.04em !important;
}

/* ── Input / Textarea ── */
input[type="text"],
textarea,
.scroll-hide {
  font-family: 'Inter', sans-serif !important;
  font-size: 13px !important;
  color: var(--bpom-text) !important;
  border: 1.5px solid var(--bpom-border) !important;
  border-radius: var(--bpom-radius) !important;
  background: white !important;
  transition: border-color 0.15s !important;
  padding: 10px 14px !important;
}

input[type="text"]:focus,
textarea:focus {
  border-color: var(--bpom-accent) !important;
  outline: none !important;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1) !important;
}

textarea::placeholder { color: #cbd5e1 !important; }

/* ── File Upload ── */
.upload-container, 
.file-preview,
input[type="file"] + div {
  border: 2px dashed var(--bpom-border) !important;
  border-radius: var(--bpom-radius-lg) !important;
  background: white !important;
  transition: all 0.2s !important;
}

.upload-container:hover {
  border-color: var(--bpom-accent) !important;
  background: var(--bpom-accent-light) !important;
}

/* ── Buttons ── */
button.primary, 
.gr-button-primary,
button[variant="primary"] {
  font-family: 'Inter', sans-serif !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  background: var(--bpom-primary) !important;
  color: white !important;
  border: none !important;
  border-radius: var(--bpom-radius) !important;
  padding: 12px 24px !important;
  cursor: pointer !important;
  transition: all 0.15s !important;
  box-shadow: 0 2px 6px rgba(30, 58, 95, 0.3) !important;
}

button.primary:hover,
.gr-button-primary:hover {
  background: var(--bpom-primary-dark) !important;
  box-shadow: 0 4px 12px rgba(30, 58, 95, 0.35) !important;
  transform: translateY(-1px) !important;
}

button.secondary,
.gr-button-secondary {
  font-family: 'Inter', sans-serif !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  background: white !important;
  color: var(--bpom-muted) !important;
  border: 1.5px solid var(--bpom-border) !important;
  border-radius: var(--bpom-radius) !important;
  padding: 10px 18px !important;
  transition: all 0.15s !important;
}

button.secondary:hover {
  background: var(--bpom-bg) !important;
  border-color: #94a3b8 !important;
}

/* ── Status Box ── */
#status-display .block,
#status-display textarea {
  background: var(--bpom-card) !important;
  border: 1.5px solid var(--bpom-border) !important;
  border-radius: var(--bpom-radius) !important;
  font-size: 13px !important;
  font-weight: 500 !important;
}

/* ── Dropdown / Select ── */
select, .dropdown {
  font-family: 'Inter', sans-serif !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  color: var(--bpom-primary) !important;
  background: var(--bpom-accent-light) !important;
  border: 1.5px solid #bfdbfe !important;
  border-radius: var(--bpom-radius) !important;
  padding: 8px 14px !important;
  cursor: pointer !important;
}

/* ── Dataframe / Table ── */
table {
  width: 100% !important;
  border-collapse: collapse !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 13px !important;
}

table th {
  background: #F8FAFC !important;
  border-bottom: 2px solid var(--bpom-border) !important;
  padding: 10px 14px !important;
  text-align: left !important;
  font-size: 11px !important;
  font-weight: 700 !important;
  color: var(--bpom-muted) !important;
  text-transform: uppercase !important;
  letter-spacing: 0.05em !important;
  white-space: nowrap !important;
}

table td {
  padding: 10px 14px !important;
  border-bottom: 1px solid var(--bpom-border-light) !important;
  color: var(--bpom-text) !important;
  vertical-align: middle !important;
}

table tr:hover td {
  background: rgba(248, 250, 252, 0.8) !important;
}

/* Status color coding in table */
table td:nth-child(4) {
  font-weight: 700 !important;
  font-size: 12px !important;
}

/* PASS rows */
table tr:has(td:nth-child(4):contains("PASS")) {
  border-left: 3px solid var(--bpom-success) !important;
}

/* FAIL rows */
table tr:has(td:nth-child(4):contains("FAIL")) td {
  background: rgba(254, 242, 242, 0.6) !important;
}

table tr:has(td:nth-child(4):contains("FAIL")) {
  border-left: 3px solid var(--bpom-error) !important;
}

/* MISSING rows */
table tr:has(td:nth-child(4):contains("MISSING")) td {
  background: rgba(255, 251, 235, 0.5) !important;
}

/* ── Dataframe container ── */
.dataframe-container, 
.svelte-1iohance,
.table-wrap {
  border: 1px solid var(--bpom-border) !important;
  border-radius: var(--bpom-radius-lg) !important;
  overflow: hidden !important;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05) !important;
}

/* ── Markdown Preview ── */
.prose, .markdown {
  font-family: 'Inter', sans-serif !important;
  font-size: 13px !important;
  line-height: 1.7 !important;
  color: var(--bpom-text) !important;
  background: white !important;
  padding: 20px !important;
  border: 1px solid var(--bpom-border) !important;
  border-radius: var(--bpom-radius-lg) !important;
}

.prose h1, .markdown h1 {
  font-size: 18px !important;
  font-weight: 700 !important;
  color: var(--bpom-primary) !important;
  border-bottom: 2px solid var(--bpom-border) !important;
  padding-bottom: 8px !important;
  margin-bottom: 16px !important;
}

.prose h2, .markdown h2 {
  font-size: 14px !important;
  font-weight: 700 !important;
  color: var(--bpom-text) !important;
  margin-top: 20px !important;
  text-transform: uppercase !important;
  letter-spacing: 0.04em !important;
}

.prose h3, .markdown h3 {
  font-size: 13px !important;
  font-weight: 600 !important;
  color: var(--bpom-muted) !important;
}

/* ── AI Narration Textarea ── */
#ai-narration-box textarea {
  font-size: 13px !important;
  line-height: 1.7 !important;
  color: var(--bpom-text) !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #f1f5f9; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #94a3b8; }

/* ── Spacing & Layout ── */
.gap-section { margin-bottom: 20px; }

/* ── Animations ── */
@keyframes bpom-fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

.tabitem > * { animation: bpom-fadeIn 0.2s ease-out; }

/* ── Download File component ── */
.file-preview { padding: 12px 16px !important; }
.file-preview .file-name { font-size: 13px !important; font-weight: 500 !important; }
"""


# ─── Gradio UI Definition ─────────────────────────────────────────────────────


def build_ui():
    theme = gr.themes.Base(
        font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"],
        font_mono=[gr.themes.GoogleFont("JetBrains Mono"), "ui-monospace", "monospace"],
    ).set(
        body_background_fill="#F8FAFC",
        background_fill_primary="#FFFFFF",
        background_fill_secondary="#F8FAFC",
        border_color_primary="#E2E8F0",
        color_accent="#2563EB",
        color_accent_soft="#EFF6FF",
        button_primary_background_fill="#1E3A5F",
        button_primary_background_fill_hover="#162d4a",
        button_primary_text_color="#FFFFFF",
        button_secondary_background_fill="#FFFFFF",
        button_secondary_border_color="#E2E8F0",
        button_secondary_text_color="#64748B",
        block_label_text_color="#64748B",
        block_title_text_color="#0F172A",
        input_background_fill="#FFFFFF",
        input_border_color="#E2E8F0",
    )

    with gr.Blocks(
        title="BPOM Compliance AI — Sistem Kepatuhan Pangan",
        theme=theme,
        css=CUSTOM_CSS,
        head="""
        <meta name="description" content="Sistem AI untuk pemeriksaan kepatuhan registrasi produk pangan BPOM secara otomatis.">
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        """
    ) as app:

        # ── State Variables ──
        state_extracted = gr.State()
        state_category = gr.State()
        state_compliance = gr.State()
        state_rag = gr.State()

        # ── Header ──
        gr.HTML(HEADER_HTML)

        # ── Step Indicator ──
        gr.HTML(STEP_INDICATOR_HTML)

        # ── Tabs ──
        with gr.Tabs(elem_id="bpom-tabs"):

            # ─────────────────────────────────────────────
            # Tab 1 — Input Dokumen
            # ─────────────────────────────────────────────
            with gr.Tab("1. 📥 Input Dokumen", elem_id="tab-input"):
                gr.HTML(TAB1_INFO_HTML)

                with gr.Row(equal_height=True):
                    with gr.Column(scale=1):
                        file_input = gr.File(
                            label="Upload Laporan Lab",
                            file_types=[".pdf", ".docx"],
                            height=260,
                            elem_id="file-upload",
                        )
                    with gr.Column(scale=1):
                        text_input = gr.Textbox(
                            label="Input Teks Manual",
                            lines=11,
                            placeholder=(
                                "Tempel teks laporan uji lab di sini...\n\n"
                                "Contoh:\n"
                                "Nama Produk: Biskuit Gandum Premium\n"
                                "Produsen: PT. Agro Pangan Nusantara\n\n"
                                "Parameter Uji:\n"
                                "- Kadar Air: 4,2% (SNI maks. 5%)\n"
                                "- Protein: 8,1 g/100g\n"
                                "- Lemak Total: 18,3 g/100g\n"
                                "- ALT: 320 CFU/g\n"
                                "- Timbal (Pb): 0,08 mg/kg\n..."
                            ),
                            elem_id="text-input",
                        )

                gr.HTML(UPLOAD_HINT_HTML)

                with gr.Row():
                    analyze_btn = gr.Button(
                        "🔍  Analisis Dokumen",
                        variant="primary",
                        size="lg",
                        elem_id="analyze-btn",
                    )

                status_box = gr.Textbox(
                    label="Status Analisis",
                    interactive=False,
                    elem_id="status-display",
                    show_label=True,
                )

            # ─────────────────────────────────────────────
            # Tab 2 — Review Hasil AI
            # ─────────────────────────────────────────────
            with gr.Tab("2. 📋 Review Hasil AI", elem_id="tab-review"):
                gr.HTML(TAB2_INFO_HTML)

                with gr.Row():
                    category_dropdown = gr.Dropdown(
                        choices=["SUPLEMEN", "DAIRY", "DAGING_OLAHAN", "BUAH_SAYUR"],
                        label="Kategori Produk (Otomatis Terdeteksi — Bisa Diubah)",
                        interactive=True,
                        elem_id="category-dropdown",
                        scale=2,
                    )

                results_df = gr.Dataframe(
                    headers=["Parameter", "Nilai Ditemukan", "Batas BPOM", "Status", "Dasar Hukum"],
                    label="Tabel Hasil Uji Kepatuhan",
                    interactive=False,
                    wrap=True,
                    column_widths=["28%", "15%", "17%", "12%", "28%"],
                    elem_id="results-table",
                )

                ai_narration = gr.Textbox(
                    label="Penjelasan AI & Rekomendasi  (Dapat Diedit)",
                    lines=10,
                    interactive=True,
                    elem_id="ai-narration-box",
                    placeholder="Narasi AI akan muncul setelah analisis selesai...",
                )

                with gr.Row():
                    generate_report_btn = gr.Button(
                        "✅  Setuju & Buat Laporan Final",
                        variant="primary",
                        elem_id="generate-report-btn",
                    )

            # ─────────────────────────────────────────────
            # Tab 3 — Laporan Final
            # ─────────────────────────────────────────────
            with gr.Tab("3. 📄 Laporan Final", elem_id="tab-report"):
                gr.HTML(TAB3_INFO_HTML)

                download_btn = gr.File(
                    label="⬇  Download PDF Laporan",
                    visible=False,
                    elem_id="download-btn",
                )

                report_preview = gr.Markdown(
                    value=(
                        "> **Laporan belum tersedia.**  \n"
                        "> Selesaikan analisis di Tab 1, periksa hasil di Tab 2, "
                        "lalu klik **'Setuju & Buat Laporan Final'** untuk menghasilkan laporan ini."
                    ),
                    elem_id="report-preview",
                )

                gr.HTML(REPORT_FOOTER_HTML)

        # ─── Event Wirings ──────────────────────────────────────────────────

        # 1. Analyze Document
        analyze_btn.click(
            fn=handle_analyze,
            inputs=[file_input, text_input],
            outputs=[
                status_box, state_extracted, state_category, state_compliance,
                state_rag, category_dropdown, results_df, ai_narration
            ]
        )

        # 2. Category Override → Re-run engine
        category_dropdown.change(
            fn=handle_category_change,
            inputs=[category_dropdown, state_extracted],
            outputs=[state_category, state_compliance, state_rag, results_df, ai_narration]
        )

        # 3. Generate Final Report
        generate_report_btn.click(
            fn=handle_generate_report,
            inputs=[state_extracted, state_category, state_compliance, ai_narration],
            outputs=[report_preview, download_btn]
        )

    return app


# Build the app at module level so it can be imported by the root app.py
app = build_ui()

if __name__ == "__main__":
    logger.info("🚀 Starting BPOM Compliance AI (Redesigned UI)...")
    app.launch(server_name="127.0.0.1", server_port=7860, share=False)
