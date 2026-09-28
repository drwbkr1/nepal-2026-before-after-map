"""Build two visual-only VV dB arrays on an already verified common grid.

This pure function does not read provider files or write a map. Its caller must
establish source, rights, header, pixel and no-content execution gates.
"""

from __future__ import annotations

import math

import numpy as np

from m2_asf_hyp3_rtc_partial_pair_core_001 import (
    FROZEN_PARTIAL_FLOOR, _valid, assess_common_valid, gamma0_power_to_db,
)


AOI_IDS = ("AOI-SOURCE", "AOI-UPPER-CORRIDOR")
ARRAY_ROLES = ("before_vv", "before_vh", "before_mask",
               "after_vv", "after_vh", "after_mask")


def prepare_common_valid_vv_db(
    *, arrays: dict[str, np.ndarray], aoi_masks: dict[str, np.ndarray],
    aoi_areas_m2: dict[str, float], pixel_area_m2: float,
    before_nodata: tuple[float | None, float | None] = (None, None),
    after_nodata: tuple[float | None, float | None] = (None, None),
) -> dict:
    """Return only common-valid VV display pixels when both AOIs pass 20%.

    VH is required for cell validity but is not displayed. Arrays must already
    occupy the same native EPSG:32645, 10 m grid; this function never resamples.
    """
    if (not isinstance(arrays, dict) or set(arrays) != set(ARRAY_ROLES)
            or not isinstance(aoi_masks, dict) or set(aoi_masks) != set(AOI_IDS)
            or not isinstance(aoi_areas_m2, dict) or set(aoi_areas_m2) != set(AOI_IDS)
            or any(not isinstance(arrays[key], np.ndarray) or arrays[key].ndim != 2
                   for key in ARRAY_ROLES)
            or len({arrays[key].shape for key in ARRAY_ROLES}) != 1
            or any(not isinstance(aoi_masks[key], np.ndarray)
                   or aoi_masks[key].shape != arrays["before_vv"].shape
                   or aoi_masks[key].ndim != 2 for key in AOI_IDS)
            or any(type(aoi_areas_m2[key]) not in (int, float)
                   or not math.isfinite(aoi_areas_m2[key])
                   or aoi_areas_m2[key] <= 0 for key in AOI_IDS)
            or type(pixel_area_m2) not in (int, float)
            or not math.isfinite(pixel_area_m2) or pixel_area_m2 <= 0):
        raise ValueError("partial_pair_display_input_invalid")

    results = [assess_common_valid(
        aoi_id=aoi_id, aoi_footprint=aoi_masks[aoi_id],
        pixel_area_m2=pixel_area_m2, aoi_area_m2=aoi_areas_m2[aoi_id],
        partial_floor=FROZEN_PARTIAL_FLOOR,
        before_nodata=before_nodata, after_nodata=after_nodata, **arrays,
    ) for aoi_id in AOI_IDS]
    status = "pass_common_valid_for_local_partial_visual_only" if all(
        item["status"] == "pass_common_valid_for_local_partial_visual_only"
        for item in results
    ) else "block_partial_pair_display"
    output = {"status": status, "aoi_results": results,
              "resampling_performed": False, "registration_measured": False,
              "scientific_admission_authorized": False}
    if status != "pass_common_valid_for_local_partial_visual_only":
        return output

    union = np.logical_or(*(aoi_masks[key].astype(bool) for key in AOI_IDS))
    before_valid = _valid(arrays["before_vv"], arrays["before_vh"],
                          arrays["before_mask"], *before_nodata)
    after_valid = _valid(arrays["after_vv"], arrays["after_vh"],
                         arrays["after_mask"], *after_nodata)
    common = union & before_valid & after_valid
    output["before_vv_db"] = gamma0_power_to_db(arrays["before_vv"], common)
    output["after_vv_db"] = gamma0_power_to_db(arrays["after_vv"], common)
    output["common_valid_cells_in_union"] = int(np.count_nonzero(common))
    output["display_polarization"] = "VV"
    output["display_units"] = "gamma0 dB"
    return output
