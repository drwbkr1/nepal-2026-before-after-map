#!/usr/bin/env python3
"""Reconcile the one receipt-recovery probe without rerunning or reconstructing it."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from m2_radar_delayed_import_probe_receipt_recovery_001_core import (
    ATTEMPT_ID,
    EXPECTED_AGGREGATE_SHA256,
    STAGE_ORDER,
    canonical_bytes,
    local_attempt_root,
    sha256_file,
    stage_positions,
    write_new_json,
)


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-delayed-import-probe-receipt-recovery-001"
TERMINAL_REF = f"records/processing/{PREFIX}-terminal-reconciliation.json"
OUTCOME_REF = f"records/processing/{PREFIX}-outcome-reconciliation.json"
APPROVAL_REF = f"records/source-gates/{PREFIX}-approval.json"
CONTRACT_REF = f"config/qa/{PREFIX}-contract.json"
PREFLIGHT_REF = f"records/readiness/{PREFIX}-final-preflight.json"
GATE_REF = f"records/readiness/{PREFIX}-implementation-publication-gate.json"
GATE_STATE_REF = f"records/readiness/{PREFIX}-gate-state-publication.json"
CHECKPOINT = "M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-TERMINAL-REVIEW"
NEXT_ACTION = (
    "Review the terminal receipt-recovery diagnostic outcome. The fresh attempt is consumed and cannot be resumed, reused, or retried; "
    "any further diagnostic or radar action requires separately reviewed authority."
)


def load_path(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"JSON root is not an object: {path.name}")
    return value


def load_ref(ref: str) -> dict[str, Any]:
    return load_path(ROOT / ref)


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
    if (ROOT / TERMINAL_REF).exists() or (ROOT / OUTCOME_REF).exists():
        raise SystemExit("reconciliation output collision")
    attempt = local_attempt_root()
    if not attempt.is_dir():
        raise SystemExit("fresh attempt root is absent; refusing reconstruction")
    required = ["terminal-reservation.json", "cleanup-reservation.json", "fallback.jsonl", "started.json", "stages.jsonl"]
    missing = [name for name in required if not (attempt / name).is_file()]
    if missing:
        raise SystemExit("missing durable attempt evidence: " + ", ".join(missing))

    started = load_path(attempt / "started.json")
    if started.get("attempt_id") != ATTEMPT_ID:
        raise SystemExit("attempt identity differs")
    stages_records = [json.loads(line) for line in (attempt / "stages.jsonl").read_text(encoding="utf-8").splitlines()]
    stages = [item.get("stage") for item in stages_records]
    positions = stage_positions(stages)
    if positions != sorted(positions) or len(positions) != len(set(positions)):
        raise SystemExit("durable stage order is not monotonic and unique")
    fallback = [json.loads(line) for line in (attempt / "fallback.jsonl").read_text(encoding="utf-8").splitlines()]
    terminal = load_path(attempt / "terminal.json") if (attempt / "terminal.json").is_file() else None
    cleanup = load_path(attempt / "cleanup.json") if (attempt / "cleanup.json").is_file() else None
    primary_fallback = next((item.get("error") for item in fallback if item.get("event") == "probe_exception_captured"), None)
    terminal_persistence = next((item.get("error") for item in fallback if item.get("event") == "terminal_persistence_exception_captured"), None)
    cleanup_persistence = next((item.get("error") for item in fallback if item.get("event") == "cleanup_persistence_exception_captured"), None)

    if terminal is not None and terminal.get("status") == "pass_exact_disposable_delayed_import_sequence":
        disposition = "pass"
        terminal_status = "pass_exact_receipt_recovery_probe_no_retry"
        failure = None
    else:
        disposition = "block"
        terminal_status = "block_receipt_recovery_probe_no_retry"
        failure = (
            ({key: terminal.get(key) for key in ("failure_code", "failure_type", "failure_message")} if terminal else None)
            or primary_fallback
            or terminal_persistence
            or cleanup_persistence
            or {"failure_code": "terminal_evidence_incomplete", "failure_type": "Unknown", "failure_message": "No reconstructable success or primary failure."}
        )

    corpus = terminal.get("corpus") if terminal else None
    exact_hash = bool(corpus and corpus.get("aggregate_sha256") == EXPECTED_AGGREGATE_SHA256)
    cleanup_status = cleanup.get("status") if cleanup else "cleanup_receipt_not_persisted"
    payload_removed = not (attempt / "corpus").exists() and not (attempt / "scratch").exists()
    terminal_reconciliation = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-TERMINAL-RECONCILIATION",
        "reconciled_at_utc": args.reconciled_at_utc,
        "status": terminal_status,
        "disposition": disposition,
        "attempt_id": ATTEMPT_ID,
        "attempt_path_class": "local_appdata_probe_specific_outside_git_and_external_custody",
        "durable_artifacts": {
            name: sha256_file(attempt / name)
            for name in required + (["terminal.json"] if terminal else []) + (["cleanup.json"] if cleanup else [])
        },
        "durable_stage_evidence": {
            "stage_count": len(stages),
            "stages": stages,
            "last_durable_stage": stages[-1] if stages else None,
            "stage_order_monotonic": True,
            "terminal_receipt_persisted": terminal is not None,
            "cleanup_receipt_persisted": cleanup is not None,
        },
        "terminal_result": terminal,
        "preserved_primary_failure": failure,
        "terminal_persistence_failure": terminal_persistence,
        "cleanup_persistence_failure": cleanup_persistence,
        "cleanup": {"status": cleanup_status, "payload_children_removed": payload_removed},
        "assertions": {
            "attempt_consumed": True,
            "automatic_retry_performed": False,
            "second_attempt_created": False,
            "success_reconstructed": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "network_request_performed": False,
            "credential_value_read": False,
            "radar_processing_executed": False,
            "baseline_or_change_analysis_executed": False,
            "interpretation_or_attribution_executed": False,
            "historical_root_cause_established": False,
            "recovery_readiness_established": False,
            "scientific_result_established": False,
        },
    }
    write_new_json(ROOT / TERMINAL_REF, terminal_reconciliation)
    preflight = load_ref(PREFLIGHT_REF)
    outcome = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-OUTCOME-RECONCILIATION",
        "reconciled_at_utc": args.reconciled_at_utc,
        "status": terminal_status,
        "disposition": disposition,
        "attempt_id": ATTEMPT_ID,
        "bindings": {
            "approval_sha256": sha256_file(ROOT / APPROVAL_REF),
            "probe_contract_sha256": sha256_file(ROOT / CONTRACT_REF),
            "implementation_publication_gate_sha256": sha256_file(ROOT / GATE_REF),
            "gate_state_publication_sha256": sha256_file(ROOT / GATE_STATE_REF),
            "final_preflight_sha256": sha256_file(ROOT / PREFLIGHT_REF),
            "attempt_started_sha256": sha256_file(attempt / "started.json"),
            "stages_sha256": sha256_file(attempt / "stages.jsonl"),
            "fallback_sha256": sha256_file(attempt / "fallback.jsonl"),
            "terminal_reconciliation_sha256": sha256_file(ROOT / TERMINAL_REF),
        },
        "preflight_result": {
            "status": preflight.get("status"),
            "attempt_root_absent": preflight.get("checks", {}).get("attempt_root_absent"),
            "arcpy_imported": preflight.get("checks", {}).get("arcpy_imported_by_preflight"),
            "production_corpus_created": preflight.get("checks", {}).get("disposable_corpus_created"),
            "project_or_external_content_read": preflight.get("checks", {}).get("project_or_external_content_read"),
        },
        "terminal_result": {
            "status": terminal_status,
            "last_durable_stage": stages[-1] if stages else None,
            "terminal_receipt_persisted": terminal is not None,
            "cleanup_receipt_persisted": cleanup is not None,
            "failure": failure,
        },
        "corpus_result": {
            "exact_expected_hash_observed": exact_hash,
            "file_count": corpus.get("file_count") if corpus else None,
            "total_logical_bytes": corpus.get("total_logical_bytes") if corpus else None,
            "aggregate_sha256": corpus.get("aggregate_sha256") if corpus else None,
            "payload_children_removed": payload_removed,
        },
        "claim_boundary": {
            "diagnostic_scope_only": True,
            "historical_root_cause_established": False,
            "radar_recovery_readiness_established": False,
            "scientific_result_established": False,
        },
        "assertions": terminal_reconciliation["assertions"],
        "next_action": NEXT_ACTION,
    }
    write_new_json(ROOT / OUTCOME_REF, outcome)

    milestone = load_ref("contracts/milestone-002.json")
    units = {item.get("id"): item for item in milestone.get("units", []) if isinstance(item, dict)}
    execution = units["M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-EXECUTION"]
    execution.update({"status": "complete", "disposition": disposition})
    execution["outputs"].extend([TERMINAL_REF, OUTCOME_REF])
    execution["gates"].update({
        "final_no_content_preflight": "success",
        "live_attempts_started": 1,
        "attempt_consumed": True,
        "terminal_status": terminal_status,
        "last_durable_stage": stages[-1] if stages else None,
        "terminal_reconciliation_sha256": sha256_file(ROOT / TERMINAL_REF),
        "outcome_reconciliation_sha256": sha256_file(ROOT / OUTCOME_REF),
    })
    execution["exit_condition_delta"] = {
        "expected": [],
        "observed": [terminal_status, cleanup_status],
        "decision_value": "terminal_diagnostic_only",
        "rationale": "The single fresh attempt is consumed. The result supports only the recorded host-time diagnostic boundary.",
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
        "record_id": "EVID-0179",
        "type": "m2_radar_delayed_import_probe_receipt_recovery_001_terminal_outcome",
        "verified_at_utc": args.reconciled_at_utc,
        "status": terminal_status,
        "claim": "The one fresh receipt-recovery diagnostic attempt is terminal and consumed. Its durable receipts support only the recorded diagnostic boundary; no retry, radar-processing, recovery-readiness, causal, or scientific claim is supported.",
        "final_preflight_ref": PREFLIGHT_REF,
        "final_preflight_sha256": sha256_file(ROOT / PREFLIGHT_REF),
        "terminal_reconciliation_ref": TERMINAL_REF,
        "terminal_reconciliation_sha256": sha256_file(ROOT / TERMINAL_REF),
        "outcome_reconciliation_ref": OUTCOME_REF,
        "outcome_reconciliation_sha256": sha256_file(ROOT / OUTCOME_REF),
        "assertions": {
            "attempt_id": ATTEMPT_ID,
            "attempt_consumed": True,
            "disposition": disposition,
            "last_durable_stage": stages[-1] if stages else None,
            "terminal_receipt_persisted": terminal is not None,
            "cleanup_receipt_persisted": cleanup is not None,
            "payload_children_removed": payload_removed,
            "automatic_retry_performed": False,
            "second_attempt_created": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "radar_processing_executed": False,
            "historical_root_cause_established": False,
            "recovery_readiness_established": False,
            "scientific_result_established": False,
            "current_checkpoint": CHECKPOINT,
        },
        "next_action": NEXT_ACTION,
    }
    with (ROOT / "records/evidence-ledger.jsonl").open("ab", buffering=0) as stream:
        stream.write(json.dumps(evidence, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n")
        os.fsync(stream.fileno())
    print(json.dumps({"status": terminal_status, "disposition": disposition, "last_durable_stage": stages[-1] if stages else None}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
