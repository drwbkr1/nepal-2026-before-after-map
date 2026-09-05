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

    def test_active_intake_preserves_four_approved_tiles_during_progress(self) -> None:
        self.assertIn(
            self.active_intake["extensions"]["status"],
            {
                "active_authorized_preflight_passed_custody_initialized",
                "active_acquisition_in_progress",
                "active_acquisition_review_required",
                "active_all_promoted_pending_geotiff_verification",
                "active_geotiff_verified_vertical_datum_deferred",
            },
        )
        self.assertEqual(len(self.active_intake["assets"]), 4)
        self.assertEqual(
            {asset["extensions"]["source_id"] for asset in self.active_intake["assets"]},
            {"M2-DEM-001", "M2-DEM-002", "M2-DEM-003", "M2-DEM-004"},
        )
        self.assertTrue(all(asset["state"] in {"authorized", "promoted", "failed"} for asset in self.active_intake["assets"]))
        self.assertFalse(any(asset["state"] == "staging" for asset in self.active_intake["assets"]))
        for asset in self.active_intake["assets"]:
            if asset["state"] == "authorized":
                self.assertEqual(asset["attempts"], [])
            else:
                self.assertEqual(len(asset["attempts"]), 1)
                self.assertIn(asset["attempts"][0]["outcome"], {"succeeded", "failed"})
        self.assertTrue(
            all(
                asset["source"]["authorization_ref"]
                == "records/source-gates/m2-dem-amendment-approval.json"
                for asset in self.active_intake["assets"]
            )
        )

    def test_active_offline_verification_is_authorized_but_data_deferred(self) -> None:
        self.assertIn(
            self.active_verification["status"],
            {
                "active_gate_deferred_no_promoted_rasters",
                "active_gate_deferred_incomplete_acquisition",
                "active_gate_blocked_acquisition_review",
                "active_gate_ready_for_geotiff_verification",
                "complete_structural_and_valid_coverage_vertical_datum_deferred",
            },
        )
        authority = self.active_verification["authority"]
        self.assertEqual(authority["dem_amendment_status"], "approved")
        self.assertTrue(authority["license_acceptance_established"])
        self.assertTrue(authority["dem_pixel_processing_authorized"])
        self.assertFalse(authority["network_access_authorized"])
        self.assertFalse(authority["custody_mutation_authorized"])
        self.assertFalse(authority["dem_download_authorized"])
        self.assertFalse(authority["this_contract_creates_authority"])
        self.assertEqual(self.active_verification["inputs"]["intake_contract_sha256"], sha256("contracts/m2-dem-intake.json"))

    def test_milestone_and_profile_preserve_parallel_dem_route(self) -> None:
        units = {unit["id"]: unit for unit in self.milestone["units"]}
        all_promoted = all(asset["state"] == "promoted" for asset in self.active_intake["assets"])
        all_verified = all(
            asset["extensions"].get("geotiff_verification_status") == "pass_structural_and_full_tile_finite"
            for asset in self.active_intake["assets"]
        )
        expected_checkpoint = "M2-DEM-VERTICAL-DATUM-REVIEW" if all_verified else ("M2-DEM-GEOTIFF-VERIFICATION" if all_promoted else "M2-DEM-ACQUISITION")
        self.assertEqual(units["M2-DEM-AMEND"]["status"], "complete")
        self.assertEqual(units["M2-DEM-PREFLIGHT"]["status"], "complete")
        self.assertEqual(units["M2-DEM-ACQUIRE"]["status"], "complete" if all_promoted else "ready")
        self.assertEqual(units["M2-DEM-VERIFY"]["status"], "complete" if all_verified else ("ready" if all_promoted else "planned"))
        self.assertEqual(set(units["M2-BASELINE"]["depends_on"]), {"M2-VERIFY", "M2-DEM-VERIFY", "M2-ORBIT-APPLY"})
        self.assertEqual(
            self.profile["control_surfaces"]["proposed_amendments"],
            ["contracts/milestone-002-radar-first-path-001-proposal.json"],
        )
        self.assertEqual(
            self.profile["control_surfaces"]["activated_amendments"],
            [
                "records/source-gates/m2-dem-amendment-approval.json",
                "records/source-gates/m2-orbit-amendment-approval.json",
                "records/source-gates/m2-radar-input-readiness-amendment-approval.json",
                "records/source-gates/m2-sentinel-recovery-002-approval.json",
                "records/source-gates/m2-sentinel-continuation-001-approval.json",
                "records/source-gates/m2-materialization-pixel-readiness-approval.json",
                "records/source-gates/m2-optical-pixel-recovery-001-approval.json",
            ],
        )
        primary_intake = load("contracts/m2-intake.json")
        continuation_review = next(
            (unit for unit in self.milestone["units"] if unit["id"] == "M2-SENTINEL-CONTINUATION-001-REVIEW"),
            None,
        )
        verify_unit = next(
            (unit for unit in self.milestone["units"] if unit["id"] == "M2-VERIFY"),
            None,
        )
        materialization_review = next(
            (unit for unit in self.milestone["units"] if unit["id"] == "M2-MATERIALIZATION-PIXEL-READINESS-REVIEW"),
            None,
        )
        full_header = next(
            (unit for unit in self.milestone["units"] if unit["id"] == "M2-FULL-INPUT-READINESS"),
            None,
        )
        optical_pixel = next(
            (unit for unit in self.milestone["units"] if unit["id"] == "M2-OPTICAL-PIXEL-READINESS"),
            None,
        )
        optical_recovery_review = next(
            (unit for unit in self.milestone["units"] if unit["id"] == "M2-OPTICAL-PIXEL-RECOVERY-001-REVIEW"),
            None,
        )
        optical_recovery_implementation = next(
            (unit for unit in self.milestone["units"] if unit["id"] == "M2-OPTICAL-PIXEL-RECOVERY-001-IMPLEMENTATION"),
            None,
        )
        optical_recovery = next(
            (unit for unit in self.milestone["units"] if unit["id"] == "M2-OPTICAL-PIXEL-RECOVERY-001"),
            None,
        )
        radar_first_path_review = next(
            (unit for unit in self.milestone["units"] if unit["id"] == "M2-RADAR-FIRST-PATH-001-REVIEW"),
            None,
        )
        expected_primary_checkpoint = (
            "M2-RADAR-FIRST-PATH-001-REVIEW"
            if radar_first_path_review is not None and radar_first_path_review.get("status") == "ready"
            else "M2-OPTICAL-PIXEL-RECOVERY-001"
            if optical_recovery is not None and optical_recovery.get("status") == "complete"
            else "M2-OPTICAL-PIXEL-RECOVERY-001-IMPLEMENTATION"
            if optical_recovery_implementation is not None and optical_recovery_implementation.get("status") == "in_progress"
            else "M2-OPTICAL-PIXEL-RECOVERY-001-REVIEW"
            if optical_recovery_review is not None and optical_recovery_review.get("status") == "ready"
            else
            "M2-OPTICAL-PIXEL-READINESS"
            if optical_pixel is not None and optical_pixel.get("status") == "in_progress"
            else
            "M2-FULL-INPUT-READINESS"
            if full_header is not None and full_header.get("status") == "in_progress"
            else
            "M2-MATERIALIZATION-PIXEL-READINESS-IMPLEMENTATION"
            if all(asset.get("state") == "promoted" for asset in primary_intake["assets"])
            and materialization_review is not None
            and materialization_review.get("status") == "complete"
            else
            "M2-MATERIALIZATION-PIXEL-READINESS-REVIEW"
            if all(asset.get("state") == "promoted" for asset in primary_intake["assets"])
            and materialization_review is not None
            and materialization_review.get("status") == "ready"
            else "M2-VERIFY"
            if all(asset.get("state") == "promoted" for asset in primary_intake["assets"])
            and verify_unit is not None
            and verify_unit.get("status") in {"in_progress", "deferred"}
            else "M2-ACQUISITION-REVIEW"
            if any(asset.get("state") == "failed" for asset in primary_intake["assets"])
            or continuation_review is not None and continuation_review.get("status") in {"ready", "complete"}
            else "M2-ACQUISITION-IN-PROGRESS"
        )
        self.assertEqual(self.profile["current_checkpoint"]["checkpoint_id"], expected_primary_checkpoint)
        self.assertEqual(self.profile["parallel_checkpoints"][0]["checkpoint_id"], expected_checkpoint)
        self.assertEqual(self.profile["parallel_checkpoints"][1]["checkpoint_id"], "M2-DEM-TERRAIN-RESULT-REVIEW")
        self.assertEqual(
            self.goal["parallel_checkpoints"],
            [expected_checkpoint, "M2-DEM-TERRAIN-RESULT-REVIEW"],
        )

    def test_activation_receipt_preserves_published_outputs_and_claim_boundary(self) -> None:
        self.assertEqual(self.receipt["status"], "pass_exact_dem_amendment_activated_preflight_pending")
        self.assertEqual(
            self.receipt["bindings"],
            {
                "reconciliation_ref": "records/source-gates/m2-dem-amendment-review-reconciliation.json",
                "reconciliation_sha256": "9d72c9786440da0c9149340cd69361b12e55f0d7dff88972bfd02ee0da5460e1",
                "approval_ref": "records/source-gates/m2-dem-amendment-approval.json",
                "approval_sha256": "6d1fc7e05854bc149ace177d89e84a7651cc049efd530cab650a9464222769d0",
                "active_intake_ref": "contracts/m2-dem-intake.json",
                "active_intake_sha256": "0fa00a4be01d3caddac28088d2d3d714040d1258b33497ebee50cbb0b8b3b5b6",
                "active_verification_ref": "contracts/m2-dem-offline-verification.json",
                "active_verification_sha256": "755bdb1fd1916d68289f5266912f8bb7f25462b512ce7cfc27a49feb44bcef42",
                "active_milestone_ref": "contracts/milestone-002.json",
                "active_milestone_sha256": "fc764ba8513c05e518096e8864ba0ec49507ca924f2474637adccef31275a6cf",
                "project_profile_ref": "records/project-control-profile.json",
                "project_profile_sha256": "dd07dec7c68fbd9e486ad96e1a34dbd66266409609db05419a6eb78d723bc844",
                "long_term_goal_ref": "records/long-term-goal.json",
                "long_term_goal_sha256": "81f5b742b8aa3e829253317faa9c6017c8c93a6deb1d10a3f6cb96c7b55c44e8",
                "activation_script_ref": "scripts/activate_m2_dem_amendment.py",
                "activation_script_sha256": "a4cc4f86b0beb81f151ccdc0bc4a4ab5d674823d7c7a5879f0e223efcd36d256",
            },
        )
        assertions = self.receipt["assertions"]
        self.assertTrue(assertions["exact_license_accepted"])
        self.assertEqual(assertions["authorized_dem_tile_count"], 4)
        self.assertFalse(assertions["network_requests_performed"])
        self.assertFalse(assertions["dem_payload_bytes_requested"])
        self.assertFalse(assertions["dem_pixels_examined"])

    def test_evidence_0031_binds_activation_without_pixel_claim(self) -> None:
        evidence = next(record for record in self.ledger if record.get("record_id") == "EVID-0031")
        self.assertEqual(evidence["status"], "pass_exact_dem_amendment_activated_preflight_pending")
        self.assertEqual(evidence["activation_receipt_sha256"], "76e4233efd4dfd2d75a6873504646558eb4a16cd1f069060f91f0194c40c63d9")
        self.assertEqual(evidence["active_intake_sha256"], "0fa00a4be01d3caddac28088d2d3d714040d1258b33497ebee50cbb0b8b3b5b6")
        self.assertEqual(evidence["active_verification_sha256"], "755bdb1fd1916d68289f5266912f8bb7f25462b512ce7cfc27a49feb44bcef42")
        for ref_key, hash_key in (("activation_receipt_ref", "activation_receipt_sha256"), ("approval_ref", "approval_sha256"), ("reconciliation_ref", "reconciliation_sha256"), ("activation_script_ref", "activation_script_sha256")):
            self.assertEqual(evidence[hash_key], sha256(evidence[ref_key]))
        self.assertFalse(evidence["assertions"]["dem_pixels_examined"])
        self.assertFalse(evidence["assertions"]["scientific_result_established"])


if __name__ == "__main__":
    unittest.main()
