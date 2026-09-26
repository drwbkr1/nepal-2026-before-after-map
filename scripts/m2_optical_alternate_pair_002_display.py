#!/usr/bin/env python3
"""Local masked RGB display only; no cross-date quantitative change product."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from m2_optical_alternate_pair_002_core import single_date_usable_mask
from m2_optical_gdal_recovery_002_adapter import TARGET_GRID


RGB_ROLES = ("B04", "B03", "B02")
DISPLAY_REFLECTANCE_MAX = 0.30


def display_rgb(dn_by_role: dict[str, np.ndarray], metadata: dict[str, Any],
                usable: np.ndarray) -> np.ndarray:
    """Use each product's own offset and quantification on one fixed display scale.

    Valid values occupy 1..255; zero is transparent/masked. No between-date
    subtraction, ratio, harmonization, or scientific admission occurs here.
    """
    if set(dn_by_role) != set(RGB_ROLES) or usable.dtype != np.bool_:
        raise ValueError("alternate_pair_rgb_roles_or_mask_invalid")
    quantification = metadata.get("quantification_value")
    offsets = metadata.get("offsets_by_band", {})
    if (not isinstance(quantification, (int, float)) or quantification <= 0
            or any(role not in offsets for role in RGB_ROLES)):
        raise ValueError("alternate_pair_rgb_scaling_metadata_invalid")
    output = np.zeros((3, *usable.shape), dtype=np.uint8)
    for index, role in enumerate(RGB_ROLES):
        dn = dn_by_role[role]
        if dn.shape != usable.shape or dn.dtype != np.uint16:
            raise ValueError("alternate_pair_rgb_dn_grid_invalid")
        valid = usable & (dn != 0) & (dn != 65535)
        reflectance = (dn[valid].astype(np.float64) + float(offsets[role])) / float(quantification)
        output[index][valid] = (1 + np.rint(np.clip(reflectance / DISPLAY_REFLECTANCE_MAX,
                                                     0, 1) * 254)).astype(np.uint8)
    return output


def warp_rgb_band(path: Path, grid: dict[str, Any] = TARGET_GRID) -> np.ndarray:
    """Read a 10 m reflectance JP2 onto the frozen 20 m display grid."""
    from osgeo import gdal, osr  # type: ignore[import-not-found]

    if grid != TARGET_GRID:
        raise ValueError("alternate_pair_rgb_target_grid_drift")
    gdal.UseExceptions()
    gdal.SetConfigOption("PROJ_NETWORK", "OFF")
    gdal.SetConfigOption("GDAL_PAM_ENABLED", "NO")
    source = gdal.OpenEx(str(path), gdal.OF_RASTER | gdal.OF_READONLY,
                         allowed_drivers=["JP2KAK", "JP2OpenJPEG", "JP2ECW"])
    if source is None or source.RasterCount != 1:
        raise ValueError("alternate_pair_rgb_source_invalid")
    target = nearest = None
    try:
        expected = osr.SpatialReference()
        expected.ImportFromEPSG(32645)
        if source.GetSpatialRef() is None or not source.GetSpatialRef().IsSame(expected):
            raise ValueError("alternate_pair_rgb_source_crs_invalid")
        options = dict(format="MEM", outputBounds=(grid["xmin"], grid["ymin"],
                                                  grid["xmax"], grid["ymax"]),
                       width=grid["columns"], height=grid["rows"],
                       dstSRS="EPSG:32645", srcNodata=65535, dstNodata=65535,
                       outputType=gdal.GDT_UInt16, multithread=False)
        target = gdal.Warp("", source, resampleAlg="bilinear", **options)
        nearest = gdal.Warp("", source, resampleAlg="near", **options)
        if target is None or nearest is None:
            raise ValueError("alternate_pair_rgb_warp_failed")
        expected_transform = (grid["xmin"], 20.0, 0.0, grid["ymax"], 0.0, -20.0)
        if (target.RasterXSize, target.RasterYSize) != (grid["columns"], grid["rows"]) or \
                tuple(target.GetGeoTransform()) != expected_transform:
            raise ValueError("alternate_pair_rgb_warp_grid_invalid")
        result = target.ReadAsArray()
        result[nearest.ReadAsArray() == 0] = 0
        return result
    finally:
        if nearest is not None:
            nearest.Close()
        if target is not None:
            target.Close()
        source.Close()


def make_masked_display(paths: dict[str, Path], metadata: dict[str, Any],
                        output: Path, *, grid: dict[str, Any] = TARGET_GRID) -> dict[str, Any]:
    """Write one local three-band EPSG:32645 display raster without replacement."""
    from osgeo import gdal, osr  # type: ignore[import-not-found]

    if output.exists() or grid != TARGET_GRID:
        raise ValueError("alternate_pair_rgb_output_collision_or_grid_drift")
    if set(paths) < {*RGB_ROLES, "SCL", "quality_classification", "B11"}:
        raise ValueError("alternate_pair_rgb_source_roles_missing")
    from m2_optical_gdal_recovery_002_adapter import warp_target

    scl = warp_target(paths["SCL"], "SCL", grid)
    quality = warp_target(paths["quality_classification"], "quality_classification", grid)
    b11 = warp_target(paths["B11"], "B11", grid)
    mask = single_date_usable_mask(scl, quality, b11)
    if mask["unknown_scl_present"]:
        raise ValueError("alternate_pair_rgb_unknown_scl")
    bands = {role: warp_rgb_band(paths[role], grid) for role in RGB_ROLES}
    rgb = display_rgb(bands, metadata, mask["usable"])
    output.parent.mkdir(parents=True, exist_ok=True)
    raster = gdal.GetDriverByName("GTiff").Create(
        str(output), grid["columns"], grid["rows"], 3, gdal.GDT_Byte,
        options=["COMPRESS=LZW", "TILED=YES", "BIGTIFF=IF_SAFER"])
    if raster is None:
        raise ValueError("alternate_pair_rgb_write_failed")
    try:
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(32645)
        raster.SetSpatialRef(srs)
        raster.SetGeoTransform((grid["xmin"], 20.0, 0.0, grid["ymax"], 0.0, -20.0))
        for index in range(3):
            band = raster.GetRasterBand(index + 1)
            band.SetNoDataValue(0)
            band.WriteArray(rgb[index])
        raster.FlushCache()
    finally:
        raster.Close()
    return {"status": "local_masked_visual_only", "wkid": 32645,
            "cell_size_m": 20.0,
            "display_reflectance_range": [0.0, DISPLAY_REFLECTANCE_MAX],
            "per_product_scaling_applied": True,
            "usable_cell_count": int(np.count_nonzero(mask["usable"])),
            "cross_date_change_analysis": False}
