#!/usr/bin/env python3
"""Record the installed ArcGIS Pro SAR-processing capability without reading data."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import arcpy


TOOLS = (
    "ComputeSARIndices_ia",
    "ConvertSARUnits_ia",
    "GenerateMaskedSARRaster_ia",
    "ApplyRadiometricCalibration_ia",
    "ApplyRadiometricTerrainFlattening_ia",
    "GenerateRadiometricTerrainCorrectedData_ia",
    "ApplyGeometricTerrainCorrection_ia",
    "Despeckle_ia",
)


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observed-at-utc", required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("records/surface-receipts/arcgis-sar-processing-capability.json"),
    )
    args = parser.parse_args()
    if not args.observed_at_utc.endswith("Z"):
        raise SystemExit("--observed-at-utc must be an RFC 3339 UTC timestamp ending in Z")

    install = arcpy.GetInstallInfo()
    tool_records = []
    for tool_name in TOOLS:
        usage = arcpy.Usage(tool_name)
        tool_records.append(
            {
                "name": tool_name,
                "available": bool(usage),
                "usage": usage or None,
                "mentions_dem_parameter": "dem" in (usage or "").casefold(),
            }
        )

    receipt = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ARCGIS-SAR-CAPABILITY-001",
        "status": "pass_capability_only_dem_dependency_unresolved",
        "observed_at_utc": args.observed_at_utc,
        "runtime": {
            "product": install.get("ProductName"),
            "version": install.get("Version"),
            "build_number": install.get("BuildNumber"),
            "license_level": arcpy.ProductInfo(),
            "image_analyst": arcpy.CheckExtension("ImageAnalyst"),
            "spatial_analyst": arcpy.CheckExtension("Spatial"),
            "python_version": install.get("PythonVersion"),
        },
        "tools": tool_records,
        "checks": {
            "all_named_tools_available": all(item["available"] for item in tool_records),
            "radiometric_terrain_flattening_requires_dem": next(
                item["mentions_dem_parameter"]
                for item in tool_records
                if item["name"] == "ApplyRadiometricTerrainFlattening_ia"
            ),
            "radiometric_terrain_corrected_data_requires_dem": next(
                item["mentions_dem_parameter"]
                for item in tool_records
                if item["name"] == "GenerateRadiometricTerrainCorrectedData_ia"
            ),
            "geometric_terrain_correction_requires_dem": next(
                item["mentions_dem_parameter"]
                for item in tool_records
                if item["name"] == "ApplyGeometricTerrainCorrection_ia"
            ),
            "satellite_or_dem_pixels_read": False,
            "processing_executed": False,
        },
        "dependency_decision": {
            "status": "defer_pending_exact_dem_source_and_rights_gate",
            "reason": "The installed terrain-correction tools accept or require a DEM, while the active M2 acquisition approval contains only eight Sentinel products and no approved elevation source.",
            "authority_created": False,
        },
        "limitations": [
            "Tool presence and usage signatures do not prove successful processing of the approved Sentinel products.",
            "No DEM, Sentinel archive, raster, credential, authenticated session, or external custody file was read.",
            "A DEM source must pass exact identity, rights, custody, integrity, and fitness gates before terrain correction begins.",
        ],
    }
    payload = canonical_bytes(receipt)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise SystemExit(f"REFUSED: output already exists: {args.output}")
    args.output.write_bytes(payload)
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "output": str(args.output),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "tool_count": len(tool_records),
                "all_named_tools_available": receipt["checks"]["all_named_tools_available"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
