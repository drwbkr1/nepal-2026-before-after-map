"""Synthetic guards for the approved actual-scene DEM coverage audit."""

from __future__ import annotations

import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from m2_radar_event_pair_dem_footprint_gate_001 import parse_geolocation_grid  # noqa: E402
from m2_radar_event_pair_dem_intake_001 import IntakeError  # noqa: E402


def write_grid(path: Path, *, omit_last: bool = False) -> None:
    root = ET.Element("product")
    image = ET.SubElement(root, "imageInformation")
    ET.SubElement(image, "numberOfLines").text = "16732"
    ET.SubElement(image, "numberOfSamples").text = "25769"
    points = ET.SubElement(root, "geolocationGridPointList")
    for row_number in range(10):
        for column_number in range(21):
            if omit_last and (row_number, column_number) == (9, 20):
                continue
            node = ET.SubElement(points, "geolocationGridPoint")
            values = {
                "line": round(row_number * 16731 / 9),
                "pixel": round(column_number * 25768 / 20),
                "latitude": 27.6 + row_number * 0.2,
                "longitude": 83.9 + column_number * 0.14,
            }
            for key, value in values.items():
                ET.SubElement(node, key).text = str(value)
    ET.ElementTree(root).write(path, encoding="utf-8")


class ActualFootprintGridTests(unittest.TestCase):
    def test_full_scene_grid_yields_closed_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "annotation.xml"
            write_grid(path)
            result = parse_geolocation_grid(path)
            self.assertEqual(result["grid_points"], 210)
            self.assertEqual(len(result["ring"]), 58)
            self.assertEqual(result["ring"][0], (83.9, 27.6))

    def test_incomplete_corner_blocks_full_extent_claim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "annotation.xml"
            write_grid(path, omit_last=True)
            with self.assertRaisesRegex(IntakeError, "geolocation_grid_not_full_actual_scene"):
                parse_geolocation_grid(path)


if __name__ == "__main__":
    unittest.main()
