"""Read-only ZIP integrity check for an exact approved HyP3 RTC product.

This checks local bytes and documented package shape without extracting files.
The caller must separately bind the HTTP transfer, job, custody path, README
provenance, and later raster/pixel QA. Synthetic tests use disposable ZIPs.
"""

from __future__ import annotations

import hashlib
import re
import stat
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from m2_asf_hyp3_rtc_core_001 import RouteStop
from m2_asf_hyp3_rtc_package_core_001 import REQUIRED_SUFFIXES, inspect_member_names


CHUNK_BYTES = 8 * 1024 * 1024
MAX_MEMBERS = 500
MAX_MEMBER_BYTES = 20 * 1024**3
MAX_TOTAL_BYTES = 100 * 1024**3
MAX_EXPANSION_RATIO = 200
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


def inspect_package_zip(
    source_id: str,
    archive_path: Path,
    *,
    expected_size_bytes: int,
    expected_sha256: str,
) -> dict:
    """Verify a prior transfer's exact local bytes and every ZIP member CRC."""
    if type(expected_size_bytes) is not int or expected_size_bytes <= 0 or not isinstance(expected_sha256, str) or not HEX64.fullmatch(expected_sha256):
        raise RouteStop("rtc_zip_transfer_binding_invalid")
    try:
        if archive_path.is_symlink() or not archive_path.is_file():
            raise RouteStop("rtc_zip_path_invalid")
        before = archive_path.stat()
        if getattr(before, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
            raise RouteStop("rtc_zip_path_invalid")
        if before.st_size != expected_size_bytes:
            raise RouteStop("rtc_zip_size_mismatch")
        digest = hashlib.sha256()
        with archive_path.open("rb") as stream:
            for block in iter(lambda: stream.read(CHUNK_BYTES), b""):
                digest.update(block)
        if digest.hexdigest() != expected_sha256:
            raise RouteStop("rtc_zip_sha256_mismatch")
        with ZipFile(archive_path) as archive:
            infos = archive.infolist()
            if not infos or len(infos) > MAX_MEMBERS:
                raise RouteStop("rtc_zip_member_count_invalid")
            names = [info.orig_filename for info in infos]
            name_result = inspect_member_names(source_id, names)
            required = {f"{name_result['product_base_name']}{suffix}".casefold() for suffix in REQUIRED_SUFFIXES}
            total = 0
            for info in infos:
                if info.flag_bits & 1:
                    raise RouteStop("rtc_zip_encrypted_member")
                mode = (info.external_attr >> 16) & 0o170000
                if mode not in (0, stat.S_IFREG, stat.S_IFDIR):
                    raise RouteStop("rtc_zip_special_member")
                if info.is_dir():
                    continue
                if info.file_size <= 0 and info.orig_filename.rsplit("/", 1)[-1].casefold() in required:
                    raise RouteStop("rtc_zip_required_member_empty")
                if info.file_size > MAX_MEMBER_BYTES:
                    raise RouteStop("rtc_zip_member_size_limit")
                total += info.file_size
                if total > MAX_TOTAL_BYTES:
                    raise RouteStop("rtc_zip_total_size_limit")
            if total > max(expected_size_bytes * MAX_EXPANSION_RATIO, 1024**3):
                raise RouteStop("rtc_zip_expansion_limit")
            if archive.testzip() is not None:
                raise RouteStop("rtc_zip_crc_failed")
        after = archive_path.stat()
        if (after.st_size, after.st_mtime_ns, after.st_ino) != (before.st_size, before.st_mtime_ns, before.st_ino):
            raise RouteStop("rtc_zip_changed_during_inspection")
    except RouteStop:
        raise
    except (BadZipFile, EOFError, OSError, RuntimeError, ValueError):
        raise RouteStop("rtc_zip_unreadable") from None
    return {
        "source_id": source_id,
        "status": "pass_local_zip_identity_structure_crc_only",
        "archive_size_bytes": expected_size_bytes,
        "archive_sha256": expected_sha256,
        "member_file_count": name_result["member_file_count"],
        "zip_crc_verified": True,
        "provider_transfer_or_job_identity_verified": False,
        "source_granule_verified_in_readme": False,
        "geotiff_headers_or_pixels_read": False,
        "arcgis_map_ready": False,
    }
