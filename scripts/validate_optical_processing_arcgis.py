#!/usr/bin/env python3
"""Exercise the optical contract with deterministic synthetic ArcGIS rasters."""

from __future__ import annotations

import argparse
import datetime as datetime_module
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import arcpy
import numpy as np

from optical_processing_core import (
    normalized_difference,
    parse_l2a_scaling_metadata,
    scale_reflectance_dn,
    validate_contract,
)


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


def save_raster(
    array: np.ndarray,
    path: Path,
    xmin: float,
    ymin: float,
    cell_size: float,
    spatial_reference: arcpy.SpatialReference,
) -> None:
    raster = arcpy.NumPyArrayToRaster(array, arcpy.Point(xmin, ymin), cell_size, cell_size)
    raster.save(str(path))
    arcpy.management.DefineProjection(str(path), spatial_reference)


def synthetic_metadata_xml(offset: int, quantification: int) -> str:
    offsets = "".join(
        f'<BOA_ADD_OFFSET band_id="{band_id}">{offset}</BOA_ADD_OFFSET>'
        for band_id in range(13)
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Level2A_User_Product xmlns="urn:synthetic:sentinel2">
  <General_Info>
    <Product_Info><PROCESSING_BASELINE>05.12</PROCESSING_BASELINE></Product_Info>
    <Product_Image_Characteristics>
      <Special_Values><SPECIAL_VALUE_TEXT>NODATA</SPECIAL_VALUE_TEXT><SPECIAL_VALUE_INDEX>0</SPECIAL_VALUE_INDEX></Special_Values>
      <BOA_QUANTIFICATION_VALUE>{quantification}</BOA_QUANTIFICATION_VALUE>
      <BOA_ADD_OFFSET_VALUES_LIST>{offsets}</BOA_ADD_OFFSET_VALUES_LIST>
    </Product_Image_Characteristics>
  </General_Info>
</Level2A_User_Product>"""


def raster_array(path: Path, nodata: float = -9999.0) -> np.ndarray:
    return arcpy.RasterToNumPyArray(str(path), nodata_to_value=nodata).astype(np.float64)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path("config/qa/optical-baseline-processing-contract.json"),
    )
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--receipt-output", type=Path, required=True)
    parser.add_argument("--verified-at-utc", default=None)
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    contract_path = (repo / args.contract).resolve()
    output_root = require_new_scratch_path(repo, repo / args.output_root)
    receipt_path = (repo / args.receipt_output).resolve(strict=False)
    if receipt_path.exists():
        raise SystemExit(f"Receipt path already exists; refusing replacement: {receipt_path}")
    if not receipt_path.parent.is_dir():
        raise SystemExit(f"Receipt parent must already exist: {receipt_path.parent}")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract_errors = validate_contract(contract)
    if contract_errors:
        raise SystemExit("Invalid contract: " + "; ".join(contract_errors))
    if arcpy.CheckExtension("Spatial") != "Available":
        raise SystemExit("ArcGIS Spatial Analyst is unavailable")

    spatial_reference = arcpy.SpatialReference(32645)
    rows = columns = 16
    cell_size = 20.0
    xmin = 300000.0
    ymin = 3100000.0
    offset = -1000
    quantification = 10000
    band_dn = {
        "B03": 2500,
        "B04": 3000,
        "B08": 5000,
        "B11": 2000,
        "B12": 1500,
    }
    raw_paths: dict[str, Path] = {}
    for band, value in band_dn.items():
        array = np.full((rows, columns), value, dtype=np.uint16)
        if band == "B04":
            array[0, 1] = 0
        path = output_root / f"synthetic_{band}_dn.tif"
        save_raster(array, path, xmin, ymin, cell_size, spatial_reference)
        raw_paths[band] = path

    scl = np.full((rows, columns), 4, dtype=np.uint8)
    scl[:, ::4] = 9
    scl_path = output_root / "synthetic_SCL.tif"
    save_raster(scl, scl_path, xmin, ymin, cell_size, spatial_reference)

    metadata_path = output_root / "synthetic_MTD_MSIL2A.xml"
    metadata_path.write_text(synthetic_metadata_xml(offset, quantification), encoding="utf-8", newline="\n")
    parsed_metadata = parse_l2a_scaling_metadata(metadata_path.read_text(encoding="utf-8"))
    if parsed_metadata["errors"]:
        raise RuntimeError("synthetic metadata did not parse: " + "; ".join(parsed_metadata["errors"]))

    output_paths: dict[str, Path] = {}
    arcpy.CheckOutExtension("Spatial")
    try:
        with arcpy.EnvManager(
            outputCoordinateSystem=spatial_reference,
            snapRaster=str(scl_path),
            cellSize=cell_size,
            extent=str(scl_path),
            overwriteOutput=False,
        ):
            scl_raster = arcpy.sa.Raster(str(scl_path))
            invalid_scl = (scl_raster != 4) & (scl_raster != 5) & (scl_raster != 6)
            scaled: dict[str, Any] = {}
            for band, raw_path in raw_paths.items():
                raw = arcpy.sa.Raster(str(raw_path))
                value = arcpy.sa.SetNull((raw == 0) | invalid_scl, (arcpy.sa.Float(raw) + offset) / quantification)
                output_path = output_root / f"synthetic_{band}_reflectance.tif"
                value.save(str(output_path))
                scaled[band] = arcpy.sa.Raster(str(output_path))
                output_paths[band] = output_path

            epsilon = float(contract["indices"]["denominator_absolute_minimum"])
            index_specs = {
                "NDVI": (scaled["B08"], scaled["B04"]),
                "MNDWI": (scaled["B03"], scaled["B11"]),
                "NBR": (scaled["B08"], scaled["B12"]),
            }
            for name, (first, second) in index_specs.items():
                denominator = first + second
                result = arcpy.sa.SetNull(arcpy.sa.Abs(denominator) <= epsilon, (first - second) / denominator)
                output_path = output_root / f"synthetic_{name}.tif"
                result.save(str(output_path))
                output_paths[name] = output_path
    finally:
        arcpy.CheckInExtension("Spatial")

    nodata_value = -9999.0
    arrays = {name: raster_array(path, nodata_value) for name, path in output_paths.items()}
    valid_mask = scl != 9
    expected_valid_count = int(valid_mask.sum())
    expected_b04_valid_count = expected_valid_count - 1
    expected_values = {
        band: scale_reflectance_dn(value, offset, quantification)
        for band, value in band_dn.items()
    }
    expected_values.update(
        {
            "NDVI": normalized_difference(expected_values["B08"], expected_values["B04"], 1e-6),
            "MNDWI": normalized_difference(expected_values["B03"], expected_values["B11"], 1e-6),
            "NBR": normalized_difference(expected_values["B08"], expected_values["B12"], 1e-6),
        }
    )
    checks: dict[str, Any] = {}
    errors: list[str] = []
    for name, array in arrays.items():
        valid_values = array[array != nodata_value]
        expected_count = expected_b04_valid_count if name in {"B04", "NDVI"} else expected_valid_count
        value_ok = valid_values.size == expected_count and np.allclose(
            valid_values,
            float(expected_values[name]),
            rtol=0,
            atol=1e-6,
        )
        checks[name] = {
            "status": "pass" if value_ok else "fail",
            "expected_value": expected_values[name],
            "observed_min": float(valid_values.min()) if valid_values.size else None,
            "observed_max": float(valid_values.max()) if valid_values.size else None,
            "expected_valid_cell_count": expected_count,
            "observed_valid_cell_count": int(valid_values.size),
        }
        if not value_ok:
            errors.append(f"{name} scaling, mask, or index result differs")

    b04_array = arrays["B04"]
    if b04_array[0, 1] != nodata_value:
        errors.append("DN zero did not remain NoData before offset")
    if not np.all(b04_array[:, ::4] == nodata_value):
        errors.append("excluded SCL class 9 did not remain NoData")
    if errors:
        raise RuntimeError("; ".join(errors))

    install = arcpy.GetInstallInfo()
    verified_at = args.verified_at_utc or datetime_module.datetime.now(
        datetime_module.timezone.utc
    ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    script_path = Path(__file__).resolve()
    core_path = script_path.with_name("optical_processing_core.py")
    receipt = {
        "receipt_id": "NEPAL-S2-OPTICAL-PROCESSING-SYNTHETIC-ARCGIS-001",
        "status": "pass_synthetic_only",
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
            "core": repo_relative(repo, core_path),
            "core_sha256": sha256(core_path),
            "arcgis_adapter": repo_relative(repo, script_path),
            "arcgis_adapter_sha256": sha256(script_path),
        },
        "synthetic_fixture": {
            "output_root": str(output_root),
            "wkid": 32645,
            "cell_size_m": cell_size,
            "rows": rows,
            "columns": columns,
            "processing_baseline": parsed_metadata["processing_baseline"],
            "quantification_value": parsed_metadata["quantification_value"],
            "offsets_by_used_band": {
                band: parsed_metadata["offsets_by_band"][band] for band in sorted(band_dn)
            },
            "raw_dn_by_band": band_dn,
            "scl_pattern": "class 9 in every fourth column; class 4 elsewhere",
            "b04_dn_zero_location": [0, 1],
            "input_sha256": {
                **{path.name: sha256(path) for path in raw_paths.values()},
                scl_path.name: sha256(scl_path),
                metadata_path.name: sha256(metadata_path),
            },
            "output_sha256": {path.name: sha256(path) for path in output_paths.values()},
        },
        "checks": checks,
        "assertions": {
            "metadata_baseline_quantification_and_offsets_parsed": True,
            "dn_zero_preserved_as_nodata": True,
            "excluded_scl_preserved_as_nodata": True,
            "reflectance_scaling_matches_predeclared_formula": True,
            "normalized_indices_match_predeclared_formulas": True,
            "real_product_metadata_parsed": False,
            "real_product_pixels_examined": False,
            "external_custody_accessed": False,
            "source_association_created": False,
            "optical_baseline_established": False,
            "change_established": False,
            "scientific_admission_authorized": False,
        },
        "claim_boundary": contract["claim_boundary"],
        "limitations": [
            "All raster and metadata inputs are deterministic synthetic fixtures.",
            "The check proves ArcGIS raster algebra, NoData handling, SCL exclusion, scaling, and index formulas only.",
            "It does not establish real-product identity, usable AOI coverage, registration, cross-platform comparability, optical change, interpretation, or attribution.",
            "The post-event optical product remains high-cloud-risk and may be inconclusive.",
        ],
        "preserved_review_bindings": {
            "source_manifest_sha256": contract["bindings"]["source_manifest_sha256"],
            "m2_activation_review_bundle_sha256": "e8d105970d64c43d955ff459ba9e5d5a3a1e4fb4f95874aa67f384e6b293a35d",
            "acquisition_plan_sha256": "6261dc61061cb962f22163755047f080e309ed2d746cdcdd61e6cf61d7ec2a8d",
        },
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "status": receipt["status"],
        "receipt": str(receipt_path),
        "checks": {name: result["status"] for name, result in checks.items()},
        "real_product_pixels_examined": False,
        "scientific_admission_authorized": False,
    }, indent=2))


if __name__ == "__main__":
    main()
