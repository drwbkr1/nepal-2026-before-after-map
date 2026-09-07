from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_m2_orbit_offline_verification_recovery_001 as runner  # noqa: E402
import verify_m2_orbit_eof_recovery_001 as verifier  # noqa: E402
from m2_orbit_io_core import OrbitControlError  # noqa: E402


SOURCE_IDS = ["M2-ORB-001", "M2-ORB-002", "M2-ORB-003", "M2-ORB-004"]
PROPOSAL_SHA256 = "0be64071cfe718ca758155ff0422cfee48af342c8a560528746adc653e6a2fcf"
BUNDLE_SHA256 = "d2f0f75f40614c56bc0e62c6eecb1588f7504f50927448192673e6e403b5933f"
APPROVAL_SHA256 = "315812935fe725b5c2928a27abc2b51faf561c423065de6216f975cecbe81f30"
CANDIDATE_SHA256 = "8db4774dfb36ce9718988c23d9a480a01028055a6a28a1bbf301a926e466df68"


def load(ref: str) -> dict:
    return json.loads((ROOT / ref).read_text(encoding="utf-8"))


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


class OrbitOfflineVerificationRecovery001Tests(unittest.TestCase):
    def test_exact_owner_approval_releases_only_implementation_before_public_ci(self) -> None:
        reconciliation = load("records/source-gates/m2-orbit-offline-verification-recovery-001-review-reconciliation.json")
        approval = load("records/source-gates/m2-orbit-offline-verification-recovery-001-approval.json")
        activation = load("records/readiness/m2-orbit-offline-verification-recovery-001-approval-activation.json")
        self.assertEqual(reconciliation["decision_counts"], {"approve": 1, "revise": 0, "defer": 0})
        self.assertFalse(reconciliation["human_decisions_fabricated"])
        self.assertEqual(sha256("records/source-gates/m2-orbit-offline-verification-recovery-001-approval.json"), APPROVAL_SHA256)
        self.assertEqual(approval["review_bundle_manifest_sha256"], BUNDLE_SHA256)
        self.assertEqual(approval["proposal_sha256"], PROPOSAL_SHA256)
        self.assertEqual(approval["authorized_recovery"]["source_ids_in_exact_order"], SOURCE_IDS)
        self.assertFalse(activation["released_now"]["real_eof_read"])
        self.assertTrue(activation["released_now"]["public_ci"])
        self.assertFalse(activation["released_now"]["external_custody_mutation"])

    def test_candidate_keeps_exact_rules_attempts_and_outputs(self) -> None:
        candidate = load("contracts/m2-orbit-offline-verification-recovery-001.json")
        base = load("contracts/m2-orbit-offline-verification.json")
        self.assertEqual(sha256("contracts/m2-orbit-offline-verification-recovery-001.json"), CANDIDATE_SHA256)
        self.assertEqual(candidate["source_ids_in_exact_order"], SOURCE_IDS)
        self.assertEqual(candidate["asset_requirements"], base["asset_requirements"])
        self.assertEqual(candidate["attempt_policy"]["m2_orb_001_new_recovery_attempts"], 1)
        self.assertEqual(candidate["attempt_policy"]["remaining_source_existing_attempts_per_source"], 1)
        self.assertTrue(candidate["attempt_policy"]["stop_on_first_failure"])
        self.assertFalse(candidate["attempt_policy"]["automatic_retry_authorized"])
        self.assertEqual(candidate["frozen_rules"]["maximum_osv_endpoint_tolerance_seconds"], 1.0)
        self.assertTrue(candidate["frozen_rules"]["source_identity_checksum_xml_osv_units_scene_binding_unchanged"])
        self.assertEqual(list(candidate["output_refs"]), SOURCE_IDS)
        self.assertIn("recovery-001", candidate["output_refs"]["M2-ORB-001"])
        self.assertTrue(all(ref.endswith("offline-verification-001.json") for ref in list(candidate["output_refs"].values())[1:]))

    def test_current_checkpoint_preserves_terminal_input_only_receipts(self) -> None:
        milestone = load("contracts/milestone-002.json")
        units = {item["id"]: item for item in milestone["units"]}
        terminal = load("records/readiness/m2-orbit-offline-verification-recovery-001-terminal-reconciliation.json")
        self.assertEqual(milestone["handoff"]["current_checkpoint"], "M2-DEM-VERTICAL-DATUM-REVIEW")
        self.assertEqual(units["M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-REVIEW"]["status"], "complete")
        self.assertEqual(units["M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-IMPLEMENTATION"]["status"], "complete")
        self.assertEqual(units["M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001"]["status"], "complete")
        self.assertEqual(units["M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001"]["disposition"], "pass")
        self.assertEqual(terminal["status"], "pass_four_exact_resorb_inputs_verified_no_application")
        self.assertFalse(terminal["assertions"]["orbit_application_performed"])
        parent = ROOT / "records/acquisition/orbit-verification"
        self.assertEqual(
            sorted(path.name for path in parent.iterdir()),
            [
                ".gitkeep",
                "m2-orb-001-offline-verification-recovery-001.json",
                "m2-orb-002-offline-verification-001.json",
                "m2-orb-003-offline-verification-001.json",
                "m2-orb-004-offline-verification-001.json",
            ],
        )

    def _fixture(self, temporary: Path):
        project_root = temporary / "project-parent"
        repo = project_root / "repo"
        custody = project_root / "custody"
        eof = custody / "m2-orb-001" / "test.EOF"
        output = repo / verifier.OUTPUT_REFS["M2-ORB-001"]
        eof.parent.mkdir(parents=True)
        output.parent.mkdir(parents=True)
        eof.write_bytes(b"payload")
        asset = {
            "asset_id": "asset-001",
            "destination_relative_path": "m2-orb-001/test.EOF",
            "observed": {"promoted_size_bytes": 7, "promoted_sha256": "abc"},
        }
        intake = {"custody_root": "custody"}
        transfer = {"ref": "receipt.json", "sha256": "receipt-sha", "identity": {"size_bytes": 7, "sha256": "abc"}, "destination_path": str(eof)}
        requirement = {"source_id": "M2-ORB-001"}
        return project_root, repo, custody, eof, output, asset, intake, transfer, requirement

    def test_exclusive_reservation_precedes_inventory_and_eof_inspection(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            values = self._fixture(Path(name))
            project_root, repo, custody, _eof, output, asset, intake, transfer, requirement = values
            events: list[str] = []

            def inventory(_path: Path):
                self.assertTrue(output.exists())
                events.append("inventory")
                return [{"same": True}]

            def inspect(_path: Path, _requirement: dict):
                self.assertTrue(output.exists())
                events.append("inspect")
                return {"status": "pass_orbit_input_only", "observed": {"size_bytes": 7, "sha256": "abc"}, "xml": {"endpoint_tolerance_seconds": 1.0}}

            with (
                patch.object(verifier, "ROOT", repo),
                patch.object(verifier, "PROJECT_ROOT", project_root),
                patch.object(verifier, "guarded_controls", return_value=(intake, {}, {}, requirement)),
                patch.object(verifier, "promoted_binding", return_value=(asset, transfer)),
                patch.object(verifier, "inventory", side_effect=inventory),
                patch.object(verifier, "inspect_eof", side_effect=inspect),
                patch.object(verifier, "sha256", return_value="control-sha"),
            ):
                code, result = verifier.execute("M2-ORB-001", custody, output)
            self.assertEqual(code, 0)
            self.assertEqual(result["status"], "pass_orbit_input_only")
            self.assertEqual(events, ["inventory", "inspect", "inventory"])
            receipt = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(receipt["persistence"]["receipt_reserved_before_eof_content_read"])

    def test_missing_parent_and_collision_stop_before_eof_access(self) -> None:
        for collision in (False, True):
            with self.subTest(collision=collision), tempfile.TemporaryDirectory() as name:
                values = self._fixture(Path(name))
                project_root, repo, custody, _eof, output, asset, intake, transfer, requirement = values
                if collision:
                    output.write_bytes(b"existing")
                else:
                    output.parent.rmdir()
                with (
                    patch.object(verifier, "ROOT", repo),
                    patch.object(verifier, "PROJECT_ROOT", project_root),
                    patch.object(verifier, "guarded_controls", return_value=(intake, {}, {}, requirement)),
                    patch.object(verifier, "promoted_binding", return_value=(asset, transfer)),
                    patch.object(verifier, "inventory", side_effect=AssertionError("inventory must not run")),
                    patch.object(verifier, "inspect_eof", side_effect=AssertionError("inspect must not run")),
                ):
                    code, result = verifier.execute("M2-ORB-001", custody, output)
                self.assertEqual(code, 12)
                self.assertEqual(result["status"], "stopped_before_eof_read")

    def test_interruption_preserves_empty_reservation_and_refuses_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            values = self._fixture(Path(name))
            project_root, repo, custody, _eof, output, asset, intake, transfer, requirement = values
            with (
                patch.object(verifier, "ROOT", repo),
                patch.object(verifier, "PROJECT_ROOT", project_root),
                patch.object(verifier, "guarded_controls", return_value=(intake, {}, {}, requirement)),
                patch.object(verifier, "promoted_binding", return_value=(asset, transfer)),
                patch.object(verifier, "inventory", side_effect=RuntimeError("synthetic interruption")),
            ):
                first_code, first = verifier.execute("M2-ORB-001", custody, output)
                second_code, second = verifier.execute("M2-ORB-001", custody, output)
            self.assertEqual(first_code, 13)
            self.assertTrue(first["reserved_receipt_preserved"])
            self.assertTrue(output.exists())
            self.assertEqual(output.stat().st_size, 0)
            self.assertEqual(second_code, 12)
            self.assertEqual(second["code"], "verification_output_collision")

    def test_complete_failure_receipt_is_durable_and_append_only(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            values = self._fixture(Path(name))
            project_root, repo, custody, _eof, output, asset, intake, transfer, requirement = values
            with (
                patch.object(verifier, "ROOT", repo),
                patch.object(verifier, "PROJECT_ROOT", project_root),
                patch.object(verifier, "guarded_controls", return_value=(intake, {}, {}, requirement)),
                patch.object(verifier, "promoted_binding", return_value=(asset, transfer)),
                patch.object(verifier, "inventory", return_value=[{"same": True}]),
                patch.object(verifier, "inspect_eof", side_effect=OrbitControlError("synthetic_rule_failure")),
                patch.object(verifier, "sha256", return_value="control-sha"),
                patch.object(verifier, "sha256_file", return_value="abc"),
            ):
                first_code, first = verifier.execute("M2-ORB-001", custody, output)
                second_code, second = verifier.execute("M2-ORB-001", custody, output)
            self.assertEqual(first_code, 2)
            self.assertEqual(first["status"], "fail")
            receipt = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(receipt["failure_code"], "synthetic_rule_failure")
            self.assertTrue(receipt["persistence"]["complete_receipt_written_through_reserved_handle"])
            self.assertEqual(second_code, 12)
            self.assertEqual(second["code"], "verification_output_collision")

    def test_fixed_order_stops_on_first_failure_without_retry(self) -> None:
        calls: list[str] = []

        def invoke(source_id: str):
            calls.append(source_id)
            if source_id == "M2-ORB-003":
                return 2, {"status": "fail"}
            return 0, {"status": "pass_orbit_input_only"}

        code, result = runner.run_sequence(invoke)
        self.assertEqual(code, 2)
        self.assertEqual(calls, ["M2-ORB-001", "M2-ORB-002", "M2-ORB-003"])
        self.assertEqual(result["completed_source_ids"], ["M2-ORB-001", "M2-ORB-002"])
        self.assertFalse(result["automatic_retry_performed"])

    def test_all_pass_sequence_is_exactly_four_calls(self) -> None:
        calls: list[str] = []

        def invoke(source_id: str):
            calls.append(source_id)
            return 0, {"status": "pass_orbit_input_only"}

        code, result = runner.run_sequence(invoke)
        self.assertEqual(code, 0)
        self.assertEqual(calls, SOURCE_IDS)
        self.assertEqual(result["completed_source_ids"], SOURCE_IDS)
        self.assertFalse(result["automatic_retry_performed"])


if __name__ == "__main__":
    unittest.main()
