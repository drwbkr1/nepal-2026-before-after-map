from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_m2_dem_geotiff.py"
SPEC = importlib.util.spec_from_file_location("verify_m2_dem_geotiff_active", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class M2DemActiveGeoTiffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load("contracts/m2-dem-offline-verification.json")
        cls.intake = load("contracts/m2-dem-intake.json")

    def test_exact_active_contract_is_ready_and_current(self):
        self.assertEqual(MODULE.validate_active_contract(self.contract), [])

    def test_each_contract_asset_has_one_promoted_receipt_binding(self):
        for asset in self.contract["assets"]:
            intake_asset, receipt, errors = MODULE.promoted_asset_binding(asset, self.intake)
            self.assertEqual(errors, [])
            self.assertIsNotNone(intake_asset)
            self.assertIsNotNone(receipt)
            self.assertEqual(receipt["event"], "dem_transfer_succeeded")
            self.assertEqual(receipt["source_id"], asset["source_id"])

    def test_stale_intake_hash_or_weakened_boundary_is_rejected(self):
        stale = copy.deepcopy(self.contract)
        stale["inputs"]["intake_contract_sha256"] = "0" * 64
        self.assertIn("verification contract active-intake hash differs", MODULE.validate_active_contract(stale))
        weakened = copy.deepcopy(self.contract)
        weakened["authority"]["network_access_authorized"] = True
        self.assertIn(
            "verification contract weakens network or custody-mutation boundaries",
            MODULE.validate_active_contract(weakened),
        )

    def test_promoted_receipt_hash_drift_is_rejected(self):
        mutated = copy.deepcopy(self.intake)
        mutated["assets"][0]["extensions"]["successful_attempt_receipt_sha256"] = "0" * 64
        _, _, errors = MODULE.promoted_asset_binding(self.contract["assets"][0], mutated)
        self.assertIn("successful transfer receipt hash differs", errors)

    def test_expected_local_sha256_participates_in_structural_decision(self):
        asset = copy.deepcopy(self.contract["assets"][0])
        asset["expected_sha256"] = "a" * 64
        observed = {
            "size_bytes": asset["expected_size_bytes"],
            "sha256": "b" * 64,
            "tiff_signature": "49492a00",
            "shape": asset["expected_shape"],
            "band_count": 1,
            "pixel_type": "F32",
            "crs_wkid": 4326,
            "cell_size_degrees": asset["expected_cell_size_degrees"],
            "extent_wgs84": MODULE.expected_extent(asset),
            "nodata": {"any_nodata": "0", "all_nodata": "0", "nodata_value": ""},
            "statistics": {"minimum": 100.0, "maximum": 8000.0},
        }
        result = MODULE.evaluate_metadata(asset, observed, self.contract["raster_controls"])
        self.assertEqual(result["status"], "fail")
        self.assertIn("sha256", result["failures"])


if __name__ == "__main__":
    unittest.main()
