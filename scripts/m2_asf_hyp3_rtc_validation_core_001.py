"""Pure guards for the exact HyP3 RTC validate-only stage.

This module performs no network, account, job, or pixel action. A validation
response is evidence of accepted request shape and quoted cost only; it is not
evidence of a submitted job, a generated product, or usable radar pixels.
"""

from __future__ import annotations

import copy
import math

from m2_asf_hyp3_rtc_core_001 import (
    ORDER,
    PER_JOB_CREDIT_CEILING,
    RouteStop,
    load_approved_jobs,
    one_job_payload,
)


VALIDATION_PASS = "pass_validate_only_identity_and_cost_only"


def one_validation_payload(jobs: tuple[dict, ...], source_id: str) -> dict:
    """Build one exact-source request with validate_only set explicitly."""
    if jobs != load_approved_jobs():
        raise RouteStop("validation_candidate_identity_mismatch")
    payload = copy.deepcopy(one_job_payload(jobs, source_id))
    payload["validate_only"] = True
    return payload


def inspect_validation(reply: dict, expected_job: dict, source_id: str) -> dict:
    """Return only non-identifying validation evidence or stop closed."""
    if source_id not in ORDER or not isinstance(reply, dict) or reply.get("validate_only") is not True:
        raise RouteStop("validation_response_not_validate_only")
    if expected_job != one_job_payload(load_approved_jobs(), source_id)["jobs"][0]:
        raise RouteStop("validation_candidate_identity_mismatch")
    jobs = reply.get("jobs")
    if not isinstance(jobs, list) or len(jobs) != 1 or not isinstance(jobs[0], dict):
        raise RouteStop("validation_response_ambiguous")
    actual = jobs[0]
    if any(actual.get(key) != expected_job[key] for key in ("name", "job_type", "job_parameters")):
        raise RouteStop("validation_identity_mismatch")
    quoted_cost = actual.get("credit_cost")
    if (
        isinstance(quoted_cost, bool)
        or not isinstance(quoted_cost, (int, float))
        or not math.isfinite(quoted_cost)
        or not 0 <= quoted_cost <= PER_JOB_CREDIT_CEILING
    ):
        raise RouteStop("validation_cost_invalid")
    if actual.get("status_code") != "PENDING" or actual.get("execution_started") is not False:
        raise RouteStop("validation_execution_state_ambiguous")
    if actual.get("files") not in (None, []):
        raise RouteStop("validation_product_state_ambiguous")
    # Deliberately omit user_id, job_id, URLs, raw response, and account values.
    return {
        "source_id": source_id,
        "status": VALIDATION_PASS,
        "quoted_basic_credit_cost_at_most_60": True,
        "job_submission_requested": False,
        "credits_spent_verified": False,
        "product_or_pixel_verified": False,
    }


def next_validation_source(receipts: list[dict]) -> str | None:
    """Accept only a passing prefix of the frozen event-first source order."""
    if not isinstance(receipts, list) or len(receipts) > len(ORDER):
        raise RouteStop("validation_receipt_order_invalid")
    for index, receipt in enumerate(receipts):
        if (
            not isinstance(receipt, dict)
            or receipt.get("source_id") != ORDER[index]
            or receipt.get("status") != VALIDATION_PASS
            or receipt.get("job_submission_requested") is not False
        ):
            raise RouteStop("validation_receipt_order_invalid")
    return ORDER[len(receipts)] if len(receipts) < len(ORDER) else None
