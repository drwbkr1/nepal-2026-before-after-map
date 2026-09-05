#!/usr/bin/env python3
"""Record exact recovery implementation readiness before public CI."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from optical_pixel_recovery_core_001 import validate_recovery_contract


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "records/readiness/m2-optical-pixel-recovery-001-implementation-readiness.json"
CONTRACT_REF = "config/qa/optical-pixel-readiness-contract-recovery-001.json"
ORIGINAL_REF = "config/qa/optical-pixel-readiness-contract-001.json"
ACTIVATION_REF = "records/readiness/m2-optical-pixel-recovery-001-activation.json"


def load(relative: str) -> dict:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {relative}")
    return value


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verified-at-utc", required=True)
    parser.add_argument("--portable-test-count", required=True, type=int)
    parser.add_argument("--arcgis-receipt", required=True)
    args = parser.parse_args()
    if OUTPUT.exists():
        raise SystemExit("refusing optical pixel recovery readiness collision")
    contract = load(CONTRACT_REF)
    original = load(ORIGINAL_REF)
    activation = load(ACTIVATION_REF)
    arcgis = load(args.arcgis_receipt)
    errors = validate_recovery_contract(contract, original)
    if errors:
        raise SystemExit("invalid recovery contract: " + "; ".join(errors))
    if activation.get("status") != "pass_exact_approval_activated_implementation_and_publication_only":
        raise SystemExit("recovery activation differs")
    if args.portable_test_count != 10:
        raise SystemExit("focused portable test count differs")
    if (
        arcgis.get("status") != "pass_exact_nested_production_shape_arcgis_synthetic"
        or arcgis.get("assertions", {}).get("exact_production_object_shape_used") is not True
        or arcgis.get("assertions", {}).get("nested_extent_normalized") is not True
        or arcgis.get("assertions", {}).get("real_product_pixels_examined") is not False
        or arcgis.get("assertions", {}).get("scientific_thresholds_changed") is not False
    ):
        raise SystemExit("ArcGIS recovery synthetic receipt differs")
    record = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-OPTICAL-PIXEL-RECOVERY-001-IMPLEMENTATION-READINESS",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_exact_shape_local_and_arcgis_synthetic_ready_public_ci_pending",
        "bindings": {
            "activation_ref": ACTIVATION_REF,
            "activation_sha256": sha256(ACTIVATION_REF),
            "contract_ref": CONTRACT_REF,
            "contract_sha256": sha256(CONTRACT_REF),
            "source_scientific_contract_ref": ORIGINAL_REF,
            "source_scientific_contract_sha256": sha256(ORIGINAL_REF),
            "arcgis_receipt_ref": args.arcgis_receipt,
            "arcgis_receipt_sha256": sha256(args.arcgis_receipt),
        },
        "implementation": contract["implementation"],
        "validation": {
            "focused_portable_test_count": args.portable_test_count,
            "focused_portable_test_status": "pass",
            "arcgis_synthetic_status": "pass",
            "exact_nested_production_shape_covered": True,
            "conflicting_flat_bound_rejected": True,
        },
        "assertions": {
            "only_operational_grid_normalization_changed": True,
            "scientific_contract_sections_unchanged": True,
            "real_001_preserved": True,
            "real_001_reused_or_retried": False,
            "recovery_attempt_started": False,
            "real_product_pixels_examined": False,
            "thresholds_sources_or_aois_changed": False,
        },
        "next_gate": "publish the exact implementation and require fresh successful public CI before the no-pixel preflight",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"status": record["status"], "output": OUTPUT.relative_to(ROOT).as_posix()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
