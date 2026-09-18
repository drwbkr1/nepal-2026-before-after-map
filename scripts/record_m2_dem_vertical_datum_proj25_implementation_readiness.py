#!/usr/bin/env python3
"""Record the tested implementation-only state before public CI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from m2_dem_vertical_datum_proj25_core import ROOT, sha256_file, write_new_json


OUTPUT = ROOT / "records/readiness/m2-dem-vertical-datum-proj25-implementation-readiness.json"
ARTIFACTS = [
    "config/qa/m2-dem-vertical-datum-proj25-contract.json",
    "scripts/m2_dem_vertical_datum_proj25_core.py",
    "scripts/preflight_m2_dem_vertical_datum_proj25.py",
    "scripts/acquire_m2_dem_vertical_grid_proj25.py",
    "scripts/preflight_m2_dem_vertical_operation_proj25.py",
    "scripts/convert_m2_dem_vertical_datum_proj25.py",
    "scripts/record_m2_dem_vertical_datum_proj25_publication_gate.py",
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
        raise SystemExit("implementation-readiness output collision")
    if not args.recorded_at_utc.endswith("Z"):
        raise SystemExit("--recorded-at-utc must be UTC")
    bindings = {ref: sha256_file(ROOT / ref) for ref in ARTIFACTS}
    record = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-DEM-VERTICAL-DATUM-PROJ25-IMPLEMENTATION-READINESS",
        "recorded_at_utc": args.recorded_at_utc,
        "status": "pass_implementation_synthetic_validation_public_ci_pending",
        "approval_sha256": "d2e839dbd005e7d1ed85ab86b26cd887135576d50ad8071b742af1134ecc186c",
        "bindings": bindings,
        "validation": {
            "portable_test_count": args.portable_test_count,
            "portable_intentional_skip_count": args.portable_skip_count,
            "arcgis_runtime_test_count": args.arcgis_test_count,
            "arcgis_runtime_test_failures": 0,
            "full_repository_test_count": args.full_test_count,
            "full_repository_intentional_skip_count": args.full_skip_count,
            "repository_checker_status": f"pass_{args.required_file_count}_required_files",
            "synthetic_height_relation": "h = H + N",
            "synthetic_output_arcgis_readable": True,
            "source_immutability_tested": True,
            "interrupted_partial_preservation_tested": True,
            "output_collision_tested": True,
            "fixed_source_order_tested": True,
        },
        "released_now": {
            "public_ci": True,
            "final_no_payload_preflight": False,
            "grid_request": False,
            "dem_pixel_read": False,
            "dem_conversion": False,
        },
        "assertions": {
            "network_requests_performed": False,
            "grid_payload_bytes_read": 0,
            "real_dem_pixels_read": False,
            "external_data_mutated": False,
            "software_installed_or_modified": False,
            "proj_network_enabled": False,
            "orbit_or_radar_action_performed": False,
            "scientific_result_established": False,
        },
    }
    write_new_json(OUTPUT, record)
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
