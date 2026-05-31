"""
BPOM Compliance System — Step 3: Product Category Classifier

Purpose:
    Classify food products into BPOM categories:
    SUPLEMEN | DAIRY | DAGING_OLAHAN | BUAH_SAYUR

    Uses rule-based keyword matching first (free, fast, no API).
    Falls back to Gemini Flash only if confidence < 0.3.

Usage:
    python src/classifier.py
"""

import os
import re
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

# ─── Keyword Map for Rule-Based Classification ──────────────────────────────

KEYWORD_MAP = {
    "SUPLEMEN": [
        "suplemen", "vitamin", "mineral", "kapsul", "tablet", "herbal",
        "extrak", "kolagen", "omega", "probiotik", "suplemen kesehatan",
        "supplement", "capsule", "multivitamin", "nutraceutical",
        "obat tradisional", "jamu", "sachet",
    ],
    "DAIRY": [
        "susu", "yogurt", "keju", "kefir", "dairy", "laktosa", "whey",
        "krimer", "butter", "cream", "milk", "susu bubuk", "susu kental",
        "susu pasteurisasi", "susu UHT", "es krim", "ice cream",
        "pasteurisasi", "sapi", "uht", "fermentasi susu",
    ],
    "DAGING_OLAHAN": [
        "daging", "sosis", "nugget", "kornet", "bakso", "ham",
        "ikan", "udang", "seafood", "processed meat", "ayam olahan",
        "sarden", "tuna", "abon", "dendeng", "burger patty",
    ],
    "BUAH_SAYUR": [
        "buah", "sayur", "jus", "juice", "tomat", "wortel", "bayam",
        "pisang", "produk nabati", "vegetable", "fruit", "selai",
        "puree", "manisan", "keripik buah", "keripik sayur",
    ],
}

CONFIDENCE_THRESHOLD = 0.3  # Below this → use Gemini


# ─── Rule-Based Classifier ──────────────────────────────────────────────────


def classify_rule_based(text: str) -> tuple[str, float]:
    """
    Classify product category by keyword matching.
    Returns (category, confidence).
    Confidence = matched_keywords / total_keywords_matched_across_all_categories.
    """
    text_lower = text.lower()
    scores: dict[str, int] = {}

    for category, keywords in KEYWORD_MAP.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        scores[category] = score

    total = sum(scores.values())
    if total == 0:
        return "SUPLEMEN", 0.0  # Default fallback

    best_category = max(scores, key=scores.get)
    confidence = scores[best_category] / total

    logger.info(f"📊 Rule-based scores: {scores}")
    logger.info(f"📌 Best: {best_category} (confidence: {confidence:.2f})")

    return best_category, confidence


# ─── Gemini Flash Fallback ───────────────────────────────────────────────────


