#!/usr/bin/env python3
"""Record local synthetic readiness for the approved one-second OSV amendment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "records/readiness/m2-orbit-osv-precision-amendment-001-implementation-readiness.json"
FILES = {
    "proposal_sha256": ROOT / "contracts/milestone-002-orbit-osv-precision-amendment-001-proposal.json",
    "review_bundle_sha256": ROOT / "reviews/m2-orbit-osv-precision-amendment-001/review-bundle.json",
    "review_reconciliation_sha256": ROOT / "records/source-gates/m2-orbit-osv-precision-amendment-001-review-reconciliation.json",
    "approval_sha256": ROOT / "records/source-gates/m2-orbit-osv-precision-amendment-001-approval.json",
    "approval_activation_sha256": ROOT / "records/readiness/m2-orbit-osv-precision-amendment-001-approval-activation.json",
    "lock_failure_sha256": ROOT / "records/readiness/m2-orbit-osv-precision-amendment-001-review-lock-attempt-001-failure.json",
    "amended_contract_sha256": ROOT / "contracts/m2-orbit-offline-verification-osv-precision-amendment-001.json",
    "contract_builder_sha256": ROOT / "scripts/build_m2_orbit_osv_precision_amendment_001_contract.py",
    "orbit_io_core_sha256": ROOT / "scripts/m2_orbit_io_core.py",
    "amendment_core_sha256": ROOT / "scripts/m2_orbit_osv_precision_amendment_001_core.py",
    "final_preflight_sha256": ROOT / "scripts/preflight_m2_orbit_osv_precision_amendment_001.py",
    "local_action_sha256": ROOT / "scripts/apply_m2_orbit_osv_precision_amendment_001.py",
    "publication_gate_recorder_sha256": ROOT / "scripts/record_m2_orbit_osv_precision_amendment_001_publication_gate.py",
    "focused_tests_sha256": ROOT / "tests/test_m2_orbit_osv_precision_amendment_001.py",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verified-at-utc", required=True)
    parser.add_argument("--focused-test-count", type=int, required=True)
    parser.add_argument("--full-test-count", type=int, required=True)
    args = parser.parse_args()
    if OUTPUT.exists() or args.focused_test_count != 9 or args.full_test_count < args.focused_test_count:
        raise SystemExit("readiness inputs or output collision invalid")
    missing = [str(path.relative_to(ROOT)) for path in FILES.values() if not path.is_file()]
    if missing:
        raise SystemExit("missing implementation files: " + ", ".join(missing))
    payload = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-OSV-PRECISION-AMENDMENT-001-IMPLEMENTATION-READINESS-001",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_local_synthetic_ready_public_ci_pending",
        "bindings": {key: sha256(path) for key, path in FILES.items()},
        "tests": {
            "focused_test_count": args.focused_test_count,
            "full_repository_test_count": args.full_test_count,
            "focused_result": "pass",
            "full_repository_result": "pass",
        },
        "assertions": {
            "exact_endpoint_pass_tested": True,
            "subsecond_endpoint_pass_tested": True,
            "one_second_boundary_pass_tested": True,
            "greater_than_one_second_rejection_tested": True,
            "tolerance_above_one_second_rejected": True,
            "strict_default_preserved": True,
            "atomic_no_replace_promotion_tested_synthetically": True,
            "staging_preservation_tested_synthetically": True,
            "real_staged_file_read": False,
            "network_requests_performed": False,
            "external_data_mutated": False,
            "local_validation_started": False,
            "scientific_result_established": False,
        },
        "next_gate": "publish the exact implementation and require successful public CI before the final no-network preflight or preserved-byte validation",
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
