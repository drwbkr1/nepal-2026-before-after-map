#!/usr/bin/env python3
"""Activate the approved continuation-001 route after its public-CI gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

from m2_sentinel_continuation_001_core import (
    ACTIVATION_REF,
    ACTIVE_INTAKE_REF,
    APPROVAL_REF,
    BUNDLE_REF,
    CONTINUATION_ID,
    CONTRACT_REF,
    EXPECTED_APPROVAL_SHA256,
    EXPECTED_BUNDLE_SHA256,
    EXPECTED_PROPOSAL_SHA256,
    EXPECTED_RECONCILIATION_SHA256,
    PROPOSAL_REF,
    PUBLICATION_GATE_REF,
    RECONCILIATION_REF,
    RECOVERY_CONTRACT_REF,
    RECOVERY_OUTCOME_REF,
    ROOT,
    SECRET_REFERENCE,
    SOURCE_ORDER,
    canonical_bytes,
    load_object,
    require_exact_contract,
    sha256_file,
    validate_approval_files,
    validate_initial_asset_state,
    validate_initial_paths_absent,
    validate_publication_gate,
    validate_retained_and_recovered_bytes,
)
from record_m2_sentinel_continuation_001_publication_gate import FILES as PUBLICATION_FILES


def git_identity() -> tuple[str, str]:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    origin = subprocess.run(["git", "rev-parse", "origin/main"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    return head, origin


def build_outputs(activated_at_utc: str) -> dict[Path, bytes]:
    validate_approval_files()
    gate_path = ROOT / PUBLICATION_GATE_REF
    gate = load_object(gate_path)
    validate_publication_gate(gate)
    head, origin = git_identity()
    if head != origin or gate.get("github_actions", {}).get("head_sha") != head:
        raise ValueError("publication commit is not current HEAD and origin/main")
    if gate.get("bindings") != {key: sha256_file(path) for key, path in PUBLICATION_FILES.items()}:
        raise ValueError("publication gate implementation bindings drift")

    intake_path = ROOT / ACTIVE_INTAKE_REF
    intake = load_object(intake_path)
    asset_snapshots = validate_initial_asset_state(intake)
    path_observations = validate_initial_paths_absent(intake)
    retained = validate_retained_and_recovered_bytes(intake)
    contract = {
        "contract_version": "1.0",
        "continuation_id": CONTINUATION_ID,
        "created_at_utc": activated_at_utc,
        "status": "active_authorized_final_no_payload_preflight_pending",
        "source_ids_in_exact_order": list(SOURCE_ORDER),
        "recovery_source_ids": [],
        "m1_src_004_request_permitted": False,
        "maximum_real_attempts_per_source": 1,
        "stop_on_first_failure": True,
        "secret_transport": SECRET_REFERENCE,
        "collision_policy": "fail",
        "promotion_mode": "atomic-no-replace",
        "assets": asset_snapshots,
        "bindings": {
            "approval_ref": APPROVAL_REF,
            "approval_sha256": EXPECTED_APPROVAL_SHA256,
            "review_bundle_ref": BUNDLE_REF,
            "review_bundle_sha256": EXPECTED_BUNDLE_SHA256,
            "review_reconciliation_ref": RECONCILIATION_REF,
            "review_reconciliation_sha256": EXPECTED_RECONCILIATION_SHA256,
            "proposal_ref": PROPOSAL_REF,
            "proposal_sha256": EXPECTED_PROPOSAL_SHA256,
            "publication_gate_ref": PUBLICATION_GATE_REF,
            "publication_gate_sha256": sha256_file(gate_path),
            "active_intake_ref": ACTIVE_INTAKE_REF,
            "active_intake_sha256_at_activation": sha256_file(intake_path),
            "recovery_contract_ref": RECOVERY_CONTRACT_REF,
            "recovery_contract_sha256": sha256_file(ROOT / RECOVERY_CONTRACT_REF),
            "recovery_outcome_ref": RECOVERY_OUTCOME_REF,
            "recovery_outcome_sha256": sha256_file(ROOT / RECOVERY_OUTCOME_REF),
            "public_commit": head,
        },
        "prohibited": {
            "m1_src_004_request": True,
            "partial_resume_or_reuse": True,
            "automatic_retry": True,
            "token_storage": True,
            "source_substitution": True,
            "pixel_processing": True,
            "baseline_or_change_analysis": True,
            "attribution_or_scientific_publication": True,
        },
    }
    require_exact_contract(contract)
    contract_bytes = canonical_bytes(contract)
    activation = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-SENTINEL-CONTINUATION-001-ACTIVATION-001",
        "activated_at_utc": activated_at_utc,
        "status": "pass_exact_continuation_001_activated_final_no_payload_preflight_pending",
        "bindings": {
            "approval_ref": APPROVAL_REF,
            "approval_sha256": EXPECTED_APPROVAL_SHA256,
            "publication_gate_ref": PUBLICATION_GATE_REF,
            "publication_gate_sha256": sha256_file(gate_path),
            "continuation_contract_ref": CONTRACT_REF,
            "continuation_contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
            "active_intake_ref": ACTIVE_INTAKE_REF,
            "active_intake_sha256": sha256_file(intake_path),
            "public_commit": head,
        },
        "preflight": {
            "source_ids_in_exact_order": list(SOURCE_ORDER),
            "fresh_authorized_source_count": len(asset_snapshots),
            "path_observations": path_observations,
            "retained_and_recovered_bytes": retained,
            "credential_presence_checked": False,
        },
        "assertions": {
            "network_requests_performed": False,
            "authentication_performed": False,
            "credential_values_read_or_recorded": False,
            "external_files_mutated": False,
            "staging_created": False,
            "product_payload_requested": False,
            "product_payload_bytes_received": 0,
            "m1_src_004_requested": False,
            "automatic_retry_authorized": False,
            "pixel_or_scientific_action_released": False,
        },
        "next_gate": "run the final deterministic no-payload preflight before opening the continuation broker",
    }
    return {ROOT / CONTRACT_REF: contract_bytes, ROOT / ACTIVATION_REF: canonical_bytes(activation)}


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
    print(json.dumps({
        "status": "activated_final_no_payload_preflight_pending",
        "outputs": [str(path.relative_to(ROOT)).replace("\\", "/") for path in outputs],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
