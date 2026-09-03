#!/usr/bin/env python3
"""Activate the offline product-verification contract under approved M2 authority."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_REF = "contracts/m2-offline-verification.json"


def load(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def write_new(relative: str, value: dict[str, Any]) -> None:
    path = ROOT / relative
    with path.open("xb") as handle:
        handle.write((json.dumps(value, indent=2) + "\n").encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())


def build_active_contract(activated_at_utc: str) -> dict[str, Any]:
    candidate = load("contracts/m2-offline-verification-candidate.json")
    milestone = load("contracts/milestone-002.json")
    intake = load("contracts/m2-intake.json")
    approval = load("records/source-gates/m2-activation-approval.json")
    source_gate = load("records/source-gates/m2-live-source-gate.json")
    custody = load("records/acquisition/custody-initialization.json")
    if milestone.get("status") != "active" or approval.get("status") != "approved":
        raise SystemExit("M2 authority is not active")
    if source_gate.get("decision", {}).get("status") != "ready":
        raise SystemExit("M2 live source gate is not ready")
    if intake.get("extensions", {}).get("custody_initialized") is not True:
        raise SystemExit("M2 custody is not initialized")
    if custody.get("status") != "created_and_verified":
        raise SystemExit("M2 custody receipt is not passing")

    active = copy.deepcopy(candidate)
    active.update({
        "verification_id": "NEPAL-M2-OFFLINE-VERIFICATION-ACTIVE-001",
        "created_at": activated_at_utc,
        "status": "active_authorized_offline_verification",
        "inputs": {
            "candidate_contract_ref": "contracts/m2-offline-verification-candidate.json",
            "candidate_contract_sha256": sha256("contracts/m2-offline-verification-candidate.json"),
            "acquisition_plan_ref": "records/acquisition-plan.json",
            "acquisition_plan_sha256": sha256("records/acquisition-plan.json"),
            "active_milestone_ref": "contracts/milestone-002.json",
            "active_milestone_sha256_at_activation": sha256("contracts/milestone-002.json"),
            "activation_approval_ref": "records/source-gates/m2-activation-approval.json",
            "activation_approval_sha256": sha256("records/source-gates/m2-activation-approval.json"),
            "active_intake_ref": "contracts/m2-intake.json",
            "active_intake_sha256_at_activation": sha256("contracts/m2-intake.json"),
            "source_gate_ref": "records/source-gates/m2-live-source-gate.json",
            "source_gate_sha256": sha256("records/source-gates/m2-live-source-gate.json"),
            "custody_initialization_ref": "records/acquisition/custody-initialization.json",
            "custody_initialization_sha256": sha256("records/acquisition/custody-initialization.json"),
        },
        "authority": {
            "mode": "inherited",
            "authority_ref": "records/source-gates/m2-activation-approval.json",
            "offline_verification_authorized": True,
            "network_access_authorized": False,
            "archive_extraction_authorized": False,
            "source_archive_mutation_authorized": False,
            "pixel_use_authorized_by_this_contract": False,
            "this_contract_creates_authority": False,
        },
    })
    active["execution_boundary"].update({
        "network_requests": "prohibited",
        "archive_extraction": "prohibited",
        "source_archive_mutation": "prohibited",
        "receipt_root": "records/acquisition/container-verification",
        "receipt_output_must_not_exist": True,
        "active_intake_asset_must_be_promoted": True,
        "active_intake_identity_must_match": True,
    })
    active["limitations"] = [
        "A passing receipt establishes exact local archive identity, provider-MD5 agreement, ZIP integrity, SAFE-root identity, and required member presence only.",
        "Provider BLAKE3 remains catalog metadata unless a separately verified local BLAKE3 implementation is introduced and bound.",
        "Member names and CRC do not establish readable rasters, valid pixels, AOI coverage, masks, registration, or scientific fitness.",
        "Each product receipt must bind the current promoted intake identity and may not replace an existing receipt.",
    ]
    active["activation_boundary"] = {
        "activated_at_utc": activated_at_utc,
        "product_count": len(active["assets"]),
        "authentication_performed": False,
        "network_requests_performed": False,
        "custody_access_performed": False,
        "product_bytes_read": 0,
    }
    return active


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activated-at-utc", required=True)
    args = parser.parse_args()
    if (ROOT / OUTPUT_REF).exists():
        raise SystemExit(f"active verification contract already exists; refusing replacement: {OUTPUT_REF}")
    active = build_active_contract(args.activated_at_utc)
    write_new(OUTPUT_REF, active)
    print(json.dumps({
        "status": active["status"],
        "contract": OUTPUT_REF,
        "contract_sha256": sha256(OUTPUT_REF),
        "product_count": len(active["assets"]),
        "network_or_authentication_performed": False,
        "product_bytes_read": 0,
    }, indent=2))


if __name__ == "__main__":
    main()
