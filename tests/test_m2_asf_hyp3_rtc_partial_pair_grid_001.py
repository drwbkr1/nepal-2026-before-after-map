"""Disposable native-grid alignment tests; no provider pixel access."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m2_asf_hyp3_rtc_partial_pair_grid_001 import (  # noqa: E402
    choose_target_grid, read_band_on_target,
)
from pixel_qa_core import load_contract  # noqa: E402


def grid(*, x0: float = 300000, y0: float = 3100000) -> dict:
    return {"wkid": 32645, "cell_size_x": 10.0, "cell_size_y": 10.0,
            "origin_x": x0, "origin_y": y0,
            "xmin": x0, "ymin": y0 - 1000,
            "xmax": x0 + 1000, "ymax": y0,
            "rotation_degrees": 0.0}


RINGS = [
    [[300020, 3099980], [300200, 3099980], [300200, 3099800],
     [300020, 3099800], [300020, 3099980]],
    [[300210, 3099790], [300400, 3099790], [300400, 3099600],
     [300210, 3099600], [300210, 3099790]],
]


class FakeBand:
    def __init__(self, values):
        self.values = values

    def ReadAsArray(self, x, y, width, height):
        return self.values[y:y + height, x:x + width]


class FakeDataset:
    def __init__(self, values, x0=300000, y0=3100000):
        self.RasterYSize, self.RasterXSize = values.shape
        self.values, self.x0, self.y0 = values, x0, y0

    def GetGeoTransform(self):
        return (self.x0, 10, 0, self.y0, 0, -10)

    def GetRasterBand(self, _index):
        return FakeBand(self.values)


class PartialPairGridTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_contract(ROOT / "config/qa/pixel-readiness-contract.json")

    def test_target_uses_two_aois_and_native_10m_alignment(self):
        target = choose_target_grid(grid(), grid(x0=300010), RINGS, self.contract)
        self.assertEqual(target["xmin"], 300020)
        self.assertEqual(target["xmax"], 300400)
        self.assertEqual(target["ymax"], 3099980)
        self.assertEqual(target["ymin"], 3099600)
        self.assertEqual((target["width"], target["height"]), (38, 38))
        self.assertFalse(target["resampling_performed"])

    def test_half_cell_offset_blocks(self):
        with self.assertRaisesRegex(ValueError, "partial_pair_grids_incompatible"):
            choose_target_grid(grid(), grid(x0=300005), RINGS, self.contract)

    def test_unapproved_extra_aoi_or_broken_polygon_shape_blocks(self):
        with self.assertRaisesRegex(ValueError, "partial_pair_target_input_invalid"):
            choose_target_grid(grid(), grid(), RINGS + [RINGS[0]], self.contract)
        broken = [RINGS[0][:-1], RINGS[1]]
        with self.assertRaisesRegex(ValueError, "partial_pair_target_input_invalid"):
            choose_target_grid(grid(), grid(), broken, self.contract)

    def test_native_window_reads_padded_edges_without_resampling(self):
        values = np.arange(16, dtype=np.float32).reshape(4, 4)
        source = FakeDataset(values)
        target = {"wkid": 32645, "cell_size_m": 10.0,
                  "xmin": 299990, "ymax": 3100010, "width": 6, "height": 6}
        result = read_band_on_target(source, target, fill=np.nan, dtype=np.float32)
        self.assertTrue(np.isnan(result[0, 0]))
        np.testing.assert_array_equal(result[1:5, 1:5], values)
        self.assertTrue(np.isnan(result[5, 5]))

    def test_misaligned_source_or_bad_target_blocks(self):
        values = np.ones((4, 4), dtype=np.float32)
        target = {"wkid": 32645, "cell_size_m": 10.0,
                  "xmin": 300000, "ymax": 3100000, "width": 4, "height": 4}
        with self.assertRaisesRegex(ValueError, "partial_pair_source_not_aligned"):
            read_band_on_target(FakeDataset(values, x0=300005), target,
                                fill=np.nan, dtype=np.float32)
        target["wkid"] = 4326
        with self.assertRaisesRegex(ValueError, "partial_pair_target_invalid"):
            read_band_on_target(FakeDataset(values), target,
                                fill=np.nan, dtype=np.float32)


if __name__ == "__main__":
    unittest.main()
