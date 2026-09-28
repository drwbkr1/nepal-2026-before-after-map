#!/usr/bin/env python3
"""Installed ArcGIS test of the after-header worker on disposable RTC files."""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile

import numpy as np
from osgeo import gdal, osr

from m2_asf_hyp3_rtc_after_header_001 import inspect_once
from m2_asf_hyp3_rtc_header_core_001 import RASTERS
from m2_asf_hyp3_rtc_package_core_001 import REQUIRED_SUFFIXES
from m2_asf_hyp3_rtc_product_header_001 import ROLE_SUFFIX
from validate_m2_asf_hyp3_rtc_vsi_header_synthetic_001 import TYPES


BASE = "S1D_IW_20260828T122141_DVP_RTC10_G_gpuned_ABCD"
JOB_ID = "27836b79-e5b2-4d8f-932f-659724ea02c3"


def main() -> int:
    gdal.UseExceptions()
    osr.UseExceptions()
    with tempfile.TemporaryDirectory(prefix="nepal-hyp3-after-header-") as dirname:
        root = Path(dirname)
        archive = root / f"{BASE}.zip"
        spatial = osr.SpatialReference()
        spatial.ImportFromEPSG(32645)
        roles_by_suffix = {suffix: role for role, suffix in ROLE_SUFFIX.items()}
        with ZipFile(archive, "w", ZIP_STORED) as package:
            package.writestr(BASE + "/", b"")
            for suffix in REQUIRED_SUFFIXES:
                member = f"{BASE}/{BASE}{suffix}"
                if suffix in roles_by_suffix:
                    role = roles_by_suffix[suffix]
                    gdal_type, numpy_type = TYPES[RASTERS[role]]
                    path = root / f"{role}.tif"
                    dataset = gdal.GetDriverByName("GTiff").Create(
                        str(path), 100, 100, 1, gdal_type)
                    dataset.SetGeoTransform((400000.0, 10.0, 0.0,
                                             3200000.0, 0.0, -10.0))
                    dataset.SetProjection(spatial.ExportToWkt())
                    dataset.GetRasterBand(1).WriteArray(
                        np.ones((100, 100), dtype=numpy_type))
                    dataset = None
                    package.write(path, member)
                else:
                    package.writestr(member, b"disposable metadata")
        archive_sha = hashlib.sha256(archive.read_bytes()).hexdigest()
        acquisition = {"product_filename": archive.name,
                       "archive_size_bytes": archive.stat().st_size,
                       "archive_sha256": archive_sha}
        result = inspect_once(acquisition, archive,
                              root / "after-header" / "attempt",
                              controlled_root=root, job_id=JOB_ID)
        if (result["status"] != "pass_after_headers_for_local_pixel_qa_only"
                or len(result["headers"]) != 6
                or result["pixels_read"] is not False
                or hashlib.sha256(archive.read_bytes()).hexdigest() != archive_sha):
            raise RuntimeError("disposable_after_header_invalid")
    print(json.dumps({"status": "pass_disposable_after_six_headers_only",
                      "raster_count": 6, "project_product_opened": False,
                      "product_pixels_read": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        print(json.dumps({"status": "stopped",
                          "code": "disposable_after_header_validation_failed"}))
        raise SystemExit(20) from None
