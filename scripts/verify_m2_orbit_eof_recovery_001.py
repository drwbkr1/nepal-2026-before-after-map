#!/usr/bin/env python3
"""Verify one exact orbit EOF only after reserving its append-only recovery receipt."""

from __future__ import annotations

import argparse
import json
import os
import stat
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO

from m2_orbit_io_core import OrbitControlError, inspect_eof
from m2_transfer_core import sha256_file
from verify_m2_orbit_eof import inventory, promoted_binding


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent.resolve()
APPROVAL_REF = "records/source-gates/m2-orbit-offline-verification-recovery-001-approval.json"
APPROVAL_SHA256 = "315812935fe725b5c2928a27abc2b51faf561c423065de6216f975cecbe81f30"
CANDIDATE_REF = "contracts/m2-orbit-offline-verification-recovery-001.json"
CANDIDATE_SHA256 = "8db4774dfb36ce9718988c23d9a480a01028055a6a28a1bbf301a926e466df68"
ACTIVE_REF = "contracts/m2-orbit-offline-verification.json"
INTAKE_REF = "contracts/m2-orbit-intake.json"
PREFLIGHT_REF = "records/readiness/m2-orbit-offline-verification-recovery-001-final-preflight.json"
SOURCE_IDS = ["M2-ORB-001", "M2-ORB-002", "M2-ORB-003", "M2-ORB-004"]
OUTPUT_REFS = {
    "M2-ORB-001": "records/acquisition/orbit-verification/m2-orb-001-offline-verification-recovery-001.json",
    "M2-ORB-002": "records/acquisition/orbit-verification/m2-orb-002-offline-verification-001.json",
    "M2-ORB-003": "records/acquisition/orbit-verification/m2-orb-003-offline-verification-001.json",
    "M2-ORB-004": "records/acquisition/orbit-verification/m2-orb-004-offline-verification-001.json",
}


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load(ref: str) -> dict[str, Any]:
    value = json.loads((ROOT / ref).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise OrbitControlError("control_root_not_object")
    return value


def sha256(ref: str) -> str:
    return sha256_file(ROOT / ref)


def is_reparse_point(path: Path) -> bool:
    attributes = getattr(os.lstat(path), "st_file_attributes", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def reserve_receipt(path: Path) -> BinaryIO:
    parent = path.parent
    expected_parent = (ROOT / "records/acquisition/orbit-verification").resolve()
    try:
        resolved_parent = parent.resolve(strict=True)
        resolved_parent.relative_to(ROOT.resolve())
    except (FileNotFoundError, ValueError) as exc:
        raise OrbitControlError("verification_output_parent_missing_or_escaped") from exc
    if (
        resolved_parent != expected_parent
        or not parent.is_dir()
        or parent.is_symlink()
        or is_reparse_point(parent)
    ):
        raise OrbitControlError("verification_output_parent_not_exact_real_directory")
    try:
        stream = path.open("xb")
    except FileExistsError as exc:
        raise OrbitControlError("verification_output_collision") from exc
    try:
        stream.flush()
        os.fsync(stream.fileno())
    except OSError as exc:
        stream.close()
        raise OrbitControlError("verification_receipt_reservation_fsync_failed") from exc
    return stream


def write_reserved_receipt(stream: BinaryIO, value: dict[str, Any]) -> None:
    if stream.tell() != 0:
        raise OrbitControlError("reserved_receipt_not_empty")
    stream.write((json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    stream.flush()
    os.fsync(stream.fileno())


def guarded_controls(source_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    if sha256(APPROVAL_REF) != APPROVAL_SHA256 or sha256(CANDIDATE_REF) != CANDIDATE_SHA256:
        raise OrbitControlError("recovery_approval_or_candidate_identity_drift")
    approval = load(APPROVAL_REF)
    candidate = load(CANDIDATE_REF)
    active = load(ACTIVE_REF)
    intake = load(INTAKE_REF)
    preflight = load(PREFLIGHT_REF)
    extension = active.get("extensions", {}).get("offline_verification_recovery_001", {})
    if (
        approval.get("status") != "approved_exact_pre_read_receipt_reservation_recovery_only"
        or approval.get("authorized_recovery", {}).get("source_ids_in_exact_order") != SOURCE_IDS
        or candidate.get("status") != "candidate_public_ci_pending"
        or candidate.get("source_ids_in_exact_order") != SOURCE_IDS
        or candidate.get("output_refs") != OUTPUT_REFS
        or active.get("status") != "active_recovery_ready_for_offline_verification"
        or active.get("bindings", {}).get("active_intake_sha256_current") != sha256(INTAKE_REF)
        or extension.get("candidate_sha256") != CANDIDATE_SHA256
        or extension.get("approval_sha256") != APPROVAL_SHA256
        or extension.get("public_ci") != "pass"
        or extension.get("final_no_content_preflight") != "required"
        or extension.get("source_ids_in_exact_order") != SOURCE_IDS
        or extension.get("m2_orb_001_recovery_attempts_remaining") != 1
        or extension.get("remaining_source_attempts_per_source_remaining") != 1
        or extension.get("automatic_retry_authorized") is not False
        or preflight.get("status") != "pass_no_content_ready_for_exact_recovery_sequence"
        or preflight.get("bindings", {}).get("active_verification_sha256") != sha256(ACTIVE_REF)
        or preflight.get("bindings", {}).get("candidate_contract_sha256") != CANDIDATE_SHA256
        or preflight.get("source_ids_in_exact_order") != SOURCE_IDS
        or preflight.get("output_refs") != OUTPUT_REFS
        or preflight.get("assertions", {}).get("eof_content_read") is not False
        or source_id not in SOURCE_IDS
    ):
        raise OrbitControlError("active_recovery_verification_binding_drift")
    requirements = [item for item in candidate.get("asset_requirements", []) if item.get("source_id") == source_id]
    if len(requirements) != 1 or requirements[0].get("maximum_osv_endpoint_tolerance_seconds") != 1.0:
        raise OrbitControlError("recovery_verification_requirement_absent_or_drifted")
    return intake, active, preflight, requirements[0]


def execute(source_id: str, custody_root_arg: Path, output_arg: Path) -> tuple[int, dict[str, Any]]:
    reserved: BinaryIO | None = None
    output = output_arg if output_arg.is_absolute() else ROOT / output_arg
    try:
        intake, active, preflight, requirement = guarded_controls(source_id)
        exact_output = (ROOT / OUTPUT_REFS[source_id]).resolve()
        if output.resolve() != exact_output:
            raise OrbitControlError("orbit_verification_output_path_not_exact")
        asset, transfer_evidence = promoted_binding(intake, source_id)
        custody_root = custody_root_arg.resolve(strict=True)
        expected_root = (PROJECT_ROOT / Path(*PurePosixPath(intake["custody_root"]).parts)).resolve(strict=True)
        if custody_root != expected_root:
            raise OrbitControlError("orbit_custody_root_mismatch")
        eof_path = (custody_root / Path(*PurePosixPath(asset["destination_relative_path"]).parts)).resolve()
        eof_path.relative_to(custody_root)
        recorded_destination = transfer_evidence.get("destination_path")
        if recorded_destination is not None and eof_path.as_posix().casefold() != str(recorded_destination).replace("\\", "/").casefold():
            raise OrbitControlError("orbit_custody_path_differs_from_transfer_receipt")
        reserved = reserve_receipt(output)
    except (OrbitControlError, FileNotFoundError, OSError, ValueError) as exc:
        code = exc.code if isinstance(exc, OrbitControlError) else "recovery_pre_read_control_failure"
        reservation_interrupted = output.exists() and code == "verification_receipt_reservation_fsync_failed"
        return (13 if reservation_interrupted else 12), {
            "status": "terminal_persistence_interruption" if reservation_interrupted else "stopped_before_eof_read",
            "code": code,
            "receipt_reserved": output.exists() and code != "verification_output_collision",
            "reserved_receipt_preserved": reservation_interrupted,
            "external_custody_mutated": False,
        }

    try:
        before_inventory = inventory(eof_path.parent)
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
            and result["observed"].get("sha256") == transfer_evidence.get("identity", {}).get("sha256")
        )
        status_value = "pass_orbit_input_only" if failure_code is None and custody_unchanged and identity_match else "fail"
        attempt_identity = (
            "m2-orb-001-offline-verification-recovery-001"
            if source_id == "M2-ORB-001"
            else f"{source_id.casefold()}-offline-verification-001"
        )
        receipt = {
            "schema_version": "1.0",
            "verification_id": "NEPAL-M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001",
            "attempt_identity": attempt_identity,
            "status": status_value,
            "verified_at_utc": now_utc(),
            "source_id": source_id,
            "asset_id": asset["asset_id"],
            "approval_sha256": APPROVAL_SHA256,
            "candidate_contract_sha256": CANDIDATE_SHA256,
            "active_verification_sha256": sha256(ACTIVE_REF),
            "final_preflight_sha256": sha256(PREFLIGHT_REF),
            "transfer_receipt_ref": transfer_evidence["ref"],
            "transfer_receipt_sha256": transfer_evidence["sha256"],
            "custody_path": str(eof_path),
            "custody_inventory_before": before_inventory,
            "custody_inventory_after": after_inventory,
            "custody_unchanged": custody_unchanged,
            "promoted_identity_match": identity_match,
            "evaluation": result,
            "failure_code": failure_code,
            "persistence": {
                "receipt_reserved_before_eof_content_read": True,
                "exclusive_creation": True,
                "complete_receipt_written_through_reserved_handle": True,
                "flush_and_fsync_required": True,
                "reuse_authorized": False,
            },
            "claim_boundary": {
                "exact_orbit_input_identity_and_structure_established": status_value == "pass_orbit_input_only",
                "precise_orbit_equivalence_established": False,
                "geolocation_or_registration_accuracy_established": False,
                "vertical_datum_fitness_established": False,
                "radar_pixel_processing_executed": False,
                "baseline_established": False,
                "scientific_result_established": False,
                "authority_created": False,
            },
        }
        write_reserved_receipt(reserved, receipt)
        return (0 if status_value == "pass_orbit_input_only" else 2), {
            "status": status_value,
            "source_id": source_id,
            "output": str(output),
            "receipt_reserved_before_eof_read": True,
        }
    except Exception as exc:  # preserve the exclusive reservation as terminal interruption evidence
        return 13, {
            "status": "terminal_persistence_interruption",
            "code": type(exc).__name__,
            "source_id": source_id,
            "output": str(output),
            "reserved_receipt_preserved": True,
            "automatic_retry_authorized": False,
            "external_custody_mutated": False,
        }
    finally:
        if reserved is not None:
            reserved.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", required=True, choices=SOURCE_IDS)
    parser.add_argument("--custody-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    code, result = execute(args.source_id, args.custody_root, args.output)
    print(json.dumps(result, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
