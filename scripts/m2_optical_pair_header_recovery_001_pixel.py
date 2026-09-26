#!/usr/bin/env python3
"""Run one distinct offline QA-only pixel attempt with unchanged optical predicates."""

from __future__ import annotations

import copy
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from m2_optical_pair_header_recovery_001_core import (
    HEADER_RECEIPT,
    PIXEL_RECEIPT as PUBLIC_RECEIPT,
    PIXEL_ROOT as ATTEMPT_ROOT,
    ROOT,
    PilotControlError,
    require_execution_release,
    sha256_file,
)
from m2_optical_pair_pilot_001_offline import PILOT_ROOT
from m2_optical_pair_pilot_001_transfer import now_utc, read_json, write_new_json
from optical_pixel_readiness_core_001 import (
    NODATA_CLASS, classify_pair_pixels, final_pixel_decision, measure_stable_registration,
)
from pixel_qa_core import evaluate_grid_pair, load_contract as load_pixel_contract
from run_m2_optical_pixel_readiness_001 import (
    bbox, grid_from_description, inventory, read_target, tabulate_classification,
)


ORIGINAL_CONTRACT = ROOT / "config/qa/optical-pixel-readiness-contract-001.json"


def frozen_execution_contract(source_ids: list[str]) -> dict[str, Any]:
    if source_ids != ["M2-OPT-001", "M2-OPT-002"]:
        raise PilotControlError("pilot_pixel_pair_order_drift")
    original = read_json(ORIGINAL_CONTRACT)
    frozen = copy.deepcopy(original)
    frozen["analysis_grid"].update(frozen["analysis_grid"]["extent"])
    frozen["exact_pair"] = {
        "before_source_id": source_ids[0],
        "after_source_id": source_ids[1],
        "pair_id": "PAIR-S2-RUM-R119-OPTICAL-PILOT-001",
    }
    frozen["attempt"] = {
        "attempt_id": "m2-optical-pair-header-receipt-recovery-001-pixel-qa-001",
        "maximum_real_invocations": 1,
        "automatic_retry_authorized": False,
        "external_attempt_root": str(ATTEMPT_ROOT),
        "external_receipt_ref": str(PUBLIC_RECEIPT),
        "collision_policy": "fail",
    }
    return frozen


def _source_members(source: Mapping[str, Any], product: Mapping[str, Any]) -> tuple[Path, dict[str, Path]]:
    materialized = PILOT_ROOT / "materialized" / source["source_id"].casefold() / "materialization-001"
    safe_root = materialized / source["exact_product_name"]
    if product["manifest_sha256"] != sha256_file(materialized / "materialization-manifest.json"):
        raise PilotControlError("pilot_pixel_manifest_identity_drift")
    selected = product["inventory"]
    if selected["status"] != "pass_inventory_only":
        raise PilotControlError("pilot_pixel_selected_inventory_not_passing")
    paths = {
        role: safe_root.joinpath(*PurePosixPath(selected["members"][role]["relative_path"]).parts)
        for role in ("SCL", "B11", "quality_classification")
    }
    for role, path in paths.items():
        item = selected["members"][role]
        if not path.is_file() or path.stat().st_size != item["size_bytes"] or sha256_file(path) != item["sha256"]:
            raise PilotControlError("pilot_pixel_member_identity_drift")
    return materialized, paths


