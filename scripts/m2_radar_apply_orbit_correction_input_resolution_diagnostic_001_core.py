#!/usr/bin/env python3
"""Strict reusable controls for the read-only input-resolution diagnostic."""

from __future__ import annotations

import hashlib
import json
import ntpath
import os
import re
from pathlib import Path
from typing import Any, BinaryIO, Iterable


CONTRACT_REF = "config/qa/m2-radar-apply-orbit-correction-input-resolution-diagnostic-001-contract.json"
ATTEMPT_ID = "radar-apply-orbit-correction-input-resolution-diagnostic-001-real-001"
EXPECTED_REFS = {
    "approval_ref": "records/source-gates/m2-radar-apply-orbit-correction-input-resolution-diagnostic-001-approval.json",
    "proposal_ref": "contracts/milestone-002-radar-apply-orbit-correction-input-resolution-diagnostic-001-proposal.json",
    "review_bundle_ref": "reviews/m2-radar-apply-orbit-correction-input-resolution-diagnostic-001/review-bundle.json",
    "review_reconciliation_ref": "records/source-gates/m2-radar-apply-orbit-correction-input-resolution-diagnostic-001-review-reconciliation.json",
    "activation_ref": "records/readiness/m2-radar-apply-orbit-correction-input-resolution-diagnostic-001-approval-activation.json",
}
EXPECTED_HASHES = {
    "approval_sha256": "be935d0011e2819debf45f4bc335ec035bc6e718380a3ad0429d5be88b269287",
    "proposal_sha256": "bb318432bf3a63f2bb75d2b1ea69716b6fbade9917d7c35ff8388d3edaa41d84",
    "review_bundle_sha256": "88c5e50d2f8f223e1c148caa0212e1b28ba4c80eb3eacae23be7e4f63bd477af",
    "review_reconciliation_sha256": "b36533fb12846f75eeba8edfb2bdc71ce7976883b1fa23759afb41de38a0d9a0",
    "activation_sha256": "624c31a184d2e960aae9c5f83b31a248757ae782799f73c832432f39d4342339",
}
EXPECTED_ATTEMPT_ROOT = (
    r"C:\Projects\Active\nepal-2026-before-after-map-data\derived\radar-pixel-orbit-application-recovery-002"
    r"\radar-pixel-orbit-application-recovery-002-real-001"
)
EXPECTED_SAFE_RELATIVE = (
    "sources/m1-src-001/"
    "S1D_IW_GRDH_1SDV_20260816T122116_20260816T122141_004151_007980_B057.SAFE"
)
EXPECTED_MANIFEST_RELATIVE = f"{EXPECTED_SAFE_RELATIVE}/manifest.safe"
EXPECTED_ORBIT_PATH = (
    r"C:\Projects\Active\nepal-2026-before-after-map-data\custody\orbits\s1d\resorb\m2-orb-001"
    r"\S1D_OPER_AUX_RESORB_OPOD_20260816T143208_V20260816T103526_20260816T140956.EOF"
)
EXPECTED_ORBIT_SHA256 = "a72c93e500a1c09b62b4cd31889837c9d57ccc41542b16397ff9f2c0fccba3f4"
EXPECTED_ORBIT_SIZE_BYTES = 639533
ALLOWED_ARCPY_CALLS = ["GetInstallInfo", "ProductInfo", "CheckExtension", "Usage", "Exists", "Describe"]
TOKEN_PATTERN = re.compile(r"(?i)(?:bearer\s+)?eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")
WINDOWS_PATH = re.compile(r"(?i)[A-Z]:\\[^\s\"']+")


class DiagnosticError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(detail or code)
        self.code = code


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


def sanitize_text(value: object, replacements: Iterable[Path] = ()) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ")
    text = TOKEN_PATTERN.sub("[REDACTED_TOKEN]", text)
    for item in replacements:
        text = text.replace(str(item), "[REDACTED_PATH]")
    text = WINDOWS_PATH.sub("[REDACTED_PATH]", text)
    return text[:1000]


def safe_error(exc: BaseException, replacements: Iterable[Path] = ()) -> dict[str, str]:
    code = getattr(exc, "code", "unexpected_diagnostic_failure")
    return {
        "failure_type": type(exc).__name__,
        "failure_code": sanitize_text(code, replacements),
        "failure_message": sanitize_text(exc, replacements),
    }


def lexical_windows_path(value: str) -> str:
    return ntpath.normcase(ntpath.normpath(value))


def contained_windows_child(parent: str, relative: str) -> str:
    candidate_relative = Path(relative)
    if candidate_relative.is_absolute() or any(part in {"", ".", ".."} for part in candidate_relative.parts):
        raise DiagnosticError("unsafe_relative_candidate")
    parent_norm = lexical_windows_path(parent)
    candidate = ntpath.join(parent, *candidate_relative.parts)
    candidate_norm = lexical_windows_path(candidate)
    if ntpath.commonpath([parent_norm, candidate_norm]) != parent_norm or candidate_norm == parent_norm:
        raise DiagnosticError("candidate_path_escape")
    return candidate


def _repo_file(root: Path, ref: str) -> Path:
    path = root / ref
    resolved_root = root.resolve()
    resolved = path.resolve(strict=False)
    if resolved_root not in resolved.parents or not path.is_file():
        raise DiagnosticError("repository_binding_missing_or_unsafe", ref)
    return path


