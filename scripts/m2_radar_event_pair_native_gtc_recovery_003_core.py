#!/usr/bin/env python3
"""Bounded native-grid and projection guards for the approved event-area pair.

This module is inert until called by the distinct recovery-003 runner. It never
opens project data, imports ArcPy, or creates an attempt by itself.
"""

from __future__ import annotations

import math
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable


TARGET = (272300.0, 3069230.0, 368820.0, 3150210.0)
TARGET_COLUMNS = 9652
TARGET_ROWS = 8098
NATIVE_MAX_DEGREES = 0.0002787777777777778
NATIVE_MAX_CELLS = 200_000_000
NATIVE_MAX_LOGICAL_BYTES = 2 * 1024**3
NATIVE_MAX_DISK_BYTES = 10 * 1024**3
PROJECTED_MAX_CELLS = 100_000_000
PROJECTED_MAX_DISK_BYTES = 10 * 1024**3
PROJECTED_MAX_EXTENSION_M = 100.0
ENVIRONMENT_NAMES = ("cellSize", "snapRaster", "outputCoordinateSystem", "extent")
PIXEL_BYTES = {"U1": 1, "S8": 1, "U8": 1, "S16": 2, "U16": 2,
               "S32": 4, "U32": 4, "F32": 4, "F64": 8}


class NativeGridStop(RuntimeError):
    """A deterministic stop before native save or projected acceptance."""


