#!/usr/bin/env python3
"""ArcGIS GDAL ZIP-window and AOI-rasterization test using disposable pixels."""

from __future__ import annotations

import gc
import json
import tempfile
from pathlib import Path
from zipfile import ZipFile

import numpy as np
from osgeo import gdal, osr

from m2_asf_hyp3_rtc_product_pixel_001 import scan_one_aoi
from pixel_qa_core import load_contract


def main() -> int:
    gdal.UseExceptions()
    osr.UseExceptions()
    with tempfile.TemporaryDirectory(prefix="nepal-hyp3-vsi-pixel-") as dirname:
        root = Path(dirname)
        archive = root / "synthetic.zip"
        spatial = osr.SpatialReference()
        spatial.ImportFromEPSG(32645)
        arrays = {
            "VV": (gdal.GDT_Float32, np.ones((100, 100), dtype=np.float32)),
            "VH": (gdal.GDT_Float32, np.ones((100, 100), dtype=np.float32)),
            "ls": (gdal.GDT_Byte, np.ones((100, 100), dtype=np.uint8)),
        }
        arrays["ls"][1][10, 10] = 5
        with ZipFile(archive, "w") as package:
            for role, (dtype, values) in arrays.items():
                path = root / f"{role}.tif"
                dataset = gdal.GetDriverByName("GTiff").Create(str(path), 100, 100, 1, dtype)
                dataset.SetGeoTransform((400000, 10, 0, 3200000, 0, -10))
                dataset.SetProjection(spatial.ExportToWkt())
                dataset.GetRasterBand(1).WriteArray(values)
                dataset = None
                package.write(path, path.name)
        datasets = {role: gdal.OpenEx("/vsizip/" + archive.as_posix() + f"/{role}.tif",
                                      gdal.OF_RASTER)
                    for role in arrays}
        if any(dataset is None for dataset in datasets.values()):
            raise RuntimeError("synthetic_zip_raster_unreadable")
        points = [[400100, 3199900], [400300, 3199900], [400300, 3199700],
                  [400100, 3199700], [400100, 3199900]]
        contract = load_contract(Path(__file__).resolve().parents[1] /
                                 "config/qa/pixel-readiness-contract.json")
        result = scan_one_aoi("AOI-SOURCE", points, datasets["VV"], datasets["VH"],
                              datasets["ls"], contract)
        if result["status"] != "pass_qa_only" or result["covered_cell_count"] != 400:
            raise RuntimeError("synthetic_aoi_window_qa_failed")
        if result["excluded_cell_count_by_reason"]["provider_layover"] != 1:
            raise RuntimeError("synthetic_mask_exclusion_failed")
        datasets.clear()
        result = None
        gc.collect()
    print(json.dumps({"status": "pass_disposable_arcgis_vsi_pixel_windows_only",
                      "project_product_opened": False, "source_pixels_read": False},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        print(json.dumps({"status": "stopped", "code": "arcgis_vsi_pixel_synthetic_failed"}))
        raise SystemExit(20) from None
