"""Portable stops for the approved native-GTC grid recovery candidate."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from m2_radar_event_pair_native_gtc_recovery_003_core import (  # noqa: E402
    NativeGridStop, TARGET, guard_materialized_size, inspect_returned_raster,
    native_gtc_call, project_with_frozen_extent, projected_grid_description,
)


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


if __name__ == "__main__":
    unittest.main()
