import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import m2_radar_dem_fitness_comparison_001 as comparison  # noqa: E402


def square(x0, y0, x1, y1):
    return [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]


class FakeRaster:
    def __init__(self, data):
        self.data = np.asarray(data)
        self.bandCount = 1 if self.data.ndim == 2 else self.data.shape[0]
        self.spatialReference = SimpleNamespace(factoryCode=4326)
        self.readOnly = True
        self.meanCellWidth = 1.0
        self.meanCellHeight = 1.0
        self.height = self.data.shape[-2]
        self.width = self.data.shape[-1]
        self.extent = SimpleNamespace(XMin=0.0, YMin=0.0)
        self.noDataValues = [-9999.0] * self.bandCount


class FakeArcPy:
    @staticmethod
    def Point(x, y):
        return SimpleNamespace(X=x, Y=y)

    @staticmethod
    def RasterToNumPyArray(raster, point, ncols, nrows):
        col = round(point.X)
        bottom = round(point.Y)
        top_index = raster.height - (bottom + nrows)
        return raster.data[..., top_index:top_index + nrows, col:col + ncols].copy()


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.rings = {
            "AOI-OVERVIEW": square(0, 0, 4, 4),
            "AOI-SOURCE": square(1, 1, 2, 2),
            "AOI-UPPER-CORRIDOR": square(2, 2, 3, 3),
        }

    def test_native_window_counts_and_multiband_order(self):
        data = np.stack((np.ones((4, 4)), np.ones((4, 4)) * 2)).astype(np.float32)
        data[0, 0, 0] = -9999
        data[1, 3, 3] = -9999
        with mock.patch.object(comparison, "BLOCK_SIZE", 2):
            result = comparison.scan_native_raster(FakeArcPy(), FakeRaster(data), self.rings, 2)
        overview = result["aois"]["AOI-OVERVIEW"]
        self.assertEqual(result["block_count"], 4)
        self.assertEqual(overview["total_native_cell_centers"], 16)
        self.assertEqual(overview["valid_per_band"], [15, 15])
        self.assertEqual(overview["valid_all_bands"], 14)
        self.assertEqual(result["aois"]["AOI-SOURCE"]["total_native_cell_centers"], 1)

    def test_coverage_floor_checks_valid_envelope_intersection(self):
        valid = {"aois": {"AOI-OVERVIEW": {"valid_per_band": [2, 2], "valid_all_bands": 2, "valid_envelope_native": [1, 1, 3, 3]}}}
        dem = {"aois": {"AOI-OVERVIEW": {"valid_per_band": [2], "valid_all_bands": 2, "valid_envelope_native": [2, 2, 4, 4]}}}
        self.assertTrue(comparison.coverage_gate(valid, dem))
        dem["aois"]["AOI-OVERVIEW"]["valid_envelope_native"] = [3, 3, 4, 4]
        self.assertFalse(comparison.coverage_gate(valid, dem))

    def test_unknown_nodata_and_shape_fail_closed(self):
        raster = FakeRaster(np.ones((4, 4)))
        raster.noDataValues = [None]
        with self.assertRaisesRegex(comparison.ComparisonError, "nodata_metadata_missing_or_ambiguous"):
            comparison.scan_native_raster(FakeArcPy(), raster, self.rings, 1)
        with self.assertRaisesRegex(comparison.ComparisonError, "raster_array_shape_mismatch"):
            comparison.validity(np.ones((2, 2, 2)), (-9999.0,))


class AttemptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.gamma = self.root / "gamma.crf"
        self.gamma.mkdir()
        self.dem = self.root / "dem.tif"
        self.dem.write_bytes(b"synthetic")
        self.attempt = self.root / "d3"
        self.aoi = self.root / comparison.AOI_REF
        self.aoi.parent.mkdir(parents=True)
        self.aoi.write_text("{}", encoding="utf-8")
        preflight = self.root / comparison.PREFLIGHT_REF
        preflight.parent.mkdir(parents=True)
        preflight.write_text(json.dumps({"status": "pass_final_no_content_preflight_one_attempt_ready", "bindings": {"execution_gate_sha256": "gate"}}), encoding="utf-8")
        for name, value in {
            "ROOT": self.root, "GAMMA": self.gamma, "DEM": self.dem, "ATTEMPT_ROOT": self.attempt,
            "OUTPUT": self.attempt / "gtc_with_existing_dem_diagnostic.crf", "MIN_FREE_BYTES": 0,
        }.items():
            patcher = mock.patch.object(comparison, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        for name in ("verify_authority", "verify_gates", "no_content_paths"):
            patcher = mock.patch.object(comparison, name, return_value={})
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch.object(comparison, "sha256", return_value="gate")
        patcher.start()
        self.addCleanup(patcher.stop)

    def fake_arcpy(self):
        class Raster:
            def __init__(self, source):
                self.source = source
            def save(self, path):
                Path(path).mkdir()
        class IA:
            calls = []
            def ApplyGeometricTerrainCorrection(self, radar, polarization="", dem="", geoid=""):
                self.calls.append((radar.source, polarization, dem, geoid))
                return Raster("result")
        class ArcPy:
            ia = IA()
            env = SimpleNamespace(overwriteOutput=None, scratchWorkspace=None)
            def CheckOutExtension(self, name): return "CheckedOut"
            def CheckInExtension(self, name): return "CheckedIn"
        ArcPy.Raster = Raster
        return ArcPy()

    def test_coverage_block_stops_before_gtc_and_consumes_attempt(self):
        fake = self.fake_arcpy()
        audit = {"aois": {"AOI-OVERVIEW": {"valid_per_band": [0], "valid_all_bands": 0, "valid_envelope_native": None}}}
        with mock.patch.object(comparison, "inspect_no_content", return_value={}), mock.patch.object(comparison, "aoi_native_rings", return_value={}), mock.patch.object(comparison, "scan_native_raster", return_value=audit):
            terminal = comparison.run_comparison(lambda: fake)
        self.assertEqual(terminal["status"], "block_diagnostic_coverage_floor_no_gtc")
        self.assertEqual(fake.ia.calls, [])
        self.assertTrue((self.attempt / "terminal.json").is_file())
        with self.assertRaisesRegex(comparison.ComparisonError, "attempt_root_collision"):
            with mock.patch.object(comparison, "no_content_paths", side_effect=comparison.ComparisonError("attempt_root_collision")):
                comparison.run_comparison(lambda: fake)

    def test_one_dem_supplied_call_save_and_sanitized_terminal(self):
        fake = self.fake_arcpy()
        gamma_audit = {"aois": {"AOI-OVERVIEW": {"valid_per_band": [2, 2], "valid_all_bands": 2, "valid_envelope_native": [1, 1, 3, 3]}}}
        dem_audit = {"aois": {"AOI-OVERVIEW": {"valid_per_band": [2], "valid_all_bands": 2, "valid_envelope_native": [1, 1, 3, 3]}}}
        with mock.patch.object(comparison, "inspect_no_content", return_value={}), mock.patch.object(comparison, "aoi_native_rings", return_value={}), mock.patch.object(comparison, "scan_native_raster", side_effect=[gamma_audit, dem_audit]):
            terminal = comparison.run_comparison(lambda: fake)
        self.assertEqual(terminal["status"], "pass_dem_supplied_gtc_diagnostic_only_output_quarantined")
        self.assertEqual(fake.ia.calls, [(str(self.gamma), "VV;VH", str(self.dem), "NONE")])
        self.assertTrue((self.attempt / "gtc_with_existing_dem_diagnostic.crf").is_dir())
        self.assertNotIn("synthetic", (self.attempt / "terminal.json").read_text())

    def test_gtc_failure_retains_sanitized_terminal_without_retry(self):
        fake = self.fake_arcpy()
        def fail_gtc(*_args):
            raise RuntimeError("ERROR 000425 private-eyJmarker")
        fake.ia.ApplyGeometricTerrainCorrection = fail_gtc
        gamma_audit = {"aois": {"AOI-OVERVIEW": {"valid_per_band": [1, 1], "valid_all_bands": 1, "valid_envelope_native": [1, 1, 2, 2]}}}
        dem_audit = {"aois": {"AOI-OVERVIEW": {"valid_per_band": [1], "valid_all_bands": 1, "valid_envelope_native": [1, 1, 2, 2]}}}
        def audit_after_reservation(*_args):
            self.assertTrue((self.attempt / "terminal-reservation.json").is_file())
            self.assertTrue((self.attempt / "cleanup-reservation.json").is_file())
            return gamma_audit if _args[-1] == 2 else dem_audit
        with mock.patch.object(comparison, "inspect_no_content", return_value={}), mock.patch.object(comparison, "aoi_native_rings", return_value={}), mock.patch.object(comparison, "scan_native_raster", side_effect=audit_after_reservation):
            terminal = comparison.run_comparison(lambda: fake)
        self.assertEqual(terminal["status"], "block_audit_gtc_or_runtime_failure_no_retry")
        self.assertEqual(terminal["arcgis_error_code"], "000425")
        self.assertFalse(terminal["output_save_started"])
        self.assertNotIn("private-eyJmarker", (self.attempt / "terminal.json").read_text())

    def test_terminal_write_failure_preserves_fallback_and_cleanup(self):
        fake = self.fake_arcpy()
        audit = {"aois": {"AOI-OVERVIEW": {"valid_per_band": [0], "valid_all_bands": 0, "valid_envelope_native": None}}}
        original = comparison.write_new_json
        def fail_terminal(path, value):
            if path.name == "terminal.json":
                raise OSError("synthetic receipt failure")
            return original(path, value)
        with mock.patch.object(comparison, "inspect_no_content", return_value={}), mock.patch.object(comparison, "aoi_native_rings", return_value={}), mock.patch.object(comparison, "scan_native_raster", return_value=audit), mock.patch.object(comparison, "write_new_json", side_effect=fail_terminal):
            terminal = comparison.run_comparison(lambda: fake)
        self.assertEqual(terminal["status"], "indeterminate_terminal_persistence_failure_no_retry")
        self.assertTrue((self.attempt / "fallback.jsonl").is_file())
        self.assertTrue((self.attempt / "cleanup.json").is_file())


if __name__ == "__main__":
    unittest.main()
