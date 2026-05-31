"""
BPOM Compliance System — Step 4: Rule Engine (CORE)

Purpose:
    DETERMINISTIC compliance checking — the heart of the system.
    Compares lab results against BPOM regulation thresholds from JSON rule files.
    
    STRICT RULES:
    - NEVER uses LLM. Only Python logic + JSON rules.
    - Returns PASS / FAIL / MISSING for every parameter.
    - Pasal hukum WAJIB in every result.
    - Zero probabilistic reasoning.

Usage:
    python src/rule_engine.py
"""

import json
import logging
from pathlib import Path
from typing import Union

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─── Rule Loading ────────────────────────────────────────────────────────────

RULES_DIR = Path(__file__).parent.parent / "rules"


def load_rules(rule_file: str) -> dict:
    """Load rules from JSON file. Raises FileNotFoundError if missing."""
    path = RULES_DIR / rule_file
    if not path.exists():
        raise FileNotFoundError(f"Rule file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


# ─── Single Parameter Check ─────────────────────────────────────────────────


def check_single_param(param: str, value: Union[float, str], rule: dict,
                        regulation: str = "") -> dict:
    """
    DETERMINISTIC check of one parameter against its rule.
    ZERO LLM involvement.
    
    Returns dict with:
        param, status (PASS|FAIL|MISSING), found, threshold_max,
        unit, pasal, regulation, message
    """
    base_result = {
        "param": param,
        "unit": rule.get("unit", ""),
        "pasal": rule.get("pasal", ""),
        "regulation": regulation,
    }

    # ── Negatif/required check ───────────────────────────────────────────
    if rule.get("required") == "negatif":
        val_str = str(value).lower().strip()
        negatif_values = [
            "negatif", "negative", "neg", "tidak terdeteksi", "nd",
            "< 3", "<3", "tidak ada", "nil", "0", "0.0",
        ]
        is_negatif = val_str in negatif_values

        return {
            **base_result,
            "status": "PASS" if is_negatif else "FAIL",
            "found": value,
            "required": "negatif",
            "message": (
                f"{param} = negatif ✅ (sesuai {rule['pasal']})"
                if is_negatif else
                f"{param} HARUS negatif, ditemukan: {value} ❌ (berdasarkan {rule['pasal']})"
            ),
        }

    # ── Check if qualitative "negatif" was provided for a numeric parameter ──
    val_str = str(value).lower().strip()
    negatif_values = [
        "negatif", "negative", "neg", "tidak terdeteksi", "nd",
        "tidak ada", "nil", "0", "0.0",
    ]
    if val_str in negatif_values:
        max_val = rule.get("max")
        return {
            **base_result,
            "status": "PASS",
            "found": value,
            "threshold_max": max_val,
            "message": (
                f"{param} = {value} ✅ (memenuhi batas maksimum {max_val} {rule.get('unit', '')}, {rule['pasal']})"
            ),
        }

    # ── Numeric threshold check ──────────────────────────────────────────
    try:
        num_val = float(str(value).replace(",", ".").replace("<", "").strip())
    except (ValueError, TypeError):
        return {
            **base_result,
            "status": "MISSING",
            "found": value,
            "message": f"{param}: tidak dapat diparse sebagai angka (value={value})",
        }

    max_val = rule.get("max")
    min_val = rule.get("min")

    if max_val is not None and num_val > max_val:
        return {
            **base_result,
            "status": "FAIL",
            "found": num_val,
            "threshold_max": max_val,
            "message": (
                f"{param} = {num_val} {rule.get('unit', '')} "
                f"MELEBIHI batas maksimum {max_val} {rule.get('unit', '')} "
                f"❌ (berdasarkan {rule['pasal']})"
            ),
        }

    if min_val is not None and num_val < min_val:
        return {
            **base_result,
            "status": "FAIL",
            "found": num_val,
            "threshold_min": min_val,
            "message": (
                f"{param} = {num_val} {rule.get('unit', '')} "
                f"DI BAWAH batas minimum {min_val} {rule.get('unit', '')} "
                f"❌ (berdasarkan {rule['pasal']})"
            ),
        }

    return {
        **base_result,
        "status": "PASS",
        "found": num_val,
        "threshold_max": max_val,
        "message": (
            f"{param} = {num_val} {rule.get('unit', '')} "
            f"✅ dalam batas ({max_val} {rule.get('unit', '')} max, {rule['pasal']})"
        ),
    }


# ─── CPPOB Checklist Check ──────────────────────────────────────────────────


def check_cppob(cppob_data: dict) -> list[dict]:
    """
    Check CPPOB (Good Manufacturing Practice) checklist items.
    Returns list of results for each checklist item.
    """
    try:
        cppob_rules = load_rules("cppob_rules.json")
    except FileNotFoundError:
        logger.warning("⚠️  cppob_rules.json not found, skipping CPPOB check")
        return []

    results = []
    checklist = cppob_rules.get("checklist", [])
    regulation = cppob_rules.get("regulation", "")

    for item in checklist:
        item_id = item["id"]
        item_label = item["label"]
        pasal = item["pasal"]

        # Check if user provided this item
        user_value = cppob_data.get(item_id)

        if user_value is None:
            results.append({
                "param": f"CPPOB: {item_label}",
                "status": "MISSING",
                "found": "Tidak tersedia",
                "pasal": pasal,
                "regulation": regulation,
                "message": f"CPPOB/{item_id}: data tidak tersedia ⚠️ ({pasal})",
            })
        elif user_value in (True, "true", "ya", "yes", 1, "1", "memenuhi"):
            results.append({
                "param": f"CPPOB: {item_label}",
                "status": "PASS",
                "found": "Memenuhi",
                "pasal": pasal,
                "regulation": regulation,
                "message": f"CPPOB/{item_id}: memenuhi ✅ ({pasal})",
            })
        else:
            results.append({
                "param": f"CPPOB: {item_label}",
                "status": "FAIL",
                "found": "Tidak memenuhi",
                "pasal": pasal,
                "regulation": regulation,
                "message": f"CPPOB/{item_id}: TIDAK memenuhi ❌ ({pasal})",
            })

    return results


# ─── Full Compliance Check ───────────────────────────────────────────────────


def run_full_compliance_check(extracted_data: dict, category: str) -> dict:
    """
    Run ALL compliance checks (microba + logam berat + CPPOB).
    
    DETERMINISTIC — no LLM, no probability, no hallucination.
    
    Args:
        extracted_data: dict from extractor with mikroba, logam_berat, cppob keys
        category: product category (SUPLEMEN|DAIRY|DAGING_OLAHAN|BUAH_SAYUR)
    
    Returns:
        {
            "overall_status": "PASS" | "FAIL",
            "violations": [...],
            "passed": [...],
            "missing": [...],
            "total_checks": int,
            "violation_count": int,
            "summary": str,
        }
    """
    logger.info(f"🔍 Running compliance check for category: {category}")

    violations: list[dict] = []
    passed: list[dict] = []
    missing: list[dict] = []

    # ── 1. Microba Check ─────────────────────────────────────────────────
    try:
        microba_rules_data = load_rules("microba_rules.json")
        microba_regulation = microba_rules_data.get("regulation", "")
        microba_rules = microba_rules_data.get("categories", {}).get(category, {})
    except FileNotFoundError:
        logger.error("microba_rules.json not found!")
        microba_rules = {}
        microba_regulation = ""

    for param, value in extracted_data.get("mikroba", {}).items():
        if param in microba_rules:
            result = check_single_param(
                param, value, microba_rules[param], microba_regulation
            )
            if result["status"] == "FAIL":
                violations.append(result)
            elif result["status"] == "MISSING":
                missing.append(result)
            else:
                passed.append(result)
            logger.info(f"  Mikroba/{param}: {result['status']}")
        else:
            logger.info(f"  Mikroba/{param}: no rule for category {category}, skipped")

    # ── 2. Logam Berat Check ─────────────────────────────────────────────
    try:
        logam_rules_data = load_rules("logam_berat_rules.json")
        logam_regulation = logam_rules_data.get("regulation", "")
        logam_rules = logam_rules_data.get("categories", {}).get(category, {})
    except FileNotFoundError:
        logger.error("logam_berat_rules.json not found!")
        logam_rules = {}
        logam_regulation = ""

    for param, value in extracted_data.get("logam_berat", {}).items():
        if param in logam_rules:
            result = check_single_param(
                param, value, logam_rules[param], logam_regulation
            )
            if result["status"] == "FAIL":
                violations.append(result)
            elif result["status"] == "MISSING":
                missing.append(result)
            else:
                passed.append(result)
            logger.info(f"  Logam/{param}: {result['status']}")
        else:
            logger.info(f"  Logam/{param}: no rule for category {category}, skipped")

    # ── 3. CPPOB Check ───────────────────────────────────────────────────
    cppob_results = check_cppob(extracted_data.get("cppob", {}))
    for result in cppob_results:
        if result["status"] == "FAIL":
            violations.append(result)
        elif result["status"] == "MISSING":
            missing.append(result)
        else:
            passed.append(result)

    # ── Determine Overall Status ─────────────────────────────────────────
    overall = "PASS" if not violations else "FAIL"
    total_checks = len(violations) + len(passed) + len(missing)

    summary = (
        f"Kategori {category}: {total_checks} parameter diperiksa, "
        f"{len(passed)} PASS, {len(violations)} FAIL, {len(missing)} MISSING. "
        f"Status keseluruhan: {overall}"
    )

    logger.info(f"\n{'=' * 50}")
    logger.info(f"📊 SUMMARY: {summary}")
    logger.info(f"{'=' * 50}")

    return {
        "overall_status": overall,
        "violations": violations,
        "passed": passed,
        "missing": missing,
        "total_checks": total_checks,
        "violation_count": len(violations),
        "summary": summary,
    }


# ─── Standalone Test ─────────────────────────────────────────────────────────


def main():
    """Test rule engine with sample data from PLAN.md."""
    print("=" * 60)
    print("RULE ENGINE TEST — Sample Data (SUPLEMEN)")
    print("=" * 60)

    # Sample data from PLAN.md
    sample_data = {
        "nama_produk": "Vita-X Suplemen Vitamin C",
        "perusahaan": "PT Maju Sehat Indonesia",
        "tanggal_uji": "2024-03-15",
        "mikroba": {
            "ALT": 2500000.0,      # 2.5 x 10^6 → FAIL (max 10^5)
            "E_coli": "negatif",   # PASS
            "Salmonella": "negatif",  # PASS
            "Kapang": 500.0,       # PASS (max 10^3)
            "Khamir": 200.0,       # PASS (max 10^3)
        },
        "logam_berat": {
            "Timbal_Pb": 3.5,      # FAIL (max 2.0 mg/kg)
            "Kadmium_Cd": 0.8,     # PASS (max 1.0 mg/kg)
        },
        "cppob": {},
    }

    result = run_full_compliance_check(sample_data, "SUPLEMEN")

    print(f"\n📊 Overall Status: {result['overall_status']}")
    print(f"   Total Checks: {result['total_checks']}")
    print(f"   Violations: {result['violation_count']}")

    print("\n❌ VIOLATIONS:")
    for v in result["violations"]:
        print(f"   {v['param']}: {v['message']}")

    print("\n✅ PASSED:")
    for p in result["passed"]:
        print(f"   {p['param']}: {p['message']}")

    if result["missing"]:
        print("\n⚠️  MISSING:")
        for m in result["missing"]:
            print(f"   {m['param']}: {m['message']}")

    # Validate expected results
    print("\n🧪 Validation:")
    assert result["overall_status"] == "FAIL", "Should be FAIL"
    print("  ✅ Overall status = FAIL")

    assert result["violation_count"] == 2, f"Expected 2 violations, got {result['violation_count']}"
    print("  ✅ Exactly 2 violations found")

    violation_params = [v["param"] for v in result["violations"]]
    assert "ALT" in violation_params, "ALT should be in violations"
    print("  ✅ ALT violation detected (2.5M > 100K CFU/g)")

    assert "Timbal_Pb" in violation_params, "Timbal_Pb should be in violations"
    print("  ✅ Timbal_Pb violation detected (3.5 > 2.0 mg/kg)")

    # Verify pasal is included in every violation
    for v in result["violations"]:
        assert v.get("pasal"), f"Missing pasal in violation: {v['param']}"
    print("  ✅ Pasal included in every violation")

    print("\n✅ All rule engine tests passed!")


if __name__ == "__main__":
    main()
