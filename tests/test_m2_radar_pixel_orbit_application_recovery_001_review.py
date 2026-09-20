import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from derive_m2_acquisition_checkpoint import (  # noqa: E402
    current_radar_pixel_orbit_application_recovery_001_execution_pending,
    current_radar_pixel_orbit_application_recovery_001_implementation_active,
    current_radar_pixel_orbit_application_recovery_001_review_publication_pending,
    current_radar_pixel_orbit_application_recovery_001_review_required,
    current_radar_pixel_orbit_application_recovery_001_terminal,
)

PROPOSAL_REF = "contracts/milestone-002-radar-pixel-orbit-application-recovery-001-proposal.json"
PREFLIGHT_REF = "records/readiness/m2-radar-pixel-orbit-application-recovery-001-review-preflight.json"
DOC_REF = "docs/M2_RADAR_PIXEL_ORBIT_APPLICATION_RECOVERY_001_REVIEW.md"
IMAGE_REF = "docs/assets/m2-radar-pixel-orbit-application-recovery-001-review.png"
SURFACE_REF = "records/surface-receipts/m2-radar-pixel-orbit-application-recovery-001-review.json"
BUNDLE_REF = "reviews/m2-radar-pixel-orbit-application-recovery-001/review-bundle.json"
CONTRACT_REF = "reviews/m2-radar-pixel-orbit-application-recovery-001/review-contract.json"
BLANK_REF = "reviews/m2-radar-pixel-orbit-application-recovery-001/blank-response.json"
READINESS_REF = "records/readiness/m2-radar-pixel-orbit-application-recovery-001-review-readiness.json"
PUBLICATION_GATE_REF = "records/readiness/m2-radar-pixel-orbit-application-recovery-001-review-publication-gate.json"
PUBLICATION_RECONCILIATION_REF = "records/readiness/m2-radar-pixel-orbit-application-recovery-001-review-publication-reconciliation.json"
TERMINAL_REF = "records/processing/m2-radar-pixel-orbit-application-001-terminal-reconciliation.json"
DIAGNOSTIC_REF = "records/processing/radar-pixel-orbit-application-001/m1-src-001-identity-failure-diagnostic.json"
PROPOSAL_SHA256 = "cacda42d4eba2d60f3725bf2933fa00ea5ede6f33e6fed4133ca4d3e1476cd04"
BUNDLE_SHA256 = "69bae7d7e92f008a4a9a88f0f7408a862c48fe652ea0e98ea022280893a09bc9"
READINESS_SHA256 = "d091c39f2957743f35d3bdc03e69e3bd4cb5715b061a2301cec8bfe96a4932ec"
CHECKPOINT = json.loads((ROOT / "records/project-control-profile.json").read_text(encoding="utf-8"))["current_checkpoint"]["checkpoint_id"]
APPROVAL_REF = "records/source-gates/m2-radar-pixel-orbit-application-recovery-001-approval.json"


def load(ref: str) -> dict:
    return json.loads((ROOT / ref).read_text(encoding="utf-8"))


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


