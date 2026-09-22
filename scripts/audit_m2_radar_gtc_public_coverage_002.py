#!/usr/bin/env python3
"""Audit all six approved SAR catalog footprints against approved DEM tile boxes."""

from __future__ import annotations

import json

from scripts.audit_m2_radar_gtc_public_coverage_001 import (
    DEM_APPROVAL_REF,
    DEM_REF,
    DIAGNOSTIC_REF,
    ROOT,
    SOURCE_APPROVAL_REF,
    SOURCE_REF,
    clip_to_box,
    sha256,
    spherical_equal_area_km2,
)


OUTPUT_REF = "records/observations/m2-radar-gtc-public-six-source-coverage-audit-002.json"
SOURCE_IDS = tuple(f"M1-SRC-{number:03d}" for number in range(1, 7))
DEM_IDS = tuple(f"M2-DEM-{number:03d}" for number in range(1, 5))
DEM_BOXES = (
    (84.0, 27.0, 85.0, 28.0),
    (85.0, 27.0, 86.0, 28.0),
    (84.0, 28.0, 85.0, 29.0),
    (85.0, 28.0, 86.0, 29.0),
)


def calculate() -> list[dict[str, object]]:
    manifest = json.loads((ROOT / SOURCE_REF).read_text(encoding="utf-8"))
    dem_manifest = json.loads((ROOT / DEM_REF).read_text(encoding="utf-8"))
    sources = [row for row in manifest["records"] if row.get("source_id") in SOURCE_IDS]
    if tuple(row["source_id"] for row in sources) != SOURCE_IDS:
        raise ValueError("approved radar source identity or order differs")
    dem = dem_manifest["records"]
    if tuple(row["source_id"] for row in dem) != DEM_IDS:
        raise ValueError("approved DEM identity or order differs")
    if tuple(tuple(map(float, row["bbox_wgs84"])) for row in dem) != DEM_BOXES:
        raise ValueError("approved DEM boxes differ")

    result = []
    for source in sources:
        footprint = source["footprint"]
        if footprint.get("type") != "Polygon" or len(footprint.get("coordinates", [])) != 1:
            raise ValueError("unexpected source footprint shape")
        ring = [tuple(map(float, point)) for point in footprint["coordinates"][0]]
        if len(ring) < 4 or ring[0] != ring[-1]:
            raise ValueError("source footprint ring is not closed")
        ring.pop()
        source_area = spherical_equal_area_km2(ring)
        overlap_area = sum(spherical_equal_area_km2(clip_to_box(ring, box)) for box in DEM_BOXES)
        if not 0 < source_area or not 0 <= overlap_area <= source_area:
            raise ValueError("invalid source or overlap area")
        result.append({
            "source_id": source["source_id"],
            "event_role": source["event_role"],
            "analysis_role": source["proposed_disposition"]["analysis_role"],
            "approved_aoi_catalog_bbox_intersections": source["coverage_status"]["approved_aoi_intersections"],
            "approx_catalog_footprint_area_km2": round(source_area, 1),
            "approx_catalog_intersection_area_km2": round(overlap_area, 1),
            "approx_catalog_intersection_percent": round(100 * overlap_area / source_area, 2),
            "approx_catalog_outside_dem_percent": round(100 * (1 - overlap_area / source_area), 2),
        })
    return result


def main() -> int:
    output = ROOT / OUTPUT_REF
    if output.exists():
        raise SystemExit("six-source coverage audit output collision")
    value = {
        "schema_version": "1.0",
        "observation_id": "NEPAL-M2-RADAR-GTC-PUBLIC-SIX-SOURCE-COVERAGE-AUDIT-002",
        "status": "local_public_metadata_coverage_observation_only",
        "input_bindings": [
            {"ref": ref, "sha256": sha256(ref)}
            for ref in (SOURCE_REF, SOURCE_APPROVAL_REF, DEM_REF, DEM_APPROVAL_REF, DIAGNOSTIC_REF)
        ],
        "method": "Clip each of six approved radar catalog polygons against the four approved nonoverlapping DEM STAC boxes in WGS84; estimate area via the spherical equal-area cylindrical transform. This is catalog geometry, not raster-pixel coverage.",
        "results": calculate(),
        "interpretation_boundary": "All six catalog polygons extend beyond the approved DEM boxes. This does not establish actual valid-pixel coverage, GTC fitness, the ERROR 000425 cause, or a suitable source-order or DEM remedy.",
        "claim_boundary": {
            "actual_radar_pixel_coverage_established": False,
            "actual_dem_valid_pixel_coverage_established": False,
            "gtc_historical_root_cause_established": False,
            "radar_recovery_readiness_established": False,
            "new_source_order_or_dem_action_authorized": False,
            "new_radar_processing_attempt_authorized": False,
            "baseline_or_change_analysis_authorized": False,
            "scientific_result_established": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"status": value["status"], "source_count": len(value["results"]), "output": OUTPUT_REF}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
