#!/usr/bin/env python3
"""Run the final no-network preflight for the approved local OSV validation."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess

from m2_orbit_osv_precision_amendment_001_core import (
    ACTIVE_INTAKE_REF,
    APPROVAL_REF,
    ATTEMPT_ID,
    CONTRACT_REF,
    DESTINATION_PATH,
    EXPECTED_SHA256,
    EXTERNAL_RECEIPT_PATH,
    FINAL_PREFLIGHT_REF,
    PROMOTION_TEMP_PATH,
    PUBLICATION_GATE_REF,
    RESULT_REF,
    ROOT,
    SOURCE_ID,
    STAGING_PATH,
    exact_file_identity,
    load_object,
    require_exact_contract,
    require_path_under_data_root,
    sha256_file,
    write_new_json,
)
from record_m2_orbit_osv_precision_amendment_001_publication_gate import FILES


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verified-at-utc", required=True)
    args = parser.parse_args()
    if not args.verified_at_utc.endswith("Z"):
        raise SystemExit("verified time must be UTC")
    output = ROOT / FINAL_PREFLIGHT_REF
    if output.exists():
        raise SystemExit("refusing final-preflight output collision")
    approval = load_object(ROOT / APPROVAL_REF)
    contract = load_object(ROOT / CONTRACT_REF)
    requirement = require_exact_contract(contract)
    gate_path = ROOT / PUBLICATION_GATE_REF
    gate = load_object(gate_path)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    origin = subprocess.run(["git", "rev-parse", "origin/main"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    if (
        approval.get("status") != "approved_exact_one_second_endpoint_rule_and_one_local_validation"
        or approval.get("authorized_amendment", {}).get("maximum_new_download_requests") != 0
        or approval.get("authorized_amendment", {}).get("maximum_local_validation_attempts") != 1
        or requirement.get("maximum_osv_endpoint_tolerance_seconds") != 1.0
        or head != origin
        or gate.get("status") != "pass_public_one_second_implementation_before_local_validation"
        or gate.get("github_actions", {}).get("head_sha") != head
        or gate.get("github_actions", {}).get("conclusion") != "success"
        or gate.get("bindings") != {key: sha256_file(path) for key, path in FILES.items()}
    ):
        raise SystemExit("approval, contract, or public-CI gate drift")
    intake = load_object(ROOT / ACTIVE_INTAKE_REF)
    assets = [item for item in intake.get("assets", []) if item.get("extensions", {}).get("source_id") == SOURCE_ID]
    if (
        len(assets) != 1
        or assets[0].get("state") != "failed"
        or assets[0].get("failure", {}).get("code") != "osv_times_do_not_span_validity"
        or not any(item.get("attempt_id") == "m2-orb-001-recovery-002-20260906t183804z-e5883324" and item.get("outcome") == "failed" for item in assets[0].get("attempts", []))
    ):
        raise SystemExit("active intake no longer preserves the exact terminal recovery state")
    for path in (STAGING_PATH, DESTINATION_PATH, PROMOTION_TEMP_PATH, EXTERNAL_RECEIPT_PATH):
        require_path_under_data_root(path)
    if (
        DESTINATION_PATH.exists()
        or PROMOTION_TEMP_PATH.exists()
        or EXTERNAL_RECEIPT_PATH.exists()
        or (ROOT / RESULT_REF).exists()
        or not DESTINATION_PATH.parent.is_dir()
    ):
        raise SystemExit("destination, temporary, receipt, result, or parent preflight failed")
    staged_identity = exact_file_identity(STAGING_PATH)
    if staged_identity["sha256"] != EXPECTED_SHA256:
        raise SystemExit("preserved staged identity drift")
    free_bytes = shutil.disk_usage(DESTINATION_PATH.parent).free
    minimum_free_bytes = staged_identity["size_bytes"] * 10
    if free_bytes < minimum_free_bytes:
        raise SystemExit("insufficient promotion storage")
    payload = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-OSV-PRECISION-AMENDMENT-001-FINAL-PREFLIGHT-001",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_no_network_ready_for_one_local_validation",
        "source_id": SOURCE_ID,
        "attempt_id": ATTEMPT_ID,
        "bindings": {
            "approval_sha256": sha256_file(ROOT / APPROVAL_REF),
            "amended_contract_sha256": sha256_file(ROOT / CONTRACT_REF),
            "publication_gate_sha256": sha256_file(gate_path),
            "active_intake_sha256": sha256_file(ROOT / ACTIVE_INTAKE_REF),
            "public_commit": head,
            "preserved_staged_identity": staged_identity,
        },
        "path_and_storage": {
            "staging_path": str(STAGING_PATH),
            "destination_path": str(DESTINATION_PATH),
            "destination_absent": True,
            "promotion_temporary_path_absent": True,
            "external_receipt_absent": True,
            "public_result_absent": True,
            "free_bytes": free_bytes,
            "minimum_free_bytes": minimum_free_bytes,
        },
        "assertions": {
            "network_requests_performed": False,
            "authentication_performed": False,
            "credential_presence_checked": False,
            "credential_values_read_or_recorded": False,
            "orbit_payload_requested": False,
            "preserved_staged_bytes_mutated": False,
            "local_semantic_validation_started": False,
            "staged_file_promoted": False,
            "other_orbit_source_requested": False,
        },
        "next_gate": "invoke the one local M2-ORB-001 validation and conditional no-replace promotion exactly once",
    }
    write_new_json(output, payload)
    print(json.dumps({"status": payload["status"], "output": FINAL_PREFLIGHT_REF}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
