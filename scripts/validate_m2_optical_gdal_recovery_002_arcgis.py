#!/usr/bin/env python3
"""Disposable GDAL and ArcPy parity on generated EPSG:32645 rasters only."""

from __future__ import annotations

import json
import copy
import tempfile
from pathlib import Path

import numpy as np
from osgeo import gdal, osr  # type: ignore[import-not-found]

from m2_optical_gdal_recovery_002_adapter import TARGET_GRID, describe, rasterize_aoi, tabulate_aoi, warp_target
from m2_optical_gdal_recovery_002_engine import qa_pair
from optical_input_readiness_core import validate_raster_description
from pixel_qa_core import load_contract


ROOT = Path(__file__).resolve().parents[1]
HEADER = json.loads((ROOT / "config/qa/optical-input-readiness-contract.json").read_text(encoding="utf-8"))
PIXEL = load_contract(ROOT / "config/qa/pixel-readiness-contract.json")
GRID = {"xmin": 273300.0, "ymin": 3070220.0, "xmax": 274500.0,
        "ymax": 3071420.0, "rows": 60, "columns": 60,
        "cell_size_m": 20.0, "wkid": 32645}


def write_jp2(path: Path, bands: list[np.ndarray], cell: float) -> None:
    temporary = path.with_suffix(".tif")
    height, width = bands[0].shape
    dtype = gdal.GDT_UInt16 if bands[0].dtype == np.uint16 else gdal.GDT_Byte
    raster = gdal.GetDriverByName("GTiff").Create(str(temporary), width, height, len(bands), dtype)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(32645)
    raster.SetProjection(srs.ExportToWkt())
    raster.SetGeoTransform((GRID["xmin"], cell, 0.0, GRID["ymax"], 0.0, -cell))
    for index, band in enumerate(bands, 1):
        raster.GetRasterBand(index).WriteArray(band)
    raster.Close()
    source = gdal.OpenEx(str(temporary), gdal.OF_RASTER | gdal.OF_READONLY)
    encoded = gdal.GetDriverByName("JP2OpenJPEG").CreateCopy(
        str(path), source, strict=1, options=["REVERSIBLE=YES", "QUALITY=100", "YCC=NO"]
    )
    if encoded is None:
        raise RuntimeError("disposable_jp2_create_failed")
    encoded.Close()
    source.Close()


