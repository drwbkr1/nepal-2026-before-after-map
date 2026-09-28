#!/usr/bin/env python3
"""Disposable ArcGIS GDAL test of the after-product three-raster AOI scan."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile

import numpy as np
from osgeo import gdal, osr

from m2_asf_hyp3_rtc_after_pixel_001 import scan_after_product
from m2_asf_hyp3_rtc_after_pixel_disposition_001 import evaluate_after_aoi_results
from m2_asf_hyp3_rtc_header_core_001 import RASTERS
from m2_asf_hyp3_rtc_product_header_001 import ROLE_SUFFIX, describe_vsi
from pixel_qa_core import load_contract
from validate_m2_asf_hyp3_rtc_vsi_header_synthetic_001 import TYPES


BASE = "S1D_IW_20260828T122141_DVP_RTC10_G_gpuned_ABCD"
ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    gdal.UseExceptions()
    osr.UseExceptions()
    with tempfile.TemporaryDirectory(prefix="nepal-hyp3-after-pixel-") as dirname:
        root = Path(dirname)
        archive = root / f"{BASE}.zip"
        spatial = osr.SpatialReference()
        spatial.ImportFromEPSG(32645)
        with ZipFile(archive, "w", ZIP_STORED) as package:
            for role, data_type in RASTERS.items():
                gdal_type, numpy_type = TYPES[data_type]
                path = root / f"{role}.tif"
                dataset = gdal.GetDriverByName("GTiff").Create(
                    str(path), 100, 100, 1, gdal_type)
                dataset.SetGeoTransform((400000.0, 10.0, 0.0,
                                         3200000.0, 0.0, -10.0))
                dataset.SetProjection(spatial.ExportToWkt())
                values = np.ones((100, 100), dtype=numpy_type)
                if role == "ls_map":
                    values[10, 10] = 5
                dataset.GetRasterBand(1).WriteArray(values)
                dataset = None
                package.write(path, f"{BASE}/{BASE}{ROLE_SUFFIX[role]}")
        headers = {role: describe_vsi(archive, f"{BASE}/{BASE}{suffix}")
                   for role, suffix in ROLE_SUFFIX.items()}
        aois = [
            ("AOI-SOURCE", [[400100, 3199900], [400300, 3199900],
                            [400300, 3199700], [400100, 3199700],
                            [400100, 3199900]]),
            ("AOI-UPPER-CORRIDOR", [[400500, 3199500], [400700, 3199500],
                                    [400700, 3199300], [400500, 3199300],
                                    [400500, 3199500]]),
        ]
        contract = load_contract(ROOT / "config/qa/pixel-readiness-contract.json")
        results = scan_after_product(archive, {"headers": headers}, aois, contract)
        decision = evaluate_after_aoi_results(results, contract)
        if (decision["status"] != "pass_after_full_area_qa_only"
                or results[0]["excluded_cell_count_by_reason"]["provider_layover"] != 1
                or results[0]["covered_cell_count"] != 400
                or decision["arcgis_map_released"] is not False):
            raise RuntimeError("disposable_after_pixel_invalid")
    print(json.dumps({"status": "pass_disposable_after_AOI_pixel_windows_only",
                      "aoi_count": 2, "project_product_opened": False,
                      "source_pixels_read": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        print(json.dumps({"status": "stopped",
                          "code": "disposable_after_pixel_validation_failed"}))
        raise SystemExit(20) from None
