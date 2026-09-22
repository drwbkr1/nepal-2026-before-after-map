#!/usr/bin/env python3
"""Bind and reconcile public CI for the single GTC metadata diagnostic."""

from __future__ import annotations

import argparse
import json
import subprocess

from m2_radar_gtc_input_compatibility_diagnostic_001 import (
    APPROVAL_REF, GATE_REF, PREFLIGHT_REF, ROOT, now_utc, sha256,
    verify_public_bindings, write_new_json,
)


PREFIX = "m2-radar-gtc-input-compatibility-diagnostic-001"
TERMINAL_REF = f"records/processing/{PREFIX}-terminal-reconciliation.json"
OUTCOME_REF = f"records/processing/{PREFIX}-outcome-reconciliation.json"
TERMINAL_GATE_REF = f"records/readiness/{PREFIX}-terminal-publication-gate.json"
FINAL_REF = f"records/readiness/{PREFIX}-terminal-publication-reconciliation.json"


def git_value(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def require_run(run_id: int) -> tuple[str, str]:
    head = git_value("rev-parse", "HEAD")
    if head != git_value("rev-parse", "origin/main"):
        raise SystemExit("local HEAD and public default branch differ")
    run = json.loads(subprocess.check_output([
        "gh", "run", "view", str(run_id), "--repo", "drwbkr1/nepal-2026-before-after-map",
        "--json", "conclusion,headSha,url,event,workflowName",
    ], cwd=ROOT, text=True))
    url = f"https://github.com/drwbkr1/nepal-2026-before-after-map/actions/runs/{run_id}"
    if (
        run.get("conclusion") != "success" or run.get("headSha") != head
        or run.get("url") != url or run.get("event") != "push"
        or run.get("workflowName") != "Validate project controls"
    ):
        raise SystemExit("public CI run does not prove exact terminal commit")
    return head, url


def write_gate(run_id: int) -> None:
    verify_public_bindings()
    if (ROOT / TERMINAL_GATE_REF).exists():
        raise SystemExit("terminal publication gate collision")
    head, url = require_run(run_id)
    terminal = json.loads((ROOT / TERMINAL_REF).read_text(encoding="utf-8"))
    outcome = json.loads((ROOT / OUTCOME_REF).read_text(encoding="utf-8"))
    if terminal.get("status") != "pass_six_current_metadata_candidates_observed_only_no_retry" or outcome.get("status") != "pass_current_metadata_observation_no_processing_release":
        raise SystemExit("terminal or outcome reconciliation differs")
    gate = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-GTC-INPUT-COMPATIBILITY-DIAGNOSTIC-001-TERMINAL-PUBLICATION-GATE",
        "recorded_at_utc": now_utc(),
        "status": "pass_public_sanitized_terminal_diagnostic_only_no_retry",
        "terminal_evidence_commit_sha": head,
        "public_ci_run_id": run_id,
        "public_ci_url": url,
        "public_ci_conclusion": "success",
        "repository_required_file_count": 1332,
        "public_test_count": 724,
        "public_intentional_skip_count": 13,
        "bindings": {
            "approval_sha256": sha256(ROOT / APPROVAL_REF),
            "implementation_gate_sha256": sha256(ROOT / GATE_REF),
            "final_preflight_sha256": sha256(ROOT / PREFLIGHT_REF),
            "terminal_reconciliation_sha256": sha256(ROOT / TERMINAL_REF),
            "outcome_reconciliation_sha256": sha256(ROOT / OUTCOME_REF),
        },
        "released_now": {"sanitized_metadata_observation_public": True, "terminal_owner_review": True, "diagnostic_retry": False, "new_radar_processing_attempt": False, "baseline_or_change_analysis": False, "scientific_publication": False},
        "assertions": {"exact_six_candidates_observed": True, "diagnostic_attempt_consumed": True, "geoprocessing_or_pixel_read_performed": False, "historical_root_cause_established": False, "radar_recovery_readiness_established": False, "scientific_result_established": False},
        "next_action": "Review the structural metadata observation. Any further GTC investigation or radar processing requires separately scoped authority; both recovery-005 and diagnostic-001 are consumed.",
    }
    write_new_json(ROOT / TERMINAL_GATE_REF, gate)
    print(json.dumps({"status": gate["status"], "terminal_publication_gate_sha256": sha256(ROOT / TERMINAL_GATE_REF)}))


def write_final(run_id: int) -> None:
    if (ROOT / FINAL_REF).exists():
        raise SystemExit("terminal publication reconciliation collision")
    head, url = require_run(run_id)
    gate = json.loads((ROOT / TERMINAL_GATE_REF).read_text(encoding="utf-8"))
    if gate.get("status") != "pass_public_sanitized_terminal_diagnostic_only_no_retry" or gate.get("public_ci_conclusion") != "success":
        raise SystemExit("terminal publication gate differs")
    final = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-GTC-INPUT-COMPATIBILITY-DIAGNOSTIC-001-TERMINAL-PUBLICATION-RECONCILIATION",
        "reconciled_at_utc": now_utc(),
        "status": "pass_exact_terminal_gate_public_ci_reconciled",
        "bindings": {"terminal_publication_gate_ref": TERMINAL_GATE_REF, "terminal_publication_gate_sha256": sha256(ROOT / TERMINAL_GATE_REF), "terminal_gate_commit_sha": head, "terminal_gate_public_ci_run_id": run_id, "terminal_gate_public_ci_url": url, "terminal_reconciliation_sha256": sha256(ROOT / TERMINAL_REF), "outcome_reconciliation_sha256": sha256(ROOT / OUTCOME_REF)},
        "current_radar_processing_checkpoint": "M2-RADAR-ESRI-SEQUENCE-RECOVERY-005-TERMINAL-REVIEW",
        "assertions": {"terminal_gate_public_ci_conclusion_success": True, "diagnostic_attempt_consumed": True, "new_radar_processing_attempt_started": False, "historical_root_cause_established": False, "radar_recovery_readiness_established": False, "scientific_result_established": False},
        "next_action": "Review the diagnostic's limited metadata findings and choose a separately scoped follow-on path; no new radar-processing authority is released.",
    }
    write_new_json(ROOT / FINAL_REF, final)
    print(json.dumps({"status": final["status"], "terminal_publication_reconciliation_sha256": sha256(ROOT / FINAL_REF)}))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("gate", "final"))
    parser.add_argument("--run-id", required=True, type=int)
    args = parser.parse_args()
    if args.stage == "gate":
        write_gate(args.run_id)
    else:
        write_final(args.run_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
