#!/usr/bin/env python3
"""Dependency-free decision core for projected raster and AOI pixel QA."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


STATUS_ORDER = {"pass_qa_only": 0, "defer": 1, "block": 2, "invalid": 3}


def load_contract(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_contract(value)
    if errors:
        raise ValueError("invalid pixel-QA contract: " + "; ".join(errors))
    return value


def validate_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if contract.get("contract_version") != "1.0" or contract.get("contract_id") != "NEPAL-PIXEL-QA-001":
        errors.append("contract identity differs")
    if contract.get("status") != "predeclared_before_product_pixels":
        errors.append("contract status must remain predeclared_before_product_pixels")
    if contract.get("analysis_crs", {}).get("wkid") != 32645:
        errors.append("analysis CRS must be EPSG:32645")
    semantics = contract.get("decision_semantics", {})
    if semantics.get("precedence") != ["invalid", "block", "defer", "pass_qa_only"]:
        errors.append("decision precedence differs")
    if semantics.get("pass_qa_only_creates_scientific_admission") is not False:
        errors.append("pixel QA must not create scientific admission")
    coverage = contract.get("aoi_coverage", {})
    partial = coverage.get("partial_evidence_defer_minimum")
    usable = coverage.get("usable_fraction_pass_minimum")
    full = coverage.get("full_coverage_pass_minimum")
    if not all(_finite_number(item) for item in (partial, usable, full)):
        errors.append("coverage thresholds must be finite numbers")
    elif not 0 < partial < usable <= full <= 1:
        errors.append("coverage thresholds are not conservatively ordered")
    grid = contract.get("grid_compatibility", {})
    if grid.get("required_wkid") != 32645 or grid.get("require_square_cells") is not True:
        errors.append("grid requirements must preserve projected square cells")
    registration = contract.get("registration", {})
    if registration.get("minimum_stable_control_pairs", 0) < 1:
        errors.append("registration requires stable controls")
    if registration.get("pass_max_rmse_pixels", 0) > registration.get("defer_max_rmse_pixels", -1):
        errors.append("registration pass threshold exceeds defer threshold")
    valid_scl = {int(item) for item in contract.get("optical_scl", {}).get("valid_surface_classes", {})}
    excluded_scl = {int(item) for item in contract.get("optical_scl", {}).get("excluded_classes", {})}
    if valid_scl != {4, 5, 6} or valid_scl & excluded_scl:
        errors.append("optical SCL valid classes must be distinct conservative surface classes")
    if set(range(12)) != valid_scl | excluded_scl:
        errors.append("optical SCL classes 0 through 11 must be classified")
    if not str(contract.get("claim_boundary", "")).startswith("Pixel QA can establish"):
        errors.append("claim boundary is missing")
    return errors


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def combine_statuses(statuses: list[str]) -> str:
    if not statuses or any(item not in STATUS_ORDER for item in statuses):
        return "invalid"
    return max(statuses, key=lambda item: STATUS_ORDER[item])


def classify_fraction(value: float, pass_minimum: float, defer_minimum: float) -> str:
    if not _finite_number(value) or value < 0 or value > 1:
        return "invalid"
    if value >= pass_minimum:
        return "pass_qa_only"
    if value >= defer_minimum:
        return "defer"
    return "block"


def evaluate_aoi_coverage(
    *,
    aoi_id: str,
    aoi_area_m2: float,
    covered_area_m2: float,
    valid_area_m2: float,
    excluded_area_by_reason_m2: dict[str, float],
    contract: dict[str, Any],
) -> dict[str, Any]:
    coverage = contract["aoi_coverage"]
    tolerance = coverage["area_consistency_tolerance_fraction"]
    precision = coverage["fraction_precision"]
    values = [aoi_area_m2, covered_area_m2, valid_area_m2, *excluded_area_by_reason_m2.values()]
    errors: list[str] = []
    if not aoi_id:
        errors.append("AOI ID is missing")
    if not all(_finite_number(item) and item >= 0 for item in values):
        errors.append("areas must be finite and nonnegative")
    if not errors and aoi_area_m2 <= 0:
        errors.append("AOI area must be positive")
    if not errors and covered_area_m2 > aoi_area_m2 * (1 + tolerance):
        errors.append("covered area exceeds AOI area beyond tolerance")
    if not errors and valid_area_m2 > covered_area_m2 * (1 + tolerance):
        errors.append("valid area exceeds covered area beyond tolerance")
    excluded_total = sum(excluded_area_by_reason_m2.values()) if not errors else 0.0
    if not errors:
        expected_excluded = max(0.0, covered_area_m2 - valid_area_m2)
        allowed_difference = max(aoi_area_m2 * tolerance, 1e-9)
        if abs(excluded_total - expected_excluded) > allowed_difference:
            errors.append("excluded areas do not reconcile with covered minus valid area")
    if errors:
        return {
            "aoi_id": aoi_id,
            "status": "invalid",
            "errors": errors,
            "scientific_admission_authorized": False,
        }

    coverage_fraction = min(1.0, covered_area_m2 / aoi_area_m2)
    usable_fraction = min(1.0, valid_area_m2 / aoi_area_m2)
    valid_within_coverage = valid_area_m2 / covered_area_m2 if covered_area_m2 else 0.0
    coverage_status = classify_fraction(
        coverage_fraction,
        coverage["full_coverage_pass_minimum"],
        coverage["partial_evidence_defer_minimum"],
    )
    usability_status = classify_fraction(
        usable_fraction,
        coverage["usable_fraction_pass_minimum"],
        coverage["partial_evidence_defer_minimum"],
    )
    status = combine_statuses([coverage_status, usability_status])
    limitations = []
    if coverage_status != "pass_qa_only":
        limitations.append("AOI coverage is incomplete for a full-area quantitative route.")
    if usability_status != "pass_qa_only":
        limitations.append("Usable AOI fraction is below the predeclared pass threshold.")
    if status == "pass_qa_only":
        limitations.append("Coverage and mask QA passed; change, interpretation, and attribution remain untested.")
    return {
        "aoi_id": aoi_id,
        "aoi_area_m2": aoi_area_m2,
        "covered_area_m2": covered_area_m2,
        "valid_area_m2": valid_area_m2,
        "coverage_fraction": round(coverage_fraction, precision),
        "usable_fraction_of_aoi": round(usable_fraction, precision),
        "valid_fraction_within_coverage": round(valid_within_coverage, precision),
        "excluded_area_by_reason_m2": excluded_area_by_reason_m2,
        "coverage_status": coverage_status,
        "usability_status": usability_status,
        "status": status,
        "limitations": limitations,
        "errors": [],
        "scientific_admission_authorized": False,
    }


def evaluate_grid_pair(before: dict[str, Any], after: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    rules = contract["grid_compatibility"]
    errors: list[str] = []
    for label, grid in (("before", before), ("after", after)):
        required = {"wkid", "cell_size_x", "cell_size_y", "origin_x", "origin_y", "xmin", "ymin", "xmax", "ymax", "rotation_degrees"}
        if set(grid) != required:
            errors.append(f"{label} grid fields differ")
            continue
        if not all(_finite_number(grid[key]) for key in required - {"wkid"}) or not isinstance(grid["wkid"], int):
            errors.append(f"{label} grid values are invalid")
            continue
        if grid["wkid"] != rules["required_wkid"]:
            errors.append(f"{label} grid is not EPSG:{rules['required_wkid']}")
        if grid["cell_size_x"] <= 0 or grid["cell_size_y"] <= 0:
            errors.append(f"{label} cell size is not positive")
        if rules["require_square_cells"] and abs(grid["cell_size_x"] - grid["cell_size_y"]) > rules["cell_size_absolute_tolerance_m"]:
            errors.append(f"{label} cells are not square")
        if rules["require_zero_rotation"] and abs(grid["rotation_degrees"]) > 1e-12:
            errors.append(f"{label} grid is rotated")
        if grid["xmax"] <= grid["xmin"] or grid["ymax"] <= grid["ymin"]:
            errors.append(f"{label} extent is invalid")
    if not errors:
        tolerance_m = rules["cell_size_absolute_tolerance_m"]
        if abs(before["cell_size_x"] - after["cell_size_x"]) > tolerance_m or abs(before["cell_size_y"] - after["cell_size_y"]) > tolerance_m:
            errors.append("before and after cell sizes differ")
        else:
            for axis in ("x", "y"):
                cell = before[f"cell_size_{axis}"]
                offset_pixels = (after[f"origin_{axis}"] - before[f"origin_{axis}"]) / cell
                if abs(offset_pixels - round(offset_pixels)) > rules["origin_alignment_tolerance_pixels"]:
                    errors.append(f"before and after {axis}-origins are not grid aligned")
        overlap_width = min(before["xmax"], after["xmax"]) - max(before["xmin"], after["xmin"])
        overlap_height = min(before["ymax"], after["ymax"]) - max(before["ymin"], after["ymin"])
        if rules["require_positive_extent_overlap"] and (overlap_width <= 0 or overlap_height <= 0):
            errors.append("before and after extents do not overlap")
    return {
        "status": "pass_qa_only" if not errors else "block",
        "errors": errors,
        "scientific_admission_authorized": False,
    }


def evaluate_registration(
    *,
    stable_control_pair_count: int | None,
    rmse_pixels: float | None,
    bias_x_pixels: float | None,
    bias_y_pixels: float | None,
    contract: dict[str, Any],
) -> dict[str, Any]:
    rules = contract["registration"]
    if stable_control_pair_count is None or rmse_pixels is None or bias_x_pixels is None or bias_y_pixels is None:
        return {
            "status": rules["not_run_status"],
            "finding": "Registration evidence has not been measured.",
            "scientific_admission_authorized": False,
        }
    if not isinstance(stable_control_pair_count, int) or stable_control_pair_count < 0:
        return {"status": "invalid", "finding": "Stable-control count is invalid.", "scientific_admission_authorized": False}
    metrics = [rmse_pixels, bias_x_pixels, bias_y_pixels]
    if not all(_finite_number(item) for item in metrics) or rmse_pixels < 0:
        return {"status": "invalid", "finding": "Registration metrics are invalid.", "scientific_admission_authorized": False}
    max_bias = max(abs(bias_x_pixels), abs(bias_y_pixels))
    if rmse_pixels > rules["defer_max_rmse_pixels"]:
        status = rules["above_defer_max_status"]
        finding = "Registration RMSE exceeds the predeclared maximum."
    elif (
        stable_control_pair_count >= rules["minimum_stable_control_pairs"]
        and rmse_pixels <= rules["pass_max_rmse_pixels"]
        and max_bias <= rules["pass_max_absolute_bias_pixels"]
    ):
        status = "pass_qa_only"
        finding = "Registration metrics meet the predeclared QA thresholds."
    else:
        status = "defer"
        finding = "Registration is measured but lacks controls or precision for a pass."
    return {
        "status": status,
        "stable_control_pair_count": stable_control_pair_count,
        "rmse_pixels": rmse_pixels,
        "bias_x_pixels": bias_x_pixels,
        "bias_y_pixels": bias_y_pixels,
        "finding": finding,
        "scientific_admission_authorized": False,
    }
