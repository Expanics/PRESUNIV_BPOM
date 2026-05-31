"""
BPOM Compliance System — Step 1: Ingest Regulations to ChromaDB

Purpose:
    Extract text from regulation PDFs, chunk per-Pasal (chunk_size=500, overlap=50),
    embed with paraphrase-multilingual-MiniLM-L12-v2, and upsert into
    ChromaDB persistent collections (one per product category).

Collections created:
    - bpom_suplemen
    - bpom_dairy
    - bpom_daging_olahan
    - bpom_buah_sayur

Usage:
    python src/ingest.py

Expected output:
    Terminal logs showing each PDF being ingested + chunk counts per collection.
"""

import re
import os
import sys
import logging
from pathlib import Path

import pdfplumber
import chromadb
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# ─── Configuration ───────────────────────────────────────────────────────────

load_dotenv()

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
REGULATIONS_PATH = os.getenv("REGULATIONS_PATH", "./data/regulations")

CATEGORY_MAP = {
    "SUPLEMEN": "bpom_suplemen",
    "DAIRY": "bpom_dairy",
    "DAGING_OLAHAN": "bpom_daging_olahan",
    "BUAH_SAYUR": "bpom_buah_sayur",
}

# Lightweight multilingual model — fits MacBook Air M2 8GB easily
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# ─── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─── PDF Text Extraction ────────────────────────────────────────────────────


def clean_line(line: str) -> str:
    """Clean a single line from PDF extraction artefacts."""
    line = line.replace("\xa0", " ").replace("\ufffe", "-")
    # Remove page number markers like  -7-  or  - 7 -
    line = re.sub(r"^[-–]\s*\d+\s*[-–]\s*$", " ", line)
    # Remove jdih watermarks
    line = re.sub(r"\bjdih\.pom\.go\.id\b", " ", line, flags=re.IGNORECASE)
    # Fix common OCR typo: "Pasa 5" → "Pasal 5"
    line = re.sub(r"^\s*Pasa\s+(\d+)\s*$", r"Pasal \1", line)
    # Collapse whitespace
    line = re.sub(r"[ \t]+", " ", line)
    return line.strip()


def extract_pdf_lines(pdf_path: str) -> list[dict]:
    """
    Extract all text lines from a PDF, page by page.
    Returns list of {"page": int, "line": str}.
    """
    rows: list[dict] = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_no, page in enumerate(pdf.pages, start=1):
                text = page.extract_text(x_tolerance=1, y_tolerance=3) or ""
                for raw_line in text.splitlines():
                    line = clean_line(raw_line)
                    if line:
                        rows.append({"page": page_no, "line": line})
    except Exception as e:
        logger.error(f"Failed to extract PDF {pdf_path}: {e}")
    return rows


# ─── Pasal-based Chunking ───────────────────────────────────────────────────


def chunk_by_pasal(rows: list[dict], source_filename: str) -> list[dict]:
    """
    Split extracted PDF lines into chunks grouped by Pasal heading.
    If a chunk exceeds CHUNK_SIZE chars, it is further split with overlap.

    Returns list of dicts:
        {pasal_id, teks, halaman_start, halaman_end, source}
    """
    chunks: list[dict] = []
    current_pasal = "HEADER"
    current_lines: list[str] = []
    current_start_page = 1

    for row in rows:
        line = row["line"]
        # Detect Pasal heading: "Pasal 1", "Pasal 23", etc.
        pasal_match = re.match(r"^Pasal\s+(\d+)\s*$", line)

        if pasal_match:
            # Save previous chunk
            if current_lines:
                _add_chunks(
                    chunks, current_pasal, current_lines,
                    current_start_page, row["page"], source_filename
                )
            current_pasal = f"Pasal {pasal_match.group(1)}"
            current_lines = [line]
            current_start_page = row["page"]
        else:
            current_lines.append(line)

    # Save last chunk
    if current_lines:
        last_page = rows[-1]["page"] if rows else current_start_page
        _add_chunks(
            chunks, current_pasal, current_lines,
            current_start_page, last_page, source_filename
        )

    # If no Pasal headings found at all, chunk the entire text
    if not chunks and rows:
        full_text = " ".join(r["line"] for r in rows)
        for i in range(0, len(full_text), CHUNK_SIZE - CHUNK_OVERLAP):
            chunk_text = full_text[i:i + CHUNK_SIZE]
            if len(chunk_text.strip()) > 20:
                chunks.append({
                    "pasal_id": "FULL_DOC",
                    "teks": chunk_text.strip(),
                    "halaman_start": rows[0]["page"],
                    "halaman_end": rows[-1]["page"],
                    "source": source_filename,
                })

    return chunks


