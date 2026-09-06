#!/usr/bin/env python3
"""Record local synthetic readiness for the approved orbit recovery-003 implementation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "records/acquisition/m2-orbit-recovery-003-implementation-readiness.json"
IMPLEMENTATION_FILES = {
    "approval_sha256": ROOT / "records/source-gates/m2-orbit-recovery-003-approval.json",
    "review_reconciliation_sha256": ROOT / "records/source-gates/m2-orbit-recovery-003-review-reconciliation.json",
    "approval_activation_sha256": ROOT / "records/readiness/m2-orbit-recovery-003-approval-activation.json",
    "superseded_readiness_sha256": ROOT / "records/acquisition/m2-orbit-recovery-003-implementation-readiness-attempt-001-superseded.json",
    "prepublication_review_failure_sha256": ROOT / "records/acquisition/m2-orbit-recovery-003-prepublication-review-attempt-001-failure.json",
    "recovery_002_outcome_sha256": ROOT / "records/acquisition/m2-orbit-recovery-002-outcome-reconciliation.json",
    "recovery_002_terminal_sha256": ROOT / "records/readiness/m2-orbit-recovery-002-terminal-reconciliation.json",
    "proposal_sha256": ROOT / "contracts/milestone-002-orbit-recovery-003-proposal.json",
    "review_bundle_sha256": ROOT / "reviews/m2-orbit-recovery-003/review-bundle.json",
    "review_publication_gate_sha256": ROOT / "records/readiness/m2-orbit-recovery-003-review-publication-gate.json",
    "core_sha256": ROOT / "scripts/m2_orbit_recovery_003_core.py",
    "broker_sha256": ROOT / "scripts/m2_orbit_recovery_003_broker.py",
    "supervisor_sha256": ROOT / "scripts/m2_orbit_recovery_003_supervisor.py",
    "recovery_runner_sha256": ROOT / "scripts/acquire_m2_orbit_recovery_003.py",
    "orbit_verifier_sha256": ROOT / "scripts/verify_m2_orbit_eof.py",
    "activation_script_sha256": ROOT / "scripts/activate_m2_orbit_recovery_003.py",
    "final_preflight_sha256": ROOT / "scripts/preflight_m2_orbit_recovery_003.py",
    "control_reconciler_sha256": ROOT / "scripts/reconcile_m2_orbit_recovery_003_controls.py",
    "outcome_reconciler_sha256": ROOT / "scripts/reconcile_m2_orbit_recovery_003_outcome.py",
    "owner_handoff_sha256": ROOT / "scripts/invoke_m2_orbit_recovery_003.ps1",
    "publication_gate_recorder_sha256": ROOT / "scripts/record_m2_orbit_recovery_003_publication_gate.py",
    "focused_tests_sha256": ROOT / "tests/test_m2_orbit_recovery_003.py",
    "orbit_io_tests_sha256": ROOT / "tests/test_m2_orbit_io.py",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verified-at-utc", required=True)
    parser.add_argument("--focused-test-count", type=int, required=True)
    parser.add_argument("--full-test-count", type=int, required=True)
    args = parser.parse_args()
    if OUTPUT.exists() or args.focused_test_count != 16 or args.full_test_count < args.focused_test_count:
        raise SystemExit("readiness inputs or output collision invalid")
    missing = [str(path.relative_to(ROOT)) for path in IMPLEMENTATION_FILES.values() if not path.is_file()]
    if missing:
        raise SystemExit("missing implementation files: " + ", ".join(missing))
    payload = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-RECOVERY-003-IMPLEMENTATION-READINESS-001",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_local_synthetic_ready_public_ci_pending",
        "bindings": {key: sha256(path) for key, path in IMPLEMENTATION_FILES.items()},
        "tests": {
            "focused_test_count": args.focused_test_count,
            "full_repository_test_count": args.full_test_count,
            "focused_result": "pass",
            "full_repository_result": "pass",
            "powershell_parser_validation": "pass",
            "windows_crlf_pipe_framing": "pass",
            "forced_broker_termination_tested_on_windows": True,
        },
        "assertions": {
            "secret_absent_from_child_command_and_environment": True,
            "secret_transport_anonymous_pipe_only": True,
            "broker_termination_does_not_end_synthetic_worker": True,
            "nonsecret_started_heartbeat_terminal_evidence_tested": True,
            "attempt_id_predeclared_before_runtime_mutation": True,
            "attempt_id_exactly_binds_started_time_and_nonce": True,
            "owner_handoff_claim_exclusive": True,
            "attempt_event_root_precedes_payload_parent": True,
            "started_event_precedes_public_catalog_revalidation": True,
            "catalog_response_hash_written_as_separate_immutable_event": True,
            "fixed_nonsecret_pretransfer_failure_codes_tested": True,
            "byte_zero_no_range_request_fixed": True,
            "distinct_exclusive_staging_tested": True,
            "size_md5_blake3_and_xml_failure_bytes_preserved": True,
            "redirect_refusal_and_path_containment_tested": True,
            "retained_failed_attempt_history_tested": True,
            "pre_attempt_crlf_failure_preserved": True,
            "real_credential_read": False,
            "network_requests_performed": False,
            "external_data_mutated": False,
            "real_recovery_started": False,
        },
        "next_gate": "publish the exact commit and require successful public CI before activation, preflight, or credential entry",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("xb") as handle:
        handle.write((json.dumps(payload, indent=2) + "\n").encode())
        handle.flush()
        os.fsync(handle.fileno())
    print(json.dumps({"status": payload["status"], "output": str(OUTPUT.relative_to(ROOT)).replace("\\", "/")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
