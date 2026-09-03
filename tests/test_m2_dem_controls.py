from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PREPARE = load_module("prepare_m2_dem_controls", "scripts/prepare_m2_dem_controls.py")
VERIFY = load_module("verify_m2_dem_geotiff", "scripts/verify_m2_dem_geotiff.py")


class M2DemControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(
            (ROOT / "records/source-gates/m2-dem-candidate-manifest.json").read_text(encoding="utf-8")
        )
        cls.proposal = json.loads(
            (ROOT / "contracts/milestone-002-dem-amendment-proposal.json").read_text(encoding="utf-8")
        )
        cls.intake = json.loads(
            (ROOT / "contracts/m2-dem-intake-candidate.json").read_text(encoding="utf-8")
        )
        cls.verification = json.loads(
            (ROOT / "contracts/m2-dem-offline-verification-candidate.json").read_text(encoding="utf-8")
        )

    def test_controls_are_deterministically_derived(self) -> None:
        generated_intake = PREPARE.build_intake(self.manifest, self.proposal)
        generated_verification = PREPARE.build_verification(self.manifest, generated_intake)
        self.assertEqual(generated_intake, self.intake)
        self.assertEqual(generated_verification, self.verification)
        self.assertEqual(
            PREPARE.validate_derivation(
                self.manifest,
                self.proposal,
                generated_intake,
                generated_verification,
            ),
            [],
        )

    def test_intake_preserves_exact_boundary_and_no_authority(self) -> None:
        self.assertEqual(len(self.intake["assets"]), 4)
        self.assertEqual(self.intake["extensions"]["authority_status"], "not_granted")
        self.assertTrue(self.intake["extensions"]["static_only_no_network_or_external_filesystem_mutation"])
        self.assertEqual({asset["state"] for asset in self.intake["assets"]}, {"planned"})
        self.assertTrue(all(asset["attempts"] == [] for asset in self.intake["assets"]))
        self.assertTrue(all(asset["expected"]["sha256"] is None for asset in self.intake["assets"]))
        self.assertEqual(
            sum(asset["expected"]["size_bytes"] for asset in self.intake["assets"]),
            170302058,
        )

    def test_candidate_verifier_refuses_execution(self) -> None:
        errors = VERIFY.validate_active_contract(self.verification)
        self.assertIn("verification contract is not active", errors)
        self.assertIn("DEM amendment is not approved", errors)
        self.assertIn("DEM pixel processing is not authorized", errors)

    def test_synthetic_expected_metadata_passes_structural_only(self) -> None:
        asset = self.verification["assets"][0]
        observed = {
            "size_bytes": asset["expected_size_bytes"],
            "sha256": "a" * 64,
            "tiff_signature": "49492a00",
            "shape": asset["expected_shape"],
            "band_count": 1,
            "pixel_type": "F32",
            "crs_wkid": 4326,
            "cell_size_degrees": asset["expected_cell_size_degrees"],
            "extent_wgs84": VERIFY.expected_extent(asset),
            "nodata": {"any_nodata": "0", "all_nodata": "0", "nodata_value": ""},
            "statistics": {"minimum": 100.0, "maximum": 8000.0},
        }
        result = VERIFY.evaluate_metadata(asset, observed, self.verification["raster_controls"])
        self.assertEqual(result["status"], "pass_structural_only")
        self.assertFalse(result["valid_pixel_coverage_established"])
        self.assertFalse(result["vertical_datum_route_established"])
        self.assertFalse(result["scientific_fitness_established"])

    def test_synthetic_metadata_drift_fails(self) -> None:
        asset = self.verification["assets"][0]
        observed = {
            "size_bytes": asset["expected_size_bytes"] + 1,
            "tiff_signature": "00000000",
            "shape": [3599, 3600],
            "band_count": 1,
            "pixel_type": "F32",
            "crs_wkid": 4326,
            "cell_size_degrees": asset["expected_cell_size_degrees"],
            "extent_wgs84": VERIFY.expected_extent(asset),
            "nodata": {"any_nodata": "0", "all_nodata": "0", "nodata_value": ""},
            "statistics": {"minimum": 100.0, "maximum": 8000.0},
        }
        result = VERIFY.evaluate_metadata(asset, observed, self.verification["raster_controls"])
        self.assertEqual(result["status"], "fail")
        self.assertEqual(set(result["failures"]), {"size_bytes", "tiff_signature", "shape"})

    def test_receipt_refuses_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "receipt.json"
            VERIFY.write_new(output, {"attempt": 1})
            with self.assertRaises(SystemExit):
                VERIFY.write_new(output, {"attempt": 2})
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), {"attempt": 1})

    def test_mutated_candidate_authority_is_detected(self) -> None:
        mutated = copy.deepcopy(self.verification)
        mutated["authority"]["dem_download_authorized"] = True
        errors = PREPARE.validate_derivation(self.manifest, self.proposal, self.intake, mutated)
        self.assertTrue(any("authority" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
