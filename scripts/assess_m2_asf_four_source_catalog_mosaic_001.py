#!/usr/bin/env python3
"""Measure four-source ascending catalog coverage by date and AOI.

This is a local geometry screen only; it never reads source or RTC pixels.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from shapely.geometry import shape
from shapely.ops import unary_union

from assess_m2_radar_event_pair_catalog_001 import projected_area_km2, percentage


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "records" / "observations" / "m2-asf-four-source-catalog-mosaic-coverage-001-local.json"
INPUTS = (
    "records/source-manifest.json",
    "config/aoi/approved-study-areas.geojson",
    "config/qa/candidate-pair-plan.json",
    "records/observations/m2-radar-event-pair-catalog-triage-001.json",
)
BEFORE = ("M1-SRC-001", "M1-SRC-002")
AFTER = ("M1-SRC-004", "M1-SRC-005")


def main() -> None:
    if OUT.exists():
        raise RuntimeError("append-only four-source catalog observation already exists")
    bindings = [
        {"ref": ref, "sha256": hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()}
        for ref in INPUTS
    ]
    manifest = json.loads((ROOT / INPUTS[0]).read_text(encoding="utf-8"))
    aoi_file = json.loads((ROOT / INPUTS[1]).read_text(encoding="utf-8"))
    pair_plan = json.loads((ROOT / INPUTS[2]).read_text(encoding="utf-8"))
    triage = json.loads((ROOT / INPUTS[3]).read_text(encoding="utf-8"))
    route = next(pair for pair in pair_plan["pairs"] if pair["pair_id"] == "PAIR-S1-ASC-R085-IW")
    if tuple(route["before_source_ids"]) != BEFORE or tuple(route["after_source_ids"]) != AFTER:
        raise RuntimeError("frozen ascending route source IDs changed")
    sources = {
        row["source_id"]: shape(row["footprint"])
        for row in manifest["records"]
        if row["source_id"] in BEFORE + AFTER
    }
    aois = {feature["id"]: shape(feature["geometry"]) for feature in aoi_file["features"]}
    if set(sources) != set(BEFORE + AFTER) or set(aois) != {
        "AOI-OVERVIEW", "AOI-SOURCE", "AOI-UPPER-CORRIDOR"
    }:
        raise RuntimeError("source or approved AOI identities changed")
    if not all(geometry.is_valid and not geometry.is_empty for geometry in (*sources.values(), *aois.values())):
        raise RuntimeError("invalid or empty catalog geometry")
    before_union = unary_union([sources[source_id] for source_id in BEFORE])
    after_union = unary_union([sources[source_id] for source_id in AFTER])
    both_date_union = before_union.intersection(after_union)
    event_pair = sources["M1-SRC-002"].intersection(sources["M1-SRC-005"])
    prior = next(row for row in triage["pair_results"] if row["before_source_id"] == "M1-SRC-002")
    rows = []
    for aoi_id, aoi in aois.items():
        result = {
            "aoi_id": aoi_id,
            "aoi_area_km2_approx": round(projected_area_km2(aoi), 3),
            "before_date_catalog_union_percent": percentage(before_union.intersection(aoi), aoi),
            "after_date_catalog_union_percent": percentage(after_union.intersection(aoi), aoi),
            "both_date_catalog_union_percent": percentage(both_date_union.intersection(aoi), aoi),
            "event_pair_002_005_catalog_percent": percentage(event_pair.intersection(aoi), aoi),
            "frozen_full_coverage_99_percent_catalog_screen": percentage(both_date_union.intersection(aoi), aoi) >= 99.0,
        }
        if result["event_pair_002_005_catalog_percent"] != prior["aoi_catalog_pair_overlap_percent"][aoi_id]:
            raise RuntimeError("event-pair geometry no longer matches frozen triage")
        rows.append(result)
    receipt = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ASF-FOUR-SOURCE-CATALOG-MOSAIC-COVERAGE-001-LOCAL",
        "status": "offline_catalog_geometry_only_no_pixel_fitness",
        "observed_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "input_bindings": bindings,
        "source_ids_by_date": {"before": list(BEFORE), "after": list(AFTER)},
        "method": "WGS84 polygon union of exact catalog footprints within each acquisition date, then intersection of the two date unions; AOI area fractions use the frozen spherical equal-area cylindrical transform (R=6371008.8 m) from assess_m2_radar_event_pair_catalog_001.py. Same-date overlap contributes once. No resampling or pixel assessment.",
        "aoi_results": rows,
        "limits": {
            "provider_RTC_job_eligibility_verified": False,
            "actual_RTC_footprint_or_valid_pixels_verified": False,
            "layover_shadow_or_border_exclusions_verified": False,
            "registration_or_seam_verified": False,
            "source_or_derived_pixels_read": False,
            "scientific_admission_or_change_analysis": False,
            "new_source_or_method_adopted": False,
        },
    }
    with OUT.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(receipt, output, ensure_ascii=False, indent=2)
        output.write("\n")
    print("PASS: four-source catalog geometry assessed; no pixels read")


if __name__ == "__main__":
    main()
