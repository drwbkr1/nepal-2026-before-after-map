import json
import unittest

from scripts.audit_m2_radar_gtc_public_coverage_001 import ROOT
from scripts.audit_m2_radar_gtc_public_coverage_002 import OUTPUT_REF, SOURCE_IDS, calculate


class SixSourceCoverageAuditTests(unittest.TestCase):
    def test_frozen_catalog_results_and_claim_limits(self):
        record = json.loads((ROOT / OUTPUT_REF).read_text(encoding="utf-8"))
        rows = calculate()
        self.assertEqual(record["results"], rows)
        self.assertEqual(tuple(row["source_id"] for row in rows), SOURCE_IDS)
        self.assertEqual(
            [row["approx_catalog_intersection_percent"] for row in rows],
            [32.83, 60.97, 25.35, 32.83, 60.96, 25.38],
        )
        self.assertTrue(all(row["approx_catalog_outside_dem_percent"] > 0 for row in rows))
        self.assertTrue(all(not value for value in record["claim_boundary"].values()))


if __name__ == "__main__":
    unittest.main()
