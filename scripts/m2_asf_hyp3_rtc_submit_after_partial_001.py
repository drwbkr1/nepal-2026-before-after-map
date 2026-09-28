#!/usr/bin/env python3
"""One gated, secret-safe M1-SRC-005 Basic RTC submission for a partial map.

The first source remains deferred. This worker neither reads its product nor
interprets change. The after-job attempt is reserved before network use and
never retried, including when a response is indeterminate.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import stat
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable
from uuid import UUID

from m2_asf_hyp3_account_probe_001 import (
    HOST, MAX_SECRET_BYTES, get_earthdata_token, read_owner_credentials,
    read_owner_token,
)
from m2_asf_hyp3_rtc_core_001 import (
    ROOT, RouteStop, check_free_credits, inspect_submission,
    load_approved_jobs, one_job_payload,
)
from m2_asf_hyp3_rtc_validation_core_001 import inspect_validation, one_validation_payload


SOURCE_ID = "M1-SRC-005"
PROPOSAL_REF = "contracts/milestone-002-asf-hyp3-rtc-partial-pair-map-001-proposal.json"
PROPOSAL_SHA = "587b3e5fe4878395d0a32802e19a66b77ed2c57dcb924dd14796d0ff462c9d8a"
BUNDLE_REF = "reviews/m2-asf-hyp3-rtc-partial-pair-map-001/review-bundle.json"
BUNDLE_SHA = "f3c981c36bc1f9ebf61f42a3451e7aa05e5a040799a59ced78a5dc741665f58e"
APPROVAL_REF = "records/source-gates/m2-asf-hyp3-rtc-partial-pair-map-001-approval.json"
APPROVAL_SHA = "7092d2c5f7e4b3f2d0c9cff22a7c0d0a44c62942746a9b73c183b3b96f08d506"
REVIEW_GATE_REF = "records/readiness/m2-asf-hyp3-rtc-partial-pair-map-001-review-publication-gate.json"
FIRST_TERMINAL_REF = "records/readiness/m2-asf-hyp3-rtc-product-pixel-001-terminal-reconciliation.json"
FIRST_TERMINAL_SHA = "2305f6ce504e550b57aa207c3eb1004f2d4c014715745776d60c004e184afecd"
IMPLEMENTATION_GATE_REF = "records/readiness/m2-asf-hyp3-rtc-submit-after-partial-001-implementation-gate.json"
PREFLIGHT_REF = "records/readiness/m2-asf-hyp3-rtc-submit-after-partial-001-preflight.json"
DATA_ROOT = ROOT.parent / f"{ROOT.name}-data"
ATTEMPT_ROOT = DATA_ROOT / "m2-asf-hyp3-rtc-submit-after-partial-001" / "attempt-001"
IMPLEMENTATION_FILES = (
    "scripts/m2_asf_hyp3_rtc_submit_after_partial_001.py",
    "scripts/invoke_m2_asf_hyp3_rtc_submit_after_partial_001.ps1",
    "tests/test_m2_asf_hyp3_rtc_submit_after_partial_001.py",
)
MAX_RESPONSE_BYTES = 262144


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        raise RouteStop("after_release_unavailable") from None


def _json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise RouteStop("after_release_unavailable") from None
    if not isinstance(value, dict):
        raise RouteStop("after_release_invalid")
    return value


def require_release(root: Path = ROOT, attempt_root: Path = ATTEMPT_ROOT) -> None:
    """Stop before stdin or network unless exact public and local gates pass."""
    if any(_sha(root / ref) != sha for ref, sha in (
        (PROPOSAL_REF, PROPOSAL_SHA), (BUNDLE_REF, BUNDLE_SHA),
        (APPROVAL_REF, APPROVAL_SHA), (FIRST_TERMINAL_REF, FIRST_TERMINAL_SHA),
    )):
        raise RouteStop("after_bound_identity_mismatch")
    approval = _json(root / APPROVAL_REF)
    review = _json(root / REVIEW_GATE_REF)
    first = _json(root / FIRST_TERMINAL_REF)
    implementation = _json(root / IMPLEMENTATION_GATE_REF)
    preflight = _json(root / PREFLIGHT_REF)
    files = implementation.get("bindings", {}).get("implementation_file_sha256")
    if (
        approval.get("decision") != "approve"
        or approval.get("authority", {}).get("at_most_one_exact_M1_SRC_005_RTC_GAMMA_job_after_gates") is not True
        or review.get("status") != "pass_exact_review_packet_public_ci_only"
        or review.get("bindings", {}).get("owner_approval_sha256") != APPROVAL_SHA
        or review.get("observed_public_ci", {}).get("run_conclusion") != "success"
        or first.get("status") != "stop_source_event_aoi_pixel_qa_no_next_date"
        or first.get("verification", {}).get("next_ASF_job_submitted") is not False
        or implementation.get("status") != "pass_submit_after_partial_implementation_public_ci_only"
        or implementation.get("bindings", {}).get("proposal_sha256") != PROPOSAL_SHA
        or implementation.get("bindings", {}).get("approval_sha256") != APPROVAL_SHA
        or implementation.get("bindings", {}).get("review_gate_sha256") != _sha(root / REVIEW_GATE_REF)
        or implementation.get("public_ci", {}).get("conclusion") != "success"
        or not isinstance(files, dict) or set(files) != set(IMPLEMENTATION_FILES)
        or any(_sha(root / ref) != files[ref] for ref in IMPLEMENTATION_FILES)
        or preflight.get("status") != "pass_submit_after_partial_no_content"
        or preflight.get("bindings", {}).get("implementation_gate_sha256") != _sha(root / IMPLEMENTATION_GATE_REF)
        or preflight.get("bindings", {}).get("first_terminal_sha256") != FIRST_TERMINAL_SHA
        or preflight.get("assertions", {}).get("attempt_absent") is not True
        or preflight.get("assertions", {}).get("no_secret_or_account_or_job_request") is not True
        or attempt_root.exists() or attempt_root.is_symlink()
    ):
        raise RouteStop("after_submission_not_released")
    data_root = attempt_root.parents[1]
    if (
        not data_root.is_dir() or data_root.is_symlink()
        or bool(getattr(data_root.stat(), "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
        or attempt_root.parent.is_symlink()
    ):
        raise RouteStop("after_custody_path_invalid")


def _write_new(path: Path, value: dict) -> None:
    try:
        with path.open("xb") as stream:
            stream.write((json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        raise RouteStop("after_receipt_collision") from None
    except OSError:
        raise RouteStop("after_receipt_write_failed") from None


def _request(token: str, method: str, path: str, body: bytes | None = None,
             connection_factory: Callable = http.client.HTTPSConnection) -> dict:
    if not token or len(token) > MAX_SECRET_BYTES or not all(c.isalnum() or c in "._-" for c in token):
        raise RouteStop("after_token_invalid")
    connection = None
    try:
        connection = connection_factory(HOST, timeout=30)
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        if body is not None:
            headers.update({"Content-Type": "application/json", "Content-Length": str(len(body))})
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        if response.status != 200:
            raise RouteStop("after_response_not_success")
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise RouteStop("after_response_too_large")
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise RouteStop("after_response_invalid")
        return value
    except RouteStop:
        raise
    except (OSError, ValueError):
        raise RouteStop("after_request_failed_or_indeterminate") from None
    finally:
        if connection is not None:
            connection.close()


def account_60(token: str) -> dict:
    value = _request(token, "GET", "/user")
    check_free_credits(value, required_jobs=1)
    if value.get("application_status") not in {"NOT_STARTED", "PENDING", "APPROVED", "REJECTED"}:
        raise RouteStop("after_account_status_unknown")
    return {"status": "pass_free_basic_capacity_at_least_60_only", "account_identity_recorded": False}


def validate_after(token: str) -> dict:
    payload = one_validation_payload(load_approved_jobs(), SOURCE_ID)
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return inspect_validation(_request(token, "POST", "/jobs", body), payload["jobs"][0], SOURCE_ID)


def submit_after(token: str) -> dict:
    payload = one_job_payload(load_approved_jobs(), SOURCE_ID)
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    result = inspect_submission(_request(token, "POST", "/jobs", body), payload["jobs"][0])
    try:
        if str(UUID(result["job_id"])) != result["job_id"]:
            raise ValueError("noncanonical UUID")
    except ValueError:
        raise RouteStop("after_job_id_invalid") from None
    return result


def run_once(token: str, attempt_root: Path = ATTEMPT_ROOT, *,
             probe: Callable = account_60, validate: Callable = validate_after,
             submit: Callable = submit_after) -> dict:
    """Reserve once; stop on any account, validation, or submission ambiguity."""
    try:
        attempt_root.parent.mkdir(parents=True, exist_ok=True)
        attempt_root.mkdir(exist_ok=False)
    except FileExistsError:
        raise RouteStop("after_attempt_collision") from None
    except OSError:
        raise RouteStop("after_attempt_reservation_failed") from None
    _write_new(attempt_root / "started.json", {
        "status": "after_attempt_reserved", "source_id": SOURCE_ID,
        "started_at_utc": _now(), "credentials_recorded": False,
    })
    try:
        account = probe(token)
        if account.get("status") != "pass_free_basic_capacity_at_least_60_only":
            raise RouteStop("after_fresh_free_capacity_unverified")
        _write_new(attempt_root / "validation-request-reserved.json", {
            "status": "validate_only_request_reserved", "source_id": SOURCE_ID, "at_utc": _now(),
        })
        validation = validate(token)
        if validation.get("source_id") != SOURCE_ID or validation.get("status") != "pass_validate_only_identity_and_cost_only":
            raise RouteStop("after_validation_invalid")
        _write_new(attempt_root / "validation-terminal.json", {**validation, "at_utc": _now()})
        _write_new(attempt_root / "submission-request-reserved.json", {
            "status": "processing_request_reserved", "source_id": SOURCE_ID, "at_utc": _now(),
        })
        result = submit(token)
        if not isinstance(result, dict) or result.get("job_type") != "RTC_GAMMA":
            raise RouteStop("after_submission_identity_invalid")
        terminal = {
            "status": "submitted_product_unverified", "source_id": SOURCE_ID,
            "job_id": result["job_id"], "credit_cost": result["credit_cost"],
            "finished_at_utc": _now(), "product_bytes_verified": False,
            "pixel_qa_pass": False, "credentials_recorded": False,
        }
    except RouteStop as exc:
        terminal = {"status": "stopped_or_indeterminate_no_retry", "source_id": SOURCE_ID,
                    "code": exc.code, "finished_at_utc": _now(), "credentials_recorded": False}
    except BaseException:
        terminal = {"status": "stopped_or_indeterminate_no_retry", "source_id": SOURCE_ID,
                    "code": "after_unexpected_failure", "finished_at_utc": _now(), "credentials_recorded": False}
    _write_new(attempt_root / "terminal.json", terminal)
    return terminal


def main() -> int:
    try:
        require_release()
        if sys.argv[1:] == ["--check-release"]:
            print(json.dumps({"status": "pass_after_submission_release_no_secret_read"}))
            return 0
        if sys.argv[1:] not in ([], ["--earthdata-credentials"]):
            raise RouteStop("after_arguments_invalid")
        if sys.argv[1:] == ["--earthdata-credentials"]:
            username, password = read_owner_credentials(sys.stdin.buffer)
            token = get_earthdata_token(username, password)
            username = password = ""
        else:
            token = read_owner_token(sys.stdin.buffer)
        result = run_once(token)
        token = ""
        print(json.dumps({key: result[key] for key in ("status", "source_id", "job_id", "code") if key in result}, sort_keys=True))
        return 0 if result["status"] == "submitted_product_unverified" else 12
    except RouteStop as exc:
        print(json.dumps({"status": "stopped", "code": exc.code, "credentials_recorded": False}, sort_keys=True))
        return 12
    except BaseException:
        print(json.dumps({"status": "stopped", "code": "after_unexpected_failure", "credentials_recorded": False}, sort_keys=True))
        return 20


if __name__ == "__main__":
    raise SystemExit(main())
