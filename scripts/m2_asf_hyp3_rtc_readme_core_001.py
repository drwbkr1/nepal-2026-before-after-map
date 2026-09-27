"""Bounded, read-only provenance screen for a verified HyP3 RTC ZIP.

The caller must first establish the exact job, transfer, archive hash, and
non-Git custody identity. This module reads only the product README member;
it never extracts files, opens GeoTIFFs, or treats text matches as pixel QA.
"""

from __future__ import annotations

import hashlib
import stat
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from m2_asf_hyp3_rtc_core_001 import ORDER, RouteStop, load_approved_jobs
from m2_asf_hyp3_rtc_package_core_001 import inspect_member_names


MAX_README_BYTES = 2 * 1024 * 1024


def inspect_product_readme(
    source_id: str,
    archive_path: Path,
    expected_product_filename: str,
) -> dict:
    """Report exact-source text evidence without returning README content."""
    if source_id not in ORDER or not isinstance(expected_product_filename, str):
        raise RouteStop("rtc_readme_input_invalid")
    approved = load_approved_jobs()
    source = next(job for job in approved if job["source_id"] == source_id)
    granule = source["job_parameters"]["granules"][0]
    try:
        if archive_path.is_symlink() or not archive_path.is_file():
            raise RouteStop("rtc_readme_archive_path_invalid")
        if getattr(archive_path.stat(), "st_file_attributes", 0) & getattr(
            stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0
        ):
            raise RouteStop("rtc_readme_archive_path_invalid")
        with ZipFile(archive_path) as archive:
            names = [info.orig_filename for info in archive.infolist()]
            package = inspect_member_names(source_id, names)
            product_base = package["product_base_name"]
            if expected_product_filename != f"{product_base}.zip":
                raise RouteStop("rtc_readme_product_identity_mismatch")
            member = f"{product_base}/{product_base}.README.md.txt"
            info = archive.getinfo(member)
            if info.file_size <= 0 or info.file_size > MAX_README_BYTES:
                raise RouteStop("rtc_readme_size_invalid")
            with archive.open(info) as stream:
                content = stream.read(MAX_README_BYTES + 1)
            if len(content) != info.file_size:
                raise RouteStop("rtc_readme_size_invalid")
            text = content.decode("utf-8-sig")
    except RouteStop:
        raise
    except (BadZipFile, KeyError, OSError, RuntimeError, UnicodeError, ValueError):
        raise RouteStop("rtc_readme_unreadable") from None

    granule_present = granule in text
    product_present = product_base in text
    return {
        "source_id": source_id,
        "status": (
            "pass_readme_exact_source_text_only"
            if granule_present and product_present
            else "defer_readme_source_text_review"
        ),
        "product_filename": expected_product_filename,
        "readme_member_size_bytes": len(content),
        "readme_sha256": hashlib.sha256(content).hexdigest(),
        "exact_source_granule_text_present": granule_present,
        "exact_product_base_text_present": product_present,
        "readme_content_recorded": False,
        "archive_hash_verified_by_this_check": False,
        "other_product_metadata_or_rights_reviewed": False,
        "geotiff_headers_or_pixels_read": False,
        "aoi_or_map_fitness_verified": False,
    }