def classify_with_gemini(product_info: str) -> dict:
    """
    Use Gemini Flash API to classify product when rule-based confidence is low.
    Returns {"kategori": str, "confidence": float, "alasan": str}
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_key_here":
        logger.warning("⚠️  GEMINI_API_KEY not set. Using rule-based fallback.")
        category, conf = classify_rule_based(product_info)
        return {"kategori": category, "confidence": conf, "alasan": "Rule-based (no API key)"}

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)

        model = genai.GenerativeModel(
            "gemini-2.0-flash",
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                top_p=0.9,
                max_output_tokens=256,
            ),
        )

        prompt_path = Path(__file__).parent.parent / "prompts" / "classify_prompt.txt"
        if prompt_path.exists():
            prompt_template = prompt_path.read_text()
        else:
            prompt_template = (
                "Klasifikasikan produk berikut ke SATU kategori: "
                "SUPLEMEN, DAIRY, DAGING_OLAHAN, BUAH_SAYUR.\n\n"
                "Info produk: {nama_produk}\n{komposisi}\n{klaim}\n{proses}\n\n"
                'Jawab HANYA JSON: {{"kategori": "...", "confidence": 0.0-1.0, "alasan": "..."}}'
            )

        prompt = prompt_template.format(
            nama_produk=product_info,
            komposisi="",
            klaim="",
            proses="",
        )

        logger.info("🤖 Calling Gemini Flash for classification...")
        response = model.generate_content(prompt)
        response_text = response.text.strip()

        # Extract JSON from response
        json_match = re.search(r"\{[^}]+\}", response_text)
        if json_match:
            result = json.loads(json_match.group())
            logger.info(f"🤖 Gemini result: {result}")
            return result
        else:
            logger.warning(f"⚠️  Could not parse Gemini response: {response_text}")
            category, conf = classify_rule_based(product_info)
            return {"kategori": category, "confidence": conf, "alasan": "Gemini parse failed, rule-based fallback"}

    except Exception as e:
        logger.error(f"Gemini classification failed: {e}")
        category, conf = classify_rule_based(product_info)
        return {"kategori": category, "confidence": conf, "alasan": f"Gemini error: {e}"}




# ─── Public API ──────────────────────────────────────────────────────────────


def classify_product(extracted_data: dict) -> dict:
    """
    Main classification function.
    Uses rule-based first, falls back to Gemini if confidence < threshold.

    Args:
        extracted_data: dict from extractor.py with keys like
                       nama_produk, komposisi, klaim, proses

    Returns:
        {"kategori": str, "confidence": float, "alasan": str, "method": str}
    """
    # Combine relevant text fields for classification
    text_parts = [
        extracted_data.get("nama_produk", ""),
        extracted_data.get("komposisi", ""),
        extracted_data.get("klaim", ""),
        extracted_data.get("proses", ""),
    ]
    combined_text = " ".join(t for t in text_parts if t)

    if not combined_text.strip():
        logger.warning("⚠️  No text available for classification")
        return {
            "kategori": "SUPLEMEN",
            "confidence": 0.0,
            "alasan": "No input text",
            "method": "default",
        }

    # Step 1: Rule-based
    category, confidence = classify_rule_based(combined_text)

    if confidence >= CONFIDENCE_THRESHOLD:
        logger.info(f"✅ Rule-based classification: {category} ({confidence:.2f})")
        return {
            "kategori": category,
            "confidence": confidence,
            "alasan": f"Keyword match score: {confidence:.2f}",
            "method": "rule_based",
        }

    # Step 2: Gemini fallback
    logger.info(f"⚠️  Low confidence ({confidence:.2f}), trying Gemini Flash...")
    gemini_result = classify_with_gemini(combined_text)
    gemini_result["method"] = "gemini_flash"
    return gemini_result


# ─── Standalone Test ─────────────────────────────────────────────────────────


def main():
    """Test classifier with various product types."""
    print("=" * 60)
    print("CLASSIFIER TEST")
    print("=" * 60)

    test_cases = [
        {
            "nama_produk": "Vita-X Suplemen Vitamin C",
            "komposisi": "Vitamin C 500mg, Zinc 10mg, kapsul gelatin",
            "expected": "SUPLEMEN",
        },
        {
            "nama_produk": "Susu Segar Pasteurisasi Ultra",
            "komposisi": "Susu sapi segar, vitamin D, kalsium",
            "expected": "DAIRY",
        },
        {
            "nama_produk": "Sosis Ayam Premium",
            "komposisi": "Daging ayam, tepung tapioka, bumbu",
            "expected": "DAGING_OLAHAN",
        },
        {
            "nama_produk": "Jus Mangga Segar",
            "komposisi": "Buah mangga, gula, air, vitamin C",
            "expected": "BUAH_SAYUR",
        },
    ]

    all_passed = True
    for i, tc in enumerate(test_cases, 1):
        result = classify_product(tc)
        status = "✅" if result["kategori"] == tc["expected"] else "❌"
        if result["kategori"] != tc["expected"]:
            all_passed = False

        print(f"\n  Test {i}: {tc['nama_produk']}")
        print(f"    Expected: {tc['expected']}")
        print(f"    Got:      {result['kategori']} ({result['confidence']:.2f})")
        print(f"    Method:   {result['method']}")
        print(f"    Status:   {status}")

    print(f"\n{'✅ All tests passed!' if all_passed else '❌ Some tests failed!'}")


if __name__ == "__main__":
    main()
