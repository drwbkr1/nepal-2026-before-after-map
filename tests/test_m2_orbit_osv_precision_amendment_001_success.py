from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from derive_m2_acquisition_checkpoint import (  # noqa: E402
    current_orbit_remaining_sources_review_preparation,
)


def load(ref: str) -> dict:
    return json.loads((ROOT / ref).read_text(encoding="utf-8"))


class OrbitOsvPrecisionAmendmentSuccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.publication = load("records/readiness/m2-orbit-osv-precision-amendment-001-implementation-publication-gate.json")
        cls.preflight = load("records/readiness/m2-orbit-osv-precision-amendment-001-final-preflight.json")
        cls.result = load("records/acquisition/m2-orbit-osv-precision-amendment-001-local-validation.json")
        cls.terminal = load("records/readiness/m2-orbit-osv-precision-amendment-001-terminal-reconciliation.json")
        cls.intake = load("contracts/m2-orbit-intake.json")
        cls.milestone = load("contracts/milestone-002.json")
        cls.profile = load("records/project-control-profile.json")
        cls.goal = load("records/long-term-goal.json")

    def test_public_ci_preceded_the_single_local_action(self) -> None:
        self.assertEqual(self.publication["status"], "pass_public_one_second_implementation_before_local_validation")
        self.assertEqual(self.publication["github_actions"]["run_id"], 34056822125)
        self.assertEqual(self.publication["github_actions"]["conclusion"], "success")
        self.assertEqual(self.preflight["status"], "pass_no_network_ready_for_one_local_validation")
        self.assertFalse(self.preflight["assertions"]["local_semantic_validation_started"])
        self.assertEqual(self.result["assertions"]["local_validation_attempt_count"], 1)
        self.assertFalse(self.result["assertions"]["automatic_retry_performed"])
        self.assertFalse(self.result["assertions"]["network_requests_performed"])

    def test_exact_input_only_result_preserves_staging(self) -> None:
        identity = {
            "size_bytes": 639533,
            "sha256": "a72c93e500a1c09b62b4cd31889837c9d57ccc41542b16397ff9f2c0fccba3f4",
            "md5": "ca7f36b1892073c883c4cff5c0517b9c",
            "blake3": "ce824099fa812d6c229bd5bef2d4a70d7185d248f91ec3111ce557868ab1269b",
        }
        self.assertEqual(self.result["status"], "pass_exact_m2_orb_001_input_promoted_no_replace")
        self.assertEqual(self.result["result"]["source_identity_after"], identity)
        self.assertEqual(self.result["result"]["destination_identity"], identity)
        self.assertTrue(self.result["result"]["staging_preserved"])
        self.assertTrue(self.result["result"]["destination_created_without_replace"])
        self.assertEqual(self.result["result"]["inspection"]["status"], "pass_orbit_input_only")
        self.assertEqual(self.result["result"]["inspection"]["xml"]["endpoint_tolerance_seconds"], 1.0)
        self.assertEqual(self.result["result"]["inspection"]["xml"]["last_endpoint_shortfall_seconds"], 0.031829)

    def test_active_intake_preserves_failures_and_records_one_promotion(self) -> None:
        asset = self.intake["assets"][0]
        self.assertEqual(asset["state"], "promoted")
        self.assertIsNone(asset["failure"])
        self.assertEqual([attempt["outcome"] for attempt in asset["attempts"]], ["failed", "failed", "promoted"])
        self.assertEqual(
            asset["extensions"]["retained_failed_attempt_ids"],
            ["m2-orb-001-20260904t050937z-8ed21d05", "m2-orb-001-recovery-002-20260906t183804z-e5883324"],
        )
        self.assertEqual(self.intake["extensions"]["current_orbit_state_counts"], {"authorized": 3, "failed": 0, "promoted": 1})
        self.assertEqual([item["state"] for item in self.intake["assets"][1:]], ["authorized", "authorized", "authorized"])

    def test_control_plane_stops_before_other_orbit_requests(self) -> None:
        units = {item["id"]: item for item in self.milestone["units"]}
        self.assertEqual(units["M2-ORBIT-OSV-PRECISION-AMENDMENT-001-IMPLEMENTATION"]["status"], "complete")
        self.assertEqual(units["M2-ORBIT-OSV-PRECISION-AMENDMENT-001"]["status"], "complete")
        self.assertEqual(units["M2-ORBIT-OSV-PRECISION-AMENDMENT-001"]["disposition"], "pass")
        self.assertFalse(units["M2-ORBIT-ACQUIRE"]["gates"]["remaining_source_requests_authorized_by_current_amendment"])
        self.assertEqual(self.terminal["status"], "pass_exact_m2_orb_001_promoted_remaining_sources_review_required")
        self.assertFalse(self.terminal["assertions"]["other_orbit_source_requested"])
        self.assertFalse(self.terminal["assertions"]["scientific_result_established"])
        checkpoint = "M2-ORBIT-CONTINUATION-001-IMPLEMENTATION"
        self.assertEqual(self.profile["current_checkpoint"]["checkpoint_id"], checkpoint)
        self.assertEqual(self.goal["current_checkpoint"], checkpoint)
        self.assertTrue(current_orbit_remaining_sources_review_preparation(ROOT, {"promoted": 8}))


if __name__ == "__main__":
    unittest.main()
