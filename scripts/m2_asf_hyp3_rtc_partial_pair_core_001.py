"""Pure partial-visual overlap checks; never grants scientific admission."""

from __future__ import annotations

import math

import numpy as np

from m2_asf_hyp3_rtc_pixel_core_001 import DOCUMENTED_MASK_VALUES
from pixel_qa_core import evaluate_grid_pair

FROZEN_PARTIAL_FLOOR = 0.2


def check_pair_grids(before: dict, after: dict, contract: dict) -> dict:
    """Require the frozen projected grid contract, with no resampling."""
    result = evaluate_grid_pair(before, after, contract)
    if result["status"] != "pass_qa_only":
        return {"status": "block_grid", "errors": result["errors"],
                "scientific_admission_authorized": False}
    return {"status": "pass_grid_for_local_visual_only", "errors": [],
            "scientific_admission_authorized": False}


def _valid(vv: np.ndarray, vh: np.ndarray, mask: np.ndarray,
           vv_nodata: float | None, vh_nodata: float | None) -> np.ndarray:
    valid = (mask == 1) & np.isfinite(vv) & np.isfinite(vh) & (vv > 0) & (vh > 0)
    if vv_nodata is not None and math.isfinite(vv_nodata):
        valid &= vv != vv_nodata
    if vh_nodata is not None and math.isfinite(vh_nodata):
        valid &= vh != vh_nodata
    return valid


def assess_common_valid(
    *, aoi_id: str, aoi_footprint: np.ndarray,
    before_vv: np.ndarray, before_vh: np.ndarray, before_mask: np.ndarray,
    after_vv: np.ndarray, after_vh: np.ndarray, after_mask: np.ndarray,
    pixel_area_m2: float, aoi_area_m2: float, partial_floor: float,
    before_nodata: tuple[float | None, float | None] = (None, None),
    after_nodata: tuple[float | None, float | None] = (None, None),
) -> dict:
    """Count same-cell VV/VH validity on both dates inside one approved AOI."""
    arrays = (aoi_footprint, before_vv, before_vh, before_mask,
              after_vv, after_vh, after_mask)
    if (
        aoi_id not in {"AOI-SOURCE", "AOI-UPPER-CORRIDOR"}
        or any(not isinstance(item, np.ndarray) or item.ndim != 2 for item in arrays)
        or len({item.shape for item in arrays}) != 1
        or not np.issubdtype(before_mask.dtype, np.integer)
        or not np.issubdtype(after_mask.dtype, np.integer)
        or not all(np.issubdtype(item.dtype, np.number)
                   for item in (before_vv, before_vh, after_vv, after_vh))
        or not all(isinstance(value, (int, float)) and math.isfinite(value) and value > 0
                   for value in (pixel_area_m2, aoi_area_m2))
        or not isinstance(partial_floor, (int, float))
        or abs(partial_floor - FROZEN_PARTIAL_FLOOR) > 1e-12
    ):
        raise ValueError("partial_pair_input_invalid")
    inside = aoi_footprint.astype(bool)
    before_unknown = inside & ~np.isin(before_mask, tuple(DOCUMENTED_MASK_VALUES))
    after_unknown = inside & ~np.isin(after_mask, tuple(DOCUMENTED_MASK_VALUES))
    before_valid = inside & _valid(before_vv, before_vh, before_mask, *before_nodata)
    after_valid = inside & _valid(after_vv, after_vh, after_mask, *after_nodata)
    common = before_valid & after_valid
    common_cells = int(np.count_nonzero(common))
    fraction = min(1.0, common_cells * pixel_area_m2 / aoi_area_m2)
    unknown_cells = int(np.count_nonzero(before_unknown | after_unknown))
    if unknown_cells:
        status = "block_unknown_provider_mask"
    elif fraction < partial_floor:
        status = "block_common_valid_area_below_partial_floor"
    else:
        status = "pass_common_valid_for_local_partial_visual_only"
    return {
        "aoi_id": aoi_id, "status": status,
        "common_valid_cells": common_cells,
        "common_valid_fraction_of_aoi": round(fraction, 6),
        "unknown_mask_cells_either_date": unknown_cells,
        "before_valid_cells": int(np.count_nonzero(before_valid)),
        "after_valid_cells": int(np.count_nonzero(after_valid)),
        "registration_measured": False,
        "full_area_QA_status_changed": False,
        "scientific_admission_authorized": False,
    }


def gamma0_power_to_db(values: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """For local display only; excluded cells become NoData (NaN)."""
    if (values.shape != valid.shape or values.ndim != 2
            or not np.issubdtype(values.dtype, np.number)
            or valid.dtype != np.bool_
            or np.any(~np.isfinite(values[valid]))
            or np.any(values[valid] <= 0)):
        raise ValueError("partial_pair_db_input_invalid")
    output = np.full(values.shape, np.nan, dtype=np.float32)
    output[valid] = 10 * np.log10(values[valid].astype(np.float64))
    return output
