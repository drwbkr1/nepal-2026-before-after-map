#!/usr/bin/env python3
"""Candidate-specific PB 05.12/05.13 controls; no project-data access on import.

This module never computes a cross-date reflectance difference or admits a
scientific baseline. The older PB 05.12 exact-pair reader remains unchanged.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from optical_processing_core import (
    parse_l2a_scaling_metadata,
    processing_baseline_from_product_id,
)


EXACT_PRODUCTS = {
    "M2-OPT-001": (
        "S2A_MSIL2A_20260824T050231_N0512_R119_T45RUM_20260824T115710.SAFE",
        "05.12",
    ),
    "M2-OPT-003": (
        "S2C_MSIL2A_20260921T045701_N0513_R119_T45RUM_20260921T102407.SAFE",
        "05.13",
    ),
}
VALID_SCL = frozenset({4, 5, 6})
KNOWN_SCL = frozenset(range(12))
TARGET_AOIS = ("AOI-SOURCE", "AOI-UPPER-CORRIDOR")
MINIMUM_BEFORE_USABLE = 0.80


def inspect_product_metadata(source_id: str, product_name: str, xml_text: str) -> dict[str, Any]:
    """Require the exact candidate name and its internally matching baseline.

    Scaling is read separately from each product. This is an identity/readiness
    check; no cross-baseline normalization is inferred from the offsets.
    """
    if source_id not in EXACT_PRODUCTS or product_name != EXACT_PRODUCTS[source_id][0]:
        raise ValueError("alternate_pair_exact_product_identity_mismatch")
    expected = EXACT_PRODUCTS[source_id][1]
    if processing_baseline_from_product_id(product_name) != expected:
        raise ValueError("alternate_pair_name_baseline_mismatch")
    parsed = parse_l2a_scaling_metadata(xml_text)
    if parsed["errors"] or parsed["processing_baseline"] != expected:
        raise ValueError("alternate_pair_internal_baseline_or_scaling_invalid")
    return {
        "source_id": source_id,
        "processing_baseline": expected,
        "quantification_value": parsed["quantification_value"],
        "offsets_by_band": parsed["offsets_by_band"],
        "dn_zero_is_nodata": True,
        "cross_baseline_harmonization": False,
    }


def single_date_usable_mask(scl: np.ndarray, quality: np.ndarray,
                            b11: np.ndarray) -> dict[str, Any]:
    """Apply the unchanged SCL, quality, and DN-zero exclusions to one date."""
    if scl.ndim != 2 or b11.shape != scl.shape or quality.shape != (3, *scl.shape):
        raise ValueError("alternate_pair_mask_shape_invalid")
    covered = ((scl != 255) & (b11 != 65535)
               & np.all(quality != 255, axis=0))
    unknown = covered & ~np.isin(scl, tuple(KNOWN_SCL))
    usable = (covered & np.isin(scl, tuple(VALID_SCL))
              & np.all(quality == 0, axis=0) & (b11 != 0))
    return {"covered": covered, "usable": usable,
            "unknown_scl_present": bool(np.any(unknown))}


def decide_before_screen(mask: dict[str, Any], aoi_masks: dict[str, np.ndarray]) -> dict[str, Any]:
    """Acquisition prerequisite only; 80% is not a scientific QA threshold."""
    if set(aoi_masks) != set(TARGET_AOIS):
        raise ValueError("alternate_pair_target_aoi_set_mismatch")
    covered = mask["covered"]
    usable = mask["usable"]
    if covered.shape != usable.shape or covered.dtype != np.bool_ or usable.dtype != np.bool_:
        raise ValueError("alternate_pair_mask_invalid")
    results: dict[str, Any] = {}
    for aoi_id in TARGET_AOIS:
        inside = aoi_masks[aoi_id]
        if inside.shape != covered.shape or inside.dtype != np.bool_:
            raise ValueError("alternate_pair_aoi_mask_invalid")
        count = int(np.count_nonzero(inside))
        if count == 0:
            raise ValueError("alternate_pair_aoi_empty")
        covered_count = int(np.count_nonzero(covered & inside))
        usable_count = int(np.count_nonzero(usable & inside))
        results[aoi_id] = {
            "aoi_cell_count": count,
            "covered_cell_count": covered_count,
            "usable_cell_count": usable_count,
            "usable_fraction_of_aoi": usable_count / count,
        }
    passed = (not mask["unknown_scl_present"] and all(
        item["usable_fraction_of_aoi"] >= MINIMUM_BEFORE_USABLE
        for item in results.values()
    ))
    return {
        "status": "pass_acquisition_prerequisite_only" if passed else "block",
        "aoi_results": results,
        "unknown_scl_present": mask["unknown_scl_present"],
        "threshold": MINIMUM_BEFORE_USABLE,
        "pair_pixel_qa_or_scientific_admission": False,
    }
