#!/usr/bin/env python3
"""Activate the exact M2-ORB-001 recovery-002 contract after successful public CI."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from m2_orbit_recovery_002_core import (
    ACTIVE_INTAKE_REF,
    ACTIVATION_REF,
    APPROVAL_REF,
    APPROVAL_SHA256,
    BUNDLE_REF,
    BUNDLE_SHA256,
    CONTRACT_REF,
    EXPECTED_ATTEMPT_PREFIX,
    EXPECTED_BLAKE3,
    EXPECTED_DESTINATION_RELATIVE,
    EXPECTED_DOWNLOAD_URL,
    EXPECTED_MD5,
    EXPECTED_PRODUCT_NAME,
    EXPECTED_PROVIDER_PRODUCT_ID,
    EXPECTED_SIZE_BYTES,
    EXPECTED_SOURCE_ID,
    EXPECTED_STAGING_RELATIVE,
    EXPECTED_STAGING_ROOT,
    ORIGINAL_ATTEMPT_ID,
    ORIGINAL_RECEIPT_REF,
    ORIGINAL_RECEIPT_SHA256,
    ORIGINAL_RECONCILIATION_REF,
    ORIGINAL_RECONCILIATION_SHA256,
    PROPOSAL_REF,
    PROPOSAL_SHA256,
    PUBLICATION_GATE_REF,
    RECONCILIATION_REF,
    RECONCILIATION_SHA256,
    ROOT,
    SECRET_REFERENCE,
    canonical_bytes,
    load_object,
    require_original_failure,
    sha256_file,
    validate_approval,
)
from record_m2_orbit_recovery_002_publication_gate import FILES


OUTPUT_CONTRACT = ROOT / CONTRACT_REF
OUTPUT_ACTIVATION = ROOT / ACTIVATION_REF


def git_identity() -> tuple[str, str]:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    origin = subprocess.run(["git", "rev-parse", "origin/main"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    return head, origin


def validate_publication_gate(gate: dict[str, Any]) -> str:
    head, origin = git_identity()
    if (
        head != origin
        or gate.get("status") != "pass_public_controls_verified_before_orbit_recovery_002"
        or gate.get("github_actions", {}).get("conclusion") != "success"
        or gate.get("github_actions", {}).get("head_sha") != head
        or gate.get("bindings") != {key: sha256_file(path) for key, path in FILES.items()}
        or gate.get("assertions", {}).get("real_recovery_started") is not False
    ):
        raise ValueError("orbit recovery-002 public-CI gate differs")
    return head


def build_outputs(activated_at_utc: str) -> dict[Path, bytes]:
    validate_approval()
    intake = load_object(ROOT / ACTIVE_INTAKE_REF)
    require_original_failure(intake)
    gate_path = ROOT / PUBLICATION_GATE_REF
    public_commit = validate_publication_gate(load_object(gate_path))
    contract = {
        "contract_version": "1.0",
        "contract_id": "nepal-m2-orbit-recovery-002",
        "created_at": activated_at_utc,
        "status": "active_one_attempt_final_preflight_pending",
        "source_id": EXPECTED_SOURCE_ID,
        "provider_product_id": EXPECTED_PROVIDER_PRODUCT_ID,
        "exact_product_name": EXPECTED_PRODUCT_NAME,
        "download_url": EXPECTED_DOWNLOAD_URL,
        "expected_size_bytes": EXPECTED_SIZE_BYTES,
        "expected_md5": EXPECTED_MD5,
        "expected_blake3": EXPECTED_BLAKE3,
        "staging_root": EXPECTED_STAGING_ROOT,
        "staging_relative_path": EXPECTED_STAGING_RELATIVE,
        "destination_relative_path": EXPECTED_DESTINATION_RELATIVE,
        "attempt_prefix": EXPECTED_ATTEMPT_PREFIX,
        "restart_offset_bytes": 0,
        "resume_partial": False,
        "maximum_real_attempts": 1,
        "automatic_retry_authorized": False,
        "secret_transport": SECRET_REFERENCE,
        "bindings": {
            "approval_ref": APPROVAL_REF,
            "approval_sha256": APPROVAL_SHA256,
            "review_reconciliation_ref": RECONCILIATION_REF,
            "review_reconciliation_sha256": RECONCILIATION_SHA256,
            "proposal_ref": PROPOSAL_REF,
            "proposal_sha256": PROPOSAL_SHA256,
            "review_bundle_ref": BUNDLE_REF,
            "review_bundle_sha256": BUNDLE_SHA256,
            "publication_gate_ref": PUBLICATION_GATE_REF,
            "publication_gate_sha256": sha256_file(gate_path),
            "public_commit": public_commit,
            "active_intake_sha256_at_activation": sha256_file(ROOT / ACTIVE_INTAKE_REF),
            "retained_failed_attempt_id": ORIGINAL_ATTEMPT_ID,
            "retained_failed_receipt_ref": ORIGINAL_RECEIPT_REF,
            "retained_failed_receipt_sha256": ORIGINAL_RECEIPT_SHA256,
            "retained_failure_reconciliation_ref": ORIGINAL_RECONCILIATION_REF,
            "retained_failure_reconciliation_sha256": ORIGINAL_RECONCILIATION_SHA256,
        },
        "does_not_authorize": [
            "M2-ORB-002 through M2-ORB-004 requests",
            "automatic retry or precise-orbit substitution",
            "token storage or exposure",
            "DEM action, orbit application, radar pixel decoding, baseline, change analysis, attribution, or scientific publication",
        ],
    }
    contract_bytes = canonical_bytes(contract)
    activation = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-RECOVERY-002-ACTIVATION-001",
        "activated_at_utc": activated_at_utc,
        "status": "pass_exact_orbit_recovery_002_activated_final_no_payload_preflight_pending",
        "bindings": {
            "approval_sha256": APPROVAL_SHA256,
            "review_reconciliation_sha256": RECONCILIATION_SHA256,
            "publication_gate_sha256": sha256_file(gate_path),
            "recovery_contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
            "active_intake_sha256": sha256_file(ROOT / ACTIVE_INTAKE_REF),
            "public_commit": public_commit,
        },
        "assertions": {
            "network_requests_performed": False,
            "authentication_performed": False,
            "credential_values_read_or_recorded": False,
            "external_data_mutated": False,
            "recovery_staging_created": False,
            "orbit_payload_requested": False,
            "other_orbit_source_requested": False,
            "automatic_retry_authorized": False,
        },
        "next_gate": "run the deterministic final no-payload preflight before owner credential entry",
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
