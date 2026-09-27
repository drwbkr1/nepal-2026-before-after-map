"""Disposable HyP3 mask and power-value QA tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from m2_asf_hyp3_rtc_pixel_core_001 import evaluate_window  # noqa: E402
from pixel_qa_core import load_contract  # noqa: E402


CONTRACT = load_contract(Path(__file__).resolve().parents[1] /
                         "config/qa/pixel-readiness-contract.json")


def evaluate(codes: list[int], vv: list[float] | None = None,
             vh: list[float] | None = None) -> dict:
    count = len(codes)
    return evaluate_window(
        aoi_id="AOI-SOURCE", aoi_area_m2=count * 100.0,
        pixel_area_m2=100.0, footprint=np.ones((1, count), dtype=np.uint8),
        vv=np.asarray([1.0] * count if vv is None else vv, dtype=np.float32).reshape(1, count),
        vh=np.asarray([1.0] * count if vh is None else vh, dtype=np.float32).reshape(1, count),
        ls=np.asarray(codes, dtype=np.uint8).reshape(1, count),
        vv_nodata=-9999.0, vh_nodata=-9999.0, contract=CONTRACT,
    )


class HyP3PixelCoreTests(unittest.TestCase):
    def test_all_valid_power_passes_local_qa_only(self) -> None:
        result = evaluate([1] * 100)
        self.assertEqual(result["status"], "pass_qa_only")
        self.assertEqual(result["valid_cell_count"], 100)
        self.assertFalse(result["registration_measured"])
        self.assertFalse(result["scientific_admission_authorized"])

    def test_all_seventeen_documented_values_partition_once(self) -> None:
        values = [0, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31]
        result = evaluate(values)
        self.assertEqual(result["covered_cell_count"], len(values))
        self.assertEqual(result["valid_cell_count"], 1)
        self.assertEqual(sum(result["excluded_cell_count_by_reason"].values()), 16)
        self.assertEqual(result["excluded_cell_count_by_reason"]["provider_slope_geometry_exclusion"], 3)
        self.assertEqual(result["excluded_cell_count_by_reason"]["provider_layover_and_shadow"], 4)
        self.assertEqual(result["status"], "block")

    def test_unknown_mask_code_defers_even_with_usable_fraction(self) -> None:
        result = evaluate([1] * 99 + [2])
        self.assertEqual(result["status"], "defer")
        self.assertTrue(result["unknown_provider_mask_value_present"])

    def test_invalid_power_and_nodata_are_excluded(self) -> None:
        result = evaluate([1] * 10,
                          vv=[1.0] * 7 + [0.0, -9999.0, float("nan")])
        self.assertEqual(result["valid_cell_count"], 7)
        self.assertEqual(result["excluded_cell_count_by_reason"]["radar_nonpositive_power"], 1)
        self.assertEqual(result["excluded_cell_count_by_reason"]["radar_nodata_or_nonfinite"], 2)

    def test_shape_or_area_errors_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "rtc_pixel_array_or_area_invalid"):
            evaluate_window(aoi_id="x", aoi_area_m2=0, pixel_area_m2=100,
                            footprint=np.ones((2, 2)), vv=np.ones((2, 2)),
                            vh=np.ones((2, 2)), ls=np.ones((2, 2), dtype=np.uint8),
                            vv_nodata=None, vh_nodata=None, contract=CONTRACT)


if __name__ == "__main__":
    unittest.main()
