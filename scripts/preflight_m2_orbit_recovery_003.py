#!/usr/bin/env python3
"""Run the final deterministic no-payload preflight for M2 orbit recovery-003."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path, PurePosixPath

from m2_orbit_recovery_003_core import (
    ACTIVE_INTAKE_REF,
    APPROVAL_REF,
    CONTRACT_REF,
    DATA_ROOT,
    EXPECTED_DESTINATION_RELATIVE,
    EXPECTED_HANDOFF_CLAIM_ROOT,
    EXPECTED_ATTEMPT_EVENT_ROOT,
    EXPECTED_SIZE_BYTES,
    EXPECTED_STAGING_ROOT,
    EXPECTED_SUPERVISOR_ROOT,
    FINAL_PREFLIGHT_REF,
    PUBLICATION_GATE_REF,
    RADAR_READINESS_REF,
    ROOT,
    load_object,
    require_exact_contract,
    require_original_failure,
    sha256_file,
    validate_approval,
    write_new_json,
)
from record_m2_orbit_recovery_003_publication_gate import FILES


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
    validate_approval()
    contract_path = ROOT / CONTRACT_REF
    contract = load_object(contract_path)
    require_exact_contract(contract)
    intake_path = ROOT / ACTIVE_INTAKE_REF
    intake = load_object(intake_path)
    require_original_failure(intake)
    gate_path = ROOT / PUBLICATION_GATE_REF
    gate = load_object(gate_path)
    head, origin = git_identity()
    if (
        head != origin
        or gate.get("status") != "pass_public_controls_verified_before_orbit_recovery_003"
        or gate.get("github_actions", {}).get("conclusion") != "success"
        or gate.get("github_actions", {}).get("head_sha") != head
        or gate.get("bindings") != {key: sha256_file(path) for key, path in FILES.items()}
    ):
        raise SystemExit("public-CI gate drift")
    radar = load_object(ROOT / RADAR_READINESS_REF)
    if (
        radar.get("status") != "pass_six_source_custody_materialization_and_header_readiness_only"
        or radar.get("assertions", {}).get("measurement_pixels_decoded") is not False
    ):
        raise SystemExit("radar source readiness drift")
    custody_root = (ROOT.parent / Path(*PurePosixPath(intake["custody_root"]).parts)).resolve(strict=True)
    destination = custody_root / Path(*PurePosixPath(EXPECTED_DESTINATION_RELATIVE).parts)
    staging_root = (ROOT.parent / Path(*PurePosixPath(EXPECTED_STAGING_ROOT).parts)).resolve(strict=False)
    attempt_event_root = (ROOT.parent / Path(*PurePosixPath(EXPECTED_ATTEMPT_EVENT_ROOT).parts)).resolve(strict=False)
    supervisor_root = (ROOT.parent / Path(*PurePosixPath(EXPECTED_SUPERVISOR_ROOT).parts)).resolve(strict=False)
    handoff_claim_root = (ROOT.parent / Path(*PurePosixPath(EXPECTED_HANDOFF_CLAIM_ROOT).parts)).resolve(strict=False)
    free_bytes = shutil.disk_usage(ROOT.parent).free
    minimum_free_bytes = EXPECTED_SIZE_BYTES * 10
    if destination.exists() or staging_root.exists() or attempt_event_root.exists() or supervisor_root.exists() or handoff_claim_root.exists() or free_bytes < minimum_free_bytes:
        raise SystemExit("destination, staging, evidence-root, supervisor-root, handoff-root, or storage preflight failed")
    payload = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-RECOVERY-003-FINAL-PREFLIGHT-001",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_no_payload_ready_for_single_secret_pipe_handoff",
        "bindings": {
            "approval_sha256": sha256_file(ROOT / APPROVAL_REF),
            "publication_gate_sha256": sha256_file(gate_path),
            "recovery_contract_sha256": sha256_file(contract_path),
            "active_intake_sha256": sha256_file(intake_path),
            "radar_source_readiness_sha256": sha256_file(ROOT / RADAR_READINESS_REF),
            "public_commit": head,
        },
        "path_and_storage": {
            "destination_absent": True,
            "recovery_staging_root_absent": True,
            "attempt_event_root_absent": True,
            "supervisor_root_absent": True,
            "owner_handoff_claim_root_absent": True,
            "free_bytes": free_bytes,
            "minimum_free_bytes": minimum_free_bytes,
        },
        "assertions": {
            "network_requests_performed": False,
            "authentication_performed": False,
            "credential_presence_checked": False,
            "credential_values_read_or_recorded": False,
            "orbit_payload_requested": False,
            "orbit_payload_bytes_received": 0,
            "external_files_mutated": False,
            "other_orbit_source_requested": False,
            "automatic_retry_authorized": False,
        },
        "next_gate": "run the owner-side token-and-handoff PowerShell once to permit the single detached M2-ORB-001 recovery attempt",
    }
    write_new_json(output, payload)
    print(json.dumps({"status": payload["status"], "output": str(output.relative_to(ROOT)).replace("\\", "/")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
