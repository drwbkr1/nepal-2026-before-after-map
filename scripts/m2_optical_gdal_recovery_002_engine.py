#!/usr/bin/env python3
"""Exact GDAL header and QA-only optical pixel evaluation; no ArcPy import."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any

from m2_optical_gdal_recovery_002_adapter import TARGET_GRID, describe, tabulate_aoi, warp_target
from m2_optical_gdal_recovery_002_core import (
    ATTEMPT_ROOT, MATERIALIZED_ROOT, ROOT, PilotControlError, now_utc,
    read_json, sha256_file, write_new_json,
)
from optical_input_readiness_core import (
    RASTER_ROLES, decide_header_readiness, select_required_members, validate_pair_grids,
)
from optical_pixel_readiness_core_001 import (
    NODATA_CLASS, classify_pair_pixels, final_pixel_decision, measure_stable_registration,
)
from optical_processing_core import parse_l2a_scaling_metadata, processing_baseline_from_product_id
from pixel_qa_core import evaluate_grid_pair, load_contract as load_pixel_contract
from run_m2_optical_pixel_readiness_001 import bbox, grid_from_description


HEADER_CONTRACT = ROOT / "config/qa/optical-input-readiness-contract.json"
PIXEL_CONTRACT = ROOT / "config/qa/pixel-readiness-contract.json"
SETTINGS = ROOT / "config/qa/optical-pixel-readiness-contract-001.json"
AOI = ROOT / "config/aoi/approved-study-areas-epsg32645.json"


def inspect_one(source: dict[str, Any], contract: dict[str, Any],
                materialized_root: Path = MATERIALIZED_ROOT) -> tuple[dict[str, Any], dict[str, Path]]:
    """Recheck selected member bytes before any GDAL header access."""
    base = materialized_root / source["source_id"].casefold() / "materialization-001"
    manifest_path = base / "materialization-manifest.json"
    manifest = read_json(manifest_path)
    selected = select_required_members(manifest, contract)
    result: dict[str, Any] = {
        "source_id": source["source_id"], "inventory_status": selected["status"],
        "metadata_errors": list(selected["errors"]), "descriptions": {},
        "manifest_sha256": sha256_file(manifest_path),
    }
    if selected["status"] != "pass_inventory_only":
        return result, {}
    safe_root = base / source["exact_product_name"]
    safe_resolved = safe_root.resolve(strict=True)
    paths: dict[str, Path] = {}
    for role, item in selected["members"].items():
        relative = item["relative_path"]
        if PurePosixPath(relative).is_absolute() or any(part in {"", ".", ".."} for part in relative.split("/")):
            raise PilotControlError("gdal_selected_member_path_unsafe")
        path = safe_root.joinpath(*PurePosixPath(relative).parts)
        try:
            path.resolve(strict=True).relative_to(safe_resolved)
        except (OSError, ValueError) as exc:
            raise PilotControlError("gdal_selected_member_path_unsafe") from exc
        if not path.is_file() or path.stat().st_size != item["size_bytes"] or sha256_file(path) != item["sha256"]:
            raise PilotControlError("gdal_selected_member_identity_drift")
        paths[role] = path
    try:
        parsed = parse_l2a_scaling_metadata(paths["metadata_product"].read_text(encoding="utf-8"))
        result["metadata_errors"].extend(parsed["errors"])
        if (parsed.get("processing_baseline") != "05.12"
                or processing_baseline_from_product_id(source["exact_product_name"]) != "05.12"):
            result["metadata_errors"].append("processing_baseline_drift")
        result["metadata"] = parsed
    except (OSError, UnicodeError, ValueError) as exc:
        result["metadata_errors"].append(f"metadata_parse_failed_{type(exc).__name__}")
    for role in sorted(RASTER_ROLES):
        try:
            result["descriptions"][role] = describe(paths[role])
        except (OSError, RuntimeError, ValueError) as exc:
            result["metadata_errors"].append(f"{role}_header_open_failed_{type(exc).__name__}")
    return result, paths


def inspect_pair(sources: list[dict[str, Any]], contract: dict[str, Any] | None = None,
                 materialized_root: Path = MATERIALIZED_ROOT) -> tuple[dict[str, Any], list[dict[str, Path]]]:
    if [source.get("source_id") for source in sources] != ["M2-OPT-001", "M2-OPT-002"]:
        raise PilotControlError("gdal_header_pair_order_drift")
    contract = contract or read_json(HEADER_CONTRACT)
    observed = [inspect_one(source, contract, materialized_root) for source in sources]
    products = [entry[0] for entry in observed]
    paths = [entry[1] for entry in observed]
    grid_errors = validate_pair_grids(products[0]["descriptions"], products[1]["descriptions"], contract)
    decision = decide_header_readiness(
        {item["source_id"]: item["inventory_status"] for item in products},
        {item["source_id"]: item["metadata_errors"] for item in products}, grid_errors,
    )
    receipt = {
        "schema_version": "1.0", "receipt_id": "NEPAL-M2-OPTICAL-GDAL-RECOVERY-002-HEADER",
        "status": decision["status"], "checked_at_utc": now_utc(),
        "pair": ["M2-OPT-001", "M2-OPT-002"],
        "products": {item["source_id"]: item for item in products}, "decision": decision,
        "pixel_values_examined": False, "network_or_credential_action": False,
        "baseline_or_change_analysis": False,
    }
    return receipt, paths


def _write_classification(classes: Any, output: Path, grid: dict[str, Any]) -> None:
    from osgeo import gdal, osr  # type: ignore[import-not-found]

    if output.exists():
        raise PilotControlError("gdal_classification_collision")
    raster = gdal.GetDriverByName("GTiff").Create(
        str(output), grid["columns"], grid["rows"], 1, gdal.GDT_Int16,
        options=["COMPRESS=LZW", "TILED=YES", "BIGTIFF=IF_SAFER"],
    )
    if raster is None:
        raise PilotControlError("gdal_classification_create_failed")
    try:
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(32645)
        raster.SetProjection(srs.ExportToWkt())
        raster.SetGeoTransform((grid["xmin"], 20.0, 0.0, grid["ymax"], 0.0, -20.0))
        raster.GetRasterBand(1).SetNoDataValue(NODATA_CLASS)
        raster.GetRasterBand(1).WriteArray(classes)
        raster.FlushCache()
    finally:
        raster.Close()


def qa_pair(paths: list[dict[str, Path]], header: dict[str, Any],
            *, grid: dict[str, Any] = TARGET_GRID, aoi: dict[str, Any] | None = None,
            settings: dict[str, Any] | None = None, pixel_contract: dict[str, Any] | None = None,
            output_root: Path = ATTEMPT_ROOT) -> dict[str, Any]:
    """Run only the unchanged mask, AOI, grid, and B11 registration predicates."""
    import numpy as np

    if header.get("status") != "pass_header_readability_only" or header.get("pair") != ["M2-OPT-001", "M2-OPT-002"]:
        raise PilotControlError("gdal_header_gate_not_passing")
    if len(paths) != 2 or any(set(item) & {"SCL", "B11", "quality_classification"} !=
                              {"SCL", "B11", "quality_classification"} for item in paths):
        raise PilotControlError("gdal_pixel_member_paths_missing")
    aoi = aoi or read_json(AOI)
    settings = settings or read_json(SETTINGS)
    pixel_contract = pixel_contract or load_pixel_contract(PIXEL_CONTRACT)
    if (settings["analysis_grid"]["extent"] != {key: grid[key] for key in ("xmin", "ymin", "xmax", "ymax")}
            or settings["analysis_grid"]["columns"] != grid["columns"]
            or settings["analysis_grid"]["rows"] != grid["rows"]):
        raise PilotControlError("gdal_frozen_pixel_grid_drift")
    arrays = [
        {"SCL": warp_target(item["SCL"], "SCL", grid),
         "B11": warp_target(item["B11"], "B11", grid),
         "quality": warp_target(item["quality_classification"], "quality_classification", grid)}
        for item in paths
    ]
    classified = classify_pair_pixels(
        arrays[0]["SCL"], arrays[1]["SCL"], arrays[0]["quality"], arrays[1]["quality"],
        arrays[0]["B11"], arrays[1]["B11"],
    )
    features = {item["attributes"]["AOI_ID"]: item for item in aoi["features"]}
    required = {"AOI-OVERVIEW", "AOI-SOURCE", "AOI-UPPER-CORRIDOR"}
    if set(features) != required:
        raise PilotControlError("gdal_aoi_set_drift")
    aoi_results = [tabulate_aoi(classified["classes"], features[key], pixel_contract,
                                classified["unknown_scl_present"], grid) for key in sorted(required)]
    products = header["products"]
    before, after = products["M2-OPT-001"]["descriptions"], products["M2-OPT-002"]["descriptions"]
    grid_b11 = evaluate_grid_pair(grid_from_description(before["B11"]),
                                  grid_from_description(after["B11"]), pixel_contract)
    grid_scl = evaluate_grid_pair(grid_from_description(before["SCL"]),
                                  grid_from_description(after["SCL"]), pixel_contract)
    grid_status = "pass_qa_only" if grid_b11["status"] == grid_scl["status"] == "pass_qa_only" else "block"
    registration = measure_stable_registration(
        arrays[0]["B11"].astype(np.float64), arrays[1]["B11"].astype(np.float64),
        classified["pair_valid"], grid=grid,
        overview_bbox=bbox(features["AOI-OVERVIEW"]),
        exclusion_bboxes=[bbox(features["AOI-SOURCE"]), bbox(features["AOI-UPPER-CORRIDOR"])],
        settings=settings["registration"], pixel_contract=pixel_contract,
    )
    by_aoi = {item["aoi_id"]: item for item in aoi_results}
    localized = final_pixel_decision([by_aoi[key]["status"] for key in ("AOI-SOURCE", "AOI-UPPER-CORRIDOR")],
                                     grid_status, registration["status"])
    all_status = final_pixel_decision([item["status"] for item in aoi_results],
                                      grid_status, registration["status"])
    class_path = output_root / "pair_usability_classification_20m.tif"
    _write_classification(classified["classes"], class_path, grid)
    return {
        "schema_version": "1.0", "receipt_id": "NEPAL-M2-OPTICAL-GDAL-RECOVERY-002-PIXEL-QA",
        "status": all_status, "localized_source_corridor_status": localized,
        "aoi_metrics": aoi_results, "overview_full_coverage_claim": False,
        "grid_compatibility": {"status": grid_status, "B11": grid_b11, "SCL": grid_scl,
                               "fixed_target": grid},
        "registration": {key: value for key, value in registration.items() if key != "controls"},
        "classification_sha256": sha256_file(class_path),
        "completed_at_utc": now_utc(),
        "real_product_pixels_examined": True, "network_or_credential_action": False,
        "automatic_retry": False, "baseline_or_change_analysis": False,
        "derived_pixel_or_scientific_publication": False,
    }
