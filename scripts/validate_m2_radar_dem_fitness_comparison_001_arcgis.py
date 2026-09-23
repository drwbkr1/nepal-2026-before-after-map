#!/usr/bin/env python3
"""Validate the installed ArcGIS block reader on disposable in-memory rasters."""

from __future__ import annotations

import json

import numpy as np
import m2_radar_dem_fitness_comparison_001 as comparison

from m2_radar_dem_fitness_comparison_001 import (
    AOI_REF, ROOT, RUNTIME_REF, aoi_native_rings, inspect_no_content,
    load_json, scan_native_raster, write_new_json,
)


def main() -> int:
    import arcpy  # type: ignore[import-not-found]

    runtime = inspect_no_content(arcpy)
    if arcpy.CheckOutExtension("ImageAnalyst") != "CheckedOut":
        raise SystemExit("disposable Image Analyst checkout failed")
    try:
        arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(4326)
        arcpy.env.overwriteOutput = False
        gamma_data = np.stack((np.ones((4, 4), dtype=np.float32), np.full((4, 4), 2.0, dtype=np.float32)))
        gamma_data[:, 0, 0] = -9999.0
        dem_data = np.ones((4, 4), dtype=np.float32)
        dem_data[0, 0] = -9999.0
        gamma = arcpy.NumPyArrayToRaster(gamma_data, arcpy.Point(84.8, 27.8), 0.01, 0.01, value_to_nodata=-9999.0)
        dem = arcpy.NumPyArrayToRaster(dem_data, arcpy.Point(84.8, 27.8), 0.01, 0.01, value_to_nodata=-9999.0)
        rings = aoi_native_rings(arcpy, load_json(ROOT / AOI_REF), 4326)
        original_block = comparison.BLOCK_SIZE
        comparison.BLOCK_SIZE = 2
        try:
            gamma_audit = scan_native_raster(arcpy, gamma, rings, 2)
            dem_audit = scan_native_raster(arcpy, dem, rings, 1)
        finally:
            comparison.BLOCK_SIZE = original_block
        gamma_overview = gamma_audit["aois"]["AOI-OVERVIEW"]
        dem_overview = dem_audit["aois"]["AOI-OVERVIEW"]
        if (
            gamma_audit["block_count"] != 4
            or dem_audit["block_count"] != 4
            or gamma_overview["total_native_cell_centers"] != 16
            or gamma_overview["valid_per_band"] != [15, 15]
            or gamma_overview["valid_all_bands"] != 15
            or dem_overview["valid_per_band"] != [15]
            or dem_overview["valid_all_bands"] != 15
        ):
            raise SystemExit("disposable native-grid coverage result differs")
    finally:
        arcpy.CheckInExtension("ImageAnalyst")
    receipt = {
        "schema_version": "1.0", "record_id": "NEPAL-M2-RADAR-DEM-FITNESS-COMPARISON-001-ARCGIS-RUNTIME-VALIDATION",
        "status": "pass_installed_disposable_native_grid_and_multiband_validation",
        "runtime": runtime,
        "synthetic": {"gamma": gamma_audit, "dem": dem_audit},
        "assertions": {"project_data_content_read": False, "external_custody_accessed": False, "gtc_called": False, "disposable_in_memory_rasters_only": True, "disposable_file_output_created": False, "image_analyst_checked_in": True, "network_or_credentials_used": False, "scientific_result_established": False},
    }
    write_new_json(ROOT / RUNTIME_REF, receipt)
    print(json.dumps({"status": receipt["status"], "receipt": RUNTIME_REF}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
