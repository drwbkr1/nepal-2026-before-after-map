#!/usr/bin/env python3
"""Read-only SAFE geolocation-grid and DEM-validity gate for the exact SAR pair."""

from __future__ import annotations

import argparse
import json
import math
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from m2_dem_vertical_datum_proj25_core import sha256_file
from m2_radar_event_pair_dem_intake_001 import IntakeError, ROOT, DATA_ROOT
from m2_radar_event_pair_dem_mosaic_001 import MOSAIC
from m2_radar_pixel_orbit_application_001_core import require_external_child, stable_inventory
from m2_radar_esri_sequence_recovery_005_core import load_execution_plan


PREFIX = "m2-radar-event-area-pair-001"
IDS = ("M1-SRC-002", "M1-SRC-005")
MOSAIC_RECORD = ROOT / "records" / "processing" / f"{PREFIX}-dem-mosaic-reconciliation.json"
IMPLEMENTATION_GATE = ROOT / "records" / "readiness" / f"{PREFIX}-footprint-implementation-gate.json"
PREFLIGHT = ROOT / "records" / "readiness" / f"{PREFIX}-footprint-preflight.json"
OUTPUT = ROOT / "records" / "processing" / f"{PREFIX}-footprint-dem-validity-gate.json"
PRODUCT_BUFFER_DEGREES = 0.005


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise IntakeError("record_not_object")
    return value


def exact_sources() -> list[dict[str, Any]]:
    proposal = read_json(ROOT / "contracts" / "milestone-002-radar-event-area-pair-001-proposal.json")
    if (proposal.get("proposed_normative_amendments", {}).get("source_subset") != list(IDS)
            or proposal.get("proposed_normative_amendments", {}).get("dem_must_span_entire_actual_processed_sar_extents") is not True):
        raise IntakeError("approved_pair_scope_drift")
    plan = load_execution_plan(ROOT)
    sources = [item for item in plan["sources"] if item["source_id"] in IDS]
    if [item["source_id"] for item in sources] != list(IDS):
        raise IntakeError("exact_source_order_drift")
    return sources


def verify_mosaic_record() -> dict[str, Any]:
    record = read_json(MOSAIC_RECORD)
    if (record.get("status") != "pass_mosaic_identity_and_structure_only_pending_actual_sar_extent_gate"
            or record.get("output_sha256") != "e46bd9455c19dda85d8c63d0f721df27a4e14abbcc9be0d15e32ed44f32dea4e"
            or not MOSAIC.is_file() or MOSAIC.stat().st_size != record.get("output_size_bytes")
            or sha256_file(MOSAIC) != record.get("output_sha256")):
        raise IntakeError("eleven_tile_mosaic_identity_drift")
    return record


