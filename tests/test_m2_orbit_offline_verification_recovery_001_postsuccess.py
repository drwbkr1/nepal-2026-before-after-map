from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from derive_m2_acquisition_checkpoint import (  # noqa: E402
    current_orbit_offline_verification_recovery_001_terminal,
)


SOURCE_IDS = ["M2-ORB-001", "M2-ORB-002", "M2-ORB-003", "M2-ORB-004"]
RECEIPT_REFS = {
    "M2-ORB-001": "records/acquisition/orbit-verification/m2-orb-001-offline-verification-recovery-001.json",
    "M2-ORB-002": "records/acquisition/orbit-verification/m2-orb-002-offline-verification-001.json",
    "M2-ORB-003": "records/acquisition/orbit-verification/m2-orb-003-offline-verification-001.json",
    "M2-ORB-004": "records/acquisition/orbit-verification/m2-orb-004-offline-verification-001.json",
}


def load(ref: str) -> dict:
    return json.loads((ROOT / ref).read_text(encoding="utf-8"))


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


class OrbitOfflineVerificationRecovery001PostsuccessTests(unittest.TestCase):
    def test_public_gate_and_final_preflight_preceded_real_reads(self) -> None:
        publication = load(
            "records/readiness/m2-orbit-offline-verification-recovery-001-implementation-publication-gate.json"
        )
        preflight = load(
            "records/readiness/m2-orbit-offline-verification-recovery-001-final-preflight.json"
        )
        self.assertEqual(publication["status"], "pass_public_recovery_controls_before_eof_reads")
        self.assertEqual(publication["github_actions"]["head_sha"], "72d69e787c772ec2157890bc58a8626e7049dce5")
        self.assertEqual(publication["github_actions"]["run_id"], 34153008607)
        self.assertFalse(publication["assertions"]["real_eof_content_read"])
        self.assertEqual(preflight["status"], "pass_no_content_ready_for_exact_recovery_sequence")
        self.assertEqual(preflight["source_ids_in_exact_order"], SOURCE_IDS)
        self.assertTrue(preflight["assertions"]["all_output_paths_absent"])
        self.assertFalse(preflight["assertions"]["eof_content_read"])

    def test_four_durable_receipts_pass_in_exact_order_without_custody_mutation(self) -> None:
        terminal = load(
            "records/readiness/m2-orbit-offline-verification-recovery-001-terminal-reconciliation.json"
        )
        self.assertEqual([item["source_id"] for item in terminal["results"]], SOURCE_IDS)
        for item in terminal["results"]:
            source_id = item["source_id"]
            self.assertEqual(item["receipt_ref"], RECEIPT_REFS[source_id])
            self.assertEqual(item["receipt_sha256"], sha256(RECEIPT_REFS[source_id]))
            receipt = load(RECEIPT_REFS[source_id])
            self.assertEqual(receipt["status"], "pass_orbit_input_only")
            self.assertTrue(receipt["persistence"]["receipt_reserved_before_eof_content_read"])
            self.assertTrue(receipt["custody_unchanged"])
            self.assertTrue(receipt["promoted_identity_match"])
            self.assertFalse(receipt["claim_boundary"]["scientific_result_established"])

    def test_terminal_state_is_input_only_and_derives_to_dem_vertical_review(self) -> None:
        terminal = load(
            "records/readiness/m2-orbit-offline-verification-recovery-001-terminal-reconciliation.json"
        )
        active = load("contracts/m2-orbit-offline-verification.json")
        milestone = load("contracts/milestone-002.json")
        profile = load("records/project-control-profile.json")
        goal = load("records/long-term-goal.json")
        units = {unit["id"]: unit for unit in milestone["units"]}
        self.assertEqual(terminal["status"], "pass_four_exact_resorb_inputs_verified_no_application")
        self.assertEqual(terminal["next_checkpoint"], "M2-DEM-VERTICAL-DATUM-REVIEW")
        self.assertFalse(terminal["claim_boundary"]["radar_pixel_processing_executed"])
        self.assertFalse(terminal["claim_boundary"]["baseline_established"])
        self.assertEqual(active["status"], "complete_pass_four_orbit_inputs_only")
        self.assertEqual(units["M2-ORBIT-VERIFY"]["gates"]["attempted_source_ids"], SOURCE_IDS)
        self.assertEqual(units["M2-ORBIT-VERIFY"]["gates"]["initial_indeterminate_attempted_source_ids"], ["M2-ORB-001"])
        self.assertFalse(units["M2-ORBIT-APPLY"]["gates"]["orbit_application_started"])
        self.assertEqual(profile["current_checkpoint"]["checkpoint_id"], "M2-DEM-VERTICAL-DATUM-REVIEW")
        self.assertEqual(goal["current_checkpoint"], "M2-DEM-VERTICAL-DATUM-REVIEW")
        self.assertEqual(
            current_orbit_offline_verification_recovery_001_terminal(ROOT, {"promoted": 8}),
            "pass",
        )

    def test_stale_projection_is_preserved_then_aligned_without_new_data_action(self) -> None:
        before = load(
            "records/readiness/m2-orbit-offline-verification-recovery-001-postsuccess-pre-reconciliation-snapshot.json"
        )
        correction = load(
            "records/readiness/m2-orbit-offline-verification-recovery-001-postsuccess-control-reconciliation.json"
        )
        after = load(
            "records/readiness/m2-orbit-offline-verification-recovery-001-postsuccess-post-reconciliation-snapshot.json"
        )
        self.assertEqual(before["recorded_claims"][0]["claimed_value"], ["M2-ORB-001"])
        self.assertEqual(correction["status"], "pass_stale_attempted_source_projection_corrected")
        self.assertEqual(correction["correction"]["after"], SOURCE_IDS)
        self.assertEqual(after["recorded_claims"][0]["claimed_value"], SOURCE_IDS)
        self.assertFalse(correction["assertions"]["eof_content_read"])
        self.assertFalse(correction["assertions"]["external_custody_mutated"])
        self.assertFalse(correction["assertions"]["orbit_application_performed"])


if __name__ == "__main__":
    unittest.main()
