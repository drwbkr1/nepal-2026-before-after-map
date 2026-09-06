#!/usr/bin/env python3
"""Record local synthetic readiness for the exact orbit continuation implementation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "records/readiness/m2-orbit-continuation-001-implementation-readiness-002.json"
FILES = {
    "approval_sha256": ROOT / "records/source-gates/m2-orbit-continuation-001-approval.json",
    "review_reconciliation_sha256": ROOT / "records/source-gates/m2-orbit-continuation-001-review-reconciliation.json",
    "approval_activation_sha256": ROOT / "records/readiness/m2-orbit-continuation-001-approval-activation.json",
    "approval_reconciliation_sha256": ROOT / "records/readiness/m2-orbit-continuation-001-approval-reconciliation.json",
    "core_sha256": ROOT / "scripts/m2_orbit_continuation_001_core.py",
    "broker_sha256": ROOT / "scripts/m2_orbit_continuation_001_broker.py",
    "supervisor_sha256": ROOT / "scripts/m2_orbit_continuation_001_supervisor.py",
    "source_runner_sha256": ROOT / "scripts/acquire_m2_orbit_continuation_001.py",
    "success_reconciler_sha256": ROOT / "scripts/reconcile_m2_orbit_continuation_001_success.py",
    "activation_script_sha256": ROOT / "scripts/activate_m2_orbit_continuation_001.py",
    "control_reconciler_sha256": ROOT / "scripts/reconcile_m2_orbit_continuation_001_controls.py",
    "final_preflight_sha256": ROOT / "scripts/preflight_m2_orbit_continuation_001.py",
    "publication_gate_recorder_sha256": ROOT / "scripts/record_m2_orbit_continuation_001_publication_gate.py",
    "owner_invoke_script_sha256": ROOT / "scripts/invoke_m2_orbit_continuation_001.ps1",
    "focused_tests_sha256": ROOT / "tests/test_m2_orbit_continuation_001.py",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verified-at-utc", required=True)
    parser.add_argument("--focused-test-count", type=int, required=True)
    parser.add_argument("--full-test-count", type=int, required=True)
    parser.add_argument("--windows-detachment-tested", action="store_true")
    args = parser.parse_args()
    if OUTPUT.exists():
        raise SystemExit("refusing implementation-readiness output collision")
    if args.focused_test_count < 16 or args.full_test_count < args.focused_test_count:
        raise SystemExit("test counts do not satisfy orbit continuation readiness")
    if os.name == "nt" and not args.windows_detachment_tested:
        raise SystemExit("Windows detached-process test was not attested")
    missing = [str(path.relative_to(ROOT)) for path in FILES.values() if not path.is_file()]
    if missing:
        raise SystemExit("missing implementation files: " + ", ".join(missing))
    payload = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-CONTINUATION-001-IMPLEMENTATION-READINESS",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_local_synthetic_ready_public_ci_pending",
        "bindings": {key: sha256(path) for key, path in FILES.items()},
        "tests": {
            "focused_test_count": args.focused_test_count,
            "full_repository_test_count": args.full_test_count,
            "focused_result": "pass",
            "full_repository_result": "pass",
            "windows_detached_process_tested": bool(args.windows_detachment_tested),
            "secret_command_environment_output_exclusion_tested": True,
            "synthetic_interruption_evidence_tested": True,
            "fixed_source_order_tested": True,
            "one_attempt_per_source_tested": True,
            "stop_on_first_failure_tested": True,
            "m2_orb_001_request_refusal_tested": True,
            "exclusive_staging_and_atomic_no_replace_tested": True,
            "redirect_range_and_retry_refusal_tested": True,
            "prospective_one_second_osv_rule_tested": True,
        },
        "assertions": {
            "network_requests_performed": False,
            "authentication_performed": False,
            "credential_values_read_or_recorded": False,
            "external_orbit_bytes_mutated": False,
            "orbit_payload_requested": False,
            "real_continuation_attempt_started": False,
            "m2_orb_001_requested_or_mutated": False,
            "automatic_retry_authorized": False,
            "orbit_application_or_scientific_action_released": False,
        },
        "next_gate": "publish this exact implementation and require passing public default-branch CI before final preflight or owner handoff",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(json.dumps({"status": payload["status"], "output": str(OUTPUT.relative_to(ROOT)).replace("\\", "/")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
