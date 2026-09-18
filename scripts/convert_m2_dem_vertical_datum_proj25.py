#!/usr/bin/env python3
"""Convert the four approved DEMs once, in order, with the local PROJ grid."""

from __future__ import annotations

import argparse
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from m2_dem_vertical_datum_proj25_core import (
    ROOT,
    controlled_path,
    load_contract,
    load_json,
    promote_no_replace,
    sha256_file,
    vertical_pipeline,
    write_new_json,
)


OPERATION_PREFLIGHT = ROOT / "records/acquisition/m2-dem-vertical-datum-proj25-operation-selection-sign-preflight.json"
BATCH_TERMINAL = ROOT / "records/processing/m2-dem-vertical-datum-proj25-conversion-batch-001.json"
AOI_REF = ROOT / "config/aoi/approved-study-areas.geojson"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def output_extent(geotransform: tuple[float, ...], width: int, height: int) -> tuple[float, float, float, float]:
    if geotransform[2] != 0.0 or geotransform[4] != 0.0 or geotransform[1] <= 0 or geotransform[5] >= 0:
        raise ValueError("only the exact north-up source grid is supported")
    xmin = geotransform[0]
    ymax = geotransform[3]
    xmax = xmin + geotransform[1] * width
    ymin = ymax + geotransform[5] * height
    return xmin, ymin, xmax, ymax


def same_geotransform(first: tuple[float, ...], second: tuple[float, ...], tolerance: float = 1e-12) -> bool:
    return len(first) == len(second) and all(abs(float(a) - float(b)) <= tolerance for a, b in zip(first, second))


def arcgis_readability(path: Path, width: int, height: int) -> dict[str, Any]:
    import arcpy  # type: ignore

    description = arcpy.Describe(str(path))
    raster = arcpy.Raster(str(path))
    if int(raster.width) != width or int(raster.height) != height:
        raise ValueError("ArcGIS dimensions differ")
    return {
        "readable": True,
        "data_type": str(description.dataType),
        "width": int(raster.width),
        "height": int(raster.height),
        "band_count": int(raster.bandCount),
        "spatial_reference_name": str(raster.spatialReference.name),
        "vertical_coordinate_system_name": str(raster.spatialReference.VCS.name)
        if raster.spatialReference.VCS else None,
        "runtime_version": arcpy.GetInstallInfo().get("Version"),
    }


def create_aoi_mask(width: int, height: int, geotransform: tuple[float, ...]) -> Any:
    from osgeo import gdal, ogr, osr  # type: ignore

    mask = gdal.GetDriverByName("MEM").Create("", width, height, 1, gdal.GDT_Byte)
    mask.SetGeoTransform(geotransform)
    spatial_reference = osr.SpatialReference()
    spatial_reference.ImportFromEPSG(4326)
    spatial_reference.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    mask.SetSpatialRef(spatial_reference)
    mask.GetRasterBand(1).Fill(0)
    vector = ogr.Open(str(AOI_REF), 0)
    if vector is None:
        raise ValueError("approved AOI could not be opened")
    layer = vector.GetLayer(0)
    if gdal.RasterizeLayer(mask, [1], layer, burn_values=[1], options=["ALL_TOUCHED=TRUE"]) != 0:
        raise ValueError("approved AOI mask rasterization failed")
    return mask


