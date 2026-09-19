from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACCESS_REF = "records/readiness/m2-dem-egm2008-component-access-closure-001.json"
SOURCE_REF = "records/source-gates/m2-dem-vertical-datum-alternate-method-001-source-review.json"
PROPOSAL_REF = "contracts/m2-dem-vertical-datum-alternate-method-001-proposal.json"
BUNDLE_REF = "reviews/m2-dem-vertical-datum-alternate-method-001/review-bundle.json"
CONTRACT_REF = "reviews/m2-dem-vertical-datum-alternate-method-001/review-contract.json"
BLANK_REF = "reviews/m2-dem-vertical-datum-alternate-method-001/blank-response.json"
READINESS_REF = "records/readiness/m2-dem-vertical-datum-alternate-method-001-review-readiness.json"
LOCAL_VALIDATION_REF = "records/readiness/m2-dem-vertical-datum-alternate-method-001-local-validation.json"
PUBLICATION_REF = "records/readiness/m2-dem-vertical-datum-alternate-method-001-review-publication-gate.json"
CHECKPOINT = "M2-DEM-VERTICAL-DATUM-ALTERNATE-METHOD-001-REVIEW"


def load(ref: str) -> dict:
    return json.loads((ROOT / ref).read_text(encoding="utf-8"))


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


