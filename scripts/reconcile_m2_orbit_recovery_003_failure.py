#!/usr/bin/env python3
"""Close terminal recovery-003 and route to the zero-decision OSV precision review."""

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
OUTCOME_REF = "records/acquisition/m2-orbit-recovery-003-outcome-reconciliation.json"
CONTROL_REF = "records/acquisition/m2-orbit-recovery-003-terminal-failure-control-reconciliation.json"
FAILED_RECONCILIATION_REF = "records/acquisition/m2-orbit-recovery-003-outcome-reconciliation-attempt-001-failure.json"
ATTEMPT_REF = "records/acquisition/orbit-attempts/m2-orb-001-recovery-002-20260906t183804z-e5883324.json"
TERMINAL_REF = "records/readiness/m2-orbit-recovery-003-terminal-reconciliation.json"
PROPOSAL_REF = "contracts/milestone-002-orbit-osv-precision-amendment-001-proposal.json"
BUNDLE_REF = "reviews/m2-orbit-osv-precision-amendment-001/review-bundle.json"
CONTRACT_REF = "reviews/m2-orbit-osv-precision-amendment-001/review-contract.json"
BLANK_REF = "reviews/m2-orbit-osv-precision-amendment-001/blank-response.json"
READINESS_REF = "records/readiness/m2-orbit-osv-precision-amendment-001-review-readiness.json"
SOURCE_REF = "records/source-gates/m2-orbit-osv-time-format-evidence.json"
RECOVERY_APPROVAL_REF = "records/source-gates/m2-orbit-recovery-003-approval.json"

PUBLICATION_UNIT = "M2-ORBIT-OSV-PRECISION-AMENDMENT-001-REVIEW-PUBLICATION"
REVIEW_UNIT = "M2-ORBIT-OSV-PRECISION-AMENDMENT-001-REVIEW"
IMPLEMENTATION_UNIT = "M2-ORBIT-OSV-PRECISION-AMENDMENT-001-IMPLEMENTATION"
LOCAL_UNIT = "M2-ORBIT-OSV-PRECISION-AMENDMENT-001"


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


