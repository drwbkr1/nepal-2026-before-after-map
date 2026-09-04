#!/usr/bin/env python3
"""Activate the exact approved recovery-002 contract after its public-CI gate."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from m2_sentinel_recovery_002_core import (
    APPROVAL_REF,
    BUNDLE_REF,
    CONTRACT_REF,
    DATA_ROOT,
    EXPECTED_APPROVAL_SHA256,
    EXPECTED_ASSET_ID,
    EXPECTED_BUNDLE_SHA256,
    EXPECTED_DESTINATION,
    EXPECTED_INTAKE_ID,
    EXPECTED_PROPOSAL_SHA256,
    EXPECTED_SOURCE_ID,
    EXPECTED_STAGING,
    ORIGINAL_ATTEMPT_ID,
    ORIGINAL_PARTIAL_BYTES,
    ORIGINAL_PARTIAL_SHA256,
    PROJECT_ROOT,
    PROPOSAL_REF,
    PUBLICATION_GATE_REF,
    RECOVERY_001_ATTEMPT_ID,
    RECOVERY_001_PARTIAL_BYTES,
    RECOVERY_001_PARTIAL_SHA256,
    RECONCILIATION_REF,
    ROOT,
    SECRET_REFERENCE,
    canonical_bytes,
    load_object,
    sha256_file,
    validate_approval,
    verify_both_retained_partials,
)
from record_m2_sentinel_recovery_002_publication_gate import FILES as PUBLICATION_FILES


ACTIVE_INTAKE_REF = "contracts/m2-intake.json"
RECOVERY_001_CONTRACT_REF = "contracts/m2-sentinel-recovery.json"
OUTPUT_CONTRACT = ROOT / CONTRACT_REF
OUTPUT_ACTIVATION = ROOT / "records/acquisition/sentinel-recovery-002-activation.json"


def current_git_identity() -> tuple[str, str]:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    origin = subprocess.run(["git", "rev-parse", "origin/main"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    return head, origin


def validate_publication_gate(gate: dict[str, Any]) -> None:
    head, origin = current_git_identity()
    if (
        gate.get("status") != "pass_public_controls_verified_before_recovery_002"
        or gate.get("github_actions", {}).get("conclusion") != "success"
        or gate.get("github_actions", {}).get("head_sha") != head
        or head != origin
        or gate.get("assertions", {}).get("real_recovery_started") is not False
        or gate.get("bindings") != {key: sha256_file(path) for key, path in PUBLICATION_FILES.items()}
    ):
        raise ValueError("recovery-002 public-CI gate differs")


def build_outputs(activated_at_utc: str) -> dict[Path, bytes]:
    if sha256_file(ROOT / BUNDLE_REF) != EXPECTED_BUNDLE_SHA256:
        raise ValueError("recovery-002 review bundle hash drift")
    if sha256_file(ROOT / PROPOSAL_REF) != EXPECTED_PROPOSAL_SHA256:
        raise ValueError("recovery-002 proposal hash drift")
    if sha256_file(ROOT / APPROVAL_REF) != EXPECTED_APPROVAL_SHA256:
        raise ValueError("recovery-002 approval hash drift")
    approval = load_object(ROOT / APPROVAL_REF)
    reconciliation = load_object(ROOT / RECONCILIATION_REF)
    validate_approval(approval, reconciliation)
    gate = load_object(ROOT / PUBLICATION_GATE_REF)
    validate_publication_gate(gate)

    active_intake = load_object(ROOT / ACTIVE_INTAKE_REF)
    recovery_001 = load_object(ROOT / RECOVERY_001_CONTRACT_REF)
    original_partial, recovery_001_partial = verify_both_retained_partials(active_intake, recovery_001)
    originals = [item for item in active_intake["assets"] if item.get("extensions", {}).get("source_id") == EXPECTED_SOURCE_ID]
    if len(originals) != 1:
        raise ValueError("M1-SRC-004 original identity drift")
    original = originals[0]
    destination = DATA_ROOT / "custody" / Path(*Path(original["destination_relative_path"]).parts)
    staging_root = DATA_ROOT / ".intake-staging" / EXPECTED_INTAKE_ID
    if destination.exists() or staging_root.exists():
        raise ValueError("recovery-002 destination or staging collision")

    asset = copy.deepcopy(original)
    asset["asset_id"] = EXPECTED_ASSET_ID
    asset["source"]["authorization_ref"] = APPROVAL_REF
    asset["staging_relative_path"] = EXPECTED_STAGING
    asset["destination_relative_path"] = EXPECTED_DESTINATION
    asset["observed"] = {
        "staged_sha256": None,
        "staged_size_bytes": None,
        "promoted_sha256": None,
        "promoted_size_bytes": None,
    }
    asset["state"] = "authorized"
    asset["attempts"] = []
    asset["failure"] = None
    asset["superseded_by"] = None
    asset["extensions"].update({
        "recovery_of_asset_id": "m1-src-004",
        "secret_transport": SECRET_REFERENCE,
        "retained_failure_count": 2,
        "original_failed_attempt_id": ORIGINAL_ATTEMPT_ID,
        "original_partial_external_path": str(original_partial),
        "original_partial_size_bytes": ORIGINAL_PARTIAL_BYTES,
        "original_partial_sha256": ORIGINAL_PARTIAL_SHA256,
        "recovery_001_failed_attempt_id": RECOVERY_001_ATTEMPT_ID,
        "recovery_001_partial_external_path": str(recovery_001_partial),
        "recovery_001_partial_size_bytes": RECOVERY_001_PARTIAL_BYTES,
        "recovery_001_partial_sha256": RECOVERY_001_PARTIAL_SHA256,
    })
    contract = {
        "contract_version": "1.0",
        "intake_id": EXPECTED_INTAKE_ID,
        "created_at": activated_at_utc,
        "collision_policy": "fail",
        "promotion_mode": "atomic-no-replace",
        "secret_policy": SECRET_REFERENCE,
        "custody_root": "nepal-2026-before-after-map-data/custody",
        "staging_root": f"nepal-2026-before-after-map-data/.intake-staging/{EXPECTED_INTAKE_ID}",
        "assets": [asset],
        "extensions": {
            "status": "active_authorized_one_fresh_attempt_final_no_payload_preflight_pending",
            "recovery_approval_ref": APPROVAL_REF,
            "recovery_approval_sha256": EXPECTED_APPROVAL_SHA256,
            "review_bundle_ref": BUNDLE_REF,
            "review_bundle_sha256": EXPECTED_BUNDLE_SHA256,
            "review_reconciliation_ref": RECONCILIATION_REF,
            "review_reconciliation_sha256": sha256_file(ROOT / RECONCILIATION_REF),
            "recovery_proposal_ref": PROPOSAL_REF,
            "recovery_proposal_sha256": EXPECTED_PROPOSAL_SHA256,
            "publication_gate_ref": PUBLICATION_GATE_REF,
            "publication_gate_sha256": sha256_file(ROOT / PUBLICATION_GATE_REF),
            "active_intake_ref": ACTIVE_INTAKE_REF,
            "active_intake_sha256_at_activation": sha256_file(ROOT / ACTIVE_INTAKE_REF),
            "recovery_001_contract_ref": RECOVERY_001_CONTRACT_REF,
            "recovery_001_contract_sha256_at_activation": sha256_file(ROOT / RECOVERY_001_CONTRACT_REF),
            "restart_offset_bytes": 0,
            "resume_any_partial": False,
            "delete_or_modify_any_partial": False,
            "reuse_any_prior_staging_path": False,
            "maximum_real_transfer_attempts": 1,
            "detached_supervisor_required": True,
            "secret_transport": SECRET_REFERENCE,
        },
    }
    contract_bytes = canonical_bytes(contract)
    activation = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-SENTINEL-RECOVERY-002-ACTIVATION-001",
        "activated_at_utc": activated_at_utc,
        "status": "pass_exact_recovery_002_activated_final_no_payload_preflight_pending",
        "bindings": {
            "approval_ref": APPROVAL_REF,
            "approval_sha256": EXPECTED_APPROVAL_SHA256,
            "publication_gate_ref": PUBLICATION_GATE_REF,
            "publication_gate_sha256": sha256_file(ROOT / PUBLICATION_GATE_REF),
            "recovery_contract_ref": CONTRACT_REF,
            "recovery_contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
            "active_intake_ref": ACTIVE_INTAKE_REF,
            "active_intake_sha256": sha256_file(ROOT / ACTIVE_INTAKE_REF),
            "recovery_001_contract_ref": RECOVERY_001_CONTRACT_REF,
            "recovery_001_contract_sha256": sha256_file(ROOT / RECOVERY_001_CONTRACT_REF),
        },
        "preflight": {
            "retained_partial_count": 2,
            "original_partial_size_bytes": original_partial.stat().st_size,
            "original_partial_sha256": sha256_file(original_partial),
            "recovery_001_partial_size_bytes": recovery_001_partial.stat().st_size,
            "recovery_001_partial_sha256": sha256_file(recovery_001_partial),
            "destination_absent": True,
            "recovery_002_staging_root_absent": True,
            "credential_presence_checked": False,
        },
        "assertions": {
            "network_requests_performed": False,
            "authentication_performed": False,
            "credential_values_read_or_recorded": False,
            "external_custody_mutated": False,
            "recovery_staging_created": False,
            "product_payload_requested": False,
            "product_payload_bytes_received": 0,
            "prior_partial_mutated": False,
            "automatic_retry_authorized": False,
            "pixel_or_scientific_action_released": False,
        },
        "next_gate": "run one deterministic no-payload preflight before opening the secret-entry broker",
    }
    return {OUTPUT_CONTRACT: contract_bytes, OUTPUT_ACTIVATION: canonical_bytes(activation)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activated-at-utc", required=True)
    args = parser.parse_args()
    if not args.activated_at_utc.endswith("Z"):
        raise SystemExit("activated time must be UTC")
    outputs = build_outputs(args.activated_at_utc)
    collisions = [str(path) for path in outputs if path.exists()]
    if collisions:
        raise SystemExit("refusing output collision: " + ", ".join(collisions))
    for path, data in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    print(json.dumps({"status": "activated_final_no_payload_preflight_pending", "outputs": [str(path.relative_to(ROOT)).replace("\\", "/") for path in outputs]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
