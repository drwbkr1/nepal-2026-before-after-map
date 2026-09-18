#!/usr/bin/env python3
"""Seal the tested metadata-recovery implementation before public CI."""

from __future__ import annotations

import argparse
import json

from m2_dem_vertical_datum_proj25_core import ROOT, sha256_file, write_new_json


OUTPUT = ROOT / "records/readiness/m2-dem-vertical-datum-proj25-metadata-recovery-001-implementation-readiness.json"
ARTIFACTS = [
    "records/source-gates/m2-dem-vertical-datum-proj25-metadata-recovery-001-review-reconciliation.json",
    "records/source-gates/m2-dem-vertical-datum-proj25-metadata-recovery-001-approval.json",
    "records/readiness/m2-dem-vertical-datum-proj25-metadata-recovery-001-approval-activation.json",
    "config/qa/m2-dem-vertical-datum-proj25-contract.json",
    "scripts/activate_m2_dem_vertical_datum_proj25_metadata_recovery_001.py",
    "scripts/m2_dem_vertical_datum_proj25_core.py",
    "scripts/acquire_m2_dem_vertical_grid_proj25.py",
    "scripts/preflight_m2_dem_vertical_datum_proj25_metadata_recovery_001.py",
    "scripts/recover_m2_dem_vertical_grid_proj25_metadata_001.py",
    "scripts/preflight_m2_dem_vertical_operation_proj25.py",
    "scripts/convert_m2_dem_vertical_datum_proj25.py",
    "scripts/derive_m2_acquisition_checkpoint.py",
    "scripts/record_m2_dem_vertical_datum_proj25_metadata_recovery_001_implementation_readiness.py",
    "tests/test_m2_dem_vertical_datum_proj25.py",
    "tests/test_m2_dem_vertical_datum_proj25_arcgis.py",
    "tests/test_m2_dem_vertical_datum_proj25_metadata_recovery_001_review.py",
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
        raise SystemExit("metadata-recovery implementation-readiness output collision")
    if not args.recorded_at_utc.endswith("Z"):
        raise SystemExit("--recorded-at-utc must be UTC")
    record = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-DEM-VERTICAL-DATUM-PROJ25-METADATA-RECOVERY-001-IMPLEMENTATION-READINESS",
        "recorded_at_utc": args.recorded_at_utc,
        "status": "pass_exact_metadata_recovery_implementation_public_ci_pending",
        "bindings": {ref: sha256_file(ROOT / ref) for ref in ARTIFACTS},
        "correction": {
            "from": "literal source_crs and target_crs metadata keys",
            "to": "exact TIFFTAG_IMAGEDESCRIPTION EPSG:4979 to EPSG:3855 plus target_crs_epsg_code=3855",
            "all_other_grid_predicates_unchanged": True,
            "source_semantics_changed": False,
            "target_semantics_changed": False,
            "tolerance_changed": False,
        },
        "validation": {
            "portable_test_count": args.portable_test_count,
            "portable_intentional_skip_count": args.portable_skip_count,
            "arcgis_runtime_test_count": args.arcgis_test_count,
            "arcgis_runtime_test_failures": 0,
            "full_repository_test_count": args.full_test_count,
            "full_repository_intentional_skip_count": args.full_skip_count,
            "repository_checker_status": f"pass_{args.required_file_count}_required_files",
            "exact_official_metadata_acceptance_tested": True,
            "metadata_drift_refusal_tested": True,
            "arcgis_runtime_readability_tested": True,
            "offline_only_recovery_path_tested": True,
            "no_replace_promotion_tested": True,
            "fixed_source_order_and_stop_on_failure_retained": True,
        },
        "released_now": {
            "public_ci": True,
            "final_no_content_preflight": False,
            "preserved_byte_read": False,
            "grid_promotion": False,
            "local_operation_and_sign_preflight": False,
            "dem_conversion": False,
        },
        "assertions": {
            "network_requests_performed": False,
            "preserved_grid_bytes_read": False,
            "grid_promoted": False,
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
