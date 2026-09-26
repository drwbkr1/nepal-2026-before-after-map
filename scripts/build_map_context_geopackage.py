#!/usr/bin/env python3
"""Package approved projected metadata polygons, never satellite pixels."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

os.environ["PROJ_NETWORK"] = "OFF"

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = (ROOT / "scratch").resolve()
SOURCES = (
    ("StudyAreas", "config/aoi/approved-study-areas-epsg32645.json", "AOI_ID", ("AOI-OVERVIEW", "AOI-SOURCE", "AOI-UPPER-CORRIDOR")),
    ("RadarCatalogFootprints", "config/arcgis/radar-catalog-footprints-epsg32645.json", "SOURCE_ID", tuple(f"M1-SRC-{i:03d}" for i in range(1, 7))),
    ("DEMTileBoxes", "config/arcgis/approved-dem-tile-boxes-epsg32645.json", "DEM_ID", tuple(f"M2-DEM-{i:03d}" for i in range(1, 5))),
)
EXPECTED_HASHES = {
    "config/aoi/approved-study-areas-epsg32645.json": "3d6c9bb39fa9b3ffeddfb0048ddabf30ee4472c0006b78c5c7d58193693ac615",
    "config/arcgis/radar-catalog-footprints-epsg32645.json": "40a0ded0ca1dc33d60a136c7c9b1b91df960bb885f58b1d418d66cfe183e530f",
    "config/arcgis/approved-dem-tile-boxes-epsg32645.json": "112f158e66cb0a1220214e15b8bbcca7ad58d657547b2d3e3b9247a5b6e8e310",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_exact_sources() -> list[tuple[str, str, str, dict]]:
    loaded = []
    for name, ref, id_field, expected_ids in SOURCES:
        path = ROOT / ref
        if digest(path) != EXPECTED_HASHES[ref]:
            raise ValueError(f"{ref}: approved metadata bytes differ")
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("geometryType") != "esriGeometryPolygon" or value.get("spatialReference", {}).get("wkid") != 32645:
            raise ValueError(f"{ref}: geometry or EPSG:32645 identity differs")
        if tuple(item["attributes"][id_field] for item in value["features"]) != expected_ids:
            raise ValueError(f"{ref}: approved feature identities or order differ")
        if any(item["geometry"].get("spatialReference", {}).get("wkid") != 32645 for item in value["features"]):
            raise ValueError(f"{ref}: feature CRS differs")
        if any(field.get("type") != "esriFieldTypeString" for field in value["fields"]):
            raise ValueError(f"{ref}: unsupported field type")
        if name == "StudyAreas" and any(item["attributes"].get("STATUS") != "approved_m1_search_review" for item in value["features"]):
            raise ValueError("AOI approval status differs")
        if name == "RadarCatalogFootprints" and any(item["attributes"].get("RECORD_KIND") != "catalog_footprint_not_pixel_coverage" for item in value["features"]):
            raise ValueError("radar catalog claim boundary differs")
        if name == "DEMTileBoxes" and any(item["attributes"].get("RECORD_KIND") != "approved_stac_tile_box_not_valid_pixel_coverage" for item in value["features"]):
            raise ValueError("DEM catalog claim boundary differs")
        loaded.append((name, ref, id_field, value))
    return loaded


def polygon(ogr, rings: list[list[list[float]]]):
    if len(rings) != 1:
        raise ValueError("expected exact single-ring catalog polygon")
    points = rings[0]
    if len(points) < 4 or points[0] != points[-1]:
        raise ValueError("catalog polygon ring is not closed")
    result = ogr.Geometry(ogr.wkbPolygon)
    ring = ogr.Geometry(ogr.wkbLinearRing)
    for point in points:
        if len(point) != 2:
            raise ValueError("catalog point is not two-dimensional")
        ring.AddPoint_2D(float(point[0]), float(point[1]))
    result.AddGeometry(ring)
    if not result.IsValid() or result.GetArea() <= 0:
        raise ValueError("catalog polygon is invalid or empty")
    return result


def build(output_dir: Path) -> dict:
    from osgeo import gdal, ogr, osr

    gdal.UseExceptions()
    ogr.UseExceptions()
    loaded = load_exact_sources()
    destination = output_dir.resolve()
    destination.relative_to(SCRATCH)
    if destination.exists():
        raise FileExistsError(f"append-only output directory already exists: {destination}")
    driver = ogr.GetDriverByName("GPKG")
    if driver is None:
        raise RuntimeError("GDAL GeoPackage driver is unavailable")
    destination.mkdir(parents=True, exist_ok=False)
    gpkg_path = destination / "Nepal_2026_Map_Context.gpkg"
    dataset = driver.CreateDataSource(str(gpkg_path))
    if dataset is None:
        raise RuntimeError("GeoPackage creation failed")
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(32645)
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    for name, _ref, _id_field, source in loaded:
        layer = dataset.CreateLayer(name, srs, ogr.wkbPolygon)
        if layer is None:
            raise RuntimeError(f"layer creation failed: {name}")
        for spec in source["fields"]:
            field = ogr.FieldDefn(spec["name"], ogr.OFTString)
            field.SetWidth(int(spec["length"]))
            if layer.CreateField(field) != 0:
                raise RuntimeError(f"field creation failed: {name}.{spec['name']}")
        for item in source["features"]:
            feature = ogr.Feature(layer.GetLayerDefn())
            for spec in source["fields"]:
                value = item["attributes"].get(spec["name"])
                if not isinstance(value, str) or len(value) > int(spec["length"]):
                    raise ValueError(f"invalid attribute: {name}.{spec['name']}")
                feature.SetField(spec["name"], value)
            feature.SetGeometry(polygon(ogr, item["geometry"]["rings"]))
            if layer.CreateFeature(feature) != 0:
                raise RuntimeError(f"feature creation failed: {name}")
        layer.SyncToDisk()
    dataset = None

    reopened = ogr.Open(str(gpkg_path))
    if reopened is None or reopened.GetLayerCount() != len(loaded):
        raise RuntimeError("GeoPackage reopen or layer count failed")
    checks = []
    for name, ref, id_field, source in loaded:
        layer = reopened.GetLayerByName(name)
        if layer is None or layer.GetFeatureCount() != len(source["features"]):
            raise RuntimeError(f"feature count failed: {name}")
        if layer.GetSpatialRef() is None or layer.GetSpatialRef().GetAuthorityCode(None) != "32645":
            raise RuntimeError(f"projected CRS failed: {name}")
        rows = list(layer)
        for actual, expected in zip(rows, source["features"]):
            if actual.GetField(id_field) != expected["attributes"][id_field]:
                raise RuntimeError(f"feature order or identity failed: {name}")
            if any(actual.GetField(field["name"]) != expected["attributes"][field["name"]] for field in source["fields"]):
                raise RuntimeError(f"attributes differ: {name}")
            if not actual.GetGeometryRef().Equals(polygon(ogr, expected["geometry"]["rings"])):
                raise RuntimeError(f"geometry differs: {name}")
        checks.append({"layer": name, "count": len(rows), "ids": [row.GetField(id_field) for row in rows], "wkid": 32645, "input_ref": ref, "input_sha256": digest(ROOT / ref)})
    reopened = None

    readme = destination / "README.md"
    readme.write_text(
        "# Nepal 2026 map context (metadata only)\n\n"
        "Add `Nepal_2026_Map_Context.gpkg` to ArcGIS Pro to inspect three EPSG:32645 polygon layers: approved search/review AOIs, Sentinel-1 catalog footprints, and approved DEM STAC tile boxes. "
        "These are not verified valid-pixel footprints, terrain coverage, observed change, interpretation, or event attribution. No satellite or DEM pixels are included. "
        "The final before/after map requires separate real-pixel QA, registration, scientific review, and export verification.\n",
        encoding="utf-8", newline="\n",
    )
    receipt = {
        "schema_version": "1.0",
        "status": "pass_ogr_metadata_geopackage_only_not_final_arcgis_delivery",
        "output": str(gpkg_path),
        "output_bytes": gpkg_path.stat().st_size,
        "output_sha256": digest(gpkg_path),
        "readme_sha256": digest(readme),
        "layers": checks,
        "checks": {"gdal_version": gdal.VersionInfo("RELEASE_NAME"), "proj_network": "OFF", "geometry_and_attributes_reopened_equal": True, "arcgis_pro_open_or_export_tested": False, "satellite_or_dem_pixels_read": False, "scientific_change_claim": False},
    }
    receipt_path = destination / "receipt.json"
    with receipt_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    receipt = build(args.output_dir)
    print(f"PASS: {receipt['output']} ({receipt['output_bytes']} bytes, metadata only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
