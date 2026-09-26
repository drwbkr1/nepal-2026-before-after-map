"""Offline inspection of one exact HyP3 Basic RTC job status response.

This module makes no request and cannot submit a job. Its output omits user
identity, download URLs, logs, and raw provider JSON. A successful service
status is not a verified archive, raster, or scientific result.
"""

from __future__ import annotations

import math

from m2_asf_hyp3_rtc_core_001 import ORDER, PER_JOB_CREDIT_CEILING, RouteStop, load_approved_jobs, one_job_payload


def inspect_exact_job_status(reply: dict, submission: dict, source_id: str) -> dict:
    """Return a sanitized status for one previously accepted exact job."""
    if source_id not in ORDER or not isinstance(reply, dict) or not isinstance(submission, dict):
        raise RouteStop("job_status_input_invalid")
    expected = one_job_payload(load_approved_jobs(), source_id)["jobs"][0]
    if (
        submission.get("name") != expected["name"]
        or submission.get("job_type") != expected["job_type"]
        or submission.get("job_parameters") != expected["job_parameters"]
        or not isinstance(submission.get("job_id"), str)
        or len(submission["job_id"]) != 36
    ):
        raise RouteStop("job_status_submission_identity_invalid")
    if any(reply.get(key) != submission[key] for key in ("job_id", "name", "job_type", "job_parameters")):
        raise RouteStop("job_status_identity_mismatch")
    cost = reply.get("credit_cost")
    if (
        isinstance(cost, bool) or not isinstance(cost, (int, float))
        or not math.isfinite(cost) or not 0 <= cost <= PER_JOB_CREDIT_CEILING
        or cost != submission.get("credit_cost")
    ):
        raise RouteStop("job_status_cost_mismatch")
    status = reply.get("status_code")
    if status not in {"PENDING", "RUNNING", "SUCCEEDED", "FAILED"}:
        raise RouteStop("job_status_unknown")
    files = reply.get("files")
    if status == "SUCCEEDED":
        if not isinstance(files, list) or not files:
            raise RouteStop("job_status_success_without_files")
        for item in files:
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("filename"), str)
                or not item["filename"]
                or isinstance(item.get("size"), bool)
                or not isinstance(item.get("size"), int)
                or item["size"] <= 0
                or not isinstance(item.get("url"), str)
                or not item["url"].startswith("https://")
            ):
                raise RouteStop("job_status_file_descriptor_invalid")
        disposition = "service_succeeded_product_unverified"
    elif status == "FAILED":
        disposition = "service_failed_terminal_no_retry"
    else:
        if files not in (None, []):
            raise RouteStop("job_status_nonterminal_files_ambiguous")
        disposition = "service_not_terminal_observe_same_job"
    return {
        "source_id": source_id,
        "job_id": submission["job_id"],
        "provider_status": status,
        "disposition": disposition,
        "reported_file_count": len(files) if status == "SUCCEEDED" else 0,
        "product_bytes_verified": False,
        "pixel_qa_pass": False,
        "change_or_attribution_claim": False,
    }
