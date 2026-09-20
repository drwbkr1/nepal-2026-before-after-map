from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-apply-orbit-correction-input-resolution-diagnostic-001"
PREPARATION_APPROVAL_REF = f"records/source-gates/{PREFIX}-review-preparation-approval.json"
PROPOSAL_REF = "contracts/milestone-002-radar-apply-orbit-correction-input-resolution-diagnostic-001-proposal.json"
PREFLIGHT_REF = f"records/readiness/{PREFIX}-review-preflight.json"
BUNDLE_REF = f"reviews/{PREFIX}/review-bundle.json"
CONTRACT_REF = f"reviews/{PREFIX}/review-contract.json"
BLANK_REF = f"reviews/{PREFIX}/blank-response.json"
READINESS_REF = f"records/readiness/{PREFIX}-review-readiness.json"
PUBLICATION_APPROVAL_REF = f"records/source-gates/{PREFIX}-review-publication-approval.json"
PUBLICATION_ACTIVATION_REF = f"records/readiness/{PREFIX}-review-publication-activation.json"
PUBLICATION_GATE_REF = f"records/readiness/{PREFIX}-review-publication-gate.json"
PUBLICATION_RECONCILIATION_REF = f"records/readiness/{PREFIX}-review-publication-reconciliation.json"
PROPOSAL_SHA256 = "bb318432bf3a63f2bb75d2b1ea69716b6fbade9917d7c35ff8388d3edaa41d84"
BUNDLE_SHA256 = "88c5e50d2f8f223e1c148caa0212e1b28ba4c80eb3eacae23be7e4f63bd477af"
READINESS_SHA256 = "42c94874b548ac80864138467fc48011e1d8f3a7a41c6721eef34fa5de204513"
PUBLICATION_CHECKPOINT = "M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-REVIEW-PUBLICATION"
REVIEW_CHECKPOINT = "M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-REVIEW"


def load(ref: str) -> dict:
    return json.loads((ROOT / ref).read_text(encoding="utf-8"))


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


