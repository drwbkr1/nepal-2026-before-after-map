from __future__ import annotations

import ast
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import m2_radar_apply_orbit_correction_input_resolution_diagnostic_receipt_persistence_recovery_001_core as core
import run_m2_radar_apply_orbit_correction_input_resolution_diagnostic_receipt_persistence_recovery_001 as runner


class FakeDescription:
    dataType = "Folder"
    datasetType = "RasterDataset"
    catalogPath = r"C:\fake\candidate"
    children = [1, 2]


class FakeArcPy:
    def __init__(self, existence: bool = True) -> None:
        self.calls: list[str] = []
        self.existence = existence

    def GetInstallInfo(self):
        self.calls.append("GetInstallInfo")
        return {"ProductName": "ArcGISPro", "Version": "3.7.1", "BuildNumber": "123"}

    def ProductInfo(self):
        self.calls.append("ProductInfo")
        return "ArcInfo"

    def CheckExtension(self, name):
        self.calls.append(f"CheckExtension:{name}")
        return "Available"

    def Usage(self, name):
        self.calls.append(f"Usage:{name}")
        return "ApplyOrbitCorrection_ia(in_radar_data, {in_orbit_file}, {folder})"

    def Exists(self, path):
        self.calls.append("Exists")
        return self.existence

    def Describe(self, path):
        self.calls.append("Describe")
        return FakeDescription()


