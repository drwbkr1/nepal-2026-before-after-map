#!/usr/bin/env python3
"""Materialize one container-verified M2 product into append-only external SAFE custody."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from m2_materialization_core import (
    MaterializationError,
    ensure_directory,
    inspect_safe_members,
    materialize_archive,
    sha256_file,
    write_new_json,
)


ROOT = Path(__file__).resolve().parents[1]
ATTEMPT_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
UTC_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


def load(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def digest(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def stop(code: str) -> None:
    print(json.dumps({"status": "stopped", "code": code, "external_mutation_performed": False}, indent=2))
    raise SystemExit(12)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--started-at-utc", required=True)
    args = parser.parse_args()
    if not ATTEMPT_ID.fullmatch(args.attempt_id):
        stop("invalid_materialization_attempt_id")
    if not UTC_TIMESTAMP.fullmatch(args.started_at_utc):
        stop("invalid_materialization_timestamp")

    contract = load("contracts/m2-materialization.json")
    milestone = load("contracts/milestone-002.json")
    intake = load("contracts/m2-intake.json")
    verification = load("contracts/m2-offline-verification.json")
    if contract.get("status") != "active_authorized_gate_deferred":
        stop("materialization_contract_not_active")
    for ref_key, hash_key in (
        ("acquisition_plan_ref", "acquisition_plan_sha256"),
        ("activation_approval_ref", "activation_approval_sha256"),
        ("active_verification_ref", "active_verification_sha256"),
        ("materialization_core_ref", "materialization_core_sha256"),
        ("runner_ref", "runner_sha256"),
    ):
        relative = contract.get("inputs", {}).get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            stop("materialization_contract_input_missing")
        if contract["inputs"].get(hash_key) != digest(relative):
            stop("materialization_contract_input_hash_mismatch")
    if milestone.get("status") != "active" or "data_processing" not in milestone.get("authority", {}).get("authorized_action_classes", []):
        stop("m2_data_processing_authority_not_active")
    assets = [item for item in contract["assets"] if item.get("source_id") == args.source_id]
    intake_assets = [item for item in intake["assets"] if item.get("extensions", {}).get("source_id") == args.source_id]
    verification_assets = [item for item in verification["assets"] if item.get("source_id") == args.source_id]
    if len(assets) != 1 or len(intake_assets) != 1 or len(verification_assets) != 1:
        stop("source_id_not_bound_exactly_once")
    asset = assets[0]
    intake_asset = intake_assets[0]
    if intake_asset.get("state") != "promoted":
        stop("asset_not_promoted")
    succeeded = [item for item in intake_asset.get("attempts", []) if item.get("outcome") == "succeeded"]
    if len(succeeded) != 1:
        stop("successful_transfer_attempt_history_invalid")
    transfer_attempt = succeeded[0]
    container_ref = f"records/acquisition/container-verification/{args.source_id.casefold()}-{transfer_attempt['attempt_id']}.json"
    container_path = ROOT / container_ref
    if not container_path.is_file():
        stop("container_receipt_missing")
    container = load(container_ref)
    if (
        container.get("status") != "pass_container_only"
        or container.get("source_id") != args.source_id
        or container.get("attempt_id") != transfer_attempt["attempt_id"]
        or container.get("result", {}).get("eligible_for_post_container_qa") is not True
    ):
        stop("container_receipt_not_passing_exact_source")
    if container.get("bindings", {}).get("verification_contract_sha256") != digest("contracts/m2-offline-verification.json"):
        stop("container_receipt_verification_contract_mismatch")

    data_root = Path(contract["execution_boundary"]["external_data_root"])
    expected_data_root_path = ROOT.parent / f"{ROOT.name}-data"
    if not data_root.is_dir() or not expected_data_root_path.is_dir():
        stop("external_data_root_missing")
    expected_data_root = expected_data_root_path.resolve(strict=True)
    if data_root.resolve(strict=True) != expected_data_root:
        stop("external_data_root_differs_from_project_boundary")
    expected_materialization_root = expected_data_root / "materialized"
    if Path(contract["execution_boundary"]["materialization_root"]).resolve(strict=False) != expected_materialization_root:
        stop("materialization_root_differs_from_project_boundary")
    custody_root = Path(verification["execution_boundary"]["custody_root_from_plan"])
    archive = custody_root.joinpath(*Path(asset["archive_relative_path"]).parts)
    if not archive.is_file():
        stop("verified_archive_missing")
    observed = intake_asset.get("observed", {})
    result = container.get("result", {})
    archive_size = archive.stat().st_size
    archive_sha = sha256_file(archive)
    if archive_size != observed.get("promoted_size_bytes") or archive_size != result.get("local_size_bytes"):
        stop("archive_size_changed_after_container_verification")
    if archive_sha != observed.get("promoted_sha256") or archive_sha != result.get("local_sha256"):
        stop("archive_sha256_changed_after_container_verification")

    receipt_ref = f"records/acquisition/materialization/{args.source_id.casefold()}-{args.attempt_id}.json"
    receipt_path = ROOT / receipt_ref
    if receipt_path.exists():
        stop("materialization_receipt_collision")
    # Revalidate the complete member namespace before any output directory is
    # created. ``materialize_archive`` repeats this check immediately before
    # extraction so a changed archive cannot bypass it.
    try:
        inspect_safe_members(archive, asset["exact_product_id"], contract["member_controls"])
    except MaterializationError as exc:
        stop(exc.code)
    materialization_root = expected_materialization_root
    ensure_directory(materialization_root, data_root)
    source_root = materialization_root / args.source_id.casefold()
    ensure_directory(source_root, data_root)
    attempt_root = source_root / args.attempt_id

    try:
        completed = materialize_archive(
            archive_path=archive,
            attempt_root=attempt_root,
            source_id=args.source_id,
            exact_product_id=asset["exact_product_id"],
            archive_sha256=archive_sha,
            controls=contract["member_controls"],
            started_at_utc=args.started_at_utc,
        )
    except MaterializationError as exc:
        if attempt_root.is_dir():
            try:
                write_new_json(
                    attempt_root / "failed.json",
                    {"status": "failed", "code": exc.code, "detail": exc.detail, "source_id": args.source_id},
                )
            except MaterializationError:
                pass
        receipt = {
            "receipt_version": "1.0",
            "status": "failed_retained",
            "source_id": args.source_id,
            "attempt_id": args.attempt_id,
            "failure_code": exc.code,
            "bindings": {
                "contract_ref": "contracts/m2-materialization.json",
                "contract_sha256": digest("contracts/m2-materialization.json"),
                "container_receipt_ref": container_ref,
                "container_receipt_sha256": digest(container_ref),
                "archive_sha256": archive_sha,
            },
            "external_attempt_root": str(attempt_root),
            "source_archive_mutated": False,
            "pixel_usability_established": False,
            "scientific_admission_authorized": False,
        }
        write_new_json(receipt_path, receipt)
        print(json.dumps({"status": receipt["status"], "code": exc.code, "receipt": receipt_ref}, indent=2))
        return 20

    external_manifest = Path(completed["manifest_path"])
    receipt = {
        "receipt_version": "1.0",
        "status": "pass_materialization_only",
        "source_id": args.source_id,
        "attempt_id": args.attempt_id,
        "exact_product_id": asset["exact_product_id"],
        "bindings": {
            "contract_ref": "contracts/m2-materialization.json",
            "contract_sha256": digest("contracts/m2-materialization.json"),
            "active_intake_ref": "contracts/m2-intake.json",
            "active_intake_sha256_at_materialization": digest("contracts/m2-intake.json"),
            "container_receipt_ref": container_ref,
            "container_receipt_sha256": digest(container_ref),
            "archive_sha256": archive_sha,
            "archive_size_bytes": archive_size,
            "external_manifest_path": str(external_manifest),
            "external_manifest_sha256": sha256_file(external_manifest),
        },
        "external_safe_root": completed["safe_root"],
        "file_count": completed["file_count"],
        "total_extracted_bytes": completed["total_extracted_bytes"],
        "activity": {
            "network_requests_performed": False,
            "authentication_performed": False,
            "source_archive_mutated": False,
        },
        "raster_readability_established": False,
        "pixel_usability_established": False,
        "baseline_established": False,
        "change_established": False,
        "scientific_admission_authorized": False,
        "next_gate": "raster_readability_and_pixel_qa",
    }
    write_new_json(receipt_path, receipt)
    print(json.dumps({"status": receipt["status"], "source_id": args.source_id, "receipt": receipt_ref}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MaterializationError as exc:
        print(json.dumps({"status": "stopped", "code": exc.code}, indent=2))
        raise SystemExit(12)
