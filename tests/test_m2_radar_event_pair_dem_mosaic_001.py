"""Portable disposable orchestration tests for the single eleven-tile mosaic."""

from __future__ import annotations

import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import m2_radar_event_pair_dem_mosaic_001 as route


class FakeArcGIS:
    def __init__(self, fail=False):
        self.fail = fail
        self.inputs = None
        self.management = self

    def SpatialReference(self, code):
        if code != 4326:
            raise AssertionError("unexpected CRS")
        return code

    def MosaicToNewRaster(self, inputs, directory, name, srs, pixel_type, cell, bands, operation, colormap):
        self.inputs = inputs
        if self.fail:
            raise RuntimeError("synthetic mosaic interruption")
        if (srs, pixel_type, cell, bands, operation, colormap) != (4326, "32_BIT_FLOAT", None, 1, "FIRST", "FIRST"):
            raise AssertionError("mosaic method drift")
        (Path(directory) / name).write_bytes(b"synthetic-mosaic")

    def Describe(self, _path):
        return SimpleNamespace(spatialReference=SimpleNamespace(factoryCode=4326), bandCount=1)


class MosaicTests(unittest.TestCase):
    def paths(self, directory):
        root = Path(directory) / "mosaic"
        return {
            "MOSAIC_ROOT": root,
            "MOSAIC": root / "ellipsoidal_dem_mosaic.tif",
            "TERMINAL": root / "terminal.json",
            "ERROR": root / "error.json",
            "CLEANUP": root / "cleanup.json",
        }

    def test_exact_eleven_inputs_one_output_and_receipts(self):
        with tempfile.TemporaryDirectory() as directory:
            inputs = [Path(directory) / f"tile-{index:02d}.tif" for index in range(11)]
            fake = FakeArcGIS()
            with ExitStack() as stack:
                stack.enter_context(patch.object(route, "exact_mosaic_inputs", return_value=inputs))
                for key, value in self.paths(directory).items():
                    stack.enter_context(patch.object(route, key, value))
                result = route.build_mosaic(arcpy_module=fake)
                self.assertEqual(result["status"], "pass_mosaic_created_pending_actual_sar_extent_and_valid_elevation_gate")
                self.assertEqual(fake.inputs, [str(path) for path in inputs])
                self.assertGreater(route.TERMINAL.stat().st_size, 0)
                self.assertGreater(route.CLEANUP.stat().st_size, 0)
                with self.assertRaisesRegex(route.IntakeError, "mosaic_attempt_collision"):
                    route.build_mosaic(arcpy_module=fake)

    def test_failure_retains_terminal_error_and_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            inputs = [Path(directory) / f"tile-{index:02d}.tif" for index in range(11)]
            fake = FakeArcGIS(fail=True)
            with ExitStack() as stack:
                stack.enter_context(patch.object(route, "exact_mosaic_inputs", return_value=inputs))
                for key, value in self.paths(directory).items():
                    stack.enter_context(patch.object(route, key, value))
                result = route.build_mosaic(arcpy_module=fake)
                self.assertEqual(result["status"], "terminal_mosaic_failure_no_retry")
                self.assertGreater(route.ERROR.stat().st_size, 0)
                self.assertGreater(route.TERMINAL.stat().st_size, 0)
                self.assertGreater(route.CLEANUP.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
