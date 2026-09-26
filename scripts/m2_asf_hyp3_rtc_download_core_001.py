"""Pure descriptor guard for the first approved HyP3 RTC ZIP transfer.

This module does not contact ASF, fetch a URL, create files, or read pixels.
The private descriptor must stay in memory or non-Git custody; public evidence
may contain only the sanitized summary returned alongside it.
"""

from __future__ import annotations

import hashlib
import re
from urllib.parse import urlsplit

from m2_asf_hyp3_rtc_core_001 import ORDER, RouteStop, load_approved_jobs
from m2_asf_hyp3_rtc_job_status_core_001 import inspect_exact_job_status
from m2_asf_hyp3_rtc_package_core_001 import PRODUCT_ROOT


MAX_ARCHIVE_BYTES = 100 * 1024**3
S3_HOST = re.compile(r"hyp3-contentbucket-[a-z0-9-]+\.s3\.us-west-2\.amazonaws\.com\Z")
CLOUDFRONT_HOST = re.compile(r"[a-z0-9-]+\.cloudfront\.net\Z")


def inspect_exact_zip_descriptor(reply: dict, submission: dict, source_id: str) -> tuple[dict, dict]:
    """Return private transfer input and a URL-free public screening result."""
    if source_id != ORDER[0]:
        raise RouteStop("rtc_download_source_not_first_job")
    status = inspect_exact_job_status(reply, submission, source_id)
    if status["disposition"] != "service_succeeded_product_unverified":
        raise RouteStop("rtc_download_job_not_succeeded")
    files = reply.get("files")
    if not isinstance(files, list) or len(files) != 1:
        raise RouteStop("rtc_download_file_count_invalid")
    item = files[0]
    filename = item.get("filename")
    if not isinstance(filename, str) or not filename.endswith(".zip"):
        raise RouteStop("rtc_download_filename_invalid")
    product_root = filename[:-4]
    match = PRODUCT_ROOT.fullmatch(product_root)
    granule_start = load_approved_jobs()[0]["job_parameters"]["granules"][0].split("_")[4]
    if match is None or match.group(1) != granule_start:
        raise RouteStop("rtc_download_filename_identity_mismatch")
    size = item.get("size")
    if type(size) is not int or not 0 < size <= MAX_ARCHIVE_BYTES:
        raise RouteStop("rtc_download_size_invalid")
    raw_url = item.get("url")
    if not isinstance(raw_url, str) or len(raw_url) > 2048:
        raise RouteStop("rtc_download_url_invalid")
    try:
        parsed = urlsplit(raw_url)
        host = parsed.hostname
        port = parsed.port
    except ValueError:
        raise RouteStop("rtc_download_url_invalid") from None
    if (
        parsed.scheme != "https" or not host or port not in (None, 443)
        or parsed.username is not None or parsed.password is not None
        or parsed.query or parsed.fragment
        or not (S3_HOST.fullmatch(host) or CLOUDFRONT_HOST.fullmatch(host))
        or parsed.path != f"/{submission['job_id']}/{filename}"
    ):
        raise RouteStop("rtc_download_url_invalid")
    private = {"url": raw_url, "filename": filename, "size_bytes": size,
               "job_id": submission["job_id"], "source_id": source_id}
    public = {
        "source_id": source_id,
        "status": "pass_exact_zip_descriptor_transfer_not_started",
        "job_id": submission["job_id"],
        "product_filename": filename,
        "expected_size_bytes": size,
        "provider_url_sha256": hashlib.sha256(raw_url.encode("utf-8")).hexdigest(),
        "provider_url_recorded_publicly": False,
        "archive_bytes_acquired": False,
        "archive_integrity_verified": False,
        "pixel_qa_pass": False,
    }
    return private, public
