#!/usr/bin/env python3
"""Exercise Sentinel-2 materialized-input readiness with synthetic JP2 files."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import arcpy
import numpy as np
from osgeo import gdal, osr

from m2_materialization_core import sha256_file, write_new_json
from optical_input_readiness_core_full_cohort_001 import (
    RASTER_ROLES,
    decide_header_readiness,
    select_required_members,
    validate_pair_grids,
)
from optical_processing_core import parse_l2a_scaling_metadata


ROOT = Path(__file__).resolve().parents[1]
UTC_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


def load(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def digest(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def metadata_xml() -> str:
    offsets = "".join(f'<BOA_ADD_OFFSET band_id="{band_id}">-1000</BOA_ADD_OFFSET>' for band_id in range(13))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Level2A_User_Product xmlns="urn:synthetic:sentinel2">
  <General_Info><Product_Info><PROCESSING_BASELINE>05.12</PROCESSING_BASELINE></Product_Info>
  <Product_Image_Characteristics>
    <Special_Values><SPECIAL_VALUE_TEXT>NODATA</SPECIAL_VALUE_TEXT><SPECIAL_VALUE_INDEX>0</SPECIAL_VALUE_INDEX></Special_Values>
    <BOA_QUANTIFICATION_VALUE>10000</BOA_QUANTIFICATION_VALUE>
    <BOA_ADD_OFFSET_VALUES_LIST>{offsets}</BOA_ADD_OFFSET_VALUES_LIST>
  </Product_Image_Characteristics></General_Info>
</Level2A_User_Product>"""


def create_jp2(
    path: Path,
    *,
    width: int,
    height: int,
    cell: float,
    pixel_type: int,
    value: int,
    band_count: int = 1,
) -> None:
    temporary = path.with_suffix(".source.tif")
    dataset = gdal.GetDriverByName("GTiff").Create(str(temporary), width, height, band_count, pixel_type)
    if dataset is None:
        raise RuntimeError("GDAL could not create the synthetic GeoTIFF")
    dataset.SetGeoTransform((273300.0, cell, 0.0, 3070380.0, 0.0, -cell))
    spatial_reference = osr.SpatialReference()
    spatial_reference.ImportFromEPSG(32645)
    dataset.SetProjection(spatial_reference.ExportToWkt())
    dtype = np.uint8 if pixel_type == gdal.GDT_Byte else np.uint16
    for band_index in range(1, band_count + 1):
        dataset.GetRasterBand(band_index).WriteArray(
            np.full((height, width), value if band_index == 1 else 0, dtype=dtype)
        )
    dataset = None
    source = gdal.Open(str(temporary))
    target = gdal.GetDriverByName("JP2OpenJPEG").CreateCopy(str(path), source, strict=1, options=["REVERSIBLE=YES"])
    if target is None:
        raise RuntimeError("GDAL could not create the synthetic JPEG2000")
    target = None
    source = None


def describe(path: Path) -> dict[str, Any]:
    item = arcpy.Describe(str(path))
    extent = item.extent
    children = sorted(
        list(getattr(item, "children", []) or []),
        key=lambda child: str(getattr(child, "name", "")),
    )
    header_source = children[0] if children else item
    result = {
        "format": getattr(item, "format", None),
        "wkid": getattr(item.spatialReference, "factoryCode", None),
        "band_count": getattr(item, "bandCount", None),
        "width": getattr(header_source, "width", None),
        "height": getattr(header_source, "height", None),
        "cell_width": getattr(header_source, "meanCellWidth", None),
        "cell_height": getattr(header_source, "meanCellHeight", None),
        "pixel_type": getattr(header_source, "pixelType", None),
        "xmin": extent.XMin,
        "ymin": extent.YMin,
        "xmax": extent.XMax,
        "ymax": extent.YMax,
    }
    if children:
        result["band_details"] = [
            {
                "name": getattr(child, "name", None),
                "width": getattr(child, "width", None),
                "height": getattr(child, "height", None),
                "cell_width": getattr(child, "meanCellWidth", None),
                "cell_height": getattr(child, "meanCellHeight", None),
                "pixel_type": getattr(child, "pixelType", None),
            }
            for child in children
        ]
    return result


