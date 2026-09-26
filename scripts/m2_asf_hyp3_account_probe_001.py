#!/usr/bin/env python3
"""One secret-safe, read-only HyP3 Basic account probe after published gates.

The Earthdata bearer token arrives on standard input, never in argv, an
environment variable, a file, a log, or a repository record. This module is
not an execution gate by itself; missing account-use or CI receipts stop it before
it reads standard input or opens a connection.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import sys
from pathlib import Path
from typing import BinaryIO, Callable

from m2_asf_hyp3_rtc_core_001 import APPROVAL_REF, PROPOSAL_SHA256, ROOT, RouteStop, check_free_credits


HOST = "hyp3-api.asf.alaska.edu"
RIGHTS_GATE_REF = "records/source-gates/m2-asf-hyp3-rtc-live-source-gate-001.json"
IMPLEMENTATION_GATE_REF = "records/readiness/m2-asf-hyp3-rtc-map-route-001-implementation-publication-gate.json"
FINAL_PREFLIGHT_REF = "records/readiness/m2-asf-hyp3-rtc-map-route-001-account-preflight.json"
MAX_SECRET_BYTES = 4096
MAX_RESPONSE_BYTES = 65536


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise RouteStop("probe_gate_unavailable") from None
    if not isinstance(value, dict):
        raise RouteStop("probe_gate_invalid")
    return value


def require_account_probe_release(root: Path = ROOT) -> None:
    """Reject account use until a scoped read-only gate and CI are durable."""
    rights = _read_json(root / RIGHTS_GATE_REF)
    implementation = _read_json(root / IMPLEMENTATION_GATE_REF)
    preflight = _read_json(root / FINAL_PREFLIGHT_REF)
    approval_sha = hashlib.sha256((root / APPROVAL_REF).read_bytes()).hexdigest()
    implementation_sha = hashlib.sha256((root / IMPLEMENTATION_GATE_REF).read_bytes()).hexdigest()
    sources = rights.get("sources")
    criteria = sources[0].get("criteria", []) if isinstance(sources, list) and len(sources) == 1 and isinstance(sources[0], dict) else []
    if (
        rights.get("decision", {}).get("status") != "ready"
        or len(criteria) != 8
        or any(item.get("required") is not True or item.get("status") not in {"pass", "not-applicable"} for item in criteria)
        or rights.get("authority", {}).get("authority_ref") != APPROVAL_REF
        or rights.get("bindings", {}).get("proposal_sha256") != PROPOSAL_SHA256
        or rights.get("bindings", {}).get("approval_sha256") != approval_sha
        or rights.get("terms", {}).get("public_account_use_guidance_assessed") is not True
        or rights.get("terms", {}).get("job_and_product_rights_released") is not False
        or "read_own_basic_account_capacity" not in rights.get("decision", {}).get("approved_actions", [])
        or implementation.get("status") != "pass_exact_implementation_public_ci"
        or implementation.get("bindings", {}).get("approval_sha256") != approval_sha
        or implementation.get("public_ci", {}).get("conclusion") != "success"
        or implementation.get("assertions", {}).get("account_or_job_request_performed") is not False
        or preflight.get("status") != "pass_no_content_account_probe_only"
        or preflight.get("bindings", {}).get("implementation_gate_sha256") != implementation_sha
        or preflight.get("bindings", {}).get("approval_sha256") != approval_sha
        or preflight.get("assertions", {}).get("secret_read_or_account_request_performed") is not False
    ):
        raise RouteStop("account_probe_not_released")


def read_owner_token(stream: BinaryIO) -> str:
    """Read one token from an anonymous pipe; never echo or retain the bytes."""
    data = bytearray(stream.readline(MAX_SECRET_BYTES + 3))
    try:
        if data.endswith(b"\r\n"):
            del data[-2:]
        elif data.endswith(b"\n"):
            del data[-1:]
        else:
            raise RouteStop("token_pipe_invalid")
        if not data or len(data) > MAX_SECRET_BYTES or any(value <= 32 or value >= 127 for value in data):
            raise RouteStop("token_pipe_invalid")
        token = data.decode("ascii")
        if not all(char.isalnum() or char in "._-" for char in token):
            raise RouteStop("token_pipe_invalid")
        return token
    finally:
        for index in range(len(data)):
            data[index] = 0


def get_basic_account(token: str, connection_factory: Callable = http.client.HTTPSConnection) -> dict:
    """Call only GET /user on the fixed Basic host; do not follow redirects."""
    if not token or len(token) > MAX_SECRET_BYTES or not all(char.isalnum() or char in "._-" for char in token):
        raise RouteStop("token_pipe_invalid")
    connection = None
    try:
        connection = connection_factory(HOST, timeout=20)
        connection.request("GET", "/user", headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
        response = connection.getresponse()
        if response.status != 200:
            raise RouteStop("account_response_not_success")
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise RouteStop("account_response_too_large")
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise RouteStop("account_response_invalid")
        balance = check_free_credits(value, required_jobs=4)
        application_status = value.get("application_status")
        if application_status not in {"NOT_STARTED", "PENDING", "APPROVED", "REJECTED"}:
            raise RouteStop("account_application_status_unknown")
        # No user_id, job_names, use_case, bearer token, or raw response leaves memory.
        return {
            "status": "account_probe_pass_free_credit_capacity_only",
            "service": "HyP3 Basic",
            "remaining_free_credits": balance,
            "four_job_nominal_ceiling": 240,
            "application_status_observed_not_interpreted_as_basic_eligibility": application_status,
            "exact_s1d_job_eligibility_verified": False,
            "credential_value_recorded": False,
            "jobs_submitted": 0,
        }
    except RouteStop:
        raise
    except (OSError, ValueError):
        raise RouteStop("account_probe_failed") from None
    finally:
        if connection is not None:
            connection.close()


def main() -> int:
    try:
        require_account_probe_release()
        if sys.argv[1:] == ["--check-release"]:
            print(json.dumps({"status": "pass_account_probe_release_no_secret_read", "credential_value_recorded": False}, sort_keys=True))
            return 0
        if len(sys.argv) != 1:
            raise RouteStop("account_probe_arguments_invalid")
        token = read_owner_token(sys.stdin.buffer)
        result = get_basic_account(token)
        token = ""
        print(json.dumps(result, sort_keys=True))
        return 0
    except RouteStop as exc:
        print(json.dumps({"status": "stopped", "code": exc.code, "credential_value_recorded": False}, sort_keys=True))
        return 12
    except BaseException:
        print(json.dumps({"status": "stopped", "code": "account_probe_unexpected_failure", "credential_value_recorded": False}, sort_keys=True))
        return 20


if __name__ == "__main__":
    raise SystemExit(main())
