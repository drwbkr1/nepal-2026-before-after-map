#!/usr/bin/env python3
"""Fixed authority and append-only paths for the offline optical header recovery."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from m2_optical_pair_pilot_001_core import PilotControlError, sha256_file
from m2_optical_pair_pilot_001_transfer import DATA_ROOT, now_utc, read_json, write_new_json


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-optical-pair-header-receipt-recovery-001"
PROPOSAL = ROOT / f"contracts/milestone-002-optical-pair-header-receipt-recovery-001-proposal.json"
BUNDLE = ROOT / f"reviews/{PREFIX}/review-bundle.json"
APPROVAL = ROOT / f"records/source-gates/{PREFIX}-approval.json"
PACKET_GATE = ROOT / f"records/readiness/{PREFIX}-packet-publication-gate.json"
IMPLEMENTATION_READINESS = ROOT / f"records/readiness/{PREFIX}-implementation-readiness.json"
EXECUTION_GATE = ROOT / f"records/readiness/{PREFIX}-execution-gate.json"
FINAL_PREFLIGHT = ROOT / f"records/readiness/{PREFIX}-final-preflight.json"
PUBLIC_TERMINAL = ROOT / f"records/readiness/{PREFIX}-terminal.json"
PILOT_TERMINAL = ROOT / "records/readiness/m2-optical-pair-pilot-001-terminal.json"
PILOT_CONTRACT = ROOT / "contracts/m2-optical-pair-pilot-001-execution.json"
ATTEMPT_ROOT = DATA_ROOT / "derived" / PREFIX / "real-001"
HEADER_RECEIPT = ATTEMPT_ROOT / "header.json"
PIXEL_ROOT = ATTEMPT_ROOT / "pixel-qa-001"
PIXEL_RECEIPT = ATTEMPT_ROOT / "pixel-qa-receipt.json"
SOURCE_IDS = ("M2-OPT-001", "M2-OPT-002")
PROPOSAL_SHA256 = "45b7dc504bf3f92b3dc72db5130596e7465c06f74e3aeb679670e886d0eee2f3"
BUNDLE_SHA256 = "c11ad27a12563b1db4ec0f95b074436c4b8ff4837b74ea9164ed9bae7e909e95"
APPROVAL_SHA256 = "d3558944b22bfe9a1fbe75cb66aca8ea1ec0f5eb91d7496449051668449ac64a"
PACKET_GATE_SHA256 = "77fee0afecb2dfa42ebbbcfefa478c047bffdbc0da28ddc59fbb24503b2b61f1"
PILOT_TERMINAL_SHA256 = "accdd4e2f192c0e527f4d92ea35152d6bb04694e682356c71f3141b316a44cfc"


def fixed_proposal() -> dict[str, Any]:
    if sha256_file(PROPOSAL) != PROPOSAL_SHA256 or sha256_file(BUNDLE) != BUNDLE_SHA256:
        raise PilotControlError("recovery_packet_byte_drift")
    return read_json(PROPOSAL)


def require_packet_release() -> dict[str, Any]:
    proposal = fixed_proposal()
    if sha256_file(APPROVAL) != APPROVAL_SHA256 or sha256_file(PACKET_GATE) != PACKET_GATE_SHA256:
        raise PilotControlError("recovery_authority_byte_drift")
    approval, gate = read_json(APPROVAL), read_json(PACKET_GATE)
    if (
        approval.get("decision") != "approve"
        or approval.get("bindings", {}).get("proposal_sha256") != PROPOSAL_SHA256
        or approval.get("bindings", {}).get("review_bundle_sha256") != BUNDLE_SHA256
        or gate.get("status") != "pass_exact_public_packet_and_approval_ci_implementation_eligible"
        or gate.get("bindings", {}).get("approval_sha256") != APPROVAL_SHA256
        or gate.get("bindings", {}).get("public_ci_conclusion") != "success"
        or sha256_file(PILOT_TERMINAL) != PILOT_TERMINAL_SHA256
        or read_json(PILOT_TERMINAL).get("terminal_code") != "pilot_arcgis_worker_no_header_receipt"
        or proposal.get("requested_single_conditional_envelope", {}).get("maximum_new_real_header_processes") != 1
    ):
        raise PilotControlError("recovery_packet_release_drift")
    return proposal


def validate_implementation_manifest() -> str:
    if not IMPLEMENTATION_READINESS.is_file():
        raise PilotControlError("recovery_implementation_readiness_missing")
    manifest = read_json(IMPLEMENTATION_READINESS)
    if manifest.get("status") != "pass_local_synthetic_public_ci_pending":
        raise PilotControlError("recovery_implementation_not_ready")
    entries = manifest.get("implementation_file_sha256")
    if not isinstance(entries, dict) or not entries:
        raise PilotControlError("recovery_implementation_manifest_invalid")
    for relative, digest in entries.items():
        candidate = ROOT / relative
        try:
            candidate.resolve(strict=True).relative_to(ROOT.resolve(strict=True))
        except (OSError, ValueError) as exc:
            raise PilotControlError("recovery_implementation_manifest_path_unsafe") from exc
        if sha256_file(candidate) != digest:
            raise PilotControlError("recovery_implementation_byte_drift")
    return sha256_file(IMPLEMENTATION_READINESS)


def require_execution_release(*, final_preflight: bool = True) -> dict[str, Any]:
    proposal = require_packet_release()
    implementation_sha = validate_implementation_manifest()
    if not EXECUTION_GATE.is_file():
        raise PilotControlError("recovery_execution_gate_missing")
    gate = read_json(EXECUTION_GATE)
    if (
        gate.get("status") != "pass_public_execution_gate"
        or gate.get("public_ci_conclusion") != "success"
        or gate.get("implementation_readiness_sha256") != implementation_sha
        or gate.get("proposal_sha256") != PROPOSAL_SHA256
        or gate.get("approval_sha256") != APPROVAL_SHA256
    ):
        raise PilotControlError("recovery_execution_gate_drift")
    if final_preflight:
        if not FINAL_PREFLIGHT.is_file():
            raise PilotControlError("recovery_final_preflight_missing")
        receipt = read_json(FINAL_PREFLIGHT)
        if (
            receipt.get("status") != "pass_offline_exact_identity_no_pixel_decode"
            or receipt.get("execution_gate_sha256") != sha256_file(EXECUTION_GATE)
            or receipt.get("proposal_sha256") != PROPOSAL_SHA256
            or receipt.get("old_terminal_sha256") != PILOT_TERMINAL_SHA256
        ):
            raise PilotControlError("recovery_final_preflight_drift")
    return proposal


def exact_sources() -> list[dict[str, Any]]:
    proposal = require_packet_release()
    sources = read_json(PILOT_CONTRACT)["sources_in_order"]
    expected = proposal["exact_existing_inputs"]
    if [item["source_id"] for item in sources] != list(SOURCE_IDS):
        raise PilotControlError("recovery_source_order_drift")
    for source, reviewed in zip(sources, expected, strict=True):
        if (
            source["source_id"] != reviewed["source_id"]
            or source["provider_product_id"] != reviewed["provider_product_id"]
            or source["exact_product_name"] != reviewed["exact_product_name"]
        ):
            raise PilotControlError("recovery_source_identity_drift")
    return sources


def file_identity(path: Path) -> dict[str, Any]:
    return {"size_bytes": path.stat().st_size, "sha256": sha256_file(path)}


def stable_json_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


__all__ = [
    "ROOT", "PREFIX", "PROPOSAL_SHA256", "APPROVAL_SHA256", "PILOT_TERMINAL_SHA256",
    "PILOT_CONTRACT", "ATTEMPT_ROOT", "HEADER_RECEIPT", "PIXEL_ROOT", "PIXEL_RECEIPT",
    "IMPLEMENTATION_READINESS", "EXECUTION_GATE", "FINAL_PREFLIGHT", "PUBLIC_TERMINAL",
    "PilotControlError", "now_utc", "read_json", "write_new_json", "sha256_file",
    "require_packet_release", "validate_implementation_manifest", "require_execution_release",
    "exact_sources", "file_identity", "stable_json_sha256",
]
