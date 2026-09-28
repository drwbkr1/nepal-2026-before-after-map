"""Pure disposition for exact after-scene event-AOI RTC pixel QA.

The frozen 80% full-area rule stays separate from the 20% *same-cell* pair
floor. This screen cannot release a map: common-valid overlap, rights, grid
agreement, registration and export have not been evaluated here.
"""

from __future__ import annotations

import math

from pixel_qa_core import classify_fraction, combine_statuses


SOURCE_ID = "M1-SRC-005"
EVENT_AOIS = ("AOI-SOURCE", "AOI-UPPER-CORRIDOR")


def evaluate_after_aoi_results(results: list[dict], contract: dict) -> dict:
    """Preserve exact full-area QA without promoting partial evidence to pass."""
    if (not isinstance(results, list) or len(results) != 2
            or [item.get("aoi_id") for item in results
                if isinstance(item, dict)] != list(EVENT_AOIS)
            or not isinstance(contract, dict)):
        raise ValueError("after_pixel_results_or_contract_invalid")
    try:
        coverage = contract["aoi_coverage"]
        full = coverage["usable_fraction_pass_minimum"]
        partial = coverage["partial_evidence_defer_minimum"]
        full_coverage = coverage["full_coverage_pass_minimum"]
    except (KeyError, TypeError):
        raise ValueError("after_pixel_contract_invalid") from None
    if (full != .8 or partial != .2 or full_coverage != .99):
        raise ValueError("after_pixel_frozen_thresholds_changed")
    statuses = []
    summaries = []
    unknown_any = False
    for item in results:
        status = item.get("status")
        unknown = item.get("unknown_provider_mask_value_present")
        if status not in {"pass_qa_only", "defer", "block"} or type(unknown) is not bool:
            raise ValueError("after_pixel_result_status_invalid")
        covered, usable = (item.get(key) for key in
                           ("coverage_fraction", "usable_fraction_of_aoi"))
        if (any(type(value) not in (int, float) or not math.isfinite(value)
                or not 0 <= value <= 1 for value in (covered, usable))
                or usable > covered + 1e-6):
            raise ValueError("after_pixel_result_fraction_invalid")
        expected = combine_statuses([
            classify_fraction(covered, full_coverage, partial),
            classify_fraction(usable, full, partial),
        ])
        if status != ("defer" if unknown and expected == "pass_qa_only" else expected):
            raise ValueError("after_pixel_result_contract_mismatch")
        statuses.append(status)
        unknown_any |= unknown
        summaries.append({"aoi_id": item["aoi_id"], "status": status,
                          "coverage_fraction": covered,
                          "usable_fraction_of_aoi": usable,
                          "unknown_provider_mask_value_present": unknown})
    full_status = combine_statuses(statuses)
    partial_candidate = (full_status != "block" and not unknown_any
                         and all(item["usable_fraction_of_aoi"] >= partial
                                 for item in summaries))
    if full_status == "block":
        decision_status = "block_after_pixel_qa_no_pair_candidate"
    elif unknown_any:
        decision_status = "defer_unknown_mask_no_pair_candidate"
    elif full_status == "pass_qa_only":
        decision_status = "pass_after_full_area_qa_only"
    else:
        decision_status = "defer_after_full_area_qa_partial_pair_candidate"
    return {
        "source_id": SOURCE_ID,
        "status": decision_status,
        "full_area_qa_status": full_status,
        "aoi_results": summaries,
        "partial_pair_candidate_pending_same_cell_overlap": partial_candidate,
        "common_valid_pair_fraction_measured": False,
        "first_source_qa_status_changed": False,
        "registration_measured": False,
        "arcgis_map_released": False,
        "baseline_or_change_admitted": False,
        "scientific_attribution_authorized": False,
    }
