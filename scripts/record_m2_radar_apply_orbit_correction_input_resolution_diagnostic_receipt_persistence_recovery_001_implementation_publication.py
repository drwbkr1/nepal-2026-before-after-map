#!/usr/bin/env python3
"""Record successful public CI for the diagnostic receipt recovery."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
from typing import Any

from m2_radar_apply_orbit_correction_input_resolution_diagnostic_receipt_persistence_recovery_001_core import canonical_bytes, sha256_file, write_new_json
from run_m2_radar_apply_orbit_correction_input_resolution_diagnostic_receipt_persistence_recovery_001 import repository_bindings


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-apply-orbit-correction-input-resolution-diagnostic-receipt-persistence-recovery-001"
GATE_REF = f"records/readiness/{PREFIX}-implementation-publication-gate.json"
RECONCILIATION_REF = f"records/readiness/{PREFIX}-implementation-publication-reconciliation.json"
READINESS_REF = f"records/readiness/{PREFIX}-implementation-readiness.json"
APPROVAL_REF = f"records/source-gates/{PREFIX}-approval.json"
CHECKPOINT = "M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-EXECUTION"
NEXT_ACTION = (
    "Publish and publicly validate the exact execution-gate state. Do not run the final no-content preflight, import production ArcPy, "
    "or access the frozen exact inputs until that gate-state commit passes public CI."
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
    parser.add_argument("--implementation-commit-sha", required=True)
    parser.add_argument("--public-ci-run-id", type=int, required=True)
    parser.add_argument("--public-ci-url", required=True)
    parser.add_argument("--required-file-count", type=int, required=True)
    parser.add_argument("--public-test-count", type=int, required=True)
    parser.add_argument("--public-skip-count", type=int, required=True)
    args = parser.parse_args()
    if not args.recorded_at_utc.endswith("Z") or len(args.implementation_commit_sha) != 40:
        raise SystemExit("invalid timestamp or implementation commit")
    if (ROOT / GATE_REF).exists() or (ROOT / RECONCILIATION_REF).exists():
        raise SystemExit("implementation publication output collision")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if head != args.implementation_commit_sha:
        raise SystemExit("HEAD does not match successful implementation commit")
    readiness = load(READINESS_REF)
    if readiness.get("status") != "pass_receipt_durability_implementation_public_ci_pending":
        raise SystemExit("implementation readiness differs")

    gate = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-IMPLEMENTATION-PUBLICATION-GATE",
        "recorded_at_utc": args.recorded_at_utc,
        "status": "pass_public_default_branch_ci_receipt_recovery_implementation_ready",
        "implementation_commit_sha": args.implementation_commit_sha,
        "public_ci_run_id": args.public_ci_run_id,
        "public_ci_url": args.public_ci_url,
        "public_ci_conclusion": "success",
        "repository_required_file_count": args.required_file_count,
        "public_test_count": args.public_test_count,
        "public_intentional_skip_count": args.public_skip_count,
        "bindings": repository_bindings(),
        "authority": {
            "approval_ref": APPROVAL_REF,
            "approval_sha256": sha256_file(ROOT / APPROVAL_REF),
            "implementation_readiness_ref": READINESS_REF,
            "implementation_readiness_sha256": sha256_file(ROOT / READINESS_REF),
        },
        "released_now": {
            "gate_state_publication": True,
            "final_no_content_preflight": False,
            "distinct_process": False,
            "project_data_content_read": False,
            "external_custody_access": False,
        },
        "assertions": {
            "final_no_content_preflight_performed": False,
            "distinct_process_started": False,
            "production_arcpy_imported": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "consumed_diagnostic_reused_or_retried": False,
            "consumed_reserved_receipts_mutated": False,
            "apply_orbit_correction_invoked": False,
            "geoprocessing_invoked": False,
            "scientific_result_established": False,
        },
        "next_action": NEXT_ACTION,
    }
    write_new_json(ROOT / GATE_REF, gate)
    reconciliation = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-IMPLEMENTATION-PUBLICATION-RECONCILIATION",
        "recorded_at_utc": args.recorded_at_utc,
        "status": "pass_public_implementation_gate_execution_gate_publication_pending",
        "implementation_publication_gate_ref": GATE_REF,
        "implementation_publication_gate_sha256": sha256_file(ROOT / GATE_REF),
        "implementation_commit_sha": args.implementation_commit_sha,
        "public_ci_run_id": args.public_ci_run_id,
        "released_now": {"gate_state_publication": True, "final_no_content_preflight": False, "distinct_process": False},
        "next_action": NEXT_ACTION,
    }
    write_new_json(ROOT / RECONCILIATION_REF, reconciliation)

    milestone = load("contracts/milestone-002.json")
    units = {item.get("id"): item for item in milestone.get("units", []) if isinstance(item, dict)}
    implementation = units["M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-IMPLEMENTATION"]
    execution = units["M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-EXECUTION"]
    implementation.update({"status": "complete", "disposition": "pass"})
    implementation["outputs"].extend([GATE_REF, RECONCILIATION_REF])
    implementation["gates"].update({
        "public_ci": "success",
        "implementation_commit_sha": args.implementation_commit_sha,
        "public_ci_run_id": args.public_ci_run_id,
        "implementation_publication_gate_sha256": sha256_file(ROOT / GATE_REF),
        "implementation_publication_reconciliation_sha256": sha256_file(ROOT / RECONCILIATION_REF),
    })
    implementation["exit_condition_delta"] = {
        "expected": [],
        "observed": ["exact receipt-durability implementation passed public default-branch CI"],
        "decision_value": "enables_dependency",
        "rationale": "Only execution-gate publication is released now; final preflight and the distinct process remain blocked.",
    }
    execution["status"] = "in_progress"
    execution["gates"].update({"public_ci": "success", "execution_gate_publication": "pending"})
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
        "record_id": "EVID-0201",
        "type": "m2_radar_apply_orbit_correction_input_resolution_diagnostic_receipt_persistence_recovery_001_implementation_publication_gate",
        "verified_at_utc": args.recorded_at_utc,
        "status": "pass_public_ci_execution_gate_publication_pending",
        "claim": "The exact receipt-durability implementation commit passed public default-branch CI. Only execution-gate publication is released; final preflight and the distinct process remain blocked.",
        "implementation_publication_gate_ref": GATE_REF,
        "implementation_publication_gate_sha256": sha256_file(ROOT / GATE_REF),
        "implementation_publication_reconciliation_ref": RECONCILIATION_REF,
        "implementation_publication_reconciliation_sha256": sha256_file(ROOT / RECONCILIATION_REF),
        "assertions": {
            "implementation_commit": args.implementation_commit_sha,
            "public_ci_run_id": args.public_ci_run_id,
            "public_ci_conclusion": "success",
            "repository_required_file_count": args.required_file_count,
            "public_test_count": args.public_test_count,
            "public_intentional_skip_count": args.public_skip_count,
            "execution_gate_publication_pending": True,
            "final_no_content_preflight_performed": False,
            "distinct_process_started": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "consumed_reserved_receipts_mutated": False,
            "geoprocessing_invoked": False,
            "scientific_result_established": False,
            "current_checkpoint": CHECKPOINT,
        },
        "next_action": NEXT_ACTION,
    }
    with (ROOT / "records/evidence-ledger.jsonl").open("ab", buffering=0) as stream:
        stream.write(json.dumps(evidence, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n")
        os.fsync(stream.fileno())
    print(json.dumps(gate, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
