#!/usr/bin/env python3
"""Distinct disposable-002 test of the actual recovery-004 bridge function."""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import traceback
from pathlib import Path

from m2_radar_event_pair_gtc_tiff_warp_recovery_004_core import bridge_and_warp
from validate_m2_radar_event_pair_gtc_tiff_warp_recovery_004_arcgis import (
    ROOT, check_packet, broad_source_bounds, now_utc, write_new, write_reserved,
)


SCRATCH = ROOT / "scratch/m2-radar-event-area-pair-gtc-tiff-warp-recovery-004-disposable-002"
RECEIPT = ROOT / "records/readiness/m2-radar-event-area-pair-gtc-tiff-warp-recovery-004-arcgis-disposable-002.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run() -> dict:
    check_packet()
    if SCRATCH.exists() or RECEIPT.exists():
        raise RuntimeError("append_only_disposable_002_collision")
    SCRATCH.mkdir(parents=True, exist_ok=False)
    terminal_path = SCRATCH / "terminal.json"
    with terminal_path.open("xb") as stream:
        stream.flush()
        os.fsync(stream.fileno())
    write_new(SCRATCH / "started.json", {"status": "generated_core_disposable_started",
                                             "at_utc": now_utc(), "protected_data_accessed": False})
    stage = "arcgis_import"
    try:
        os.environ["PROJ_NETWORK"] = "OFF"
        os.environ["GDAL_PAM_ENABLED"] = "NO"
        import arcpy  # type: ignore
        import numpy as np  # type: ignore

        arcpy.env.overwriteOutput = False
        west, south, east, north = broad_source_bounds(arcpy)
        cell = .001
        cols = math.ceil((east-west)/cell)
        rows = math.ceil((north-south)/cell)
        if rows*cols > 2_000_000:
            raise RuntimeError("generated_core_source_cap")
        outputs = {}
        for name, categorical in (("continuous", False), ("categorical", True)):
            stage = f"generated_core_{name}"
            if categorical:
                values = np.ones((rows, cols), dtype=np.uint8)
                values[rows//3:rows//3+30, cols//3:cols//3+30] = 0
                values[rows//2:rows//2+30, cols//2:cols//2+30] = 3
                values[:5, :] = 255
                nodata = 255
            else:
                values = np.stack((np.full((rows, cols), 7.25, dtype=np.float32),
                                   np.full((rows, cols), 9.5, dtype=np.float32)))
                values[:, :5, :] = -9999
                nodata = -9999
            crf = SCRATCH / f"generated_{name}.crf"
            bridge = SCRATCH / f"bridge_{name}.tif"
            target = SCRATCH / f"projected_{name}.tif"
            if shutil.disk_usage(SCRATCH).free < 60 * 1024**3:
                raise RuntimeError("generated_core_space_gate")
            arcpy.NumPyArrayToRaster(values, arcpy.Point(west, south), cell, cell,
                                    value_to_nodata=nodata).save(str(crf))
            arcpy.management.DefineProjection(str(crf), arcpy.SpatialReference(4326))
            outputs[name] = bridge_and_warp(arcpy, crf, bridge, target,
                                            categorical=categorical)
            if outputs[name]["projected_center_valid_cells"] <= 0:
                raise RuntimeError("generated_core_center_coverage_missing")
        terminal = {"schema_version": "1.0", "status": "pass_generated_production_bridge_core_only",
                    "completed_at_utc": now_utc(), "arcgis_version": arcpy.GetInstallInfo().get("Version"),
                    "results": outputs,
                    "core_sha256": sha(ROOT / "scripts/m2_radar_event_pair_gtc_tiff_warp_recovery_004_core.py"),
                    "validator_sha256": sha(Path(__file__)),
                    "protected_data_accessed": False, "real_attempt_started": False,
                    "sar_fitness_proven": False, "baseline_or_change_analysis_executed": False}
    except BaseException as exc:
        frame = traceback.extract_tb(exc.__traceback__)[-1]
        code = str(exc) if type(exc) is RuntimeError else "disposable_core_exception"
        if len(code) > 80 or any(char in code for char in ("\\", "/", ":", "@")):
            code = "disposable_core_exception"
        terminal = {"schema_version": "1.0", "status": "block_generated_core_no_real_attempt",
                    "completed_at_utc": now_utc(), "last_stage": stage,
                    "failure_type": type(exc).__name__, "failure_code": code,
                    "failure_site": {"function": frame.name, "line": frame.lineno},
                    "protected_data_accessed": False, "real_attempt_started": False,
                    "sar_fitness_proven": False, "baseline_or_change_analysis_executed": False}
    write_reserved(terminal_path, terminal)
    write_new(RECEIPT, {"schema_version": "1.0", "status": terminal["status"],
                       "terminal_sha256": sha(terminal_path),
                       "core_sha256": sha(ROOT / "scripts/m2_radar_event_pair_gtc_tiff_warp_recovery_004_core.py"),
                       "validator_sha256": sha(Path(__file__)),
                       "protected_data_accessed": False, "real_attempt_started": False})
    return terminal


if __name__ == "__main__":
    result = run()
    print(json.dumps({"status": result["status"], "stage": result.get("last_stage", "completed")}))
    raise SystemExit(0 if result["status"] == "pass_generated_production_bridge_core_only" else 20)
