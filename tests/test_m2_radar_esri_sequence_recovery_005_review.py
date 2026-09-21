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
    current_radar_esri_sequence_recovery_005_review_required,
    current_radar_esri_sequence_recovery_005_stage,
)

OBSERVATION_REF = "records/observations/m2-radar-gtc-despeckle-prerequisite-audit-001.json"
PROPOSAL_REF = "contracts/milestone-002-radar-esri-sequence-recovery-005-proposal.json"
REVIEW_REF = "docs/M2_RADAR_ESRI_SEQUENCE_RECOVERY_005_REVIEW.md"
BUNDLE_REF = "reviews/m2-radar-esri-sequence-recovery-005/review-bundle.json"
OBSERVATION_SHA256 = "1237c8e8cc6d3905228dd7797782782b0262d634489c62d56d6850c213e7f4eb"
PROPOSAL_SHA256 = "5e7ca67eedecba76746e7c3862b691d0e954425cadadd0782ff90ed3f95ab217"
REVIEW_SHA256 = "d53879c8496b71187f5fd4b003b3c08e3eb76e308f932d717aaa8b937d716443"
BUNDLE_SHA256 = "19af7c293e91bea1e5c46092263e67ce064781f10601f3139024457817b0bcd0"
APPROVAL_REF = "records/source-gates/m2-radar-esri-sequence-recovery-005-approval.json"
RECONCILIATION_REF = "records/source-gates/m2-radar-esri-sequence-recovery-005-review-reconciliation.json"
ACTIVATION_REF = "records/readiness/m2-radar-esri-sequence-recovery-005-approval-activation.json"
APPROVAL_SHA256 = "da95bf4570a7062166a758ce5cfb037300b2a039bfc9454995cd366313595a20"
RECONCILIATION_SHA256 = "c8c25fc6958db2c927c8550b885a82f03d5582754e95cf9fcbaf26261a35365b"
ACTIVATION_SHA256 = "9376187bb965d15b70a7e15aa930f4052d0f7cbf7c9e6fd6b03e5dae830b5290"
CHECKPOINT = "M2-RADAR-ESRI-SEQUENCE-RECOVERY-005-IMPLEMENTATION"


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


