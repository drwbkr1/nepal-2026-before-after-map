#!/usr/bin/env python3
"""Project approved AOIs with ArcGIS Pro and emit an ArcGIS FeatureSet JSON."""

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
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source = json.loads(args.input.read_text(encoding="utf-8"))
    if source.get("properties", {}).get("status") != "approved_m1_search_review":
        raise SystemExit("input AOI is not approved for M1 search and review")

    wgs84 = arcpy.SpatialReference(4326)
    utm45n = arcpy.SpatialReference(32645)
    features = []
    all_xy: list[tuple[float, float]] = []
    for feature in source["features"]:
        rings = feature["geometry"]["coordinates"]
        projected_rings = []
        for ring in rings:
            points = arcpy.Array([arcpy.Point(x, y) for x, y in ring])
            polygon = arcpy.Polygon(points, wgs84)
            projected = polygon.projectAs(utm45n)
            geometry = json.loads(projected.JSON)
            for projected_ring in geometry["rings"]:
                projected_rings.append(projected_ring)
                all_xy.extend((float(x), float(y)) for x, y in projected_ring)
        properties = feature["properties"]
        features.append(
            {
                "attributes": {
                    "AOI_ID": properties["aoi_id"],
                    "NAME": properties["name"],
                    "PURPOSE": properties["purpose"],
                    "STATUS": properties["status"],
                    "SOURCE_REF": properties["source_ref"],
                },
                "geometry": {
                    "rings": projected_rings,
                    "spatialReference": {"wkid": 32645, "latestWkid": 32645},
                },
            }
        )

    output = {
        "objectIdFieldName": "",
        "uniqueIdField": {"name": "AOI_ID", "isSystemMaintained": False},
        "globalIdFieldName": "",
        "geometryType": "esriGeometryPolygon",
        "spatialReference": {"wkid": 32645, "latestWkid": 32645},
        "fields": [
            {"name": "AOI_ID", "type": "esriFieldTypeString", "alias": "AOI ID", "length": 40},
            {"name": "NAME", "type": "esriFieldTypeString", "alias": "Name", "length": 80},
            {"name": "PURPOSE", "type": "esriFieldTypeString", "alias": "Purpose", "length": 160},
            {"name": "STATUS", "type": "esriFieldTypeString", "alias": "Status", "length": 40},
            {"name": "SOURCE_REF", "type": "esriFieldTypeString", "alias": "Source reference", "length": 160},
        ],
        "features": features,
        "projectMetadata": {
            "source": str(args.input).replace("\\", "/"),
            "sourceSha256": sha256(args.input),
            "sourceCrs": "EPSG:4326",
            "analysisCrs": "EPSG:32645",
            "projectionEngine": "ArcGIS Pro arcpy Geometry.projectAs",
            "arcgisVersion": arcpy.GetInstallInfo().get("Version"),
            "extent": {
                "xmin": min(x for x, _ in all_xy),
                "ymin": min(y for _, y in all_xy),
                "xmax": max(x for x, _ in all_xy),
                "ymax": max(y for _, y in all_xy),
                "spatialReference": {"wkid": 32645, "latestWkid": 32645},
            },
            "claimBoundary": "Projected search and review extents; not change polygons or event attribution.",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "status": "projected_with_arcgis",
                "arcgis_version": output["projectMetadata"]["arcgisVersion"],
                "spatial_reference": output["spatialReference"],
                "feature_count": len(features),
                "output_sha256": sha256(args.output),
                "output": str(args.output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