def main() -> int:
    gdal.UseExceptions()
    gdal.SetConfigOption("PROJ_NETWORK", "OFF")
    with tempfile.TemporaryDirectory(prefix="nepal-optical-gdal-parity-") as folder:
        root = Path(folder)
        scl = root / "generated_scl.jp2"
        quality = root / "generated_quality.jp2"
        b11 = root / "generated_b11.jp2"
        scl_data = np.full((60, 60), 4, dtype=np.uint8)
        scl_data[0:3, 0:3] = 9
        quality_data = [np.zeros((20, 20), dtype=np.uint8) for _ in range(3)]
        quality_data[0][0, 0] = 1
        b11_data = (np.arange(3600, dtype=np.uint16).reshape((60, 60)) + 100).astype(np.uint16)
        b11_data[10, 10] = 0
        write_jp2(scl, [scl_data], 20.0)
        write_jp2(quality, quality_data, 60.0)
        write_jp2(b11, [b11_data], 20.0)
        descriptions = {"SCL": describe(scl), "quality_classification": describe(quality), "B11": describe(b11)}
        for role, description in descriptions.items():
            if validate_raster_description(role, description, HEADER):
                raise RuntimeError("disposable_header_predicate_failed")
        scl_target = warp_target(scl, "SCL", GRID)
        quality_target = warp_target(quality, "quality_classification", GRID)
        b11_target = warp_target(b11, "B11", GRID)
        if not np.array_equal(scl_target, scl_data) or not np.array_equal(b11_target, b11_data):
            raise RuntimeError("disposable_pixel_decode_drift")
        expected_mask = np.zeros((3, 60, 60), dtype=np.uint8)
        expected_mask[0, 0:3, 0:3] = 1
        if not np.array_equal(quality_target, expected_mask):
            raise RuntimeError("disposable_quality_semantics_drift")
        feature = {"attributes": {"AOI_ID": "AOI-SOURCE"}, "geometry": {"rings": [[
            [GRID["xmin"], GRID["ymin"]], [GRID["xmax"], GRID["ymin"]],
            [GRID["xmax"], GRID["ymax"]], [GRID["xmin"], GRID["ymax"]],
            [GRID["xmin"], GRID["ymin"]]
        ]]}}
        mask = rasterize_aoi(feature, GRID)
        if not mask.all():
            raise RuntimeError("disposable_aoi_rasterization_drift")
        import arcpy  # type: ignore[import-not-found]
        from run_m2_optical_pixel_readiness_001 import read_target

        observed_arcgis = arcpy.RasterToNumPyArray(str(scl))
        if not np.array_equal(observed_arcgis, scl_target):
            raise RuntimeError("disposable_arcgis_scl_parity_failed")
        for role, path, target, fill in (
            ("SCL", scl, scl_target, 255),
            ("B11", b11, b11_target, 65535),
            ("quality_classification", quality, quality_target, 255),
        ):
            observed = read_target(arcpy, path, GRID, fill)
            if not np.array_equal(observed, target):
                raise RuntimeError(f"disposable_arcgis_{role}_target_parity_failed")
        status = tabulate_aoi(np.ones((60, 60), dtype=np.int16), feature, PIXEL, False, GRID)
        if status["status"] != "pass_qa_only" or status["covered_area_m2"] != 60 * 60 * 400:
            raise RuntimeError("disposable_aoi_decision_parity_failed")
        settings = copy.deepcopy(json.loads((ROOT / "config/qa/optical-pixel-readiness-contract-001.json").read_text(encoding="utf-8")))
        settings["analysis_grid"].update({"extent": {key: GRID[key] for key in ("xmin", "ymin", "xmax", "ymax")},
                                          "rows": 60, "columns": 60})

        def square(identifier: str, xmin: float, ymin: float, xmax: float, ymax: float):
            return {"attributes": {"AOI_ID": identifier}, "geometry": {"rings": [[
                [xmin, ymin], [xmax, ymin], [xmax, ymax], [xmin, ymax], [xmin, ymin]
            ]]}}

        aoi = {"features": [
            square("AOI-OVERVIEW", GRID["xmin"], GRID["ymin"], GRID["xmax"], GRID["ymax"]),
            square("AOI-SOURCE", GRID["xmin"] + 100, GRID["ymin"] + 100,
                   GRID["xmin"] + 300, GRID["ymin"] + 300),
            square("AOI-UPPER-CORRIDOR", GRID["xmin"] + 400, GRID["ymin"] + 400,
                   GRID["xmin"] + 600, GRID["ymin"] + 600),
        ]}
        header = {"status": "pass_header_readability_only", "pair": ["M2-OPT-001", "M2-OPT-002"],
                  "products": {source: {"descriptions": descriptions} for source in ("M2-OPT-001", "M2-OPT-002")}}
        pixel = qa_pair([{"SCL": scl, "B11": b11, "quality_classification": quality}] * 2,
                        header, grid=GRID, aoi=aoi, settings=settings, pixel_contract=PIXEL,
                        output_root=root)
        if {item["aoi_id"] for item in pixel["aoi_metrics"]} != {
                "AOI-OVERVIEW", "AOI-SOURCE", "AOI-UPPER-CORRIDOR"}:
            raise RuntimeError("disposable_end_to_end_aoi_set_failed")
        if pixel["status"] not in {"pass_qa_only", "defer", "block", "invalid"} or not pixel["classification_sha256"]:
            raise RuntimeError("disposable_end_to_end_pixel_decision_failed")
        if arcpy.CheckExtension("Spatial") != "Available":
            raise RuntimeError("disposable_spatial_analyst_unavailable")
        arcpy.CheckOutExtension("Spatial")
        try:
            geodatabase = root / "disposable_parity.gdb"
            arcpy.management.CreateFileGDB(str(root), geodatabase.name)
            feature_class = str(geodatabase / "SyntheticAOIs")
            arcpy.management.CreateFeatureclass(str(geodatabase), "SyntheticAOIs", "POLYGON",
                                                spatial_reference=arcpy.SpatialReference(32645))
            arcpy.management.AddField(feature_class, "AOI_ID", "TEXT", field_length=40)
            with arcpy.da.InsertCursor(feature_class, ["AOI_ID", "SHAPE@"]) as cursor:
                for item in aoi["features"]:
                    points = [arcpy.Point(*pair) for pair in item["geometry"]["rings"][0]]
                    polygon = arcpy.Polygon(arcpy.Array(points), arcpy.SpatialReference(32645))
                    cursor.insertRow((item["attributes"]["AOI_ID"], polygon))
            table = str(geodatabase / "SyntheticTabulate")
            arcpy.sa.TabulateArea(feature_class, "AOI_ID",
                                  str(root / "pair_usability_classification_20m.tif"),
                                  "Value", table, 20.0, "CLASSES_AS_FIELDS")
            field_names = [field.name for field in arcpy.ListFields(table)]
            area_fields = [name for name in field_names if name.upper().startswith("VALUE_")]
            with arcpy.da.SearchCursor(table, ["AOI_ID", *area_fields]) as cursor:
                arcgis_areas = {row[0]: sum(float(value or 0) for value in row[1:]) for row in cursor}
            for item in pixel["aoi_metrics"]:
                if abs(arcgis_areas[item["aoi_id"]] - item["covered_area_m2"]) > 400.0:
                    raise RuntimeError("disposable_arcgis_aoi_tabulation_parity_failed")
        finally:
            arcpy.CheckInExtension("Spatial")
            arcpy.management.ClearWorkspaceCache()
            arcpy.management.Delete(str(geodatabase))
        source_width = int(np.ceil((TARGET_GRID["xmax"] - TARGET_GRID["xmin"]) / 60.0))
        source_height = int(np.ceil((TARGET_GRID["ymax"] - TARGET_GRID["ymin"]) / 60.0))
        full_source = gdal.GetDriverByName("MEM").Create("", source_width, source_height, 3, gdal.GDT_Byte)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(32645)
        full_source.SetProjection(srs.ExportToWkt())
        full_source.SetGeoTransform((TARGET_GRID["xmin"], 60.0, 0.0,
                                     TARGET_GRID["ymax"], 0.0, -60.0))
        full_source.GetRasterBand(1).WriteArray(np.array([[1]], dtype=np.uint8), 0, 0)
        full_source.GetRasterBand(2).WriteArray(np.array([[1]], dtype=np.uint8), source_width // 2, source_height // 2)
        full_source.GetRasterBand(3).WriteArray(np.array([[1]], dtype=np.uint8), source_width - 1, source_height - 1)
        full_path = root / "generated_production_shape_quality.jp2"
        encoded = gdal.GetDriverByName("JP2OpenJPEG").CreateCopy(
            str(full_path), full_source, strict=1, options=["REVERSIBLE=YES", "QUALITY=100", "YCC=NO"]
        )
        if encoded is None:
            raise RuntimeError("disposable_production_jp2_create_failed")
        encoded.Close()
        full_source.Close()
        full_target = warp_target(full_path, "quality_classification")
        if full_target.shape != (3, 3950, 4726) or np.count_nonzero(full_target[0]) != 9:
            raise RuntimeError("disposable_production_shape_mask_drift")
        if np.any(full_target[0, :3, :3] != 1) or np.any(full_target[1, 100:103, 100:103] != 0):
            raise RuntimeError("disposable_production_shape_mask_semantics_drift")
    print(json.dumps({"status": "pass_disposable_gdal_arcgis_header_mask_grid_aoi_parity",
                      "project_data_accessed": False, "real_attempt_started": False,
                      "network_or_credentials": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
