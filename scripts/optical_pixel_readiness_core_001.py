#!/usr/bin/env python3
"""Portable decisions for the exact optical pixel-readiness attempt."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from pixel_qa_core import combine_statuses, evaluate_registration


NODATA_CLASS = -9999
VALID_CLASS = 1
VALID_SCL = {4, 5, 6}
KNOWN_SCL = set(range(12))
REASON_CODES = {
    **{100 + value: f"before_scl_{value}" for value in range(12)},
    **{200 + value: f"after_scl_{value}" for value in range(12)},
    190: "before_scl_unknown",
    290: "after_scl_unknown",
    300: "before_quality_classification",
    301: "after_quality_classification",
    400: "before_dn_zero",
    401: "after_dn_zero",
}


def validate_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if contract.get("contract_id") != "NEPAL-S2-PIXEL-READINESS-REAL-001":
        errors.append("contract identity differs")
    if contract.get("status") != "active_preobservation_exact_pair_one_attempt":
        errors.append("contract status differs")
    if contract.get("exact_pair") != {
        "before_source_id": "M1-SRC-010",
        "after_source_id": "M1-SRC-008",
        "pair_id": "PAIR-S2-RUM-R119",
    }:
        errors.append("exact optical pair differs")
    if contract.get("approved_aoi_ids") != ["AOI-OVERVIEW", "AOI-SOURCE", "AOI-UPPER-CORRIDOR"]:
        errors.append("approved AOIs differ")
    if contract.get("attempt", {}).get("attempt_id") != "optical-pixel-readiness-real-001":
        errors.append("attempt identity differs")
    if contract.get("attempt", {}).get("maximum_real_invocations") != 1:
        errors.append("real invocation limit differs")
    if contract.get("attempt", {}).get("automatic_retry_authorized") is not False:
        errors.append("automatic retry must remain prohibited")
    if contract.get("analysis_grid", {}).get("wkid") != 32645 or contract.get("analysis_grid", {}).get("cell_size_m") != 20.0:
        errors.append("analysis grid differs")
    mask = contract.get("mask", {})
    if mask.get("valid_scl_classes") != [4, 5, 6] or mask.get("quality_classification_clear_value") != 0:
        errors.append("conservative mask differs")
    registration = contract.get("registration", {})
    expected_registration = {
        "band_role": "B11",
        "candidate_grid_rows": 30,
        "candidate_grid_columns": 30,
        "patch_radius_pixels": 10,
        "search_radius_pixels": 2,
        "minimum_pair_valid_fraction": 0.8,
        "minimum_patch_standard_deviation_dn": 20.0,
        "minimum_correlation": 0.6,
        "event_aoi_exclusion_buffer_m": 1000.0,
    }
    for key, expected in expected_registration.items():
        if registration.get(key) != expected:
            errors.append(f"registration setting differs: {key}")
    boundary = contract.get("claim_boundary", {})
    if any(boundary.get(key) is not False for key in (
        "spectral_indices_computed", "candidate_change_polygons_created", "baseline_established",
        "change_established", "event_attribution_established", "scientific_admission_authorized",
    )):
        errors.append("claim boundary releases prohibited science")
    return errors


def classify_pair_pixels(
    before_scl: np.ndarray,
    after_scl: np.ndarray,
    before_quality: np.ndarray,
    after_quality: np.ndarray,
    before_b11: np.ndarray,
    after_b11: np.ndarray,
) -> dict[str, Any]:
    shape = before_scl.shape
    arrays = (after_scl, before_b11, after_b11)
    if any(item.shape != shape for item in arrays):
        raise ValueError("single-band target arrays differ in shape")
    if before_quality.shape != (3, *shape) or after_quality.shape != (3, *shape):
        raise ValueError("quality classification arrays must be three-band target grids")
    covered = (
        (before_scl != 255) & (after_scl != 255)
        & (before_b11 != 65535) & (after_b11 != 65535)
        & np.all(before_quality != 255, axis=0) & np.all(after_quality != 255, axis=0)
    )
    classes = np.full(shape, NODATA_CLASS, dtype=np.int16)
    remaining = covered.copy()
    for prefix, scl, base, unknown_code in (
        ("before", before_scl, 100, 190),
        ("after", after_scl, 200, 290),
    ):
        unknown = remaining & ~np.isin(scl, list(KNOWN_SCL))
        classes[unknown] = unknown_code
        remaining &= ~unknown
        for value in sorted(KNOWN_SCL - VALID_SCL):
            selected = remaining & (scl == value)
            classes[selected] = base + value
            remaining &= ~selected
    for quality, code in ((before_quality, 300), (after_quality, 301)):
        selected = remaining & np.any(quality != 0, axis=0)
        classes[selected] = code
        remaining &= ~selected
    for band, code in ((before_b11, 400), (after_b11, 401)):
        selected = remaining & (band == 0)
        classes[selected] = code
        remaining &= ~selected
    classes[remaining] = VALID_CLASS
    return {
        "classes": classes,
        "covered": covered,
        "pair_valid": classes == VALID_CLASS,
        "unknown_scl_present": bool(np.any(classes == 190) or np.any(classes == 290)),
        "reason_codes": dict(REASON_CODES),
    }


def _correlation(left: np.ndarray, right: np.ndarray, valid: np.ndarray, minimum_count: int) -> float | None:
    if int(valid.sum()) < minimum_count:
        return None
    x = left[valid].astype(np.float64)
    y = right[valid].astype(np.float64)
    x -= x.mean()
    y -= y.mean()
    denominator = float(np.sqrt(np.dot(x, x) * np.dot(y, y)))
    if not math.isfinite(denominator) or denominator <= 0:
        return None
    value = float(np.dot(x, y) / denominator)
    return value if math.isfinite(value) else None


def _parabolic(left: float | None, center: float, right: float | None) -> float:
    if left is None or right is None:
        return 0.0
    denominator = left - 2.0 * center + right
    if abs(denominator) < 1e-12:
        return 0.0
    return max(-0.5, min(0.5, 0.5 * (left - right) / denominator))


def measure_stable_registration(
    before: np.ndarray,
    after: np.ndarray,
    pair_valid: np.ndarray,
    *,
    grid: dict[str, float],
    overview_bbox: tuple[float, float, float, float],
    exclusion_bboxes: list[tuple[float, float, float, float]],
    settings: dict[str, Any],
    pixel_contract: dict[str, Any],
) -> dict[str, Any]:
    if before.shape != after.shape or before.shape != pair_valid.shape or before.ndim != 2:
        raise ValueError("registration arrays differ")
    rows, columns = before.shape
    radius = int(settings["patch_radius_pixels"])
    search = int(settings["search_radius_pixels"])
    margin = radius + search + 1
    candidate_rows = np.linspace(margin, rows - margin - 1, int(settings["candidate_grid_rows"]), dtype=int)
    candidate_columns = np.linspace(margin, columns - margin - 1, int(settings["candidate_grid_columns"]), dtype=int)
    required_pixels = int(math.ceil((2 * radius + 1) ** 2 * float(settings["minimum_pair_valid_fraction"])))
    accepted: list[dict[str, Any]] = []
    rejected = {"outside_overview": 0, "event_exclusion": 0, "insufficient_valid": 0, "low_texture": 0, "low_correlation": 0}
    buffer_m = float(settings["event_aoi_exclusion_buffer_m"])
    for row in candidate_rows:
        y = float(grid["ymax"]) - (float(row) + 0.5) * float(grid["cell_size_m"])
        for column in candidate_columns:
            x = float(grid["xmin"]) + (float(column) + 0.5) * float(grid["cell_size_m"])
            if not (overview_bbox[0] <= x <= overview_bbox[2] and overview_bbox[1] <= y <= overview_bbox[3]):
                rejected["outside_overview"] += 1
                continue
            if any(xmin - buffer_m <= x <= xmax + buffer_m and ymin - buffer_m <= y <= ymax + buffer_m for xmin, ymin, xmax, ymax in exclusion_bboxes):
                rejected["event_exclusion"] += 1
                continue
            base = before[row - radius:row + radius + 1, column - radius:column + radius + 1]
            base_valid = pair_valid[row - radius:row + radius + 1, column - radius:column + radius + 1]
            if int(base_valid.sum()) < required_pixels:
                rejected["insufficient_valid"] += 1
                continue
            correlations: dict[tuple[int, int], float | None] = {}
            for dy in range(-search, search + 1):
                for dx in range(-search, search + 1):
                    shifted = after[row + dy - radius:row + dy + radius + 1, column + dx - radius:column + dx + radius + 1]
                    shifted_valid = pair_valid[row + dy - radius:row + dy + radius + 1, column + dx - radius:column + dx + radius + 1]
                    valid = base_valid & shifted_valid
                    if int(valid.sum()) < required_pixels:
                        correlations[(dx, dy)] = None
                        continue
                    if float(np.std(base[valid])) < float(settings["minimum_patch_standard_deviation_dn"]) or float(np.std(shifted[valid])) < float(settings["minimum_patch_standard_deviation_dn"]):
                        correlations[(dx, dy)] = None
                    else:
                        correlations[(dx, dy)] = _correlation(base, shifted, valid, required_pixels)
            usable = [(value, dx, dy) for (dx, dy), value in correlations.items() if value is not None]
            if not usable:
                rejected["low_texture"] += 1
                continue
            peak, dx, dy = max(usable, key=lambda item: (item[0], -abs(item[1]) - abs(item[2]), -abs(item[1]), -abs(item[2])))
            if peak < float(settings["minimum_correlation"]):
                rejected["low_correlation"] += 1
                continue
            sub_x = _parabolic(correlations.get((dx - 1, dy)), peak, correlations.get((dx + 1, dy)))
            sub_y = _parabolic(correlations.get((dx, dy - 1)), peak, correlations.get((dx, dy + 1)))
            accepted.append({"x": x, "y": y, "shift_x_pixels": dx + sub_x, "shift_y_pixels": dy + sub_y, "correlation": peak})
    if accepted:
        shifts_x = np.array([item["shift_x_pixels"] for item in accepted], dtype=np.float64)
        shifts_y = np.array([item["shift_y_pixels"] for item in accepted], dtype=np.float64)
        rmse = float(np.sqrt(np.mean(shifts_x ** 2 + shifts_y ** 2)))
        bias_x = float(np.mean(shifts_x))
        bias_y = float(np.mean(shifts_y))
    else:
        rmse = bias_x = bias_y = None
    decision = evaluate_registration(
        stable_control_pair_count=len(accepted),
        rmse_pixels=rmse,
        bias_x_pixels=bias_x,
        bias_y_pixels=bias_y,
        contract=pixel_contract,
    )
    return {
        **decision,
        "candidate_count": int(len(candidate_rows) * len(candidate_columns)),
        "accepted_control_count": len(accepted),
        "rejected_counts": rejected,
        "controls": accepted,
        "method": "deterministic B11 normalized local cross-correlation outside buffered event AOIs",
    }


def final_pixel_decision(aoi_statuses: list[str], grid_status: str, registration_status: str) -> str:
    return combine_statuses([*aoi_statuses, grid_status, registration_status])
