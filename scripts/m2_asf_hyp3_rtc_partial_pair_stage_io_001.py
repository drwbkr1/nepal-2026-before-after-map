"""Native-grid, disposable-testable IO bridge for a gated ASF visual panel.

This module accepts already opened datasets. It does not open provider ZIPs,
verify rights, reserve a real attempt, or release itself for real pixel reads.
Its caller must complete those distinct gates before invoking it on real data.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

import numpy as np

from m2_asf_hyp3_rtc_partial_pair_grid_001 import (
    choose_target_grid, rasterize_ring_on_target, read_band_on_target,
)
from m2_asf_hyp3_rtc_partial_pair_stage_core_001 import (
    AOI_IDS, ARRAY_ROLES, prepare_common_valid_vv_db,
)


DISPLAY_NAMES = ("before_common_valid_vv_db.tif", "after_common_valid_vv_db.tif")


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _is_epsg32645(spatial) -> bool:
    from osgeo import osr

    if spatial is None:
        return False
    expected = osr.SpatialReference()
    expected.ImportFromEPSG(32645)
    return bool(spatial.IsSame(expected))


def _grid(dataset, *, mask: bool) -> dict:
    from osgeo import gdal

    spatial = dataset.GetSpatialRef()
    gt = dataset.GetGeoTransform()
    if (not _is_epsg32645(spatial)
            or dataset.RasterCount != 1
            or dataset.GetRasterBand(1).DataType != (gdal.GDT_Byte if mask else gdal.GDT_Float32)
            or gt is None or len(gt) != 6
            or any(not math.isfinite(value) for value in gt)
            or abs(gt[1] - 10.) > 1e-6 or abs(gt[5] + 10.) > 1e-6
            or gt[2] != 0 or gt[4] != 0
            or dataset.RasterXSize <= 0 or dataset.RasterYSize <= 0):
        raise ValueError("partial_pair_stage_dataset_header_invalid")
    return {"wkid": 32645, "cell_size_x": gt[1], "cell_size_y": -gt[5],
            "origin_x": gt[0], "origin_y": gt[3],
            "xmin": gt[0], "ymin": gt[3] + dataset.RasterYSize * gt[5],
            "xmax": gt[0] + dataset.RasterXSize * gt[1], "ymax": gt[3],
            "rotation_degrees": 0.}


def _area(ring: list[list[float]]) -> float:
    from osgeo import ogr

    linear = ogr.Geometry(ogr.wkbLinearRing)
    for x, y in ring:
        linear.AddPoint_2D(float(x), float(y))
    polygon = ogr.Geometry(ogr.wkbPolygon)
    polygon.AddGeometry(linear)
    if polygon.IsEmpty() or not polygon.IsValid():
        raise ValueError("partial_pair_stage_aoi_invalid")
    return polygon.GetArea()


def _write_raster(path: Path, values: np.ndarray, target: dict) -> dict:
    from osgeo import gdal, osr

    if path.exists() or values.shape != (target["height"], target["width"]):
        raise ValueError("partial_pair_stage_raster_output_invalid")
    spatial = osr.SpatialReference()
    spatial.ImportFromEPSG(32645)
    dataset = gdal.GetDriverByName("GTiff").Create(
        str(path), target["width"], target["height"], 1, gdal.GDT_Float32,
        options=["TILED=YES", "COMPRESS=LZW"],
    )
    if dataset is None:
        raise ValueError("partial_pair_stage_raster_create_failed")
    dataset.SetSpatialRef(spatial)
    dataset.SetGeoTransform((target["xmin"], 10., 0., target["ymax"], 0., -10.))
    band = dataset.GetRasterBand(1)
    band.SetNoDataValue(float("nan"))
    band.WriteArray(values)
    band.FlushCache()
    dataset.FlushCache()
    dataset = None
    check = gdal.OpenEx(str(path), gdal.OF_RASTER)
    try:
        if (check is None or not _is_epsg32645(check.GetSpatialRef())
                or check.RasterXSize != target["width"]
                or check.RasterYSize != target["height"]):
            raise ValueError("partial_pair_stage_raster_reopen_failed")
        actual = check.GetRasterBand(1).ReadAsArray()
        if actual is None or not np.array_equal(actual, values, equal_nan=True):
            raise ValueError("partial_pair_stage_raster_pixel_verify_failed")
    finally:
        check = None
    return {"name": path.name, "size_bytes": path.stat().st_size,
            "sha256": _sha(path)}


def stage_from_open_datasets(
    *, datasets: dict, rings: dict[str, list[list[float]]],
    contract: dict, output: Path,
) -> dict:
    """Save two matched VV rasters only after both event AOIs pass overlap.

    The caller must provide exactly the six frozen roles and two approved rings,
    bind them to source identities, verify rights and reserve the real attempt.
    No source dataset is modified, resampled, or exported.
    """
    from osgeo import gdal

    gdal.UseExceptions()
    if (not isinstance(datasets, dict) or set(datasets) != set(ARRAY_ROLES)
            or not isinstance(rings, dict) or set(rings) != set(AOI_IDS)
            or not isinstance(output, Path) or output.exists() or output.is_symlink()):
        raise ValueError("partial_pair_stage_inputs_or_output_invalid")
    grids = {role: _grid(dataset, mask=role.endswith("mask"))
             for role, dataset in datasets.items()}
    if any(grids[role] != grids["before_vv"] for role in ("before_vh", "before_mask")):
        raise ValueError("partial_pair_stage_before_grid_drift")
    if any(grids[role] != grids["after_vv"] for role in ("after_vh", "after_mask")):
        raise ValueError("partial_pair_stage_after_grid_drift")
    target = choose_target_grid(grids["before_vv"], grids["after_vv"],
                                [rings[key] for key in AOI_IDS], contract)
    arrays = {role: read_band_on_target(
        datasets[role], target,
        fill=0 if role.endswith("mask") else np.nan,
        dtype=np.uint8 if role.endswith("mask") else np.float32,
    ) for role in ARRAY_ROLES}
    aoi_masks = {key: rasterize_ring_on_target(rings[key], target)
                 for key in AOI_IDS}
    stage = prepare_common_valid_vv_db(
        arrays=arrays, aoi_masks=aoi_masks,
        aoi_areas_m2={key: _area(rings[key]) for key in AOI_IDS},
        pixel_area_m2=100.,
        before_nodata=(datasets["before_vv"].GetRasterBand(1).GetNoDataValue(),
                       datasets["before_vh"].GetRasterBand(1).GetNoDataValue()),
        after_nodata=(datasets["after_vv"].GetRasterBand(1).GetNoDataValue(),
                      datasets["after_vh"].GetRasterBand(1).GetNoDataValue()),
    )
    result = {"status": stage["status"], "aoi_results": stage["aoi_results"],
              "wkid": 32645, "target_grid": target,
              "resampling_performed": False, "registration_measured": False,
              "scientific_admission_authorized": False}
    if stage["status"] != "pass_common_valid_for_local_partial_visual_only":
        return result
    output.mkdir(parents=True, exist_ok=False)
    result["display_rasters"] = [
        _write_raster(output / name, stage[key], target)
        for name, key in zip(DISPLAY_NAMES, ("before_vv_db", "after_vv_db"), strict=True)
    ]
    result["display_polarization"] = "VV"
    result["display_units"] = "gamma0 dB"
    result["common_valid_cells_in_union"] = stage["common_valid_cells_in_union"]
    return result
