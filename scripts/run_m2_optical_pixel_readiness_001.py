#!/usr/bin/env python3
"""Run the one exact optical pair pixel-readiness attempt in ArcGIS Pro."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from pathlib import Path, PurePosixPath
from typing import Any

from m2_optical_pixel_stage_gate import CONTRACT_REF, ROOT, validate_pixel_stage_execution
from optical_pixel_readiness_core_001 import NODATA_CLASS, REASON_CODES, VALID_CLASS, classify_pair_pixels, final_pixel_decision, measure_stable_registration, validate_contract
from pixel_qa_core import evaluate_aoi_coverage, evaluate_grid_pair, load_contract as load_pixel_contract


UTC_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
VALUE_FIELD = re.compile(r"^VALUE_(-?\d+)$", re.IGNORECASE)


def load_path(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_new_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def inventory(root: Path) -> list[dict[str, Any]]:
    return [
        {"relative_path": path.relative_to(root).as_posix(), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for path in sorted((item for item in root.rglob("*") if item.is_file()), key=lambda item: str(item).casefold())
    ]


def bbox(feature: dict[str, Any]) -> tuple[float, float, float, float]:
    coordinates = [point for ring in feature["geometry"]["rings"] for point in ring]
    xs = [float(point[0]) for point in coordinates]
    ys = [float(point[1]) for point in coordinates]
    return min(xs), min(ys), max(xs), max(ys)


def grid_from_description(description: dict[str, Any]) -> dict[str, Any]:
    return {
        "wkid": int(description["wkid"]),
        "cell_size_x": float(description["cell_width"]),
        "cell_size_y": float(description["cell_height"]),
        "origin_x": float(description["xmin"]),
        "origin_y": float(description["ymin"]),
        "xmin": float(description["xmin"]),
        "ymin": float(description["ymin"]),
        "xmax": float(description["xmax"]),
        "ymax": float(description["ymax"]),
        "rotation_degrees": 0.0,
    }


def read_target(arcpy: Any, path: Path, target: dict[str, Any], fill_value: int) -> Any:
    import numpy as np

    description = arcpy.Describe(str(path))
    children = list(getattr(description, "children", []) or [])
    header = children[0] if children else description
    source = arcpy.RasterToNumPyArray(str(path), nodata_to_value=fill_value)
    source_extent = description.extent
    source_cell_x = float(header.meanCellWidth)
    source_cell_y = float(header.meanCellHeight)
    rows = int(target["rows"])
    columns = int(target["columns"])
    cell = float(target["cell_size_m"])
    target_x = float(target["xmin"]) + (np.arange(columns) + 0.5) * cell
    target_y = float(target["ymax"]) - (np.arange(rows) + 0.5) * cell
    source_columns = np.floor((target_x - float(source_extent.XMin)) / source_cell_x).astype(np.int64)
    source_rows = np.floor((float(source_extent.YMax) - target_y) / source_cell_y).astype(np.int64)
    valid_columns = np.where((source_columns >= 0) & (source_columns < int(header.width)))[0]
    valid_rows = np.where((source_rows >= 0) & (source_rows < int(header.height)))[0]
    if source.ndim == 2:
        output = np.full((rows, columns), fill_value, dtype=source.dtype)
        output[np.ix_(valid_rows, valid_columns)] = source[np.ix_(source_rows[valid_rows], source_columns[valid_columns])]
    elif source.ndim == 3:
        bands = source.shape[0]
        output = np.full((bands, rows, columns), fill_value, dtype=source.dtype)
        output[np.ix_(np.arange(bands), valid_rows, valid_columns)] = source[np.ix_(np.arange(bands), source_rows[valid_rows], source_columns[valid_columns])]
    else:
        raise ValueError(f"unsupported raster array dimensions: {source.ndim}")
    return output


def tabulate_classification(arcpy: Any, aoi_fc: Path, class_raster: Path, output_table: Path, contract: dict[str, Any], unknown_scl_present: bool) -> list[dict[str, Any]]:
    arcpy.sa.TabulateArea(str(aoi_fc), "AOI_ID", str(class_raster), "Value", str(output_table), 20.0, "CLASSES_AS_FIELDS")
    areas = {str(identifier): float(area) for identifier, area in arcpy.da.SearchCursor(str(aoi_fc), ["AOI_ID", "SHAPE@AREA"])}
    fields = {field.name: int(match.group(1)) for field in arcpy.ListFields(str(output_table)) if (match := VALUE_FIELD.match(field.name))}
    if not fields:
        raise RuntimeError("TabulateArea produced no classification fields")
    results = []
    cursor_fields = ["AOI_ID", *fields]
    for row in arcpy.da.SearchCursor(str(output_table), cursor_fields):
        identifier = str(row[0])
        class_areas = {fields[field]: float(value or 0.0) for field, value in zip(cursor_fields[1:], row[1:])}
        valid_area = class_areas.get(VALID_CLASS, 0.0)
        excluded = {REASON_CODES.get(code, f"unknown_classification_{code}"): area for code, area in class_areas.items() if code != VALID_CLASS and area > 0}
        result = evaluate_aoi_coverage(
            aoi_id=identifier,
            aoi_area_m2=areas[identifier],
            covered_area_m2=sum(class_areas.values()),
            valid_area_m2=valid_area,
            excluded_area_by_reason_m2=excluded,
            contract=contract,
        )
        result["classification_area_m2"] = {str(code): area for code, area in sorted(class_areas.items())}
        if unknown_scl_present and result["status"] == "pass_qa_only":
            result["status"] = "defer"
            result["limitations"].append("Unknown SCL values were conservatively excluded and require review.")
        results.append(result)
    return sorted(results, key=lambda item: item["aoi_id"])


def execute(contract: dict[str, Any], started_at: str, attempt_root: Path) -> dict[str, Any]:
    import arcpy  # type: ignore[import-not-found]
    import numpy as np

    pixel_contract = load_pixel_contract(ROOT / contract["inputs"]["pixel_readiness_ref"])
    aoi_path = ROOT / contract["inputs"]["approved_aoi_ref"]
    aoi_json = load_path(aoi_path)
    header = load_path(ROOT / contract["inputs"]["optical_header_receipt_ref"])
    target = contract["analysis_grid"]
    products: dict[str, dict[str, Any]] = {}
    source_roots: dict[str, Path] = {}
    for role in ("before", "after"):
        expected = contract["products"][role]
        materialization = load_path(ROOT / expected["materialization_receipt_ref"])
        safe_root = Path(materialization["external_safe_root"]).resolve(strict=True)
        source_roots[role] = safe_root.parent
        members = {name: safe_root.joinpath(*PurePosixPath(item["relative_path"]).parts) for name, item in expected["selected_members"].items()}
        products[role] = {"safe_root": safe_root, "members": members}
    source_before = {role: inventory(root) for role, root in source_roots.items()}
    arrays: dict[str, dict[str, Any]] = {}
    for role in ("before", "after"):
        arrays[role] = {
            "SCL": read_target(arcpy, products[role]["members"]["SCL"], target, 255),
            "B11": read_target(arcpy, products[role]["members"]["B11"], target, 65535),
            "quality": read_target(arcpy, products[role]["members"]["quality_classification"], target, 255),
        }
    classified = classify_pair_pixels(arrays["before"]["SCL"], arrays["after"]["SCL"], arrays["before"]["quality"], arrays["after"]["quality"], arrays["before"]["B11"], arrays["after"]["B11"])
    sr = arcpy.SpatialReference(32645)
    class_path = attempt_root / "pair_usability_classification_20m.tif"
    class_raster = arcpy.NumPyArrayToRaster(classified["classes"], arcpy.Point(float(target["xmin"]), float(target["ymin"])), 20.0, 20.0, NODATA_CLASS)
    class_raster.save(str(class_path))
    arcpy.management.DefineProjection(str(class_path), sr)
    gdb = attempt_root / "optical_pixel_qa.gdb"
    arcpy.management.CreateFileGDB(str(attempt_root), gdb.name)
    aoi_fc = gdb / "ApprovedStudyAreas"
    arcpy.conversion.JSONToFeatures(str(aoi_path), str(aoi_fc))
    if arcpy.CheckExtension("Spatial") != "Available":
        raise RuntimeError("ArcGIS Spatial Analyst is unavailable")
    arcpy.CheckOutExtension("Spatial")
    try:
        aoi_results = tabulate_classification(arcpy, aoi_fc, class_path, gdb / "AOIPairUsability", pixel_contract, classified["unknown_scl_present"])
    finally:
        arcpy.CheckInExtension("Spatial")
    descriptions = header["products"]
    grid_b11 = evaluate_grid_pair(grid_from_description(descriptions["M1-SRC-010"]["descriptions"]["B11"]), grid_from_description(descriptions["M1-SRC-008"]["descriptions"]["B11"]), pixel_contract)
    grid_scl = evaluate_grid_pair(grid_from_description(descriptions["M1-SRC-010"]["descriptions"]["SCL"]), grid_from_description(descriptions["M1-SRC-008"]["descriptions"]["SCL"]), pixel_contract)
    grid_status = "pass_qa_only" if grid_b11["status"] == grid_scl["status"] == "pass_qa_only" else "block"
    by_id = {feature["attributes"]["AOI_ID"]: feature for feature in aoi_json["features"]}
    registration = measure_stable_registration(
        arrays["before"]["B11"].astype(np.float64), arrays["after"]["B11"].astype(np.float64), classified["pair_valid"],
        grid=target,
        overview_bbox=bbox(by_id["AOI-OVERVIEW"]),
        exclusion_bboxes=[bbox(by_id["AOI-SOURCE"]), bbox(by_id["AOI-UPPER-CORRIDOR"])],
        settings=contract["registration"], pixel_contract=pixel_contract,
    )
    status = final_pixel_decision([item["status"] for item in aoi_results], grid_status, registration["status"])
    metrics = {
        "attempt_id": contract["attempt"]["attempt_id"],
        "started_at_utc": started_at,
        "status": status,
        "aoi_metrics": aoi_results,
        "grid_compatibility": {"status": grid_status, "B11": grid_b11, "SCL": grid_scl, "fixed_target": target},
        "registration": registration,
        "claim_boundary": contract["claim_boundary"],
    }
    source_after = {role: inventory(root) for role, root in source_roots.items()}
    unchanged = source_before == source_after
    if not unchanged:
        status = "invalid"
        metrics["status"] = status
        metrics["external_source_inventory_changed"] = True
    metrics_path = attempt_root / "metrics.json"
    write_new_json(metrics_path, metrics)
    registration_public = {key: value for key, value in registration.items() if key != "controls"}
    outputs = {
        "classification_ref": str(class_path), "classification_sha256": sha256_file(class_path),
        "metrics_ref": str(metrics_path), "metrics_sha256": sha256_file(metrics_path),
    }
    completed = {"status": "complete", "attempt_id": contract["attempt"]["attempt_id"], "decision_status": status, "outputs": outputs}
    write_new_json(attempt_root / "completed.json", completed)
    install = arcpy.GetInstallInfo()
    return {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-S2-PIXEL-READINESS-REAL-001",
        "attempt_id": contract["attempt"]["attempt_id"],
        "started_at_utc": started_at,
        "status": status,
        "runtime": {"product": install.get("ProductName", "ArcGISPro"), "version": install.get("Version"), "license_level": install.get("LicenseLevel", arcpy.ProductInfo()), "spatial_analyst": "available_and_used"},
        "bindings": {"contract_ref": CONTRACT_REF, "contract_sha256": sha256_file(ROOT / CONTRACT_REF)},
        "pair": contract["exact_pair"],
        "approved_aoi_ids": contract["approved_aoi_ids"],
        "aoi_metrics": aoi_results,
        "grid_compatibility": {"status": grid_status, "B11": grid_b11, "SCL": grid_scl, "fixed_target": target},
        "registration": registration_public,
        "external_outputs": outputs,
        "activity": {"network_requests_performed": False, "authentication_performed": False, "source_materialization_inventories_unchanged": unchanged, "real_product_pixels_examined": True, "spectral_indices_computed": False, "candidate_change_polygons_created": False},
        "claim_boundary": contract["claim_boundary"],
        "limitations": contract["limitations"],
        "next_gate": "reconcile this terminal QA-only result; do not retry, substitute, run a baseline, or claim change",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--started-at-utc", required=True)
    parser.add_argument("--receipt-output", required=True)
    args = parser.parse_args()
    if not args.execute:
        raise SystemExit("refusing without --execute")
    if not UTC_TIMESTAMP.fullmatch(args.started_at_utc):
        raise SystemExit("invalid started timestamp")
    validate_pixel_stage_execution()
    contract = load_path(ROOT / CONTRACT_REF)
    errors = validate_contract(contract)
    if errors:
        raise SystemExit("invalid optical pixel contract: " + "; ".join(errors))
    if args.attempt_id != contract["attempt"]["attempt_id"] or args.receipt_output != contract["attempt"]["public_receipt_ref"]:
        raise SystemExit("exact optical pixel attempt identity differs")
    attempt_root = Path(contract["attempt"]["external_attempt_root"])
    receipt_path = ROOT / args.receipt_output
    if attempt_root.exists() or receipt_path.exists():
        raise SystemExit("refusing optical pixel attempt collision")
    os.environ.setdefault("GDAL_PAM_ENABLED", "NO")
    attempt_root.mkdir(parents=True, exist_ok=False)
    write_new_json(attempt_root / "started.json", {"status": "started", "attempt_id": args.attempt_id, "started_at_utc": args.started_at_utc, "contract_sha256": sha256_file(ROOT / CONTRACT_REF)})
    try:
        receipt = execute(contract, args.started_at_utc, attempt_root)
    except Exception as exc:
        failure = {"status": "invalid", "attempt_id": args.attempt_id, "started_at_utc": args.started_at_utc, "error_type": type(exc).__name__, "error": str(exc), "automatic_retry_authorized": False}
        write_new_json(attempt_root / "failure.json", failure)
        write_new_json(receipt_path, {**failure, "receipt_id": "NEPAL-S2-PIXEL-READINESS-REAL-001", "activity": {"real_product_pixel_access_attempted": True}, "next_gate": "retain terminal failure; a new attempt requires separate authority"})
        print(json.dumps({"status": "invalid", "receipt": args.receipt_output, "error_type": type(exc).__name__}, indent=2))
        return 20
    write_new_json(receipt_path, receipt)
    print(json.dumps({"status": receipt["status"], "receipt": args.receipt_output}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
