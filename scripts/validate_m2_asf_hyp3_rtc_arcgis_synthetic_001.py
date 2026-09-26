#!/usr/bin/env python3
"""Disposable six-raster ArcGIS header test for the approved HyP3 route.

The test generates its own tiny TIFFs in a fresh OS temporary directory. It
does not read project imagery, external custody, an account, or a HyP3 job.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import arcpy
import numpy as np

from m2_asf_hyp3_rtc_core_001 import ORDER
from m2_asf_hyp3_rtc_header_core_001 import RASTERS, inspect_raster_headers


DTYPES = {"Float32": np.float32, "Byte": np.uint8, "Int16": np.int16}
ARCGIS_TYPES = {"F32": "Float32", "U8": "Byte", "S16": "Int16"}


def _descriptor(path: Path) -> dict:
    raster = arcpy.Raster(str(path))
    extent = raster.extent
    data_type = ARCGIS_TYPES.get(raster.pixelType)
    if data_type is None:
        raise RuntimeError("unexpected_disposable_raster_type")
    return {
        "width": int(raster.width), "height": int(raster.height),
        "band_count": int(raster.bandCount), "data_type": data_type,
        "grid": {
            "wkid": int(raster.spatialReference.factoryCode),
            "cell_size_x": float(raster.meanCellWidth),
            "cell_size_y": float(raster.meanCellHeight),
            "origin_x": float(extent.XMin), "origin_y": float(extent.YMax),
            "xmin": float(extent.XMin), "ymin": float(extent.YMin),
            "xmax": float(extent.XMax), "ymax": float(extent.YMax),
            "rotation_degrees": 0.0,
        },
    }


def main() -> int:
    os_temp_root = Path(tempfile.gettempdir()).resolve()
    with tempfile.TemporaryDirectory(prefix="nepal-hyp3-arcgis-synthetic-", dir=os_temp_root) as dirname:
        disposable = Path(dirname).resolve()
        if disposable.parent != os_temp_root:
            raise RuntimeError("disposable_root_invalid")
        headers = {}
        for role, expected_type in RASTERS.items():
            values = np.ones((100, 100), dtype=DTYPES[expected_type])
            raster = arcpy.NumPyArrayToRaster(values, arcpy.Point(400000, 3199000), 10, 10)
            path = disposable / f"synthetic_{role}.tif"
            raster.save(str(path))
            arcpy.management.DefineProjection(str(path), arcpy.SpatialReference(32645))
            headers[role] = _descriptor(path)
            del raster
        result = inspect_raster_headers(ORDER[0], headers)
        if result["status"] != "pass_header_descriptor_rules_only":
            raise RuntimeError("synthetic_header_guard_failed")
        shifted = json.loads(json.dumps(headers))
        shifted["vh"]["grid"]["origin_x"] += 5.0
        shifted["vh"]["grid"]["xmin"] += 5.0
        shifted["vh"]["grid"]["xmax"] += 5.0
        try:
            inspect_raster_headers(ORDER[0], shifted)
        except ValueError:
            pass
        else:
            raise RuntimeError("synthetic_shift_not_rejected")
    print(json.dumps({
        "status": "pass_disposable_arcgis_header_runtime_only",
        "source_id": ORDER[0], "raster_count": len(RASTERS),
        "pixel_or_project_data_read": False, "provider_product_verified": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except Exception:
        print(json.dumps({"status": "stopped", "code": "arcgis_synthetic_runtime_failed"}, sort_keys=True))
        raise SystemExit(20) from None
    raise SystemExit(exit_code)
