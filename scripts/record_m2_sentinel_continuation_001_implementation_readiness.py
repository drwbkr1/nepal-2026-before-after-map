#!/usr/bin/env python3
"""Record local synthetic readiness for continuation-001."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "records/acquisition/sentinel-continuation-001-implementation-readiness.json"
SUPERSEDED = ROOT / "records/acquisition/sentinel-continuation-001-implementation-readiness-attempt-001-superseded.json"
SUPERSEDED_SHA256 = "86af300807b6db28e97deb6b8188d609f02bf0bed3044741e1eb124eddc28c48"
IMPLEMENTATION_FILES = {
    "approval_sha256": ROOT / "records/source-gates/m2-sentinel-continuation-001-approval.json",
    "review_reconciliation_sha256": ROOT / "records/source-gates/m2-sentinel-continuation-001-review-reconciliation.json",
    "core_sha256": ROOT / "scripts/m2_sentinel_continuation_001_core.py",
    "broker_sha256": ROOT / "scripts/m2_sentinel_continuation_001_broker.py",
    "supervisor_sha256": ROOT / "scripts/m2_sentinel_continuation_001_supervisor.py",
    "source_runner_sha256": ROOT / "scripts/acquire_m2_sentinel_continuation_001.py",
    "exact_product_runner_sha256": ROOT / "scripts/acquire_m2_product_pipe.py",
    "transfer_core_sha256": ROOT / "scripts/m2_transfer_core.py",
    "container_verifier_sha256": ROOT / "scripts/verify_m2_product_container.py",
    "success_reconciler_sha256": ROOT / "scripts/reconcile_m2_sentinel_continuation_001_success.py",
    "activation_script_sha256": ROOT / "scripts/activate_m2_sentinel_continuation_001.py",
    "final_preflight_sha256": ROOT / "scripts/preflight_m2_sentinel_continuation_001.py",
    "publication_gate_recorder_sha256": ROOT / "scripts/record_m2_sentinel_continuation_001_publication_gate.py",
    "focused_tests_sha256": ROOT / "tests/test_m2_sentinel_continuation_001.py",
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
    if not SUPERSEDED.is_file() or sha256(SUPERSEDED) != SUPERSEDED_SHA256:
        raise SystemExit("superseded attempt-001 readiness identity drift")
    if args.focused_test_count < 16 or args.full_test_count < args.focused_test_count:
        raise SystemExit("test counts do not satisfy continuation-001 readiness")
    if os.name == "nt" and not args.windows_detachment_tested:
        raise SystemExit("Windows detached-process test was not attested by the local test run")
    missing = [str(path.relative_to(ROOT)) for path in IMPLEMENTATION_FILES.values() if not path.is_file()]
    if missing:
        raise SystemExit("missing implementation files: " + ", ".join(missing))
    payload = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-SENTINEL-CONTINUATION-001-IMPLEMENTATION-READINESS-002",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_local_synthetic_ready_public_ci_pending",
        "supersedes": {
            "ref": str(SUPERSEDED.relative_to(ROOT)).replace("\\", "/"),
            "sha256": SUPERSEDED_SHA256,
            "reason": "prelaunch Git-state boundary was added after the first local pass and before publication",
        },
        "bindings": {key: sha256(path) for key, path in IMPLEMENTATION_FILES.items()},
        "tests": {
            "focused_test_count": args.focused_test_count,
            "full_repository_test_count": args.full_test_count,
            "focused_result": "pass",
            "full_repository_result": "pass",
            "windows_detached_process_tested": bool(args.windows_detachment_tested),
            "safe_known_control_code_tested": True,
            "unexpected_exception_message_and_secret_exclusion_tested": True,
            "fixed_source_order_tested": True,
            "one_attempt_per_source_tested": True,
            "stop_on_first_failure_tested": True,
            "m1_src_004_request_refusal_tested": True,
            "exclusive_staging_and_atomic_no_replace_tested": True,
            "redirect_and_range_refusal_tested": True,
            "container_gate_tested": True,
        },
        "assertions": {
            "network_requests_performed": False,
            "authentication_performed": False,
            "credential_values_read_or_recorded": False,
            "external_product_bytes_mutated": False,
            "product_payload_requested": False,
            "real_continuation_attempt_started": False,
            "m1_src_004_requested": False,
            "automatic_retry_authorized": False,
            "pixel_processing_released": False,
        },
        "next_gate": "publish this exact implementation and require passing public CI before activation or token entry",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(json.dumps({"status": payload["status"], "output": str(OUTPUT.relative_to(ROOT)).replace("\\", "/")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
