#!/usr/bin/env python3
"""Record the installed ArcGIS SAR tool signatures without reading project data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import arcpy  # type: ignore


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "records/surface-receipts/m2-radar-pixel-orbit-application-001-capability.json"
TOOLS = [
    "ApplyOrbitCorrection_ia",
    "RemoveThermalNoise_ia",
    "ApplyRadiometricCalibration_ia",
    "ApplyRadiometricTerrainFlattening_ia",
    "ApplyGeometricTerrainCorrection_ia",
    "ConvertSARUnits_ia",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observed-at-utc", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise SystemExit(f"output collision: {output}")

    install = arcpy.GetInstallInfo()
    usage = {name: arcpy.Usage(name) for name in TOOLS}
    expected_prefixes = {
        "ApplyOrbitCorrection_ia": "ApplyOrbitCorrection_ia(in_radar_data, {in_orbit_file}, {folder})",
        "RemoveThermalNoise_ia": "RemoveThermalNoise_ia(in_radar_data, out_radar_data",
        "ApplyRadiometricCalibration_ia": "ApplyRadiometricCalibration_ia(in_radar_data, out_radar_data",
        "ApplyRadiometricTerrainFlattening_ia": "ApplyRadiometricTerrainFlattening_ia(in_radar_data, out_radar_data, in_dem_raster",
        "ApplyGeometricTerrainCorrection_ia": "ApplyGeometricTerrainCorrection_ia(in_radar_data, out_radar_data",
        "ConvertSARUnits_ia": "ConvertSARUnits_ia(in_radar_data, out_radar_data",
    }
    signatures_match = all(usage[name].startswith(prefix) for name, prefix in expected_prefixes.items())
    receipt = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-001-CAPABILITY",
        "observed_at_utc": args.observed_at_utc,
        "status": "pass_installed_runtime_capability_only_no_project_data_read" if signatures_match else "block_tool_signature_mismatch",
        "runtime": {
            "product": install.get("ProductName"),
            "version": install.get("Version"),
            "build_number": install.get("BuildNumber"),
            "license_level": arcpy.ProductInfo(),
            "image_analyst": arcpy.CheckExtension("ImageAnalyst"),
        },
        "tool_usage": usage,
        "checks": {
            "all_required_signatures_match": signatures_match,
            "explicit_orbit_file_parameter_available": "{in_orbit_file}" in usage["ApplyOrbitCorrection_ia"],
            "explicit_dem_parameter_available": "in_dem_raster" in usage["ApplyRadiometricTerrainFlattening_ia"],
            "project_sentinel_content_read": False,
            "project_orbit_content_read": False,
            "project_dem_content_read": False,
            "processing_executed": False,
            "network_request_performed": False,
        },
        "limitations": [
            "Tool presence and usage signatures do not establish successful execution on the six approved Sentinel-1 products.",
            "No project raster, orbit, DEM, credential, network resource, or external custody path was opened.",
            "Output behavior, original-input immutability, and stop-on-failure controls require synthetic validation before any real action.",
        ],
    }
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(receipt, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(json.dumps({"output": str(output), "status": receipt["status"]}, indent=2))
    return 0 if signatures_match else 12


if __name__ == "__main__":
    raise SystemExit(main())
