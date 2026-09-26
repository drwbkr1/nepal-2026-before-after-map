#!/usr/bin/env python3
"""One gated, secret-safe submission of the first exact HyP3 Basic RTC job.

This does not poll, download, read pixels, or submit another source. An attempt
is reserved before POST /jobs and can never be reused after interruption.
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
    HOST, MAX_SECRET_BYTES, get_basic_account, get_earthdata_token,
    read_owner_credentials, read_owner_token,
)
from m2_asf_hyp3_rtc_core_001 import (
    APPROVAL_REF, ORDER, PROPOSAL_SHA256, ROOT, RouteStop,
    inspect_submission, load_approved_jobs, one_job_payload,
)


SOURCE_ID = ORDER[0]
SOURCE_GATE_REF = "records/source-gates/m2-asf-hyp3-rtc-processing-source-gate-001.json"
VALIDATION_REF = "records/readiness/m2-asf-hyp3-rtc-validate-only-terminal-reconciliation-001.json"
IMPLEMENTATION_GATE_REF = "records/readiness/m2-asf-hyp3-rtc-submit-first-implementation-gate-001.json"
PREFLIGHT_REF = "records/readiness/m2-asf-hyp3-rtc-submit-first-preflight-001.json"
DATA_ROOT = ROOT.parent / f"{ROOT.name}-data"
ATTEMPT_ROOT = DATA_ROOT / "m2-asf-hyp3-rtc-submit-first-001" / "attempt-001"
VALIDATION_ROOT = DATA_ROOT / "m2-asf-hyp3-rtc-validate-only-001" / "attempt-001"
IMPLEMENTATION_FILES = (
    "scripts/m2_asf_hyp3_rtc_submit_first_001.py",
    "scripts/invoke_m2_asf_hyp3_rtc_submit_first_001.ps1",
    "scripts/validate_m2_asf_hyp3_rtc_arcgis_synthetic_001.py",
    "tests/test_m2_asf_hyp3_rtc_submit_first_001.py",
)
MAX_RESPONSE_BYTES = 262144


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise RouteStop("submission_release_unavailable") from None
    if not isinstance(value, dict):
        raise RouteStop("submission_release_invalid")
    return value


def _sha(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        raise RouteStop("submission_release_unavailable") from None


def require_submission_release(
    root: Path = ROOT, attempt_root: Path = ATTEMPT_ROOT,
    validation_root: Path = VALIDATION_ROOT,
) -> None:
    """Check every published gate and validation byte identity before stdin."""
    source = _read_json(root / SOURCE_GATE_REF)
    validation = _read_json(root / VALIDATION_REF)
    gate = _read_json(root / IMPLEMENTATION_GATE_REF)
    preflight = _read_json(root / PREFLIGHT_REF)
    validation_terminal = _read_json(validation_root / "terminal.json")
    sources = source.get("sources")
    criteria = sources[0].get("criteria", []) if isinstance(sources, list) and len(sources) == 1 and isinstance(sources[0], dict) else []
    published = gate.get("bindings", {}).get("implementation_file_sha256", {})
    files_match = isinstance(published, dict) and set(published) == set(IMPLEMENTATION_FILES)
    if files_match:
        files_match = all(_sha(root / ref) == published[ref] for ref in IMPLEMENTATION_FILES)
    data_root = attempt_root.parents[1]
    if (
        source.get("decision", {}).get("status") != "ready"
        or source.get("authority", {}).get("authority_ref") != APPROVAL_REF
        or source.get("bindings", {}).get("approved_proposal_sha256") != PROPOSAL_SHA256
        or source.get("bindings", {}).get("owner_approval_sha256") != _sha(root / APPROVAL_REF)
        or source.get("bindings", {}).get("validate_only_terminal_reconciliation_sha256") != _sha(root / VALIDATION_REF)
        or "submit_exact_free_basic_rtc_job" not in source.get("decision", {}).get("approved_actions", [])
        or len(criteria) != 8
        or any(item.get("required") is not True or item.get("status") != "pass" for item in criteria)
        or validation.get("status") != "pass_exact_four_scene_validation_identity_and_cost_only"
        or validation.get("exact_order") != list(ORDER)
        or validation.get("verification", {}).get("processing_job_submissions_requested") != 0
        or _sha(validation_root / "terminal.json") != validation.get("attempt_terminal_sha256")
        or validation_terminal.get("status") != "pass_all_four_validate_only_requests"
        or validation_terminal.get("completed_sources") != list(ORDER)
        or validation_terminal.get("processing_job_submissions_requested") != 0
        or gate.get("status") != "pass_submit_first_implementation_public_ci_only"
        or gate.get("bindings", {}).get("proposal_sha256") != PROPOSAL_SHA256
        or gate.get("bindings", {}).get("approval_sha256") != _sha(root / APPROVAL_REF)
        or gate.get("bindings", {}).get("source_gate_sha256") != _sha(root / SOURCE_GATE_REF)
        or gate.get("bindings", {}).get("validation_reconciliation_sha256") != _sha(root / VALIDATION_REF)
        or gate.get("public_ci", {}).get("conclusion") != "success"
        or not files_match
        or preflight.get("status") != "pass_submit_first_no_content"
        or preflight.get("bindings", {}).get("implementation_gate_sha256") != _sha(root / IMPLEMENTATION_GATE_REF)
        or preflight.get("bindings", {}).get("source_gate_sha256") != _sha(root / SOURCE_GATE_REF)
        or preflight.get("assertions", {}).get("job_request_performed") is not False
        or attempt_root.exists()
        or not data_root.is_dir()
        or data_root.is_symlink()
        or bool(getattr(data_root.stat(), "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
        or attempt_root.parent.is_symlink()
    ):
        raise RouteStop("submission_not_released")


def _write_new_json(path: Path, value: dict) -> None:
    try:
        with path.open("xb") as stream:
            stream.write((json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        raise RouteStop("submission_receipt_collision") from None
    except OSError:
        raise RouteStop("submission_receipt_write_failed") from None


def post_exact_first_job(token: str, connection_factory: Callable = http.client.HTTPSConnection) -> dict:
    """Send one false-validate-only request; return a whitelisted receipt."""
    if not isinstance(token, str) or not token or len(token) > MAX_SECRET_BYTES or not all(char.isalnum() or char in "._-" for char in token):
        raise RouteStop("submission_token_invalid")
    payload = one_job_payload(load_approved_jobs(), SOURCE_ID)
    if payload.get("validate_only") is not False or len(payload.get("jobs", [])) != 1:
        raise RouteStop("submission_payload_invalid")
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
            raise RouteStop("submission_response_not_success")
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise RouteStop("submission_response_too_large")
        reply = json.loads(raw)
        accepted = inspect_submission(reply, payload["jobs"][0])
        job_id = accepted["job_id"]
        try:
            if str(UUID(job_id)) != job_id:
                raise ValueError("noncanonical UUID")
        except ValueError:
            raise RouteStop("submission_job_id_invalid") from None
        return {
            "source_id": SOURCE_ID, "status": "submitted_product_unverified",
            "job_id": job_id, "name": accepted["name"],
            "job_type": accepted["job_type"],
            "job_parameters": accepted["job_parameters"],
            "status_code": accepted["status_code"],
            "credit_cost": accepted["credit_cost"],
        }
    except RouteStop:
        raise
    except (OSError, ValueError):
        raise RouteStop("submission_request_failed_or_indeterminate") from None
    finally:
        if connection is not None:
            connection.close()


def submit_first(
    token: str, attempt_root: Path = ATTEMPT_ROOT,
    *, account_probe: Callable = get_basic_account,
    post_one: Callable = post_exact_first_job,
) -> dict:
    """Reserve one attempt after a fresh free-credit check, then POST once."""
    account = account_probe(token)
    if account.get("status") != "account_probe_pass_free_credit_capacity_only" or account.get("at_least_240_free_basic_credits") is not True:
        raise RouteStop("submission_fresh_free_capacity_unverified")
    try:
        attempt_root.parent.mkdir(parents=True, exist_ok=True)
        attempt_root.mkdir(exist_ok=False)
    except FileExistsError:
        raise RouteStop("submission_attempt_collision") from None
    except OSError:
        raise RouteStop("submission_attempt_reservation_failed") from None
    _write_new_json(attempt_root / "started.json", {
        "status": "request_reserved", "source_id": SOURCE_ID,
        "started_at_utc": now_utc(), "validate_only": False,
        "fresh_free_basic_capacity_at_least_240": True,
        "credentials_recorded": False,
    })
    try:
        result = post_one(token)
        if result.get("source_id") != SOURCE_ID or result.get("status") != "submitted_product_unverified":
            raise RouteStop("submission_result_invalid")
    except RouteStop as exc:
        _write_new_json(attempt_root / "terminal.json", {
            "status": "stopped_or_indeterminate_no_retry", "source_id": SOURCE_ID,
            "code": exc.code, "finished_at_utc": now_utc(),
            "job_identity_verified": False, "credentials_recorded": False,
        })
        return {"status": "stopped_or_indeterminate_no_retry", "source_id": SOURCE_ID, "code": exc.code}
    _write_new_json(attempt_root / "terminal.json", {
        **result, "finished_at_utc": now_utc(), "credentials_recorded": False,
        "product_bytes_verified": False, "pixel_qa_pass": False,
    })
    return {"status": "submitted_product_unverified", "source_id": SOURCE_ID,
            "job_id": result["job_id"], "product_bytes_verified": False, "pixel_qa_pass": False}


def main() -> int:
    try:
        require_submission_release()
        if sys.argv[1:] == ["--check-release"]:
            print(json.dumps({"status": "pass_submit_first_release_no_secret_read"}, sort_keys=True))
            return 0
        if sys.argv[1:] not in ([], ["--earthdata-credentials"]):
            raise RouteStop("submission_arguments_invalid")
        if sys.argv[1:] == ["--earthdata-credentials"]:
            username, password = read_owner_credentials(sys.stdin.buffer)
            token = get_earthdata_token(username, password)
            username = password = ""
        else:
            token = read_owner_token(sys.stdin.buffer)
        result = submit_first(token)
        token = ""
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"] == "submitted_product_unverified" else 12
    except RouteStop as exc:
        print(json.dumps({"status": "stopped", "code": exc.code, "credentials_recorded": False}, sort_keys=True))
        return 12
    except BaseException:
        print(json.dumps({"status": "stopped", "code": "submission_unexpected_failure", "credentials_recorded": False}, sort_keys=True))
        return 20


if __name__ == "__main__":
    raise SystemExit(main())
