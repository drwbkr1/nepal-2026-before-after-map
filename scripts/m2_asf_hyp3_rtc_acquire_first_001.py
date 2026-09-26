#!/usr/bin/env python3
"""Gated, single-attempt acquisition of the first exact HyP3 RTC ZIP.

This worker does not submit a job, retry a request, or decode a raster. It
reserves a non-Git attempt before the authenticated status GET and writes only
URL-free, credential-free append-only receipts.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from m2_asf_hyp3_account_probe_001 import (
    get_earthdata_token, read_owner_credentials, read_owner_token,
)
from m2_asf_hyp3_rtc_core_001 import (
    APPROVAL_REF, ORDER, ROOT, RouteStop, load_approved_jobs, one_job_payload,
)
from m2_asf_hyp3_rtc_http_transfer_001 import (
    fetch_first_descriptor_once, transfer_first_zip_once,
)
from m2_transfer_core import TransferControlError, ensure_directory


SOURCE_ID = ORDER[0]
EXACT_JOB_ID = "dad53076-78fc-42e8-a58e-ad17efb88a7e"
DATA_ROOT = ROOT.parent / f"{ROOT.name}-data"
SUBMISSION_REF = "m2-asf-hyp3-rtc-submit-first-001/attempt-001/terminal.json"
ATTEMPT_ROOT = DATA_ROOT / "m2-asf-hyp3-rtc-acquire-first-001" / "attempt-001"
PRODUCT_DIR = DATA_ROOT / "m2-asf-hyp3-rtc-products-001"
SOURCE_GATE_REF = "records/source-gates/m2-asf-hyp3-rtc-processing-source-gate-001.json"
GATE_REF = "records/readiness/m2-asf-hyp3-rtc-acquire-first-implementation-gate-002.json"
PREFLIGHT_REF = "records/readiness/m2-asf-hyp3-rtc-acquire-first-execution-preflight-001.json"
IMPLEMENTATION_FILES = (
    "scripts/m2_asf_hyp3_rtc_http_transfer_001.py",
    "scripts/m2_asf_hyp3_rtc_acquire_first_001.py",
    "scripts/invoke_m2_asf_hyp3_rtc_acquire_first_001.ps1",
    "scripts/m2_asf_hyp3_rtc_transfer_core_001.py",
    "tests/test_m2_asf_hyp3_rtc_zip_core_001.py",
)


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise RouteStop("rtc_acquire_release_unavailable") from None
    if not isinstance(value, dict):
        raise RouteStop("rtc_acquire_release_invalid")
    return value


def _sha(path: Path) -> str:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
    except OSError:
        raise RouteStop("rtc_acquire_release_unavailable") from None


def _safe_directory(path: Path) -> bool:
    try:
        return (
            path.is_dir() and not path.is_symlink()
            and not bool(getattr(path.stat(), "st_file_attributes", 0)
                         & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
        )
    except OSError:
        return False


def require_acquisition_release(
    root: Path = ROOT, data_root: Path = DATA_ROOT,
    attempt_root: Path = ATTEMPT_ROOT,
) -> dict:
    """Check exact approved job and published implementation before stdin."""
    gate = _read_json(root / GATE_REF)
    preflight = _read_json(root / PREFLIGHT_REF)
    source = _read_json(root / SOURCE_GATE_REF)
    submission_path = data_root / SUBMISSION_REF
    if (
        submission_path.is_symlink() or submission_path.parent.is_symlink()
        or submission_path.parent.parent.is_symlink()
    ):
        raise RouteStop("rtc_acquire_submission_path_invalid")
    submission = _read_json(submission_path)
    expected = one_job_payload(load_approved_jobs(root), SOURCE_ID)["jobs"][0]
    published = gate.get("bindings", {}).get("implementation_file_sha256")
    files_match = isinstance(published, dict) and set(published) == set(IMPLEMENTATION_FILES)
    if files_match:
        files_match = all(_sha(root / ref) == published[ref] for ref in IMPLEMENTATION_FILES)
    if (
        gate.get("status") != "pass_acquire_first_implementation_public_ci_only"
        or gate.get("public_ci", {}).get("conclusion") != "success"
        or gate.get("bindings", {}).get("approval_sha256") != _sha(root / APPROVAL_REF)
        or gate.get("bindings", {}).get("source_gate_sha256") != _sha(root / SOURCE_GATE_REF)
        or gate.get("bindings", {}).get("submission_terminal_sha256") != _sha(submission_path)
        or not files_match
        or preflight.get("status") != "pass_first_product_no_content_preflight"
        or preflight.get("bindings", {}).get("implementation_gate_sha256") != _sha(root / GATE_REF)
        or preflight.get("bindings", {}).get("submission_terminal_sha256") != _sha(submission_path)
        or preflight.get("assertions", {}).get("provider_status") != "SUCCEEDED"
        or preflight.get("assertions", {}).get("exact_job_id") != EXACT_JOB_ID
        or preflight.get("assertions", {}).get("attempt_root_absent") is not True
        or preflight.get("assertions", {}).get("destination_collision_absent") is not True
        or preflight.get("assertions", {}).get("no_network_or_pixel_read") is not True
        or source.get("decision", {}).get("status") != "ready"
        or source.get("authority", {}).get("authority_ref") != APPROVAL_REF
        or submission.get("status") != "submitted_product_unverified"
        or submission.get("source_id") != SOURCE_ID
        or submission.get("job_id") != EXACT_JOB_ID
        or any(submission.get(key) != expected[key] for key in ("name", "job_type", "job_parameters"))
        or submission.get("credentials_recorded") is not False
        or submission.get("product_bytes_verified") is not False
        or submission.get("pixel_qa_pass") is not False
        or not _safe_directory(data_root)
        or attempt_root.parent.parent.resolve() != data_root.resolve()
        or attempt_root.exists() or attempt_root.is_symlink()
        or PRODUCT_DIR.is_symlink()
    ):
        raise RouteStop("rtc_acquire_not_released")
    return submission


def _write_new_json(path: Path, value: dict) -> None:
    try:
        with path.open("xb") as stream:
            stream.write((json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        raise RouteStop("rtc_acquire_receipt_collision") from None
    except OSError:
        raise RouteStop("rtc_acquire_receipt_write_failed") from None


def acquire_first_once(
    token: str, submission: dict,
    attempt_root: Path = ATTEMPT_ROOT,
    product_dir: Path = PRODUCT_DIR,
    *,
    controlled_root: Path = DATA_ROOT,
    fetch_descriptor: Callable = fetch_first_descriptor_once,
    transfer_zip: Callable = transfer_first_zip_once,
) -> dict:
    """Reserve once, bind one successful response, and verify/promote one ZIP."""
    if submission.get("job_id") != EXACT_JOB_ID or attempt_root.exists():
        raise RouteStop("rtc_acquire_attempt_or_job_invalid")
    try:
        attempt_root.parent.mkdir(parents=True, exist_ok=True)
        attempt_root.mkdir(exist_ok=False)
    except (FileExistsError, OSError):
        raise RouteStop("rtc_acquire_attempt_reservation_failed") from None
    _write_new_json(attempt_root / "started.json", {
        "status": "request_reserved", "source_id": SOURCE_ID,
        "job_id": EXACT_JOB_ID, "started_at_utc": now_utc(),
        "method": "one_GET_status_then_one_GET_zip_if_succeeded",
        "credentials_recorded": False,
    })
    try:
        private, public = fetch_descriptor(token, submission)
        if private.get("source_id") != SOURCE_ID or private.get("job_id") != EXACT_JOB_ID:
            raise RouteStop("rtc_acquire_descriptor_identity_invalid")
        _write_new_json(attempt_root / "descriptor.json", public)
        try:
            ensure_directory(product_dir, controlled_root)
        except (OSError, TransferControlError):
            raise RouteStop("rtc_acquire_product_directory_invalid") from None
        result = transfer_zip(
            private, submission, controlled_root,
            attempt_root / "product.part", product_dir / private["filename"],
        )
        if (
            result.get("status") != "pass_local_zip_promoted_no_replace"
            or result.get("job_id") != EXACT_JOB_ID
            or result.get("product_filename") != private["filename"]
        ):
            raise RouteStop("rtc_acquire_transfer_result_invalid")
        terminal = {
            **result, "finished_at_utc": now_utc(),
            "archive_integrity_verified": True,
            "source_granule_verified_in_readme": False,
            "geotiff_headers_or_pixels_read": False,
            "arcgis_map_ready": False,
        }
    except RouteStop as exc:
        terminal = {
            "status": "stopped_no_automatic_retry", "source_id": SOURCE_ID,
            "job_id": EXACT_JOB_ID, "code": exc.code,
            "finished_at_utc": now_utc(), "credentials_recorded": False,
            "archive_integrity_verified": False, "pixel_qa_pass": False,
        }
    except Exception:
        terminal = {
            "status": "stopped_no_automatic_retry", "source_id": SOURCE_ID,
            "job_id": EXACT_JOB_ID, "code": "rtc_acquire_unexpected_failure",
            "finished_at_utc": now_utc(), "credentials_recorded": False,
            "archive_integrity_verified": False, "pixel_qa_pass": False,
        }
    _write_new_json(attempt_root / "terminal.json", terminal)
    return terminal


def main() -> int:
    try:
        submission = require_acquisition_release()
        if sys.argv[1:] == ["--check-release"]:
            print(json.dumps({"status": "pass_acquire_first_release_no_secret_read"}, sort_keys=True))
            return 0
        if sys.argv[1:] not in ([], ["--earthdata-credentials"]):
            raise RouteStop("rtc_acquire_arguments_invalid")
        if sys.argv[1:] == ["--earthdata-credentials"]:
            username, password = read_owner_credentials(sys.stdin.buffer)
            token = get_earthdata_token(username, password)
            username = password = ""
        else:
            token = read_owner_token(sys.stdin.buffer)
        result = acquire_first_once(token, submission)
        token = ""
        print(json.dumps({
            "status": result["status"], "source_id": SOURCE_ID,
            "job_id": EXACT_JOB_ID, "code": result.get("code"),
            "archive_integrity_verified": result.get("archive_integrity_verified", False),
            "pixel_qa_pass": False,
        }, sort_keys=True))
        return 0 if result["status"] == "pass_local_zip_promoted_no_replace" else 12
    except RouteStop as exc:
        print(json.dumps({"status": "stopped", "code": exc.code, "credentials_recorded": False}, sort_keys=True))
        return 12
    except BaseException:
        print(json.dumps({"status": "stopped", "code": "rtc_acquire_unexpected_failure", "credentials_recorded": False}, sort_keys=True))
        return 20


if __name__ == "__main__":
    raise SystemExit(main())
