import importlib.util
import inspect
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "reconcile_m2_dem_acquisition.py"
SPEC = importlib.util.spec_from_file_location("reconcile_m2_dem_acquisition", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.path.insert(0, str(ROOT / "scripts"))
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def assets(*states):
    return [{"state": state} for state in states]


class M2DemAcquisitionProgressTests(unittest.TestCase):
    def test_all_authorized_remains_acquisition(self):
        result = MODULE.evaluate_progress(assets("authorized", "authorized", "authorized", "authorized"))
        self.assertEqual(result["checkpoint"], "M2-DEM-ACQUISITION")
        self.assertEqual(result["disposition"], "in_progress")

    def test_partial_promotion_remains_acquisition(self):
        result = MODULE.evaluate_progress(assets("promoted", "authorized", "authorized", "authorized"))
        self.assertEqual(result["counts"], {"authorized": 3, "failed": 0, "promoted": 1})
        self.assertEqual(result["checkpoint"], "M2-DEM-ACQUISITION")

    def test_all_promoted_advances_to_geotiff_verification(self):
        result = MODULE.evaluate_progress(assets("promoted", "promoted", "promoted", "promoted"))
        self.assertEqual(result["checkpoint"], "M2-DEM-GEOTIFF-VERIFICATION")
        self.assertEqual(result["disposition"], "complete")

    def test_any_failure_requires_review(self):
        result = MODULE.evaluate_progress(assets("promoted", "failed", "authorized", "authorized"))
        self.assertEqual(result["checkpoint"], "M2-DEM-ACQUISITION-REVIEW")
        self.assertEqual(result["disposition"], "review")

    def test_staging_or_wrong_count_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unsupported DEM acquisition state"):
            MODULE.evaluate_progress(assets("staging", "authorized", "authorized", "authorized"))
        with self.assertRaisesRegex(ValueError, "unsupported DEM acquisition state"):
            MODULE.evaluate_progress(assets("authorized"))

    def test_current_promoted_receipt_identity_reconciles_without_external_access(self):
        verify_external_parameter = inspect.signature(MODULE.validate_asset_history).parameters["verify_external"]
        self.assertIs(verify_external_parameter.default, True)
        intake = MODULE.load(MODULE.INTAKE_PATH)
        summaries = MODULE.validate_asset_history(intake, verify_external=False)
        promoted = [item for item in summaries if item["state"] == "promoted"]
        self.assertGreaterEqual(len(promoted), 1)
        self.assertEqual(
            [item["source_id"] for item in promoted],
            MODULE.EXPECTED_SOURCE_IDS[: len(promoted)],
        )
        for item in promoted:
            self.assertGreater(item["local_size_bytes"], 0)
            self.assertEqual(len(item["local_sha256"]), 64)
            self.assertTrue(all(character in "0123456789abcdef" for character in item["local_sha256"]))


if __name__ == "__main__":
    unittest.main()
