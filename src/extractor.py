"""
BPOM Compliance System — Step 2: Lab Report Extractor

Purpose:
    Extract structured data from user-uploaded lab reports.
    Supports PDF (pdfplumber + pytesseract fallback), DOCX, and raw text.
    Uses regex patterns to parse microbiology and heavy metal test results.

    Handles various input formats:
    - "ALT: 2.5 x 10^6 CFU/g" (colon separator)
    - "Total Plate Count ............ 1.2 x 10^5 CFU/g" (dot separator)
    - "Kadar Timbal (Pb) ............ 0.15 mg/kg" (alias with dots)
    - Multiline key:\n value format

Output format:
    {
        "nama_produk": "...",
        "perusahaan": "...",
        "tanggal_uji": "...",
        "komposisi": "...",
        "klaim": "...",
        "proses": "...",
        "mikroba": {"ALT": 5000.0, "E_coli": "negatif", ...},
        "logam_berat": {"Timbal_Pb": 0.05, ...},
        "cppob": {"sanitasi_fasilitas": true, ...}
    }

Usage:
    python src/extractor.py
"""

import re
import os
import sys
import logging
from pathlib import Path
from typing import Optional, Union

import pdfplumber

# Optional imports — graceful fallback if not installed
try:
    from docx import Document as DocxDocument
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

try:
    import pytesseract
    from pdf2image import convert_from_path
    HAS_OCR = True
except ImportError:
    HAS_OCR = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─── Flexible separator pattern ──────────────────────────────────────────────
# Handles: "ALT: 250000", "ALT ......... 250000", "ALT - 250000", "ALT  250000"
_SEP = r"[\s.:,\-_]+"


# ─── Regex Patterns for Lab Data ─────────────────────────────────────────────

# Microbiology parameters
MIKROBA_PATTERNS = {
    "ALT": [
        # "Total Plate Count ............ 1.2 x 10^5 CFU/g"
        r"(?:ALT|TPC|Angka\s+Lempeng\s+Total|Total\s+Plate\s+Count)" + _SEP + r"([\d.,]+)\s*(?:x\s*10\^?\s*(\d+))?\s*(?:CFU/[gm]l?)?",
        r"(?:ALT|TPC|Angka\s+Lempeng\s+Total|Total\s+Plate\s+Count)" + _SEP + r"(\d[\d.,]*)\s*(?:CFU/[gm]l?)?",
    ],
    "E_coli": [
        r"E[\.\s]*[Cc]oli" + _SEP + r"(negatif|negative|tidak\s+terdeteksi|nd|<\s*[\d.,]+|[\d.,]+)\s*(?:APM|MPN|CFU)?",
        r"E[\.\s]*[Cc]oli\s*[:\-]?\s*(negatif|negative|tidak\s+terdeteksi|nd|<\s*[\d.,]+|[\d.,]+)",
    ],
    "Salmonella": [
        r"Salmonella" + _SEP + r"(negatif|negative|tidak\s+terdeteksi|nd|positif|positive|[\d.,]+)",
        r"Salmonella\s*[:\-]?\s*(negatif|negative|tidak\s+terdeteksi|nd|positif|positive|[\d.,]+)",
    ],
    "Coliform": [
        r"[Cc]oliform" + _SEP + r"(negatif|negative|<\s*[\d.,]+|[\d.,]+)\s*(?:APM|MPN|CFU)?",
    ],
    "Staphylococcus_aureus": [
        r"[Ss]taphylococcus[\s.]*[Aa]ureus" + _SEP + r"(negatif|negative|tidak\s+terdeteksi|nd|<\s*[\d.,]+|[\d.,]+)",
    ],
    "Kapang": [
        # "Kapang dan Khamir ............ 40 CFU/g" → captured as Kapang
        r"[Kk]apang(?:\s+dan\s+[Kk]hamir)?" + _SEP + r"([\d.,]+)\s*(?:CFU/[gm]l?)?",
    ],
    "Khamir": [
        # Standalone "Khamir: 200 CFU/g" (Kapang dan Khamir handled by Kapang pattern)
        r"(?:^|\n)\s*-?\s*[Kk]hamir" + _SEP + r"([\d.,]+)\s*(?:CFU/[gm]l?)?",
    ],
    "Bacillus_cereus": [
        r"[Bb]acillus[\s.]*[Cc]ereus" + _SEP + r"(negatif|negative|<\s*[\d.,]+|[\d.,]+)",
    ],
    "Clostridium_perfringens": [
        r"[Cc]lostridium[\s.]*[Pp]erfringens" + _SEP + r"(negatif|negative|<\s*[\d.,]+|[\d.,]+)",
    ],
    "Listeria": [
        r"[Ll]isteria" + _SEP + r"(negatif|negative|tidak\s+terdeteksi|nd|positif|positive|[\d.,]+)",
    ],
}