def run_qa_pixels(sources: list[dict[str, Any]], *, arcpy: Any) -> dict[str, Any]:
    require_execution_release()
    if [item["source_id"] for item in sources] != ["M2-OPT-001", "M2-OPT-002"]:
        raise PilotControlError("pilot_pixel_pair_order_drift")
    if ATTEMPT_ROOT.exists() or PUBLIC_RECEIPT.exists():
        raise PilotControlError("pilot_pixel_attempt_consumed")
    header = read_json(HEADER_RECEIPT)
    if header.get("status") != "pass_header_readability_only" or header.get("pair") != ["M2-OPT-001", "M2-OPT-002"]:
        raise PilotControlError("pilot_header_gate_not_passing")
    original = frozen_execution_contract([item["source_id"] for item in sources])
    target = original["analysis_grid"]
    products = header["products"]
    roots_paths = [_source_members(source, products[source["source_id"]]) for source in sources]
    before_inventory = [inventory(root) for root, _ in roots_paths]
    ATTEMPT_ROOT.mkdir(parents=True, exist_ok=False)
    write_new_json(ATTEMPT_ROOT / "started.json", {
        "status": "started", "attempt_id": original["attempt"]["attempt_id"],
        "started_at_utc": now_utc(), "header_sha256": sha256_file(HEADER_RECEIPT),
        "old_attempt_reused": False, "automatic_retry": False,
    })
    try:
        receipt = _execute_pixels(sources, products, roots_paths, before_inventory, original, target, arcpy)
    except BaseException as exc:
        failure = {
            "schema_version": "1.0", "receipt_id": "NEPAL-M2-OPTICAL-PAIR-HEADER-RECEIPT-RECOVERY-001-PIXEL-QA",
            "status": "invalid", "attempt_id": original["attempt"]["attempt_id"],
            "completed_at_utc": now_utc(), "exception_type": type(exc).__name__,
            "exception_text_recorded": False, "automatic_retry": False,
            "claim_boundary": {"baseline_established": False, "change_established": False, "scientific_admission": False},
        }
        write_new_json(ATTEMPT_ROOT / "failure.json", failure)
        write_new_json(PUBLIC_RECEIPT, failure)
        return failure
    write_new_json(PUBLIC_RECEIPT, receipt)
    return receipt


