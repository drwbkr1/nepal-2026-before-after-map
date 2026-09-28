#!/usr/bin/env python3
"""Installed ArcGIS/GDAL native-pair test with generated in-memory rasters."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from m2_asf_hyp3_rtc_partial_pair_core_001 import assess_common_valid
from m2_asf_hyp3_rtc_partial_pair_grid_001 import (
    choose_target_grid, rasterize_ring_on_target, read_band_on_target,
)
from pixel_qa_core import load_contract


ROOT = Path(__file__).resolve().parents[1]
RINGS = [
    [[300020., 3100420.], [300220., 3100420.], [300220., 3100620.],
     [300020., 3100620.], [300020., 3100420.]],
    [[300230., 3100200.], [300430., 3100200.], [300430., 3100400.],
     [300230., 3100400.], [300230., 3100200.]],
]


def _raster(values: np.ndarray, x0: float):
    from osgeo import gdal, osr

    rows, columns = values.shape
    dtype = gdal.GDT_Byte if values.dtype == np.uint8 else gdal.GDT_Float32
    ds = gdal.GetDriverByName("MEM").Create("", columns, rows, 1, dtype)
    spatial = osr.SpatialReference()
    spatial.ImportFromEPSG(32645)
    ds.SetSpatialRef(spatial)
    ds.SetGeoTransform((x0, 10., 0., 3100640., 0., -10.))
    ds.GetRasterBand(1).WriteArray(values)
    return ds


def _grid(x0: float) -> dict:
    return {"wkid": 32645, "cell_size_x": 10., "cell_size_y": 10.,
            "origin_x": x0, "origin_y": 3100640.,
            "xmin": x0, "ymin": 3100000., "xmax": x0 + 640.,
            "ymax": 3100640., "rotation_degrees": 0.}


def validate() -> dict:
    import arcpy

    contract = load_contract(ROOT / "config/qa/pixel-readiness-contract.json")
    target = choose_target_grid(_grid(300000.), _grid(300010.), RINGS, contract)
    before = np.ones((64, 64), dtype=np.float32)
    after = np.full((64, 64), 2., dtype=np.float32)
    before_mask = np.ones((64, 64), dtype=np.uint8)
    after_mask = np.ones((64, 64), dtype=np.uint8)
    before_mask[5:12, 5:14] = 5
    after_mask[10:16, 15:20] = 17
    datasets = {
        "before_vv": _raster(before, 300000.),
        "before_vh": _raster(before, 300000.),
        "before_mask": _raster(before_mask, 300000.),
        "after_vv": _raster(after, 300010.),
        "after_vh": _raster(after, 300010.),
        "after_mask": _raster(after_mask, 300010.),
    }
    arrays = {
        key: read_band_on_target(ds, target,
                                 fill=0 if key.endswith("mask") else np.nan,
                                 dtype=np.uint8 if key.endswith("mask") else np.float32)
        for key, ds in datasets.items()
    }
    results = []
    for aoi_id, ring in zip(("AOI-SOURCE", "AOI-UPPER-CORRIDOR"), RINGS, strict=True):
        mask = rasterize_ring_on_target(ring, target)
        result = assess_common_valid(
            aoi_id=aoi_id, aoi_footprint=mask,
            pixel_area_m2=100., aoi_area_m2=40000., partial_floor=.2,
            **arrays,
        )
        if result["status"] != "pass_common_valid_for_local_partial_visual_only":
            raise RuntimeError("disposable_common_valid_overlap_failed")
        results.append(result)
    return {
        "status": "pass_disposable_native_grid_common_valid_arcgis_runtime",
        "arcgis_version": arcpy.GetInstallInfo()["Version"],
        "wkid": target["wkid"],
        "target_width": target["width"], "target_height": target["height"],
        "resampling_performed": False,
        "aoi_common_valid_fraction": {item["aoi_id"]: item["common_valid_fraction_of_aoi"]
                                      for item in results},
        "project_or_provider_data_read": False,
        "network_or_credential_action": False,
        "scientific_admission": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
