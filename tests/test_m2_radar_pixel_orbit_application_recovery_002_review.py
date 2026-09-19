from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-pixel-orbit-application-recovery-002"
PROPOSAL_REF = "contracts/milestone-002-radar-pixel-orbit-application-recovery-002-proposal.json"
APPROVAL_REF = f"records/source-gates/{PREFIX}-review-preparation-approval.json"
PUBLICATION_APPROVAL_REF = f"records/source-gates/{PREFIX}-review-publication-approval.json"
PUBLICATION_ACTIVATION_REF = f"records/readiness/{PREFIX}-review-publication-activation.json"
PUBLICATION_GATE_REF = f"records/readiness/{PREFIX}-review-publication-gate.json"
PUBLICATION_RECONCILIATION_REF = f"records/readiness/{PREFIX}-review-publication-reconciliation.json"
PREFLIGHT_REF = f"records/readiness/{PREFIX}-review-preflight.json"
IMAGE_REF = f"docs/assets/{PREFIX}-review.png"
SURFACE_REF = f"records/surface-receipts/{PREFIX}-review.json"
VISUAL_REF = f"records/surface-receipts/{PREFIX}-review-visual-inspection.json"
BUNDLE_REF = f"reviews/{PREFIX}/review-bundle.json"
CONTRACT_REF = f"reviews/{PREFIX}/review-contract.json"
BLANK_REF = f"reviews/{PREFIX}/blank-response.json"
READINESS_REF = f"records/readiness/{PREFIX}-review-readiness.json"

PROPOSAL_SHA256 = "86366bca8681bbe90dfdd19d6c5b676e490e6dd87c8e04c2900e9fb1df4b29ca"
BUNDLE_SHA256 = "e699dfc3c4f7dd5ca697581cf4a299c66128fda7691473d65749681e3dfc211c"
READINESS_SHA256 = "c5035d74504543f408099343a149a0c9b3317eaacaed767c47faa395d25f6bd4"
IMAGE_SHA256 = "383fae06f1cf147fec1a7e9f7820b1d2456cf5e211124548ef573063045a2aeb"
VISUAL_SHA256 = "472ef8c3cf99e2a14e86c4944e621cc0b51a0b045b8f07f6c2eb9d34497e3dd4"
CURRENT_CHECKPOINT = "M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-002-TERMINAL-REVIEW"
SOURCE_ORDER = [f"M1-SRC-{index:03d}" for index in range(1, 7)]
ROUTE_ORDER = ["PAIR-S1-ASC-R085-IW", "PAIR-S1-DESC-R121-IW"]


def load(ref: str) -> dict:
    return json.loads((ROOT / ref).read_text(encoding="utf-8"))


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


