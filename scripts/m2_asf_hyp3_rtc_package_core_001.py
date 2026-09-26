"""No-pixel structural screen for an exact ASF HyP3 GAMMA RTC package.

Member names and the documented naming convention are only an early screen.
They do not prove ZIP integrity, source metadata, georeferencing, mask codes,
usable pixels, or scientific fitness.
"""

from __future__ import annotations

import re

from m2_asf_hyp3_rtc_core_001 import ORDER, RouteStop, load_approved_jobs


PRODUCT_ROOT = re.compile(r"S1D_IW_(\d{8}T\d{6})_DV([PRO])_RTC10_G_gpuned_[0-9A-F]{4}\Z")
REQUIRED_SUFFIXES = (
    "_VV.tif", "_VH.tif", "_ls_map.tif", "_dem.tif", "_inc_map.tif", "_area.tif",
    "_VV.tif.xml", "_VH.tif.xml", "_ls_map.tif.xml", "_dem.tif.xml",
    "_inc_map.tif.xml", "_area.tif.xml",
    ".README.md.txt", ".log", "_shape.shp", "_shape.shx", "_shape.dbf", "_shape.prj",
)


def inspect_member_names(source_id: str, members: list[str]) -> dict:
    """Reject unsafe or mismatched names before any archive extraction."""
    if source_id not in ORDER or not isinstance(members, list) or not members:
        raise RouteStop("rtc_package_members_invalid")
    approved = load_approved_jobs()
    source = next(job for job in approved if job["source_id"] == source_id)
    expected_start = source["job_parameters"]["granules"][0].split("_")[4]
    files: set[str] = set()
    roots: set[str] = set()
    for member in members:
        if not isinstance(member, str) or not member or "\\" in member or "\x00" in member:
            raise RouteStop("rtc_package_path_invalid")
        if member.endswith("/"):
            parts = member[:-1].split("/")
            if len(parts) != 1 or not parts[0] or parts[0] in {".", ".."}:
                raise RouteStop("rtc_package_path_invalid")
            roots.add(parts[0])
            continue
        parts = member.split("/")
        if len(parts) != 2 or any(part in {"", ".", ".."} for part in parts):
            raise RouteStop("rtc_package_path_invalid")
        root, filename = parts
        if re.fullmatch(r"[A-Za-z0-9._-]+", filename) is None:
            raise RouteStop("rtc_package_path_invalid")
        if filename.casefold() in files:
            raise RouteStop("rtc_package_member_duplicate")
        files.add(filename.casefold())
        roots.add(root)
    if len(roots) != 1:
        raise RouteStop("rtc_package_root_ambiguous")
    product_root = next(iter(roots))
    match = PRODUCT_ROOT.fullmatch(product_root)
    if match is None or match.group(1) != expected_start:
        raise RouteStop("rtc_package_product_identity_mismatch")
    required = {f"{product_root}{suffix}".casefold() for suffix in REQUIRED_SUFFIXES}
    if not required.issubset(files):
        raise RouteStop("rtc_package_required_member_missing")
    if f"{product_root}_rgb.tif".casefold() in files:
        raise RouteStop("rtc_package_unapproved_rgb_tif")
    return {
        "source_id": source_id,
        "status": "pass_documented_member_names_only",
        "product_base_name": product_root,
        "provider_orbit_type_code": match.group(2),
        "member_file_count": len(files),
        "source_granule_verified_in_readme": False,
        "zip_integrity_verified": False,
        "geotiff_headers_or_pixels_read": False,
        "provider_mask_codes_assessed": False,
        "arcgis_map_ready": False,
    }
