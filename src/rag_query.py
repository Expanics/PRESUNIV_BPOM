"""
BPOM Compliance System — Step 5: RAG Query (Semantic Search)

Purpose:
    Perform semantic search on ChromaDB to retrieve relevant regulation
    passages for a given product category and query.
    
    Uses paraphrase-multilingual-MiniLM-L12-v2 for query embedding.
    Searches ONLY the collection for the specified category.

Output:
    List of {teks, source, pasal, halaman, score}

Usage:
    python src/rag_query.py
"""

import os
import logging
from typing import Optional

import chromadb
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─── Configuration ───────────────────────────────────────────────────────────

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

COLLECTION_MAP = {
    "SUPLEMEN": "bpom_suplemen",
    "DAIRY": "bpom_dairy",
    "DAGING_OLAHAN": "bpom_daging_olahan",
    "BUAH_SAYUR": "bpom_buah_sayur",
}

# Singleton model cache to avoid reloading
_model_cache: Optional[SentenceTransformer] = None


def _get_model() -> SentenceTransformer:
    """Load embedding model (cached singleton)."""
    global _model_cache
    if _model_cache is None:
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        _model_cache = SentenceTransformer(EMBEDDING_MODEL)
        logger.info("✅ Embedding model loaded")
    return _model_cache


# ─── Query Function ─────────────────────────────────────────────────────────


def query_regulations(category: str, query_text: str,
                       top_k: int = 5) -> list[dict]:
    """
    Semantic search ChromaDB for the specified category.
    
    Args:
        category: SUPLEMEN | DAIRY | DAGING_OLAHAN | BUAH_SAYUR
        query_text: natural language query (Indonesian or English)
        top_k: number of results to return
    
    Returns:
        List of dicts with keys: teks, source, pasal, halaman, score
    """
    if category not in COLLECTION_MAP:
        logger.error(f"Unknown category: {category}")
        return []

    collection_name = COLLECTION_MAP[category]

    try:
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        collection = client.get_collection(collection_name)
    except Exception as e:
        logger.error(f"Failed to open collection {collection_name}: {e}")
        return []

    count = collection.count()
    if count == 0:
        logger.warning(f"⚠️  Collection {collection_name} is empty. Run ingest.py first.")
        return []

    logger.info(f"🔍 Querying {collection_name} ({count} chunks) for: '{query_text[:80]}...'")

    model = _get_model()
    query_embedding = model.encode([query_text])[0].tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, count),
        include=["documents", "metadatas", "distances"],
    )

    # Parse results
    output = []
    for i in range(len(results["documents"][0])):
        distance = results["distances"][0][i]
        # ChromaDB cosine distance → similarity (1 - distance for cosine)
        score = 1 - distance

        output.append({
            "teks": results["documents"][0][i],
            "source": results["metadatas"][0][i].get("source", ""),
            "pasal": results["metadatas"][0][i].get("pasal", ""),
            "halaman": results["metadatas"][0][i].get("halaman_start", 0),
            "kategori": results["metadatas"][0][i].get("kategori", ""),
            "score": round(score, 4),
        })

    logger.info(f"✅ Found {len(output)} results (top score: {output[0]['score'] if output else 'N/A'})")
    return output


def query_for_violations(category: str, violations: list[dict],
                          top_k: int = 5) -> list[dict]:
    """
    Query regulations relevant to detected violations.
    Builds a combined query from violation params and messages.
    """
    if not violations:
        return []

    # Build query from violation details
    query_parts = []
    for v in violations:
        param = v.get("param", "")
        pasal = v.get("pasal", "")
        query_parts.append(f"batas {param} {pasal}")

    combined_query = " ".join(query_parts)
    logger.info(f"🔍 Querying for violations: {combined_query[:100]}...")

    return query_regulations(category, combined_query, top_k=top_k)


# ─── Standalone Test ─────────────────────────────────────────────────────────


def main():
    """Test RAG query with a sample query."""
    print("=" * 60)
    print("RAG QUERY TEST")
    print("=" * 60)

    # Test query
    test_category = "SUPLEMEN"
    test_query = "batas maksimal cemaran mikroba suplemen kesehatan ALT"

    print(f"\n📂 Category: {test_category}")
    print(f"🔍 Query: {test_query}")

    results = query_regulations(test_category, test_query, top_k=5)

    if not results:
        print("\n⚠️  No results found. Make sure to run ingest.py first!")
        print("    Command: python src/ingest.py")
        return

    print(f"\n📋 Top {len(results)} Results:")
    for i, r in enumerate(results, 1):
        print(f"\n  [{i}] Score: {r['score']:.4f}")
        print(f"      Source: {r['source']}")
        print(f"      Pasal: {r['pasal']}")
        print(f"      Page: {r['halaman']}")
        print(f"      Text: {r['teks'][:150]}...")

    # Test violation-based query
    print("\n" + "=" * 60)
    print("VIOLATION-BASED QUERY TEST")
    print("=" * 60)

    sample_violations = [
        {"param": "ALT", "pasal": "Lampiran I Tabel 1", "message": "ALT melebihi batas"},
        {"param": "Timbal_Pb", "pasal": "Lampiran Tabel 1", "message": "Timbal melebihi batas"},
    ]

    violation_results = query_for_violations(test_category, sample_violations)
    print(f"\n📋 Violation query returned {len(violation_results)} results")
    for i, r in enumerate(violation_results, 1):
        print(f"  [{i}] {r['pasal']} from {r['source']} (score: {r['score']:.4f})")

    print("\n✅ RAG query test complete!")


if __name__ == "__main__":
    main()
