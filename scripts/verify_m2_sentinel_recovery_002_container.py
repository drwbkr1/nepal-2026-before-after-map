#!/usr/bin/env python3
"""Verify the promoted recovery-002 archive offline and without extraction."""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
from typing import Any

import prepare_m2_verification as verification
from m2_sentinel_recovery_002_core import (
    APPROVAL_REF,
    CONTRACT_REF,
    DATA_ROOT,
    EXPECTED_APPROVAL_SHA256,
    EXPECTED_SOURCE_ID,
    ORIGINAL_PARTIAL_SHA256,
    RECOVERY_001_PARTIAL_SHA256,
    ROOT,
    Recovery002ControlError,
    load_object,
    require_exact_contract,
    sha256_file,
    verify_both_retained_partials,
    write_new_json,
)


ACTIVE_INTAKE_PATH = ROOT / "contracts/m2-intake.json"
RECOVERY_001_CONTRACT_PATH = ROOT / "contracts/m2-sentinel-recovery.json"
RECOVERY_CONTRACT_PATH = ROOT / CONTRACT_REF
APPROVAL_PATH = ROOT / APPROVAL_REF
VERIFICATION_CONTRACT_PATH = ROOT / "contracts/m2-offline-verification.json"
RECEIPT_ROOT = ROOT / "records/acquisition/container-verification"


def verify_and_record(scanned_at_utc: str) -> dict[str, Any]:
    recovery = load_object(RECOVERY_CONTRACT_PATH)
    asset = require_exact_contract(recovery)
    if asset.get("state") != "promoted":
        raise Recovery002ControlError("recovery_002_asset_not_promoted")
    successes = [item for item in asset.get("attempts", []) if item.get("outcome") == "succeeded"]
    if len(successes) != 1:
        raise Recovery002ControlError("recovery_002_success_history_invalid")
    if sha256_file(APPROVAL_PATH) != EXPECTED_APPROVAL_SHA256:
        raise Recovery002ControlError("recovery_002_approval_hash_drift")

    active = load_object(ACTIVE_INTAKE_PATH)
    recovery_001 = load_object(RECOVERY_001_CONTRACT_PATH)
    original_partial, recovery_001_partial = verify_both_retained_partials(active, recovery_001)
    verification_contract = load_object(VERIFICATION_CONTRACT_PATH)
    candidates = [item for item in verification_contract.get("assets", []) if item.get("source_id") == EXPECTED_SOURCE_ID]
    if verification_contract.get("status") != "active_authorized_offline_verification" or len(candidates) != 1:
        raise Recovery002ControlError("offline_verification_contract_drift")

    custody_root = (ROOT.parent / Path(*PurePosixPath(recovery["custody_root"]).parts)).resolve(strict=True)
    archive = (custody_root / Path(*PurePosixPath(asset["destination_relative_path"]).parts)).resolve(strict=False)
    try:
        archive.relative_to(custody_root)
    except ValueError as exc:
        raise Recovery002ControlError("recovery_002_archive_outside_custody") from exc
    if not archive.is_file():
        raise Recovery002ControlError("recovery_002_promoted_archive_missing")

    attempt_id = successes[0]["attempt_id"]
    output = RECEIPT_ROOT / f"m1-src-004-{attempt_id}.json"
    result = verification.scan_archive(candidates[0], archive, verification_contract["archive_controls"])
    observed = asset.get("observed", {})
    if result.get("local_sha256") != observed.get("promoted_sha256"):
        result["errors"].append("local SHA-256 differs from recovery-002 promoted identity")
    if result.get("local_size_bytes") != observed.get("promoted_size_bytes"):
        result["errors"].append("local size differs from recovery-002 promoted identity")
    if result["errors"]:
        result["status"] = "block"
        result["eligible_for_post_container_qa"] = False

    transfer_ref = asset.get("extensions", {}).get("successful_attempt_receipt")
    transfer_path = ROOT / transfer_ref if isinstance(transfer_ref, str) else None
    if transfer_path is None or not transfer_path.is_file():
        raise Recovery002ControlError("recovery_002_transfer_receipt_missing")
    receipt = {
        "receipt_version": "1.0",
        "receipt_id": f"NEPAL-M2-CONTAINER-RECOVERY-002-{attempt_id}",
        "scanned_at_utc": scanned_at_utc,
        "status": result["status"],
        "source_id": EXPECTED_SOURCE_ID,
        "attempt_id": attempt_id,
        "bindings": {
            "verification_contract_ref": "contracts/m2-offline-verification.json",
            "verification_contract_sha256": sha256_file(VERIFICATION_CONTRACT_PATH),
            "recovery_002_contract_ref": CONTRACT_REF,
            "recovery_002_contract_sha256_at_scan": sha256_file(RECOVERY_CONTRACT_PATH),
            "recovery_002_approval_ref": APPROVAL_REF,
            "recovery_002_approval_sha256": sha256_file(APPROVAL_PATH),
            "transfer_receipt_ref": transfer_ref,
            "transfer_receipt_sha256": sha256_file(transfer_path),
            "original_failed_partial_sha256": sha256_file(original_partial),
            "recovery_001_failed_partial_sha256": sha256_file(recovery_001_partial),
        },
        "assertions": {
            "original_failed_partial_unchanged": sha256_file(original_partial) == ORIGINAL_PARTIAL_SHA256,
            "recovery_001_failed_partial_unchanged": sha256_file(recovery_001_partial) == RECOVERY_001_PARTIAL_SHA256,
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
        "next_gate": "success_only_original_product_continuation" if result["status"] == "pass_container_only" else "stop_new_review_required",
        "limitations": verification_contract["limitations"],
    }
    write_new_json(output, receipt)
    return {
        "returncode": 0 if result["status"] == "pass_container_only" else 20,
        "status": result["status"],
        "source_id": EXPECTED_SOURCE_ID,
        "attempt_id": attempt_id,
        "receipt": str(output.relative_to(ROOT)).replace("\\", "/"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--scanned-at-utc", required=True)
    args = parser.parse_args()
    if args.source_id != EXPECTED_SOURCE_ID:
        raise Recovery002ControlError("recovery_002_source_outside_approval")
    result = verify_and_record(args.scanned_at_utc)
    print(json.dumps(result, indent=2))
    return int(result["returncode"])


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Recovery002ControlError as exc:
        print(json.dumps({"status": "stopped", "code": exc.code, "mutations_performed": False}, indent=2))
        raise SystemExit(12)
