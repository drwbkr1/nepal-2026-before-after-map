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

    def test_initialized_external_custody_contains_no_orbit_payloads(self) -> None:
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
            self.assertEqual([path for path in custody_root.rglob("*") if path.is_file()], [])
            staging_files = [path for path in staging_root.rglob("*") if path.is_file()]
            unexpected = [
                path
                for path in staging_files
                if "attempt-events" not in path.relative_to(staging_root).parts or path.suffix.casefold() != ".json"
            ]
            self.assertEqual(unexpected, [])
        self.assertEqual(self.intake["extensions"]["status"], "active_acquisition_review_required")
        self.assertEqual(
            self.intake["extensions"]["sentinel_custody_prerequisite_status"],
            "partial_three_of_six_promoted_and_verified_one_failed_two_unattempted",
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
