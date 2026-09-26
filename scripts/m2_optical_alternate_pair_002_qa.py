#!/usr/bin/env python3
"""Exact cross-baseline pair QA for display eligibility, never change analysis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from m2_optical_alternate_pair_002_core import EXACT_PRODUCTS, TARGET_AOIS
from m2_optical_alternate_pair_002_reader import AOI, HEADER_CONTRACT, inspect_materialized
from m2_optical_gdal_recovery_002_adapter import TARGET_GRID, tabulate_aoi, warp_target
from optical_input_readiness_core import decide_header_readiness, validate_pair_grids
from optical_pixel_readiness_core_001 import (
    classify_pair_pixels, final_pixel_decision, measure_stable_registration,
)
from pixel_qa_core import evaluate_grid_pair, load_contract as load_pixel_contract
from run_m2_optical_pixel_readiness_001 import bbox, grid_from_description


ROOT = Path(__file__).resolve().parents[1]
PIXEL_CONTRACT = ROOT / "config/qa/pixel-readiness-contract.json"
SETTINGS = ROOT / "config/qa/optical-pixel-readiness-contract-001.json"
SOURCE_ORDER = ("M2-OPT-001", "M2-OPT-003")


def inspect_exact_pair(bases: dict[str, Path]) -> tuple[dict[str, Any], dict[str, dict[str, Path]]]:
    if set(bases) != set(SOURCE_ORDER):
        raise ValueError("alternate_pair_source_set_invalid")
    contract = json.loads(HEADER_CONTRACT.read_text(encoding="utf-8"))
    observations = {source_id: inspect_materialized(source_id, bases[source_id],
                                                    contract=contract)
                    for source_id in SOURCE_ORDER}
    headers = {source_id: observations[source_id][0] for source_id in SOURCE_ORDER}
    paths = {source_id: observations[source_id][1] for source_id in SOURCE_ORDER}
    for source_id in SOURCE_ORDER:
        if headers[source_id]["exact_product_name"] != EXACT_PRODUCTS[source_id][0]:
            raise ValueError("alternate_pair_header_identity_invalid")
    grids = validate_pair_grids(headers[SOURCE_ORDER[0]]["descriptions"],
                                headers[SOURCE_ORDER[1]]["descriptions"], contract)
    decision = decide_header_readiness(
        {source_id: "pass_inventory_only" for source_id in SOURCE_ORDER},
        {source_id: [] for source_id in SOURCE_ORDER}, grids,
    )
    return {
        "status": decision["status"], "source_order": list(SOURCE_ORDER),
        "products": headers, "grid_errors": grids,
        "processing_baselines": ["05.12", "05.13"],
        "pixel_values_decoded": False,
    }, paths


def evaluate_pair(paths: dict[str, dict[str, Path]], header: dict[str, Any],
                  *, grid: dict[str, Any] = TARGET_GRID,
                  aoi: dict[str, Any] | None = None,
                  settings: dict[str, Any] | None = None,
                  pixel_contract: dict[str, Any] | None = None) -> dict[str, Any]:
    """Use frozen masks, geometry and registration; disclose PB method mismatch."""
    if header.get("status") != "pass_header_readability_only" or header.get("source_order") != list(SOURCE_ORDER):
        raise ValueError("alternate_pair_header_gate_not_passing")
    if set(paths) != set(SOURCE_ORDER) or grid != TARGET_GRID:
        raise ValueError("alternate_pair_source_or_grid_drift")
    needed = {"SCL", "B11", "quality_classification"}
    if any(set(paths[source_id]) < needed for source_id in SOURCE_ORDER):
        raise ValueError("alternate_pair_pixel_roles_missing")
    aoi = aoi or json.loads(AOI.read_text(encoding="utf-8"))
    settings = settings or json.loads(SETTINGS.read_text(encoding="utf-8"))
    pixel_contract = pixel_contract or load_pixel_contract(PIXEL_CONTRACT)
    frozen = settings["analysis_grid"]
    if (frozen["extent"] != {key: grid[key] for key in ("xmin", "ymin", "xmax", "ymax")}
            or frozen["rows"] != grid["rows"] or frozen["columns"] != grid["columns"]):
        raise ValueError("alternate_pair_frozen_grid_drift")
    arrays = {
        source_id: {
            "SCL": warp_target(paths[source_id]["SCL"], "SCL", grid),
            "B11": warp_target(paths[source_id]["B11"], "B11", grid),
            "quality": warp_target(paths[source_id]["quality_classification"],
                                   "quality_classification", grid),
        }
        for source_id in SOURCE_ORDER
    }
    before, after = (arrays[source_id] for source_id in SOURCE_ORDER)
    classified = classify_pair_pixels(before["SCL"], after["SCL"],
                                      before["quality"], after["quality"],
                                      before["B11"], after["B11"])
    features = {feature["attributes"]["AOI_ID"]: feature for feature in aoi["features"]}
    if set(features) != {"AOI-OVERVIEW", *TARGET_AOIS}:
        raise ValueError("alternate_pair_aoi_set_drift")
    by_aoi = {identifier: tabulate_aoi(classified["classes"], features[identifier],
                                      pixel_contract, classified["unknown_scl_present"], grid)
              for identifier in sorted(features)}
    descriptions = header["products"]
    before_header = descriptions[SOURCE_ORDER[0]]["descriptions"]
    after_header = descriptions[SOURCE_ORDER[1]]["descriptions"]
    grid_b11 = evaluate_grid_pair(grid_from_description(before_header["B11"]),
                                  grid_from_description(after_header["B11"]), pixel_contract)
    grid_scl = evaluate_grid_pair(grid_from_description(before_header["SCL"]),
                                  grid_from_description(after_header["SCL"]), pixel_contract)
    grid_status = "pass_qa_only" if grid_b11["status"] == grid_scl["status"] == "pass_qa_only" else "block"
    registration = measure_stable_registration(
        before["B11"].astype(np.float64), after["B11"].astype(np.float64),
        classified["pair_valid"], grid=grid,
        overview_bbox=bbox(features["AOI-OVERVIEW"]),
        exclusion_bboxes=[bbox(features[identifier]) for identifier in TARGET_AOIS],
        settings=settings["registration"], pixel_contract=pixel_contract,
    )
    localized = final_pixel_decision(
        [by_aoi[identifier]["status"] for identifier in TARGET_AOIS],
        grid_status, registration["status"])
    return {
        "status": localized, "source_order": list(SOURCE_ORDER),
        "aoi_metrics": by_aoi,
        "grid_compatibility": {"status": grid_status, "B11": grid_b11,
                               "SCL": grid_scl, "fixed_target": grid},
        "registration": {key: value for key, value in registration.items() if key != "controls"},
        "processing_baselines": ["05.12", "05.13"],
        "method_uncertainty": "PB 05.13 changed L2A no-data boundaries and cast-shadow classification; differences in valid-pixel masks are not mapped as landscape change.",
        "overview_full_coverage_claim": False,
        "cross_date_reflectance_or_index_change_computed": False,
        "baseline_admission_or_event_attribution": False,
        "derived_pixel_or_scientific_publication": False,
    }