class M2RadarEsriSequenceRecovery005ReviewTests(unittest.TestCase):
    def test_exact_packet_approval_and_artifact_bindings(self) -> None:
        proposal = load(PROPOSAL_REF)
        bundle = load(BUNDLE_REF)
        self.assertEqual(sha256(OBSERVATION_REF), OBSERVATION_SHA256)
        self.assertEqual(sha256(PROPOSAL_REF), PROPOSAL_SHA256)
        self.assertEqual(sha256(REVIEW_REF), REVIEW_SHA256)
        self.assertEqual(sha256(BUNDLE_REF), BUNDLE_SHA256)
        self.assertEqual(proposal["human_decision_count"], 0)
        self.assertFalse(proposal["authority_basis"]["publication_implementation_or_execution_authorized"])
        self.assertEqual(bundle["human_decision_count"], 0)
        self.assertEqual(bundle["candidate_identity"]["proposal_sha256"], PROPOSAL_SHA256)
        for artifact in bundle["artifacts"]:
            self.assertEqual(artifact["sha256"], sha256(artifact["path"]))
        self.assertEqual(sha256(APPROVAL_REF), APPROVAL_SHA256)
        self.assertEqual(sha256(RECONCILIATION_REF), RECONCILIATION_SHA256)
        self.assertEqual(sha256(ACTIVATION_REF), ACTIVATION_SHA256)
        approval = load(APPROVAL_REF)
        self.assertTrue(approval["attestation"])
        self.assertEqual(approval["human_decision_count"], 1)
        self.assertEqual(approval["bindings"]["proposal_sha256"], PROPOSAL_SHA256)
        self.assertEqual(approval["bindings"]["review_bundle_sha256"], BUNDLE_SHA256)
        self.assertTrue(approval["authorized_scope"]["approve_recovery_specific_refined_lee_scientific_method_amendment"])
        self.assertFalse(approval["authorized_scope"]["intermediate_owner_reconfirmation_required"])

    def test_official_guidance_is_fit_only_for_method_review(self) -> None:
        observation = load(OBSERVATION_REF)
        self.assertEqual(
            observation["status"],
            "pass_official_method_guidance_for_zero_decision_review_only",
        )
        self.assertEqual(len(observation["official_sources"]), 4)
        self.assertTrue(all(source["publisher"] == "Esri" for source in observation["official_sources"]))
        self.assertEqual(observation["project_contract_mismatch"]["frozen_primary_despeckle"], "NONE")
        self.assertEqual(
            observation["project_contract_mismatch"]["official_esri_sequence_requires_intervening_stage"],
            "Despeckle",
        )
        self.assertEqual(
            observation["source_gate_assessment"]["decision"],
            "pass_for_zero_decision_proposal_preparation_only",
        )
        self.assertFalse(observation["assertions"]["project_data_read"])
        self.assertFalse(observation["assertions"]["external_custody_read"])
        self.assertFalse(observation["assertions"]["historical_root_cause_established"])

    def test_method_amendment_and_exact_call_are_explicit(self) -> None:
        proposal = load(PROPOSAL_REF)
        amendment = proposal["proposed_scientific_method_amendment"]
        correction = proposal["proposed_correction"]
        self.assertTrue(amendment["amendment_required"])
        self.assertEqual(amendment["historical_primary_route"], "no_despeckle")
        self.assertEqual(amendment["proposed_recovery_005_primary_despeckle"], "REFINED_LEE")
        self.assertEqual(amendment["filter_size_argument"], "omitted")
        self.assertFalse(amendment["historical_contracts_mutated"])
        self.assertEqual(
            correction["exact_call"],
            "arcpy.ia.Despeckle(gamma_slant, 'VV;VH', 'REFINED_LEE')",
        )
        self.assertEqual(correction["insert_after"], "ApplyRadiometricTerrainFlattening")
        self.assertEqual(correction["insert_before"], "ApplyGeometricTerrainCorrection_gamma")
        self.assertTrue(correction["gamma_gtc_input_becomes_exact_despeckled_output"])

    def test_one_attempt_boundary_and_claim_limits_are_frozen(self) -> None:
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

    def test_control_plane_inherits_one_completed_owner_decision(self) -> None:
        milestone = load("contracts/milestone-002.json")
        units = {unit["id"]: unit for unit in milestone["units"]}
        review = units["M2-RADAR-ESRI-SEQUENCE-RECOVERY-005-REVIEW"]
        recovery = units["M2-RADAR-ESRI-SEQUENCE-RECOVERY-005"]
        self.assertEqual(review["status"], "complete")
        self.assertTrue(review["human_gate"])
        self.assertEqual(review["gates"]["human_decision_count"], 1)
        self.assertTrue(review["gates"]["publication_authorized"])
        self.assertTrue(review["gates"]["implementation_authorized"])
        self.assertTrue(review["gates"]["new_real_attempt_authorized"])
        self.assertEqual(recovery["status"], "in_progress")
        self.assertFalse(recovery["human_gate"])
        self.assertEqual(recovery["gates"]["inherited_owner_authority"], "pass_exact_combined_approval")
        self.assertEqual(recovery["gates"]["real_attempts_started"], 0)
        self.assertFalse(current_radar_esri_sequence_recovery_005_review_required(ROOT, {"promoted": 8}))
        self.assertEqual(current_radar_esri_sequence_recovery_005_stage(ROOT, {"promoted": 8}), "implementation")

    def test_controls_and_derivation_point_to_implementation(self) -> None:
        milestone = load("contracts/milestone-002.json")
        profile = load("records/project-control-profile.json")
        goal = load("records/long-term-goal.json")
        self.assertEqual(milestone["handoff"]["current_checkpoint"], CHECKPOINT)
        self.assertEqual(profile["current_checkpoint"]["checkpoint_id"], CHECKPOINT)
        self.assertEqual(goal["current_checkpoint"], CHECKPOINT)
        self.assertEqual(profile["control_surfaces"]["proposed_amendments"], [])
        self.assertEqual(goal["proposed_amendments"], [])
        self.assertEqual(profile["parallel_checkpoints"][0]["authority_ref"], APPROVAL_REF)
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/derive_m2_acquisition_checkpoint.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["checkpoint"]["checkpoint_id"], CHECKPOINT)


if __name__ == "__main__":
    unittest.main()
