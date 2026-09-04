from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from change_evidence_core import (  # noqa: E402
    classify_optical_sample,
    classify_radar_sample,
    evaluate_route_report,
    evaluate_synthesis,
    validate_contract,
)


CONTRACT_PATH = ROOT / "config/qa/change-evidence-contract.json"


def route_report(route_id: str = "PAIR-S1-ASC-R085-IW", candidates: int = 100, area_m2: float = 10000.0) -> dict:
    kind = "optical" if route_id == "PAIR-S2-RUM-R119" else "radar"
    profile = "OPTICAL-ROBUST-INDEX-DELTA-001" if kind == "optical" else "RADAR-ROBUST-DELTA-DB-001"
    return {
        "route_id": route_id,
        "route_kind": kind,
        "threshold_profile": profile,
        "input_qa_status": "pass_qa_only",
        "stable_control_zone_count": 30,
        "stable_valid_pixel_count": 10000,
        "stable_scale_valid": True,
        "coverage_fraction": 0.99,
        "usable_fraction": 0.8,
        "registration_rmse_pixels": 0.5,
        "registration_bias_abs_pixels": 0.5,
        "candidate_pixel_count": candidates,
        "candidate_area_m2": area_m2,
        "output_manifest_verified": True,
        "failed_history_preserved": True,
    }


class ChangeEvidenceCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def test_tracked_contract_is_valid_and_creates_no_authority(self) -> None:
        self.assertEqual(validate_contract(self.contract), [])
        self.assertTrue(all(value is False for value in self.contract["authority"].values()))

    def test_optical_metrics_remain_separate_observations(self) -> None:
        controls = {name: [-0.03, -0.01, 0.0, 0.01, 0.03] for name in self.contract["threshold_profiles"]["OPTICAL-ROBUST-INDEX-DELTA-001"]["metrics"]}
        result = classify_optical_sample({"dndvi_pre_minus_post": 0.25, "dnbr_pre_minus_post": 0.02, "dmndwi_post_minus_pre": 0.24}, controls, self.contract)
        self.assertEqual(result["status"], "candidate")
        self.assertEqual(set(result["classes"]), {"vegetation_index_decrease", "modified_water_index_increase"})
        self.assertNotIn("possible_debris_deposition", result["classes"])

    def test_radar_is_two_sided_and_retains_polarization_direction(self) -> None:
        controls = {"VV": [-0.4, -0.2, 0.0, 0.1, 0.3], "VH": [-0.3, -0.1, 0.0, 0.2, 0.4]}
        result = classify_radar_sample({"VV": 2.0, "VH": -2.1}, controls, self.contract)
        self.assertEqual(result["status"], "candidate")
        self.assertEqual(set(result["classes"]), {"radar_backscatter_increase", "radar_backscatter_decrease"})
        self.assertEqual(result["polarization_agreement"], "opposite_direction")

    def test_zero_stable_scale_defers_instead_of_tuning(self) -> None:
        controls = {"VV": [0.0] * 5, "VH": [0.0] * 5}
        result = classify_radar_sample({"VV": 2.0, "VH": 2.0}, controls, self.contract)
        self.assertEqual(result["status"], "defer")

    def test_route_can_pass_candidate_only_without_interpretation(self) -> None:
        result = evaluate_route_report(route_report(), self.contract)
        self.assertEqual(result["status"], "pass_candidate_only")
        self.assertTrue(result["candidate_admitted"])
        self.assertFalse(result["interpretation_created"])
        self.assertFalse(result["attribution_created"])

    def test_testable_zero_candidate_is_not_failure(self) -> None:
        result = evaluate_route_report(route_report(candidates=0, area_m2=0.0), self.contract)
        self.assertEqual(result["status"], "pass_no_candidate_observed")

    def test_insufficient_stable_reference_or_small_object_defers(self) -> None:
        report = route_report(candidates=40, area_m2=4000.0)
        report["stable_control_zone_count"] = 29
        result = evaluate_route_report(report, self.contract)
        self.assertEqual(result["status"], "defer")
        self.assertTrue(any("stable-reference" in item for item in result["reasons"]))
        self.assertTrue(any("minimum mapping unit" in item for item in result["reasons"]))

    def test_missing_failure_history_or_registration_blocks(self) -> None:
        report = route_report()
        report["failed_history_preserved"] = False
        report["registration_rmse_pixels"] = 0.6
        result = evaluate_route_report(report, self.contract)
        self.assertEqual(result["status"], "block")
        self.assertTrue(any("history" in item for item in result["reasons"]))
        self.assertTrue(any("registration" in item for item in result["reasons"]))

    def test_candidate_area_must_match_pixel_count_and_grid(self) -> None:
        result = evaluate_route_report(route_report(candidates=100, area_m2=5001.0), self.contract)
        self.assertEqual(result["status"], "invalid")
        self.assertTrue(any("inconsistent with pixel count" in item for item in result["reasons"]))

    def test_cross_sensor_overlap_is_coincidence_not_attribution(self) -> None:
        result = evaluate_synthesis([
            {"route_id": "PAIR-S1-ASC-R085-IW", "status": "pass_candidate_only"},
            {"route_id": "PAIR-S1-DESC-R121-IW", "status": "pass_no_candidate_observed"},
            {"route_id": "PAIR-S2-RUM-R119", "status": "pass_candidate_only"},
        ], 0.30, self.contract)
        self.assertEqual(result["status"], "spatially_coincident_candidates")
        self.assertTrue(result["multisensor"])
        self.assertFalse(result["attribution_established"])

    def test_disagreement_and_untestable_routes_remain_distinct(self) -> None:
        disagreement = evaluate_synthesis([
            {"route_id": "PAIR-S1-ASC-R085-IW", "status": "pass_candidate_only"},
            {"route_id": "PAIR-S1-DESC-R121-IW", "status": "pass_no_candidate_observed"},
            {"route_id": "PAIR-S2-RUM-R119", "status": "pass_candidate_only"},
        ], 0.10, self.contract)
        inconclusive = evaluate_synthesis([
            {"route_id": "PAIR-S1-ASC-R085-IW", "status": "defer"},
            {"route_id": "PAIR-S1-DESC-R121-IW", "status": "pass_no_candidate_observed"},
            {"route_id": "PAIR-S2-RUM-R119", "status": "pass_no_candidate_observed"},
        ], None, self.contract)
        self.assertEqual(disagreement["status"], "disagreement_retained")
        self.assertEqual(inconclusive["status"], "inconclusive")

    def test_synthesis_cannot_omit_a_route_disposition(self) -> None:
        result = evaluate_synthesis([
            {"route_id": "PAIR-S1-ASC-R085-IW", "status": "pass_candidate_only"},
            {"route_id": "PAIR-S2-RUM-R119", "status": "pass_candidate_only"},
        ], 0.5, self.contract)
        self.assertEqual(result["status"], "invalid")


if __name__ == "__main__":
    unittest.main()
