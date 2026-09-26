"""Disposable controls for the distinct offline optical recovery."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import m2_optical_pair_header_recovery_001_core as core  # noqa: E402
import m2_optical_pair_header_recovery_001_execute as execute  # noqa: E402
import m2_optical_pair_header_recovery_001_header as header  # noqa: E402
import m2_optical_pair_header_recovery_001_worker as worker  # noqa: E402


class RecoveryControlTests(unittest.TestCase):
    def test_exact_packet_is_released_but_real_gate_is_not_yet_present(self) -> None:
        proposal = core.require_packet_release()
        self.assertEqual([item["source_id"] for item in proposal["exact_existing_inputs"]],
                         ["M2-OPT-001", "M2-OPT-002"])
        with patch.object(core, "IMPLEMENTATION_READINESS", ROOT / "tests/never-a-real-gate.json"):
            with self.assertRaises(core.PilotControlError):
                core.require_execution_release()

    def test_child_environment_strips_secret_keys(self) -> None:
        result = execute.child_environment({"PATH": "synthetic", "CDSE_TOKEN": "secret-value",
                                            "AUTHORIZATION": "secret-value", "API_KEY": "secret-value"})
        self.assertEqual(result, {"PATH": "synthetic"})

    def test_untrusted_child_receipt_cannot_publish_secret_text(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            attempt = Path(folder)
            (attempt / "worker-terminal.json").write_text(json.dumps({
                "status": "stopped", "stage": "secret-value", "error_class": "secret-value",
                "safe_code": "secret-value", "header_status": "secret-value",
            }), encoding="utf-8")
            with patch.object(execute, "ATTEMPT_ROOT", attempt), patch.object(execute, "HEADER_RECEIPT", attempt / "header.json"), \
                    patch.object(execute, "PIXEL_RECEIPT", attempt / "pixel.json"):
                result = execute.terminal_from_child(20)
        self.assertNotIn("secret-value", json.dumps(result))
        self.assertEqual(result["stage"], "child_no_terminal_receipt")

    def test_header_uses_frozen_checks_and_stops_on_first_source_failure(self) -> None:
        sources = [{"source_id": "M2-OPT-001"}, {"source_id": "M2-OPT-002"}]
        calls: list[str] = []

        def fail_first(source, _arcpy, _contract):
            calls.append(source["source_id"])
            raise core.PilotControlError("synthetic_first_source_failure")

        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "header.json"
            with patch.object(header, "require_execution_release"), patch.object(header, "inspect_materialized_one", side_effect=fail_first):
                with self.assertRaises(core.PilotControlError):
                    header.inspect_recovery_headers(sources, object(), output)
            self.assertFalse(output.exists())
        self.assertEqual(calls, ["M2-OPT-001"])

    def test_worker_early_import_failure_writes_stage_and_safe_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            attempt = Path(folder)
            with patch.object(worker, "ATTEMPT", attempt), patch.object(sys, "argv", ["worker", "--real"]), \
                    patch.dict(sys.modules, {"m2_optical_pair_header_recovery_001_pixel": None}):
                code = worker.main()
            self.assertEqual(code, 20)
            self.assertTrue((attempt / "child-started.json").is_file())
            terminal = json.loads((attempt / "worker-terminal.json").read_text(encoding="utf-8"))
            self.assertEqual(terminal["stage"], "project_imports")
            self.assertFalse(terminal["exception_text_recorded"])

    def test_parent_reserves_receipts_and_never_retries_after_interruption(self) -> None:
        proposal = {"exact_existing_inputs": [
            {"verified_archive_sha256": "a", "materialization_manifest_sha256": "b"},
            {"verified_archive_sha256": "c", "materialization_manifest_sha256": "d"},
        ]}
        identities = [
            {"source_id": "M2-OPT-001", "archive_sha256": "a", "manifest_sha256": "b"},
            {"source_id": "M2-OPT-002", "archive_sha256": "c", "manifest_sha256": "d"},
        ]
        preflight = {"sources_in_order": identities, "arcgis_runtime": {"version": "3.7.1", "spatial": "Available"}}
        calls: list[str] = []

        def interrupted(_argv, **kwargs):
            calls.append("spawn")
            self.assertTrue((attempt / "terminal-reserved.json").is_file())
            self.assertTrue((attempt / "cleanup-reserved.json").is_file())
            self.assertTrue((attempt / "stage-plan.json").is_file())
            self.assertFalse(any("secret-value" in value for value in kwargs["env"].values()))
            raise OSError("secret-value")

        with tempfile.TemporaryDirectory() as folder:
            attempt = Path(folder) / "attempt"
            public = Path(folder) / "terminal.json"
            with patch.object(execute, "ATTEMPT_ROOT", attempt), patch.object(execute, "PUBLIC_TERMINAL", public), \
                    patch.object(execute, "HEADER_RECEIPT", attempt / "header.json"), \
                    patch.object(execute, "PIXEL_RECEIPT", attempt / "pixel.json"), \
                    patch.object(execute, "require_execution_release", return_value=proposal), \
                    patch.object(execute, "read_json", return_value=preflight), \
                    patch.object(execute, "exact_sources", return_value=[{"source_id": "M2-OPT-001"}, {"source_id": "M2-OPT-002"}]), \
                    patch.object(execute, "inventory_materialized", side_effect=identities), \
                    patch.dict(execute.os.environ, {"CDSE_TOKEN": "secret-value"}):
                result = execute.run_once(runner=interrupted)
                self.assertEqual(result["status"], "stopped")
                self.assertEqual(result["stage"], "supervisor_spawn_or_receipt")
                self.assertTrue((attempt / "terminal.json").is_file())
                self.assertTrue((attempt / "cleanup.json").is_file())
                self.assertNotIn("secret-value", public.read_text(encoding="utf-8"))
                with self.assertRaises(core.PilotControlError):
                    execute.run_once(runner=interrupted)
        self.assertEqual(calls, ["spawn"])

    def test_terminal_persistence_failure_does_not_suppress_cleanup(self) -> None:
        proposal = {"exact_existing_inputs": [
            {"verified_archive_sha256": "a", "materialization_manifest_sha256": "b"},
            {"verified_archive_sha256": "c", "materialization_manifest_sha256": "d"},
        ]}
        identities = [
            {"source_id": "M2-OPT-001", "archive_sha256": "a", "manifest_sha256": "b"},
            {"source_id": "M2-OPT-002", "archive_sha256": "c", "manifest_sha256": "d"},
        ]
        preflight = {"sources_in_order": identities, "arcgis_runtime": {"version": "3.7.1", "spatial": "Available"}}
        original_write = execute.write_new_json

        def fail_terminal(path, value):
            if path.name == "terminal.json":
                raise OSError("synthetic persistence failure")
            original_write(path, value)

        with tempfile.TemporaryDirectory() as folder:
            attempt = Path(folder) / "attempt"
            public = Path(folder) / "public.json"
            with patch.object(execute, "ATTEMPT_ROOT", attempt), patch.object(execute, "PUBLIC_TERMINAL", public), \
                    patch.object(execute, "HEADER_RECEIPT", attempt / "header.json"), \
                    patch.object(execute, "PIXEL_RECEIPT", attempt / "pixel.json"), \
                    patch.object(execute, "require_execution_release", return_value=proposal), \
                    patch.object(execute, "read_json", return_value=preflight), \
                    patch.object(execute, "exact_sources", return_value=[{"source_id": "M2-OPT-001"}, {"source_id": "M2-OPT-002"}]), \
                    patch.object(execute, "inventory_materialized", side_effect=identities), \
                    patch.object(execute, "write_new_json", side_effect=fail_terminal):
                result = execute.run_once(runner=lambda *_args, **_kwargs: SimpleNamespace(returncode=20))
            self.assertEqual(result["stage"], "receipt_persistence")
            self.assertEqual(result["receipt_persistence_errors"], ["terminal"])
            self.assertTrue((attempt / "cleanup.json").is_file())
            self.assertTrue(public.is_file())


if __name__ == "__main__":
    unittest.main()
