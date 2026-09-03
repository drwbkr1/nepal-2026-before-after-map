import unittest

import numpy as np

from scripts.dem_terrain_quality_core import combine_statuses, evaluate_seam, evaluate_tile


TILE_THRESHOLDS = {
    "block_nodata_or_nonfinite_count": 0,
    "block_minimum_elevation_m": -500.0,
    "block_maximum_elevation_m": 9000.0,
    "block_max_abs_local_curvature_m": 2000.0,
    "defer_abs_local_curvature_m": 1000.0,
    "defer_local_curvature_fraction": 0.0001,
    "defer_exact_2x2_plateau_fraction": 0.50,
}

SEAM_THRESHOLDS = {
    "block_residual_abs_max_m": 2000.0,
    "defer_signed_median_abs_m": 25.0,
    "defer_residual_abs_median_m": 30.0,
    "defer_residual_abs_p95_m": 150.0,
    "defer_residual_abs_p99_m": 300.0,
    "defer_residual_level_m": 100.0,
    "defer_residual_above_level_fraction": 0.05,
}


class DemTerrainQualityCoreTests(unittest.TestCase):
    def test_continuous_plane_passes_tile_and_seams(self):
        rows, columns = np.mgrid[0:8, 0:8]
        west = 1000.0 + rows * 3.0 + columns * 4.0
        east = 1000.0 + rows * 3.0 + (columns + 8) * 4.0
        south = 1000.0 + (7 - rows) * 3.0 + columns * 4.0
        north = 1000.0 + (15 - rows) * 3.0 + columns * 4.0
        self.assertEqual(evaluate_tile(west, TILE_THRESHOLDS)["status"], "pass")
        self.assertEqual(evaluate_seam(west, east, "west_east", SEAM_THRESHOLDS)["status"], "pass")
        self.assertEqual(evaluate_seam(south, north, "south_north", SEAM_THRESHOLDS)["status"], "pass")

    def test_moderate_systematic_offset_defers(self):
        base = np.tile(np.arange(8, dtype=float), (8, 1)) * 4.0 + 1000.0
        shifted = base + 8 * 4.0 + 300.0
        result = evaluate_seam(base, shifted, "west_east", SEAM_THRESHOLDS)
        self.assertEqual(result["status"], "defer")
        self.assertIn("systematic_seam_offset", result["deferrals"])

    def test_gross_seam_and_impossible_elevation_block(self):
        base = np.tile(np.arange(8, dtype=float), (8, 1)) + 1000.0
        gross = base + 8.0 + 3000.0
        self.assertEqual(evaluate_seam(base, gross, "west_east", SEAM_THRESHOLDS)["status"], "block")
        impossible = base.copy()
        impossible[3, 3] = 9500.0
        result = evaluate_tile(impossible, TILE_THRESHOLDS)
        self.assertEqual(result["status"], "block")
        self.assertIn("maximum_elevation_outside_physical_bound", result["failures"])

    def test_nonfinite_cell_blocks_and_precedence_is_stable(self):
        values = np.arange(64, dtype=float).reshape(8, 8) + 1000.0
        values[2, 2] = np.nan
        self.assertEqual(evaluate_tile(values, TILE_THRESHOLDS)["status"], "block")
        self.assertEqual(combine_statuses(["pass", "defer"]), "defer")
        self.assertEqual(combine_statuses(["pass", "defer", "block"]), "block")

    def test_unsupported_seam_orientation_is_rejected(self):
        values = np.ones((8, 8), dtype=float)
        with self.assertRaisesRegex(ValueError, "unsupported seam orientation"):
            evaluate_seam(values, values, "diagonal", SEAM_THRESHOLDS)


if __name__ == "__main__":
    unittest.main()