# Heavy metal parameters
LOGAM_BERAT_PATTERNS = {
    "Timbal_Pb": [
        # "Kadar Timbal (Pb) ............ 0.15 mg/kg"
        r"(?:[Kk]adar\s+)?(?:[Tt]imbal|Pb)\s*(?:\(Pb\))?" + _SEP + r"([\d.,]+)\s*(?:mg/kg|ppm|mg/l)?",
        r"(?:[Tt]imbal|Pb)\s*(?:\(Pb\))?\s*[:\-]?\s*([\d.,]+)\s*(?:mg/kg|ppm|mg/l)?",
    ],
    "Kadmium_Cd": [
        r"(?:[Kk]adar\s+)?(?:[Kk]admium|Cd)\s*(?:\(Cd\))?" + _SEP + r"([\d.,]+)\s*(?:mg/kg|ppm|mg/l)?",
        r"(?:[Kk]admium|Cd)\s*(?:\(Cd\))?\s*[:\-]?\s*([\d.,]+)\s*(?:mg/kg|ppm|mg/l)?",
    ],
    "Merkuri_Hg": [
        r"(?:[Kk]adar\s+)?(?:[Mm]erkuri|Hg)\s*(?:\(Hg\))?" + _SEP + r"([\d.,]+)\s*(?:mg/kg|ppm|mg/l)?",
        r"(?:[Mm]erkuri|Hg)\s*(?:\(Hg\))?\s*[:\-]?\s*([\d.,]+)\s*(?:mg/kg|ppm|mg/l)?",
    ],
    "Arsen_As": [
        r"(?:[Kk]adar\s+)?(?:[Aa]rsen|As)\s*(?:\(As\))?" + _SEP + r"([\d.,]+)\s*(?:mg/kg|ppm|mg/l)?",
        r"(?:[Aa]rsen|As)\s*(?:\(As\))?\s*[:\-]?\s*([\d.,]+)\s*(?:mg/kg|ppm|mg/l)?",
    ],
    "Timah_Sn": [
        r"(?:[Kk]adar\s+)?(?:[Tt]imah|Sn)\s*(?:\(Sn\))?" + _SEP + r"([\d.,]+)\s*(?:mg/kg|ppm|mg/l)?",
        r"(?:[Tt]imah|Sn)\s*(?:\(Sn\))?\s*[:\-]?\s*([\d.,]+)\s*(?:mg/kg|ppm|mg/l)?",
    ],
}

# Product metadata patterns (applied AFTER text preprocessing)
META_PATTERNS = {
    "nama_produk": r"(?:[Nn]ama\s+[Pp]roduk|[Pp]roduct\s+[Nn]ame)\s*[:\-]?\s*(.+)",
    "perusahaan": r"(?:[Pp]erusahaan|[Cc]ompany|[Pp]rodusen|[Pp]emohon|[Pp]abrik)\s*[:\-]?\s*(.+)",
    "tanggal_uji": r"(?:[Tt]anggal\s+[Pp]engujian|[Tt]anggal\s+[Uu]ji|[Tt]est\s+[Dd]ate|[Tt]anggal\s+[Aa]nalisis)\s*[:\-]?\s*(\d{4}[\-/]\d{2}[\-/]\d{2}|\d{1,2}\s+\w+\s+\d{4}|\d{1,2}[\-/]\d{1,2}[\-/]\d{4})",
    "komposisi": r"(?:[Kk]omposisi|[Cc]omposition|[Bb]ahan)\s*[:\-]?\s*(.+)",
    "klaim": r"(?:[Kk]laim(?:\s+[Pp]roduk)?|[Cc]laim)\s*[:\-]?\s*(.+)",
    "proses": r"(?:[Pp]roses\s+[Pp]roduksi|[Pp]rocess)\s*[:\-]?\s*(.+)",
}


# ─── Text Preprocessing ─────────────────────────────────────────────────────


def _preprocess_text(raw_text: str) -> str:
    """
    Preprocess input text to normalize formats:
    1. Join multiline "Key:\\nValue" into "Key: Value"
    2. Extract section-based content (=== KOMPOSISI ===)
    """
    lines = raw_text.split('\n')
    joined = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()
        # If line ends with ':' and next line has content (not a section header)
        if stripped.endswith(':') and not stripped.startswith('==='):
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and not next_line.startswith('===') and not next_line.endswith(':'):
                    joined.append(f"{stripped} {next_line}")
                    i += 2
                    continue
        joined.append(line)
        i += 1

    return '\n'.join(joined)


