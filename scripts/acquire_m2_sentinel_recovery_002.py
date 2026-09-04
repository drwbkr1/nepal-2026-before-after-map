#!/usr/bin/env python3
"""Run the one approved recovery-002 transfer with an in-memory token."""

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

from acquire_m2_product import DOWNLOAD_HOST, live_page_consistency_check, now_utc, public_catalog_check
from m2_sentinel_recovery_002_core import (
    APPROVAL_REF,
    CONTRACT_REF,
    DATA_ROOT,
    EXPECTED_APPROVAL_SHA256,
    EXPECTED_ASSET_ID,
    EXPECTED_BUNDLE_SHA256,
    EXPECTED_INTAKE_ID,
    EXPECTED_PROPOSAL_SHA256,
    EXPECTED_RECONCILIATION_SHA256,
    EXPECTED_SOURCE_ID,
    FINAL_PREFLIGHT_REF,
    PUBLICATION_GATE_REF,
    RECONCILIATION_REF,
    ROOT,
    SECRET_REFERENCE,
    ORIGINAL_ATTEMPT_ID,
    ORIGINAL_PARTIAL_BYTES,
    ORIGINAL_PARTIAL_SHA256,
    RECOVERY_001_ATTEMPT_ID,
    RECOVERY_001_PARTIAL_BYTES,
    RECOVERY_001_PARTIAL_SHA256,
    Recovery002ControlError,
    load_object,
    require_exact_contract,
    require_fresh_authorized_attempt,
    sha256_file,
    validate_approval,
    validate_secret,
    verify_both_retained_partials,
)
from m2_transfer_core import (
    NoRedirectHandler,
    TransferControlError,
    ensure_directory,
    promote_atomic_no_replace,
    replace_json,
    require_safe_child,
    write_new_json,
)


PROJECT_ROOT = ROOT.parent.resolve()
RECOVERY_CONTRACT_PATH = ROOT / CONTRACT_REF
ACTIVE_INTAKE_PATH = ROOT / "contracts/m2-intake.json"
RECOVERY_001_CONTRACT_PATH = ROOT / "contracts/m2-sentinel-recovery.json"
BASE_APPROVAL_PATH = ROOT / "records/source-gates/m2-activation-approval.json"
RECOVERY_APPROVAL_PATH = ROOT / APPROVAL_REF
REVIEW_RECONCILIATION_PATH = ROOT / RECONCILIATION_REF
PROPOSAL_PATH = ROOT / "contracts/milestone-002-sentinel-recovery-002-proposal.json"
BUNDLE_PATH = ROOT / "reviews/m2-sentinel-recovery-002/review-bundle.json"
PREFLIGHT_PATH = ROOT / "records/acquisition/preflight.json"
PREFLIGHT_REFRESH_PATH = ROOT / "records/acquisition/preflight-refresh.json"
SOURCE_GATE_REFRESH_PATH = ROOT / "records/source-gates/m2-live-source-gate-refresh.json"
TERMS_RECONCILIATION_PATH = ROOT / "records/source-gates/m2-terms-page-reconciliation.json"
PLAN_PATH = ROOT / "records/acquisition-plan.json"
PUBLICATION_GATE_PATH = ROOT / PUBLICATION_GATE_REF
FINAL_PREFLIGHT_PATH = ROOT / FINAL_PREFLIGHT_REF
RECEIPT_ROOT = ROOT / "records/acquisition/recovery-attempts"


def stream_to_exclusive_staging_with_progress(
    response: Any,
    staging: Path,
    *,
    expected_size: int,
    expected_md5: str,
    progress_callback: Callable[[int], None] | None = None,
) -> dict[str, Any]:
    """Stream one response to a new file and verify it without touching legacy code."""
    sha256_digest = hashlib.sha256()
    md5_digest = hashlib.md5(usedforsecurity=False)
    size = 0
    try:
        with staging.open("xb") as handle:
            while True:
                block = response.read(8 * 1024 * 1024)
                if not block:
                    break
                handle.write(block)
                sha256_digest.update(block)
                md5_digest.update(block)
                size += len(block)
                if progress_callback is not None:
                    progress_callback(size)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise TransferControlError("staging_collision") from exc
    if size != expected_size:
        raise TransferControlError("transferred_size_mismatch")
    observed_md5 = md5_digest.hexdigest()
    if observed_md5.casefold() != expected_md5.casefold():
        raise TransferControlError("provider_md5_mismatch")
    return {"size_bytes": size, "sha256": sha256_digest.hexdigest(), "md5": observed_md5}


