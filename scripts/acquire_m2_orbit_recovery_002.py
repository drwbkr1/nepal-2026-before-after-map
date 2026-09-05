#!/usr/bin/env python3
"""Run the single approved byte-zero M2-ORB-001 recovery with an in-memory token."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
import uuid
from pathlib import Path, PurePosixPath
from typing import Any, Callable
from urllib.parse import urlsplit

from acquire_m2_orbit_file import public_catalog_check, verified_sentinel_custody
from m2_orbit_io_core import OrbitControlError, inspect_eof, provider_checksum_map, stream_to_exclusive_staging
from m2_orbit_recovery_002_core import (
    ACTIVE_INTAKE_REF,
    ACTIVE_VERIFICATION_REF,
    APPROVAL_REF,
    CONTRACT_REF,
    DATA_ROOT,
    EXPECTED_ATTEMPT_PREFIX,
    EXPECTED_BLAKE3,
    EXPECTED_DESTINATION_RELATIVE,
    EXPECTED_DOWNLOAD_URL,
    EXPECTED_MD5,
    EXPECTED_PRODUCT_NAME,
    EXPECTED_PROVIDER_PRODUCT_ID,
    EXPECTED_SIZE_BYTES,
    EXPECTED_SOURCE_ID,
    EXPECTED_STAGING_RELATIVE,
    EXPECTED_STAGING_ROOT,
    FINAL_PREFLIGHT_REF,
    MANIFEST_REF,
    MILESTONE_REF,
    ORIGINAL_ATTEMPT_ID,
    ORIGINAL_RECEIPT_REF,
    PUBLICATION_GATE_REF,
    RADAR_READINESS_REF,
    ROOT,
    SECRET_REFERENCE,
    OrbitRecovery002Error,
    load_object,
    now_utc,
    replace_json,
    require_exact_contract,
    require_original_failure,
    require_safe_child,
    sha256_file,
    validate_approval,
    validate_secret,
    write_new_json,
)
from m2_transfer_core import NoRedirectHandler, promote_atomic_no_replace
from record_m2_orbit_recovery_002_publication_gate import FILES as PUBLICATION_FILES


PROJECT_ROOT = ROOT.parent.resolve()
RECEIPT_ROOT = ROOT / "records/acquisition/orbit-attempts"
DOWNLOAD_HOST = "download.dataspace.copernicus.eu"


def current_git_identity() -> tuple[str, str]:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    origin = subprocess.run(["git", "rev-parse", "origin/main"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    return head, origin


def download_headers(access_value: str) -> dict[str, str]:
    validate_secret(access_value)
    return {
        "Authorization": f"Bearer {access_value}",
        "User-Agent": "nepal-2026-orbit-recovery-002/1.0",
        "Accept": "application/octet-stream,application/xml,text/xml,*/*",
        "Accept-Encoding": "identity",
    }


def build_attempt_id(started_at: str, nonce: str) -> str:
    return f"{EXPECTED_ATTEMPT_PREFIX}-{started_at.replace(':', '').replace('-', '')}-{nonce}".casefold()


def _validate_publication_gate() -> dict[str, Any]:
    gate = load_object(ROOT / PUBLICATION_GATE_REF)
    head, origin = current_git_identity()
    if (
        gate.get("status") != "pass_public_controls_verified_before_orbit_recovery_002"
        or gate.get("github_actions", {}).get("conclusion") != "success"
        or gate.get("github_actions", {}).get("head_sha") != head
        or head != origin
        or gate.get("bindings") != {key: sha256_file(path) for key, path in PUBLICATION_FILES.items()}
        or gate.get("assertions", {}).get("real_recovery_started") is not False
        or gate.get("assertions", {}).get("credential_values_read_or_recorded") is not False
    ):
        raise OrbitRecovery002Error("publication_gate_drift")
    return gate


def _single_record(container: list[dict[str, Any]], key: str, value: str, code: str) -> dict[str, Any]:
    matches = [item for item in container if item.get(key) == value]
    if len(matches) != 1:
        raise OrbitRecovery002Error(code)
    return matches[0]


def validate_preconditions(access_value: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], Path, Path]:
    validate_secret(access_value)
    validate_approval()
    _validate_publication_gate()
    contract = load_object(ROOT / CONTRACT_REF)
    require_exact_contract(contract)
    intake = load_object(ROOT / ACTIVE_INTAKE_REF)
    asset = require_original_failure(intake)
    verification = load_object(ROOT / ACTIVE_VERIFICATION_REF)
    manifest = load_object(ROOT / MANIFEST_REF)
    record = _single_record(manifest.get("records", []), "source_id", EXPECTED_SOURCE_ID, "manifest_source_absent_or_ambiguous")
    requirement = _single_record(verification.get("asset_requirements", []), "source_id", EXPECTED_SOURCE_ID, "verification_requirement_absent_or_ambiguous")
    radar = load_object(ROOT / RADAR_READINESS_REF)
    milestone = load_object(ROOT / MILESTONE_REF)
    units = {item.get("id"): item for item in milestone.get("units", [])}
    if (
        radar.get("status") != "pass_six_source_custody_materialization_and_header_readiness_only"
        or radar.get("source_ids") != [f"M1-SRC-{index:03d}" for index in range(1, 7)]
        or radar.get("assertions", {}).get("measurement_pixels_decoded") is not False
        or units.get("M2-RADAR-SOURCE-READINESS", {}).get("status") != "complete"
        or units.get("M2-ORBIT-RECOVERY-002-IMPLEMENTATION", {}).get("status") != "complete"
        or units.get("M2-ORBIT-RECOVERY-002", {}).get("status") not in {"ready", "in_progress"}
    ):
        raise OrbitRecovery002Error("milestone_or_radar_readiness_drift")
    if (
        record.get("provider_product_id") != EXPECTED_PROVIDER_PRODUCT_ID
        or record.get("exact_product_name") != EXPECTED_PRODUCT_NAME
        or record.get("download_url") != EXPECTED_DOWNLOAD_URL
        or record.get("content_length_bytes") != EXPECTED_SIZE_BYTES
        or provider_checksum_map(record.get("provider_checksums", [])) != {"MD5": EXPECTED_MD5, "BLAKE3": EXPECTED_BLAKE3}
        or requirement.get("expected_size_bytes") != EXPECTED_SIZE_BYTES
        or requirement.get("exact_product_name") != EXPECTED_PRODUCT_NAME
    ):
        raise OrbitRecovery002Error("exact_orbit_identity_drift")
    final_preflight = load_object(ROOT / FINAL_PREFLIGHT_REF)
    if (
        final_preflight.get("status") != "pass_no_payload_ready_for_single_secret_pipe_handoff"
        or final_preflight.get("bindings", {}).get("approval_sha256") != sha256_file(ROOT / APPROVAL_REF)
        or final_preflight.get("bindings", {}).get("publication_gate_sha256") != sha256_file(ROOT / PUBLICATION_GATE_REF)
        or final_preflight.get("bindings", {}).get("recovery_contract_sha256") != sha256_file(ROOT / CONTRACT_REF)
        or final_preflight.get("bindings", {}).get("active_intake_sha256") != sha256_file(ROOT / ACTIVE_INTAKE_REF)
        or final_preflight.get("assertions", {}).get("credential_values_read_or_recorded") is not False
        or final_preflight.get("assertions", {}).get("orbit_payload_requested") is not False
    ):
        raise OrbitRecovery002Error("final_no_payload_preflight_drift")
    custody_root = (PROJECT_ROOT / Path(*PurePosixPath(intake["custody_root"]).parts)).resolve(strict=True)
    staging_parent = (DATA_ROOT / ".intake-staging").resolve(strict=True)
    staging_root = (PROJECT_ROOT / Path(*PurePosixPath(EXPECTED_STAGING_ROOT).parts)).resolve(strict=False)
    destination = require_safe_child(custody_root, custody_root / Path(*PurePosixPath(EXPECTED_DESTINATION_RELATIVE).parts))
    if destination.exists() or staging_root.exists():
        raise OrbitRecovery002Error("destination_or_recovery_staging_collision")
    if shutil.disk_usage(PROJECT_ROOT).free < EXPECTED_SIZE_BYTES * 10:
        raise OrbitRecovery002Error("free_space_below_recovery_requirement")
    return intake, asset, record, requirement, destination, staging_parent


def run_recovery(
    access_value: str,
    *,
    progress: Callable[[str, str | None, int | None], None] | None = None,
    catalog_check: Callable[[dict[str, Any]], dict[str, Any]] = public_catalog_check,
    opener_factory: Callable[..., Any] = urllib.request.build_opener,
) -> dict[str, Any]:
    intake, asset, record, requirement, destination, staging_parent = validate_preconditions(access_value)
    source_uri = record["download_url"]
    parsed = urlsplit(source_uri)
    if parsed.scheme != "https" or parsed.hostname != DOWNLOAD_HOST or parsed.query or parsed.fragment or source_uri != EXPECTED_DOWNLOAD_URL:
        raise OrbitRecovery002Error("download_route_outside_reviewed_boundary")
    sentinel_custody = verified_sentinel_custody(record)
    if progress:
        progress("public_catalog_revalidation", None, 0)
    catalog = catalog_check(record)
    staging_root = DATA_ROOT / ".intake-staging" / "nepal-m2-orbit-recovery-002"
    staging_root.mkdir(parents=False, exist_ok=False)
    staging = require_safe_child(staging_root, staging_root / Path(*PurePosixPath(EXPECTED_STAGING_RELATIVE).parts))
    staging.parent.mkdir(parents=True, exist_ok=False)
    events_root = staging_root / "attempt-events" / EXPECTED_ASSET_ID
    events_root.mkdir(parents=True, exist_ok=False)
    started_at = now_utc()
    attempt_id = build_attempt_id(started_at, uuid.uuid4().hex[:8])
    receipt_path = RECEIPT_ROOT / f"{attempt_id}.json"
    if receipt_path.exists():
        raise OrbitRecovery002Error("attempt_receipt_collision")
    started_event_path = events_root / f"{attempt_id}-started.json"
    started_event = {
        "schema_version": "1.0",
        "event": "orbit_recovery_002_started",
        "attempt_id": attempt_id,
        "source_id": EXPECTED_SOURCE_ID,
        "started_at": started_at,
        "restart_offset_bytes": 0,
        "range_or_resume_used": False,
        "source_uri": source_uri,
        "catalog_response_sha256": catalog["response_sha256"],
        "verified_sentinel_custody": sentinel_custody,
        "credential_reference": SECRET_REFERENCE,
        "credential_value_recorded": False,
        "staging_path": str(staging),
        "destination_path": str(destination),
        "retained_failed_attempt_id": ORIGINAL_ATTEMPT_ID,
        "retained_failed_receipt_ref": ORIGINAL_RECEIPT_REF,
    }
    write_new_json(started_event_path, started_event)
    asset["attempts"].append({
        "attempt_id": attempt_id,
        "started_at": started_at,
        "completed_at": None,
        "outcome": "started",
        "extensions": {
            "source_id": EXPECTED_SOURCE_ID,
            "recovery_id": "M2-ORBIT-RECOVERY-002",
            "catalog_response_sha256": catalog["response_sha256"],
            "verified_sentinel_custody": sentinel_custody,
            "external_started_event": str(started_event_path),
            "credential_reference": SECRET_REFERENCE,
            "credential_value_recorded": False,
            "restart_offset_bytes": 0,
            "range_or_resume_used": False,
        },
    })
    asset["state"] = "staging"
    asset["extensions"]["retained_failed_attempt_ids"] = [ORIGINAL_ATTEMPT_ID]
    replace_json(ROOT / ACTIVE_INTAKE_REF, intake, f"{attempt_id}-started")
    if progress:
        progress("authenticated_byte_zero_transfer", attempt_id, 0)

    try:
        request = urllib.request.Request(source_uri, headers=download_headers(access_value))
        opener = opener_factory(NoRedirectHandler())
        with opener.open(request, timeout=120) as response:
            if int(response.status) != 200 or response.geturl() != source_uri:
                raise OrbitControlError("orbit_download_response_identity_drift")
            content_length = response.headers.get("Content-Length")
            if content_length is None or int(content_length) != EXPECTED_SIZE_BYTES:
                raise OrbitControlError("orbit_download_content_length_mismatch")
            if "text/html" in (response.headers.get("Content-Type") or "").casefold():
                raise OrbitControlError("unexpected_html_payload")
            transferred = stream_to_exclusive_staging(
                response,
                staging,
                expected_size=EXPECTED_SIZE_BYTES,
                expected_md5=EXPECTED_MD5,
                expected_blake3=EXPECTED_BLAKE3,
            )
        if progress:
            progress("staged_orbit_validation", attempt_id, transferred["size_bytes"])
        staged_validation = inspect_eof(staging, requirement, logical_name=EXPECTED_PRODUCT_NAME)
        promoted = promote_atomic_no_replace(staging, destination)
        if promoted["sha256"] != transferred["sha256"] or promoted["size_bytes"] != transferred["size_bytes"]:
            raise OrbitControlError("promoted_orbit_identity_differs_from_staged")
        completed_at = now_utc()
        terminal = {
            "schema_version": "1.0",
            "event": "orbit_recovery_002_succeeded",
            "attempt_id": attempt_id,
            "source_id": EXPECTED_SOURCE_ID,
            "started_at": started_at,
            "completed_at": completed_at,
            "local_size_bytes": promoted["size_bytes"],
            "local_sha256": promoted["sha256"],
            "provider_md5": transferred["md5"],
            "provider_blake3": transferred["blake3"],
            "provider_checksums_locally_verified": True,
            "staged_xml_validation": staged_validation["xml"],
            "scene_binding": staged_validation["scene_binding"],
            "destination_path": str(destination),
            "credential_reference": SECRET_REFERENCE,
            "credential_value_recorded": False,
            "retained_failed_attempt_id": ORIGINAL_ATTEMPT_ID,
            "retry_automatically_authorized": False,
        }
        terminal_path = events_root / f"{attempt_id}-succeeded.json"
        write_new_json(terminal_path, terminal)
        write_new_json(receipt_path, terminal)
        refreshed = load_object(ROOT / ACTIVE_INTAKE_REF)
        refreshed_asset = _single_record(refreshed["assets"], "asset_id", EXPECTED_ASSET_ID, "active_asset_missing_after_transfer")
        attempt = _single_record(refreshed_asset["attempts"], "attempt_id", attempt_id, "attempt_missing_after_transfer")
        attempt.update({"completed_at": completed_at, "outcome": "succeeded"})
        attempt["extensions"]["external_terminal_event"] = str(terminal_path)
        refreshed_asset["state"] = "promoted"
        refreshed_asset["failure"] = None
        refreshed_asset["observed"] = {
            "staged_sha256": transferred["sha256"],
            "staged_size_bytes": transferred["size_bytes"],
            "promoted_sha256": promoted["sha256"],
            "promoted_size_bytes": promoted["size_bytes"],
        }
        refreshed_asset["extensions"].update({
            "successful_attempt_receipt": str(receipt_path.relative_to(ROOT)).replace("\\", "/"),
            "successful_attempt_receipt_sha256": sha256_file(receipt_path),
            "provider_md5_verified": True,
            "provider_blake3_verified": True,
            "staged_xml_verification_status": "pass_orbit_input_only",
            "offline_reverification_status": "pending",
        })
        replace_json(ROOT / ACTIVE_INTAKE_REF, refreshed, f"{attempt_id}-succeeded")
        active_verification = load_object(ROOT / ACTIVE_VERIFICATION_REF)
        active_verification["status"] = "active_gate_ready_for_offline_verification"
        active_verification["bindings"]["active_intake_sha256_current"] = sha256_file(ROOT / ACTIVE_INTAKE_REF)
        active_verification["bindings"]["latest_promoted_source_id"] = EXPECTED_SOURCE_ID
        replace_json(ROOT / ACTIVE_VERIFICATION_REF, active_verification, f"{attempt_id}-ready")
        if progress:
            progress("promoted_pending_offline_reverification", attempt_id, promoted["size_bytes"])
        return {
            "returncode": 0,
            "status": "promoted_pending_offline_reverification",
            "source_id": EXPECTED_SOURCE_ID,
            "attempt_id": attempt_id,
            "size_bytes": promoted["size_bytes"],
            "sha256": promoted["sha256"],
            "receipt": str(receipt_path.relative_to(ROOT)).replace("\\", "/"),
            "credential_value_recorded": False,
        }
    except BaseException as exc:
        completed_at = now_utc()
        if isinstance(exc, (OrbitControlError, OrbitRecovery002Error)):
            failure_code = exc.code
        elif isinstance(exc, urllib.error.HTTPError):
            failure_code = "orbit_redirect_or_http_status_rejected"
        elif isinstance(exc, (urllib.error.URLError, TimeoutError, ConnectionError, OSError)):
            failure_code = "orbit_provider_transport_failure"
        else:
            failure_code = "unexpected_orbit_recovery_002_failure"
        terminal = {
            "schema_version": "1.0",
            "event": "orbit_recovery_002_failed",
            "attempt_id": attempt_id,
            "source_id": EXPECTED_SOURCE_ID,
            "started_at": started_at,
            "completed_at": completed_at,
            "failure_code": failure_code,
            "partial_bytes_preserved": staging.stat().st_size if staging.exists() else 0,
            "credential_reference": SECRET_REFERENCE,
            "credential_value_recorded": False,
            "retained_failed_attempt_id": ORIGINAL_ATTEMPT_ID,
            "retry_automatically_authorized": False,
        }
        terminal_path = events_root / f"{attempt_id}-failed.json"
        write_new_json(terminal_path, terminal)
        write_new_json(receipt_path, terminal)
        refreshed = load_object(ROOT / ACTIVE_INTAKE_REF)
        refreshed_asset = _single_record(refreshed["assets"], "asset_id", EXPECTED_ASSET_ID, "active_asset_missing_after_failure")
        attempt = _single_record(refreshed_asset["attempts"], "attempt_id", attempt_id, "attempt_missing_after_failure")
        attempt.update({"completed_at": completed_at, "outcome": "failed"})
        attempt["extensions"]["external_terminal_event"] = str(terminal_path)
        refreshed_asset["state"] = "failed"
        refreshed_asset["failure"] = {"code": failure_code, "recorded_at": completed_at}
        replace_json(ROOT / ACTIVE_INTAKE_REF, refreshed, f"{attempt_id}-failed")
        if progress:
            progress("terminal_failure_no_retry", attempt_id, terminal["partial_bytes_preserved"])
        return {
            "returncode": 20,
            "status": "failed_preserved",
            "source_id": EXPECTED_SOURCE_ID,
            "attempt_id": attempt_id,
            "failure_code": failure_code,
            "partial_bytes_preserved": terminal["partial_bytes_preserved"],
            "receipt": str(receipt_path.relative_to(ROOT)).replace("\\", "/"),
            "credential_value_recorded": False,
        }


def main() -> int:
    print(json.dumps({
        "status": "stopped",
        "code": "direct_execution_forbidden_use_anonymous_pipe_broker",
        "source_id": EXPECTED_SOURCE_ID,
        "credential_value_recorded": False,
        "mutations_performed": False,
    }, indent=2))
    return 12


if __name__ == "__main__":
    raise SystemExit(main())
