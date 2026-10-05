"""Presentation extent and metadata-only export checks, using disposable geometry."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from gis_experiment_atlas_001 import aoi_bounds, make_geopackage
from package_gis_experiment_atlas_001 import compare_atlas_snapshots, member_path, seal_zip
from gis_evidence_catalog_001 import RECORDS, add_geopackage_tables, build_catalog, load_public_records, primary_tables, verify_unchanged_original_files
from arcgis_demo_roundtrip import inventory
from unittest.mock import patch
import hashlib
from gis_experiment_atlas_001 import RASTERS
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


class EvidenceCatalog(unittest.TestCase):
    def test_public_snapshots_use_committed_bytes_and_refuse_uncommitted_changes(self):
        docs = self.documents()
        blobs = {ref: (json.dumps(docs[key],indent=2)+"\n").encode("utf-8") for key,(ref,_) in RECORDS.items()}
        def git_fixture(args, **kwargs):
            if args[1] == "ls-files": return "\n".join(blobs)
            if args[1] == "rev-parse": return "a"*40+"\n"
            return blobs[args[2].split(":",1)[1]]
        with tempfile.TemporaryDirectory() as folder, patch("gis_evidence_catalog_001.subprocess.check_output", side_effect=git_fixture):
            repo=Path(folder)
            for ref,blob in blobs.items():
                path=repo/ref
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(blob.replace(b"\n",b"\r\n"))
            loaded,hashes,snapshots,commit=load_public_records(repo)
            self.assertEqual(loaded,docs)
            self.assertEqual(commit,"a"*40)
            self.assertEqual(snapshots["brightness"],blobs[RECORDS["brightness"][0]])
            self.assertEqual(hashes["brightness"],hashlib.sha256(blobs[RECORDS["brightness"][0]]).hexdigest())
            path=repo/RECORDS["brightness"][0]
            changed=json.loads(path.read_text(encoding="utf-8"))
            changed["status"]="uncommitted fixture change"
            path.write_text(json.dumps(changed),encoding="utf-8")
            with self.assertRaises(ValueError): load_public_records(repo)
    def test_existing_artifact_change_is_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            (path/"fixture.txt").write_text("generated fixture", encoding="utf-8")
            original = inventory(path)
            self.assertEqual(verify_unchanged_original_files(original,path),1)
            (path/"fixture.txt").write_text("changed", encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_unchanged_original_files(original,path)
    def documents(self):
        docs = {key: {"status": "generated status " + key} for key in RECORDS}
        before, after = "M1-SRC-002", "M1-SRC-005"
        docs["manifest"]["records"] = [{"source_id": source, "event_role": role,
            "exact_product_id": "generated fixture " + role, "acquisition_start_utc": date + "T00:00:00Z",
            "acquisition_end_utc": date + "T00:00:01Z", "orbit_or_tile": {"generated": True}}
            for source, role, date in ((before, "before", "2026-08-16"), (after, "after", "2026-08-28"))]
        docs["before_qa"].update(bindings={"archive_sha256": "a"*64}, event_AOI_results=[
            {"aoi_id": key, "status": "defer", "usable_fraction_of_aoi": fraction}
            for key, fraction in (("AOI-SOURCE", .5), ("AOI-UPPER-CORRIDOR", .7))])
        docs["after_archive"]["bindings"] = {"archive_sha256": "b"*64}
        docs["after_qa"]["observations"] = {"both_AOIs_full_area_QA_status": "defer",
            "AOI_SOURCE_usable_fraction": .6, "AOI_UPPER_CORRIDOR_usable_fraction": .75}
        docs["pair"].update(bindings={"before_source_id": before, "after_source_id": after,
            "before_archive_sha256": "a"*64, "after_archive_sha256": "b"*64},
            staged_display={role+"_sha256": RASTERS[name] for role, name in (("before", "before_common_valid_vv_db.tif"), ("after", "after_common_valid_vv_db.tif"))},
            pair_measurement={"scientific_admission": False, "AOI_SOURCE_common_valid_fraction": .45, "AOI_UPPER_CORRIDOR_common_valid_fraction": .65})
        docs["brightness"].update(scientific_admission=False, formula="generated formula", inputs=[
            {"source_id": source, "date": date, "sha256": RASTERS[name]}
            for source, date, name in ((before,"2026-08-16","before_common_valid_vv_db.tif"), (after,"2026-08-28","after_common_valid_vv_db.tif"))],
            numeric_outputs=[{"file": name, "sha256": RASTERS[name]} for name in ("delta_vv_db.tif", "excluded_cells.tif")])
        docs["atlas"].update(rasters=RASTERS.copy(), package={"sha256": "c"*64}, scientific_admission=False)
        return docs

    def test_exact_history_and_full_aoi_fractions_preserved(self):
        docs = self.documents()
        catalog = build_catalog(docs, dict.fromkeys(RECORDS, "d"*64))
        self.assertEqual({row["Evidence_Key"]: row["Exact_Status"] for row in catalog["EvidenceHistory"]},
                         {key: doc["status"] for key, doc in docs.items()})
        self.assertEqual(len(catalog["ArtifactLineage"]), 18)
        self.assertEqual(len(catalog["CoverageHistory"]), 6)
        self.assertEqual(catalog["CoverageHistory"][0]["Fraction_of_Full_AOI"], .5)
        self.assertFalse(catalog["scientific_admission"])
        self.assertEqual([row["Kind"] for row in catalog["ClaimRegister"]],
                         ["sensor measurement", "interpretation boundary", "attribution boundary"])

    def test_changed_identity_fraction_or_scientific_state_refuses(self):
        for changed in ("archive", "date", "fraction", "admission"):
            docs = self.documents()
            if changed == "archive": docs["after_archive"]["bindings"]["archive_sha256"] = "e"*64
            if changed == "date": docs["manifest"]["records"][0]["acquisition_start_utc"] = "2026-08-17T00:00:00Z"
            if changed == "fraction": docs["pair"]["pair_measurement"]["AOI_SOURCE_common_valid_fraction"] = 1.1
            if changed == "admission": docs["brightness"]["scientific_admission"] = True
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                build_catalog(docs, dict.fromkeys(RECORDS, "d"*64))

    def test_new_gpkg_attributes_leave_original_rows_and_geometry_unchanged(self):
        try:
            from osgeo import ogr
        except ImportError:
            self.skipTest("Installed-runtime GDAL covers disposable GeoPackage extension")
        fields = [{"name": "AOI_ID", "length": 40}]
        features = [{"attributes": {"AOI_ID": str(i)}, "geometry": {"rings": [[[100+i,200],[110+i,200],[110+i,210],[100+i,210],[100+i,200]]]}} for i in range(3)]
        sources = [{"Source_ID": str(i), "Acquired": "fixture", "RasterFile": "fixture.tif", "SHA256": "0"*64, "Use_Status": "generated"} for i in range(2)]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"generated.gpkg"
            make_geopackage(path, {"fields":fields,"features":features}, sources)
            original = primary_tables(path.resolve())
            catalog = build_catalog(self.documents(), dict.fromkeys(RECORDS, "d"*64))
            counts = add_geopackage_tables(path, catalog)
            self.assertEqual(counts, {"SourceIdentity":2,"EvidenceHistory":16,"ArtifactLineage":18,"CoverageHistory":6,"ClaimRegister":3})
            self.assertEqual(primary_tables(path.resolve()), original)
            ds = ogr.Open(str(path), 0)
            self.assertEqual(ds.GetLayerCount(), 8)
            ds = None


if __name__ == "__main__":
    unittest.main()
