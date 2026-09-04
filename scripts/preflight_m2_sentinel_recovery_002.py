#!/usr/bin/env python3
"""Run the final deterministic no-payload preflight for recovery-002."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path, PurePosixPath

from m2_sentinel_recovery_002_core import (
    APPROVAL_REF,
    CONTRACT_REF,
    DATA_ROOT,
    EXPECTED_APPROVAL_SHA256,
    EXPECTED_INTAKE_ID,
    FINAL_PREFLIGHT_REF,
    PUBLICATION_GATE_REF,
    ROOT,
    load_object,
    require_exact_contract,
    require_fresh_authorized_attempt,
    sha256_file,
    validate_approval,
    verify_both_retained_partials,
    write_new_json,
)
from record_m2_sentinel_recovery_002_publication_gate import FILES as PUBLICATION_FILES


def git_identity() -> tuple[str, str]:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    origin = subprocess.run(["git", "rev-parse", "origin/main"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    return head, origin


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verified-at-utc", required=True)
    args = parser.parse_args()
    output = ROOT / FINAL_PREFLIGHT_REF
    if output.exists():
        raise SystemExit("refusing final-preflight output collision")
    contract_path = ROOT / CONTRACT_REF
    contract = load_object(contract_path)
    asset = require_exact_contract(contract)
    require_fresh_authorized_attempt(asset)
    approval = load_object(ROOT / APPROVAL_REF)
    reconciliation = load_object(ROOT / "records/source-gates/m2-sentinel-recovery-002-review-reconciliation.json")
    validate_approval(approval, reconciliation)
    if sha256_file(ROOT / APPROVAL_REF) != EXPECTED_APPROVAL_SHA256:
        raise SystemExit("approval hash drift")
    gate_path = ROOT / PUBLICATION_GATE_REF
    gate = load_object(gate_path)
    head, origin = git_identity()
    if (
        gate.get("status") != "pass_public_controls_verified_before_recovery_002"
        or gate.get("github_actions", {}).get("conclusion") != "success"
        or gate.get("github_actions", {}).get("head_sha") != head
        or head != origin
        or gate.get("bindings") != {key: sha256_file(path) for key, path in PUBLICATION_FILES.items()}
    ):
        raise SystemExit("public-CI gate drift")

    active_intake = load_object(ROOT / "contracts/m2-intake.json")
    recovery_001 = load_object(ROOT / "contracts/m2-sentinel-recovery.json")
    original_partial, recovery_001_partial = verify_both_retained_partials(active_intake, recovery_001)
    custody_root = (ROOT.parent / Path(*PurePosixPath(contract["custody_root"]).parts)).resolve(strict=True)
    destination = custody_root / Path(*PurePosixPath(asset["destination_relative_path"]).parts)
    staging_root = DATA_ROOT / ".intake-staging" / EXPECTED_INTAKE_ID
    free_gib = shutil.disk_usage(ROOT.parent).free / (1024 ** 3)
    if destination.exists() or staging_root.exists() or free_gib < 60.0:
        raise SystemExit("destination, staging, or storage preflight failed")
    payload = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-SENTINEL-RECOVERY-002-FINAL-PREFLIGHT-001",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_no_payload_ready_for_single_secret_pipe_handoff",
        "bindings": {
            "approval_ref": APPROVAL_REF,
            "approval_sha256": sha256_file(ROOT / APPROVAL_REF),
            "publication_gate_ref": PUBLICATION_GATE_REF,
            "publication_gate_sha256": sha256_file(gate_path),
            "recovery_contract_ref": CONTRACT_REF,
            "recovery_contract_sha256": sha256_file(contract_path),
            "active_intake_sha256": sha256_file(ROOT / "contracts/m2-intake.json"),
            "recovery_001_contract_sha256": sha256_file(ROOT / "contracts/m2-sentinel-recovery.json"),
            "public_commit": head,
        },
        "retained_partials": [
            {"attempt_id": "m1-src-004-20260904t043930z-ac125c11", "size_bytes": original_partial.stat().st_size, "sha256": sha256_file(original_partial)},
            {"attempt_id": "m1-src-004-recovery-001-20260904t201220z-e4388c64", "size_bytes": recovery_001_partial.stat().st_size, "sha256": sha256_file(recovery_001_partial)},
        ],
        "path_and_storage": {
            "destination_absent": True,
            "recovery_002_staging_root_absent": True,
            "free_gib": free_gib,
            "minimum_free_gib": 60.0,
        },
        "assertions": {
            "network_requests_performed": False,
            "authentication_performed": False,
            "credential_presence_checked": False,
            "credential_values_read_or_recorded": False,
            "product_payload_requested": False,
            "product_payload_bytes_received": 0,
            "external_files_mutated": False,
            "automatic_retry_authorized": False,
        },
        "next_gate": "open the broker once, paste the token into the hidden prompt, and allow one detached recovery-002 attempt",
    }
    write_new_json(output, payload)
    print(json.dumps({"status": payload["status"], "output": str(output.relative_to(ROOT)).replace("\\", "/")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
