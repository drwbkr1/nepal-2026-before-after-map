#!/usr/bin/env python3
"""Inert, source-free guards for the approved recovery-004 raster bridge.

Importing this module never imports ArcPy/GDAL or accesses project custody.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any


TARGET = (272300.0, 3069230.0, 368820.0, 3150210.0)
WIDTH = 9652
HEIGHT = 8098
MAX_PROJECTED_CELLS = 100_000_000
MAX_OUTPUT_BYTES = 10 * 1024**3
MIN_FREE_BYTES = 60 * 1024**3


class BridgeStop(RuntimeError):
    """Stop before accepting a materialized bridge or projected raster."""


def check_free_bytes(free_bytes: int, next_logical_bytes: int) -> None:
    if (not isinstance(free_bytes, int) or not isinstance(next_logical_bytes, int)
            or next_logical_bytes <= 0 or free_bytes < max(MIN_FREE_BYTES, 2 * next_logical_bytes)):
        raise BridgeStop("insufficient_materialization_free_space")


def check_bridge_metadata(before: dict[str, Any], after: dict[str, Any]) -> None:
    """Check declared properties; pixel equality must be checked separately."""
    required = ("wkid", "width", "height", "bands", "pixel_type", "nodata")
    if any(key not in before or key not in after for key in required):
        raise BridgeStop("bridge_metadata_missing")
    if any(before[key] != after[key] for key in required):
        raise BridgeStop("bridge_metadata_changed")
    for key in ("transform", "bounds"):
        left, right = before.get(key), after.get(key)
        if (not isinstance(left, (list, tuple)) or not isinstance(right, (list, tuple))
                or len(left) != len(right) or len(left) not in (4, 6)):
            raise BridgeStop("bridge_georeference_missing")
        try:
            identical = all(math.isfinite(float(a)) and math.isfinite(float(b))
                            and abs(float(a) - float(b)) <= 1e-9 for a, b in zip(left, right))
        except (ValueError, TypeError, OverflowError):
            identical = False
        if not identical:
            raise BridgeStop("bridge_georeference_changed")


def check_full_pixels(before: Any, after: Any, *, categorical: bool) -> dict[str, Any]:
    """Compare complete generated arrays, including NoData and valid zero mask class."""
    import numpy as np  # imported only when invoked

    left, right = np.asarray(before), np.asarray(after)
    if left.shape != right.shape or left.dtype != right.dtype or not np.array_equal(left, right, equal_nan=True):
        raise BridgeStop("bridge_full_pixels_changed")
    if categorical:
        classes = {int(item) for item in np.unique(right)}
        if not {0, 1, 3, 255}.issubset(classes):
            raise BridgeStop("bridge_mask_classes_missing")
    else:
        valid = right[right != -9999.0]
        if valid.size == 0 or not np.isfinite(valid).all():
            raise BridgeStop("bridge_finite_values_missing")
    return {"full_pixel_array_equal": True, "shape": list(left.shape),
            "dtype": str(left.dtype), "categorical_zero_retained": categorical}


def check_projected_grid(dataset: Any, *, expected_bands: int) -> dict[str, Any]:
    """Exact GDAL grid guard; the output frame is never counted as coverage."""
    if dataset is None:
        raise BridgeStop("projected_output_missing")
    if (dataset.RasterXSize != WIDTH or dataset.RasterYSize != HEIGHT
            or dataset.RasterCount != expected_bands
            or dataset.RasterXSize * dataset.RasterYSize > MAX_PROJECTED_CELLS):
        raise BridgeStop("projected_shape_or_band_mismatch")
    expected = (TARGET[0], 10.0, 0.0, TARGET[3], 0.0, -10.0)
    transform = dataset.GetGeoTransform()
    if len(transform) != 6 or any(abs(float(a) - b) > 1e-7 for a, b in zip(transform, expected)):
        raise BridgeStop("projected_transform_mismatch")
    from osgeo import osr  # imported only when invoked

    spatial = osr.SpatialReference(wkt=dataset.GetProjection())
    expected_srs = osr.SpatialReference()
    expected_srs.ImportFromEPSG(32645)
    spatial.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    expected_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    if not spatial.IsSame(expected_srs, ["IGNORE_DATA_AXIS_TO_SRS_AXIS_MAPPING=YES"]):
        raise BridgeStop("projected_crs_mismatch")
    return {"wkid": 32645, "width": WIDTH, "height": HEIGHT,
            "bands": expected_bands, "transform": list(expected),
            "frame_is_coverage_proof": False}


def check_output_size(path: Path) -> int:
    if not path.is_file():
        raise BridgeStop("materialized_output_missing")
    size = path.stat().st_size
    if size <= 0 or size > MAX_OUTPUT_BYTES:
        raise BridgeStop("materialized_output_size_limit")
    return size


def arc_raster_metadata(arcpy: Any, path: Path) -> dict[str, Any]:
    raster = arcpy.Raster(str(path))
    extent = raster.extent
    x, y = float(raster.meanCellWidth), float(raster.meanCellHeight)
    nodata = raster.noDataValue
    if nodata is None or not math.isfinite(float(nodata)):
        raise BridgeStop("native_nodata_missing")
    return {"wkid": int(raster.spatialReference.factoryCode),
            "width": int(raster.width), "height": int(raster.height),
            "bands": int(raster.bandCount), "pixel_type": str(raster.pixelType),
            "nodata": nodata,
            "transform": [float(extent.XMin), x, 0.0, float(extent.YMax), 0.0, -y],
            "bounds": [float(extent.XMin), float(extent.YMin),
                       float(extent.XMax), float(extent.YMax)]}


def _sample_window(arcpy: Any, path: Path, metadata: dict[str, Any],
                   xoff: int, yoff: int, size: int) -> Any:
    x, dx, _, ymax, _, negative_dy = metadata["transform"]
    lower_left = arcpy.Point(x + xoff * dx, ymax + (yoff + size) * negative_dy)
    return arcpy.RasterToNumPyArray(str(path), lower_left_corner=lower_left,
                                    ncols=size, nrows=size,
                                    nodata_to_value=metadata["nodata"])


def bridge_and_warp(arcpy: Any, native_crf: Path, tiff: Path, projected: Path,
                    *, categorical: bool) -> dict[str, Any]:
    """One strictly checked real bridge and exact Warp; no alternate projection."""
    import shutil
    import numpy as np

    from m2_radar_event_pair_native_gtc_recovery_003_core import guard_materialized_size

    if tiff.exists() or projected.exists():
        raise BridgeStop("bridge_or_projected_output_collision")
    before = arc_raster_metadata(arcpy, native_crf)
    if before["wkid"] != 4326 or before["bands"] != (1 if categorical else 2):
        raise BridgeStop("native_bridge_crs_or_band_mismatch")
    if categorical and before["nodata"] in (0, 1, 2, 3, 4, 5):
        raise BridgeStop("categorical_nodata_collides_with_mask_class")
    pixel_bytes = {"U8": 1, "U16": 2, "S16": 2, "F32": 4, "F64": 8}
    bytes_per_sample = pixel_bytes.get(before["pixel_type"].upper())
    if bytes_per_sample is None:
        raise BridgeStop("native_bridge_pixel_type_unknown")
    native_logical = before["width"] * before["height"] * before["bands"] * bytes_per_sample
    check_free_bytes(shutil.disk_usage(tiff.parent).free, native_logical)
    arcpy.management.CopyRaster(str(native_crf), str(tiff), format="TIFF")
    if check_output_size(tiff) > MAX_OUTPUT_BYTES:
        raise BridgeStop("bridge_disk_limit_exceeded")
    after = arc_raster_metadata(arcpy, tiff)
    check_bridge_metadata(before, after)
    size = min(128, before["width"], before["height"])
    if size <= 0:
        raise BridgeStop("native_bridge_empty")
    positions = {(0, 0), ((before["width"] - size)//2, (before["height"] - size)//2),
                 (before["width"] - size, before["height"] - size)}
    arc_windows = []
    for xoff, yoff in sorted(positions):
        left = _sample_window(arcpy, native_crf, before, xoff, yoff, size)
        right = _sample_window(arcpy, tiff, before, xoff, yoff, size)
        if np.asarray(left).shape != np.asarray(right).shape or not np.array_equal(left, right, equal_nan=True):
            raise BridgeStop("bridge_sampled_pixels_changed")
        arc_windows.append((xoff, yoff, left))
    # GDAL never sees the copy until ArcPy's metadata and value checks pass.
    from osgeo import gdal, osr  # type: ignore

    gdal.UseExceptions()
    gdal.SetConfigOption("PROJ_NETWORK", "OFF")
    source = gdal.OpenEx(str(tiff), gdal.OF_RASTER | gdal.OF_READONLY)
    if source is None or source.GetDriver().ShortName != "GTiff":
        raise BridgeStop("bridge_gdal_tiff_unreadable")
    try:
        if (source.RasterXSize, source.RasterYSize, source.RasterCount) != (
                before["width"], before["height"], before["bands"]):
            raise BridgeStop("bridge_gdal_shape_changed")
        sr = osr.SpatialReference(wkt=source.GetProjection())
        expected_srs = osr.SpatialReference()
        expected_srs.ImportFromEPSG(4326)
        sr.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        expected_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        if not sr.IsSame(expected_srs, ["IGNORE_DATA_AXIS_TO_SRS_AXIS_MAPPING=YES"]) or any(
                abs(a-b) > 1e-9 for a, b in zip(source.GetGeoTransform(), before["transform"])):
            raise BridgeStop("bridge_gdal_georeference_changed")
        if any(source.GetRasterBand(n).GetNoDataValue() != before["nodata"]
               for n in range(1, before["bands"] + 1)):
            raise BridgeStop("bridge_gdal_nodata_changed")
        for xoff, yoff, left in arc_windows:
            bands = [source.GetRasterBand(n).ReadAsArray(xoff, yoff, size, size)
                     for n in range(1, before["bands"] + 1)]
            right = bands[0] if len(bands) == 1 else np.stack(bands)
            if np.asarray(left).shape != np.asarray(right).shape or not np.array_equal(left, right, equal_nan=True):
                raise BridgeStop("bridge_gdal_sampled_pixels_changed")
        projected_logical = WIDTH * HEIGHT * before["bands"] * bytes_per_sample
        check_free_bytes(shutil.disk_usage(projected.parent).free, projected_logical)
        result = gdal.Warp(
            str(projected), source, format="GTiff", outputBounds=TARGET,
            width=WIDTH, height=HEIGHT, dstSRS="EPSG:32645",
            resampleAlg="near" if categorical else "bilinear",
            srcNodata=before["nodata"], dstNodata=before["nodata"],
            creationOptions=["TILED=YES", "COMPRESS=LZW", "BIGTIFF=IF_SAFER"],
            multithread=False, warpMemoryLimit=256 * 1024 * 1024,
        )
        try:
            grid = check_projected_grid(result, expected_bands=before["bands"])
            if any(result.GetRasterBand(n).GetNoDataValue() != before["nodata"]
                   for n in range(1, before["bands"] + 1)):
                raise BridgeStop("projected_nodata_changed")
            center = result.GetRasterBand(1).ReadAsArray(WIDTH//2-64, HEIGHT//2-64, 128, 128)
            valid = np.isfinite(center) & (center != before["nodata"])
            if categorical and any(int(v) not in {0, 1, 2, 3, 4, 5, int(before["nodata"])}
                                   for v in np.unique(center)):
                raise BridgeStop("projected_mask_class_changed")
            return {"native_metadata": before, "bridge_metadata": after,
                    "arc_and_gdal_sample_windows_equal": len(arc_windows),
                    "projected_grid": grid, "projected_center_valid_cells": int(valid.sum()),
                    "bridge_disk_bytes": tiff.stat().st_size,
                    "projected_disk_bytes": check_output_size(projected),
                    "resampling": "NEAREST" if categorical else "BILINEAR",
                    "frame_is_coverage_proof": False}
        finally:
            if result is not None:
                result.Close()
    finally:
        source.Close()
