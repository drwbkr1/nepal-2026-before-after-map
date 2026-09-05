#!/usr/bin/env python3
"""Validate the publication and final-preflight gate before real headers."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APPROVAL_REF = "records/source-gates/m2-materialization-pixel-readiness-approval.json"
MATERIALIZATION_RECONCILIATION_REF = "records/acquisition/sentinel-materialization-reconciliation-002.json"
READINESS_REF = "records/readiness/m2-header-stage-implementation-readiness.json"
PUBLICATION_GATE_REF = "records/readiness/m2-header-stage-publication-gate.json"
PREFLIGHT_REF = "records/readiness/m2-header-stage-final-preflight.json"


class HeaderGateError(RuntimeError):
    pass


def load(ref: str) -> dict:
    path = ROOT / ref
    if not path.is_file():
        raise HeaderGateError(f"missing:{ref}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise HeaderGateError(f"invalid:{ref}")
    return value


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def git_identity() -> tuple[str, str]:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    origin = subprocess.run(["git", "rev-parse", "origin/main"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    return head, origin


def validate_header_stage_execution() -> None:
    approval = load(APPROVAL_REF)
    reconciliation = load(MATERIALIZATION_RECONCILIATION_REF)
    gate = load(PUBLICATION_GATE_REF)
    preflight = load(PREFLIGHT_REF)
    head, origin = git_identity()
    if head != origin:
        raise HeaderGateError("head_origin_mismatch")
    if approval.get("status") != "approved_exact_dependency_ordered_bounded_actions":
        raise HeaderGateError("approval_differs")
    if reconciliation.get("status") != "pass_all_eight_materialized_identity_only":
        raise HeaderGateError("materialization_reconciliation_differs")
    if (
        gate.get("status") != "pass_public_controls_verified_before_real_header_inspections"
        or gate.get("github_actions", {}).get("conclusion") != "success"
        or gate.get("github_actions", {}).get("head_sha") != head
        or gate.get("bindings", {}).get("approval_sha256") != sha256(APPROVAL_REF)
        or gate.get("bindings", {}).get("materialization_reconciliation_sha256") != sha256(MATERIALIZATION_RECONCILIATION_REF)
        or gate.get("bindings", {}).get("implementation_readiness_sha256") != sha256(READINESS_REF)
    ):
        raise HeaderGateError("publication_gate_differs")
    if (
        preflight.get("status") != "pass_exact_header_inputs_ready_no_real_header_access"
        or preflight.get("bindings", {}).get("publication_gate_sha256") != sha256(PUBLICATION_GATE_REF)
        or preflight.get("assertions", {}).get("real_raster_headers_opened") is not False
        or preflight.get("assertions", {}).get("measurement_pixels_decoded") is not False
        or preflight.get("assertions", {}).get("real_attempt_outputs_absent") is not True
    ):
        raise HeaderGateError("final_preflight_differs")
