#!/usr/bin/env python3
"""Record local synthetic readiness for approved materialization stage 1."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "records/readiness/m2-materialization-stage-1-implementation-readiness.json"
SUPERSEDED = ROOT / "records/readiness/m2-materialization-stage-1-implementation-readiness-attempt-001-superseded.json"
SUPERSEDED_SHA256 = "8e066c16ca65a8bb4d90a13b0b866b403fdf55e94a5dc8b597e98370fc5bcc6a"
FILES = {
    "approval_sha256": ROOT / "records/source-gates/m2-materialization-pixel-readiness-approval.json",
    "activation_sha256": ROOT / "records/readiness/m2-materialization-pixel-readiness-activation.json",
    "review_reconciliation_sha256": ROOT / "records/source-gates/m2-materialization-pixel-readiness-review-reconciliation.json",
    "materialization_core_sha256": ROOT / "scripts/m2_materialization_core.py",
    "materialization_runner_sha256": ROOT / "scripts/materialize_m2_product.py",
    "remaining_core_sha256": ROOT / "scripts/m2_materialization_remaining_core.py",
    "remaining_preflight_sha256": ROOT / "scripts/preflight_m2_materialization_remaining.py",
    "remaining_runner_sha256": ROOT / "scripts/run_m2_materialization_remaining.py",
    "remaining_reconciler_sha256": ROOT / "scripts/reconcile_m2_materialization_remaining.py",
    "activation_script_sha256": ROOT / "scripts/activate_m2_materialization_pixel_readiness.py",
    "publication_gate_recorder_sha256": ROOT / "scripts/record_m2_materialization_stage_1_publication_gate.py",
    "focused_tests_sha256": ROOT / "tests/test_m2_materialization_remaining.py",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verified-at-utc", required=True)
    parser.add_argument("--focused-test-count", type=int, required=True)
    parser.add_argument("--full-test-count", type=int, required=True)
    args = parser.parse_args()
    if OUTPUT.exists():
        raise SystemExit("refusing implementation-readiness output collision")
    if not SUPERSEDED.is_file() or sha256(SUPERSEDED) != SUPERSEDED_SHA256:
        raise SystemExit("superseded readiness identity drift")
    if args.focused_test_count < 10 or args.full_test_count < args.focused_test_count:
        raise SystemExit("test counts do not satisfy materialization stage-1 readiness")
    missing = [str(path.relative_to(ROOT)) for path in FILES.values() if not path.is_file()]
    if missing:
        raise SystemExit("missing implementation files: " + ", ".join(missing))
    record = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-MATERIALIZATION-STAGE-1-IMPLEMENTATION-READINESS-001",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_local_synthetic_ready_public_ci_pending",
        "supersedes": {
            "ref": str(SUPERSEDED.relative_to(ROOT)).replace("\\", "/"),
            "sha256": SUPERSEDED_SHA256,
            "reason": "the first readiness record preceded executable stop-on-first-failure and exact-order runner tests",
        },
        "bindings": {key: sha256(path) for key, path in FILES.items()},
        "tests": {
            "focused_test_count": args.focused_test_count,
            "full_repository_test_count": args.full_test_count,
            "focused_result": "pass",
            "full_repository_result": "pass",
            "exact_order_tested": True,
            "one_attempt_per_source_tested": True,
            "stop_on_first_failure_tested": True,
            "collision_refusal_tested": True,
            "public_ci_gate_tested": True,
            "no_network_or_authentication_tested": True,
            "no_pixel_decoding_tested": True,
            "no_replacement_tested": True,
        },
        "assertions": {
            "external_data_mutated": False,
            "archive_extraction_performed": False,
            "measurement_pixels_read": False,
            "network_requests_performed": False,
            "authentication_performed": False,
            "real_materialization_started": False,
            "automatic_retry_authorized": False,
            "header_or_pixel_stage_released": False,
        },
        "next_gate": "publish this exact stage-1 implementation and require successful public CI before the final no-mutation preflight",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"status": record["status"], "output": str(OUTPUT.relative_to(ROOT)).replace("\\", "/")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
