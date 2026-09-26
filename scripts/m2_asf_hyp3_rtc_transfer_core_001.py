"""Stream and verify one exact HyP3 RTC ZIP in disposable or non-Git custody.

The caller must first bind a SUCCEEDED job to the exact private download
descriptor, open that descriptor's HTTPS URL without redirects, and choose a
    safe staging/destination path under controlled non-Git custody. This module
    never contacts ASF, reads credentials, retries, or decodes raster values.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import BinaryIO

from m2_asf_hyp3_rtc_core_001 import ORDER, RouteStop
from m2_asf_hyp3_rtc_download_core_001 import MAX_ARCHIVE_BYTES
from m2_asf_hyp3_rtc_zip_core_001 import inspect_package_zip
from m2_transfer_core import TransferControlError, promote_atomic_no_replace


CHUNK_BYTES = 8 * 1024 * 1024


def stream_exact_zip_once(
    source: BinaryIO,
    staging_path: Path,
    *,
    source_id: str,
    expected_size_bytes: int,
    chunk_bytes: int = CHUNK_BYTES,
) -> dict:
    """Reserve new staging bytes, bound the stream, and check the ZIP container.

    A failed or interrupted staging file is intentionally retained for an
    append-only attempt receipt. No destination promotion occurs on failure.
    """
    if (
        source_id != ORDER[0]
        or type(expected_size_bytes) is not int
        or not 0 < expected_size_bytes <= MAX_ARCHIVE_BYTES
        or type(chunk_bytes) is not int
        or not 0 < chunk_bytes <= CHUNK_BYTES
        or staging_path.is_symlink()
    ):
        raise RouteStop("rtc_transfer_binding_invalid")
    digest = hashlib.sha256()
    size = 0
    try:
        with staging_path.open("xb") as target:
            while True:
                block = source.read(chunk_bytes)
                if not block:
                    break
                if not isinstance(block, bytes) or len(block) > chunk_bytes:
                    raise RouteStop("rtc_transfer_stream_invalid")
                size += len(block)
                if size > expected_size_bytes:
                    raise RouteStop("rtc_transfer_exceeds_descriptor_size")
                target.write(block)
                digest.update(block)
            target.flush()
            os.fsync(target.fileno())
    except FileExistsError:
        raise RouteStop("rtc_transfer_staging_collision") from None
    except OSError:
        raise RouteStop("rtc_transfer_stream_failed") from None
    if size != expected_size_bytes:
        raise RouteStop("rtc_transfer_size_mismatch")
    sha = digest.hexdigest()
    zip_screen = inspect_package_zip(
        source_id, staging_path,
        expected_size_bytes=expected_size_bytes,
        expected_sha256=sha,
    )
    return {
        "source_id": source_id,
        "status": "pass_staged_bytes_and_zip_only",
        "size_bytes": size,
        "sha256": sha,
        "zip_crc_verified": zip_screen["zip_crc_verified"],
        "member_file_count": zip_screen["member_file_count"],
        "provider_descriptor_bound_by_caller": False,
        "raster_pixel_values_decoded": False,
        "pixel_qa_pass": False,
    }


def promote_verified_zip_no_replace(
    staging_path: Path, destination_path: Path, staged: dict,
) -> dict:
    """Promote already checked bytes without replacing an existing product."""
    if (
        not isinstance(staged, dict)
        or staged.get("status") != "pass_staged_bytes_and_zip_only"
        or staged.get("source_id") != ORDER[0]
        or staged.get("zip_crc_verified") is not True
        or type(staged.get("size_bytes")) is not int
        or not isinstance(staged.get("sha256"), str)
        or staging_path.is_symlink()
        or destination_path.is_symlink()
    ):
        raise RouteStop("rtc_transfer_promotion_binding_invalid")
    # Reinspect immediately before promotion in case staged bytes changed.
    inspect_package_zip(
        ORDER[0], staging_path,
        expected_size_bytes=staged["size_bytes"],
        expected_sha256=staged["sha256"],
    )
    try:
        promoted = promote_atomic_no_replace(staging_path, destination_path)
    except (OSError, TransferControlError):
        raise RouteStop("rtc_transfer_promotion_failed") from None
    if promoted != {"size_bytes": staged["size_bytes"], "sha256": staged["sha256"]}:
        raise RouteStop("rtc_transfer_post_promotion_mismatch")
    return {
        "source_id": ORDER[0],
        "status": "pass_local_zip_promoted_no_replace",
        "archive_size_bytes": promoted["size_bytes"],
        "archive_sha256": promoted["sha256"],
        "raster_pixel_values_decoded": False,
        "pixel_qa_pass": False,
    }
