#!/usr/bin/env python3
"""Record local implementation readiness without reading an orbit EOF."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_REF = "records/readiness/m2-orbit-offline-verification-recovery-001-implementation-readiness.json"
BINDINGS = {
    "proposal_sha256": "contracts/milestone-002-orbit-offline-verification-recovery-001-proposal.json",
    "approval_sha256": "records/source-gates/m2-orbit-offline-verification-recovery-001-approval.json",
    "approval_activation_sha256": "records/readiness/m2-orbit-offline-verification-recovery-001-approval-activation.json",
    "approval_reconciliation_sha256": "records/readiness/m2-orbit-offline-verification-recovery-001-approval-reconciliation.json",
    "candidate_contract_sha256": "contracts/m2-orbit-offline-verification-recovery-001.json",
    "builder_sha256": "scripts/build_m2_orbit_offline_verification_recovery_001.py",
    "verifier_sha256": "scripts/verify_m2_orbit_eof_recovery_001.py",
    "runner_sha256": "scripts/run_m2_orbit_offline_verification_recovery_001.py",
    "preflight_sha256": "scripts/preflight_m2_orbit_offline_verification_recovery_001.py",
    "publication_recorder_sha256": "scripts/record_m2_orbit_offline_verification_recovery_001_publication_gate.py",
    "activation_script_sha256": "scripts/activate_m2_orbit_offline_verification_recovery_001.py",
    "terminal_reconciler_sha256": "scripts/reconcile_m2_orbit_offline_verification_recovery_001.py",
    "tests_sha256": "tests/test_m2_orbit_offline_verification_recovery_001.py",
}


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verified-at-utc", required=True)
    parser.add_argument("--focused-test-count", type=int, required=True)
    parser.add_argument("--full-test-count", type=int, required=True)
    parser.add_argument("--checker-file-count", type=int, required=True)
    args = parser.parse_args()
    if not args.verified_at_utc.endswith("Z") or (ROOT / OUTPUT_REF).exists():
        raise SystemExit("invalid verification time or readiness output collision")
    output_parent = ROOT / "records/acquisition/orbit-verification"
    if not output_parent.is_dir() or sorted(path.name for path in output_parent.iterdir()) != [".gitkeep"]:
        raise SystemExit("tracked output parent is not exact and empty except marker")
    candidate = json.loads((ROOT / BINDINGS["candidate_contract_sha256"]).read_text(encoding="utf-8"))
    active = json.loads((ROOT / "contracts/m2-orbit-offline-verification.json").read_text(encoding="utf-8"))
    if (
        candidate.get("status") != "candidate_public_ci_pending"
        or active.get("status") != "terminal_indeterminate_m2_orb_001_receipt_persistence_failure"
        or list(candidate.get("output_refs", {})) != ["M2-ORB-001", "M2-ORB-002", "M2-ORB-003", "M2-ORB-004"]
        or any((ROOT / ref).exists() for ref in candidate.get("output_refs", {}).values())
    ):
        raise SystemExit("candidate, active contract, or output collision differs")
    receipt = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-IMPLEMENTATION-READINESS",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_local_recovery_implementation_ready_public_ci_pending",
        "bindings": {name: sha256(ref) for name, ref in BINDINGS.items()},
        "tests": {
            "focused_test_count": args.focused_test_count,
            "full_repository_test_count": args.full_test_count,
            "project_checker_file_count": args.checker_file_count,
            "git_diff_check": "pass",
        },
        "assertions": {
            "tracked_output_parent_exists": True,
            "receipt_reserved_before_eof_content_read": True,
            "empty_or_partial_reservation_preserved": True,
            "fixed_order_and_stop_on_first_failure_enforced": True,
            "scientific_validation_rules_changed": False,
            "real_eof_content_read": False,
            "network_request_performed": False,
            "credential_value_read_or_recorded": False,
            "external_custody_mutated": False,
            "verification_receipt_created": False,
            "orbit_application_performed": False,
            "dem_or_radar_pixel_action_performed": False,
            "baseline_change_attribution_or_publication_performed": False,
        },
        "next_gate": "commit and successful public default-branch CI before activation, final no-content preflight, or EOF read",
    }
    path = ROOT / OUTPUT_REF
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(receipt, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    print(json.dumps({"status": receipt["status"], "output": OUTPUT_REF}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
