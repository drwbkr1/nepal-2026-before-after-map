#!/usr/bin/env python3
"""Disposable ArcGIS-runtime adapter test; never reads project imagery."""

from __future__ import annotations

import json
import gc
import tempfile
from pathlib import Path

import arcpy  # type: ignore[import-not-found]
import numpy as np

from optical_pixel_readiness_core_001 import classify_pair_pixels
from run_m2_optical_pixel_readiness_001 import read_target


def main() -> int:
    if arcpy.CheckExtension("Spatial") != "Available":
        raise RuntimeError("Spatial Analyst is unavailable")
    with tempfile.TemporaryDirectory(prefix="nepal-optical-pilot-synthetic-") as folder:
        root = Path(folder)
        cell = 20.0
        grid = {"xmin": 300000.0, "ymin": 3100000.0, "xmax": 301000.0, "ymax": 3101000.0,
                "cell_size_m": cell, "rows": 50, "columns": 50}
        b11 = (np.arange(2500, dtype=np.uint16).reshape(50, 50) + 100).astype(np.uint16)
        scl = np.full((50, 50), 4, dtype=np.uint8)
        quality = np.zeros((3, 50, 50), dtype=np.uint8)
        quality[0, 0, 0] = 1
        arrays = {"B11": b11, "SCL": scl, "quality": quality}
        paths = {}
        for role, array in arrays.items():
            path = root / f"{role}.tif"
            raster = arcpy.NumPyArrayToRaster(array, arcpy.Point(grid["xmin"], grid["ymin"]), cell, cell)
            raster.save(str(path))
            arcpy.management.DefineProjection(str(path), arcpy.SpatialReference(32645))
            paths[role] = path
        observed = {
            "B11": read_target(arcpy, paths["B11"], grid, 65535),
            "SCL": read_target(arcpy, paths["SCL"], grid, 255),
            "quality": read_target(arcpy, paths["quality"], grid, 255),
        }
        if any(observed[key].shape != value.shape or not np.array_equal(observed[key], value) for key, value in arrays.items()):
            raise RuntimeError("ArcGIS target read differs from disposable generated arrays")
        classified = classify_pair_pixels(
            observed["SCL"], observed["SCL"], observed["quality"], observed["quality"],
            observed["B11"], observed["B11"],
        )
        if int(classified["pair_valid"].sum()) != 2499 or int(classified["classes"][0, 0]) != 300:
            raise RuntimeError("ArcGIS-array mask classification differs")
        del raster
        gc.collect()
        arcpy.ClearWorkspaceCache_management()
        for path in paths.values():
            arcpy.management.Delete(str(path))
    print(json.dumps({
        "status": "pass_disposable_arcgis_runtime_only",
        "arcgis_version": arcpy.GetInstallInfo().get("Version"),
        "grid_wkid": 32645,
        "synthetic_rows": 50,
        "synthetic_columns": 50,
        "source_or_external_custody_accessed": False,
        "real_product_pixels_examined": False,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
