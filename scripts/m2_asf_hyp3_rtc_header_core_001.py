"""Pure header-only screen for the approved HyP3 RTC GeoTIFF set.

The caller must separately establish archive integrity and map each descriptor
to its exact package member. No raster is opened or pixel value inspected here.
"""

from __future__ import annotations

import hashlib
import math

from m2_asf_hyp3_rtc_core_001 import ORDER, ROOT, RouteStop, load_approved_jobs
from pixel_qa_core import evaluate_grid_pair, load_contract


CONTRACT_REF = "config/qa/pixel-readiness-contract.json"
CONTRACT_SHA256 = "5a66ae11288813868f362c342027ce0e4850d435dfbb2cfec3f5098b17d123e2"
RASTERS = {
    "vv": "Float32",
    "vh": "Float32",
    "ls_map": "Byte",
    "dem": "Int16",
    "inc_map": "Float32",
    "area": "Float32",
}
HEADER_KEYS = {"width", "height", "band_count", "data_type", "grid"}
GRID_KEYS = {
    "wkid", "cell_size_x", "cell_size_y", "origin_x", "origin_y",
    "xmin", "ymin", "xmax", "ymax", "rotation_degrees",
}


def _contract() -> dict:
    path = ROOT / CONTRACT_REF
    try:
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != CONTRACT_SHA256:
            raise RouteStop("rtc_header_contract_identity_mismatch")
        return load_contract(path)
    except (OSError, ValueError) as exc:
        if isinstance(exc, RouteStop):
            raise
        raise RouteStop("rtc_header_contract_unreadable") from None


def inspect_raster_headers(source_id: str, headers: dict) -> dict:
    """Check exact six-raster header shape and common projected support only."""
    if source_id not in ORDER or source_id not in {job["source_id"] for job in load_approved_jobs()}:
        raise RouteStop("rtc_header_source_invalid")
    if not isinstance(headers, dict) or set(headers) != set(RASTERS):
        raise RouteStop("rtc_header_raster_set_invalid")
    contract = _contract()
    tolerance = contract["grid_compatibility"]["cell_size_absolute_tolerance_m"]
    reference = None
    for role, expected_type in RASTERS.items():
        header = headers[role]
        if not isinstance(header, dict) or set(header) != HEADER_KEYS:
            raise RouteStop("rtc_header_shape_invalid")
        if any(type(header[key]) is not int or header[key] <= 0 for key in ("width", "height", "band_count")):
            raise RouteStop("rtc_header_dimensions_invalid")
        if header["band_count"] != 1 or header["data_type"] != expected_type:
            raise RouteStop("rtc_header_band_or_type_invalid")
        grid = header["grid"]
        if not isinstance(grid, dict) or set(grid) != GRID_KEYS:
            raise RouteStop("rtc_header_grid_shape_invalid")
        if type(grid["wkid"]) is not int or any(
            type(grid[key]) not in (int, float) or not math.isfinite(grid[key])
            for key in GRID_KEYS - {"wkid"}
        ):
            raise RouteStop("rtc_header_grid_value_invalid")
        if any(abs(grid[f"cell_size_{axis}"] - contract["grid_compatibility"]["radar_candidate_cell_size_m"]) > tolerance for axis in ("x", "y")):
            raise RouteStop("rtc_header_spacing_invalid")
        if evaluate_grid_pair(grid, grid, contract)["status"] != "pass_qa_only":
            raise RouteStop("rtc_header_projected_grid_invalid")
        if (
            abs(grid["origin_x"] - grid["xmin"]) > tolerance
            or abs(grid["origin_y"] - grid["ymax"]) > tolerance
            or abs(grid["xmax"] - grid["xmin"] - header["width"] * grid["cell_size_x"]) > tolerance
            or abs(grid["ymax"] - grid["ymin"] - header["height"] * grid["cell_size_y"]) > tolerance
        ):
            raise RouteStop("rtc_header_extent_dimensions_inconsistent")
        if reference is None:
            reference = header
        else:
            if header["width"] != reference["width"] or header["height"] != reference["height"]:
                raise RouteStop("rtc_header_layer_dimensions_mismatch")
            if any(abs(grid[key] - reference["grid"][key]) > tolerance for key in GRID_KEYS - {"wkid"}) or grid["wkid"] != reference["grid"]["wkid"]:
                raise RouteStop("rtc_header_layer_grid_mismatch")
    return {
        "source_id": source_id,
        "status": "pass_synthetic_header_grid_only",
        "expected_raster_count": len(RASTERS),
        "required_wkid": contract["grid_compatibility"]["required_wkid"],
        "expected_cell_size_m": contract["grid_compatibility"]["radar_candidate_cell_size_m"],
        "archive_integrity_verified": False,
        "actual_headers_opened": False,
        "source_identity_from_headers_verified": False,
        "nodata_or_mask_codes_assessed": False,
        "pixels_or_aoi_coverage_assessed": False,
        "arcgis_map_ready": False,
    }