def create_safe(root: Path, product_id: str) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    safe = root / product_id
    files = {
        "metadata_product": safe / "MTD_MSIL2A.xml",
        "metadata_tile": safe / "GRANULE/G/MTD_TL.xml",
        "B02": safe / "GRANULE/G/IMG_DATA/R10m/T_B02_10m.jp2",
        "B03": safe / "GRANULE/G/IMG_DATA/R10m/T_B03_10m.jp2",
        "B04": safe / "GRANULE/G/IMG_DATA/R10m/T_B04_10m.jp2",
        "B08": safe / "GRANULE/G/IMG_DATA/R10m/T_B08_10m.jp2",
        "B11": safe / "GRANULE/G/IMG_DATA/R20m/T_B11_20m.jp2",
        "B12": safe / "GRANULE/G/IMG_DATA/R20m/T_B12_20m.jp2",
        "SCL": safe / "GRANULE/G/IMG_DATA/R20m/T_SCL_20m.jp2",
        "quality_classification": safe / "GRANULE/G/QI_DATA/MSK_CLASSI_B00.jp2",
    }
    for path in files.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    files["metadata_product"].write_text(metadata_xml(), encoding="utf-8")
    files["metadata_tile"].write_text("<Synthetic_Tile_Metadata/>", encoding="utf-8")
    for role in ("B02", "B03", "B04", "B08"):
        create_jp2(files[role], width=12, height=12, cell=10.0, pixel_type=gdal.GDT_UInt16, value=3000)
    for role in ("B11", "B12"):
        create_jp2(files[role], width=6, height=6, cell=20.0, pixel_type=gdal.GDT_UInt16, value=2000)
    create_jp2(files["SCL"], width=6, height=6, cell=20.0, pixel_type=gdal.GDT_Byte, value=4)
    create_jp2(
        files["quality_classification"],
        width=2,
        height=2,
        cell=60.0,
        pixel_type=gdal.GDT_Byte,
        value=1,
        band_count=3,
    )
    manifest_files = []
    for path in sorted((item for item in safe.rglob("*") if item.is_file() and not item.name.endswith(".source.tif"))):
        manifest_files.append(
            {
                "relative_path": path.relative_to(safe).as_posix(),
                "size_bytes": path.stat().st_size,
                "zip_crc32": "synthetic",
                "sha256": sha256_file(path),
            }
        )
    descriptions = {role: describe(path) for role, path in files.items() if role in RASTER_ROLES}
    return {
        "manifest_version": "1.0",
        "status": "complete",
        "source_id": "SYNTHETIC",
        "exact_product_id": product_id,
        "archive_sha256": "synthetic",
        "file_count": len(manifest_files),
        "total_extracted_bytes": sum(item["size_bytes"] for item in manifest_files),
        "files": manifest_files,
    }, descriptions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--receipt-output", type=Path, required=True)
    parser.add_argument("--verified-at-utc", required=True)
    args = parser.parse_args()
    if not UTC_TIMESTAMP.fullmatch(args.verified_at_utc):
        raise SystemExit("verified timestamp must be RFC 3339 UTC")
    if args.output_root.exists() or args.receipt_output.exists():
        raise SystemExit("refusing existing synthetic output or receipt path")
    args.output_root.mkdir(parents=True)
    gdal.UseExceptions()
    contract = load("config/qa/optical-input-readiness-contract-full-cohort-001.json")
    before_manifest, before_descriptions = create_safe(args.output_root / "before", "S2X_BEFORE_SYNTHETIC.SAFE")
    after_manifest, after_descriptions = create_safe(args.output_root / "after", "S2X_AFTER_SYNTHETIC.SAFE")
    before_inventory = select_required_members(before_manifest, contract)
    after_inventory = select_required_members(after_manifest, contract)
    metadata = {
        "before": parse_l2a_scaling_metadata(metadata_xml()),
        "after": parse_l2a_scaling_metadata(metadata_xml()),
    }
    metadata_errors = {role: value["errors"] for role, value in metadata.items()}
    grid_errors = validate_pair_grids(before_descriptions, after_descriptions, contract)
    decision = decide_header_readiness(
        {"before": before_inventory["status"], "after": after_inventory["status"]},
        metadata_errors,
        grid_errors,
    )
    shifted = json.loads(json.dumps(after_descriptions))
    for role in RASTER_ROLES:
        shifted[role]["xmin"] += 10.0
        shifted[role]["xmax"] += 10.0
    shifted_errors = validate_pair_grids(before_descriptions, shifted, contract)
    install = arcpy.GetInstallInfo()
    script_ref = "scripts/validate_optical_input_readiness_arcgis_full_cohort_001.py"
    receipt = {
        "receipt_version": "1.0",
        "receipt_id": "NEPAL-S2-MATERIALIZED-INPUT-READINESS-SYNTHETIC-FULL-COHORT-001",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_synthetic_only_with_expected_misalignment_block" if decision["status"] == "pass_header_readability_only" and shifted_errors else "fail",
        "runtime": {
            "product": install.get("ProductName", "ArcGISPro"),
            "version": install.get("Version"),
            "license_level": install.get("LicenseLevel", arcpy.ProductInfo()),
            "gdal_version": gdal.VersionInfo(),
            "jp2_driver": "JP2OpenJPEG",
        },
        "bindings": {
            "contract_ref": "config/qa/optical-input-readiness-contract-full-cohort-001.json",
            "contract_sha256": digest("config/qa/optical-input-readiness-contract-full-cohort-001.json"),
            "core_ref": "scripts/optical_input_readiness_core_full_cohort_001.py",
            "core_sha256": digest("scripts/optical_input_readiness_core_full_cohort_001.py"),
            "adapter_ref": script_ref,
            "adapter_sha256": digest(script_ref),
        },
        "fixture": {
            "output_root": str(args.output_root.resolve()),
            "source_association": "synthetic_none",
            "before_inventory_status": before_inventory["status"],
            "after_inventory_status": after_inventory["status"],
            "jp2_raster_count": len(RASTER_ROLES) * 2,
            "wkid": 32645,
            "ten_metre_dimensions": [12, 12],
            "twenty_metre_dimensions": [6, 6],
            "quality_classification_dimensions": [2, 2],
            "quality_classification_band_count": 3,
            "quality_classification_cell_size_m": 60.0,
            "metadata_checks": {
                role: {
                    "processing_baseline": value["processing_baseline"],
                    "quantification_value": value["quantification_value"],
                    "used_band_offset_count": len({band: offset for band, offset in value["offsets_by_band"].items() if band in {"B02", "B03", "B04", "B08", "B11", "B12"}}),
                    "errors": value["errors"],
                }
                for role, value in metadata.items()
            },
            "header_descriptions": {
                "before": before_descriptions,
                "after": after_descriptions,
            },
        },
        "checks": {
            "aligned_pair": decision,
            "intentional_after_grid_shift": {"status": "block" if shifted_errors else "unexpected_pass", "errors": shifted_errors},
        },
        "retained_failures": [
            {
                "attempt": "scratch/arcgis-jp2-capability-001",
                "status": "fail",
                "method": "ArcGIS CopyRaster to JP2 with U16",
                "error": "No raster store is configurated.",
            },
            {
                "attempt": "scratch/arcgis-jp2-capability-002",
                "status": "fail",
                "method": "ArcGIS CopyRaster to JP2 with U8",
                "error": "No raster store is configurated.",
            },
            {
                "attempt": "scratch/optical-input-readiness-arcgis-007",
                "status": "fail",
                "method": "ArcGIS dataset-level Describe for a three-band JP2",
                "error": "ArcGIS exposed width, height, cell size, and pixel type only on the Band_1 through Band_3 child descriptions.",
            },
        ],
        "retained_prepublication_attempts": [
            {
                "attempt": "scratch/optical-input-readiness-arcgis-001",
                "status": "superseded_before_publication",
                "reason": "The first passing receipt summarized the JP2 fixture but did not retain the per-role ArcGIS header descriptions or parsed scaling fields.",
                "real_product_data_used": False,
            },
            {
                "attempt": "scratch/optical-input-readiness-arcgis-002",
                "status": "superseded_before_publication",
                "reason": "The bound production runner was hardened to retain metadata-parse and ArcGIS-header failures as block evidence rather than raising before the result could be recorded.",
                "real_product_data_used": False,
            },
            {
                "attempt": "scratch/optical-input-readiness-arcgis-003",
                "status": "superseded_before_publication",
                "reason": "The header validator was strengthened to require dimensions, cell sizes, and reported extents to reconcile for every JP2 before the final receipt was frozen.",
                "real_product_data_used": False,
            },
            {
                "attempt": "scratch/optical-input-readiness-arcgis-004",
                "status": "superseded_before_publication",
                "reason": "The ArcGIS run passed, but its chained invocation followed a failed portable fixture expectation and therefore was not accepted as the final control checkpoint.",
                "real_product_data_used": False,
            },
            {
                "attempt": "scratch/optical-input-readiness-arcgis-005",
                "status": "superseded_before_publication",
                "reason": "The production receipt activity fields were made explicit about attempted versus complete ArcGIS header opening before the final contract was frozen.",
                "real_product_data_used": False,
            },
        ],
        "retained_published_attempts": [
            {
                "attempt": "scratch/optical-input-readiness-arcgis-006",
                "published_commit": "df3e93aadef064129c928463cc1f5eec562e3950",
                "status": "superseded_after_publication",
                "reason": "Official Sentinel-2 documentation confirms that PB 05.12 MSK_CLASSI_B00.jp2 is a three-band 60 m Boolean mask; the published fixture incorrectly modeled it as one-band 20 m.",
                "real_product_data_used": False,
            },
        ],
        "assertions": {
            "synthetic_jp2_opened_by_arcgis": True,
            "aligned_pair_passed_header_readiness_only": decision["status"] == "pass_header_readability_only",
            "intentional_grid_shift_blocked": bool(shifted_errors),
            "external_custody_accessed": False,
            "real_materialization_receipt_used": False,
            "real_product_metadata_read": False,
            "real_product_pixels_examined": False,
            "pixel_usability_established": False,
            "baseline_established": False,
            "change_established": False,
            "scientific_admission_authorized": False,
        },
        "limitations": contract["limitations"],
    }
    write_new_json(args.receipt_output, receipt)
    print(json.dumps({"status": receipt["status"], "receipt": str(args.receipt_output)}, indent=2))
    if receipt["status"] == "fail":
        raise SystemExit(20)


if __name__ == "__main__":
    main()
