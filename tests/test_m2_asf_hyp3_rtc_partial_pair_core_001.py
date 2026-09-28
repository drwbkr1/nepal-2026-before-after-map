"""Disposable array tests for the strictly visual RTC partial-pair threshold."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m2_asf_hyp3_rtc_partial_pair_core_001 import (  # noqa: E402
    assess_common_valid, check_pair_grids, gamma0_power_to_db,
)
from pixel_qa_core import load_contract  # noqa: E402


class PartialPairCoreTests(unittest.TestCase):
    def _arrays(self, before_mask, after_mask):
        shape = (2, 5)
        return {
            "aoi_id": "AOI-SOURCE",
            "aoi_footprint": np.ones(shape, dtype=np.uint8),
            "before_vv": np.ones(shape, dtype=np.float32),
            "before_vh": np.ones(shape, dtype=np.float32),
            "before_mask": np.array(before_mask, dtype=np.uint8).reshape(shape),
            "after_vv": np.ones(shape, dtype=np.float32),
            "after_vh": np.ones(shape, dtype=np.float32),
            "after_mask": np.array(after_mask, dtype=np.uint8).reshape(shape),
            "pixel_area_m2": 100,
            "aoi_area_m2": 1000,
            "partial_floor": 0.2,
        }

    def test_exact_common_floor_passes_as_visual_only(self):
        before = [1, 1, 1, 5, 5, 5, 5, 5, 5, 5]
        after = [1, 1, 5, 1, 5, 5, 5, 5, 5, 5]
        result = assess_common_valid(**self._arrays(before, after))
        self.assertEqual(result["common_valid_cells"], 2)
        self.assertEqual(result["common_valid_fraction_of_aoi"], .2)
        self.assertEqual(result["status"], "pass_common_valid_for_local_partial_visual_only")
        self.assertFalse(result["registration_measured"])
        self.assertFalse(result["scientific_admission_authorized"])

    def test_disjoint_individual_valid_areas_block(self):
        result = assess_common_valid(**self._arrays(
            [1, 1, 1, 5, 5, 5, 5, 5, 5, 5],
            [5, 5, 5, 1, 1, 1, 5, 5, 5, 5],
        ))
        self.assertEqual(result["before_valid_cells"], 3)
        self.assertEqual(result["after_valid_cells"], 3)
        self.assertEqual(result["common_valid_cells"], 0)
        self.assertEqual(result["status"], "block_common_valid_area_below_partial_floor")

    def test_unknown_mask_blocks_even_with_large_common_area(self):
        result = assess_common_valid(**self._arrays([1] * 10, [1] * 9 + [2]))
        self.assertEqual(result["unknown_mask_cells_either_date"], 1)
        self.assertEqual(result["status"], "block_unknown_provider_mask")

    def test_nodata_or_nonpositive_excluded(self):
        args = self._arrays([1] * 10, [1] * 10)
        args["before_vv"][0, 0] = 0
        args["after_vh"][0, 1] = -9999
        args["after_nodata"] = (None, -9999)
        result = assess_common_valid(**args)
        self.assertEqual(result["common_valid_cells"], 8)

    def test_invalid_aoi_and_shape_stop(self):
        args = self._arrays([1] * 10, [1] * 10)
        args["aoi_id"] = "AOI-UNAPPROVED"
        with self.assertRaisesRegex(ValueError, "partial_pair_input_invalid"):
            assess_common_valid(**args)
        args["aoi_id"] = "AOI-SOURCE"
        args["after_vh"] = np.ones((1, 10), dtype=np.float32)
        with self.assertRaisesRegex(ValueError, "partial_pair_input_invalid"):
            assess_common_valid(**args)

    def test_partial_floor_cannot_be_lowered(self):
        args = self._arrays([1] * 10, [1] * 10)
        args["partial_floor"] = 0.19
        with self.assertRaisesRegex(ValueError, "partial_pair_input_invalid"):
            assess_common_valid(**args)

    def test_grid_alignment_requires_integer_pixel_offset(self):
        contract = load_contract(ROOT / "config/qa/pixel-readiness-contract.json")
        grid = {
            "wkid": 32645, "cell_size_x": 10.0, "cell_size_y": 10.0,
            "origin_x": 200000.0, "origin_y": 3200000.0,
            "xmin": 200000.0, "ymin": 3199000.0,
            "xmax": 201000.0, "ymax": 3200000.0,
            "rotation_degrees": 0.0,
        }
        self.assertEqual(check_pair_grids(grid, grid, contract)["status"],
                         "pass_grid_for_local_visual_only")
        shifted = dict(grid, origin_x=200005.0, xmin=200005.0, xmax=201005.0)
        self.assertEqual(check_pair_grids(grid, shifted, contract)["status"], "block_grid")

    def test_db_conversion_masks_exclusions_and_rejects_nonpositive_valid(self):
        values = np.array([[1.0, 10.0], [100.0, 0.0]], dtype=np.float32)
        valid = np.array([[True, True], [True, False]])
        result = gamma0_power_to_db(values, valid)
        np.testing.assert_allclose(result[valid], [0, 10, 20], atol=1e-5)
        self.assertTrue(np.isnan(result[1, 1]))
        valid[1, 1] = True
        with self.assertRaisesRegex(ValueError, "partial_pair_db_input_invalid"):
            gamma0_power_to_db(values, valid)


if __name__ == "__main__":
    unittest.main()
