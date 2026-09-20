from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-apply-orbit-correction-input-resolution-diagnostic-receipt-persistence-recovery-001"
SOURCE_PREFIX = "m2-radar-apply-orbit-correction-input-resolution-diagnostic-001"
PROPOSAL_REF = f"contracts/milestone-002-{PREFIX.removeprefix('m2-')}-proposal.json"
PREPARATION_APPROVAL_REF = f"records/source-gates/{PREFIX}-review-preparation-approval.json"
PUBLICATION_APPROVAL_REF = f"records/source-gates/{PREFIX}-review-publication-approval.json"
PUBLICATION_ACTIVATION_REF = f"records/readiness/{PREFIX}-review-publication-activation.json"
FAILURE_OBSERVATION_REF = f"records/readiness/{SOURCE_PREFIX}-terminal-receipt-persistence-failure-observation.json"
PREFLIGHT_REF = f"records/readiness/{PREFIX}-review-preflight.json"
IMAGE_REF = f"docs/assets/{PREFIX}-review.png"
SURFACE_REF = f"records/surface-receipts/{PREFIX}-review.json"
VISUAL_REF = f"records/surface-receipts/{PREFIX}-review-visual-inspection.json"
BUNDLE_REF = f"reviews/{PREFIX}/review-bundle.json"
CONTRACT_REF = f"reviews/{PREFIX}/review-contract.json"
BLANK_REF = f"reviews/{PREFIX}/blank-response.json"
PREVISUAL_REF = f"records/readiness/{PREFIX}-review-readiness-previsual.json"
READINESS_REF = f"records/readiness/{PREFIX}-review-readiness.json"
TERMINAL_REF = f"records/processing/{SOURCE_PREFIX}-terminal.json"
CLEANUP_REF = f"records/processing/{SOURCE_PREFIX}-cleanup.json"
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
CURRENT_CHECKPOINT = json.loads((ROOT / "records/project-control-profile.json").read_text(encoding="utf-8"))[
    "current_checkpoint"
]["checkpoint_id"]
PROTECTED_HASHES = {
    f"config/qa/{SOURCE_PREFIX}-contract.json": "e390c0918947eaac49df025bf1b3c6c0ee35804c04404b12a42597dc4411e724",
    f"scripts/{SOURCE_PREFIX.replace('-', '_')}_core.py": "9d6ca7be8514b62d088eea3e1648b002ae40f25555ab620ca298efa37b7d5129",
    f"scripts/run_{SOURCE_PREFIX.replace('-', '_')}.py": "34239fb9669559f1668887c89b08db5f7e213cfea3132ef0eeb3dffebd041d8f",
    f"tests/test_{SOURCE_PREFIX.replace('-', '_')}.py": "3741af9396bf25b3fc22d35560e92ad1cea90cf964a4ba99384e6fe78014ca1d",
}


def load(ref: str) -> dict:
    return json.loads((ROOT / ref).read_text(encoding="utf-8"))


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


