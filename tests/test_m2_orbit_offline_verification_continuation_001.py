from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import verify_m2_orbit_eof as verifier  # noqa: E402
from m2_orbit_io_core import OrbitControlError  # noqa: E402


SOURCE_IDS = ["M2-ORB-001", "M2-ORB-002", "M2-ORB-003", "M2-ORB-004"]


def load(ref: str) -> dict:
    return json.loads((ROOT / ref).read_text(encoding="utf-8"))


class OrbitOfflineVerificationContinuation001Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.intake = load("contracts/m2-orbit-intake.json")
        cls.active = load("contracts/m2-orbit-offline-verification.json")
        cls.candidate = load("contracts/m2-orbit-offline-verification-continuation-001.json")

    def test_candidate_projects_exact_source_order_and_one_second_rules(self) -> None:
        self.assertEqual(
            self.candidate["status"],
            "terminal_consumed_m2_orb_001_receipt_persistence_failure",
        )
        self.assertEqual([item["source_id"] for item in self.candidate["asset_requirements"]], SOURCE_IDS)
        self.assertEqual(
            [item["maximum_osv_endpoint_tolerance_seconds"] for item in self.candidate["asset_requirements"]],
            [1.0, 1.0, 1.0, 1.0],
        )
        self.assertEqual(
            self.candidate["authority"]["remaining_sources_endpoint_approval_sha256"],
            hashlib.sha256((ROOT / "records/source-gates/m2-orbit-continuation-001-approval.json").read_bytes()).hexdigest(),
        )

    def test_current_complete_contract_blocks_additional_real_eof_reads_after_pass(self) -> None:
        self.assertEqual(
            self.active["status"],
            "complete_pass_four_orbit_inputs_only",
        )
        with self.assertRaisesRegex(OrbitControlError, "active_orbit_verification_binding_drift"):
            verifier.guarded_controls()

    def test_promoted_binding_accepts_preserved_local_m2_orb_001_evidence(self) -> None:
        asset, evidence = verifier.promoted_binding(self.intake, "M2-ORB-001")
        self.assertEqual(asset["state"], "promoted")
        self.assertEqual(evidence["attempt_id"], "m2-orb-001-osv-precision-amendment-001-local-001")
        self.assertEqual(evidence["ref"], "records/acquisition/m2-orbit-osv-precision-amendment-001-local-validation.json")
        self.assertEqual(evidence["identity"]["sha256"], asset["observed"]["promoted_sha256"])

    def test_promoted_binding_accepts_exact_continuation_receipts(self) -> None:
        for source_id in SOURCE_IDS[1:]:
            asset, evidence = verifier.promoted_binding(self.intake, source_id)
            self.assertIn("-continuation-001-", evidence["attempt_id"])
            self.assertEqual(evidence["identity"]["sha256"], asset["observed"]["promoted_sha256"])
            self.assertTrue(evidence["ref"].startswith("records/acquisition/orbit-attempts/"))

    def test_duplicate_success_attempt_is_rejected(self) -> None:
        changed = copy.deepcopy(self.intake)
        asset = next(item for item in changed["assets"] if item["extensions"]["source_id"] == "M2-ORB-002")
        asset["attempts"].append(copy.deepcopy(asset["attempts"][0]))
        with self.assertRaisesRegex(OrbitControlError, "orbit_asset_not_promoted_by_exactly_one_success"):
            verifier.promoted_binding(changed, "M2-ORB-002")


if __name__ == "__main__":
    unittest.main()
