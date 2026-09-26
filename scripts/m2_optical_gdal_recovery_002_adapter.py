#!/usr/bin/env python3
"""GDAL-only adapters for the frozen optical header and QA decisions.

All functions accept caller-selected paths. Importing this module never opens
project custody. Real-source access is controlled by the separate supervisor.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from optical_pixel_readiness_core_001 import REASON_CODES, VALID_CLASS
from pixel_qa_core import evaluate_aoi_coverage


DRIVERS = {"JP2KAK", "JP2OpenJPEG", "JP2ECW"}
TARGET_GRID = {"xmin": 273300.0, "ymin": 3070220.0, "xmax": 367820.0,
               "ymax": 3149220.0, "rows": 3950, "columns": 4726,
               "cell_size_m": 20.0, "wkid": 32645}


def _gdal() -> tuple[Any, Any]:
    from osgeo import gdal, osr  # type: ignore[import-not-found]

    gdal.UseExceptions()
    gdal.SetConfigOption("PROJ_NETWORK", "OFF")
    gdal.SetConfigOption("GDAL_PAM_ENABLED", "NO")
    return gdal, osr


def describe(path: Path) -> dict[str, Any]:
    """Read a JP2 header only, rejecting a missing or inequivalent CRS."""
    gdal, osr = _gdal()
    dataset = gdal.OpenEx(str(path), gdal.OF_RASTER | gdal.OF_READONLY,
                          allowed_drivers=sorted(DRIVERS))
    if dataset is None:
        raise ValueError("gdal_jp2_header_open_failed")
    try:
        transform = dataset.GetGeoTransform(can_return_null=True)
        if (transform is None or transform[2] != 0 or transform[4] != 0
                or transform[1] <= 0 or transform[5] >= 0):
            raise ValueError("gdal_jp2_transform_invalid")
        source_srs = dataset.GetSpatialRef()
        expected_srs = osr.SpatialReference()
        expected_srs.ImportFromEPSG(32645)
        if source_srs is None or not source_srs.IsSame(expected_srs):
            raise ValueError("gdal_jp2_crs_not_equivalent")
        pixel_types = {gdal.GDT_Byte: "U8", gdal.GDT_UInt16: "U16"}
        bands = [pixel_types.get(dataset.GetRasterBand(index).DataType)
                 for index in range(1, dataset.RasterCount + 1)]
        if not bands or None in bands or len(set(bands)) != 1:
            raise ValueError("gdal_jp2_pixel_type_invalid")
        width, height = dataset.RasterXSize, dataset.RasterYSize
        cell_x, cell_y = float(transform[1]), -float(transform[5])
        result = {
            "format": "JP2", "reader_driver": dataset.GetDriver().ShortName,
            "wkid": 32645, "crs_equivalence_verified": True,
            "band_count": dataset.RasterCount, "width": width, "height": height,
            "cell_width": cell_x, "cell_height": cell_y, "pixel_type": bands[0],
            "xmin": float(transform[0]), "ymax": float(transform[3]),
            "xmax": float(transform[0]) + width * cell_x,
            "ymin": float(transform[3]) - height * cell_y,
        }
        if dataset.RasterCount == 3:
            result["band_details"] = [
                {"name": f"Band_{index}", "width": width, "height": height,
                 "cell_width": cell_x, "cell_height": cell_y, "pixel_type": bands[index - 1]}
                for index in range(1, 4)
            ]
        return result
    finally:
        dataset.Close()


def warp_target(path: Path, role: str, grid: dict[str, Any] = TARGET_GRID) -> Any:
    """Decode only the approved target grid using categorical/continuous rules."""
    if role not in {"SCL", "quality_classification", "B11"}:
        raise ValueError("gdal_pixel_role_unapproved")
    gdal, osr = _gdal()
    if (grid.get("wkid") != 32645 or grid.get("cell_size_m") != 20.0
            or (grid["xmax"] - grid["xmin"]) != grid["columns"] * 20.0
            or (grid["ymax"] - grid["ymin"]) != grid["rows"] * 20.0):
        raise ValueError("gdal_target_grid_drift")
    source = gdal.OpenEx(str(path), gdal.OF_RASTER | gdal.OF_READONLY,
                         allowed_drivers=sorted(DRIVERS))
    if source is None:
        raise ValueError("gdal_pixel_source_open_failed")
    target = None
    nearest = None
    try:
        expected = osr.SpatialReference()
        expected.ImportFromEPSG(32645)
        if source.GetSpatialRef() is None or not source.GetSpatialRef().IsSame(expected):
            raise ValueError("gdal_pixel_crs_not_equivalent")
        is_continuous = role == "B11"
        fill = 65535 if is_continuous else 255
        target = gdal.Warp(
            "", source, format="MEM", outputBounds=(grid["xmin"], grid["ymin"],
                                                   grid["xmax"], grid["ymax"]),
            width=grid["columns"], height=grid["rows"], dstSRS="EPSG:32645",
            resampleAlg="bilinear" if is_continuous else "near",
            srcNodata=65535 if is_continuous else 255, dstNodata=fill,
            outputType=gdal.GDT_UInt16 if is_continuous else gdal.GDT_Byte,
            multithread=False,
        )
        if target is None or (target.RasterXSize, target.RasterYSize) != (grid["columns"], grid["rows"]):
            raise ValueError("gdal_target_warp_failed")
        if tuple(target.GetGeoTransform()) != (grid["xmin"], 20.0, 0.0, grid["ymax"], 0.0, -20.0):
            raise ValueError("gdal_target_transform_drift")
        count = 3 if role == "quality_classification" else 1
        if target.RasterCount != count:
            raise ValueError("gdal_target_band_count_drift")
        array = target.ReadAsArray()
        if array is None:
            raise ValueError("gdal_target_decode_failed")
        if is_continuous:
            # Preserve the frozen DN-zero exclusion at each target cell center.
            # Bilinear values alone can smear a source zero into nonzero DNs.
            nearest = gdal.Warp(
                "", source, format="MEM", outputBounds=(grid["xmin"], grid["ymin"],
                                                       grid["xmax"], grid["ymax"]),
                width=grid["columns"], height=grid["rows"], dstSRS="EPSG:32645",
                resampleAlg="near", srcNodata=65535, dstNodata=65535,
                outputType=gdal.GDT_UInt16, multithread=False,
            )
            if nearest is None or (nearest.RasterXSize, nearest.RasterYSize) != (grid["columns"], grid["rows"]):
                raise ValueError("gdal_zero_mask_resample_failed")
            array[nearest.ReadAsArray() == 0] = 0
        return array
    finally:
        if nearest is not None:
            nearest.Close()
        if target is not None:
            target.Close()
        source.Close()


def polygon_area(rings: list[list[list[float]]]) -> float:
    """Signed ring areas support holes in the frozen Esri polygon geometry."""
    total = 0.0
    for ring in rings:
        if len(ring) < 4 or ring[0] != ring[-1]:
            raise ValueError("gdal_aoi_ring_invalid")
        twice = sum(float(left[0]) * float(right[1]) - float(right[0]) * float(left[1])
                     for left, right in zip(ring, ring[1:]))
        total += twice / 2.0
    if not math.isfinite(total) or abs(total) <= 0:
        raise ValueError("gdal_aoi_area_invalid")
    return abs(total)


def rasterize_aoi(feature: dict[str, Any], grid: dict[str, Any] = TARGET_GRID) -> Any:
    """Rasterize an approved Esri polygon on the exact QA grid by cell center."""
    from osgeo import ogr  # type: ignore[import-not-found]

    gdal, osr = _gdal()
    shape = ogr.Geometry(ogr.wkbPolygon)
    for coordinates in feature["geometry"]["rings"]:
        ring = ogr.Geometry(ogr.wkbLinearRing)
        for x, y in coordinates:
            ring.AddPoint_2D(float(x), float(y))
        shape.AddGeometry(ring)
    memory = ogr.GetDriverByName("MEM").CreateDataSource("")
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(32645)
    layer = memory.CreateLayer("approved_aoi", srs, ogr.wkbPolygon)
    record = ogr.Feature(layer.GetLayerDefn())
    record.SetGeometry(shape)
    layer.CreateFeature(record)
    raster = gdal.GetDriverByName("MEM").Create("", grid["columns"], grid["rows"], 1, gdal.GDT_Byte)
    raster.SetGeoTransform((grid["xmin"], 20.0, 0.0, grid["ymax"], 0.0, -20.0))
    raster.SetProjection(srs.ExportToWkt())
    raster.GetRasterBand(1).Fill(0)
    try:
        if gdal.RasterizeLayer(raster, [1], layer, burn_values=[1]) != 0:
            raise ValueError("gdal_aoi_rasterize_failed")
        return raster.ReadAsArray() == 1
    finally:
        raster.Close()
        memory = None


def tabulate_aoi(classes: Any, feature: dict[str, Any], contract: dict[str, Any],
                 unknown_scl_present: bool, grid: dict[str, Any] = TARGET_GRID) -> dict[str, Any]:
    import numpy as np

    identifier = feature["attributes"]["AOI_ID"]
    inside = rasterize_aoi(feature, grid)
    if classes.shape != inside.shape:
        raise ValueError("gdal_aoi_class_grid_drift")
    codes, counts = np.unique(classes[inside & (classes != -9999)], return_counts=True)
    areas = {int(code): float(count) * 400.0 for code, count in zip(codes, counts)}
    excluded = {REASON_CODES.get(code, f"unknown_classification_{code}"): area
                for code, area in areas.items() if code != VALID_CLASS and area > 0}
    result = evaluate_aoi_coverage(
        aoi_id=identifier, aoi_area_m2=polygon_area(feature["geometry"]["rings"]),
        covered_area_m2=sum(areas.values()), valid_area_m2=areas.get(VALID_CLASS, 0.0),
        excluded_area_by_reason_m2=excluded, contract=contract,
    )
    result["classification_area_m2"] = {str(code): area for code, area in sorted(areas.items())}
    if unknown_scl_present and result["status"] == "pass_qa_only":
        result["status"] = "defer"
        result["limitations"].append("Unknown SCL values were conservatively excluded and require review.")
    return result
