#!/usr/bin/env python3
"""Record local synthetic readiness for the approved recovery-002 implementation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "records/acquisition/sentinel-recovery-002-implementation-readiness.json"
IMPLEMENTATION_FILES = {
    "approval_sha256": ROOT / "records/source-gates/m2-sentinel-recovery-002-approval.json",
    "review_reconciliation_sha256": ROOT / "records/source-gates/m2-sentinel-recovery-002-review-reconciliation.json",
    "core_sha256": ROOT / "scripts/m2_sentinel_recovery_002_core.py",
    "broker_sha256": ROOT / "scripts/m2_sentinel_recovery_002_broker.py",
    "supervisor_sha256": ROOT / "scripts/m2_sentinel_recovery_002_supervisor.py",
    "recovery_runner_sha256": ROOT / "scripts/acquire_m2_sentinel_recovery_002.py",
    "continuation_runner_sha256": ROOT / "scripts/acquire_m2_product_pipe.py",
    "container_verifier_sha256": ROOT / "scripts/verify_m2_sentinel_recovery_002_container.py",
    "supervisor_reconciler_sha256": ROOT / "scripts/reconcile_m2_sentinel_recovery_002_supervisor.py",
    "success_reconciler_sha256": ROOT / "scripts/reconcile_m2_sentinel_recovery_002_success.py",
    "activation_script_sha256": ROOT / "scripts/activate_m2_sentinel_recovery_002.py",
    "final_preflight_sha256": ROOT / "scripts/preflight_m2_sentinel_recovery_002.py",
    "publication_gate_recorder_sha256": ROOT / "scripts/record_m2_sentinel_recovery_002_publication_gate.py",
    "focused_tests_sha256": ROOT / "tests/test_m2_sentinel_recovery_002.py",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verified-at-utc", required=True)
    parser.add_argument("--focused-test-count", type=int, required=True)
    parser.add_argument("--full-test-count", type=int, required=True)
    args = parser.parse_args()
    if OUTPUT.exists() or args.focused_test_count != 12 or args.full_test_count < args.focused_test_count:
        raise SystemExit("readiness inputs or output collision invalid")
    payload = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-SENTINEL-RECOVERY-002-IMPLEMENTATION-READINESS-001",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_local_synthetic_ready_public_ci_pending",
        "bindings": {key: sha256(path) for key, path in IMPLEMENTATION_FILES.items()},
        "tests": {
            "focused_test_count": args.focused_test_count,
            "full_repository_test_count": args.full_test_count,
            "focused_result": "pass",
            "full_repository_result": "pass",
            "forced_broker_termination_tested_on_windows": True,
        },
        "assertions": {
            "secret_absent_from_child_command_and_environment": True,
            "secret_transport_anonymous_pipe_only": True,
            "broker_termination_does_not_end_synthetic_worker": True,
            "nonsecret_started_heartbeat_terminal_evidence_tested": True,
            "absent_worker_reconciliation_tested": True,
            "byte_zero_no_range_request_fixed": True,
            "exclusive_staging_and_atomic_no_replace_tested": True,
            "size_and_md5_failure_bytes_preserved": True,
            "redirect_refusal_and_path_containment_tested": True,
            "real_credential_read": False,
            "network_requests_performed": False,
            "external_data_mutated": False,
            "real_recovery_started": False,
        },
        "next_gate": "publish exact commit and require successful public CI before activation or credential entry",
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
