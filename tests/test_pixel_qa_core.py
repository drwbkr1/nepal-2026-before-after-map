from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "pixel_qa_core.py"
SPEC = importlib.util.spec_from_file_location("pixel_qa_core", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
CONTRACT = MODULE.load_contract(ROOT / "config/qa/pixel-readiness-contract.json")


def grid(**updates):
    value = {
        "wkid": 32645,
        "cell_size_x": 20.0,
        "cell_size_y": 20.0,
        "origin_x": 500000.0,
        "origin_y": 3000000.0,
        "xmin": 500000.0,
        "ymin": 3000000.0,
        "xmax": 501000.0,
        "ymax": 3001000.0,
        "rotation_degrees": 0.0,
    }
    value.update(updates)
    return value


class PixelQACoreTests(unittest.TestCase):
    def test_contract_is_predeclared_and_claim_bounded(self) -> None:
        self.assertEqual(MODULE.validate_contract(CONTRACT), [])
        self.assertFalse(CONTRACT["decision_semantics"]["pass_qa_only_creates_scientific_admission"])
        self.assertEqual(set(CONTRACT["optical_scl"]["valid_surface_classes"]), {"4", "5", "6"})

    def test_full_coverage_and_usable_fraction_pass_qa_only(self) -> None:
        result = MODULE.evaluate_aoi_coverage(
            aoi_id="source-area",
            aoi_area_m2=100.0,
            covered_area_m2=100.0,
            valid_area_m2=85.0,
            excluded_area_by_reason_m2={"cloud": 15.0},
            contract=CONTRACT,
        )
        self.assertEqual(result["status"], "pass_qa_only")
        self.assertFalse(result["scientific_admission_authorized"])

    def test_partial_coverage_defers_without_erasing_usable_area(self) -> None:
        result = MODULE.evaluate_aoi_coverage(
            aoi_id="upper-corridor",
            aoi_area_m2=100.0,
            covered_area_m2=60.0,
            valid_area_m2=45.0,
            excluded_area_by_reason_m2={"cloud": 15.0},
            contract=CONTRACT,
        )
        self.assertEqual(result["status"], "defer")
        self.assertEqual(result["valid_area_m2"], 45.0)

    def test_very_low_usable_fraction_blocks_route_not_source(self) -> None:
        result = MODULE.evaluate_aoi_coverage(
            aoi_id="source-area",
            aoi_area_m2=100.0,
            covered_area_m2=100.0,
            valid_area_m2=10.0,
            excluded_area_by_reason_m2={"cloud": 90.0},
            contract=CONTRACT,
        )
        self.assertEqual(result["status"], "block")
        self.assertFalse(CONTRACT["decision_semantics"]["block_rejects_source_identity"])

    def test_inconsistent_area_is_invalid(self) -> None:
        result = MODULE.evaluate_aoi_coverage(
            aoi_id="source-area",
            aoi_area_m2=100.0,
            covered_area_m2=80.0,
            valid_area_m2=90.0,
            excluded_area_by_reason_m2={},
            contract=CONTRACT,
        )
        self.assertEqual(result["status"], "invalid")

    def test_aligned_grid_pair_passes(self) -> None:
        after = grid(origin_x=500020.0, xmin=500020.0, xmax=501020.0)
        self.assertEqual(MODULE.evaluate_grid_pair(grid(), after, CONTRACT)["status"], "pass_qa_only")

    def test_subpixel_origin_shift_blocks_analysis_ready_pair(self) -> None:
        after = grid(origin_x=500012.0, xmin=500012.0, xmax=501012.0)
        result = MODULE.evaluate_grid_pair(grid(), after, CONTRACT)
        self.assertEqual(result["status"], "block")
        self.assertTrue(any("origins" in error for error in result["errors"]))

    def test_wrong_crs_and_nonoverlap_block(self) -> None:
        wrong = grid(wkid=4326, xmin=600000.0, xmax=601000.0)
        result = MODULE.evaluate_grid_pair(grid(), wrong, CONTRACT)
        self.assertEqual(result["status"], "block")
        self.assertTrue(any("EPSG:32645" in error for error in result["errors"]))

    def test_registration_not_run_defers(self) -> None:
        result = MODULE.evaluate_registration(
            stable_control_pair_count=None,
            rmse_pixels=None,
            bias_x_pixels=None,
            bias_y_pixels=None,
            contract=CONTRACT,
        )
        self.assertEqual(result["status"], "defer")

    def test_registration_threshold_boundaries(self) -> None:
        passed = MODULE.evaluate_registration(
            stable_control_pair_count=30,
            rmse_pixels=0.5,
            bias_x_pixels=0.5,
            bias_y_pixels=-0.5,
            contract=CONTRACT,
        )
        deferred = MODULE.evaluate_registration(
            stable_control_pair_count=20,
            rmse_pixels=0.5,
            bias_x_pixels=0.1,
            bias_y_pixels=0.1,
            contract=CONTRACT,
        )
        blocked = MODULE.evaluate_registration(
            stable_control_pair_count=50,
            rmse_pixels=1.01,
            bias_x_pixels=0.1,
            bias_y_pixels=0.1,
            contract=CONTRACT,
        )
        self.assertEqual(passed["status"], "pass_qa_only")
        self.assertEqual(deferred["status"], "defer")
        self.assertEqual(blocked["status"], "block")

    def test_mutated_threshold_order_is_rejected(self) -> None:
        mutated = copy.deepcopy(CONTRACT)
        mutated["aoi_coverage"]["partial_evidence_defer_minimum"] = 0.9
        self.assertTrue(any("ordered" in error for error in MODULE.validate_contract(mutated)))


if __name__ == "__main__":
    unittest.main()
