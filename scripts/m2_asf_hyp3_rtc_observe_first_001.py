#!/usr/bin/env python3
"""One read-only, secret-safe status observation for the first HyP3 RTC job.

Each invocation reserves a distinct non-Git receipt before one GET. No POST,
retry, download, product pixel read, or map action occurs here.
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
from uuid import UUID, uuid4

from m2_asf_hyp3_account_probe_001 import (
    HOST, MAX_SECRET_BYTES, get_earthdata_token, read_owner_credentials,
    read_owner_token,
)
from m2_asf_hyp3_rtc_core_001 import (
    APPROVAL_REF, ORDER, PER_JOB_CREDIT_CEILING, ROOT, RouteStop,
    load_approved_jobs, one_job_payload,
)
from m2_asf_hyp3_rtc_job_status_core_001 import inspect_exact_job_status


SOURCE_ID = ORDER[0]
SUBMISSION_REF = "m2-asf-hyp3-rtc-submit-first-001/attempt-001/terminal.json"
MONITOR_GATE_REF = "records/readiness/m2-asf-hyp3-rtc-observe-first-implementation-gate-001.json"
SOURCE_GATE_REF = "records/source-gates/m2-asf-hyp3-rtc-processing-source-gate-001.json"
DATA_ROOT = ROOT.parent / f"{ROOT.name}-data"
OBSERVATION_PARENT = DATA_ROOT / "m2-asf-hyp3-rtc-observe-first-001"
IMPLEMENTATION_FILES = (
    "scripts/m2_asf_hyp3_rtc_observe_first_001.py",
    "scripts/invoke_m2_asf_hyp3_rtc_observe_first_001.ps1",
    "tests/test_m2_asf_hyp3_rtc_observe_first_001.py",
)
MAX_RESPONSE_BYTES = 262144


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise RouteStop("observation_release_unavailable") from None
    if not isinstance(value, dict):
        raise RouteStop("observation_release_invalid")
    return value


def _sha(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        raise RouteStop("observation_release_unavailable") from None


def _canonical_uuid(value: object) -> bool:
    try:
        return isinstance(value, str) and str(UUID(value)) == value
    except ValueError:
        return False


def require_observation_release(
    root: Path = ROOT, data_root: Path = DATA_ROOT,
    observation_parent: Path = OBSERVATION_PARENT,
) -> dict:
    """Require a published observer and a locally verified first submission."""
    gate = _read_json(root / MONITOR_GATE_REF)
    source = _read_json(root / SOURCE_GATE_REF)
    submission_path = data_root / SUBMISSION_REF
    if submission_path.is_symlink() or submission_path.parent.is_symlink() or submission_path.parent.parent.is_symlink():
        raise RouteStop("observation_submission_path_invalid")
    submission = _read_json(submission_path)
    published = gate.get("bindings", {}).get("implementation_file_sha256")
    files_match = isinstance(published, dict) and set(published) == set(IMPLEMENTATION_FILES)
    if files_match:
        files_match = all(_sha(root / ref) == published[ref] for ref in IMPLEMENTATION_FILES)
    try:
        data_safe = (
            data_root.is_dir() and not data_root.is_symlink()
            and not bool(getattr(data_root.stat(), "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
            and observation_parent.parent.resolve() == data_root.resolve()
            and not observation_parent.is_symlink()
            and not (observation_parent.exists() and bool(getattr(observation_parent.stat(), "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)))
        )
    except OSError:
        data_safe = False
    expected = one_job_payload(load_approved_jobs(), SOURCE_ID)["jobs"][0]
    if (
        gate.get("status") != "pass_observe_first_implementation_public_ci_only"
        or gate.get("bindings", {}).get("approval_sha256") != _sha(root / APPROVAL_REF)
        or gate.get("bindings", {}).get("source_gate_sha256") != _sha(root / SOURCE_GATE_REF)
        or gate.get("public_ci", {}).get("conclusion") != "success"
        or not files_match
        or source.get("decision", {}).get("status") != "ready"
        or source.get("authority", {}).get("authority_ref") != APPROVAL_REF
        or not data_safe
        or submission.get("status") != "submitted_product_unverified"
        or submission.get("source_id") != SOURCE_ID
        or not _canonical_uuid(submission.get("job_id"))
        or any(submission.get(key) != expected[key] for key in ("name", "job_type", "job_parameters"))
        or submission.get("status_code") not in {"PENDING", "RUNNING", "SUCCEEDED"}
        or type(submission.get("credit_cost")) not in (int, float)
        or not 0 <= submission["credit_cost"] <= PER_JOB_CREDIT_CEILING
        or submission.get("credentials_recorded") is not False
        or submission.get("product_bytes_verified") is not False
        or submission.get("pixel_qa_pass") is not False
    ):
        raise RouteStop("observation_not_released")
    # The pure inspector checks every exact approved job field against the
    # candidate when the actual status response arrives.
    return submission


def _write_new_json(path: Path, value: dict) -> None:
    try:
        with path.open("xb") as stream:
            stream.write((json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        raise RouteStop("observation_receipt_collision") from None
    except OSError:
        raise RouteStop("observation_receipt_write_failed") from None


def get_one_job_status(
    token: str, submission: dict,
    connection_factory: Callable = http.client.HTTPSConnection,
) -> dict:
    """One exact Basic GET; return no account, URLs, logs, or raw JSON."""
    job_id = submission.get("job_id")
    if (
        not isinstance(token, str) or not token or len(token) > MAX_SECRET_BYTES
        or not all(char.isalnum() or char in "._-" for char in token)
        or not _canonical_uuid(job_id)
    ):
        raise RouteStop("observation_input_invalid")
    connection = None
    try:
        connection = connection_factory(HOST, timeout=30)
        connection.request(
            "GET", f"/jobs/{job_id}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )
        response = connection.getresponse()
        if response.status != 200:
            raise RouteStop("observation_response_not_success")
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise RouteStop("observation_response_too_large")
        reply = json.loads(raw)
        return inspect_exact_job_status(reply, submission, SOURCE_ID)
    except RouteStop:
        raise
    except (OSError, ValueError):
        raise RouteStop("observation_request_failed") from None
    finally:
        if connection is not None:
            connection.close()


def observe_once(
    token: str, submission: dict,
    observation_parent: Path = OBSERVATION_PARENT,
    *, get_status: Callable = get_one_job_status,
) -> dict:
    """Reserve a distinct observation; a failure never mutates the job."""
    if observation_parent.is_symlink() or (
        observation_parent.exists()
        and bool(getattr(observation_parent.stat(), "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
    ):
        raise RouteStop("observation_parent_invalid")
    attempt = observation_parent / f"observation-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}-{uuid4().hex[:12]}"
    try:
        observation_parent.mkdir(parents=True, exist_ok=True)
        attempt.mkdir(exist_ok=False)
    except (FileExistsError, OSError):
        raise RouteStop("observation_reservation_failed") from None
    _write_new_json(attempt / "started.json", {
        "status": "request_reserved", "source_id": SOURCE_ID,
        "job_id": submission["job_id"], "started_at_utc": now_utc(),
        "method": "GET", "credentials_recorded": False,
    })
    try:
        result = get_status(token, submission)
        if result.get("source_id") != SOURCE_ID or result.get("job_id") != submission["job_id"]:
            raise RouteStop("observation_result_invalid")
    except RouteStop as exc:
        _write_new_json(attempt / "terminal.json", {
            "status": "stopped_no_job_mutation", "source_id": SOURCE_ID,
            "job_id": submission["job_id"], "code": exc.code,
            "finished_at_utc": now_utc(), "credentials_recorded": False,
        })
        return {"status": "stopped_no_job_mutation", "code": exc.code, "source_id": SOURCE_ID}
    _write_new_json(attempt / "terminal.json", {
        **result, "finished_at_utc": now_utc(), "credentials_recorded": False,
    })
    return result


def main() -> int:
    try:
        submission = require_observation_release()
        if sys.argv[1:] == ["--check-release"]:
            print(json.dumps({"status": "pass_observation_release_no_secret_read"}, sort_keys=True))
            return 0
        if sys.argv[1:] not in ([], ["--earthdata-credentials"]):
            raise RouteStop("observation_arguments_invalid")
        if sys.argv[1:] == ["--earthdata-credentials"]:
            username, password = read_owner_credentials(sys.stdin.buffer)
            token = get_earthdata_token(username, password)
            username = password = ""
        else:
            token = read_owner_token(sys.stdin.buffer)
        result = observe_once(token, submission)
        token = ""
        print(json.dumps(result, sort_keys=True))
        return 0 if result.get("disposition") in {
            "service_not_terminal_observe_same_job", "service_succeeded_product_unverified",
            "service_failed_terminal_no_retry",
        } else 12
    except RouteStop as exc:
        print(json.dumps({"status": "stopped", "code": exc.code, "credentials_recorded": False}, sort_keys=True))
        return 12
    except BaseException:
        print(json.dumps({"status": "stopped", "code": "observation_unexpected_failure", "credentials_recorded": False}, sort_keys=True))
        return 20


if __name__ == "__main__":
    raise SystemExit(main())
