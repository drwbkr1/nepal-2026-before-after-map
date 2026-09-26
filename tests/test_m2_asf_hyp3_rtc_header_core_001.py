"""Synthetic-only tests for HyP3 RTC projected header guards."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from m2_asf_hyp3_rtc_core_001 import ORDER, RouteStop  # noqa: E402
from m2_asf_hyp3_rtc_header_core_001 import RASTERS, inspect_raster_headers  # noqa: E402


def headers() -> dict:
    grid = {
        "wkid": 32645, "cell_size_x": 10.0, "cell_size_y": 10.0,
        "origin_x": 400000.0, "origin_y": 3200000.0,
        "xmin": 400000.0, "ymin": 3199000.0,
        "xmax": 401000.0, "ymax": 3200000.0,
        "rotation_degrees": 0.0,
    }
    return {
        role: {"width": 100, "height": 100, "band_count": 1,
               "data_type": data_type, "grid": copy.deepcopy(grid)}
        for role, data_type in RASTERS.items()
    }


class HeaderScreenTests(unittest.TestCase):
    def test_all_exact_sources_pass_synthetic_headers_only(self) -> None:
        for source_id in ORDER:
            with self.subTest(source_id=source_id):
                result = inspect_raster_headers(source_id, headers())
                self.assertEqual(result["status"], "pass_synthetic_header_grid_only")
                self.assertFalse(result["actual_headers_opened"])
                self.assertFalse(result["pixels_or_aoi_coverage_assessed"])
                self.assertFalse(result["arcgis_map_ready"])

    def test_wrong_crs_spacing_type_or_missing_layer_stops(self) -> None:
        mutations = []
        wrong_crs = headers(); wrong_crs["vv"]["grid"]["wkid"] = 4326; mutations.append(wrong_crs)
        wrong_spacing = headers(); wrong_spacing["vv"]["grid"]["cell_size_x"] = 20.0; mutations.append(wrong_spacing)
        wrong_type = headers(); wrong_type["ls_map"]["data_type"] = "Float32"; mutations.append(wrong_type)
        missing = headers(); del missing["area"]; mutations.append(missing)
        for altered in mutations:
            with self.subTest(altered=altered), self.assertRaises(RouteStop):
                inspect_raster_headers(ORDER[0], altered)

    def test_shifted_layer_and_inconsistent_dimensions_stop(self) -> None:
        shifted = headers()
        shifted["vh"]["grid"].update(origin_x=400005.0, xmin=400005.0, xmax=401005.0)
        with self.assertRaisesRegex(RouteStop, "rtc_header_layer_grid_mismatch"):
            inspect_raster_headers(ORDER[0], shifted)
        inconsistent = headers()
        inconsistent["vv"]["width"] = 101
        with self.assertRaisesRegex(RouteStop, "rtc_header_extent_dimensions_inconsistent"):
            inspect_raster_headers(ORDER[0], inconsistent)

    def test_nonfinite_rotation_and_invalid_source_stop(self) -> None:
        invalid = headers()
        invalid["dem"]["grid"]["rotation_degrees"] = float("nan")
        with self.assertRaisesRegex(RouteStop, "rtc_header_grid_value_invalid"):
            inspect_raster_headers(ORDER[0], invalid)
        with self.assertRaisesRegex(RouteStop, "rtc_header_source_invalid"):
            inspect_raster_headers("M1-SRC-999", headers())


if __name__ == "__main__":
    unittest.main()
