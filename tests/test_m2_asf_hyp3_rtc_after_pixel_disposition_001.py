"""Exact after-source full QA and partial-candidate decision boundaries."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m2_asf_hyp3_rtc_after_pixel_disposition_001 import (  # noqa: E402
    evaluate_after_aoi_results,
)
from pixel_qa_core import load_contract  # noqa: E402


CONTRACT = load_contract(ROOT / "config/qa/pixel-readiness-contract.json")


def result(aoi: str, usable: float, *, covered: float = 1.0,
           status: str = "defer", unknown: bool = False) -> dict:
    return {"aoi_id": aoi, "status": status,
            "aoi_area_m2": 100.0, "covered_area_m2": covered * 100.0,
            "valid_area_m2": usable * 100.0,
            "coverage_fraction": round(covered, 6),
            "usable_fraction_of_aoi": round(usable, 6),
            "unknown_provider_mask_value_present": unknown}


class AfterPixelDispositionTests(unittest.TestCase):
    def test_full_pass_never_admits_change(self):
        values = [result("AOI-SOURCE", .83, status="pass_qa_only"),
                  result("AOI-UPPER-CORRIDOR", .91, status="pass_qa_only")]
        decision = evaluate_after_aoi_results(values, CONTRACT)
        self.assertEqual(decision["status"], "pass_after_full_area_qa_only")
        self.assertFalse(decision["arcgis_map_released"])
        self.assertFalse(decision["baseline_or_change_admitted"])

    def test_defer_can_only_be_candidate_for_future_common_overlap(self):
        values = [result("AOI-SOURCE", .55),
                  result("AOI-UPPER-CORRIDOR", .76)]
        decision = evaluate_after_aoi_results(values, CONTRACT)
        self.assertEqual(decision["status"],
                         "defer_after_full_area_qa_partial_pair_candidate")
        self.assertEqual(decision["full_area_qa_status"], "defer")
        self.assertTrue(decision["partial_pair_candidate_pending_same_cell_overlap"])
        self.assertFalse(decision["common_valid_pair_fraction_measured"])

    def test_unknown_mask_or_below_floor_blocks_candidate(self):
        unknown = [result("AOI-SOURCE", .83, status="defer", unknown=True),
                   result("AOI-UPPER-CORRIDOR", .91, status="pass_qa_only")]
        below = [result("AOI-SOURCE", .19, status="block"),
                 result("AOI-UPPER-CORRIDOR", .76)]
        for values, expected in ((unknown, "defer_unknown_mask_no_pair_candidate"),
                                 (below, "block_after_pixel_qa_no_pair_candidate")):
            with self.subTest(values=values):
                decision = evaluate_after_aoi_results(values, CONTRACT)
                self.assertEqual(decision["status"], expected)
                self.assertFalse(decision["partial_pair_candidate_pending_same_cell_overlap"])

    def test_contract_drift_and_reordered_or_false_status_stop(self):
        values = [result("AOI-SOURCE", .55),
                  result("AOI-UPPER-CORRIDOR", .76)]
        changed = copy.deepcopy(CONTRACT)
        changed["aoi_coverage"]["partial_evidence_defer_minimum"] = .1
        with self.assertRaisesRegex(ValueError, "frozen_thresholds_changed"):
            evaluate_after_aoi_results(values, changed)
        with self.assertRaisesRegex(ValueError, "results_or_contract_invalid"):
            evaluate_after_aoi_results(values[::-1], CONTRACT)
        values[0]["status"] = "pass_qa_only"
        with self.assertRaisesRegex(ValueError, "result_contract_mismatch"):
            evaluate_after_aoi_results(values, CONTRACT)

    def test_rounded_20_percent_does_not_promote_raw_below_floor(self):
        values = [result("AOI-SOURCE", .1999999, status="block"),
                  result("AOI-UPPER-CORRIDOR", .76)]
        decision = evaluate_after_aoi_results(values, CONTRACT)
        self.assertEqual(decision["aoi_results"][0]["usable_fraction_of_aoi"], .2)
        self.assertEqual(decision["status"], "block_after_pixel_qa_no_pair_candidate")
        self.assertFalse(decision["partial_pair_candidate_pending_same_cell_overlap"])


if __name__ == "__main__":
    unittest.main()
