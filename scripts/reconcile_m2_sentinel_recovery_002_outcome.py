#!/usr/bin/env python3
"""Reconcile the successful recovery-002 and its stopped continuation boundary."""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT.parent / f"{ROOT.name}-data"
ACTIVE_INTAKE = ROOT / "contracts/m2-intake.json"
RECOVERY_CONTRACT = ROOT / "contracts/m2-sentinel-recovery-002.json"
TRANSFER_RECEIPT = ROOT / "records/acquisition/recovery-attempts/m1-src-004-recovery-002-20260905t002925z-cc1fe1e9.json"
CONTAINER_RECEIPT = ROOT / "records/acquisition/container-verification/m1-src-004-m1-src-004-recovery-002-20260905t002925z-cc1fe1e9.json"
OUTPUT = ROOT / "records/acquisition/sentinel-recovery-002-supervisor-reconciliation-001.json"

SUPERVISOR_ID = "m2-sentinel-recovery-002-20260905t002910z-a5e736c9"
ATTEMPT_ID = "m1-src-004-recovery-002-20260905t002925z-cc1fe1e9"
SOURCE_ID = "M1-SRC-004"
DESTINATION = DATA_ROOT / "custody/products/m1-src-004/S1D_IW_GRDH_1SDV_20260828T122116_20260828T122141_004326_007FA4_C523.SAFE.zip"
DESTINATION_SIZE = 1_732_332_897
DESTINATION_SHA256 = "a606cac063cc23e60a623f020192fc097d327f3dafadf1115802b2a458eaceab"
ORIGINAL_PARTIAL = DATA_ROOT / ".intake-staging/nepal-m2-intake-001/m1-src-004/S1D_IW_GRDH_1SDV_20260828T122116_20260828T122141_004326_007FA4_C523.SAFE.zip.part"
ORIGINAL_PARTIAL_SIZE = 561_593_598
ORIGINAL_PARTIAL_SHA256 = "299b2d07ccb58747cce43ae3b18e6d25c1c6d72a5653831b50a44ca72677ea66"
RECOVERY_001_PARTIAL = DATA_ROOT / ".intake-staging/nepal-m2-sentinel-recovery-001/m1-src-004-recovery-001/S1D_IW_GRDH_1SDV_20260828T122116_20260828T122141_004326_007FA4_C523.SAFE.zip.part"
RECOVERY_001_PARTIAL_SIZE = 1_333_788_672
RECOVERY_001_PARTIAL_SHA256 = "c2d3a878f98615ddaa5e0bf21df5eb5f65c591719cb26b5f43b361aa4eac4cac"
SUPERVISOR_ROOT = DATA_ROOT / "derived/m2-sentinel-recovery-002-supervisor" / SUPERVISOR_ID
SUPERVISOR_STARTED = SUPERVISOR_ROOT / f"{SUPERVISOR_ID}-started.json"
SUPERVISOR_HEARTBEAT = SUPERVISOR_ROOT / f"{SUPERVISOR_ID}-heartbeat.json"
SUPERVISOR_TERMINAL = SUPERVISOR_ROOT / f"{SUPERVISOR_ID}-failed.json"
CONTINUATION_SOURCE_IDS = ("M1-SRC-005", "M1-SRC-006", "M1-SRC-008", "M1-SRC-010")


