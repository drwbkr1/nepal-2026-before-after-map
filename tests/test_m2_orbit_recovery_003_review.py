from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_REF = "contracts/milestone-002-orbit-recovery-003-proposal.json"
BUNDLE_REF = "reviews/m2-orbit-recovery-003/review-bundle.json"
CONTRACT_REF = "reviews/m2-orbit-recovery-003/review-contract.json"
BLANK_REF = "reviews/m2-orbit-recovery-003/blank-response.json"
READINESS_REF = "records/readiness/m2-orbit-recovery-003-review-readiness.json"
OUTCOME_REF = "records/acquisition/m2-orbit-recovery-002-outcome-reconciliation.json"
CONTROL_REF = "records/readiness/m2-orbit-recovery-002-terminal-reconciliation.json"
PROPOSAL_SHA256 = "5aa4a0042024634a7ade191e0c5f36614216d8581a9c0535c0042be20583bfa3"
BUNDLE_SHA256 = "bc3cdc22d16251c77b26d9903036b4317221e2b01207aa9db26436bfd091fe9d"


def load(ref: str) -> dict:
    return json.loads((ROOT / ref).read_text(encoding="utf-8"))


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


class M2OrbitRecovery003ReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.proposal = load(PROPOSAL_REF)
        cls.bundle = load(BUNDLE_REF)
        cls.contract = load(CONTRACT_REF)
        cls.blank = load(BLANK_REF)
        cls.readiness = load(READINESS_REF)
        cls.outcome = load(OUTCOME_REF)
        cls.control = load(CONTROL_REF)
        cls.milestone = load("contracts/milestone-002.json")

    def test_terminal_recovery_002_boundary_is_preserved(self) -> None:
        self.assertEqual(self.outcome["status"], "terminal_pretransfer_supervisor_failure_no_retry")
        self.assertIsNone(self.outcome["attempt_id"])
        self.assertEqual(self.outcome["failure"]["classification"], "unclassified_local_pretransfer_failure")
        self.assertFalse(self.outcome["failure"]["catalog_response_hash_persisted"])
        self.assertTrue(self.outcome["assertions"]["recovery_002_authority_consumed"])
        self.assertFalse(self.outcome["assertions"]["orbit_download_requested"])
        self.assertEqual(self.outcome["assertions"]["orbit_payload_bytes_received"], 0)
        self.assertFalse(self.outcome["assertions"]["automatic_retry_performed"])

    def test_proposal_is_exact_one_file_evidence_first_and_no_retry(self) -> None:
        self.assertEqual(sha256(PROPOSAL_REF), PROPOSAL_SHA256)
        recovery = self.proposal["proposed_recovery"]
        self.assertEqual(recovery["source_id"], "M2-ORB-001")
        self.assertEqual(recovery["provider_product_id"], "d4fdc474-0069-459b-9534-b5999dec5aab")
        self.assertEqual(recovery["required_new_attempt_namespace"], "m2-orb-001-recovery-002")
        self.assertTrue(recovery["required_new_staging_root"].endswith("nepal-m2-orbit-recovery-003"))
        self.assertEqual(recovery["maximum_owner_handoffs"], 1)
        self.assertEqual(recovery["maximum_real_attempts"], 1)
        self.assertFalse(recovery["automatic_retry_authorized"])
        self.assertIn("predeclare the recovery attempt ID", recovery["implementation_corrections"][0])

    def test_proposal_preserves_unknowns_and_prohibits_broader_work(self) -> None:
        self.assertEqual(self.proposal["observed_limits"]["root_cause_status"], "unresolved_bounded_local_pretransfer_window")
        self.assertTrue(any("exception category" in item for item in self.proposal["observed_limits"]["unknown"]))
        prohibited = " ".join(self.proposal["approval_would_not_authorize"])
        for phrase in ("M2-ORB-002", "automatic retry", "AUX_POEORB", "decode radar pixels", "scientific result"):
            self.assertIn(phrase, prohibited)

    def test_bundle_contract_and_response_are_hash_bound_and_blank(self) -> None:
        self.assertEqual(sha256(BUNDLE_REF), BUNDLE_SHA256)
        self.assertEqual(self.bundle["candidate_identity"], f"M2-ORBIT-RECOVERY-003-PROPOSAL-SHA256:{PROPOSAL_SHA256}")
        for artifact in self.bundle["artifacts"]:
            if artifact["path"] == "contracts/m2-orbit-intake.json":
                self.assertNotEqual(artifact["sha256"], sha256(artifact["path"]))
            else:
                self.assertEqual(artifact["sha256"], sha256(artifact["path"]))
            for receipt in artifact["render_receipts"]:
                self.assertEqual(receipt["sha256"], sha256(receipt["path"]))
        self.assertEqual(self.contract["review_bundle"]["manifest_sha256"], BUNDLE_SHA256)
        self.assertEqual(self.contract["items"], [{"item_id": "M2-ORBIT-RECOVERY-003", "evidence_sha256": BUNDLE_SHA256}])
        self.assertFalse(self.blank["completed"])
        self.assertFalse(self.blank["reviewer"]["attestation"])
        self.assertIsNone(self.blank["responses"][0]["decision"])
        self.assertEqual(self.readiness["review"]["human_decision_count"], 0)
        self.assertFalse(self.readiness["assertions"]["recovery_003_authorized"])

    def test_active_graph_stops_at_recovery_003_owner_review(self) -> None:
        units = {unit["id"]: unit for unit in self.milestone["units"]}
        self.assertEqual(units["M2-ORBIT-RECOVERY-002"]["status"], "complete")
        self.assertEqual(units["M2-ORBIT-RECOVERY-002"]["disposition"], "block")
        self.assertEqual(units["M2-ORBIT-RECOVERY-003-REVIEW"]["status"], "complete")
        self.assertEqual(units["M2-ORBIT-RECOVERY-003-IMPLEMENTATION"]["status"], "complete")
        self.assertEqual(units["M2-ORBIT-RECOVERY-003"]["status"], "complete")
        self.assertEqual(units["M2-ORBIT-RECOVERY-003"]["disposition"], "block")
        self.assertEqual(units["M2-ORBIT-ACQUIRE"]["depends_on"][-1], "M2-ORBIT-OSV-PRECISION-AMENDMENT-001")
        self.assertEqual(
            units["M2-ORBIT-OSV-PRECISION-AMENDMENT-001-REVIEW-PUBLICATION"]["status"],
            "ready",
        )
        self.assertEqual(self.control["status"], "terminal_failure_preserved_recovery_003_review_ready")
        self.assertFalse(self.control["assertions"]["recovery_003_authorized"])


if __name__ == "__main__":
    unittest.main()
