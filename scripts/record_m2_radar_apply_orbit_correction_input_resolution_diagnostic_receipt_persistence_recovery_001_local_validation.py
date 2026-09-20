#!/usr/bin/env python3
"""Record local packet validation while preserving the unreconciled terminal block."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-apply-orbit-correction-input-resolution-diagnostic-receipt-persistence-recovery-001"
SOURCE_PREFIX = "m2-radar-apply-orbit-correction-input-resolution-diagnostic-001"
READINESS_REF = f"records/readiness/{PREFIX}-review-readiness.json"
VALIDATION_REF = f"records/readiness/{PREFIX}-local-validation.json"
PROPOSAL_REF = f"contracts/milestone-002-{PREFIX.removeprefix('m2-')}-proposal.json"
BUNDLE_REF = f"reviews/{PREFIX}/review-bundle.json"
CONTRACT_REF = f"reviews/{PREFIX}/review-contract.json"
BLANK_REF = f"reviews/{PREFIX}/blank-response.json"
FAILURE_REF = f"records/readiness/{SOURCE_PREFIX}-terminal-receipt-persistence-failure-observation.json"
TERMINAL_REF = f"records/processing/{SOURCE_PREFIX}-terminal.json"
CLEANUP_REF = f"records/processing/{SOURCE_PREFIX}-cleanup.json"
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
EXPECTED_FAILURES = [
    "test_m2_checkpoint_reconciliation.M2CheckpointReconciliationTests.test_candidate_output_is_scratch_only_and_no_replace",
    "test_m2_checkpoint_reconciliation.M2CheckpointReconciliationTests.test_current_repository_checkpoint_is_reconciled_read_only",
]


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def load(ref: str) -> dict[str, Any]:
    value = json.loads((ROOT / ref).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {ref}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recorded-at-utc", required=True)
    parser.add_argument("--focused-test-count", type=int, required=True)
    parser.add_argument("--full-test-count", type=int, required=True)
    parser.add_argument("--full-failure-count", type=int, required=True)
    parser.add_argument("--full-skip-count", type=int, required=True)
    args = parser.parse_args()
    if not args.recorded_at_utc.endswith("Z") or (ROOT / VALIDATION_REF).exists():
        raise SystemExit("invalid timestamp or validation output collision")
    if (
        args.focused_test_count != 7
        or args.full_test_count != 652
        or args.full_failure_count != 2
        or args.full_skip_count != 6
    ):
        raise SystemExit("observed test counts differ")
    readiness = load(READINESS_REF)
    proposal = load(PROPOSAL_REF)
    bundle = load(BUNDLE_REF)
    contract = load(CONTRACT_REF)
    blank = load(BLANK_REF)
    failure = load(FAILURE_REF)
    if (
        readiness.get("status") != "pass_local_zero_decision_packet_ready_publication_authority_required"
        or proposal.get("human_decision_count") != 0
        or bundle.get("human_decision_count") != 0
        or contract.get("workflow_authority", {}).get("review_response_open") is not False
        or blank.get("completed") is not False
        or failure.get("status") != "terminal_process_consumed_reserved_receipts_empty_result_indeterminate"
        or sha256(TERMINAL_REF) != EMPTY_SHA256
        or sha256(CLEANUP_REF) != EMPTY_SHA256
        or (ROOT / TERMINAL_REF).stat().st_size != 0
        or (ROOT / CLEANUP_REF).stat().st_size != 0
    ):
        raise SystemExit("packet or preserved terminal evidence differs")

    record = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-LOCAL-VALIDATION",
        "recorded_at_utc": args.recorded_at_utc,
        "status": "pass_packet_specific_validation_repository_reconciliation_block_retained",
        "bindings": {
            "proposal_ref": PROPOSAL_REF,
            "proposal_sha256": sha256(PROPOSAL_REF),
            "review_bundle_ref": BUNDLE_REF,
            "review_bundle_sha256": sha256(BUNDLE_REF),
            "review_contract_ref": CONTRACT_REF,
            "review_contract_sha256": sha256(CONTRACT_REF),
            "blank_response_ref": BLANK_REF,
            "blank_response_sha256": sha256(BLANK_REF),
            "review_readiness_ref": READINESS_REF,
            "review_readiness_sha256": sha256(READINESS_REF),
            "failure_observation_ref": FAILURE_REF,
            "failure_observation_sha256": sha256(FAILURE_REF),
            "reserved_terminal_sha256": EMPTY_SHA256,
            "reserved_cleanup_sha256": EMPTY_SHA256,
        },
        "validation": {
            "packet_specific_tests": {
                "tests_run": args.focused_test_count,
                "failures": 0,
                "errors": 0,
                "result": "pass",
            },
            "full_portable_suite": {
                "tests_run": args.full_test_count,
                "intentional_skips": args.full_skip_count,
                "failures": args.full_failure_count,
                "errors": 0,
                "result": "expected_reconciliation_block",
                "failure_tests": EXPECTED_FAILURES,
            },
            "repository_checker": {
                "result": "expected_reconciliation_block",
                "message": "project profile DEM parallel checkpoint differs",
            },
            "packet_json_and_hash_bindings_valid": True,
            "rendered_surface_visually_inspected": True,
            "reserved_receipts_preserved_zero_byte": True,
            "canonical_checkpoint_intentionally_unchanged": True,
            "public_ci_readiness_established": False,
        },
        "interpretation": {
            "packet_specific_validation_passed": True,
            "repository_wide_validation_passed": False,
            "block_is_the_preserved_unreconciled_consumed_diagnostic_state": True,
            "control_plane_reconciliation_performed": False,
            "checker_or_checkpoint_logic_modified": False,
            "publication_integration_authorized": False,
        },
        "assertions": {
            "git_staging_performed": False,
            "git_commit_created": False,
            "git_push_performed": False,
            "public_ci_started": False,
            "arcpy_invoked": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "new_diagnostic_process_started": False,
            "consumed_attempt_retried_or_reused": False,
            "reserved_receipt_mutated": False,
            "scientific_result_established": False,
        },
        "next_action": (
            "Obtain explicit owner authorization for bounded repository-control integration, publication of the exact "
            "zero-decision packet, public default-branch CI, and exact post-CI reconciliation. Keep the owner proposal "
            "response closed and perform no ArcPy, data-access, retry, reconstruction, processing, or scientific action."
        ),
    }
    path = ROOT / VALIDATION_REF
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(
        json.dumps(
            {
                "status": record["status"],
                "validation_sha256": sha256(VALIDATION_REF),
                "packet_specific_tests": args.focused_test_count,
                "full_suite_tests": args.full_test_count,
                "retained_failures": args.full_failure_count,
                "next_gate": "explicit publication and public-CI authorization",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