def _extract_section(text: str, section_name: str) -> str:
    """Extract content between === SECTION_NAME === and next === or end of text."""
    pattern = rf"===\s*{section_name}\s*===\s*\n([\s\S]*?)(?=\n===|\Z)"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        content = match.group(1).strip()
        # Remove bullet points and clean
        lines = []
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('==='):
                line = re.sub(r'^[-•]\s*', '', line)  # Remove bullet
                lines.append(line)
        return '\n'.join(lines)
    return ""


# ─── Text Extraction Functions ──────────────────────────────────────────────


def extract_from_pdf(pdf_path: str) -> str:
    """
    Extract text from PDF. Uses pdfplumber first (for text-layer PDFs).
    Falls back to pytesseract OCR for scanned PDFs.
    """
    text = ""

    # Try pdfplumber first
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text(x_tolerance=1, y_tolerance=3) or ""
                text += page_text + "\n"
    except Exception as e:
        logger.warning(f"pdfplumber failed for {pdf_path}: {e}")

    # If we got meaningful text, return it
    if len(text.strip()) > 50:
        logger.info(f"📄 Extracted {len(text)} chars from PDF (pdfplumber)")
        return text.strip()

    # Fallback: OCR with pytesseract
    if HAS_OCR:
        logger.info("📷 Falling back to OCR (pytesseract)...")
        try:
            images = convert_from_path(pdf_path)
            ocr_text = ""
            for i, img in enumerate(images):
                page_text = pytesseract.image_to_string(img, lang="ind+eng")
                ocr_text += page_text + "\n"
            if len(ocr_text.strip()) > 50:
                logger.info(f"📷 OCR extracted {len(ocr_text)} chars")
                return ocr_text.strip()
        except Exception as e:
            logger.warning(f"OCR failed: {e}")

    logger.warning(f"⚠️  Could not extract meaningful text from {pdf_path}")
    return text.strip()


def extract_from_docx(docx_path: str) -> str:
    """Extract text from a DOCX file using python-docx."""
    if not HAS_DOCX:
        logger.error("python-docx not installed. Cannot process DOCX files.")
        return ""

    try:
        doc = DocxDocument(docx_path)
        text = "\n".join(para.text for para in doc.paragraphs if para.text.strip())
        logger.info(f"📄 Extracted {len(text)} chars from DOCX")
        return text.strip()
    except Exception as e:
        logger.error(f"Failed to extract DOCX {docx_path}: {e}")
        return ""


def extract_from_text(text: str) -> str:
    """Pass-through for raw text input."""
    return text.strip()


# ─── Lab Data Parsing ────────────────────────────────────────────────────────


def _parse_value(raw: str) -> Union[float, str]:
    """
    Convert raw extracted value to float or string.
    Handles: "2.5 x 10^6" → 2500000.0, "negatif" → "negatif", "< 3" → "< 3"
    """
    raw = raw.strip()

    # Qualitative results
    qualitative = ["negatif", "negative", "neg", "tidak terdeteksi", "nd",
                    "positif", "positive"]
    if raw.lower() in qualitative:
        return raw.lower()

    # "< 3" style
    if raw.startswith("<"):
        return raw

    # Numeric
    try:
        return float(raw.replace(",", "."))
    except ValueError:
        return raw


def _parse_scientific_notation(match: re.Match) -> float:
    """Parse values like '2.5 x 10^6' from regex match groups."""
    base_str = match.group(1).replace(",", ".")
    base = float(base_str)

    if match.lastindex and match.lastindex >= 2 and match.group(2):
        exponent = int(match.group(2))
        return base * (10 ** exponent)

    return base


