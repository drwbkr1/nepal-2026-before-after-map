#!/usr/bin/env python3
"""Verify the promoted M1-SRC-004 recovery archive without network or extraction."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from typing import Any

import prepare_m2_verification as verification
from acquire_m2_sentinel_recovery import (
    ACTIVE_INTAKE_PATH,
    FAILED_RECEIPT_PATH,
    RECOVERY_APPROVAL_PATH,
    RECOVERY_CONTRACT_PATH,
    verify_original_failure_unchanged,
)
from m2_sentinel_recovery_core import EXPECTED_SOURCE_ID, RecoveryControlError, require_exact_recovery_contract


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent.resolve()
VERIFICATION_CONTRACT_PATH = ROOT / "contracts/m2-offline-verification.json"
RECEIPT_ROOT = ROOT / "records/acquisition/container-verification"


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RecoveryControlError("control_root_not_object")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_new(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(verification.canonical_bytes(value))
        handle.flush()
        os.fsync(handle.fileno())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--scanned-at-utc", required=True)
    args = parser.parse_args()
    if args.source_id != EXPECTED_SOURCE_ID:
        raise RecoveryControlError("recovery_source_outside_exact_approval")

    recovery = load(RECOVERY_CONTRACT_PATH)
    recovery_asset = require_exact_recovery_contract(recovery)
    active_intake = load(ACTIVE_INTAKE_PATH)
    failed_receipt = load(FAILED_RECEIPT_PATH)
    retained_partial = verify_original_failure_unchanged(active_intake, failed_receipt)
    approval = load(RECOVERY_APPROVAL_PATH)
    verification_contract = load(VERIFICATION_CONTRACT_PATH)
    if recovery_asset.get("state") != "promoted":
        raise RecoveryControlError("recovery_asset_not_promoted")
    succeeded = [attempt for attempt in recovery_asset.get("attempts", []) if attempt.get("outcome") == "succeeded"]
    if len(succeeded) != 1:
        raise RecoveryControlError("recovery_success_history_invalid")
    if approval.get("status") != "approved_exact_bounded_fresh_byte_zero_recovery":
        raise RecoveryControlError("recovery_approval_not_active")
    source_assets = [
        asset for asset in verification_contract.get("assets", [])
        if asset.get("source_id") == EXPECTED_SOURCE_ID
    ]
    if len(source_assets) != 1:
        raise RecoveryControlError("verification_source_not_bound_once")

    custody_root = (PROJECT_ROOT / Path(*PurePosixPath(recovery["custody_root"]).parts)).resolve(strict=True)
    archive = (custody_root / Path(*PurePosixPath(recovery_asset["destination_relative_path"]).parts)).resolve(strict=False)
    try:
        archive.relative_to(custody_root)
    except ValueError as exc:
        raise RecoveryControlError("recovery_archive_outside_custody") from exc
    if not archive.is_file():
        raise RecoveryControlError("recovery_promoted_archive_missing")

    attempt_id = succeeded[0]["attempt_id"]
    output = RECEIPT_ROOT / f"m1-src-004-{attempt_id}.json"
    if output.exists():
        raise RecoveryControlError("recovery_container_receipt_collision")
    result = verification.scan_archive(source_assets[0], archive, verification_contract["archive_controls"])
    observed = recovery_asset.get("observed", {})
    if result.get("local_sha256") != observed.get("promoted_sha256"):
        result["errors"].append("local SHA-256 differs from recovery intake promoted identity")
    if result.get("local_size_bytes") != observed.get("promoted_size_bytes"):
        result["errors"].append("local size differs from recovery intake promoted identity")
    if result["errors"]:
        result["status"] = "block"
        result["eligible_for_post_container_qa"] = False
    transfer_ref = recovery_asset.get("extensions", {}).get("successful_attempt_receipt")
    transfer_path = ROOT / transfer_ref if isinstance(transfer_ref, str) else None
    if transfer_path is None or not transfer_path.is_file():
        raise RecoveryControlError("recovery_transfer_receipt_missing")

    receipt = {
        "receipt_version": "1.0",
        "receipt_id": f"NEPAL-M2-CONTAINER-RECOVERY-{EXPECTED_SOURCE_ID}-{attempt_id}",
        "scanned_at_utc": args.scanned_at_utc,
        "status": result["status"],
        "source_id": EXPECTED_SOURCE_ID,
        "attempt_id": attempt_id,
        "bindings": {
            "verification_contract_ref": str(VERIFICATION_CONTRACT_PATH.relative_to(ROOT)).replace("\\", "/"),
            "verification_contract_sha256": sha256(VERIFICATION_CONTRACT_PATH),
            "recovery_intake_ref": str(RECOVERY_CONTRACT_PATH.relative_to(ROOT)).replace("\\", "/"),
            "recovery_intake_sha256_at_scan": sha256(RECOVERY_CONTRACT_PATH),
            "recovery_approval_ref": str(RECOVERY_APPROVAL_PATH.relative_to(ROOT)).replace("\\", "/"),
            "recovery_approval_sha256": sha256(RECOVERY_APPROVAL_PATH),
            "transfer_receipt_ref": transfer_ref,
            "transfer_receipt_sha256": sha256(transfer_path),
            "retained_failed_partial_sha256": sha256(retained_partial),
        },
        "activity": {
            "network_requests_performed": False,
            "authentication_performed": False,
            "archive_extraction_performed": False,
            "source_archive_mutation_performed": False,
            "retained_failed_partial_mutation_performed": False,
        },
        "result": result,
        "pixel_usability_established": False,
        "scientific_fitness_established": False,
        "next_gate": (
            "reconcile_recovery_then_continue_only_original_unattempted_products"
            if result["status"] == "pass_container_only"
            else "retain_recovery_failure_and_request_new_review"
        ),
        "limitations": verification_contract["limitations"],
    }
    write_new(output, receipt)
    print(json.dumps({
        "status": result["status"],
        "source_id": EXPECTED_SOURCE_ID,
        "attempt_id": attempt_id,
        "receipt": str(output.relative_to(ROOT)).replace("\\", "/"),
        "pixel_usability_established": False,
    }, indent=2))
    return 0 if result["status"] == "pass_container_only" else 20


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RecoveryControlError as exc:
        print(json.dumps({"status": "stopped", "code": exc.code, "mutations_performed": False}, indent=2))
        raise SystemExit(12)