def validate_contract(contract: dict[str, Any], root: Path) -> list[str]:
    errors: list[str] = []
    if contract.get("contract_id") != "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-CONTRACT":
        errors.append("contract identity differs")
    if contract.get("status") != "approved_implementation_publication_pending":
        errors.append("contract status differs")
    authority = contract.get("authority", {})
    for key, expected in EXPECTED_REFS.items():
        if authority.get(key) != expected:
            errors.append(f"authority ref differs: {key}")
    for key, expected in EXPECTED_HASHES.items():
        if authority.get(key) != expected:
            errors.append(f"authority hash differs: {key}")
            continue
        ref = authority.get(key.removesuffix("_sha256") + "_ref")
        try:
            if not isinstance(ref, str) or sha256_file(_repo_file(root, ref)) != expected:
                errors.append(f"bound authority file differs: {key}")
        except DiagnosticError:
            errors.append(f"bound authority file missing: {key}")
    diagnostic = contract.get("diagnostic", {})
    if diagnostic != {
        "diagnostic_id": ATTEMPT_ID,
        "maximum_processes": 1,
        "maximum_final_preflights": 1,
        "automatic_retry": False,
        "mode": "read_only_single_process_no_geoprocessing",
    }:
        errors.append("diagnostic boundary differs")
    inputs = contract.get("exact_inputs", {})
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
    if inputs != expected_inputs:
        errors.append("exact input boundary differs")
    try:
        contained_windows_child(inputs.get("recovery_attempt_root", ""), inputs.get("safe_directory_relative", ""))
        contained_windows_child(inputs.get("recovery_attempt_root", ""), inputs.get("manifest_relative", ""))
    except (DiagnosticError, TypeError):
        errors.append("candidate path containment differs")
    if contract.get("arcgis_read_only_calls") != ALLOWED_ARCPY_CALLS:
        errors.append("ArcPy read-only call allowlist differs")
    durability = contract.get("receipt_durability", {})
    if any(durability.get(key) is not True for key in (
        "terminal_identity_reserved_before_external_content_access",
        "cleanup_identity_reserved_before_external_content_access",
        "exclusive_no_replace",
        "reserved_handles_flushed_and_fsynced",
    )):
        errors.append("receipt durability differs")
    limits = contract.get("limits", {})
    if any(limits.get(key) != 0 for key in (
        "apply_orbit_correction_calls", "geoprocessing_tool_calls", "network_requests",
        "credential_actions", "source_orbit_or_dem_copies", "source_orbit_or_dem_mutations",
        "derived_raster_outputs", "baseline_or_change_actions", "scientific_outputs",
    )):
        errors.append("zero-action limits differ")
    protected = contract.get("protected_public_evidence", [])
    if not isinstance(protected, list) or len(protected) != 10:
        errors.append("protected evidence set differs")
    else:
        for item in protected:
            ref = item.get("path")
            expected = item.get("sha256")
            try:
                if not isinstance(ref, str) or not isinstance(expected, str) or sha256_file(_repo_file(root, ref)) != expected:
                    errors.append(f"protected evidence differs: {ref}")
            except DiagnosticError:
                errors.append(f"protected evidence missing: {ref}")
    return errors


def load_contract(root: Path) -> dict[str, Any]:
    path = _repo_file(root, CONTRACT_REF)
    contract = load_object(path)
    errors = validate_contract(contract, root)
    if errors:
        raise DiagnosticError("diagnostic_contract_invalid", "; ".join(errors))
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


def catalog_path_class(value: object, paths: dict[str, Path]) -> str:
    if not isinstance(value, str) or not value:
        return "unavailable"
    observed = lexical_windows_path(value)
    exact = {name: lexical_windows_path(str(path)) for name, path in paths.items()}
    for name in ("safe_directory", "manifest", "orbit"):
        if observed == exact[name]:
            return f"exact_{name}"
    safe = exact["safe_directory"]
    try:
        if ntpath.commonpath([safe, observed]) == safe and observed != safe:
            return "inside_exact_safe_directory"
    except ValueError:
        pass
    return "other_or_unresolved"


def describe_summary(description: Any, paths: dict[str, Path]) -> dict[str, Any]:
    children = getattr(description, "children", None)
    try:
        children_count = len(children) if children is not None else None
    except TypeError:
        children_count = None
    return {
        "data_type": sanitize_text(getattr(description, "dataType", None), paths.values()),
        "dataset_type": sanitize_text(getattr(description, "datasetType", None), paths.values()),
        "catalog_path_class": catalog_path_class(getattr(description, "catalogPath", None), paths),
        "children_count": children_count,
    }


__all__ = [
    "ALLOWED_ARCPY_CALLS", "ATTEMPT_ID", "CONTRACT_REF", "DiagnosticError",
    "EXPECTED_ATTEMPT_ROOT", "EXPECTED_MANIFEST_RELATIVE", "EXPECTED_ORBIT_PATH",
    "EXPECTED_ORBIT_SHA256", "EXPECTED_ORBIT_SIZE_BYTES", "EXPECTED_SAFE_RELATIVE",
    "canonical_bytes", "catalog_path_class", "describe_summary", "external_paths",
    "load_contract", "load_object", "persist_reserved", "reserve_output", "safe_error",
    "sanitize_text", "sha256_file", "validate_contract", "write_new_json",
]
