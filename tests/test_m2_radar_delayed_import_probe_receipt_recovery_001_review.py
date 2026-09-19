from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-delayed-import-probe-receipt-recovery-001"
PROPOSAL_REF = "contracts/milestone-002-radar-delayed-import-probe-receipt-recovery-001-proposal.json"
PREPARATION_APPROVAL_REF = f"records/source-gates/{PREFIX}-review-preparation-approval.json"
PUBLICATION_APPROVAL_REF = f"records/source-gates/{PREFIX}-review-publication-approval.json"
PUBLICATION_ACTIVATION_REF = f"records/readiness/{PREFIX}-review-publication-activation.json"
PREFLIGHT_REF = f"records/readiness/{PREFIX}-review-preflight.json"
IMAGE_REF = f"docs/assets/{PREFIX}-review.png"
SURFACE_REF = f"records/surface-receipts/{PREFIX}-review.json"
VISUAL_REF = f"records/surface-receipts/{PREFIX}-review-visual-inspection.json"
BUNDLE_REF = f"reviews/{PREFIX}/review-bundle.json"
CONTRACT_REF = f"reviews/{PREFIX}/review-contract.json"
BLANK_REF = f"reviews/{PREFIX}/blank-response.json"
READINESS_REF = f"records/readiness/{PREFIX}-review-readiness.json"
TERMINAL_REF = "records/processing/m2-radar-delayed-import-probe-001-terminal-reconciliation.json"
OUTCOME_REF = "records/processing/m2-radar-delayed-import-probe-001-outcome-reconciliation.json"

PROPOSAL_SHA256 = "9bbe934bd1dcbe7d1b0700b83473db2ab1a130c13fa6d183d3b1a247dfe88e09"
BUNDLE_SHA256 = "df43e0d93f1d40aa85fb1f8730cc57d596fcc4345299b0939b22f822321a9695"
READINESS_SHA256 = "468d29d68f9e1c8323a7f388b74457e3063ae9a115d69bcaedde077d49617dc8"
CURRENT_CHECKPOINT = "M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-TERMINAL-REVIEW"
PROTECTED_HASHES = {
    "config/qa/m2-radar-delayed-import-probe-001-contract.json": "c9bf8154bfb44cf6a76a9cdfc695c30b7e2bf2349d64ab9e8c0e922ca0b70ac0",
    "scripts/m2_radar_delayed_import_probe_001_core.py": "b15bcc4f6ec4034aa890d551f3d700977367e9f1bc7e28c69cbdd50f17588d2a",
    "scripts/run_m2_radar_delayed_import_probe_001.py": "189f59a81733e163c07d72abacf917b9e8482af871b323402a84047ec816792c",
    "tests/test_m2_radar_delayed_import_probe_001.py": "b6d01b9e18d6a0448fb53581d7ae522ca97db17ec337420ca8ccce226b0cfa02",
}


def load(ref: str) -> dict:
    return json.loads((ROOT / ref).read_text(encoding="utf-8"))


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