class M2DiagnosticReceiptPersistenceRecovery001ReviewTests(unittest.TestCase):
    def test_preparation_authority_is_exact_and_local_only(self) -> None:
        approval = load(PREPARATION_APPROVAL_REF)
        self.assertEqual(approval["status"], "approved_local_zero_decision_review_preparation_only")
        self.assertTrue(approval["authority_basis"]["attestation_claimed"])
        self.assertIn("local zero-decision proposal and review preparation", approval["authority_basis"]["owner_instruction"])
        boundary = approval["authority_boundary"]
        self.assertTrue(boundary["local_review_packet_preparation_authorized"])
        self.assertTrue(boundary["local_validation_authorized"])
        for key, value in boundary.items():
            if key not in {"local_review_packet_preparation_authorized", "local_validation_authorized"}:
                self.assertFalse(value, key)

    def test_consumed_receipts_and_public_implementation_are_unchanged(self) -> None:
        self.assertEqual((ROOT / TERMINAL_REF).stat().st_size, 0)
        self.assertEqual((ROOT / CLEANUP_REF).stat().st_size, 0)
        self.assertEqual(sha256(TERMINAL_REF), EMPTY_SHA256)
        self.assertEqual(sha256(CLEANUP_REF), EMPTY_SHA256)
        for ref, expected in PROTECTED_HASHES.items():
            self.assertEqual(sha256(ref), expected)

    def test_failure_observation_is_terminal_indeterminate_without_reconstruction(self) -> None:
        failure = load(FAILURE_OBSERVATION_REF)
        self.assertEqual(
            failure["status"],
            "terminal_process_consumed_reserved_receipts_empty_result_indeterminate",
        )
        self.assertEqual(failure["process_observation"]["process_exit_code"], 1)
        self.assertEqual(failure["process_observation"]["failure_type"], "AttributeError")
        self.assertEqual(failure["process_observation"]["failure_code"], "terminal_timestamp_construction_failed")
        assertions = failure["assertions"]
        self.assertTrue(assertions["diagnostic_process_consumed"])
        self.assertFalse(assertions["automatic_retry_performed"])
        self.assertFalse(assertions["runner_terminal_json_persisted"])
        self.assertFalse(assertions["runner_cleanup_json_persisted"])
        self.assertFalse(assertions["input_resolution_result_reconstructed"])
        self.assertFalse(assertions["current_input_resolution_established"])
        self.assertFalse(assertions["apply_orbit_correction_invoked"])
        self.assertFalse(assertions["geoprocessing_invoked"])

    def test_proposal_is_zero_decision_and_changes_receipt_durability_only(self) -> None:
        proposal = load(PROPOSAL_REF)
        self.assertEqual(
            proposal["status"],
            "proposed_inactive_local_review_prepared_publication_and_owner_approval_required",
        )
        self.assertEqual(proposal["human_decision_count"], 0)
        self.assertFalse(proposal["preparation_authority"]["public_publication_authorized"])
        self.assertFalse(proposal["preparation_authority"]["implementation_authorized"])
        self.assertFalse(proposal["observed_state"]["current_input_resolution_established"])
        self.assertIn("post_observation_bias", proposal["observed_state"])
        recovery = proposal["exact_recovery_contract"]
        self.assertTrue(recovery["distinct_from_consumed_attempt"])
        self.assertEqual(recovery["maximum_processes"], 1)
        self.assertFalse(recovery["automatic_retry"])
        self.assertTrue(recovery["fixed_check_order_unchanged"])
        self.assertEqual(recovery["maximum_apply_orbit_correction_calls"], 0)
        self.assertEqual(recovery["maximum_geoprocessing_calls"], 0)
        receipt = recovery["receipt_durability"]
        self.assertTrue(receipt["function_local_datetime_imports"])
        self.assertTrue(receipt["fallback_journal_initialized_before_external_reads"])
        self.assertTrue(receipt["original_sanitized_exception_recorded_before_normal_terminal_assembly"])
        self.assertTrue(receipt["later_persistence_error_cannot_replace_original_error"])
        self.assertTrue(receipt["consumed_empty_receipts_remain_immutable"])
        for value in proposal["current_authority_limits"].values():
            self.assertEqual(value, 0)

    def test_bundle_contract_and_response_are_local_and_blank(self) -> None:
        bundle = load(BUNDLE_REF)
        contract = load(CONTRACT_REF)
        blank = load(BLANK_REF)
        self.assertEqual(bundle["status"], "locally_prepared_zero_decisions_publication_authority_required")
        self.assertEqual(bundle["human_decision_count"], 0)
        for artifact in bundle["artifacts"]:
            self.assertEqual(artifact["sha256"], sha256(artifact["path"]))
            for receipt in artifact["render_receipts"]:
                self.assertEqual(receipt["sha256"], sha256(receipt["path"]))
        self.assertEqual(contract["review_bundle"]["manifest_sha256"], sha256(BUNDLE_REF))
        self.assertFalse(contract["workflow_authority"]["public_review_publication_authorized"])
        self.assertFalse(contract["workflow_authority"]["review_response_open"])
        for value in contract["authority_boundary"].values():
            self.assertFalse(value)
        self.assertFalse(blank["completed"])
        self.assertFalse(blank["reviewer"]["attestation"])
        self.assertIsNone(blank["responses"][0]["decision"])
        self.assertEqual(blank["human_decision_count"], 0)
        self.assertTrue(blank["response_not_open_until_public_ci"])

    def test_surface_and_final_readiness_are_locally_verified_without_release(self) -> None:
        preflight = load(PREFLIGHT_REF)
        surface = load(SURFACE_REF)
        visual = load(VISUAL_REF)
        previsual = load(PREVISUAL_REF)
        readiness = load(READINESS_REF)
        self.assertEqual(preflight["status"], "pass_ready_local_zero_decision_packet_preparation_only")
        self.assertEqual(surface["artifact_sha256"], sha256(IMAGE_REF))
        self.assertEqual((surface["width_px"], surface["height_px"]), (1800, 2060))
        self.assertEqual(visual["status"], "pass_agent_visual_inspection")
        self.assertFalse(visual["inspection"]["text_clipped_or_overlapping"])
        self.assertEqual(
            previsual["status"],
            "pass_local_zero_decision_packet_structurally_ready_visual_inspection_pending",
        )
        self.assertEqual(
            readiness["status"],
            "pass_local_zero_decision_packet_ready_publication_authority_required",
        )
        self.assertTrue(readiness["validation"]["rendered_surface_visually_inspected"])
        self.assertTrue(readiness["released_now"]["local_packet_preparation"])
        self.assertTrue(readiness["released_now"]["local_packet_validation"])
        for key, value in readiness["released_now"].items():
            if key not in {"local_packet_preparation", "local_packet_validation"}:
                self.assertFalse(value, key)

    def test_publication_authority_is_zero_decision_and_preserves_receipts(self) -> None:
        approval = load(PUBLICATION_APPROVAL_REF)
        activation = load(PUBLICATION_ACTIVATION_REF)
        self.assertEqual(approval["status"], "approved_exact_zero_decision_review_publication_only")
        self.assertEqual(approval["bindings"]["proposal_sha256"], sha256(PROPOSAL_REF))
        self.assertEqual(approval["bindings"]["review_bundle_sha256"], sha256(BUNDLE_REF))
        self.assertTrue(approval["attestation"])
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
        self.assertFalse(activation["assertions"]["reserved_receipt_mutated"])
        self.assertFalse(activation["assertions"]["new_diagnostic_process_started"])
        self.assertEqual((ROOT / TERMINAL_REF).read_bytes(), b"")
        self.assertEqual((ROOT / CLEANUP_REF).read_bytes(), b"")

    def test_canonical_controls_are_reconciled(self) -> None:
        milestone = load("contracts/milestone-002.json")
        profile = load("records/project-control-profile.json")
        goal = load("records/long-term-goal.json")
        self.assertEqual(milestone["handoff"]["current_checkpoint"], CURRENT_CHECKPOINT)
        self.assertEqual(profile["current_checkpoint"]["checkpoint_id"], CURRENT_CHECKPOINT)
        self.assertEqual(goal["current_checkpoint"], CURRENT_CHECKPOINT)


if __name__ == "__main__":
    unittest.main()