class DiagnosticReceiptPersistenceRecovery001Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads((ROOT / core.CONTRACT_REF).read_text(encoding="utf-8"))

    def synthetic_contract(self, orbit_bytes: bytes = b"orbit") -> dict:
        value = copy.deepcopy(self.contract)
        value["exact_inputs"]["orbit_size_bytes"] = len(orbit_bytes)
        value["exact_inputs"]["orbit_sha256"] = hashlib.sha256(orbit_bytes).hexdigest()
        return value

    def synthetic_paths(
        self,
        root: Path,
        *,
        create_attempt: bool = True,
        create_safe: bool = True,
        create_manifest: bool = True,
        create_orbit: bool = True,
    ) -> dict[str, Path]:
        attempt = root / "attempt"
        safe = attempt / "sources" / "m1-src-001" / "candidate.SAFE"
        manifest = safe / "manifest.safe"
        orbit = root / "orbit.EOF"
        root.mkdir(parents=True, exist_ok=True)
        if create_attempt:
            attempt.mkdir(parents=True)
        if create_safe:
            safe.mkdir(parents=True)
        if create_manifest:
            manifest.write_bytes(b"manifest")
        if create_orbit:
            orbit.write_bytes(b"orbit")
        return {"attempt_root": attempt, "safe_directory": safe, "manifest": manifest, "orbit": orbit}

    def run_body(
        self,
        root: Path,
        *,
        paths: dict[str, Path],
        arcpy_loader,
        terminal_persister=core.persist_reserved,
        cleanup_persister=core.persist_reserved,
    ) -> tuple[int, Path, Path, Path]:
        terminal = root / "outputs" / "terminal.json"
        cleanup = root / "outputs" / "cleanup.json"
        fallback = root / "outputs" / "fallback.jsonl"
        code = runner.execute_diagnostic_body(
            "2026-09-20T18:00:00Z",
            contract=self.synthetic_contract(),
            paths=paths,
            terminal_path=terminal,
            cleanup_path=cleanup,
            fallback_path=fallback,
            bindings={"synthetic": "exact"},
            arcpy_loader=arcpy_loader,
            terminal_persister=terminal_persister,
            cleanup_persister=cleanup_persister,
        )
        return code, terminal, cleanup, fallback

    def test_contract_exact_and_consumed_receipts_immutable(self) -> None:
        self.assertEqual(core.validate_contract(self.contract, ROOT), [])
        self.assertEqual(self.contract["attempt"]["maximum_processes"], 1)
        self.assertFalse(self.contract["attempt"]["automatic_retry"])
        self.assertTrue(all(value == 0 for value in self.contract["limits"].values()))
        for ref in (runner.CONSUMED_TERMINAL_REF, runner.CONSUMED_CLEANUP_REF):
            path = ROOT / ref
            self.assertEqual(path.stat().st_size, 0)
            self.assertEqual(core.sha256_file(path), core.EMPTY_SHA256)

    def test_runner_uses_function_local_datetime_and_delayed_arcpy(self) -> None:
        source = (ROOT / runner.RUNNER_REF).read_text(encoding="utf-8")
        tree = ast.parse(source)
        now_function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "now_utc")
        self.assertTrue(any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in now_function.body))
        top_imports = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
        self.assertFalse(any(isinstance(node, ast.Import) and any(alias.name == "arcpy" for alias in node.names) for node in top_imports))
        runner.datetime = object()
        self.assertTrue(runner.now_utc().endswith("Z"))

    def test_source_has_no_processing_network_copy_or_retry_route(self) -> None:
        source = (ROOT / runner.RUNNER_REF).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imports.update(
            node.module.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        self.assertTrue(imports.isdisjoint({"requests", "urllib", "httpx", "socket", "shutil"}))
        self.assertNotIn(".ApplyOrbitCorrection(", source)
        self.assertNotIn("arcpy.management", source)
        self.assertNotIn("arcpy.analysis", source)
        self.assertNotIn("arcpy.ia.", source)
        self.assertNotIn("copyfile(", source)
        self.assertNotIn("copytree(", source)
        self.assertTrue((ROOT / runner.ARCGIS_VALIDATOR_REF).is_file())

    def test_success_reserves_and_persists_distinct_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self.synthetic_paths(root / "inputs")
            fake = FakeArcPy()
            code, terminal, cleanup, fallback = self.run_body(root, paths=paths, arcpy_loader=lambda: fake)
            self.assertEqual(code, 0)
            terminal_data = json.loads(terminal.read_text(encoding="utf-8"))
            cleanup_data = json.loads(cleanup.read_text(encoding="utf-8"))
            self.assertEqual(terminal_data["status"], "pass_current_input_resolution_diagnostic_only")
            self.assertEqual(cleanup_data["status"], "pass_no_payload_or_temporary_artifact_cleanup_required")
            self.assertFalse(terminal_data["assertions"]["geoprocessing_invoked"])
            events = [json.loads(line)["event"] for line in fallback.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(events[0], "fallback_journal_initialized")
            self.assertIn("terminal_receipt_persisted", events)
            self.assertIn("cleanup_disposition_recorded", events)

    def test_missing_input_captures_original_error_before_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self.synthetic_paths(
                root / "inputs", create_attempt=False, create_safe=False, create_manifest=False
            )
            called = False

            def forbidden_loader():
                nonlocal called
                called = True
                raise AssertionError("ArcPy must not load")

            code, terminal, cleanup, fallback = self.run_body(root, paths=paths, arcpy_loader=forbidden_loader)
            self.assertEqual(code, 20)
            self.assertFalse(called)
            self.assertEqual(json.loads(terminal.read_text())["status"], "block_missing_exact_input_no_retry")
            self.assertTrue(cleanup.is_file())
            records = [json.loads(line) for line in fallback.read_text().splitlines()]
            self.assertEqual(records[2]["event"], "primary_diagnostic_exception_captured")
            self.assertEqual(records[2]["error"]["failure_code"], "exact_recovery_attempt_root_missing")

    def test_terminal_write_failure_preserves_primary_error_and_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self.synthetic_paths(root / "inputs")
            token = "eyJabcdefghijk.abcdefghijk.abcdefghijk"

            def failed_loader():
                raise RuntimeError(f"{token} C:\\secret\\candidate")

            def failed_terminal(handle, value):
                raise OSError("forced terminal persistence failure")

            code, terminal, cleanup, fallback = self.run_body(
                root,
                paths=paths,
                arcpy_loader=failed_loader,
                terminal_persister=failed_terminal,
            )
            self.assertEqual(code, 21)
            self.assertEqual(terminal.stat().st_size, 0)
            self.assertTrue(cleanup.is_file())
            text = fallback.read_text(encoding="utf-8")
            self.assertIn("primary_diagnostic_exception_captured", text)
            self.assertIn("terminal_persistence_exception_captured", text)
            self.assertIn("[REDACTED_TOKEN]", text)
            self.assertNotIn(token, text)
            self.assertNotIn("C:\\secret\\candidate", text)

    def test_cleanup_write_failure_is_recorded_independently(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self.synthetic_paths(root / "inputs")

            def failed_cleanup(handle, value):
                raise OSError("forced cleanup persistence failure")

            code, terminal, cleanup, fallback = self.run_body(
                root,
                paths=paths,
                arcpy_loader=lambda: FakeArcPy(),
                cleanup_persister=failed_cleanup,
            )
            self.assertEqual(code, 22)
            self.assertTrue(terminal.stat().st_size > 0)
            self.assertEqual(cleanup.stat().st_size, 0)
            self.assertIn("cleanup_persistence_exception_captured", fallback.read_text(encoding="utf-8"))

    def test_output_collision_stops_before_external_read(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self.synthetic_paths(root / "inputs")
            terminal = root / "terminal.json"
            terminal.write_text("reserved", encoding="utf-8")
            called = False

            def forbidden_loader():
                nonlocal called
                called = True
                raise AssertionError

            with self.assertRaisesRegex(core.DiagnosticError, "diagnostic_recovery_output_collision"):
                runner.execute_diagnostic_body(
                    "2026-09-20T18:00:00Z",
                    contract=self.synthetic_contract(),
                    paths=paths,
                    terminal_path=terminal,
                    cleanup_path=root / "cleanup.json",
                    fallback_path=root / "fallback.jsonl",
                    bindings={},
                    arcpy_loader=forbidden_loader,
                )
            self.assertFalse(called)

    def test_arcgis_calls_remain_read_only_and_fixed(self) -> None:
        fake = FakeArcPy()
        paths = {name: Path(f"C:/fake/{name}") for name in ("attempt_root", "safe_directory", "manifest", "orbit")}
        result = runner.arcpy_observations(fake, paths)
        self.assertEqual(fake.calls[:5], [
            "GetInstallInfo",
            "ProductInfo",
            "CheckExtension:ImageAnalyst",
            "CheckExtension:Spatial",
            "Usage:ApplyOrbitCorrection_ia",
        ])
        self.assertEqual(fake.calls.count("Exists"), 3)
        self.assertEqual(fake.calls.count("Describe"), 3)
        self.assertIn("catalog_recognition", result)

    def test_filesystem_identity_remains_strict(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = self.synthetic_paths(Path(temporary))
            result = runner.filesystem_observations(paths, self.synthetic_contract())
            self.assertEqual(result["manifest"]["sha256"], hashlib.sha256(b"manifest").hexdigest())
            self.assertEqual(result["orbit"]["sha256"], hashlib.sha256(b"orbit").hexdigest())


if __name__ == "__main__":
    unittest.main()
