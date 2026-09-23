#!/usr/bin/env python3
"""Disposable installed ArcGIS eleven-input mosaic orchestration test."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np

import m2_radar_event_pair_dem_mosaic_001 as route


def main() -> int:
    import arcpy  # type: ignore

    with tempfile.TemporaryDirectory(prefix="nepal-event-pair-mosaic-synthetic-") as temporary:
        root = Path(temporary)
        inputs = []
        for index in range(11):
            path = root / f"tile-{index:02d}.tif"
            raster = arcpy.NumPyArrayToRaster(
                np.full((2, 2), float(index + 1), dtype=np.float32),
                arcpy.Point(86.0, 27.0), 0.5, 0.5,
            )
            raster.save(str(path))
            arcpy.management.DefineProjection(str(path), arcpy.SpatialReference(4326))
            raster = None
            inputs.append(path)
        output_root = root / "mosaic-attempt"
        with (
            patch.object(route, "exact_mosaic_inputs", return_value=inputs),
            patch.object(route, "MOSAIC_ROOT", output_root),
            patch.object(route, "MOSAIC", output_root / "ellipsoidal_dem_mosaic.tif"),
            patch.object(route, "TERMINAL", output_root / "terminal.json"),
            patch.object(route, "ERROR", output_root / "error.json"),
            patch.object(route, "CLEANUP", output_root / "cleanup.json"),
        ):
            result = route.build_mosaic(arcpy_module=arcpy)
            if result["status"] != "pass_mosaic_created_pending_actual_sar_extent_and_valid_elevation_gate":
                raise ValueError("disposable eleven-input mosaic failed")
            if arcpy.Raster(str(route.MOSAIC)).bandCount != 1:
                raise ValueError("synthetic mosaic band count differs")
            output_sha = result["output_sha256"]
    print(json.dumps({"status": "pass_disposable_eleven_input_mosaic", "arcgis_version": arcpy.GetInstallInfo().get("Version"), "input_count": 11, "synthetic_output_sha256": output_sha}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