class ReconciliationError(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ReconciliationError(f"not_object:{path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def replace(path: Path, value: dict[str, Any], nonce: str) -> None:
    temporary = path.with_name(f"{path.name}.{nonce}.tmp")
    with temporary.open("xb") as handle:
        handle.write(canonical(value))
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def write_new(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(canonical(value))
        handle.flush()
        os.fsync(handle.fileno())


def exact_file(path: Path, size: int, digest: str, label: str) -> None:
    if not path.is_file() or path.stat().st_size != size or sha256(path) != digest:
        raise ReconciliationError(f"{label}_identity_drift")


def one_asset(intake: dict[str, Any], source_id: str) -> dict[str, Any]:
    matches = [a for a in intake.get("assets", []) if a.get("extensions", {}).get("source_id") == source_id]
    if len(matches) != 1:
        raise ReconciliationError(f"asset_identity_drift:{source_id}")
    return matches[0]


def main() -> int:
    if OUTPUT.exists():
        raise ReconciliationError("reconciliation_collision")

    exact_file(DESTINATION, DESTINATION_SIZE, DESTINATION_SHA256, "promoted_destination")
    exact_file(ORIGINAL_PARTIAL, ORIGINAL_PARTIAL_SIZE, ORIGINAL_PARTIAL_SHA256, "original_partial")
    exact_file(RECOVERY_001_PARTIAL, RECOVERY_001_PARTIAL_SIZE, RECOVERY_001_PARTIAL_SHA256, "recovery_001_partial")

    transfer = load(TRANSFER_RECEIPT)
    container = load(CONTAINER_RECEIPT)
    started = load(SUPERVISOR_STARTED)
    heartbeat = load(SUPERVISOR_HEARTBEAT)
    terminal = load(SUPERVISOR_TERMINAL)
    if (
        transfer.get("event") != "recovery_002_transfer_succeeded"
        or transfer.get("attempt_id") != ATTEMPT_ID
        or transfer.get("local_size_bytes") != DESTINATION_SIZE
        or transfer.get("local_sha256") != DESTINATION_SHA256
        or transfer.get("provider_md5_match") is not True
        or container.get("status") != "pass_container_only"
        or container.get("attempt_id") != ATTEMPT_ID
        or container.get("result", {}).get("local_sha256") != DESTINATION_SHA256
        or terminal.get("event") != "supervisor_failed"
        or terminal.get("supervisor_id") != SUPERVISOR_ID
        or terminal.get("phase") != "continuation_live_preflight"
        or terminal.get("terminal_code") != "unexpected_supervisor_failure"
        or terminal.get("retry_automatically_authorized") is not False
    ):
        raise ReconciliationError("recovery_or_supervisor_evidence_drift")

    absent_paths: list[str] = []
    for source_id in CONTINUATION_SOURCE_IDS:
        key = source_id.casefold()
        paths = [
            DATA_ROOT / f".intake-staging/nepal-m2-intake-001/{key}",
            DATA_ROOT / f".intake-staging/nepal-m2-intake-001/attempt-events/{key}",
            DATA_ROOT / f"custody/products/{key}",
        ]
        for path in paths:
            if path.exists():
                raise ReconciliationError(f"continuation_path_exists:{source_id}:{path}")
            absent_paths.append(str(path))

    active = load(ACTIVE_INTAKE)
    recovery = load(RECOVERY_CONTRACT)
    base = one_asset(active, SOURCE_ID)
    recovery_assets = recovery.get("assets", [])
    if (
        base.get("state") != "failed"
        or len(base.get("attempts", [])) != 1
        or base["attempts"][0].get("attempt_id") != "m1-src-004-20260904t043930z-ac125c11"
        or len(recovery_assets) != 1
        or recovery_assets[0].get("state") != "promoted"
    ):
        raise ReconciliationError("intake_history_drift")
    recovery_asset = recovery_assets[0]
    successful = [a for a in recovery_asset.get("attempts", []) if a.get("outcome") == "succeeded"]
    if len(successful) != 1 or successful[0].get("attempt_id") != ATTEMPT_ID:
        raise ReconciliationError("recovery_success_history_drift")

    before_active_sha = sha256(ACTIVE_INTAKE)
    before_recovery_sha = sha256(RECOVERY_CONTRACT)
    reconciled_active = copy.deepcopy(active)
    target = one_asset(reconciled_active, SOURCE_ID)
    target["attempts"].append(copy.deepcopy(successful[0]))
    target["state"] = "promoted"
    target["failure"] = None
    target["observed"] = copy.deepcopy(recovery_asset["observed"])
    target["extensions"].update({
        "successful_attempt_receipt": str(TRANSFER_RECEIPT.relative_to(ROOT)).replace("\\", "/"),
        "successful_attempt_receipt_sha256": sha256(TRANSFER_RECEIPT),
        "container_receipt": str(CONTAINER_RECEIPT.relative_to(ROOT)).replace("\\", "/"),
        "container_receipt_sha256": sha256(CONTAINER_RECEIPT),
        "provider_md5_verified": True,
        "provider_blake3_locally_verified": False,
        "satisfied_by_recovery_002": True,
        "recovery_002_contract_ref": str(RECOVERY_CONTRACT.relative_to(ROOT)).replace("\\", "/"),
        "recovery_002_contract_sha256_at_recovery_success": before_recovery_sha,
        "retained_failed_attempt_count": 2,
    })
    reconciled_active["extensions"]["status"] = "active_four_promoted_four_authorized_continuation_review_required"

    reconciled_recovery = copy.deepcopy(recovery)
    reconciled_recovery["extensions"].update({
        "status": "promoted_container_pass_continuation_stopped_pre_attempt_new_review_required",
        "container_receipt_ref": str(CONTAINER_RECEIPT.relative_to(ROOT)).replace("\\", "/"),
        "container_receipt_sha256": sha256(CONTAINER_RECEIPT),
        "supervisor_terminal_event": str(SUPERVISOR_TERMINAL),
        "supervisor_terminal_event_sha256": sha256(SUPERVISOR_TERMINAL),
        "continuation_attempt_started": False,
        "continuation_payload_request_performed": False,
        "automatic_retry_authorized": False,
    })

    replace(ACTIVE_INTAKE, reconciled_active, "recovery-002-outcome")
    replace(RECOVERY_CONTRACT, reconciled_recovery, "recovery-002-outcome")

    receipt = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-SENTINEL-RECOVERY-002-SUPERVISOR-RECONCILIATION-001",
        "recorded_at_utc": "2026-09-05T00:36:32Z",
        "status": "recovery_and_container_pass_continuation_stopped_before_attempt_cause_unknown",
        "recovery": {
            "source_id": SOURCE_ID,
            "attempt_id": ATTEMPT_ID,
            "transfer_receipt_ref": str(TRANSFER_RECEIPT.relative_to(ROOT)).replace("\\", "/"),
            "transfer_receipt_sha256": sha256(TRANSFER_RECEIPT),
            "container_receipt_ref": str(CONTAINER_RECEIPT.relative_to(ROOT)).replace("\\", "/"),
            "container_receipt_sha256": sha256(CONTAINER_RECEIPT),
            "destination_path": str(DESTINATION),
            "destination_size_bytes": DESTINATION_SIZE,
            "destination_sha256": DESTINATION_SHA256,
            "provider_md5_match": True,
            "container_status": "pass_container_only",
        },
        "supervisor": {
            "supervisor_id": SUPERVISOR_ID,
            "started_event_path": str(SUPERVISOR_STARTED),
            "started_event_sha256": sha256(SUPERVISOR_STARTED),
            "last_heartbeat_path": str(SUPERVISOR_HEARTBEAT),
            "last_heartbeat_sha256": sha256(SUPERVISOR_HEARTBEAT),
            "terminal_event_path": str(SUPERVISOR_TERMINAL),
            "terminal_event_sha256": sha256(SUPERVISOR_TERMINAL),
            "terminal_phase": "continuation_live_preflight",
            "terminal_code": "unexpected_supervisor_failure",
            "exact_cause_established": False,
            "exception_message_recorded": False,
        },
        "retained_failures": [
            {"attempt_id": "m1-src-004-20260904t043930z-ac125c11", "partial_size_bytes": ORIGINAL_PARTIAL_SIZE, "partial_sha256": ORIGINAL_PARTIAL_SHA256},
            {"attempt_id": "m1-src-004-recovery-001-20260904t201220z-e4388c64", "partial_size_bytes": RECOVERY_001_PARTIAL_SIZE, "partial_sha256": RECOVERY_001_PARTIAL_SHA256},
        ],
        "continuation_boundary": {
            "source_ids": list(CONTINUATION_SOURCE_IDS),
            "attempt_count": 0,
            "payload_request_count": 0,
            "staging_event_and_destination_paths_verified_absent": absent_paths,
            "automatic_retry_authorized": False,
            "new_exact_review_required": True,
        },
        "contract_reconciliation": {
            "active_intake_sha256_before": before_active_sha,
            "active_intake_sha256_after": sha256(ACTIVE_INTAKE),
            "recovery_002_contract_sha256_before": before_recovery_sha,
            "recovery_002_contract_sha256_after": sha256(RECOVERY_CONTRACT),
            "m1_src_004_satisfied_only_by_recovery_002": True,
            "historical_failed_attempts_preserved": True,
        },
        "assertions": {
            "credential_value_recorded": False,
            "recovery_retried": False,
            "continuation_attempt_started": False,
            "continuation_payload_request_performed": False,
            "pixel_usability_established": False,
            "scientific_fitness_established": False,
        },
        "limitations": [
            "The recovery transfer and container check passed; the overall supervisor terminal state is still a failure because continuation stopped.",
            "The generic terminal code does not preserve the underlying exception type or message, so the exact continuation preflight cause is unknown.",
            "A later successful read-only check would not prove what failed at the recorded terminal time.",
            "Container verification establishes no raster readability, usable AOI pixels, registration, or scientific change.",
        ],
        "next_gate": "M2-SENTINEL-CONTINUATION-001-REVIEW",
    }
    write_new(OUTPUT, receipt)
    print(json.dumps({"status": receipt["status"], "receipt": str(OUTPUT.relative_to(ROOT)).replace("\\", "/"), "receipt_sha256": sha256(OUTPUT)}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconciliationError as exc:
        print(json.dumps({"status": "stopped", "code": str(exc), "automatic_retry_authorized": False}, indent=2))
        raise SystemExit(12)
