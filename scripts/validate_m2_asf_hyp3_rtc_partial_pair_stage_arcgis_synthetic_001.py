#!/usr/bin/env python3
"""Disposable ArcGIS check of native-grid overlap through two VV dB rasters."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np

from m2_asf_hyp3_rtc_partial_pair_stage_io_001 import (
    DISPLAY_NAMES, stage_from_open_datasets,
)
from pixel_qa_core import load_contract
from validate_m2_asf_hyp3_rtc_partial_pair_grid_arcgis_synthetic_001 import (
    RINGS, _raster,
)


ROOT = Path(__file__).resolve().parents[1]


def validate() -> dict:
    import arcpy
    from osgeo import gdal

    contract = load_contract(ROOT / "config/qa/pixel-readiness-contract.json")
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
    with tempfile.TemporaryDirectory(prefix="nepal-rtc-pair-stage-") as temporary:
        root = Path(temporary)
        result = stage_from_open_datasets(
            datasets=native,
            rings={key: ring for key, ring in zip(
                ("AOI-SOURCE", "AOI-UPPER-CORRIDOR"), RINGS, strict=True)},
            contract=contract, output=root / "stage",
        )
        if (result["status"] != "pass_common_valid_for_local_partial_visual_only"
                or [item["name"] for item in result["display_rasters"]]
                != list(DISPLAY_NAMES)):
            raise RuntimeError("disposable_stage_overlap_or_output_failed")
        for name in DISPLAY_NAMES:
            path = root / "stage" / name
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
            if dataset.GetRasterBand(1).GetNoDataValue() is None:
                raise RuntimeError("disposable_stage_nodata_missing")
            actual = dataset.GetRasterBand(1).ReadAsArray()
            if np.count_nonzero(np.isfinite(actual)) != result["common_valid_cells_in_union"]:
                raise RuntimeError("disposable_stage_common_mask_mismatch")
            dataset = None
        arcpy.management.ClearWorkspaceCache()
        native["after_mask"].GetRasterBand(1).WriteArray(
            np.full(shape, 5, dtype=np.uint8))
        blocked_output = root / "blocked"
        blocked = stage_from_open_datasets(
            datasets=native,
            rings={key: ring for key, ring in zip(
                ("AOI-SOURCE", "AOI-UPPER-CORRIDOR"), RINGS, strict=True)},
            contract=contract, output=blocked_output,
        )
        if (blocked["status"] != "block_partial_pair_display"
                or blocked_output.exists() or "display_rasters" in blocked):
            raise RuntimeError("disposable_stage_block_created_pixels")
    return {"status": "pass_disposable_common_valid_vv_db_arcgis_runtime",
            "arcgis_version": arcpy.GetInstallInfo()["Version"],
            "wkid": 32645, "cell_size_m": 10,
            "aoi_common_valid_fraction": {
                item["aoi_id"]: item["common_valid_fraction_of_aoi"]
                for item in result["aoi_results"]},
            "display_polarization": "VV", "resampling_performed": False,
            "blocked_pair_wrote_no_rasters": True,
            "provider_or_project_data_read": False,
            "map_or_scientific_admission": False}


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
