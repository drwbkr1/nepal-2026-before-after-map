#!/usr/bin/env python3
"""Acquire one exact M2 product through a secret-safe, fail-closed transfer."""

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
from typing import Any
from urllib.parse import urlsplit

from m2_transfer_core import (
    NoRedirectHandler,
    TransferControlError,
    ensure_directory,
    promote_atomic_no_replace,
    replace_json,
    require_safe_child,
    sha256_file,
    stream_to_exclusive_staging,
    write_new_json,
)


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent.resolve()
INTAKE_PATH = ROOT / "contracts/m2-intake.json"
CONTRACT_PATH = ROOT / "contracts/milestone-002.json"
APPROVAL_PATH = ROOT / "records/source-gates/m2-activation-approval.json"
PREFLIGHT_PATH = ROOT / "records/acquisition/preflight.json"
PLAN_PATH = ROOT / "records/acquisition-plan.json"
CATALOG_BASE = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
DOWNLOAD_HOST = "download.dataspace.copernicus.eu"
TOKEN_ENVIRONMENT_REFERENCE = "CDSE_ACCESS_TOKEN"


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TransferControlError("control_root_not_object")
    return value


def checksum_map(values: list[dict[str, Any]]) -> dict[str, str]:
    return {str(item["Algorithm"]).upper(): str(item["Value"]).casefold() for item in values}


