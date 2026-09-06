#!/usr/bin/env python3
"""Reconcile terminal recovery-002 failure and route to blank recovery-003 review."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MILESTONE_REF = "contracts/milestone-002.json"
PROFILE_REF = "records/project-control-profile.json"
GOAL_REF = "records/long-term-goal.json"
OUTCOME_REF = "records/acquisition/m2-orbit-recovery-002-outcome-reconciliation.json"
CONTROL_REF = "records/readiness/m2-orbit-recovery-002-terminal-reconciliation.json"
PROPOSAL_REF = "contracts/milestone-002-orbit-recovery-003-proposal.json"
BUNDLE_REF = "reviews/m2-orbit-recovery-003/review-bundle.json"
CONTRACT_REF = "reviews/m2-orbit-recovery-003/review-contract.json"
BLANK_REF = "reviews/m2-orbit-recovery-003/blank-response.json"
READINESS_REF = "records/readiness/m2-orbit-recovery-003-review-readiness.json"
FINAL_PREFLIGHT_REF = "records/acquisition/m2-orbit-recovery-002-final-preflight.json"
PUBLICATION_REF = "records/acquisition/m2-orbit-recovery-002-publication-gate.json"
APPROVAL_REF = "records/source-gates/m2-orbit-recovery-002-approval.json"


def load(ref: str) -> dict[str, Any]:
    value = json.loads((ROOT / ref).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {ref}")
    return value


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def write_new(ref: str, value: dict[str, Any]) -> None:
    path = ROOT / ref
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(canonical_bytes(value))
        stream.flush()
        os.fsync(stream.fileno())


def replace_json(ref: str, value: dict[str, Any], nonce: str) -> None:
    path = ROOT / ref
    temporary = path.with_name(path.name + f".{nonce}.tmp")
    if temporary.exists():
        raise ValueError(f"temporary path collision: {temporary}")
    with temporary.open("xb") as stream:
        stream.write(canonical_bytes(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def unit_by_id(milestone: dict[str, Any], unit_id: str) -> dict[str, Any]:
    matches = [unit for unit in milestone.get("units", []) if unit.get("id") == unit_id]
    if len(matches) != 1:
        raise ValueError(f"expected one milestone unit: {unit_id}")
    return matches[0]


def add_unique_unit(milestone: dict[str, Any], unit: dict[str, Any]) -> None:
    if any(item.get("id") == unit["id"] for item in milestone.get("units", [])):
        raise ValueError(f"unit already exists: {unit['id']}")
    milestone["units"].append(unit)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconciled-at-utc", required=True)
    args = parser.parse_args()
    if not args.reconciled_at_utc.endswith("Z"):
        raise SystemExit("reconciled time must be UTC")
    if (ROOT / CONTROL_REF).exists():
        raise SystemExit(f"refusing output collision: {CONTROL_REF}")

    outcome = load(OUTCOME_REF)
    proposal = load(PROPOSAL_REF)
    bundle = load(BUNDLE_REF)
    contract = load(CONTRACT_REF)
    blank = load(BLANK_REF)
    readiness = load(READINESS_REF)
    if (
        outcome.get("status") != "terminal_pretransfer_supervisor_failure_no_retry"
        or outcome.get("attempt_id") is not None
        or outcome.get("assertions", {}).get("recovery_002_authority_consumed") is not True
        or outcome.get("assertions", {}).get("orbit_download_requested") is not False
        or outcome.get("assertions", {}).get("orbit_payload_bytes_received") != 0
    ):
        raise SystemExit("recovery-002 outcome boundary drift")
    if proposal.get("status") != "proposed_not_authorized" or proposal.get("human_gate", {}).get("review_required") is not True:
        raise SystemExit("recovery-003 proposal is not a blank human gate")
    bundle_sha = sha256(BUNDLE_REF)
    if contract.get("review_bundle", {}).get("manifest_sha256") != bundle_sha:
        raise SystemExit("recovery-003 review contract binding drift")
    if (
        blank.get("completed") is not False
        or blank.get("reviewer", {}).get("attestation") is not False
        or blank.get("responses") != [{"item_id": "M2-ORBIT-RECOVERY-003", "evidence_sha256": bundle_sha, "decision": None, "notes": ""}]
        or readiness.get("review", {}).get("human_decision_count") != 0
        or readiness.get("assertions", {}).get("recovery_003_authorized") is not False
    ):
        raise SystemExit("recovery-003 review is not exactly blank")

    milestone = load(MILESTONE_REF)
    profile = load(PROFILE_REF)
    goal = load(GOAL_REF)
    recovery_002 = unit_by_id(milestone, "M2-ORBIT-RECOVERY-002")
    if recovery_002.get("status") != "ready" or recovery_002.get("gates", {}).get("maximum_real_attempts") != 1:
        raise SystemExit("recovery-002 unit is not at the activated one-attempt checkpoint")

    control = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ORBIT-RECOVERY-002-TERMINAL-RECONCILIATION",
        "reconciled_at_utc": args.reconciled_at_utc,
        "status": "terminal_failure_preserved_recovery_003_review_ready",
        "bindings": {
            "outcome_ref": OUTCOME_REF,
            "outcome_sha256": sha256(OUTCOME_REF),
            "approval_ref": APPROVAL_REF,
            "approval_sha256": sha256(APPROVAL_REF),
            "publication_gate_ref": PUBLICATION_REF,
            "publication_gate_sha256": sha256(PUBLICATION_REF),
            "final_preflight_ref": FINAL_PREFLIGHT_REF,
            "final_preflight_sha256": sha256(FINAL_PREFLIGHT_REF),
            "recovery_003_proposal_ref": PROPOSAL_REF,
            "recovery_003_proposal_sha256": sha256(PROPOSAL_REF),
            "recovery_003_bundle_ref": BUNDLE_REF,
            "recovery_003_bundle_sha256": bundle_sha,
            "recovery_003_contract_ref": CONTRACT_REF,
            "recovery_003_contract_sha256": sha256(CONTRACT_REF),
            "recovery_003_blank_response_ref": BLANK_REF,
            "recovery_003_blank_response_sha256": sha256(BLANK_REF),
        },
        "assertions": {
            "recovery_002_owner_handoff_count": 1,
            "recovery_002_authority_consumed": True,
            "recovery_002_attempt_id_created": False,
            "recovery_002_download_requested": False,
            "recovery_002_payload_bytes_received": 0,
            "recovery_002_automatic_retry_performed": False,
            "recovery_003_human_decision_count": 0,
            "recovery_003_authorized": False,
            "credential_values_read_or_recorded_by_reconciliation": False,
            "network_requests_performed_by_reconciliation": False,
            "external_data_mutated_by_reconciliation": False,
            "radar_pixels_read": False,
            "dem_action_performed": False,
            "scientific_result_established": False,
        },
        "next_gate": f"owner review of recovery-003 bundle SHA-256 {bundle_sha} and proposal SHA-256 {sha256(PROPOSAL_REF)}",
    }
    write_new(CONTROL_REF, control)
    control_sha = sha256(CONTROL_REF)

    recovery_002.update({
        "status": "complete",
        "disposition": "block",
        "outputs": [OUTCOME_REF, CONTROL_REF],
        "next_dependency": "M2-ORBIT-RECOVERY-003-REVIEW",
    })
    recovery_002["gates"].update({
        "final_no_payload_preflight": "pass",
        "owner_handoff_count": 1,
        "supervisor_invocation_count": 1,
        "transfer_attempt_count": 0,
        "authority_consumed": True,
        "outcome_ref": OUTCOME_REF,
        "outcome_sha256": sha256(OUTCOME_REF),
        "terminal_reconciliation_ref": CONTROL_REF,
        "terminal_reconciliation_sha256": control_sha,
    })
    recovery_002["retained_failures"].append(OUTCOME_REF)
    recovery_002["exit_condition_delta"] = {
        "expected": ["EXIT-201-VERIFIED-CUSTODY"],
        "observed": [],
        "decision_value": "block",
        "rationale": "The one approved owner handoff launched a supervisor but terminated in local pretransfer setup before an attempt ID or payload request; the recovery identity is consumed and cannot retry.",
    }

    add_unique_unit(milestone, {
        "id": "M2-ORBIT-RECOVERY-003-REVIEW",
        "purpose": "Obtain one exact owner decision on a distinct evidence-first recovery after the terminal recovery-002 pretransfer failure.",
        "depends_on": ["M2-ORBIT-RECOVERY-002", "M2-RADAR-SOURCE-READINESS", "M2-ORBIT-PREFLIGHT"],
        "action_class": "authority_broadening",
        "human_gate": True,
        "status": "ready",
        "inputs": [PROPOSAL_REF, BUNDLE_REF, CONTRACT_REF, OUTCOME_REF, CONTROL_REF],
        "outputs": ["records/source-gates/m2-orbit-recovery-003-review-reconciliation.json", "records/source-gates/m2-orbit-recovery-003-approval.json"],
        "gates": {"proposal_sha256": sha256(PROPOSAL_REF), "review_bundle_sha256": bundle_sha, "review_contract_sha256": sha256(CONTRACT_REF), "blank_response_sha256": sha256(BLANK_REF), "human_decision_count": 0, "attestation": False, "recovery_authorized": False, "maximum_future_attempts_if_approved": 1, "other_orbit_source_requests_authorized_by_this_review": False},
        "disposition": None,
        "retained_failures": [OUTCOME_REF],
        "exit_condition_delta": {"expected": [], "observed": [], "decision_value": "awaiting_owner_decision", "rationale": "The recovery-003 packet is blank and creates no implementation, credential, catalog, or payload authority."},
        "next_dependency": None,
    })
    add_unique_unit(milestone, {
        "id": "M2-ORBIT-RECOVERY-003-IMPLEMENTATION",
        "purpose": "If separately approved, implement and publicly validate the exact evidence-first recovery-003 controls before any real access.",
        "depends_on": ["M2-ORBIT-RECOVERY-003-REVIEW"],
        "action_class": "external_publication",
        "human_gate": False,
        "status": "planned",
        "inputs": [], "outputs": [],
        "gates": {"public_ci": "required", "final_no_payload_preflight": "required_after_public_ci"},
        "disposition": None, "retained_failures": [OUTCOME_REF],
        "exit_condition_delta": {"expected": [], "observed": [], "decision_value": "unknown", "rationale": "No recovery-003 approval or implementation exists."},
        "next_dependency": "M2-ORBIT-RECOVERY-003",
    })
    add_unique_unit(milestone, {
        "id": "M2-ORBIT-RECOVERY-003",
        "purpose": "If every new gate passes, permit at most one owner handoff and one byte-zero request for exact M2-ORB-001 under a distinct evidence-first identity.",
        "depends_on": ["M2-ORBIT-RECOVERY-003-IMPLEMENTATION"],
        "action_class": "data_acquisition",
        "human_gate": False,
        "status": "planned",
        "inputs": [], "outputs": [],
        "gates": {"maximum_owner_handoffs": 1, "maximum_real_attempts": 1, "automatic_retry_authorized": False, "source_id": "M2-ORB-001", "other_orbit_source_requests_authorized_by_this_unit": False},
        "disposition": None, "retained_failures": [OUTCOME_REF],
        "exit_condition_delta": {"expected": ["EXIT-201-VERIFIED-CUSTODY"], "observed": [], "decision_value": "unknown", "rationale": "The blank review creates no recovery-003 action authority."},
        "next_dependency": "M2-ORBIT-ACQUIRE",
    })

    orbit_acquire = unit_by_id(milestone, "M2-ORBIT-ACQUIRE")
    orbit_acquire["depends_on"] = ["M2-ORBIT-PREFLIGHT", "M2-RADAR-SOURCE-READINESS", "M2-ORBIT-RECOVERY-003"]
    orbit_acquire["gates"].update({
        "retained_failure_review": "recovery_003_review_ready_zero_decisions",
        "retained_failure_review_ref": CONTRACT_REF,
        "retained_failure_review_bundle_sha256": bundle_sha,
        "retained_failure_recovery_proposal_sha256": sha256(PROPOSAL_REF),
        "orbit_recovery_002_status": "terminal_block_consumed_no_transfer_attempt",
        "orbit_recovery_003_status": "planned_not_authorized",
    })
    orbit_acquire["retained_failures"].append({
        "source_id": "M2-ORB-001",
        "supervisor_id": outcome["supervisor_id"],
        "attempt_id": None,
        "failure_code": outcome["failure"]["terminal_code"],
        "partial_bytes_preserved": 0,
        "outcome_ref": OUTCOME_REF,
        "outcome_sha256": sha256(OUTCOME_REF),
        "retry_automatically_authorized": False,
    })
    orbit_acquire["exit_condition_delta"]["rationale"] = "Recovery-002 is terminal without an attempt ID or payload; recovery-003 is a blank human gate and releases no orbit action."
    orbit_acquire["rationale"] = "Orbit acquisition remains deferred until recovery-003 receives an exact owner decision and, only if approved, passes implementation, public CI, final preflight, and its one owner-selected attempt."

    next_action = f"Review M2 orbit recovery-003 bundle SHA-256 {bundle_sha} and proposal SHA-256 {sha256(PROPOSAL_REF)}; approve, revise, or defer the evidence-first one-file recovery. No retry, credential, catalog, payload, DEM, radar-pixel, baseline, change, attribution, or scientific-publication action is authorized before an attested decision."
    milestone["handoff"]["current_checkpoint"] = "M2-ORBIT-RECOVERY-003-REVIEW"
    milestone["handoff"]["next_action"] = next_action
    milestone["handoff"]["do_not_carry_forward"].extend([
        "Recovery-002 is terminal after one owner handoff and supervisor invocation; it created no attempt ID or payload request and cannot be retried under its consumed authority.",
        "The exact recovery-002 local exception category and returned catalog hash are unavailable; preserve that uncertainty.",
        "Recovery-003 is a blank review and authorizes no implementation, credential, catalog, payload, other orbit source, processing, or scientific action.",
    ])
    if APPROVAL_REF not in milestone["scope"]["active_amendments"]:
        milestone["scope"]["active_amendments"].append(APPROVAL_REF)

    controls = profile["control_surfaces"]
    controls["proposed_amendments"] = [PROPOSAL_REF]
    if APPROVAL_REF not in controls["activated_amendments"]:
        controls["activated_amendments"].append(APPROVAL_REF)
    profile["current_checkpoint"] = {"checkpoint_id": "M2-ORBIT-RECOVERY-003-REVIEW", "expected_branch": "main", "expected_head": None, "next_action": next_action}
    explicit = profile["gate_policy"]["explicit_human_gates"]
    explicit[:] = [item for item in explicit if item.get("unit_id") != "M2-ORBIT-RECOVERY-002-REVIEW"]
    explicit.append({"unit_id": "M2-ORBIT-RECOVERY-003-REVIEW", "reason": "Would authorize only the exact evidence-first recovery-003 implementation, public-CI gate, final no-payload preflight, and one owner-selected M2-ORB-001 attempt.", "authority_ref": CONTRACT_REF})

    goal["current_checkpoint"] = "M2-ORBIT-RECOVERY-003-REVIEW"
    goal["proposed_amendments"] = [PROPOSAL_REF]
    if APPROVAL_REF not in goal["active_amendments"]:
        goal["active_amendments"].append(APPROVAL_REF)

    nonce = "orbit-recovery-002-terminal"
    replace_json(MILESTONE_REF, milestone, nonce)
    replace_json(PROFILE_REF, profile, nonce)
    replace_json(GOAL_REF, goal, nonce)
    print(json.dumps({"status": control["status"], "control_sha256": control_sha, "proposal_sha256": sha256(PROPOSAL_REF), "review_bundle_sha256": bundle_sha}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
