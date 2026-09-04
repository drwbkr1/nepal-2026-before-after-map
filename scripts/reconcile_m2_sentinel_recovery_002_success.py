#!/usr/bin/env python3
"""Reconcile a passing recovery-002 into the active intake after continuation."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from m2_sentinel_recovery_002_core import (
    CONTRACT_REF,
    EXPECTED_SOURCE_ID,
    ORIGINAL_ATTEMPT_ID,
    ROOT,
    Recovery002ControlError,
    load_object,
    now_utc,
    replace_json,
    require_exact_contract,
    sha256_file,
    verify_both_retained_partials,
    write_new_json,
)


ACTIVE_INTAKE_PATH = ROOT / "contracts/m2-intake.json"
RECOVERY_001_PATH = ROOT / "contracts/m2-sentinel-recovery.json"
RECOVERY_002_PATH = ROOT / CONTRACT_REF
CONTAINER_ROOT = ROOT / "records/acquisition/container-verification"
OUTPUT = ROOT / "records/acquisition/sentinel-recovery-002-success-reconciliation.json"
CONTINUATION_SOURCE_IDS = ("M1-SRC-005", "M1-SRC-006", "M1-SRC-008", "M1-SRC-010")


def _one_asset(intake: dict[str, Any], source_id: str) -> dict[str, Any]:
    assets = [item for item in intake.get("assets", []) if item.get("extensions", {}).get("source_id") == source_id]
    if len(assets) != 1:
        raise Recovery002ControlError("active_intake_source_identity_drift")
    return assets[0]


def _passing_container(source_id: str, attempt_id: str) -> Path:
    path = CONTAINER_ROOT / f"{source_id.casefold()}-{attempt_id}.json"
    if not path.is_file() or load_object(path).get("status") != "pass_container_only":
        raise Recovery002ControlError("required_container_receipt_not_passing")
    return path


def build_reconciled_intake(
    active: dict[str, Any], recovery: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    base_asset = _one_asset(active, EXPECTED_SOURCE_ID)
    if (
        base_asset.get("state") != "failed"
        or len(base_asset.get("attempts", [])) != 1
        or base_asset["attempts"][0].get("attempt_id") != ORIGINAL_ATTEMPT_ID
    ):
        raise Recovery002ControlError("original_failure_history_not_current")
    recovery_asset = require_exact_contract(recovery)
    successes = [item for item in recovery_asset.get("attempts", []) if item.get("outcome") == "succeeded"]
    if recovery_asset.get("state") != "promoted" or len(successes) != 1:
        raise Recovery002ControlError("recovery_002_success_history_invalid")
    recovery_attempt = successes[0]
    recovery_container = _passing_container(EXPECTED_SOURCE_ID, recovery_attempt["attempt_id"])

    continuation_receipts: dict[str, dict[str, str]] = {}
    for source_id in CONTINUATION_SOURCE_IDS:
        asset = _one_asset(active, source_id)
        successful = [item for item in asset.get("attempts", []) if item.get("outcome") == "succeeded"]
        if asset.get("state") != "promoted" or len(successful) != 1:
            raise Recovery002ControlError("continuation_not_fully_promoted")
        receipt = _passing_container(source_id, successful[0]["attempt_id"])
        continuation_receipts[source_id] = {
            "attempt_id": successful[0]["attempt_id"],
            "container_receipt_ref": str(receipt.relative_to(ROOT)).replace("\\", "/"),
            "container_receipt_sha256": sha256_file(receipt),
        }

    reconciled = copy.deepcopy(active)
    target = _one_asset(reconciled, EXPECTED_SOURCE_ID)
    target["attempts"].append(copy.deepcopy(recovery_attempt))
    target["state"] = "promoted"
    target["failure"] = None
    target["observed"] = copy.deepcopy(recovery_asset["observed"])
    target["extensions"].update({
        "successful_attempt_receipt": recovery_asset["extensions"]["successful_attempt_receipt"],
        "successful_attempt_receipt_sha256": recovery_asset["extensions"]["successful_attempt_receipt_sha256"],
        "provider_md5_verified": True,
        "provider_blake3_locally_verified": False,
        "satisfied_by_recovery_002": True,
        "recovery_002_contract_ref": CONTRACT_REF,
        "recovery_002_contract_sha256": sha256_file(RECOVERY_002_PATH),
        "retained_failed_attempt_count": 2,
    })
    details = {
        "recovery_attempt_id": recovery_attempt["attempt_id"],
        "recovery_container_receipt_ref": str(recovery_container.relative_to(ROOT)).replace("\\", "/"),
        "recovery_container_receipt_sha256": sha256_file(recovery_container),
        "continuation": continuation_receipts,
    }
    return reconciled, details


def reconcile_success() -> dict[str, Any]:
    if OUTPUT.exists():
        raise Recovery002ControlError("success_reconciliation_collision")
    active = load_object(ACTIVE_INTAKE_PATH)
    recovery_001 = load_object(RECOVERY_001_PATH)
    verify_both_retained_partials(active, recovery_001)
    recovery = load_object(RECOVERY_002_PATH)
    reconciled, details = build_reconciled_intake(active, recovery)
    before_sha = sha256_file(ACTIVE_INTAKE_PATH)
    nonce = f"recovery-002-success-{now_utc().replace(':', '').replace('-', '')}"
    replace_json(ACTIVE_INTAKE_PATH, reconciled, nonce)
    receipt = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-SENTINEL-RECOVERY-002-SUCCESS-RECONCILIATION-001",
        "recorded_at_utc": now_utc(),
        "status": "reconciled_recovery_002_and_four_success_only_continuations",
        "bindings": {
            "active_intake_sha256_before": before_sha,
            "active_intake_sha256_after": sha256_file(ACTIVE_INTAKE_PATH),
            "recovery_002_contract_ref": CONTRACT_REF,
            "recovery_002_contract_sha256": sha256_file(RECOVERY_002_PATH),
            **details,
        },
        "assertions": {
            "original_failed_attempt_preserved_in_history": True,
            "recovery_001_failed_attempt_preserved_externally": True,
            "all_five_products_container_verified": True,
            "automatic_retry_performed": False,
            "credential_values_read_or_recorded": False,
            "pixel_usability_established": False,
            "scientific_fitness_established": False,
        },
        "next_gate": "reconcile milestone state and begin separately governed pixel-readiness work",
    }
    write_new_json(OUTPUT, receipt)
    return receipt


if __name__ == "__main__":
    raise SystemExit("This reconciler is invoked only by the detached recovery-002 supervisor after all passing container receipts.")
