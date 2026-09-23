#!/usr/bin/env python3
"""Disposable ArcGIS runtime check for the exact pair-mask operators and signatures."""

from __future__ import annotations

import json
import gc
import tempfile
from pathlib import Path

import numpy as np  # type: ignore
import arcpy  # type: ignore

from m2_dem_vertical_datum_proj25_core import sha256_file
from m2_radar_esri_sequence_processing_005 import arcgis_signature_status


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "records/readiness/m2-radar-event-area-pair-001-radar-arcgis-runtime-validation.json"


def save_array(path: Path, values: np.ndarray, *, nodata: int | None = None) -> None:
    raster = arcpy.NumPyArrayToRaster(values, arcpy.Point(0, 0), 10, 10, value_to_nodata=nodata)
    raster.save(str(path))


def main() -> int:
    if OUTPUT.exists():
        raise RuntimeError("radar_disposable_runtime_receipt_collision")
    signatures = arcgis_signature_status(arcpy)
    if not signatures["all_match"] or arcpy.CheckOutExtension("Spatial") != "CheckedOut":
        raise RuntimeError("arcgis_required_signature_or_spatial_extension_unavailable")
    try:
        with tempfile.TemporaryDirectory(prefix="nepal-event-pair-radar-disposable-") as directory:
            root = Path(directory)
            before_values = np.ones((32, 32), dtype=np.int16)
            before_values[8, 8] = -9999
            before_mask_values = np.ones((32, 32), dtype=np.int16)
            after_mask_values = np.ones((32, 32), dtype=np.int16)
            before_mask_values[5, 5] = 4
            after_mask_values[6, 6] = 3
            before_mask_values[7, 7] = 0
            before = root / "before.tif"
            after = root / "after.tif"
            before_mask_path = root / "before_mask.tif"
            after_mask_path = root / "after_mask.tif"
            save_array(before, before_values, nodata=-9999)
            save_array(after, np.ones((32, 32), dtype=np.int16))
            save_array(before_mask_path, before_mask_values)
            save_array(after_mask_path, after_mask_values)
            before_raster = arcpy.Raster(str(before))
            after_raster = arcpy.Raster(str(after))
            before_mask = arcpy.sa.Int(arcpy.sa.Raster(str(before_mask_path)) + 0.5)
            after_mask = arcpy.sa.Int(arcpy.sa.Raster(str(after_mask_path)) + 0.5)
            covered = (~arcpy.sa.IsNull(before_raster)) & (~arcpy.sa.IsNull(after_raster))
            layover = (before_mask == 4) | (before_mask == 5) | (after_mask == 4) | (after_mask == 5)
            shadow = (before_mask == 3) | (after_mask == 3)
            undetermined = (before_mask == 0) | (after_mask == 0)
            geometric_valid = ((before_mask == 1) | (before_mask == 2)) & ((after_mask == 1) | (after_mask == 2))
            categorical = arcpy.sa.Con(layover, 2, arcpy.sa.Con(shadow, 3, arcpy.sa.Con(undetermined, 0, arcpy.sa.Con(geometric_valid, 1, 90))))
            output = root / "pair_mask.tif"
            arcpy.sa.SetNull(~covered, categorical).save(str(output))
            observed = arcpy.RasterToNumPyArray(str(output), nodata_to_value=255)
            if (observed.shape != (32, 32) or int(observed[0, 0]) != 1 or int(observed[5, 5]) != 2
                    or int(observed[6, 6]) != 3 or int(observed[7, 7]) != 0 or int(observed[8, 8]) != 255):
                raise RuntimeError("disposable_event_pair_mask_semantics_failed")
            del observed, categorical, geometric_valid, undetermined, shadow, layover, covered
            del before_mask, after_mask, before_raster, after_raster
            gc.collect()
            arcpy.management.ClearWorkspaceCache()
    finally:
        arcpy.CheckInExtension("Spatial")
    record = {
        "schema_version": "1.0",
        "status": "pass_disposable_arcgis_event_pair_mask_and_signatures",
        "runner_sha256": sha256_file(ROOT / "scripts/m2_radar_event_pair_processing_001.py"),
        "arcgis_version": arcpy.GetInstallInfo().get("Version"),
        "all_required_raster_function_signatures_match": True,
        "disposable_pixel_count": 1024,
        "valid_layover_shadow_undetermined_and_nodata_predicates_pass": True,
        "project_data_or_external_custody_accessed": False,
        "radar_geoprocessing_on_project_data": False,
    }
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"status": record["status"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
