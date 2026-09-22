#!/usr/bin/env python3
"""Validate projected public-metadata FeatureSets in ArcGIS Pro memory only."""

from __future__ import annotations

import argparse
import datetime as datetime_module
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAP_RECEIPT_REF = "records/observations/m2-radar-catalog-dem-coverage-map-001.json"
RADAR_REF = "config/arcgis/radar-catalog-footprints-epsg32645.json"
DEM_REF = "config/arcgis/approved-dem-tile-boxes-epsg32645.json"
DEFAULT_RECEIPT_REF = "records/surface-receipts/m2-radar-catalog-coverage-arcgis-validation-001.json"


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", default=DEFAULT_RECEIPT_REF)
    args = parser.parse_args()
    receipt_path = ROOT / args.receipt
    if receipt_path.exists():
        raise SystemExit("ArcGIS validation receipt collision")
    map_receipt = json.loads((ROOT / MAP_RECEIPT_REF).read_text(encoding="utf-8"))
    expected_hashes = {item["ref"]: item["sha256"] for item in map_receipt["outputs"]}
    if expected_hashes.get(RADAR_REF) != sha256(RADAR_REF) or expected_hashes.get(DEM_REF) != sha256(DEM_REF):
        raise SystemExit("projected FeatureSet hash differs from published metadata observation")

    import arcpy

    arcpy.env.overwriteOutput = False
    observations = []
    for ref, key_field, expected_ids, memory_name in (
        (RADAR_REF, "SOURCE_ID", [f"M1-SRC-{i:03d}" for i in range(1, 7)], r"memory\radar_catalog_coverage_validation_001"),
        (DEM_REF, "DEM_ID", [f"M2-DEM-{i:03d}" for i in range(1, 5)], r"memory\dem_catalog_coverage_validation_001"),
    ):
        if arcpy.Exists(memory_name):
            raise SystemExit("temporary ArcGIS feature class collision")
        try:
            arcpy.conversion.JSONToFeatures(str((ROOT / ref).resolve()), memory_name)
            description = arcpy.Describe(memory_name)
            count = int(arcpy.management.GetCount(memory_name)[0])
            rows = []
            with arcpy.da.SearchCursor(memory_name, [key_field, "SHAPE@AREA", "SHAPE@"]) as cursor:
                for feature_id, area, geometry in cursor:
                    rows.append({
                        "id": feature_id,
                        "area_square_metres": round(float(area), 1),
                        "point_count": int(geometry.pointCount) if geometry else 0,
                    })
            if count != len(expected_ids) or sorted(row["id"] for row in rows) != expected_ids:
                raise ValueError("ArcGIS feature count or exact IDs differ")
            if description.shapeType != "Polygon" or description.spatialReference.factoryCode != 32645:
                raise ValueError("ArcGIS polygon or EPSG:32645 identity differs")
            if any(row["area_square_metres"] <= 0 or row["point_count"] < 4 for row in rows):
                raise ValueError("ArcGIS imported an empty or degenerate polygon")
            extent = description.extent
            observations.append({
                "input_ref": ref,
                "input_sha256": sha256(ref),
                "temporary_dataset": memory_name,
                "feature_count": count,
                "shape_type": description.shapeType,
                "spatial_reference_wkid": description.spatialReference.factoryCode,
                "extent_m": {"xmin": extent.XMin, "ymin": extent.YMin, "xmax": extent.XMax, "ymax": extent.YMax},
                "features": sorted(rows, key=lambda row: row["id"]),
            })
        finally:
            if arcpy.Exists(memory_name):
                arcpy.management.Delete(memory_name)

    receipt = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-RADAR-CATALOG-COVERAGE-ARCGIS-VALIDATION-001",
        "validated_at_utc": datetime_module.datetime.now(datetime_module.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "pass_arcgis_metadata_featureset_import_only",
        "inputs": {"map_observation_ref": MAP_RECEIPT_REF, "map_observation_sha256": sha256(MAP_RECEIPT_REF)},
        "runtime": {"product": arcpy.GetInstallInfo().get("ProductName"), "version": arcpy.GetInstallInfo().get("Version")},
        "method": "ArcGIS Pro JSONToFeatures in memory, Describe, GetCount, and geometry cursor checks over repository metadata JSON only",
        "observations": observations,
        "assertions": {
            "project_data_or_external_custody_accessed": False,
            "radar_or_dem_pixels_read": False,
            "gtc_or_other_sar_processing_invoked": False,
            "metadata_featureset_import_and_epsg32645_established": True,
            "arcgis_map_or_package_created": False,
            "valid_pixel_coverage_or_change_established": False,
        },
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    with receipt_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(receipt, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"status": receipt["status"], "counts": [row["feature_count"] for row in observations], "receipt": args.receipt, "sha256": sha256(args.receipt)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
