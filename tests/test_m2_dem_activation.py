from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


class M2DemActivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.reconciliation = load("records/source-gates/m2-dem-amendment-review-reconciliation.json")
        cls.approval = load("records/source-gates/m2-dem-amendment-approval.json")
        cls.candidate_intake = load("contracts/m2-dem-intake-candidate.json")
        cls.active_intake = load("contracts/m2-dem-intake.json")
        cls.candidate_verification = load("contracts/m2-dem-offline-verification-candidate.json")
        cls.active_verification = load("contracts/m2-dem-offline-verification.json")
        cls.milestone = load("contracts/milestone-002.json")
        cls.profile = load("records/project-control-profile.json")
        cls.goal = load("records/long-term-goal.json")
        cls.receipt = load("records/acquisition/dem-amendment-activation.json")
        cls.ledger = [
            json.loads(line)
            for line in (ROOT / "records/evidence-ledger.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def test_exact_reconciled_owner_approval_is_bound(self) -> None:
        self.assertEqual(self.reconciliation["status"], "reconciled_exact_human_response")
        self.assertEqual(self.reconciliation["decision_counts"], {"approve": 1, "revise": 0, "defer": 0})
        self.assertFalse(self.reconciliation["human_decisions_fabricated"])
        self.assertEqual(self.approval["status"], "approved")
        self.assertEqual(
            self.approval["review_bundle_manifest_sha256"],
            "caecbdfe69ec1a6c8c39401b63756005820a727cb8f9e7e0084753e2d6afb39e",
        )
        self.assertEqual(
            self.approval["amendment_proposal_sha256"],
            "92f48680c0b779398d8bbebd872a60bc3850f008f5c9b68d5bf45a2448abdd69",
        )
        self.assertEqual(
            self.approval["license"]["document_sha256"],
            "9cd37d37ea654bbcaf0a2e059e6a3a5b5f76072824d8dd860ccf274ada8951bd",
        )

    def test_candidate_controls_remain_non_authorizing_history(self) -> None:
        self.assertEqual(self.candidate_intake["extensions"]["authority_status"], "not_granted")
        self.assertTrue(all(asset["state"] == "planned" for asset in self.candidate_intake["assets"]))
        self.assertEqual(self.candidate_verification["status"], "candidate_static_control_not_authorized")
        self.assertEqual(self.candidate_verification["authority"]["dem_amendment_status"], "not_granted")

    def test_active_intake_contains_only_four_authorized_unattempted_tiles(self) -> None:
        self.assertEqual(self.active_intake["extensions"]["status"], "active_authorized_unattempted")
        self.assertEqual(len(self.active_intake["assets"]), 4)
        self.assertEqual(
            {asset["extensions"]["source_id"] for asset in self.active_intake["assets"]},
            {"M2-DEM-001", "M2-DEM-002", "M2-DEM-003", "M2-DEM-004"},
        )
        self.assertTrue(all(asset["state"] == "authorized" for asset in self.active_intake["assets"]))
        self.assertTrue(all(asset["attempts"] == [] for asset in self.active_intake["assets"]))
        self.assertTrue(
            all(
                asset["source"]["authorization_ref"]
                == "records/source-gates/m2-dem-amendment-approval.json"
                for asset in self.active_intake["assets"]
            )
        )

    def test_active_offline_verification_is_authorized_but_data_deferred(self) -> None:
        self.assertEqual(self.active_verification["status"], "active_gate_deferred_no_promoted_rasters")
        authority = self.active_verification["authority"]
        self.assertEqual(authority["dem_amendment_status"], "approved")
        self.assertTrue(authority["license_acceptance_established"])
        self.assertTrue(authority["dem_pixel_processing_authorized"])
        self.assertFalse(authority["network_access_authorized"])
        self.assertFalse(authority["custody_mutation_authorized"])
        self.assertFalse(authority["dem_download_authorized"])
        self.assertFalse(authority["this_contract_creates_authority"])
        self.assertEqual(self.active_verification["inputs"]["intake_contract_sha256"], sha256("contracts/m2-dem-intake.json"))

    def test_milestone_and_profile_expose_parallel_dem_preflight(self) -> None:
        units = {unit["id"]: unit for unit in self.milestone["units"]}
        self.assertEqual(units["M2-DEM-AMEND"]["status"], "complete")
        self.assertEqual(units["M2-DEM-PREFLIGHT"]["status"], "ready")
        self.assertEqual(units["M2-DEM-ACQUIRE"]["status"], "planned")
        self.assertEqual(units["M2-DEM-VERIFY"]["status"], "planned")
        self.assertEqual(set(units["M2-BASELINE"]["depends_on"]), {"M2-VERIFY", "M2-DEM-VERIFY"})
        self.assertEqual(self.profile["control_surfaces"]["proposed_amendments"], [])
        self.assertEqual(
            self.profile["control_surfaces"]["activated_amendments"],
            ["records/source-gates/m2-dem-amendment-approval.json"],
        )
        self.assertEqual(self.profile["current_checkpoint"]["checkpoint_id"], "M2-AUTHENTICATION-REFERENCE")
        self.assertEqual(self.profile["parallel_checkpoints"][0]["checkpoint_id"], "M2-DEM-FRESH-PREFLIGHT")
        self.assertEqual(self.goal["parallel_checkpoints"], ["M2-DEM-FRESH-PREFLIGHT"])

    def test_activation_receipt_binds_current_outputs_and_claim_boundary(self) -> None:
        self.assertEqual(self.receipt["status"], "pass_exact_dem_amendment_activated_preflight_pending")
        for ref_key, hash_key in (
            ("reconciliation_ref", "reconciliation_sha256"),
            ("approval_ref", "approval_sha256"),
            ("active_intake_ref", "active_intake_sha256"),
            ("active_verification_ref", "active_verification_sha256"),
            ("active_milestone_ref", "active_milestone_sha256"),
            ("project_profile_ref", "project_profile_sha256"),
            ("long_term_goal_ref", "long_term_goal_sha256"),
            ("activation_script_ref", "activation_script_sha256"),
        ):
            relative = self.receipt["bindings"][ref_key]
            self.assertEqual(self.receipt["bindings"][hash_key], sha256(relative))
        assertions = self.receipt["assertions"]
        self.assertTrue(assertions["exact_license_accepted"])
        self.assertEqual(assertions["authorized_dem_tile_count"], 4)
        self.assertFalse(assertions["network_requests_performed"])
        self.assertFalse(assertions["dem_payload_bytes_requested"])
        self.assertFalse(assertions["dem_pixels_examined"])

    def test_evidence_0031_binds_activation_without_pixel_claim(self) -> None:
        evidence = next(record for record in self.ledger if record.get("record_id") == "EVID-0031")
        self.assertEqual(evidence["status"], "pass_exact_dem_amendment_activated_preflight_pending")
        for ref_key, hash_key in (
            ("activation_receipt_ref", "activation_receipt_sha256"),
            ("approval_ref", "approval_sha256"),
            ("active_intake_ref", "active_intake_sha256"),
            ("active_verification_ref", "active_verification_sha256"),
            ("reconciliation_ref", "reconciliation_sha256"),
            ("activation_script_ref", "activation_script_sha256"),
        ):
            self.assertEqual(evidence[hash_key], sha256(evidence[ref_key]))
        self.assertFalse(evidence["assertions"]["dem_pixels_examined"])
        self.assertFalse(evidence["assertions"]["scientific_result_established"])


if __name__ == "__main__":
    unittest.main()
