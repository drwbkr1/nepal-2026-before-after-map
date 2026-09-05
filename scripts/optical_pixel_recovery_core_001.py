#!/usr/bin/env python3
"""Operational normalization and contract checks for optical recovery-001."""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_CONTRACT_REF = "config/qa/optical-pixel-readiness-contract-001.json"
ORIGINAL_CONTRACT_SHA256 = "2410955b686d545a39f1962c2924b8515cc130c3db9bbae5fe314f1e5bd04fa7"
APPROVAL_REF = "records/source-gates/m2-optical-pixel-recovery-001-approval.json"
APPROVAL_SHA256 = "983303532e95814828fd55d1f8c26c55d06d6785d579d236f8e5321072e8fcff"
REAL_001_RECEIPT_REF = "records/readiness/optical-pixel/m2-s2-pixel-readiness-real-001.json"
REAL_001_RECEIPT_SHA256 = "0f756c23ecaeaf017c196b0d79632960be5d249854d296f11fece639260d2164"
REAL_001_RECONCILIATION_REF = "records/readiness/m2-optical-pixel-real-001-reconciliation.json"
REAL_001_RECONCILIATION_SHA256 = "0e99672232d16208c77053e5343997c5dfc7ee4d4367ccaf68ee9eee13865e1a"


def sha256_file(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def normalize_analysis_grid(grid: dict[str, Any]) -> dict[str, Any]:
    """Return the existing grid with nested extent bounds exposed to the old executor."""
    if not isinstance(grid, dict):
        raise ValueError("analysis grid must be an object")
    extent = grid.get("extent")
    if not isinstance(extent, dict):
        raise ValueError("analysis grid extent must be an object")
    normalized = copy.deepcopy(grid)
    for key in ("xmin", "ymin", "xmax", "ymax"):
        value = extent.get(key)
        if not isinstance(value, (int, float)):
            raise ValueError(f"analysis grid extent {key} is missing or nonnumeric")
        if key in grid and float(grid[key]) != float(value):
            raise ValueError(f"analysis grid top-level {key} conflicts with extent")
        normalized[key] = float(value)
    return normalized


def validate_recovery_contract(contract: dict[str, Any], original: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if contract.get("contract_id") != "NEPAL-S2-PIXEL-READINESS-RECOVERY-001":
        errors.append("recovery contract identity differs")
    if contract.get("status") != "active_post_observation_operational_correction_one_attempt":
        errors.append("recovery contract status differs")
    authority = contract.get("recovery_authority", {})
    if authority.get("approval_ref") != APPROVAL_REF or authority.get("approval_sha256") != APPROVAL_SHA256:
        errors.append("recovery approval binding differs")
    source = contract.get("source_scientific_contract", {})
    if source.get("ref") != ORIGINAL_CONTRACT_REF or source.get("sha256") != ORIGINAL_CONTRACT_SHA256:
        errors.append("original scientific contract binding differs")
    if sha256_file(ORIGINAL_CONTRACT_REF) != ORIGINAL_CONTRACT_SHA256:
        errors.append("original scientific contract bytes drifted")
    if sha256_file(APPROVAL_REF) != APPROVAL_SHA256:
        errors.append("recovery approval bytes drifted")
    trigger = contract.get("retained_real_001", {})
    if trigger.get("receipt_ref") != REAL_001_RECEIPT_REF or trigger.get("receipt_sha256") != REAL_001_RECEIPT_SHA256:
        errors.append("real-001 receipt binding differs")
    if trigger.get("reconciliation_ref") != REAL_001_RECONCILIATION_REF or trigger.get("reconciliation_sha256") != REAL_001_RECONCILIATION_SHA256:
        errors.append("real-001 reconciliation binding differs")
    for key in ("inputs", "exact_pair", "approved_aoi_ids", "products", "analysis_grid", "mask", "registration", "execution_boundary", "decision_domain", "claim_boundary"):
        if contract.get(key) != original.get(key):
            errors.append(f"scientific contract section differs: {key}")
    attempt = contract.get("attempt", {})
    if attempt != {
        "attempt_id": "optical-pixel-readiness-recovery-001",
        "maximum_real_invocations": 1,
        "automatic_retry_authorized": False,
        "external_attempt_root": r"C:\Projects\Active\nepal-2026-before-after-map-data\derived\optical-pixel-readiness-recovery-001",
        "public_receipt_ref": "records/readiness/optical-pixel/m2-s2-pixel-readiness-recovery-001.json",
        "minimum_free_space_bytes": 2147483648,
        "collision_policy": "fail",
    }:
        errors.append("recovery attempt boundary differs")
    correction = contract.get("operational_correction", {})
    if correction.get("only_change") != "normalize existing analysis_grid.extent bounds for the unchanged executor":
        errors.append("operational correction differs")
    if correction.get("threshold_changes") is not False or correction.get("source_or_aoi_changes") is not False:
        errors.append("operational correction broadens scientific scope")
    implementation = contract.get("implementation", {})
    for key in ("core", "runner", "stage_gate", "final_preflight", "publication_gate_recorder", "arcgis_adapter", "portable_tests", "reconciler"):
        ref = implementation.get(f"{key}_ref")
        digest = implementation.get(f"{key}_sha256")
        if not isinstance(ref, str) or not isinstance(digest, str) or sha256_file(ref) != digest:
            errors.append(f"recovery implementation binding differs: {key}")
    return errors
