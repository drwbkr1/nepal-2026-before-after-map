from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate_pair_plan.py"
SPEC = importlib.util.spec_from_file_location("validate_pair_plan", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
PLAN = json.loads((ROOT / "config/qa/candidate-pair-plan.json").read_text(encoding="utf-8"))
MANIFEST = json.loads((ROOT / "records/source-manifest.json").read_text(encoding="utf-8"))
APPROVAL = json.loads((ROOT / "records/source-gates/source-manifest-approval.json").read_text(encoding="utf-8"))
CONTRACT = json.loads((ROOT / "config/qa/pixel-readiness-contract.json").read_text(encoding="utf-8"))


class PairPlanTests(unittest.TestCase):
    def test_tracked_plan_and_hash_bindings_validate(self) -> None:
        self.assertEqual(MODULE.load_and_validate(ROOT / "config/qa/candidate-pair-plan.json", ROOT), PLAN)

    def test_three_independent_routes_use_all_eight_accepted_sources_once(self) -> None:
        self.assertEqual(len(PLAN["pairs"]), 3)
        source_ids = [
            source_id
            for pair in PLAN["pairs"]
            for source_id in [*pair["before_source_ids"], *pair["after_source_ids"]]
        ]
        self.assertEqual(len(source_ids), 8)
        self.assertEqual(len(source_ids), len(set(source_ids)))

    def test_source_roles_and_orbit_or_tile_metadata_match(self) -> None:
        self.assertEqual(MODULE.validate_plan(PLAN, MANIFEST, APPROVAL, CONTRACT), [])

    def test_synthetic_route_cannot_create_source_association(self) -> None:
        self.assertFalse(PLAN["decision_semantics"]["synthetic_inputs_create_source_association"])
        self.assertFalse(PLAN["decision_semantics"]["qa_pass_creates_scientific_admission"])

    def test_plan_creates_no_authority(self) -> None:
        self.assertEqual(PLAN["authority"]["mode"], "not_granted")
        self.assertEqual(PLAN["authority"]["authorized_actions"], [])

    def test_source_substitution_is_rejected(self) -> None:
        mutated = copy.deepcopy(PLAN)
        mutated["pairs"][0]["before_source_ids"][0] = "M1-SRC-007"
        self.assertTrue(any("outside" in error or "exactly once" in error for error in MODULE.validate_plan(mutated, MANIFEST, APPROVAL, CONTRACT)))

    def test_mixed_orbit_pair_is_rejected(self) -> None:
        mutated = copy.deepcopy(PLAN)
        mutated["pairs"][0]["after_source_ids"][0] = "M1-SRC-006"
        self.assertTrue(any("orbit" in error or "exactly once" in error for error in MODULE.validate_plan(mutated, MANIFEST, APPROVAL, CONTRACT)))

    def test_cell_size_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(PLAN)
        mutated["pairs"][2]["target_cell_size_m"] = 10.0
        self.assertTrue(any("cell size" in error for error in MODULE.validate_plan(mutated, MANIFEST, APPROVAL, CONTRACT)))

    def test_pixel_result_invention_is_rejected(self) -> None:
        mutated = copy.deepcopy(PLAN)
        mutated["pairs"][1]["pixel_status"] = "pass"
        self.assertTrue(any("invents" in error for error in MODULE.validate_plan(mutated, MANIFEST, APPROVAL, CONTRACT)))


if __name__ == "__main__":
    unittest.main()
