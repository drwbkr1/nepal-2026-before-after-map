#!/usr/bin/env python3
"""Run the one approved byte-zero recovery of exact Sentinel source M1-SRC-004."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
import uuid
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlsplit

from acquire_m2_product import (
    DOWNLOAD_HOST,
    TOKEN_ENVIRONMENT_REFERENCE,
    live_page_consistency_check,
    now_utc,
    public_catalog_check,
)
from m2_sentinel_recovery_core import (
    EXPECTED_ASSET_ID,
    EXPECTED_FAILED_ATTEMPT_ID,
    EXPECTED_PARTIAL_BYTES,
    EXPECTED_PARTIAL_SHA256,
    EXPECTED_SOURCE_ID,
    RecoveryControlError,
    require_exact_recovery_contract,
    require_fresh_authorized_attempt,
    require_original_failure,
    set_attempt_terminal,
)
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
DATA_ROOT = PROJECT_ROOT / "nepal-2026-before-after-map-data"
RECOVERY_CONTRACT_PATH = ROOT / "contracts/m2-sentinel-recovery.json"
ACTIVE_INTAKE_PATH = ROOT / "contracts/m2-intake.json"
BASE_APPROVAL_PATH = ROOT / "records/source-gates/m2-activation-approval.json"
RECOVERY_APPROVAL_PATH = ROOT / "records/source-gates/m2-sentinel-recovery-approval.json"
REVIEW_RECONCILIATION_PATH = ROOT / "records/source-gates/m2-sentinel-recovery-review-reconciliation.json"
PROPOSAL_PATH = ROOT / "contracts/milestone-002-sentinel-recovery-proposal.json"
BUNDLE_PATH = ROOT / "reviews/m2-sentinel-recovery/review-bundle.json"
FAILED_RECEIPT_PATH = ROOT / "records/acquisition/attempts/m1-src-004-20260904t043930z-ac125c11.json"
PREFLIGHT_PATH = ROOT / "records/acquisition/preflight.json"
PREFLIGHT_REFRESH_PATH = ROOT / "records/acquisition/preflight-refresh.json"
SOURCE_GATE_REFRESH_PATH = ROOT / "records/source-gates/m2-live-source-gate-refresh.json"
TERMS_RECONCILIATION_PATH = ROOT / "records/source-gates/m2-terms-page-reconciliation.json"
PLAN_PATH = ROOT / "records/acquisition-plan.json"
PUBLICATION_GATE_PATH = ROOT / "records/acquisition/sentinel-recovery-publication-gate.json"
RECEIPT_ROOT = ROOT / "records/acquisition/recovery-attempts"

EXPECTED_BUNDLE_SHA256 = "dffa194cc91636a35b5f55af6ece32bb6eb90d77b65ea3d9865413f912d146e7"
EXPECTED_PROPOSAL_SHA256 = "7b8b5e83265b37962f879ca7dad85ab5f5c04ceb28ee0f15fa774a79df7fd013"
EXPECTED_FAILED_RECEIPT_SHA256 = "8cbaf911e5a3329c5aa00a7288e237fa71987a2d4f03cea8c630c7dd28b9e7e9"


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RecoveryControlError("control_root_not_object")
    return value


def build_attempt_id(started_at: str, nonce: str) -> str:
    return f"{EXPECTED_ASSET_ID}-{started_at.replace(':', '').replace('-', '')}-{nonce}".lower()


def current_git_identity() -> tuple[str, str]:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()
    origin = subprocess.run(
        ["git", "rev-parse", "origin/main"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()
    return head, origin


def validate_publication_gate(gate: dict[str, Any]) -> None:
    head, origin = current_git_identity()
    bindings = gate.get("bindings", {})
    if (
        gate.get("status") != "pass_public_controls_verified_before_real_recovery"
        or gate.get("github_actions", {}).get("conclusion") != "success"
        or gate.get("github_actions", {}).get("head_sha") != head
        or head != origin
        or bindings.get("recovery_runner_sha256") != sha256_file(Path(__file__))
        or bindings.get("recovery_core_sha256") != sha256_file(ROOT / "scripts/m2_sentinel_recovery_core.py")
        or bindings.get("activation_script_sha256") != sha256_file(ROOT / "scripts/activate_m2_sentinel_recovery.py")
        or bindings.get("container_verifier_sha256") != sha256_file(ROOT / "scripts/verify_m2_sentinel_recovery_container.py")
        or bindings.get("tests_sha256") != sha256_file(ROOT / "tests/test_m2_sentinel_recovery.py")
    ):
        raise RecoveryControlError("recovery_publication_gate_drift")


def validate_authority(contract: dict[str, Any], approval: dict[str, Any], reconciliation: dict[str, Any]) -> None:
    extensions = contract.get("extensions", {})
    if (
        sha256_file(BUNDLE_PATH) != EXPECTED_BUNDLE_SHA256
        or sha256_file(PROPOSAL_PATH) != EXPECTED_PROPOSAL_SHA256
        or sha256_file(FAILED_RECEIPT_PATH) != EXPECTED_FAILED_RECEIPT_SHA256
        or approval.get("status") != "approved_exact_bounded_fresh_byte_zero_recovery"
        or approval.get("review_bundle_manifest_sha256") != EXPECTED_BUNDLE_SHA256
        or approval.get("recovery_proposal_sha256") != EXPECTED_PROPOSAL_SHA256
        or approval.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}
        or approval.get("human_decisions_fabricated") is not False
        or reconciliation.get("status") != "reconciled_exact_human_response"
        or reconciliation.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}
        or extensions.get("recovery_approval_sha256") != sha256_file(RECOVERY_APPROVAL_PATH)
        or extensions.get("review_reconciliation_sha256") != sha256_file(REVIEW_RECONCILIATION_PATH)
    ):
        raise RecoveryControlError("recovery_authority_or_binding_drift")


def retained_partial_path(active_intake: dict[str, Any]) -> Path:
    assets = [
        asset for asset in active_intake.get("assets", [])
        if asset.get("extensions", {}).get("source_id") == EXPECTED_SOURCE_ID
    ]
    if len(assets) != 1:
        raise RecoveryControlError("original_failed_asset_identity_drift")
    event_path_value = assets[0].get("attempts", [{}])[0].get("extensions", {}).get("external_started_event")
    if not isinstance(event_path_value, str):
        raise RecoveryControlError("original_started_event_reference_missing")
    event_path = Path(event_path_value).resolve(strict=True)
    try:
        event_path.relative_to(DATA_ROOT.resolve(strict=True))
    except ValueError as exc:
        raise RecoveryControlError("original_started_event_outside_data_root") from exc
    event = load(event_path)
    partial_value = event.get("staging_path")
    if not isinstance(partial_value, str):
        raise RecoveryControlError("retained_partial_reference_missing")
    partial = Path(partial_value).resolve(strict=True)
    try:
        partial.relative_to(DATA_ROOT.resolve(strict=True))
    except ValueError as exc:
        raise RecoveryControlError("retained_partial_outside_data_root") from exc
    return partial


def verify_original_failure_unchanged(active_intake: dict[str, Any], failed_receipt: dict[str, Any]) -> Path:
    partial = retained_partial_path(active_intake)
    require_original_failure(
        active_intake,
        failed_receipt,
        partial_size=partial.stat().st_size,
        partial_sha256=sha256_file(partial),
    )
    return partial


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", required=True)
    args = parser.parse_args()
    if args.source_id != EXPECTED_SOURCE_ID:
        raise RecoveryControlError("recovery_source_outside_exact_approval")

    access_value = os.environ.get(TOKEN_ENVIRONMENT_REFERENCE)
    if not access_value:
        print(json.dumps({
            "status": "stopped",
            "code": "secret_safe_access_reference_missing",
            "required_reference": TOKEN_ENVIRONMENT_REFERENCE,
            "mutations_performed": False,
        }, indent=2))
        return 12

    contract = load(RECOVERY_CONTRACT_PATH)
    asset = require_exact_recovery_contract(contract)
    require_fresh_authorized_attempt(asset)
    active_intake = load(ACTIVE_INTAKE_PATH)
    failed_receipt = load(FAILED_RECEIPT_PATH)
    approval = load(RECOVERY_APPROVAL_PATH)
    reconciliation = load(REVIEW_RECONCILIATION_PATH)
    proposal = load(PROPOSAL_PATH)
    base_approval = load(BASE_APPROVAL_PATH)
    preflight = load(PREFLIGHT_PATH)
    preflight_refresh = load(PREFLIGHT_REFRESH_PATH)
    plan = load(PLAN_PATH)
    gate = load(PUBLICATION_GATE_PATH)

    validate_authority(contract, approval, reconciliation)
    validate_publication_gate(gate)
    if proposal.get("status") != "proposed_not_authorized" or base_approval.get("status") != "approved":
        raise RecoveryControlError("base_authority_or_proposal_drift")
    if (
        preflight_refresh.get("status") != "pass_no_external_mutation"
        or preflight_refresh.get("base_preflight", {}).get("sha256") != sha256_file(PREFLIGHT_PATH)
        or preflight_refresh.get("source_gate", {}).get("sha256") != sha256_file(SOURCE_GATE_REFRESH_PATH)
        or preflight_refresh.get("terms_reconciliation", {}).get("sha256") != sha256_file(TERMS_RECONCILIATION_PATH)
        or preflight_refresh.get("authority", {}).get("approval_sha256") != sha256_file(BASE_APPROVAL_PATH)
    ):
        raise RecoveryControlError("m2_preflight_refresh_binding_drift")

    partial = verify_original_failure_unchanged(active_intake, failed_receipt)
    matching_plan = [record for record in plan.get("records", []) if record.get("source_id") == EXPECTED_SOURCE_ID]
    if len(matching_plan) != 1:
        raise RecoveryControlError("recovery_source_not_bound_once_in_original_plan")
    source_uri = asset["source"]["uri"]
    parsed = urlsplit(source_uri)
    if parsed.scheme != "https" or parsed.hostname != DOWNLOAD_HOST or parsed.query or parsed.fragment:
        raise RecoveryControlError("download_route_outside_reviewed_boundary")

    custody_root = (PROJECT_ROOT / Path(*PurePosixPath(contract["custody_root"]).parts)).resolve(strict=True)
    staging_parent = (DATA_ROOT / ".intake-staging").resolve(strict=True)
    staging_root = (PROJECT_ROOT / Path(*PurePosixPath(contract["staging_root"]).parts)).resolve(strict=False)
    destination = require_safe_child(
        custody_root, custody_root / Path(*PurePosixPath(asset["destination_relative_path"]).parts)
    )
    staging = staging_root / Path(*PurePosixPath(asset["staging_relative_path"]).parts)
    if destination.exists() or staging_root.exists() or staging.exists():
        raise RecoveryControlError("recovery_destination_or_staging_collision")
    free_gib = shutil.disk_usage(PROJECT_ROOT).free / (1024 ** 3)
    if free_gib < float(preflight["storage"]["minimum_free_gib"]):
        raise RecoveryControlError("free_space_below_approved_minimum")

    page_observations = live_page_consistency_check(preflight_refresh)
    catalog = public_catalog_check(asset, matching_plan[0])
    ensure_directory(staging_root, staging_parent)
    staging = require_safe_child(staging_root, staging)
    ensure_directory(staging.parent, staging_root)
    ensure_directory(destination.parent, custody_root)
    events_root = staging_root / "attempt-events" / EXPECTED_ASSET_ID
    ensure_directory(events_root, staging_root)

    started_at = now_utc()
    attempt_id = build_attempt_id(started_at, uuid.uuid4().hex[:8])
    started_event_path = events_root / f"{attempt_id}-started.json"
    started_event = {
        "schema_version": "1.0",
        "event": "recovery_transfer_started",
        "attempt_id": attempt_id,
        "asset_id": EXPECTED_ASSET_ID,
        "source_id": EXPECTED_SOURCE_ID,
        "started_at": started_at,
        "source_uri": source_uri,
        "catalog_response_sha256": catalog["response_sha256"],
        "official_page_observations": page_observations,
        "expected_catalog_size_bytes": catalog["content_length_bytes"],
        "credential_reference": TOKEN_ENVIRONMENT_REFERENCE,
        "credential_value_recorded": False,
        "restart_offset_bytes": 0,
        "range_or_resume_used": False,
        "retained_failed_attempt_id": EXPECTED_FAILED_ATTEMPT_ID,
        "retained_partial_size_bytes": EXPECTED_PARTIAL_BYTES,
        "retained_partial_sha256": EXPECTED_PARTIAL_SHA256,
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
            "source_id": EXPECTED_SOURCE_ID,
            "catalog_response_sha256": catalog["response_sha256"],
            "external_started_event": str(started_event_path),
            "credential_reference": TOKEN_ENVIRONMENT_REFERENCE,
            "credential_value_recorded": False,
            "restart_offset_bytes": 0,
            "range_or_resume_used": False,
        },
    })
    asset["state"] = "staging"
    replace_json(RECOVERY_CONTRACT_PATH, contract, f".{attempt_id}.started-tmp")

    try:
        opener = urllib.request.build_opener(NoRedirectHandler())
        request = urllib.request.Request(source_uri, headers={
            "Authorization": f"Bearer {access_value}",
            "User-Agent": "nepal-2026-controlled-intake/1.0",
            "Accept-Encoding": "identity",
        })
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
        if promoted != {"size_bytes": staged["size_bytes"], "sha256": staged["sha256"]}:
            raise TransferControlError("promoted_identity_differs_from_staged")
        if partial.stat().st_size != EXPECTED_PARTIAL_BYTES or sha256_file(partial) != EXPECTED_PARTIAL_SHA256:
            raise RecoveryControlError("retained_partial_changed_during_recovery")
        completed_at = now_utc()
        terminal_event = {
            "schema_version": "1.0",
            "event": "recovery_transfer_succeeded",
            "attempt_id": attempt_id,
            "asset_id": EXPECTED_ASSET_ID,
            "source_id": EXPECTED_SOURCE_ID,
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
            "restart_offset_bytes": 0,
            "range_or_resume_used": False,
            "retained_failed_attempt_preserved": True,
            "retained_partial_sha256_unchanged": True,
            "credential_value_recorded": False,
        }
        terminal_path = events_root / f"{attempt_id}-succeeded.json"
        write_new_json(terminal_path, terminal_event)
        public_receipt = RECEIPT_ROOT / f"{attempt_id}.json"
        write_new_json(public_receipt, terminal_event)
        refreshed = load(RECOVERY_CONTRACT_PATH)
        refreshed_asset = set_attempt_terminal(
            refreshed, attempt_id, completed_at, outcome="succeeded", failure_code=None
        )
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
            "retained_failed_attempt_preserved": True,
        })
        replace_json(RECOVERY_CONTRACT_PATH, refreshed, f".{attempt_id}.succeeded-tmp")
        print(json.dumps({
            "status": "promoted_pending_container_verification",
            "source_id": EXPECTED_SOURCE_ID,
            "attempt_id": attempt_id,
            "size_bytes": promoted["size_bytes"],
            "sha256": promoted["sha256"],
            "receipt": str(public_receipt.relative_to(ROOT)).replace("\\", "/"),
            "credential_value_recorded": False,
        }, indent=2))
        return 0
    except BaseException as exc:
        completed_at = now_utc()
        if isinstance(exc, (TransferControlError, RecoveryControlError)):
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
            "event": "recovery_transfer_failed",
            "attempt_id": attempt_id,
            "asset_id": EXPECTED_ASSET_ID,
            "source_id": EXPECTED_SOURCE_ID,
            "started_at": started_at,
            "completed_at": completed_at,
            "failure_code": failure_code,
            "partial_bytes_preserved": staging.stat().st_size if staging.exists() else 0,
            "original_failed_partial_preserved": partial.is_file(),
            "credential_value_recorded": False,
            "retry_automatically_authorized": False,
        }
        terminal_path = events_root / f"{attempt_id}-failed.json"
        write_new_json(terminal_path, terminal_event)
        public_receipt = RECEIPT_ROOT / f"{attempt_id}.json"
        write_new_json(public_receipt, terminal_event)
        refreshed = load(RECOVERY_CONTRACT_PATH)
        set_attempt_terminal(refreshed, attempt_id, completed_at, outcome="failed", failure_code=failure_code)
        replace_json(RECOVERY_CONTRACT_PATH, refreshed, f".{attempt_id}.failed-tmp")
        print(json.dumps({
            "status": "failed_preserved",
            "source_id": EXPECTED_SOURCE_ID,
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
    except (RecoveryControlError, TransferControlError) as exc:
        print(json.dumps({"status": "stopped", "code": exc.code, "mutations_performed": False}, indent=2))
        raise SystemExit(12)
