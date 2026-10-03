#!/usr/bin/env python3
"""Disposable installed-ArcGIS supervisor and frozen visual-method validation."""
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

import arcpy  # type: ignore[import-not-found]

import run_m2_landsat9_pixel_visual_recovery_001 as recovery
import validate_m2_landsat9_pixel_visual_panel_001_arcgis as fixture


def main():
    suite = unittest.defaultTestLoader.discover(str(recovery.ROOT / "tests"),
                                               pattern="test_landsat9_pixel_visual_recovery_001.py")
    result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
    if not result.wasSuccessful():
        raise RuntimeError("disposable_supervisor_tests_failed")
    with tempfile.TemporaryDirectory(prefix="landsat9-recovery-synthetic-") as temporary:
        root = Path(temporary)
        gate = root / "gate.json"
        recovery.write_new(gate, {
            "status": "pass_final_no_content_preflight", "recovery_approval_sha256": recovery.APPROVAL_SHA,
            "recovery_attempt_root_absent": True, "independent_event_roots_absent": True,
            "implementation_public_ci_commit": "a" * 40,
            "implementation_public_ci_run_id": "12345678"})
        observed = {}
        def worker(gate_path):
            observed.update(fixture.main())
            attempt = root / "attempt"
            attempt.mkdir()
            recovery.write_new(attempt / "terminal.json", {"status": "pass_local_arcgis_visual_panel_only"})
            return 0
        supervision = recovery.supervise(gate, attempt=root / "attempt", events=root / "events",
                                        fallback=root / "fallback", worker=worker)
        if supervision["status"] != "pass_local_arcgis_visual_panel_only":
            raise RuntimeError("disposable_supervisor_runtime_failed")
    return {"status": "pass_disposable_installed_arcgis_recovery_synthetic",
            "arcgis_version": arcpy.GetInstallInfo()["Version"], "supervisor_tests": result.testsRun,
            "frozen_method_fixture": observed, "supervisor_cleanup_persisted": True,
            "project_data_or_external_custody_access": False}


if __name__ == "__main__":
    try:
        print(json.dumps(main(), sort_keys=True))
    except BaseException as exc:
        print(json.dumps({"status": "stopped", "code": "arcgis_recovery_synthetic_failed",
                          "exception_class": recovery.safe_exception(exc)}, sort_keys=True))
        sys.exit(20)
