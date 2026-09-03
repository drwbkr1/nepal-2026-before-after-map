from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "prepare_radar_processing_contract", ROOT / "scripts/prepare_radar_processing_contract.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RadarProcessingContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(
            (ROOT / "config/qa/radar-baseline-processing-contract.json").read_text(encoding="utf-8")
        )

    def complete_observation(self) -> dict:
        return {
            "verified_sentinel_source_ids": self.contract["input_requirements"]["sentinel_assets"]["exact_source_ids"],
            "verified_dem_source_ids": self.contract["input_requirements"]["dem_assets"]["exact_source_ids"],
            "vertical_datum_route_status": "validated",
            "orbit_types_by_source": {
                source_id: "precise"
                for source_id in self.contract["input_requirements"]["sentinel_assets"]["exact_source_ids"]
            },
            "pixel_readiness_status": "pass_qa_only",
        }

    def test_tracked_contract_is_deterministic(self) -> None:
        rebuilt = MODULE.build_contract(self.contract["created_at_utc"])
        self.assertEqual(rebuilt, self.contract)
        self.assertEqual(MODULE.validate_contract(rebuilt), [])

    def test_current_no_pixel_state_defers(self) -> None:
        result = MODULE.evaluate_readiness(self.contract, {})
        self.assertEqual(result["status"], "defer")
        self.assertFalse(result["scientific_admission_authorized"])

    def test_exact_verified_inputs_can_become_processing_ready(self) -> None:
        result = MODULE.evaluate_readiness(self.contract, self.complete_observation())
        self.assertEqual(result["status"], "ready_for_controlled_processing")
        self.assertEqual(result["reasons"], [])
        self.assertFalse(result["scientific_admission_authorized"])

    def test_predicted_orbit_defers(self) -> None:
        observed = self.complete_observation()
        first_source = next(iter(observed["orbit_types_by_source"]))
        observed["orbit_types_by_source"][first_source] = "predicted"
        result = MODULE.evaluate_readiness(self.contract, observed)
        self.assertEqual(result["status"], "defer")
        self.assertTrue(any("predicted" in reason for reason in result["reasons"]))

    def test_unresolved_vertical_datum_defers(self) -> None:
        observed = self.complete_observation()
        observed["vertical_datum_route_status"] = "unresolved"
        result = MODULE.evaluate_readiness(self.contract, observed)
        self.assertEqual(result["status"], "defer")
        self.assertTrue(any("vertical datum" in reason for reason in result["reasons"]))

    def test_out_of_scope_source_is_invalid(self) -> None:
        observed = self.complete_observation()
        observed["verified_sentinel_source_ids"] = observed["verified_sentinel_source_ids"] + ["M1-SRC-999"]
        result = MODULE.evaluate_readiness(self.contract, observed)
        self.assertEqual(result["status"], "invalid")
        self.assertTrue(any("outside" in reason for reason in result["reasons"]))


if __name__ == "__main__":
    unittest.main()
