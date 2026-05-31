"""
BPOM Compliance System — Step 6: LLM Narrator (Gemini Flash)

Purpose:
    Use Gemini 1.5 Flash ONLY for:
    - Narrating violation explanations in Indonesian
    - Summarizing compliance results
    - Generating final reports
    
    NEVER for PASS/FAIL decisions. Temperature = 0.1.

Usage:
    python src/llm_narrator.py
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─── Gemini Configuration ───────────────────────────────────────────────────

_gemini_model = None


def _get_gemini_model():
    """Lazily initialize Gemini model (singleton)."""
    global _gemini_model
    if _gemini_model is not None:
        return _gemini_model

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_key_here":
        logger.warning("⚠️  GEMINI_API_KEY not set. LLM narration disabled.")
        return None

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)

        _gemini_model = genai.GenerativeModel(
            "gemini-2.0-flash",
            generation_config=genai.GenerationConfig(
                temperature=0.1,       # WAJIB rendah — minimize hallucination
                top_p=0.9,
                max_output_tokens=2048,
            ),
        )
        logger.info("✅ Gemini Flash model initialized (temp=0.1, top_p=0.9)")
        return _gemini_model

    except Exception as e:
        logger.error(f"Failed to initialize Gemini: {e}")
        return None


# ─── Narration Functions ─────────────────────────────────────────────────────


def narrate_violations(extracted_data: dict, category: str,
                        violations: list[dict],
                        rag_evidence: list[dict]) -> str:
    """
    Generate human-readable narration of violations.
    LLM ONLY explains — it does NOT change PASS/FAIL.
    
    Args:
        extracted_data: parsed lab data
        category: product category
        violations: list of violation dicts from rule engine
        rag_evidence: list of relevant regulation passages from RAG
    
    Returns:
        Narration text in Indonesian
    """
    if not violations:
        return "✅ Semua parameter memenuhi standar BPOM yang berlaku. Tidak ditemukan pelanggaran."

    model = _get_gemini_model()
    if model is None:
        # Fallback: generate basic narration without LLM
        return _fallback_narration(violations)

    # Load prompt template
    prompt_path = Path(__file__).parent.parent / "prompts" / "compliance_llm_prompt.txt"
    if prompt_path.exists():
        prompt_template = prompt_path.read_text(encoding="utf-8")
    else:
        prompt_template = (
            "Jelaskan pelanggaran berikut dalam bahasa Indonesia formal.\n"
            "Produk: {nama_produk} ({kategori})\n"
            "Violations: {violations_json}\n"
            "Regulasi: {rag_evidence}\n"
            "Format: per violation dengan pasal."
        )

    # Build RAG evidence text
    rag_text = "\n".join(
        f"[{e.get('pasal', 'N/A')} dari {e.get('source', 'N/A')}]: {e.get('teks', '')[:300]}"
        for e in rag_evidence[:5]
    ) if rag_evidence else "Tidak ada data regulasi tambahan."

    prompt = prompt_template.format(
        nama_produk=extracted_data.get("nama_produk", "Tidak diketahui"),
        kategori=category,
        violations_json=json.dumps(violations, indent=2, ensure_ascii=False),
        rag_evidence=rag_text,
    )

    try:
        logger.info("🤖 Generating violation narration with Gemini Flash...")
        response = model.generate_content(prompt)
        narration = response.text
        logger.info(f"✅ Narration generated ({len(narration)} chars)")
        return narration
    except Exception as e:
        logger.error(f"Gemini narration failed: {e}")
        return _fallback_narration(violations)


def generate_report_narration(extracted_data: dict, category: str,
                               compliance_result: dict,
                               user_edits: Optional[dict] = None) -> str:
    """
    Generate final report narration using Gemini Flash.
    
    Args:
        extracted_data: parsed lab data
        category: product category
        compliance_result: full result from rule engine
        user_edits: optional user edits/revisions
    
    Returns:
        Formatted report text in Indonesian
    """
    model = _get_gemini_model()
    if model is None:
        return _fallback_report(extracted_data, category, compliance_result)

    prompt_path = Path(__file__).parent.parent / "prompts" / "report_prompt.txt"
    if prompt_path.exists():
        prompt_template = prompt_path.read_text(encoding="utf-8")
    else:
        prompt_template = (
            "Buat laporan compliance BPOM untuk:\n"
            "Produk: {nama_produk}\nPerusahaan: {perusahaan}\n"
            "Tanggal: {tanggal}\nKategori: {kategori}\n"
            "Hasil: {all_results_json}\nViolations: {violations_json}\n"
            "Edits: {user_edits}"
        )

    all_results = compliance_result.get("passed", []) + compliance_result.get("violations", [])

    prompt = prompt_template.format(
        nama_produk=extracted_data.get("nama_produk", ""),
        perusahaan=extracted_data.get("perusahaan", ""),
        tanggal=extracted_data.get("tanggal_uji", ""),
        kategori=category,
        all_results_json=json.dumps(all_results, indent=2, ensure_ascii=False),
        violations_json=json.dumps(
            compliance_result.get("violations", []), indent=2, ensure_ascii=False
        ),
        user_edits=json.dumps(user_edits or {}, indent=2, ensure_ascii=False),
    )

    try:
        logger.info("🤖 Generating final report with Gemini Flash...")
        response = model.generate_content(prompt)
        report = response.text
        logger.info(f"✅ Report generated ({len(report)} chars)")
        return report
    except Exception as e:
        logger.error(f"Gemini report generation failed: {e}")
        return _fallback_report(extracted_data, category, compliance_result)


# ─── Fallback (No LLM) ──────────────────────────────────────────────────────


def _fallback_narration(violations: list[dict]) -> str:
    """Generate basic narration without LLM (template-based)."""
    lines = ["## Temuan Ketidaksesuaian\n"]
    for i, v in enumerate(violations, 1):
        param = v.get("param", "N/A")
        found = v.get("found", "N/A")
        threshold = v.get("threshold_max", v.get("required", "N/A"))
        unit = v.get("unit", "")
        pasal = v.get("pasal", "N/A")
        regulation = v.get("regulation", "")

        lines.append(
            f"{i}. **{param}**: Ditemukan {found} {unit}, "
            f"batas maksimum {threshold} {unit}\n"
            f"   Berdasarkan {regulation} ({pasal}): "
            f"Parameter {param} melebihi batas yang ditetapkan.\n"
            f"   Rekomendasi: Evaluasi proses produksi dan bahan baku "
            f"untuk menurunkan kadar {param}.\n"
        )
    return "\n".join(lines)


def _fallback_report(extracted_data: dict, category: str,
                      compliance_result: dict) -> str:
    """Generate basic report without LLM."""
    violations = compliance_result.get("violations", [])
    passed = compliance_result.get("passed", [])
    overall = compliance_result.get("overall_status", "N/A")

    report = f"""---
