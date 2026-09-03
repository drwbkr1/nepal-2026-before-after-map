#!/usr/bin/env python3
"""Portable decisions for materialized Sentinel-2 header readiness."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import math
import re
from pathlib import PurePosixPath
from typing import Any


ROLE_PATTERNS = {
    "metadata_product": "MTD_MSIL2A.xml",
    "metadata_tile": "GRANULE/*/MTD_TL.xml",
    "B02": "GRANULE/*/IMG_DATA/R10m/*_B02_10m.jp2",
    "B03": "GRANULE/*/IMG_DATA/R10m/*_B03_10m.jp2",
    "B04": "GRANULE/*/IMG_DATA/R10m/*_B04_10m.jp2",
    "B08": "GRANULE/*/IMG_DATA/R10m/*_B08_10m.jp2",
    "B11": "GRANULE/*/IMG_DATA/R20m/*_B11_20m.jp2",
    "B12": "GRANULE/*/IMG_DATA/R20m/*_B12_20m.jp2",
    "SCL": "GRANULE/*/IMG_DATA/R20m/*_SCL_20m.jp2",
    "quality_classification": "GRANULE/*/QI_DATA/MSK_CLASSI_B00.jp2",
}
TEN_METRE_ROLES = {"B02", "B03", "B04", "B08"}
TWENTY_METRE_ROLES = {"B11", "B12", "SCL"}
RASTER_ROLES = TEN_METRE_ROLES | TWENTY_METRE_ROLES | {"quality_classification"}
HEX64 = re.compile(r"[0-9a-f]{64}")


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def validate_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if contract.get("contract_id") != "NEPAL-S2-MATERIALIZED-INPUT-READINESS-001":
        errors.append("contract identity differs")
    if contract.get("status") != "predeclared_gate_deferred_no_real_safe":
        errors.append("contract must remain gate-deferred")
    if contract.get("analysis_crs", {}).get("wkid") != 32645:
        errors.append("analysis CRS differs")
    if contract.get("required_members", {}).get("role_patterns") != ROLE_PATTERNS:
        errors.append("required optical member patterns differ")
    route = contract.get("route", {})
    if route.get("before_source_id") != "M1-SRC-010" or route.get("after_source_id") != "M1-SRC-008":
        errors.append("exact optical source pair differs")
    if route.get("processing_baseline") != "05.12" or route.get("tile") != "45RUM" or route.get("relative_orbit") != 119:
        errors.append("optical route identity differs")
    if contract.get("prerequisites", {}).get("materialization_receipt_status") != "pass_materialization_only":
        errors.append("materialization prerequisite differs")
    if contract.get("execution_boundary", {}).get("network_requests") != "prohibited":
        errors.append("input readiness must remain offline")
    claim = contract.get("claim_boundary", {})
    if any(claim.get(key) is not False for key in (
        "pixel_values_examined",
        "pixel_usability_established",
        "baseline_established",
        "change_established",
        "scientific_admission_authorized",
    )):
        errors.append("contract invents downstream evidence")
    return errors


def select_required_members(
    external_manifest: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    if external_manifest.get("status") != "complete":
        errors.append("external materialization manifest is not complete")
    files = external_manifest.get("files")
    if not isinstance(files, list):
        return {"status": "block", "members": {}, "errors": ["external manifest files are missing"]}
    paths: dict[str, dict[str, Any]] = {}
    for item in files:
        relative = item.get("relative_path") if isinstance(item, dict) else None
        if not isinstance(relative, str):
            errors.append("external manifest contains a missing relative path")
            continue
        posix = PurePosixPath(relative)
        if posix.is_absolute() or any(part in {"", ".", ".."} for part in relative.split("/")):
            errors.append(f"external manifest contains an unsafe path: {relative}")
            continue
        folded = relative.casefold()
        if folded in paths:
            errors.append(f"external manifest contains a case-insensitive duplicate: {relative}")
            continue
        if not isinstance(item.get("size_bytes"), int) or item["size_bytes"] <= 0:
            errors.append(f"external manifest member is empty or has invalid size: {relative}")
        if not isinstance(item.get("sha256"), str) or not HEX64.fullmatch(item["sha256"]):
            errors.append(f"external manifest member lacks SHA-256: {relative}")
        paths[folded] = item
    selected: dict[str, dict[str, Any]] = {}
    patterns = contract["required_members"]["role_patterns"]
    for role, pattern in patterns.items():
        matches = [item for folded, item in paths.items() if fnmatch.fnmatchcase(folded, pattern.casefold())]
        if len(matches) != 1:
            errors.append(f"{role} requires exactly one member; observed {len(matches)}")
        else:
            selected[role] = matches[0]
    return {"status": "pass_inventory_only" if not errors else "block", "members": selected, "errors": errors}


def validate_raster_description(
    role: str,
    description: dict[str, Any],
    contract: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if role not in RASTER_ROLES:
        return [f"unknown raster role: {role}"]
    if description.get("format") != "JP2":
        errors.append(f"{role} format is not JP2")
    if description.get("wkid") != contract["analysis_crs"]["wkid"]:
        errors.append(f"{role} CRS is not EPSG:32645")
    if description.get("band_count") != 1:
        errors.append(f"{role} is not single-band")
    if not isinstance(description.get("width"), int) or description["width"] <= 0:
        errors.append(f"{role} width is invalid")
    if not isinstance(description.get("height"), int) or description["height"] <= 0:
        errors.append(f"{role} height is invalid")
    cell_width = description.get("cell_width")
    cell_height = description.get("cell_height")
    valid_cell_width = isinstance(cell_width, (int, float)) and not isinstance(cell_width, bool) and math.isfinite(cell_width) and cell_width > 0
    valid_cell_height = isinstance(cell_height, (int, float)) and not isinstance(cell_height, bool) and math.isfinite(cell_height) and cell_height > 0
    if not valid_cell_width:
        errors.append(f"{role} cell width is invalid")
    if not valid_cell_height:
        errors.append(f"{role} cell height is invalid")
    if role in TEN_METRE_ROLES:
        expected_cell = 10.0
    elif role in TWENTY_METRE_ROLES:
        expected_cell = 20.0
    else:
        expected_cell = None
    tolerance = float(contract["header_checks"]["cell_size_tolerance_m"])
    if expected_cell is not None:
        if not valid_cell_width or not math.isclose(float(cell_width), expected_cell, abs_tol=tolerance):
            errors.append(f"{role} cell width differs from {expected_cell:g} m")
        if not valid_cell_height or not math.isclose(float(cell_height), expected_cell, abs_tol=tolerance):
            errors.append(f"{role} cell height differs from {expected_cell:g} m")
    pixel_type = description.get("pixel_type")
    if role in TEN_METRE_ROLES | {"B11", "B12"} and pixel_type not in {"U16", "U12"}:
        errors.append(f"{role} pixel type is not unsigned Sentinel-2 reflectance DN")
    if role == "SCL" and pixel_type not in {"U8", "U16"}:
        errors.append("SCL pixel type is not unsigned categorical data")
    for key in ("xmin", "ymin", "xmax", "ymax"):
        value = description.get(key)
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            errors.append(f"{role} extent {key} is invalid")
    extent_values = [description.get(key) for key in ("xmin", "ymin", "xmax", "ymax")]
    if all(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) for value in extent_values):
        xmin, ymin, xmax, ymax = (float(value) for value in extent_values)
        if xmax <= xmin or ymax <= ymin:
            errors.append(f"{role} extent ordering is invalid")
        elif valid_cell_width and valid_cell_height and isinstance(description.get("width"), int) and isinstance(description.get("height"), int):
            extent_tolerance = float(contract["header_checks"]["extent_tolerance_m"])
            if not math.isclose(xmax - xmin, description["width"] * float(cell_width), abs_tol=extent_tolerance):
                errors.append(f"{role} width, cell size, and x extent are inconsistent")
            if not math.isclose(ymax - ymin, description["height"] * float(cell_height), abs_tol=extent_tolerance):
                errors.append(f"{role} height, cell size, and y extent are inconsistent")
    return errors


def validate_product_grid(
    descriptions: dict[str, dict[str, Any]],
    contract: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    for role in sorted(RASTER_ROLES):
        if role not in descriptions:
            errors.append(f"missing raster description for {role}")
        else:
            errors.extend(validate_raster_description(role, descriptions[role], contract))
    if errors:
        return errors
    reference = descriptions["B02"]
    tolerance = float(contract["header_checks"]["extent_tolerance_m"])
    for role in TEN_METRE_ROLES | TWENTY_METRE_ROLES:
        item = descriptions[role]
        for key in ("xmin", "ymin", "xmax", "ymax"):
            if not math.isclose(float(item[key]), float(reference[key]), abs_tol=tolerance):
                errors.append(f"{role} extent differs from B02 at {key}")
    return errors


def validate_pair_grids(
    before: dict[str, dict[str, Any]],
    after: dict[str, dict[str, Any]],
    contract: dict[str, Any],
) -> list[str]:
    errors = validate_product_grid(before, contract) + validate_product_grid(after, contract)
    if errors:
        return errors
    tolerance = float(contract["header_checks"]["extent_tolerance_m"])
    for role in sorted(TEN_METRE_ROLES | TWENTY_METRE_ROLES):
        left, right = before[role], after[role]
        for key in ("width", "height", "band_count", "wkid", "pixel_type"):
            if left[key] != right[key]:
                errors.append(f"before/after {role} differs at {key}")
        for key in ("cell_width", "cell_height", "xmin", "ymin", "xmax", "ymax"):
            if not math.isclose(float(left[key]), float(right[key]), abs_tol=tolerance):
                errors.append(f"before/after {role} differs at {key}")
    return errors


def decide_header_readiness(
    inventory_statuses: dict[str, str],
    metadata_errors: dict[str, list[str]],
    grid_errors: list[str],
) -> dict[str, Any]:
    reasons: list[str] = []
    for source_id, status in inventory_statuses.items():
        if status != "pass_inventory_only":
            reasons.append(f"{source_id} materialized member inventory did not pass")
    for source_id, errors in metadata_errors.items():
        reasons.extend(f"{source_id} metadata: {error}" for error in errors)
    reasons.extend(grid_errors)
    return {
        "status": "pass_header_readability_only" if not reasons else "block",
        "reasons": reasons,
        "pixel_values_examined": False,
        "pixel_usability_established": False,
        "baseline_established": False,
        "change_established": False,
        "scientific_admission_authorized": False,
    }