def verify_staged_output(source_path: Path, output_path: Path) -> dict[str, Any]:
    from osgeo import gdal, osr  # type: ignore
    import numpy as np  # type: ignore

    source = gdal.OpenEx(str(source_path), gdal.OF_RASTER | gdal.OF_READONLY)
    output = gdal.OpenEx(str(output_path), gdal.OF_RASTER | gdal.OF_READONLY)
    if source is None or output is None:
        raise ValueError("source or converted output is not GDAL-readable")
    width, height = int(source.RasterXSize), int(source.RasterYSize)
    if int(output.RasterXSize) != width or int(output.RasterYSize) != height:
        raise ValueError("converted dimensions differ")
    source_gt = tuple(float(value) for value in source.GetGeoTransform())
    output_gt = tuple(float(value) for value in output.GetGeoTransform())
    if not same_geotransform(source_gt, output_gt):
        raise ValueError("converted geotransform differs")
    output_srs = output.GetSpatialRef()
    if output_srs is None:
        raise ValueError("converted output CRS is absent")
    output_srs.AutoIdentifyEPSG()
    codes = {output_srs.GetAuthorityCode(None), output_srs.GetAuthorityCode("GEOGCRS")}
    if "4979" not in codes and "4979" not in output_srs.ExportToWkt():
        raise ValueError("converted output is not bound to EPSG:4979")
    source_band, output_band = source.GetRasterBand(1), output.GetRasterBand(1)
    source_nodata, output_nodata = source_band.GetNoDataValue(), output_band.GetNoDataValue()
    if source_nodata != output_nodata:
        raise ValueError("NoData semantics differ")
    if gdal.GetDataTypeName(output_band.DataType) != "Float32":
        raise ValueError("converted output is not Float32")
    mask = create_aoi_mask(width, height, source_gt)
    mask_band = mask.GetRasterBand(1)
    block_x, block_y = source_band.GetBlockSize()
    block_x = max(int(block_x), 256)
    block_y = max(int(block_y), 256)
    valid_count = aoi_count = aoi_nonfinite = nodata_mismatch = 0
    delta_count = 0
    delta_sum = delta_sum_squares = 0.0
    delta_min = math.inf
    delta_max = -math.inf
    samples: list[Any] = []
    for yoff in range(0, height, block_y):
        ysize = min(block_y, height - yoff)
        for xoff in range(0, width, block_x):
            xsize = min(block_x, width - xoff)
            source_values = np.asarray(source_band.ReadAsArray(xoff, yoff, xsize, ysize), dtype=np.float64)
            output_values = np.asarray(output_band.ReadAsArray(xoff, yoff, xsize, ysize), dtype=np.float64)
            valid = np.isfinite(source_values)
            if source_nodata is not None:
                valid &= source_values != float(source_nodata)
            output_valid = np.isfinite(output_values)
            if output_nodata is not None:
                output_valid &= output_values != float(output_nodata)
            nodata_mismatch += int(np.count_nonzero(valid != output_valid))
            if np.any(valid & ~np.isfinite(output_values)):
                raise ValueError("converted output contains nonfinite source-valid pixels")
            delta = output_values[valid] - source_values[valid]
            if delta.size:
                delta_count += int(delta.size)
                delta_sum += float(np.sum(delta, dtype=np.float64))
                delta_sum_squares += float(np.sum(delta * delta, dtype=np.float64))
                delta_min = min(delta_min, float(np.min(delta)))
                delta_max = max(delta_max, float(np.max(delta)))
                samples.append(delta[:: max(1, int(delta.size // 4096))])
            valid_count += int(np.count_nonzero(valid))
            aoi = np.asarray(mask_band.ReadAsArray(xoff, yoff, xsize, ysize), dtype=np.uint8) == 1
            aoi_count += int(np.count_nonzero(aoi))
            aoi_nonfinite += int(np.count_nonzero(aoi & ~output_valid))
    if valid_count == 0 or delta_count == 0 or nodata_mismatch != 0 or aoi_nonfinite != 0:
        raise ValueError("converted finite/NoData/AOI acceptance checks failed")
    sampled = np.concatenate(samples) if samples else np.array([], dtype=np.float64)
    mean = delta_sum / delta_count
    variance = max(0.0, delta_sum_squares / delta_count - mean * mean)
    source = output = mask = None
    return {
        "width": width,
        "height": height,
        "geotransform": list(source_gt),
        "same_dimensions": True,
        "same_geotransform": True,
        "source_nodata": source_nodata,
        "output_nodata": output_nodata,
        "nodata_mismatch_count": nodata_mismatch,
        "source_valid_pixel_count": valid_count,
        "approved_aoi_pixel_count": aoi_count,
        "approved_aoi_nonfinite_count": aoi_nonfinite,
        "correction_m": {
            "count": delta_count,
            "minimum": delta_min,
            "maximum": delta_max,
            "mean": mean,
            "standard_deviation": math.sqrt(variance),
            "sampled_p01": float(np.percentile(sampled, 1)),
            "sampled_p50": float(np.percentile(sampled, 50)),
            "sampled_p99": float(np.percentile(sampled, 99)),
            "sample_count": int(sampled.size),
        },
    }


def convert_one(item: dict[str, Any], grid: Path, started_at: str) -> dict[str, Any]:
    from osgeo import gdal  # type: ignore

    source_id = item["source_id"]
    attempt_id = f"{source_id.lower()}-proj25-conversion-001"
    public_started = ROOT / f"records/processing/{attempt_id}-started.json"
    public_terminal = ROOT / f"records/processing/{attempt_id}-terminal.json"
    source = controlled_path(item["source_relative_path"])
    destination = controlled_path(item["output_relative_path"])
    staging = controlled_path(
        f".intake-staging/nepal-m2-dem-vertical-datum-proj25-001/{source_id.lower()}/{destination.name}.part.tif"
    )
    events = controlled_path(f"derived/control-events/m2-dem-vertical-datum-proj25/{attempt_id}")
    if public_started.exists() or public_terminal.exists() or destination.exists() or staging.exists() or events.exists():
        raise ValueError(f"{source_id} conversion attempt collision")
    events.mkdir(parents=True, exist_ok=False)
    started = {
        "schema_version": "1.0",
        "event": "m2_dem_vertical_conversion_started",
        "attempt_id": attempt_id,
        "source_id": source_id,
        "started_at_utc": started_at,
        "source_path": str(source),
        "destination_path": str(destination),
        "staging_path": str(staging),
        "maximum_attempts": 1,
        "automatic_retry_authorized": False,
        "source_overwrite_permitted": False,
        "proj_network_enabled": False,
    }
    write_new_json(events / "started.json", started)
    write_new_json(public_started, {**started, "external_started_event": str(events / "started.json")})
    stage = "source_identity"
    try:
        source_before = {"size_bytes": source.stat().st_size, "sha256": sha256_file(source)}
        if source_before["sha256"] != item["source_sha256"]:
            raise ValueError("source DEM byte identity differs")
        os.environ["PROJ_NETWORK"] = "OFF"
        gdal.UseExceptions()
        source_dataset = gdal.OpenEx(str(source), gdal.OF_RASTER | gdal.OF_READONLY)
        if source_dataset is None:
            raise ValueError("source DEM cannot be opened")
        width, height = int(source_dataset.RasterXSize), int(source_dataset.RasterYSize)
        geotransform = tuple(float(value) for value in source_dataset.GetGeoTransform())
        extent = output_extent(geotransform, width, height)
        nodata = source_dataset.GetRasterBand(1).GetNoDataValue()
        source_dataset = None
        staging.parent.mkdir(parents=True, exist_ok=False)
        stage = "gdal_vertical_conversion"
        options = gdal.WarpOptions(
            format="GTiff",
            srcSRS="EPSG:9518",
            dstSRS="EPSG:4979",
            coordinateOperation=vertical_pipeline(grid),
            outputBounds=extent,
            width=width,
            height=height,
            resampleAlg="near",
            srcNodata=nodata,
            dstNodata=nodata,
            outputType=gdal.GDT_Float32,
            creationOptions=["TILED=YES", "COMPRESS=DEFLATE", "PREDICTOR=3", "BIGTIFF=IF_SAFER"],
            warpOptions=["INIT_DEST=NO_DATA"],
        )
        result = gdal.Warp(str(staging), str(source), options=options)
        if result is None:
            raise ValueError("GDAL vertical conversion returned no dataset")
        result.FlushCache()
        result = None
        stage = "staged_output_verification"
        verification = verify_staged_output(source, staging)
        arcgis = arcgis_readability(staging, width, height)
        source_after = {"size_bytes": source.stat().st_size, "sha256": sha256_file(source)}
        if source_after != source_before:
            raise ValueError("source DEM changed during conversion")
        staged_identity = {"size_bytes": staging.stat().st_size, "sha256": sha256_file(staging)}
        stage = "no_replace_promotion"
        promoted = promote_no_replace(staging, destination, staged_identity["size_bytes"], staged_identity["sha256"])
        terminal = {
            "schema_version": "1.0",
            "event": "m2_dem_vertical_conversion_succeeded",
            "status": "pass_converted_verified_promoted",
            "attempt_id": attempt_id,
            "source_id": source_id,
            "started_at_utc": started_at,
            "completed_at_utc": utc_now(),
            "source_before": source_before,
            "source_after": source_after,
            "source_immutable": True,
            "staged": staged_identity,
            "promoted": promoted,
            "verification": verification,
            "arcgis_readability": arcgis,
            "destination_path": str(destination),
            "staging_bytes_preserved": True,
            "attempt_count": 1,
            "automatic_retry_performed": False,
            "proj_network_enabled": False,
        }
        write_new_json(events / "terminal.json", terminal)
        write_new_json(public_terminal, {**terminal, "external_terminal_event": str(events / "terminal.json")})
        return terminal
    except BaseException as exc:
        terminal = {
            "schema_version": "1.0",
            "event": "m2_dem_vertical_conversion_failed",
            "status": "terminal_failure_stop_batch_no_retry",
            "attempt_id": attempt_id,
            "source_id": source_id,
            "started_at_utc": started_at,
            "completed_at_utc": utc_now(),
            "last_stage": stage,
            "failure_type": type(exc).__name__,
            "failure_message": str(exc),
            "partial_bytes_preserved": staging.stat().st_size if staging.exists() else 0,
            "destination_created": destination.exists(),
            "automatic_retry_authorized": False,
        }
        try:
            write_new_json(events / "terminal.json", terminal)
        finally:
            write_new_json(public_terminal, {**terminal, "external_terminal_event": str(events / "terminal.json")})
        return terminal


def correction_edge(source: Path, output: Path, edge: str) -> Any:
    from osgeo import gdal  # type: ignore
    import numpy as np  # type: ignore

    first = gdal.OpenEx(str(source), gdal.OF_RASTER | gdal.OF_READONLY)
    second = gdal.OpenEx(str(output), gdal.OF_RASTER | gdal.OF_READONLY)
    width, height = int(first.RasterXSize), int(first.RasterYSize)
    if edge == "left":
        window = (0, 0, 1, height)
    elif edge == "right":
        window = (width - 1, 0, 1, height)
    elif edge == "top":
        window = (0, 0, width, 1)
    elif edge == "bottom":
        window = (0, height - 1, width, 1)
    else:
        raise ValueError("unsupported edge")
    src = np.asarray(first.GetRasterBand(1).ReadAsArray(*window), dtype=np.float64).ravel()
    out = np.asarray(second.GetRasterBand(1).ReadAsArray(*window), dtype=np.float64).ravel()
    first = second = None
    return out - src


def seam_statistics(contract: dict[str, Any]) -> list[dict[str, Any]]:
    import numpy as np  # type: ignore

    by_id = {item["source_id"]: item for item in contract["dem_sources_in_exact_order"]}
    pairs = [
        ("M2-DEM-001", "right", "M2-DEM-002", "left", "E85-N27"),
        ("M2-DEM-003", "right", "M2-DEM-004", "left", "E85-N28"),
        ("M2-DEM-001", "top", "M2-DEM-003", "bottom", "N28-E84"),
        ("M2-DEM-002", "top", "M2-DEM-004", "bottom", "N28-E85"),
    ]
    results = []
    for first_id, first_edge, second_id, second_edge, seam_id in pairs:
        first = by_id[first_id]
        second = by_id[second_id]
        a = correction_edge(controlled_path(first["source_relative_path"]), controlled_path(first["output_relative_path"]), first_edge)
        b = correction_edge(controlled_path(second["source_relative_path"]), controlled_path(second["output_relative_path"]), second_edge)
        valid = np.isfinite(a) & np.isfinite(b)
        if not np.any(valid):
            raise ValueError(f"no finite correction samples at seam {seam_id}")
        residual = np.abs(a[valid] - b[valid])
        results.append({
            "seam_id": seam_id,
            "sample_count": int(residual.size),
            "correction_discontinuity_abs_median_m": float(np.median(residual)),
            "correction_discontinuity_abs_p99_m": float(np.percentile(residual, 99)),
            "correction_discontinuity_abs_max_m": float(np.max(residual)),
        })
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--started-at-utc", default=None)
    args = parser.parse_args()
    if BATCH_TERMINAL.exists():
        raise SystemExit("conversion batch terminal receipt collision")
    started_at = args.started_at_utc or utc_now()
    contract = load_contract()
    operation = load_json(OPERATION_PREFLIGHT)
    if (
        operation.get("status") != "pass_exact_local_inverse_operation_h_equals_H_plus_N"
        or operation.get("assertions", {}).get("dem_pixels_read") is not False
        or operation.get("grid_sha256") != contract["grid"]["expected_sha256"]
    ):
        raise SystemExit("operation-selection sign preflight differs")
    grid = controlled_path(contract["grid"]["destination_relative_path"])
    if not grid.is_file() or sha256_file(grid) != contract["grid"]["expected_sha256"]:
        raise SystemExit("approved grid identity differs before conversion")
    os.environ["PROJ_NETWORK"] = "OFF"
    results = []
    for item in contract["dem_sources_in_exact_order"]:
        result = convert_one(item, grid, started_at)
        results.append(result)
        if result["status"] != "pass_converted_verified_promoted":
            break
    all_passed = len(results) == len(contract["dem_sources_in_exact_order"]) and all(
        item["status"] == "pass_converted_verified_promoted" for item in results
    )
    seam_failure = None
    if all_passed:
        try:
            seams = seam_statistics(contract)
        except BaseException as exc:
            seams = []
            seam_failure = {"failure_type": type(exc).__name__, "failure_message": str(exc)}
            all_passed = False
    else:
        seams = []
    batch = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-DEM-VERTICAL-DATUM-PROJ25-CONVERSION-BATCH-001",
        "status": "pass_four_fixed_order_conversions_verified" if all_passed else "terminal_failure_stopped_no_retry",
        "started_at_utc": started_at,
        "completed_at_utc": utc_now(),
        "source_order": [item["source_id"] for item in contract["dem_sources_in_exact_order"]],
        "attempted_order": [item["source_id"] for item in results],
        "results": [{"source_id": item["source_id"], "status": item["status"], "attempt_id": item["attempt_id"]} for item in results],
        "seams": seams,
        "seam_failure": seam_failure,
        "assertions": {
            "maximum_attempts_per_dem": 1,
            "automatic_retry_performed": False,
            "stopped_on_first_failure": not all_passed,
            "source_files_immutable": all(item.get("source_immutable") is True for item in results if item["status"].startswith("pass")),
            "proj_network_enabled": False,
            "orbit_or_radar_action_performed": False,
            "scientific_result_established": False,
        },
    }
    write_new_json(BATCH_TERMINAL, batch)
    print(json.dumps(batch, indent=2))
    return 0 if all_passed else 20


if __name__ == "__main__":
    raise SystemExit(main())
