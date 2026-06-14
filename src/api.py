"""
BPOM Compliance System — FastAPI Backend

Menggantikan Gradio dengan REST API yang bisa dikonsumsi oleh React frontend.

Endpoints:
    POST /api/analyze    — Upload file atau text, jalankan full pipeline
    POST /api/report     — Generate PDF + markdown report
    GET  /api/download   — Download PDF yang sudah digenerate
    GET  /health         — Health check
"""

import os
import sys
import logging
import tempfile
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from src.extractor import extract_and_parse
from src.classifier import classify_product
from src.rule_engine import run_full_compliance_check
from src.report_generator import generate_pdf_report, generate_markdown_report

# Thread pool untuk menjalankan blocking calls (embedding model, Gemini)
_executor = ThreadPoolExecutor(max_workers=2)

# RAG & LLM — opsional, skip jika model/library bermasalah
try:
    from src.rag_query import query_for_violations
    from src.llm_narrator import narrate_violations
    RAG_AVAILABLE = True
    logging.info("✅ RAG & LLM tersedia")
except Exception as _e:
    logging.warning(f"⚠️  RAG/LLM tidak tersedia (akan skip): {_e}")
    RAG_AVAILABLE = False
    query_for_violations = None
    narrate_violations = None

# Timeout RAG+LLM dalam detik — jika lebih dari ini, pakai fallback narasi
RAG_TIMEOUT_SECONDS = 45

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ─── App Setup ────────────────────────────────────────────────────────────────

