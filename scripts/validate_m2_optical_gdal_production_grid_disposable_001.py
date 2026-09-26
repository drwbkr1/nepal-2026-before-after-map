#!/usr/bin/env python3
"""Source-free, production-shape GDAL mask resampling check for the optical route."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
from osgeo import gdal, osr  # type: ignore[import-not-found]


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config/qa/optical-baseline-processing-contract.json"
SOURCE_CELL_M = 60


def indices_for_source_cell(origin: float, cell: float, source_index: int,
                            target_origin: float, target_cell: float, count: int) -> list[int]:
    """Return target cell-center indices within one source cell on one axis."""
    start = origin + source_index * cell
    stop = start + cell
    return [
        index for index in range(count)
        if start <= target_origin + (index + 0.5) * target_cell < stop
    ]


def main() -> int:
    gdal.UseExceptions()
    gdal.SetConfigOption("PROJ_NETWORK", "OFF")
    gdal.SetConfigOption("GDAL_PAM_ENABLED", "NO")
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    grid = contract["analysis_grid"]
    extent = grid["extent"]
    xmin, ymin = float(extent["xmin"]), float(extent["ymin"])
    xmax, ymax = float(extent["xmax"]), float(extent["ymax"])
    width, height = int(grid["columns"]), int(grid["rows"])
    cell = float(grid["cell_size_m"])
    if int(grid["wkid"]) != 32645 or cell != 20.0:
        raise RuntimeError("frozen_optical_grid_changed")
    if (xmax - xmin, ymax - ymin) != (width * cell, height * cell):
        raise RuntimeError("frozen_optical_grid_dimensions_mismatch")
    source_width = int(np.ceil((xmax - xmin) / SOURCE_CELL_M))
    source_height = int(np.ceil((ymax - ymin) / SOURCE_CELL_M))
    source = gdal.GetDriverByName("MEM").Create("", source_width, source_height, 3, gdal.GDT_Byte)
    if source is None:
        raise RuntimeError("disposable_source_create_failed")
    target = None
    reopened = None
    try:
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(32645)
        source.SetProjection(srs.ExportToWkt())
        source.SetGeoTransform((xmin, SOURCE_CELL_M, 0.0, ymax, 0.0, -SOURCE_CELL_M))
        marks = [(0, 0), (source_width // 2, source_height // 2),
                 (source_width - 1, source_height - 1)]
        for band_number, (source_column, source_row) in enumerate(marks, start=1):
            source.GetRasterBand(band_number).WriteArray(
                np.array([[band_number]], dtype=np.uint8), source_column, source_row
            )
        with tempfile.TemporaryDirectory(prefix="nepal-optical-gdal-mask-") as folder:
            jp2_path = Path(folder) / "generated_quality_classification.jp2"
            encoded = gdal.GetDriverByName("JP2OpenJPEG").CreateCopy(
                str(jp2_path), source, strict=1,
                options=["REVERSIBLE=YES", "QUALITY=100", "YCC=NO"],
            )
            if encoded is None:
                raise RuntimeError("disposable_jp2_create_failed")
            encoded.Close()
            try:
                reopened = gdal.OpenEx(str(jp2_path), gdal.OF_RASTER | gdal.OF_READONLY)
                if reopened is None or reopened.GetDriver().ShortName not in {"JP2KAK", "JP2OpenJPEG"}:
                    raise RuntimeError("disposable_jp2_default_reader_failed")
                reader_driver = reopened.GetDriver().ShortName
                if (reopened.RasterXSize, reopened.RasterYSize, reopened.RasterCount) != (source_width, source_height, 3):
                    raise RuntimeError("disposable_jp2_source_dimensions_mismatch")
                for band_number, (source_column, source_row) in enumerate(marks, start=1):
                    observed_source = reopened.GetRasterBand(band_number).ReadAsArray()
                    source_locations = set(zip(*np.nonzero(observed_source), strict=True))
                    if source_locations != {(source_row, source_column)} or observed_source[source_row, source_column] != band_number:
                        raise RuntimeError(f"disposable_jp2_source_mask_mismatch_band_{band_number}")
                target = gdal.Warp(
                    "", reopened, format="MEM", outputBounds=(xmin, ymin, xmax, ymax),
                    width=width, height=height, dstSRS="EPSG:32645", resampleAlg="near",
                )
                if target is None or (target.RasterXSize, target.RasterYSize, target.RasterCount) != (width, height, 3):
                    raise RuntimeError("production_shape_target_dimensions_mismatch")
                if tuple(target.GetGeoTransform()) != (xmin, cell, 0.0, ymax, 0.0, -cell):
                    raise RuntimeError("production_shape_target_transform_mismatch")
                checks: list[dict[str, int]] = []
                for band_number, (source_column, source_row) in enumerate(marks, start=1):
                    columns = indices_for_source_cell(xmin, SOURCE_CELL_M, source_column,
                                                      xmin, cell, width)
                    rows = indices_for_source_cell(-ymax, SOURCE_CELL_M, source_row,
                                                   -ymax, cell, height)
                    # Y increases downward in the row-index calculation above.
                    observed = target.GetRasterBand(band_number).ReadAsArray()
                    locations = set(zip(*np.nonzero(observed), strict=True))
                    expected = {(row, column) for row in rows for column in columns}
                    if locations != expected or any(observed[row, column] != band_number for row, column in expected):
                        raise RuntimeError(f"production_shape_mask_mismatch_band_{band_number}")
                    checks.append({"band": band_number, "expected_nonzero_cells": len(expected),
                                   "observed_nonzero_cells": len(locations)})
            finally:
                if target is not None:
                    target.Close()
                    target = None
                if reopened is not None:
                    reopened.Close()
                    reopened = None
        print(json.dumps({
            "status": "pass_disposable_production_grid_jp2_mask_resampling_only",
            "gdal_version": gdal.VersionInfo("--version"),
            "generated_jp2_reader_driver": reader_driver,
            "generated_jp2_source_columns": source_width,
            "generated_jp2_source_rows": source_height,
            "projected_wkid": 32645,
            "target_columns": width, "target_rows": height,
            "target_cells_per_band": width * height,
            "source_cell_m": SOURCE_CELL_M, "target_cell_m": cell,
            "categorical_resampling": "NEAREST", "three_band_checks": checks,
            "proj_network": "OFF",
            "arcpy_imported": False, "real_source_or_external_custody_accessed": False,
            "real_product_pixels_examined": False, "new_real_attempt_started": False,
        }))
        return 0
    finally:
        if target is not None:
            target.Close()
        if reopened is not None:
            reopened.Close()
        source.Close()


if __name__ == "__main__":
    raise SystemExit(main())
