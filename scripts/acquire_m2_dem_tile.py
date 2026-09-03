#!/usr/bin/env python3
"""Acquire one exact approved DEM tile through anonymous fail-closed intake."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO
from urllib.parse import urlsplit

from m2_transfer_core import (
    NoRedirectHandler,
    TransferControlError,
    ensure_directory,
    promote_atomic_no_replace,
    replace_json,
    require_safe_child,
    sha256_file,
    write_new_json,
)


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent.resolve()
INTAKE_PATH = ROOT / "contracts/m2-dem-intake.json"
VERIFICATION_PATH = ROOT / "contracts/m2-dem-offline-verification.json"
MILESTONE_PATH = ROOT / "contracts/milestone-002.json"
APPROVAL_PATH = ROOT / "records/source-gates/m2-dem-amendment-approval.json"
PREFLIGHT_PATH = ROOT / "records/acquisition/dem-preflight.json"
SOURCE_GATE_PATH = ROOT / "records/source-gates/m2-dem-live-source-gate.json"
CUSTODY_RECEIPT_PATH = ROOT / "records/acquisition/dem-custody-initialization.json"
MANIFEST_PATH = ROOT / "records/source-gates/m2-dem-candidate-manifest.json"
DOWNLOAD_HOST = "copernicus-dem-30m.s3.eu-central-1.amazonaws.com"
EXPECTED_SOURCE_IDS = ["M2-DEM-001", "M2-DEM-002", "M2-DEM-003", "M2-DEM-004"]


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TransferControlError("control_root_not_object")
    return value


def stream_sha256_to_exclusive_staging(source: BinaryIO, staging_path: Path, *, expected_size: int, chunk_size: int = 8 * 1024 * 1024) -> dict[str, Any]:
    if staging_path.exists():
        raise TransferControlError("staging_collision")
    digest = hashlib.sha256()
    size = 0
    with staging_path.open("xb") as handle:
        while True:
            block = source.read(chunk_size)
            if not block:
                break
            handle.write(block)
            digest.update(block)
            size += len(block)
        handle.flush()
        os.fsync(handle.fileno())
    result = {"size_bytes": size, "sha256": digest.hexdigest()}
    if size != expected_size:
        raise TransferControlError("transferred_size_mismatch")
    return result


def normalized_headers(headers: Any) -> dict[str, str]:
    return {str(key).casefold(): str(value) for key, value in headers.items()}


def remote_identity_checks(asset: dict[str, Any], *, status: int, resolved_url: str, headers: dict[str, str], body_size: int) -> dict[str, bool]:
    extensions = asset["extensions"]
    expected_size = int(asset["expected"]["size_bytes"])
    return {
        "http_200": status == 200,
        "exact_url_no_redirect": resolved_url == asset["source"]["uri"],
        "head_body_empty": body_size == 0,
        "content_length_match": int(headers.get("content-length", "-1")) == expected_size,
        "content_type_tiff": headers.get("content-type", "").split(";", 1)[0].casefold() == "image/tiff",
        "etag_match": headers.get("etag", "").strip('"') == extensions["remote_etag_metadata"],
        "last_modified_match": headers.get("last-modified") == extensions["remote_last_modified_metadata"],
        "accept_ranges_bytes": headers.get("accept-ranges", "").casefold() == "bytes",
        "no_requester_charge": "x-amz-request-charged" not in headers,
    }


def anonymous_head(asset: dict[str, Any]) -> dict[str, Any]:
    uri = asset["source"]["uri"]
    opener = urllib.request.build_opener(NoRedirectHandler())
    request = urllib.request.Request(uri, method="HEAD", headers={"User-Agent": "nepal-2026-dem-intake/1.0", "Accept": "image/tiff,*/*"})
    try:
        with opener.open(request, timeout=60) as response:
            body = response.read()
            headers = normalized_headers(response.headers)
            status = int(response.status)
            resolved = response.geturl()
    except urllib.error.HTTPError as exc:
        if 300 <= exc.code < 400:
            raise TransferControlError("redirect_refused") from exc
        raise TransferControlError("remote_head_http_failure") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise TransferControlError("remote_head_unavailable") from exc
    checks = remote_identity_checks(asset, status=status, resolved_url=resolved, headers=headers, body_size=len(body))
    if not all(checks.values()):
        raise TransferControlError("remote_identity_drift")
    return {
        "status_code": status,
        "resolved_url": resolved,
        "content_length_bytes": int(headers["content-length"]),
        "content_type": headers.get("content-type"),
        "etag": headers.get("etag", "").strip('"'),
        "last_modified": headers.get("last-modified"),
        "accept_ranges": headers.get("accept-ranges"),
        "response_body_bytes": len(body),
        "checks": checks,
    }


def set_attempt_terminal(intake: dict[str, Any], asset_id: str, attempt_id: str, completed_at: str, *, outcome: str, failure_code: str | None) -> dict[str, Any]:
    asset = next(item for item in intake["assets"] if item["asset_id"] == asset_id)
    attempt = next(item for item in asset["attempts"] if item["attempt_id"] == attempt_id)
    attempt["completed_at"] = completed_at
    attempt["outcome"] = outcome
    if outcome == "failed":
        asset["state"] = "failed"
        asset["failure"] = {"code": failure_code, "recorded_at": completed_at}
    return asset


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", required=True, choices=EXPECTED_SOURCE_IDS)
    args = parser.parse_args()

    intake = load(INTAKE_PATH)
    verification = load(VERIFICATION_PATH)
    milestone = load(MILESTONE_PATH)
    approval = load(APPROVAL_PATH)
    preflight = load(PREFLIGHT_PATH)
    source_gate = load(SOURCE_GATE_PATH)
    custody_receipt = load(CUSTODY_RECEIPT_PATH)
    manifest = load(MANIFEST_PATH)
    if approval.get("status") != "approved" or approval.get("authorized_source_ids") != EXPECTED_SOURCE_IDS:
        raise TransferControlError("dem_authority_inactive_or_drifted")
    if preflight.get("status") != "pass_no_payload_no_external_mutation" or source_gate.get("decision", {}).get("status") != "ready":
        raise TransferControlError("dem_preflight_not_passing")
    if preflight.get("source_gate", {}).get("sha256") != sha256_file(SOURCE_GATE_PATH):
        raise TransferControlError("dem_preflight_source_gate_binding_drift")
    if custody_receipt.get("status") != "created_and_verified_empty" or intake.get("extensions", {}).get("custody_initialization_sha256") != sha256_file(CUSTODY_RECEIPT_PATH):
        raise TransferControlError("dem_custody_not_initialized")
    if intake.get("extensions", {}).get("preflight_sha256") != sha256_file(PREFLIGHT_PATH):
        raise TransferControlError("dem_intake_preflight_binding_drift")
    if verification.get("inputs", {}).get("intake_contract_sha256") != sha256_file(INTAKE_PATH):
        raise TransferControlError("dem_verification_intake_binding_drift")
    units = {unit["id"]: unit for unit in milestone.get("units", [])}
    if units.get("M2-DEM-ACQUIRE", {}).get("status") != "ready" or units.get("M2-DEM-PREFLIGHT", {}).get("disposition") != "pass":
        raise TransferControlError("dem_acquisition_unit_not_ready")
    if any(asset.get("state") == "staging" for asset in intake.get("assets", [])):
        raise TransferControlError("another_dem_transfer_is_active")
    matching_assets = [asset for asset in intake.get("assets", []) if asset.get("extensions", {}).get("source_id") == args.source_id]
    matching_manifest = [record for record in manifest.get("records", []) if record.get("source_id") == args.source_id]
    if len(matching_assets) != 1 or len(matching_manifest) != 1:
        raise TransferControlError("source_id_not_exactly_approved_once")
    asset = matching_assets[0]
    manifest_record = matching_manifest[0]
    if asset.get("state") != "authorized" or asset.get("attempts") != []:
        raise TransferControlError("asset_not_fresh_authorized")
    source_uri = asset["source"]["uri"]
    parsed = urlsplit(source_uri)
    if parsed.scheme != "https" or parsed.hostname != DOWNLOAD_HOST or parsed.query or parsed.fragment or source_uri != manifest_record["anonymous_https_url"]:
        raise TransferControlError("download_route_outside_reviewed_boundary")
    if asset["extensions"]["item_id"] != manifest_record["item_id"] or asset["expected"]["size_bytes"] != manifest_record["anonymous_head"]["content_length_bytes"]:
        raise TransferControlError("intake_manifest_identity_drift")

    custody_root = (PROJECT_ROOT / Path(*PurePosixPath(intake["custody_root"]).parts)).resolve(strict=True)
    staging_root = (PROJECT_ROOT / Path(*PurePosixPath(intake["staging_root"]).parts)).resolve(strict=True)
    destination = require_safe_child(custody_root, custody_root / Path(*PurePosixPath(asset["destination_relative_path"]).parts))
    staging = require_safe_child(staging_root, staging_root / Path(*PurePosixPath(asset["staging_relative_path"]).parts))
    if destination.exists() or staging.exists():
        raise TransferControlError("destination_or_staging_collision")
    expected_size = int(asset["expected"]["size_bytes"])
    if shutil.disk_usage(PROJECT_ROOT).free < expected_size * 2:
        raise TransferControlError("free_space_below_staging_and_promotion_requirement")
    head = anonymous_head(asset)

    ensure_directory(staging.parent, staging_root)
    ensure_directory(destination.parent, custody_root)
    events_root = staging_root / "attempt-events" / asset["asset_id"]
    ensure_directory(events_root, staging_root)
    started_at = now_utc()
    attempt_id = f"{asset['asset_id']}-{started_at.replace(':', '').replace('-', '')}-{uuid.uuid4().hex[:8]}"
    started_event_path = events_root / f"{attempt_id}-started.json"
    started_event = {
        "schema_version": "1.0",
        "event": "dem_transfer_started",
        "attempt_id": attempt_id,
        "asset_id": asset["asset_id"],
        "source_id": args.source_id,
        "started_at": started_at,
        "source_uri": source_uri,
        "preflight_sha256": sha256_file(PREFLIGHT_PATH),
        "remote_head": head,
        "anonymous_access": True,
        "credential_or_account_used": False,
        "resume": False,
        "staging_path": str(staging),
        "destination_path": str(destination),
    }
    write_new_json(started_event_path, started_event)
    asset["attempts"].append({
        "attempt_id": attempt_id,
        "started_at": started_at,
        "completed_at": None,
        "outcome": "started",
        "extensions": {"source_id": args.source_id, "preflight_sha256": sha256_file(PREFLIGHT_PATH), "external_started_event": str(started_event_path), "anonymous_access": True, "credential_or_account_used": False, "resume": False},
    })
    asset["state"] = "staging"
    replace_json(INTAKE_PATH, intake, f".{attempt_id}.started-tmp")

    try:
        opener = urllib.request.build_opener(NoRedirectHandler())
        request = urllib.request.Request(source_uri, headers={"User-Agent": "nepal-2026-dem-intake/1.0", "Accept": "image/tiff,*/*", "Accept-Encoding": "identity"})
        with opener.open(request, timeout=180) as response:
            headers = normalized_headers(response.headers)
            if response.status != 200 or response.geturl() != source_uri:
                raise TransferControlError("download_response_identity_drift")
            if int(headers.get("content-length", "-1")) != expected_size:
                raise TransferControlError("download_content_length_mismatch")
            if headers.get("content-type", "").split(";", 1)[0].casefold() != "image/tiff":
                raise TransferControlError("unexpected_payload_content_type")
            if headers.get("etag", "").strip('"') != head["etag"] or headers.get("last-modified") != head["last_modified"]:
                raise TransferControlError("download_remote_identity_drift")
            staged = stream_sha256_to_exclusive_staging(response, staging, expected_size=expected_size)
        promoted = promote_atomic_no_replace(staging, destination)
        if promoted != staged:
            raise TransferControlError("promoted_identity_differs_from_staged")
        completed_at = now_utc()
        terminal_event = {
            "schema_version": "1.0",
            "event": "dem_transfer_succeeded",
            "attempt_id": attempt_id,
            "asset_id": asset["asset_id"],
            "source_id": args.source_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "source_uri": source_uri,
            "preflight_sha256": sha256_file(PREFLIGHT_PATH),
            "remote_head": head,
            "local_sha256": promoted["sha256"],
            "local_size_bytes": promoted["size_bytes"],
            "destination_path": str(destination),
            "anonymous_access": True,
            "credential_or_account_used": False,
            "provider_checksum_available": False,
            "geotiff_verification_status": "pending",
        }
        terminal_path = events_root / f"{attempt_id}-succeeded.json"
        write_new_json(terminal_path, terminal_event)
        public_receipt = ROOT / "records" / "acquisition" / "dem-attempts" / f"{attempt_id}.json"
        write_new_json(public_receipt, terminal_event)
        refreshed = load(INTAKE_PATH)
        refreshed_asset = set_attempt_terminal(refreshed, asset["asset_id"], attempt_id, completed_at, outcome="succeeded", failure_code=None)
        refreshed_asset["state"] = "promoted"
        refreshed_asset["observed"].update({"staged_sha256": staged["sha256"], "staged_size_bytes": staged["size_bytes"], "promoted_sha256": promoted["sha256"], "promoted_size_bytes": promoted["size_bytes"]})
        refreshed_asset["extensions"].update({"successful_attempt_receipt": str(public_receipt.relative_to(ROOT)).replace("\\", "/"), "successful_attempt_receipt_sha256": sha256_file(public_receipt), "provider_checksum_available": False, "geotiff_verification_status": "pending"})
        replace_json(INTAKE_PATH, refreshed, f".{attempt_id}.succeeded-tmp")
        print(json.dumps({"status": "promoted_pending_geotiff_verification", "source_id": args.source_id, "attempt_id": attempt_id, "size_bytes": promoted["size_bytes"], "sha256": promoted["sha256"], "receipt": str(public_receipt.relative_to(ROOT)).replace("\\", "/"), "credential_or_account_used": False}, indent=2))
        return 0
    except BaseException as exc:
        completed_at = now_utc()
        if isinstance(exc, TransferControlError):
            failure_code = exc.code
        elif isinstance(exc, urllib.error.HTTPError):
            failure_code = "redirect_or_http_status_rejected"
        elif isinstance(exc, (urllib.error.URLError, TimeoutError, ConnectionError, OSError)):
            failure_code = "provider_transport_failure"
        else:
            failure_code = "unexpected_transfer_failure"
        terminal_event = {
            "schema_version": "1.0",
            "event": "dem_transfer_failed",
            "attempt_id": attempt_id,
            "asset_id": asset["asset_id"],
            "source_id": args.source_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "failure_code": failure_code,
            "partial_bytes_preserved": staging.stat().st_size if staging.exists() else 0,
            "anonymous_access": True,
            "credential_or_account_used": False,
            "retry_automatically_authorized": False,
        }
        terminal_path = events_root / f"{attempt_id}-failed.json"
        write_new_json(terminal_path, terminal_event)
        public_receipt = ROOT / "records" / "acquisition" / "dem-attempts" / f"{attempt_id}.json"
        write_new_json(public_receipt, terminal_event)
        refreshed = load(INTAKE_PATH)
        set_attempt_terminal(refreshed, asset["asset_id"], attempt_id, completed_at, outcome="failed", failure_code=failure_code)
        replace_json(INTAKE_PATH, refreshed, f".{attempt_id}.failed-tmp")
        print(json.dumps({"status": "failed_preserved", "source_id": args.source_id, "attempt_id": attempt_id, "failure_code": failure_code, "partial_bytes_preserved": terminal_event["partial_bytes_preserved"], "receipt": str(public_receipt.relative_to(ROOT)).replace("\\", "/"), "credential_or_account_used": False}, indent=2))
        return 20


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except TransferControlError as exc:
        print(json.dumps({"status": "stopped", "code": exc.code, "mutations_performed": False}, indent=2))
        raise SystemExit(12)
