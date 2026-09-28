#!/usr/bin/env python3
"""Disposable ArcGIS check of native-grid overlap through two VV dB rasters."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np

from m2_asf_hyp3_rtc_partial_pair_grid_001 import (
    choose_target_grid, rasterize_ring_on_target, read_band_on_target,
)
from m2_asf_hyp3_rtc_partial_pair_stage_core_001 import prepare_common_valid_vv_db
from pixel_qa_core import load_contract
from validate_m2_asf_hyp3_rtc_partial_pair_grid_arcgis_synthetic_001 import (
    RINGS, _grid, _raster,
)


ROOT = Path(__file__).resolve().parents[1]


def _save(path: Path, values: np.ndarray, target: dict) -> None:
    from osgeo import gdal, osr

    driver = gdal.GetDriverByName("GTiff")
    dataset = driver.Create(str(path), target["width"], target["height"],
                            1, gdal.GDT_Float32,
                            options=["TILED=YES", "COMPRESS=LZW"])
    if dataset is None:
        raise RuntimeError("disposable_stage_create_failed")
    spatial = osr.SpatialReference()
    spatial.ImportFromEPSG(32645)
    dataset.SetSpatialRef(spatial)
    dataset.SetGeoTransform((target["xmin"], 10., 0., target["ymax"], 0., -10.))
    band = dataset.GetRasterBand(1)
    band.SetNoDataValue(float("nan"))
    band.WriteArray(values)
    band.FlushCache()
    dataset.FlushCache()
    dataset = None


def validate() -> dict:
    import arcpy
    from osgeo import gdal

    contract = load_contract(ROOT / "config/qa/pixel-readiness-contract.json")
    target = choose_target_grid(_grid(300000.), _grid(300010.), RINGS, contract)
    shape = (64, 64)
    before = np.ones(shape, dtype=np.float32)
    after = np.full(shape, 10., dtype=np.float32)
    before_mask = np.ones(shape, dtype=np.uint8)
    after_mask = np.ones(shape, dtype=np.uint8)
    before_mask[5:12, 5:14] = 5
    after_mask[10:16, 15:20] = 17
    native = {
        "before_vv": _raster(before, 300000.),
        "before_vh": _raster(before, 300000.),
        "before_mask": _raster(before_mask, 300000.),
        "after_vv": _raster(after, 300010.),
        "after_vh": _raster(after, 300010.),
        "after_mask": _raster(after_mask, 300010.),
    }
    arrays = {key: read_band_on_target(
        dataset, target, fill=0 if key.endswith("mask") else np.nan,
        dtype=np.uint8 if key.endswith("mask") else np.float32,
    ) for key, dataset in native.items()}
    aoi_masks = {key: rasterize_ring_on_target(ring, target)
                 for key, ring in zip(("AOI-SOURCE", "AOI-UPPER-CORRIDOR"),
                                      RINGS, strict=True)}
    stage = prepare_common_valid_vv_db(
        arrays=arrays, aoi_masks=aoi_masks,
        aoi_areas_m2={"AOI-SOURCE": 40000.,
                      "AOI-UPPER-CORRIDOR": 40000.},
        pixel_area_m2=100.,
    )
    if stage["status"] != "pass_common_valid_for_local_partial_visual_only":
        raise RuntimeError("disposable_stage_overlap_failed")
    with tempfile.TemporaryDirectory(prefix="nepal-rtc-pair-stage-") as temporary:
        root = Path(temporary)
        paths = [root / "before_vv_db.tif", root / "after_vv_db.tif"]
        arrays_db = [stage["before_vv_db"], stage["after_vv_db"]]
        for path, values in zip(paths, arrays_db, strict=True):
            _save(path, values, target)
        for path, expected in zip(paths, arrays_db, strict=True):
            raster = arcpy.Raster(str(path))
            try:
                if (raster.spatialReference.factoryCode != 32645
                        or raster.bandCount != 1 or raster.pixelType != "F32"
                        or raster.meanCellWidth != 10.
                        or raster.meanCellHeight != 10.):
                    raise RuntimeError("disposable_stage_arcgis_header_invalid")
            finally:
                del raster
            dataset = gdal.OpenEx(str(path), gdal.OF_RASTER)
            actual = dataset.GetRasterBand(1).ReadAsArray()
            if not np.array_equal(actual, expected, equal_nan=True):
                raise RuntimeError("disposable_stage_raster_pixels_differ")
            dataset = None
        arcpy.management.ClearWorkspaceCache()
    return {"status": "pass_disposable_common_valid_vv_db_arcgis_runtime",
            "arcgis_version": arcpy.GetInstallInfo()["Version"],
            "wkid": 32645, "cell_size_m": 10,
            "aoi_common_valid_fraction": {
                item["aoi_id"]: item["common_valid_fraction_of_aoi"]
                for item in stage["aoi_results"]},
            "display_polarization": "VV", "resampling_performed": False,
            "provider_or_project_data_read": False,
            "map_or_scientific_admission": False}


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
