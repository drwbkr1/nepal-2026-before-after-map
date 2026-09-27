#!/usr/bin/env python3
"""Disposable ArcGIS GDAL /vsizip/ header test; no project product access."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from zipfile import ZipFile

import numpy as np
from osgeo import gdal, osr

from m2_asf_hyp3_rtc_core_001 import ORDER
from m2_asf_hyp3_rtc_header_core_001 import RASTERS, inspect_raster_headers
from m2_asf_hyp3_rtc_product_header_001 import describe_vsi


TYPES = {"Float32": (gdal.GDT_Float32, np.float32),
         "Byte": (gdal.GDT_Byte, np.uint8),
         "Int16": (gdal.GDT_Int16, np.int16)}


def main() -> int:
    gdal.UseExceptions()
    osr.UseExceptions()
    with tempfile.TemporaryDirectory(prefix="nepal-hyp3-vsi-header-") as dirname:
        root = Path(dirname)
        archive = root / "synthetic.zip"
        spatial = osr.SpatialReference()
        spatial.ImportFromEPSG(32645)
        with ZipFile(archive, "w") as package:
            for role, data_type in RASTERS.items():
                gdal_type, numpy_type = TYPES[data_type]
                path = root / f"{role}.tif"
                dataset = gdal.GetDriverByName("GTiff").Create(
                    str(path), 100, 100, 1, gdal_type
                )
                dataset.SetGeoTransform((400000, 10, 0, 3200000, 0, -10))
                dataset.SetProjection(spatial.ExportToWkt())
                dataset.GetRasterBand(1).WriteArray(np.ones((100, 100), dtype=numpy_type))
                dataset = None
                package.write(path, path.name)
        headers = {role: describe_vsi(archive, f"{role}.tif") for role in RASTERS}
        result = inspect_raster_headers(ORDER[0], headers)
        if result["status"] != "pass_header_descriptor_rules_only":
            raise RuntimeError("synthetic_header_guard_failed")
        shifted = json.loads(json.dumps(headers))
        shifted["vh"]["grid"]["xmin"] += 5
        shifted["vh"]["grid"]["origin_x"] += 5
        shifted["vh"]["grid"]["xmax"] += 5
        try:
            inspect_raster_headers(ORDER[0], shifted)
        except ValueError:
            pass
        else:
            raise RuntimeError("synthetic_shift_not_rejected")
    print(json.dumps({"status": "pass_disposable_arcgis_vsi_headers_only",
                      "raster_count": len(RASTERS), "project_product_opened": False,
                      "product_pixels_read": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        print(json.dumps({"status": "stopped", "code": "arcgis_vsi_header_synthetic_failed"}))
        raise SystemExit(20) from None
