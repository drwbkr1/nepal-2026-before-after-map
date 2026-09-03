#!/usr/bin/env python3
"""Verify one authorized Copernicus DEM GeoTIFF in read-only local custody."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return value


def tiff_signature(path: Path) -> str:
    with path.open("rb") as handle:
        return handle.read(4).hex()


def expected_extent(asset: dict[str, Any]) -> list[float]:
    transform = asset["expected_transform"]
    rows, columns = asset["expected_shape"]
    xmin = transform[0]
    ymax = transform[3]
    xmax = xmin + columns * transform[1]
    ymin = ymax + rows * transform[5]
    return [xmin, ymin, xmax, ymax]


def evaluate_metadata(
    asset: dict[str, Any], observed: dict[str, Any], controls: dict[str, Any]
) -> dict[str, Any]:
    checks: dict[str, dict[str, Any]] = {}

    def check(name: str, passed: bool, expected: Any, actual: Any) -> None:
        checks[name] = {
            "status": "pass" if passed else "fail",
            "expected": expected,
            "actual": actual,
        }

    check(
        "size_bytes",
        observed.get("size_bytes") == asset["expected_size_bytes"],
        asset["expected_size_bytes"],
        observed.get("size_bytes"),
    )
    check(
        "tiff_signature",
        observed.get("tiff_signature") in controls["tiff_signatures"],
        controls["tiff_signatures"],
        observed.get("tiff_signature"),
    )
    check(
        "shape",
        observed.get("shape") == asset["expected_shape"],
        asset["expected_shape"],
        observed.get("shape"),
    )
    check(
        "band_count",
        observed.get("band_count") == asset["expected_band_count"],
        asset["expected_band_count"],
        observed.get("band_count"),
    )
    check(
        "pixel_type",
        observed.get("pixel_type") == asset["expected_pixel_type"],
        asset["expected_pixel_type"],
        observed.get("pixel_type"),
    )
    check(
        "crs_wkid",
        observed.get("crs_wkid") == asset["expected_crs_wkid"],
        asset["expected_crs_wkid"],
        observed.get("crs_wkid"),
    )
    cell_tolerance = controls["cell_size_absolute_tolerance_degrees"]
    actual_cell = observed.get("cell_size_degrees")
    cell_ok = (
        isinstance(actual_cell, list)
        and len(actual_cell) == 2
        and all(
            math.isfinite(float(actual)) and abs(float(actual) - expected) <= cell_tolerance
            for actual, expected in zip(actual_cell, asset["expected_cell_size_degrees"])
        )
    )
    check("cell_size", cell_ok, asset["expected_cell_size_degrees"], actual_cell)

    extent_tolerance = controls["extent_absolute_tolerance_degrees"]
    expected_bounds = expected_extent(asset)
    actual_extent = observed.get("extent_wgs84")
    extent_ok = (
        isinstance(actual_extent, list)
        and len(actual_extent) == 4
        and all(
            math.isfinite(float(actual)) and abs(float(actual) - expected) <= extent_tolerance
            for actual, expected in zip(actual_extent, expected_bounds)
        )
    )
    check("raster_extent", extent_ok, expected_bounds, actual_extent)

    nodata = observed.get("nodata")
    nodata_ok = isinstance(nodata, dict) and {
        "any_nodata",
        "all_nodata",
        "nodata_value",
    }.issubset(nodata)
    check("nodata_property_inspection", nodata_ok, "captured", nodata)

    statistics = observed.get("statistics")
    statistics_ok = (
        isinstance(statistics, dict)
        and all(key in statistics for key in ("minimum", "maximum"))
        and all(math.isfinite(float(statistics[key])) for key in ("minimum", "maximum"))
        and float(statistics["minimum"]) <= float(statistics["maximum"])
    )
    check("statistics_capture", statistics_ok, "finite minimum <= maximum", statistics)
    failures = [name for name, result in checks.items() if result["status"] != "pass"]
    return {
        "status": "pass_structural_only" if not failures else "fail",
        "checks": checks,
        "failures": failures,
        "valid_pixel_coverage_established": False,
        "vertical_datum_route_established": False,
        "scientific_fitness_established": False,
    }


def inspect_with_arcpy(path: Path) -> dict[str, Any]:
    import arcpy  # type: ignore

    description = arcpy.Describe(str(path))

    def raster_property(name: str) -> str:
        return str(arcpy.management.GetRasterProperties(str(path), name).getOutput(0))

    return {
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "tiff_signature": tiff_signature(path),
        "shape": [int(description.height), int(description.width)],
        "band_count": int(description.bandCount),
        "pixel_type": str(description.pixelType),
        "crs_wkid": int(description.spatialReference.factoryCode),
        "cell_size_degrees": [float(description.meanCellWidth), float(description.meanCellHeight)],
        "extent_wgs84": [
            float(description.extent.XMin),
            float(description.extent.YMin),
            float(description.extent.XMax),
            float(description.extent.YMax),
        ],
        "nodata": {
            "any_nodata": raster_property("ANYNODATA"),
            "all_nodata": raster_property("ALLNODATA"),
            "nodata_value": raster_property("NODATAVALUE"),
        },
        "statistics": {
            "minimum": float(raster_property("MINIMUM")),
            "maximum": float(raster_property("MAXIMUM")),
        },
    }


def validate_active_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if contract.get("status") != "active":
        errors.append("verification contract is not active")
    authority = contract.get("authority", {})
    if authority.get("dem_amendment_status") != "approved":
        errors.append("DEM amendment is not approved")
    if authority.get("dem_pixel_processing_authorized") is not True:
        errors.append("DEM pixel processing is not authorized")
    if authority.get("this_contract_creates_authority") is not False:
        errors.append("verification contract must not create authority")
    return errors


def write_new(path: Path, value: object) -> None:
    if not path.parent.is_dir():
        raise SystemExit(f"REFUSED: output parent does not already exist: {path.parent}")
    if path.exists():
        raise SystemExit(f"REFUSED: output receipt already exists: {path}")
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--asset-id", required=True)
    parser.add_argument("--custody-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    contract_path = args.contract if args.contract.is_absolute() else ROOT / args.contract
    contract = load_json(contract_path)
    errors = validate_active_contract(contract)
    if errors:
        raise SystemExit("REFUSED: " + "; ".join(errors))
    matches = [item for item in contract.get("assets", []) if item.get("asset_id") == args.asset_id]
    if len(matches) != 1:
        raise SystemExit(f"REFUSED: asset identity is not unique in contract: {args.asset_id}")
    asset = matches[0]
    raster = (args.custody_root.resolve() / asset["raster_relative_path"]).resolve()
    try:
        raster.relative_to(args.custody_root.resolve())
    except ValueError as exc:
        raise SystemExit("REFUSED: raster path escapes custody root") from exc
    if not raster.is_file():
        raise SystemExit(f"REFUSED: promoted DEM raster is missing: {raster}")

    observed = inspect_with_arcpy(raster)
    evaluation = evaluate_metadata(asset, observed, contract["raster_controls"])
    receipt = {
        "verification_id": contract["verification_id"],
        "asset_id": asset["asset_id"],
        "source_id": asset["source_id"],
        "contract_sha256": sha256_file(contract_path),
        "raster_relative_path": asset["raster_relative_path"],
        "observed": observed,
        "evaluation": evaluation,
        "claim_boundary": {
            "structural_raster_fitness_established": evaluation["status"] == "pass_structural_only",
            "valid_pixel_coverage_established": False,
            "vertical_datum_route_established": False,
            "sentinel_processing_executed": False,
            "scientific_result_established": False,
        },
    }
    output = args.output if args.output.is_absolute() else ROOT / args.output
    write_new(output, receipt)
    print(json.dumps({"status": evaluation["status"], "output": str(output)}, indent=2))
    if evaluation["status"] != "pass_structural_only":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