def append_unique(items: list[Any], value: Any) -> None:
    if value not in items:
        items.append(value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconciled-at-utc", required=True)
    args = parser.parse_args()
    if not args.reconciled_at_utc.endswith("Z"):
        raise SystemExit("reconciled time must be UTC")
    if (ROOT / TERMINAL_REF).exists():
        raise SystemExit(f"refusing output collision: {TERMINAL_REF}")

    outcome = load(OUTCOME_REF)
    control = load(CONTROL_REF)
    proposal = load(PROPOSAL_REF)
    bundle = load(BUNDLE_REF)
    contract = load(CONTRACT_REF)
    blank = load(BLANK_REF)
    readiness = load(READINESS_REF)
    if (
        outcome.get("status") != "terminal_failure_preserved_no_retry"
        or outcome.get("attempt_id") != "m2-orb-001-recovery-002-20260906t183804z-e5883324"
        or outcome.get("terminal_code") != "osv_times_do_not_span_validity"
        or outcome.get("assertions", {}).get("owner_handoff_count") != 1
        or outcome.get("assertions", {}).get("recovery_003_authority_consumed") is not True
        or control.get("status") != "reconciled_terminal_failure_active_intake_no_retry"
        or control.get("observations", {}).get("preserved_staged_file", {}).get("sha256") != "a72c93e500a1c09b62b4cd31889837c9d57ccc41542b16397ff9f2c0fccba3f4"
    ):
        raise SystemExit("recovery-003 terminal outcome boundary differs")
    bundle_sha = sha256(BUNDLE_REF)
    if (
        proposal.get("status") != "proposed_not_authorized"
        or proposal.get("human_gate", {}).get("review_required") is not True
        or proposal.get("proposed_amendment", {}).get("maximum_new_download_requests") != 0
        or proposal.get("proposed_amendment", {}).get("maximum_osv_endpoint_tolerance_seconds") != 1.0
        or contract.get("review_bundle", {}).get("manifest_sha256") != bundle_sha
        or blank.get("completed") is not False
        or blank.get("reviewer", {}).get("attestation") is not False
        or blank.get("responses", [{}])[0].get("decision") is not None
        or readiness.get("review", {}).get("human_decision_count") != 0
        or readiness.get("assertions", {}).get("amendment_authorized") is not False
    ):
        raise SystemExit("OSV precision review is not exactly blank and bounded")

    terminal = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ORBIT-RECOVERY-003-TERMINAL-RECONCILIATION",
        "reconciled_at_utc": args.reconciled_at_utc,
        "status": "terminal_validation_failure_preserved_osv_precision_review_publication_pending",
        "bindings": {
            "outcome_ref": OUTCOME_REF,
            "outcome_sha256": sha256(OUTCOME_REF),
            "terminal_control_reconciliation_ref": CONTROL_REF,
            "terminal_control_reconciliation_sha256": sha256(CONTROL_REF),
            "preserved_outcome_reconciliation_failure_ref": FAILED_RECONCILIATION_REF,
            "preserved_outcome_reconciliation_failure_sha256": sha256(FAILED_RECONCILIATION_REF),
            "attempt_receipt_ref": ATTEMPT_REF,
            "attempt_receipt_sha256": sha256(ATTEMPT_REF),
            "recovery_003_approval_ref": RECOVERY_APPROVAL_REF,
            "recovery_003_approval_sha256": sha256(RECOVERY_APPROVAL_REF),
            "source_evidence_ref": SOURCE_REF,
            "source_evidence_sha256": sha256(SOURCE_REF),
            "precision_amendment_proposal_ref": PROPOSAL_REF,
            "precision_amendment_proposal_sha256": sha256(PROPOSAL_REF),
            "precision_amendment_bundle_ref": BUNDLE_REF,
            "precision_amendment_bundle_sha256": bundle_sha,
            "precision_amendment_contract_ref": CONTRACT_REF,
            "precision_amendment_contract_sha256": sha256(CONTRACT_REF),
            "precision_amendment_blank_response_ref": BLANK_REF,
            "precision_amendment_blank_response_sha256": sha256(BLANK_REF),
        },
        "observations": {
            "source_id": "M2-ORB-001",
            "supervisor_id": outcome["supervisor_id"],
            "attempt_id": outcome["attempt_id"],
            "terminal_code": outcome["terminal_code"],
            "downloaded_bytes_preserved_in_staging": 639533,
            "staged_sha256": "a72c93e500a1c09b62b4cd31889837c9d57ccc41542b16397ff9f2c0fccba3f4",
            "provider_md5_matches": True,
            "provider_blake3_matches": True,
            "validity_stop_shortfall_seconds": 0.031829,
            "destination_exists": False,
            "precision_review_human_decision_count": 0,
        },
        "assertions": {
            "recovery_003_owner_handoff_count": 1,
            "recovery_003_download_request_count": 1,
            "recovery_003_authority_consumed": True,
            "recovery_003_automatic_retry_performed": False,
            "orbit_file_promoted": False,
            "precision_amendment_authorized": False,
            "credential_values_read_or_recorded_by_reconciliation": False,
            "network_requests_performed_by_reconciliation": False,
            "external_payload_mutated_by_reconciliation": False,
            "other_orbit_source_requested": False,
            "orbit_application_performed": False,
            "radar_pixels_read": False,
            "dem_action_performed": False,
            "scientific_result_established": False,
        },
        "next_gate": "publish the exact zero-decision OSV precision amendment review and require successful public CI before owner review",
    }
    write_new(TERMINAL_REF, terminal)
    terminal_sha = sha256(TERMINAL_REF)

    milestone = load(MILESTONE_REF)
    profile = load(PROFILE_REF)
    goal = load(GOAL_REF)
    recovery = unit_by_id(milestone, "M2-ORBIT-RECOVERY-003")
    if recovery.get("status") != "ready" or recovery.get("gates", {}).get("authority_consumed") is not False:
        raise SystemExit("recovery-003 unit is not at the exact pre-handoff checkpoint")
    recovery.update({
        "status": "complete",
        "disposition": "block",
        "outputs": [ATTEMPT_REF, CONTROL_REF, OUTCOME_REF, TERMINAL_REF],
        "next_dependency": PUBLICATION_UNIT,
    })
    recovery["gates"].update({
        "owner_handoff_count": 1,
        "supervisor_invocation_count": 1,
        "transfer_attempt_count": 1,
        "download_request_count": 1,
        "preserved_staged_bytes": 639533,
        "authority_consumed": True,
        "terminal_code": "osv_times_do_not_span_validity",
        "outcome_ref": OUTCOME_REF,
        "outcome_sha256": sha256(OUTCOME_REF),
        "terminal_reconciliation_ref": TERMINAL_REF,
        "terminal_reconciliation_sha256": terminal_sha,
    })
    for ref in (ATTEMPT_REF, FAILED_RECONCILIATION_REF, CONTROL_REF, OUTCOME_REF):
        append_unique(recovery["retained_failures"], ref)
    recovery["exit_condition_delta"] = {
        "expected": ["EXIT-201-VERIFIED-CUSTODY"],
        "observed": [],
        "decision_value": "block",
        "rationale": "The one approved request retained checksum-matching bytes in staging but failed the frozen literal OSV validity-span check by 0.031829 seconds; no promotion occurred and recovery-003 cannot retry.",
    }

    add_unique_unit(milestone, {
        "id": PUBLICATION_UNIT,
        "purpose": "Publish and publicly validate the exact zero-decision OSV precision amendment review packet before owner review.",
        "depends_on": ["M2-ORBIT-RECOVERY-003"],
        "action_class": "external_publication",
        "human_gate": False,
        "status": "ready",
        "inputs": [PROPOSAL_REF, BUNDLE_REF, CONTRACT_REF, READINESS_REF, TERMINAL_REF],
        "outputs": ["records/readiness/m2-orbit-osv-precision-amendment-001-review-publication-gate.json"],
        "gates": {"public_ci": "required", "human_decision_count": 0, "amendment_authorized": False},
        "disposition": None,
        "retained_failures": [ATTEMPT_REF, OUTCOME_REF],
        "exit_condition_delta": {"expected": [], "observed": [], "decision_value": "unknown", "rationale": "The packet is locally ready but has not passed its public default-branch gate."},
        "next_dependency": REVIEW_UNIT,
    })
    add_unique_unit(milestone, {
        "id": REVIEW_UNIT,
        "purpose": "Obtain one exact owner decision on the proposed one-second OSV endpoint-consistency rule and preserved-staging route.",
        "depends_on": [PUBLICATION_UNIT],
        "action_class": "authority_broadening",
        "human_gate": True,
        "status": "planned",
        "inputs": [PROPOSAL_REF, BUNDLE_REF, CONTRACT_REF, TERMINAL_REF],
        "outputs": ["records/source-gates/m2-orbit-osv-precision-amendment-001-review-reconciliation.json", "records/source-gates/m2-orbit-osv-precision-amendment-001-approval.json"],
        "gates": {"proposal_sha256": sha256(PROPOSAL_REF), "review_bundle_sha256": bundle_sha, "review_contract_sha256": sha256(CONTRACT_REF), "blank_response_sha256": sha256(BLANK_REF), "human_decision_count": 0, "attestation": False, "amendment_authorized": False, "maximum_future_network_requests_if_approved": 0, "maximum_future_local_validation_attempts_if_approved": 1},
        "disposition": None,
        "retained_failures": [ATTEMPT_REF, OUTCOME_REF],
        "exit_condition_delta": {"expected": [], "observed": [], "decision_value": "awaiting_publication_gate", "rationale": "The review remains blank and cannot be handed off until its exact packet passes public CI."},
        "next_dependency": IMPLEMENTATION_UNIT,
    })
    add_unique_unit(milestone, {
        "id": IMPLEMENTATION_UNIT,
        "purpose": "If separately approved, implement and publicly validate only the exact one-second OSV endpoint-consistency amendment.",
        "depends_on": [REVIEW_UNIT],
        "action_class": "external_publication",
        "human_gate": False,
        "status": "planned",
        "inputs": [],
        "outputs": [],
        "gates": {"public_ci": "required_after_approval", "final_no_network_preflight": "required_after_public_ci"},
        "disposition": None,
        "retained_failures": [ATTEMPT_REF, OUTCOME_REF],
        "exit_condition_delta": {"expected": [], "observed": [], "decision_value": "unknown", "rationale": "No amendment decision or implementation exists."},
        "next_dependency": LOCAL_UNIT,
    })
    add_unique_unit(milestone, {
        "id": LOCAL_UNIT,
        "purpose": "If every gate passes, validate the exact preserved staged bytes once and conditionally promote them without any network request.",
        "depends_on": [IMPLEMENTATION_UNIT],
        "action_class": "data_promotion",
        "human_gate": False,
        "status": "planned",
        "inputs": [],
        "outputs": [],
        "gates": {"maximum_local_validation_attempts": 1, "maximum_network_requests": 0, "automatic_retry_authorized": False, "source_id": "M2-ORB-001", "maximum_endpoint_tolerance_seconds": 1.0, "other_orbit_source_requests_authorized_by_this_unit": False},
        "disposition": None,
        "retained_failures": [ATTEMPT_REF, OUTCOME_REF],
        "exit_condition_delta": {"expected": ["EXIT-201-VERIFIED-CUSTODY"], "observed": [], "decision_value": "unknown", "rationale": "The blank review creates no local validation or promotion authority."},
        "next_dependency": "M2-ORBIT-VERIFY",
    })

    orbit_acquire = unit_by_id(milestone, "M2-ORBIT-ACQUIRE")
    orbit_acquire["depends_on"] = ["M2-ORBIT-PREFLIGHT", "M2-RADAR-SOURCE-READINESS", LOCAL_UNIT]
    orbit_acquire["gates"].update({
        "retained_failure_review": "osv_precision_amendment_review_publication_pending_zero_decisions",
        "retained_failure_review_ref": CONTRACT_REF,
        "retained_failure_review_bundle_sha256": bundle_sha,
        "retained_failure_recovery_proposal_sha256": sha256(PROPOSAL_REF),
        "orbit_recovery_003_status": "terminal_block_consumed_one_request_no_promotion",
        "osv_precision_amendment_status": "proposed_not_authorized_publication_pending",
    })
    orbit_acquire["retained_failures"].append({
        "source_id": "M2-ORB-001",
        "supervisor_id": outcome["supervisor_id"],
        "attempt_id": outcome["attempt_id"],
        "failure_code": outcome["terminal_code"],
        "partial_bytes_preserved": 639533,
        "receipt_ref": ATTEMPT_REF,
        "receipt_sha256": sha256(ATTEMPT_REF),
        "outcome_ref": OUTCOME_REF,
        "outcome_sha256": sha256(OUTCOME_REF),
        "retry_automatically_authorized": False,
    })
    orbit_acquire["exit_condition_delta"] = {"expected": ["EXIT-201-VERIFIED-CUSTODY"], "observed": [], "decision_value": "no_progress", "rationale": "Recovery-003 is terminal after the exact staged orbit failed the frozen literal OSV span check; the precision amendment is a zero-decision packet pending public CI."}
    orbit_acquire["rationale"] = "No orbit file is promoted. The exact M2-ORB-001 staged bytes are preserved, but any one-second precision interpretation and local promotion require a separately published and approved amendment."

    append_unique(milestone["scope"]["active_amendments"], RECOVERY_APPROVAL_REF)
    next_action = f"Publish the exact zero-decision OSV precision amendment packet at proposal SHA-256 {sha256(PROPOSAL_REF)} and bundle SHA-256 {bundle_sha}; require successful public CI before owner review. Do not retry recovery-003, touch credentials, request any orbit file, or promote staged bytes."
    milestone["handoff"]["current_checkpoint"] = PUBLICATION_UNIT
    milestone["handoff"]["next_action"] = next_action
    milestone["handoff"]["do_not_carry_forward"].extend([
        "Recovery-003 is terminal and consumed after one handoff and one M2-ORB-001 request; its full checksum-matching staged bytes failed the frozen OSV span check and were not promoted.",
        "The 0.031829-second validity-stop shortfall is an observation; a one-second tolerance is only a proposed inference from format precision and is not yet authorized.",
        "The OSV precision amendment packet has zero decisions and authorizes no token, network request, retry, promotion, other orbit source, processing, or scientific action.",
    ])

    controls = profile["control_surfaces"]
    controls["proposed_amendments"] = [PROPOSAL_REF]
    append_unique(controls["activated_amendments"], RECOVERY_APPROVAL_REF)
    profile["current_checkpoint"] = {"checkpoint_id": PUBLICATION_UNIT, "expected_branch": "main", "expected_head": None, "next_action": next_action}
    explicit = profile["gate_policy"]["explicit_human_gates"]
    explicit[:] = [item for item in explicit if item.get("unit_id") != "M2-ORBIT-RECOVERY-003-REVIEW"]
    explicit.append({"unit_id": REVIEW_UNIT, "reason": "Would authorize only the exact one-second OSV endpoint-consistency implementation, public-CI gate, final no-network preflight, and one local validation and conditional promotion of the already preserved M2-ORB-001 staged bytes.", "authority_ref": CONTRACT_REF})

    goal["current_checkpoint"] = PUBLICATION_UNIT
    goal["proposed_amendments"] = [PROPOSAL_REF]
    append_unique(goal["active_amendments"], RECOVERY_APPROVAL_REF)

    nonce = "orbit-recovery-003-terminal"
    replace_json(MILESTONE_REF, milestone, nonce)
    replace_json(PROFILE_REF, profile, nonce)
    replace_json(GOAL_REF, goal, nonce)
    print(json.dumps({"status": terminal["status"], "terminal_sha256": terminal_sha, "proposal_sha256": sha256(PROPOSAL_REF), "review_bundle_sha256": bundle_sha}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
