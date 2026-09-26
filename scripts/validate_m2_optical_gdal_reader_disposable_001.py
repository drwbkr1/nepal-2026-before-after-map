#!/usr/bin/env python3
"""Source-free GDAL reader feasibility for the frozen optical header contract."""

from __future__ import annotations

import copy
import gc
import json
import tempfile
from pathlib import Path

import numpy as np
from osgeo import gdal, osr  # type: ignore[import-not-found]

from optical_input_readiness_core import RASTER_ROLES, decide_header_readiness, validate_pair_grids


ROOT = Path(__file__).resolve().parents[1]
HEADER_CONTRACT = ROOT / "config/qa/optical-input-readiness-contract.json"
XMIN, YMAX, SPAN = 273300.0, 3070380.0, 1200.0
TEN_METRE = {"B02", "B03", "B04", "B08"}
TWENTY_METRE = {"B11", "B12", "SCL"}


def generated_role(role: str) -> tuple[int, int, int, int, np.dtype, list[np.ndarray]]:
    if role in TEN_METRE:
        cell, count, dtype, bands = 10, 120, gdal.GDT_UInt16, 1
    elif role in TWENTY_METRE:
        cell, count, dtype, bands = 20, 60, gdal.GDT_Byte if role == "SCL" else gdal.GDT_UInt16, 1
    elif role == "quality_classification":
        cell, count, dtype, bands = 60, 20, gdal.GDT_Byte, 3
    else:
        raise ValueError("unknown synthetic optical role")
    value = 4 if role == "SCL" else 100 if role != "quality_classification" else 0
    array_type = np.uint8 if dtype == gdal.GDT_Byte else np.uint16
    arrays = [np.full((count, count), value, dtype=array_type) for _ in range(bands)]
    if role == "quality_classification":
        arrays[0][0, 0] = 1
    return cell, count, count, bands, array_type, arrays


def make_jp2(path: Path, role: str) -> None:
    cell, width, height, bands, _, arrays = generated_role(role)
    dtype = gdal.GDT_Byte if role in {"SCL", "quality_classification"} else gdal.GDT_UInt16
    temporary = path.with_suffix(".source.tif")
    source = gdal.GetDriverByName("GTiff").Create(str(temporary), width, height, bands, dtype)
    if source is None:
        raise RuntimeError("synthetic_geotiff_create_failed")
    source.SetGeoTransform((XMIN, float(cell), 0.0, YMAX, 0.0, -float(cell)))
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(32645)
    source.SetProjection(srs.ExportToWkt())
    for index, array in enumerate(arrays, start=1):
        source.GetRasterBand(index).WriteArray(array)
    source.Close()
    opened = gdal.OpenEx(str(temporary), gdal.OF_RASTER | gdal.OF_READONLY)
    copy_ds = gdal.GetDriverByName("JP2OpenJPEG").CreateCopy(
        str(path), opened, strict=1, options=["REVERSIBLE=YES", "QUALITY=100", "YCC=NO"]
    )
    if copy_ds is None:
        opened.Close()
        raise RuntimeError("synthetic_jp2_create_failed")
    if any(not np.array_equal(copy_ds.GetRasterBand(i).ReadAsArray(), array)
           for i, array in enumerate(arrays, start=1)):
        copy_ds.Close()
        opened.Close()
        raise RuntimeError("synthetic_jp2_fixture_not_lossless")
    copy_ds.Close()
    opened.Close()


def describe_jp2(path: Path) -> dict[str, object]:
    dataset = gdal.OpenEx(str(path), gdal.OF_RASTER | gdal.OF_READONLY)
    if dataset is None:
        raise RuntimeError("synthetic_jp2_open_failed")
    try:
        reader_driver = dataset.GetDriver().ShortName
        if reader_driver not in {"JP2OpenJPEG", "JP2KAK", "JP2ECW"}:
            raise RuntimeError("synthetic_jp2_reader_driver_unexpected")
        transform = dataset.GetGeoTransform(can_return_null=True)
        if transform is None or transform[2] != 0 or transform[4] != 0 or transform[1] <= 0 or transform[5] >= 0:
            raise RuntimeError("synthetic_jp2_grid_invalid")
        srs = dataset.GetSpatialRef()
        if srs is None:
            raise RuntimeError("synthetic_jp2_crs_missing")
        expected = osr.SpatialReference()
        expected.ImportFromEPSG(32645)
        if not srs.IsSame(expected):
            raise RuntimeError("synthetic_jp2_crs_not_equivalent_to_epsg32645")
        types = {gdal.GDT_Byte: "U8", gdal.GDT_UInt16: "U16"}
        band_types = [types.get(dataset.GetRasterBand(i).DataType) for i in range(1, dataset.RasterCount + 1)]
        if any(value is None for value in band_types) or len(set(band_types)) != 1:
            raise RuntimeError("synthetic_jp2_pixel_type_invalid")
        width, height = dataset.RasterXSize, dataset.RasterYSize
        cell_width, cell_height = float(transform[1]), -float(transform[5])
        result: dict[str, object] = {
            "format": "JP2", "reader_driver": reader_driver,
            "wkid": 32645, "crs_equivalence_verified": True,
            "embedded_epsg_authority_present": srs.GetAuthorityCode(None) is not None,
            "band_count": dataset.RasterCount,
            "width": width, "height": height, "cell_width": cell_width,
            "cell_height": cell_height, "pixel_type": band_types[0],
            "xmin": float(transform[0]), "ymax": float(transform[3]),
            "xmax": float(transform[0]) + width * cell_width,
            "ymin": float(transform[3]) - height * cell_height,
        }
        if dataset.RasterCount == 3:
            result["band_details"] = [
                {"name": f"Band_{i}", "width": width, "height": height,
                 "cell_width": cell_width, "cell_height": cell_height, "pixel_type": band_types[i - 1]}
                for i in range(1, 4)
            ]
        return result
    finally:
        dataset.Close()


