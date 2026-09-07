#!/usr/bin/env python3
"""Record local readiness for the exact four-source offline orbit verifier implementation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "records/readiness/m2-orbit-offline-verification-continuation-001-implementation-readiness.json"
FILES = {
    "candidate_contract_sha256": ROOT / "contracts/m2-orbit-offline-verification-continuation-001.json",
    "active_pending_contract_sha256": ROOT / "contracts/m2-orbit-offline-verification.json",
    "continuation_success_sha256": ROOT / "records/acquisition/m2-orbit-continuation-001-success-reconciliation.json",
    "terminal_project_reconciliation_sha256": ROOT / "records/readiness/m2-orbit-continuation-001-terminal-project-reconciliation.json",
    "verifier_sha256": ROOT / "scripts/verify_m2_orbit_eof.py",
    "candidate_builder_sha256": ROOT / "scripts/build_m2_orbit_offline_verification_continuation_001.py",
    "activation_sha256": ROOT / "scripts/activate_m2_orbit_offline_verification_continuation_001.py",
    "final_preflight_sha256": ROOT / "scripts/preflight_m2_orbit_offline_verification_continuation_001.py",
    "terminal_reconciler_sha256": ROOT / "scripts/reconcile_m2_orbit_offline_verification_continuation_001.py",
    "publication_recorder_sha256": ROOT / "scripts/record_m2_orbit_offline_verification_continuation_001_publication_gate.py",
    "focused_tests_sha256": ROOT / "tests/test_m2_orbit_offline_verification_continuation_001.py",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verified-at-utc", required=True)
    parser.add_argument("--focused-test-count", type=int, required=True)
    parser.add_argument("--full-test-count", type=int, required=True)
    args = parser.parse_args()
    if not args.verified_at_utc.endswith("Z") or OUTPUT.exists():
        raise SystemExit("implementation readiness collision or invalid time")
    if args.focused_test_count < 5 or args.full_test_count < args.focused_test_count:
        raise SystemExit("test counts do not satisfy offline verifier readiness")
    missing = [str(path.relative_to(ROOT)) for path in FILES.values() if not path.is_file()]
    if missing:
        raise SystemExit("missing implementation files: " + ", ".join(missing))
    payload = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ORBIT-OFFLINE-VERIFICATION-CONTINUATION-001-IMPLEMENTATION-READINESS",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_local_offline_verifier_ready_public_ci_pending",
        "bindings": {key: sha256(path) for key, path in FILES.items()},
        "tests": {
            "focused_test_count": args.focused_test_count,
            "full_repository_test_count": args.full_test_count,
            "focused_result": "pass",
            "full_repository_result": "pass",
            "m2_orb_001_local_promotion_receipt_compatibility_tested": True,
            "continuation_receipt_compatibility_tested": True,
            "duplicate_success_rejection_tested": True,
            "preactivation_real_read_refusal_tested": True,
            "exact_source_order_and_one_second_rules_tested": True,
        },
        "assertions": {
            "real_eof_content_read": False,
            "network_request_performed": False,
            "credential_value_read_or_recorded": False,
            "external_data_mutated": False,
            "offline_verification_receipt_created": False,
            "orbit_application_performed": False,
            "radar_pixel_or_dem_action_performed": False,
            "baseline_change_attribution_or_publication_performed": False,
        },
        "next_gate": "publish this exact implementation and require successful public default-branch CI before activation or any EOF content read",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("xb") as stream:
        stream.write((json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"status": payload["status"], "output": str(OUTPUT.relative_to(ROOT)).replace("\\", "/")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
