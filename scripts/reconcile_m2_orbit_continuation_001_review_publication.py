#!/usr/bin/env python3
"""Record public CI and advance the blank orbit-continuation review gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_REF = "contracts/milestone-002-orbit-continuation-001-proposal.json"
BUNDLE_REF = "reviews/m2-orbit-continuation-001/review-bundle.json"
CONTRACT_REF = "reviews/m2-orbit-continuation-001/review-contract.json"
BLANK_REF = "reviews/m2-orbit-continuation-001/blank-response.json"
READINESS_REF = "records/readiness/m2-orbit-continuation-001-review-readiness.json"
LOCAL_READINESS_REF = "records/readiness/m2-orbit-continuation-001-review-publication-local-readiness.json"
TERMINAL_REF = "records/readiness/m2-orbit-osv-precision-amendment-001-terminal-reconciliation.json"
INTAKE_REF = "contracts/m2-orbit-intake.json"
MILESTONE_REF = "contracts/milestone-002.json"
PROFILE_REF = "records/project-control-profile.json"
GOAL_REF = "records/long-term-goal.json"
PUBLICATION_REF = "records/readiness/m2-orbit-continuation-001-review-publication-gate.json"
RECONCILIATION_REF = "records/readiness/m2-orbit-continuation-001-review-publication-reconciliation.json"
SOURCE_IDS = ["M2-ORB-002", "M2-ORB-003", "M2-ORB-004"]
CHECKPOINT = "M2-ORBIT-CONTINUATION-001-REVIEW"


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
    matches = [item for item in milestone.get("units", []) if item.get("id") == unit_id]
    if len(matches) != 1:
        raise ValueError(f"milestone unit missing or ambiguous: {unit_id}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--published-at-utc", required=True)
    parser.add_argument("--run-id", type=int, required=True)
    args = parser.parse_args()
    if not args.published_at_utc.endswith("Z"):
        raise SystemExit("published time must be UTC")
    if (ROOT / PUBLICATION_REF).exists() or (ROOT / RECONCILIATION_REF).exists():
        raise SystemExit("publication output collision")

    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    origin = subprocess.run(["git", "rev-parse", "origin/main"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    run_raw = subprocess.run(
        ["gh", "run", "view", str(args.run_id), "--json", "databaseId,status,conclusion,headSha,url,workflowName"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    run = json.loads(run_raw)
    proposal = load(PROPOSAL_REF)
    bundle = load(BUNDLE_REF)
    contract = load(CONTRACT_REF)
    blank = load(BLANK_REF)
    readiness = load(READINESS_REF)
    local_readiness = load(LOCAL_READINESS_REF)
    terminal = load(TERMINAL_REF)
    intake = load(INTAKE_REF)
    if (
        head != origin
        or run.get("databaseId") != args.run_id
        or run.get("headSha") != head
        or run.get("status") != "completed"
        or run.get("conclusion") != "success"
        or run.get("workflowName") != "Validate project controls"
        or proposal.get("status") != "proposed_not_authorized"
        or proposal.get("proposed_continuation", {}).get("source_ids_in_exact_order") != SOURCE_IDS
        or proposal.get("proposed_continuation", {}).get("maximum_endpoint_tolerance_seconds") != 1.0
        or bundle.get("candidate_identity") != f"M2-ORBIT-CONTINUATION-001-PROPOSAL-SHA256:{sha256(PROPOSAL_REF)}"
        or contract.get("review_bundle", {}).get("manifest_sha256") != sha256(BUNDLE_REF)
        or blank.get("completed") is not False
        or blank.get("reviewer", {}).get("attestation") is not False
        or blank.get("responses", [{}])[0].get("decision") is not None
        or readiness.get("review", {}).get("human_decision_count") != 0
        or readiness.get("assertions", {}).get("continuation_authorized") is not False
        or local_readiness.get("status") != "pass_exact_zero_decision_packet_ready_public_ci_pending"
        or terminal.get("status") != "pass_exact_m2_orb_001_promoted_remaining_sources_review_required"
        or intake.get("extensions", {}).get("current_orbit_state_counts") != {"authorized": 3, "failed": 0, "promoted": 1}
        or [item.get("state") for item in intake.get("assets", [])] != ["promoted", "authorized", "authorized", "authorized"]
    ):
        raise SystemExit("packet, zero-decision state, current orbit state, or public CI differs")

    publication = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ORBIT-CONTINUATION-001-REVIEW-PUBLICATION-GATE",
        "verified_at_utc": args.published_at_utc,
        "status": "pass_exact_blank_packet_public_ci_owner_review_ready",
        "bindings": {
            "proposal_sha256": sha256(PROPOSAL_REF),
            "review_bundle_sha256": sha256(BUNDLE_REF),
            "review_contract_sha256": sha256(CONTRACT_REF),
            "blank_response_sha256": sha256(BLANK_REF),
            "review_readiness_sha256": sha256(READINESS_REF),
            "local_publication_readiness_sha256": sha256(LOCAL_READINESS_REF),
            "terminal_reconciliation_sha256": sha256(TERMINAL_REF),
            "active_intake_sha256": sha256(INTAKE_REF),
        },
        "github_actions": {
            "workflow_name": run["workflowName"],
            "run_id": run["databaseId"],
            "head_sha": run["headSha"],
            "status": run["status"],
            "conclusion": run["conclusion"],
            "url": run["url"],
        },
        "assertions": {
            "human_decision_count": 0,
            "attestation": False,
            "continuation_authorized": False,
            "implementation_started": False,
            "credential_values_read_or_recorded": False,
            "orbit_network_or_payload_request_performed_by_publication_gate": False,
            "external_data_mutated": False,
            "m2_orb_001_mutated": False,
            "scientific_result_established": False,
        },
        "next_action": "Conduct one exact owner review of the bound continuation-001 packet; do not implement or access any source before a completed attested decision is locked and reconciled.",
    }
    write_new(PUBLICATION_REF, publication)

    milestone = load(MILESTONE_REF)
    profile = load(PROFILE_REF)
    goal = load(GOAL_REF)
    before = {
        "milestone": sha256(MILESTONE_REF),
        "profile": sha256(PROFILE_REF),
        "goal": sha256(GOAL_REF),
    }
    if any(item.get("id", "").startswith("M2-ORBIT-CONTINUATION-001") for item in milestone.get("units", [])):
        raise SystemExit("continuation units already exist")
    retained = [
        "records/acquisition/orbit-attempts/m2-orb-001-20260904t050937z-8ed21d05.json",
        "records/acquisition/m2-orbit-recovery-002-outcome-reconciliation.json",
        "records/acquisition/m2-orbit-recovery-003-outcome-reconciliation.json",
        "records/readiness/m2-orbit-osv-precision-amendment-001-terminal-reconciliation.json",
    ]
    publication_unit = {
        "id": "M2-ORBIT-CONTINUATION-001-REVIEW-PUBLICATION",
        "purpose": "Publish and publicly validate the exact zero-decision continuation packet for the three remaining orbit sources.",
        "depends_on": ["M2-ORBIT-OSV-PRECISION-AMENDMENT-001"],
        "action_class": "external_publication",
        "human_gate": False,
        "status": "complete",
        "inputs": [PROPOSAL_REF, BUNDLE_REF, CONTRACT_REF, READINESS_REF, LOCAL_READINESS_REF, TERMINAL_REF],
        "outputs": [PUBLICATION_REF, RECONCILIATION_REF],
        "gates": {
            "public_ci": "pass",
            "publication_commit": head,
            "public_ci_run_id": run["databaseId"],
            "publication_gate_sha256": sha256(PUBLICATION_REF),
            "human_decision_count": 0,
            "continuation_authorized": False,
        },
        "disposition": "pass",
        "retained_failures": retained,
        "exit_condition_delta": {
            "expected": [],
            "observed": ["exact blank continuation packet passed public default-branch CI"],
            "decision_value": "enables_dependency",
            "rationale": "Public validation passed without creating a human decision or source-access authority.",
        },
        "next_dependency": "M2-ORBIT-CONTINUATION-001-REVIEW",
    }
    review_unit = {
        "id": "M2-ORBIT-CONTINUATION-001-REVIEW",
        "purpose": "Obtain one exact owner decision on the fixed-order, one-attempt remaining-orbit continuation.",
        "depends_on": ["M2-ORBIT-CONTINUATION-001-REVIEW-PUBLICATION"],
        "action_class": "authority_broadening",
        "human_gate": True,
        "status": "ready",
        "inputs": [PROPOSAL_REF, BUNDLE_REF, CONTRACT_REF, PUBLICATION_REF, TERMINAL_REF],
        "outputs": [
            "records/source-gates/m2-orbit-continuation-001-review-reconciliation.json",
            "records/source-gates/m2-orbit-continuation-001-approval.json",
        ],
        "gates": {
            "proposal_sha256": sha256(PROPOSAL_REF),
            "review_bundle_sha256": sha256(BUNDLE_REF),
            "review_contract_sha256": sha256(CONTRACT_REF),
            "blank_response_sha256": sha256(BLANK_REF),
            "publication_gate_sha256": sha256(PUBLICATION_REF),
            "public_ci": "pass",
            "source_ids_in_exact_order": SOURCE_IDS,
            "maximum_owner_handoffs_if_approved": 1,
            "maximum_real_attempts_per_source_if_approved": 1,
            "stop_on_first_failure_if_approved": True,
            "maximum_endpoint_tolerance_seconds_if_approved": 1.0,
            "human_decision_count": 0,
            "attestation": False,
            "continuation_authorized": False,
        },
        "disposition": None,
        "retained_failures": retained,
        "exit_condition_delta": {
            "expected": [],
            "observed": [],
            "decision_value": "unknown",
            "rationale": "The exact packet is publicly validated and awaits one owner decision.",
        },
        "next_dependency": "M2-ORBIT-CONTINUATION-001-IMPLEMENTATION",
    }
    implementation_unit = {
        "id": "M2-ORBIT-CONTINUATION-001-IMPLEMENTATION",
        "purpose": "If approved, implement and publicly validate only the exact remaining-orbit continuation controls.",
        "depends_on": ["M2-ORBIT-CONTINUATION-001-REVIEW"],
        "action_class": "external_publication",
        "human_gate": False,
        "status": "planned",
        "inputs": ["records/source-gates/m2-orbit-continuation-001-approval.json", PROPOSAL_REF],
        "outputs": [
            "bounded continuation implementation",
            "records/readiness/m2-orbit-continuation-001-implementation-readiness.json",
            "records/readiness/m2-orbit-continuation-001-publication-gate.json",
        ],
        "gates": {
            "public_ci": "required",
            "synthetic_interruption_and_secret_exposure_tests": "required",
            "exact_order_and_stop_on_first_failure_tests": "required",
            "credential_or_source_access_before_public_ci": False,
        },
        "disposition": None,
        "retained_failures": retained,
        "exit_condition_delta": {"expected": [], "observed": [], "decision_value": "unknown", "rationale": "No implementation is authorized before owner approval."},
        "next_dependency": "M2-ORBIT-CONTINUATION-001",
    }
    action_unit = {
        "id": "M2-ORBIT-CONTINUATION-001",
        "purpose": "If every gate passes, request, verify, and conditionally promote the three exact remaining orbit files once each in fixed order.",
        "depends_on": ["M2-ORBIT-CONTINUATION-001-IMPLEMENTATION"],
        "action_class": "data_acquisition",
        "human_gate": False,
        "status": "planned",
        "inputs": ["records/source-gates/m2-orbit-continuation-001-approval.json", INTAKE_REF],
        "outputs": ["external orbit attempt evidence", "records/acquisition remaining-orbit receipts", "terminal reconciliation"],
        "gates": {
            "source_ids_in_exact_order": SOURCE_IDS,
            "maximum_owner_handoffs": 1,
            "maximum_real_attempts_per_source": 1,
            "stop_on_first_failure": True,
            "automatic_retry_authorized": False,
            "m2_orb_001_request_authorized": False,
            "maximum_endpoint_tolerance_seconds": 1.0,
            "public_ci": "required",
            "final_no_payload_preflight": "required",
        },
        "disposition": None,
        "retained_failures": retained,
        "exit_condition_delta": {"expected": ["EXIT-201-VERIFIED-CUSTODY"], "observed": [], "decision_value": "unknown", "rationale": "No source action has been authorized or attempted."},
        "next_dependency": "M2-ORBIT-VERIFY",
    }
    milestone["units"].extend([publication_unit, review_unit, implementation_unit, action_unit])
    orbit_acquire = unit_by_id(milestone, "M2-ORBIT-ACQUIRE")
    orbit_acquire["gates"].update({
        "retained_failure_review": "m2_orb_001_promoted_continuation_001_owner_review_pending",
        "remaining_source_review_ref": CONTRACT_REF,
        "remaining_source_review_bundle_sha256": sha256(BUNDLE_REF),
        "remaining_source_proposal_sha256": sha256(PROPOSAL_REF),
        "remaining_source_requests_authorized_by_current_review": False,
    })
    orbit_acquire["rationale"] = "One exact restituted orbit file is promoted and input-only verified. The publicly validated continuation packet for the other three contains zero decisions and releases no request."
    next_action = (
        f"Review M2 orbit continuation-001 bundle SHA-256 {sha256(BUNDLE_REF)} and proposal SHA-256 {sha256(PROPOSAL_REF)}; "
        "approve, revise, or defer the fixed-order one-attempt continuation. No implementation, credential, live query, payload request, custody mutation, orbit application, DEM or radar-pixel action, baseline, change analysis, attribution, or scientific publication is authorized before an attested decision."
    )
    milestone["handoff"]["current_checkpoint"] = CHECKPOINT
    milestone["handoff"]["next_action"] = next_action
    note = "The continuation-001 packet is blank and publicly validated; it creates no implementation or source-access authority before an exact attested owner decision is locked and reconciled."
    if note not in milestone["handoff"]["do_not_carry_forward"]:
        milestone["handoff"]["do_not_carry_forward"].append(note)
    profile["current_checkpoint"] = {"checkpoint_id": CHECKPOINT, "expected_branch": "main", "expected_head": None, "next_action": next_action}
    gates = profile["gate_policy"]["explicit_human_gates"]
    gates.append({"unit_id": "M2-ORBIT-CONTINUATION-001-REVIEW", "reason": "Records the normative owner decision for the exact three-source continuation and prospective one-second endpoint rule before source access.", "authority_ref": CONTRACT_REF})
    goal["current_checkpoint"] = CHECKPOINT

    nonce = "orbit-continuation-001-review-publication"
    replace_json(MILESTONE_REF, milestone, nonce)
    replace_json(PROFILE_REF, profile, nonce)
    replace_json(GOAL_REF, goal, nonce)
    reconciliation = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ORBIT-CONTINUATION-001-REVIEW-PUBLICATION-RECONCILIATION",
        "reconciled_at_utc": args.published_at_utc,
        "status": "pass_exact_public_packet_owner_review_ready_zero_decisions",
        "bindings": {
            "publication_gate_sha256": sha256(PUBLICATION_REF),
            "proposal_sha256": sha256(PROPOSAL_REF),
            "review_bundle_sha256": sha256(BUNDLE_REF),
            "review_contract_sha256": sha256(CONTRACT_REF),
            "blank_response_sha256": sha256(BLANK_REF),
            "milestone_sha256_before": before["milestone"],
            "milestone_sha256_after": sha256(MILESTONE_REF),
            "profile_sha256_before": before["profile"],
            "profile_sha256_after": sha256(PROFILE_REF),
            "goal_sha256_before": before["goal"],
            "goal_sha256_after": sha256(GOAL_REF),
        },
        "review": {"human_decision_count": 0, "attestation": False, "continuation_authorized": False},
        "assertions": {
            "public_ci_conclusion": "success",
            "implementation_started": False,
            "credential_values_read_or_recorded": False,
            "orbit_network_or_payload_request_performed_by_reconciliation": False,
            "external_data_mutated": False,
            "m2_orb_001_mutated": False,
            "scientific_result_established": False,
        },
        "current_checkpoint": CHECKPOINT,
        "next_action": next_action,
    }
    write_new(RECONCILIATION_REF, reconciliation)
    print(json.dumps({
        "status": reconciliation["status"],
        "publication_gate_sha256": sha256(PUBLICATION_REF),
        "reconciliation_sha256": sha256(RECONCILIATION_REF),
        "checkpoint": CHECKPOINT,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
