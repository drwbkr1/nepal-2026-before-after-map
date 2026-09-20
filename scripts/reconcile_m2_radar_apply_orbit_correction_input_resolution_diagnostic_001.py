#!/usr/bin/env python3
"""Reconcile the sole read-only diagnostic without rerunning it."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from m2_radar_apply_orbit_correction_input_resolution_diagnostic_001_core import ATTEMPT_ID, CONTRACT_REF, canonical_bytes, sha256_file, write_new_json


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-apply-orbit-correction-input-resolution-diagnostic-001"
TERMINAL_REF = f"records/processing/{PREFIX}-terminal.json"
CLEANUP_REF = f"records/processing/{PREFIX}-cleanup.json"
OUTCOME_REF = f"records/processing/{PREFIX}-outcome-reconciliation.json"
APPROVAL_REF = f"records/source-gates/{PREFIX}-approval.json"
PREFLIGHT_REF = f"records/readiness/{PREFIX}-final-preflight.json"
GATE_REF = f"records/readiness/{PREFIX}-implementation-publication-gate.json"
GATE_STATE_REF = f"records/readiness/{PREFIX}-gate-state-publication.json"
CHECKPOINT = "M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-TERMINAL-REVIEW"
NEXT_ACTION = (
    "Review the terminal input-resolution diagnostic outcome. The diagnostic process is consumed and cannot be resumed, reused, "
    "or retried; no path correction, reconstruction, substitution, geoprocessing, new radar attempt, attribution, or scientific action is released."
)


def load(ref: str) -> dict[str, Any]:
    value = json.loads((ROOT / ref).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"JSON root is not an object: {ref}")
    return value


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
    parser.add_argument("--reconciled-at-utc", required=True)
    args = parser.parse_args()
    if not args.reconciled_at_utc.endswith("Z"):
        raise SystemExit("--reconciled-at-utc must be UTC")
    if (ROOT / OUTCOME_REF).exists():
        raise SystemExit("outcome reconciliation collision")
    if not (ROOT / TERMINAL_REF).is_file() or not (ROOT / CLEANUP_REF).is_file():
        raise SystemExit("terminal or cleanup receipt is absent; refusing reconstruction")
    terminal = load(TERMINAL_REF)
    cleanup = load(CLEANUP_REF)
    preflight = load(PREFLIGHT_REF)
    allowed_statuses = {
        "pass_current_input_resolution_diagnostic_only",
        "block_missing_exact_input_no_retry",
        "block_read_only_diagnostic_failure_no_retry",
    }
    if (
        terminal.get("status") not in allowed_statuses
        or terminal.get("diagnostic_id") != ATTEMPT_ID
        or terminal.get("assertions", {}).get("diagnostic_process_consumed") is not True
        or terminal.get("assertions", {}).get("automatic_retry_performed") is not False
        or cleanup.get("status") != "pass_no_payload_or_temporary_artifact_cleanup_required"
        or cleanup.get("diagnostic_id") != ATTEMPT_ID
        or cleanup.get("terminal_sha256") != sha256_file(ROOT / TERMINAL_REF)
        or preflight.get("status") != "pass_final_no_content_preflight_one_read_only_diagnostic_released"
    ):
        raise SystemExit("terminal diagnostic evidence differs")
    disposition = "pass" if terminal["status"].startswith("pass_") else "block"
    assertions = dict(terminal["assertions"])
    outcome = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-OUTCOME-RECONCILIATION",
        "reconciled_at_utc": args.reconciled_at_utc,
        "status": terminal["status"],
        "disposition": disposition,
        "diagnostic_id": ATTEMPT_ID,
        "bindings": {
            "approval_sha256": sha256_file(ROOT / APPROVAL_REF),
            "diagnostic_contract_sha256": sha256_file(ROOT / CONTRACT_REF),
            "implementation_publication_gate_sha256": sha256_file(ROOT / GATE_REF),
            "gate_state_publication_sha256": sha256_file(ROOT / GATE_STATE_REF),
            "final_preflight_sha256": sha256_file(ROOT / PREFLIGHT_REF),
            "terminal_sha256": sha256_file(ROOT / TERMINAL_REF),
            "cleanup_sha256": sha256_file(ROOT / CLEANUP_REF),
        },
        "diagnostic_result": {
            "filesystem_observations": terminal.get("filesystem_observations"),
            "arcgis_observations": terminal.get("arcgis_observations"),
            "failure_code": terminal.get("failure_code"),
            "failure_type": terminal.get("failure_type"),
            "failure_message": terminal.get("failure_message"),
        },
        "claim_boundary": {
            "current_input_resolution_observation_only": True,
            "historical_root_cause_established": False,
            "corrected_apply_orbit_correction_call_established": False,
            "radar_recovery_readiness_established": False,
            "path_correction_or_substitution_authorized": False,
            "new_radar_attempt_authorized": False,
            "baseline_or_change_authorized": False,
            "interpretation_or_attribution_authorized": False,
            "derived_pixel_publication_authorized": False,
            "scientific_result_established": False,
        },
        "assertions": assertions,
        "next_action": NEXT_ACTION,
    }
    write_new_json(ROOT / OUTCOME_REF, outcome)

    milestone = load("contracts/milestone-002.json")
    units = {item.get("id"): item for item in milestone.get("units", []) if isinstance(item, dict)}
    execution = units["M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-EXECUTION"]
    execution.update({"status": "complete", "disposition": disposition})
    execution["outputs"].extend([TERMINAL_REF, CLEANUP_REF, OUTCOME_REF])
    execution["gates"].update({
        "final_no_content_preflight": "success",
        "diagnostic_processes_started": 1,
        "diagnostic_process_consumed": True,
        "terminal_status": terminal["status"],
        "terminal_sha256": sha256_file(ROOT / TERMINAL_REF),
        "cleanup_sha256": sha256_file(ROOT / CLEANUP_REF),
        "outcome_reconciliation_sha256": sha256_file(ROOT / OUTCOME_REF),
        "apply_orbit_correction_calls": 0,
        "geoprocessing_calls": 0,
    })
    execution["exit_condition_delta"] = {
        "expected": [],
        "observed": [terminal["status"], cleanup["status"]],
        "decision_value": "terminal_diagnostic_only",
        "rationale": "The sole diagnostic process is consumed. Its result supports only the current input-resolution observations recorded in the terminal receipt.",
    }
    milestone["handoff"].update({"current_checkpoint": CHECKPOINT, "next_action": NEXT_ACTION, "parallel_checkpoint": CHECKPOINT, "parallel_next_action": NEXT_ACTION})
    profile = load("records/project-control-profile.json")
    profile["current_checkpoint"].update({"checkpoint_id": CHECKPOINT, "expected_branch": "main", "expected_head": None, "next_action": NEXT_ACTION})
    profile["parallel_checkpoints"] = [{"checkpoint_id": CHECKPOINT, "authority_ref": APPROVAL_REF, "next_action": NEXT_ACTION}]
    goal = load("records/long-term-goal.json")
    goal.update({"current_checkpoint": CHECKPOINT, "parallel_checkpoints": [CHECKPOINT]})
    nonce = args.reconciled_at_utc.replace(":", "").replace("-", "")
    replace_json("contracts/milestone-002.json", milestone, nonce)
    replace_json("records/project-control-profile.json", profile, nonce)
    replace_json("records/long-term-goal.json", goal, nonce)

    evidence = {
        "record_id": "EVID-0197",
        "type": "m2_radar_apply_orbit_correction_input_resolution_diagnostic_001_terminal_outcome",
        "verified_at_utc": args.reconciled_at_utc,
        "status": terminal["status"],
        "claim": "The sole read-only input-resolution diagnostic is terminal and consumed. The evidence supports only current path presence and ArcGIS catalog recognition observations; it establishes no historical cause, correction, recovery readiness, or scientific result.",
        "final_preflight_ref": PREFLIGHT_REF,
        "final_preflight_sha256": sha256_file(ROOT / PREFLIGHT_REF),
        "terminal_ref": TERMINAL_REF,
        "terminal_sha256": sha256_file(ROOT / TERMINAL_REF),
        "cleanup_ref": CLEANUP_REF,
        "cleanup_sha256": sha256_file(ROOT / CLEANUP_REF),
        "outcome_reconciliation_ref": OUTCOME_REF,
        "outcome_reconciliation_sha256": sha256_file(ROOT / OUTCOME_REF),
        "assertions": {
            "diagnostic_id": ATTEMPT_ID,
            "diagnostic_process_consumed": True,
            "disposition": disposition,
            "automatic_retry_performed": False,
            "project_data_content_read": assertions.get("project_data_content_read"),
            "external_custody_accessed": assertions.get("external_custody_accessed"),
            "apply_orbit_correction_invoked": False,
            "geoprocessing_invoked": False,
            "historical_root_cause_established": False,
            "radar_recovery_readiness_established": False,
            "scientific_result_established": False,
            "current_checkpoint": CHECKPOINT,
        },
        "next_action": NEXT_ACTION,
    }
    with (ROOT / "records/evidence-ledger.jsonl").open("ab", buffering=0) as stream:
        stream.write(json.dumps(evidence, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n")
        os.fsync(stream.fileno())
    print(json.dumps({"status": terminal["status"], "disposition": disposition, "diagnostic_id": ATTEMPT_ID}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
