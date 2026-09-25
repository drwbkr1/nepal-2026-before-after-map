"""Pure grid guards and one coverage-verified projected Clip method.

Importing this module cannot read project data, import ArcPy, or start an attempt.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Callable


TARGET = (272300.0, 3069230.0, 368820.0, 3150210.0)
TARGET_COLUMNS = 9652
TARGET_ROWS = 8098
CELL_M = 10.0
MAX_INTERMEDIATE_CELLS = 100_000_000
MAX_INTERMEDIATE_EXTENSION_M = 2000.0
MAX_FINAL_EXTENSION_M = 100.0
MAX_SINGLE_OUTPUT_BYTES = 10 * 1024**3
TOLERANCE_M = 1e-6


class MapRouteStop(RuntimeError):
    """A named, nonsecret stop before an invalid grid can be used."""


def _number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise MapRouteStop("grid_metadata_invalid")
    return float(value)


def _positive_int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise MapRouteStop("grid_metadata_invalid")
    return value


def _description(info: dict[str, Any], *, expected_bands: int) -> tuple[tuple[float, float, float, float], int]:
    try:
        wkid = _positive_int(info["wkid"])
        width = _positive_int(info["width"])
        height = _positive_int(info["height"])
        bands = _positive_int(info["band_count"])
        cell_x = _number(info["cell_size_x"])
        cell_y = _number(info["cell_size_y"])
        bounds = tuple(_number(value) for value in info["bounds"])
    except (KeyError, TypeError, ValueError) as exc:
        raise MapRouteStop("grid_metadata_invalid") from exc
    if (len(bounds) != 4 or wkid != 32645 or bands != expected_bands
            or abs(cell_x - CELL_M) > TOLERANCE_M or abs(cell_y - CELL_M) > TOLERANCE_M
            or bounds[0] >= bounds[2] or bounds[1] >= bounds[3]
            or abs((bounds[2] - bounds[0]) - width * CELL_M) > TOLERANCE_M
            or abs((bounds[3] - bounds[1]) - height * CELL_M) > TOLERANCE_M):
        raise MapRouteStop("grid_crs_cell_band_or_dimensions_drift")
    for origin, anchor in ((bounds[0], TARGET[0]), (bounds[1], TARGET[1])):
        offset = (origin - anchor) / CELL_M
        if abs(offset - round(offset)) > TOLERANCE_M:
            raise MapRouteStop("grid_snap_alignment_missing")
    return bounds, width * height


def check_intermediate(info: dict[str, Any], *, expected_bands: int) -> dict[str, Any]:
    bounds, cells = _description(info, expected_bands=expected_bands)
    if cells > MAX_INTERMEDIATE_CELLS:
        raise MapRouteStop("intermediate_cell_ceiling_exceeded")
    if (bounds[0] > TARGET[0] + TOLERANCE_M or bounds[1] > TARGET[1] + TOLERANCE_M
            or bounds[2] < TARGET[2] - TOLERANCE_M or bounds[3] < TARGET[3] - TOLERANCE_M):
        raise MapRouteStop("intermediate_does_not_cover_frozen_target")
    extension = (TARGET[0] - bounds[0], TARGET[1] - bounds[1],
                 bounds[2] - TARGET[2], bounds[3] - TARGET[3])
    if any(value > MAX_INTERMEDIATE_EXTENSION_M + TOLERANCE_M for value in extension):
        raise MapRouteStop("intermediate_extension_above_2000_m")
    return {"bounds": list(bounds), "cells": cells, "extension_each_side_m": list(extension),
            "covers_frozen_target": True}


def check_final(info: dict[str, Any], *, expected_bands: int) -> dict[str, Any]:
    bounds, cells = _description(info, expected_bands=expected_bands)
    if any(abs(bounds[index] - TARGET[index]) > MAX_FINAL_EXTENSION_M for index in range(4)):
        raise MapRouteStop("final_extent_above_100_m_guard")
    if (info["width"] != TARGET_COLUMNS or info["height"] != TARGET_ROWS
            or any(abs(bounds[index] - TARGET[index]) > TOLERANCE_M for index in range(4))):
        raise MapRouteStop("final_grid_not_exact_frozen_target")
    return {"bounds": list(bounds), "cells": cells, "exact_frozen_grid": True}


def output_bytes(path: Path) -> int:
    if path.is_file():
        size = path.stat().st_size
    elif path.is_dir():
        size = sum(item.stat().st_size for item in path.rglob("*") if item.is_file())
    else:
        raise MapRouteStop("materialized_grid_missing")
    if size > MAX_SINGLE_OUTPUT_BYTES:
        raise MapRouteStop("single_output_above_10_gib")
    return size


def describe(arcpy: Any, path: Path) -> dict[str, Any]:
    raster = arcpy.Raster(str(path))
    extent = raster.extent
    return {
        "wkid": int(raster.spatialReference.factoryCode),
        "bounds": [float(extent.XMin), float(extent.YMin), float(extent.XMax), float(extent.YMax)],
        "width": int(raster.width), "height": int(raster.height),
        "band_count": int(raster.bandCount),
        "cell_size_x": float(raster.meanCellWidth), "cell_size_y": float(raster.meanCellHeight),
    }


def project_then_clip(arcpy: Any, source: Path, intermediate: Path, final: Path,
                      snap: Path, *, categorical: bool, expected_bands: int,
                      before_materialization: Callable[[str], None] | None = None) -> dict[str, Any]:
    """Project once; stop unless it covers the target; Clip once without resampling."""
    if intermediate.exists() or final.exists():
        raise MapRouteStop("projected_output_collision")
    crs = arcpy.SpatialReference(32645)
    extent = arcpy.Extent(*TARGET, spatial_reference=crs)
    method = "NEAREST" if categorical else "BILINEAR"
    if before_materialization is not None:
        before_materialization("ProjectRaster")
    with arcpy.EnvManager(outputCoordinateSystem=crs, snapRaster=str(snap), cellSize=CELL_M,
                          extent=extent, resamplingMethod=method, overwriteOutput=False):
        arcpy.management.ProjectRaster(str(source), str(intermediate), crs, method, CELL_M)
    intermediate_info = describe(arcpy, intermediate)
    intermediate_gate = check_intermediate(intermediate_info, expected_bands=expected_bands)
    intermediate_size = output_bytes(intermediate)
    rectangle = " ".join(str(value) for value in TARGET)
    if before_materialization is not None:
        before_materialization("Clip")
    with arcpy.EnvManager(outputCoordinateSystem=crs, snapRaster=str(snap), cellSize=CELL_M,
                          extent=extent, resamplingMethod=method, overwriteOutput=False):
        arcpy.management.Clip(str(intermediate), rectangle, str(final), "#", "#", "NONE", "NO_MAINTAIN_EXTENT")
    final_info = describe(arcpy, final)
    final_gate = check_final(final_info, expected_bands=expected_bands)
    final_size = output_bytes(final)
    return {
        "resampling": method,
        "clip_mode": "NO_MAINTAIN_EXTENT",
        "intermediate": {**intermediate_info, **intermediate_gate, "materialized_disk_bytes": intermediate_size},
        "final": {**final_info, **final_gate, "materialized_disk_bytes": final_size},
    }
