from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from derive_m2_acquisition_checkpoint import (  # noqa: E402
    current_radar_pixel_orbit_application_001_execution_pending,
    current_radar_pixel_orbit_application_001_implementation_active,
    current_radar_pixel_orbit_application_001_review_publication_pending,
    current_radar_pixel_orbit_application_001_review_required,
)


PROPOSAL_REF = "contracts/milestone-002-radar-pixel-orbit-application-001-proposal.json"
CANDIDATE_REF = "records/readiness/m2-radar-pixel-orbit-application-001-candidate-manifest.json"
AUDIT_REF = "records/readiness/m2-radar-pixel-orbit-application-001-readiness-audit.json"
BUNDLE_REF = "reviews/m2-radar-pixel-orbit-application-001/review-bundle.json"
CONTRACT_REF = "reviews/m2-radar-pixel-orbit-application-001/review-contract.json"
BLANK_REF = "reviews/m2-radar-pixel-orbit-application-001/blank-response.json"
READINESS_REF = "records/readiness/m2-radar-pixel-orbit-application-001-review-readiness.json"
PUBLICATION_REF = "records/readiness/m2-radar-pixel-orbit-application-001-review-publication-gate.json"
RECONCILIATION_REF = "records/readiness/m2-radar-pixel-orbit-application-001-review-publication-reconciliation.json"
PROPOSAL_SHA256 = "3a0f03c5269f4e3e6822c1e31bbe5f19cd288e9e17db67b42990d96b27a4f490"
BUNDLE_SHA256 = "84af38b7e325e862272b97c9f198dc7a3c3aa2371f4c428e36aaaac6e937f633"
CANDIDATE_SHA256 = "dc4ff8a70c3eb115ee78069afbfd759cc1532fce58de6970584d6b7e5fa34af7"


def load(ref: str) -> dict:
    return json.loads((ROOT / ref).read_text(encoding="utf-8"))


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


