#!/usr/bin/env python3
"""Verify one promoted M2 archive without network access or extraction."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path, PurePosixPath
from typing import Any

import prepare_m2_verification as verification


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent.resolve()
CONTRACT_PATH = ROOT / "contracts/m2-offline-verification.json"
INTAKE_PATH = ROOT / "contracts/m2-intake.json"
RECEIPT_ROOT = ROOT / "records/acquisition/container-verification"


class VerificationStop(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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

    contract = load(CONTRACT_PATH)
    intake = load(INTAKE_PATH)
    if contract.get("status") != "active_authorized_offline_verification":
        raise VerificationStop("active_verification_contract_missing")
    contract_assets = [item for item in contract["assets"] if item.get("source_id") == args.source_id]
    intake_assets = [item for item in intake["assets"] if item.get("extensions", {}).get("source_id") == args.source_id]
    if len(contract_assets) != 1 or len(intake_assets) != 1:
        raise VerificationStop("source_id_not_bound_exactly_once")
    asset = contract_assets[0]
    intake_asset = intake_assets[0]
    if intake_asset.get("state") != "promoted":
        raise VerificationStop("asset_not_promoted")
    succeeded = [attempt for attempt in intake_asset.get("attempts", []) if attempt.get("outcome") == "succeeded"]
    if len(succeeded) != 1:
        raise VerificationStop("promoted_asset_attempt_history_invalid")
    attempt_id = succeeded[0]["attempt_id"]
    output = RECEIPT_ROOT / f"{args.source_id.casefold()}-{attempt_id}.json"
    if output.exists():
        raise VerificationStop("container_receipt_collision")

    custody_root = (PROJECT_ROOT / Path(*PurePosixPath(intake["custody_root"]).parts)).resolve(strict=True)
    archive = (custody_root / Path(*PurePosixPath(asset["archive_relative_path"]).parts)).resolve(strict=False)
    try:
        archive.relative_to(custody_root)
    except ValueError as exc:
        raise VerificationStop("archive_path_outside_custody") from exc
    if not archive.is_file():
        raise VerificationStop("promoted_archive_missing")

    result = verification.scan_archive(asset, archive, contract["archive_controls"])
    observed = intake_asset.get("observed", {})
    if result.get("local_sha256") != observed.get("promoted_sha256"):
        result["errors"].append("local SHA-256 differs from active intake promoted identity")
    if result.get("local_size_bytes") != observed.get("promoted_size_bytes"):
        result["errors"].append("local size differs from active intake promoted identity")
    if result["errors"]:
        result["status"] = "block"
        result["eligible_for_post_container_qa"] = False

    transfer_receipt_ref = intake_asset.get("extensions", {}).get("successful_attempt_receipt")
    transfer_receipt = ROOT / transfer_receipt_ref if isinstance(transfer_receipt_ref, str) else None
    if transfer_receipt is None or not transfer_receipt.is_file():
        raise VerificationStop("successful_transfer_receipt_missing")
    receipt = {
        "receipt_version": "1.0",
        "receipt_id": f"NEPAL-M2-CONTAINER-{args.source_id}-{attempt_id}",
        "scanned_at_utc": args.scanned_at_utc,
        "status": result["status"],
        "source_id": args.source_id,
        "attempt_id": attempt_id,
        "bindings": {
            "verification_contract_ref": str(CONTRACT_PATH.relative_to(ROOT)).replace("\\", "/"),
            "verification_contract_sha256": sha256(CONTRACT_PATH),
            "active_intake_ref": str(INTAKE_PATH.relative_to(ROOT)).replace("\\", "/"),
            "active_intake_sha256_at_scan": sha256(INTAKE_PATH),
            "transfer_receipt_ref": transfer_receipt_ref,
            "transfer_receipt_sha256": sha256(transfer_receipt),
        },
        "activity": {
            "network_requests_performed": False,
            "authentication_performed": False,
            "archive_extraction_performed": False,
            "source_archive_mutation_performed": False,
        },
        "result": result,
        "pixel_usability_established": False,
        "scientific_fitness_established": False,
        "next_gate": "post_container_gates" if result["status"] == "pass_container_only" else "resolve retained container block",
        "limitations": contract["limitations"],
    }
    write_new(output, receipt)
    print(json.dumps({
        "status": result["status"],
        "source_id": args.source_id,
        "attempt_id": attempt_id,
        "receipt": str(output.relative_to(ROOT)).replace("\\", "/"),
        "pixel_usability_established": False,
    }, indent=2))
    return 0 if result["status"] == "pass_container_only" else 20


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except VerificationStop as exc:
        print(json.dumps({"status": "stopped", "code": exc.code, "mutations_performed": False}, indent=2))
        raise SystemExit(12)
