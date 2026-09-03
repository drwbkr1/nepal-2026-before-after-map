#!/usr/bin/env python3
"""Pure NumPy metrics and decisions for Copernicus DEM terrain QA."""

from __future__ import annotations

from typing import Any

import numpy as np


def _finite(values: np.ndarray) -> np.ndarray:
    return np.asarray(values, dtype=np.float64)[np.isfinite(values)]


def _percentile(values: np.ndarray, q: float) -> float:
    finite = _finite(values)
    if finite.size == 0:
        raise ValueError("metric contains no finite values")
    return float(np.percentile(finite, q))


def evaluate_tile(values: np.ndarray, thresholds: dict[str, Any]) -> dict[str, Any]:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 2 or min(array.shape) < 3:
        raise ValueError("tile must be a two-dimensional array at least 3 by 3")
    finite_mask = np.isfinite(array)
    finite = array[finite_mask]
    if finite.size == 0:
        return {
            "status": "block",
            "failures": ["no_finite_cells"],
            "deferrals": [],
            "metrics": {"total_cell_count": int(array.size), "finite_cell_count": 0},
        }

    center = array[1:-1, 1:-1]
    neighbor_mean = (
        array[:-2, 1:-1]
        + array[2:, 1:-1]
        + array[1:-1, :-2]
        + array[1:-1, 2:]
    ) / 4.0
    curvature = np.abs(center - neighbor_mean)
    curvature = curvature[np.isfinite(curvature)]
    block_curvature = float(thresholds["block_max_abs_local_curvature_m"])
    defer_curvature = float(thresholds["defer_abs_local_curvature_m"])
    spike_count = int(np.count_nonzero(curvature > defer_curvature))
    spike_fraction = float(spike_count / curvature.size) if curvature.size else 0.0

    blocks = np.stack(
        [array[:-1, :-1], array[1:, :-1], array[:-1, 1:], array[1:, 1:]],
        axis=0,
    )
    plateau = np.all(np.isfinite(blocks), axis=0) & np.all(blocks == blocks[0], axis=0)
    plateau_fraction = float(np.count_nonzero(plateau) / plateau.size)

    metrics = {
        "shape": [int(array.shape[0]), int(array.shape[1])],
        "total_cell_count": int(array.size),
        "finite_cell_count": int(finite.size),
        "nodata_or_nonfinite_cell_count": int(array.size - finite.size),
        "minimum_m": float(np.min(finite)),
        "maximum_m": float(np.max(finite)),
        "mean_m": float(np.mean(finite)),
        "standard_deviation_m": float(np.std(finite)),
        "zero_value_count": int(np.count_nonzero(finite == 0.0)),
        "exact_negative_32768_count": int(np.count_nonzero(finite == -32768.0)),
        "local_curvature_max_abs_m": float(np.max(curvature)) if curvature.size else None,
        "local_curvature_p999_abs_m": _percentile(curvature, 99.9) if curvature.size else None,
        "local_curvature_above_defer_count": spike_count,
        "local_curvature_above_defer_fraction": spike_fraction,
        "exact_2x2_plateau_fraction": plateau_fraction,
    }
    failures: list[str] = []
    deferrals: list[str] = []
    if metrics["nodata_or_nonfinite_cell_count"] > int(thresholds["block_nodata_or_nonfinite_count"]):
        failures.append("nodata_or_nonfinite_cells")
    if metrics["minimum_m"] < float(thresholds["block_minimum_elevation_m"]):
        failures.append("minimum_elevation_outside_physical_bound")
    if metrics["maximum_m"] > float(thresholds["block_maximum_elevation_m"]):
        failures.append("maximum_elevation_outside_physical_bound")
    if metrics["exact_negative_32768_count"]:
        failures.append("unmasked_negative_32768_sentinel")
    if metrics["local_curvature_max_abs_m"] is not None and metrics["local_curvature_max_abs_m"] > block_curvature:
        failures.append("gross_single_cell_curvature")
    if spike_fraction > float(thresholds["defer_local_curvature_fraction"]):
        deferrals.append("elevated_single_cell_curvature_fraction")
    if plateau_fraction > float(thresholds["defer_exact_2x2_plateau_fraction"]):
        deferrals.append("large_exact_plateau_fraction")
    status = "block" if failures else ("defer" if deferrals else "pass")
    return {"status": status, "failures": failures, "deferrals": deferrals, "metrics": metrics}