def live_page_consistency_check(preflight: dict[str, Any]) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for expected in preflight.get("official_page_checks", []):
        url = expected.get("url")
        expected_sha = expected.get("sha256")
        if not isinstance(url, str) or not isinstance(expected_sha, str):
            raise TransferControlError("preflight_page_binding_incomplete")
        request = urllib.request.Request(url, headers={"User-Agent": "nepal-2026-controlled-intake/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                body = response.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise TransferControlError("official_page_revalidation_unavailable") from exc
        observed_sha = hashlib.sha256(body).hexdigest()
        if observed_sha != expected_sha:
            raise TransferControlError("official_access_or_terms_page_changed")
        observations.append({
            "page_id": expected.get("page_id"),
            "url": url,
            "sha256": observed_sha,
            "unchanged_from_preflight": True,
        })
    if len(observations) != 4:
        raise TransferControlError("preflight_page_binding_count_invalid")
    return observations


def public_catalog_check(asset: dict[str, Any], plan_record: dict[str, Any]) -> dict[str, Any]:
    provider_id = asset["extensions"]["provider_product_id"]
    url = f"{CATALOG_BASE}({provider_id})?%24expand=Attributes"
    request = urllib.request.Request(url, headers={"User-Agent": "nepal-2026-controlled-intake/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read()
        product = json.loads(body.decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TransferControlError("catalog_revalidation_unavailable") from exc
    actual = checksum_map(product.get("Checksum", []))
    expected = checksum_map(plan_record["provider_checksums"])
    checks = {
        "provider_id": product.get("Id") == provider_id,
        "product_name": product.get("Name") == asset["extensions"]["exact_product_id"],
        "content_length": product.get("ContentLength") == asset["extensions"]["catalog_content_length_bytes"],
        "checksums": actual == expected,
        "online": product.get("Online") is True,
    }
    if not all(checks.values()):
        raise TransferControlError("live_catalog_identity_or_availability_drift")
    return {
        "url": url,
        "response_sha256": hashlib.sha256(body).hexdigest(),
        "content_length_bytes": product["ContentLength"],
        "provider_md5": actual["MD5"],
        "provider_blake3_metadata": actual["BLAKE3"],
        "checks": checks,
    }


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
    parser.add_argument("--source-id", required=True, help="Exact approved source ID, such as M1-SRC-001")
    args = parser.parse_args()

    access_value = os.environ.get(TOKEN_ENVIRONMENT_REFERENCE)
    if not access_value:
        print(json.dumps({
            "status": "stopped",
            "code": "secret_safe_access_reference_missing",
            "required_reference": TOKEN_ENVIRONMENT_REFERENCE,
            "mutations_performed": False,
        }, indent=2))
        return 12

    intake = load(INTAKE_PATH)
    contract = load(CONTRACT_PATH)
    approval = load(APPROVAL_PATH)
    preflight = load(PREFLIGHT_PATH)
    plan = load(PLAN_PATH)
    if approval.get("status") != "approved" or contract.get("status") != "active":
        raise TransferControlError("m2_authority_inactive")
    if approval.get("acquisition_plan_sha256") != sha256_file(PLAN_PATH):
        raise TransferControlError("approved_acquisition_plan_hash_drift")
    if contract.get("authority", {}).get("approval_sha256") != sha256_file(APPROVAL_PATH):
        raise TransferControlError("active_contract_approval_hash_drift")
    if preflight.get("source_gate", {}).get("sha256") != intake.get("extensions", {}).get("source_gate_sha256"):
        raise TransferControlError("preflight_source_gate_binding_drift")
    units = {unit["id"]: unit for unit in contract["units"]}
    acquire = units.get("M2-ACQUIRE", {})
    if acquire.get("status") != "ready" or acquire.get("gates", {}).get("custody_initialization") != "pass":
        raise TransferControlError("m2_acquisition_unit_not_ready")
    if preflight.get("status") != "pass_no_external_mutation":
        raise TransferControlError("m2_preflight_not_passing")
    matching_assets = [item for item in intake["assets"] if item.get("extensions", {}).get("source_id") == args.source_id]
    matching_plan = [item for item in plan["records"] if item.get("source_id") == args.source_id]
    if len(matching_assets) != 1 or len(matching_plan) != 1:
        raise TransferControlError("source_id_not_exactly_approved_once")
    asset = matching_assets[0]
    plan_record = matching_plan[0]
    if asset.get("state") != "authorized" or asset.get("attempts") != []:
        raise TransferControlError("asset_not_fresh_authorized")
    source_uri = asset["source"]["uri"]
    parsed_source = urlsplit(source_uri)
    if parsed_source.scheme != "https" or parsed_source.hostname != DOWNLOAD_HOST or parsed_source.query or parsed_source.fragment:
        raise TransferControlError("download_route_outside_reviewed_boundary")

    custody_root = (PROJECT_ROOT / Path(*PurePosixPath(intake["custody_root"]).parts)).resolve(strict=True)
    staging_root = (PROJECT_ROOT / Path(*PurePosixPath(intake["staging_root"]).parts)).resolve(strict=True)
    if not custody_root.is_dir() or not staging_root.is_dir():
        raise TransferControlError("initialized_custody_path_missing")
    destination = require_safe_child(custody_root, custody_root / Path(*PurePosixPath(asset["destination_relative_path"]).parts))
    staging = require_safe_child(staging_root, staging_root / Path(*PurePosixPath(asset["staging_relative_path"]).parts))
    if destination.exists() or staging.exists():
        raise TransferControlError("destination_or_staging_collision")
    free_gib = shutil.disk_usage(PROJECT_ROOT).free / (1024 ** 3)
    if free_gib < float(preflight["storage"]["minimum_free_gib"]):
        raise TransferControlError("free_space_below_approved_minimum")

    page_observations = live_page_consistency_check(preflight)
    catalog = public_catalog_check(asset, plan_record)
    ensure_directory(staging.parent, staging_root)
    ensure_directory(destination.parent, custody_root)
    events_root = staging_root / "attempt-events" / asset["asset_id"]
    ensure_directory(events_root, staging_root)
    started_at = now_utc()
    attempt_id = f"{asset['asset_id']}-{started_at.replace(':', '').replace('-', '')}-{uuid.uuid4().hex[:8]}"
    started_event_path = events_root / f"{attempt_id}-started.json"
    started_event = {
        "schema_version": "1.0",
        "event": "transfer_started",
        "attempt_id": attempt_id,
        "asset_id": asset["asset_id"],
        "source_id": args.source_id,
        "started_at": started_at,
        "source_uri": source_uri,
        "catalog_response_sha256": catalog["response_sha256"],
        "official_page_observations": page_observations,
        "expected_catalog_size_bytes": catalog["content_length_bytes"],
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
            "external_started_event": str(started_event_path),
            "credential_reference": TOKEN_ENVIRONMENT_REFERENCE,
            "credential_value_recorded": False,
            "resume": False,
        },
    })
    asset["state"] = "staging"
    replace_json(INTAKE_PATH, intake, f".{attempt_id}.started-tmp")

    try:
        opener = urllib.request.build_opener(NoRedirectHandler())
        request = urllib.request.Request(
            source_uri,
            headers={
                "Authorization": f"Bearer {access_value}",
                "User-Agent": "nepal-2026-controlled-intake/1.0",
                "Accept-Encoding": "identity",
            },
        )
        with opener.open(request, timeout=120) as response:
            if response.status != 200 or response.geturl() != source_uri:
                raise TransferControlError("download_response_identity_drift")
            declared_length = response.headers.get("Content-Length")
            if declared_length is None or int(declared_length) != catalog["content_length_bytes"]:
                raise TransferControlError("authenticated_content_length_mismatch")
            if "text/html" in (response.headers.get("Content-Type") or "").casefold():
                raise TransferControlError("unexpected_html_payload")
            staged = stream_to_exclusive_staging(
                response,
                staging,
                expected_size=catalog["content_length_bytes"],
                expected_md5=catalog["provider_md5"],
            )
        promoted = promote_atomic_no_replace(staging, destination)
        if promoted["sha256"] != staged["sha256"] or promoted["size_bytes"] != staged["size_bytes"]:
            raise TransferControlError("promoted_identity_differs_from_staged")
        completed_at = now_utc()
        terminal_event = {
            "schema_version": "1.0",
            "event": "transfer_succeeded",
            "attempt_id": attempt_id,
            "asset_id": asset["asset_id"],
            "source_id": args.source_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "catalog_response_sha256": catalog["response_sha256"],
            "local_sha256": promoted["sha256"],
            "local_size_bytes": promoted["size_bytes"],
            "provider_md5": catalog["provider_md5"],
            "provider_md5_match": True,
            "provider_blake3_metadata": catalog["provider_blake3_metadata"],
            "provider_blake3_locally_verified": False,
            "destination_path": str(destination),
            "credential_value_recorded": False,
        }
        terminal_path = events_root / f"{attempt_id}-succeeded.json"
        write_new_json(terminal_path, terminal_event)
        public_receipt = ROOT / "records" / "acquisition" / "attempts" / f"{attempt_id}.json"
        write_new_json(public_receipt, terminal_event)
        refreshed_intake = load(INTAKE_PATH)
        refreshed_asset = set_attempt_terminal(
            refreshed_intake, asset["asset_id"], attempt_id, completed_at, outcome="succeeded", failure_code=None
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
            "provider_blake3_locally_verified": False,
        })
        replace_json(INTAKE_PATH, refreshed_intake, f".{attempt_id}.succeeded-tmp")
        print(json.dumps({
            "status": "promoted_pending_container_verification",
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
        if isinstance(exc, TransferControlError):
            failure_code = exc.code
        elif isinstance(exc, urllib.error.HTTPError):
            failure_code = "redirect_or_http_status_rejected"
        elif isinstance(exc, urllib.error.URLError):
            failure_code = "provider_transport_failure"
        elif isinstance(exc, (TimeoutError, ConnectionError)):
            failure_code = "provider_transport_failure"
        else:
            failure_code = "unexpected_transfer_failure"
        terminal_event = {
            "schema_version": "1.0",
            "event": "transfer_failed",
            "attempt_id": attempt_id,
            "asset_id": asset["asset_id"],
            "source_id": args.source_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "failure_code": failure_code,
            "partial_bytes_preserved": staging.stat().st_size if staging.exists() else 0,
            "credential_value_recorded": False,
            "retry_automatically_authorized": False,
        }
        terminal_path = events_root / f"{attempt_id}-failed.json"
        write_new_json(terminal_path, terminal_event)
        public_receipt = ROOT / "records" / "acquisition" / "attempts" / f"{attempt_id}.json"
        write_new_json(public_receipt, terminal_event)
        refreshed_intake = load(INTAKE_PATH)
        set_attempt_terminal(
            refreshed_intake, asset["asset_id"], attempt_id, completed_at, outcome="failed", failure_code=failure_code
        )
        replace_json(INTAKE_PATH, refreshed_intake, f".{attempt_id}.failed-tmp")
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
    try:
        raise SystemExit(main())
    except TransferControlError as exc:
        print(json.dumps({"status": "stopped", "code": exc.code, "mutations_performed": False}, indent=2))
        raise SystemExit(12)