# LAPORAN COMPLIANCE BPOM

**Nama Produk**: {extracted_data.get('nama_produk', 'N/A')}
**Perusahaan**: {extracted_data.get('perusahaan', 'N/A')}
**Tanggal Uji**: {extracted_data.get('tanggal_uji', 'N/A')}
**Kategori**: {category}
**Status Keseluruhan**: {'❌ TIDAK MEMENUHI' if overall == 'FAIL' else '✅ MEMENUHI'}

## RINGKASAN EKSEKUTIF
Dari {len(passed) + len(violations)} parameter yang diperiksa, 
{len(passed)} parameter memenuhi standar dan {len(violations)} parameter 
tidak memenuhi standar BPOM yang berlaku.

## DETAIL HASIL UJI

### ✅ Parameter MEMENUHI Standar
"""
    for p in passed:
        report += f"- {p.get('param', 'N/A')}: {p.get('found', 'N/A')} {p.get('unit', '')} ({p.get('pasal', '')})\n"

    if violations:
        report += "\n### ❌ Parameter TIDAK MEMENUHI Standar\n"
        for v in violations:
            report += (
                f"- **{v.get('param', 'N/A')}**: {v.get('found', 'N/A')} {v.get('unit', '')} "
                f"(batas: {v.get('threshold_max', v.get('required', 'N/A'))} {v.get('unit', '')}) "
                f"— {v.get('pasal', 'N/A')}\n"
            )

    report += "\n---\n"
    return report


# ─── Standalone Test ─────────────────────────────────────────────────────────


def main():
    """Test LLM narrator with sample violations."""
    print("=" * 60)
    print("LLM NARRATOR TEST")
    print("=" * 60)

    sample_data = {
        "nama_produk": "Vita-X Suplemen Vitamin C",
        "perusahaan": "PT Maju Sehat Indonesia",
        "tanggal_uji": "2024-03-15",
    }

    sample_violations = [
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
    ]

    sample_rag = [
        {
            "teks": "Batas maksimal ALT untuk suplemen kesehatan adalah 10^5 CFU/g",
            "source": "BPOM_RULE.pdf",
            "pasal": "Lampiran I Tabel 1",
        },
    ]

    # Test narration
    print("\n📝 Testing violation narration...")
    narration = narrate_violations(sample_data, "SUPLEMEN", sample_violations, sample_rag)
    print(f"\n{narration}")

    # Test report generation
    print("\n" + "=" * 60)
    print("📄 Testing report generation...")
    compliance_result = {
        "overall_status": "FAIL",
        "violations": sample_violations,
        "passed": [
            {"param": "E_coli", "status": "PASS", "found": "negatif", "unit": "/g", "pasal": "Lampiran I Tabel 1"},
        ],
    }
    report = generate_report_narration(sample_data, "SUPLEMEN", compliance_result)
    print(f"\n{report}")

    print("\n✅ LLM narrator test complete!")


if __name__ == "__main__":
    main()
