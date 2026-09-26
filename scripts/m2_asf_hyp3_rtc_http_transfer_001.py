"""One-attempt transport for the approved first HyP3 RTC product.

The caller owns the append-only attempt receipt and secret-safe credential
handoff. This module never prints a token, provider URL, or response body.
Only the exact successful M1-SRC-002 job can reach a ZIP transfer.
"""

from __future__ import annotations

import http.client
import json
import shutil
import stat
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit
from uuid import UUID

from m2_asf_hyp3_account_probe_001 import HOST, MAX_SECRET_BYTES
from m2_asf_hyp3_rtc_core_001 import ORDER, RouteStop
from m2_asf_hyp3_rtc_download_core_001 import (
    CLOUDFRONT_HOST, MAX_ARCHIVE_BYTES, S3_HOST, inspect_exact_zip_descriptor,
)
from m2_asf_hyp3_rtc_transfer_core_001 import (
    promote_verified_zip_no_replace, stream_exact_zip_once,
)
from m2_transfer_core import TransferControlError, require_safe_child


MAX_STATUS_BYTES = 262144
MIN_FREE_MARGIN_BYTES = 1024**3


def _canonical_job_id(value: object) -> bool:
    try:
        return isinstance(value, str) and str(UUID(value)) == value
    except ValueError:
        return False


def fetch_first_descriptor_once(
    token: str, submission: dict,
    connection_factory: Callable = http.client.HTTPSConnection,
) -> tuple[dict, dict]:
    """Make one authenticated GET, returning private and URL-free views."""
    job_id = submission.get("job_id") if isinstance(submission, dict) else None
    if (
        not isinstance(token, str) or not token or len(token) > MAX_SECRET_BYTES
        or not all(char.isalnum() or char in "._-" for char in token)
        or not _canonical_job_id(job_id)
    ):
        raise RouteStop("rtc_acquire_status_input_invalid")
    connection = None
    try:
        connection = connection_factory(HOST, timeout=30)
        connection.request(
            "GET", f"/jobs/{job_id}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )
        response = connection.getresponse()
        if response.status != 200:
            raise RouteStop("rtc_acquire_status_response_invalid")
        raw = response.read(MAX_STATUS_BYTES + 1)
        if len(raw) > MAX_STATUS_BYTES:
            raise RouteStop("rtc_acquire_status_response_too_large")
        reply = json.loads(raw)
        return inspect_exact_zip_descriptor(reply, submission, ORDER[0])
    except RouteStop:
        raise
    except Exception:
        raise RouteStop("rtc_acquire_status_request_failed") from None
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass


def transfer_first_zip_once(
    private: dict, submission: dict, controlled_root: Path,
    staging_path: Path, destination_path: Path,
    connection_factory: Callable = http.client.HTTPSConnection,
) -> dict:
    """Stream one exact HTTPS ZIP to non-Git custody with no replacement.

    A failed stream leaves its partial path untouched. There is no redirect,
    range request, automatic retry, second URL, or destination overwrite.
    """
    if not isinstance(private, dict) or not isinstance(submission, dict):
        raise RouteStop("rtc_acquire_descriptor_invalid")
    job_id = submission.get("job_id")
    filename = private.get("filename")
    size = private.get("size_bytes")
    url = private.get("url")
    if (
        private.get("source_id") != ORDER[0]
        or not _canonical_job_id(job_id)
        or private.get("job_id") != job_id
        or not isinstance(filename, str) or not filename.endswith(".zip")
        or type(size) is not int or not 0 < size <= MAX_ARCHIVE_BYTES
        or not isinstance(url, str) or len(url) > 2048
        or destination_path.name != filename
    ):
        raise RouteStop("rtc_acquire_descriptor_invalid")
    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        port = parsed.port
    except ValueError:
        raise RouteStop("rtc_acquire_url_invalid") from None
    if (
        parsed.scheme != "https" or not host or port not in (None, 443)
        or parsed.username is not None or parsed.password is not None
        or parsed.query or parsed.fragment
        or not (S3_HOST.fullmatch(host) or CLOUDFRONT_HOST.fullmatch(host))
        or parsed.path != f"/{job_id}/{filename}"
    ):
        raise RouteStop("rtc_acquire_url_invalid")
    try:
        if (
            not controlled_root.is_dir() or controlled_root.is_symlink()
            or bool(getattr(controlled_root.stat(), "st_file_attributes", 0)
                    & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
        ):
            raise RouteStop("rtc_acquire_custody_root_invalid")
        require_safe_child(controlled_root, staging_path)
        require_safe_child(controlled_root, destination_path)
        if (
            staging_path.parent == destination_path.parent
            or staging_path.exists() or destination_path.exists()
            or staging_path.is_symlink() or destination_path.is_symlink()
            or not staging_path.parent.is_dir() or not destination_path.parent.is_dir()
            or shutil.disk_usage(controlled_root).free < size + MIN_FREE_MARGIN_BYTES
        ):
            raise RouteStop("rtc_acquire_custody_preflight_failed")
    except RouteStop:
        raise
    except (OSError, TransferControlError):
        raise RouteStop("rtc_acquire_custody_preflight_failed") from None
    connection = None
    try:
        connection = connection_factory(host, timeout=120)
        connection.request("GET", parsed.path, headers={"Accept": "application/zip"})
        response = connection.getresponse()
        if response.status != 200:
            raise RouteStop("rtc_acquire_zip_response_invalid")
        length = response.getheader("Content-Length")
        encoding = response.getheader("Content-Encoding")
        content_range = response.getheader("Content-Range")
        if length != str(size) or encoding not in (None, "identity") or content_range is not None:
            raise RouteStop("rtc_acquire_zip_headers_invalid")
        staged = stream_exact_zip_once(
            response, staging_path, source_id=ORDER[0], expected_size_bytes=size,
        )
        promoted = promote_verified_zip_no_replace(staging_path, destination_path, staged)
        return {
            **promoted,
            "job_id": job_id,
            "product_filename": filename,
            "provider_url_recorded": False,
            "credentials_recorded": False,
        }
    except RouteStop:
        raise
    except Exception:
        raise RouteStop("rtc_acquire_zip_request_failed") from None
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass
