#!/usr/bin/env python3
"""Exercise the nested production-grid correction with synthetic ArcGIS rasters."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import arcpy
import numpy as np

import run_m2_optical_pixel_readiness_001 as original
from optical_pixel_readiness_core_001 import classify_pair_pixels, measure_stable_registration
from optical_pixel_recovery_core_001 import normalize_analysis_grid, validate_recovery_contract
from pixel_qa_core import load_contract as load_pixel_contract


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(array: np.ndarray, path: Path, xmin: float, ymin: float, cell: float, sr: arcpy.SpatialReference) -> None:
    raster = arcpy.NumPyArrayToRaster(array, arcpy.Point(xmin, ymin), cell, cell)
    raster.save(str(path))
    arcpy.management.DefineProjection(str(path), sr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--receipt-output", type=Path, required=True)
    parser.add_argument("--verified-at-utc", required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    output_root = (repo / args.output_root).resolve(strict=False)
    receipt = (repo / args.receipt_output).resolve(strict=False)
    if output_root.exists() or receipt.exists():
        raise SystemExit("synthetic recovery output collision")
    output_root.mkdir(parents=True)
    contract_path = repo / "config/qa/optical-pixel-readiness-contract-recovery-001.json"
    original_path = repo / "config/qa/optical-pixel-readiness-contract-001.json"
    pixel_path = repo / "config/qa/pixel-readiness-contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    original_contract = json.loads(original_path.read_text(encoding="utf-8"))
    errors = validate_recovery_contract(contract, original_contract)
    if errors:
        raise SystemExit("invalid exact recovery contract: " + "; ".join(errors))
    pixel_contract = load_pixel_contract(pixel_path)
    rows = columns = 240
    xmin, ymin, cell = 300000.0, 3100000.0, 20.0
    target_nested = {
        "wkid": 32645,
        "name": "WGS 1984 UTM Zone 45N",
        "cell_size_m": cell,
        "snap_basis": "synthetic exact production object shape",
        "extent": {
            "xmin": xmin,
            "ymin": ymin,
            "xmax": xmin + columns * cell,
            "ymax": ymin + rows * cell,
        },
        "columns": columns,
        "rows": rows,
        "continuous_resampling": "BILINEAR",
        "categorical_resampling": "NEAREST",
        "grid_drift_disposition": "block",
    }
    target = normalize_analysis_grid(target_nested)
    if any(key in target_nested for key in ("xmin", "ymin", "xmax", "ymax")):
        raise RuntimeError("synthetic input did not preserve the nested production shape")
    sr = arcpy.SpatialReference(32645)
    rng = np.random.default_rng(260905)
    before = rng.integers(800, 5000, size=(rows, columns), dtype=np.uint16)
    after = before.copy()
    scl_before = np.full((rows, columns), 4, dtype=np.uint8)
    scl_after = np.full((rows, columns), 4, dtype=np.uint8)
    scl_after[:, ::10] = 9
    zero = np.zeros((rows, columns), dtype=np.uint8)
    paths = {}
    for name, array in (("before_b11", before), ("after_b11", after), ("before_scl", scl_before), ("after_scl", scl_after)):
        path = output_root / f"{name}.tif"
        save(array, path, xmin, ymin, cell, sr)
        paths[name] = path
    quality_bands = []
    for index in range(3):
        path = output_root / f"quality_{index + 1}.tif"
        save(zero, path, xmin, ymin, cell, sr)
        quality_bands.append(path)
    quality_path = output_root / "quality_three_band.tif"
    arcpy.management.CompositeBands([str(path) for path in quality_bands], str(quality_path))
    observed = {
        "before_b11": original.read_target(arcpy, paths["before_b11"], target, 65535),
        "after_b11": original.read_target(arcpy, paths["after_b11"], target, 65535),
        "before_scl": original.read_target(arcpy, paths["before_scl"], target, 255),
        "after_scl": original.read_target(arcpy, paths["after_scl"], target, 255),
        "quality": original.read_target(arcpy, quality_path, target, 255),
    }
    classified = classify_pair_pixels(
        observed["before_scl"],
        observed["after_scl"],
        observed["quality"],
        observed["quality"],
        observed["before_b11"],
        observed["after_b11"],
    )
    registration = measure_stable_registration(
        observed["before_b11"].astype(np.float64),
        observed["after_b11"].astype(np.float64),
        classified["pair_valid"],
        grid=target,
        overview_bbox=(xmin, ymin, target["xmax"], target["ymax"]),
        exclusion_bboxes=[],
        settings=contract["registration"],
        pixel_contract=pixel_contract,
    )
    shifted = np.roll(observed["after_b11"], 2, axis=1)
    shifted_registration = measure_stable_registration(
        observed["before_b11"].astype(np.float64),
        shifted.astype(np.float64),
        classified["pair_valid"],
        grid=target,
        overview_bbox=(xmin, ymin, target["xmax"], target["ymax"]),
        exclusion_bboxes=[],
        settings=contract["registration"],
        pixel_contract=pixel_contract,
    )
    if registration["status"] != "pass_qa_only" or registration["accepted_control_count"] < 30:
        raise RuntimeError("aligned nested-grid registration did not pass")
    if shifted_registration["status"] != "block":
        raise RuntimeError("two-pixel nested-grid synthetic shift did not block")
    if not np.any(classified["classes"] == 209) or not np.any(classified["classes"] == 1):
        raise RuntimeError("conservative SCL classification differs")
    install = arcpy.GetInstallInfo()
    record = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-S2-PIXEL-READINESS-RECOVERY-001-SYNTHETIC-ARCGIS",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_exact_nested_production_shape_arcgis_synthetic",
        "runtime": {
            "product": install.get("ProductName", "ArcGISPro"),
            "version": install.get("Version"),
            "license_level": install.get("LicenseLevel", arcpy.ProductInfo()),
        },
        "bindings": {
            "contract_ref": "config/qa/optical-pixel-readiness-contract-recovery-001.json",
            "contract_sha256": sha256(contract_path),
            "source_scientific_contract_sha256": sha256(original_path),
            "pixel_contract_sha256": sha256(pixel_path),
            "adapter_sha256": sha256(Path(__file__)),
        },
        "checks": {
            "nested_input_extent": target_nested["extent"],
            "normalized_bounds": {key: target[key] for key in ("xmin", "ymin", "xmax", "ymax")},
            "aligned_registration": {key: value for key, value in registration.items() if key != "controls"},
            "two_pixel_shift": {key: value for key, value in shifted_registration.items() if key != "controls"},
            "valid_pixel_count": int(np.sum(classified["classes"] == 1)),
            "after_cloud_pixel_count": int(np.sum(classified["classes"] == 209)),
        },
        "assertions": {
            "exact_production_object_shape_used": True,
            "nested_extent_normalized": True,
            "synthetic_rasters_only": True,
            "real_materialization_receipts_used": False,
            "external_custody_accessed": False,
            "real_product_pixels_examined": False,
            "scientific_thresholds_changed": False,
            "spectral_indices_computed": False,
            "candidate_change_polygons_created": False,
        },
        "next_gate": "portable tests and fresh public CI before the recovery no-pixel preflight",
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    with receipt.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"status": record["status"], "receipt": str(receipt)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
