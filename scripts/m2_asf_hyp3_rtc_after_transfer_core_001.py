"""Single-stream, no-replace ZIP verification for exact M1-SRC-005."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import BinaryIO

from m2_asf_hyp3_rtc_core_001 import RouteStop
from m2_asf_hyp3_rtc_download_core_001 import MAX_ARCHIVE_BYTES
from m2_asf_hyp3_rtc_zip_core_001 import inspect_package_zip
from m2_transfer_core import TransferControlError, promote_atomic_no_replace


SOURCE_ID = "M1-SRC-005"
CHUNK_BYTES = 8 * 1024 * 1024


def stream_after_zip_once(
    source: BinaryIO, staging: Path, *, expected_size_bytes: int,
    chunk_bytes: int = CHUNK_BYTES,
) -> dict:
    """Exclusive staging, exact size/SHA, and CRC; retain failed partials."""
    if (
        type(expected_size_bytes) is not int or not 0 < expected_size_bytes <= MAX_ARCHIVE_BYTES
        or type(chunk_bytes) is not int or not 0 < chunk_bytes <= CHUNK_BYTES
        or staging.exists() or staging.is_symlink()
    ):
        raise RouteStop("after_transfer_binding_invalid")
    digest = hashlib.sha256()
    size = 0
    try:
        with staging.open("xb") as target:
            while True:
                block = source.read(chunk_bytes)
                if not block:
                    break
                if not isinstance(block, bytes) or len(block) > chunk_bytes:
                    raise RouteStop("after_transfer_stream_invalid")
                size += len(block)
                if size > expected_size_bytes:
                    raise RouteStop("after_transfer_exceeds_descriptor_size")
                target.write(block)
                digest.update(block)
            target.flush()
            os.fsync(target.fileno())
    except RouteStop:
        raise
    except Exception:
        raise RouteStop("after_transfer_stream_failed") from None
    if size != expected_size_bytes:
        raise RouteStop("after_transfer_size_mismatch")
    sha = digest.hexdigest()
    checked = inspect_package_zip(
        SOURCE_ID, staging, expected_size_bytes=size, expected_sha256=sha)
    if checked.get("zip_crc_verified") is not True:
        raise RouteStop("after_transfer_zip_not_verified")
    return {"source_id": SOURCE_ID, "status": "pass_staged_bytes_and_zip_only",
            "size_bytes": size, "sha256": sha, "zip_crc_verified": True,
            "member_file_count": checked["member_file_count"],
            "provider_job_identity_verified_by_caller": False,
            "raster_pixel_values_decoded": False}


def promote_after_zip_no_replace(staging: Path, destination: Path,
                                 staged: dict) -> dict:
    """Recheck exact staged bytes and publish by atomic no-replace link."""
    if (
        not isinstance(staged, dict)
        or staged.get("source_id") != SOURCE_ID
        or staged.get("status") != "pass_staged_bytes_and_zip_only"
        or staged.get("zip_crc_verified") is not True
        or type(staged.get("size_bytes")) is not int
        or not isinstance(staged.get("sha256"), str)
        or staging.is_symlink() or destination.is_symlink() or destination.exists()
    ):
        raise RouteStop("after_transfer_promotion_binding_invalid")
    inspect_package_zip(
        SOURCE_ID, staging,
        expected_size_bytes=staged["size_bytes"], expected_sha256=staged["sha256"])
    try:
        promoted = promote_atomic_no_replace(staging, destination)
    except (OSError, TransferControlError):
        raise RouteStop("after_transfer_promotion_failed") from None
    if promoted != {"size_bytes": staged["size_bytes"], "sha256": staged["sha256"]}:
        raise RouteStop("after_transfer_post_promotion_mismatch")
    return {"source_id": SOURCE_ID, "status": "pass_local_zip_promoted_no_replace",
            "archive_size_bytes": promoted["size_bytes"],
            "archive_sha256": promoted["sha256"],
            "raster_pixel_values_decoded": False, "pixel_qa_pass": False}