def current_git_identity() -> tuple[str, str]:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    origin = subprocess.run(["git", "rev-parse", "origin/main"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    return head, origin


def build_attempt_id(started_at: str, nonce: str) -> str:
    return f"{EXPECTED_ASSET_ID}-{started_at.replace(':', '').replace('-', '')}-{nonce}".lower()


def validate_publication_gate(gate: dict[str, Any]) -> None:
    head, origin = current_git_identity()
    bound_files = {
        "approval_sha256": RECOVERY_APPROVAL_PATH,
        "review_reconciliation_sha256": REVIEW_RECONCILIATION_PATH,
        "activation_script_sha256": ROOT / "scripts/activate_m2_sentinel_recovery_002.py",
        "core_sha256": ROOT / "scripts/m2_sentinel_recovery_002_core.py",
        "broker_sha256": ROOT / "scripts/m2_sentinel_recovery_002_broker.py",
        "supervisor_sha256": ROOT / "scripts/m2_sentinel_recovery_002_supervisor.py",
        "recovery_runner_sha256": ROOT / "scripts/acquire_m2_sentinel_recovery_002.py",
        "continuation_runner_sha256": ROOT / "scripts/acquire_m2_product_pipe.py",
        "container_verifier_sha256": ROOT / "scripts/verify_m2_sentinel_recovery_002_container.py",
        "final_preflight_sha256": ROOT / "scripts/preflight_m2_sentinel_recovery_002.py",
        "supervisor_reconciler_sha256": ROOT / "scripts/reconcile_m2_sentinel_recovery_002_supervisor.py",
        "success_reconciler_sha256": ROOT / "scripts/reconcile_m2_sentinel_recovery_002_success.py",
        "tests_sha256": ROOT / "tests/test_m2_sentinel_recovery_002.py",
        "implementation_readiness_sha256": ROOT / "records/acquisition/sentinel-recovery-002-implementation-readiness.json",
        "implementation_readiness_recorder_sha256": ROOT / "scripts/record_m2_sentinel_recovery_002_implementation_readiness.py",
    }
    if (
        gate.get("status") != "pass_public_controls_verified_before_recovery_002"
        or gate.get("github_actions", {}).get("conclusion") != "success"
        or gate.get("github_actions", {}).get("head_sha") != head
        or head != origin
        or gate.get("assertions", {}).get("real_recovery_started") is not False
        or gate.get("bindings") != {key: sha256_file(path) for key, path in bound_files.items()}
    ):
        raise Recovery002ControlError("recovery_002_publication_gate_drift")


def set_attempt_terminal(
    contract: dict[str, Any],
    attempt_id: str,
    completed_at: str,
    *,
    outcome: str,
    failure_code: str | None,
) -> dict[str, Any]:
    asset = require_exact_contract(contract)
    attempt = next((item for item in asset["attempts"] if item.get("attempt_id") == attempt_id), None)
    if attempt is None:
        raise Recovery002ControlError("recovery_002_attempt_missing")
    attempt["completed_at"] = completed_at
    attempt["outcome"] = outcome
    if outcome == "failed":
        asset["state"] = "failed"
        asset["failure"] = {"code": failure_code, "recorded_at": completed_at}
        contract["extensions"]["status"] = "terminal_recovery_002_failure_new_review_required"
    elif outcome == "succeeded":
        asset["state"] = "promoted"
        asset["failure"] = None
        contract["extensions"]["status"] = "promoted_pending_container_verification"
    else:
        raise Recovery002ControlError("recovery_002_terminal_outcome_invalid")
    return asset


def validate_preconditions(access_value: str) -> tuple[dict[str, Any], dict[str, Any], Path, Path, Path, Path]:
    validate_secret(access_value)
    if sha256_file(BUNDLE_PATH) != EXPECTED_BUNDLE_SHA256 or sha256_file(PROPOSAL_PATH) != EXPECTED_PROPOSAL_SHA256:
        raise Recovery002ControlError("recovery_002_review_identity_drift")
    if sha256_file(RECOVERY_APPROVAL_PATH) != EXPECTED_APPROVAL_SHA256:
        raise Recovery002ControlError("recovery_002_approval_hash_drift")
    if sha256_file(REVIEW_RECONCILIATION_PATH) != EXPECTED_RECONCILIATION_SHA256:
        raise Recovery002ControlError("recovery_002_reconciliation_hash_drift")
    approval = load_object(RECOVERY_APPROVAL_PATH)
    reconciliation = load_object(REVIEW_RECONCILIATION_PATH)
    validate_approval(approval, reconciliation)
    contract = load_object(RECOVERY_CONTRACT_PATH)
    asset = require_exact_contract(contract)
    require_fresh_authorized_attempt(asset)
    gate = load_object(PUBLICATION_GATE_PATH)
    validate_publication_gate(gate)
    final_preflight = load_object(FINAL_PREFLIGHT_PATH)
    active_intake = load_object(ACTIVE_INTAKE_PATH)
    recovery_001 = load_object(RECOVERY_001_CONTRACT_PATH)
    original_partial, recovery_001_partial = verify_both_retained_partials(active_intake, recovery_001)
    if (
        final_preflight.get("status") != "pass_no_payload_ready_for_single_secret_pipe_handoff"
        or final_preflight.get("bindings", {}).get("approval_sha256") != sha256_file(RECOVERY_APPROVAL_PATH)
        or final_preflight.get("bindings", {}).get("publication_gate_sha256") != sha256_file(PUBLICATION_GATE_PATH)
        or final_preflight.get("bindings", {}).get("recovery_contract_sha256") != sha256_file(RECOVERY_CONTRACT_PATH)
        or final_preflight.get("bindings", {}).get("active_intake_sha256") != sha256_file(ACTIVE_INTAKE_PATH)
        or final_preflight.get("bindings", {}).get("recovery_001_contract_sha256") != sha256_file(RECOVERY_001_CONTRACT_PATH)
        or final_preflight.get("assertions", {}).get("credential_values_read_or_recorded") is not False
    ):
        raise Recovery002ControlError("recovery_002_final_preflight_drift")
    custody_root = (PROJECT_ROOT / Path(*PurePosixPath(contract["custody_root"]).parts)).resolve(strict=True)
    staging_parent = (DATA_ROOT / ".intake-staging").resolve(strict=True)
    staging_root = (PROJECT_ROOT / Path(*PurePosixPath(contract["staging_root"]).parts)).resolve(strict=False)
    destination = require_safe_child(custody_root, custody_root / Path(*PurePosixPath(asset["destination_relative_path"]).parts))
    staging = staging_root / Path(*PurePosixPath(asset["staging_relative_path"]).parts)
    if destination.exists() or staging_root.exists() or staging.exists():
        raise Recovery002ControlError("recovery_002_destination_or_staging_collision")
    return contract, asset, original_partial, recovery_001_partial, destination, staging_parent


def run_recovery(
    access_value: str,
    *,
    progress: Callable[[str, str | None, int | None], None] | None = None,
) -> dict[str, Any]:
    contract, asset, original_partial, recovery_001_partial, destination, staging_parent = validate_preconditions(access_value)
    base_approval = load_object(BASE_APPROVAL_PATH)
    preflight = load_object(PREFLIGHT_PATH)
    preflight_refresh = load_object(PREFLIGHT_REFRESH_PATH)
    plan = load_object(PLAN_PATH)
    if base_approval.get("status") != "approved" or preflight.get("status") != "pass_no_external_mutation":
        raise Recovery002ControlError("base_m2_authority_or_preflight_drift")
    if (
        preflight_refresh.get("status") != "pass_no_external_mutation"
        or preflight_refresh.get("base_preflight", {}).get("sha256") != sha256_file(PREFLIGHT_PATH)
        or preflight_refresh.get("source_gate", {}).get("sha256") != sha256_file(SOURCE_GATE_REFRESH_PATH)
        or preflight_refresh.get("terms_reconciliation", {}).get("sha256") != sha256_file(TERMS_RECONCILIATION_PATH)
        or preflight_refresh.get("authority", {}).get("approval_sha256") != sha256_file(BASE_APPROVAL_PATH)
    ):
        raise Recovery002ControlError("m2_preflight_refresh_binding_drift")
    matching_plan = [item for item in plan.get("records", []) if item.get("source_id") == EXPECTED_SOURCE_ID]
    if len(matching_plan) != 1:
        raise Recovery002ControlError("recovery_002_source_not_bound_once")
    source_uri = asset["source"]["uri"]
    parsed = urlsplit(source_uri)
    if parsed.scheme != "https" or parsed.hostname != DOWNLOAD_HOST or parsed.query or parsed.fragment:
        raise Recovery002ControlError("download_route_outside_reviewed_boundary")
    if shutil.disk_usage(PROJECT_ROOT).free / (1024 ** 3) < float(preflight["storage"]["minimum_free_gib"]):
        raise Recovery002ControlError("free_space_below_approved_minimum")

    if progress:
        progress("live_preflight", None, 0)
    page_observations = live_page_consistency_check(preflight_refresh)
    catalog = public_catalog_check(asset, matching_plan[0])
    staging_root = DATA_ROOT / ".intake-staging" / EXPECTED_INTAKE_ID
    ensure_directory(staging_root, staging_parent)
    staging = require_safe_child(staging_root, staging_root / Path(*PurePosixPath(asset["staging_relative_path"]).parts))
    ensure_directory(staging.parent, staging_root)
    ensure_directory(destination.parent, (DATA_ROOT / "custody").resolve(strict=True))
    events_root = staging_root / "attempt-events" / EXPECTED_ASSET_ID
    ensure_directory(events_root, staging_root)

    started_at = now_utc()
    attempt_id = build_attempt_id(started_at, uuid.uuid4().hex[:8])
    started_event_path = events_root / f"{attempt_id}-started.json"
    started_event = {
        "schema_version": "1.0",
        "event": "recovery_002_transfer_started",
        "attempt_id": attempt_id,
        "asset_id": EXPECTED_ASSET_ID,
        "source_id": EXPECTED_SOURCE_ID,
        "started_at": started_at,
        "source_uri": source_uri,
        "catalog_response_sha256": catalog["response_sha256"],
        "official_page_observations": page_observations,
        "expected_catalog_size_bytes": catalog["content_length_bytes"],
        "credential_reference": SECRET_REFERENCE,
        "credential_value_recorded": False,
        "restart_offset_bytes": 0,
        "range_or_resume_used": False,
        "retained_failed_attempt_ids": [ORIGINAL_ATTEMPT_ID, RECOVERY_001_ATTEMPT_ID],
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
            "credential_reference": SECRET_REFERENCE,
            "credential_value_recorded": False,
            "restart_offset_bytes": 0,
            "range_or_resume_used": False,
        },
    })
    asset["state"] = "staging"
    contract["extensions"]["status"] = "staging_one_attempt_active"
    replace_json(RECOVERY_CONTRACT_PATH, contract, f".{attempt_id}.started-tmp")
    if progress:
        progress("transfer", attempt_id, 0)

    try:
        opener = urllib.request.build_opener(NoRedirectHandler())
        request = urllib.request.Request(source_uri, headers={
            "Authorization": f"Bearer {access_value}",
            "User-Agent": "nepal-2026-controlled-intake/2.0",
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

            def callback(size: int) -> None:
                if progress:
                    progress("transfer", attempt_id, size)

            staged = stream_to_exclusive_staging_with_progress(
                response,
                staging,
                expected_size=catalog["content_length_bytes"],
                expected_md5=catalog["provider_md5"],
                progress_callback=callback,
            )
        if progress:
            progress("promotion", attempt_id, staged["size_bytes"])
        if (
            original_partial.stat().st_size != ORIGINAL_PARTIAL_BYTES
            or sha256_file(original_partial) != ORIGINAL_PARTIAL_SHA256
            or recovery_001_partial.stat().st_size != RECOVERY_001_PARTIAL_BYTES
            or sha256_file(recovery_001_partial) != RECOVERY_001_PARTIAL_SHA256
        ):
            raise Recovery002ControlError("retained_partial_changed_during_recovery_002")
        promoted = promote_atomic_no_replace(staging, destination)
        if promoted != {"size_bytes": staged["size_bytes"], "sha256": staged["sha256"]}:
            raise TransferControlError("promoted_identity_differs_from_staged")
        completed_at = now_utc()
        terminal_event = {
            "schema_version": "1.0",
            "event": "recovery_002_transfer_succeeded",
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
            "retained_failure_count": 2,
            "retained_partials_unchanged": True,
            "credential_value_recorded": False,
        }
        terminal_path = events_root / f"{attempt_id}-succeeded.json"
        write_new_json(terminal_path, terminal_event)
        public_receipt = RECEIPT_ROOT / f"{attempt_id}.json"
        write_new_json(public_receipt, terminal_event)
        refreshed = load_object(RECOVERY_CONTRACT_PATH)
        refreshed_asset = set_attempt_terminal(refreshed, attempt_id, completed_at, outcome="succeeded", failure_code=None)
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
            "retained_failure_count": 2,
            "retained_partials_unchanged": True,
        })
        replace_json(RECOVERY_CONTRACT_PATH, refreshed, f".{attempt_id}.succeeded-tmp")
        return {"returncode": 0, "status": "promoted_pending_container_verification", "source_id": EXPECTED_SOURCE_ID, "attempt_id": attempt_id, "receipt": str(public_receipt.relative_to(ROOT)).replace("\\", "/")}
    except Exception as exc:
        completed_at = now_utc()
        if isinstance(exc, (TransferControlError, Recovery002ControlError)):
            failure_code = exc.code
        elif isinstance(exc, urllib.error.HTTPError):
            failure_code = "redirect_or_http_status_rejected"
        elif isinstance(exc, (urllib.error.URLError, TimeoutError, ConnectionError)):
            failure_code = "provider_transport_failure"
        else:
            failure_code = "unexpected_transfer_failure"
        terminal_event = {
            "schema_version": "1.0",
            "event": "recovery_002_transfer_failed",
            "attempt_id": attempt_id,
            "asset_id": EXPECTED_ASSET_ID,
            "source_id": EXPECTED_SOURCE_ID,
            "started_at": started_at,
            "completed_at": completed_at,
            "failure_code": failure_code,
            "partial_bytes_preserved": staging.stat().st_size if staging.exists() else 0,
            "prior_failure_count_preserved": 2,
            "credential_value_recorded": False,
            "retry_automatically_authorized": False,
        }
        terminal_path = events_root / f"{attempt_id}-failed.json"
        write_new_json(terminal_path, terminal_event)
        public_receipt = RECEIPT_ROOT / f"{attempt_id}.json"
        write_new_json(public_receipt, terminal_event)
        refreshed = load_object(RECOVERY_CONTRACT_PATH)
        set_attempt_terminal(refreshed, attempt_id, completed_at, outcome="failed", failure_code=failure_code)
        replace_json(RECOVERY_CONTRACT_PATH, refreshed, f".{attempt_id}.failed-tmp")
        return {"returncode": 20, "status": "failed_preserved", "source_id": EXPECTED_SOURCE_ID, "attempt_id": attempt_id, "failure_code": failure_code, "receipt": str(public_receipt.relative_to(ROOT)).replace("\\", "/")}


if __name__ == "__main__":
    raise SystemExit("This module accepts a credential only from the detached supervisor in memory; use m2_sentinel_recovery_002_broker.py.")
