#!/usr/bin/env python3
"""Frozen pair-002 authority, custody locations, and append-only primitives."""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT.parent / f"{ROOT.name}-data"
PREFIX = "m2-optical-alternate-map-pair-002"
PROPOSAL = ROOT / f"contracts/milestone-002-optical-alternate-map-pair-002-proposal.json"
BUNDLE = ROOT / f"reviews/{PREFIX}/review-bundle.json"
APPROVAL = ROOT / f"records/source-gates/{PREFIX}-approval.json"
EXECUTION_GATE = ROOT / f"records/readiness/{PREFIX}-execution-gate.json"
FINAL_PREFLIGHT = ROOT / f"records/readiness/{PREFIX}-final-preflight.json"
BEFORE_TERMINAL = ROOT / f"records/readiness/{PREFIX}-before-screen-terminal.json"
BEFORE_SOURCE = DATA_ROOT / "derived/m2-optical-pair-pilot-001/materialized/m2-opt-001/materialization-001"
ATTEMPTS_ROOT = DATA_ROOT / "derived" / PREFIX
PROPOSAL_SHA256 = "c38ed063e8eadd44b364e41235e0cc9ba8fb09e620f32e1eb4d96e4a8fde7de0"
BUNDLE_SHA256 = "980df8c0412fd1997ba5d6cc67a5f8b7a3b7cb5b3e62ed6fad96c2bd5f9c3e6d"
APPROVAL_SHA256 = "a85e5c2d4d2bc93f22d700674cb65db74eef0f9085ece18cc53480de00cf1458"
EXPECTED_ATTEMPTS = {
    "before_single_date_screen": "m2-optical-alternate-map-pair-002-before-screen-real-001",
    "new_source_acquisition": "m2-optical-alternate-map-pair-002-m2-opt-003-acquisition-real-001",
    "pair_header_and_pixel_qa": "m2-optical-alternate-map-pair-002-pair-qa-real-001",
    "local_visual_map": "m2-optical-alternate-map-pair-002-local-display-real-001",
}
SAFE_CODE = re.compile(r"[a-z0-9_]{3,96}\Z")
SENSITIVE_KEY = re.compile(r"TOKEN|SECRET|PASSWORD|AUTHORIZATION|CREDENTIAL|API[_-]?KEY|CDSE", re.I)


class PairControlError(RuntimeError):
    def __init__(self, code: str):
        safe = code if SAFE_CODE.fullmatch(code) else "invalid_pair_control_code"
        super().__init__(safe)
        self.code = safe


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PairControlError("pair_record_root_invalid")
    return value


def write_new_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write((json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())


def child_environment(environment: dict[str, str]) -> dict[str, str]:
    return {key: value for key, value in environment.items() if not SENSITIVE_KEY.search(key)}


def require_packet() -> dict[str, Any]:
    if (sha256_file(PROPOSAL) != PROPOSAL_SHA256
            or sha256_file(BUNDLE) != BUNDLE_SHA256
            or sha256_file(APPROVAL) != APPROVAL_SHA256):
        raise PairControlError("pair_packet_byte_drift")
    proposal, approval, bundle = read_json(PROPOSAL), read_json(APPROVAL), read_json(BUNDLE)
    for kind in ("review", "proposal", "method_risk", "source_eligibility",
                 "corrected_metadata_screen"):
        ref, digest = bundle.get(f"{kind}_ref"), bundle.get(f"{kind}_sha256")
        if (not isinstance(ref, str) or not isinstance(digest, str)
                or sha256_file(ROOT / ref) != digest):
            raise PairControlError("pair_review_binding_drift")
    if (approval.get("decision") != "approve" or approval.get("human_decision_count") != 1
            or approval.get("bindings", {}).get("proposal_sha256") != PROPOSAL_SHA256
            or approval.get("bindings", {}).get("review_bundle_sha256") != BUNDLE_SHA256
            or proposal.get("fixed_new_attempt_identities", {}) != {
                **EXPECTED_ATTEMPTS,
                "attempt_root_rule": "Each exact identity must be absent in both public records and intended non-Git custody at final no-content preflight; any collision stops the envelope without substitution."
            }):
        raise PairControlError("pair_packet_authority_or_attempt_drift")
    return proposal


def require_public_ci() -> dict[str, Any]:
    require_packet()
    if not EXECUTION_GATE.is_file():
        raise PairControlError("pair_public_ci_gate_missing")
    gate = read_json(EXECUTION_GATE)
    if (gate.get("status") != "pass_public_default_branch_ci_pair_002_before_screen_gate"
            or gate.get("proposal_sha256") != PROPOSAL_SHA256
            or gate.get("bundle_sha256") != BUNDLE_SHA256
            or gate.get("approval_sha256") != APPROVAL_SHA256
            or gate.get("public_ci_conclusion") != "success"
            or not isinstance(gate.get("public_ci_run_id"), int)
            or not isinstance(gate.get("implementation_commit"), str)):
        raise PairControlError("pair_public_ci_gate_invalid")
    return gate


def attempt_path(kind: str) -> Path:
    if kind not in EXPECTED_ATTEMPTS:
        raise PairControlError("pair_attempt_kind_unapproved")
    return ATTEMPTS_ROOT / EXPECTED_ATTEMPTS[kind]
