#!/usr/bin/env python3
"""Record local portable and ArcGIS synthetic readiness for header Stage 2."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "records/readiness/m2-header-stage-implementation-readiness.json"
FILES = {
    "approval_sha256": ROOT / "records/source-gates/m2-materialization-pixel-readiness-approval.json",
    "materialization_reconciliation_sha256": ROOT / "records/acquisition/sentinel-materialization-reconciliation-002.json",
    "radar_contract_sha256": ROOT / "config/qa/radar-input-readiness-contract-full-cohort-001.json",
    "radar_core_sha256": ROOT / "scripts/radar_input_readiness_core_full_cohort_001.py",
    "radar_runner_sha256": ROOT / "scripts/inspect_radar_inputs_arcgis_full_cohort_001.py",
    "radar_adapter_sha256": ROOT / "scripts/validate_radar_input_readiness_arcgis_full_cohort_001.py",
    "radar_synthetic_receipt_sha256": ROOT / "records/surface-receipts/radar-input-readiness-synthetic-full-cohort-001.json",
    "optical_contract_sha256": ROOT / "config/qa/optical-input-readiness-contract-full-cohort-001.json",
    "optical_core_sha256": ROOT / "scripts/optical_input_readiness_core_full_cohort_001.py",
    "optical_runner_sha256": ROOT / "scripts/inspect_optical_inputs_arcgis_full_cohort_001.py",
    "optical_adapter_sha256": ROOT / "scripts/validate_optical_input_readiness_arcgis_full_cohort_001.py",
    "optical_synthetic_receipt_sha256": ROOT / "records/surface-receipts/optical-input-readiness-synthetic-full-cohort-001.json",
    "stage_gate_sha256": ROOT / "scripts/m2_header_stage_gate.py",
    "final_preflight_sha256": ROOT / "scripts/preflight_m2_full_header_readiness.py",
    "publication_gate_recorder_sha256": ROOT / "scripts/record_m2_header_stage_publication_gate.py",
    "focused_tests_sha256": ROOT / "tests/test_m2_full_header_readiness.py",
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
        raise SystemExit("refusing implementation-readiness output collision")
    if args.focused_test_count < 10 or args.full_test_count < args.focused_test_count:
        raise SystemExit("test counts do not satisfy header readiness")
    missing = [str(path.relative_to(ROOT)) for path in FILES.values() if not path.is_file()]
    if missing:
        raise SystemExit("missing header implementation evidence: " + ", ".join(missing))
    radar = json.loads(FILES["radar_synthetic_receipt_sha256"].read_text(encoding="utf-8"))
    optical = json.loads(FILES["optical_synthetic_receipt_sha256"].read_text(encoding="utf-8"))
    if not str(radar.get("status", "")).startswith("pass_") or not str(optical.get("status", "")).startswith("pass_"):
        raise SystemExit("ArcGIS synthetic header evidence is not passing")
    record = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-FULL-HEADER-STAGE-IMPLEMENTATION-READINESS-001",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_local_and_arcgis_synthetic_ready_public_ci_pending",
        "bindings": {key: sha256(path) for key, path in FILES.items()},
        "tests": {"focused_test_count": args.focused_test_count, "full_repository_test_count": args.full_test_count, "portable_result": "pass", "arcgis_radar_result": "pass", "arcgis_optical_result": "pass", "intentional_block_cases": "pass", "no_replacement_cases": "pass"},
        "assertions": {"external_custody_accessed_by_synthetic_tests": False, "real_materialization_receipts_used_by_synthetic_tests": False, "real_raster_headers_opened": False, "real_product_pixels_examined": False, "network_requests_performed": False, "real_header_attempt_started": False},
        "next_gate": "publish this exact header implementation and require successful public CI before the final no-header preflight",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": record["status"], "output": str(OUTPUT.relative_to(ROOT)).replace("\\", "/")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
