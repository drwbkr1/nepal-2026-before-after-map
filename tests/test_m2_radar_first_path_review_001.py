from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_REF = "contracts/milestone-002-radar-first-path-001-proposal.json"
BUNDLE_REF = "reviews/m2-radar-first-path-001/review-bundle.json"
CONTRACT_REF = "reviews/m2-radar-first-path-001/review-contract.json"
BLANK_REF = "reviews/m2-radar-first-path-001/blank-response.json"
READINESS_REF = "records/readiness/m2-radar-first-path-001-review-readiness.json"
ANALYSIS_REF = "records/readiness/m2-post-optical-route-analysis-001.json"


def load(ref: str) -> dict:
    return json.loads((ROOT / ref).read_text(encoding="utf-8"))


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


class RadarFirstPathReview001Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.analysis = load(ANALYSIS_REF)
        cls.proposal = load(PROPOSAL_REF)
        cls.bundle = load(BUNDLE_REF)
        cls.contract = load(CONTRACT_REF)
        cls.blank = load(BLANK_REF)
        cls.readiness = load(READINESS_REF)
        cls.milestone = load("contracts/milestone-002.json")
        cls.profile = load("records/project-control-profile.json")
        cls.goal = load("records/long-term-goal.json")

    def test_live_analysis_preserves_terminal_optical_result(self) -> None:
        self.assertEqual(self.analysis["status"], "needs_owner_route_decision")
        self.assertEqual(self.analysis["reconciliation_outcome"], "drift_requires_normative_path_choice")
        self.assertIn("terminal BLOCK", " ".join(self.analysis["findings"]))
        self.assertEqual(self.analysis["assertions"]["human_decision_count"], 0)
        self.assertFalse(self.analysis["assertions"]["real_product_pixels_read"])
        self.assertFalse(self.analysis["assertions"]["external_data_mutated"])

    def test_proposal_is_control_only_and_keeps_future_gates_separate(self) -> None:
        self.assertEqual(self.proposal["status"], "proposed_not_authorized")
        self.assertEqual(self.proposal["recommended_decision"], "approve_radar_first_control_path")
        prohibited = " ".join(self.proposal["does_not_authorize"])
        for phrase in ("optical retry", "DEM conversion", "orbit catalogue", "measurement-pixel", "baseline processing"):
            self.assertIn(phrase, prohibited)
        sequence = " ".join(self.proposal["future_sequence_after_control_amendment"])
        self.assertIn("separate owner decisions", sequence)
        self.assertIn("separate radar pixel-readiness proposal", sequence)

    def test_review_bundle_and_contract_bind_exact_public_bytes(self) -> None:
        proposal_sha = sha256(PROPOSAL_REF)
        bundle_sha = sha256(BUNDLE_REF)
        self.assertEqual(proposal_sha, "ae2ddfa153a86b7acf7f8ec500690713d5ced9a8ddd58f5655d831e1eb282c77")
        self.assertEqual(bundle_sha, "5a5bd80f724841f9558ad5ff966ed0d49222419f7310b345492172e4639421ad")
        self.assertEqual(
            self.bundle["candidate_identity"],
            f"M2-RADAR-FIRST-PATH-001-PROPOSAL-SHA256:{proposal_sha}",
        )
        for artifact in self.bundle["artifacts"]:
            self.assertEqual(artifact["sha256"], sha256(artifact["path"]))
            for receipt in artifact["render_receipts"]:
                self.assertEqual(receipt["sha256"], sha256(receipt["path"]))
        self.assertEqual(self.contract["review_bundle"]["manifest_sha256"], bundle_sha)
        self.assertEqual(self.contract["items"], [{"item_id": "M2-RADAR-FIRST-PATH-001", "evidence_sha256": bundle_sha}])

    def test_blank_response_has_zero_human_decisions(self) -> None:
        self.assertFalse(self.blank["completed"])
        self.assertFalse(self.blank["reviewer"]["attestation"])
        self.assertIsNone(self.blank["responses"][0]["decision"])
        self.assertEqual(self.blank["responses"][0]["evidence_sha256"], sha256(BUNDLE_REF))
        self.assertEqual(self.readiness["status"], "pass_ready_owner_review_zero_decisions")
        self.assertEqual(self.readiness["review"]["human_decision_count"], 0)
        self.assertFalse(self.readiness["assertions"]["control_amendment_authorized"])
        self.assertFalse(self.readiness["assertions"]["radar_pixel_readiness_authorized"])

    def test_current_controls_point_to_review_without_activating_proposal(self) -> None:
        units = {unit["id"]: unit for unit in self.milestone["units"]}
        review = units["M2-RADAR-FIRST-PATH-001-REVIEW"]
        self.assertEqual(review["status"], "ready")
        self.assertTrue(review["human_gate"])
        self.assertEqual(review["gates"]["human_decision_count"], 0)
        self.assertFalse(review["gates"]["control_amendment_authorized"])
        self.assertEqual(self.profile["current_checkpoint"]["checkpoint_id"], review["id"])
        self.assertEqual(self.goal["current_checkpoint"], review["id"])
        self.assertEqual(
            self.profile["control_surfaces"]["proposed_amendments"],
            [PROPOSAL_REF],
        )
        self.assertNotIn(PROPOSAL_REF, self.goal["active_amendments"])


if __name__ == "__main__":
    unittest.main()
