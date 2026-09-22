#!/usr/bin/env python3
"""Validate installed GTC signature and a disposable raster, without project data."""

from __future__ import annotations

import json
import numpy as np

from m2_radar_gtc_dem_isolation_probe_001 import ROOT, RUNTIME_REF, inspect_no_content, write_new_json


def main() -> int:
    import arcpy  # type: ignore[import-not-found]

    runtime = inspect_no_content(arcpy)
    if arcpy.CheckOutExtension("ImageAnalyst") != "CheckedOut":
        raise SystemExit("Image Analyst checkout failed in disposable validation")
    try:
        raster = arcpy.NumPyArrayToRaster(np.ones((2, 2), dtype=np.uint8), arcpy.Point(0, 0), 10, 10)
        if raster.__class__.__name__ != "Raster":
            raise SystemExit("Disposable raster constructor returned a non-Raster")
    finally:
        arcpy.CheckInExtension("ImageAnalyst")
    receipt = {
        "schema_version": "1.0", "record_id": "NEPAL-M2-RADAR-GTC-DEM-ISOLATION-PROBE-001-ARCGIS-RUNTIME-VALIDATION",
        "status": "pass_installed_signature_and_disposable_raster_construct_only", "runtime": runtime,
        "assertions": {"project_data_content_read": False, "external_custody_accessed": False, "gtc_called": False, "disposable_raster_constructed": True, "disposable_file_output_created": False, "image_analyst_checked_in": True, "network_or_credentials_used": False, "scientific_result_established": False},
    }
    write_new_json(ROOT / RUNTIME_REF, receipt)
    print(json.dumps({"status": receipt["status"], "receipt": RUNTIME_REF}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
