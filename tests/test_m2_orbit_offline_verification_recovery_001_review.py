from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_REF = "contracts/milestone-002-orbit-offline-verification-recovery-001-proposal.json"
BUNDLE_REF = "reviews/m2-orbit-offline-verification-recovery-001/review-bundle.json"
CONTRACT_REF = "reviews/m2-orbit-offline-verification-recovery-001/review-contract.json"
BLANK_REF = "reviews/m2-orbit-offline-verification-recovery-001/blank-response.json"
TERMINAL_REF = "records/readiness/m2-orbit-offline-verification-001-terminal-reconciliation.json"
READINESS_REF = "records/readiness/m2-orbit-offline-verification-recovery-001-review-readiness.json"
PUBLICATION_GATE_REF = "records/readiness/m2-orbit-offline-verification-recovery-001-review-publication-gate.json"
PUBLICATION_RECONCILIATION_REF = "records/readiness/m2-orbit-offline-verification-recovery-001-review-publication-reconciliation.json"
PROPOSAL_SHA256 = "0be64071cfe718ca758155ff0422cfee48af342c8a560528746adc653e6a2fcf"
BUNDLE_SHA256 = "d2f0f75f40614c56bc0e62c6eecb1588f7504f50927448192673e6e403b5933f"


def load(ref: str) -> dict:
    return json.loads((ROOT / ref).read_text(encoding="utf-8"))


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


class OrbitOfflineVerificationRecoveryReviewTests(unittest.TestCase):
    def test_terminal_record_does_not_reconstruct_lost_result(self) -> None:
        terminal = load(TERMINAL_REF)
        assertions = terminal["assertions"]
        self.assertEqual(
            terminal["status"],
            "terminal_indeterminate_m2_orb_001_evaluated_receipt_not_persisted_no_retry_released",
        )
        self.assertEqual(terminal["attempt"]["result_disposition"], "indeterminate")
        self.assertTrue(assertions["m2_orb_001_eof_content_read"])
        self.assertTrue(assertions["verification_evaluation_executed_in_memory"])
        self.assertFalse(assertions["evaluation_result_durably_persisted"])
        self.assertFalse(assertions["result_reconstructed_or_inferred"])
        self.assertFalse(assertions["external_orbit_custody_mutated"])
        self.assertFalse(assertions["later_source_eof_content_read"])

    def test_recovery_keeps_scientific_rules_and_order_fixed(self) -> None:
        proposal = load(PROPOSAL_REF)
        recovery = proposal["proposed_recovery"]
        self.assertEqual(sha256(PROPOSAL_REF), PROPOSAL_SHA256)
        self.assertEqual(
            recovery["source_ids_in_exact_order"],
            ["M2-ORB-001", "M2-ORB-002", "M2-ORB-003", "M2-ORB-004"],
        )
        self.assertEqual(recovery["m2_orb_001_new_recovery_attempts"], 1)
        self.assertEqual(recovery["remaining_source_existing_attempts_per_source"], 1)
        self.assertTrue(recovery["stop_on_first_failure"])
        self.assertFalse(recovery["automatic_retry_authorized"])
        self.assertEqual(recovery["maximum_osv_endpoint_tolerance_seconds"], 1.0)
        self.assertIn(
            "leave every scientific validation predicate",
            " ".join(recovery["required_implementation"]),
        )

    def test_review_bundle_is_exact_valid_and_blank(self) -> None:
        bundle = load(BUNDLE_REF)
        contract = load(CONTRACT_REF)
        blank = load(BLANK_REF)
        readiness = load(READINESS_REF)
        self.assertEqual(sha256(BUNDLE_REF), BUNDLE_SHA256)
        self.assertEqual(contract["review_bundle"]["manifest_sha256"], BUNDLE_SHA256)
        self.assertEqual(
            contract["items"],
            [
                {
                    "item_id": "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001",
                    "evidence_sha256": BUNDLE_SHA256,
                }
            ],
        )
        self.assertTrue(bundle["review_surface"]["blank_state_verified"])
        self.assertFalse(blank["completed"])
        self.assertFalse(blank["reviewer"]["attestation"])
        self.assertIsNone(blank["responses"][0]["decision"])
        self.assertEqual(readiness["review"]["human_decision_count"], 0)
        self.assertFalse(readiness["assertions"]["recovery_authorized"])

    def test_public_ci_historically_released_only_the_blank_owner_review(self) -> None:
        gate = load(PUBLICATION_GATE_REF)
        reconciliation = load(PUBLICATION_RECONCILIATION_REF)
        milestone = load("contracts/milestone-002.json")
        units = {unit["id"]: unit for unit in milestone["units"]}
        publication = units["M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-REVIEW-PUBLICATION"]
        review = units["M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-REVIEW"]
        self.assertEqual(gate["github_actions"]["head_sha"], "d4e113911061236c0ff2e7ccd8f1042814d44002")
        self.assertEqual(gate["github_actions"]["run_id"], 34148866971)
        self.assertEqual(gate["github_actions"]["conclusion"], "success")
        self.assertEqual(reconciliation["assertions"]["human_decision_count"], 0)
        self.assertFalse(reconciliation["assertions"]["attestation"])
        self.assertFalse(reconciliation["assertions"]["recovery_authorized"])
        self.assertEqual((publication["status"], publication["disposition"]), ("complete", "pass"))
        self.assertEqual((review["status"], review["disposition"]), ("complete", "pass"))
        self.assertEqual(review["gates"]["human_decision_count"], 1)
        self.assertTrue(review["gates"]["recovery_authorized"])


if __name__ == "__main__":
    unittest.main()