class ApplyOrbitCorrectionInputResolutionDiagnostic001ReviewTests(unittest.TestCase):
    def test_preparation_authority_is_exact_and_local_only(self) -> None:
        approval = load(PREPARATION_APPROVAL_REF)
        self.assertEqual(approval["status"], "approved_local_zero_decision_review_preparation_only")
        self.assertEqual(approval["authority_basis"]["owner_response"], "yes")
        self.assertTrue(approval["authority_basis"]["explicit_affirmation"])
        boundary = approval["authority_boundary"]
        self.assertTrue(boundary["local_review_packet_preparation_authorized"])
        self.assertTrue(boundary["local_validation_authorized"])
        for key, value in boundary.items():
            if key not in {"local_review_packet_preparation_authorized", "local_validation_authorized"}:
                self.assertFalse(value, key)

    def test_proposal_is_zero_decision_and_preserves_the_terminal_boundary(self) -> None:
        proposal = load(PROPOSAL_REF)
        self.assertEqual(sha256(PROPOSAL_REF), PROPOSAL_SHA256)
        self.assertEqual(proposal["human_decision_count"], 0)
        observed = proposal["observed_state"]
        self.assertTrue(observed["attempt_terminal_and_consumed"])
        self.assertEqual(observed["source_id_started"], "M1-SRC-001")
        self.assertEqual(observed["orbit_source_id_bound"], "M2-ORB-001")
        self.assertEqual(observed["failing_tool"], "ApplyOrbitCorrection")
        self.assertFalse(observed["later_sources_started"])
        self.assertFalse(observed["route_evaluations_started"])
        self.assertFalse(observed["exact_unresolved_object_identified"])
        self.assertFalse(observed["attempt_root_current_presence_observed"])
        self.assertFalse(observed["historical_root_cause_established"])
        self.assertFalse(observed["radar_recovery_readiness_established"])
        for item in proposal["protected_public_evidence"]:
            self.assertTrue(item["must_remain_unchanged_during_preparation"])
            self.assertEqual(item["sha256"], sha256(item["path"]))

    def test_proposed_diagnostic_is_read_only_and_has_zero_processing_calls(self) -> None:
        diagnostic = load(PROPOSAL_REF)["proposed_diagnostic_contract"]
        self.assertEqual(diagnostic["mode"], "read_only_single_process_no_geoprocessing")
        self.assertEqual(diagnostic["maximum_real_diagnostic_processes"], 1)
        self.assertEqual(diagnostic["maximum_apply_orbit_correction_calls"], 0)
        self.assertEqual(diagnostic["maximum_geoprocessing_tool_calls"], 0)
        self.assertIn("not observed", diagnostic["exact_inputs"]["attempt_root_current_presence"])
        self.assertEqual(
            diagnostic["result_semantics"]["missing_attempt_root_or_candidate_semantics"],
            "terminal block without reconstruction, substitution, copy, or processing",
        )
        self.assertFalse(diagnostic["automatic_retry"])
        for key in (
            "network_requests",
            "credential_actions",
            "source_orbit_or_dem_copies",
            "source_orbit_or_dem_mutations",
            "derived_raster_outputs",
            "baseline_or_change_actions",
            "scientific_outputs",
        ):
            self.assertEqual(diagnostic[key], 0, key)
        self.assertIn("evaluate arcpy.Exists for copied SAFE directory", diagnostic["fixed_check_order"])
        self.assertIn("evaluate arcpy.Exists for copied manifest.safe", diagnostic["fixed_check_order"])
        self.assertIn("evaluate arcpy.Exists for exact orbit EOF", diagnostic["fixed_check_order"])
        self.assertIn("historical root cause", diagnostic["result_semantics"]["pass_does_not_establish"])
        self.assertIn("authorization for a correction or retry", diagnostic["result_semantics"]["pass_does_not_establish"])

    def test_bundle_contract_and_response_remain_closed(self) -> None:
        bundle = load(BUNDLE_REF)
        contract = load(CONTRACT_REF)
        blank = load(BLANK_REF)
        self.assertEqual(sha256(BUNDLE_REF), BUNDLE_SHA256)
        self.assertEqual(bundle["human_decision_count"], 0)
        for item in bundle["artifacts"]:
            self.assertEqual(item["sha256"], sha256(item["path"]))
        self.assertFalse(bundle["decision_requested_after_publication"]["response_open"])
        self.assertEqual(contract["review_bundle"]["manifest_sha256"], BUNDLE_SHA256)
        self.assertFalse(contract["workflow_authority"]["public_review_publication_authorized"])
        self.assertFalse(contract["workflow_authority"]["review_response_open"])
        for value in contract["authority_boundary"].values():
            self.assertFalse(value)
        self.assertFalse(blank["completed"])
        self.assertFalse(blank["reviewer"]["attestation"])
        self.assertIsNone(blank["responses"][0]["decision"])
        self.assertEqual(blank["human_decision_count"], 0)
        self.assertTrue(blank["response_not_open_until_public_ci"])

    def test_readiness_releases_only_local_preparation(self) -> None:
        readiness = load(READINESS_REF)
        preflight = load(PREFLIGHT_REF)
        self.assertEqual(sha256(READINESS_REF), READINESS_SHA256)
        self.assertEqual(readiness["status"], "pass_local_zero_decision_packet_ready_publication_authority_required")
        self.assertEqual(readiness["bindings"]["proposal_sha256"], PROPOSAL_SHA256)
        self.assertEqual(readiness["bindings"]["review_bundle_sha256"], BUNDLE_SHA256)
        self.assertEqual(readiness["validation"]["human_decision_count"], 0)
        self.assertTrue(readiness["released_now"]["local_packet_preparation"])
        self.assertTrue(readiness["released_now"]["local_packet_validation"])
        for key, value in readiness["released_now"].items():
            if key not in {"local_packet_preparation", "local_packet_validation"}:
                self.assertFalse(value, key)
        self.assertEqual(
            preflight["bindings"]["preparation_script_sha256"],
            sha256("scripts/prepare_m2_radar_apply_orbit_correction_input_resolution_diagnostic_001_review.py"),
        )
        for key in (
            "git_commit_created",
            "git_push_performed",
            "public_ci_started",
            "arcpy_invoked",
            "project_data_content_read",
            "external_custody_accessed",
            "apply_orbit_correction_invoked",
            "new_attempt_created",
            "radar_processing_executed",
            "historical_root_cause_established",
            "scientific_result_established",
        ):
            self.assertFalse(preflight["assertions"][key], key)

    def test_publication_authority_and_activation_are_exact_and_narrow(self) -> None:
        approval = load(PUBLICATION_APPROVAL_REF)
        activation = load(PUBLICATION_ACTIVATION_REF)
        self.assertEqual(approval["status"], "approved_exact_zero_decision_review_publication_only")
        self.assertEqual(approval["human_decision_count"], 1)
        self.assertTrue(approval["attestation"])
        self.assertEqual(approval["bindings"]["proposal_sha256"], PROPOSAL_SHA256)
        self.assertEqual(approval["bindings"]["review_bundle_sha256"], BUNDLE_SHA256)
        allowed = {
            "repository_control_integration_authorized",
            "public_default_branch_publication_authorized",
            "public_ci_authorized",
            "post_ci_publication_reconciliation_authorized",
        }
        for key, value in approval["authority_boundary"].items():
            self.assertEqual(value, key in allowed, key)
        self.assertEqual(activation["status"], "pass_exact_publication_authority_activated_public_ci_pending")
        self.assertFalse(activation["released_now"]["diagnostic_implementation"])
        self.assertFalse(activation["released_now"]["arcpy_invocation"])
        self.assertFalse(activation["released_now"]["apply_orbit_correction"])
        self.assertFalse(activation["released_now"]["geoprocessing"])
        self.assertFalse(activation["released_now"]["attempt_root_reconstruction_or_substitution"])
        self.assertFalse(activation["released_now"]["new_radar_attempt"])

    def test_publication_phase_matches_canonical_controls(self) -> None:
        milestone = load("contracts/milestone-002.json")
        profile = load("records/project-control-profile.json")
        goal = load("records/long-term-goal.json")
        gate_exists = (ROOT / PUBLICATION_GATE_REF).is_file()
        expected = profile["current_checkpoint"]["checkpoint_id"]
        self.assertTrue(
            expected.startswith("M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-")
            or expected.startswith(
                "M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-"
            )
        )
        self.assertEqual(milestone["handoff"]["current_checkpoint"], expected)
        self.assertEqual(goal["current_checkpoint"], expected)
        if gate_exists:
            gate = load(PUBLICATION_GATE_REF)
            reconciliation = load(PUBLICATION_RECONCILIATION_REF)
            self.assertEqual(gate["status"], "pass_public_default_branch_ci_zero_decision_owner_review_ready")
            self.assertTrue(gate["released_now"]["owner_proposal_review"])
            self.assertFalse(gate["released_now"]["diagnostic_implementation"])
            self.assertEqual(reconciliation["current_checkpoint"], REVIEW_CHECKPOINT)

    def test_publication_scripts_are_control_plane_only(self) -> None:
        for ref in (
            "scripts/integrate_m2_radar_apply_orbit_correction_input_resolution_diagnostic_001_review_publication.py",
            "scripts/record_m2_radar_apply_orbit_correction_input_resolution_diagnostic_001_review_publication.py",
        ):
            source = (ROOT / ref).read_text(encoding="utf-8")
            self.assertNotIn("import arcpy", source)
            self.assertNotIn("from arcpy", source)
            self.assertNotIn("ApplyOrbitCorrection(", source)


if __name__ == "__main__":
    unittest.main()
