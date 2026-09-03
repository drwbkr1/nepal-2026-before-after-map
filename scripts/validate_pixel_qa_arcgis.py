#!/usr/bin/env python3
"""Exercise the pixel-readiness contract with synthetic EPSG:32645 rasters in ArcGIS Pro."""

from __future__ import annotations

import argparse
import datetime as datetime_module
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

import arcpy
import numpy as np

from pixel_qa_core import (
    evaluate_aoi_coverage,
    evaluate_grid_pair,
    evaluate_registration,
    load_contract,
)


VALUE_FIELD = re.compile(r"^VALUE_(-?\d+)$", re.IGNORECASE)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def repo_relative(repo: Path, path: Path) -> str:
    return path.resolve().relative_to(repo).as_posix()


def require_new_scratch_path(repo: Path, output_root: Path) -> Path:
    resolved = output_root.resolve(strict=False)
    scratch = (repo / "scratch").resolve(strict=False)
    try:
        resolved.relative_to(scratch)
    except ValueError as exc:
        raise SystemExit(f"Output root must be a new path under {scratch}: {resolved}") from exc
    if resolved.exists():
        raise SystemExit(f"Output root already exists; use a new attempt path: {resolved}")
    resolved.mkdir(parents=True)
    return resolved


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


def save_raster(array: np.ndarray, path: Path, xmin: float, ymin: float, cell_size: float, sr: arcpy.SpatialReference) -> None:
    raster = arcpy.NumPyArrayToRaster(array, arcpy.Point(xmin, ymin), cell_size, cell_size)
    raster.save(str(path))
    arcpy.management.DefineProjection(str(path), sr)


