"""
BPOM Compliance System — Step 8: Gradio UI

Purpose:
    Provide an interactive web interface for the compliance system.
    Follows a 3-tab workflow:
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
        # Gradio File component returns a filepath string (or NamedString)
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
        # Will be overridden by LLM narration
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
    
    # Re-run rule engine
    compliance = run_full_compliance_check(extracted_data, new_category)
    df_data = _build_results_table(compliance)

    # Re-run RAG & LLM
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
        new_category,       # state_category
        compliance,         # state_compliance
        rag_results,        # state_rag
        gr.update(value=df_data),       # results_df
        gr.update(value=narration_text) # ai_narration
    )


def handle_generate_report(extracted_data, category, compliance, edited_narration):
    """Step 3: Generate Final Markdown and PDF Reports."""
    if not extracted_data or not compliance:
        return "⚠️ Tidak ada data untuk di-generate. Lakukan analisis dulu.", None

    logger.info("📄 Generating Final Reports...")
    
    # Markdown for preview
    md_report = generate_markdown_report(extracted_data, category, compliance, edited_narration)
    
    # PDF for download — save in project root
    pdf_path = str(PROJECT_ROOT / "laporan_compliance_bpom.pdf")
    generate_pdf_report(extracted_data, category, compliance, edited_narration, pdf_path)
    
    return md_report, gr.update(value=pdf_path, visible=True)


# ─── Gradio UI Definition ────────────────────────────────────────────────────


def build_ui():
    theme = gr.themes.Soft(
        primary_hue="blue", 
        secondary_hue="slate",
        font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"]
    )
    
    custom_css = """
    /* Ensure table headers are beautifully spaced and never squished vertically */
    table th, .thead th {
        white-space: nowrap !important;
        vertical-align: middle !important;
        font-weight: 700 !important;
        background-color: #f8fafc !important;
        border-bottom: 2px solid #e2e8f0 !important;
    }
    
    /* Clean container styling */
    .gradio-container {
        max-width: 1200px !important;
        margin: 0 auto !important;
    }
    
    /* Sleek title styling */
    h1 {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        font-weight: 800 !important;
        margin-bottom: 0.25rem !important;
    }
    """
    
    with gr.Blocks(title="BPOM Compliance AI", theme=theme, css=custom_css) as app:
        
        # State Variables
        state_extracted = gr.State()
        state_category = gr.State()
        state_compliance = gr.State()
        state_rag = gr.State()

        # Header
        gr.Markdown(
            """
            # 🏛️ BPOM Compliance AI System
            **Sistem Cerdas Pemeriksaan Kepatuhan Registrasi Produk Pangan**
            
            Sistem ini melakukan ekstraksi dokumen, klasifikasi otomatis, dan pengecekan parameter mikroba & logam berat secara deterministik menggunakan rule engine, didukung oleh AI untuk penjelasan regulasi.
            """
        )

        with gr.Tabs():
            # ─── Tab 1: Input ───────────────────────────────────────────────
            with gr.Tab("1. 📥 Input Dokumen"):
                with gr.Row():
                    with gr.Column(scale=1):
                        file_input = gr.File(
                            label="Upload Laporan Lab (PDF/DOCX)",
                            file_types=[".pdf", ".docx"],
                            height=300
                        )
                    with gr.Column(scale=1):
                        text_input = gr.Textbox(
                            label="Atau Masukkan Teks Manual",
                            lines=10,
                            placeholder="Contoh:\nNama Produk: Vita-X Suplemen\nALT: 250000 CFU/g\nTimbal: 1.5 mg/kg..."
                        )
                
                analyze_btn = gr.Button("🔍 Analisis Dokumen", variant="primary", size="lg")
                status_box = gr.Textbox(label="Status", interactive=False)

            # ─── Tab 2: Review ──────────────────────────────────────────────
            with gr.Tab("2. 📋 Review Hasil AI"):
                gr.Markdown("### Hasil Analisis Otomatis")
                
                with gr.Row():
                    category_dropdown = gr.Dropdown(
                        choices=["SUPLEMEN", "DAIRY", "DAGING_OLAHAN", "BUAH_SAYUR"],
                        label="Kategori Produk (Otomatis Terdeteksi - Bisa Diubah)",
                        interactive=True
                    )
                
                results_df = gr.Dataframe(
                    headers=["Parameter", "Nilai Ditemukan", "Batas BPOM", "Status", "Dasar Hukum"],
                    label="Detail Pengecekan (Deterministik)",
                    interactive=False,
                    wrap=True,
                    column_widths=["25%", "15%", "15%", "15%", "30%"]
                )
                
                ai_narration = gr.Textbox(
                    label="Penjelasan AI & Rekomendasi (Dapat Diedit)",
                    lines=10,
                    interactive=True
                )
                
                with gr.Row():
                    generate_report_btn = gr.Button("✅ Setuju & Buat Laporan Final", variant="primary")

            # ─── Tab 3: Report ──────────────────────────────────────────────
            with gr.Tab("3. 📄 Laporan Final"):
                
                download_btn = gr.File(label="Download PDF Laporan", visible=False)
                
                report_preview = gr.Markdown(
                    "Laporan final akan muncul di sini setelah Anda mengklik 'Setuju & Buat Laporan Final' di tab Review."
                )

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
        
        # 2. Category Override
        category_dropdown.change(
            fn=handle_category_change,
            inputs=[category_dropdown, state_extracted],
            outputs=[state_category, state_compliance, state_rag, results_df, ai_narration]
        )
        
        # 3. Generate Report
        generate_report_btn.click(
            fn=handle_generate_report,
            inputs=[state_extracted, state_category, state_compliance, ai_narration],
            outputs=[report_preview, download_btn]
        )

    return app


# Build the app at module level so it can be imported by the root app.py
app = build_ui()

if __name__ == "__main__":
    logger.info("🚀 Starting Gradio App...")
    app.launch(server_name="127.0.0.1", server_port=7860, share=False)
