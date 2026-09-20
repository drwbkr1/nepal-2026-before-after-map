from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from derive_m2_acquisition_checkpoint import (  # noqa: E402
    current_dem_proj25_metadata_recovery_001_implementation_active,
    current_dem_proj25_receipt_persistence_recovery_002_review_publication_pending,
    current_dem_proj25_receipt_persistence_recovery_002_review_required,
    current_dem_proj25_receipt_persistence_recovery_002_implementation_active,
    current_dem_proj25_receipt_persistence_recovery_002_complete,
)


PROPOSAL_SHA256 = "15180773dd351c9f738e4227ee3faa3ce571f683935f0a229c466bee692b5657"
BUNDLE_SHA256 = "cb4b87ff5c2fcc577bab0f8377524fb7463701a4a3d798fc594b5db4e570f1b5"
GRID_SHA256 = "4191d471eefebf24091b56dbc604353cb3b8cf8cc70e448bb9ae56a272bef17a"


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


class M2DemProj25ReceiptPersistenceRecovery002ReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.failure = load("records/acquisition/m2-dem-vertical-datum-proj25-metadata-recovery-001-runtime-failure.json")
        cls.outcome = load("records/acquisition/m2-dem-vertical-datum-proj25-metadata-recovery-001-outcome-reconciliation.json")
        cls.proposal = load("contracts/m2-dem-vertical-datum-proj25-receipt-persistence-recovery-002-proposal.json")
        cls.bundle = load("reviews/m2-dem-proj25-receipt-persistence-recovery-002/review-bundle.json")
        cls.contract = load("reviews/m2-dem-proj25-receipt-persistence-recovery-002/review-contract.json")
        cls.blank = load("reviews/m2-dem-proj25-receipt-persistence-recovery-002/blank-response.json")
        cls.readiness = load("records/readiness/m2-dem-proj25-receipt-persistence-recovery-002-review-readiness.json")
        cls.milestone = load("contracts/milestone-002.json")
        cls.profile = load("records/project-control-profile.json")
        cls.goal = load("records/long-term-goal.json")

    def test_recovery_001_is_terminal_after_exact_promotion_without_terminal_receipt(self) -> None:
        self.assertEqual(self.failure["status"], "terminal_failure_after_conditional_promotion_no_terminal_receipt")
        self.assertEqual(self.failure["process_exit_code"], 1)
        self.assertEqual(self.failure["observed_external_state"]["destination_sha256"], GRID_SHA256)
        self.assertTrue(self.failure["observed_external_state"]["same_file_identity"])
        self.assertFalse(self.failure["durable_evidence"]["public_terminal_exists"])
        self.assertEqual(self.outcome["status"], "block_terminal_receipt_persistence_failure_after_exact_promotion")
        self.assertTrue(self.outcome["disposition"]["recovery_001_terminal"])
        self.assertFalse(self.outcome["disposition"]["retry_authorized"])
        self.assertFalse(self.outcome["control_flow_inference"]["durable_terminal_success_reconstructed"])

    def test_proposal_is_exact_zero_network_and_zero_new_promotion(self) -> None:
        self.assertEqual(sha256("contracts/m2-dem-vertical-datum-proj25-receipt-persistence-recovery-002-proposal.json"), PROPOSAL_SHA256)
        self.assertEqual(self.proposal["status"], "proposed_inactive_owner_review_required")
        self.assertEqual(self.proposal["limits"]["network_requests"], 0)
        self.assertEqual(self.proposal["limits"]["recovery_001_retries"], 0)
        self.assertEqual(self.proposal["limits"]["new_promotion_actions"], 0)
        self.assertEqual(self.proposal["limits"]["receipt_recovery_002_attempts"], 1)
        self.assertFalse(self.proposal["limits"]["automatic_retry"])
        self.assertFalse(self.proposal["claim_boundary"]["receipt_recovery_authorized"])
        self.assertFalse(self.proposal["claim_boundary"]["dem_conversion_authorized"])

    def test_review_bundle_is_exact_and_blank(self) -> None:
        self.assertEqual(sha256("reviews/m2-dem-proj25-receipt-persistence-recovery-002/review-bundle.json"), BUNDLE_SHA256)
        self.assertEqual(self.bundle["human_decision_count"], 0)
        self.assertEqual(self.contract["review_bundle"]["manifest_sha256"], BUNDLE_SHA256)
        self.assertTrue(self.contract["required_attestation"])
        self.assertFalse(self.blank["completed"])
        self.assertFalse(self.blank["reviewer"]["attestation"])
        self.assertIsNone(self.blank["responses"][0]["decision"])
        self.assertEqual(self.blank["responses"][0]["evidence_sha256"], BUNDLE_SHA256)

    def test_readiness_releases_only_publication(self) -> None:
        self.assertEqual(self.readiness["status"], "pass_ready_publication_zero_decisions")
        self.assertEqual(self.readiness["validation"]["human_decision_count"], 0)
        for key in (
            "receipt_recovery_authorized", "network_request_authorized", "new_promotion_authorized",
            "operation_sign_preflight_authorized", "dem_conversion_authorized",
            "dem_pixels_read_during_preparation", "scientific_result_established",
        ):
            self.assertFalse(self.readiness["assertions"][key])

    def test_control_state_routes_to_bounded_implementation(self) -> None:
        checkpoint = json.loads((ROOT / "records/project-control-profile.json").read_text(encoding="utf-8"))["current_checkpoint"]["checkpoint_id"]
        self.assertEqual(self.profile["current_checkpoint"]["checkpoint_id"], checkpoint)
        self.assertEqual(self.goal["current_checkpoint"], checkpoint)
        self.assertEqual(self.milestone["handoff"]["current_checkpoint"], checkpoint)
        self.assertEqual(
            self.goal["proposed_amendments"],
            [],
        )
        self.assertFalse(current_dem_proj25_receipt_persistence_recovery_002_review_publication_pending(ROOT, {"promoted": 8}))
        self.assertFalse(current_dem_proj25_receipt_persistence_recovery_002_review_required(ROOT, {"promoted": 8}))
        self.assertFalse(current_dem_proj25_receipt_persistence_recovery_002_implementation_active(ROOT, {"promoted": 8}))
        self.assertTrue(current_dem_proj25_receipt_persistence_recovery_002_complete(ROOT, {"promoted": 8}))
        self.assertFalse(current_dem_proj25_metadata_recovery_001_implementation_active(ROOT, {"promoted": 8}))

    def test_milestone_preserves_terminal_history_and_conditional_dependency(self) -> None:
        units = {unit["id"]: unit for unit in self.milestone["units"]}
        prior = units["M2-DEM-PROJ25-METADATA-RECOVERY-001-IMPLEMENTATION"]
        review = units["M2-DEM-PROJ25-RECEIPT-PERSISTENCE-RECOVERY-002-REVIEW"]
        implementation = units["M2-DEM-PROJ25-RECEIPT-PERSISTENCE-RECOVERY-002-IMPLEMENTATION"]
        conversion = units["M2-DEM-VERTICAL-DATUM-CONVERSION"]
        self.assertEqual(prior["disposition"], "block_terminal_receipt_persistence_failure_after_exact_promotion")
        self.assertEqual(review["status"], "complete")
        self.assertEqual(review["gates"]["human_decision_count"], 1)
        self.assertTrue(review["gates"]["attestation"])
        self.assertTrue(review["gates"]["receipt_persistence_correction_authorized"])
        self.assertFalse(review["gates"]["receipt_recovery_authorized"])
        self.assertEqual(implementation["status"], "complete")
        self.assertEqual(implementation["gates"]["public_ci"], "success")
        self.assertEqual(implementation["gates"]["final_no_content_preflight"], "pass")
        self.assertEqual(conversion["status"], "complete")
        self.assertEqual(conversion["disposition"], "pass")
        self.assertEqual(conversion["depends_on"], [implementation["id"]])


if __name__ == "__main__":
    unittest.main()
