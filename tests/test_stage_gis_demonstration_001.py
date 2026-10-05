"""Path and integrity coverage for staging; no ArcPy or imagery fixtures."""
import sys
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from stage_gis_demonstration_001 import digest, preflight
from arcgis_demo_roundtrip import compare, has_data_source


class StagePreflight(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "input"
        self.source.mkdir()
        self.project = self.source / "fixture.aprx"
        self.project.write_bytes(b"disposable project placeholder")
        self.rasters = self.source / "images"
        self.rasters.mkdir()
        self.raster = self.rasters / "fixture.tif"
        self.raster.write_bytes(b"disposable non-raster placeholder")
        self.output = self.root / "new"

    def check(self):
        return preflight(self.project, self.rasters, self.output, digest(self.project),
                         {"fixture.tif": digest(self.raster)})

    def test_exact_disjoint_inputs_leave_files_untouched(self):
        before = self.raster.read_bytes()
        self.assertEqual(len(self.check()), 2)
        self.assertEqual(self.raster.read_bytes(), before)
        self.assertFalse(self.output.exists())

    def test_collision_is_rejected(self):
        self.output.mkdir()
        with self.assertRaisesRegex(ValueError, "collision"):
            self.check()

    def test_nested_output_is_rejected(self):
        self.output = self.source / "new"
        with self.assertRaisesRegex(ValueError, "overlap"):
            self.check()

    def test_hash_drift_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "hash drift"):
            preflight(self.project, self.rasters, self.output, "0" * 64,
                      {"fixture.tif": digest(self.raster)})


class RoundTripComparison(unittest.TestCase):
    def test_standalone_table_without_layer_supports_is_accepted(self):
        self.assertTrue(has_data_source(SimpleNamespace(dataSource="local-table")))

    def test_object_without_data_source_is_rejected(self):
        self.assertFalse(has_data_source(SimpleNamespace(name="no data")))

    def test_changed_map_structure_is_detected(self):
        before = {"maps": [{"wkid": 32645}], "layouts": []}
        after = {"maps": [{"wkid": 4326}], "layouts": []}
        result = compare(before, after)
        self.assertFalse(result["structure_equal"])
        self.assertTrue(result["layout_pixels_equal"])

    def test_changed_render_is_detected(self):
        before = {"maps": [], "layouts": [{"pixels": "before"}]}
        after = {"maps": [], "layouts": [{"pixels": "after"}]}
        self.assertFalse(compare(before, after)["layout_pixels_equal"])


if __name__ == "__main__":
    unittest.main()