def _execute_pixels(
    sources: list[dict[str, Any]],
    products: Mapping[str, Any],
    roots_paths: list[tuple[Path, dict[str, Path]]],
    before_inventory: list[list[dict[str, Any]]],
    original: Mapping[str, Any],
    target: Mapping[str, Any],
    arcpy: Any,
) -> dict[str, Any]:
    import numpy as np

    pixel_contract = load_pixel_contract(ROOT / original["inputs"]["pixel_readiness_ref"])
    aoi_path = ROOT / original["inputs"]["approved_aoi_ref"]
    aoi_json = read_json(aoi_path)
    arrays = []
    for _, paths in roots_paths:
        arrays.append({
            "SCL": read_target(arcpy, paths["SCL"], target, 255),
            "B11": read_target(arcpy, paths["B11"], target, 65535),
            "quality": read_target(arcpy, paths["quality_classification"], target, 255),
        })
    classified = classify_pair_pixels(
        arrays[0]["SCL"], arrays[1]["SCL"], arrays[0]["quality"], arrays[1]["quality"],
        arrays[0]["B11"], arrays[1]["B11"],
    )
    class_path = ATTEMPT_ROOT / "pair_usability_classification_20m.tif"
    raster = arcpy.NumPyArrayToRaster(
        classified["classes"], arcpy.Point(float(target["xmin"]), float(target["ymin"])),
        20.0, 20.0, NODATA_CLASS,
    )
    raster.save(str(class_path))
    arcpy.management.DefineProjection(str(class_path), arcpy.SpatialReference(32645))
    gdb = ATTEMPT_ROOT / "optical_pixel_qa.gdb"
    arcpy.management.CreateFileGDB(str(ATTEMPT_ROOT), gdb.name)
    aoi_fc = gdb / "ApprovedStudyAreas"
    arcpy.conversion.JSONToFeatures(str(aoi_path), str(aoi_fc))
    if arcpy.CheckExtension("Spatial") != "Available":
        raise PilotControlError("pilot_spatial_analyst_unavailable")
    arcpy.CheckOutExtension("Spatial")
    try:
        aoi_results = tabulate_classification(arcpy, aoi_fc, class_path, gdb / "AOIPairUsability", pixel_contract, classified["unknown_scl_present"])
    finally:
        arcpy.CheckInExtension("Spatial")
    ids = {item["aoi_id"] for item in aoi_results}
    if ids != {"AOI-OVERVIEW", "AOI-SOURCE", "AOI-UPPER-CORRIDOR"}:
        raise PilotControlError("pilot_aoi_metrics_incomplete")
    left = products[sources[0]["source_id"]]["descriptions"]
    right = products[sources[1]["source_id"]]["descriptions"]
    grid_b11 = evaluate_grid_pair(grid_from_description(left["B11"]), grid_from_description(right["B11"]), pixel_contract)
    grid_scl = evaluate_grid_pair(grid_from_description(left["SCL"]), grid_from_description(right["SCL"]), pixel_contract)
    grid_status = "pass_qa_only" if grid_b11["status"] == grid_scl["status"] == "pass_qa_only" else "block"
    by_id = {feature["attributes"]["AOI_ID"]: feature for feature in aoi_json["features"]}
    registration = measure_stable_registration(
        arrays[0]["B11"].astype(np.float64), arrays[1]["B11"].astype(np.float64), classified["pair_valid"],
        grid=target, overview_bbox=bbox(by_id["AOI-OVERVIEW"]),
        exclusion_bboxes=[bbox(by_id["AOI-SOURCE"]), bbox(by_id["AOI-UPPER-CORRIDOR"])],
        settings=original["registration"], pixel_contract=pixel_contract,
    )
    by_aoi = {item["aoi_id"]: item for item in aoi_results}
    localized_status = final_pixel_decision(
        [by_aoi[key]["status"] for key in ("AOI-SOURCE", "AOI-UPPER-CORRIDOR")],
        grid_status, registration["status"],
    )
    all_aoi_status = final_pixel_decision([item["status"] for item in aoi_results], grid_status, registration["status"])
    after_inventory = [inventory(root) for root, _ in roots_paths]
    unchanged = before_inventory == after_inventory
    if not unchanged:
        localized_status = all_aoi_status = "invalid"
    metrics = {
        "status": all_aoi_status, "localized_source_corridor_status": localized_status,
        "aoi_metrics": aoi_results,
        "grid_compatibility": {"status": grid_status, "B11": grid_b11, "SCL": grid_scl, "fixed_target": target},
        "registration": registration,
        "source_materializations_unchanged": unchanged,
    }
    metrics_path = ATTEMPT_ROOT / "metrics.json"
    write_new_json(metrics_path, metrics)
    outputs = {
        "classification_ref": str(class_path), "classification_sha256": sha256_file(class_path),
        "metrics_ref": str(metrics_path), "metrics_sha256": sha256_file(metrics_path),
    }
    write_new_json(ATTEMPT_ROOT / "completed.json", {
        "status": "complete", "decision_status": all_aoi_status,
        "localized_source_corridor_status": localized_status, "outputs": outputs,
    })
    return {
        "schema_version": "1.0", "receipt_id": "NEPAL-M2-OPTICAL-PAIR-HEADER-RECEIPT-RECOVERY-001-PIXEL-QA",
        "status": all_aoi_status, "localized_source_corridor_status": localized_status,
        "overview_full_coverage_claim": False,
        "attempt_id": original["attempt"]["attempt_id"], "completed_at_utc": now_utc(),
        "pair": original["exact_pair"], "aoi_metrics": aoi_results,
        "grid_compatibility": {"status": grid_status, "B11": grid_b11, "SCL": grid_scl, "fixed_target": target},
        "registration": {key: value for key, value in registration.items() if key != "controls"},
        "external_outputs": outputs,
        "activity": {"real_product_pixels_examined": True, "network_requests": False, "authentication": False, "source_materializations_unchanged": unchanged},
        "claim_boundary": {"pass_qa_only_is_not_baseline_admission": True, "baseline_established": False, "change_established": False, "event_attribution": False, "derived_pixel_or_scientific_publication": False},
        "automatic_retry": False,
    }