def parse_lab_data(raw_text: str) -> dict:
    """
    Parse raw text from a lab report into structured data.

    Returns dict with keys:
        nama_produk, perusahaan, tanggal_uji, komposisi, klaim, proses,
        mikroba (dict), logam_berat (dict), cppob (dict)
    """
    result = {
        "nama_produk": "",
        "perusahaan": "",
        "tanggal_uji": "",
        "komposisi": "",
        "klaim": "",
        "proses": "",
        "mikroba": {},
        "logam_berat": {},
        "cppob": {},
    }

    # Preprocess: join multiline key:value pairs
    preprocessed = _preprocess_text(raw_text)
    logger.info(f"  Preprocessed text: {len(preprocessed)} chars")

    # Extract metadata from preprocessed text
    for key, pattern in META_PATTERNS.items():
        match = re.search(pattern, preprocessed, re.IGNORECASE)
        if match:
            result[key] = match.group(1).strip()
            logger.info(f"  Found {key}: {result[key][:50]}...")

    # Extract section-based content (overrides regex if found)
    section_komposisi = _extract_section(raw_text, "KOMPOSISI")
    if section_komposisi:
        result["komposisi"] = section_komposisi
        logger.info(f"  Found komposisi (section): {section_komposisi[:50]}...")

    section_klaim = _extract_section(raw_text, "KLAIM(?:\\s+PRODUK)?")
    if section_klaim:
        result["klaim"] = section_klaim
        logger.info(f"  Found klaim (section): {section_klaim[:50]}...")

    # Extract microbiology parameters (search in original text too for flexibility)
    search_text = raw_text + "\n" + preprocessed
    for param_name, patterns in MIKROBA_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, search_text, re.IGNORECASE)
            if match:
                # Handle scientific notation for ALT
                if param_name == "ALT" and match.lastindex and match.lastindex >= 2 and match.group(2):
                    value = _parse_scientific_notation(match)
                else:
                    value = _parse_value(match.group(1))
                result["mikroba"][param_name] = value
                logger.info(f"  Found mikroba/{param_name}: {value}")
                break

    # Special: if "Kapang dan Khamir" was found as combined, also set Khamir to same value
    if "Kapang" in result["mikroba"] and "Khamir" not in result["mikroba"]:
        # Check if original text had "Kapang dan Khamir" (combined)
        if re.search(r"[Kk]apang\s+dan\s+[Kk]hamir", raw_text):
            result["mikroba"]["Khamir"] = result["mikroba"]["Kapang"]
            logger.info(f"  Set Khamir = Kapang (combined value): {result['mikroba']['Khamir']}")

    # Extract heavy metal parameters
    for param_name, patterns in LOGAM_BERAT_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, search_text, re.IGNORECASE)
            if match:
                value = _parse_value(match.group(1))
                result["logam_berat"][param_name] = value
                logger.info(f"  Found logam_berat/{param_name}: {value}")
                break

    # Extract CPPOB Checklist parameters from raw text
    cppob_keywords = {
        "sanitasi_fasilitas": [r"sanitasi", r"fasilitas memenuhi standar sanitasi"],
        "hygiene_personel": [r"hygiene", r"higiene", r"personel terjaga"],
        "storage_suhu": [r"suhu", r"penyimpanan pada suhu"],
        "air_bersih": [r"air bersih", r"sumber air"],
        "pest_control": [r"hama", r"pengendalian hama"],
        "transport_higienis": [r"transportasi", r"syarat higiene"]
    }
    for item_id, regexes in cppob_keywords.items():
        for regex in regexes:
            match = re.search(rf"{regex}" + r"[\s.:,\-_]+" + r"(ya|yes|memenuhi|ok|true|aman|baik|sesuai|tidak|no|gagal|tidak memenuhi)", raw_text, re.IGNORECASE)
            if match:
                status_str = match.group(1).lower()
                is_ok = status_str in ("ya", "yes", "memenuhi", "ok", "true", "aman", "baik", "sesuai")
                result["cppob"][item_id] = is_ok
                logger.info(f"  Found CPPOB/{item_id}: {is_ok}")
                break

    return result


# ─── Public API ──────────────────────────────────────────────────────────────


def extract_and_parse(file_path: Optional[str] = None,
                      raw_text: Optional[str] = None) -> dict:
    """
    Main extraction function. Accepts either a file path or raw text.
    Auto-detects file type from extension.
    """
    if raw_text:
        logger.info("📝 Processing raw text input")
        text = extract_from_text(raw_text)
    elif file_path:
        ext = Path(file_path).suffix.lower()
        if ext == ".pdf":
            text = extract_from_pdf(file_path)
        elif ext in (".docx", ".doc"):
            text = extract_from_docx(file_path)
        elif ext == ".txt":
            text = Path(file_path).read_text(encoding="utf-8", errors="ignore")
        else:
            logger.error(f"Unsupported file type: {ext}")
            return {}
    else:
        logger.error("No input provided (file_path or raw_text)")
        return {}

    if not text:
        logger.error("No text extracted from input")
        return {}

    logger.info(f"📊 Parsing lab data from {len(text)} chars...")
    return parse_lab_data(text)


# ─── Standalone Test ─────────────────────────────────────────────────────────


