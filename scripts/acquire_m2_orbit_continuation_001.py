#!/usr/bin/env python3
"""Run one exact source under the approved orbit continuation-001 controls."""

from __future__ import annotations

import json
import shutil
import urllib.error
import urllib.request
import uuid
from pathlib import Path, PurePosixPath
from typing import Any, Callable
from urllib.parse import urlsplit

from acquire_m2_orbit_file import verified_sentinel_custody
from m2_orbit_continuation_001_core import (
    ACTIVE_INTAKE_REF,
    ACTIVE_VERIFICATION_REF,
    DATA_ROOT,
    FINAL_PREFLIGHT_REF,
    MANIFEST_REF,
    PRESERVED_SOURCE_ID,
    ROOT,
    SECRET_REFERENCE,
    SOURCE_ORDER,
    OrbitContinuation001Error,
    _one_asset,
    load_object,
    now_utc,
    validate_preserved_m2_orb_001_bytes,
    validate_runtime_gate,
    validate_secret,
    write_new_json,
)
from m2_orbit_io_core import OrbitControlError, inspect_eof, provider_checksum_map, stream_to_exclusive_staging
from m2_transfer_core import NoRedirectHandler, TransferControlError, promote_atomic_no_replace, replace_json, require_safe_child, sha256_file


DOWNLOAD_HOST = "download.dataspace.copernicus.eu"
ATTEMPT_ROOT = DATA_ROOT / "derived/m2-orbit-continuation-001-attempts"
STAGING_ROOT = DATA_ROOT / ".intake-staging/nepal-m2-orbit-continuation-001"
PUBLIC_RECEIPT_ROOT = ROOT / "records/acquisition/orbit-attempts"


def build_attempt_id(source_id: str, started_at: str, nonce: str) -> str:
    return f"{source_id.casefold()}-continuation-001-{started_at.replace(':', '').replace('-', '').casefold()}-{nonce}"


def one_record(records: list[dict[str, Any]], key: str, value: str, code: str) -> dict[str, Any]:
    matches = [record for record in records if record.get(key) == value]
    if len(matches) != 1:
        raise OrbitContinuation001Error(code)
    return matches[0]


def validate_source_sequence(intake: dict[str, Any], source_id: str) -> dict[str, Any]:
    if source_id == PRESERVED_SOURCE_ID or source_id not in SOURCE_ORDER:
        raise OrbitContinuation001Error("continuation_source_outside_exact_release")
    validate_preserved_m2_orb_001_bytes(intake)
    position = SOURCE_ORDER.index(source_id)
    for index, expected_source in enumerate(SOURCE_ORDER):
        asset = _one_asset(intake, expected_source)
        if index < position:
            if asset.get("state") != "promoted" or len(asset.get("attempts", [])) != 1 or asset["attempts"][0].get("outcome") != "succeeded":
                raise OrbitContinuation001Error("prior_continuation_source_not_exact_success")
        else:
            if (
                asset.get("state") != "authorized"
                or asset.get("attempts") != []
                or asset.get("failure") is not None
                or any(value is not None for value in asset.get("observed", {}).values())
            ):
                raise OrbitContinuation001Error("current_or_later_continuation_source_not_fresh")
    return _one_asset(intake, source_id)


def download_headers(secret: str) -> dict[str, str]:
    validate_secret(secret)
    return {
        "Authorization": f"Bearer {secret}",
        "User-Agent": "nepal-2026-orbit-continuation-001/1.0",
        "Accept": "application/octet-stream,application/xml,text/xml,*/*",
        "Accept-Encoding": "identity",
    }


def failure_code_for(exc: BaseException, stage: str) -> str:
    if isinstance(exc, KeyboardInterrupt):
        return "orbit_continuation_001_interrupted"
    if isinstance(exc, (OrbitContinuation001Error, OrbitControlError, TransferControlError)):
        code = getattr(exc, "code", "")
        if isinstance(code, str) and code:
            return code
    if isinstance(exc, urllib.error.HTTPError):
        return "orbit_redirect_or_http_status_rejected"
    if isinstance(exc, (urllib.error.URLError, TimeoutError, ConnectionError, OSError)):
        return "orbit_provider_transport_failure"
    return f"unexpected_{stage}_failure" if stage.replace("_", "").isalnum() else "unexpected_orbit_continuation_failure"


