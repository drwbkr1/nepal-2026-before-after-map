import sys
import struct
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from landsat9_pixel_visual_core_001 import (
    PixelMethodError, aoi_cell_weights, classify_pixels, nearest_rank_stretch,
    validate_headers, weighted_metrics,
)
from run_m2_landsat9_pixel_visual_panel_001 import tiff_georeference


class Landsat9PixelVisualCoreTests(unittest.TestCase):
    def test_exact_partial_cell_area_and_accounting(self):
        ring = [[0, 0], [45, 0], [45, 45], [0, 45], [0, 0]]
        weights = aoi_cell_weights(ring, 0, 60, 2, 2)
        np.testing.assert_allclose(weights, [[450, 225], [900, 450]])
        self.assertAlmostEqual(float(weights.sum()), 2025)

    def test_header_grid_lattice_and_nodata_key(self):
        roles = ("QA_PIXEL", "QA_RADSAT", "SR_QA_AEROSOL", "SR_B3", "SR_B4", "SR_B5", "SR_B6", "SR_B7")
        h = dict(wkid=32645, bands=1, rows=10, columns=10, cell_x=30., cell_y=30.,
                 xmin=0., ymin=0., xmax=300., ymax=300., nodata=None)
        pair = {"before": {r: dict(h) for r in roles}, "after": {r: dict(h, xmin=120., xmax=420.) for r in roles}}
        self.assertEqual(validate_headers(pair)["after_offset_columns"], 4)
        pair["after"]["SR_B7"]["xmin"] += 1
        with self.assertRaises(PixelMethodError):
            validate_headers(pair)

    def test_mask_precedence_and_full_aoi_denominator(self):
        qa = np.array([[0, 1 << 5], [1 << 3, 0]], dtype=np.uint16)
        radsat = np.zeros((2, 2), dtype=np.uint16)
        aerosol = np.full((2, 2), 2, dtype=np.uint8)
        bands = np.full((5, 2, 2), 20000, dtype=np.uint16)
        footprint = np.ones((2, 2), dtype=bool)
        before = classify_pixels(qa, radsat, aerosol, bands, footprint, [None] * 8)
        self.assertEqual(before["reason"].tolist(), [[7, 3], [2, 7]])
        after = classify_pixels(np.zeros_like(qa), radsat, aerosol, bands, footprint, [None] * 8)
        result = weighted_metrics(np.full((2, 2), 900.), before, after, footprint, footprint)
        self.assertEqual(result["paired_strict_usable_fraction"], .5)
        self.assertEqual(result["visual_status"], "partial_insufficient_for_full_area_comparison")

    def test_aerosol_conjunction_and_nonphysical(self):
        shape = (1, 4)
        aerosol = np.array([[1, 192, 194, 34]], dtype=np.uint8)
        bands = np.full((5, *shape), 20000, dtype=np.uint16)
        bands[:, 0, 3] = 1
        result = classify_pixels(np.zeros(shape, dtype=np.uint16),
                                 np.zeros(shape, dtype=np.uint16), aerosol,
                                 bands, np.ones(shape, dtype=bool), [None] * 8)
        self.assertEqual(result["reason"].tolist(), [[1, 5, 7, 6]])
        self.assertTrue(result["raw"]["aerosol_interpolated"][0, 3])

    def test_nearest_rank_is_fixed(self):
        self.assertEqual(nearest_rank_stretch(np.arange(100)), (1., 97.))

    def test_header_only_classic_tiff_georeference_tags(self):
        # First IFD and two out-of-line DOUBLE tags. No image payload exists.
        header = b"II" + struct.pack("<HI", 42, 8)
        ifd = struct.pack("<H", 2)
        ifd += struct.pack("<HHII", 33550, 12, 3, 38)
        ifd += struct.pack("<HHII", 33922, 12, 6, 62)
        ifd += struct.pack("<I", 0)
        data = struct.pack("<3d", 30., 30., 0.) + struct.pack("<6d", 0., 0., 0., 300000., 3100000., 0.)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "synthetic.tif"
            path.write_bytes(header + ifd + data)
            self.assertEqual(tiff_georeference(path), {
                "rotation_x": 0., "rotation_y": 0., "tag_cell_x": 30., "tag_cell_y": 30.})


if __name__ == "__main__":
    unittest.main()
