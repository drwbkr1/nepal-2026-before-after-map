#!/usr/bin/env python3
"""Seal the tested receipt-persistence recovery-002 implementation before public CI."""

from __future__ import annotations

import argparse
import json

from m2_dem_vertical_datum_proj25_core import ROOT, sha256_file, write_new_json


OUTPUT = ROOT / "records/readiness/m2-dem-proj25-receipt-persistence-recovery-002-implementation-readiness.json"
ARTIFACTS = [
    "records/source-gates/m2-dem-proj25-receipt-persistence-recovery-002-review-reconciliation.json",
    "records/source-gates/m2-dem-proj25-receipt-persistence-recovery-002-approval.json",
    "records/readiness/m2-dem-proj25-receipt-persistence-recovery-002-approval-activation.json",
    "config/qa/m2-dem-vertical-datum-proj25-contract.json",
    "scripts/activate_m2_dem_proj25_receipt_persistence_recovery_002.py",
    "scripts/m2_dem_vertical_datum_proj25_core.py",
    "scripts/recover_m2_dem_vertical_grid_proj25_metadata_001.py",
    "scripts/preflight_m2_dem_proj25_receipt_persistence_recovery_002.py",
    "scripts/recover_m2_dem_proj25_receipt_persistence_002.py",
    "scripts/preflight_m2_dem_vertical_operation_proj25.py",
    "scripts/convert_m2_dem_vertical_datum_proj25.py",
    "scripts/derive_m2_acquisition_checkpoint.py",
    "scripts/record_m2_dem_proj25_receipt_persistence_recovery_002_implementation_readiness.py",
    "tests/test_m2_dem_proj25_receipt_persistence_recovery_002.py",
    "tests/test_m2_dem_vertical_datum_proj25.py",
    "tests/test_m2_dem_vertical_datum_proj25_arcgis.py",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recorded-at-utc", required=True)
    parser.add_argument("--portable-test-count", type=int, required=True)
    parser.add_argument("--portable-skip-count", type=int, required=True)
    parser.add_argument("--arcgis-test-count", type=int, required=True)
    parser.add_argument("--full-test-count", type=int, required=True)
    parser.add_argument("--full-skip-count", type=int, required=True)
    parser.add_argument("--required-file-count", type=int, required=True)
    args = parser.parse_args()
    if OUTPUT.exists():
        raise SystemExit("receipt-persistence recovery-002 implementation-readiness output collision")
    if not args.recorded_at_utc.endswith("Z"):
        raise SystemExit("--recorded-at-utc must be UTC")
    record = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-DEM-PROJ25-RECEIPT-PERSISTENCE-RECOVERY-002-IMPLEMENTATION-READINESS",
        "recorded_at_utc": args.recorded_at_utc,
        "status": "pass_exact_receipt_persistence_recovery_002_implementation_public_ci_pending",
        "bindings": {ref: sha256_file(ROOT / ref) for ref in ARTIFACTS},
        "correction": {
            "timestamp_binding": "function_local_datetime_module_import",
            "receipt_reservation": "exclusive_create_flush_fsync_before_grid_content_read",
            "recovery_001_terminal_unchanged": True,
            "grid_identity_unchanged": True,
            "scientific_predicates_changed": False,
            "source_order_changed": False,
            "threshold_or_tolerance_changed": False,
        },
        "validation": {
            "portable_test_count": args.portable_test_count,
            "portable_intentional_skip_count": args.portable_skip_count,
            "arcgis_runtime_test_count": args.arcgis_test_count,
            "arcgis_runtime_test_failures": 0,
            "full_repository_test_count": args.full_test_count,
            "full_repository_intentional_skip_count": args.full_skip_count,
            "repository_checker_status": f"pass_{args.required_file_count}_required_files",
            "pre_read_reservation_tested": True,
            "unexpected_interruption_persistence_tested": True,
            "validation_failure_persistence_tested": True,
            "collision_and_missing_parent_refusal_tested": True,
            "arcgis_timestamp_rebinding_tested": True,
            "network_and_promotion_absence_tested": True,
        },
        "released_now": {
            "public_ci": True,
            "final_no_content_preflight": False,
            "promoted_grid_inspection": False,
            "new_grid_promotion": False,
            "local_operation_and_sign_preflight": False,
            "dem_conversion": False,
        },
        "assertions": {
            "network_requests_performed": False,
            "promoted_grid_bytes_read": False,
            "new_grid_promotion_performed": False,
            "real_dem_pixels_read": False,
            "external_data_mutated": False,
            "software_installed_or_modified": False,
            "proj_network_enabled": False,
            "orbit_or_radar_action_performed": False,
            "baseline_or_change_analysis_performed": False,
            "scientific_result_established": False,
        },
    }
    write_new_json(OUTPUT, record)
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
