"""Pure exact M1-SRC-005 job and one-ZIP descriptor guards.

No network or filesystem mutation. A successful provider status remains only
product availability, not verified bytes, rights, raster QA, or map fitness.
"""

from __future__ import annotations

import hashlib
from urllib.parse import urlsplit
from uuid import UUID

from m2_asf_hyp3_rtc_core_001 import RouteStop, load_approved_jobs, one_job_payload
from m2_asf_hyp3_rtc_download_core_001 import (
    CLOUDFRONT_HOST, MAX_ARCHIVE_BYTES, S3_HOST,
)
from m2_asf_hyp3_rtc_job_status_core_001 import inspect_exact_job_status
from m2_asf_hyp3_rtc_package_core_001 import PRODUCT_ROOT


SOURCE_ID = "M1-SRC-005"


def _canonical_uuid(value: object) -> bool:
    try:
        return isinstance(value, str) and str(UUID(value)) == value
    except ValueError:
        return False


def submission_view(terminal: dict) -> dict:
    """Join a sanitized terminal receipt to the immutable approved job."""
    if (
        not isinstance(terminal, dict)
        or terminal.get("status") != "submitted_product_unverified"
        or terminal.get("source_id") != SOURCE_ID
        or not _canonical_uuid(terminal.get("job_id"))
        or type(terminal.get("credit_cost")) not in (int, float)
        or not 0 <= terminal["credit_cost"] <= 60
        or terminal.get("credentials_recorded") is not False
        or terminal.get("product_bytes_verified") is not False
        or terminal.get("pixel_qa_pass") is not False
    ):
        raise RouteStop("after_submission_receipt_invalid")
    expected = one_job_payload(load_approved_jobs(), SOURCE_ID)["jobs"][0]
    return {**expected, "job_id": terminal["job_id"], "credit_cost": terminal["credit_cost"]}


def inspect_after_zip_descriptor(reply: dict, terminal: dict) -> tuple[dict, dict]:
    """Require exact succeeded job and one safe product URL; omit URL publicly."""
    submission = submission_view(terminal)
    status = inspect_exact_job_status(reply, submission, SOURCE_ID)
    if status["disposition"] != "service_succeeded_product_unverified":
        raise RouteStop("after_job_not_succeeded")
    files = reply.get("files")
    if not isinstance(files, list) or len(files) != 1 or not isinstance(files[0], dict):
        raise RouteStop("after_zip_file_count_invalid")
    item = files[0]
    filename = item.get("filename")
    if not isinstance(filename, str) or not filename.endswith(".zip"):
        raise RouteStop("after_zip_filename_invalid")
    product = filename[:-4]
    match = PRODUCT_ROOT.fullmatch(product)
    start = submission["job_parameters"]["granules"][0].split("_")[4]
    if match is None or match.group(1) != start:
        raise RouteStop("after_zip_product_identity_mismatch")
    size = item.get("size")
    if type(size) is not int or not 0 < size <= MAX_ARCHIVE_BYTES:
        raise RouteStop("after_zip_size_invalid")
    url = item.get("url")
    if not isinstance(url, str) or len(url) > 2048:
        raise RouteStop("after_zip_url_invalid")
    try:
        parsed = urlsplit(url)
        host, port = parsed.hostname, parsed.port
    except ValueError:
        raise RouteStop("after_zip_url_invalid") from None
    if (
        parsed.scheme != "https" or not host or port not in (None, 443)
        or parsed.username is not None or parsed.password is not None
        or parsed.query or parsed.fragment
        or not (S3_HOST.fullmatch(host) or CLOUDFRONT_HOST.fullmatch(host))
        or parsed.path != f"/{submission['job_id']}/{filename}"
    ):
        raise RouteStop("after_zip_url_invalid")
    private = {"source_id": SOURCE_ID, "job_id": submission["job_id"],
               "filename": filename, "size_bytes": size, "url": url}
    public = {
        "source_id": SOURCE_ID,
        "status": "pass_exact_after_zip_descriptor_transfer_not_started",
        "job_id": submission["job_id"],
        "product_filename": filename,
        "expected_size_bytes": size,
        "provider_url_sha256": hashlib.sha256(url.encode("utf-8")).hexdigest(),
        "provider_url_recorded_publicly": False,
        "archive_bytes_acquired": False,
        "archive_integrity_verified": False,
        "pixel_qa_pass": False,
    }
    return private, public
