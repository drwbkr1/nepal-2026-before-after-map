from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from derive_m2_acquisition_checkpoint import (  # noqa: E402
    current_radar_raster_function_call_shape_recovery_004_review_required,
    current_radar_raster_function_call_shape_recovery_004_stage,
)

OBSERVATION_REF = "records/observations/m2-radar-ia-raster-function-signature-audit-001.json"
PROPOSAL_REF = "contracts/milestone-002-radar-raster-function-call-shape-recovery-004-proposal.json"
REVIEW_REF = "docs/M2_RADAR_RASTER_FUNCTION_CALL_SHAPE_RECOVERY_004_REVIEW.md"
BUNDLE_REF = "reviews/m2-radar-raster-function-call-shape-recovery-004/review-bundle.json"
APPROVAL_REF = "records/source-gates/m2-radar-raster-function-call-shape-recovery-004-approval.json"
RECONCILIATION_REF = "records/source-gates/m2-radar-raster-function-call-shape-recovery-004-review-reconciliation.json"
ACTIVATION_REF = "records/readiness/m2-radar-raster-function-call-shape-recovery-004-approval-activation.json"
OBSERVATION_SHA256 = "fb7ebc9d4f62e855cdce8ef4cec2fe9bb8fcbb6220f4d4a0bda62877fa9b1eae"
PROPOSAL_SHA256 = "bee3b46d05bf671b8b6657ee12629dfeaa5f04a9adce40bd0593823a664429ed"
REVIEW_SHA256 = "a43584c40f69ac5ad414349bd9073cfdb4f7d0a338862f1148504c966c7ca157"
BUNDLE_SHA256 = "46c52b15d939a2ca7536205b61ec06158a84708e59425a92224a5a6dad7969c5"
APPROVAL_SHA256 = "b7133be0ee697895d45ba5702dae046c183472f2c93bf81029f130d333aa460a"
RECONCILIATION_SHA256 = "1218d0732ae7794fc0efbe17dc680d02caed30a70baef4409f6d54ae9880acdf"
ACTIVATION_SHA256 = "f4539c9707a5935cee0189867ba966a665becc14dccf3bc35a617b981a913a4b"
CHECKPOINT = "M2-RADAR-RASTER-FUNCTION-CALL-SHAPE-RECOVERY-004-TERMINAL-REVIEW"


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


class M2RadarRasterFunctionCallShapeRecovery004ReviewTests(unittest.TestCase):
    def test_exact_packet_approval_and_artifact_bindings(self) -> None:
        proposal = load(PROPOSAL_REF)
        bundle = load(BUNDLE_REF)
        self.assertEqual(sha256(OBSERVATION_REF), OBSERVATION_SHA256)
        self.assertEqual(sha256(PROPOSAL_REF), PROPOSAL_SHA256)
        self.assertEqual(sha256(REVIEW_REF), REVIEW_SHA256)
        self.assertEqual(sha256(BUNDLE_REF), BUNDLE_SHA256)
        self.assertEqual(sha256(APPROVAL_REF), APPROVAL_SHA256)
        self.assertEqual(sha256(RECONCILIATION_REF), RECONCILIATION_SHA256)
        self.assertEqual(sha256(ACTIVATION_REF), ACTIVATION_SHA256)
        self.assertEqual(proposal["status"], "proposed_inactive_local_one_decision_review")
        self.assertEqual(bundle["candidate_identity"]["proposal_sha256"], PROPOSAL_SHA256)
        for artifact in bundle["artifacts"]:
            self.assertEqual(artifact["sha256"], sha256(artifact["path"]))
        approval = load(APPROVAL_REF)
        self.assertTrue(approval["attestation"])
        self.assertEqual(approval["human_decision_count"], 1)
        self.assertEqual(approval["bindings"]["proposal_sha256"], PROPOSAL_SHA256)
        self.assertEqual(approval["bindings"]["review_bundle_sha256"], BUNDLE_SHA256)
        self.assertFalse(approval["authorized_scope"]["intermediate_owner_reconfirmation_required"])

    def test_signature_audit_supports_one_coherent_correction(self) -> None:
        observation = load(OBSERVATION_REF)
        self.assertEqual(observation["status"], "pass_read_only_installed_runtime_signature_inventory")
        self.assertEqual(observation["finding"]["other_five_interfaces"], "raster_returning_functions_without_output_path")
        proposal = load(PROPOSAL_REF)
        correction = proposal["proposed_correction"]
        self.assertEqual(correction["apply_orbit_correction_call"], "unchanged")
        self.assertEqual(len(correction["exact_call_shapes"]), 6)
        self.assertTrue(correction["exclusive_output_save"])
        self.assertTrue(correction["returned_object_must_expose_save"])
        self.assertTrue(correction["output_must_exist_after_save"])
        self.assertTrue(correction["no_change_to_algorithm_parameters"])

    def test_approved_attempt_and_claim_boundaries_are_frozen(self) -> None:
        proposal = load(PROPOSAL_REF)
        attempt = proposal["proposed_attempt"]
        self.assertEqual(attempt["maximum_processes"], 1)
        self.assertEqual(attempt["maximum_real_attempts"], 1)
        self.assertFalse(attempt["automatic_retry"])
        self.assertTrue(attempt["stop_on_first_failure"])
        self.assertEqual(attempt["network_requests"], 0)
        self.assertEqual(attempt["credential_actions"], 0)
        self.assertTrue(all(proposal["single_owner_decision_scope"].values()))
        self.assertTrue(all(value is False for value in load(BUNDLE_REF)["claim_boundary"].values()))

    def test_control_plane_inherits_one_completed_human_decision(self) -> None:
        milestone = load("contracts/milestone-002.json")
        units = {unit["id"]: unit for unit in milestone["units"]}
        review = units["M2-RADAR-RASTER-FUNCTION-CALL-SHAPE-RECOVERY-004-REVIEW"]
        recovery = units["M2-RADAR-RASTER-FUNCTION-CALL-SHAPE-RECOVERY-004"]
        self.assertEqual(review["status"], "complete")
        self.assertEqual(review["gates"]["human_decision_count"], 1)
        self.assertEqual(review["gates"]["owner_combined_decision"], "approved_exact")
        self.assertTrue(review["gates"]["publication_authorized"])
        self.assertEqual(recovery["status"], "complete")
        self.assertEqual(recovery["disposition"], "block")
        self.assertEqual(recovery["gates"]["inherited_owner_authority"], "pass_exact_combined_approval")
        self.assertEqual(recovery["gates"]["real_attempts_started"], 1)
        self.assertTrue(recovery["gates"]["attempt_consumed"])
        pending_human = [
            unit["id"] for unit in milestone["units"]
            if unit.get("human_gate") is True and unit.get("status") in {"ready", "in_progress", "pending"}
        ]
        self.assertEqual(pending_human, [])

    def test_controls_and_derivation_point_to_terminal_review(self) -> None:
        milestone = load("contracts/milestone-002.json")
        profile = load("records/project-control-profile.json")
        goal = load("records/long-term-goal.json")
        self.assertEqual(milestone["handoff"]["current_checkpoint"], CHECKPOINT)
        self.assertEqual(profile["current_checkpoint"]["checkpoint_id"], CHECKPOINT)
        self.assertEqual(goal["current_checkpoint"], CHECKPOINT)
        self.assertEqual(profile["parallel_checkpoints"][0]["authority_ref"], APPROVAL_REF)
        self.assertFalse(current_radar_raster_function_call_shape_recovery_004_review_required(ROOT, {"promoted": 8}))
        self.assertEqual(current_radar_raster_function_call_shape_recovery_004_stage(ROOT, {"promoted": 8}), "terminal")
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/derive_m2_acquisition_checkpoint.py")],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["checkpoint"]["checkpoint_id"], CHECKPOINT)

    def test_implementation_contract_and_arcgis_signature_receipt_exist(self) -> None:
        contract = load("config/qa/m2-radar-raster-function-call-shape-recovery-004-contract.json")
        runtime = load("records/readiness/m2-radar-raster-function-call-shape-recovery-004-arcgis-runtime-validation.json")
        self.assertEqual(contract["authority"]["approval_sha256"], APPROVAL_SHA256)
        self.assertEqual(contract["attempt"]["maximum_real_attempts"], 1)
        self.assertEqual(runtime["status"], "pass_installed_arcgis_runtime_six_interface_signature_only_validation")
        self.assertTrue(runtime["assertions"]["signature_inspection_only"])
        self.assertFalse(runtime["assertions"]["geoprocessing_invoked"])

    def test_terminal_reconciliation_preserves_failure_and_no_retry_boundary(self) -> None:
        terminal = load("records/processing/m2-radar-raster-function-call-shape-recovery-004-terminal-reconciliation.json")
        outcome = load("records/processing/m2-radar-raster-function-call-shape-recovery-004-outcome-reconciliation.json")
        self.assertEqual(
            terminal["status"],
            "block_raster_function_recovery_004_source_001_geometric_terrain_correction_gamma_no_retry",
        )
        self.assertEqual(terminal["execution_result"]["source_ids_attempted"], ["M1-SRC-001"])
        self.assertEqual(terminal["execution_result"]["route_ids_attempted"], [])
        self.assertEqual(terminal["execution_result"]["stopped_tool"], "ApplyGeometricTerrainCorrection_gamma")
        self.assertEqual(terminal["execution_result"]["failure_type"], "ExecuteError")
        self.assertFalse(terminal["call_boundary_observation"]["function_returned_successfully"])
        self.assertFalse(terminal["call_boundary_observation"]["returned_raster_save_started"])
        self.assertFalse(terminal["call_boundary_observation"]["output_created"])
        self.assertFalse(terminal["assertions"]["automatic_retry_performed"])
        self.assertFalse(terminal["assertions"]["second_attempt_created"])
        self.assertEqual(outcome["bindings"]["terminal_reconciliation_sha256"], sha256(
            "records/processing/m2-radar-raster-function-call-shape-recovery-004-terminal-reconciliation.json"
        ))
        self.assertFalse(outcome["assertions"]["radar_recovery_readiness_established"])

    def test_terminal_publication_gate_binds_successful_public_ci(self) -> None:
        gate = load("records/readiness/m2-radar-raster-function-call-shape-recovery-004-terminal-publication-gate.json")
        self.assertEqual(gate["status"], "pass_public_terminal_block_published_no_retry")
        self.assertEqual(gate["terminal_commit_sha"], "e4be97407bd4c8ce9e12e1759b17a94c9c73a1f7")
        self.assertEqual(gate["public_ci_run_id"], 35644029954)
        self.assertEqual(gate["public_ci_conclusion"], "success")
        self.assertEqual(gate["public_test_count"], 696)
        self.assertFalse(gate["released_now"]["attempt_retry_or_reuse"])
        self.assertFalse(gate["assertions"]["historical_failure_root_cause_established"])

    def test_terminal_publication_reconciliation_closes_the_envelope(self) -> None:
        reconciliation = load(
            "records/readiness/m2-radar-raster-function-call-shape-recovery-004-terminal-publication-reconciliation.json"
        )
        self.assertEqual(reconciliation["status"], "pass_exact_terminal_gate_public_ci_reconciled")
        self.assertEqual(reconciliation["bindings"]["terminal_gate_commit_sha"], "120f658893e40c262745f55b7f975fe320365191")
        self.assertEqual(reconciliation["bindings"]["terminal_gate_public_ci_run_id"], 35644433136)
        self.assertTrue(reconciliation["assertions"]["terminal_gate_public_ci_conclusion_success"])
        self.assertFalse(reconciliation["assertions"]["second_attempt_created"])
        self.assertEqual(reconciliation["current_checkpoint"], CHECKPOINT)


if __name__ == "__main__":
    unittest.main()
