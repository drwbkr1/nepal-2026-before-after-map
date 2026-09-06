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
PUBLICATION_REF = "records/readiness/m2-radar-first-path-001-review-publication-gate.json"
ANALYSIS_REF = "records/readiness/m2-post-optical-route-analysis-001.json"
RECONCILIATION_REF = "records/source-gates/m2-radar-first-path-001-review-reconciliation.json"
APPROVAL_REF = "records/source-gates/m2-radar-first-path-001-approval.json"
ACTIVATION_REF = "records/readiness/m2-radar-first-path-001-activation.json"
OPTICAL_ROUTE_REF = "records/readiness/m2-optical-route-disposition-001.json"
RADAR_ROUTE_REF = "records/readiness/m2-radar-source-readiness-001.json"
STALE_ORBIT_REF = "records/readiness/m2-orbit-recovery-001-stale-evidence.json"
CONTROL_REF = "records/readiness/m2-radar-first-path-001-control-reconciliation.json"


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
        cls.publication = load(PUBLICATION_REF)
        cls.reconciliation = load(RECONCILIATION_REF)
        cls.approval = load(APPROVAL_REF)
        cls.activation = load(ACTIVATION_REF)
        cls.optical_route = load(OPTICAL_ROUTE_REF)
        cls.radar_route = load(RADAR_ROUTE_REF)
        cls.stale_orbit = load(STALE_ORBIT_REF)
        cls.control = load(CONTROL_REF)
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

    def test_publication_gate_binds_passing_public_commit_without_authority(self) -> None:
        self.assertEqual(self.publication["status"], "pass_exact_review_packet_public_ci")
        self.assertEqual(self.publication["publication_commit"], "b357e335cb1312c124384958ee5fd6512e184eeb")
        self.assertEqual(self.publication["github_actions"]["run_id"], 33990934063)
        self.assertEqual(self.publication["github_actions"]["conclusion"], "success")
        for key in ("analysis", "proposal", "review_bundle", "review_contract", "blank_response", "readiness"):
            self.assertEqual(
                self.publication["bindings"][f"{key}_sha256"],
                sha256(self.publication["bindings"][f"{key}_ref"]),
            )
        self.assertEqual(self.publication["assertions"]["human_decision_count"], 0)
        self.assertFalse(self.publication["assertions"]["control_amendment_authorized"])
        self.assertFalse(self.publication["assertions"]["real_product_pixels_read_during_publication"])

    def test_exact_approval_is_locked_and_activates_only_the_control_route(self) -> None:
        self.assertEqual(self.reconciliation["status"], "reconciled_exact_human_response")
        self.assertEqual(self.reconciliation["decision_counts"], {"approve": 1, "revise": 0, "defer": 0})
        self.assertFalse(self.reconciliation["human_decisions_fabricated"])
        self.assertEqual(self.approval["locked_response_sha256"], self.reconciliation["response_sha256"])
        self.assertEqual(self.approval["lock_receipt_sha256"], self.reconciliation["receipt_sha256"])
        self.assertEqual(self.activation["status"], "pass_control_route_split_and_corrected_review_preparation_only")
        self.assertTrue(self.activation["released_now"]["control_graph_route_split"])
        for key in ("orbit_access_or_download", "dem_action", "radar_pixel_decoding", "baseline_or_change_analysis", "scientific_publication"):
            self.assertFalse(self.activation["released_now"][key])

    def test_route_records_preserve_optical_block_and_bind_radar_headers_only(self) -> None:
        self.assertEqual(self.optical_route["status"], "terminal_block_preserved_no_alternate_route_authorized")
        self.assertEqual(self.optical_route["route"]["real_001_disposition"], "INVALID")
        self.assertEqual(self.optical_route["route"]["recovery_001_disposition"], "BLOCK")
        self.assertFalse(self.optical_route["route"]["retry_authorized"])
        self.assertEqual(self.radar_route["status"], "pass_six_source_custody_materialization_and_header_readiness_only")
        self.assertEqual(self.radar_route["source_ids"], [f"M1-SRC-{index:03d}" for index in range(1, 7)])
        self.assertFalse(self.radar_route["assertions"]["measurement_pixels_decoded"])
        self.assertFalse(self.radar_route["assertions"]["baseline_established"])
        self.assertEqual(self.stale_orbit["status"], "stale_unapproved_preserved_not_actionable")
        self.assertEqual(self.stale_orbit["bindings"]["proposal_sha256"], "ce76d633a8104ea5800f51dccd4b1037f930d41b7f08a3de32eed68c6697915a")
        self.assertEqual(self.stale_orbit["bindings"]["review_bundle_sha256"], "df5aa9d0d03f8ee30a5cd74b91f74a88c83a525e762c22b0bd2b6773ccb5bc6b")

    def test_current_controls_preserve_route_split_and_point_to_recovery_003_review(self) -> None:
        units = {unit["id"]: unit for unit in self.milestone["units"]}
        review = units["M2-RADAR-FIRST-PATH-001-REVIEW"]
        self.assertEqual(review["status"], "complete")
        self.assertTrue(review["human_gate"])
        self.assertEqual(review["gates"]["human_decision_count"], 1)
        self.assertTrue(review["gates"]["control_amendment_authorized"])
        self.assertEqual(units["M2-OPTICAL-ROUTE-DISPOSITION"]["disposition"], "block")
        self.assertEqual(units["M2-RADAR-SOURCE-READINESS"]["status"], "complete")
        self.assertEqual(units["M2-VERIFY"]["status"], "deferred")
        self.assertEqual(units["M2-ORBIT-RECOVERY-002-REVIEW"]["status"], "complete")
        self.assertEqual(units["M2-ORBIT-RECOVERY-002-REVIEW"]["gates"]["human_decision_count"], 1)
        self.assertEqual(units["M2-ORBIT-RECOVERY-003-REVIEW"]["status"], "complete")
        self.assertEqual(units["M2-ORBIT-RECOVERY-003-REVIEW"]["gates"]["human_decision_count"], 1)
        self.assertEqual(units["M2-ORBIT-RECOVERY-003"]["disposition"], "block")
        self.assertEqual(
            self.profile["current_checkpoint"]["checkpoint_id"],
            "M2-ORBIT-CONTINUATION-001-IMPLEMENTATION",
        )
        self.assertEqual(
            self.goal["current_checkpoint"],
            "M2-ORBIT-CONTINUATION-001-IMPLEMENTATION",
        )
        self.assertEqual(
            self.profile["control_surfaces"]["proposed_amendments"],
            [],
        )
        self.assertIn(APPROVAL_REF, self.goal["active_amendments"])
        self.assertEqual(self.control["status"], "pass_route_split_and_corrected_orbit_review_ready")
        self.assertEqual(self.control["assertions"]["corrected_orbit_human_decision_count"], 0)


if __name__ == "__main__":
    unittest.main()
