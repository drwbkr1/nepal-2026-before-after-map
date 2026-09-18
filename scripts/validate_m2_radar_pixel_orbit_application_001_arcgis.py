#!/usr/bin/env python3
"""Run synthetic ArcGIS-runtime checks for the approved radar processing adapter."""

from __future__ import annotations

import argparse
import ast
import datetime as datetime_module
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

import arcpy  # type: ignore
import numpy as np

from m2_radar_pixel_orbit_application_001_core import (
    classify_radar_pair,
    evaluate_route,
    evaluate_same_date_seam,
    measure_stable_registration,
    validate_contract,
    write_new_json,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REF = "config/qa/m2-radar-pixel-orbit-application-001-contract.json"
PIXEL_CONTRACT_REF = "config/qa/pixel-readiness-contract.json"
RUNNER_REF = "scripts/run_m2_radar_pixel_orbit_application_001.py"
VALUE_FIELD = re.compile(r"^VALUE_(-?\d+)$", re.IGNORECASE)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save_raster(array: np.ndarray, path: Path, xmin: float, ymin: float, cell_size: float, sr: Any) -> None:
    raster = arcpy.NumPyArrayToRaster(array, arcpy.Point(xmin, ymin), cell_size, cell_size)
    raster.save(str(path))
    arcpy.management.DefineProjection(str(path), sr)


def raster_grid(path: Path) -> dict[str, Any]:
    description = arcpy.Describe(str(path))
    extent = description.extent
    return {
        "wkid": int(description.spatialReference.factoryCode),
        "cell_size_x": float(description.meanCellWidth),
        "cell_size_y": float(description.meanCellHeight),
        "origin_x": float(extent.XMin),
        "origin_y": float(extent.YMin),
        "xmin": float(extent.XMin),
        "ymin": float(extent.YMin),
        "xmax": float(extent.XMax),
        "ymax": float(extent.YMax),
        "rotation_degrees": 0.0,
    }


def require_new_scratch_path(path: Path) -> Path:
    resolved = path.resolve(strict=False)
    scratch = (ROOT / "scratch").resolve(strict=False)
    try:
        resolved.relative_to(scratch)
    except ValueError as exc:
        raise SystemExit(f"output root must be under {scratch}") from exc
    if resolved.exists():
        raise SystemExit(f"output collision: {resolved}")
    resolved.mkdir(parents=True)
    return resolved


def tool_signature_checks() -> dict[str, Any]:
    prefixes = {
        "ApplyOrbitCorrection_ia": "ApplyOrbitCorrection_ia(in_radar_data, {in_orbit_file}, {folder})",
        "RemoveThermalNoise_ia": "RemoveThermalNoise_ia(in_radar_data, out_radar_data",
        "ApplyRadiometricCalibration_ia": "ApplyRadiometricCalibration_ia(in_radar_data, out_radar_data",
        "ApplyRadiometricTerrainFlattening_ia": "ApplyRadiometricTerrainFlattening_ia(in_radar_data, out_radar_data, in_dem_raster",
        "ApplyGeometricTerrainCorrection_ia": "ApplyGeometricTerrainCorrection_ia(in_radar_data, out_radar_data",
        "ConvertSARUnits_ia": "ConvertSARUnits_ia(in_radar_data, out_radar_data",
    }
    usage = {name: arcpy.Usage(name) for name in prefixes}
    return {"usage": usage, "all_match": all(usage[name].startswith(prefix) for name, prefix in prefixes.items())}


def runner_call_checks() -> dict[str, Any]:
    expected_counts = {
        "RemoveThermalNoise": 3,
        "ApplyRadiometricCalibration": 4,
        "ApplyRadiometricTerrainFlattening": 9,
        "ApplyGeometricTerrainCorrection": 5,
        "ConvertSARUnits": 3,
    }
    tree = ast.parse((ROOT / RUNNER_REF).read_text(encoding="utf-8"))
    observed: dict[str, list[int]] = {key: [] for key in expected_counts}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in observed:
            observed[node.func.attr].append(len(node.args))
    return {
        "expected_positional_argument_counts": expected_counts,
        "observed_positional_argument_counts": observed,
        "all_match": all(values and all(value == expected_counts[name] for value in values) for name, values in observed.items()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--receipt-output", required=True, type=Path)
    parser.add_argument("--verified-at-utc", default=None)
    args = parser.parse_args()

    output_root = require_new_scratch_path(ROOT / args.output_root)
    receipt_path = args.receipt_output if args.receipt_output.is_absolute() else ROOT / args.receipt_output
    if receipt_path.exists() or not receipt_path.parent.is_dir():
        raise SystemExit("receipt collision or missing pre-existing parent")
    contract_path = ROOT / CONTRACT_REF
    pixel_path = ROOT / PIXEL_CONTRACT_REF
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    pixel_contract = json.loads(pixel_path.read_text(encoding="utf-8"))
    errors = validate_contract(contract, ROOT)
    if errors:
        raise SystemExit("invalid implementation contract: " + "; ".join(errors))
    signatures = tool_signature_checks()
    if not signatures["all_match"]:
        raise SystemExit("installed ArcGIS SAR tool signatures differ")
    runner_calls = runner_call_checks()
    if not runner_calls["all_match"]:
        raise SystemExit("production runner SAR calls do not match installed signatures")
    if arcpy.CheckExtension("ImageAnalyst") != "Available" or arcpy.CheckExtension("Spatial") != "Available":
        raise SystemExit("required ArcGIS extensions are unavailable")

    sr = arcpy.SpatialReference(32645)
    rows = columns = 180
    cell = 10.0
    xmin = 300000.0
    ymin = 3100000.0
    ymax = ymin + rows * cell
    rng = np.random.default_rng(20260918)
    before = rng.normal(1.0, 0.2, (rows, columns)).astype(np.float32)
    after = before.copy()
    before_native = np.ones((rows, columns), dtype=np.uint8)
    after_native = np.ones((rows, columns), dtype=np.uint8)
    before_native[:, :5] = 4
    after_native[:5, :] = 3
    before_valid = np.ones((rows, columns), dtype=bool)
    after_valid = np.ones((rows, columns), dtype=bool)
    classified = classify_radar_pair(before_native, after_native, before_valid, after_valid)

    before_path = output_root / "synthetic_before_vv_linear.tif"
    after_path = output_root / "synthetic_after_vv_linear.tif"
    mask_path = output_root / "synthetic_pair_mask.tif"
    save_raster(before, before_path, xmin, ymin, cell, sr)
    save_raster(after, after_path, xmin, ymin, cell, sr)
    save_raster(classified["classes"], mask_path, xmin, ymin, cell, sr)

    registration = measure_stable_registration(
        before,
        after,
        classified["pair_valid"],
        grid={"xmin": xmin, "ymax": ymax, "cell_size_m": cell},
        overview_bbox=(xmin, ymin, xmin + columns * cell, ymax),
        exclusion_bboxes=[],
        settings=contract["registration"],
        pixel_contract=pixel_contract,
    )
    area_per_cell = cell * cell
    valid_count = int(classified["pair_valid"].sum())
    covered_count = int(classified["covered"].sum())
    excluded = {
        "layover": int(np.count_nonzero(classified["classes"] == 2)) * area_per_cell,
        "radar_shadow": int(np.count_nonzero(classified["classes"] == 3)) * area_per_cell,
        "native_undetermined": int(np.count_nonzero(classified["classes"] == 0)) * area_per_cell,
    }
    excluded = {key: value for key, value in excluded.items() if value}
    observation = {
        "aoi_id": "AOI-SYNTHETIC",
        "aoi_area_m2": rows * columns * area_per_cell,
        "covered_area_m2": covered_count * area_per_cell,
        "valid_area_m2": valid_count * area_per_cell,
        "excluded_area_by_reason_m2": excluded,
    }
    seam = evaluate_same_date_seam(before, after, classified["pair_valid"])
    route = evaluate_route(
        route_id="PAIR-S1-ASC-R085-IW",
        aoi_observations=[observation],
        before_grid=raster_grid(before_path),
        after_grid=raster_grid(after_path),
        registration=registration,
        seam_observations=[seam],
        pixel_contract=pixel_contract,
        unknown_mask_class_present=classified["unknown_native_class_present"],
    )

    dem_dir = output_root / "synthetic_dem_tiles"
    dem_dir.mkdir()
    dem_paths: list[Path] = []
    for row_index in range(2):
        for column_index in range(2):
            tile = np.full((10, 10), 1000 + row_index * 10 + column_index, dtype=np.float32)
            path = dem_dir / f"dem_{row_index}_{column_index}.tif"
            save_raster(tile, path, 84.0 + column_index * 0.01, 27.0 + row_index * 0.01, 0.001, arcpy.SpatialReference(4326))
            dem_paths.append(path)
    dem_mosaic = output_root / "synthetic_dem_mosaic.tif"
    arcpy.management.MosaicToNewRaster(
        [str(path) for path in dem_paths],
        str(output_root),
        dem_mosaic.name,
        arcpy.SpatialReference(4326),
        "32_BIT_FLOAT",
        0.001,
        1,
        "FIRST",
        "FIRST",
    )
    dem_desc = arcpy.Describe(str(dem_mosaic))
    if int(dem_desc.spatialReference.factoryCode) != 4326 or int(dem_desc.bandCount) != 1:
        raise RuntimeError("synthetic DEM mosaic differs")
    if registration["status"] != "pass_qa_only" or route["status"] != "pass_qa_only":
        raise RuntimeError("synthetic registration or route QA did not pass")

    install = arcpy.GetInstallInfo()
    verified = args.verified_at_utc or datetime_module.datetime.now(datetime_module.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    receipt = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-001-SYNTHETIC-ARCGIS",
        "verified_at_utc": verified,
        "status": "pass_synthetic_arcgis_runtime_only",
        "runtime": {
            "product": install.get("ProductName"),
            "version": install.get("Version"),
            "license_level": arcpy.ProductInfo(),
            "image_analyst": arcpy.CheckExtension("ImageAnalyst"),
            "spatial_analyst": arcpy.CheckExtension("Spatial"),
        },
        "bindings": {
            "implementation_contract_ref": CONTRACT_REF,
            "implementation_contract_sha256": sha256(contract_path),
            "pixel_contract_ref": PIXEL_CONTRACT_REF,
            "pixel_contract_sha256": sha256(pixel_path),
            "core_ref": "scripts/m2_radar_pixel_orbit_application_001_core.py",
            "core_sha256": sha256(ROOT / "scripts/m2_radar_pixel_orbit_application_001_core.py"),
            "adapter_ref": "scripts/validate_m2_radar_pixel_orbit_application_001_arcgis.py",
            "adapter_sha256": sha256(Path(__file__).resolve()),
            "production_runner_ref": RUNNER_REF,
            "production_runner_sha256": sha256(ROOT / RUNNER_REF),
        },
        "checks": {
            "tool_signatures": signatures,
            "production_runner_call_arguments": runner_calls,
            "mask_class_counts": classified["class_counts"],
            "registration": {key: value for key, value in registration.items() if key != "controls"},
            "route_evaluation": {key: value for key, value in route.items() if key != "registration_controls"},
            "dem_mosaic": {
                "source_tile_count": len(dem_paths),
                "wkid": int(dem_desc.spatialReference.factoryCode),
                "band_count": int(dem_desc.bandCount),
                "sha256": sha256(dem_mosaic),
            },
        },
        "assertions": {
            "synthetic_only": True,
            "exact_sar_tool_signatures_present": True,
            "production_runner_calls_match_installed_signatures": True,
            "common_epsg32645_grid_exercised": True,
            "categorical_mask_translation_exercised": True,
            "stable_registration_exercised": True,
            "same_date_seam_measurement_exercised": True,
            "four_tile_dem_mosaic_exercised": True,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "network_request_performed": False,
            "orbit_application_executed": False,
            "baseline_or_change_analysis_executed": False,
            "scientific_admission_authorized": False,
        },
        "synthetic_outputs": {
            "output_root": str(output_root),
            "before_sha256": sha256(before_path),
            "after_sha256": sha256(after_path),
            "mask_sha256": sha256(mask_path),
        },
        "limitations": [
            "Synthetic rasters test ArcGIS raster I/O, DEM mosaicking, grid, masks, registration, seams, and route decisions only.",
            "The SAR tools were signature-checked but were not executed because arbitrary synthetic rasters are not valid Sentinel-1 SAFE data.",
            "No project Sentinel, orbit, DEM, credential, network resource, baseline, change product, or scientific claim was accessed or created.",
        ],
    }
    write_new_json(receipt_path, receipt)
    print(json.dumps({"status": receipt["status"], "receipt": str(receipt_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
