from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/complete_m2_dem_verification.py"
SPEC = importlib.util.spec_from_file_location("complete_m2_dem_verification", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.path.insert(0, str(ROOT / "scripts"))
SPEC.loader.exec_module(MODULE)


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class M2DemVerificationCompletionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load("contracts/m2-dem-offline-verification.json")
        cls.intake = load("contracts/m2-dem-intake.json")
        cls.aois = load("config/aoi/approved-study-areas.geojson")

    def test_four_exact_passes_and_two_failures_are_preserved(self):
        passes, failures = MODULE.validate_pass_receipts(self.contract, self.intake)
        self.assertEqual([item["source_id"] for item in passes], MODULE.EXPECTED_SOURCE_IDS)
        self.assertEqual(len(failures), 2)
        self.assertEqual(sum(item["local_size_bytes"] for item in passes), 170302058)
        self.assertEqual(sum(item["valid_cell_count"] for item in passes), 51840000)
        self.assertEqual(sum(item["nodata_or_nonfinite_cell_count"] for item in passes), 0)

    def test_all_approved_aois_have_valid_coverage_basis(self):
        passes, _ = MODULE.validate_pass_receipts(self.contract, self.intake)
        results = MODULE.evaluate_aoi_coverage(self.contract, self.aois, passes)
        self.assertEqual([item["aoi_id"] for item in results], ["AOI-OVERVIEW", "AOI-SOURCE", "AOI-UPPER-CORRIDOR"])
        self.assertTrue(all(item["status"] == "pass_valid_coverage" for item in results))

    def test_aoi_outside_verified_footprint_fails(self):
        passes, _ = MODULE.validate_pass_receipts(self.contract, self.intake)
        shifted = json.loads(json.dumps(self.aois))
        shifted["features"][0]["geometry"]["coordinates"][0][0][0] = 86.1
        results = MODULE.evaluate_aoi_coverage(self.contract, shifted, passes)
        self.assertEqual(results[0]["status"], "fail")


if __name__ == "__main__":
    unittest.main()
