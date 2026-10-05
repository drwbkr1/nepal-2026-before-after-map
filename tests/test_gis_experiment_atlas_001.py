"""Presentation extent and metadata-only export checks, using disposable geometry."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from gis_experiment_atlas_001 import aoi_bounds, make_geopackage
from package_gis_experiment_atlas_001 import compare_atlas_snapshots, member_path, seal_zip
import copy


class AtlasExtent(unittest.TestCase):
    def test_metadata_extent_padding_does_not_mutate_geometry(self):
        feature = {"geometry": {"rings": [[[0, 10], [10, 10], [10, 20], [0, 10]]]}}
        original = json.dumps(feature)
        self.assertEqual(aoi_bounds(feature, .1), [-1, 9, 11, 21])
        self.assertEqual(json.dumps(feature), original)

    def test_degenerate_geometry_or_negative_padding_is_rejected(self):
        feature = {"geometry": {"rings": [[[0, 0], [0, 1], [0, 0]]]}}
        with self.assertRaises(ValueError):
            aoi_bounds(feature)
        feature["geometry"]["rings"][0][1] = [1, 1]
        with self.assertRaises(ValueError):
            aoi_bounds(feature, -.1)


class DisposableGeoPackage(unittest.TestCase):
    def test_projected_geometry_and_nonspatial_method_tables_reopen(self):
        try:
            from osgeo import ogr
        except ImportError:
            self.skipTest("GDAL unavailable in portable runtime; installed-runtime test covers it")
        fields = [{"name": "AOI_ID", "length": 40}]
        features = [{"attributes": {"AOI_ID": str(i)}, "geometry": {"rings": [[[100+i, 200], [110+i, 200], [110+i, 210], [100+i, 210], [100+i, 200]]]}} for i in range(3)]
        sources = [{"Source_ID": str(i), "Acquired": "fixture", "RasterFile": "fixture.tif", "SHA256": "0"*64, "Use_Status": "disposable"} for i in range(2)]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "generated.gpkg"
            self.assertEqual(make_geopackage(path, {"fields": fields, "features": features}, sources),
                             {"StudyAreas": 3, "DisplayedSources": 2, "ExperimentMethod": 1})
            ds = ogr.Open(str(path), 0)
            layer = row = None
            try:
                layer = ds.GetLayerByName("StudyAreas")
                self.assertEqual(layer.GetSpatialRef().GetAuthorityCode(None), "32645")
                # Hold the owning feature while its borrowed geometry is read.
                row = layer.GetNextFeature()
                geom = json.loads(row.GetGeometryRef().ExportToJson())
                self.assertEqual(geom["coordinates"], features[0]["geometry"]["rings"])
            finally:
                row = layer = ds = None


class DisposableBundle(unittest.TestCase):
    def test_field_order_adapter_keeps_type_name_and_other_checks_strict(self):
        original = {"maps": [{"items": [{"fields": [["OBJECTID", "OID"], ["NAME", "String"]], "rows": 3}]}], "layouts": []}
        reordered = copy.deepcopy(original)
        fields = reordered["maps"][0]["items"][0]["fields"]
        fields.reverse()
        self.assertTrue(compare_atlas_snapshots(original, reordered)["structure_equal"])
        self.assertEqual(original["maps"][0]["items"][0]["fields"][0][0], "OBJECTID")
        self.assertEqual(fields[0][0], "NAME")
        for key, value in (("fields", [["OBJECTID", "OID"], ["NAME", "Double"]]), ("rows", 4)):
            changed = copy.deepcopy(reordered)
            changed["maps"][0]["items"][0][key] = value
            self.assertFalse(compare_atlas_snapshots(original, changed)["structure_equal"])
    def test_archive_identity_and_no_replace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / "bundle"
            (folder / "nested").mkdir(parents=True)
            (folder / "nested/value.txt").write_text("generated fixture", encoding="utf-8")
            result = seal_zip(folder, root / "test.zip", root / "extracted")
            self.assertTrue(result["crc_pass"] and result["all_file_hashes_match"])
            self.assertEqual((root / "extracted/nested/value.txt").read_text(encoding="utf-8"), "generated fixture")
            with self.assertRaises(ValueError):
                seal_zip(folder, root / "test.zip", root / "another-extraction")

    def test_unsafe_member_names_are_rejected(self):
        for name in ("../escape", "/absolute", "C:/drive", "nested\\escape", "nested/../escape", "./normalized"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                member_path(name)


if __name__ == "__main__":
    unittest.main()
