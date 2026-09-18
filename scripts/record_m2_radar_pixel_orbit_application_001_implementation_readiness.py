#!/usr/bin/env python3
"""Seal the approved six-source radar implementation before public CI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from m2_radar_pixel_orbit_application_001_core import sha256_file, write_new_json


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "records/readiness/m2-radar-pixel-orbit-application-001-implementation-readiness.json"
ARTIFACTS = [
    "records/source-gates/m2-radar-pixel-orbit-application-001-review-reconciliation.json",
    "records/source-gates/m2-radar-pixel-orbit-application-001-approval.json",
    "records/readiness/m2-radar-pixel-orbit-application-001-approval-activation.json",
    "config/qa/m2-radar-pixel-orbit-application-001-contract.json",
    "scripts/activate_m2_radar_pixel_orbit_application_001.py",
    "scripts/m2_radar_pixel_orbit_application_001_core.py",
    "scripts/run_m2_radar_pixel_orbit_application_001.py",
    "scripts/validate_m2_radar_pixel_orbit_application_001_arcgis.py",
    "scripts/derive_m2_acquisition_checkpoint.py",
    "scripts/record_m2_radar_pixel_orbit_application_001_implementation_readiness.py",
    "tests/test_m2_radar_pixel_orbit_application_001.py",
    "tests/test_m2_radar_pixel_orbit_application_001_review.py",
    "records/readiness/m2-radar-pixel-orbit-application-001-synthetic-attempt-001-failure.json",
    "records/surface-receipts/m2-radar-pixel-orbit-application-001-synthetic.json",
    "records/surface-receipts/m2-radar-pixel-orbit-application-001-synthetic-002.json",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recorded-at-utc", required=True)
    parser.add_argument("--focused-test-count", type=int, required=True)
    parser.add_argument("--arcgis-runtime-test-count", type=int, required=True)
    parser.add_argument("--full-test-count", type=int, required=True)
    parser.add_argument("--full-skip-count", type=int, required=True)
    parser.add_argument("--required-file-count", type=int, required=True)
    args = parser.parse_args()
    if OUTPUT.exists():
        raise SystemExit("radar implementation-readiness output collision")
    if not args.recorded_at_utc.endswith("Z"):
        raise SystemExit("--recorded-at-utc must be UTC")
    record = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-001-IMPLEMENTATION-READINESS",
        "recorded_at_utc": args.recorded_at_utc,
        "status": "pass_exact_six_source_implementation_public_ci_pending",
        "bindings": {ref: sha256_file(ROOT / ref) for ref in ARTIFACTS},
        "implementation": {
            "source_order": [f"M1-SRC-{index:03d}" for index in range(1, 7)],
            "route_order": ["PAIR-S1-ASC-R085-IW", "PAIR-S1-DESC-R121-IW"],
            "attempt_id": "radar-pixel-orbit-application-001-real-001",
            "explicit_orbit_file_application": True,
            "exact_ellipsoidal_dem_mosaic": True,
            "common_output_wkid": 32645,
            "common_output_cell_size_m": 10.0,
            "windowed_registration": True,
            "windowed_seam_sampling": True,
            "source_started_receipt_before_content_copy": True,
            "attempt_started_receipt_before_identity_read": True,
            "stop_on_first_source_execution_failure": True,
            "automatic_retry_authorized": False,
        },
        "validation": {
            "focused_test_count": args.focused_test_count,
            "arcgis_runtime_test_count": args.arcgis_runtime_test_count,
            "arcgis_runtime_test_failures": 0,
            "full_repository_test_count": args.full_test_count,
            "full_repository_intentional_skip_count": args.full_skip_count,
            "repository_checker_status": f"pass_{args.required_file_count}_required_files",
            "installed_arcgis_sar_signatures_checked": True,
            "production_runner_argument_order_checked": True,
            "synthetic_mask_registration_seam_and_dem_mosaic_checked": True,
            "fixed_order_and_stop_on_failure_checked": True,
            "publication_gate_fail_closed_checked": True,
            "network_library_absence_checked": True,
        },
        "released_now": {
            "public_ci": True,
            "final_no_content_preflight": False,
            "project_data_content_read": False,
            "orbit_application": False,
            "radar_pixel_processing": False,
            "route_evaluation": False,
        },
        "assertions": {
            "project_data_content_read": False,
            "external_custody_accessed_by_implementation_tests": False,
            "external_custody_mutated": False,
            "network_request_performed": False,
            "credential_value_read": False,
            "real_processing_attempt_created": False,
            "orbit_application_executed": False,
            "radar_pixel_processing_executed": False,
            "baseline_admission_authorized": False,
            "change_analysis_executed": False,
            "interpretation_or_attribution_executed": False,
            "derived_pixel_publication_authorized": False,
            "scientific_result_established": False,
        },
        "next_action": "Commit and publish the exact implementation, then require successful public default-branch CI before the final no-content preflight.",
    }
    write_new_json(OUTPUT, record)
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
