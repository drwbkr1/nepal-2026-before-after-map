#!/usr/bin/env python3
"""Exercise exact optical pixel QA mechanics with synthetic ArcGIS rasters."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import arcpy
import numpy as np

from optical_pixel_readiness_core_001 import classify_pair_pixels, measure_stable_registration, validate_contract
from pixel_qa_core import load_contract as load_pixel_contract
from run_m2_optical_pixel_readiness_001 import read_target


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
        raise SystemExit("synthetic output collision")
    output_root.mkdir(parents=True)
    contract_path = repo / "config/qa/optical-pixel-readiness-contract-001.json"
    pixel_path = repo / "config/qa/pixel-readiness-contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    errors = validate_contract(contract)
    if errors:
        raise SystemExit("invalid exact contract: " + "; ".join(errors))
    pixel_contract = load_pixel_contract(pixel_path)
    rows = columns = 240
    xmin, ymin, cell = 300000.0, 3100000.0, 20.0
    target = {"xmin": xmin, "ymin": ymin, "xmax": xmin + columns * cell, "ymax": ymin + rows * cell, "rows": rows, "columns": columns, "cell_size_m": cell}
    sr = arcpy.SpatialReference(32645)
    rng = np.random.default_rng(260827)
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
        "before_b11": read_target(arcpy, paths["before_b11"], target, 65535),
        "after_b11": read_target(arcpy, paths["after_b11"], target, 65535),
        "before_scl": read_target(arcpy, paths["before_scl"], target, 255),
        "after_scl": read_target(arcpy, paths["after_scl"], target, 255),
        "quality": read_target(arcpy, quality_path, target, 255),
    }
    classified = classify_pair_pixels(observed["before_scl"], observed["after_scl"], observed["quality"], observed["quality"], observed["before_b11"], observed["after_b11"])
    registration = measure_stable_registration(
        observed["before_b11"].astype(np.float64), observed["after_b11"].astype(np.float64), classified["pair_valid"],
        grid=target, overview_bbox=(xmin, ymin, target["xmax"], target["ymax"]), exclusion_bboxes=[], settings=contract["registration"], pixel_contract=pixel_contract,
    )
    shifted = np.roll(observed["after_b11"], 2, axis=1)
    shifted_registration = measure_stable_registration(
        observed["before_b11"].astype(np.float64), shifted.astype(np.float64), classified["pair_valid"],
        grid=target, overview_bbox=(xmin, ymin, target["xmax"], target["ymax"]), exclusion_bboxes=[], settings=contract["registration"], pixel_contract=pixel_contract,
    )
    if registration["status"] != "pass_qa_only" or registration["accepted_control_count"] < 30:
        raise RuntimeError("aligned stable-control registration did not pass")
    if shifted_registration["status"] != "block":
        raise RuntimeError("two-pixel synthetic shift did not block")
    if not np.any(classified["classes"] == 209) or not np.any(classified["classes"] == 1):
        raise RuntimeError("conservative SCL classification differs")
    install = arcpy.GetInstallInfo()
    record = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-S2-PIXEL-READINESS-SYNTHETIC-ARCGIS-001",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_synthetic_arcgis_with_expected_shift_block",
        "runtime": {"product": install.get("ProductName", "ArcGISPro"), "version": install.get("Version"), "license_level": install.get("LicenseLevel", arcpy.ProductInfo())},
        "bindings": {"contract_ref": "config/qa/optical-pixel-readiness-contract-001.json", "contract_sha256": sha256(contract_path), "pixel_contract_sha256": sha256(pixel_path), "adapter_sha256": sha256(Path(__file__))},
        "checks": {"aligned_registration": {key: value for key, value in registration.items() if key != "controls"}, "two_pixel_shift": {key: value for key, value in shifted_registration.items() if key != "controls"}, "valid_pixel_count": int(np.sum(classified["classes"] == 1)), "after_cloud_pixel_count": int(np.sum(classified["classes"] == 209))},
        "assertions": {"synthetic_rasters_only": True, "real_materialization_receipts_used": False, "external_custody_accessed": False, "real_product_pixels_examined": False, "spectral_indices_computed": False, "candidate_change_polygons_created": False},
        "next_gate": "portable tests and public CI before any real optical pixel access",
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": record["status"], "receipt": str(receipt)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
