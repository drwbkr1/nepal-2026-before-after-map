#!/usr/bin/env python3
"""Disposable ArcGIS-runtime GDAL test; reads no project raster or SAFE."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np  # type: ignore
from osgeo import gdal, ogr  # type: ignore

from m2_dem_vertical_datum_proj25_core import sha256_file
from m2_radar_event_pair_dem_footprint_gate_001 import polygon_from_ring, scan_dem_validity


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "records/readiness/m2-radar-event-area-pair-001-footprint-arcgis-runtime-validation-final.json"


def main() -> int:
    if OUTPUT.exists():
        raise RuntimeError("disposable_runtime_receipt_collision")
    gdal.UseExceptions()
    dataset = gdal.GetDriverByName("MEM").Create("", 100, 100, 1, gdal.GDT_Float32)
    dataset.SetGeoTransform((84.0, 0.001, 0, 29.0, 0, -0.001))
    spatial = ogr.osr.SpatialReference()
    spatial.ImportFromEPSG(4326)
    dataset.SetProjection(spatial.ExportToWkt())
    band = dataset.GetRasterBand(1)
    band.SetNoDataValue(-9999.0)
    band.WriteArray(np.full((100, 100), 120.0, dtype=np.float32))
    ring = [(84.02, 28.98), (84.08, 28.98), (84.08, 28.92), (84.02, 28.92)]
    geometry = polygon_from_ring(ring, ogr)
    valid = scan_dem_validity(dataset, [geometry, geometry], gdal=gdal, ogr=ogr, np=np)
    values = np.full((100, 100), 120.0, dtype=np.float32)
    values[40:50, 40:50] = -9999.0
    band.WriteArray(values)
    blocked = scan_dem_validity(dataset, [geometry, geometry], gdal=gdal, ogr=ogr, np=np)
    if (valid["dem_grid_cells_in_full_buffered_footprint"] == 0 or valid["invalid_dem_cells"] != 0
            or blocked["invalid_dem_cells"] != 100):
        raise RuntimeError("disposable_valid_and_nodata_predicates_failed")
    result = {
        "schema_version": "1.0",
        "status": "pass_disposable_arcgis_runtime_footprint_mask_and_nodata_rejection",
        "production_code_sha256": sha256_file(ROOT / "scripts/m2_radar_event_pair_dem_footprint_gate_001.py"),
        "disposable_raster_cells": 10000,
        "valid_case_selected_cells": valid["dem_grid_cells_in_full_buffered_footprint"],
        "valid_case_invalid_cells": valid["invalid_dem_cells"],
        "nodata_case_invalid_cells": blocked["invalid_dem_cells"],
        "project_data_or_external_custody_accessed": False,
    }
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"status": result["status"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
