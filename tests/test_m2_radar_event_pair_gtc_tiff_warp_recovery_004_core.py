"""Portable source-free stops for the approved recovery-004 method."""

from __future__ import annotations

import sys
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from m2_radar_event_pair_gtc_tiff_warp_recovery_004_core import (  # noqa: E402
    BridgeStop, HEIGHT, WIDTH, bridge_and_warp, check_bridge_metadata,
    check_free_bytes, check_full_pixels, check_projected_grid,
)
import m2_radar_event_pair_gtc_tiff_warp_recovery_004_processing as processing  # noqa: E402


class BridgeTests(unittest.TestCase):
    def test_free_space_is_greater_of_sixty_gib_or_twice_logical(self):
        check_free_bytes(60 * 1024**3, 2 * 1024**3)
        with self.assertRaises(BridgeStop):
            check_free_bytes(60 * 1024**3 - 1, 2 * 1024**3)
        with self.assertRaises(BridgeStop):
            check_free_bytes(60 * 1024**3, 40 * 1024**3)

    def test_bridge_metadata_requires_exact_properties(self):
        record = dict(wkid=4326, width=256, height=256, bands=2, pixel_type="F32",
                      nodata=-9999.0, transform=[85, .00025, 0, 29, 0, -.00025],
                      bounds=[85, 28.936, 85.064, 29])
        check_bridge_metadata(record, record.copy())
        for key, value in (("nodata", None), ("pixel_type", "U8"),
                           ("transform", [85, .001, 0, 29, 0, -.00025])):
            changed = dict(record, **{key: value})
            with self.subTest(key=key), self.assertRaises(BridgeStop):
                check_bridge_metadata(record, changed)

    def test_full_pixel_change_and_zero_class_stop(self):
        import numpy as np

        mask = np.array([[0, 1], [3, 255]], dtype=np.uint8)
        self.assertTrue(check_full_pixels(mask, mask.copy(), categorical=True)["categorical_zero_retained"])
        with self.assertRaises(BridgeStop):
            check_full_pixels(mask, np.where(mask == 0, 255, mask).astype(np.uint8), categorical=True)
        continuous = np.array([[1.5, -9999], [2.5, 3.5]], dtype=np.float32)
        check_full_pixels(continuous, continuous.copy(), categorical=False)
        with self.assertRaises(BridgeStop):
            check_full_pixels(continuous, continuous.astype(np.float64), categorical=False)

    def test_exact_grid_rejects_framing_drift(self):
        class Spatial:
            def __init__(self, wkt=None): self.wkt = wkt
            def ImportFromEPSG(self, code): self.wkt = str(code)
            def SetAxisMappingStrategy(self, _): pass
            def IsSame(self, other, _): return self.wkt == other.wkt

        fake = SimpleNamespace(RasterXSize=WIDTH, RasterYSize=HEIGHT, RasterCount=2,
                               GetGeoTransform=lambda: (272300., 10., 0., 3150210., 0., -10.),
                               GetProjection=lambda: "32645")
        with patch.dict(sys.modules, {"osgeo": SimpleNamespace(osr=SimpleNamespace(
                SpatialReference=Spatial, OAMS_TRADITIONAL_GIS_ORDER=0))}):
            self.assertFalse(check_projected_grid(fake, expected_bands=2)["frame_is_coverage_proof"])
            fake.RasterXSize -= 1
            with self.assertRaises(BridgeStop):
                check_projected_grid(fake, expected_bands=2)

    def test_categorical_nodata_collision_blocks_before_copy(self):
        record = dict(wkid=4326, width=100, height=100, bands=1,
                      pixel_type="U8", nodata=0)
        with patch("m2_radar_event_pair_gtc_tiff_warp_recovery_004_core.arc_raster_metadata",
                   return_value=record):
            with self.assertRaisesRegex(BridgeStop, "categorical_nodata_collides"):
                bridge_and_warp(SimpleNamespace(), Path("native.crf"),
                                Path("bridge.tif"), Path("projected.tif"), categorical=True)

    def test_native_dem_extent_failure_precedes_raster_save(self):
        saved = []
        raster = SimpleNamespace(
            spatialReference=SimpleNamespace(factoryCode=4326), width=4000, height=4000,
            bandCount=2, meanCellWidth=.00025, meanCellHeight=.00025,
            extent=SimpleNamespace(XMin=85., YMin=28., XMax=86., YMax=29.),
            isTemporary=True, pixelType="F32", save=lambda path: saved.append(path))
        fake = SimpleNamespace(ia=SimpleNamespace(ApplyGeometricTerrainCorrection=lambda *_: raster))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "receipts" / "native").mkdir(parents=True)
            with (patch.object(processing, "native_gtc_environment", return_value=nullcontext()),
                  patch.object(processing, "_verify_dem_native_extent",
                               side_effect=RuntimeError("synthetic_dem_gap"))):
                with self.assertRaisesRegex(RuntimeError, "synthetic_dem_gap"):
                    processing._save_native_gtc(
                        arcpy=fake, arguments=("generated",), output=root / "native.crf",
                        source_id="M1-SRC-002", stage_recorder=lambda **_: None,
                        attempt_root=root, dem_mosaic=root / "generated-dem.tif",
                        source_bounds=(84., 27., 87., 30.),
                        aoi_bounds=((85.2, 28.2, 85.4, 28.4),), categorical=False)
        self.assertEqual(saved, [])


if __name__ == "__main__":
    unittest.main()