def _add_chunks(
    chunks: list[dict],
    pasal_id: str,
    lines: list[str],
    start_page: int,
    end_page: int,
    source: str,
) -> None:
    """Join lines into text and split if > CHUNK_SIZE chars."""
    full_text = " ".join(lines).strip()
    if len(full_text) < 20:
        return

    if len(full_text) <= CHUNK_SIZE:
        chunks.append({
            "pasal_id": pasal_id,
            "teks": full_text,
            "halaman_start": start_page,
            "halaman_end": end_page,
            "source": source,
        })
    else:
        # Split into overlapping chunks
        step = CHUNK_SIZE - CHUNK_OVERLAP
        for i in range(0, len(full_text), step):
            chunk_text = full_text[i:i + CHUNK_SIZE]
            if len(chunk_text.strip()) > 20:
                chunks.append({
                    "pasal_id": pasal_id,
                    "teks": chunk_text.strip(),
                    "halaman_start": start_page,
                    "halaman_end": end_page,
                    "source": source,
                })


# ─── ChromaDB Ingest ────────────────────────────────────────────────────────


def ingest_all_regulations() -> dict[str, int]:
    """
    Main ingestion function. Reads all regulation PDFs from
    data/regulations/<CATEGORY>/*.pdf, chunks them, embeds, and upserts
    into ChromaDB.

    Returns dict mapping collection_name → total chunk count.
    """
    logger.info("=" * 60)
    logger.info("BPOM Regulation Ingestion — Starting")
    logger.info("=" * 60)

    # Initialise ChromaDB persistent client
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    logger.info(f"ChromaDB path: {os.path.abspath(CHROMA_DB_PATH)}")

    # Load embedding model
    logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)
    logger.info("✅ Embedding model loaded")

    reg_path = Path(REGULATIONS_PATH)
    if not reg_path.exists():
        logger.error(f"Regulations path not found: {reg_path}")
        sys.exit(1)

    results: dict[str, int] = {}

    for category, collection_name in CATEGORY_MAP.items():
        logger.info("-" * 50)
        logger.info(f"📂 Category: {category} → Collection: {collection_name}")

        # Get or create collection (safe to re-run)
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        cat_path = reg_path / category
        if not cat_path.exists():
            logger.warning(f"⚠️  Folder {cat_path} does not exist — skipping")
            results[collection_name] = 0
            continue

        pdf_files = list(cat_path.glob("*.pdf"))
        if not pdf_files:
            logger.warning(f"⚠️  No PDFs in {cat_path} — skipping")
            results[collection_name] = 0
            continue

        all_chunks: list[dict] = []

        for pdf_file in pdf_files:
            logger.info(f"  📄 Processing: {pdf_file.name}")
            rows = extract_pdf_lines(str(pdf_file))
            logger.info(f"     Extracted {len(rows)} lines")

            chunks = chunk_by_pasal(rows, pdf_file.name)
            logger.info(f"     Created {len(chunks)} chunks")
            all_chunks.extend(chunks)

        if not all_chunks:
            logger.warning(f"  No chunks created for {category}")
            results[collection_name] = 0
            continue

        # Embed all chunks
        texts = [c["teks"] for c in all_chunks]
        logger.info(f"  🧮 Embedding {len(texts)} chunks...")
        embeddings = model.encode(
            texts, batch_size=16, show_progress_bar=True
        )

        # Build IDs and metadata
        ids = [
            f"{c['source'].replace('.pdf', '')}_{c['pasal_id']}_{i}"
            for i, c in enumerate(all_chunks)
        ]
        metadatas = [
            {
                "source": c["source"],
                "pasal": c["pasal_id"],
                "halaman_start": c["halaman_start"],
                "halaman_end": c["halaman_end"],
                "kategori": category,
            }
            for c in all_chunks
        ]

        # Upsert in batches (ChromaDB has batch limits)
        BATCH_SIZE = 100
        for batch_start in range(0, len(ids), BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, len(ids))
            collection.upsert(
                ids=ids[batch_start:batch_end],
                embeddings=embeddings[batch_start:batch_end].tolist(),
                documents=texts[batch_start:batch_end],
                metadatas=metadatas[batch_start:batch_end],
            )

        count = collection.count()
        results[collection_name] = count
        logger.info(f"  ✅ {collection_name}: {count} total chunks in ChromaDB")

    # Summary
    logger.info("=" * 60)
    logger.info("INGESTION SUMMARY")
    logger.info("=" * 60)
    total = 0
    for coll_name, count in results.items():
        logger.info(f"  {coll_name}: {count} chunks")
        total += count
    logger.info(f"  TOTAL: {total} chunks across {len(results)} collections")
    logger.info("=" * 60)

    return results


# ─── Standalone Test ─────────────────────────────────────────────────────────


def main():
    """Standalone entry point for testing ingestion."""
    results = ingest_all_regulations()

    # Verify by querying each collection
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    print("\n📊 Verification — Collection counts:")
    for category, collection_name in CATEGORY_MAP.items():
        try:
            collection = client.get_collection(collection_name)
            count = collection.count()
            print(f"  {collection_name}: {count} chunks ✅")

            # Peek at first chunk
            peek = collection.peek(limit=1)
            if peek["documents"]:
                doc_preview = peek["documents"][0][:100]
                print(f"    Preview: {doc_preview}...")
        except Exception as e:
            print(f"  {collection_name}: ERROR — {e}")

    print("\n✅ Ingest complete!")


if __name__ == "__main__":
    main()
