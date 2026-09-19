#!/usr/bin/env python3
"""Record public CI for the receipt-recovery execution gate state."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
from typing import Any

from m2_radar_delayed_import_probe_receipt_recovery_001_core import canonical_bytes, local_attempt_root, sha256_file, write_new_json
from run_m2_radar_delayed_import_probe_receipt_recovery_001 import repository_bindings


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-delayed-import-probe-receipt-recovery-001"
OUTPUT_REF = f"records/readiness/{PREFIX}-gate-state-publication.json"
GATE_REF = f"records/readiness/{PREFIX}-implementation-publication-gate.json"
RECONCILIATION_REF = f"records/readiness/{PREFIX}-implementation-publication-reconciliation.json"
APPROVAL_REF = f"records/source-gates/{PREFIX}-approval.json"
CHECKPOINT = "M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-EXECUTION"
NEXT_ACTION = (
    "Run the one authorized final no-content preflight once. Stop on failure; only on pass may the one fresh disposable "
    "receipt-recovery probe begin, and it must never be retried."
)


def load(ref: str) -> dict[str, Any]:
    return json.loads((ROOT / ref).read_text(encoding="utf-8"))


def replace_json(ref: str, value: object, nonce: str) -> None:
    path = ROOT / ref
    temporary = path.with_name(f".{path.name}.{nonce}.tmp")
    with temporary.open("xb") as stream:
        stream.write(canonical_bytes(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recorded-at-utc", required=True)
    parser.add_argument("--gate-state-commit-sha", required=True)
    parser.add_argument("--public-ci-run-id", type=int, required=True)
    parser.add_argument("--public-ci-url", required=True)
    parser.add_argument("--required-file-count", type=int, required=True)
    parser.add_argument("--public-test-count", type=int, required=True)
    parser.add_argument("--public-skip-count", type=int, required=True)
    args = parser.parse_args()
    if not args.recorded_at_utc.endswith("Z") or len(args.gate_state_commit_sha) != 40:
        raise SystemExit("invalid timestamp or gate-state commit")
    if (ROOT / OUTPUT_REF).exists():
        raise SystemExit("gate-state publication output collision")
    if local_attempt_root().exists():
        raise SystemExit("fresh production attempt already exists")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if head != args.gate_state_commit_sha:
        raise SystemExit("HEAD does not match successful gate-state commit")
    gate = load(GATE_REF)
    reconciliation = load(RECONCILIATION_REF)
    if (
        gate.get("status") != "pass_public_default_branch_ci_receipt_recovery_implementation_ready"
        or gate.get("public_ci_conclusion") != "success"
        or gate.get("bindings") != repository_bindings()
        or reconciliation.get("status") != "pass_public_implementation_gate_gate_state_publication_pending"
    ):
        raise SystemExit("implementation publication gate differs")

    record = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-GATE-STATE-PUBLICATION",
        "recorded_at_utc": args.recorded_at_utc,
        "status": "pass_public_gate_state_final_preflight_released",
        "gate_state_commit_sha": args.gate_state_commit_sha,
        "public_ci_run_id": args.public_ci_run_id,
        "public_ci_url": args.public_ci_url,
        "public_ci_conclusion": "success",
        "repository_required_file_count": args.required_file_count,
        "public_test_count": args.public_test_count,
        "public_intentional_skip_count": args.public_skip_count,
        "bindings": {
            **repository_bindings(),
            "implementation_publication_gate_sha256": sha256_file(ROOT / GATE_REF),
            "implementation_publication_reconciliation_sha256": sha256_file(ROOT / RECONCILIATION_REF),
        },
        "released_now": {"final_no_content_preflight": True, "fresh_probe_only_on_preflight_pass": True},
        "assertions": {
            "final_no_content_preflight_performed": False,
            "fresh_probe_process_started": False,
            "production_corpus_created": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "consumed_probe_reused_or_retried": False,
            "radar_processing_executed": False,
            "historical_root_cause_established": False,
            "recovery_readiness_established": False,
            "scientific_result_established": False,
        },
        "next_action": NEXT_ACTION,
    }
    write_new_json(ROOT / OUTPUT_REF, record)
    milestone = load("contracts/milestone-002.json")
    units = {item.get("id"): item for item in milestone.get("units", []) if isinstance(item, dict)}
    execution = units["M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-EXECUTION"]
    execution["gates"].update({
        "gate_state_publication": "success",
        "gate_state_commit_sha": args.gate_state_commit_sha,
        "gate_state_public_ci_run_id": args.public_ci_run_id,
        "gate_state_publication_sha256": sha256_file(ROOT / OUTPUT_REF),
        "final_no_content_preflight": "released_not_started",
    })
    execution["outputs"].append(OUTPUT_REF)
    milestone["handoff"].update({"current_checkpoint": CHECKPOINT, "next_action": NEXT_ACTION, "parallel_checkpoint": CHECKPOINT, "parallel_next_action": NEXT_ACTION})
    profile = load("records/project-control-profile.json")
    profile["current_checkpoint"].update({"checkpoint_id": CHECKPOINT, "expected_branch": "main", "expected_head": None, "next_action": NEXT_ACTION})
    profile["parallel_checkpoints"] = [{"checkpoint_id": CHECKPOINT, "authority_ref": APPROVAL_REF, "next_action": NEXT_ACTION}]
    goal = load("records/long-term-goal.json")
    goal.update({"current_checkpoint": CHECKPOINT, "parallel_checkpoints": [CHECKPOINT]})
    nonce = str(args.public_ci_run_id)
    replace_json("contracts/milestone-002.json", milestone, nonce)
    replace_json("records/project-control-profile.json", profile, nonce)
    replace_json("records/long-term-goal.json", goal, nonce)

    evidence = {
        "record_id": "EVID-0178",
        "type": "m2_radar_delayed_import_probe_receipt_recovery_001_gate_state_publication",
        "verified_at_utc": args.recorded_at_utc,
        "status": "pass_public_gate_state_final_preflight_released",
        "claim": "The exact receipt-recovery execution gate state passed public default-branch CI. One final no-content preflight is released; the fresh probe remains conditional on that pass.",
        "gate_state_publication_ref": OUTPUT_REF,
        "gate_state_publication_sha256": sha256_file(ROOT / OUTPUT_REF),
        "assertions": {
            "gate_state_commit": args.gate_state_commit_sha,
            "public_ci_run_id": args.public_ci_run_id,
            "public_ci_conclusion": "success",
            "repository_required_file_count": args.required_file_count,
            "public_test_count": args.public_test_count,
            "public_intentional_skip_count": args.public_skip_count,
            "final_no_content_preflight_released": True,
            "final_no_content_preflight_performed": False,
            "fresh_probe_process_started": False,
            "production_corpus_created": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "consumed_probe_reused_or_retried": False,
            "radar_processing_executed": False,
            "scientific_result_established": False,
        },
        "next_action": NEXT_ACTION,
    }
    with (ROOT / "records/evidence-ledger.jsonl").open("ab", buffering=0) as stream:
        stream.write(json.dumps(evidence, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n")
        os.fsync(stream.fileno())
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
