"""Conservative HyP3-specific pixel classifications under frozen M2 QA rules."""

from __future__ import annotations

import numpy as np

from pixel_qa_core import evaluate_aoi_coverage


DOCUMENTED_MASK_VALUES = frozenset((0, 1, 3, 5, 7, 9, 11, 13, 15,
                                    17, 19, 21, 23, 25, 27, 29, 31))
SLOPE_ONLY = frozenset((3, 9, 11))


def evaluate_window(
    *, aoi_id: str, aoi_area_m2: float, pixel_area_m2: float,
    footprint: np.ndarray, vv: np.ndarray, vh: np.ndarray, ls: np.ndarray,
    vv_nodata: float | None, vh_nodata: float | None, contract: dict,
) -> dict:
    """Count every AOI cell exactly once; only mask code 1 can be usable."""
    if (
        footprint.ndim != 2 or footprint.shape != vv.shape
        or footprint.shape != vh.shape or footprint.shape != ls.shape
        or not np.issubdtype(vv.dtype, np.number)
        or not np.issubdtype(vh.dtype, np.number)
        or not np.issubdtype(ls.dtype, np.integer)
        or not np.isfinite(aoi_area_m2) or aoi_area_m2 <= 0
        or not np.isfinite(pixel_area_m2) or pixel_area_m2 <= 0
    ):
        raise ValueError("rtc_pixel_array_or_area_invalid")
    inside = footprint.astype(bool)
    codes = ls.astype(np.int16, copy=False)
    documented = np.isin(codes, tuple(DOCUMENTED_MASK_VALUES))
    unknown = inside & ~documented
    untested = inside & (codes == 0)
    slope_only = inside & np.isin(codes, tuple(SLOPE_ONLY))
    both = inside & documented & ((codes & 4) != 0) & ((codes & 16) != 0)
    layover = inside & documented & ((codes & 4) != 0) & ~both
    shadow = inside & documented & ((codes & 16) != 0) & ~both
    candidate = inside & (codes == 1)
    finite = np.isfinite(vv) & np.isfinite(vh)
    if vv_nodata is not None and np.isfinite(vv_nodata):
        finite &= vv != vv_nodata
    if vh_nodata is not None and np.isfinite(vh_nodata):
        finite &= vh != vh_nodata
    nodata = candidate & ~finite
    nonpositive = candidate & finite & ((vv <= 0) | (vh <= 0))
    valid = candidate & finite & (vv > 0) & (vh > 0)
    reasons = {
        "provider_mask_untested": int(np.count_nonzero(untested)),
        "provider_slope_geometry_exclusion": int(np.count_nonzero(slope_only)),
        "provider_layover": int(np.count_nonzero(layover)),
        "provider_shadow": int(np.count_nonzero(shadow)),
        "provider_layover_and_shadow": int(np.count_nonzero(both)),
        "provider_mask_unknown": int(np.count_nonzero(unknown)),
        "radar_nodata_or_nonfinite": int(np.count_nonzero(nodata)),
        "radar_nonpositive_power": int(np.count_nonzero(nonpositive)),
    }
    covered_count = int(np.count_nonzero(inside))
    valid_count = int(np.count_nonzero(valid))
    if sum(reasons.values()) + valid_count != covered_count:
        raise ValueError("rtc_pixel_exclusions_do_not_partition_aoi")
    evaluated = evaluate_aoi_coverage(
        aoi_id=aoi_id, aoi_area_m2=aoi_area_m2,
        covered_area_m2=covered_count * pixel_area_m2,
        valid_area_m2=valid_count * pixel_area_m2,
        excluded_area_by_reason_m2={
            key: count * pixel_area_m2 for key, count in reasons.items() if count
        },
        contract=contract,
    )
    if reasons["provider_mask_unknown"] and evaluated["status"] == "pass_qa_only":
        evaluated["status"] = "defer"
        evaluated["limitations"].append("Undocumented provider mask values require review.")
    evaluated["covered_cell_count"] = covered_count
    evaluated["valid_cell_count"] = valid_count
    evaluated["excluded_cell_count_by_reason"] = reasons
    evaluated["unknown_provider_mask_value_present"] = bool(reasons["provider_mask_unknown"])
    evaluated["registration_measured"] = False
    evaluated["scientific_admission_authorized"] = False
    return evaluated
