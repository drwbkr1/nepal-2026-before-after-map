#!/usr/bin/env python3
"""Disposable full frozen route, new metadata adapter and supervisor test.

All inputs, controls, rasters and receipts are temporary synthetic files.
No production archive, AOI, attempt or external custody is opened.
"""
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import arcpy
import numpy as np
import run_m2_landsat9_visual_route_completion_001 as completion

sys.path.insert(0, str(completion.ROOT / "tests"))
from test_landsat9_visual_route_completion_001 import fixture_bytes, fixture_groups


def main():
    suite = unittest.TestSuite()
    for pattern in ("test_landsat9_visual_route_completion_001.py", "test_landsat9_pixel_visual_recovery_001.py"):
        suite.addTests(unittest.defaultTestLoader.discover(str(completion.ROOT / "tests"), pattern=pattern))
    tests = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
    if not tests.wasSuccessful():
        raise RuntimeError("disposable_completion_tests_failed")
    with tempfile.TemporaryDirectory(prefix="landsat9-completion-synthetic-", ignore_cleanup_errors=True) as temporary:
        root = Path(temporary)
        attempt, events, fallback = (root / name for name in ("attempt", "events", "fallback"))
        gate = root / "gate.json"
        payload = {"status": "pass_final_no_content_preflight", "approval_sha256": completion.APPROVAL_SHA,
                   "recovery_approval_sha256": completion.APPROVAL_SHA, "recovery_attempt_root_absent": True,
                   "independent_event_roots_absent": True, "implementation_hashes": completion.code_hashes(),
                   "implementation_public_ci_commit": "a" * 40, "implementation_public_ci_run_id": "12345678"}
        completion.write_new(gate, payload)
        aoi = root / "synthetic-aoi.json"
        ring = [[300030,3100030],[300120,3100030],[300120,3100120],[300030,3100120],[300030,3100030]]
        completion.write_new(aoi, {"features": [{"attributes": {"AOI_ID": key}, "geometry": {"rings": [ring]}}
                                               for key in ("AOI-SOURCE", "AOI-UPPER-CORRIDOR")]})
        order = []

        def extract(role, role_root):
            order.append(role)
            product, scene, *_ = completion.frozen.PRODUCTS[role]
            text, xml = fixture_bytes(fixture_groups(product, scene))
            paths = {}
            for suffix, raw in (("_MTL.txt", text), ("_MTL.xml", xml)):
                p = role_root / ("synthetic" + suffix); p.write_bytes(raw); paths[suffix] = p
            for name in completion.frozen.ROLES:
                suffix = "_" + name + ".TIF"
                array = np.full((5, 5), 20000 if name.startswith("SR_B") else (2 if name == "SR_QA_AEROSOL" else 0), dtype=np.uint16)
                if name.startswith("SR_B"):
                    array[1:4,1:4] += np.arange(9,dtype=np.uint16).reshape(3,3)*100
                path = role_root / ("synthetic" + suffix)
                arcpy.NumPyArrayToRaster(array, arcpy.Point(300000,3100000),30,30).save(str(path))
                arcpy.management.DefineProjection(str(path),arcpy.SpatialReference(32645))
                paths[suffix] = path
            return paths

        def worker(gate_path):
            with completion.binding(attempt), completion.supervisor_binding(), \
                    patch.object(completion.frozen, "_check_controls", return_value=None), \
                    patch.object(completion.frozen, "AOI", aoi), \
                    patch.object(completion.frozen, "extract_exact", side_effect=extract), \
                    completion.durable.worker_stage_markers(events):
                result = completion.frozen.run_once(payload, arcpy)
            return 0 if result["status"].startswith("pass_") else 20

        result = completion.supervise(gate, attempt=attempt, events=events, fallback=fallback, worker=worker)
        if result["status"] != "pass_local_arcgis_visual_panel_only" or order != ["before","after"]:
            raise RuntimeError("disposable_full_route_failed")
        terminal = json.loads((attempt / "terminal.json").read_text())
        qa = terminal["aoi_metrics"]
        if any(m["paired_strict_usable_fraction"] != 1 for m in qa.values()):
            raise RuntimeError("disposable_full_route_qa_failed")
        stages = [json.loads(p.read_text())["stage"] for p in sorted(events.glob("stage-*.json"))]
        if stages[:4] != ["before_materialization","before_headers","after_materialization","after_headers"]:
            raise RuntimeError("disposable_full_route_order_failed")
    return {"status": "pass_disposable_installed_arcgis_completion_synthetic", "arcgis_version": arcpy.GetInstallInfo()["Version"],
            "portable_tests_after_arcpy_import": tests.testsRun, "fixed_source_order": order,
            "full_frozen_route_with_grouped_metadata": True, "both_aoi_paired_valid_fraction": 1.,
            "fresh_process_reopen": True, "supervisor_cleanup_persisted": True,
            "project_data_or_external_custody_access": False}


if __name__ == "__main__":
    try:
        print(json.dumps(main(),sort_keys=True))
    except BaseException as exc:
        print(json.dumps({"status":"stopped","code":"arcgis_completion_synthetic_failed",
                          "exception_class":completion.durable.safe_exception(exc)},sort_keys=True))
        raise SystemExit(20)