def main():
    """Test extractor with BOTH sample formats."""
    print("=" * 60)
    print("EXTRACTOR TEST — Sample Lab Report")
    print("=" * 60)

    # Test 1: Original plan format (colon separator)
    sample_text_1 = """
Nama Produk: Vita-X Suplemen Vitamin C
Perusahaan: PT Maju Sehat Indonesia
Tanggal Uji: 2024-03-15
Komposisi: Vitamin C 500mg, Zinc 10mg, Excipient

Hasil Uji Mikrobiologi:
- ALT: 2.5 x 10^6 CFU/g
- E.coli: negatif
- Salmonella: negatif
- Kapang: 500 CFU/g
- Khamir: 200 CFU/g

Hasil Uji Logam Berat:
- Timbal (Pb): 3.5 mg/kg
- Kadmium (Cd): 0.8 mg/kg
"""

    print("\n--- Test 1: Colon format ---")
    result1 = extract_and_parse(raw_text=sample_text_1)

    assert result1["nama_produk"] == "Vita-X Suplemen Vitamin C", f"nama_produk: {result1['nama_produk']}"
    assert result1["mikroba"].get("ALT") == 2500000.0, f"ALT: {result1['mikroba'].get('ALT')}"
    assert result1["mikroba"].get("E_coli") == "negatif", f"E_coli: {result1['mikroba'].get('E_coli')}"
    assert result1["logam_berat"].get("Timbal_Pb") == 3.5, f"Timbal_Pb: {result1['logam_berat'].get('Timbal_Pb')}"
    print("  ✅ Test 1 passed (colon format)")

    # Test 2: User's actual format (dot separator + multiline)
    sample_text_2 = """
=== INFORMASI PRODUK ===

Nama Produk:
VitaBoost Max

Produsen:
PT NutriWell Indonesia

=== KOMPOSISI ===

Vitamin C .................... 1000 mg
Ginseng Extract .............. 250 mg

=== HASIL UJI LABORATORIUM ===

Total Plate Count ............ 1.2 x 10^5 CFU/g
Kapang dan Khamir ............ 40 CFU/g
Kadar Timbal (Pb) ............ 0.15 mg/kg

Tanggal Pengujian:
12 Mei 2026

=== KLAIM PRODUK ===

- Membantu meningkatkan daya tahan tubuh
- Menyembuhkan diabetes secara alami
"""

    print("\n--- Test 2: Dot separator + multiline ---")
    result2 = extract_and_parse(raw_text=sample_text_2)

    print(f"\n📋 Extracted Data (Test 2):")
    for key, value in result2.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    {k}: {v}")
        else:
            val_preview = str(value)[:60]
            print(f"  {key}: {val_preview}")

    # Validate
    print("\n✅ Validation (Test 2):")
    assert result2["nama_produk"] == "VitaBoost Max", f"nama_produk: {result2['nama_produk']}"
    print(f"  ✅ nama_produk: {result2['nama_produk']}")

    assert result2["perusahaan"] == "PT NutriWell Indonesia", f"perusahaan: {result2['perusahaan']}"
    print(f"  ✅ perusahaan: {result2['perusahaan']}")

    assert result2["tanggal_uji"] == "12 Mei 2026", f"tanggal_uji: {result2['tanggal_uji']}"
    print(f"  ✅ tanggal_uji: {result2['tanggal_uji']}")

    alt_val = result2["mikroba"].get("ALT")
    assert alt_val == 120000.0, f"ALT should be 120000.0 (1.2 x 10^5), got {alt_val}"
    print(f"  ✅ ALT = {alt_val} (1.2 x 10^5)")

    kapang = result2["mikroba"].get("Kapang")
    assert kapang == 40.0, f"Kapang should be 40.0, got {kapang}"
    print(f"  ✅ Kapang = {kapang}")

    khamir = result2["mikroba"].get("Khamir")
    assert khamir == 40.0, f"Khamir should be 40.0 (from Kapang dan Khamir), got {khamir}"
    print(f"  ✅ Khamir = {khamir} (from 'Kapang dan Khamir')")

    pb = result2["logam_berat"].get("Timbal_Pb")
    assert pb == 0.15, f"Timbal_Pb should be 0.15, got {pb}"
    print(f"  ✅ Timbal_Pb = {pb}")

    assert "komposisi" in result2 and result2["komposisi"], f"komposisi missing"
    print(f"  ✅ komposisi extracted")

    assert "klaim" in result2 and result2["klaim"], f"klaim missing"
    print(f"  ✅ klaim extracted")

    print("\n✅ All extractor tests passed!")


if __name__ == "__main__":
    main()
