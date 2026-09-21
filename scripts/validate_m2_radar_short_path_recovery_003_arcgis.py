#!/usr/bin/env python3
"""Validate the short-path recovery contract in the installed ArcGIS runtime.

This check uses disposable paths only. It imports ArcPy and inspects the
licensed ApplyOrbitCorrection interface but does not invoke geoprocessing.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile

import arcpy  # type: ignore

import m2_radar_short_path_recovery_003_core as core
import run_m2_radar_short_path_recovery_003 as runner


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_REF = "records/readiness/m2-radar-short-path-recovery-003-arcgis-runtime-validation.json"
EXTERNAL_ROOT = Path(r"C:\Projects\Active\nepal-2026-before-after-map-data").resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verified-at-utc", required=True)
    args = parser.parse_args()
    if not args.verified_at_utc.endswith("Z"):
        raise SystemExit("--verified-at-utc must be UTC")
    output = ROOT / OUTPUT_REF
    if output.exists():
        raise SystemExit("ArcGIS runtime validation output collision")

    with tempfile.TemporaryDirectory(prefix="nepal-radar-short-path-003-") as temporary:
        temporary_root = Path(temporary).resolve()
        if (
            temporary_root == ROOT
            or ROOT in temporary_root.parents
            or temporary_root == EXTERNAL_ROOT
            or EXTERNAL_ROOT in temporary_root.parents
        ):
            raise SystemExit("temporary root intersects repository or external custody")
        disposable_240 = temporary_root / ("x" * max(1, 240 - len(str(temporary_root)) - 1))
        if len(str(disposable_240)) != 240:
            raise SystemExit("disposable 240-character boundary construction failed")

    install = arcpy.GetInstallInfo()
    product_info = str(arcpy.ProductInfo())
    image_status = str(arcpy.CheckExtension("ImageAnalyst"))
    spatial_status = str(arcpy.CheckExtension("Spatial"))
    tool = getattr(arcpy.ia, "ApplyOrbitCorrection", None)
    documentation = str(getattr(tool, "__doc__", "") or "")
    if not product_info or product_info.casefold() in {"notinitialized", "none"}:
        raise SystemExit("ArcGIS product is not initialized")
    if image_status not in {"Available", "CheckedOut"}:
        raise SystemExit(f"Image Analyst is unavailable: {image_status}")
    if spatial_status not in {"Available", "CheckedOut"}:
        raise SystemExit(f"Spatial Analyst is unavailable: {spatial_status}")
    if not callable(tool):
        raise SystemExit("ApplyOrbitCorrection is unavailable")
    if "orbit" not in documentation.casefold() or "radar" not in documentation.casefold():
        raise SystemExit("ApplyOrbitCorrection interface documentation is unavailable")

    plan = core.load_execution_plan(ROOT)
    receipt = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-SHORT-PATH-RECOVERY-003-ARCGIS-RUNTIME-VALIDATION",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_installed_arcgis_runtime_signature_license_and_disposable_path_validation",
        "runtime": {
            "product": install.get("ProductName"),
            "version": install.get("Version"),
            "license_level": product_info,
            "image_analyst_status": image_status,
            "spatial_analyst_status": spatial_status,
            "python_executable": str(Path(__import__("sys").executable).resolve()),
        },
        "bindings": runner.repository_bindings(),
        "checks": {
            "contract_loaded_and_authority_bound": plan["contract"]["contract_id"]
            == "NEPAL-M2-RADAR-SHORT-PATH-RECOVERY-003",
            "apply_orbit_correction_callable": True,
            "apply_orbit_correction_documentation_mentions_radar_and_orbit": True,
            "image_analyst_license_available": True,
            "spatial_analyst_license_available": True,
            "disposable_240_character_path_constructed": True,
        },
        "assertions": {
            "disposable_inputs_only": True,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "apply_orbit_correction_invoked": False,
            "geoprocessing_invoked": False,
            "extension_checked_out": False,
            "network_request_performed": False,
            "credential_value_read": False,
            "production_attempt_created": False,
            "baseline_or_change_analysis_executed": False,
            "scientific_result_established": False,
        },
    }
    core.write_new_json(output, receipt)
    print(json.dumps({"status": receipt["status"], "receipt": OUTPUT_REF}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
