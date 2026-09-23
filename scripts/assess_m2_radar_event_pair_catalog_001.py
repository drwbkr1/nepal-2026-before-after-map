"""Local, metadata-only event-pair/AOI triage; does not admit raster pixels."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from shapely.geometry import box, shape
from shapely.ops import transform, unary_union


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "records/observations/m2-radar-event-pair-catalog-triage-001.json"
INPUTS = {
    "records/source-manifest.json": "6c67a1a6cb3411bd9ccab5f837e2c060757ddc5f1317f171bc5f62f9b1a22eef",
    "config/aoi/approved-study-areas.geojson": "17af33b60f59faef3a8f9cb2a44978a4e241e00d7329ee99076cce688073bd98",
    "records/source-gates/m2-dem-candidate-manifest.json": "1fb1b96f4bb3e42b77b4638d7ea36f13685eb29dec7e01a63c27acfc56786243",
    "records/observations/m2-radar-gtc-public-six-source-coverage-audit-002.json": "606ef9cf5c6ce4f884b7e28288bd5e4befefd3b7445dd0ba07a9e1f5db2c54d7",
    "records/processing/m2-radar-dem-fitness-comparison-001-terminal-reconciliation.json": "b69c9082a42184d2c26367659610e8afa1467aae8bf27a256e6d337c54bc1bd8",
}
PAIRS = (("M1-SRC-001", "M1-SRC-004"), ("M1-SRC-002", "M1-SRC-005"), ("M1-SRC-003", "M1-SRC-006"))
EARTH_RADIUS_M = 6371008.8


def projected_area_km2(geometry):
    return transform(
        lambda lon, lat, z=None: (
            EARTH_RADIUS_M * math.radians(lon),
            EARTH_RADIUS_M * math.sin(math.radians(lat)),
        ),
        geometry,
    ).area / 1_000_000


def percentage(part, whole):
    return round(100 * projected_area_km2(part) / projected_area_km2(whole), 3)


def main():
    bindings = []
    for ref, expected in INPUTS.items():
        actual = hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Input identity changed: {ref}")
        bindings.append({"ref": ref, "sha256": actual})

    manifest = json.loads((ROOT / "records/source-manifest.json").read_text(encoding="utf-8"))
    aoi_file = json.loads((ROOT / "config/aoi/approved-study-areas.geojson").read_text(encoding="utf-8"))
    dem_manifest = json.loads((ROOT / "records/source-gates/m2-dem-candidate-manifest.json").read_text(encoding="utf-8"))
    six_source_audit = json.loads((ROOT / "records/observations/m2-radar-gtc-public-six-source-coverage-audit-002.json").read_text(encoding="utf-8"))
    sources = {row["source_id"]: shape(row["footprint"]) for row in manifest["records"] if row["source_id"] in {sid for pair in PAIRS for sid in pair}}
    if len(sources) != 6 or len(dem_manifest["records"]) != 4:
        raise ValueError("Frozen source or DEM count changed")
    aois = {feature["id"]: shape(feature["geometry"]) for feature in aoi_file["features"]}
    if set(aois) != {"AOI-OVERVIEW", "AOI-SOURCE", "AOI-UPPER-CORRIDOR"}:
        raise ValueError("Approved AOIs changed")
    dem_boxes = unary_union([box(*row["bbox_wgs84"]) for row in dem_manifest["records"]])

    pair_results = []
    for before_id, after_id in PAIRS:
        pair_overlap = sources[before_id].intersection(sources[after_id])
        pair_results.append({
            "before_source_id": before_id,
            "after_source_id": after_id,
            "catalog_pair_overlap_area_km2_approx": round(projected_area_km2(pair_overlap), 3),
            "aoi_catalog_pair_overlap_percent": {
                aoi_id: percentage(pair_overlap.intersection(aoi), aoi)
                for aoi_id, aoi in aois.items()
            },
            "aoi_catalog_pair_and_dem_box_overlap_percent": {
                aoi_id: percentage(pair_overlap.intersection(aoi).intersection(dem_boxes), aoi)
                for aoi_id, aoi in aois.items()
            },
        })
    results_by_pair = {row["before_source_id"]: row for row in pair_results}
    dem_aoi_percent = {
        aoi_id: percentage(aoi.intersection(dem_boxes), aoi)
        for aoi_id, aoi in aois.items()
    }

    result = {
        "schema_version": "1.0",
        "observation_id": "NEPAL-M2-RADAR-EVENT-PAIR-CATALOG-TRIAGE-001",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "local_zero_decision_metadata_only_unpublished",
        "input_bindings": bindings,
        "method": "Intersect each exact before/after public catalog footprint pair with each approved AOI and the union of four approved DEM STAC boxes in WGS84; estimate area fractions by spherical equal-area cylindrical transform with R=6371008.8 m. This is catalog geometry, not raster or DEM valid-pixel coverage.",
        "approved_aoi_dem_box_overlap_percent": dem_aoi_percent,
        "pair_results": pair_results,
        "interpretation": {
            "regional_context_pair_001_004_source_or_upper_corridor_catalog_overlap": any(
                results_by_pair["M1-SRC-001"]["aoi_catalog_pair_overlap_percent"][aoi_id] > 0
                for aoi_id in ("AOI-SOURCE", "AOI-UPPER-CORRIDOR")
            ),
            "event_pair_002_005_source_and_upper_corridor_catalog_overlap_percent": min(
                results_by_pair["M1-SRC-002"]["aoi_catalog_pair_overlap_percent"][aoi_id]
                for aoi_id in ("AOI-SOURCE", "AOI-UPPER-CORRIDOR")
            ),
            "event_pair_003_006_source_catalog_overlap_percent": results_by_pair["M1-SRC-003"]["aoi_catalog_pair_overlap_percent"]["AOI-SOURCE"],
            "event_pair_003_006_upper_corridor_catalog_overlap_is_partial": 0 < results_by_pair["M1-SRC-003"]["aoi_catalog_pair_overlap_percent"]["AOI-UPPER-CORRIDOR"] < 100,
            "approved_dem_boxes_cover_all_approved_aois_in_catalog_geometry": all(value == 100.0 for value in dem_aoi_percent.values()),
            "existing_four_tiles_cover_all_six_full_swaths": all(row["approx_catalog_intersection_percent"] == 100.0 for row in six_source_audit["results"]),
            "m1_src_001_diagnostic_generalizes_to_event_pairs": False,
        },
        "limits": {
            "actual_event_pair_valid_radar_pixels_established": False,
            "actual_event_pair_valid_dem_pixels_established": False,
            "dem_sufficiency_for_full_swath_or_gtc_established": False,
            "event_pair_registration_or_change_established": False,
            "new_dem_tiles_selected_or_authorized": False,
            "event_pair_pixel_read_or_processing_authorized": False,
            "baseline_or_change_analysis_authorized": False,
            "scientific_claim_authorized": False,
        },
        "next_decision_frame": "One owner-reviewed, bounded event-pair AOI pixel/DEM-readiness method should be considered using exact M1-SRC-002/005 first, with explicit stop rules and no automatic admission. Decide separately whether full-swath terrain correction requires more DEM coverage; catalog AOI overlap alone cannot answer it.",
    }
    if (
        result["interpretation"]["regional_context_pair_001_004_source_or_upper_corridor_catalog_overlap"]
        or result["interpretation"]["event_pair_002_005_source_and_upper_corridor_catalog_overlap_percent"] != 100.0
        or result["interpretation"]["event_pair_003_006_source_catalog_overlap_percent"] != 100.0
        or not result["interpretation"]["approved_dem_boxes_cover_all_approved_aois_in_catalog_geometry"]
        or result["interpretation"]["existing_four_tiles_cover_all_six_full_swaths"]
    ):
        raise ValueError("Catalog geometry no longer supports the frozen triage description")
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(OUTPUT)


if __name__ == "__main__":
    main()