def annotation_paths(source: dict[str, Any]) -> tuple[Path, Path, dict[str, Any]]:
    safe = require_external_child(DATA_ROOT, Path(source["safe_root"]))
    manifest_path = require_external_child(DATA_ROOT, Path(source["external_manifest_path"]))
    if not safe.is_dir() or not manifest_path.is_file() or sha256_file(manifest_path) != source["external_manifest_sha256"]:
        raise IntakeError("safe_or_manifest_identity_drift")
    manifest = read_json(manifest_path)
    if manifest.get("source_id") != source["source_id"] or manifest.get("exact_product_id") != source["exact_product_id"]:
        raise IntakeError("safe_manifest_identity_drift")
    paths = []
    for polarization in ("vv", "vh"):
        matches = [item for item in manifest.get("files", [])
                   if Path(item["relative_path"]).parent.as_posix().casefold() == "annotation"
                   and item["relative_path"].lower().endswith(".xml")
                   and f"-grd-{polarization}-" in item["relative_path"].lower()]
        if len(matches) != 1:
            raise IntakeError("exact_annotation_inventory_missing")
        item = matches[0]
        relative = Path(item["relative_path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise IntakeError("unsafe_annotation_path")
        path = require_external_child(safe, safe / relative)
        if not path.is_file() or path.stat().st_size != item["size_bytes"]:
            raise IntakeError("annotation_file_missing_or_size_drift")
        paths.append(path)
    return paths[0], paths[1], manifest


def parse_geolocation_grid(path: Path) -> dict[str, Any]:
    root = ET.parse(path).getroot()
    lines = int(root.findtext(".//numberOfLines") or "0")
    samples = int(root.findtext(".//numberOfSamples") or "0")
    points: dict[tuple[int, int], tuple[float, float]] = {}
    for node in root.findall(".//geolocationGridPoint"):
        key = (int(node.findtext("line") or "-1"), int(node.findtext("pixel") or "-1"))
        lat = float(node.findtext("latitude") or "nan")
        lon = float(node.findtext("longitude") or "nan")
        if key in points or not (math.isfinite(lat) and math.isfinite(lon)) or not (25 < lat < 32 and 80 < lon < 90):
            raise IntakeError("geolocation_point_invalid")
        points[key] = (lon, lat)
    row_ids = sorted({key[0] for key in points})
    column_ids = sorted({key[1] for key in points})
    if (lines != 16732 or samples != 25769 or len(row_ids) != 10 or len(column_ids) != 21
            or row_ids[0] != 0 or row_ids[-1] != lines - 1
            or column_ids[0] != 0 or column_ids[-1] != samples - 1
            or len(points) != len(row_ids) * len(column_ids) or len(points) != 210):
        raise IntakeError("geolocation_grid_not_full_actual_scene")
    ring = ([points[(row_ids[0], column)] for column in column_ids]
            + [points[(row, column_ids[-1])] for row in row_ids[1:]]
            + [points[(row_ids[-1], column)] for column in reversed(column_ids[:-1])]
            + [points[(row, column_ids[0])] for row in reversed(row_ids[1:-1])])
    return {"lines": lines, "samples": samples, "grid_points": len(points), "ring": ring}


def no_content_preflight() -> dict[str, Any]:
    if PREFLIGHT.exists() or OUTPUT.exists():
        raise IntakeError("footprint_preflight_or_audit_collision")
    implementation = read_json(IMPLEMENTATION_GATE)
    if (implementation.get("status") != "pass_public_ci_footprint_implementation"
            or implementation.get("code_sha256") != sha256_file(Path(__file__))
            or implementation.get("mosaic_reconciliation_sha256") != sha256_file(MOSAIC_RECORD)):
        raise IntakeError("footprint_public_implementation_gate_missing")
    sources = exact_sources()
    mosaic = verify_mosaic_record()
    annotations = []
    for source in sources:
        vv, vh, manifest = annotation_paths(source)
        inventory_names = {item["relative_path"].casefold() for item in manifest["files"]}
        if len(inventory_names) != len(manifest["files"]):
            raise IntakeError("safe_inventory_duplicate_paths")
        annotations.append({"source_id": source["source_id"], "vv_exists": vv.is_file(), "vh_exists": vh.is_file(), "manifest_sha256": source["external_manifest_sha256"]})
    return {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-EVENT-AREA-PAIR-001-FOOTPRINT-PREFLIGHT",
        "checked_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": "pass_no_content_footprint_audit_eligible",
        "implementation_gate_sha256": sha256_file(IMPLEMENTATION_GATE),
        "mosaic_output_sha256": mosaic["output_sha256"],
        "source_annotations": annotations,
        "safe_member_hash_scan_started": False,
        "dem_pixel_scan_started": False,
        "radar_geoprocessing_started": False,
    }


def polygon_from_ring(ring: list[tuple[float, float]], ogr: Any) -> Any:
    linear = ogr.Geometry(ogr.wkbLinearRing)
    for lon, lat in ring + [ring[0]]:
        linear.AddPoint_2D(lon, lat)
    polygon = ogr.Geometry(ogr.wkbPolygon)
    polygon.AddGeometry(linear)
    if not polygon.IsValid():
        raise IntakeError("geolocation_boundary_polygon_invalid")
    return polygon.Buffer(PRODUCT_BUFFER_DEGREES)


def scan_dem_validity(dataset: Any, polygons: list[Any], *, gdal: Any, ogr: Any, np: Any) -> dict[str, Any]:
    merged = polygons[0].Union(polygons[1])
    if merged is None or merged.IsEmpty() or not merged.IsValid():
        raise IntakeError("polarization_footprint_union_invalid")
    west, east, south, north = merged.GetEnvelope()
    x_origin, dx, _, y_origin, _, dy = dataset.GetGeoTransform()
    x0 = max(0, math.floor((west - x_origin) / dx) - 1)
    x1 = min(dataset.RasterXSize, math.ceil((east - x_origin) / dx) + 1)
    y0 = max(0, math.floor((north - y_origin) / dy) - 1)
    y1 = min(dataset.RasterYSize, math.ceil((south - y_origin) / dy) + 1)
    if x0 >= x1 or y0 >= y1 or west < x_origin or east > x_origin + dataset.RasterXSize * dx or north > y_origin or south < y_origin + dataset.RasterYSize * dy:
        raise IntakeError("actual_sar_footprint_outside_dem_extent")
    width, height = x1 - x0, y1 - y0
    mask = gdal.GetDriverByName("MEM").Create("", width, height, 1, gdal.GDT_Byte)
    mask.SetGeoTransform((x_origin + x0 * dx, dx, 0, y_origin + y0 * dy, 0, dy))
    mask.SetProjection(dataset.GetProjection())
    from osgeo import osr  # type: ignore

    reference = osr.SpatialReference()
    if reference.ImportFromWkt(dataset.GetProjection()) != 0:
        raise IntakeError("dem_spatial_reference_unreadable")
    datasource = ogr.GetDriverByName("Memory").CreateDataSource("")
    layer = datasource.CreateLayer("footprint", srs=reference, geom_type=ogr.wkbPolygon)
    feature = ogr.Feature(layer.GetLayerDefn())
    feature.SetGeometry(merged)
    layer.CreateFeature(feature)
    gdal.RasterizeLayer(mask, [1], layer, burn_values=[1], options=["ALL_TOUCHED=TRUE"])
    band = dataset.GetRasterBand(1)
    nodata = band.GetNoDataValue()
    count = invalid = 0
    minimum = float("inf")
    maximum = float("-inf")
    for offset in range(0, height, 256):
        rows = min(256, height - offset)
        included = mask.GetRasterBand(1).ReadAsArray(0, offset, width, rows) != 0
        selected = int(np.count_nonzero(included))
        if not selected:
            continue
        values = band.ReadAsArray(x0, y0 + offset, width, rows)
        native_mask = band.GetMaskBand().ReadAsArray(x0, y0 + offset, width, rows) != 0
        valid = included & native_mask & np.isfinite(values)
        if nodata is not None:
            valid &= values != nodata
        count += selected
        invalid += selected - int(np.count_nonzero(valid))
        if np.any(valid):
            minimum = min(minimum, float(np.min(values[valid])))
            maximum = max(maximum, float(np.max(values[valid])))
    if count == 0:
        raise IntakeError("actual_sar_footprint_empty_on_dem")
    return {
        "footprint_bounds_degrees": [round(west, 8), round(south, 8), round(east, 8), round(north, 8)],
        "conservative_buffer_degrees": PRODUCT_BUFFER_DEGREES,
        "dem_grid_cells_in_full_buffered_footprint": count,
        "valid_dem_cells": count - invalid,
        "invalid_dem_cells": invalid,
        "valid_fraction": round((count - invalid) / count, 9),
        "observed_min_ellipsoidal_elevation_m": None if minimum == float("inf") else round(minimum, 4),
        "observed_max_ellipsoidal_elevation_m": None if maximum == float("-inf") else round(maximum, 4),
    }


def audit() -> dict[str, Any]:
    if OUTPUT.exists():
        raise IntakeError("footprint_audit_already_written")
    preflight = read_json(PREFLIGHT)
    if preflight.get("status") != "pass_no_content_footprint_audit_eligible" or preflight.get("implementation_gate_sha256") != sha256_file(IMPLEMENTATION_GATE):
        raise IntakeError("footprint_no_content_preflight_missing")
    sources = exact_sources()
    verify_mosaic_record()
    from osgeo import gdal, ogr  # type: ignore
    import numpy as np  # type: ignore

    gdal.UseExceptions()
    os.environ["PROJ_NETWORK"] = "OFF"
    dataset = gdal.Open(str(MOSAIC), gdal.GA_ReadOnly)
    if dataset is None or dataset.RasterXSize != 14400 or dataset.RasterYSize != 10800:
        raise IntakeError("mosaic_open_or_shape_drift")
    results = []
    for source in sources:
        vv_path, vh_path, manifest = annotation_paths(source)
        safe = require_external_child(DATA_ROOT, Path(source["safe_root"]))
        expected_inventory = sorted(
            ({"relative_path": item["relative_path"], "size_bytes": item["size_bytes"], "sha256": item["sha256"]}
             for item in manifest.get("files", [])),
            key=lambda item: item["relative_path"].casefold(),
        )
        if stable_inventory(safe) != expected_inventory:
            raise IntakeError("safe_member_byte_identity_drift")
        grids = [parse_geolocation_grid(path) for path in (vv_path, vh_path)]
        polygons = [polygon_from_ring(grid["ring"], ogr) for grid in grids]
        scan = scan_dem_validity(dataset, polygons, gdal=gdal, ogr=ogr, np=np)
        results.append({
            "source_id": source["source_id"],
            "safe_manifest_sha256": source["external_manifest_sha256"],
            "annotation_sha256": {"VV": sha256_file(vv_path), "VH": sha256_file(vh_path)},
            "geolocation_grid_points_per_polarization": [grid["grid_points"] for grid in grids],
            **scan,
        })
        if scan["invalid_dem_cells"] != 0:
            break
    passed = len(results) == 2 and all(item["invalid_dem_cells"] == 0 for item in results)
    return {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-EVENT-AREA-PAIR-001-FOOTPRINT-DEM-VALIDITY-GATE",
        "checked_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": "pass_full_actual_sar_footprints_have_valid_dem" if passed else "block_full_actual_sar_footprint_dem_gap",
        "method": "Exact materialized SAFE VV and VH annotation geolocation-grid outer boundaries, full scene line and sample extrema, conservative 0.005-degree buffer, GDAL ALL_TOUCHED rasterization, exhaustive native DEM grid-cell mask and finite/nodata scan; not catalog boxes or approved AOI rectangles.",
        "mosaic_output_sha256": sha256_file(MOSAIC),
        "source_results": results,
        "radar_processing_started": False,
        "baseline_or_change_analysis_started": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--preflight", action="store_true")
    group.add_argument("--run-read-only-audit", action="store_true")
    args = parser.parse_args()
    try:
        result = no_content_preflight() if args.preflight else audit()
        target = PREFLIGHT if args.preflight else OUTPUT
        with target.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
        print(json.dumps({"status": result["status"], "sources_evaluated": len(result.get("source_results", []))}))
        return 0 if result["status"].startswith("pass_") else 20
    except IntakeError as exc:
        print(json.dumps({"status": "stopped_before_footprint_gate", "code": exc.code}))
        return 12


if __name__ == "__main__":
    raise SystemExit(main())
