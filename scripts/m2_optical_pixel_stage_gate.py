#!/usr/bin/env python3
"""Validate public-CI and no-pixel preflight gates before the real attempt."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APPROVAL_REF = "records/source-gates/m2-materialization-pixel-readiness-approval.json"
HEADER_RECONCILIATION_REF = "records/readiness/m2-full-header-readiness-reconciliation.json"
CONTRACT_REF = "config/qa/optical-pixel-readiness-contract-001.json"
READINESS_REF = "records/readiness/m2-optical-pixel-implementation-readiness.json"
PUBLICATION_GATE_REF = "records/readiness/m2-optical-pixel-publication-gate.json"
PREFLIGHT_REF = "records/readiness/m2-optical-pixel-final-preflight.json"


class PixelGateError(RuntimeError):
    pass


def load(ref: str) -> dict:
    path = ROOT / ref
    if not path.is_file():
        raise PixelGateError(f"missing:{ref}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PixelGateError(f"invalid:{ref}")
    return value


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def git_identity() -> tuple[str, str]:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    origin = subprocess.run(["git", "rev-parse", "origin/main"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    return head, origin


def validate_pixel_stage_execution() -> None:
    approval = load(APPROVAL_REF)
    header = load(HEADER_RECONCILIATION_REF)
    contract = load(CONTRACT_REF)
    gate = load(PUBLICATION_GATE_REF)
    preflight = load(PREFLIGHT_REF)
    head, origin = git_identity()
    if head != origin:
        raise PixelGateError("head_origin_mismatch")
    if approval.get("status") != "approved_exact_dependency_ordered_bounded_actions":
        raise PixelGateError("approval_differs")
    if header.get("status") != "pass_both_exact_header_routes_only":
        raise PixelGateError("optical_header_prerequisite_differs")
    if contract.get("status") != "active_preobservation_exact_pair_one_attempt":
        raise PixelGateError("pixel_contract_differs")
    if (
        gate.get("status") != "pass_public_controls_verified_before_optical_pixel_attempt"
        or gate.get("github_actions", {}).get("conclusion") != "success"
        or gate.get("github_actions", {}).get("head_sha") != head
        or gate.get("bindings", {}).get("approval_sha256") != sha256(APPROVAL_REF)
        or gate.get("bindings", {}).get("header_reconciliation_sha256") != sha256(HEADER_RECONCILIATION_REF)
        or gate.get("bindings", {}).get("contract_sha256") != sha256(CONTRACT_REF)
        or gate.get("bindings", {}).get("implementation_readiness_sha256") != sha256(READINESS_REF)
    ):
        raise PixelGateError("publication_gate_differs")
    if (
        preflight.get("status") != "pass_exact_optical_pixel_inputs_ready_no_pixel_access"
        or preflight.get("bindings", {}).get("publication_gate_sha256") != sha256(PUBLICATION_GATE_REF)
        or preflight.get("assertions", {}).get("real_product_pixels_examined") is not False
        or preflight.get("assertions", {}).get("attempt_paths_absent") is not True
    ):
        raise PixelGateError("final_preflight_differs")