class M2RadarPixelOrbitApplicationRecovery001ReviewTests(unittest.TestCase):
    def test_exact_terminal_evidence_is_preserved(self) -> None:
        proposal = load(PROPOSAL_REF)
        terminal = load(TERMINAL_REF)
        diagnostic = load(DIAGNOSTIC_REF)
        self.assertEqual(sha256(PROPOSAL_REF), PROPOSAL_SHA256)
        self.assertEqual(proposal["trigger"]["terminal_reconciliation_sha256"], sha256(TERMINAL_REF))
        self.assertEqual(proposal["trigger"]["identity_failure_diagnostic_sha256"], sha256(DIAGNOSTIC_REF))
        self.assertEqual(terminal["status"], "block_terminal_inventory_representation_mismatch_no_retry")
        self.assertTrue(terminal["assertions"]["real_attempt_consumed"])
        self.assertEqual(diagnostic["comparison"]["byte_identity_mismatch_count"], 0)
        self.assertTrue(diagnostic["comparison"]["normalized_sorted_expected_matches_actual"])

    def test_proposal_is_bounded_and_zero_decision(self) -> None:
        proposal = load(PROPOSAL_REF)
        self.assertEqual(proposal["status"], "proposed_inactive_owner_review_required")
        self.assertEqual(proposal["human_decision_count"], 0)
        self.assertEqual(proposal["fixed_sequence"]["source_ids"], [f"M1-SRC-{index:03d}" for index in range(1, 7)])
        self.assertEqual(proposal["fixed_sequence"]["route_ids"], ["PAIR-S1-ASC-R085-IW", "PAIR-S1-DESC-R121-IW"])
        self.assertEqual(proposal["fixed_sequence"]["consumed_attempt_id"], "radar-pixel-orbit-application-001-real-001")
        self.assertEqual(proposal["fixed_sequence"]["new_attempt_id"], "radar-pixel-orbit-application-recovery-001-real-001")
        self.assertEqual(proposal["limits"]["new_real_attempts"], 1)
        self.assertFalse(proposal["limits"]["automatic_retry"])
        self.assertEqual(proposal["limits"]["network_requests"], 0)
        self.assertEqual(proposal["limits"]["credential_or_token_actions"], 0)

    def test_normalization_keeps_byte_identity_strict(self) -> None:
        proposal = load(PROPOSAL_REF)
        observed = proposal["observed_mismatch"]
        self.assertEqual(observed["expected_file_count"], 26)
        self.assertEqual(observed["actual_file_count"], 26)
        self.assertEqual(observed["added_path_count"], 0)
        self.assertEqual(observed["missing_path_count"], 0)
        self.assertEqual(observed["byte_identity_mismatch_count"], 0)
        self.assertEqual(observed["representation_only_mismatch_count"], 26)
        self.assertEqual(observed["ordering_position_mismatch_count"], 17)
        actions = "\n".join(proposal["proposed_bounded_actions"])
        self.assertIn("relative_path, size_bytes, and sha256", actions)
        self.assertIn("duplicate normalized path", actions)
        self.assertIn("hard failure", actions)

    def test_bundle_contract_and_blank_response_are_exact(self) -> None:
        bundle = load(BUNDLE_REF)
        contract = load(CONTRACT_REF)
        blank = load(BLANK_REF)
        self.assertEqual(sha256(BUNDLE_REF), BUNDLE_SHA256)
        self.assertEqual(bundle["human_decision_count"], 0)
        for artifact in bundle["artifacts"]:
            self.assertEqual(artifact["sha256"], sha256(artifact["path"]))
            for receipt in artifact["render_receipts"]:
                self.assertEqual(receipt["sha256"], sha256(receipt["path"]))
        self.assertEqual(contract["review_bundle"]["manifest_sha256"], BUNDLE_SHA256)
        self.assertTrue(contract["required_attestation"])
        self.assertFalse(contract["authority_boundary"]["implementation_authorized"])
        self.assertFalse(contract["authority_boundary"]["new_attempt_authorized"])
        self.assertFalse(blank["completed"])
        self.assertFalse(blank["reviewer"]["attestation"])
        self.assertIsNone(blank["responses"][0]["decision"])

    def test_review_surface_and_preflight_make_no_execution_claim(self) -> None:
        preflight = load(PREFLIGHT_REF)
        surface = load(SURFACE_REF)
        self.assertEqual(preflight["status"], "pass_ready_prepare_zero_decision_review")
        self.assertFalse(preflight["checks"]["current_authority_allows_retry"])
        for key in ("project_data_content_read", "external_custody_accessed", "external_custody_mutated", "implementation_authorized", "new_attempt_authorized", "scientific_result_established"):
            self.assertFalse(preflight["assertions"][key])
        self.assertEqual(surface["status"], "pass_static_review_surface")
        self.assertEqual((surface["width_px"], surface["height_px"]), (1800, 1540))
        self.assertEqual(surface["artifact_sha256"], sha256(IMAGE_REF))
        self.assertEqual(surface["assertions"]["human_decision_count"], 0)

    def test_exact_approval_releases_implementation_only(self) -> None:
        readiness = load(READINESS_REF)
        publication_gate = load(PUBLICATION_GATE_REF)
        publication_reconciliation = load(PUBLICATION_RECONCILIATION_REF)
        milestone = load("contracts/milestone-002.json")
        profile = load("records/project-control-profile.json")
        goal = load("records/long-term-goal.json")
        self.assertEqual(sha256(READINESS_REF), READINESS_SHA256)
        self.assertEqual(readiness["status"], "pass_ready_publication_zero_decisions")
        self.assertEqual(readiness["checks"]["proposal_sha256"], PROPOSAL_SHA256)
        self.assertEqual(readiness["checks"]["review_bundle_sha256"], BUNDLE_SHA256)
        self.assertEqual(readiness["checks"]["human_decision_count"], 0)
        self.assertEqual(publication_gate["status"], "pass_public_default_branch_ci_zero_decision_review_ready")
        self.assertEqual(publication_gate["public_ci_conclusion"], "success")
        self.assertTrue(publication_gate["released_now"]["owner_review"])
        self.assertFalse(publication_gate["released_now"]["implementation"])
        self.assertFalse(publication_gate["released_now"]["new_real_attempt"])
        self.assertEqual(publication_reconciliation["status"], "pass_public_gate_owner_review_ready")
        self.assertEqual(publication_reconciliation["publication_gate_sha256"], sha256(PUBLICATION_GATE_REF))
        self.assertEqual(milestone["handoff"]["current_checkpoint"], CHECKPOINT)
        self.assertEqual(profile["current_checkpoint"]["checkpoint_id"], CHECKPOINT)
        self.assertEqual(goal["current_checkpoint"], CHECKPOINT)
        self.assertEqual(
            goal["proposed_amendments"],
            [],
        )
        self.assertIn(APPROVAL_REF, goal["active_amendments"])
        units = {item["id"]: item for item in milestone["units"]}
        review = units["M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-001-REVIEW"]
        implementation = units["M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-001-IMPLEMENTATION"]
        execution = units["M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-001-EXECUTION"]
        self.assertEqual(review["status"], "complete")
        self.assertEqual(review["disposition"], "pass")
        self.assertEqual(review["gates"]["human_decision_count"], 1)
        self.assertTrue(review["gates"]["attestation"])
        self.assertTrue(review["gates"]["implementation_authorized"])
        self.assertEqual(implementation["status"], "complete")
        self.assertEqual(implementation["gates"]["public_ci"], "success")
        self.assertFalse(implementation["gates"]["project_data_content_read"])
        self.assertEqual(execution["status"], "complete")
        self.assertEqual(execution["disposition"], "block")
        self.assertEqual(execution["gates"]["real_attempts_started"], 1)
        self.assertTrue(current_radar_pixel_orbit_application_recovery_001_terminal(ROOT, {"promoted": 8}))
        self.assertFalse(current_radar_pixel_orbit_application_recovery_001_execution_pending(ROOT, {"promoted": 8}))
        self.assertFalse(current_radar_pixel_orbit_application_recovery_001_implementation_active(ROOT, {"promoted": 8}))
        self.assertFalse(current_radar_pixel_orbit_application_recovery_001_review_required(ROOT, {"promoted": 8}))
        self.assertFalse(current_radar_pixel_orbit_application_recovery_001_review_publication_pending(ROOT, {"promoted": 8}))


if __name__ == "__main__":
    unittest.main()
