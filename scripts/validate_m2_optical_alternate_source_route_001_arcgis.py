"""Disposable L8/L9 full metadata/materialization/header/pixel/panel validation.

Only generated TARs, tiny rasters, AOIs, controls and receipts are accessed.
No project source, custody file, provider or browser is opened.
"""
import argparse
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import arcpy
import numpy as np
import run_m2_optical_alternate_source_route_001 as route
import sys
sys.path.insert(0, str(route.ROOT / "tests"))
from test_optical_alternate_source_route_001 import feature, metadata_suffixes
from test_landsat9_visual_route_completion_001 import fixture_bytes, fixture_groups
from test_landsat_l2_grouped_mtl_integrity_002 import write_tar
from landsat_l2_grouped_mtl_integrity_002 import inspect_bundle


def main(output):
    suite = unittest.TestSuite()
    # Discovery uses the portable Python geometry dependency. ArcGIS needs only
    # the selected locked identities, frozen metadata/QA and durable supervisor.
    # Do not install or inject discovery libraries into the ArcGIS environment.
    for pattern in ("test_landsat9_visual_route_completion_001.py", "test_landsat9_pixel_visual_recovery_001.py"):
        suite.addTests(unittest.defaultTestLoader.discover(str(route.ROOT / "tests"), pattern=pattern))
    tests = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
    if not tests.wasSuccessful():
        raise RuntimeError("disposable_tests_failed")
    output.mkdir(parents=True, exist_ok=False)
    evidence = []
    with tempfile.TemporaryDirectory(prefix="optical-alternate-synthetic-", ignore_cleanup_errors=True) as temporary:
        root = Path(temporary)
        for sensor in (8, 9):
            working = root / str(sensor); working.mkdir()
            pair = {"locked_rank":1,"platform":f"landsat-{sensor}"}
            for role,date in (("before","20260803"),("after","20260904")):
                item=feature(sensor,date)
                pair[role]={"product_id":item["id"][:-3],"scene_id":item["properties"]["landsat:scene_id"],
                            "acquired_at_utc":item["properties"]["datetime"],"eligible":True}
            aoi = working / "aoi.json"
            ring = [[300030,3100030],[300120,3100030],[300120,3100120],[300030,3100120],[300030,3100030]]
            route.write_new(aoi, {"features": [{"attributes": {"AOI_ID": key}, "geometry": {"rings": [ring]}} for key in route.policy.AOIS]})
            sources = {}
            for role in ("before", "after"):
                source = pair[role]; product = source["product_id"]
                text, xml = fixture_bytes(fixture_groups(product,source["scene_id"]))
                items = []
                for suffix in metadata_suffixes():
                    raw = text if suffix == "_MTL.txt" else xml if suffix == "_MTL.xml" else b"disposable-not-decoded"
                    if suffix[1:-4] in route.frozen.ROLES:
                        name = suffix[1:-4]
                        array = np.full((5,5),20000 if name.startswith("SR_B") else (2 if name=="SR_QA_AEROSOL" else 0),dtype=np.uint16)
                        if name.startswith("SR_B"):
                            array[1:4,1:4] += np.arange(9,dtype=np.uint16).reshape(3,3)*100
                        path = working / (role+suffix)
                        arcpy.NumPyArrayToRaster(array, arcpy.Point(300000,3100000),30,30).save(str(path))
                        arcpy.management.DefineProjection(str(path),arcpy.SpatialReference(32645))
                        raw = path.read_bytes()
                    items.append((product+suffix,raw))
                archive = working / (product+".tar")
                write_tar(archive,items)
                sources[product] = (archive,inspect_bundle(archive,product,source["scene_id"]))
            attempt,events,fallback = (working/name for name in ("attempt","events","fallback"))
            gate = working / "gate.json"
            payload = {"status":"pass_final_no_content_preflight","approval_sha256":route.policy.APPROVAL_SHA,
                       "recovery_approval_sha256":route.policy.APPROVAL_SHA,"recovery_attempt_root_absent":True,
                       "independent_event_roots_absent":True,"implementation_hashes":route.code_hashes(),
                       "implementation_public_ci_commit":"a"*40,"implementation_public_ci_run_id":"12345678"}
            route.write_new(gate,payload)
            loader = lambda source,*args:sources[source["product_id"]]

            def worker(path):
                qa = route.pair_qa_once(pair,attempt,events,arcpy,data=working,aoi=aoi,load_source=loader)
                route.write_new(attempt/"terminal.json",qa)
                return 0

            with patch.object(route,"validate_gate",return_value=None):
                supervised = route.supervise_stage(gate,roots=(attempt,events,fallback),worker=worker)
            if supervised["status"] != "pass_pair_visual_qa_only":
                raise RuntimeError("disposable_qa_supervision_failed")
            qa = route.read(attempt/"pixel-qa.json")
            if not qa["full_both_aois"] or any(m["paired_strict_usable_fraction"] != 1 for m in qa["aoi_metrics"].values()):
                raise RuntimeError("disposable_qa_predicates_failed")
            stages = [route.read(p)["stage"] for p in sorted(events.glob("stage-*.json"))]
            if stages != ["before_metadata","after_metadata","before_materialization_and_headers",
                          "after_materialization_and_headers","pair_headers","pixels_AOI-SOURCE","pixels_AOI-UPPER-CORRIDOR"]:
                raise RuntimeError("disposable_metadata_header_pixel_order_failed")
            # Only generated local sources are admitted to the selected-panel
            # wrapper; all production receipt and source access is replaced.
            with patch.object(route,"source_receipt",side_effect=loader):
                built = route.build_selected(pair,attempt,output/str(sensor),arcpy)
            if built["status"] != "pass_local_visual_panel_only":
                raise RuntimeError("disposable_panel_failed")
            project = arcpy.mp.ArcGISProject(str(output/str(sensor)/"Nepal_Landsat_Visual_Before_After_Local.aprx"))
            texts = " ".join(t.text for t in project.listLayouts()[0].listElements("TEXT_ELEMENT"))
            if not all(pair[role]["product_id"] in texts for role in ("before","after")) or "Landsat-9" in texts:
                raise RuntimeError("disposable_new_source_labels_failed")
            del project
            evidence.append({"sensor":sensor,"metadata_first_then_all_headers_then_pixels":True,
                             "both_aoi_paired_valid_fraction":1.,"fresh_reopen":built["reopened"],
                             "source_labels_exact":True,"qa_supervisor_terminal_and_cleanup_persisted":True,
                             "panel_sha256":built["built"]["png_sha256"]})
    result = {"status":"pass_disposable_installed_arcgis_alternate_route_synthetic",
              "arcgis_version":arcpy.GetInstallInfo()["Version"],"portable_tests_after_arcpy_import":tests.testsRun,
              "sensors":evidence,"project_data_or_external_custody_access":False,"provider_requests":0,
              "implementation_hashes":route.code_hashes()}
    route.write_new(output/"terminal.json",result)
    return result


if __name__ == "__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--output",required=True);args=parser.parse_args()
    try:
        print(json.dumps(main(Path(args.output)),sort_keys=True))
    except BaseException as exc:
        print(json.dumps({"status":"stopped","code":"disposable_arcgis_alternate_route_failed","exception_class":route.durable.safe_exception(exc)}))
        raise SystemExit(20)
