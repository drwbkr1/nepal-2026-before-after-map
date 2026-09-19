import ast
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import m2_radar_apply_orbit_correction_input_resolution_diagnostic_001_core as core
import run_m2_radar_apply_orbit_correction_input_resolution_diagnostic_001 as runner


class FakeDescription:
    dataType = "Folder"
    datasetType = "RasterDataset"
    catalogPath = "C:\\fake\\candidate"
    children = [1, 2]


class FakeArcPy:
    def __init__(self, existence=True):
        self.calls = []
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


class InputResolutionDiagnostic001Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads((ROOT / core.CONTRACT_REF).read_text(encoding="utf-8"))

    def synthetic_contract(self, orbit_bytes=b"orbit"):
        value = copy.deepcopy(self.contract)
        value["exact_inputs"]["orbit_size_bytes"] = len(orbit_bytes)
        value["exact_inputs"]["orbit_sha256"] = hashlib.sha256(orbit_bytes).hexdigest()
        return value

    def synthetic_paths(self, root: Path, *, create_attempt=True, create_safe=True, create_manifest=True, create_orbit=True):
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

    def test_contract_is_exact_zero_geoprocessing_and_hash_bound(self):
        self.assertEqual(core.validate_contract(self.contract, ROOT), [])
        self.assertEqual(self.contract["diagnostic"]["maximum_processes"], 1)
        self.assertFalse(self.contract["diagnostic"]["automatic_retry"])
        self.assertTrue(all(value == 0 for value in self.contract["limits"].values()))
        self.assertEqual(self.contract["arcgis_read_only_calls"], core.ALLOWED_ARCPY_CALLS)

    def test_candidate_paths_are_exact_and_contained(self):
        paths = core.external_paths(self.contract)
        self.assertEqual(str(paths["attempt_root"]), core.EXPECTED_ATTEMPT_ROOT)
        self.assertEqual(str(paths["safe_directory"]), str(Path(core.EXPECTED_ATTEMPT_ROOT) / Path(core.EXPECTED_SAFE_RELATIVE)))
        self.assertEqual(str(paths["manifest"]), str(Path(core.EXPECTED_ATTEMPT_ROOT) / Path(core.EXPECTED_MANIFEST_RELATIVE)))
        with self.assertRaises(core.DiagnosticError):
            core.contained_windows_child(core.EXPECTED_ATTEMPT_ROOT, "../escape")

    def test_receipts_reserve_exclusively_and_persist_through_same_handle(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "receipt.json"
            handle = core.reserve_output(path)
            self.assertEqual(path.stat().st_size, 0)
            with self.assertRaises(FileExistsError):
                core.reserve_output(path)
            core.persist_reserved(handle, {"status": "pass"})
            self.assertEqual(json.loads(path.read_text())["status"], "pass")

    def test_filesystem_observation_passes_exact_synthetic_inputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = self.synthetic_paths(Path(temporary))
            result = runner.filesystem_observations(paths, self.synthetic_contract())
            self.assertEqual(result["manifest"]["sha256"], hashlib.sha256(b"manifest").hexdigest())
            self.assertEqual(result["orbit"]["sha256"], hashlib.sha256(b"orbit").hexdigest())

    def test_missing_attempt_root_stops_before_arcpy(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = self.synthetic_paths(Path(temporary), create_attempt=False, create_safe=False, create_manifest=False)
            with self.assertRaisesRegex(core.DiagnosticError, "exact_recovery_attempt_root_missing"):
                runner.filesystem_observations(paths, self.synthetic_contract())

    def test_arcpy_observation_uses_only_read_only_allowlist(self):
        fake = FakeArcPy()
        paths = {name: Path(f"C:/fake/{name}") for name in ("attempt_root", "safe_directory", "manifest", "orbit")}
        result = runner.arcpy_observations(fake, paths)
        self.assertEqual(fake.calls[:5], [
            "GetInstallInfo", "ProductInfo", "CheckExtension:ImageAnalyst", "CheckExtension:Spatial",
            "Usage:ApplyOrbitCorrection_ia",
        ])
        self.assertEqual(fake.calls.count("Exists"), 3)
        self.assertEqual(fake.calls.count("Describe"), 3)
        self.assertIn("catalog_recognition", result)

    def test_source_contains_no_processing_network_or_copy_route(self):
        source = (SCRIPTS / "run_m2_radar_apply_orbit_correction_input_resolution_diagnostic_001.py").read_text(encoding="utf-8")
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

    def _execute_in_temp(self, temporary: str, paths, arcpy_loader):
        temp_root = Path(temporary)
        (temp_root / runner.FINAL_PREFLIGHT_REF).parent.mkdir(parents=True, exist_ok=True)
        (temp_root / runner.IMPLEMENTATION_GATE_REF).parent.mkdir(parents=True, exist_ok=True)
        (temp_root / runner.GATE_STATE_REF).parent.mkdir(parents=True, exist_ok=True)
        (temp_root / runner.IMPLEMENTATION_GATE_REF).write_text("{}\n", encoding="utf-8")
        (temp_root / runner.GATE_STATE_REF).write_text("{}\n", encoding="utf-8")
        preflight = {
            "status": "pass_final_no_content_preflight_one_read_only_diagnostic_released",
            "bindings": {
                "implementation_publication_gate_sha256": core.sha256_file(temp_root / runner.IMPLEMENTATION_GATE_REF),
                "gate_state_publication_sha256": core.sha256_file(temp_root / runner.GATE_STATE_REF),
            },
            "diagnostic_id": core.ATTEMPT_ID,
        }
        (temp_root / runner.FINAL_PREFLIGHT_REF).write_text(json.dumps(preflight), encoding="utf-8")
        contract = self.synthetic_contract()
        gate = {"implementation_commit_sha": "a" * 40, "public_ci_run_id": 1}
        state = {"gate_state_commit_sha": "b" * 40, "public_ci_run_id": 2}
        with (
            mock.patch.object(runner, "ROOT", temp_root),
            mock.patch.object(runner, "implementation_publication_gate", return_value=gate),
            mock.patch.object(runner, "gate_state_publication", return_value=state),
            mock.patch.object(runner, "load_contract", return_value=contract),
            mock.patch.object(runner, "protected_evidence_bindings", return_value={"synthetic": "exact"}),
            mock.patch.object(runner, "repository_bindings", return_value={"synthetic": "exact"}),
        ):
            code = runner.execute_diagnostic(
                "2026-09-19T00:00:00Z", arcpy_loader=arcpy_loader, paths_override=paths
            )
        return code, json.loads((temp_root / runner.TERMINAL_REF).read_text()), json.loads((temp_root / runner.CLEANUP_REF).read_text())

    def test_synthetic_execution_persists_terminal_and_cleanup_without_processing(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = self.synthetic_paths(Path(temporary) / "inputs")
            fake = FakeArcPy()
            code, terminal, cleanup = self._execute_in_temp(temporary, paths, lambda: fake)
            self.assertEqual(code, 0)
            self.assertEqual(terminal["status"], "pass_current_input_resolution_diagnostic_only")
            self.assertFalse(terminal["assertions"]["apply_orbit_correction_invoked"])
            self.assertFalse(terminal["assertions"]["geoprocessing_invoked"])
            self.assertEqual(cleanup["status"], "pass_no_payload_or_temporary_artifact_cleanup_required")

    def test_synthetic_missing_candidate_is_terminal_and_never_imports_arcpy(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = self.synthetic_paths(Path(temporary) / "inputs", create_attempt=False, create_safe=False, create_manifest=False)
            called = False

            def forbidden_loader():
                nonlocal called
                called = True
                raise AssertionError("ArcPy must not be imported")

            code, terminal, _ = self._execute_in_temp(temporary, paths, forbidden_loader)
            self.assertEqual(code, 20)
            self.assertEqual(terminal["status"], "block_missing_exact_input_no_retry")
            self.assertFalse(called)
            self.assertTrue(terminal["assertions"]["diagnostic_process_consumed"])


if __name__ == "__main__":
    unittest.main()
