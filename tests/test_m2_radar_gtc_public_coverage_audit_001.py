import json
import unittest
from pathlib import Path

from scripts.audit_m2_radar_gtc_public_coverage_001 import (
    OUTPUT_REF, ROOT, calculate, clip_to_box, spherical_equal_area_km2,
)


class PublicCoverageAuditTests(unittest.TestCase):
    def test_rectangle_clip_and_area(self):
        square = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)]
        quarter = clip_to_box(square, (1.0, 1.0, 2.0, 2.0))
        self.assertEqual(len(quarter), 4)
        self.assertGreater(spherical_equal_area_km2(quarter), 0)
        self.assertAlmostEqual(
            spherical_equal_area_km2(quarter) / spherical_equal_area_km2(square),
            0.2499, places=3,
        )
        self.assertEqual(clip_to_box(square, (3.0, 3.0, 4.0, 4.0)), [])

    def test_frozen_catalog_result_and_claim_limits(self):
        expected = calculate()
        record = json.loads((ROOT / OUTPUT_REF).read_text(encoding="utf-8"))
        self.assertEqual(record["result"], expected)
        self.assertEqual(expected["approx_catalog_intersection_percent"], 32.83)
        self.assertEqual(expected["approx_catalog_outside_dem_percent"], 67.17)
        self.assertFalse(record["claim_boundary"]["actual_radar_pixel_coverage_established"])
        self.assertFalse(record["claim_boundary"]["gtc_historical_root_cause_established"])
        self.assertFalse(record["claim_boundary"]["new_dem_acquisition_or_processing_authorized"])


if __name__ == "__main__":
    unittest.main()
