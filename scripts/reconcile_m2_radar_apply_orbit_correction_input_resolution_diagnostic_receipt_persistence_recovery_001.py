#!/usr/bin/env python3
"""Reconcile the distinct read-only diagnostic recovery without rerunning it."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from m2_radar_apply_orbit_correction_input_resolution_diagnostic_receipt_persistence_recovery_001_core import ATTEMPT_ID, canonical_bytes, sha256_file, write_new_json


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-apply-orbit-correction-input-resolution-diagnostic-receipt-persistence-recovery-001"
RAW_TERMINAL_REF = f"records/processing/{PREFIX}-terminal.json"
RAW_CLEANUP_REF = f"records/processing/{PREFIX}-cleanup.json"
FALLBACK_REF = f"records/processing/{PREFIX}-fallback.jsonl"
TERMINAL_REF = f"records/processing/{PREFIX}-terminal-reconciliation.json"
OUTCOME_REF = f"records/processing/{PREFIX}-outcome-reconciliation.json"
APPROVAL_REF = f"records/source-gates/{PREFIX}-approval.json"
CONTRACT_REF = f"config/qa/{PREFIX}-contract.json"
PREFLIGHT_REF = f"records/readiness/{PREFIX}-final-preflight.json"
GATE_REF = f"records/readiness/{PREFIX}-implementation-publication-gate.json"
GATE_STATE_REF = f"records/readiness/{PREFIX}-gate-state-publication.json"
CHECKPOINT = "M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-TERMINAL-REVIEW"
NEXT_ACTION = (
    "Review the terminal read-only diagnostic outcome. The distinct process is consumed and cannot be resumed, reused, or retried; "
    "any further diagnostic, path, geoprocessing, or radar action requires separately reviewed authority."
)


def load_ref(ref: str) -> dict[str, Any]:
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


def load_optional_nonempty(ref: str) -> dict[str, Any] | None:
    path = ROOT / ref
    if not path.is_file() or path.stat().st_size == 0:
        return None
    return load_ref(ref)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconciled-at-utc", required=True)
    args = parser.parse_args()
    if not args.reconciled_at_utc.endswith("Z"):
        raise SystemExit("--reconciled-at-utc must be UTC")
    if (ROOT / TERMINAL_REF).exists() or (ROOT / OUTCOME_REF).exists():
        raise SystemExit("reconciliation output collision")
    fallback_path = ROOT / FALLBACK_REF
    if not fallback_path.is_file() or fallback_path.stat().st_size == 0:
        raise SystemExit("durable fallback evidence is absent; refusing reconstruction")
    fallback = [json.loads(line) for line in fallback_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not fallback or fallback[0].get("event") != "fallback_journal_initialized":
        raise SystemExit("fallback initialization evidence differs")
    terminal = load_optional_nonempty(RAW_TERMINAL_REF)
    cleanup = load_optional_nonempty(RAW_CLEANUP_REF)
    primary_fallback = next((item.get("error") for item in fallback if item.get("event") == "primary_diagnostic_exception_captured"), None)
    terminal_persistence = next((item.get("error") for item in fallback if item.get("event") == "terminal_persistence_exception_captured"), None)
    cleanup_persistence = next((item.get("error") for item in fallback if item.get("event") == "cleanup_persistence_exception_captured"), None)
    if terminal is not None and terminal.get("attempt_id") != ATTEMPT_ID:
        raise SystemExit("terminal attempt identity differs")
    if cleanup is not None and cleanup.get("attempt_id") != ATTEMPT_ID:
        raise SystemExit("cleanup attempt identity differs")

    if terminal is not None and terminal.get("status") == "pass_current_input_resolution_diagnostic_only":
        disposition = "pass_diagnostic_only"
        terminal_status = "pass_current_input_resolution_diagnostic_only_no_retry"
        failure = None
    else:
        disposition = "block"
        terminal_status = "block_read_only_diagnostic_recovery_no_retry"
        failure = (
            ({key: terminal.get(key) for key in ("failure_code", "failure_type", "failure_message")} if terminal else None)
            or primary_fallback
            or terminal_persistence
            or cleanup_persistence
            or {"failure_code": "terminal_evidence_incomplete", "failure_type": "Unknown", "failure_message": "No success result can be established from the durable evidence."}
        )
    consumed_terminal = ROOT / "records/processing/m2-radar-apply-orbit-correction-input-resolution-diagnostic-001-terminal.json"
    consumed_cleanup = ROOT / "records/processing/m2-radar-apply-orbit-correction-input-resolution-diagnostic-001-cleanup.json"
    consumed_immutable = (
        consumed_terminal.is_file()
        and consumed_cleanup.is_file()
        and consumed_terminal.stat().st_size == 0
        and consumed_cleanup.stat().st_size == 0
        and sha256_file(consumed_terminal) == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        and sha256_file(consumed_cleanup) == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
    if not consumed_immutable:
        raise SystemExit("consumed zero-byte receipts changed")

    durable_artifacts = {FALLBACK_REF: sha256_file(fallback_path)}
    for ref in (RAW_TERMINAL_REF, RAW_CLEANUP_REF):
        path = ROOT / ref
        if path.is_file():
            durable_artifacts[ref] = sha256_file(path)
    terminal_reconciliation = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-TERMINAL-RECONCILIATION",
        "reconciled_at_utc": args.reconciled_at_utc,
        "status": terminal_status,
        "disposition": disposition,
        "attempt_id": ATTEMPT_ID,
        "durable_artifacts": durable_artifacts,
        "terminal_result": terminal,
        "cleanup_result": cleanup,
        "preserved_primary_failure": failure,
        "terminal_persistence_failure": terminal_persistence,
        "cleanup_persistence_failure": cleanup_persistence,
        "assertions": {
            "distinct_process_consumed": True,
            "automatic_retry_performed": False,
            "second_process_created": False,
            "success_reconstructed": False,
            "consumed_diagnostic_reused_or_retried": False,
            "consumed_reserved_receipts_mutated": False,
            "apply_orbit_correction_invoked": False,
            "geoprocessing_invoked": False,
            "source_or_path_substituted": False,
            "baseline_or_change_analysis_executed": False,
            "interpretation_or_attribution_executed": False,
            "historical_root_cause_established": False,
            "radar_recovery_readiness_established": False,
            "scientific_result_established": False,
        },
    }
    write_new_json(ROOT / TERMINAL_REF, terminal_reconciliation)
    preflight = load_ref(PREFLIGHT_REF)
    outcome = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-OUTCOME-RECONCILIATION",
        "reconciled_at_utc": args.reconciled_at_utc,
        "status": terminal_status,
        "disposition": disposition,
        "attempt_id": ATTEMPT_ID,
        "bindings": {
            "approval_sha256": sha256_file(ROOT / APPROVAL_REF),
            "recovery_contract_sha256": sha256_file(ROOT / CONTRACT_REF),
            "implementation_publication_gate_sha256": sha256_file(ROOT / GATE_REF),
            "gate_state_publication_sha256": sha256_file(ROOT / GATE_STATE_REF),
            "final_preflight_sha256": sha256_file(ROOT / PREFLIGHT_REF),
            "fallback_sha256": sha256_file(fallback_path),
            "terminal_reconciliation_sha256": sha256_file(ROOT / TERMINAL_REF),
        },
        "preflight_result": {
            "status": preflight.get("status"),
            "arcpy_imported": preflight.get("checks", {}).get("arcpy_imported_by_preflight"),
            "external_attempt_root_presence_checked": preflight.get("checks", {}).get("external_attempt_root_presence_checked"),
            "project_or_external_content_read": preflight.get("checks", {}).get("project_or_external_content_read"),
        },
        "terminal_result": {
            "status": terminal_status,
            "raw_terminal_receipt_persisted": terminal is not None,
            "cleanup_receipt_persisted": cleanup is not None,
            "failure": failure,
        },
        "claim_boundary": {
            "current_input_resolution_diagnostic_only": disposition == "pass_diagnostic_only",
            "historical_root_cause_established": False,
            "corrected_apply_orbit_correction_call_established": False,
            "radar_recovery_readiness_established": False,
            "scientific_result_established": False,
        },
        "assertions": terminal_reconciliation["assertions"],
        "next_action": NEXT_ACTION,
    }
    write_new_json(ROOT / OUTCOME_REF, outcome)

    milestone = load_ref("contracts/milestone-002.json")
    units = {item.get("id"): item for item in milestone.get("units", []) if isinstance(item, dict)}
    execution = units["M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-EXECUTION"]
    execution.update({"status": "complete", "disposition": disposition})
    execution["outputs"].extend([RAW_TERMINAL_REF, RAW_CLEANUP_REF, FALLBACK_REF, TERMINAL_REF, OUTCOME_REF])
    execution["gates"].update({
        "final_no_content_preflight": "success",
        "processes_started": 1,
        "process_consumed": True,
        "terminal_status": terminal_status,
        "terminal_reconciliation_sha256": sha256_file(ROOT / TERMINAL_REF),
        "outcome_reconciliation_sha256": sha256_file(ROOT / OUTCOME_REF),
    })
    execution["exit_condition_delta"] = {
        "expected": [],
        "observed": [terminal_status, cleanup.get("status") if cleanup else "cleanup_receipt_not_persisted"],
        "decision_value": "terminal_diagnostic_only",
        "rationale": "The one distinct process is consumed. The result supports only the recorded current input-resolution diagnostic boundary.",
    }
    milestone["handoff"].update({"current_checkpoint": CHECKPOINT, "next_action": NEXT_ACTION, "parallel_checkpoint": CHECKPOINT, "parallel_next_action": NEXT_ACTION})
    profile = load_ref("records/project-control-profile.json")
    profile["current_checkpoint"].update({"checkpoint_id": CHECKPOINT, "expected_branch": "main", "expected_head": None, "next_action": NEXT_ACTION})
    profile["parallel_checkpoints"] = [{"checkpoint_id": CHECKPOINT, "authority_ref": APPROVAL_REF, "next_action": NEXT_ACTION}]
    goal = load_ref("records/long-term-goal.json")
    goal.update({"current_checkpoint": CHECKPOINT, "parallel_checkpoints": [CHECKPOINT]})
    nonce = args.reconciled_at_utc.replace(":", "").replace("-", "")
    replace_json("contracts/milestone-002.json", milestone, nonce)
    replace_json("records/project-control-profile.json", profile, nonce)
    replace_json("records/long-term-goal.json", goal, nonce)

    evidence = {
        "record_id": "EVID-0203",
        "type": "m2_radar_apply_orbit_correction_input_resolution_diagnostic_receipt_persistence_recovery_001_terminal_outcome",
        "verified_at_utc": args.reconciled_at_utc,
        "status": terminal_status,
        "claim": "The one distinct read-only diagnostic recovery process is terminal and consumed. Its durable receipts support only the recorded current input-resolution boundary; no retry, causal, recovery-readiness, processing, or scientific claim is supported.",
        "final_preflight_ref": PREFLIGHT_REF,
        "final_preflight_sha256": sha256_file(ROOT / PREFLIGHT_REF),
        "terminal_reconciliation_ref": TERMINAL_REF,
        "terminal_reconciliation_sha256": sha256_file(ROOT / TERMINAL_REF),
        "outcome_reconciliation_ref": OUTCOME_REF,
        "outcome_reconciliation_sha256": sha256_file(ROOT / OUTCOME_REF),
        "assertions": {
            "attempt_id": ATTEMPT_ID,
            "distinct_process_consumed": True,
            "disposition": disposition,
            "raw_terminal_receipt_persisted": terminal is not None,
            "cleanup_receipt_persisted": cleanup is not None,
            "automatic_retry_performed": False,
            "second_process_created": False,
            "consumed_reserved_receipts_mutated": False,
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
    print(json.dumps({"status": terminal_status, "disposition": disposition}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
