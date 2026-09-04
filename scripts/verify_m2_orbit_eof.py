#!/usr/bin/env python3
"""Reverify one promoted S1D AUX_RESORB EOF in read-only local custody."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from m2_orbit_io_core import OrbitControlError, inspect_eof
from m2_transfer_core import sha256_file


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent.resolve()
APPROVAL_PATH = ROOT / "records/source-gates/m2-orbit-amendment-approval.json"
ACTIVE_INTAKE_PATH = ROOT / "contracts/m2-orbit-intake.json"
ACTIVE_VERIFICATION_PATH = ROOT / "contracts/m2-orbit-offline-verification.json"
MANIFEST_PATH = ROOT / "records/source-gates/m2-orbit-candidate-manifest.json"
PROPOSAL_SHA256 = "b17e256068759946be611bf4e7beffe0d3121e9e731b6c42163525eca2cf0292"
REVIEW_BUNDLE_SHA256 = "ee5fbf4933b52be8f97441b78a73559a973bd975efc21b43625f1ceca54e2ff1"
EXPECTED_SOURCE_IDS = ["M2-ORB-001", "M2-ORB-002", "M2-ORB-003", "M2-ORB-004"]


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise OrbitControlError("control_root_not_object")
    return value


def write_new(path: Path, value: dict[str, Any]) -> None:
    if not path.parent.is_dir():
        raise OrbitControlError("verification_output_parent_missing")
    if path.exists():
        raise OrbitControlError("verification_output_collision")
    with path.open("xb") as handle:
        handle.write((json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))


def inventory(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "relative_path": path.relative_to(root).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in sorted(item for item in root.rglob("*") if item.is_file())
    ]


def guarded_controls() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if not APPROVAL_PATH.is_file() or not ACTIVE_INTAKE_PATH.is_file() or not ACTIVE_VERIFICATION_PATH.is_file():
        raise OrbitControlError("orbit_authority_or_active_controls_missing")
    approval = load(APPROVAL_PATH)
    intake = load(ACTIVE_INTAKE_PATH)
    verification = load(ACTIVE_VERIFICATION_PATH)
    if (
        approval.get("status") != "approved"
        or approval.get("amendment_proposal_sha256") != PROPOSAL_SHA256
        or approval.get("review_bundle_manifest_sha256") != REVIEW_BUNDLE_SHA256
        or approval.get("authorized_source_ids") != EXPECTED_SOURCE_IDS
        or approval.get("authorized_orbit_type") != "AUX_RESORB"
        or approval.get("orbit_quality", {}).get("later_precise_substitution_status")
        != "separately_gated_not_authorized"
    ):
        raise OrbitControlError("orbit_approval_identity_or_scope_drift")
    if (
        intake.get("extensions", {}).get("scope_authority") != "granted_exact_four_resorb_files"
        or intake.get("extensions", {}).get("amendment_approval_sha256") != sha256_file(APPROVAL_PATH)
        or intake.get("extensions", {}).get("manifest_sha256") != sha256_file(MANIFEST_PATH)
    ):
        raise OrbitControlError("active_orbit_intake_binding_drift")
    if (
        verification.get("status") != "active_gate_ready_for_offline_verification"
        or verification.get("authority", {}).get("orbit_input_verification_authorized") is not True
        or verification.get("authority", {}).get("precise_orbit_substitution_authorized") is not False
        or verification.get("bindings", {}).get("active_intake_sha256_current") != sha256_file(ACTIVE_INTAKE_PATH)
        or verification.get("bindings", {}).get("candidate_manifest_sha256") != sha256_file(MANIFEST_PATH)
    ):
        raise OrbitControlError("active_orbit_verification_binding_drift")
    return approval, intake, verification


def promoted_binding(
    intake: dict[str, Any], source_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    matches = [asset for asset in intake.get("assets", []) if asset.get("extensions", {}).get("source_id") == source_id]
    if len(matches) != 1:
        raise OrbitControlError("promoted_orbit_asset_absent_or_ambiguous")
    asset = matches[0]
    attempts = asset.get("attempts", [])
    if asset.get("state") != "promoted" or len(attempts) != 1 or attempts[0].get("outcome") != "succeeded":
        raise OrbitControlError("orbit_asset_not_promoted_once")
    receipt_ref = asset.get("extensions", {}).get("successful_attempt_receipt")
    receipt_sha = asset.get("extensions", {}).get("successful_attempt_receipt_sha256")
    if not isinstance(receipt_ref, str) or not receipt_ref.startswith("records/acquisition/orbit-attempts/"):
        raise OrbitControlError("orbit_transfer_receipt_reference_invalid")
    receipt_path = (ROOT / receipt_ref).resolve()
    try:
        receipt_path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise OrbitControlError("orbit_transfer_receipt_path_escape") from exc
    if not receipt_path.is_file() or receipt_sha != sha256_file(receipt_path):
        raise OrbitControlError("orbit_transfer_receipt_missing_or_drifted")
    receipt = load(receipt_path)
    observed = asset.get("observed", {})
    if (
        receipt.get("event") != "orbit_transfer_succeeded"
        or receipt.get("attempt_id") != attempts[0].get("attempt_id")
        or receipt.get("source_id") != source_id
        or receipt.get("local_sha256") != observed.get("promoted_sha256")
        or receipt.get("local_size_bytes") != observed.get("promoted_size_bytes")
        or observed.get("staged_sha256") != observed.get("promoted_sha256")
        or observed.get("staged_size_bytes") != observed.get("promoted_size_bytes")
        or receipt.get("provider_checksums_locally_verified") is not True
    ):
        raise OrbitControlError("orbit_transfer_receipt_identity_mismatch")
    return asset, receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", required=True, choices=EXPECTED_SOURCE_IDS)
    parser.add_argument("--custody-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output

    try:
        approval, intake, verification = guarded_controls()
        asset, transfer_receipt = promoted_binding(intake, args.source_id)
        requirements = [
            item for item in verification.get("asset_requirements", []) if item.get("source_id") == args.source_id
        ]
        if len(requirements) != 1:
            raise OrbitControlError("orbit_verification_requirement_absent_or_ambiguous")
        requirement = requirements[0]
        custody_root = args.custody_root.resolve(strict=True)
        expected_root = (PROJECT_ROOT / Path(*PurePosixPath(intake["custody_root"]).parts)).resolve(strict=True)
        if custody_root != expected_root:
            raise OrbitControlError("orbit_custody_root_mismatch")
        eof_path = (custody_root / Path(*PurePosixPath(asset["destination_relative_path"]).parts)).resolve()
        try:
            eof_path.relative_to(custody_root)
        except ValueError as exc:
            raise OrbitControlError("orbit_custody_path_escape") from exc
        if eof_path.as_posix().casefold() != str(transfer_receipt.get("destination_path", "")).replace("\\", "/").casefold():
            raise OrbitControlError("orbit_custody_path_differs_from_transfer_receipt")
        before_inventory = inventory(eof_path.parent)
    except (OrbitControlError, FileNotFoundError) as exc:
        code = exc.code if isinstance(exc, OrbitControlError) else "orbit_custody_root_missing"
        print(json.dumps({"status": "stopped", "code": code, "mutations_performed": False}, indent=2))
        return 12

    failure_code: str | None = None
    try:
        result = inspect_eof(eof_path, requirement)
    except OrbitControlError as exc:
        failure_code = exc.code
        result = {
            "status": "fail",
            "observed": {
                "size_bytes": eof_path.stat().st_size if eof_path.is_file() else None,
                "sha256": sha256_file(eof_path) if eof_path.is_file() else None,
            },
            "xml": None,
            "scene_binding": None,
        }
    after_inventory = inventory(eof_path.parent)
    custody_unchanged = before_inventory == after_inventory
    promoted = asset["observed"]
    identity_match = (
        result["observed"].get("size_bytes") == promoted.get("promoted_size_bytes")
        and result["observed"].get("sha256") == promoted.get("promoted_sha256")
        and result["observed"].get("sha256") == transfer_receipt.get("local_sha256")
    )
    status = "pass_orbit_input_only" if failure_code is None and custody_unchanged and identity_match else "fail"
    receipt = {
        "schema_version": "1.0",
        "verification_id": "NEPAL-M2-ORBIT-OFFLINE-VERIFICATION-001",
        "status": status,
        "verified_at_utc": now_utc(),
        "source_id": args.source_id,
        "asset_id": asset["asset_id"],
        "approval_sha256": sha256_file(APPROVAL_PATH),
        "active_intake_sha256": sha256_file(ACTIVE_INTAKE_PATH),
        "verification_contract_sha256": sha256_file(ACTIVE_VERIFICATION_PATH),
        "transfer_receipt_ref": asset["extensions"]["successful_attempt_receipt"],
        "transfer_receipt_sha256": asset["extensions"]["successful_attempt_receipt_sha256"],
        "custody_path": str(eof_path),
        "custody_inventory_before": before_inventory,
        "custody_inventory_after": after_inventory,
        "custody_unchanged": custody_unchanged,
        "promoted_identity_match": identity_match,
        "evaluation": result,
        "failure_code": failure_code,
        "claim_boundary": {
            "exact_orbit_input_identity_and_structure_established": status == "pass_orbit_input_only",
            "precise_orbit_equivalence_established": False,
            "geolocation_or_registration_accuracy_established": False,
            "vertical_datum_fitness_established": False,
            "radar_pixel_processing_executed": False,
            "baseline_established": False,
            "scientific_result_established": False,
            "authority_created": False,
        },
    }
    try:
        write_new(output, receipt)
    except OrbitControlError as exc:
        print(json.dumps({"status": "stopped", "code": exc.code, "mutations_performed": False}, indent=2))
        return 12
    print(json.dumps({"status": status, "source_id": args.source_id, "output": str(output)}, indent=2))
    return 0 if status == "pass_orbit_input_only" else 2


if __name__ == "__main__":
    raise SystemExit(main())
