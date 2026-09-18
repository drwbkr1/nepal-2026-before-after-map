#!/usr/bin/env python3
"""Record one successful public implementation CI run without performing real data access."""

from __future__ import annotations

import argparse
import json
import subprocess

from m2_dem_vertical_datum_proj25_core import ROOT, sha256_file, write_new_json


OUTPUT = ROOT / "records/readiness/m2-dem-vertical-datum-proj25-implementation-publication-gate.json"
READINESS = ROOT / "records/readiness/m2-dem-vertical-datum-proj25-implementation-readiness.json"


def command(*args: str) -> str:
    result = subprocess.run(args, cwd=ROOT, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--verified-at-utc", required=True)
    parser.add_argument("--required-file-count", type=int, required=True)
    parser.add_argument("--public-test-count", type=int, required=True)
    parser.add_argument("--public-skip-count", type=int, required=True)
    args = parser.parse_args()
    if OUTPUT.exists():
        raise SystemExit("publication-gate output collision")
    if not args.verified_at_utc.endswith("Z"):
        raise SystemExit("--verified-at-utc must be UTC")
    head = command("git", "rev-parse", "HEAD")
    branch = command("git", "branch", "--show-current")
    if branch != "main":
        raise SystemExit("implementation publication gate requires local main")
    run = json.loads(command("gh", "run", "view", str(args.run_id), "--json", "headSha,conclusion,event,workflowName,url"))
    if run.get("headSha") != head or run.get("conclusion") != "success" or run.get("event") != "push":
        raise SystemExit("public CI run does not prove the exact local implementation commit")
    record = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-DEM-VERTICAL-DATUM-PROJ25-IMPLEMENTATION-PUBLICATION-GATE",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_public_default_branch_ci_real_actions_released",
        "implementation_commit": head,
        "public_ci_run_id": args.run_id,
        "public_ci_conclusion": "success",
        "public_ci_event": run["event"],
        "public_ci_workflow": run["workflowName"],
        "public_ci_url": run["url"],
        "repository_required_file_count": args.required_file_count,
        "public_test_count": args.public_test_count,
        "public_intentional_skip_count": args.public_skip_count,
        "bindings": {
            "approval_sha256": sha256_file(ROOT / "records/source-gates/m2-dem-vertical-datum-alternate-method-001-approval.json"),
            "implementation_contract_sha256": sha256_file(ROOT / "config/qa/m2-dem-vertical-datum-proj25-contract.json"),
            "implementation_readiness_sha256": sha256_file(READINESS),
        },
        "released_now": {
            "final_no_payload_preflight": True,
            "one_grid_request_only_after_preflight": True,
            "conditional_fixed_order_conversion_only_after_grid_and_sign_pass": True,
        },
        "assertions": {
            "grid_request_performed": False,
            "grid_payload_bytes_read": 0,
            "dem_pixels_read": False,
            "dem_conversion_executed": False,
            "proj_network_enabled": False,
            "orbit_or_radar_action_performed": False,
            "scientific_result_established": False,
        },
    }
    write_new_json(OUTPUT, record)
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
