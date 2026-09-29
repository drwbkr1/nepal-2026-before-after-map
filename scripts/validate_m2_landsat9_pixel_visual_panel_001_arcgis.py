#!/usr/bin/env python3
"""Installed-ArcGIS disposable synthetic gate; never touches project data."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import arcpy  # type: ignore[import-not-found]
import numpy as np

from landsat9_pixel_visual_core_001 import validate_headers
from landsat9_visual_panel_arcgis_001 import build, fresh_reopen
from run_m2_landsat9_pixel_visual_panel_001 import raster_headers, read_aoi_date


def main() -> dict:
    # ArcGIS may retain a file-geodatabase lock until process teardown.
    with tempfile.TemporaryDirectory(prefix="landsat9-panel-synthetic-", ignore_cleanup_errors=True) as temporary:
        root = Path(temporary)
        paths = {}
        for role in ("QA_PIXEL", "QA_RADSAT", "SR_QA_AEROSOL", "SR_B3", "SR_B4", "SR_B5", "SR_B6", "SR_B7"):
            suffix = "_" + role + ".TIF"
            array = np.full((5, 5), 20000 if role.startswith("SR_B") else (2 if role == "SR_QA_AEROSOL" else 0), dtype=np.uint16)
            if role == "SR_B7":
                array[0, 0] = 21000
            path = root / ("synthetic" + suffix)
            arcpy.NumPyArrayToRaster(array, arcpy.Point(300000, 3100000), 30, 30).save(str(path))
            arcpy.management.DefineProjection(str(path), arcpy.SpatialReference(32645))
            paths[suffix] = path
        headers = raster_headers(paths, arcpy)
        grid = validate_headers({"before": headers, "after": headers})
        window = (300030., 3100120., 3, 3)
        values, footprint = read_aoi_date(paths, headers, window, arcpy)
        if not bool(footprint.all()) or not bool(values["strict_valid"].all()):
            raise ValueError("synthetic_pixel_gate_failed")
        attempt = root / "attempt"
        attempt.mkdir()
        bands = values["calibrated"][[4, 3, 1]].copy()
        bands[:, 0, 0] += .01
        np.savez_compressed(attempt / "aoi-source-panel-data.npz",
                            weights=np.full((3, 3), 900., dtype=np.float64),
                            before_reason=np.full((3, 3), 7, dtype=np.uint8),
                            after_reason=np.full((3, 3), 7, dtype=np.uint8),
                            before_bands=bands, after_bands=bands + .005,
                            xmin=window[0], ymax=window[1])
        metrics = {"AOI-SOURCE": {"visual_status": "pixel_qa_pass_for_visual_comparison_only",
                                   "before": {"footprint_fraction": 1., "strict_usable_fraction": 1.},
                                   "after": {"footprint_fraction": 1., "strict_usable_fraction": 1.},
                                   "paired_strict_usable_fraction": 1.},
                   "AOI-UPPER-CORRIDOR": {"visual_status": "no_visual_panel_for_aoi"}}
        data = {"AOI-SOURCE": {"npz": "aoi-source-panel-data.npz"}}
        mtls = {"before": {"date_acquired": "2026-08-10", "scene_center_time": "05:00:00Z"},
                "after": {"date_acquired": "2026-08-26", "scene_center_time": "05:00:00Z"}}
        source_bands = {date: {band: paths[f"_SR_{band}.TIF"] for band in ("B7", "B6", "B4")}
                        for date in ("before", "after")}
        built = build(attempt, metrics, data, mtls, source_bands, root / "panel", arcpy)
        reopened = fresh_reopen(root / "panel")
        if built["status"] != "built_visual_panel_pending_fresh_reopen" or reopened["status"] != "pass_fresh_process_reopen":
            raise ValueError("synthetic_panel_gate_failed")
        return {"status": "pass_disposable_installed_arcgis_synthetic",
                "arcgis_version": arcpy.GetInstallInfo()["Version"],
                "header_lattice": grid["after_offset_columns"],
                "pixel_valid_cells": int(values["strict_valid"].sum()),
                "panel_fresh_reopen": True}


if __name__ == "__main__":
    try:
        print(json.dumps(main(), sort_keys=True))
    except BaseException:
        print(json.dumps({"status": "stopped", "code": "arcgis_synthetic_validation_failed"}))
        raise
