"""Portable stops for the approved native-GTC grid recovery candidate."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from m2_radar_event_pair_native_gtc_recovery_003_core import (  # noqa: E402
    NativeGridStop, TARGET, guard_materialized_size, inspect_returned_raster,
    native_gtc_call, native_gtc_environment, project_with_frozen_extent,
    projected_grid_description,
)
import m2_radar_event_pair_native_gtc_recovery_003 as runner  # noqa: E402
import m2_radar_event_pair_native_gtc_recovery_003_processing as processing  # noqa: E402


def bounds(xmin=85.0, ymin=28.0, xmax=86.0, ymax=29.0):
    return SimpleNamespace(XMin=xmin, YMin=ymin, XMax=xmax, YMax=ymax)


def raster(**changes):
    result = dict(spatialReference=SimpleNamespace(factoryCode=4326), width=4000,
                  height=4000, bandCount=2, meanCellWidth=0.00025,
                  meanCellHeight=0.00025, extent=bounds(), isTemporary=True,
                  pixelType="F32")
    result.update(changes)
    return SimpleNamespace(**result)


SOURCE = (84.0, 27.0, 87.0, 30.0)
AOIS = ((85.2, 28.2, 85.4, 28.4), (85.3, 28.3, 85.5, 28.5))


class FakeArcPy:
    def __init__(self):
        self.env = SimpleNamespace(cellSize=10.0, snapRaster="projected-snap",
                                   outputCoordinateSystem="projected-crs", extent="projected-extent",
                                   resamplingMethod="BILINEAR")
        self.calls = []

    def ClearEnvironment(self, name):
        self.calls.append(("clear", name))
        setattr(self.env, name, None)


class NativeGridCoreTests(unittest.TestCase):
    def test_terminal_method_guard_blocks_all_real_entry_points(self):
        self.assertTrue(runner.METHOD_TERMINAL_BLOCKED)
        for function in (lambda: runner.no_content_preflight(None),
                         runner.run_supervised,
                         lambda: runner.run_one(reserved_by_supervisor=True)):
            with self.assertRaisesRegex(Exception, "recovery_003_disposable_method_terminal_no_real_attempt"):
                function()

    def test_native_fine_grid_and_gross_resource_stops(self):
        result = inspect_returned_raster(raster(), source_bounds=SOURCE, aoi_bounds=AOIS)
        self.assertEqual((result["declared_cells"], result["declared_logical_bytes"]), (16_000_000, 128_000_000))
        for invalid in (raster(width=2, height=2, meanCellWidth=10.0, meanCellHeight=10.0),
                        raster(width=200_000, height=200_000), raster(pixelType=None),
                        raster(extent=bounds(80, 20, 81, 21)), raster(spatialReference=SimpleNamespace(factoryCode=32645))):
            with self.subTest(invalid=invalid), self.assertRaises(NativeGridStop):
                inspect_returned_raster(invalid, source_bounds=SOURCE, aoi_bounds=AOIS)

    def test_environment_cleared_and_restored_on_success_and_exception(self):
        for fails in (False, True):
            fake = FakeArcPy()
            original = vars(fake.env).copy()
            records = []

            def call(*args):
                self.assertEqual(args, ("native-input", "VV;VH"))
                self.assertTrue(all(getattr(fake.env, key) is None for key in
                                    ("cellSize", "snapRaster", "outputCoordinateSystem", "extent")))
                self.assertEqual(fake.env.resamplingMethod, "NEAREST")
                if fails:
                    raise ValueError("synthetic failure")
                return "unsaved-raster"

            if fails:
                with self.assertRaisesRegex(ValueError, "synthetic failure"):
                    native_gtc_call(fake, call, ("native-input", "VV;VH"),
                                    resampling="NEAREST", record_environment=records.append)
            else:
                self.assertEqual(native_gtc_call(fake, call, ("native-input", "VV;VH"),
                                                 resampling="NEAREST", record_environment=records.append),
                                 "unsaved-raster")
            self.assertEqual(vars(fake.env), original)
            self.assertEqual([name for action, name in fake.calls if action == "clear"],
                             ["cellSize", "snapRaster", "outputCoordinateSystem", "extent"])
            self.assertEqual(len(records), 1)

    def test_projected_grid_guard_and_disk_limit(self):
        description = SimpleNamespace(spatialReference=SimpleNamespace(factoryCode=32645),
                                      width=9652, height=8098, meanCellWidth=10.0,
                                      meanCellHeight=10.0, extent=bounds(*TARGET))
        self.assertEqual(projected_grid_description(description)["cells"], 78_161_896)
        description.extent = bounds(TARGET[0] - 101, TARGET[1], TARGET[2], TARGET[3])
        with self.assertRaises(NativeGridStop):
            projected_grid_description(description)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "small.bin"
            path.write_bytes(b"ok")
            self.assertEqual(guard_materialized_size(path, projected=False), 2)

    def test_native_scope_stays_cleared_through_lazy_save(self):
        fake = FakeArcPy()
        prior = vars(fake.env).copy()
        for fails in (False, True):
            with self.subTest(fails=fails):
                try:
                    with native_gtc_environment(fake, resampling="BILINEAR",
                                                record_environment=lambda _: None):
                        self.assertTrue(all(getattr(fake.env, key) is None for key in
                                            ("cellSize", "snapRaster", "outputCoordinateSystem", "extent")))
                        if fails:
                            raise RuntimeError("lazy save stopped")
                except RuntimeError:
                    self.assertTrue(fails)
                self.assertEqual(vars(fake.env), prior)

    def test_projection_uses_one_crs_bearing_extent(self):
        calls = []
        description = SimpleNamespace(spatialReference=SimpleNamespace(factoryCode=32645),
                                      width=9652, height=8098, meanCellWidth=10.0,
                                      meanCellHeight=10.0, extent=bounds(*TARGET))

        class Context:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

        def extent(*values, spatial_reference=None):
            calls.append(("extent", values, spatial_reference))
            return "CRS-bearing extent"

        def manager(**kwargs):
            calls.append(("environment", kwargs))
            return Context()

        def project(*args):
            calls.append(("project", args))

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "projected.tif"
            output.write_bytes(b"output")
            fake = SimpleNamespace(SpatialReference=lambda wkid: f"EPSG:{wkid}", Extent=extent,
                                   EnvManager=manager, management=SimpleNamespace(ProjectRaster=project),
                                   Describe=lambda _: description)
            result = project_with_frozen_extent(fake, Path("native.tif"), output,
                                                Path("snap.tif"), categorical=True)
        self.assertEqual(result["resampling"], "NEAREST")
        self.assertEqual(calls[0], ("extent", TARGET, "EPSG:32645"))
        self.assertEqual(calls[1][1]["extent"], "CRS-bearing extent")
        self.assertEqual(calls[2][1][3], "NEAREST")
        self.assertEqual(sum(call[0] == "project" for call in calls), 1)

    def test_fixed_source_order_stops_before_second_date(self):
        called = []

        def worker(source_id):
            called.append(source_id)
            return {"source_id": source_id, "status": "stop_source_aoi_qa_no_next_date"}

        result = runner.source_sequence(worker)
        self.assertEqual(called, ["M1-SRC-002"])
        self.assertEqual(len(result), 1)

    def test_supervisor_retains_terminal_after_worker_exits_without_receipts(self):
        class FailedChild:
            pid = 12345

            def poll(self):
                return 21

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preflight = root / "preflight.json"
            gate = root / "gate.json"
            gate.write_text("{}", encoding="utf-8")
            preflight.write_text(
                '{"status":"pass_final_no_content_two_source_radar_preflight",'
                '"implementation_gate_sha256":"' + runner.sha256_file(gate) + '"}',
                encoding="utf-8")
            with (patch.object(runner, "ATTEMPT_ROOT", root / "a2"),
                  patch.object(runner, "DATA_ROOT", root),
                  patch.object(runner, "PREFLIGHT", preflight),
                  patch.object(runner, "IMPLEMENTATION_GATE", gate),
                  patch.object(runner, "METHOD_TERMINAL_BLOCKED", False),
                  patch.object(runner.subprocess, "Popen", return_value=FailedChild())):
                result = runner.run_supervised()
            self.assertEqual(result["worker_return_code"], 21)
            self.assertFalse(result["worker_terminal_receipt_written"])
            self.assertIn("terminal_supervisor_stop_no_retry", (root / "a2" / "terminal.json").read_text())
            self.assertGreater((root / "a2" / "cleanup.json").stat().st_size, 0)
            self.assertTrue((root / "a2" / "supervisor.json").is_file())

    def test_native_pipeline_order_and_presave_coarse_stop(self):
        class Raster:
            spatialReference = SimpleNamespace(factoryCode=4326)
            width = 4000
            height = 4000
            bandCount = 2
            meanCellWidth = 0.00025
            meanCellHeight = 0.00025
            extent = bounds()
            isTemporary = True
            pixelType = "F32"

            def __init__(self, call_name, root, coarse=False):
                self.call_name = call_name
                self.root = root
                if coarse:
                    self.width = 2
                    self.height = 2
                    self.meanCellWidth = 10.0
                    self.meanCellHeight = 10.0

            def save(self, path):
                if "GTC" in self.call_name:
                    receipt = self.root / "receipts" / "native" / f"m1-src-002-{self.call_name}-presave.json"
                    assert receipt.is_file()
                Path(path).mkdir()
                (Path(path) / "data.bin").write_bytes(b"sample")

        class IA:
            def __init__(self, root, calls, coarse):
                self.root, self.calls, self.coarse = root, calls, coarse

            def _call(self, name, *args):
                self.calls.append((name, args))
                if name == "ApplyRadiometricTerrainFlattening":
                    for output in args[5:8]:
                        Path(output).mkdir()
                return Raster(name, self.root, coarse=self.coarse and name == "ApplyGeometricTerrainCorrection_gamma")

            def RemoveThermalNoise(self, *args): return self._call("RemoveThermalNoise", *args)
            def ApplyRadiometricCalibration(self, *args): return self._call("ApplyRadiometricCalibration", *args)
            def ApplyRadiometricTerrainFlattening(self, *args): return self._call("ApplyRadiometricTerrainFlattening", *args)
            def Despeckle(self, *args): return self._call("Despeckle", *args)
            def ApplyGeometricTerrainCorrection(self, *args):
                return self._call("ApplyGeometricTerrainCorrection_mask" if args[1] == "#" else "ApplyGeometricTerrainCorrection_gamma", *args)
            def ConvertSARUnits(self, *args): return self._call("ConvertSARUnits", *args)

        for coarse in (False, True):
            with self.subTest(coarse=coarse), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                output = {name: root / f"{name}.crf" for name in
                          ("thermal", "beta", "gamma_slant", "scattering", "distortion",
                           "native_mask", "gamma_despeckled", "gamma_gtc_raw", "db_gtc_raw", "mask_gtc_raw")}
                calls = []
                fake = FakeArcPy()
                fake.ia = IA(root, calls, coarse)
                kwargs = dict(arcpy=fake, manifest=root / "manifest.safe", dem_mosaic=root / "dem.tif",
                              source_id="M1-SRC-002", stage_recorder=lambda **_: None,
                              outputs=output, attempt_root=root, source_bounds=SOURCE, aoi_bounds=AOIS)
                if coarse:
                    with self.assertRaises(NativeGridStop):
                        processing.execute_raster_function_pipeline(**kwargs)
                    self.assertFalse(output["gamma_gtc_raw"].exists())
                    self.assertEqual([name for name, _ in calls][-1], "ApplyGeometricTerrainCorrection_gamma")
                else:
                    result = processing.execute_raster_function_pipeline(**kwargs)
                    self.assertEqual([name for name, _ in calls], [
                        "RemoveThermalNoise", "ApplyRadiometricCalibration", "ApplyRadiometricTerrainFlattening",
                        "Despeckle", "ApplyGeometricTerrainCorrection_gamma", "ConvertSARUnits",
                        "ApplyGeometricTerrainCorrection_mask"])
                    self.assertEqual(result["gamma"]["declared_cells"], 16_000_000)
                    self.assertEqual(result["mask"]["declared_cells"], 16_000_000)


if __name__ == "__main__":
    unittest.main()
