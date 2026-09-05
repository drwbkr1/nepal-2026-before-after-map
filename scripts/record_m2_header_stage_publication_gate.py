#!/usr/bin/env python3
"""Record successful public CI before the two real header inspections."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from record_m2_header_stage_implementation_readiness import FILES as READINESS_FILES


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "records/readiness/m2-header-stage-publication-gate.json"
READINESS = ROOT / "records/readiness/m2-header-stage-implementation-readiness.json"


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
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    origin = subprocess.check_output(["git", "rev-parse", "origin/main"], cwd=ROOT, text=True).strip()
    if head != args.commit_sha or origin != args.commit_sha:
        raise SystemExit("publication commit is not current HEAD and origin/main")
    if args.run_id <= 0 or not args.run_url.startswith("https://github.com/drwbkr1/nepal-2026-before-after-map/actions/runs/"):
        raise SystemExit("invalid GitHub Actions identity")
    readiness = json.loads(READINESS.read_text(encoding="utf-8"))
    if readiness.get("bindings") != {key: sha256(path) for key, path in READINESS_FILES.items()}:
        raise SystemExit("implementation readiness bindings drift")
    record = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-FULL-HEADER-STAGE-PUBLICATION-GATE-001",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_public_controls_verified_before_real_header_inspections",
        "bindings": {
            "approval_sha256": sha256(ROOT / "records/source-gates/m2-materialization-pixel-readiness-approval.json"),
            "materialization_reconciliation_sha256": sha256(ROOT / "records/acquisition/sentinel-materialization-reconciliation-002.json"),
            "implementation_readiness_sha256": sha256(READINESS),
            **{key: sha256(path) for key, path in READINESS_FILES.items() if key.endswith("contract_sha256") or key.endswith("core_sha256") or key.endswith("runner_sha256") or key.endswith("adapter_sha256")},
        },
        "github_actions": {"workflow": "Validate project controls", "run_id": args.run_id, "url": args.run_url, "head_sha": args.commit_sha, "conclusion": "success"},
        "assertions": {"remote_ref_verified": True, "public_ci_passed": True, "real_header_attempt_started": False, "measurement_pixels_read": False, "external_data_mutated": False},
        "next_gate": "pass the final no-header preflight before the one radar real-003 and one optical real-001 inspection",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": record["status"], "output": str(OUTPUT.relative_to(ROOT)).replace("\\", "/")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
