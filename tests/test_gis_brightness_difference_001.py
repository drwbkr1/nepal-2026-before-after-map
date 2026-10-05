"""Arithmetic checks on generated inputs; never read Nepal TIFFs in CI."""
import sys
import unittest
import hashlib
import json
import struct
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from gis_brightness_difference_001 import brightness_difference, matching_grid
from export_gis_swipe_renders_001 import world_bounds


class BrightnessDifference(unittest.TestCase):
    def test_sign_zero_and_unclamped_numeric_values(self):
        before = np.array([[-20, -20, -20, -30]], dtype=np.float32)
        after = np.array([[-23, -20, -17, 5]], dtype=np.float32)
        delta, excluded = brightness_difference(before, after)
        np.testing.assert_array_equal(delta, [[-3, 0, 3, 35]])
        np.testing.assert_array_equal(excluded, [[0, 0, 0, 0]])
        self.assertEqual(delta.dtype, np.float32)
        self.assertEqual(excluded.dtype, np.uint8)
        np.testing.assert_array_equal(before, [[-20, -20, -20, -30]])

    def test_nan_infinity_and_finite_nodata_are_excluded(self):
        before = np.array([[np.nan, -4, np.inf, -9999, -1]], dtype=np.float32)
        after = np.array([[1, np.nan, 3, 4, -9998]], dtype=np.float32)
        delta, excluded = brightness_difference(before, after, -9999, -9998)
        self.assertTrue(np.isnan(delta).all())
        np.testing.assert_array_equal(excluded, np.ones((1, 5), dtype=np.uint8))

    def test_display_colors_and_mismatched_shapes_rejected(self):
        for before, after in [(np.zeros((2, 2), dtype=np.uint8), np.zeros((2, 2), dtype=np.uint8)),
                              (np.zeros((2, 2)), np.zeros((3, 2))),
                              (np.zeros((0, 2)), np.zeros((0, 2)))]:
            with self.assertRaises(ValueError):
                brightness_difference(before, after)

    def test_grid_drift_stops_without_warp(self):
        grid = {"wkid": 32645, "geotransform": [100, 10, 0, 200, 0, -10], "width": 2}
        self.assertEqual(matching_grid(grid, dict(grid)), grid)
        for changed in ({**grid, "wkid": 3857}, {**grid, "width": 3},
                        {**grid, "geotransform": [105, 10, 0, 200, 0, -10]}):
            with self.assertRaisesRegex(ValueError, "Grid mismatch"):
                matching_grid(grid, changed)


class PublishedDifference(unittest.TestCase):
    def test_native_preview_bytes_and_grid_match_original_viewer(self):
        root = Path(__file__).resolve().parents[1] / "docs/viewer"
        source = json.loads((root / "renders/DIFFERENCE_SOURCE.json").read_text(encoding="utf-8"))
        text = (root / "data.js").read_text(encoding="utf-8").strip()
        data = json.loads(text.removeprefix("window.NEPAL_VIEWER = Object.freeze(").removesuffix(");"))
        render = source["render"]
        for filename, expected in ((render["file"], render["sha256"]),
                                   (render["world_file"], render["world_file_sha256"])):
            with (root / "renders" / filename).open("rb") as handle:
                self.assertEqual(hashlib.file_digest(handle, "sha256").hexdigest(), expected)
        raw = (root / "renders" / render["file"]).read_bytes()[:24]
        size = list(struct.unpack(">II", raw[16:24]))
        coeff = [float(v) for v in (root / "renders" / render["world_file"]).read_text(encoding="utf-8").splitlines()]
        self.assertEqual(size, data["before"]["size"])
        self.assertEqual(world_bounds(coeff, *size), data["bounds"])
        self.assertEqual(render["sha256"], data["difference"]["sha256"])
        self.assertEqual(data["difference"]["display_range_db"], [-6, 6])
        self.assertEqual(source["formula"], "after_vv_db - before_vv_db")
        self.assertFalse(source["registration_verified"])


if __name__ == "__main__":
    unittest.main()
