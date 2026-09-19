#!/usr/bin/env python3
"""Reconcile the one recovery-002 attempt without rerunning or reconstructing it."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from m2_radar_pixel_orbit_application_001_core import canonical_bytes, sha256_file
from m2_radar_pixel_orbit_application_recovery_002_core import ATTEMPT_ID, CONTRACT_REF, SOURCE_ORDER, ROUTE_ORDER, stage_positions, write_new_json


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-pixel-orbit-application-recovery-002"
TERMINAL_REF = f"records/processing/{PREFIX}-terminal-reconciliation.json"
OUTCOME_REF = f"records/processing/{PREFIX}-outcome-reconciliation.json"
APPROVAL_REF = f"records/source-gates/{PREFIX}-approval.json"
PREFLIGHT_REF = f"records/readiness/{PREFIX}-final-preflight.json"
GATE_REF = f"records/readiness/{PREFIX}-implementation-publication-gate.json"
GATE_STATE_REF = f"records/readiness/{PREFIX}-gate-state-publication.json"
ATTEMPT_ROOT = Path(
    r"C:\Projects\Active\nepal-2026-before-after-map-data\derived\radar-pixel-orbit-application-recovery-002"
    r"\radar-pixel-orbit-application-recovery-002-real-001"
)
CHECKPOINT = "M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-002-TERMINAL-REVIEW"
NEXT_ACTION = (
    "Review the terminal recovery-002 outcome. The fresh attempt is consumed and cannot be resumed, reused, or retried. "
    "Baseline admission, change analysis, interpretation, attribution, derived-pixel publication, and scientific publication "
    "remain blocked pending separate reviewed authority."
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
    attempt = ATTEMPT_ROOT
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
    if positions != sorted(positions):
        raise SystemExit("durable stage order is not monotonic")
    fallback = [json.loads(line) for line in (attempt / "fallback.jsonl").read_text(encoding="utf-8").splitlines()]
    terminal = load_path(attempt / "terminal.json") if (attempt / "terminal.json").is_file() else None
    cleanup = load_path(attempt / "cleanup.json") if (attempt / "cleanup.json").is_file() else None
    primary_fallback = next((item.get("error") for item in fallback if item.get("event") == "processing_exception_captured"), None)
    terminal_persistence = next((item.get("error") for item in fallback if item.get("event") == "terminal_persistence_exception_captured"), None)
    cleanup_persistence = next((item.get("error") for item in fallback if item.get("event") == "cleanup_persistence_exception_captured"), None)

    sources = terminal.get("source_execution", {}) if terminal else {}
    routes = terminal.get("route_evaluations", []) if terminal else []
    source_ids = [item.get("source_id") for item in sources.get("results", [])]
    route_ids = [item.get("route_id") for item in routes]
    success = bool(
        terminal
        and terminal.get("status") == "pass_six_sources_two_routes_qa_only"
        and sources.get("status") == "pass_all_sources"
        and source_ids == SOURCE_ORDER
        and route_ids == ROUTE_ORDER
        and cleanup
        and cleanup.get("status") == "cleanup_completed"
        and terminal.get("external_custody_unchanged") is True
    )
    disposition = "pass" if success else "block"
    terminal_status = "pass_recovery_002_six_sources_two_routes_qa_only_no_retry" if success else "block_recovery_002_attempt_no_retry"
    failed_source = next((item for item in sources.get("results", []) if item.get("status") != "pass_source_qa_only"), None)
    failed_route = next((item for item in routes if item.get("status") != "pass_route_evaluated_qa_only"), None)
    failure = None if success else (
        ({key: terminal.get(key) for key in ("failure_code", "failure_type", "failure_message") if terminal.get(key) is not None} if terminal else None)
        or failed_source
        or failed_route
        or primary_fallback
        or terminal_persistence
        or cleanup_persistence
        or {"failure_code": "terminal_evidence_incomplete", "failure_type": "Unknown", "failure_message": "No reconstructable success or primary failure."}
    )
    content_read = "identity_scan_completed" in stages
    arcpy_invoked = "arcpy_import_started" in stages
    radar_processing = any(item.get("stage") == "source_processing_fixed_order" and item.get("source_id") for item in stages_records)
    route_evaluation = any(item.get("stage") == "route_evaluation_fixed_order" and item.get("route_id") for item in stages_records)
    terminal_reconciliation = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-002-TERMINAL-RECONCILIATION",
        "reconciled_at_utc": args.reconciled_at_utc,
        "status": terminal_status,
        "disposition": disposition,
        "attempt_id": ATTEMPT_ID,
        "attempt_path_class": "approved_external_derived_append_only_exact_attempt_root",
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
        "cleanup": {"status": cleanup.get("status") if cleanup else "cleanup_receipt_not_persisted"},
        "assertions": {
            "attempt_consumed": True,
            "automatic_retry_performed": False,
            "second_attempt_created": False,
            "success_reconstructed": False,
            "project_data_content_read": content_read,
            "external_custody_accessed": content_read,
            "production_arcpy_invoked": arcpy_invoked,
            "radar_processing_executed": radar_processing,
            "route_evaluation_executed": route_evaluation,
            "source_orbit_or_dem_custody_mutated": False,
            "baseline_or_change_analysis_executed": False,
            "interpretation_or_attribution_executed": False,
            "historical_root_cause_established": False,
            "radar_recovery_readiness_established": False,
            "derived_pixel_publication_authorized": False,
            "scientific_result_established": False,
        },
    }
    write_new_json(ROOT / TERMINAL_REF, terminal_reconciliation)
    preflight = load_ref(PREFLIGHT_REF)
    outcome = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-002-OUTCOME-RECONCILIATION",
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
            "attempt_started_sha256": sha256_file(attempt / "started.json"),
            "stages_sha256": sha256_file(attempt / "stages.jsonl"),
            "fallback_sha256": sha256_file(attempt / "fallback.jsonl"),
            "terminal_reconciliation_sha256": sha256_file(ROOT / TERMINAL_REF),
        },
        "preflight_result": {
            "status": preflight.get("status"),
            "attempt_root_absent": preflight.get("assertions", {}).get("attempt_root_absent"),
            "project_data_content_read": preflight.get("assertions", {}).get("project_data_content_read"),
            "external_custody_content_read": preflight.get("assertions", {}).get("external_custody_content_read"),
            "arcpy_invoked": preflight.get("assertions", {}).get("arcpy_invoked"),
        },
        "execution_result": {
            "source_ids_attempted": source_ids,
            "route_ids_attempted": route_ids,
            "stopped_source_id": sources.get("stopped_source_id"),
            "stopped_route_id": terminal.get("stopped_route_id") if terminal else None,
            "external_custody_unchanged": terminal.get("external_custody_unchanged") if terminal else None,
            "failure": failure,
        },
        "claim_boundary": {
            "qa_processing_only": True,
            "baseline_admission_authorized": False,
            "change_analysis_authorized": False,
            "interpretation_or_attribution_authorized": False,
            "historical_root_cause_established": False,
            "radar_recovery_readiness_established": False,
            "derived_pixel_publication_authorized": False,
            "scientific_result_established": False,
        },
        "assertions": terminal_reconciliation["assertions"],
        "next_action": NEXT_ACTION,
    }
    write_new_json(ROOT / OUTCOME_REF, outcome)

    milestone = load_ref("contracts/milestone-002.json")
    units = {item.get("id"): item for item in milestone.get("units", []) if isinstance(item, dict)}
    execution = units["M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-002-EXECUTION"]
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
        "observed": [terminal_status, terminal_reconciliation["cleanup"]["status"]],
        "decision_value": "terminal_qa_only",
        "rationale": "The single fresh recovery-002 attempt is consumed. The result supports only the recorded QA boundary.",
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
        "record_id": "EVID-0187",
        "type": "m2_radar_pixel_orbit_application_recovery_002_terminal_outcome",
        "verified_at_utc": args.reconciled_at_utc,
        "status": terminal_status,
        "claim": "The one fresh recovery-002 attempt is terminal and consumed. Its durable receipts support only the recorded QA boundary; no retry, baseline admission, change analysis, causal, recovery-readiness, derived-publication, or scientific claim is supported.",
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
            "automatic_retry_performed": False,
            "second_attempt_created": False,
            "project_data_content_read": content_read,
            "external_custody_accessed": content_read,
            "radar_processing_executed": radar_processing,
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
    print(json.dumps({"status": terminal_status, "disposition": disposition, "last_durable_stage": stages[-1] if stages else None}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