def _finite(value: Any, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise NativeGridStop(f"nonfinite_{name}") from exc
    if not math.isfinite(result):
        raise NativeGridStop(f"nonfinite_{name}")
    return result


def _positive_integer(value: Any, name: str) -> int:
    if isinstance(value, bool):
        raise NativeGridStop(f"invalid_{name}")
    try:
        result = int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise NativeGridStop(f"invalid_{name}") from exc
    if result <= 0 or result != value:
        raise NativeGridStop(f"invalid_{name}")
    return result


def _bounds(extent: Any) -> tuple[float, float, float, float]:
    value = tuple(_finite(getattr(extent, key, None), f"extent_{key}")
                  for key in ("XMin", "YMin", "XMax", "YMax"))
    if value[0] >= value[2] or value[1] >= value[3]:
        raise NativeGridStop("invalid_extent")
    return value


def positive_overlap(a: tuple[float, float, float, float],
                     b: tuple[float, float, float, float]) -> bool:
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def inspect_returned_raster(raster: Any, *, source_bounds: tuple[float, float, float, float],
                            aoi_bounds: tuple[tuple[float, float, float, float], ...]) -> dict[str, Any]:
    """Read every required native property before save; unknown is a hard stop."""
    try:
        wkid = _positive_integer(raster.spatialReference.factoryCode, "wkid")
        width = _positive_integer(raster.width, "width")
        height = _positive_integer(raster.height, "height")
        bands = _positive_integer(raster.bandCount, "band_count")
        cell_x = _finite(raster.meanCellWidth, "cell_x")
        cell_y = _finite(raster.meanCellHeight, "cell_y")
        bounds = _bounds(raster.extent)
        temporary = raster.isTemporary
        pixel_type = raster.pixelType
    except (AttributeError, RuntimeError) as exc:
        raise NativeGridStop("native_metadata_unavailable_before_save") from exc
    if not isinstance(temporary, bool) or not isinstance(pixel_type, str):
        raise NativeGridStop("native_metadata_unavailable_before_save")
    bytes_per_sample = PIXEL_BYTES.get(pixel_type.upper())
    if bytes_per_sample is None:
        raise NativeGridStop("native_pixel_type_unknown")
    cells = width * height
    logical_bytes = cells * bands * bytes_per_sample
    if wkid != 4326 or cell_x <= 0 or cell_y <= 0 or cell_x > NATIVE_MAX_DEGREES or cell_y > NATIVE_MAX_DEGREES:
        raise NativeGridStop("native_crs_or_cell_size_gross_screen_failed")
    if cells > NATIVE_MAX_CELLS or logical_bytes > NATIVE_MAX_LOGICAL_BYTES:
        raise NativeGridStop("native_declared_resource_limit_exceeded")
    if not positive_overlap(bounds, source_bounds) or not aoi_bounds or not all(
            positive_overlap(bounds, aoi) for aoi in aoi_bounds):
        raise NativeGridStop("native_source_or_event_aoi_overlap_missing")
    return {"wkid": wkid, "width": width, "height": height, "band_count": bands,
            "cell_size_x_degrees": cell_x, "cell_size_y_degrees": cell_y,
            "bounds": list(bounds), "is_temporary": temporary, "pixel_type": pixel_type,
            "declared_cells": cells, "declared_logical_bytes": logical_bytes,
            "native_effective_resolution_degrees": [cell_x, cell_y]}


@contextmanager
def native_gtc_environment(arcpy: Any, *, resampling: str,
                           record_environment: Callable[[dict[str, Any]], None]):
    """Hold the native settings through lazy metadata reads and the Raster save."""
    if resampling not in ("BILINEAR", "NEAREST"):
        raise NativeGridStop("invalid_gtc_resampling")
    prior = {name: getattr(arcpy.env, name) for name in ENVIRONMENT_NAMES}
    prior_resampling = arcpy.env.resamplingMethod
    try:
        for name in ENVIRONMENT_NAMES:
            arcpy.ClearEnvironment(name)
        arcpy.env.resamplingMethod = resampling
        cleared = {name: getattr(arcpy.env, name) for name in ENVIRONMENT_NAMES}
        changed = {name: prior[name] is None or str(cleared[name]) != str(prior[name])
                   for name in ENVIRONMENT_NAMES}
        if not all(changed.values()):
            raise NativeGridStop("native_environment_clear_not_effective")
        record_environment({"cleared": {name: None if value is None else str(value)
                                        for name, value in cleared.items()},
                            "prior_nondefault_cleared": changed, "resampling": resampling})
        yield
    finally:
        for name in ENVIRONMENT_NAMES:
            setattr(arcpy.env, name, prior[name])
        arcpy.env.resamplingMethod = prior_resampling


def native_gtc_call(arcpy: Any, function: Callable[..., Any], arguments: tuple[Any, ...],
                    *, resampling: str, record_environment: Callable[[dict[str, Any]], None]) -> Any:
    """Compatibility helper for eager call-only validation."""
    with native_gtc_environment(arcpy, resampling=resampling, record_environment=record_environment):
        return function(*arguments)


def dataset_bytes(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    if not path.is_dir():
        raise NativeGridStop("materialized_output_missing")
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def guard_materialized_size(path: Path, *, projected: bool) -> int:
    observed = dataset_bytes(path)
    cap = PROJECTED_MAX_DISK_BYTES if projected else NATIVE_MAX_DISK_BYTES
    if observed > cap:
        raise NativeGridStop("materialized_output_disk_limit_exceeded")
    return observed


def projected_grid_description(description: Any) -> dict[str, Any]:
    try:
        wkid = _positive_integer(description.spatialReference.factoryCode, "projected_wkid")
        width = _positive_integer(description.width, "projected_width")
        height = _positive_integer(description.height, "projected_height")
        cell_x = _finite(description.meanCellWidth, "projected_cell_x")
        cell_y = _finite(description.meanCellHeight, "projected_cell_y")
        bounds = _bounds(description.extent)
    except (AttributeError, RuntimeError) as exc:
        raise NativeGridStop("projected_metadata_unavailable") from exc
    if (wkid != 32645 or width * height > PROJECTED_MAX_CELLS
            or cell_x <= 0 or cell_y <= 0
            or bounds[0] < TARGET[0] - PROJECTED_MAX_EXTENSION_M
            or bounds[1] < TARGET[1] - PROJECTED_MAX_EXTENSION_M
            or bounds[2] > TARGET[2] + PROJECTED_MAX_EXTENSION_M
            or bounds[3] > TARGET[3] + PROJECTED_MAX_EXTENSION_M):
        raise NativeGridStop("projected_grid_resource_or_extent_limit_exceeded")
    return {"wkid": wkid, "width": width, "height": height, "cells": width * height,
            "cell_size_m": [cell_x, cell_y], "bounds": list(bounds),
            "target_bounds_m": list(TARGET), "target_columns": TARGET_COLUMNS,
            "target_rows": TARGET_ROWS}


def project_with_frozen_extent(arcpy: Any, source: Path, destination: Path,
                               snap: Path, *, categorical: bool) -> dict[str, Any]:
    """One CRS-bearing-extent ProjectRaster path, with no Clip or fallback."""
    crs = arcpy.SpatialReference(32645)
    extent = arcpy.Extent(*TARGET, spatial_reference=crs)
    method = "NEAREST" if categorical else "BILINEAR"
    with arcpy.EnvManager(outputCoordinateSystem=crs, snapRaster=str(snap), cellSize=10.0,
                          extent=extent, resamplingMethod=method, overwriteOutput=False):
        arcpy.management.ProjectRaster(str(source), str(destination), crs, method, 10.0)
    result = projected_grid_description(arcpy.Describe(str(destination)))
    result["materialized_disk_bytes"] = guard_materialized_size(destination, projected=True)
    result["resampling"] = method
    return result
