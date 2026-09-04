#!/usr/bin/env python3
"""Acquire one exact approved S1D orbit file through fail-closed intake."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlsplit

from m2_orbit_io_core import (
    OrbitControlError,
    inspect_eof,
    provider_checksum_map,
    stream_to_exclusive_staging,
)
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
APPROVAL_PATH = ROOT / "records/source-gates/m2-orbit-amendment-approval.json"
ACTIVE_INTAKE_PATH = ROOT / "contracts/m2-orbit-intake.json"
ACTIVE_VERIFICATION_PATH = ROOT / "contracts/m2-orbit-offline-verification.json"
SENTINEL_INTAKE_PATH = ROOT / "contracts/m2-intake.json"
PREFLIGHT_PATH = ROOT / "records/acquisition/orbit-preflight.json"
CUSTODY_RECEIPT_PATH = ROOT / "records/acquisition/orbit-custody-initialization.json"
LIVE_SOURCE_GATE_PATH = ROOT / "records/source-gates/m2-orbit-live-source-gate.json"
MANIFEST_PATH = ROOT / "records/source-gates/m2-orbit-candidate-manifest.json"
PROPOSAL_PATH = ROOT / "contracts/milestone-002-orbit-amendment-proposal.json"
REVIEW_BUNDLE_PATH = ROOT / "reviews/m2-orbit-amendment/review-bundle.json"
MILESTONE_PATH = ROOT / "contracts/milestone-002.json"
DOWNLOAD_HOST = "download.dataspace.copernicus.eu"
CATALOGUE_BASE = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
TOKEN_ENVIRONMENT_REFERENCE = "CDSE_ACCESS_TOKEN"
PROPOSAL_SHA256 = "b17e256068759946be611bf4e7beffe0d3121e9e731b6c42163525eca2cf0292"
REVIEW_BUNDLE_SHA256 = "ee5fbf4933b52be8f97441b78a73559a973bd975efc21b43625f1ceca54e2ff1"
EXPECTED_SOURCE_IDS = ["M2-ORB-001", "M2-ORB-002", "M2-ORB-003", "M2-ORB-004"]


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TransferControlError("control_root_not_object")
    return value


def build_attempt_id(asset_id: str, started_at: str, nonce: str) -> str:
    return f"{asset_id}-{started_at.replace(':', '').replace('-', '')}-{nonce}".lower()


def stopped(code: str) -> int:
    print(json.dumps({"status": "stopped", "code": code, "mutations_performed": False}, indent=2))
    return 12


def authority_and_activation_guard() -> dict[str, dict[str, Any]]:
    if not APPROVAL_PATH.is_file():
        raise TransferControlError("orbit_authority_not_approved")
    approval = load(APPROVAL_PATH)
    if (
        approval.get("status") != "approved"
        or approval.get("amendment_proposal_sha256") != PROPOSAL_SHA256
        or approval.get("review_bundle_manifest_sha256") != REVIEW_BUNDLE_SHA256
        or approval.get("authorized_source_ids") != EXPECTED_SOURCE_IDS
        or approval.get("authorized_orbit_type") != "AUX_RESORB"
        or approval.get("orbit_quality", {}).get("later_precise_substitution_status")
        != "separately_gated_not_authorized"
    ):
        raise TransferControlError("orbit_approval_identity_or_scope_drift")
    required = {
        "milestone": MILESTONE_PATH,
        "intake": ACTIVE_INTAKE_PATH,
        "verification": ACTIVE_VERIFICATION_PATH,
        "preflight": PREFLIGHT_PATH,
        "custody": CUSTODY_RECEIPT_PATH,
        "source_gate": LIVE_SOURCE_GATE_PATH,
    }
    if any(not path.is_file() for path in required.values()):
        raise TransferControlError("orbit_activation_or_preflight_incomplete")
    controls = {name: load(path) for name, path in required.items()}
    controls["approval"] = approval
    controls["manifest"] = load(MANIFEST_PATH)

    milestone = controls["milestone"]
    verification_units = [unit for unit in milestone.get("units", []) if unit.get("id") == "M2-VERIFY"]
    if (
        milestone.get("status") != "active"
        or milestone.get("authority", {}).get("authority_ref") != "records/source-gates/m2-activation-approval.json"
        or len(verification_units) != 1
        or verification_units[0].get("status") != "complete"
    ):
        raise TransferControlError("sentinel_verification_unit_not_complete")

    intake = controls["intake"]
    verification = controls["verification"]
    preflight = controls["preflight"]
    custody = controls["custody"]
    source_gate = controls["source_gate"]
    extensions = intake.get("extensions", {})
    if (
        extensions.get("status") not in {
            "active_authorized_preflight_passed_custody_initialized",
            "active_acquisition_in_progress",
        }
        or extensions.get("scope_authority") != "granted_exact_four_resorb_files"
        or extensions.get("amendment_approval_sha256") != sha256_file(APPROVAL_PATH)
        or extensions.get("proposal_sha256") != PROPOSAL_SHA256
        or extensions.get("manifest_sha256") != sha256_file(MANIFEST_PATH)
        or extensions.get("preflight_sha256") != sha256_file(PREFLIGHT_PATH)
        or extensions.get("custody_initialization_sha256") != sha256_file(CUSTODY_RECEIPT_PATH)
    ):
        raise TransferControlError("active_orbit_intake_binding_drift")
    if (
        verification.get("status") not in {
            "active_gate_deferred_no_promoted_orbits",
            "active_gate_ready_for_offline_verification",
        }
        or verification.get("authority", {}).get("orbit_payload_acquisition_authorized") is not True
        or verification.get("authority", {}).get("precise_orbit_substitution_authorized") is not False
        or verification.get("bindings", {}).get("amendment_approval_sha256") != sha256_file(APPROVAL_PATH)
    ):
        raise TransferControlError("active_orbit_verification_binding_drift")
    if (
        preflight.get("status") != "pass_no_payload_no_external_mutation_sentinel_custody_pending"
        or preflight.get("proposal_sha256") != PROPOSAL_SHA256
        or preflight.get("review_bundle_sha256") != REVIEW_BUNDLE_SHA256
        or preflight.get("candidate_manifest_sha256") != sha256_file(MANIFEST_PATH)
        or preflight.get("source_gate_sha256") != sha256_file(LIVE_SOURCE_GATE_PATH)
        or preflight.get("assertions", {}).get("orbit_payload_bytes_requested") != 0
        or source_gate.get("decision", {}).get("status") != "ready"
    ):
        raise TransferControlError("orbit_preflight_not_passing")
    if (
        custody.get("status") != "created_and_verified_empty"
        or custody.get("preflight_sha256") != sha256_file(PREFLIGHT_PATH)
        or custody.get("credential_values_read_or_recorded") is not False
    ):
        raise TransferControlError("orbit_custody_not_initialized")
    return controls


def verified_sentinel_custody(record: dict[str, Any]) -> list[dict[str, str]]:
    """Require every Sentinel source bound to this orbit to be promoted and container-verified."""
    if not SENTINEL_INTAKE_PATH.is_file():
        raise TransferControlError("bound_sentinel_intake_missing")
    intake = load(SENTINEL_INTAKE_PATH)
    verified: list[dict[str, str]] = []
    for source_id in record.get("sentinel_source_ids", []):
        matches = [
            asset
            for asset in intake.get("assets", [])
            if asset.get("extensions", {}).get("source_id") == source_id
        ]
        if len(matches) != 1:
            raise TransferControlError("bound_sentinel_source_absent_or_ambiguous")
        asset = matches[0]
        succeeded = [attempt for attempt in asset.get("attempts", []) if attempt.get("outcome") == "succeeded"]
        if asset.get("state") != "promoted" or len(succeeded) != 1:
            raise TransferControlError("bound_sentinel_source_not_promoted")
        attempt_id = succeeded[0].get("attempt_id")
        transfer_ref = asset.get("extensions", {}).get("successful_attempt_receipt")
        transfer_sha = asset.get("extensions", {}).get("successful_attempt_receipt_sha256")
        if not isinstance(attempt_id, str) or not isinstance(transfer_ref, str) or not isinstance(transfer_sha, str):
            raise TransferControlError("bound_sentinel_transfer_binding_missing")
        transfer_path = (ROOT / transfer_ref).resolve()
        try:
            transfer_path.relative_to(ROOT.resolve())
        except ValueError as exc:
            raise TransferControlError("bound_sentinel_transfer_receipt_path_escape") from exc
        if not transfer_path.is_file() or sha256_file(transfer_path) != transfer_sha:
            raise TransferControlError("bound_sentinel_transfer_receipt_missing_or_drifted")
        verification_path = (
            ROOT
            / "records/acquisition/container-verification"
            / f"{source_id.casefold()}-{attempt_id}.json"
        )
        if not verification_path.is_file():
            raise TransferControlError("bound_sentinel_container_verification_missing")
        receipt = load(verification_path)
        if (
            receipt.get("status") != "pass_container_only"
            or receipt.get("source_id") != source_id
            or receipt.get("attempt_id") != attempt_id
            or receipt.get("bindings", {}).get("transfer_receipt_sha256") != transfer_sha
        ):
            raise TransferControlError("bound_sentinel_container_verification_not_passing")
        verified.append(
            {
                "source_id": source_id,
                "transfer_receipt_sha256": transfer_sha,
                "container_verification_ref": str(verification_path.relative_to(ROOT)).replace("\\", "/"),
                "container_verification_sha256": sha256_file(verification_path),
            }
        )
    return verified


def normalized_live_product(item: dict[str, Any]) -> dict[str, Any]:
    locations = [location for location in item.get("Locations", []) if location.get("FormatType") == "Compressed"]
    if len(locations) != 1:
        raise TransferControlError("live_orbit_location_ambiguous")
    return {
        "provider_product_id": item.get("Id"),
        "exact_product_name": item.get("Name"),
        "s3_path": item.get("S3Path"),
        "content_length_bytes": item.get("ContentLength"),
        "validity_start_utc": item.get("ContentDate", {}).get("Start"),
        "validity_end_utc": item.get("ContentDate", {}).get("End"),
        "publication_date_utc": item.get("PublicationDate"),
        "modification_date_utc": item.get("ModificationDate"),
        "online": item.get("Online"),
        "eviction_date_utc": locations[0].get("EvictionDate"),
        "provider_checksums": provider_checksum_map(item.get("Checksum", [])),
    }


def public_catalog_check(record: dict[str, Any]) -> dict[str, Any]:
    url = f"{CATALOGUE_BASE}({record['provider_product_id']})?$expand=Locations"
    opener = urllib.request.build_opener(NoRedirectHandler())
    request = urllib.request.Request(url, headers={"User-Agent": "nepal-2026-orbit-intake/1.0", "Accept": "application/json"})
    try:
        with opener.open(request, timeout=60) as response:
            if int(response.status) != 200 or response.geturl() != url:
                raise TransferControlError("orbit_catalog_response_identity_drift")
            body = response.read()
        item = json.loads(body.decode("utf-8"))
    except TransferControlError:
        raise
    except (urllib.error.URLError, TimeoutError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TransferControlError("orbit_catalog_revalidation_unavailable") from exc
    live = normalized_live_product(item)
    expected_checksums = provider_checksum_map(record["provider_checksums"])
    expected = {
        "provider_product_id": record["provider_product_id"],
        "exact_product_name": record["exact_product_name"],
        "s3_path": record["s3_path"],
        "content_length_bytes": record["content_length_bytes"],
        "validity_start_utc": record["validity_start_utc"],
        "validity_end_utc": record["validity_end_utc"],
        "publication_date_utc": record["publication_date_utc"],
        "modification_date_utc": record["modification_date_utc"],
        "online": True,
        "eviction_date_utc": record["eviction_date_utc"],
        "provider_checksums": expected_checksums,
    }
    if live != expected:
        raise TransferControlError("live_orbit_catalog_identity_or_availability_drift")
    return {"url": url, "response_sha256": hashlib.sha256(body).hexdigest(), "identity": live}


def set_attempt_terminal(
    intake: dict[str, Any],
    asset_id: str,
    attempt_id: str,
    completed_at: str,
    *,
    outcome: str,
    failure_code: str | None,
) -> dict[str, Any]:
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

    try:
        controls = authority_and_activation_guard()
    except TransferControlError as exc:
        return stopped(exc.code)

    intake = controls["intake"]
    verification = controls["verification"]
    manifest = controls["manifest"]
    if any(asset.get("state") == "staging" for asset in intake.get("assets", [])):
        return stopped("another_orbit_transfer_is_active")
    matching_assets = [asset for asset in intake.get("assets", []) if asset.get("extensions", {}).get("source_id") == args.source_id]
    matching_records = [record for record in manifest.get("records", []) if record.get("source_id") == args.source_id]
    matching_requirements = [record for record in verification.get("asset_requirements", []) if record.get("source_id") == args.source_id]
    if len(matching_assets) != 1 or len(matching_records) != 1 or len(matching_requirements) != 1:
        return stopped("orbit_source_identity_absent_or_ambiguous")
    asset, record, requirement = matching_assets[0], matching_records[0], matching_requirements[0]
    if asset.get("state") != "authorized" or asset.get("attempts") != []:
        return stopped("orbit_asset_not_fresh_authorized")
    if asset.get("expected", {}).get("size_bytes") != record.get("content_length_bytes"):
        return stopped("orbit_intake_manifest_size_drift")
    if asset.get("extensions", {}).get("provider_product_id") != record.get("provider_product_id"):
        return stopped("orbit_intake_manifest_identity_drift")

    try:
        sentinel_custody = verified_sentinel_custody(record)
    except TransferControlError as exc:
        return stopped(exc.code)

    source_uri = asset["source"]["uri"]
    parsed = urlsplit(source_uri)
    if (
        parsed.scheme != "https"
        or parsed.hostname != DOWNLOAD_HOST
        or parsed.query
        or parsed.fragment
        or source_uri != record["download_url"]
    ):
        return stopped("orbit_download_route_outside_reviewed_boundary")
    try:
        custody_root = (PROJECT_ROOT / Path(*PurePosixPath(intake["custody_root"]).parts)).resolve(strict=True)
        staging_root = (PROJECT_ROOT / Path(*PurePosixPath(intake["staging_root"]).parts)).resolve(strict=True)
        destination = require_safe_child(custody_root, custody_root / Path(*PurePosixPath(asset["destination_relative_path"]).parts))
        staging = require_safe_child(staging_root, staging_root / Path(*PurePosixPath(asset["staging_relative_path"]).parts))
    except (FileNotFoundError, TransferControlError):
        return stopped("orbit_custody_path_missing_or_unsafe")
    if destination.exists() or staging.exists():
        return stopped("orbit_destination_or_staging_collision")
    expected_size = int(asset["expected"]["size_bytes"])
    if shutil.disk_usage(PROJECT_ROOT).free < expected_size * 3:
        return stopped("free_space_below_orbit_staging_verification_requirement")

    try:
        catalog = public_catalog_check(record)
    except TransferControlError as exc:
        return stopped(exc.code)

    try:
        checksums = provider_checksum_map(record["provider_checksums"])
    except OrbitControlError as exc:
        return stopped(exc.code)
    access_value = os.environ.get(TOKEN_ENVIRONMENT_REFERENCE)
    if not access_value:
        return stopped("secret_safe_access_reference_missing")

    if not staging.parent.is_dir() or not destination.parent.is_dir():
        return stopped("orbit_preinitialized_asset_directory_missing")
    events_root = staging_root / "attempt-events" / asset["asset_id"]
    if not events_root.is_dir():
        return stopped("orbit_preinitialized_event_directory_missing")
    started_at = now_utc()
    attempt_id = build_attempt_id(asset["asset_id"], started_at, uuid.uuid4().hex[:8])
    started_event_path = events_root / f"{attempt_id}-started.json"
    public_receipt = ROOT / "records/acquisition/orbit-attempts" / f"{attempt_id}.json"
    if public_receipt.exists():
        return stopped("orbit_attempt_receipt_collision")
    started_event = {
        "schema_version": "1.0",
        "event": "orbit_transfer_started",
        "attempt_id": attempt_id,
        "asset_id": asset["asset_id"],
        "source_id": args.source_id,
        "started_at": started_at,
        "source_uri": source_uri,
        "approval_sha256": sha256_file(APPROVAL_PATH),
        "preflight_sha256": sha256_file(PREFLIGHT_PATH),
        "catalog_response_sha256": catalog["response_sha256"],
        "verified_sentinel_custody": sentinel_custody,
        "credential_reference": TOKEN_ENVIRONMENT_REFERENCE,
        "credential_value_recorded": False,
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
        "extensions": {
            "source_id": args.source_id,
            "catalog_response_sha256": catalog["response_sha256"],
            "verified_sentinel_custody": sentinel_custody,
            "external_started_event": str(started_event_path),
            "credential_reference": TOKEN_ENVIRONMENT_REFERENCE,
            "credential_value_recorded": False,
            "resume": False,
        },
    })
    asset["state"] = "staging"
    replace_json(ACTIVE_INTAKE_PATH, intake, f".{attempt_id}.started-tmp")

    try:
        opener = urllib.request.build_opener(NoRedirectHandler())
        request = urllib.request.Request(
            source_uri,
            headers={
                "Authorization": f"Bearer {access_value}",
                "User-Agent": "nepal-2026-orbit-intake/1.0",
                "Accept": "application/octet-stream,application/xml,text/xml,*/*",
                "Accept-Encoding": "identity",
            },
        )
        with opener.open(request, timeout=120) as response:
            if int(response.status) != 200 or response.geturl() != source_uri:
                raise OrbitControlError("orbit_download_response_identity_drift")
            content_length = response.headers.get("Content-Length")
            if content_length is None or int(content_length) != expected_size:
                raise OrbitControlError("orbit_download_content_length_mismatch")
            if "text/html" in (response.headers.get("Content-Type") or "").casefold():
                raise OrbitControlError("unexpected_html_payload")
            staged = stream_to_exclusive_staging(
                response,
                staging,
                expected_size=expected_size,
                expected_md5=checksums["MD5"],
                expected_blake3=checksums["BLAKE3"],
            )
        staged_validation = inspect_eof(staging, requirement, logical_name=asset["extensions"]["exact_product_name"])
        promoted = promote_atomic_no_replace(staging, destination)
        if promoted["sha256"] != staged["sha256"] or promoted["size_bytes"] != staged["size_bytes"]:
            raise OrbitControlError("promoted_orbit_identity_differs_from_staged")
        completed_at = now_utc()
        terminal_event = {
            "schema_version": "1.0",
            "event": "orbit_transfer_succeeded",
            "attempt_id": attempt_id,
            "asset_id": asset["asset_id"],
            "source_id": args.source_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "source_uri": source_uri,
            "approval_sha256": sha256_file(APPROVAL_PATH),
            "preflight_sha256": sha256_file(PREFLIGHT_PATH),
            "catalog_response_sha256": catalog["response_sha256"],
            "local_size_bytes": promoted["size_bytes"],
            "local_sha256": promoted["sha256"],
            "provider_md5": staged["md5"],
            "provider_blake3": staged["blake3"],
            "provider_checksums_locally_verified": True,
            "staged_xml_validation": staged_validation["xml"],
            "scene_binding": staged_validation["scene_binding"],
            "destination_path": str(destination),
            "credential_reference": TOKEN_ENVIRONMENT_REFERENCE,
            "credential_value_recorded": False,
            "offline_reverification_status": "pending",
        }
        write_new_json(events_root / f"{attempt_id}-succeeded.json", terminal_event)
        write_new_json(public_receipt, terminal_event)
        refreshed = load(ACTIVE_INTAKE_PATH)
        refreshed_asset = set_attempt_terminal(
            refreshed, asset["asset_id"], attempt_id, completed_at, outcome="succeeded", failure_code=None
        )
        refreshed_asset["state"] = "promoted"
        refreshed_asset["observed"].update({
            "staged_sha256": staged["sha256"],
            "staged_size_bytes": staged["size_bytes"],
            "promoted_sha256": promoted["sha256"],
            "promoted_size_bytes": promoted["size_bytes"],
        })
        refreshed_asset["extensions"].update({
            "successful_attempt_receipt": str(public_receipt.relative_to(ROOT)).replace("\\", "/"),
            "successful_attempt_receipt_sha256": sha256_file(public_receipt),
            "provider_md5_verified": True,
            "provider_blake3_verified": True,
            "staged_xml_verification_status": "pass_orbit_input_only",
            "offline_reverification_status": "pending",
        })
        replace_json(ACTIVE_INTAKE_PATH, refreshed, f".{attempt_id}.succeeded-tmp")
        refreshed_verification = load(ACTIVE_VERIFICATION_PATH)
        refreshed_verification["status"] = "active_gate_ready_for_offline_verification"
        refreshed_verification["bindings"]["active_intake_sha256_current"] = sha256_file(ACTIVE_INTAKE_PATH)
        refreshed_verification["bindings"]["latest_promoted_source_id"] = args.source_id
        replace_json(ACTIVE_VERIFICATION_PATH, refreshed_verification, f".{attempt_id}.ready-tmp")
        print(json.dumps({
            "status": "promoted_pending_offline_reverification",
            "source_id": args.source_id,
            "attempt_id": attempt_id,
            "size_bytes": promoted["size_bytes"],
            "sha256": promoted["sha256"],
            "receipt": str(public_receipt.relative_to(ROOT)).replace("\\", "/"),
            "credential_value_recorded": False,
        }, indent=2))
        return 0
    except BaseException as exc:
        completed_at = now_utc()
        if isinstance(exc, (OrbitControlError, TransferControlError)):
            failure_code = exc.code
        elif isinstance(exc, urllib.error.HTTPError):
            failure_code = "orbit_redirect_or_http_status_rejected"
        elif isinstance(exc, (urllib.error.URLError, TimeoutError, ConnectionError, OSError)):
            failure_code = "orbit_provider_transport_failure"
        else:
            failure_code = "unexpected_orbit_transfer_failure"
        terminal_event = {
            "schema_version": "1.0",
            "event": "orbit_transfer_failed",
            "attempt_id": attempt_id,
            "asset_id": asset["asset_id"],
            "source_id": args.source_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "failure_code": failure_code,
            "partial_bytes_preserved": staging.stat().st_size if staging.exists() else 0,
            "credential_reference": TOKEN_ENVIRONMENT_REFERENCE,
            "credential_value_recorded": False,
            "retry_automatically_authorized": False,
        }
        write_new_json(events_root / f"{attempt_id}-failed.json", terminal_event)
        write_new_json(public_receipt, terminal_event)
        refreshed = load(ACTIVE_INTAKE_PATH)
        set_attempt_terminal(
            refreshed, asset["asset_id"], attempt_id, completed_at, outcome="failed", failure_code=failure_code
        )
        replace_json(ACTIVE_INTAKE_PATH, refreshed, f".{attempt_id}.failed-tmp")
        print(json.dumps({
            "status": "failed_preserved",
            "source_id": args.source_id,
            "attempt_id": attempt_id,
            "failure_code": failure_code,
            "partial_bytes_preserved": terminal_event["partial_bytes_preserved"],
            "receipt": str(public_receipt.relative_to(ROOT)).replace("\\", "/"),
            "credential_value_recorded": False,
        }, indent=2))
        return 20


if __name__ == "__main__":
    raise SystemExit(main())
