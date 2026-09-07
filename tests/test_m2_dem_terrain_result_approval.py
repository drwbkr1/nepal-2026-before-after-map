import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


class TerrainResultApprovalTests(unittest.TestCase):
    def test_exact_review_response_is_reconciled_without_new_authority(self) -> None:
        reconciliation = load("records/source-gates/m2-dem-terrain-result-review-reconciliation.json")
        approval = load("records/source-gates/m2-dem-terrain-result-approval.json")

        self.assertEqual(reconciliation["status"], "reconciled_exact_human_response")
        self.assertEqual(reconciliation["human_decision_count"], 1)
        self.assertEqual(reconciliation["decision_counts"], {"approve": 1, "revise": 0, "defer": 0})
        self.assertFalse(reconciliation["human_decisions_fabricated"])
        self.assertFalse(reconciliation["downstream_authorization_created"])
        self.assertEqual(
            approval["review_bundle_manifest_sha256"],
            "834ad354fc134b2017afdd3b238c1a6271276e8b1a95776e434180c7283a26d5",
        )
        self.assertEqual(
            approval["proposal_sha256"],
            "80855c6859a6a78de5712883f604c4f6f7816e459b44638054c3f6a1e848a90c",
        )
        self.assertEqual(
            approval["terrain_receipt_sha256"],
            "9663c261de37c77fd96896d1fbb37c4c3a970c47966661908673db880e640dd7",
        )
        self.assertEqual(approval["locked_response_sha256"], reconciliation["response_sha256"])
        self.assertEqual(approval["lock_receipt_sha256"], reconciliation["receipt_sha256"])

    def test_failed_audit_input_is_preserved_and_corrected_append_only(self) -> None:
        failure = load("records/readiness/m2-dem-terrain-readiness-owner-review-001-audit-failure.json")
        corrected = load("records/readiness/m2-dem-terrain-readiness-owner-review-002-input.json")
        original = load("records/readiness/m2-dem-terrain-readiness-input.json")

        self.assertEqual(failure["exit_code"], 4)
        self.assertFalse(failure["audit_output_created"])
        self.assertEqual(
            failure["audit_input_sha256"],
            sha256("records/readiness/m2-dem-terrain-readiness-owner-review-001-input.json"),
        )
        self.assertEqual(corrected["candidate_id"], original["candidate_id"])
        self.assertEqual(corrected["candidate_manifest_sha256"], original["candidate_manifest_sha256"])
        original_gates = {gate["gate_id"]: gate for gate in original["gates"]}
        corrected_gates = {gate["gate_id"]: gate for gate in corrected["gates"]}
        self.assertEqual(set(corrected_gates), set(original_gates))
        for gate_id in set(original_gates) - {"human-review"}:
            self.assertEqual(corrected_gates[gate_id], original_gates[gate_id])
        self.assertEqual(corrected_gates["human-review"]["status"], "pass")

    def test_reassessment_closes_only_owner_review_gate(self) -> None:
        decision = load("records/readiness/m2-dem-terrain-readiness-owner-review-002-decision.json")
        control = load("records/readiness/m2-dem-terrain-result-owner-review-reconciliation.json")
        profile = load("records/project-control-profile.json")
        goal = load("records/long-term-goal.json")

        self.assertEqual(decision["decision"], "defer")
        self.assertIn("human-review", [item["gate_id"] for item in decision["pass_evidence"]])
        self.assertEqual(
            decision["deferred_required_gate_ids"],
            ["evaluation-design", "radar-input-fitness", "uncertainty-and-exclusions"],
        )
        self.assertEqual(decision["authorized_next_actions"], [])
        self.assertFalse(decision["training_authorized_by_this_audit"])
        self.assertEqual(control["gate_reassessment"]["human_review"], "pass")
        self.assertEqual(control["gate_reassessment"]["overall_decision"], "defer")
        self.assertFalse(control["assertions"]["vertical_datum_resolved"])
        self.assertFalse(control["assertions"]["orbit_application_authorized"])
        self.assertFalse(control["assertions"]["radar_pixel_processing_authorized"])
        self.assertEqual(
            [item["checkpoint_id"] for item in profile["parallel_checkpoints"]],
            ["M2-DEM-VERTICAL-DATUM-REVIEW"],
        )
        self.assertEqual(goal["parallel_checkpoints"], ["M2-DEM-VERTICAL-DATUM-REVIEW"])


if __name__ == "__main__":
    unittest.main()
