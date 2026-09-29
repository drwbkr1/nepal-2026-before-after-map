from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "landsat_c2_qa_flags", ROOT / "scripts" / "landsat_c2_qa_flags.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LandsatC2QAFlagTests(unittest.TestCase):
    def test_each_pixel_flag_uses_its_documented_bit(self) -> None:
        fields = (
            "fill", "dilated_cloud", "high_confidence_cirrus",
            "high_confidence_cloud", "high_confidence_cloud_shadow",
            "high_confidence_snow", "clear_bit", "water",
        )
        for bit, field in enumerate(fields):
            with self.subTest(bit=bit, field=field):
                decoded = MODULE.decode_qa_pixel(np.array([1 << bit], dtype=np.uint16))
                self.assertTrue(decoded[field][0])
                self.assertTrue(all(not decoded[other][0] for other in fields if other != field))

    def test_pixel_flags_and_confidences_remain_separate(self) -> None:
        words = np.array([0, (1 << 4) | (1 << 6) | (2 << 8) | (3 << 12)], dtype=np.uint16)
        decoded = MODULE.decode_qa_pixel(words)
        self.assertEqual(decoded["high_confidence_cloud_shadow"].tolist(), [False, True])
        self.assertEqual(decoded["clear_bit"].tolist(), [False, True])
        self.assertEqual(decoded["cloud_confidence"].tolist(), [0, 2])
        self.assertEqual(decoded["snow_ice_confidence"].tolist(), [0, 3])
        self.assertFalse(decoded["high_confidence_cloud"][1])

    def test_radsat_maps_only_selected_bands_and_terrain(self) -> None:
        words = np.array([1 << 0, (1 << 2) | (1 << 4) | (1 << 11)], dtype=np.uint16)
        decoded = MODULE.decode_qa_radsat(words)
        self.assertEqual(decoded["band3_saturated"].tolist(), [False, True])
        self.assertEqual(decoded["band5_saturated"].tolist(), [False, True])
        self.assertEqual(decoded["terrain_occlusion"].tolist(), [False, True])
        self.assertEqual(decoded["band4_saturated"].tolist(), [False, False])

    def test_aerosol_retrieval_and_level_are_not_a_mask_decision(self) -> None:
        words = np.array([0, (1 << 1) | (1 << 5) | (3 << 6)], dtype=np.uint8)
        decoded = MODULE.decode_sr_qa_aerosol(words)
        self.assertEqual(decoded["valid_retrieval"].tolist(), [False, True])
        self.assertEqual(decoded["interpolated"].tolist(), [False, True])
        self.assertEqual(decoded["aerosol_level"].tolist(), [0, 3])

    def test_rejects_noninteger_and_out_of_range_words(self) -> None:
        for values in ([1.0], [-1], [65536]):
            with self.subTest(values=values), self.assertRaises(ValueError):
                MODULE.decode_qa_pixel(values)
        with self.assertRaises(ValueError):
            MODULE.decode_sr_qa_aerosol([256])


if __name__ == "__main__":
    unittest.main()
