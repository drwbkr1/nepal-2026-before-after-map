#!/usr/bin/env python3
"""Strict controls for ApplyOrbitCorrection input-resolution receipt recovery-001."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, BinaryIO, Iterable

from m2_radar_apply_orbit_correction_input_resolution_diagnostic_001_core import (
    ALLOWED_ARCPY_CALLS,
    DiagnosticError,
    EXPECTED_ATTEMPT_ROOT,
    EXPECTED_MANIFEST_RELATIVE,
    EXPECTED_ORBIT_PATH,
    EXPECTED_ORBIT_SHA256,
    EXPECTED_ORBIT_SIZE_BYTES,
    EXPECTED_SAFE_RELATIVE,
    catalog_path_class,
    contained_windows_child,
    describe_summary,
    sanitize_text,
)


CONTRACT_REF = (
    "config/qa/m2-radar-apply-orbit-correction-input-resolution-diagnostic-"
    "receipt-persistence-recovery-001-contract.json"
)
ATTEMPT_ID = (
    "radar-apply-orbit-correction-input-resolution-diagnostic-"
    "receipt-persistence-recovery-001-real-001"
)
CONSUMED_PREFIX = "m2-radar-apply-orbit-correction-input-resolution-diagnostic-001"
PREFIX = "m2-radar-apply-orbit-correction-input-resolution-diagnostic-receipt-persistence-recovery-001"
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
EXPECTED_AUTHORITY_REFS = {
    "approval_ref": f"records/source-gates/{PREFIX}-approval.json",
    "proposal_ref": (
        "contracts/milestone-002-radar-apply-orbit-correction-input-resolution-diagnostic-"
        "receipt-persistence-recovery-001-proposal.json"
    ),
    "review_bundle_ref": f"reviews/{PREFIX}/review-bundle.json",
    "review_reconciliation_ref": f"records/source-gates/{PREFIX}-review-reconciliation.json",
    "activation_ref": f"records/readiness/{PREFIX}-approval-activation.json",
}


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise DiagnosticError("json_root_not_object")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_new_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(canonical_bytes(value))
        stream.flush()
        os.fsync(stream.fileno())


def append_jsonl(path: Path, value: object, *, initialize: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "xb" if initialize else "ab"
    with path.open(mode, buffering=0) as stream:
        stream.write(json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n")
        os.fsync(stream.fileno())


def reserve_output(path: Path) -> BinaryIO:
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = path.open("xb+")
    stream.flush()
    os.fsync(stream.fileno())
    return stream


def persist_reserved(stream: BinaryIO, value: object) -> None:
    payload = canonical_bytes(value)
    stream.seek(0)
    stream.write(payload)
    stream.truncate()
    stream.flush()
    os.fsync(stream.fileno())
    stream.close()


def safe_error(exc: BaseException, replacements: Iterable[Path] = ()) -> dict[str, str]:
    code = getattr(exc, "code", "unexpected_diagnostic_recovery_failure")
    return {
        "failure_type": type(exc).__name__,
        "failure_code": sanitize_text(code, replacements),
        "failure_message": sanitize_text(exc, replacements),
    }


def _repo_file(root: Path, ref: str) -> Path:
    path = root / ref
    resolved_root = root.resolve()
    resolved = path.resolve(strict=False)
    if resolved_root not in resolved.parents or not path.is_file():
        raise DiagnosticError("repository_binding_missing_or_unsafe", ref)
    return path


def validate_contract(contract: dict[str, Any], root: Path) -> list[str]:
    errors: list[str] = []
    if contract.get("contract_id") != (
        "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-"
        "RECEIPT-PERSISTENCE-RECOVERY-001-CONTRACT"
    ):
        errors.append("contract identity differs")
    if contract.get("status") != "approved_implementation_publication_pending":
        errors.append("contract status differs")
    authority = contract.get("authority", {})
    for key, expected_ref in EXPECTED_AUTHORITY_REFS.items():
        if authority.get(key) != expected_ref:
            errors.append(f"authority ref differs: {key}")
            continue
        hash_key = key.removesuffix("_ref") + "_sha256"
        expected_hash = authority.get(hash_key)
        try:
            if not isinstance(expected_hash, str) or sha256_file(_repo_file(root, expected_ref)) != expected_hash:
                errors.append(f"authority binding differs: {key}")
        except DiagnosticError:
            errors.append(f"authority binding missing: {key}")
    attempt = contract.get("attempt", {})
    if attempt != {
        "attempt_id": ATTEMPT_ID,
        "maximum_processes": 1,
        "automatic_retry": False,
        "distinct_from_consumed_attempt": True,
        "mode": "read_only_single_process_no_geoprocessing",
    }:
        errors.append("attempt boundary differs")
    expected_inputs = {
        "terminal_attempt_id": "radar-pixel-orbit-application-recovery-002-real-001",
        "source_id": "M1-SRC-001",
        "orbit_source_id": "M2-ORB-001",
        "recovery_attempt_root": EXPECTED_ATTEMPT_ROOT,
        "safe_directory_relative": EXPECTED_SAFE_RELATIVE,
        "manifest_relative": EXPECTED_MANIFEST_RELATIVE,
        "orbit_path": EXPECTED_ORBIT_PATH,
        "orbit_sha256": EXPECTED_ORBIT_SHA256,
        "orbit_size_bytes": EXPECTED_ORBIT_SIZE_BYTES,
    }
    inputs = contract.get("exact_inputs", {})
    if inputs != expected_inputs:
        errors.append("exact input boundary differs")
    try:
        contained_windows_child(inputs.get("recovery_attempt_root", ""), inputs.get("safe_directory_relative", ""))
        contained_windows_child(inputs.get("recovery_attempt_root", ""), inputs.get("manifest_relative", ""))
    except (DiagnosticError, TypeError):
        errors.append("candidate containment differs")
    if contract.get("arcgis_read_only_calls") != ALLOWED_ARCPY_CALLS:
        errors.append("ArcPy allowlist differs")
    durability = contract.get("receipt_durability", {})
    required_durability = (
        "new_terminal_identity_reserved_before_external_reads",
        "new_cleanup_identity_reserved_before_external_reads",
        "fallback_journal_initialized_before_external_reads",
        "function_local_datetime_imports",
        "original_sanitized_exception_recorded_before_normal_terminal_assembly",
        "later_persistence_error_cannot_replace_original_error",
        "cleanup_recording_independent_of_terminal_serialization",
        "fallback_is_not_success_evidence",
        "consumed_empty_receipts_remain_immutable",
    )
    if any(durability.get(key) is not True for key in required_durability):
        errors.append("receipt durability differs")
    protected = contract.get("protected_consumed_receipts", {})
    expected_protected = {
        "terminal_ref": f"records/processing/{CONSUMED_PREFIX}-terminal.json",
        "terminal_sha256": EMPTY_SHA256,
        "cleanup_ref": f"records/processing/{CONSUMED_PREFIX}-cleanup.json",
        "cleanup_sha256": EMPTY_SHA256,
        "required_bytes_each": 0,
    }
    if protected != expected_protected:
        errors.append("protected consumed receipt contract differs")
    else:
        for ref_key, sha_key in (("terminal_ref", "terminal_sha256"), ("cleanup_ref", "cleanup_sha256")):
            try:
                path = _repo_file(root, protected[ref_key])
                if path.stat().st_size != 0 or sha256_file(path) != protected[sha_key]:
                    errors.append(f"consumed receipt differs: {ref_key}")
            except DiagnosticError:
                errors.append(f"consumed receipt missing: {ref_key}")
    limits = contract.get("limits", {})
    if any(limits.get(key) != 0 for key in (
        "apply_orbit_correction_calls",
        "geoprocessing_tool_calls",
        "network_requests",
        "credential_actions",
        "source_orbit_or_dem_copies",
        "source_orbit_or_dem_mutations",
        "derived_raster_outputs",
        "baseline_or_change_actions",
        "scientific_outputs",
    )):
        errors.append("zero-action limits differ")
    return errors


def load_contract(root: Path) -> dict[str, Any]:
    contract = load_object(_repo_file(root, CONTRACT_REF))
    errors = validate_contract(contract, root)
    if errors:
        raise DiagnosticError("diagnostic_recovery_contract_invalid", "; ".join(errors))
    return contract


def external_paths(contract: dict[str, Any]) -> dict[str, Path]:
    inputs = contract["exact_inputs"]
    attempt_root = inputs["recovery_attempt_root"]
    return {
        "attempt_root": Path(attempt_root),
        "safe_directory": Path(contained_windows_child(attempt_root, inputs["safe_directory_relative"])),
        "manifest": Path(contained_windows_child(attempt_root, inputs["manifest_relative"])),
        "orbit": Path(inputs["orbit_path"]),
    }


__all__ = [
    "ALLOWED_ARCPY_CALLS",
    "ATTEMPT_ID",
    "CONSUMED_PREFIX",
    "CONTRACT_REF",
    "DiagnosticError",
    "EMPTY_SHA256",
    "EXPECTED_ATTEMPT_ROOT",
    "EXPECTED_MANIFEST_RELATIVE",
    "EXPECTED_ORBIT_PATH",
    "EXPECTED_ORBIT_SHA256",
    "EXPECTED_ORBIT_SIZE_BYTES",
    "EXPECTED_SAFE_RELATIVE",
    "PREFIX",
    "append_jsonl",
    "canonical_bytes",
    "catalog_path_class",
    "describe_summary",
    "external_paths",
    "load_contract",
    "load_object",
    "persist_reserved",
    "reserve_output",
    "safe_error",
    "sanitize_text",
    "sha256_file",
    "validate_contract",
    "write_new_json",
]
