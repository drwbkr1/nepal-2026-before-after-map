from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT.parent / "nepal-2026-before-after-map-data"
EXPECTED_SOURCE_IDS = [f"M2-ORB-{index:03d}" for index in range(1, 5)]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class M2OrbitPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.gate = load("records/source-gates/m2-orbit-live-source-gate.json")
        cls.preflight = load("records/acquisition/orbit-preflight.json")
        cls.custody = load("records/acquisition/orbit-custody-initialization.json")
        cls.failure = load("records/acquisition/orbit-custody-initialization-attempt-001-failure.json")
        cls.readiness = load("records/acquisition/orbit-custody-initialization-attempt-002-readiness.json")
        cls.intake = load("contracts/m2-orbit-intake.json")

    def test_live_gate_is_ready_but_transfer_prerequisite_is_explicit(self) -> None:
        self.assertEqual(self.gate["decision"]["status"], "ready")
        self.assertEqual(
            self.gate["decision"]["downstream_prerequisite_status"],
            "blocked_on_matching_verified_sentinel_custody",
        )
        self.assertEqual([source["source_id"] for source in self.gate["sources"]], EXPECTED_SOURCE_IDS)
        for source in self.gate["sources"]:
            self.assertTrue(all(item["status"] == "pass" for item in source["criteria"]))
        self.assertIn("silently substitute later precise orbit files", self.gate["write_boundary"]["still_prohibited"])

    def test_preflight_revalidates_exact_sources_rights_paths_and_storage(self) -> None:
        self.assertEqual(
            self.preflight["status"],
            "pass_no_payload_no_external_mutation_sentinel_custody_pending",
        )
        self.assertEqual(len(self.preflight["live_products"]), 4)
        self.assertTrue(all(item["status"] == "pass_exact_identity_online_unchanged" for item in self.preflight["live_products"]))
        self.assertTrue(all(item["status"] == "pass_exact_reviewed_bytes" for item in self.preflight["live_rights_pages"]))
        self.assertEqual(self.preflight["path_checks"]["status"], "pass")
        self.assertEqual(self.preflight["storage_check"]["status"], "pass")
        self.assertEqual(self.preflight["sentinel_custody_prerequisite"]["promoted_and_verified_count"], 0)
        assertions = self.preflight["assertions"]
        self.assertEqual(assertions["orbit_payload_bytes_requested"], 0)
        self.assertFalse(assertions["authentication_performed"])
        self.assertFalse(assertions["credential_values_read_or_recorded"])
        self.assertFalse(assertions["precise_substitution_authorized"])

    def test_failed_initialization_and_exact_correction_are_preserved(self) -> None:
        self.assertEqual(
            self.failure["status"],
            "failed_missing_attempt_events_parent_after_partial_empty_directory_creation",
        )
        self.assertEqual(len(self.failure["observed_partial_directories"]), 7)
        self.assertEqual(self.failure["observed_files"], [])
        self.assertFalse(self.failure["assertions"]["retry_in_attempt_001_authorized"])
        self.assertEqual(
            self.readiness["status"],
            "pass_exact_empty_partial_inventory_continuation_predeclared",
        )
        self.assertEqual(
            self.readiness["failure_sha256"],
            sha256_path(ROOT / "records/acquisition/orbit-custody-initialization-attempt-001-failure.json"),
        )
        self.assertEqual(
            self.readiness["implementation_sha256"],
            sha256_path(ROOT / "scripts/initialize_m2_orbit_custody.py"),
        )

    def test_initialization_receipt_remains_and_current_custody_contains_all_approved_orbits(self) -> None:
        self.assertEqual(self.custody["status"], "created_and_verified_empty")
        self.assertEqual(self.custody["verification"]["preserved_partial_directory_count"], 7)
        self.assertEqual(self.custody["verification"]["created_directory_count_attempt_002"], 10)
        self.assertTrue(self.custody["verification"]["all_paths_exist"])
        self.assertTrue(self.custody["verification"]["all_paths_not_reparse_points"])
        external_receipt = Path(self.custody["paths"]["external_receipt"])
        if external_receipt.is_file():
            self.assertEqual(sha256_path(external_receipt), sha256_path(ROOT / "records/acquisition/orbit-custody-initialization.json"))
            custody_root = Path(self.custody["paths"]["custody_root"])
            staging_root = Path(self.custody["paths"]["staging_root"])
            custody_files = [path for path in custody_root.rglob("*") if path.is_file()]
            expected = {
                "S1D_OPER_AUX_RESORB_OPOD_20260816T143208_V20260816T103526_20260816T140956.EOF": "a72c93e500a1c09b62b4cd31889837c9d57ccc41542b16397ff9f2c0fccba3f4",
                "S1D_OPER_AUX_RESORB_OPOD_20260819T014707_V20260818T215010_20260819T012120.EOF": "7462fa65549339c09c36338cb690d0b953c665c3c61a397def3cfa7b2d453262",
                "S1D_OPER_AUX_RESORB_OPOD_20260828T143236_V20260828T103527_20260828T140957.EOF": "c08bf997f1bf02fb25dcf2a4f35643aef4754fbea03c6c2fb0fa9db4a0efe778",
                "S1D_OPER_AUX_RESORB_OPOD_20260831T014822_V20260830T215011_20260831T012111.EOF": "281388e94a7a8a708f229fd7d19f93de426bb077699db3aaabdad7125043bd83",
            }
            self.assertEqual(len(custody_files), 4)
            self.assertEqual({path.name: sha256_path(path) for path in custody_files}, expected)
            staging_files = [path for path in staging_root.rglob("*") if path.is_file()]
            unexpected = [
                path
                for path in staging_files
                if "attempt-events" not in path.relative_to(staging_root).parts or path.suffix.casefold() != ".json"
            ]
            self.assertEqual(unexpected, [])
        self.assertEqual(self.intake["extensions"]["status"], "active_all_four_orbits_promoted_input_verified")
        self.assertEqual(
            self.intake["extensions"]["sentinel_custody_prerequisite_status"],
            "all_six_promoted_and_container_verified",
        )

    def test_evidence_ledger_contains_preflight_failure_correction_and_success(self) -> None:
        ledger = [json.loads(line) for line in (ROOT / "records/evidence-ledger.jsonl").read_text(encoding="utf-8").splitlines()]
        by_id = {item["record_id"]: item for item in ledger}
        self.assertEqual(by_id["EVID-0054"]["preflight_sha256"], sha256_path(ROOT / "records/acquisition/orbit-preflight.json"))
        self.assertEqual(by_id["EVID-0055"]["failure_sha256"], sha256_path(ROOT / "records/acquisition/orbit-custody-initialization-attempt-001-failure.json"))
        self.assertEqual(by_id["EVID-0056"]["readiness_sha256"], sha256_path(ROOT / "records/acquisition/orbit-custody-initialization-attempt-002-readiness.json"))
        self.assertEqual(by_id["EVID-0057"]["custody_receipt_sha256"], sha256_path(ROOT / "records/acquisition/orbit-custody-initialization.json"))
        self.assertFalse(by_id["EVID-0057"]["assertions"]["authentication_performed"])
        self.assertEqual(by_id["EVID-0057"]["assertions"]["orbit_payload_bytes_requested"], 0)


if __name__ == "__main__":
    unittest.main()