def tabulate_aoi_coverage(
    *,
    aoi_fc: Path,
    scl_raster: Path,
    output_table: Path,
    contract: dict[str, Any],
    cell_size: float,
) -> list[dict[str, Any]]:
    arcpy.sa.TabulateArea(
        str(aoi_fc),
        "AOI_ID",
        str(scl_raster),
        "Value",
        str(output_table),
        cell_size,
        "CLASSES_AS_FIELDS",
    )
    area_by_aoi = {
        str(aoi_id): float(area)
        for aoi_id, area in arcpy.da.SearchCursor(str(aoi_fc), ["AOI_ID", "SHAPE@AREA"])
    }
    class_fields: dict[str, int] = {}
    for field in arcpy.ListFields(str(output_table)):
        matched = VALUE_FIELD.match(field.name)
        if matched:
            class_fields[field.name] = int(matched.group(1))
    if not class_fields:
        raise RuntimeError("TabulateArea produced no VALUE_<class> fields")

    valid_classes = {int(value) for value in contract["optical_scl"]["valid_surface_classes"]}
    excluded_classes = {
        int(value): reason
        for value, reason in contract["optical_scl"]["excluded_classes"].items()
    }
    cursor_fields = ["AOI_ID", *class_fields]
    results: list[dict[str, Any]] = []
    for row in arcpy.da.SearchCursor(str(output_table), cursor_fields):
        aoi_id = str(row[0])
        areas = {
            class_fields[field]: float(value or 0.0)
            for field, value in zip(cursor_fields[1:], row[1:])
        }
        valid_area = sum(area for class_value, area in areas.items() if class_value in valid_classes)
        excluded: dict[str, float] = {}
        unknown_classes: list[int] = []
        for class_value, area in areas.items():
            if class_value in valid_classes or area == 0:
                continue
            reason = excluded_classes.get(class_value)
            if reason is None:
                reason = f"unknown_scl_class_{class_value}"
                unknown_classes.append(class_value)
            excluded[reason] = excluded.get(reason, 0.0) + area
        result = evaluate_aoi_coverage(
            aoi_id=aoi_id,
            aoi_area_m2=area_by_aoi[aoi_id],
            covered_area_m2=sum(areas.values()),
            valid_area_m2=valid_area,
            excluded_area_by_reason_m2=excluded,
            contract=contract,
        )
        result["scl_class_area_m2"] = {str(key): value for key, value in sorted(areas.items())}
        if unknown_classes and result["status"] == "pass_qa_only":
            result["status"] = "defer"
            result["limitations"].append("Unknown SCL classes require explicit review under the predeclared policy.")
        result["unknown_scl_classes"] = sorted(unknown_classes)
        results.append(result)
    return sorted(results, key=lambda item: item["aoi_id"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=Path("config/qa/pixel-readiness-contract.json"))
    parser.add_argument("--approved-aoi", type=Path, default=Path("config/aoi/approved-study-areas-epsg32645.json"))
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--receipt-output", type=Path, required=True)
    parser.add_argument("--verified-at-utc", default=None)
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    contract_path = (repo / args.contract).resolve()
    aoi_path = (repo / args.approved_aoi).resolve()
    receipt_path = (repo / args.receipt_output).resolve(strict=False)
    script_path = Path(__file__).resolve()
    core_path = script_path.with_name("pixel_qa_core.py")
    if receipt_path.exists():
        raise SystemExit(f"Receipt path already exists; refusing replacement: {receipt_path}")
    output_root = require_new_scratch_path(repo, repo / args.output_root)
    contract = load_contract(contract_path)
    aoi_json = json.loads(aoi_path.read_text(encoding="utf-8"))

    extent = aoi_json["projectMetadata"]["extent"]
    cell_size = float(contract["grid_compatibility"]["optical_multispectral_change_cell_size_m"])
    buffer_cells = 2
    xmin = math.floor(float(extent["xmin"]) / cell_size) * cell_size - buffer_cells * cell_size
    ymin = math.floor(float(extent["ymin"]) / cell_size) * cell_size - buffer_cells * cell_size
    xmax = math.ceil(float(extent["xmax"]) / cell_size) * cell_size + buffer_cells * cell_size
    ymax = math.ceil(float(extent["ymax"]) / cell_size) * cell_size + buffer_cells * cell_size
    columns = int(round((xmax - xmin) / cell_size))
    rows = int(round((ymax - ymin) / cell_size))
    sr = arcpy.SpatialReference(contract["analysis_crs"]["wkid"])

    gdb = output_root / "pixel_qa.gdb"
    arcpy.management.CreateFileGDB(str(output_root), gdb.name)
    aoi_fc = gdb / "ApprovedStudyAreas"
    arcpy.conversion.JSONToFeatures(str(aoi_path), str(aoi_fc))
    aoi_description = arcpy.Describe(str(aoi_fc))
    aoi_count = int(arcpy.management.GetCount(str(aoi_fc))[0])

    before_path = output_root / "synthetic_before.tif"
    after_path = output_root / "synthetic_after.tif"
    scl_path = output_root / "synthetic_scl.tif"
    misaligned_path = output_root / "synthetic_misaligned.tif"

    values = np.full((rows, columns), 1000, dtype=np.uint16)
    save_raster(values, before_path, xmin, ymin, cell_size, sr)
    values.fill(1005)
    save_raster(values, after_path, xmin, ymin, cell_size, sr)
    del values

    scl = np.full((rows, columns), 4, dtype=np.uint8)
    scl[:, ::10] = 9
    save_raster(scl, scl_path, xmin, ymin, cell_size, sr)
    del scl

    misaligned = np.full((32, 32), 1, dtype=np.uint8)
    shift = 0.6 * cell_size
    save_raster(misaligned, misaligned_path, xmin + shift, ymin + shift, cell_size, sr)
    del misaligned

    aligned_grid_result = evaluate_grid_pair(raster_grid(before_path), raster_grid(after_path), contract)
    misaligned_grid_result = evaluate_grid_pair(raster_grid(before_path), raster_grid(misaligned_path), contract)
    registration_result = evaluate_registration(
        stable_control_pair_count=None,
        rmse_pixels=None,
        bias_x_pixels=None,
        bias_y_pixels=None,
        contract=contract,
    )

    if arcpy.CheckExtension("Spatial") != "Available":
        raise RuntimeError("ArcGIS Spatial Analyst is unavailable for TabulateArea")
    arcpy.CheckOutExtension("Spatial")
    try:
        with arcpy.EnvManager(
            outputCoordinateSystem=sr,
            snapRaster=str(scl_path),
            cellSize=cell_size,
            extent=str(scl_path),
        ):
            aoi_results = tabulate_aoi_coverage(
                aoi_fc=aoi_fc,
                scl_raster=scl_path,
                output_table=gdb / "AOISCLArea",
                contract=contract,
                cell_size=cell_size,
            )
    finally:
        arcpy.CheckInExtension("Spatial")

    errors: list[str] = []
    if aoi_count != 3 or int(aoi_description.spatialReference.factoryCode) != 32645:
        errors.append("approved AOI import did not preserve three EPSG:32645 features")
    if len(aoi_results) != 3 or any(item["status"] != "pass_qa_only" for item in aoi_results):
        errors.append("synthetic SCL coverage did not pass all three AOIs")
    if aligned_grid_result["status"] != "pass_qa_only":
        errors.append("aligned synthetic grid pair did not pass")
    if misaligned_grid_result["status"] != "block":
        errors.append("deliberately shifted synthetic grid did not block")
    if registration_result["status"] != "defer":
        errors.append("unmeasured registration did not defer")
    if errors:
        raise RuntimeError("; ".join(errors))

    install = arcpy.GetInstallInfo()
    verified_at = args.verified_at_utc or datetime_module.datetime.now(datetime_module.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    receipt = {
        "receipt_id": "NEPAL-PIXEL-QA-SYNTHETIC-ARCGIS-001",
        "status": "pass_synthetic_only_with_expected_block_and_defer",
        "verified_at_utc": verified_at,
        "runtime": {
            "product": install.get("ProductName", "ArcGISPro"),
            "version": install.get("Version"),
            "license_level": arcpy.ProductInfo().replace("ArcInfo", "Advanced"),
            "spatial_analyst": "available_and_used",
        },
        "inputs": {
            "contract": repo_relative(repo, contract_path),
            "contract_sha256": sha256(contract_path),
            "approved_aoi": repo_relative(repo, aoi_path),
            "approved_aoi_sha256": sha256(aoi_path),
            "core": repo_relative(repo, core_path),
            "core_sha256": sha256(core_path),
            "arcgis_adapter": repo_relative(repo, script_path),
            "arcgis_adapter_sha256": sha256(script_path),
        },
        "synthetic_fixture": {
            "output_root": str(output_root),
            "file_geodatabase": str(gdb),
            "wkid": 32645,
            "cell_size_m": cell_size,
            "rows": rows,
            "columns": columns,
            "scl_pattern": "nine columns class 4 vegetation followed by one column class 9 high-probability cloud",
            "raster_sha256": {
                "synthetic_before.tif": sha256(before_path),
                "synthetic_after.tif": sha256(after_path),
                "synthetic_scl.tif": sha256(scl_path),
                "synthetic_misaligned.tif": sha256(misaligned_path),
            },
        },
        "aoi_import": {
            "feature_count": aoi_count,
            "spatial_reference_wkid": int(aoi_description.spatialReference.factoryCode),
        },
        "checks": {
            "aoi_scl_coverage": aoi_results,
            "aligned_grid_pair": aligned_grid_result,
            "deliberately_misaligned_grid_pair": misaligned_grid_result,
            "registration_not_measured": registration_result,
        },
        "assertions": {
            "all_three_aoi_coverage_results_pass_qa_only": True,
            "aligned_grid_pair_passes_qa_only": True,
            "subpixel_shift_is_blocked": True,
            "unmeasured_registration_is_deferred": True,
            "real_product_pixels_examined": False,
            "scientific_admission_authorized": False,
            "m2_activated": False,
        },
        "retained_failures": [],
        "claim_boundary": contract["claim_boundary"],
        "limitations": [
            "All rasters are deterministic synthetic fixtures; results establish adapter behavior only.",
            "No external custody root was probed or created and no Sentinel product, credential, network route, or authenticated session was accessed.",
            "Synthetic coverage and grid passes are not evidence of real-product coverage, masks, registration, change, interpretation, or attribution.",
            "Registration intentionally remains DEFER because no stable-control measurement was performed.",
            "The deliberately shifted raster is an expected BLOCK test and does not reject any approved source identity.",
            "M2 remains proposed and not active.",
        ],
        "preserved_review_bindings": {
            "acquisition_plan_sha256": "6261dc61061cb962f22163755047f080e309ed2d746cdcdd61e6cf61d7ec2a8d",
            "m2_activation_review_bundle_sha256": "e8d105970d64c43d955ff459ba9e5d5a3a1e4fb4f95874aa67f384e6b293a35d",
        },
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_bytes((json.dumps(receipt, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({
        "status": receipt["status"],
        "receipt": str(receipt_path),
        "aoi_statuses": {item["aoi_id"]: item["status"] for item in aoi_results},
        "aligned_grid": aligned_grid_result["status"],
        "misaligned_grid": misaligned_grid_result["status"],
        "registration": registration_result["status"],
    }, indent=2))


if __name__ == "__main__":
    main()