def catalog_from_final_preflight(record: dict[str, Any]) -> dict[str, Any]:
    preflight = load_object(ROOT / FINAL_PREFLIGHT_REF)
    entries = [item for item in preflight.get("catalog_revalidation", []) if item.get("source_id") == record.get("source_id")]
    if len(entries) != 1:
        raise OrbitContinuation001Error("final_preflight_catalog_binding_missing")
    entry = entries[0]
    identity = entry.get("identity", {})
    if (
        entry.get("status") != "pass_exact_live_identity_online"
        or identity.get("provider_product_id") != record.get("provider_product_id")
        or identity.get("exact_product_name") != record.get("exact_product_name")
        or identity.get("content_length_bytes") != record.get("content_length_bytes")
        or identity.get("provider_checksums") != provider_checksum_map(record.get("provider_checksums", []))
    ):
        raise OrbitContinuation001Error("final_preflight_catalog_identity_drift")
    return {"response_sha256": entry.get("response_sha256"), "identity": identity}


def run_continuation_source(
    source_id: str,
    secret: str,
    *,
    progress: Callable[[str, str | None, int | None], None] | None = None,
    catalog_checker: Callable[[dict[str, Any]], dict[str, Any]] = catalog_from_final_preflight,
    opener_factory: Callable[..., Any] = urllib.request.build_opener,
    nonce_factory: Callable[[], str] = lambda: uuid.uuid4().hex[:8],
) -> dict[str, Any]:
    """Make at most one byte-zero request for one exact allowlisted source."""
    validate_secret(secret)
    validate_runtime_gate()
    intake_path = ROOT / ACTIVE_INTAKE_REF
    intake = load_object(intake_path)
    asset = validate_source_sequence(intake, source_id)
    manifest = load_object(ROOT / MANIFEST_REF)
    verification = load_object(ROOT / ACTIVE_VERIFICATION_REF)
    record = one_record(manifest.get("records", []), "source_id", source_id, "manifest_source_missing_or_ambiguous")
    requirement = dict(one_record(verification.get("asset_requirements", []), "source_id", source_id, "verification_source_missing_or_ambiguous"))
    requirement["maximum_osv_endpoint_tolerance_seconds"] = 1.0
    if (
        record.get("provider_product_id") != asset.get("extensions", {}).get("provider_product_id")
        or record.get("exact_product_name") != asset.get("extensions", {}).get("exact_product_name")
        or record.get("content_length_bytes") != asset.get("expected", {}).get("size_bytes")
        or requirement.get("provider_product_id") != record.get("provider_product_id")
        or requirement.get("expected_size_bytes") != record.get("content_length_bytes")
    ):
        raise OrbitContinuation001Error("continuation_source_control_binding_drift")
    sentinel_custody = verified_sentinel_custody(record)
    source_uri = asset.get("source", {}).get("uri", "")
    parsed = urlsplit(source_uri)
    if (
        parsed.scheme != "https"
        or parsed.hostname != DOWNLOAD_HOST
        or parsed.query
        or parsed.fragment
        or source_uri != record.get("download_url")
    ):
        raise OrbitContinuation001Error("continuation_download_route_outside_reviewed_boundary")
    custody_root = (ROOT.parent / Path(*PurePosixPath(str(intake["custody_root"])).parts)).resolve(strict=True)
    destination = require_safe_child(custody_root, custody_root / Path(*PurePosixPath(asset["destination_relative_path"]).parts))
    staging_parent = STAGING_ROOT / f"{asset['asset_id']}-continuation-001"
    staging = staging_parent / f"{record['exact_product_name']}.part"
    started_at = now_utc()
    nonce = nonce_factory()
    if not isinstance(nonce, str) or len(nonce) != 8 or any(character not in "0123456789abcdef" for character in nonce):
        raise OrbitContinuation001Error("continuation_attempt_nonce_invalid")
    attempt_id = build_attempt_id(source_id, started_at, nonce)
    events_root = ATTEMPT_ROOT / attempt_id
    receipt_path = PUBLIC_RECEIPT_ROOT / f"{attempt_id}.json"
    if destination.exists() or staging.exists() or staging_parent.exists() or events_root.exists() or receipt_path.exists():
        raise OrbitContinuation001Error("continuation_destination_staging_or_evidence_collision")
    expected_size = int(record["content_length_bytes"])
    if shutil.disk_usage(ROOT.parent).free < expected_size * 10:
        raise OrbitContinuation001Error("free_space_below_orbit_continuation_requirement")
    stage = "predeclared_event_storage"
    catalog_response_sha256: str | None = None
    intake_attempt_recorded = False
    try:
        events_root.mkdir(parents=True, exist_ok=False)
        started_event = {
            "schema_version": "1.0",
            "event": "orbit_continuation_001_started",
            "continuation_id": "M2-ORBIT-CONTINUATION-001",
            "attempt_id": attempt_id,
            "source_id": source_id,
            "started_at": started_at,
            "source_uri": source_uri,
            "verified_sentinel_custody": sentinel_custody,
            "planned_staging_path": str(staging),
            "planned_destination_path": str(destination),
            "restart_offset_bytes": 0,
            "range_or_resume_used": False,
            "maximum_osv_endpoint_tolerance_seconds": 1.0,
            "credential_reference": SECRET_REFERENCE,
            "credential_value_recorded": False,
        }
        write_new_json(events_root / f"{attempt_id}-started.json", started_event)
        asset["attempts"].append({
            "attempt_id": attempt_id,
            "started_at": started_at,
            "completed_at": None,
            "outcome": "started",
            "extensions": {
                "source_id": source_id,
                "continuation_id": "M2-ORBIT-CONTINUATION-001",
                "external_started_event": str(events_root / f"{attempt_id}-started.json"),
                "credential_reference": SECRET_REFERENCE,
                "credential_value_recorded": False,
                "restart_offset_bytes": 0,
                "range_or_resume_used": False,
                "maximum_osv_endpoint_tolerance_seconds": 1.0,
            },
        })
        asset["state"] = "staging"
        intake["extensions"]["status"] = "active_orbit_continuation_001_in_progress"
        replace_json(intake_path, intake, f".{attempt_id}.started-tmp")
        intake_attempt_recorded = True
        if progress:
            progress("validated_preflight_catalog_binding", attempt_id, 0)
        stage = "validated_preflight_catalog_binding"
        catalog = catalog_checker(record)
        catalog_response_sha256 = str(catalog["response_sha256"])
        write_new_json(events_root / f"{attempt_id}-catalog-preflight-bound.json", {
            "schema_version": "1.0",
            "event": "orbit_continuation_001_catalog_preflight_binding_validated",
            "attempt_id": attempt_id,
            "source_id": source_id,
            "observed_at": now_utc(),
            "catalog_response_sha256": catalog_response_sha256,
            "credential_reference": SECRET_REFERENCE,
            "credential_value_recorded": False,
        })
        refreshed = load_object(intake_path)
        refreshed_asset = _one_asset(refreshed, source_id)
        refreshed_asset["attempts"][0]["extensions"]["catalog_response_sha256"] = catalog_response_sha256
        refreshed_asset["attempts"][0]["extensions"]["verified_sentinel_custody"] = sentinel_custody
        replace_json(intake_path, refreshed, f".{attempt_id}.catalog-tmp")
        stage = "staging_parent_setup"
        staging_parent.mkdir(parents=True, exist_ok=False)
        checksums = provider_checksum_map(record["provider_checksums"])
        if progress:
            progress("authenticated_byte_zero_transfer", attempt_id, 0)
        stage = "authenticated_byte_zero_transfer"
        request = urllib.request.Request(source_uri, headers=download_headers(secret))
        opener = opener_factory(NoRedirectHandler())
        with opener.open(request, timeout=120) as response:
            if int(response.status) != 200 or response.geturl() != source_uri:
                raise OrbitControlError("orbit_download_response_identity_drift")
            content_length = response.headers.get("Content-Length")
            if content_length is None or int(content_length) != expected_size:
                raise OrbitControlError("orbit_download_content_length_mismatch")
            if "text/html" in (response.headers.get("Content-Type") or "").casefold():
                raise OrbitControlError("unexpected_html_payload")
            transferred = stream_to_exclusive_staging(
                response,
                staging,
                expected_size=expected_size,
                expected_md5=checksums["MD5"],
                expected_blake3=checksums["BLAKE3"],
            )
        if progress:
            progress("staged_orbit_validation", attempt_id, transferred["size_bytes"])
        stage = "staged_orbit_validation"
        staged_validation = inspect_eof(staging, requirement, logical_name=record["exact_product_name"])
        stage = "no_replace_promotion"
        promoted = promote_atomic_no_replace(staging, destination)
        if promoted["sha256"] != transferred["sha256"] or promoted["size_bytes"] != transferred["size_bytes"]:
            raise OrbitControlError("promoted_orbit_identity_differs_from_staged")
        completed_at = now_utc()
        success = {
            "schema_version": "1.0",
            "event": "orbit_continuation_001_succeeded",
            "continuation_id": "M2-ORBIT-CONTINUATION-001",
            "attempt_id": attempt_id,
            "source_id": source_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "catalog_response_sha256": catalog_response_sha256,
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
            "retry_automatically_authorized": False,
        }
        terminal_path = events_root / f"{attempt_id}-succeeded.json"
        write_new_json(terminal_path, success)
        write_new_json(receipt_path, success)
        refreshed = load_object(intake_path)
        refreshed_asset = _one_asset(refreshed, source_id)
        refreshed_attempt = one_record(refreshed_asset["attempts"], "attempt_id", attempt_id, "started_attempt_missing_after_transfer")
        refreshed_attempt.update({"completed_at": completed_at, "outcome": "succeeded"})
        refreshed_attempt["extensions"]["external_terminal_event"] = str(terminal_path)
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
            "maximum_osv_endpoint_tolerance_seconds": 1.0,
        })
        counts = {state: sum(1 for item in refreshed["assets"] if item.get("state") == state) for state in ("authorized", "failed", "promoted")}
        refreshed["extensions"]["current_orbit_state_counts"] = counts
        replace_json(intake_path, refreshed, f".{attempt_id}.succeeded-tmp")
        refreshed_verification = load_object(ROOT / ACTIVE_VERIFICATION_REF)
        refreshed_verification["status"] = "active_gate_ready_for_offline_verification"
        refreshed_verification["bindings"]["active_intake_sha256_current"] = sha256_file(intake_path)
        refreshed_verification["bindings"]["latest_promoted_source_id"] = source_id
        replace_json(ROOT / ACTIVE_VERIFICATION_REF, refreshed_verification, f".{attempt_id}.ready-tmp")
        if progress:
            progress("promoted_and_input_verified", attempt_id, promoted["size_bytes"])
        return {
            "returncode": 0,
            "status": "promoted_and_input_verified",
            "source_id": source_id,
            "attempt_id": attempt_id,
            "size_bytes": promoted["size_bytes"],
            "sha256": promoted["sha256"],
            "receipt": str(receipt_path.relative_to(ROOT)).replace("\\", "/"),
            "credential_value_recorded": False,
        }
    except BaseException as exc:
        completed_at = now_utc()
        failure_code = failure_code_for(exc, stage)
        partial_bytes = staging.stat().st_size if staging.exists() and staging.is_file() else 0
        failure = {
            "schema_version": "1.0",
            "event": "orbit_continuation_001_failed",
            "continuation_id": "M2-ORBIT-CONTINUATION-001",
            "attempt_id": attempt_id,
            "source_id": source_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "failure_code": failure_code,
            "last_stage": stage,
            "partial_bytes_preserved": partial_bytes,
            "catalog_response_sha256": catalog_response_sha256,
            "credential_reference": SECRET_REFERENCE,
            "credential_value_recorded": False,
            "retry_automatically_authorized": False,
        }
        terminal_path = events_root / f"{attempt_id}-failed.json"
        terminal_written = False
        receipt_written = False
        try:
            if events_root.is_dir():
                write_new_json(terminal_path, failure)
                terminal_written = True
        except BaseException:
            pass
        try:
            write_new_json(receipt_path, failure)
            receipt_written = True
        except BaseException:
            pass
        if intake_attempt_recorded:
            try:
                refreshed = load_object(intake_path)
                refreshed_asset = _one_asset(refreshed, source_id)
                refreshed_attempt = one_record(refreshed_asset["attempts"], "attempt_id", attempt_id, "started_attempt_missing_after_failure")
                refreshed_attempt.update({"completed_at": completed_at, "outcome": "failed"})
                refreshed_attempt["extensions"]["external_terminal_event"] = str(terminal_path) if terminal_written else None
                refreshed_asset["state"] = "failed"
                refreshed_asset["failure"] = {"code": failure_code, "recorded_at": completed_at}
                counts = {state: sum(1 for item in refreshed["assets"] if item.get("state") == state) for state in ("authorized", "failed", "promoted")}
                refreshed["extensions"]["current_orbit_state_counts"] = counts
                refreshed["extensions"]["status"] = "terminal_orbit_continuation_001_failure_no_retry"
                replace_json(intake_path, refreshed, f".{attempt_id}.failed-tmp")
            except BaseException:
                pass
        if progress:
            progress("terminal_failure_no_retry", attempt_id, partial_bytes)
        return {
            "returncode": 20,
            "status": "failed_preserved",
            "source_id": source_id,
            "attempt_id": attempt_id,
            "failure_code": failure_code,
            "partial_bytes_preserved": partial_bytes,
            "external_terminal_evidence_written": terminal_written,
            "public_receipt_written": receipt_written,
            "receipt": str(receipt_path.relative_to(ROOT)).replace("\\", "/") if receipt_written else None,
            "credential_value_recorded": False,
        }


if __name__ == "__main__":
    raise SystemExit("This module accepts credentials only from the detached orbit continuation supervisor in memory.")
