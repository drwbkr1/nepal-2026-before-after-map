#!/usr/bin/env python3
"""Validate a terminal DEM transfer and reconcile the active acquisition checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from typing import Any

from m2_transfer_core import replace_json, require_safe_child, sha256_file, write_new_json


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent.resolve()
INTAKE_PATH = ROOT / "contracts/m2-dem-intake.json"
VERIFICATION_PATH = ROOT / "contracts/m2-dem-offline-verification.json"
MILESTONE_PATH = ROOT / "contracts/milestone-002.json"
PROFILE_PATH = ROOT / "records/project-control-profile.json"
GOAL_PATH = ROOT / "records/long-term-goal.json"
APPROVAL_PATH = ROOT / "records/source-gates/m2-dem-amendment-approval.json"
PREFLIGHT_PATH = ROOT / "records/acquisition/dem-preflight.json"
RUNNER_PATH = ROOT / "scripts/acquire_m2_dem_tile.py"
EXPECTED_SOURCE_IDS = ["M2-DEM-001", "M2-DEM-002", "M2-DEM-003", "M2-DEM-004"]


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return value


def serialized(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_value(value: object) -> str:
    return hashlib.sha256(serialized(value)).hexdigest()


def evaluate_progress(assets: list[dict[str, Any]]) -> dict[str, Any]:
    allowed = {"authorized", "promoted", "failed"}
    states = [asset.get("state") for asset in assets]
    if len(assets) != 4 or any(state not in allowed for state in states):
        raise ValueError("unsupported DEM acquisition state")
    counts = {state: states.count(state) for state in sorted(allowed)}
    if counts["failed"]:
        checkpoint = "M2-DEM-ACQUISITION-REVIEW"
        disposition = "review"
    elif counts["promoted"] == 4:
        checkpoint = "M2-DEM-GEOTIFF-VERIFICATION"
        disposition = "complete"
    else:
        checkpoint = "M2-DEM-ACQUISITION"
        disposition = "in_progress"
    return {"counts": counts, "checkpoint": checkpoint, "disposition": disposition}


def validate_asset_history(intake: dict[str, Any], *, verify_external: bool = True) -> list[dict[str, Any]]:
    custody_relative = PurePosixPath(intake["custody_root"])
    staging_relative = PurePosixPath(intake["staging_root"])
    for label, relative in (("custody", custody_relative), ("staging", staging_relative)):
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"{label} root escapes the project parent")
    custody_root = PROJECT_ROOT / Path(*custody_relative.parts)
    staging_root = PROJECT_ROOT / Path(*staging_relative.parts)
    if verify_external:
        custody_root = custody_root.resolve(strict=True)
        staging_root = staging_root.resolve(strict=True)
    summaries: list[dict[str, Any]] = []
    for asset in intake["assets"]:
        source_id = asset["extensions"]["source_id"]
        state = asset["state"]
        attempts = asset.get("attempts", [])
        destination_relative = PurePosixPath(asset["destination_relative_path"])
        staging_asset_relative = PurePosixPath(asset["staging_relative_path"])
        if destination_relative.is_absolute() or ".." in destination_relative.parts or staging_asset_relative.is_absolute() or ".." in staging_asset_relative.parts:
            raise ValueError(f"asset path escapes the controlled root: {source_id}")
        destination = custody_root / Path(*destination_relative.parts)
        staging = staging_root / Path(*staging_asset_relative.parts)
        if verify_external:
            destination = require_safe_child(custody_root, destination)
            staging = require_safe_child(staging_root, staging)
        if state == "authorized":
            if attempts or (verify_external and (destination.exists() or staging.exists())):
                raise ValueError(f"authorized asset has attempt or bytes: {source_id}")
            summaries.append({"source_id": source_id, "state": state, "attempt_id": None})
            continue
        if len(attempts) != 1 or attempts[0].get("outcome") not in {"succeeded", "failed"} or not attempts[0].get("completed_at"):
            raise ValueError(f"terminal asset history is incomplete: {source_id}")
        attempt = attempts[0]
        if state == "failed":
            if attempt["outcome"] != "failed" or asset.get("failure", {}).get("code") is None or (verify_external and destination.exists()):
                raise ValueError(f"failed asset history differs: {source_id}")
            summaries.append({"source_id": source_id, "state": state, "attempt_id": attempt["attempt_id"]})
            continue
        if attempt["outcome"] != "succeeded" or (verify_external and (not destination.is_file() or staging.exists())):
            raise ValueError(f"promoted asset paths or history differ: {source_id}")
        receipt_ref = asset["extensions"].get("successful_attempt_receipt")
        if not isinstance(receipt_ref, str):
            raise ValueError(f"promoted asset receipt is absent: {source_id}")
        receipt_path = ROOT / receipt_ref
        if not receipt_path.is_file() or asset["extensions"].get("successful_attempt_receipt_sha256") != sha256_file(receipt_path):
            raise ValueError(f"promoted asset receipt binding differs: {source_id}")
        receipt = load(receipt_path)
        observed = asset["observed"]
        actual_size = destination.stat().st_size if verify_external else observed.get("promoted_size_bytes")
        actual_sha = sha256_file(destination) if verify_external else observed.get("promoted_sha256")
        if (
            receipt.get("event") != "dem_transfer_succeeded"
            or receipt.get("attempt_id") != attempt["attempt_id"]
            or receipt.get("source_id") != source_id
            or receipt.get("local_size_bytes") != actual_size
            or receipt.get("local_sha256") != actual_sha
            or observed.get("promoted_size_bytes") != actual_size
            or observed.get("promoted_sha256") != actual_sha
            or observed.get("staged_size_bytes") != actual_size
            or observed.get("staged_sha256") != actual_sha
            or not isinstance(actual_size, int)
            or actual_size <= 0
            or not isinstance(actual_sha, str)
            or len(actual_sha) != 64
        ):
            raise ValueError(f"promoted asset byte identity differs: {source_id}")
        summaries.append({"source_id": source_id, "state": state, "attempt_id": attempt["attempt_id"], "receipt_ref": receipt_ref, "receipt_sha256": sha256_file(receipt_path), "local_size_bytes": actual_size, "local_sha256": actual_sha})
    return summaries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--reconciled-at-utc", required=True)
    args = parser.parse_args()
    if not args.reconciled_at_utc.endswith("Z"):
        raise SystemExit("--reconciled-at-utc must be an RFC 3339 UTC timestamp ending in Z")

    intake = load(INTAKE_PATH)
    verification = load(VERIFICATION_PATH)
    milestone = load(MILESTONE_PATH)
    profile = load(PROFILE_PATH)
    goal = load(GOAL_PATH)
    approval = load(APPROVAL_PATH)
    preflight = load(PREFLIGHT_PATH)
    if approval.get("status") != "approved" or approval.get("authorized_source_ids") != EXPECTED_SOURCE_IDS:
        raise SystemExit("exact DEM authority is absent or differs")
    if preflight.get("status") != "pass_no_payload_no_external_mutation" or intake.get("extensions", {}).get("preflight_sha256") != sha256_file(PREFLIGHT_PATH):
        raise SystemExit("DEM preflight binding differs")
    if [asset.get("extensions", {}).get("source_id") for asset in intake.get("assets", [])] != EXPECTED_SOURCE_IDS:
        raise SystemExit("DEM intake source order or identity differs")
    matches = [(asset, attempt) for asset in intake["assets"] for attempt in asset.get("attempts", []) if attempt.get("attempt_id") == args.attempt_id]
    if len(matches) != 1 or matches[0][1].get("outcome") not in {"succeeded", "failed"}:
        raise SystemExit("attempt is absent, ambiguous, or nonterminal")
    checkpoint_path = ROOT / "records" / "acquisition" / "dem-checkpoints" / f"{args.attempt_id}.json"
    if checkpoint_path.exists():
        raise SystemExit(f"checkpoint receipt already exists: {checkpoint_path}")

    intake_sha_before = sha256_file(INTAKE_PATH)
    summaries = validate_asset_history(intake)
    progress = evaluate_progress(intake["assets"])
    terminal_summary = next(item for item in summaries if item.get("attempt_id") == args.attempt_id)
    checkpoint = {
        "schema_version": "1.0",
        "checkpoint_id": f"NEPAL-{args.attempt_id.upper()}-RECONCILIATION",
        "status": "pass_terminal_attempt_reconciled" if terminal_summary["state"] == "promoted" else "review_terminal_failure_reconciled",
        "reconciled_at_utc": args.reconciled_at_utc,
        "attempt_id": args.attempt_id,
        "terminal_asset": terminal_summary,
        "bindings": {
            "approval_ref": str(APPROVAL_PATH.relative_to(ROOT)).replace("\\", "/"),
            "approval_sha256": sha256_file(APPROVAL_PATH),
            "preflight_ref": str(PREFLIGHT_PATH.relative_to(ROOT)).replace("\\", "/"),
            "preflight_sha256": sha256_file(PREFLIGHT_PATH),
            "active_intake_ref": str(INTAKE_PATH.relative_to(ROOT)).replace("\\", "/"),
            "active_intake_sha256_before_reconciliation": intake_sha_before,
            "transfer_runner_ref": str(RUNNER_PATH.relative_to(ROOT)).replace("\\", "/"),
            "transfer_runner_sha256": sha256_file(RUNNER_PATH),
            "reconciliation_script_ref": "scripts/reconcile_m2_dem_acquisition.py",
            "reconciliation_script_sha256": sha256_file(ROOT / "scripts/reconcile_m2_dem_acquisition.py"),
        },
        "progress": progress,
        "all_assets": summaries,
        "claim_boundary": {"transferred_byte_identity_established_for_promoted_assets": True, "geotiff_readability_established": False, "valid_pixel_coverage_established": False, "vertical_datum_route_established": False, "radar_processing_executed": False, "scientific_result_established": False},
    }
    write_new_json(checkpoint_path, checkpoint)

    if progress["disposition"] == "review":
        intake["extensions"]["status"] = "active_acquisition_review_required"
        verification["status"] = "active_gate_blocked_acquisition_review"
    elif progress["disposition"] == "complete":
        intake["extensions"]["status"] = "active_all_promoted_pending_geotiff_verification"
        verification["status"] = "active_gate_ready_for_geotiff_verification"
    else:
        intake["extensions"]["status"] = "active_acquisition_in_progress"
        verification["status"] = "active_gate_deferred_incomplete_acquisition"
    intake["extensions"].update({"last_reconciled_attempt_id": args.attempt_id, "last_reconciled_at_utc": args.reconciled_at_utc, "last_checkpoint_ref": str(checkpoint_path.relative_to(ROOT)).replace("\\", "/"), "last_checkpoint_sha256": sha256_file(checkpoint_path)})
    new_intake_sha = sha256_value(intake)
    verification["inputs"]["intake_contract_sha256"] = new_intake_sha

    units = {unit["id"]: unit for unit in milestone["units"]}
    acquire = units["M2-DEM-ACQUIRE"]
    verify = units["M2-DEM-VERIFY"]
    counts = progress["counts"]
    acquire["gates"].update({"authorized_count": counts["authorized"], "promoted_count": counts["promoted"], "failed_count": counts["failed"], "last_checkpoint_ref": str(checkpoint_path.relative_to(ROOT)).replace("\\", "/"), "last_checkpoint_sha256": sha256_file(checkpoint_path)})
    if progress["disposition"] == "complete":
        acquire.update({"status": "complete", "disposition": "pass", "exit_condition_delta": {"expected": ["EXIT-201-VERIFIED-CUSTODY"], "observed": ["EXIT-201-VERIFIED-CUSTODY"], "decision_value": "enables_dependency", "rationale": "All four exact tiles are promoted with reconciled byte identity; GeoTIFF verification remains next."}})
        verify["status"] = "ready"
    elif progress["disposition"] == "review":
        acquire.update({"status": "ready", "disposition": "block", "exit_condition_delta": {"expected": ["EXIT-201-VERIFIED-CUSTODY"], "observed": [], "decision_value": "block", "rationale": "A failed attempt requires review; retry is not automatically authorized."}})
    else:
        acquire.update({"status": "ready", "disposition": None, "exit_condition_delta": {"expected": ["EXIT-201-VERIFIED-CUSTODY"], "observed": [], "decision_value": "unknown", "rationale": f"{counts['promoted']} exact DEM files are promoted with reconciled SHA-256 and size receipts; continue one exact unattempted tile at a time."}})

    remaining = next((item for item in summaries if item["state"] == "authorized"), None)
    if progress["checkpoint"] == "M2-DEM-ACQUISITION":
        next_action = f"Acquire {remaining['source_id']} only through append-only staging, exact size and local SHA-256, and no-replace promotion."
    elif progress["checkpoint"] == "M2-DEM-GEOTIFF-VERIFICATION":
        next_action = "Run the active offline ArcGIS GeoTIFF verifier for each of the four promoted DEM tiles; do not infer pixel or vertical-datum fitness from transfer success."
    else:
        next_action = "Review the retained DEM transfer failure; do not retry or advance to GeoTIFF verification without a new bounded decision."
    milestone["handoff"].update({"parallel_checkpoint": progress["checkpoint"], "parallel_next_action": next_action})
    profile["parallel_checkpoints"] = [{"checkpoint_id": progress["checkpoint"], "authority_ref": "records/source-gates/m2-dem-amendment-approval.json", "next_action": next_action}]
    goal["parallel_checkpoints"] = [progress["checkpoint"]]

    replace_json(INTAKE_PATH, intake, f".{args.attempt_id}.reconcile-intake-tmp")
    replace_json(VERIFICATION_PATH, verification, f".{args.attempt_id}.reconcile-verification-tmp")
    replace_json(MILESTONE_PATH, milestone, f".{args.attempt_id}.reconcile-milestone-tmp")
    replace_json(PROFILE_PATH, profile, f".{args.attempt_id}.reconcile-profile-tmp")
    replace_json(GOAL_PATH, goal, f".{args.attempt_id}.reconcile-goal-tmp")
    print(json.dumps({"status": checkpoint["status"], "attempt_id": args.attempt_id, "progress": progress, "checkpoint_receipt": str(checkpoint_path.relative_to(ROOT)).replace("\\", "/"), "checkpoint_receipt_sha256": sha256_file(checkpoint_path), "active_intake_sha256": sha256_file(INTAKE_PATH), "active_verification_sha256": sha256_file(VERIFICATION_PATH), "next_checkpoint": progress["checkpoint"]}, indent=2))


if __name__ == "__main__":
    main()
