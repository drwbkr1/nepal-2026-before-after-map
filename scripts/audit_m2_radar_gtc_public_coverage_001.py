#!/usr/bin/env python3
"""Compare approved catalog footprint and DEM tile boxes without reading raster data."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REF = "records/source-manifest.json"
SOURCE_APPROVAL_REF = "records/source-gates/source-manifest-approval.json"
DEM_REF = "records/source-gates/m2-dem-candidate-manifest.json"
DEM_APPROVAL_REF = "records/source-gates/m2-dem-amendment-approval.json"
DIAGNOSTIC_REF = "records/processing/m2-radar-gtc-input-compatibility-diagnostic-001-terminal-reconciliation.json"
OUTPUT_REF = "records/observations/m2-radar-gtc-public-coverage-audit-001.json"
SOURCE_ID = "M1-SRC-001"
EXPECTED_DEM_IDS = ("M2-DEM-001", "M2-DEM-002", "M2-DEM-003", "M2-DEM-004")
EARTH_RADIUS_METRES = 6_371_008.8


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def clip_polygon(polygon: list[tuple[float, float]], side: int, value: float) -> list[tuple[float, float]]:
    """Clip a lon/lat ring against one axis-aligned rectangle side."""
    if not polygon:
        return []
    axis = side // 2
    keep_greater = side in (0, 2)

    def inside(point: tuple[float, float]) -> bool:
        return point[axis] >= value if keep_greater else point[axis] <= value

    def crossing(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
        fraction = (value - a[axis]) / (b[axis] - a[axis])
        return (a[0] + fraction * (b[0] - a[0]), a[1] + fraction * (b[1] - a[1]))

    result = []
    previous = polygon[-1]
    for current in polygon:
        if inside(current):
            if not inside(previous):
                result.append(crossing(previous, current))
            result.append(current)
        elif inside(previous):
            result.append(crossing(previous, current))
        previous = current
    return result


def clip_to_box(polygon: list[tuple[float, float]], bbox: tuple[float, float, float, float]) -> list[tuple[float, float]]:
    west, south, east, north = bbox
    for side, value in enumerate((west, east, south, north)):
        polygon = clip_polygon(polygon, side, value)
    return polygon


def spherical_equal_area_km2(polygon: list[tuple[float, float]]) -> float:
    """Area under x=R*longitude and y=R*sin(latitude), on a sphere."""
    if len(polygon) < 3:
        return 0.0
    projected = [
        (EARTH_RADIUS_METRES * math.radians(lon), EARTH_RADIUS_METRES * math.sin(math.radians(lat)))
        for lon, lat in polygon
    ]
    double_area = sum(
        a[0] * b[1] - b[0] * a[1]
        for a, b in zip(projected, projected[1:] + projected[:1])
    )
    return abs(double_area) / 2_000_000.0


def calculate() -> dict[str, object]:
    source = json.loads((ROOT / SOURCE_REF).read_text(encoding="utf-8"))
    dem = json.loads((ROOT / DEM_REF).read_text(encoding="utf-8"))
    candidates = [item for item in source["records"] if item.get("source_id") == SOURCE_ID]
    if len(candidates) != 1:
        raise ValueError("exact source record missing or ambiguous")
    footprint = candidates[0]["footprint"]
    if footprint.get("type") != "Polygon" or len(footprint.get("coordinates", [])) != 1:
        raise ValueError("unexpected source footprint shape")
    ring = [tuple(map(float, point)) for point in footprint["coordinates"][0]]
    if ring[0] == ring[-1]:
        ring.pop()
    if len(ring) < 3:
        raise ValueError("source footprint is degenerate")
    records = dem["records"]
    if tuple(item["source_id"] for item in records) != EXPECTED_DEM_IDS:
        raise ValueError("DEM selection identity or order differs")
    boxes = [tuple(map(float, item["bbox_wgs84"])) for item in records]
    if boxes != [
        (84.0, 27.0, 85.0, 28.0), (85.0, 27.0, 86.0, 28.0),
        (84.0, 28.0, 85.0, 29.0), (85.0, 28.0, 86.0, 29.0),
    ]:
        raise ValueError("DEM tile boxes are not the frozen contiguous 2x2 grid")
    source_area = spherical_equal_area_km2(ring)
    overlap_area = sum(spherical_equal_area_km2(clip_to_box(ring, box)) for box in boxes)
    if source_area <= 0 or overlap_area > source_area:
        raise ValueError("invalid polygon-area result")
    return {
        "source_catalog_footprint_bounds_wgs84": [min(p[0] for p in ring), min(p[1] for p in ring), max(p[0] for p in ring), max(p[1] for p in ring)],
        "dem_tile_union_bounds_wgs84": [84.0, 27.0, 86.0, 29.0],
        "approx_source_catalog_area_km2": round(source_area, 1),
        "approx_catalog_intersection_area_km2": round(overlap_area, 1),
        "approx_catalog_intersection_percent": round(100.0 * overlap_area / source_area, 2),
        "approx_catalog_outside_dem_percent": round(100.0 * (1.0 - overlap_area / source_area), 2),
    }


def main() -> int:
    output = ROOT / OUTPUT_REF
    if output.exists():
        raise SystemExit("coverage-audit output collision")
    result = calculate()
    value = {
        "schema_version": "1.0",
        "observation_id": "NEPAL-M2-RADAR-GTC-PUBLIC-COVERAGE-AUDIT-001",
        "status": "local_public_metadata_coverage_observation_only",
        "source_id": SOURCE_ID,
        "input_bindings": [
            {"ref": ref, "sha256": sha256(ref)}
            for ref in (SOURCE_REF, SOURCE_APPROVAL_REF, DEM_REF, DEM_APPROVAL_REF, DIAGNOSTIC_REF)
        ],
        "method": "Clip the approved source catalog polygon against each of four nonoverlapping approved DEM STAC boxes in WGS84; estimate areas with the spherical equal-area cylindrical transform x=R*lon, y=R*sin(lat), R=6371008.8 m. This approximates catalog geometry, not raster pixel coverage.",
        "result": result,
        "official_method_context": {
            "esri_gtc_url": "https://doc.esri.com/en/arcgis-pro/latest/tool-reference/image-analyst/apply-geometric-terrain-correction.html",
            "esri_sar_faq_url": "https://doc.esri.com/en/arcgis-pro/latest/help/analysis/image-analyst/synthetic-aperture-radar-faq.html",
            "accessed_date_utc": "2026-09-22",
            "summary": "Esri states that GTC approximates elevation from metadata tie points where a DEM does not cover an area, while recommending a DEM wherever land is present. Esri separately states that radiometric terrain flattening can leave NoData outside DEM coverage. This audit does not establish which behavior caused the observed GTC error.",
        },
        "claim_boundary": {
            "actual_radar_pixel_coverage_established": False,
            "actual_dem_valid_pixel_coverage_established": False,
            "gtc_historical_root_cause_established": False,
            "radar_recovery_readiness_established": False,
            "new_dem_acquisition_or_processing_authorized": False,
            "new_radar_processing_attempt_authorized": False,
            "baseline_or_change_analysis_authorized": False,
            "scientific_result_established": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"status": value["status"], "result": result, "output": OUTPUT_REF}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
