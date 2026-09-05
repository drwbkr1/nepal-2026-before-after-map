#!/usr/bin/env python3
"""Validate publication and no-pixel gates for optical recovery-001."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APPROVAL_REF = "records/source-gates/m2-optical-pixel-recovery-001-approval.json"
ACTIVATION_REF = "records/readiness/m2-optical-pixel-recovery-001-activation.json"
REAL_001_RECONCILIATION_REF = "records/readiness/m2-optical-pixel-real-001-reconciliation.json"
CONTRACT_REF = "config/qa/optical-pixel-readiness-contract-recovery-001.json"
READINESS_REF = "records/readiness/m2-optical-pixel-recovery-001-implementation-readiness.json"
PUBLICATION_GATE_REF = "records/readiness/m2-optical-pixel-recovery-001-publication-gate.json"
PREFLIGHT_REF = "records/readiness/m2-optical-pixel-recovery-001-final-preflight.json"


class RecoveryGateError(RuntimeError):
    pass


def load(ref: str) -> dict:
    path = ROOT / ref
    if not path.is_file():
        raise RecoveryGateError(f"missing:{ref}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RecoveryGateError(f"invalid:{ref}")
    return value


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def git_identity() -> tuple[str, str]:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    origin = subprocess.run(["git", "rev-parse", "origin/main"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    return head, origin


def validate_recovery_publication() -> None:
    approval = load(APPROVAL_REF)
    activation = load(ACTIVATION_REF)
    retained = load(REAL_001_RECONCILIATION_REF)
    contract = load(CONTRACT_REF)
    readiness = load(READINESS_REF)
    gate = load(PUBLICATION_GATE_REF)
    head, origin = git_identity()
    if head != origin:
        raise RecoveryGateError("head_origin_mismatch")
    if (
        approval.get("status") != "approved_exact_post_observation_operational_correction_and_one_recovery"
        or approval.get("authorized_recovery", {}).get("attempt_id") != "optical-pixel-readiness-recovery-001"
        or approval.get("authorized_recovery", {}).get("maximum_real_invocations") != 1
        or approval.get("authorized_recovery", {}).get("automatic_retry_authorized") is not False
    ):
        raise RecoveryGateError("approval_differs")
    if activation.get("status") != "pass_exact_approval_activated_implementation_and_publication_only":
        raise RecoveryGateError("activation_differs")
    if retained.get("status") != "invalid_terminal_real_001_no_retry_released":
        raise RecoveryGateError("retained_real_001_differs")
    if contract.get("status") != "active_post_observation_operational_correction_one_attempt":
        raise RecoveryGateError("recovery_contract_differs")
    if readiness.get("status") != "pass_exact_shape_local_and_arcgis_synthetic_ready_public_ci_pending":
        raise RecoveryGateError("implementation_readiness_differs")
    if (
        gate.get("status") != "pass_public_controls_verified_before_optical_pixel_recovery_001"
        or gate.get("github_actions", {}).get("conclusion") != "success"
        or gate.get("github_actions", {}).get("head_sha") != head
        or gate.get("bindings", {}).get("approval_sha256") != sha256(APPROVAL_REF)
        or gate.get("bindings", {}).get("activation_sha256") != sha256(ACTIVATION_REF)
        or gate.get("bindings", {}).get("real_001_reconciliation_sha256") != sha256(REAL_001_RECONCILIATION_REF)
        or gate.get("bindings", {}).get("contract_sha256") != sha256(CONTRACT_REF)
        or gate.get("bindings", {}).get("implementation_readiness_sha256") != sha256(READINESS_REF)
        or gate.get("assertions", {}).get("recovery_attempt_started") is not False
    ):
        raise RecoveryGateError("publication_gate_differs")


def validate_recovery_stage_execution() -> None:
    validate_recovery_publication()
    contract = load(CONTRACT_REF)
    preflight = load(PREFLIGHT_REF)
    if (
        preflight.get("status") != "pass_exact_optical_pixel_recovery_001_inputs_ready_no_pixel_access"
        or preflight.get("bindings", {}).get("publication_gate_sha256") != sha256(PUBLICATION_GATE_REF)
        or preflight.get("bindings", {}).get("contract_sha256") != sha256(CONTRACT_REF)
        or preflight.get("attempt", {}).get("attempt_id") != contract.get("attempt", {}).get("attempt_id")
        or preflight.get("assertions", {}).get("real_product_pixels_examined") is not False
        or preflight.get("assertions", {}).get("recovery_attempt_paths_absent") is not True
        or preflight.get("assertions", {}).get("real_001_preserved_exact") is not True
    ):
        raise RecoveryGateError("final_preflight_differs")
