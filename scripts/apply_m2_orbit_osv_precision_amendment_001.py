#!/usr/bin/env python3
"""Run the single approved local validation and conditional M2-ORB-001 promotion."""

from __future__ import annotations

import argparse
import json
import os
import traceback

from m2_orbit_osv_precision_amendment_001_core import (
    ATTEMPT_ID,
    CONTRACT_REF,
    DESTINATION_PATH,
    EXTERNAL_RECEIPT_PATH,
    FINAL_PREFLIGHT_REF,
    PROMOTION_TEMP_PATH,
    PUBLICATION_GATE_REF,
    RESULT_REF,
    ROOT,
    SOURCE_ID,
    STAGING_PATH,
    atomic_no_replace_promote,
    load_object,
    require_exact_contract,
    require_path_under_data_root,
    sha256_file,
    write_new_json,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executed-at-utc", required=True)
    args = parser.parse_args()
    if not args.executed_at_utc.endswith("Z"):
        raise SystemExit("execution time must be UTC")
    result_path = ROOT / RESULT_REF
    if result_path.exists():
        raise SystemExit("refusing local-validation result collision; retry is not authorized")
    for path in (STAGING_PATH, DESTINATION_PATH, PROMOTION_TEMP_PATH, EXTERNAL_RECEIPT_PATH):
        require_path_under_data_root(path)
    preflight_path = ROOT / FINAL_PREFLIGHT_REF
    gate_path = ROOT / PUBLICATION_GATE_REF
    contract_path = ROOT / CONTRACT_REF
    preflight = load_object(preflight_path)
    gate = load_object(gate_path)
    contract = load_object(contract_path)
    requirement = require_exact_contract(contract)
    if (
        preflight.get("status") != "pass_no_network_ready_for_one_local_validation"
        or preflight.get("attempt_id") != ATTEMPT_ID
        or preflight.get("bindings", {}).get("amended_contract_sha256") != sha256_file(contract_path)
        or preflight.get("bindings", {}).get("publication_gate_sha256") != sha256_file(gate_path)
        or preflight.get("path_and_storage", {}).get("destination_absent") is not True
        or gate.get("status") != "pass_public_one_second_implementation_before_local_validation"
    ):
        raise SystemExit("final preflight or publication gate drift")
    payload: dict[str, object]
    try:
        promoted = atomic_no_replace_promote(STAGING_PATH, DESTINATION_PATH, PROMOTION_TEMP_PATH, requirement)
        external_receipt = {
            "schema_version": "1.0",
            "receipt_id": "NEPAL-M2-ORBIT-OSV-PRECISION-AMENDMENT-001-EXTERNAL-PROMOTION-001",
            "executed_at_utc": args.executed_at_utc,
            "status": "pass_exact_bytes_promoted_no_replace_staging_preserved",
            "source_id": SOURCE_ID,
            "attempt_id": ATTEMPT_ID,
            "staging_path": str(STAGING_PATH),
            "destination_path": str(DESTINATION_PATH),
            "result": promoted,
            "assertions": {
                "network_requests_performed": False,
                "credential_values_read_or_recorded": False,
                "staging_preserved": True,
                "destination_created_without_replace": True,
                "orbit_application_performed": False,
                "radar_pixels_decoded": False,
            },
        }
        write_new_json(EXTERNAL_RECEIPT_PATH, external_receipt)
        payload = {
            "schema_version": "1.0",
            "receipt_id": "NEPAL-M2-ORBIT-OSV-PRECISION-AMENDMENT-001-LOCAL-VALIDATION-001",
            "executed_at_utc": args.executed_at_utc,
            "status": "pass_exact_m2_orb_001_input_promoted_no_replace",
            "source_id": SOURCE_ID,
            "attempt_id": ATTEMPT_ID,
            "bindings": {
                "final_preflight_sha256": sha256_file(preflight_path),
                "publication_gate_sha256": sha256_file(gate_path),
                "amended_contract_sha256": sha256_file(contract_path),
                "external_receipt_path": str(EXTERNAL_RECEIPT_PATH),
                "external_receipt_sha256": sha256_file(EXTERNAL_RECEIPT_PATH),
            },
            "result": promoted,
            "assertions": {
                "local_validation_attempt_count": 1,
                "automatic_retry_performed": False,
                "network_requests_performed": False,
                "credential_values_read_or_recorded": False,
                "preserved_staging_file_mutated": False,
                "destination_created_without_replace": True,
                "other_orbit_source_requested": False,
                "orbit_application_performed": False,
                "dem_or_radar_pixels_processed": False,
                "baseline_or_change_analysis_performed": False,
                "scientific_result_established": False,
            },
            "next_gate": "reconcile the single local result into active intake and milestone controls without requesting another orbit source",
        }
        return_code = 0
    except Exception as exc:  # terminal evidence must survive any one-attempt failure
        code = getattr(exc, "code", type(exc).__name__)
        payload = {
            "schema_version": "1.0",
            "receipt_id": "NEPAL-M2-ORBIT-OSV-PRECISION-AMENDMENT-001-LOCAL-VALIDATION-001",
            "executed_at_utc": args.executed_at_utc,
            "status": "terminal_local_validation_failure_no_retry",
            "source_id": SOURCE_ID,
            "attempt_id": ATTEMPT_ID,
            "failure_code": str(code),
            "failure_type": type(exc).__name__,
            "traceback_sha256": __import__("hashlib").sha256(traceback.format_exc().encode("utf-8")).hexdigest(),
            "observations": {
                "staging_exists": STAGING_PATH.exists(),
                "destination_exists": DESTINATION_PATH.exists(),
                "promotion_temporary_exists": PROMOTION_TEMP_PATH.exists(),
                "external_receipt_exists": EXTERNAL_RECEIPT_PATH.exists(),
            },
            "assertions": {
                "local_validation_attempt_count": 1,
                "automatic_retry_authorized": False,
                "network_requests_performed": False,
                "credential_values_read_or_recorded": False,
                "other_orbit_source_requested": False,
            },
            "next_gate": "preserve this terminal result; any remediation requires another explicit review",
        }
        return_code = 1
    write_new_json(result_path, payload)
    print(json.dumps({"status": payload["status"], "output": RESULT_REF}, indent=2))
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