class M2RadarDelayedImportProbeReceiptRecovery001ReviewTests(unittest.TestCase):
    def test_preparation_authority_is_local_only(self) -> None:
        approval = load(PREPARATION_APPROVAL_REF)
        self.assertEqual(approval["status"], "approved_local_review_preparation_only")
        self.assertEqual(approval["authority_basis"]["owner_instruction"], "I authorize preparation.")
        boundary = approval["authority_boundary"]
        self.assertTrue(boundary["local_review_packet_preparation_authorized"])
        self.assertTrue(boundary["local_validation_authorized"])
        for key in (
            "git_commit_authorized",
            "public_review_packet_publication_authorized",
            "public_ci_authorized",
            "owner_proposal_decision_recording_authorized",
            "recovery_implementation_authorized",
            "arcpy_invocation_authorized",
            "disposable_corpus_creation_authorized",
            "new_probe_attempt_authorized",
            "project_data_or_external_custody_access_authorized",
            "radar_processing_authorized",
            "baseline_or_change_authorized",
            "scientific_publication_authorized",
        ):
            self.assertFalse(boundary[key])

    def test_consumed_attempt_and_public_implementation_are_immutable_inputs(self) -> None:
        terminal = load(TERMINAL_REF)
        outcome = load(OUTCOME_REF)
        self.assertEqual(terminal["status"], "block_terminal_receipt_persistence_failure_no_retry")
        self.assertEqual(terminal["attempt_id"], "radar-delayed-import-probe-001-real-001")
        self.assertEqual(terminal["durable_stage_evidence"]["last_durable_stage"], "arcpy_import_started")
        self.assertFalse(terminal["process_failure"]["original_caught_exception_recoverable"])
        self.assertEqual(outcome["status"], "block_probe_terminal_persistence_failure_no_retry")
        self.assertTrue(outcome["assertions"]["attempt_consumed"])
        for ref, expected in PROTECTED_HASHES.items():
            self.assertEqual(sha256(ref), expected)

    def test_proposal_is_zero_decision_and_post_observation_limited(self) -> None:
        proposal = load(PROPOSAL_REF)
        self.assertEqual(sha256(PROPOSAL_REF), PROPOSAL_SHA256)
        self.assertEqual(
            proposal["status"],
            "proposed_inactive_local_review_prepared_publication_and_owner_approval_required",
        )
        self.assertEqual(proposal["human_decision_count"], 0)
        self.assertFalse(proposal["preparation_authority"]["public_publication_authorized"])
        self.assertFalse(proposal["preparation_authority"]["implementation_authorized"])
        self.assertTrue(proposal["observed_state"]["consumed_attempt_terminal"])
        self.assertFalse(proposal["observed_state"]["historical_root_cause_established"])
        self.assertIn("post_observation_bias", proposal["observed_state"])

    def test_proposed_recovery_changes_only_receipt_durability(self) -> None:
        proposal = load(PROPOSAL_REF)
        recovery = proposal["exact_recovery_contract"]
        self.assertEqual(
            recovery["attempt_id"],
            "radar-delayed-import-probe-receipt-recovery-001-real-001",
        )
        self.assertTrue(recovery["distinct_from_consumed_attempt"])
        self.assertEqual(recovery["corpus"]["file_count"], 156)
        self.assertEqual(recovery["corpus"]["total_logical_bytes"], 10_367_157_634)
        self.assertEqual(
            recovery["corpus"]["expected_stable_order_aggregate_sha256"],
            "dd56f8b28a1ed1c6e2b4b1d7d8f5db4fd86dab80a910fe79c8d018d58942430b",
        )
        self.assertTrue(recovery["stage_order_unchanged_from_probe_001_contract"])
        receipt = recovery["receipt_durability"]
        self.assertTrue(receipt["terminal_identity_reserved_before_corpus"])
        self.assertTrue(receipt["cleanup_identity_reserved_before_corpus"])
        self.assertTrue(receipt["fallback_journal_initialized_before_corpus"])
        self.assertTrue(receipt["original_sanitized_exception_recorded_before_normal_terminal_assembly"])
        self.assertTrue(receipt["fallback_is_not_success_evidence"])
        self.assertFalse(recovery["result_semantics"]["historical_root_cause_claim_allowed"])
        self.assertFalse(recovery["result_semantics"]["radar_recovery_readiness_claim_allowed"])
        self.assertFalse(recovery["result_semantics"]["scientific_claim_allowed"])
        limits = proposal["limits"]
        self.assertEqual(limits["consumed_attempt_retries_or_reuses"], 0)
        self.assertEqual(limits["future_live_attempts"], 1)
        self.assertFalse(limits["automatic_retry"])
        for key in (
            "network_requests",
            "credential_or_token_actions",
            "software_installations",
            "uac_actions",
            "project_data_content_reads",
            "external_custody_reads",
            "external_custody_mutations",
            "orbit_applications",
            "radar_pixel_reads",
            "baseline_or_change_actions",
            "scientific_outputs",
        ):
            self.assertEqual(limits[key], 0)

    def test_bundle_contract_and_response_are_local_and_blank(self) -> None:
        bundle = load(BUNDLE_REF)
        contract = load(CONTRACT_REF)
        blank = load(BLANK_REF)
        self.assertEqual(sha256(BUNDLE_REF), BUNDLE_SHA256)
        self.assertEqual(bundle["status"], "locally_prepared_zero_decisions_publication_authority_required")
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

    def test_surface_and_readiness_are_locally_verified_without_release(self) -> None:
        preflight = load(PREFLIGHT_REF)
        surface = load(SURFACE_REF)
        visual = load(VISUAL_REF)
        readiness = load(READINESS_REF)
        self.assertEqual(sha256(READINESS_REF), READINESS_SHA256)
        self.assertEqual(preflight["status"], "pass_ready_local_zero_decision_packet_preparation_only")
        self.assertEqual(surface["artifact_sha256"], sha256(IMAGE_REF))
        self.assertEqual((surface["width_px"], surface["height_px"]), (1800, 1880))
        self.assertEqual(visual["status"], "pass_agent_visual_inspection")
        self.assertEqual(visual["artifact_sha256"], sha256(IMAGE_REF))
        self.assertFalse(visual["inspection"]["text_clipped_or_overlapping"])
        self.assertEqual(
            readiness["status"],
            "pass_local_zero_decision_packet_ready_publication_authority_required",
        )
        self.assertTrue(readiness["validation"]["rendered_surface_visually_inspected"])
        self.assertTrue(readiness["released_now"]["local_packet_preparation"])
        self.assertTrue(readiness["released_now"]["local_packet_validation"])
        for key in (
            "git_commit_or_push",
            "public_ci",
            "owner_proposal_review",
            "implementation",
            "arcpy_invocation",
            "disposable_corpus_creation",
            "new_probe_attempt",
            "project_data_or_external_custody_access",
            "radar_processing",
            "baseline_or_change_analysis",
            "scientific_publication",
        ):
            self.assertFalse(readiness["released_now"][key])

    def test_publication_history_is_preserved_after_exact_owner_approval(self) -> None:
        approval = load(PUBLICATION_APPROVAL_REF)
        activation = load(PUBLICATION_ACTIVATION_REF)
        self.assertEqual(approval["status"], "approved_exact_zero_decision_review_publication_only")
        self.assertEqual(approval["bindings"]["proposal_sha256"], PROPOSAL_SHA256)
        self.assertEqual(approval["bindings"]["review_bundle_sha256"], BUNDLE_SHA256)
        self.assertTrue(approval["attestation"])
        self.assertEqual(
            activation["status"],
            "pass_exact_publication_authority_activated_public_ci_pending",
        )
        self.assertTrue(activation["released_now"]["public_default_branch_publication"])
        self.assertTrue(activation["released_now"]["public_ci"])
        self.assertFalse(activation["released_now"]["owner_proposal_review"])
        self.assertFalse(activation["released_now"]["implementation"])
        self.assertFalse(activation["released_now"]["new_probe_attempt"])
        milestone = load("contracts/milestone-002.json")
        profile = load("records/project-control-profile.json")
        goal = load("records/long-term-goal.json")
        self.assertEqual(milestone["handoff"]["current_checkpoint"], CURRENT_CHECKPOINT)
        self.assertEqual(profile["current_checkpoint"]["checkpoint_id"], CURRENT_CHECKPOINT)
        self.assertEqual(goal["current_checkpoint"], CURRENT_CHECKPOINT)
        self.assertEqual(goal["proposed_amendments"], [])
        units = {item["id"]: item for item in milestone["units"]}
        review = units["M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-REVIEW"]
        implementation = units["M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-IMPLEMENTATION"]
        execution = units["M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-EXECUTION"]
        self.assertEqual(review["status"], "complete")
        self.assertEqual(review["gates"]["public_ci"], "success")
        self.assertTrue(review["gates"]["review_response_open"])
        self.assertEqual(review["gates"]["human_decision_count"], 1)
        self.assertTrue(review["gates"]["attestation"])
        self.assertTrue(review["gates"]["implementation_authorized"])
        self.assertTrue(review["gates"]["new_probe_attempt_authorized"])
        self.assertEqual(implementation["status"], "complete")
        self.assertEqual(implementation["gates"]["public_ci"], "success")
        self.assertEqual(execution["status"], "complete")
        self.assertEqual(execution["gates"]["gate_state_publication"], "success")
        self.assertEqual(execution["gates"]["final_no_content_preflight"], "success")
        self.assertEqual(execution["gates"]["live_attempts_started"], 1)
        self.assertTrue(execution["gates"]["attempt_consumed"])
        self.assertEqual(execution["gates"]["terminal_status"], "pass_exact_receipt_recovery_probe_no_retry")


if __name__ == "__main__":
    unittest.main()
