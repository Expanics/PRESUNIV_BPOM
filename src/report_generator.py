"""
BPOM Compliance System — Step 7: Report Generator

Purpose:
    Generate final compliance reports in PDF format using FPDF2.
    Includes:
    - Header with product info
    - Test results table (PASS highlighted green, FAIL highlighted red)
    - Violations section with pasal references
    - Recommendations
    - Legal basis section

Usage:
    python src/report_generator.py
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fpdf import FPDF

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─── PDF Report Class ───────────────────────────────────────────────────────


class BPOMReport(FPDF):
    """Custom FPDF class for BPOM compliance reports."""

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        """Page header with title."""
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, "LAPORAN COMPLIANCE BPOM", border=0, align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, "Sistem Cerdas Pemeriksaan Kepatuhan Registrasi Produk Pangan", border=0, align="C", new_x="LMARGIN", new_y="NEXT")
        self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
        self.ln(5)

    def footer(self):
        """Page footer with timestamp and page number."""
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cell(0, 10, f"Generated: {timestamp} | Page {self.page_no()}/{{nb}}", align="C")


# ─── Report Generation ──────────────────────────────────────────────────────


def generate_pdf_report(
    extracted_data: dict,
    category: str,
    compliance_result: dict,
    narration: str = "",
    output_path: str = "laporan_compliance.pdf",
) -> str:
    """
    Generate a PDF compliance report.
    
    Args:
        extracted_data: parsed lab data
        category: product category
        compliance_result: full result from rule engine
        narration: LLM-generated narration text
        output_path: where to save the PDF
    
    Returns:
        Path to generated PDF file
    """
    logger.info(f"📄 Generating PDF report: {output_path}")

    pdf = BPOMReport()
    pdf.alias_nb_pages()
    pdf.add_page()

    # ── Product Info Section ─────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "INFORMASI PRODUK", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)

    info_items = [
        ("Nama Produk", extracted_data.get("nama_produk", "N/A")),
        ("Perusahaan", extracted_data.get("perusahaan", "N/A")),
        ("Tanggal Uji", extracted_data.get("tanggal_uji", "N/A")),
        ("Kategori", category),
        ("Status", compliance_result.get("overall_status", "N/A")),
    ]

    for label, value in info_items:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(45, 7, f"{label}:", new_x="RIGHT")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 7, str(value), new_x="LMARGIN", new_y="NEXT")

    pdf.ln(5)

    # ── Executive Summary ────────────────────────────────────────────────
    overall = compliance_result.get("overall_status", "N/A")
    violations = compliance_result.get("violations", [])
    passed = compliance_result.get("passed", [])
    missing = compliance_result.get("missing", [])
    total = len(violations) + len(passed) + len(missing)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "RINGKASAN EKSEKUTIF", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)

    if overall == "FAIL":
        pdf.set_text_color(200, 0, 0)
        summary = (
            f"TIDAK MEMENUHI STANDAR. Dari {total} parameter yang diperiksa, "
            f"{len(violations)} parameter tidak memenuhi persyaratan BPOM."
        )
    else:
        pdf.set_text_color(0, 128, 0)
        summary = (
            f"MEMENUHI STANDAR. Seluruh {total} parameter yang diperiksa "
            f"memenuhi persyaratan BPOM yang berlaku."
        )

    pdf.multi_cell(0, 6, summary)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)

    # ── Test Results Table ───────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "DETAIL HASIL UJI", new_x="LMARGIN", new_y="NEXT")

    # Table header
    col_widths = [45, 35, 35, 25, 50]
    headers = ["Parameter", "Nilai", "Batas", "Status", "Pasal"]

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(220, 220, 220)
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 7, h, border=1, fill=True)
    pdf.ln()

    # Table rows — PASS items
    pdf.set_font("Helvetica", "", 8)
    all_results = passed + violations + missing

    for r in all_results:
        param = str(r.get("param", ""))[:20]
        found = str(r.get("found", ""))[:15]
        threshold = str(r.get("threshold_max", r.get("required", "")))[:15]
        status = r.get("status", "")
        pasal = str(r.get("pasal", ""))[:25]

        # Color coding
        if status == "FAIL":
            pdf.set_fill_color(255, 200, 200)  # Red background
        elif status == "PASS":
            pdf.set_fill_color(200, 255, 200)  # Green background
        else:
            pdf.set_fill_color(255, 255, 200)  # Yellow background

        pdf.cell(col_widths[0], 6, param, border=1, fill=True)
        pdf.cell(col_widths[1], 6, found, border=1, fill=True)
        pdf.cell(col_widths[2], 6, threshold, border=1, fill=True)
        pdf.cell(col_widths[3], 6, status, border=1, fill=True)
        pdf.cell(col_widths[4], 6, pasal, border=1, fill=True)
        pdf.ln()

    pdf.ln(5)

    # ── Violations Detail ────────────────────────────────────────────────
    if violations:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "TEMUAN KETIDAKSESUAIAN", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)

        for i, v in enumerate(violations, 1):
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(200, 0, 0)
            pdf.cell(0, 6, f"{i}. {v.get('param', 'N/A')}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", "", 9)

            message = v.get("message", "")
            # Sanitize for Latin-1 encoding
            message = message.encode("latin-1", errors="replace").decode("latin-1")
            pdf.multi_cell(0, 5, f"   {message}")
            pdf.ln(2)

        pdf.ln(3)

    # ── AI Narration ─────────────────────────────────────────────────────
    if narration:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "ANALISIS DAN REKOMENDASI", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        # Sanitize narration for Latin-1
        safe_narration = narration.encode("latin-1", errors="replace").decode("latin-1")
        pdf.multi_cell(0, 5, safe_narration)
        pdf.ln(5)

    # ── Legal Basis ──────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "DASAR HUKUM", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)

    regulations = set()
    for r in all_results:
        reg = r.get("regulation", "")
        if reg:
            regulations.add(reg)

    if not regulations:
        regulations = {
            "PerBPOM No. 13 Tahun 2019 tentang Batas Maksimal Cemaran Mikroba dalam Pangan Olahan",
            "Peraturan BPOM Nomor 9 Tahun 2022 tentang Persyaratan Cemaran Logam Berat dalam Pangan Olahan",
            "Peraturan BPOM Nomor 22 Tahun 2021 tentang Tata Cara Penerbitan Izin CPPOB",
        }

    for i, reg in enumerate(sorted(regulations), 1):
        safe_reg = reg.encode("latin-1", errors="replace").decode("latin-1")
        pdf.cell(0, 5, f"{i}. {safe_reg}", new_x="LMARGIN", new_y="NEXT")

    # ── Save PDF ─────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    pdf.output(output_path)
    logger.info(f"✅ PDF report saved: {output_path}")

    return output_path


# ─── Markdown Report ─────────────────────────────────────────────────────────


def generate_markdown_report(
    extracted_data: dict,
    category: str,
    compliance_result: dict,
    narration: str = "",
) -> str:
    """
    Generate a Markdown-formatted compliance report (for Gradio display).
    """
    violations = compliance_result.get("violations", [])
    passed = compliance_result.get("passed", [])
    missing = compliance_result.get("missing", [])
    overall = compliance_result.get("overall_status", "N/A")
    total = len(violations) + len(passed) + len(missing)

    status_icon = "❌ TIDAK MEMENUHI" if overall == "FAIL" else "✅ MEMENUHI"

    md = f"""# LAPORAN COMPLIANCE BPOM