class M2RadarPixelOrbitApplication001ReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate = load(CANDIDATE_REF)
        cls.audit = load(AUDIT_REF)
        cls.proposal = load(PROPOSAL_REF)
        cls.bundle = load(BUNDLE_REF)
        cls.contract = load(CONTRACT_REF)
        cls.blank = load(BLANK_REF)
        cls.readiness = load(READINESS_REF)
        cls.capability = load("records/surface-receipts/m2-radar-pixel-orbit-application-001-capability.json")
        cls.milestone = load("contracts/milestone-002.json")
        cls.profile = load("records/project-control-profile.json")
        cls.goal = load("records/long-term-goal.json")

    def test_exact_candidate_binds_six_sources_four_orbits_and_four_dems(self) -> None:
        self.assertEqual(sha256(CANDIDATE_REF), CANDIDATE_SHA256)
        self.assertEqual([item["source_id"] for item in self.candidate["sentinel_sources"]], [f"M1-SRC-{index:03d}" for index in range(1, 7)])
        self.assertEqual([item["source_id"] for item in self.candidate["orbit_inputs"]], [f"M2-ORB-{index:03d}" for index in range(1, 5)])
        self.assertEqual([item["source_id"] for item in self.candidate["dem_inputs"]], [f"M2-DEM-{index:03d}" for index in range(1, 5)])
        observed = self.candidate["current_observations"]
        for key in ("measurement_pixels_decoded", "orbit_application_started", "terrain_processing_started", "masked_aoi_coverage_measured", "registration_measured", "baseline_established", "change_established"):
            self.assertFalse(observed[key])

    def test_readiness_audit_is_defer_and_does_not_create_authority(self) -> None:
        self.assertEqual(self.audit["decision"], "defer")
        statuses = {gate["gate_id"]: gate["status"] for gate in self.audit["gates"]}
        self.assertEqual(statuses["source-and-terms"], "pass")
        self.assertEqual(statuses["provenance-and-custody"], "pass")
        self.assertEqual(statuses["schema-and-quality"], "defer")
        self.assertEqual(statuses["coverage-and-balance"], "defer")
        self.assertEqual(statuses["reproducibility"], "defer")
        self.assertFalse(self.audit["authority_boundary"]["this_audit_creates_authority"])
        self.assertEqual(self.audit["authority_boundary"]["authorized_actions"], [])

    def test_proposal_freezes_dependency_order_and_attempt_limits(self) -> None:
        self.assertEqual(sha256(PROPOSAL_REF), PROPOSAL_SHA256)
        self.assertEqual(self.proposal["status"], "proposed_inactive_owner_review_required")
        self.assertEqual(self.proposal["fixed_sequence"]["source_ids"], [f"M1-SRC-{index:03d}" for index in range(1, 7)])
        self.assertEqual(self.proposal["fixed_sequence"]["route_ids"], ["PAIR-S1-ASC-R085-IW", "PAIR-S1-DESC-R121-IW"])
        limits = self.proposal["limits"]
        self.assertEqual(limits["orbit_application_attempts_per_source"], 1)
        self.assertEqual(limits["qa_processing_attempts_per_source"], 1)
        self.assertEqual(limits["route_qa_attempts_per_pair"], 1)
        self.assertEqual(limits["network_requests"], 0)
        self.assertEqual(limits["source_overwrites"], 0)
        self.assertEqual(limits["output_overwrites"], 0)
        self.assertFalse(limits["automatic_retry"])
        self.assertTrue(limits["stop_on_execution_failure"])
        self.assertTrue(limits["continue_independent_route_disposition_after_scientific_block_or_defer"])

    def test_bundle_contract_and_response_are_exact_and_blank(self) -> None:
        self.assertEqual(sha256(BUNDLE_REF), BUNDLE_SHA256)
        self.assertEqual(self.bundle["human_decision_count"], 0)
        for artifact in self.bundle["artifacts"]:
            self.assertEqual(artifact["sha256"], sha256(artifact["path"]))
            for receipt in artifact["render_receipts"]:
                self.assertEqual(receipt["sha256"], sha256(receipt["path"]))
        self.assertEqual(self.contract["review_bundle"]["manifest_sha256"], BUNDLE_SHA256)
        self.assertTrue(self.contract["required_attestation"])
        self.assertFalse(self.blank["completed"])
        self.assertFalse(self.blank["reviewer"]["attestation"])
        self.assertIsNone(self.blank["responses"][0]["decision"])
        self.assertEqual(self.blank["responses"][0]["evidence_sha256"], BUNDLE_SHA256)

    def test_capability_and_review_preparation_read_no_project_content(self) -> None:
        self.assertEqual(self.capability["status"], "pass_installed_runtime_capability_only_no_project_data_read")
        self.assertTrue(self.capability["checks"]["all_required_signatures_match"])
        for key in ("project_sentinel_content_read", "project_orbit_content_read", "project_dem_content_read", "processing_executed", "network_request_performed"):
            self.assertFalse(self.capability["checks"][key])
        for key in ("orbit_application_authorized", "radar_pixel_processing_authorized", "baseline_or_change_authorized", "project_data_content_read_during_preparation", "network_requests_performed", "external_custody_mutated", "scientific_result_established"):
            self.assertFalse(self.readiness["assertions"][key])

    def test_control_state_matches_terminal_block(self) -> None:
        published = (ROOT / PUBLICATION_REF).exists()
        checkpoint = json.loads((ROOT / "records/project-control-profile.json").read_text(encoding="utf-8"))["current_checkpoint"]["checkpoint_id"]
        self.assertEqual(self.profile["current_checkpoint"]["checkpoint_id"], checkpoint)
        self.assertEqual(self.goal["current_checkpoint"], checkpoint)
        self.assertEqual(self.milestone["handoff"]["current_checkpoint"], checkpoint)
        pending_recovery = []
        self.assertEqual(self.goal["proposed_amendments"], pending_recovery)
        self.assertEqual(self.profile["control_surfaces"]["proposed_amendments"], pending_recovery)
        self.assertEqual(self.goal["active_amendments"][-1], "records/source-gates/m2-radar-apply-orbit-correction-input-resolution-diagnostic-001-approval.json")
        self.assertEqual(self.profile["control_surfaces"]["activated_amendments"][-1], "records/source-gates/m2-radar-apply-orbit-correction-input-resolution-diagnostic-001-approval.json")
        if published:
            publication = load(PUBLICATION_REF)
            reconciliation = load(RECONCILIATION_REF)
            self.assertEqual(publication["status"], "pass_public_default_branch_ci_zero_decision_review_ready")
            self.assertEqual(publication["public_ci_conclusion"], "success")
            self.assertEqual(publication["commit_sha"], "14b796cfc95d9fd77fdc33d56354c949681ef09d")
            self.assertEqual(publication["public_ci_run_id"], 35389407797)
            self.assertEqual(publication["repository_required_file_count"], 980)
            self.assertEqual(publication["public_test_count"], 552)
            self.assertEqual(publication["public_intentional_skip_count"], 13)
            self.assertEqual(reconciliation["status"], "pass_public_gate_owner_review_ready")
            self.assertEqual(reconciliation["publication_gate_sha256"], sha256(PUBLICATION_REF))
            self.assertTrue(reconciliation["released_now"]["owner_review"])
            for key in ("implementation", "project_data_content_read", "orbit_application", "radar_pixel_processing", "baseline_or_change_analysis", "scientific_publication"):
                self.assertFalse(reconciliation["released_now"][key])
            self.assertFalse(current_radar_pixel_orbit_application_001_review_required(ROOT, {"promoted": 8}))
            self.assertFalse(current_radar_pixel_orbit_application_001_review_publication_pending(ROOT, {"promoted": 8}))
            self.assertFalse(current_radar_pixel_orbit_application_001_implementation_active(ROOT, {"promoted": 8}))
            self.assertFalse(current_radar_pixel_orbit_application_001_execution_pending(ROOT, {"promoted": 8}))
        else:
            self.assertTrue(current_radar_pixel_orbit_application_001_review_publication_pending(ROOT, {"promoted": 8}))
            self.assertFalse(current_radar_pixel_orbit_application_001_review_required(ROOT, {"promoted": 8}))

    def test_milestone_review_unit_records_exact_approval_and_limited_release(self) -> None:
        units = {unit["id"]: unit for unit in self.milestone["units"]}
        review = units["M2-RADAR-PIXEL-ORBIT-APPLICATION-001-REVIEW"]
        implementation = units["M2-RADAR-PIXEL-ORBIT-APPLICATION-001-IMPLEMENTATION"]
        execution = units["M2-RADAR-PIXEL-ORBIT-APPLICATION-001-EXECUTION"]
        self.assertEqual(review["status"], "complete")
        self.assertEqual(review["disposition"], "pass")
        self.assertTrue(review["human_gate"])
        self.assertEqual(review["gates"]["human_decision_count"], 1)
        self.assertTrue(review["gates"]["attestation"])
        self.assertTrue(review["gates"]["route_authorized"])
        self.assertFalse(review["gates"]["baseline_or_change_authorized"])
        self.assertEqual(implementation["status"], "complete")
        self.assertEqual(implementation["disposition"], "pass")
        self.assertEqual(implementation["gates"]["public_ci"], "success")
        self.assertFalse(implementation["gates"]["project_data_content_read"])
        self.assertFalse(implementation["gates"]["orbit_application_started"])
        self.assertEqual(execution["status"], "complete")
        self.assertEqual(execution["disposition"], "block")
        self.assertEqual(execution["gates"]["public_ci"], "success")
        self.assertEqual(execution["gates"]["gate_record_publication"], "success")
        self.assertEqual(execution["gates"]["final_no_content_preflight"], "pass")
        self.assertEqual(execution["gates"]["gate_state_public_ci_run_id"], 35396191631)
        self.assertEqual(execution["gates"]["source_attempts_started"], 0)
        self.assertEqual(execution["gates"]["real_attempts_started"], 1)
        self.assertFalse(execution["gates"]["source_processing_started"])


if __name__ == "__main__":
    unittest.main()
