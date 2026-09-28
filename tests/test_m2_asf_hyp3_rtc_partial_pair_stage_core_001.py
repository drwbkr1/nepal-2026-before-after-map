"""Disposable-array coverage for the visual-only partial-pair stage."""

import sys
import unittest
from pathlib import Path

import numpy as np


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from m2_asf_hyp3_rtc_partial_pair_stage_core_001 import (  # noqa: E402
    prepare_common_valid_vv_db,
)


class PartialPairStageCoreTests(unittest.TestCase):
    def _inputs(self):
        shape = (2, 5)
        arrays = {
            "before_vv": np.ones(shape, dtype=np.float32),
            "before_vh": np.ones(shape, dtype=np.float32),
            "before_mask": np.ones(shape, dtype=np.uint8),
            "after_vv": np.full(shape, 10, dtype=np.float32),
            "after_vh": np.ones(shape, dtype=np.float32),
            "after_mask": np.ones(shape, dtype=np.uint8),
        }
        source = np.zeros(shape, dtype=np.uint8)
        source[0, :] = 1
        corridor = np.zeros(shape, dtype=np.uint8)
        corridor[1, :] = 1
        return {"arrays": arrays,
                "aoi_masks": {"AOI-SOURCE": source,
                              "AOI-UPPER-CORRIDOR": corridor},
                "aoi_areas_m2": {"AOI-SOURCE": 500.,
                                 "AOI-UPPER-CORRIDOR": 500.},
                "pixel_area_m2": 100.}

    def test_emits_only_common_valid_vv_db_at_frozen_floor(self):
        values = self._inputs()
        values["arrays"]["after_mask"][0, 1:] = 5
        values["arrays"]["before_vh"][1, 1:] = 0
        result = prepare_common_valid_vv_db(**values)
        self.assertEqual(result["status"],
                         "pass_common_valid_for_local_partial_visual_only")
        self.assertEqual([item["common_valid_cells"] for item in result["aoi_results"]],
                         [1, 1])
        self.assertEqual(result["common_valid_cells_in_union"], 2)
        self.assertEqual(result["display_polarization"], "VV")
        self.assertEqual(np.count_nonzero(np.isfinite(result["before_vv_db"])), 2)
        self.assertEqual(np.count_nonzero(np.isfinite(result["after_vv_db"])), 2)
        self.assertEqual(result["before_vv_db"][0, 0], 0.)
        self.assertAlmostEqual(result["after_vv_db"][0, 0], 10.)
        self.assertFalse(result["registration_measured"])

    def test_below_floor_returns_no_display_arrays(self):
        values = self._inputs()
        values["arrays"]["after_mask"][0, :] = 5
        result = prepare_common_valid_vv_db(**values)
        self.assertEqual(result["status"], "block_partial_pair_display")
        self.assertNotIn("before_vv_db", result)
        self.assertNotIn("after_vv_db", result)

    def test_unknown_provider_mask_returns_no_display_arrays(self):
        values = self._inputs()
        values["arrays"]["after_mask"][0, 2] = 255
        result = prepare_common_valid_vv_db(**values)
        self.assertEqual(result["status"], "block_partial_pair_display")
        self.assertEqual(result["aoi_results"][0]["status"],
                         "block_unknown_provider_mask")
        self.assertNotIn("before_vv_db", result)

    def test_rejects_shape_or_aoi_substitution(self):
        values = self._inputs()
        values["arrays"]["after_vv"] = np.ones((1, 5), dtype=np.float32)
        with self.assertRaisesRegex(ValueError, "partial_pair_display_input_invalid"):
            prepare_common_valid_vv_db(**values)
        values = self._inputs()
        values["aoi_masks"].pop("AOI-UPPER-CORRIDOR")
        with self.assertRaisesRegex(ValueError, "partial_pair_display_input_invalid"):
            prepare_common_valid_vv_db(**values)


if __name__ == "__main__":
    unittest.main()
