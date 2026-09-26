#!/usr/bin/env python3
"""One owner-controlled, fixed-order HyP3 Basic validate-only attempt.

The executable is inert until its separate source, public-CI, and final
no-content gates are published. It never submits a processing job. Every
network attempt is reserved before the request, and no retry is automatic.
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

from m2_asf_hyp3_account_probe_001 import (
    HOST, MAX_SECRET_BYTES, get_basic_account,
    get_earthdata_token, read_owner_credentials, read_owner_token,
)
from m2_asf_hyp3_rtc_core_001 import APPROVAL_REF, ORDER, PROPOSAL_SHA256, ROOT, RouteStop, load_approved_jobs
from m2_asf_hyp3_rtc_validation_core_001 import inspect_validation, one_validation_payload


SOURCE_GATE_REF = "records/source-gates/m2-asf-hyp3-rtc-validate-only-source-gate-001.json"
IMPLEMENTATION_GATE_REF = "records/readiness/m2-asf-hyp3-rtc-validate-only-implementation-gate-001.json"
PREFLIGHT_REF = "records/readiness/m2-asf-hyp3-rtc-validate-only-preflight-001.json"
DATA_ROOT = ROOT.parent / f"{ROOT.name}-data"
ATTEMPT_ROOT = DATA_ROOT / "m2-asf-hyp3-rtc-validate-only-001" / "attempt-001"
MAX_VALIDATION_RESPONSE_BYTES = 262144
IMPLEMENTATION_FILES = (
    "scripts/m2_asf_hyp3_rtc_validate_only_001.py",
    "scripts/invoke_m2_asf_hyp3_rtc_validate_only_001.ps1",
    "tests/test_m2_asf_hyp3_rtc_validate_only_001.py",
)


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise RouteStop("validation_release_unavailable") from None
    if not isinstance(value, dict):
        raise RouteStop("validation_release_invalid")
    return value


def require_validation_release(root: Path = ROOT, attempt_root: Path = ATTEMPT_ROOT) -> None:
    """Stop before stdin or network unless every separate gate is current."""
    data_root = attempt_root.parents[1]
    source = _read_json(root / SOURCE_GATE_REF)
    gate = _read_json(root / IMPLEMENTATION_GATE_REF)
    preflight = _read_json(root / PREFLIGHT_REF)
    try:
        approval_sha = hashlib.sha256((root / APPROVAL_REF).read_bytes()).hexdigest()
        source_sha = hashlib.sha256((root / SOURCE_GATE_REF).read_bytes()).hexdigest()
        gate_sha = hashlib.sha256((root / IMPLEMENTATION_GATE_REF).read_bytes()).hexdigest()
        published = gate["bindings"]["implementation_file_sha256"]
        files_match = set(published) == set(IMPLEMENTATION_FILES) and all(
            hashlib.sha256((root / ref).read_bytes()).hexdigest() == published[ref]
            for ref in IMPLEMENTATION_FILES
        )
    except (OSError, KeyError, TypeError, ValueError):
        raise RouteStop("validation_release_invalid") from None
    sources = source.get("sources")
    criteria = sources[0].get("criteria", []) if isinstance(sources, list) and len(sources) == 1 and isinstance(sources[0], dict) else []
    if (
        source.get("decision", {}).get("status") != "ready"
        or len(criteria) != 8
        or any(item.get("required") is not True or item.get("status") not in {"pass", "not-applicable"} for item in criteria)
        or "validate_exact_rtc_job_without_submission" not in source.get("decision", {}).get("approved_actions", [])
        or source.get("authority", {}).get("authority_ref") != APPROVAL_REF
        or source.get("bindings", {}).get("proposal_sha256") != PROPOSAL_SHA256
        or source.get("bindings", {}).get("approval_sha256") != approval_sha
        or source.get("scope", {}).get("processing_job_submission_released") is not False
        or gate.get("status") != "pass_validate_only_implementation_public_ci_only"
        or gate.get("bindings", {}).get("approval_sha256") != approval_sha
        or gate.get("bindings", {}).get("source_gate_sha256") != source_sha
        or gate.get("public_ci", {}).get("conclusion") != "success"
        or not files_match
        or preflight.get("status") != "pass_validate_only_no_content"
        or preflight.get("bindings", {}).get("implementation_gate_sha256") != gate_sha
        or preflight.get("bindings", {}).get("approval_sha256") != approval_sha
        or preflight.get("assertions", {}).get("secret_or_account_or_job_request_performed") is not False
        or attempt_root.exists()
        or not data_root.is_dir()
        or data_root.is_symlink()
        or bool(getattr(data_root.stat(), "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
        or attempt_root.parent.is_symlink()
    ):
        raise RouteStop("validation_not_released")


def _write_new_json(path: Path, value: dict) -> None:
    try:
        with path.open("xb") as stream:
            stream.write((json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        raise RouteStop("validation_receipt_collision") from None
    except OSError:
        raise RouteStop("validation_receipt_write_failed") from None


def post_one_validate_only(token: str, source_id: str, connection_factory: Callable = http.client.HTTPSConnection) -> dict:
    """Send one exact-source dry-run request to the fixed Basic endpoint."""
    if not isinstance(token, str) or not token or len(token) > MAX_SECRET_BYTES or not all(char.isalnum() or char in "._-" for char in token):
        raise RouteStop("validation_token_invalid")
    jobs = load_approved_jobs()
    payload = one_validation_payload(jobs, source_id)
    if payload.get("validate_only") is not True or len(payload.get("jobs", [])) != 1:
        raise RouteStop("validation_payload_not_dry_run")
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    connection = None
    try:
        connection = connection_factory(HOST, timeout=30)
        connection.request(
            "POST", "/jobs", body=body,
            headers={
                "Authorization": f"Bearer {token}", "Accept": "application/json",
                "Content-Type": "application/json", "Content-Length": str(len(body)),
            },
        )
        response = connection.getresponse()
        if response.status != 200:
            raise RouteStop("validation_response_not_success")
        raw = response.read(MAX_VALIDATION_RESPONSE_BYTES + 1)
        if len(raw) > MAX_VALIDATION_RESPONSE_BYTES:
            raise RouteStop("validation_response_too_large")
        reply = json.loads(raw)
        return inspect_validation(reply, payload["jobs"][0], source_id)
    except RouteStop:
        raise
    except (OSError, ValueError):
        raise RouteStop("validation_request_failed") from None
    finally:
        if connection is not None:
            connection.close()


def validate_fixed_order(
    token: str,
    attempt_root: Path = ATTEMPT_ROOT,
    *,
    account_probe: Callable = get_basic_account,
    validate_one: Callable = post_one_validate_only,
) -> dict:
    """Check capacity, then reserve and attempt each exact source once."""
    account = account_probe(token)
    if account.get("status") != "account_probe_pass_free_credit_capacity_only" or account.get("at_least_240_free_basic_credits") is not True:
        raise RouteStop("validation_account_capacity_unverified")
    try:
        attempt_root.parent.mkdir(parents=True, exist_ok=True)
        attempt_root.mkdir(exist_ok=False)
    except FileExistsError:
        raise RouteStop("validation_attempt_collision") from None
    except OSError:
        raise RouteStop("validation_attempt_reservation_failed") from None
    _write_new_json(attempt_root / "started.json", {
        "status": "started", "started_at_utc": now_utc(),
        "source_order": list(ORDER), "validate_only": True,
        "account_capacity_pass_only": True, "credentials_recorded": False,
    })
    completed = []
    for index, source_id in enumerate(ORDER, start=1):
        prefix = f"{index:02d}-{source_id.lower()}"
        _write_new_json(attempt_root / f"{prefix}-started.json", {
            "source_id": source_id, "status": "request_reserved",
            "started_at_utc": now_utc(), "validate_only": True,
        })
        try:
            result = validate_one(token, source_id)
            if result.get("source_id") != source_id or result.get("status") != "pass_validate_only_identity_and_cost_only":
                raise RouteStop("validation_result_invalid")
        except RouteStop as exc:
            terminal = {"source_id": source_id, "status": "stopped_no_retry", "code": exc.code,
                        "finished_at_utc": now_utc(), "processing_job_submission_requested": False}
            _write_new_json(attempt_root / f"{prefix}-terminal.json", terminal)
            _write_new_json(attempt_root / "terminal.json", {
                "status": "stopped_on_first_validation_failure_no_retry", "completed_sources": completed,
                "stopped_source": source_id, "code": exc.code, "finished_at_utc": now_utc(),
                "processing_job_submissions_requested": 0, "credentials_recorded": False,
            })
            return {"status": "stopped_on_first_validation_failure_no_retry", "completed_sources": completed,
                    "stopped_source": source_id, "code": exc.code, "processing_job_submissions_requested": 0}
        _write_new_json(attempt_root / f"{prefix}-terminal.json", {**result, "finished_at_utc": now_utc()})
        completed.append(source_id)
    _write_new_json(attempt_root / "terminal.json", {
        "status": "pass_all_four_validate_only_requests", "completed_sources": completed,
        "finished_at_utc": now_utc(), "processing_job_submissions_requested": 0, "credentials_recorded": False,
    })
    return {"status": "pass_all_four_validate_only_requests",
            "completed_sources": completed, "processing_job_submissions_requested": 0}


def main() -> int:
    try:
        require_validation_release()
        if sys.argv[1:] == ["--check-release"]:
            print(json.dumps({"status": "pass_validate_only_release_no_secret_read"}, sort_keys=True))
            return 0
        if sys.argv[1:] not in ([], ["--earthdata-credentials"]):
            raise RouteStop("validation_arguments_invalid")
        if sys.argv[1:] == ["--earthdata-credentials"]:
            username, password = read_owner_credentials(sys.stdin.buffer)
            token = get_earthdata_token(username, password)
            username = password = ""
        else:
            token = read_owner_token(sys.stdin.buffer)
        result = validate_fixed_order(token)
        token = ""
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"] == "pass_all_four_validate_only_requests" else 12
    except RouteStop as exc:
        print(json.dumps({"status": "stopped", "code": exc.code, "credentials_recorded": False}, sort_keys=True))
        return 12
    except BaseException:
        print(json.dumps({"status": "stopped", "code": "validation_unexpected_failure", "credentials_recorded": False}, sort_keys=True))
        return 20


if __name__ == "__main__":
    raise SystemExit(main())
