#!/usr/bin/env python3
"""Gated status observation and one exact after-product ZIP intake.

Pending status makes no ZIP request. A successful status reserves one append-only
download attempt before streaming; failed or partial bytes are never retried.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import shutil
import stat
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit
from uuid import uuid4

from m2_asf_hyp3_account_probe_001 import (
    HOST, MAX_SECRET_BYTES, get_earthdata_token, read_owner_credentials,
    read_owner_token,
)
from m2_asf_hyp3_rtc_after_descriptor_core_001 import (
    SOURCE_ID, inspect_after_zip_descriptor, submission_view,
)
from m2_asf_hyp3_rtc_after_transfer_core_001 import (
    promote_after_zip_no_replace, stream_after_zip_once,
)
from m2_asf_hyp3_rtc_core_001 import ROOT, RouteStop
from m2_asf_hyp3_rtc_job_status_core_001 import inspect_exact_job_status
from m2_transfer_core import TransferControlError, ensure_directory, require_safe_child


DATA_ROOT = ROOT.parent / f"{ROOT.name}-data"
SUBMISSION_REF = "m2-asf-hyp3-rtc-submit-after-partial-001/attempt-001/terminal.json"
OBSERVATION_PARENT = DATA_ROOT / "m2-asf-hyp3-rtc-observe-after-partial-001"
ATTEMPT_ROOT = DATA_ROOT / "m2-asf-hyp3-rtc-acquire-after-partial-001" / "attempt-001"
PRODUCT_DIR = DATA_ROOT / "m2-asf-hyp3-rtc-products-after-partial-001"
APPROVAL_REF = "records/source-gates/m2-asf-hyp3-rtc-partial-pair-map-001-approval.json"
APPROVAL_SHA = "7092d2c5f7e4b3f2d0c9cff22a7c0d0a44c62942746a9b73c183b3b96f08d506"
SOURCE_GATE_REF = "records/source-gates/m2-asf-hyp3-rtc-processing-source-gate-001.json"
SOURCE_GATE_SHA = "7f1af5e46f9b1cba3753383b686a68618c7694b53a4be07d612b6df6045bd8a4"
GATE_REF = "records/readiness/m2-asf-hyp3-rtc-acquire-after-partial-001-implementation-gate.json"
PREFLIGHT_REF = "records/readiness/m2-asf-hyp3-rtc-acquire-after-partial-001-preflight.json"
IMPLEMENTATION_FILES = (
    "scripts/m2_asf_hyp3_rtc_after_descriptor_core_001.py",
    "scripts/m2_asf_hyp3_rtc_after_transfer_core_001.py",
    "scripts/m2_asf_hyp3_rtc_acquire_after_partial_001.py",
    "scripts/invoke_m2_asf_hyp3_rtc_acquire_after_partial_001.ps1",
    "tests/test_m2_asf_hyp3_rtc_after_descriptor_core_001.py",
    "tests/test_m2_asf_hyp3_rtc_after_transfer_core_001.py",
    "tests/test_m2_asf_hyp3_rtc_acquire_after_partial_001.py",
)
MAX_STATUS_BYTES = 262144
MIN_FREE_MARGIN_BYTES = 1024**3


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha(path: Path) -> str:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
    except OSError:
        raise RouteStop("after_acquire_release_unavailable") from None


def _json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise RouteStop("after_acquire_release_unavailable") from None
    if not isinstance(value, dict):
        raise RouteStop("after_acquire_release_invalid")
    return value


def _write_new(path: Path, value: dict) -> None:
    try:
        with path.open("xb") as stream:
            stream.write((json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        raise RouteStop("after_acquire_receipt_collision") from None
    except OSError:
        raise RouteStop("after_acquire_receipt_write_failed") from None


def _safe_dir(path: Path) -> bool:
    try:
        return (path.is_dir() and not path.is_symlink()
                and not bool(getattr(path.stat(), "st_file_attributes", 0)
                             & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)))
    except OSError:
        return False


def require_release(root: Path = ROOT, data_root: Path = DATA_ROOT,
                    attempt_root: Path = ATTEMPT_ROOT) -> dict:
    """Check published implementation, exact submission and no-content gate."""
    submission_path = data_root / SUBMISSION_REF
    if (submission_path.is_symlink() or submission_path.parent.is_symlink()
            or submission_path.parent.parent.is_symlink()):
        raise RouteStop("after_acquire_submission_path_invalid")
    submission = _json(submission_path)
    submission_view(submission)
    gate = _json(root / GATE_REF)
    preflight = _json(root / PREFLIGHT_REF)
    approval = _json(root / APPROVAL_REF)
    source = _json(root / SOURCE_GATE_REF)
    files = gate.get("bindings", {}).get("implementation_file_sha256")
    if (
        _sha(root / APPROVAL_REF) != APPROVAL_SHA
        or _sha(root / SOURCE_GATE_REF) != SOURCE_GATE_SHA
        or approval.get("decision") != "approve"
        or approval.get("authority", {}).get("conditional_one_zip_acquisition_integrity_provenance_rights_header_and_pixel_qa") is not True
        or source.get("decision", {}).get("status") != "ready"
        or gate.get("status") != "pass_acquire_after_partial_implementation_public_ci_only"
        or gate.get("bindings", {}).get("approval_sha256") != APPROVAL_SHA
        or gate.get("bindings", {}).get("source_gate_sha256") != SOURCE_GATE_SHA
        or gate.get("bindings", {}).get("submission_terminal_sha256") != _sha(submission_path)
        or gate.get("public_ci", {}).get("conclusion") != "success"
        or not isinstance(files, dict) or set(files) != set(IMPLEMENTATION_FILES)
        or any(_sha(root / ref) != files[ref] for ref in IMPLEMENTATION_FILES)
        or preflight.get("status") != "pass_acquire_after_partial_no_content"
        or preflight.get("bindings", {}).get("implementation_gate_sha256") != _sha(root / GATE_REF)
        or preflight.get("bindings", {}).get("submission_terminal_sha256") != _sha(submission_path)
        or preflight.get("assertions", {}).get("attempt_absent") is not True
        or preflight.get("assertions", {}).get("destination_collision_absent") is not True
        or preflight.get("assertions", {}).get("no_secret_or_status_or_zip_request") is not True
        or not _safe_dir(data_root)
        or attempt_root.parent.parent.resolve() != data_root.resolve()
        or attempt_root.exists() or attempt_root.is_symlink()
        or attempt_root.parent.is_symlink()
        or PRODUCT_DIR.is_symlink()
    ):
        raise RouteStop("after_acquire_not_released")
    return submission


def get_after_status(token: str, submission: dict,
                     connection_factory: Callable = http.client.HTTPSConnection) -> tuple[dict, dict]:
    """One exact GET. Private reply stays in memory; public view has no URLs."""
    view = submission_view(submission)
    if not token or len(token) > MAX_SECRET_BYTES or not all(c.isalnum() or c in "._-" for c in token):
        raise RouteStop("after_acquire_token_invalid")
    connection = None
    try:
        connection = connection_factory(HOST, timeout=30)
        connection.request("GET", f"/jobs/{view['job_id']}",
                           headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
        response = connection.getresponse()
        if response.status != 200:
            raise RouteStop("after_acquire_status_response_invalid")
        raw = response.read(MAX_STATUS_BYTES + 1)
        if len(raw) > MAX_STATUS_BYTES:
            raise RouteStop("after_acquire_status_response_too_large")
        reply = json.loads(raw)
        if not isinstance(reply, dict):
            raise RouteStop("after_acquire_status_shape_invalid")
        return reply, inspect_exact_job_status(reply, view, SOURCE_ID)
    except RouteStop:
        raise
    except Exception:
        raise RouteStop("after_acquire_status_request_failed") from None
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass


def transfer_after_once(private: dict, controlled_root: Path, staging: Path,
                        destination: Path,
                        connection_factory: Callable = http.client.HTTPSConnection) -> dict:
    """One URL-bound HTTPS GET, exact stream/ZIP check, no-replace promotion."""
    if not isinstance(private, dict) or private.get("source_id") != SOURCE_ID:
        raise RouteStop("after_acquire_descriptor_invalid")
    try:
        parsed = urlsplit(private["url"])
        host, port = parsed.hostname, parsed.port
    except (KeyError, TypeError, ValueError):
        raise RouteStop("after_acquire_url_invalid") from None
    if (
        parsed.scheme != "https" or not host
        or parsed.path != f"/{private.get('job_id')}/{private.get('filename')}"
        or parsed.query or parsed.fragment or parsed.username or parsed.password
        or port not in (None, 443)
        or destination.name != private.get("filename")
        or type(private.get("size_bytes")) is not int
        or not 0 < private["size_bytes"] <= 100 * 1024**3
    ):
        raise RouteStop("after_acquire_url_invalid")
    # The descriptor guard already restricted the hostname; enforce it again
    # immediately before the request, against a mutated private object.
    from m2_asf_hyp3_rtc_download_core_001 import CLOUDFRONT_HOST, S3_HOST
    if not (S3_HOST.fullmatch(host) or CLOUDFRONT_HOST.fullmatch(host)):
        raise RouteStop("after_acquire_url_invalid")
    size = private["size_bytes"]
    try:
        require_safe_child(controlled_root, staging)
        require_safe_child(controlled_root, destination)
        if (not _safe_dir(controlled_root) or not _safe_dir(staging.parent)
                or not _safe_dir(destination.parent)
                or staging.exists() or destination.exists()
                or staging.is_symlink() or destination.is_symlink()
                or shutil.disk_usage(controlled_root).free < size + MIN_FREE_MARGIN_BYTES):
            raise RouteStop("after_acquire_custody_preflight_failed")
    except RouteStop:
        raise
    except (OSError, TransferControlError):
        raise RouteStop("after_acquire_custody_preflight_failed") from None
    connection = None
    try:
        connection = connection_factory(host, timeout=120)
        connection.request("GET", parsed.path, headers={"Accept": "application/zip"})
        response = connection.getresponse()
        if response.status != 200:
            raise RouteStop("after_acquire_zip_response_invalid")
        if (response.getheader("Content-Length") != str(size)
                or response.getheader("Content-Encoding") not in (None, "identity")
                or response.getheader("Content-Range") is not None):
            raise RouteStop("after_acquire_zip_headers_invalid")
        staged = stream_after_zip_once(response, staging, expected_size_bytes=size)
        promoted = promote_after_zip_no_replace(staging, destination, staged)
        return {**promoted, "job_id": private["job_id"],
                "product_filename": private["filename"],
                "provider_url_recorded": False, "credentials_recorded": False}
    except RouteStop:
        raise
    except Exception:
        raise RouteStop("after_acquire_zip_request_failed") from None
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass


def observe_and_maybe_acquire(token: str, submission: dict,
                              observation_parent: Path = OBSERVATION_PARENT,
                              attempt_root: Path = ATTEMPT_ROOT,
                              product_dir: Path = PRODUCT_DIR,
                              controlled_root: Path = DATA_ROOT,
                              *, get_status: Callable = get_after_status,
                              transfer: Callable = transfer_after_once) -> dict:
    """One status observation; download only after exact SUCCEEDED response."""
    view = submission_view(submission)
    if not _safe_dir(controlled_root) or observation_parent.is_symlink():
        raise RouteStop("after_acquire_custody_root_invalid")
    try:
        ensure_directory(observation_parent, controlled_root)
        observation = observation_parent / f"observation-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}-{uuid4().hex[:12]}"
        observation.mkdir(exist_ok=False)
    except (OSError, TransferControlError):
        raise RouteStop("after_acquire_observation_reservation_failed") from None
    _write_new(observation / "started.json", {
        "status": "status_request_reserved", "source_id": SOURCE_ID,
        "job_id": view["job_id"], "at_utc": _now(), "credentials_recorded": False,
    })
    try:
        reply, status = get_status(token, submission)
        if status.get("source_id") != SOURCE_ID or status.get("job_id") != view["job_id"]:
            raise RouteStop("after_acquire_status_identity_invalid")
    except RouteStop as exc:
        result = {"status": "status_observation_stopped_no_zip_request", "source_id": SOURCE_ID,
                  "job_id": view["job_id"], "code": exc.code,
                  "zip_request_performed": False, "credentials_recorded": False, "at_utc": _now()}
        _write_new(observation / "terminal.json", result)
        return result
    _write_new(observation / "terminal.json", {**status, "at_utc": _now(),
                                                "credentials_recorded": False})
    if status["disposition"] != "service_succeeded_product_unverified":
        return {**status, "zip_request_performed": False}
    if attempt_root.exists() or attempt_root.is_symlink():
        raise RouteStop("after_acquire_attempt_collision")
    private, public = inspect_after_zip_descriptor(reply, submission)
    try:
        ensure_directory(attempt_root.parent, controlled_root)
        attempt_root.mkdir(exist_ok=False)
    except (OSError, TransferControlError):
        raise RouteStop("after_acquire_attempt_reservation_failed") from None
    _write_new(attempt_root / "started.json", {
        "status": "zip_request_reserved", "source_id": SOURCE_ID,
        "job_id": view["job_id"], "at_utc": _now(),
        "credentials_recorded": False,
    })
    _write_new(attempt_root / "descriptor.json", public)
    try:
        ensure_directory(product_dir, controlled_root)
        result = transfer(private, controlled_root, attempt_root / "product.part",
                          product_dir / private["filename"])
        if (result.get("status") != "pass_local_zip_promoted_no_replace"
                or result.get("job_id") != view["job_id"]
                or result.get("product_filename") != private["filename"]):
            raise RouteStop("after_acquire_transfer_result_invalid")
        terminal = {**result, "finished_at_utc": _now(),
                    "archive_integrity_verified": True,
                    "source_granule_verified_in_readme": False,
                    "geotiff_headers_or_pixels_read": False,
                    "arcgis_map_ready": False}
    except RouteStop as exc:
        terminal = {"status": "stopped_no_automatic_retry", "source_id": SOURCE_ID,
                    "job_id": view["job_id"], "code": exc.code, "finished_at_utc": _now(),
                    "credentials_recorded": False, "archive_integrity_verified": False,
                    "pixel_qa_pass": False}
    except BaseException:
        terminal = {"status": "stopped_no_automatic_retry", "source_id": SOURCE_ID,
                    "job_id": view["job_id"], "code": "after_acquire_unexpected_failure",
                    "finished_at_utc": _now(), "credentials_recorded": False,
                    "archive_integrity_verified": False, "pixel_qa_pass": False}
    _write_new(attempt_root / "terminal.json", terminal)
    return terminal


def main() -> int:
    try:
        submission = require_release()
        if sys.argv[1:] == ["--check-release"]:
            print(json.dumps({"status": "pass_after_acquire_release_no_secret_read"}))
            return 0
        if sys.argv[1:] not in ([], ["--earthdata-credentials"]):
            raise RouteStop("after_acquire_arguments_invalid")
        if sys.argv[1:] == ["--earthdata-credentials"]:
            username, password = read_owner_credentials(sys.stdin.buffer)
            token = get_earthdata_token(username, password)
            username = password = ""
        else:
            token = read_owner_token(sys.stdin.buffer)
        result = observe_and_maybe_acquire(token, submission)
        token = ""
        print(json.dumps({key: result[key] for key in (
            "status", "disposition", "source_id", "job_id", "code",
            "archive_integrity_verified", "zip_request_performed") if key in result}, sort_keys=True))
        return 0 if (result.get("status") == "pass_local_zip_promoted_no_replace"
                     or result.get("disposition") == "service_not_terminal_observe_same_job") else 12
    except RouteStop as exc:
        print(json.dumps({"status": "stopped", "code": exc.code,
                          "credentials_recorded": False}, sort_keys=True))
        return 12
    except BaseException:
        print(json.dumps({"status": "stopped", "code": "after_acquire_unexpected_failure",
                          "credentials_recorded": False}, sort_keys=True))
        return 20


if __name__ == "__main__":
    raise SystemExit(main())
