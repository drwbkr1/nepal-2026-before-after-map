#!/usr/bin/env python3
"""Record the public-CI gate for the exact recovery-002 implementation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "records/acquisition/sentinel-recovery-002-publication-gate.json"
FILES = {
    "approval_sha256": ROOT / "records/source-gates/m2-sentinel-recovery-002-approval.json",
    "review_reconciliation_sha256": ROOT / "records/source-gates/m2-sentinel-recovery-002-review-reconciliation.json",
    "activation_script_sha256": ROOT / "scripts/activate_m2_sentinel_recovery_002.py",
    "core_sha256": ROOT / "scripts/m2_sentinel_recovery_002_core.py",
    "broker_sha256": ROOT / "scripts/m2_sentinel_recovery_002_broker.py",
    "supervisor_sha256": ROOT / "scripts/m2_sentinel_recovery_002_supervisor.py",
    "recovery_runner_sha256": ROOT / "scripts/acquire_m2_sentinel_recovery_002.py",
    "continuation_runner_sha256": ROOT / "scripts/acquire_m2_product_secret_pipe.py",
    "container_verifier_sha256": ROOT / "scripts/verify_m2_sentinel_recovery_002_container.py",
    "final_preflight_sha256": ROOT / "scripts/preflight_m2_sentinel_recovery_002.py",
    "supervisor_reconciler_sha256": ROOT / "scripts/reconcile_m2_sentinel_recovery_002_supervisor.py",
    "success_reconciler_sha256": ROOT / "scripts/reconcile_m2_sentinel_recovery_002_success.py",
    "tests_sha256": ROOT / "tests/test_m2_sentinel_recovery_002.py",
    "implementation_readiness_sha256": ROOT / "records/acquisition/sentinel-recovery-002-implementation-readiness.json",
    "implementation_readiness_recorder_sha256": ROOT / "scripts/record_m2_sentinel_recovery_002_implementation_readiness.py",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verified-at-utc", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--run-url", required=True)
    args = parser.parse_args()
    if OUTPUT.exists():
        raise SystemExit("refusing publication-gate output collision")
    if re.fullmatch(r"[0-9a-f]{40}", args.commit_sha) is None:
        raise SystemExit("invalid commit SHA")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    origin = subprocess.run(["git", "rev-parse", "origin/main"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    if head != args.commit_sha or origin != args.commit_sha:
        raise SystemExit("publication commit is not current HEAD and origin/main")
    if args.run_id <= 0 or not args.run_url.startswith("https://github.com/drwbkr1/nepal-2026-before-after-map/actions/runs/"):
        raise SystemExit("invalid GitHub Actions identity")
    missing = [str(path.relative_to(ROOT)) for path in FILES.values() if not path.is_file()]
    if missing:
        raise SystemExit("missing implementation files: " + ", ".join(missing))
    payload = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-SENTINEL-RECOVERY-002-PUBLICATION-GATE-001",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_public_controls_verified_before_recovery_002",
        "bindings": {key: sha256(path) for key, path in FILES.items()},
        "github_actions": {
            "workflow": "Validate project controls",
            "run_id": args.run_id,
            "url": args.run_url,
            "head_sha": args.commit_sha,
            "conclusion": "success",
        },
        "assertions": {
            "remote_ref_verified": True,
            "public_ci_passed": True,
            "real_recovery_started": False,
            "network_requests_performed_by_this_record": False,
            "credential_values_read_or_recorded": False,
            "authority_created": False,
        },
        "next_gate": "activate recovery-002 and pass the deterministic no-payload preflight before opening the broker",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(json.dumps({"status": payload["status"], "output": str(OUTPUT.relative_to(ROOT)).replace("\\", "/")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
