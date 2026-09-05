#!/usr/bin/env python3
"""Record local portable and ArcGIS readiness for optical pixel Stage 3."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "records/readiness/m2-optical-pixel-implementation-readiness.json"
FILES = {
    "approval_sha256": ROOT / "records/source-gates/m2-materialization-pixel-readiness-approval.json",
    "header_publication_gate_sha256": ROOT / "records/readiness/m2-header-stage-publication-gate.json",
    "header_final_preflight_sha256": ROOT / "records/readiness/m2-header-stage-final-preflight.json",
    "radar_header_receipt_sha256": ROOT / "records/readiness/radar-input/m2-s1-input-readiness-real-003.json",
    "optical_header_receipt_sha256": ROOT / "records/readiness/optical-input/m2-s2-input-readiness-real-001.json",
    "header_reconciliation_sha256": ROOT / "records/readiness/m2-full-header-readiness-reconciliation.json",
    "contract_sha256": ROOT / "config/qa/optical-pixel-readiness-contract-001.json",
    "core_sha256": ROOT / "scripts/optical_pixel_readiness_core_001.py",
    "runner_sha256": ROOT / "scripts/run_m2_optical_pixel_readiness_001.py",
    "stage_gate_sha256": ROOT / "scripts/m2_optical_pixel_stage_gate.py",
    "final_preflight_sha256": ROOT / "scripts/preflight_m2_optical_pixel_readiness.py",
    "publication_gate_recorder_sha256": ROOT / "scripts/record_m2_optical_pixel_publication_gate.py",
    "arcgis_adapter_sha256": ROOT / "scripts/validate_optical_pixel_readiness_arcgis_001.py",
    "arcgis_synthetic_receipt_sha256": ROOT / "records/surface-receipts/optical-pixel-readiness-synthetic-arcgis-001.json",
    "portable_tests_sha256": ROOT / "tests/test_m2_optical_pixel_readiness.py",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verified-at-utc", required=True)
    parser.add_argument("--focused-test-count", required=True, type=int)
    parser.add_argument("--full-test-count", required=True, type=int)
    args = parser.parse_args()
    if OUTPUT.exists():
        raise SystemExit("refusing optical pixel readiness collision")
    if args.focused_test_count < 10 or args.full_test_count < args.focused_test_count:
        raise SystemExit("test counts do not satisfy optical pixel readiness")
    missing = [str(path.relative_to(ROOT)) for path in FILES.values() if not path.is_file()]
    if missing:
        raise SystemExit("missing optical pixel implementation evidence: " + ", ".join(missing))
    synthetic = json.loads(FILES["arcgis_synthetic_receipt_sha256"].read_text(encoding="utf-8"))
    if synthetic.get("status") != "pass_synthetic_arcgis_with_expected_shift_block":
        raise SystemExit("ArcGIS optical pixel synthetic evidence is not passing")
    record = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-OPTICAL-PIXEL-IMPLEMENTATION-READINESS-002",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_local_and_arcgis_synthetic_ready_public_ci_pending",
        "bindings": {key: sha256(path) for key, path in FILES.items()},
        "tests": {"focused_test_count": args.focused_test_count, "full_repository_test_count": args.full_test_count, "portable_result": "pass", "arcgis_result": "pass", "intentional_two_pixel_shift": "block"},
        "assertions": {"exact_pair_frozen": True, "three_approved_aois_frozen": True, "thresholds_frozen_before_real_pixels": True, "external_custody_accessed_by_synthetic_tests": False, "real_product_pixels_examined": False, "real_attempt_started": False, "radar_pixel_access_released": False, "baseline_or_change_released": False},
        "next_gate": "publish this exact implementation and require successful public CI before the final no-pixel preflight",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": record["status"], "output": OUTPUT.relative_to(ROOT).as_posix()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
