#!/usr/bin/env python3
"""Bind the approved metadata diagnostic implementation to a successful public CI run."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from m2_radar_gtc_input_compatibility_diagnostic_001 import (
    APPROVAL_REF, BUNDLE_SHA, GATE_REF, PROPOSAL_SHA, ROOT, now_utc,
    sha256, verify_public_bindings, write_new_json,
)


RUNNER_REF = "scripts/m2_radar_gtc_input_compatibility_diagnostic_001.py"
TEST_REF = "tests/test_m2_radar_gtc_input_compatibility_diagnostic_001.py"
ARCGIS_REF = "scripts/validate_m2_radar_gtc_input_compatibility_diagnostic_001_arcgis.py"


def git_value(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, type=int)
    args = parser.parse_args()
    verify_public_bindings()
    if (ROOT / GATE_REF).exists():
        raise SystemExit("implementation publication gate collision")
    head = git_value("rev-parse", "HEAD")
    if head != git_value("rev-parse", "origin/main"):
        raise SystemExit("local and public default-branch commits differ")
    run = json.loads(subprocess.check_output([
        "gh", "run", "view", str(args.run_id), "--repo", "drwbkr1/nepal-2026-before-after-map",
        "--json", "conclusion,headSha,url,event,workflowName",
    ], cwd=ROOT, text=True))
    if (
        run.get("conclusion") != "success"
        or run.get("headSha") != head
        or run.get("event") != "push"
        or run.get("workflowName") != "Validate project controls"
        or run.get("url") != f"https://github.com/drwbkr1/nepal-2026-before-after-map/actions/runs/{args.run_id}"
    ):
        raise SystemExit("public CI run does not prove the exact implementation commit")
    gate = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-GTC-INPUT-COMPATIBILITY-DIAGNOSTIC-001-IMPLEMENTATION-PUBLICATION-GATE",
        "recorded_at_utc": now_utc(),
        "status": "pass_public_default_branch_ci_implementation_ready",
        "implementation_commit_sha": head,
        "public_ci_run_id": args.run_id,
        "public_ci_url": run["url"],
        "public_ci_conclusion": "success",
        "bindings": {
            "approval_sha256": sha256(ROOT / APPROVAL_REF),
            "proposal_sha256": PROPOSAL_SHA,
            "review_bundle_sha256": BUNDLE_SHA,
            "runner_sha256": sha256(ROOT / RUNNER_REF),
            "portable_tests_sha256": sha256(ROOT / TEST_REF),
            "arcgis_synthetic_validator_sha256": sha256(ROOT / ARCGIS_REF),
        },
        "released_now": {"final_no_content_preflight": True, "diagnostic_process_after_preflight": True, "new_radar_processing_attempt": False},
    }
    write_new_json(ROOT / GATE_REF, gate)
    print(json.dumps({"status": gate["status"], "implementation_commit_sha": head, "public_ci_run_id": args.run_id, "gate_sha256": sha256(ROOT / GATE_REF)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
