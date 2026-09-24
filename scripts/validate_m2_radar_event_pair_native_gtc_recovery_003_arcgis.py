#!/usr/bin/env python3
"""One disposable ArcGIS check of recovery-003 grid mechanics; never read project data."""

from __future__ import annotations

import json
import math
import os
import tempfile
import traceback
from pathlib import Path

import numpy as np  # type: ignore
import arcpy  # type: ignore

from m2_dem_vertical_datum_proj25_core import sha256_file
from m2_radar_event_pair_native_gtc_recovery_003_core import (
    TARGET, NativeGridStop, inspect_returned_raster, native_gtc_environment,
    project_with_frozen_extent,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "records/readiness/m2-radar-event-area-pair-native-gtc-grid-recovery-003-arcgis-disposable-validation-007.json"


def same_environment_setting(name: str, left: object, right: object) -> bool:
    if name == "outputCoordinateSystem" and left is not None and right is not None:
        return (int(left.factoryCode) == int(right.factoryCode)
                and left.exportToString() == right.exportToString())
    if name == "extent" and left is not None and right is not None:
        return all(float(getattr(left, key)) == float(getattr(right, key))
                   for key in ("XMin", "YMin", "XMax", "YMax"))
    return str(left) == str(right)


def run() -> dict:
    if OUTPUT.exists():
        raise RuntimeError("recovery_003_disposable_receipt_collision")
    os.environ["PROJ_NETWORK"] = "OFF"
    checked_out = arcpy.CheckOutExtension("Spatial")
    if checked_out != "CheckedOut":
        raise RuntimeError("spatial_analyst_unavailable")
    try:
        with tempfile.TemporaryDirectory(prefix="nepal-native-gtc-recovery-003-disposable-", ignore_cleanup_errors=True) as temporary:
            scratch = Path(temporary)
            source = scratch / "native_4326.tif"
            categorical = scratch / "native_mask_4326.tif"
            snap = scratch / "snap_32645.tif"
            projected = scratch / "projected_32645.tif"
            projected_mask = scratch / "projected_mask_32645.tif"
            broad_source = scratch / "broad_4326.tif"
            broad_projected = scratch / "broad_projected_32645.tif"
            arcpy.env.overwriteOutput = False
            arcpy.NumPyArrayToRaster(np.full((512, 512), 7.0, dtype=np.float32),
                                    arcpy.Point(85.15, 28.0), 0.00025, 0.00025).save(str(source))
            mask_values = np.ones((512, 512), dtype=np.uint8)
            mask_values[100:200, 100:200] = 3
            arcpy.NumPyArrayToRaster(mask_values, arcpy.Point(85.15, 28.0), 0.00025, 0.00025).save(str(categorical))
            arcpy.management.DefineProjection(str(source), arcpy.SpatialReference(4326))
            arcpy.management.DefineProjection(str(categorical), arcpy.SpatialReference(4326))
            arcpy.NumPyArrayToRaster(np.zeros((2, 2), dtype=np.uint8),
                                    arcpy.Point(TARGET[0], TARGET[1]), 10, 10).save(str(snap))
            arcpy.management.DefineProjection(str(snap), arcpy.SpatialReference(32645))
            saved_prior = {name: getattr(arcpy.env, name) for name in
                           ("cellSize", "snapRaster", "outputCoordinateSystem", "extent", "resamplingMethod")}
            clear_records = []
            try:
                arcpy.env.cellSize = 10.0
                arcpy.env.snapRaster = str(snap)
                arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(32645)
                arcpy.env.extent = arcpy.Extent(*TARGET, spatial_reference=arcpy.SpatialReference(32645))
                configured = {name: getattr(arcpy.env, name) for name in saved_prior}
                with native_gtc_environment(arcpy, resampling="BILINEAR", record_environment=clear_records.append):
                    native = arcpy.sa.Int(arcpy.Raster(str(categorical)))
                    native_metadata = inspect_returned_raster(
                        native, source_bounds=(84.0, 27.0, 87.0, 30.0),
                        aoi_bounds=((85.16, 28.02, 85.18, 28.04),))
                restored = {name: getattr(arcpy.env, name) for name in saved_prior}
                drift = [name for name in saved_prior
                         if not same_environment_setting(name, configured[name], restored[name])]
                if drift:
                    raise RuntimeError("native_environment_not_restored:" + ",".join(drift))
            finally:
                for name, value in saved_prior.items():
                    setattr(arcpy.env, name, value)
            continuous_grid = project_with_frozen_extent(arcpy, source, projected, snap, categorical=False)
            categorical_grid = project_with_frozen_extent(arcpy, categorical, projected_mask, snap, categorical=True)
            if continuous_grid["cells"] > 100_000_000 or categorical_grid["cells"] > 100_000_000:
                raise RuntimeError("disposable_projected_grid_cap_failed")
            center = arcpy.PointGeometry(arcpy.Point(85.19, 28.09), arcpy.SpatialReference(4326)).projectAs(
                arcpy.SpatialReference(32645)).firstPoint
            values = arcpy.RasterToNumPyArray(str(projected_mask),
                                              lower_left_corner=arcpy.Point(center.X - 1500, center.Y - 1500),
                                              ncols=300, nrows=300, nodata_to_value=255)
            observed = {int(value) for value in np.unique(values)}
            if not observed.issubset({1, 3, 255}) or 1 not in observed or 3 not in observed:
                raise RuntimeError("categorical_mask_classes_not_preserved")
            projected_crs = arcpy.SpatialReference(32645)
            geographic_crs = arcpy.SpatialReference(4326)
            projected_corners = ((TARGET[0], TARGET[1]), (TARGET[0], TARGET[3]),
                                 (TARGET[2], TARGET[1]), (TARGET[2], TARGET[3]))
            geographic_corners = [arcpy.PointGeometry(arcpy.Point(x, y), projected_crs).projectAs(geographic_crs).firstPoint
                                  for x, y in projected_corners]
            west = min(point.X for point in geographic_corners) - 0.002
            east = max(point.X for point in geographic_corners) + 0.002
            south = min(point.Y for point in geographic_corners) - 0.002
            north = max(point.Y for point in geographic_corners) + 0.002
            wide_columns = math.ceil((east - west) / 0.001)
            wide_rows = math.ceil((north - south) / 0.001)
            arcpy.NumPyArrayToRaster(np.full((wide_rows, wide_columns), 7.0, dtype=np.float32),
                                    arcpy.Point(west, south), 0.001, 0.001).save(str(broad_source))
            arcpy.management.DefineProjection(str(broad_source), arcpy.SpatialReference(4326))
            try:
                broad_grid = project_with_frozen_extent(arcpy, broad_source, broad_projected, snap, categorical=False)
            except NativeGridStop as exc:
                description = arcpy.Describe(str(broad_projected))
                extent = description.extent
                return {"schema_version": "1.0", "status": "block_disposable_broad_projected_guard",
                        "guard_code": str(exc),
                        "observed_broad_grid": {"wkid": int(description.spatialReference.factoryCode),
                                                "width": int(description.width), "height": int(description.height),
                                                "cells": int(description.width) * int(description.height),
                                                "bounds": [float(extent.XMin), float(extent.YMin),
                                                           float(extent.XMax), float(extent.YMax)]},
                        "generated_source_shape": [wide_rows, wide_columns],
                        "project_data_or_external_custody_accessed": False,
                        "sar_specific_gtc_fitness_proven": False}
            box = broad_grid["bounds"]
            if (box[0] > TARGET[0] or box[1] > TARGET[1]
                    or box[2] < TARGET[2] or box[3] < TARGET[3]):
                raise RuntimeError("broad_disposable_target_not_covered")
            return {
                "schema_version": "1.0", "status": "pass_disposable_arcgis_grid_mechanics_only",
                "arcgis_version": arcpy.GetInstallInfo().get("Version"),
                "native_generated_raster_metadata": native_metadata,
                "cleared_environment": clear_records,
                "environment_restored": True,
                "continuous_projected_grid": continuous_grid,
                "categorical_projected_grid": categorical_grid,
                "broad_projected_grid": broad_grid,
                "categorical_values_in_sample": sorted(observed),
                "core_sha256": sha256_file(ROOT / "scripts/m2_radar_event_pair_native_gtc_recovery_003_core.py"),
                "processing_sha256": sha256_file(ROOT / "scripts/m2_radar_event_pair_native_gtc_recovery_003_processing.py"),
                "project_data_or_external_custody_accessed": False,
                "sar_specific_gtc_fitness_proven": False,
                "baseline_or_change_analysis_authorized": False,
            }
    finally:
        arcpy.CheckInExtension("Spatial")


def main() -> int:
    try:
        record = run()
    except Exception as exc:
        frame = traceback.extract_tb(exc.__traceback__)[-1]
        known = {"disposable_projected_grid_cap_failed", "broad_disposable_target_not_covered",
                 "categorical_mask_classes_not_preserved", "spatial_analyst_unavailable"}
        if type(exc) is RuntimeError and str(exc).startswith("native_environment_not_restored:"):
            code = str(exc)
        else:
            code = str(exc) if type(exc) is RuntimeError and str(exc) in known else getattr(exc, "code", "arcgis_disposable_error")
        record = {"schema_version": "1.0", "status": "block_disposable_arcgis_mechanics",
                  "failure_type": type(exc).__name__,
                  "failure_code": code,
                  "failure_site": {"function": frame.name, "line": frame.lineno},
                  "project_data_or_external_custody_accessed": False,
                  "sar_specific_gtc_fitness_proven": False}
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"status": record["status"]}))
    return 0 if record["status"] == "pass_disposable_arcgis_grid_mechanics_only" else 20


if __name__ == "__main__":
    raise SystemExit(main())
