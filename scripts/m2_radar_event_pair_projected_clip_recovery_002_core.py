"""Pure resource and grid guards for the approved event-pair projected clip."""

from __future__ import annotations

import math
from typing import Any


MAX_INTERMEDIATE_CELLS = 100_000_000
MAX_INTERMEDIATE_BYTES = 10_737_418_240
MAX_INTERMEDIATE_EXTENSION_M = 10_000.0
MAX_FINAL_BOUNDARY_DIFFERENCE_M = 100.0
TARGET = (272300.0, 3069230.0, 368820.0, 3150210.0)


def _valid_description(description: dict[str, Any]) -> bool:
    bounds = description.get("bounds")
    fields = ("wkid", "width", "height", "band_count", "cell_size_x", "cell_size_y")
    return (
        all(key in description for key in fields)
        and isinstance(bounds, list)
        and len(bounds) == 4
        and all(isinstance(value, (int, float)) and math.isfinite(value) for value in bounds)
        and bounds[0] < bounds[2]
        and bounds[1] < bounds[3]
        and all(isinstance(description[key], int) and description[key] > 0 for key in ("width", "height", "band_count"))
        and all(isinstance(description[key], (int, float)) and math.isfinite(description[key]) and description[key] > 0
                for key in ("cell_size_x", "cell_size_y"))
    )


def check_intermediate(description: dict[str, Any], *, target: tuple[float, float, float, float], cell_m: float,
                       bands: int, logical_bytes: int) -> list[str]:
    if not _valid_description(description):
        return ["intermediate_metadata_missing_or_invalid"]
    errors: list[str] = []
    bounds = description["bounds"]
    if description["wkid"] != 32645:
        errors.append("intermediate_crs_mismatch")
    if description["band_count"] != bands:
        errors.append("intermediate_band_count_mismatch")
    if abs(description["cell_size_x"] - cell_m) > 1e-6 or abs(description["cell_size_y"] - cell_m) > 1e-6:
        errors.append("intermediate_cell_size_mismatch")
    if description["width"] * description["height"] > MAX_INTERMEDIATE_CELLS:
        errors.append("intermediate_cell_ceiling_exceeded")
    if not isinstance(logical_bytes, int) or logical_bytes < 0 or logical_bytes > MAX_INTERMEDIATE_BYTES:
        errors.append("intermediate_byte_ceiling_exceeded")
    if any((target[0] - bounds[0] > MAX_INTERMEDIATE_EXTENSION_M,
            target[1] - bounds[1] > MAX_INTERMEDIATE_EXTENSION_M,
            bounds[2] - target[2] > MAX_INTERMEDIATE_EXTENSION_M,
            bounds[3] - target[3] > MAX_INTERMEDIATE_EXTENSION_M)):
        errors.append("intermediate_extent_ceiling_exceeded")
    return errors


def check_final(description: dict[str, Any], *, target: tuple[float, float, float, float], cell_m: float,
                bands: int, snap_origin: tuple[float, float]) -> list[str]:
    if not _valid_description(description):
        return ["final_metadata_missing_or_invalid"]
    errors: list[str] = []
    bounds = description["bounds"]
    if description["wkid"] != 32645:
        errors.append("final_crs_mismatch")
    if description["band_count"] != bands:
        errors.append("final_band_count_mismatch")
    if abs(description["cell_size_x"] - cell_m) > 1e-6 or abs(description["cell_size_y"] - cell_m) > 1e-6:
        errors.append("final_cell_size_mismatch")
    if any(abs(bounds[index] - target[index]) > MAX_FINAL_BOUNDARY_DIFFERENCE_M for index in range(4)):
        errors.append("final_target_boundary_mismatch")
    for index in (0, 1):
        offset = (bounds[index] - snap_origin[index]) / cell_m
        if abs(offset - round(offset)) > 1e-6:
            errors.append("final_snap_origin_mismatch")
            break
    return errors