class M2RadarPixelOrbitApplicationRecovery002ReviewTests(unittest.TestCase):
    def test_preparation_authority_is_exact_and_local_only(self) -> None:
        approval = load(APPROVAL_REF)
        self.assertEqual(approval["status"], "approved_local_zero_decision_review_preparation_only")
        self.assertTrue(approval["authority_basis"]["attestation"])
        self.assertEqual(
            approval["authority_basis"]["owner_scope"],
            "local zero-decision proposal and review preparation and validation only",
        )
        boundary = approval["authority_boundary"]
        self.assertTrue(boundary["local_review_packet_preparation_authorized"])
        self.assertTrue(boundary["local_validation_authorized"])
        for key, value in boundary.items():
            if key not in {"local_review_packet_preparation_authorized", "local_validation_authorized"}:
                self.assertFalse(value, key)

    def test_publication_authority_releases_only_repository_and_ci_actions(self) -> None:
        approval = load(PUBLICATION_APPROVAL_REF)
        activation = load(PUBLICATION_ACTIVATION_REF)
        self.assertEqual(approval["status"], "approved_exact_zero_decision_review_publication_only")
        self.assertEqual(approval["human_decision_count"], 1)
        self.assertTrue(approval["attestation"])
        self.assertEqual(approval["bindings"]["proposal_sha256"], PROPOSAL_SHA256)
        self.assertEqual(approval["bindings"]["review_bundle_sha256"], BUNDLE_SHA256)
        boundary = approval["authority_boundary"]
        for key in (
            "repository_control_integration_authorized",
            "public_default_branch_publication_authorized",
            "public_ci_authorized",
            "post_ci_publication_reconciliation_authorized",
        ):
            self.assertTrue(boundary[key], key)
        for key, value in boundary.items():
            if key not in {
                "repository_control_integration_authorized",
                "public_default_branch_publication_authorized",
                "public_ci_authorized",
                "post_ci_publication_reconciliation_authorized",
            }:
                self.assertFalse(value, key)
        self.assertEqual(
            activation["status"],
            "pass_exact_publication_authority_activated_public_ci_pending",
        )
        self.assertEqual(
            activation["bindings"]["publication_approval_sha256"],
            sha256(PUBLICATION_APPROVAL_REF),
        )
        self.assertFalse(activation["assertions"]["owner_review_open"])
        self.assertFalse(activation["assertions"]["owner_proposal_decision_recorded"])

    def test_publication_gate_opens_only_owner_review(self) -> None:
        gate = load(PUBLICATION_GATE_REF)
        reconciliation = load(PUBLICATION_RECONCILIATION_REF)
        self.assertEqual(
            gate["status"],
            "pass_public_default_branch_ci_zero_decision_owner_review_ready",
        )
        self.assertEqual(gate["commit_sha"], "2de376ecd1ed4c226cd5fa2d2e39b763aa5c9438")
        self.assertEqual(gate["public_ci_run_id"], 35468801414)
        self.assertEqual(gate["repository_required_file_count"], 1141)
        self.assertEqual(gate["public_test_count"], 618)
        self.assertEqual(gate["public_intentional_skip_count"], 13)
        self.assertTrue(gate["released_now"]["owner_proposal_review"])
        for key, value in gate["released_now"].items():
            if key != "owner_proposal_review":
                self.assertFalse(value, key)
        self.assertEqual(reconciliation["status"], "pass_public_gate_owner_review_ready")
        self.assertEqual(
            reconciliation["publication_gate_sha256"],
            sha256(PUBLICATION_GATE_REF),
        )
        self.assertEqual(reconciliation["current_checkpoint"], "M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-002-REVIEW")

    def test_proposal_identity_evidence_and_claim_limits(self) -> None:
        proposal = load(PROPOSAL_REF)
        self.assertEqual(sha256(PROPOSAL_REF), PROPOSAL_SHA256)
        self.assertEqual(proposal["human_decision_count"], 0)
        self.assertFalse(proposal["preparation_authority"]["public_publication_authorized"])
        self.assertFalse(proposal["preparation_authority"]["implementation_authorized"])
        self.assertFalse(proposal["preparation_authority"]["new_attempt_authorized"])
        observed = proposal["observed_state"]
        self.assertTrue(observed["radar_attempt_terminal_and_consumed"])
        self.assertTrue(observed["probe_attempt_terminal_and_consumed"])
        self.assertFalse(observed["radar_failure_exact_arcpy_statement_known"])
        self.assertFalse(observed["historical_root_cause_established"])
        self.assertFalse(observed["radar_recovery_readiness_established"])
        self.assertIn("post_observation_bias", observed)
        for artifact in proposal["protected_public_evidence"]:
            self.assertTrue(artifact["must_remain_unchanged_during_preparation"])
            self.assertEqual(artifact["sha256"], sha256(artifact["path"]))

    def test_exact_attempt_order_and_scientific_contract_remain_bounded(self) -> None:
        proposal = load(PROPOSAL_REF)
        recovery = proposal["exact_recovery_contract"]
        self.assertEqual(recovery["attempt_id"], "radar-pixel-orbit-application-recovery-002-real-001")
        self.assertEqual(
            recovery["consumed_attempt_ids"],
            [
                "radar-pixel-orbit-application-recovery-001-real-001",
                "radar-delayed-import-probe-receipt-recovery-001-real-001",
            ],
        )
        self.assertTrue(recovery["distinct_from_consumed_attempts"])
        self.assertEqual(recovery["fixed_source_order"], SOURCE_ORDER)
        self.assertEqual(recovery["fixed_route_order"], ROUTE_ORDER)
        self.assertTrue(recovery["delayed_arcpy_import_after_exact_identity_scan"])
        self.assertTrue(recovery["inventory_comparator_unchanged_from_recovery_001"])
        self.assertEqual(recovery["scientific_contracts_unchanged"]["crs"], "EPSG:32645")
        self.assertEqual(recovery["scientific_contracts_unchanged"]["grid_resolution_metres"], 10)
        self.assertFalse(
            recovery["scientific_contracts_unchanged"][
                "source_orbit_dem_aoi_mask_threshold_registration_and_route_substitution_allowed"
            ]
        )
        semantics = recovery["result_semantics"]
        self.assertFalse(semantics["historical_root_cause_claim_allowed"])
        self.assertFalse(semantics["baseline_admission_allowed"])
        self.assertFalse(semantics["change_analysis_allowed"])
        self.assertFalse(semantics["scientific_claim_allowed"])
        limits = proposal["limits"]
        self.assertEqual(limits["consumed_attempt_retries_or_reuses"], 0)
        self.assertEqual(limits["future_real_attempts"], 1)
        self.assertFalse(limits["automatic_retry"])
        self.assertTrue(limits["stop_on_first_failure"])
        for key in (
            "network_requests",
            "credential_or_token_actions",
            "software_installations",
            "uac_actions",
            "source_overwrites",
            "external_custody_mutations",
            "baseline_or_change_actions",
            "scientific_outputs",
        ):
            self.assertEqual(limits[key], 0, key)

    def test_bundle_contract_and_response_are_zero_decision(self) -> None:
        bundle = load(BUNDLE_REF)
        contract = load(CONTRACT_REF)
        blank = load(BLANK_REF)
        self.assertEqual(sha256(BUNDLE_REF), BUNDLE_SHA256)
        self.assertEqual(bundle["human_decision_count"], 0)
        for artifact in bundle["artifacts"]:
            self.assertEqual(artifact["sha256"], sha256(artifact["path"]))
            for receipt in artifact["render_receipts"]:
                self.assertEqual(receipt["sha256"], sha256(receipt["path"]))
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

    def test_surface_and_visual_inspection_are_bound(self) -> None:
        surface = load(SURFACE_REF)
        visual = load(VISUAL_REF)
        readiness = load(READINESS_REF)
        self.assertEqual(surface["artifact_sha256"], IMAGE_SHA256)
        self.assertEqual(sha256(IMAGE_REF), IMAGE_SHA256)
        self.assertEqual((surface["width_px"], surface["height_px"]), (1800, 2040))
        self.assertEqual(sha256(VISUAL_REF), VISUAL_SHA256)
        self.assertEqual(visual["status"], "pass_agent_visual_inspection")
        self.assertEqual(visual["surface"]["sha256"], IMAGE_SHA256)
        self.assertFalse(visual["inspection"]["text_clipped_or_overlapping"])
        self.assertFalse(visual["inspection"]["claim_overreach_observed"])
        self.assertEqual(readiness["bindings"]["visual_inspection_sha256"], VISUAL_SHA256)
        self.assertTrue(readiness["validation"]["rendered_surface_visually_inspected"])

    def test_readiness_preserves_current_checkpoint_and_releases_nothing_else(self) -> None:
        preflight = load(PREFLIGHT_REF)
        readiness = load(READINESS_REF)
        self.assertEqual(sha256(READINESS_REF), READINESS_SHA256)
        self.assertEqual(preflight["status"], "pass_ready_local_zero_decision_packet_preparation_only")
        self.assertEqual(
            readiness["status"],
            "pass_local_zero_decision_packet_ready_publication_authority_required",
        )
        self.assertEqual(readiness["bindings"]["proposal_sha256"], PROPOSAL_SHA256)
        self.assertEqual(readiness["bindings"]["review_bundle_sha256"], BUNDLE_SHA256)
        self.assertEqual(readiness["validation"]["human_decision_count"], 0)
        self.assertTrue(readiness["validation"]["canonical_checkpoint_intentionally_unchanged"])
        self.assertTrue(readiness["released_now"]["local_packet_preparation"])
        self.assertTrue(readiness["released_now"]["local_packet_validation"])
        for key, value in readiness["released_now"].items():
            if key not in {"local_packet_preparation", "local_packet_validation"}:
                self.assertFalse(value, key)
        for control_ref, path in (
            ("milestone", "contracts/milestone-002.json"),
            ("profile", "records/project-control-profile.json"),
            ("goal", "records/long-term-goal.json"),
        ):
            control = load(path)
            if control_ref == "milestone":
                observed = control["handoff"]["current_checkpoint"]
            elif control_ref == "profile":
                observed = control["current_checkpoint"]["checkpoint_id"]
            else:
                observed = control["current_checkpoint"]
            self.assertEqual(observed, CURRENT_CHECKPOINT)

    def test_preflight_binds_the_final_preparation_script(self) -> None:
        preflight = load(PREFLIGHT_REF)
        self.assertEqual(
            preflight["bindings"]["preparation_script_sha256"],
            sha256("scripts/prepare_m2_radar_pixel_orbit_application_recovery_002_review.py"),
        )
        assertions = preflight["assertions"]
        self.assertFalse(assertions["git_commit_created"])
        self.assertFalse(assertions["git_push_performed"])
        self.assertFalse(assertions["public_ci_started"])
        self.assertFalse(assertions["arcpy_invoked"])
        self.assertFalse(assertions["project_data_content_read"])
        self.assertFalse(assertions["external_custody_accessed"])
        self.assertFalse(assertions["new_attempt_created"])
        self.assertFalse(assertions["radar_processing_executed"])


if __name__ == "__main__":
    unittest.main()