def evaluate_seam(
    first: np.ndarray,
    second: np.ndarray,
    orientation: str,
    thresholds: dict[str, Any],
) -> dict[str, Any]:
    a = np.asarray(first, dtype=np.float64)
    b = np.asarray(second, dtype=np.float64)
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("seam inputs must be two-dimensional")
    if orientation == "west_east":
        if a.shape[0] != b.shape[0] or min(a.shape[1], b.shape[1]) < 2:
            raise ValueError("west/east seam arrays are incompatible")
        a_inner, a_edge = a[:, -2], a[:, -1]
        b_edge, b_inner = b[:, 0], b[:, 1]
    elif orientation == "south_north":
        if a.shape[1] != b.shape[1] or min(a.shape[0], b.shape[0]) < 2:
            raise ValueError("south/north seam arrays are incompatible")
        a_inner, a_edge = a[1, :], a[0, :]
        b_edge, b_inner = b[-1, :], b[-2, :]
    else:
        raise ValueError("unsupported seam orientation")

    valid = np.isfinite(a_inner) & np.isfinite(a_edge) & np.isfinite(b_edge) & np.isfinite(b_inner)
    if not np.any(valid):
        return {"status": "block", "failures": ["no_finite_seam_samples"], "deferrals": [], "metrics": {"sample_count": 0}}
    a_inner, a_edge, b_edge, b_inner = (item[valid] for item in (a_inner, a_edge, b_edge, b_inner))
    seam_step = b_edge - a_edge
    expected_step = ((a_edge - a_inner) + (b_inner - b_edge)) / 2.0
    residual = seam_step - expected_step
    absolute = np.abs(residual)
    flag_level = float(thresholds["defer_residual_level_m"])
    metrics = {
        "sample_count": int(residual.size),
        "seam_step_median_m": float(np.median(seam_step)),
        "residual_signed_median_m": float(np.median(residual)),
        "residual_abs_median_m": float(np.median(absolute)),
        "residual_abs_p95_m": _percentile(absolute, 95.0),
        "residual_abs_p99_m": _percentile(absolute, 99.0),
        "residual_abs_max_m": float(np.max(absolute)),
        "residual_above_level_count": int(np.count_nonzero(absolute > flag_level)),
        "residual_above_level_fraction": float(np.count_nonzero(absolute > flag_level) / residual.size),
        "defer_residual_level_m": flag_level,
    }
    failures: list[str] = []
    deferrals: list[str] = []
    if metrics["residual_abs_max_m"] > float(thresholds["block_residual_abs_max_m"]):
        failures.append("gross_seam_discontinuity")
    if abs(metrics["residual_signed_median_m"]) > float(thresholds["defer_signed_median_abs_m"]):
        deferrals.append("systematic_seam_offset")
    if metrics["residual_abs_median_m"] > float(thresholds["defer_residual_abs_median_m"]):
        deferrals.append("elevated_median_seam_residual")
    if metrics["residual_abs_p95_m"] > float(thresholds["defer_residual_abs_p95_m"]):
        deferrals.append("elevated_p95_seam_residual")
    if metrics["residual_abs_p99_m"] > float(thresholds["defer_residual_abs_p99_m"]):
        deferrals.append("elevated_p99_seam_residual")
    if metrics["residual_above_level_fraction"] > float(thresholds["defer_residual_above_level_fraction"]):
        deferrals.append("frequent_large_seam_residuals")
    status = "block" if failures else ("defer" if deferrals else "pass")
    return {"status": status, "failures": failures, "deferrals": sorted(set(deferrals)), "metrics": metrics}


def combine_statuses(statuses: list[str]) -> str:
    if not statuses:
        raise ValueError("at least one status is required")
    if any(status == "block" for status in statuses):
        return "block"
    if any(status == "defer" for status in statuses):
        return "defer"
    if all(status == "pass" for status in statuses):
        return "pass"
    raise ValueError("unsupported status")
