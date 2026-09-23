"""Portable eleven-cell seam topology and complete-sample tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import reconcile_m2_radar_event_pair_dem_conversion_001 as route


CELLS = (
    (27, 84), (27, 85), (27, 86),
    (28, 83), (28, 84), (28, 85), (28, 86),
    (29, 83), (29, 84), (29, 85), (29, 86),
)


def items():
    return [
        {
            "source_id": f"synthetic-{index:02d}",
            "source_relative_path": f"custody/dem/copernicus-glo30/Copernicus_DSM_COG_10_N{lat:02d}_00_E{lon:03d}_00_DEM.tif",
            "output_relative_path": f"derived/dem/egm2008-ellipsoidal-proj25/Copernicus_DSM_COG_10_N{lat:02d}_00_E{lon:03d}_00_DEM_WGS84_ELLIPSOIDAL.tif",
        }
        for index, (lat, lon) in enumerate(CELLS)
    ]


class SeamTests(unittest.TestCase):
    def test_exact_fifteen_touching_edges(self):
        pairs = route.adjacent_pairs(items())
        self.assertEqual(len(pairs), 15)
        self.assertEqual(len({item[-1] for item in pairs}), 15)

    def test_complete_finite_correction_samples_required(self):
        self.assertEqual(len(route.measure_seams(items(), edge_reader=lambda *_args: np.zeros(3600))), 15)
        with self.assertRaisesRegex(route.IntakeError, "seam_correction_sample_incomplete"):
            route.measure_seams(items(), edge_reader=lambda *_args: np.zeros(3599))


if __name__ == "__main__":
    unittest.main()
