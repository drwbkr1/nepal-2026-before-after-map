#!/usr/bin/env python3
"""Record the exact successful public CI gate without reading external data."""

from __future__ import annotations

import argparse
import json
import subprocess

from m2_dem_vertical_datum_proj25_core import ROOT, sha256_file, write_new_json


OUTPUT = ROOT / "records/readiness/m2-dem-vertical-datum-proj25-metadata-recovery-001-implementation-publication-gate.json"
RECONCILIATION = ROOT / "records/readiness/m2-dem-vertical-datum-proj25-metadata-recovery-001-implementation-publication-reconciliation.json"
IMPLEMENTATION_COMMIT = "b37f9da8753a1e6e192f909b76a8097224d49021"


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
    if OUTPUT.exists() or RECONCILIATION.exists():
        raise SystemExit("metadata-recovery publication output collision")
    if not args.verified_at_utc.endswith("Z"):
        raise SystemExit("--verified-at-utc must be UTC")
    if command("git", "rev-parse", "HEAD") != IMPLEMENTATION_COMMIT:
        raise SystemExit("local HEAD is not the exact implementation commit")
    if command("git", "branch", "--show-current") != "main":
        raise SystemExit("metadata-recovery publication gate requires local main")
    run = json.loads(command(
        "gh", "run", "view", str(args.run_id),
        "--json", "headSha,conclusion,event,workflowName,url",
    ))
    if (
        run.get("headSha") != IMPLEMENTATION_COMMIT
        or run.get("conclusion") != "success"
        or run.get("event") != "push"
    ):
        raise SystemExit("public CI run does not prove the exact implementation commit")
    bindings = {
        "approval_sha256": sha256_file(ROOT / "records/source-gates/m2-dem-vertical-datum-proj25-metadata-recovery-001-approval.json"),
        "activation_sha256": sha256_file(ROOT / "records/readiness/m2-dem-vertical-datum-proj25-metadata-recovery-001-approval-activation.json"),
        "implementation_readiness_sha256": sha256_file(ROOT / "records/readiness/m2-dem-vertical-datum-proj25-metadata-recovery-001-implementation-readiness.json"),
        "implementation_contract_sha256": sha256_file(ROOT / "config/qa/m2-dem-vertical-datum-proj25-contract.json"),
    }
    gate = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-DEM-VERTICAL-DATUM-PROJ25-METADATA-RECOVERY-001-IMPLEMENTATION-PUBLICATION-GATE",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_public_default_branch_ci_offline_recovery_released",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "public_ci_run_id": args.run_id,
        "public_ci_conclusion": "success",
        "public_ci_event": run["event"],
        "public_ci_workflow": run["workflowName"],
        "public_ci_url": run["url"],
        "repository_required_file_count": args.required_file_count,
        "public_test_count": args.public_test_count,
        "public_intentional_skip_count": args.public_skip_count,
        "bindings": bindings,
        "released_now": {
            "final_no_content_preflight": True,
            "offline_recovery_only_after_preflight": True,
            "grid_promotion_only_on_recovery_pass": True,
            "local_operation_and_sign_preflight_only_after_promotion": True,
            "fixed_order_conversion_only_after_all_prior_gates": True,
        },
        "assertions": {
            "final_no_content_preflight_performed": False,
            "network_requests_performed": False,
            "preserved_grid_bytes_read": False,
            "grid_promoted": False,
            "dem_pixels_read": False,
            "dem_conversion_executed": False,
            "orbit_or_radar_action_performed": False,
            "scientific_result_established": False,
        },
    }
    write_new_json(OUTPUT, gate)
    reconciliation = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-DEM-VERTICAL-DATUM-PROJ25-METADATA-RECOVERY-001-IMPLEMENTATION-PUBLICATION-RECONCILIATION",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_public_gate_final_no_content_preflight_ready",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "public_ci_run_id": args.run_id,
        "publication_gate_sha256": sha256_file(OUTPUT),
        "current_checkpoint": "M2-DEM-PROJ25-METADATA-RECOVERY-001-IMPLEMENTATION",
        "released_now": {
            "final_no_content_preflight": True,
            "preserved_byte_read": False,
            "grid_promotion": False,
            "dem_conversion": False,
        },
        "assertions": {
            "network_requests_performed": False,
            "preserved_grid_bytes_read": False,
            "external_data_mutated": False,
            "scientific_result_established": False,
        },
    }
    write_new_json(RECONCILIATION, reconciliation)
    print(json.dumps({
        "publication_gate": str(OUTPUT.relative_to(ROOT)).replace("\\", "/"),
        "publication_gate_sha256": sha256_file(OUTPUT),
        "reconciliation": str(RECONCILIATION.relative_to(ROOT)).replace("\\", "/"),
        "reconciliation_sha256": sha256_file(RECONCILIATION),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
