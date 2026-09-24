#!/usr/bin/env python3
"""Disposable ArcGIS check of an EPSG:32645 extent on broad EPSG:4326 input."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np


TARGET = (272300.0, 3069230.0, 368820.0, 3150210.0)
TEST_CELL_M = 50.0


def inspect(arcpy, path: Path) -> dict:
    d = arcpy.Describe(str(path))
    e = d.extent
    cells = int(d.width) * int(d.height)
    return {
        "wkid": int(d.spatialReference.factoryCode),
        "bounds": [float(e.XMin), float(e.YMin), float(e.XMax), float(e.YMax)],
        "width": int(d.width),
        "height": int(d.height),
        "cells": cells,
        "band_count": int(d.bandCount),
    }


def evaluate(output: dict, values: np.ndarray) -> dict:
    bounds = output["bounds"]
    margin = 100.0
    inside = all((bounds[0] >= TARGET[0] - margin,
                  bounds[1] >= TARGET[1] - margin,
                  bounds[2] <= TARGET[2] + margin,
                  bounds[3] <= TARGET[3] + margin))
    finite = values[np.isfinite(values)]
    pixels_ok = finite.size > 0 and np.any(np.isclose(finite, 7.0, atol=0.01))
    return {
        "status": "pass_disposable_crs_explicit_extent" if output["wkid"] == 32645 and output["cells"] <= 4000000 and inside and pixels_ok else "block_disposable_extent_not_proven",
        "output": output,
        "bounds_within_100_m_of_target": inside,
        "output_contains_expected_synthetic_value": bool(pixels_ok),
        "project_data_or_external_custody_accessed": False,
    }


def run() -> dict:
    import arcpy  # type: ignore

    stage = "temporary_directory"
    with tempfile.TemporaryDirectory(prefix="nepal-disposable-extent-", ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        source = root / "broad_4326.tif"
        destination = root / "bounded_32645.tif"
        stage = "create_synthetic_source"
        raster = arcpy.NumPyArrayToRaster(np.full((200, 200), 7, dtype=np.uint8), arcpy.Point(80.0, 10.0), 0.1, 0.1)
        raster.save(str(source))
        del raster
        arcpy.management.DefineProjection(str(source), arcpy.SpatialReference(4326))
        stage = "inspect_synthetic_source"
        source_info = inspect(arcpy, source)
        if source_info["wkid"] != 4326 or source_info["bounds"] != [80.0, 10.0, 100.0, 30.0] or source_info["cells"] != 40000:
            return {"status": "block_disposable_source_shape_invalid", "source": source_info}
        projected = arcpy.SpatialReference(32645)
        stage = "construct_crs_explicit_extent"
        extent = arcpy.Extent(*TARGET, spatial_reference=projected)
        stage = "project_synthetic_source"
        with arcpy.EnvManager(outputCoordinateSystem=projected, cellSize=TEST_CELL_M,
                              extent=extent, resamplingMethod="NEAREST", overwriteOutput=False):
            arcpy.management.ProjectRaster(str(source), str(destination), projected, "NEAREST", TEST_CELL_M)
        stage = "inspect_projected_output"
        output_info = inspect(arcpy, destination)
        stage = "read_synthetic_pixels"
        values = arcpy.RasterToNumPyArray(str(destination), nodata_to_value=255)
        result = evaluate(output_info, values)
        result["source"] = source_info
        result["arcgis_version"] = arcpy.GetInstallInfo().get("Version")
        result["test_cell_size_m"] = TEST_CELL_M
        result["target_bounds"] = list(TARGET)
        result["temporary_outputs_removed_on_exit"] = None
        return result


if __name__ == "__main__":
    try:
        result = run()
    except Exception as exc:
        result = {"status": "block_disposable_arcgis_exception", "failure_type": type(exc).__name__,
                  "failure_message": str(exc)[:200],
                  "project_data_or_external_custody_accessed": False}
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["status"] == "pass_disposable_crs_explicit_extent" else 20)