class DemVerticalDatumAlternateMethod001ReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.access = load(ACCESS_REF)
        cls.sources = load(SOURCE_REF)
        cls.proposal = load(PROPOSAL_REF)
        cls.bundle = load(BUNDLE_REF)
        cls.contract = load(CONTRACT_REF)
        cls.blank = load(BLANK_REF)
        cls.readiness = load(READINESS_REF)
        cls.local_validation = load(LOCAL_VALIDATION_REF)
        cls.publication = load(PUBLICATION_REF)
        cls.milestone = load("contracts/milestone-002.json")
        cls.profile = load("records/project-control-profile.json")
        cls.goal = load("records/long-term-goal.json")

    def test_esri_path_is_closed_without_rewriting_prior_approval(self) -> None:
        self.assertEqual(self.access["status"], "closed_owner_report_and_fresh_machine_reinspection")
        self.assertFalse(self.access["owner_report"]["private_helpdesk_content_recorded"])
        self.assertFalse(self.access["fresh_machine_reinspection"]["expected_transformation_available"])
        self.assertEqual(self.access["fresh_machine_reinspection"]["matching_egm2008_grids"], [])
        self.assertEqual(self.access["reconciliation"]["approved_esri_route_status"], "unavailable_preserved_as_historical_selected_method")
        self.assertFalse(self.access["reconciliation"]["route_substitution_authorized"])

    def test_redirect_partial_is_terminal_unusable_and_not_selected(self) -> None:
        partial = self.access["accidental_sourceforge_redirect"]
        self.assertEqual(partial["bytes_received"], 11321072)
        self.assertEqual(partial["partial_sha256"], "7c0a8597880f622554f6b84355e9587b8b9619e0010247e32ac61ecdd67f7734")
        self.assertFalse(partial["promoted"])
        self.assertFalse(partial["usable"])
        self.assertFalse(partial["retry_authorized"])
        self.assertFalse(partial["selected_for_production"])

    def test_recommended_proj_grid_has_exact_open_identity(self) -> None:
        candidate = self.sources["recommended_candidate"]
        self.assertEqual(candidate["name"], "us_nga_egm08_25.tif")
        self.assertEqual(candidate["content_length_bytes"], 80585622)
        self.assertEqual(candidate["sha256"], "4191d471eefebf24091b56dbc604353cb3b8cf8cc70e448bb9ae56a272bef17a")
        self.assertEqual(candidate["license"], "Public Domain")
        self.assertEqual(candidate["source_crs"], "EPSG:4979")
        self.assertEqual(candidate["target_crs"], "EPSG:3855")
        self.assertEqual(candidate["payload_bytes_read_during_review"], 0)
        self.assertFalse(self.sources["assertions"]["recommended_grid_payload_downloaded"])

    def test_proposal_exposes_material_method_change_and_fail_closed_sequence(self) -> None:
        self.assertEqual(self.proposal["status"], "proposed_not_authorized")
        self.assertEqual(self.proposal["decision_requested"]["recommended_route"], "local_proj_egm2008_2_5_preconversion_then_none")
        self.assertIn("grid spacing changes", " ".join(self.proposal["material_change_from_prior_approval"]["changed"]))
        bounded = self.proposal["bounded_execution_if_approved"]
        self.assertEqual(bounded["maximum_grid_requests"], 1)
        self.assertEqual(bounded["maximum_conversion_attempts_per_dem"], 1)
        self.assertFalse(bounded["automatic_retry"])
        self.assertTrue(bounded["stop_on_first_failure"])
        self.assertFalse(bounded["proj_network_enabled"])
        prohibited = " ".join(self.proposal["actions_not_authorized"])
        for phrase in ("quarantined GeographicLib partial", "software", "overwrite", "radar measurement pixels", "scientific claim"):
            self.assertIn(phrase, prohibited)

    def test_review_bundle_contract_and_blank_bind_exact_bytes(self) -> None:
        proposal_sha = sha256(PROPOSAL_REF)
        bundle_sha = sha256(BUNDLE_REF)
        self.assertEqual(proposal_sha, "dd920e205cb34f812dbbed422909acd9d3357d2f7b53f6843eccf03259e226d7")
        self.assertEqual(bundle_sha, "caa27cad02aa78caeb38c511ea3cae7ebb637833bd4d54881b8a557a38eb1702")
        self.assertEqual(self.bundle["candidate_identity"], f"M2-DEM-VERTICAL-DATUM-ALTERNATE-METHOD-001-PROPOSAL-SHA256:{proposal_sha}")
        for artifact in self.bundle["artifacts"]:
            self.assertEqual(artifact["sha256"], sha256(artifact["path"]))
            for receipt in artifact["render_receipts"]:
                self.assertEqual(receipt["sha256"], sha256(receipt["path"]))
        self.assertEqual(self.contract["review_bundle"]["manifest_sha256"], bundle_sha)
        self.assertEqual(self.blank["responses"][0]["evidence_sha256"], bundle_sha)

    def test_review_is_zero_decision_and_releases_no_action(self) -> None:
        self.assertFalse(self.blank["completed"])
        self.assertFalse(self.blank["reviewer"]["attestation"])
        self.assertIsNone(self.blank["responses"][0]["decision"])
        self.assertEqual(self.readiness["status"], "pass_ready_owner_review_zero_decisions")
        self.assertEqual(self.readiness["review"]["human_decision_count"], 0)
        for key in ("alternate_method_authorized", "grid_acquisition_authorized", "dem_conversion_authorized", "radar_processing_authorized", "scientific_result_established"):
            self.assertFalse(self.readiness["assertions"][key])

    def test_current_controls_preserve_review_and_activate_bounded_implementation(self) -> None:
        units = {unit["id"]: unit for unit in self.milestone["units"]}
        install = units["M2-DEM-EGM2008-COMPONENT-INSTALL"]
        review = units[CHECKPOINT]
        implementation_checkpoint = "M2-DEM-VERTICAL-DATUM-ALTERNATE-METHOD-001-IMPLEMENTATION"
        current_checkpoint = "M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-EXECUTION"
        implementation = units[implementation_checkpoint]
        acquisition = units["M2-DEM-EGM2008-PROJ25-ACQUISITION"]
        conversion = units["M2-DEM-VERTICAL-DATUM-CONVERSION"]
        self.assertEqual(install["status"], "complete")
        self.assertEqual(install["disposition"], "block")
        self.assertEqual(install["next_dependency"], CHECKPOINT)
        self.assertEqual(review["status"], "complete")
        self.assertEqual(review["disposition"], "pass")
        self.assertTrue(review["human_gate"])
        self.assertEqual(review["gates"]["human_decision_count"], 1)
        self.assertTrue(review["gates"]["attestation"])
        self.assertTrue(review["gates"]["alternate_method_authorized"])
        self.assertEqual(implementation["status"], "complete")
        self.assertEqual(implementation["disposition"], "pass_public_default_branch_ci")
        self.assertEqual(acquisition["status"], "complete")
        self.assertEqual(acquisition["disposition"], "block_terminal_metadata_representation_mismatch")
        self.assertEqual(conversion["depends_on"], ["M2-DEM-PROJ25-RECEIPT-PERSISTENCE-RECOVERY-002-IMPLEMENTATION"])
        self.assertEqual(self.milestone["handoff"]["current_checkpoint"], current_checkpoint)
        self.assertEqual(self.profile["current_checkpoint"]["checkpoint_id"], current_checkpoint)
        self.assertEqual(self.goal["current_checkpoint"], current_checkpoint)
        expected_proposal = []
        self.assertEqual(self.profile["control_surfaces"]["proposed_amendments"], expected_proposal)
        self.assertEqual(self.goal["proposed_amendments"], expected_proposal)
        self.assertIn("records/source-gates/m2-dem-vertical-datum-alternate-method-001-approval.json", self.goal["active_amendments"])

    def test_local_validation_preserves_initial_failure_and_corrected_pass(self) -> None:
        attempts = self.local_validation["attempts"]
        self.assertEqual(self.local_validation["status"], "pass_after_preserved_checkpoint_expectation_failure")
        self.assertEqual((attempts[0]["test_count"], attempts[0]["failure_count"]), (506, 6))
        self.assertEqual((attempts[1]["test_count"], attempts[1]["failure_count"]), (506, 0))
        self.assertEqual((attempts[2]["test_count"], attempts[2]["failure_count"]), (507, 0))
        self.assertTrue(self.local_validation["assertions"]["initial_failure_preserved"])
        self.assertTrue(self.local_validation["assertions"]["corrected_full_suite_passed"])
        self.assertTrue(self.local_validation["assertions"]["final_full_suite_passed"])

    def test_public_packet_passed_default_branch_ci_without_releasing_action(self) -> None:
        self.assertEqual(self.publication["commit_sha"], "847501b227de4d258309c5909e5333bd8e824947")
        self.assertEqual(self.publication["public_ci_run_id"], 35297712043)
        self.assertEqual(self.publication["public_ci_conclusion"], "success")
        self.assertEqual(self.publication["public_test_count"], 507)
        self.assertEqual(self.publication["assertions"]["human_decision_count"], 0)
        self.assertFalse(self.publication["assertions"]["alternate_method_authorized"])


if __name__ == "__main__":
    unittest.main()
