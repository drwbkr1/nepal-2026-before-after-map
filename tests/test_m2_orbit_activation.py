from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUNDLE_SHA256 = "ee5fbf4933b52be8f97441b78a73559a973bd975efc21b43625f1ceca54e2ff1"
PROPOSAL_SHA256 = "b17e256068759946be611bf4e7beffe0d3121e9e731b6c42163525eca2cf0292"
RECOVERY_PROPOSAL_SHA256 = "ce76d633a8104ea5800f51dccd4b1037f930d41b7f08a3de32eed68c6697915a"
RECOVERY_BUNDLE_SHA256 = "df5aa9d0d03f8ee30a5cd74b91f74a88c83a525e762c22b0bd2b6773ccb5bc6b"
EXPECTED_SOURCE_IDS = [f"M2-ORB-{index:03d}" for index in range(1, 5)]
EXPECTED_SENTINEL_IDS = [f"M1-SRC-{index:03d}" for index in range(1, 7)]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


class M2OrbitActivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.reconciliation = load("records/source-gates/m2-orbit-amendment-review-reconciliation.json")
        cls.approval = load("records/source-gates/m2-orbit-amendment-approval.json")
        cls.intake = load("contracts/m2-orbit-intake.json")
        cls.verification = load("contracts/m2-orbit-offline-verification.json")
        cls.activation = load("records/acquisition/orbit-amendment-activation.json")
        cls.milestone = load("contracts/milestone-002.json")
        cls.profile = load("records/project-control-profile.json")
        cls.goal = load("records/long-term-goal.json")
        cls.recovery_proposal = load("contracts/milestone-002-orbit-recovery-proposal.json")
        cls.recovery_bundle = load("reviews/m2-orbit-recovery/review-bundle.json")
        cls.recovery_contract = load("reviews/m2-orbit-recovery/review-contract.json")
        cls.recovery_blank = load("reviews/m2-orbit-recovery/blank-response.json")

    def test_exact_human_decision_is_locked_and_reconciled(self) -> None:
        self.assertEqual(self.reconciliation["status"], "reconciled_exact_human_response")
        self.assertEqual(self.reconciliation["decision_counts"], {"approve": 1, "revise": 0, "defer": 0})
        self.assertFalse(self.reconciliation["human_decisions_fabricated"])
        self.assertEqual(self.approval["locked_response_sha256"], self.reconciliation["response_sha256"])
        self.assertEqual(self.approval["lock_receipt_sha256"], self.reconciliation["receipt_sha256"])

    def test_approval_binds_only_four_restituted_files(self) -> None:
        self.assertEqual(self.approval["review_bundle_manifest_sha256"], BUNDLE_SHA256)
        self.assertEqual(self.approval["amendment_proposal_sha256"], PROPOSAL_SHA256)
        self.assertEqual(self.approval["authorized_source_ids"], EXPECTED_SOURCE_IDS)
        self.assertEqual(self.approval["authorized_sentinel_source_ids"], EXPECTED_SENTINEL_IDS)
        self.assertEqual(self.approval["authorized_orbit_type"], "AUX_RESORB")
        self.assertEqual(
            self.approval["orbit_quality"]["later_precise_substitution_status"],
            "separately_gated_not_authorized",
        )
        self.assertFalse(self.approval["credential_policy"]["value_recorded"])

    def test_active_controls_preserve_current_failure_and_prerequisite_blocks(self) -> None:
        self.assertEqual(
            self.intake["extensions"]["status"],
            "active_acquisition_review_required",
        )
        self.assertEqual(self.intake["extensions"]["amendment_approval_sha256"], sha256("records/source-gates/m2-orbit-amendment-approval.json"))
        self.assertEqual(
            {state: sum(asset["state"] == state for asset in self.intake["assets"]) for state in ("authorized", "failed", "promoted")},
            {"authorized": 3, "failed": 1, "promoted": 0},
        )
        failed = next(asset for asset in self.intake["assets"] if asset["state"] == "failed")
        self.assertEqual(failed["extensions"]["source_id"], "M2-ORB-001")
        self.assertFalse(failed["attempts"][0]["extensions"]["credential_value_recorded"])
        self.assertTrue(
            all(asset["extensions"]["sentinel_custody_prerequisite"] == "not_satisfied_at_activation" for asset in self.intake["assets"])
        )
        self.assertEqual(self.verification["status"], "active_gate_deferred_no_promoted_orbits")
        self.assertFalse(self.verification["authority"]["precise_orbit_substitution_authorized"])
        self.assertFalse(self.verification["authority"]["radar_pixel_processing_authorized_by_this_contract"])

    def test_project_control_surfaces_consume_review_without_releasing_other_gates(self) -> None:
        unit_by_id = {unit["id"]: unit for unit in self.milestone["units"]}
        self.assertEqual(unit_by_id["M2-ORBIT-AMEND"]["status"], "complete")
        self.assertEqual(unit_by_id["M2-ORBIT-PREFLIGHT"]["status"], "complete")
        self.assertEqual(unit_by_id["M2-ORBIT-ACQUIRE"]["status"], "blocked_retained_failure_review")
        self.assertEqual(unit_by_id["M2-ORBIT-ACQUIRE"]["gates"]["retained_failure_review"], "required")
        self.assertEqual(unit_by_id["M2-ORBIT-ACQUIRE"]["gates"]["milestone_dependency_m2_verify"], "not_satisfied")
        self.assertTrue(unit_by_id["M2-ORBIT-ACQUIRE"]["gates"]["orbit_custody_initialized"])
        self.assertEqual(unit_by_id["M2-ORBIT-APPLY"]["gates"]["dem_vertical_datum_gate"], "pending")
        self.assertEqual(self.profile["control_surfaces"]["proposed_amendments"], [])
        self.assertEqual(
            self.profile["control_surfaces"]["activated_amendments"],
            [
                "records/source-gates/m2-dem-amendment-approval.json",
                "records/source-gates/m2-orbit-amendment-approval.json",
                "records/source-gates/m2-radar-input-readiness-amendment-approval.json",
            ],
        )
        checkpoints = [item["checkpoint_id"] for item in self.profile["parallel_checkpoints"]]
        self.assertIn("M2-DEM-VERTICAL-DATUM-REVIEW", checkpoints)
        self.assertIn("M2-DEM-TERRAIN-RESULT-REVIEW", checkpoints)
        self.assertIn("M2-ORBIT-ACQUISITION-REVIEW", checkpoints)
        self.assertNotIn("M2-ORBIT-AMENDMENT-REVIEW", checkpoints)
        self.assertEqual(self.goal["parallel_checkpoints"], checkpoints)

    def test_activation_receipt_binds_outputs_and_claim_boundary(self) -> None:
        bindings = self.activation["bindings"]
        for ref_key, sha_key in (
            ("approval_ref", "approval_sha256"),
            ("active_verification_ref", "active_verification_sha256"),
            ("activation_script_ref", "activation_script_sha256"),
        ):
            self.assertEqual(bindings[sha_key], sha256(bindings[ref_key]))
        self.assertNotEqual(bindings["active_intake_sha256"], sha256(bindings["active_intake_ref"]))
        self.assertNotEqual(bindings["active_milestone_sha256"], sha256(bindings["active_milestone_ref"]))
        self.assertNotEqual(bindings["project_profile_sha256"], sha256(bindings["project_profile_ref"]))
        self.assertNotEqual(bindings["long_term_goal_sha256"], sha256(bindings["long_term_goal_ref"]))
        self.assertEqual(self.activation["assertions"]["orbit_payload_bytes_requested"], 0)
        self.assertEqual(self.activation["assertions"]["matching_sentinel_sources_promoted_at_activation"], 0)
        self.assertFalse(self.activation["assertions"]["precise_substitution_authorized"])
        self.assertFalse(self.activation["assertions"]["scientific_result_established"])

    def test_recovery_review_is_exact_blank_and_dependency_gated(self) -> None:
        self.assertEqual(sha256("contracts/milestone-002-orbit-recovery-proposal.json"), RECOVERY_PROPOSAL_SHA256)
        self.assertEqual(sha256("reviews/m2-orbit-recovery/review-bundle.json"), RECOVERY_BUNDLE_SHA256)
        self.assertEqual(self.recovery_proposal["status"], "proposed_not_authorized")
        self.assertIn(
            "the full M2-VERIFY unit is complete after the exact eight-product Sentinel acquisition and verification route is reconciled",
            self.recovery_proposal["proposed_recovery"]["prerequisites"],
        )
        self.assertEqual(
            self.recovery_bundle["candidate_identity"],
            f"M2-ORBIT-RECOVERY-PROPOSAL-SHA256:{RECOVERY_PROPOSAL_SHA256}",
        )
        self.assertEqual(self.recovery_contract["review_bundle"]["manifest_sha256"], RECOVERY_BUNDLE_SHA256)
        self.assertNotIn("data_acquisition", self.recovery_contract["workflow_authority"]["authorized_action_classes"])
        self.assertFalse(self.recovery_blank["completed"])
        self.assertFalse(self.recovery_blank["reviewer"]["attestation"])
        self.assertEqual(self.recovery_blank["responses"][0]["evidence_sha256"], RECOVERY_BUNDLE_SHA256)
        self.assertIsNone(self.recovery_blank["responses"][0]["decision"])

    def test_evidence_ledger_records_activation_once(self) -> None:
        ledger = [json.loads(line) for line in (ROOT / "records/evidence-ledger.jsonl").read_text(encoding="utf-8").splitlines()]
        records = [item for item in ledger if item.get("record_id") == "EVID-0053"]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["activation_receipt_sha256"], sha256("records/acquisition/orbit-amendment-activation.json"))
        self.assertEqual(records[0]["approval_sha256"], sha256("records/source-gates/m2-orbit-amendment-approval.json"))


if __name__ == "__main__":
    unittest.main()
