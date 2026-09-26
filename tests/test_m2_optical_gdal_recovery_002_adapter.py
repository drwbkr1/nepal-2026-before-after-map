"""Source-free tests for the optical GDAL adapter; no project custody."""

from __future__ import annotations

import sys
import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from m2_optical_gdal_recovery_002_adapter import polygon_area  # noqa: E402
import m2_optical_gdal_recovery_002_core as core  # noqa: E402
import m2_optical_gdal_recovery_002_execute as execute  # noqa: E402
import m2_optical_gdal_recovery_002_worker as worker  # noqa: E402
import m2_optical_gdal_recovery_002_engine as engine  # noqa: E402
from optical_input_readiness_core import ROLE_PATTERNS  # noqa: E402


class GeometryTests(unittest.TestCase):
    def test_closed_square_area(self) -> None:
        self.assertEqual(polygon_area([[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]), 100)

    def test_invalid_ring_blocks(self) -> None:
        with self.assertRaisesRegex(ValueError, "gdal_aoi_ring_invalid"):
            polygon_area([[[0, 0], [10, 0], [10, 10], [0, 10]]])


class AuthorityAndReceiptTests(unittest.TestCase):
    def test_exact_packet_and_source_binding(self) -> None:
        self.assertEqual(core.require_packet_release()["proposal_id"],
                         "NEPAL-M2-OPTICAL-GDAL-HEADER-PIXEL-RECOVERY-002")
        self.assertEqual([item["source_id"] for item in core.exact_sources()], list(core.SOURCE_IDS))
        self.assertFalse(core.frozen_binding()["automatic_retry"])

    def test_unpublished_execution_gate_stops_protected_access(self) -> None:
        with patch.object(core, "IMPLEMENTATION", ROOT / "tests/never-a-real-gate.json"):
            with self.assertRaises(core.PilotControlError):
                core.require_execution_release()

    def test_child_environment_removes_secret_keys(self) -> None:
        self.assertEqual(execute.child_environment({"PATH": "synthetic", "CDSE_TOKEN": "secret-value",
                                                    "PASSWORD": "secret-value", "API_KEY": "secret-value"}),
                         {"PATH": "synthetic"})

    def test_untrusted_receipt_never_echoes_secret_text(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            attempt = Path(folder)
            (attempt / "worker-terminal.json").write_text(json.dumps({
                "status": "stopped", "stage": "secret-value", "error_class": "secret-value",
                "safe_code": "secret-value", "pixel_status": "secret-value",
            }), encoding="utf-8")
            with patch.object(execute, "ATTEMPT_ROOT", attempt), \
                    patch.object(execute, "HEADER_RECEIPT", attempt / "header.json"), \
                    patch.object(execute, "PIXEL_RECEIPT", attempt / "pixel.json"):
                result = execute.terminal_from_child(20)
        self.assertNotIn("secret-value", json.dumps(result))
        self.assertEqual(result["stage"], "child_no_terminal_receipt")

    def test_worker_import_failure_preserves_safe_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            attempt = Path(folder)
            for name in ("started.json", "terminal-reserved.json", "cleanup-reserved.json"):
                (attempt / name).write_text("{}", encoding="utf-8")
            with patch.object(worker, "ATTEMPT", attempt), patch.object(sys, "argv", ["worker", "--real"]), \
                    patch.dict(sys.modules, {"m2_optical_gdal_recovery_002_engine": None}):
                code = worker.main()
            self.assertEqual(code, 20)
            terminal = json.loads((attempt / "worker-terminal.json").read_text(encoding="utf-8"))
            self.assertEqual(terminal["stage"], "project_imports")
            self.assertFalse(terminal["exception_text_recorded"])

    def test_supervisor_reserves_receipts_and_never_retries_after_interruption(self) -> None:
        proposal = {"exact_existing_sources": [
            {"archive_sha256": "a", "materialization_manifest_sha256": "b"},
            {"archive_sha256": "c", "materialization_manifest_sha256": "d"},
        ]}
        identities = [
            {"source_id": "M2-OPT-001", "archive_sha256": "a", "manifest_sha256": "b"},
            {"source_id": "M2-OPT-002", "archive_sha256": "c", "manifest_sha256": "d"},
        ]
        preflight = {"sources_in_order": identities, "raster_pixel_values_decoded": False}
        calls: list[str] = []

        def read_fixture(path):
            return preflight if Path(path) == execute.FINAL_PREFLIGHT else proposal

        def interrupted(_argv, **kwargs):
            calls.append("spawn")
            self.assertTrue((attempt / "terminal-reserved.json").is_file())
            self.assertTrue((attempt / "cleanup-reserved.json").is_file())
            self.assertNotIn("secret-value", json.dumps(kwargs["env"]))
            raise OSError("secret-value")

        with tempfile.TemporaryDirectory() as folder:
            attempt = Path(folder) / "attempt"
            public = Path(folder) / "terminal.json"
            with patch.object(execute, "ATTEMPT_ROOT", attempt), \
                    patch.object(execute, "PUBLIC_TERMINAL", public), \
                    patch.object(execute, "HEADER_RECEIPT", attempt / "header.json"), \
                    patch.object(execute, "PIXEL_RECEIPT", attempt / "pixel.json"), \
                    patch.object(execute, "require_execution_release"), \
                    patch.object(execute, "read_json", side_effect=read_fixture), \
                    patch.object(execute, "exact_sources", return_value=[
                        {"source_id": "M2-OPT-001"}, {"source_id": "M2-OPT-002"}]), \
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

    def test_reservation_failure_consumes_identity_without_spawning(self) -> None:
        proposal = {"exact_existing_sources": [
            {"archive_sha256": "a", "materialization_manifest_sha256": "b"},
            {"archive_sha256": "c", "materialization_manifest_sha256": "d"},
        ]}
        preflight = {"raster_pixel_values_decoded": False, "sources_in_order": [
            {"source_id": "M2-OPT-001", "archive_sha256": "a", "manifest_sha256": "b"},
            {"source_id": "M2-OPT-002", "archive_sha256": "c", "manifest_sha256": "d"},
        ]}
        written = execute.write_new_json
        calls = []

        def fail_reservation(path, value):
            if Path(path).name == "terminal-reserved.json":
                raise OSError("secret-value")
            return written(path, value)

        def forbidden_spawn(*_args, **_kwargs):
            calls.append("spawn")
            raise AssertionError("worker must not spawn")

        with tempfile.TemporaryDirectory() as folder:
            attempt = Path(folder) / "attempt"
            public = Path(folder) / "terminal.json"

            def read_fixture(path):
                return preflight if Path(path) == execute.FINAL_PREFLIGHT else proposal

            with patch.object(execute, "ATTEMPT_ROOT", attempt), \
                    patch.object(execute, "PUBLIC_TERMINAL", public), \
                    patch.object(execute, "require_execution_release"), \
                    patch.object(execute, "read_json", side_effect=read_fixture), \
                    patch.object(execute, "exact_sources", return_value=[
                        {"source_id": "M2-OPT-001"}, {"source_id": "M2-OPT-002"}]), \
                    patch.object(execute, "write_new_json", side_effect=fail_reservation):
                result = execute.run_once(runner=forbidden_spawn)
            self.assertEqual(result["stage"], "receipt_reservation")
            self.assertEqual(calls, [])
            self.assertTrue((attempt / "terminal.json").is_file())
            self.assertTrue((attempt / "cleanup.json").is_file())
            self.assertNotIn("secret-value", public.read_text(encoding="utf-8"))


class SourceIdentityTests(unittest.TestCase):
    def test_selected_members_rechecked_before_header_and_mutation_blocks(self) -> None:
        product = "S2A_MSIL2A_20260824T050231_N0512_R119_T45RUM_20260824T115710.SAFE"
        source = {"source_id": "M2-OPT-001", "exact_product_name": product}
        metadata = ("<root><PROCESSING_BASELINE>05.12</PROCESSING_BASELINE>"
                    "<SPECIAL_VALUE_TEXT>NODATA</SPECIAL_VALUE_TEXT><SPECIAL_VALUE_INDEX>0</SPECIAL_VALUE_INDEX>"
                    "<BOA_QUANTIFICATION_VALUE>10000</BOA_QUANTIFICATION_VALUE>"
                    + "".join(f'<BOA_ADD_OFFSET band_id="{i}">-1000</BOA_ADD_OFFSET>' for i in range(13))
                    + "</root>")
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder) / "m2-opt-001/materialization-001"
            safe = base / product
            safe.mkdir(parents=True)
            files = []
            for role, pattern in ROLE_PATTERNS.items():
                relative = pattern.replace("*", "SYNTHETIC")
                path = safe / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                content = metadata.encode() if role == "metadata_product" else b"synthetic-disposable"
                path.write_bytes(content)
                files.append({"relative_path": relative, "size_bytes": len(content),
                              "sha256": hashlib.sha256(content).hexdigest()})
            (base / "materialization-manifest.json").write_text(
                json.dumps({"status": "complete", "files": files}), encoding="utf-8")
            with patch.object(engine, "describe", return_value={"format": "JP2"}) as described:
                result, paths = engine.inspect_one(
                    source, engine.read_json(engine.HEADER_CONTRACT), Path(folder))
            self.assertEqual(result["inventory_status"], "pass_inventory_only")
            self.assertEqual(result["metadata_errors"], [])
            self.assertEqual(described.call_count, 8)
            self.assertEqual(len(paths), 10)
            paths["SCL"].write_bytes(b"modified-disposable")
            with self.assertRaises(core.PilotControlError):
                engine.inspect_one(source, engine.read_json(engine.HEADER_CONTRACT), Path(folder))


if __name__ == "__main__":
    unittest.main()
