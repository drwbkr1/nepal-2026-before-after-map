import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from scripts import m2_radar_gtc_input_compatibility_diagnostic_001 as diagnostic


class FakeArcPy:
    def __init__(self, missing_index=None):
        self.missing_index = missing_index
        self.exists_calls = 0
        self.describe_calls = 0
        self.ia = SimpleNamespace(ApplyGeometricTerrainCorrection=lambda *_: None)

    def ProductInfo(self):
        return "ArcInfo"

    def CheckExtension(self, _name):
        return "Available"

    def Exists(self, _path):
        index = self.exists_calls
        self.exists_calls += 1
        return index != self.missing_index

    def Describe(self, path):
        self.describe_calls += 1
        band_count = 1 if path.endswith(".tif") else 2
        return SimpleNamespace(
            dataType="RasterDataset", datasetType="Raster Dataset", format="CRF",
            bandCount=band_count, pixelType="F32", meanCellWidth=10.0,
            meanCellHeight=10.0, spatialReference=SimpleNamespace(factoryCode=32645),
            extent=SimpleNamespace(XMin=0, XMax=20, YMin=0, YMax=20),
            isMultidimensional=False,
        )


class GtcDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.recovery = self.root / "a1"
        self.recovery.mkdir()
        for ref in diagnostic.CANDIDATES:
            path = self.recovery / ref
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"synthetic metadata fixture")
        self.diagnostic_root = self.root / "d1"
        preflight = self.root / diagnostic.PREFLIGHT_REF
        preflight.parent.mkdir(parents=True, exist_ok=True)
        preflight.write_text(json.dumps({"status": "pass_no_content_single_attempt_ready"}), encoding="utf-8")
        patches = [
            mock.patch.object(diagnostic, "ROOT", self.root),
            mock.patch.object(diagnostic, "RECOVERY_ROOT", self.recovery),
            mock.patch.object(diagnostic, "DIAGNOSTIC_ROOT", self.diagnostic_root),
            mock.patch.object(diagnostic, "verify_public_bindings", return_value=({}, {})),
            mock.patch.object(diagnostic, "verify_gate", return_value={}),
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_one_process_observes_metadata_and_second_invocation_stops(self):
        fake = FakeArcPy()
        result = diagnostic.run_diagnostic(lambda: fake)
        self.assertEqual(result["status"], "pass_current_structural_metadata_observed_only")
        self.assertEqual(len(result["candidate_observations"]), 6)
        self.assertEqual(fake.describe_calls, 6)
        self.assertTrue(result["structural_comparisons"]["dem_single_band_observed"])
        self.assertNotIn(str(self.recovery), json.dumps(result))
        with self.assertRaisesRegex(diagnostic.DiagnosticError, "diagnostic_attempt_root_collision"):
            diagnostic.run_diagnostic(lambda: self.fail("second import"))

    def test_missing_candidate_consumes_process_before_arcpy_import(self):
        (self.recovery / diagnostic.CANDIDATES[1]).unlink()
        result = diagnostic.run_diagnostic(lambda: self.fail("ArcPy import after missing candidate"))
        self.assertEqual(result["status"], "block_exact_candidate_or_catalog")
        self.assertEqual(result["failure_code"], "exact_candidate_1_missing")
        self.assertTrue((self.diagnostic_root / "terminal.json").is_file())
        self.assertTrue((self.diagnostic_root / "cleanup.json").is_file())

    def test_catalog_failure_preserves_prior_metadata_without_geoprocessing(self):
        fake = FakeArcPy(missing_index=2)
        result = diagnostic.run_diagnostic(lambda: fake)
        self.assertEqual(result["failure_code"], "candidate_2_not_recognized_by_arcgis")
        self.assertEqual(len(result["candidate_observations"]), 2)
        self.assertEqual(fake.describe_calls, 2)
        self.assertFalse(result["assertions"]["geoprocessing_called"])


if __name__ == "__main__":
    unittest.main()
