from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_SHA256 = "0eb9e60f3cd26365cc447eb007e28186470a778928730b055b633c5e88d344e4"
BUNDLE_SHA256 = "71b3eea557cbd027fecec299b8661ce555a8fa993bccd8ffaea8f525d79d01a7"


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


class OrbitOsvPrecisionAmendmentPublicationTests(unittest.TestCase):
    def test_public_gate_preserves_failed_run_and_binds_success(self) -> None:
        gate = load("records/readiness/m2-orbit-osv-precision-amendment-001-review-publication-gate.json")
        self.assertEqual(gate["status"], "pass_exact_blank_review_packet_public_ci")
        self.assertEqual(gate["github_actions"]["run_id"], 34054314929)
        self.assertEqual(gate["github_actions"]["head_sha"], "39a1807f77ed6463f4100b753aa85a3e299220d5")
        self.assertEqual(gate["github_actions"]["conclusion"], "success")
        self.assertEqual(gate["bindings"]["proposal_sha256"], PROPOSAL_SHA256)
        self.assertEqual(gate["bindings"]["review_bundle_sha256"], BUNDLE_SHA256)
        self.assertTrue(gate["assertions"]["failed_prior_run_preserved"])
        self.assertFalse(gate["assertions"]["amendment_authorized"])

    def test_publication_reconciliation_history_remains_bound_after_approval(self) -> None:
        milestone = load("contracts/milestone-002.json")
        profile = load("records/project-control-profile.json")
        goal = load("records/long-term-goal.json")
        reconciliation = load("records/readiness/m2-orbit-osv-precision-amendment-001-review-publication-reconciliation.json")
        units = {unit["id"]: unit for unit in milestone["units"]}
        self.assertEqual(units["M2-ORBIT-OSV-PRECISION-AMENDMENT-001-REVIEW-PUBLICATION"]["status"], "complete")
        self.assertEqual(units["M2-ORBIT-OSV-PRECISION-AMENDMENT-001-REVIEW"]["status"], "complete")
        self.assertEqual(units["M2-ORBIT-OSV-PRECISION-AMENDMENT-001-REVIEW"]["gates"]["human_decision_count"], 1)
        self.assertTrue(units["M2-ORBIT-OSV-PRECISION-AMENDMENT-001-REVIEW"]["gates"]["amendment_authorized"])
        self.assertEqual(
            profile["current_checkpoint"]["checkpoint_id"],
            "M2-DEM-VERTICAL-DATUM-REVIEW",
        )
        self.assertEqual(
            goal["current_checkpoint"],
            "M2-DEM-VERTICAL-DATUM-REVIEW",
        )
        self.assertEqual(reconciliation["status"], "pass_public_packet_owner_review_ready_zero_decisions")
        self.assertFalse(reconciliation["assertions"]["staged_file_promoted"])

    def test_blank_response_and_packet_identity_are_unchanged(self) -> None:
        gate = load("records/readiness/m2-orbit-osv-precision-amendment-001-review-publication-gate.json")
        blank = load("reviews/m2-orbit-osv-precision-amendment-001/blank-response.json")
        self.assertEqual(sha256("contracts/milestone-002-orbit-osv-precision-amendment-001-proposal.json"), PROPOSAL_SHA256)
        self.assertEqual(sha256("reviews/m2-orbit-osv-precision-amendment-001/review-bundle.json"), BUNDLE_SHA256)
        self.assertEqual(gate["bindings"]["blank_response_sha256"], sha256("reviews/m2-orbit-osv-precision-amendment-001/blank-response.json"))
        self.assertFalse(blank["completed"])
        self.assertFalse(blank["reviewer"]["attestation"])
        self.assertIsNone(blank["responses"][0]["decision"])


if __name__ == "__main__":
    unittest.main()