## Informasi Produk
| Field | Value |
|---|---|
| Nama Produk | {extracted_data.get('nama_produk', 'N/A')} |
| Perusahaan | {extracted_data.get('perusahaan', 'N/A')} |
| Tanggal Uji | {extracted_data.get('tanggal_uji', 'N/A')} |
| Kategori | {category} |
| **Status** | **{status_icon}** |

## Ringkasan Eksekutif
Dari **{total}** parameter yang diperiksa: **{len(passed)}** PASS, **{len(violations)}** FAIL, **{len(missing)}** MISSING.

## Detail Hasil Uji

| Parameter | Nilai | Batas | Status | Pasal |
|---|---|---|---|---|
"""

    for r in passed:
        md += f"| {r.get('param', '')} | {r.get('found', '')} | {r.get('threshold_max', r.get('required', ''))} | ✅ PASS | {r.get('pasal', '')} |\n"

    for r in violations:
        md += f"| **{r.get('param', '')}** | **{r.get('found', '')}** | **{r.get('threshold_max', r.get('required', ''))}** | ❌ FAIL | **{r.get('pasal', '')}** |\n"

    for r in missing:
        md += f"| {r.get('param', '')} | {r.get('found', '')} | - | ⚠️ MISSING | {r.get('pasal', '')} |\n"

    if violations:
        md += "\n## Temuan Ketidaksesuaian\n\n"
        for i, v in enumerate(violations, 1):
            md += f"{i}. **{v.get('param', '')}**: {v.get('message', '')}\n\n"

    if narration:
        md += f"\n## Analisis dan Rekomendasi\n\n{narration}\n"

    md += f"\n---\n*Laporan dihasilkan pada {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"

    return md


# ─── Standalone Test ─────────────────────────────────────────────────────────


def main():
    """Test report generation with sample data."""
    print("=" * 60)
    print("REPORT GENERATOR TEST")
    print("=" * 60)

    sample_data = {
        "nama_produk": "Vita-X Suplemen Vitamin C",
        "perusahaan": "PT Maju Sehat Indonesia",
        "tanggal_uji": "2024-03-15",
    }

    sample_result = {
        "overall_status": "FAIL",
        "violations": [
            {
                "param": "ALT",
                "status": "FAIL",
                "found": 2500000.0,
                "threshold_max": 100000.0,
                "unit": "CFU/g",
                "pasal": "Lampiran I Tabel 1",
                "regulation": "PerBPOM No. 13 Tahun 2019",
                "message": "ALT = 2500000.0 CFU/g MELEBIHI batas max 100000.0 CFU/g",
            },
            {
                "param": "Timbal_Pb",
                "status": "FAIL",
                "found": 3.5,
                "threshold_max": 2.0,
                "unit": "mg/kg",
                "pasal": "Lampiran Tabel 1",
                "regulation": "PerBPOM No. 9 Tahun 2022",
                "message": "Timbal_Pb = 3.5 mg/kg MELEBIHI batas max 2.0 mg/kg",
            },
        ],
        "passed": [
            {"param": "E_coli", "status": "PASS", "found": "negatif", "threshold_max": None, "required": "negatif", "unit": "/g", "pasal": "Lampiran I Tabel 1", "regulation": "PerBPOM No. 13 Tahun 2019"},
            {"param": "Salmonella", "status": "PASS", "found": "negatif", "threshold_max": None, "required": "negatif", "unit": "/25g", "pasal": "Lampiran I Tabel 1", "regulation": "PerBPOM No. 13 Tahun 2019"},
            {"param": "Kadmium_Cd", "status": "PASS", "found": 0.8, "threshold_max": 1.0, "unit": "mg/kg", "pasal": "Lampiran Tabel 1", "regulation": "PerBPOM No. 9 Tahun 2022"},
        ],
        "missing": [],
    }

    narration = "Ditemukan 2 pelanggaran pada produk suplemen. ALT melebihi batas 25x lipat. Timbal melebihi batas 1.75x."

    # Test PDF generation
    output_pdf = "test_laporan_compliance.pdf"
    pdf_path = generate_pdf_report(sample_data, "SUPLEMEN", sample_result, narration, output_pdf)
    print(f"\n✅ PDF generated: {pdf_path}")

    # Test Markdown generation
    md_report = generate_markdown_report(sample_data, "SUPLEMEN", sample_result, narration)
    print(f"\n📝 Markdown Report Preview:\n")
    print(md_report[:500])

    # Clean up test file
    if os.path.exists(output_pdf):
        print(f"\n✅ PDF file exists ({os.path.getsize(output_pdf)} bytes)")

    print("\n✅ Report generator test complete!")


if __name__ == "__main__":
    main()