def check_quality_resampling(path: Path) -> bool:
    source = gdal.OpenEx(str(path), gdal.OF_RASTER | gdal.OF_READONLY)
    if source is None:
        raise RuntimeError("synthetic_quality_source_open_failed")
    alternative = gdal.OpenEx(str(path), gdal.OF_RASTER | gdal.OF_READONLY, allowed_drivers=["JP2OpenJPEG"])
    expected_source = np.zeros((3, 20, 20), dtype=np.uint8)
    expected_source[0, 0, 0] = 1
    if alternative is None:
        source.Close()
        raise RuntimeError("synthetic_quality_openjpeg_reader_missing")
    alternative_equal = bool(np.array_equal(alternative.ReadAsArray(), expected_source))
    alternative.Close()
    if not alternative_equal or not np.array_equal(source.ReadAsArray(), expected_source):
        source.Close()
        raise RuntimeError("synthetic_quality_jp2_decoder_changed_mask")
    target = None
    try:
        target = gdal.Warp(
            "", source, format="MEM", outputBounds=(XMIN, YMAX - SPAN, XMIN + SPAN, YMAX),
            xRes=20.0, yRes=20.0, resampleAlg="near",
        )
        if target is None or target.RasterCount != 3 or (target.RasterXSize, target.RasterYSize) != (60, 60):
            raise RuntimeError("synthetic_quality_target_grid_invalid")
        array = target.ReadAsArray()
        expected = np.zeros((3, 60, 60), dtype=np.uint8)
        expected[0, :3, :3] = 1
        return bool(np.array_equal(array, expected))
    finally:
        if target is not None:
            target.Close()
        source.Close()


def main() -> int:
    gdal.UseExceptions()
    contract = json.loads(HEADER_CONTRACT.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="nepal-optical-gdal-disposable-") as folder:
        root = Path(folder)
        descriptions: dict[str, dict[str, object]] = {}
        for role in sorted(RASTER_ROLES):
            path = root / f"{role}.jp2"
            make_jp2(path, role)
            descriptions[role] = describe_jp2(path)
        pair_errors = validate_pair_grids(descriptions, descriptions, contract)
        decision = decide_header_readiness(
            {"M2-OPT-001": "pass_inventory_only", "M2-OPT-002": "pass_inventory_only"},
            {"M2-OPT-001": [], "M2-OPT-002": []}, pair_errors,
        )
        shifted = copy.deepcopy(descriptions)
        shifted["B11"]["xmin"] = float(shifted["B11"]["xmin"]) + 20.0
        shifted["B11"]["xmax"] = float(shifted["B11"]["xmax"]) + 20.0
        shifted_errors = validate_pair_grids(descriptions, shifted, contract)
        mask_equal = check_quality_resampling(root / "quality_classification.jp2")
        reader_drivers = sorted({str(item["reader_driver"]) for item in descriptions.values()})
        all_crs_equivalent = all(item["crs_equivalence_verified"] is True for item in descriptions.values())
        all_embedded_codes_present = all(item["embedded_epsg_authority_present"] is True for item in descriptions.values())
        gc.collect()
    if decision["status"] != "pass_header_readability_only" or not shifted_errors or not mask_equal or not all_crs_equivalent:
        print(json.dumps({
            "status": "synthetic_gdal_reader_frozen_predicate_mismatch",
            "header_status": decision["status"], "header_errors": pair_errors[:8],
            "shifted_error_count": len(shifted_errors), "quality_mask_exact": mask_equal,
            "crs_equivalent": all_crs_equivalent,
        }))
        return 20
    print(json.dumps({
        "status": "pass_disposable_gdal_optical_reader_feasibility",
        "gdal_version": gdal.VersionInfo("--version"),
        "generated_roles": len(RASTER_ROLES),
        "reader_drivers": reader_drivers,
        "all_crs_equivalent_to_epsg32645": all_crs_equivalent,
        "all_embedded_epsg_authority_codes_present": all_embedded_codes_present,
        "frozen_header_pass_on_matching_synthetic_pair": True,
        "frozen_header_block_on_shifted_pair": True,
        "quality_mask_nearest_neighbor_exact": True,
        "arcpy_imported": False,
        "real_source_or_external_custody_accessed": False,
        "real_product_pixels_examined": False,
        "new_real_attempt_started": False,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
