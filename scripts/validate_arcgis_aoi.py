#!/usr/bin/env python3
"""Open the projected AOI FeatureSet with ArcGIS and write a validation receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import arcpy


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--validated-at-utc", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    output_fc = r"memory\m1_approved_aoi_validation"
    arcpy.conversion.JSONToFeatures(str(args.input.resolve()), output_fc)
    description = arcpy.Describe(output_fc)
    count = int(arcpy.management.GetCount(output_fc)[0])
    areas = []
    with arcpy.da.SearchCursor(output_fc, ["AOI_ID", "SHAPE@AREA", "SHAPE@"] ) as rows:
        for aoi_id, area, geometry in rows:
            areas.append({"aoi_id": aoi_id, "area_square_metres": area, "is_empty": geometry is None or geometry.pointCount == 0})

    checks = {
        "json_to_features": "pass",
        "feature_count_3": "pass" if count == 3 else "fail",
        "spatial_reference_epsg_32645": "pass" if description.spatialReference.factoryCode == 32645 else "fail",
        "nonempty_positive_area": "pass" if all(not row["is_empty"] and row["area_square_metres"] > 0 for row in areas) else "fail",
    }
    if "fail" in checks.values():
        raise SystemExit(json.dumps(checks))

    extent = description.extent
    receipt = {
        "schema_version": "1.0",
        "receipt_id": "M1-APPROVED-AOI-ARCGIS-VALIDATION-001",
        "status": "pass",
        "validated_at_utc": args.validated_at_utc,
        "input": str(args.input).replace("\\", "/"),
        "input_sha256": sha256(args.input),
        "arcgis_version": arcpy.GetInstallInfo().get("Version"),
        "method": "ArcGIS JSON To Features plus Describe and geometry cursor checks",
        "spatial_reference": {
            "factory_code": description.spatialReference.factoryCode,
            "name": description.spatialReference.name,
        },
        "feature_count": count,
        "extent": {"xmin": extent.XMin, "ymin": extent.YMin, "xmax": extent.XMax, "ymax": extent.YMax},
        "features": areas,
        "checks": checks,
        "retained_failures": [
            {
                "attempt": 1,
                "status": "failed_after_json_import",
                "reason": "ArcGIS Pro 3.7.1 Polygon objects do not expose the attempted isEmpty property.",
                "remediation": "Use a null-or-pointCount geometry emptiness check and rerun the full import validation.",
            }
        ],
        "limitations": [
            "This validates ArcGIS import, CRS, geometry count, and nonzero projected area only.",
            "The geometries are approved search and review extents, not event-change polygons.",
        ],
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": "pass", "receipt": str(args.receipt), "receipt_sha256": sha256(args.receipt)}, indent=2))


if __name__ == "__main__":
    main()
