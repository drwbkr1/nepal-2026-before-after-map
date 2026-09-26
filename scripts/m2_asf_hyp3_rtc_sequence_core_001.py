"""Offline order guard for the approved four-scene HyP3 Basic RTC route.

This module has no credential, filesystem, or network capability. It does not
release job submission. A future gated executor must bind actual immutable
receipts and rights before using this prospective ordering decision.
"""

from __future__ import annotations

from m2_asf_hyp3_rtc_core_001 import ORDER, RouteStop


EVENT_PAIR = ORDER[:2]


def next_job_after_evidence(
    validation_terminal: dict,
    completed_jobs: list[dict],
    event_pair_qa: dict | None = None,
) -> str | None:
    """Choose the next exact source only from a passing, ordered prefix.

    Success here is a planning result, not an authorization or a real-data
    disposition. Event-pair QA is needed before either context-strip job.
    """
    if (
        not isinstance(validation_terminal, dict)
        or validation_terminal.get("status") != "pass_all_four_validate_only_requests"
        or validation_terminal.get("completed_sources") != list(ORDER)
        or validation_terminal.get("processing_job_submissions_requested") != 0
    ):
        raise RouteStop("submission_validation_evidence_missing")
    if not isinstance(completed_jobs, list) or len(completed_jobs) > len(ORDER):
        raise RouteStop("submission_completed_order_invalid")
    for index, item in enumerate(completed_jobs):
        if (
            not isinstance(item, dict)
            or set(item) != {"source_id", "job_terminal_status", "submission_identity_verified"}
            or item["source_id"] != ORDER[index]
            or item["job_terminal_status"] != "SUCCEEDED"
            or item["submission_identity_verified"] is not True
        ):
            raise RouteStop("submission_completed_order_invalid")
    if len(completed_jobs) >= len(EVENT_PAIR) and (
        not isinstance(event_pair_qa, dict)
        or set(event_pair_qa) != {
            "source_ids", "status", "product_identity_and_integrity_pass", "pixel_qa_pass"
        }
        or event_pair_qa["source_ids"] != list(EVENT_PAIR)
        or event_pair_qa["status"] != "PASS_QA_ONLY"
        or event_pair_qa["product_identity_and_integrity_pass"] is not True
        or event_pair_qa["pixel_qa_pass"] is not True
    ):
        raise RouteStop("submission_event_pair_qa_missing")
    return ORDER[len(completed_jobs)] if len(completed_jobs) < len(ORDER) else None
