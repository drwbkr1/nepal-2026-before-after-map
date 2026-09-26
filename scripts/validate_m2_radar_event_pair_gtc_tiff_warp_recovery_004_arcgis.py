#!/usr/bin/env python3
"""One append-only disposable CRF/TIFF/Warp proof; generated pixels only."""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import traceback
from pathlib import Path

from m2_radar_event_pair_gtc_tiff_warp_recovery_004_core import (
    TARGET, WIDTH, HEIGHT, BridgeStop, check_bridge_metadata, check_free_bytes,
    check_full_pixels, check_output_size, check_projected_grid,
)


ROOT = Path(__file__).resolve().parents[1]
SCRATCH = ROOT / "scratch/m2-radar-event-area-pair-gtc-tiff-warp-recovery-004-disposable-001"
RECEIPT = ROOT / "records/readiness/m2-radar-event-area-pair-gtc-tiff-warp-recovery-004-arcgis-disposable-001.json"
PROPOSAL = ROOT / "contracts/milestone-002-radar-event-area-pair-gtc-tiff-warp-recovery-004-proposal.json"
BUNDLE = ROOT / "reviews/m2-radar-event-area-pair-gtc-tiff-warp-recovery-004/review-bundle.json"
APPROVAL = ROOT / "records/source-gates/m2-radar-event-area-pair-gtc-tiff-warp-recovery-004-approval.json"
PACKET_GATE = ROOT / "records/readiness/m2-radar-event-area-pair-gtc-tiff-warp-recovery-004-packet-publication-gate.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now_utc() -> str:
    import datetime as dt  # ArcPy may rebind module globals

    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_new(path: Path, record: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def write_reserved(path: Path, record: dict) -> None:
    with path.open("r+b") as stream:
        if stream.seek(0, os.SEEK_END):
            raise RuntimeError("reserved_receipt_already_written")
        stream.write((json.dumps(record, indent=2) + "\n").encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())


def check_packet() -> None:
    gate = json.loads(PACKET_GATE.read_text(encoding="utf-8"))
    approval = json.loads(APPROVAL.read_text(encoding="utf-8"))
    if (sha(PROPOSAL) != "69f69b8685f3f0daf9d00a361377085fccb6e954d4ba8d16e40241f2a6c8fd92"
            or sha(BUNDLE) != "1378fb4057dfa47c36f83366c47936dae553e3c52dfee9a710a9c4757b94e93d"
            or approval.get("decision") != "approve"
            or gate.get("status") != "pass_exact_public_packet_and_approval_ci_implementation_eligible"
            or gate.get("bindings", {}).get("approval_sha256") != sha(APPROVAL)
            or gate.get("bindings", {}).get("public_ci_conclusion") != "success"):
        raise RuntimeError("exact_public_packet_gate_missing")


def arc_metadata(arcpy, path: Path) -> dict:
    raster = arcpy.Raster(str(path))
    extent = raster.extent
    x = float(raster.meanCellWidth)
    y = float(raster.meanCellHeight)
    return {"wkid": int(raster.spatialReference.factoryCode),
            "width": int(raster.width), "height": int(raster.height),
            "bands": int(raster.bandCount), "pixel_type": str(raster.pixelType),
            "nodata": raster.noDataValue,
            "transform": [float(extent.XMin), x, 0.0, float(extent.YMax), 0.0, -y],
            "bounds": [float(extent.XMin), float(extent.YMin),
                       float(extent.XMax), float(extent.YMax)]}


def check_one_bridge(arcpy, np, *, categorical: bool) -> dict:
    name = "categorical" if categorical else "continuous"
    crf = SCRATCH / f"generated_{name}_4326.crf"
    tif = SCRATCH / f"generated_{name}_4326.tif"
    size = 256
    row = np.arange(size, dtype=np.float32)[:, None]
    col = np.arange(size, dtype=np.float32)[None, :]
    if categorical:
        array = np.where((np.arange(size)[:, None] // 32 + np.arange(size)[None, :] // 32) % 2,
                         1, 3).astype(np.uint8)
        array[20:40, 20:40] = 0  # a valid class, never target NoData
        array[0:8, :] = 255
        nodata = 255
    else:
        array = np.stack((7 + row * .01 + col * .001,
                          9 + row * .001 + col * .01)).astype(np.float32)
        array[:, 0:8, :] = -9999
        nodata = -9999
    check_free_bytes(shutil.disk_usage(SCRATCH).free, int(array.nbytes))
    arcpy.NumPyArrayToRaster(array, arcpy.Point(85.10, 28.20), .00025, .00025,
                            value_to_nodata=nodata).save(str(crf))
    arcpy.management.DefineProjection(str(crf), arcpy.SpatialReference(4326))
    before = arc_metadata(arcpy, crf)
    check_free_bytes(shutil.disk_usage(SCRATCH).free, int(array.nbytes))
    arcpy.management.CopyRaster(str(crf), str(tif), format="TIFF")
    after = arc_metadata(arcpy, tif)
    check_bridge_metadata(before, after)
    observed_crf = arcpy.RasterToNumPyArray(str(crf), nodata_to_value=nodata)
    observed_tif = arcpy.RasterToNumPyArray(str(tif), nodata_to_value=nodata)
    arc_check = check_full_pixels(observed_crf, observed_tif, categorical=categorical)
    # Only after ArcPy's independent comparison may GDAL open the bridge TIFF.
    from osgeo import gdal  # type: ignore

    source = gdal.OpenEx(str(tif), gdal.OF_RASTER | gdal.OF_READONLY)
    if source is None or source.GetDriver().ShortName != "GTiff":
        raise BridgeStop("bridge_gdal_tiff_unreadable")
    try:
        gdal_array = source.ReadAsArray()
        gdal_check = check_full_pixels(observed_crf, gdal_array, categorical=categorical)
        gdal_nodata = [source.GetRasterBand(n).GetNoDataValue()
                       for n in range(1, source.RasterCount + 1)]
        if any(value != nodata for value in gdal_nodata):
            raise BridgeStop("bridge_gdal_nodata_changed")
        if source.GetGeoTransform() != tuple(before["transform"]):
            raise BridgeStop("bridge_gdal_transform_changed")
        return {"arc_metadata": before, "arc_tiff_metadata": after,
                "arc_full_pixels": arc_check, "gdal_full_pixels": gdal_check,
                "gdal_nodata": gdal_nodata,
                "tiff_disk_bytes": check_output_size(tif)}
    finally:
        source.Close()


def broad_source_bounds(arcpy) -> tuple[float, float, float, float]:
    projected = arcpy.SpatialReference(32645)
    geographic = arcpy.SpatialReference(4326)
    corners = ((TARGET[0], TARGET[1]), (TARGET[0], TARGET[3]),
               (TARGET[2], TARGET[1]), (TARGET[2], TARGET[3]))
    points = [arcpy.PointGeometry(arcpy.Point(x, y), projected).projectAs(geographic).firstPoint
              for x, y in corners]
    return (min(p.X for p in points) - .002, min(p.Y for p in points) - .002,
            max(p.X for p in points) + .002, max(p.Y for p in points) + .002)


def check_exact_warp(arcpy, np, *, categorical: bool) -> dict:
    from osgeo import gdal  # type: ignore

    name = "categorical" if categorical else "continuous"
    west, south, east, north = broad_source_bounds(arcpy)
    cell = .001
    cols = math.ceil((east - west) / cell)
    rows = math.ceil((north - south) / cell)
    if rows * cols > 2_000_000:
        raise BridgeStop("generated_broad_source_too_large")
    source_path = SCRATCH / f"generated_broad_{name}_4326.tif"
    output = SCRATCH / f"generated_broad_{name}_32645.tif"
    driver = gdal.GetDriverByName("GTiff")
    source = driver.Create(str(source_path), cols, rows, 1,
                           gdal.GDT_Byte if categorical else gdal.GDT_Float32)
    if source is None:
        raise BridgeStop("generated_broad_source_create_failed")
    try:
        from osgeo import osr  # type: ignore

        sr = osr.SpatialReference()
        sr.ImportFromEPSG(4326)
        source.SetProjection(sr.ExportToWkt())
        source.SetGeoTransform((west, cell, 0.0, north, 0.0, -cell))
        if categorical:
            values = np.where((np.arange(rows)[:, None] // 17 + np.arange(cols)[None, :] // 17) % 2,
                              1, 3).astype(np.uint8)
            values[rows//3:rows//3+20, cols//3:cols//3+20] = 0
            values[:5, :] = 255
            nodata = 255
        else:
            values = np.full((rows, cols), 7.25, dtype=np.float32)
            values[:5, :] = -9999
            nodata = -9999
        band = source.GetRasterBand(1)
        band.SetNoDataValue(nodata)
        band.WriteArray(values)
        source.FlushCache()
        check_free_bytes(shutil.disk_usage(SCRATCH).free, WIDTH * HEIGHT * (1 if categorical else 4))
        warped = gdal.Warp(str(output), source, format="GTiff", outputBounds=TARGET,
                           width=WIDTH, height=HEIGHT, dstSRS="EPSG:32645",
                           resampleAlg="near" if categorical else "bilinear",
                           srcNodata=nodata, dstNodata=nodata,
                           creationOptions=["TILED=YES", "COMPRESS=LZW", "BIGTIFF=IF_SAFER"],
                           multithread=False, warpMemoryLimit=256 * 1024 * 1024)
        try:
            grid = check_projected_grid(warped, expected_bands=1)
            if warped.GetRasterBand(1).GetNoDataValue() != nodata:
                raise BridgeStop("projected_nodata_changed")
            sample = warped.GetRasterBand(1).ReadAsArray(WIDTH//2 - 32, HEIGHT//2 - 32, 64, 64)
            classes = sorted(int(value) for value in np.unique(sample)) if categorical else []
            if categorical and not set(classes).issubset({0, 1, 3, 255}):
                raise BridgeStop("projected_mask_class_changed")
            if not categorical and not np.isfinite(sample[sample != nodata]).all():
                raise BridgeStop("projected_finite_sample_failed")
            return {"grid": grid, "nodata": nodata,
                    "center_sample_valid_count": int(np.count_nonzero(sample != nodata)),
                    "center_sample_classes": classes,
                    "on_disk_bytes": check_output_size(output),
                    "source_rows": rows, "source_columns": cols,
                    "resampling": "NEAREST" if categorical else "BILINEAR",
                    "coverage_proven_by_frame": False}
        finally:
            if warped is not None:
                warped.Close()
    finally:
        source.Close()


def run() -> dict:
    check_packet()
    if SCRATCH.exists() or RECEIPT.exists():
        raise RuntimeError("append_only_disposable_identity_collision")
    SCRATCH.mkdir(parents=True, exist_ok=False)
    terminal_path = SCRATCH / "terminal.json"
    with terminal_path.open("xb") as stream:
        stream.flush()
        os.fsync(stream.fileno())
    write_new(SCRATCH / "started.json", {"status": "generated_disposable_started",
                                             "at_utc": now_utc(), "protected_data_accessed": False})
    stage = "arcgis_import"
    try:
        os.environ["PROJ_NETWORK"] = "OFF"
        os.environ["GDAL_PAM_ENABLED"] = "NO"
        import arcpy  # type: ignore
        import numpy as np  # type: ignore
        from osgeo import gdal  # type: ignore

        gdal.UseExceptions()
        gdal.SetConfigOption("PROJ_NETWORK", "OFF")
        gdal.SetConfigOption("GDAL_PAM_ENABLED", "NO")
        arcpy.env.overwriteOutput = False
        stage = "bridge_continuous"
        continuous = check_one_bridge(arcpy, np, categorical=False)
        stage = "bridge_categorical"
        categorical = check_one_bridge(arcpy, np, categorical=True)
        stage = "warp_continuous"
        continuous_warp = check_exact_warp(arcpy, np, categorical=False)
        stage = "warp_categorical"
        categorical_warp = check_exact_warp(arcpy, np, categorical=True)
        terminal = {"schema_version": "1.0", "status": "pass_generated_bridge_and_exact_grid_only",
                    "completed_at_utc": now_utc(), "arcgis_version": arcpy.GetInstallInfo().get("Version"),
                    "gdal_version": gdal.VersionInfo("--version"),
                    "bridge": {"continuous": continuous, "categorical": categorical},
                    "warp": {"continuous": continuous_warp, "categorical": categorical_warp},
                    "core_sha256": sha(ROOT / "scripts/m2_radar_event_pair_gtc_tiff_warp_recovery_004_core.py"),
                    "validator_sha256": sha(Path(__file__)), "protected_data_accessed": False,
                    "real_attempt_started": False, "sar_fitness_proven": False,
                    "baseline_or_change_analysis_executed": False}
    except BaseException as exc:
        frame = traceback.extract_tb(exc.__traceback__)[-1]
        code = str(exc) if type(exc) in (RuntimeError, BridgeStop) else "disposable_exception"
        if len(code) > 80 or any(char in code for char in ("\\", "/", ":", "@")):
            code = "disposable_exception"
        terminal = {"schema_version": "1.0", "status": "block_generated_method_no_real_attempt",
                    "completed_at_utc": now_utc(), "last_stage": stage,
                    "failure_type": type(exc).__name__, "failure_code": code,
                    "failure_site": {"function": frame.name, "line": frame.lineno},
                    "protected_data_accessed": False, "real_attempt_started": False,
                    "sar_fitness_proven": False, "baseline_or_change_analysis_executed": False}
    write_reserved(terminal_path, terminal)
    write_new(RECEIPT, {"schema_version": "1.0",
                       "status": terminal["status"],
                       "terminal_sha256": sha(terminal_path),
                       "core_sha256": sha(ROOT / "scripts/m2_radar_event_pair_gtc_tiff_warp_recovery_004_core.py"),
                       "validator_sha256": sha(Path(__file__)),
                       "protected_data_accessed": False, "real_attempt_started": False,
                       "sar_fitness_proven": False})
    return terminal


def main() -> int:
    value = run()
    print(json.dumps({"status": value["status"],
                      "stage": value.get("last_stage", "completed")}))
    return 0 if value["status"] == "pass_generated_bridge_and_exact_grid_only" else 20


if __name__ == "__main__":
    raise SystemExit(main())