app = FastAPI(title="BPOM Compliance AI API", version="2.4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Pydantic Models ──────────────────────────────────────────────────────────

class ReportRequest(BaseModel):
    category: str
    narration: str
    extracted: dict
    compliance: dict


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _format_dasar_hukum(item: dict) -> str:
    regulation = item.get("regulation", "")
    pasal = item.get("pasal", "")
    if regulation and pasal:
        return f"{regulation}, {pasal}"
    return regulation or pasal or "-"


def _build_compliance_rows(compliance: dict) -> list:
    rows = []
    for v in compliance.get("violations", []):
        rows.append({
            "param": v.get("param", ""),
            "found": str(v.get("found", "")),
            "threshold": str(v.get("threshold_max", v.get("required", ""))),
            "status": "FAIL",
            "dasarHukum": _format_dasar_hukum(v),
        })
    for p in compliance.get("passed", []):
        rows.append({
            "param": p.get("param", ""),
            "found": str(p.get("found", "")),
            "threshold": str(p.get("threshold_max", p.get("required", ""))),
            "status": "PASS",
            "dasarHukum": _format_dasar_hukum(p),
        })
    for m in compliance.get("missing", []):
        rows.append({
            "param": m.get("param", ""),
            "found": "-",
            "threshold": "-",
            "status": "MISSING",
            "dasarHukum": _format_dasar_hukum(m),
        })
    return rows


def _build_violation_cards(compliance: dict, rag_results: list) -> list:
    cards = []
    violations = compliance.get("violations", [])

    rag_map = {}
    for r in rag_results or []:
        if isinstance(r, dict):
            key = r.get("param", r.get("parameter", ""))
            if key:
                rag_map[key.lower()] = r

    for i, v in enumerate(violations):
        param = v.get("param", "")
        found = str(v.get("found", ""))
        threshold = str(v.get("threshold_max", v.get("required", "")))
        regulation = _format_dasar_hukum(v)

        # Severity by ratio
        severity = "medium"
        try:
            fn = float(str(found).replace(",", ".").split()[0])
            tn = float(str(threshold).replace(",", ".").split()[0])
            ratio = fn / tn if tn > 0 else 2
            severity = "high" if ratio >= 1.5 else "medium" if ratio >= 1.1 else "low"
        except Exception:
            severity = "high" if i == 0 else "medium"

        rag_data = rag_map.get(param.lower(), {})
        rekomendasi = rag_data.get("rekomendasi", rag_data.get("recommendation",
            f"Nilai {param} ({found}) melebihi batas regulasi BPOM ({threshold}). "
            f"Lakukan reformulasi produk untuk memenuhi persyaratan {regulation}."
        ))

        cards.append({
            "id": str(i + 1),
            "namaParameter": param,
            "nilaiTemuan": found,
            "batasRegulasi": f"{threshold} ({regulation})",
            "rekomendasi": rekomendasi,
            "severity": severity,
        })
    return cards


def _simple_narration(compliance: dict) -> str:
    """Narasi sederhana tanpa LLM — dari data violation langsung."""
    violations = compliance.get("violations", [])
    passed = compliance.get("passed", [])
    missing = compliance.get("missing", [])

    total = len(violations) + len(passed) + len(missing)
    pct = round(len(passed) / total * 100, 1) if total > 0 else 0

    if not violations:
        return f"✅ Semua {len(passed)} parameter memenuhi standar BPOM yang berlaku."

    params_fail = ", ".join(v.get("param", "") for v in violations[:5])
    narr = (
        f"Berdasarkan hasil analisis rule engine terhadap {total} parameter uji, "
        f"produk TIDAK MEMENUHI syarat BPOM dalam kondisi formulasi saat ini.\n\n"
        f"• {len(passed)} parameter PASS ({pct}% kepatuhan)\n"
        f"• {len(violations)} parameter FAIL: {params_fail}\n"
    )
    if missing:
        narr += f"• {len(missing)} parameter data tidak tersedia (MISSING)\n"
    narr += "\nProdusen disarankan melakukan reformulasi sebelum pengajuan registrasi ke BPOM."
    return narr


def _determine_narration(extracted: dict, category: str, compliance: dict) -> str:
    has_violations = bool(compliance.get("violations"))
    has_passed = bool(compliance.get("passed"))
    has_missing = bool(compliance.get("missing"))

    if has_violations:
        return _simple_narration(compliance)
    elif has_passed and not has_missing:
        return f"✅ Semua {len(compliance.get('passed', []))} parameter memenuhi standar BPOM yang berlaku."
    elif has_passed and has_missing:
        return (
            f"✅ {len(compliance.get('passed', []))} parameter memenuhi standar BPOM.\n"
            f"⚠️ {len(compliance.get('missing', []))} parameter tidak memiliki data (MISSING). "
            f"Lengkapi data lab untuk pengecekan lengkap."
        )
    else:
        return "⚠️ Tidak ada data parameter yang terdeteksi dari dokumen."


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.post("/api/analyze")
async def analyze(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    category_override: Optional[str] = Form(None),
):
    logger.info("=" * 50)
    logger.info("🚀 NEW ANALYSIS REQUEST")

    if not file and not text:
        raise HTTPException(status_code=400, detail="Kirim file atau teks input.")

    # Simpan file upload ke temp
    file_path = None
    tmp_path = None
    if file and file.filename:
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        file_path = tmp_path
        logger.info(f"📁 File: {file.filename} → {file_path}")

    try:
        # 1. Extract
        extracted = extract_and_parse(file_path=file_path, raw_text=text or "")
        if not extracted:
            raise HTTPException(status_code=422, detail="Tidak ada data yang berhasil diekstrak dari dokumen.")

        # 2. Classify
        if category_override:
            category = category_override
        else:
            try:
                class_result = classify_product(extracted)
                category = class_result["kategori"]
            except Exception as e:
                logger.warning(f"Klasifikasi gagal: {e} → default SUPLEMEN")
                category = "SUPLEMEN"

        # 3. Rule Engine
        compliance = run_full_compliance_check(extracted, category)

        # 4. Narasi — coba LLM dengan timeout, fallback ke simple narration
        narration = _determine_narration(extracted, category, compliance)
        rag_results = []

        if compliance.get("violations") and RAG_AVAILABLE:
            try:
                loop = asyncio.get_event_loop()

                def _run_rag():
                    results = query_for_violations(category, compliance["violations"])
                    llm_text = narrate_violations(
                        extracted, category, compliance["violations"], results
                    )
                    return results, llm_text

                rag_future = loop.run_in_executor(_executor, _run_rag)
                rag_results, llm_narration = await asyncio.wait_for(
                    rag_future, timeout=RAG_TIMEOUT_SECONDS
                )
                if llm_narration:
                    narration = llm_narration

            except asyncio.TimeoutError:
                logger.warning(f"⏱️  RAG/LLM timeout ({RAG_TIMEOUT_SECONDS}s) — pakai fallback narasi")
            except Exception as e:
                logger.warning(f"RAG/LLM gagal (pakai fallback): {e}")

        # 5. Build response
        rows = _build_compliance_rows(compliance)
        violation_cards = _build_violation_cards(compliance, rag_results)

        pass_count = len(compliance.get("passed", []))
        fail_count = len(compliance.get("violations", []))
        miss_count = len(compliance.get("missing", []))
        total = pass_count + fail_count + miss_count
        compliance_pct = round(pass_count / total * 100, 1) if total > 0 else 0

        logger.info(f"✅ Selesai: {pass_count} PASS, {fail_count} FAIL, {miss_count} MISSING")

        return JSONResponse({
            "success": True,
            "category": category,
            "extracted": extracted,
            "compliance": compliance,
            "rows": rows,
            "violationCards": violation_cards,
            "narration": narration,
            "summary": {
                "pass": pass_count,
                "fail": fail_count,
                "missing": miss_count,
                "total": total,
                "compliancePct": compliance_pct,
            },
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


@app.post("/api/report")
async def generate_report(body: ReportRequest):
    logger.info("📄 Generating Final Reports...")
    if not body.extracted or not body.compliance:
        raise HTTPException(status_code=400, detail="Data tidak lengkap.")
    try:
        md_report = generate_markdown_report(
            body.extracted, body.category, body.compliance, body.narration
        )
        pdf_path = str(PROJECT_ROOT / "laporan_compliance_bpom.pdf")
        generate_pdf_report(
            body.extracted, body.category, body.compliance, body.narration, pdf_path
        )
        return JSONResponse({"success": True, "markdown": md_report, "pdfReady": True})
    except Exception as e:
        logger.error(f"Report error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download")
async def download_report():
    pdf_path = PROJECT_ROOT / "laporan_compliance_bpom.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Laporan PDF belum dibuat.")
    return FileResponse(
        path=str(pdf_path),
        filename="laporan_compliance_bpom.pdf",
        media_type="application/pdf",
    )


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.4.0", "rag": RAG_AVAILABLE}

# Serve React Frontend (For Hugging Face Spaces / Docker deployment)
from fastapi.staticfiles import StaticFiles

dist_dir = PROJECT_ROOT / "BPOM Compliance AI UI Redesign" / "dist"
if dist_dir.exists():
    logger.info(f"Serving static frontend from {dist_dir}")
    # Mount assets folder
    assets_dir = dist_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    
    # Catch-all route to serve index.html for SPA routing (must be last)
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        # Don't intercept API routes if they return 404
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")
        
        # Check if requested file exists (like favicon.ico)
        file_path = dist_dir / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
            
        # Fallback to index.html for React routing
        return FileResponse(str(dist_dir / "index.html"))

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting BPOM Compliance AI API on :8000")
    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=True)
