#!/usr/bin/env python3
"""Generated-raster ArcGIS validation for the approved projected-clip proposal."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np

from m2_radar_event_pair_projected_clip_recovery_002_core import (
    TARGET, check_final, check_intermediate,
)


SNAP_ORIGIN = (TARGET[0], TARGET[1])
STAGES = (("coarse", 50.0, TARGET), ("window_10m", 10.0, (300000.0, 3100000.0, 301000.0, 3101000.0)))


def describe(arcpy, path: Path) -> dict:
    item = arcpy.Raster(str(path))
    extent = item.extent
    return {
        "wkid": int(item.spatialReference.factoryCode),
        "bounds": [float(extent.XMin), float(extent.YMin), float(extent.XMax), float(extent.YMax)],
        "width": int(item.width),
        "height": int(item.height),
        "band_count": int(item.bandCount),
        "cell_size_x": float(item.meanCellWidth),
        "cell_size_y": float(item.meanCellHeight),
    }


def _save_generated(arcpy, root: Path) -> dict[str, Path]:
    columns = np.arange(200, dtype=np.float32)[None, :]
    rows = np.arange(200, dtype=np.float32)[:, None]
    continuous = np.stack((7.0 + rows * 0.01 + columns * 0.001,
                           9.0 + rows * 0.002 + columns * 0.01)).astype(np.float32)
    mask = np.array((1, 2, 3, 4, 5, 0), dtype=np.uint8)[(np.arange(200)[:, None] // 3 + np.arange(200)[None, :] // 3) % 6]
    output: dict[str, Path] = {}
    for name, array in (("continuous", continuous), ("mask", mask)):
        path = root / f"generated_{name}_4326.tif"
        raster = arcpy.NumPyArrayToRaster(array, arcpy.Point(80.0, 10.0), 0.1, 0.1)
        raster.save(str(path))
        del raster
        arcpy.management.DefineProjection(str(path), arcpy.SpatialReference(4326))
        info = describe(arcpy, path)
        if info["wkid"] != 4326 or info["bounds"] != [80.0, 10.0, 100.0, 30.0] or info["width"] != 200 or info["height"] != 200:
            raise ValueError("generated_source_shape_invalid")
        output[name] = path
    return output


def _compare_retained(arcpy, intermediate: Path, final: Path, final_info: dict, *, categorical: bool) -> dict:
    nodata = 255 if categorical else -9999.0
    final_values = arcpy.RasterToNumPyArray(str(final), nodata_to_value=nodata)
    projected_values = arcpy.RasterToNumPyArray(
        str(intermediate), lower_left_corner=arcpy.Point(final_info["bounds"][0], final_info["bounds"][1]),
        ncols=final_info["width"], nrows=final_info["height"], nodata_to_value=nodata,
    )
    same = final_values.shape == projected_values.shape and bool(np.array_equal(final_values, projected_values))
    if categorical:
        values = np.unique(final_values)
        valid = values[values != 255]
        classes_ok = valid.size >= 2 and set(map(int, valid)).issubset({0, 1, 2, 3, 4, 5})
    else:
        classes_ok = bool(np.any(final_values != nodata))
    return {"array_shape": list(final_values.shape), "retained_pixels_identical": same,
            "synthetic_values_or_mask_classes_valid": classes_ok}


def _stage(arcpy, root: Path, sources: dict[str, Path], *, stage: str, cell_m: float,
           target: tuple[float, float, float, float]) -> dict:
    projected = arcpy.SpatialReference(32645)
    snap = root / f"snap_{stage}.tif"
    snap_raster = arcpy.NumPyArrayToRaster(np.zeros((2, 2), dtype=np.uint8), arcpy.Point(*SNAP_ORIGIN), cell_m, cell_m)
    snap_raster.save(str(snap))
    del snap_raster
    arcpy.management.DefineProjection(str(snap), projected)
    extent = arcpy.Extent(*target, spatial_reference=projected)
    results = {}
    for name, categorical, bands in (("continuous", False, 2), ("mask", True, 1)):
        intermediate = root / f"{name}_{stage}_intermediate.tif"
        final = root / f"{name}_{stage}_clipped.tif"
        method = "NEAREST" if categorical else "BILINEAR"
        with arcpy.EnvManager(outputCoordinateSystem=projected, snapRaster=str(snap), cellSize=cell_m,
                              extent=extent, resamplingMethod=method, overwriteOutput=False):
            arcpy.management.ProjectRaster(str(sources[name]), str(intermediate), projected, method, cell_m)
        intermediate_info = describe(arcpy, intermediate)
        errors = check_intermediate(intermediate_info, target=target, cell_m=cell_m, bands=bands,
                                    logical_bytes=intermediate.stat().st_size)
        results[name] = {"intermediate": intermediate_info, "intermediate_errors": errors}
        if errors:
            return {"status": "block_disposable_intermediate", "stage": stage, "results": results}
        rectangle = " ".join(str(value) for value in target)
        with arcpy.EnvManager(outputCoordinateSystem=projected, snapRaster=str(snap), cellSize=cell_m,
                              overwriteOutput=False):
            arcpy.management.Clip(str(intermediate), rectangle, str(final), "#", "#", "NONE", "NO_MAINTAIN_EXTENT")
        final_info = describe(arcpy, final)
        final_errors = check_final(final_info, target=target, cell_m=cell_m, bands=bands, snap_origin=SNAP_ORIGIN)
        comparison = _compare_retained(arcpy, intermediate, final, final_info, categorical=categorical)
        results[name].update({"final": final_info, "final_errors": final_errors, "comparison": comparison})
        if final_errors or not comparison["retained_pixels_identical"] or not comparison["synthetic_values_or_mask_classes_valid"]:
            return {"status": "block_disposable_final", "stage": stage, "results": results}
    return {"status": "pass_disposable_stage", "stage": stage, "results": results}


def run() -> dict:
    import arcpy  # type: ignore

    stage = "create_generated_inputs"
    root: Path | None = None
    result: dict = {"status": "block_disposable_unknown"}
    try:
        with tempfile.TemporaryDirectory(prefix="nepal-projected-clip-002-", ignore_cleanup_errors=True) as temp:
            root = Path(temp)
            sources = _save_generated(arcpy, root)
            stages = []
            for name, cell_m, target in STAGES:
                stage = name
                item = _stage(arcpy, root, sources, stage=name, cell_m=cell_m, target=target)
                stages.append(item)
                if item["status"] != "pass_disposable_stage":
                    break
            result = {"status": "pass_disposable_projected_clip" if len(stages) == len(STAGES) and all(x["status"] == "pass_disposable_stage" for x in stages) else "block_disposable_projected_clip",
                      "arcgis_version": arcpy.GetInstallInfo().get("Version"), "stages": stages,
                      "project_data_or_external_custody_accessed": False}
    except Exception as exc:
        result = {"status": "block_disposable_exception", "stage": stage, "failure_type": type(exc).__name__,
                  "failure_message": str(exc).replace(str(root), "[DISPOSABLE_ROOT]")[:200] if root is not None else type(exc).__name__,
                  "project_data_or_external_custody_accessed": False}
    result["temporary_directory_removed"] = root is not None and not root.exists()
    return result


if __name__ == "__main__":
    outcome = run()
    print(json.dumps(outcome, sort_keys=True))
    raise SystemExit(0 if outcome["status"] == "pass_disposable_projected_clip" else 20)
