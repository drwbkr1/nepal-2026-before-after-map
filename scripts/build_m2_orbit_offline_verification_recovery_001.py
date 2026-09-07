#!/usr/bin/env python3
"""Build the approved offline orbit-verification recovery-001 candidate contract."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE_REF = "contracts/m2-orbit-offline-verification.json"
PROPOSAL_REF = "contracts/milestone-002-orbit-offline-verification-recovery-001-proposal.json"
PROPOSAL_SHA256 = "0be64071cfe718ca758155ff0422cfee48af342c8a560528746adc653e6a2fcf"
APPROVAL_REF = "records/source-gates/m2-orbit-offline-verification-recovery-001-approval.json"
APPROVAL_SHA256 = "315812935fe725b5c2928a27abc2b51faf561c423065de6216f975cecbe81f30"
OUTPUT_REF = "contracts/m2-orbit-offline-verification-recovery-001.json"
SOURCE_IDS = ["M2-ORB-001", "M2-ORB-002", "M2-ORB-003", "M2-ORB-004"]
OUTPUT_REFS = {
    "M2-ORB-001": "records/acquisition/orbit-verification/m2-orb-001-offline-verification-recovery-001.json",
    "M2-ORB-002": "records/acquisition/orbit-verification/m2-orb-002-offline-verification-001.json",
    "M2-ORB-003": "records/acquisition/orbit-verification/m2-orb-003-offline-verification-001.json",
    "M2-ORB-004": "records/acquisition/orbit-verification/m2-orb-004-offline-verification-001.json",
}


def load(ref: str) -> dict[str, Any]:
    value = json.loads((ROOT / ref).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {ref}")
    return value


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def build(created_at_utc: str) -> dict[str, Any]:
    if sha256(PROPOSAL_REF) != PROPOSAL_SHA256 or sha256(APPROVAL_REF) != APPROVAL_SHA256:
        raise ValueError("proposal or approval identity drift")
    base = load(BASE_REF)
    proposal = load(PROPOSAL_REF)
    approval = load(APPROVAL_REF)
    recovery = approval.get("authorized_recovery", {})
    requirements = copy.deepcopy(base.get("asset_requirements", []))
    if (
        base.get("status") != "terminal_indeterminate_m2_orb_001_receipt_persistence_failure"
        or [item.get("source_id") for item in requirements] != SOURCE_IDS
        or any(item.get("maximum_osv_endpoint_tolerance_seconds") != 1.0 for item in requirements)
        or proposal.get("proposed_recovery") != recovery
        or recovery.get("source_ids_in_exact_order") != SOURCE_IDS
        or recovery.get("m2_orb_001_new_recovery_attempts") != 1
        or recovery.get("remaining_source_existing_attempts_per_source") != 1
        or recovery.get("automatic_retry_authorized") is not False
        or recovery.get("stop_on_first_failure") is not True
        or recovery.get("network_requests_authorized") != 0
        or recovery.get("external_custody_mutation_authorized") is not False
    ):
        raise ValueError("approved recovery or base verification contract differs")
    return {
        "schema_version": "1.0",
        "contract_id": "NEPAL-M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001",
        "status": "candidate_public_ci_pending",
        "created_at_utc": created_at_utc,
        "authority": {
            "approval_ref": APPROVAL_REF,
            "approval_sha256": APPROVAL_SHA256,
            "proposal_ref": PROPOSAL_REF,
            "proposal_sha256": PROPOSAL_SHA256,
            "orbit_input_verification_authorized": True,
            "network_requests_authorized": 0,
            "credential_handoffs_authorized": 0,
            "external_custody_mutation_authorized": False,
            "automatic_retry_authorized": False,
            "second_recovery_authorized": False,
            "orbit_application_authorized": False,
            "radar_pixel_or_dem_action_authorized": False,
        },
        "bindings": {
            "base_active_verification_ref": BASE_REF,
            "base_active_verification_sha256": sha256(BASE_REF),
            "active_intake_ref": "contracts/m2-orbit-intake.json",
            "active_intake_sha256": sha256("contracts/m2-orbit-intake.json"),
            "terminal_reconciliation_ref": "records/readiness/m2-orbit-offline-verification-001-terminal-reconciliation.json",
            "terminal_reconciliation_sha256": sha256("records/readiness/m2-orbit-offline-verification-001-terminal-reconciliation.json"),
        },
        "source_ids_in_exact_order": SOURCE_IDS,
        "output_refs": OUTPUT_REFS,
        "attempt_policy": {
            "m2_orb_001_attempt_identity": "m2-orb-001-offline-verification-recovery-001",
            "m2_orb_001_new_recovery_attempts": 1,
            "remaining_source_attempt_identity": "offline-verification-001",
            "remaining_source_existing_attempts_per_source": 1,
            "stop_on_first_failure": True,
            "automatic_retry_authorized": False,
            "preserve_empty_or_partial_reservation": True,
            "reuse_reserved_path_authorized": False,
        },
        "persistence_order": [
            "validate controls, exact output path, custody root, and source path without reading EOF content",
            "require the exact tracked output parent to be a real non-link directory inside the repository",
            "open the exact receipt path with exclusive creation and fsync the empty reservation",
            "only after reservation, inventory and inspect the EOF content",
            "write the complete receipt through the reserved handle, flush, and fsync",
            "preserve every empty or partial reservation as terminal interruption evidence and refuse reuse",
        ],
        "asset_requirements": requirements,
        "frozen_rules": {
            "source_identity_checksum_xml_osv_units_scene_binding_unchanged": True,
            "maximum_osv_endpoint_tolerance_seconds": 1.0,
            "precise_orbit_substitution_authorized": False,
        },
        "activation_boundary": {
            "public_default_branch_ci_required": True,
            "final_no_content_preflight_required": True,
            "real_eof_reads_before_activation_authorized": False,
            "output_parent_creation_authorized": True,
            "network_requests_authorized": False,
            "external_custody_mutation_authorized": False,
        },
        "claim_boundary": copy.deepcopy(base.get("claim_boundary", {})),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--created-at-utc", required=True)
    args = parser.parse_args()
    if not args.created_at_utc.endswith("Z"):
        raise SystemExit("created time must be UTC")
    path = ROOT / OUTPUT_REF
    if path.exists():
        raise SystemExit("refusing candidate contract output collision")
    payload = canonical(build(args.created_at_utc))
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"status": "candidate_public_ci_pending", "output": OUTPUT_REF, "sha256": hashlib.sha256(payload).hexdigest()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
