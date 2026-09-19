#!/usr/bin/env python3
"""Strict reusable controls for radar pixel/orbit recovery-002."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Iterable

import m2_radar_pixel_orbit_application_001_core as base
import m2_radar_pixel_orbit_application_recovery_001_core as recovery_001


CONTRACT_REF = "config/qa/m2-radar-pixel-orbit-application-recovery-002-contract.json"
BASE_CONTRACT_REF = "config/qa/m2-radar-pixel-orbit-application-001-contract.json"
RECOVERY_001_CONTRACT_REF = "config/qa/m2-radar-pixel-orbit-application-recovery-001-contract.json"
ATTEMPT_ID = "radar-pixel-orbit-application-recovery-002-real-001"
SOURCE_ORDER = [f"M1-SRC-{index:03d}" for index in range(1, 7)]
ROUTE_ORDER = ["PAIR-S1-ASC-R085-IW", "PAIR-S1-DESC-R121-IW"]
STAGE_ORDER = (
    "attempt_reserved",
    "terminal_and_cleanup_receipts_reserved",
    "fallback_journal_initialized",
    "identity_scan_started",
    "identity_scan_completed",
    "arcpy_import_started",
    "arcpy_import_completed",
    "product_info_started",
    "product_info_completed",
    "image_analyst_checkout_started",
    "image_analyst_checkout_completed",
    "spatial_checkout_started",
    "spatial_checkout_completed",
    "dem_mosaic_started",
    "dem_mosaic_completed",
    "analysis_support_started",
    "analysis_support_completed",
    "source_processing_fixed_order",
    "route_evaluation_fixed_order",
    "postattempt_identity_scan_started",
    "postattempt_identity_scan_completed",
    "terminal_receipt_persisted",
    "cleanup_started",
    "cleanup_completed_or_warning",
)
EXPECTED_HASHES = {
    "approval_sha256": "d16f3306d582257b32c25911e9f7f50efad935e9599a90e82247d6d813b29d40",
    "proposal_sha256": "86366bca8681bbe90dfdd19d6c5b676e490e6dd87c8e04c2900e9fb1df4b29ca",
    "review_bundle_sha256": "e699dfc3c4f7dd5ca697581cf4a299c66128fda7691473d65749681e3dfc211c",
    "review_reconciliation_sha256": "2193aa08750861bc71abec248f1cad7e6b9749b50e2e1debb4eb591c9665d97e",
}
ACTIVATION_SHA256 = "3d3118db0a7c87781ac3f3c690bb086397abb625e908b1b376fe5d8435fd2e57"
EXPECTED_REFS = {
    "approval_ref": "records/source-gates/m2-radar-pixel-orbit-application-recovery-002-approval.json",
    "activation_ref": "records/readiness/m2-radar-pixel-orbit-application-recovery-002-approval-activation.json",
    "proposal_ref": "contracts/milestone-002-radar-pixel-orbit-application-recovery-002-proposal.json",
    "review_bundle_ref": "reviews/m2-radar-pixel-orbit-application-recovery-002/review-bundle.json",
    "review_reconciliation_ref": "records/source-gates/m2-radar-pixel-orbit-application-recovery-002-review-reconciliation.json",
}
TOKEN_PATTERN = re.compile(r"(?i)(?:bearer\s+)?eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")
WINDOWS_PATH = re.compile(r"(?i)[A-Z]:\\[^\s\"']+")


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def write_new_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(canonical_bytes(value))
        stream.flush()
        os.fsync(stream.fileno())


def append_jsonl(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab", buffering=0) as stream:
        stream.write(json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n")
        os.fsync(stream.fileno())


def sanitize_text(value: object, replacements: Iterable[Path] = ()) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ")
    text = TOKEN_PATTERN.sub("[REDACTED_TOKEN]", text)
    for item in replacements:
        text = text.replace(str(item), "[REDACTED_PATH]")
    text = WINDOWS_PATH.sub("[REDACTED_PATH]", text)
    return text[:1000]


def safe_error(exc: BaseException, replacements: Iterable[Path] = ()) -> dict[str, str]:
    code = getattr(exc, "code", None)
    return {
        "failure_type": type(exc).__name__,
        "failure_code": sanitize_text(code if code is not None else "unexpected_processing_failure", replacements),
        "failure_message": sanitize_text(exc, replacements),
    }


def stage_positions(stages: Iterable[str]) -> list[int]:
    positions = {name: index for index, name in enumerate(STAGE_ORDER)}
    result: list[int] = []
    for stage in stages:
        if stage not in positions:
            raise base.RadarRouteError("unknown_recovery_002_stage", stage)
        result.append(positions[stage])
    return result


def _repo_file(root: Path, ref: str) -> Path:
    candidate = root / ref
    resolved_root = root.resolve()
    resolved = candidate.resolve(strict=False)
    if resolved == resolved_root or resolved_root not in resolved.parents or not candidate.is_file():
        raise base.RadarRouteError("repository_binding_missing_or_unsafe", ref)
    return candidate


def validate_contract(contract: dict[str, Any], root: Path) -> list[str]:
    errors: list[str] = []
    if contract.get("contract_id") != "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-002":
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
            if not isinstance(ref, str) or base.sha256_file(_repo_file(root, ref)) != expected:
                errors.append(f"bound authority file differs: {key}")
        except base.RadarRouteError:
            errors.append(f"bound authority file missing: {key}")
    try:
        if base.sha256_file(_repo_file(root, EXPECTED_REFS["activation_ref"])) != ACTIVATION_SHA256:
            errors.append("bound authority file differs: activation_ref")
    except base.RadarRouteError:
        errors.append("bound authority file missing: activation_ref")
    if contract.get("base_contract_ref") != BASE_CONTRACT_REF:
        errors.append("base contract ref differs")
    elif contract.get("base_contract_sha256") != base.sha256_file(_repo_file(root, BASE_CONTRACT_REF)):
        errors.append("base contract bytes differ")
    if contract.get("recovery_001_contract_ref") != RECOVERY_001_CONTRACT_REF:
        errors.append("recovery-001 contract ref differs")
    elif contract.get("recovery_001_contract_sha256") != base.sha256_file(_repo_file(root, RECOVERY_001_CONTRACT_REF)):
        errors.append("recovery-001 contract bytes differ")
    if contract.get("fixed_source_order") != SOURCE_ORDER:
        errors.append("source order differs")
    if contract.get("fixed_route_order") != ROUTE_ORDER:
        errors.append("route order differs")
    if contract.get("stage_order") != list(STAGE_ORDER):
        errors.append("stage order differs")
    recovery_001_contract = base.load_object(_repo_file(root, RECOVERY_001_CONTRACT_REF))
    if contract.get("inventory_comparison") != recovery_001_contract.get("inventory_comparison"):
        errors.append("inventory comparator differs from recovery-001")
    attempt = contract.get("attempt", {})
    expected_attempt = {
        "attempt_id": ATTEMPT_ID,
        "consumed_attempt_ids": [
            "radar-pixel-orbit-application-recovery-001-real-001",
            "radar-delayed-import-probe-receipt-recovery-001-real-001",
        ],
        "maximum_final_preflights": 1,
        "maximum_real_attempts": 1,
        "maximum_orbit_application_attempts_per_source": 1,
        "maximum_qa_processing_attempts_per_source": 1,
        "maximum_route_qa_attempts_per_pair": 1,
        "process_count": 1,
        "automatic_retry_authorized": False,
        "stop_on_first_failure": True,
        "external_attempt_root": (
            r"C:\Projects\Active\nepal-2026-before-after-map-data\derived\radar-pixel-orbit-application-recovery-002"
            r"\radar-pixel-orbit-application-recovery-002-real-001"
        ),
        "minimum_free_space_bytes": 64_424_509_440,
        "collision_policy": "fail",
    }
    if attempt != expected_attempt:
        errors.append("attempt boundary differs")
    receipt = contract.get("receipt_durability", {})
    for key in (
        "terminal_identity_reserved_before_project_data_read",
        "cleanup_identity_reserved_before_project_data_read",
        "stage_journal_initialized_before_project_data_read",
        "fallback_journal_initialized_before_project_data_read",
        "first_sanitized_exception_recorded_before_normal_terminal_assembly",
        "persistence_errors_append_without_replacing_first_exception",
        "cleanup_outer_finally_independent_of_terminal_serialization",
    ):
        if receipt.get(key) is not True:
            errors.append(f"receipt durability differs: {key}")
    if receipt.get("fallback_is_success_evidence") is not False:
        errors.append("fallback claim boundary differs")
    for key in ("network_requests", "authentication", "source_overwrite", "output_overwrite", "automatic_retry"):
        if contract.get("execution_boundary", {}).get(key) != "prohibited":
            errors.append(f"execution boundary differs: {key}")
    if any(value is not False for value in contract.get("claim_boundary", {}).values()):
        errors.append("claim boundary releases prohibited work")
    return errors


def load_execution_plan(root: Path, contract_ref: str = CONTRACT_REF) -> dict[str, Any]:
    contract_path = _repo_file(root, contract_ref)
    contract = base.load_object(contract_path)
    errors = validate_contract(contract, root)
    if errors:
        raise base.RadarRouteError("recovery_002_contract_invalid", "; ".join(errors))
    plan = base.load_execution_plan(root, BASE_CONTRACT_REF)
    merged = dict(plan["contract"])
    merged["contract_id"] = contract["contract_id"]
    merged["status"] = contract["status"]
    merged["attempt"] = contract["attempt"]
    merged["recovery_authority"] = contract["authority"]
    merged["inventory_comparison"] = contract["inventory_comparison"]
    merged["receipt_durability"] = contract["receipt_durability"]
    merged["stage_order"] = contract["stage_order"]
    plan.update({
        "contract": merged,
        "contract_ref": contract_ref,
        "contract_sha256": base.sha256_file(contract_path),
        "base_contract_ref": BASE_CONTRACT_REF,
        "base_contract_sha256": contract["base_contract_sha256"],
        "recovery_001_contract_ref": RECOVERY_001_CONTRACT_REF,
        "recovery_001_contract_sha256": contract["recovery_001_contract_sha256"],
        "recovery_contract": contract,
    })
    return plan


def verify_external_identities(plan: dict[str, Any]) -> dict[str, Any]:
    return recovery_001.verify_external_identities(plan)


__all__ = [
    "ATTEMPT_ID",
    "BASE_CONTRACT_REF",
    "CONTRACT_REF",
    "RECOVERY_001_CONTRACT_REF",
    "ROUTE_ORDER",
    "SOURCE_ORDER",
    "STAGE_ORDER",
    "append_jsonl",
    "canonical_bytes",
    "load_execution_plan",
    "safe_error",
    "sanitize_text",
    "stage_positions",
    "validate_contract",
    "verify_external_identities",
    "write_new_json",
]
