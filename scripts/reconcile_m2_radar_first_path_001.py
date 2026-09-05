#!/usr/bin/env python3
"""Reconcile the approved radar-first route into active project controls."""

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
APPROVAL_REF = "records/source-gates/m2-radar-first-path-001-approval.json"
ACTIVATION_REF = "records/readiness/m2-radar-first-path-001-activation.json"
OPTICAL_REF = "records/readiness/m2-optical-route-disposition-001.json"
RADAR_REF = "records/readiness/m2-radar-source-readiness-001.json"
STALE_REF = "records/readiness/m2-orbit-recovery-001-stale-evidence.json"
PROPOSAL_REF = "contracts/milestone-002-radar-first-path-001-proposal.json"
RECONCILIATION_REF = "records/source-gates/m2-radar-first-path-001-review-reconciliation.json"
ORBIT_PROPOSAL_REF = "contracts/milestone-002-orbit-recovery-002-proposal.json"
ORBIT_BUNDLE_REF = "reviews/m2-orbit-recovery-002/review-bundle.json"
ORBIT_CONTRACT_REF = "reviews/m2-orbit-recovery-002/review-contract.json"
ORBIT_BLANK_REF = "reviews/m2-orbit-recovery-002/blank-response.json"
ORBIT_READINESS_REF = "records/readiness/m2-orbit-recovery-002-review-readiness.json"
CONTROL_REF = "records/readiness/m2-radar-first-path-001-control-reconciliation.json"


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


def replace_json(ref: str, value: dict[str, Any]) -> None:
    path = ROOT / ref
    temporary = path.with_name(path.name + ".radar-first-001-tmp")
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

    approval = load(APPROVAL_REF)
    activation = load(ACTIVATION_REF)
    radar = load(RADAR_REF)
    stale = load(STALE_REF)
    orbit_proposal = load(ORBIT_PROPOSAL_REF)
    orbit_bundle = load(ORBIT_BUNDLE_REF)
    orbit_contract = load(ORBIT_CONTRACT_REF)
    orbit_blank = load(ORBIT_BLANK_REF)
    orbit_readiness = load(ORBIT_READINESS_REF)
    if approval.get("status") != "approved_control_route_split_and_corrected_review_preparation_only":
        raise SystemExit("radar-first approval identity drift")
    if activation.get("status") != "pass_control_route_split_and_corrected_review_preparation_only":
        raise SystemExit("radar-first activation identity drift")
    if radar.get("status") != "pass_six_source_custody_materialization_and_header_readiness_only":
        raise SystemExit("radar source readiness is not passing")
    if stale.get("status") != "stale_unapproved_preserved_not_actionable":
        raise SystemExit("old orbit review is not preserved as stale evidence")
    if orbit_proposal.get("status") != "proposed_not_authorized":
        raise SystemExit("corrected orbit proposal is not blank authority")
    if orbit_blank.get("completed") is not False or orbit_blank.get("reviewer", {}).get("attestation") is not False:
        raise SystemExit("corrected orbit response is not blank")
    if orbit_blank.get("responses", [{}])[0].get("decision") is not None:
        raise SystemExit("corrected orbit response contains a decision")
    if orbit_readiness.get("review", {}).get("human_decision_count") != 0:
        raise SystemExit("corrected orbit readiness contains a human decision")

    milestone = load(MILESTONE_REF)
    profile = load(PROFILE_REF)
    goal = load(GOAL_REF)
    if milestone.get("handoff", {}).get("current_checkpoint") != "M2-RADAR-FIRST-PATH-001-REVIEW":
        raise SystemExit("active milestone checkpoint drift")
    if profile.get("current_checkpoint", {}).get("checkpoint_id") != "M2-RADAR-FIRST-PATH-001-REVIEW":
        raise SystemExit("project profile checkpoint drift")
    if goal.get("current_checkpoint") != "M2-RADAR-FIRST-PATH-001-REVIEW":
        raise SystemExit("goal checkpoint drift")

    control = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-FIRST-PATH-001-CONTROL-RECONCILIATION",
        "reconciled_at_utc": args.reconciled_at_utc,
        "status": "pass_route_split_and_corrected_orbit_review_ready",
        "bindings": {
            "approval_ref": APPROVAL_REF,
            "approval_sha256": sha256(APPROVAL_REF),
            "activation_ref": ACTIVATION_REF,
            "activation_sha256": sha256(ACTIVATION_REF),
            "review_reconciliation_ref": RECONCILIATION_REF,
            "review_reconciliation_sha256": sha256(RECONCILIATION_REF),
            "optical_route_disposition_ref": OPTICAL_REF,
            "optical_route_disposition_sha256": sha256(OPTICAL_REF),
            "radar_source_readiness_ref": RADAR_REF,
            "radar_source_readiness_sha256": sha256(RADAR_REF),
            "stale_orbit_packet_ref": STALE_REF,
            "stale_orbit_packet_sha256": sha256(STALE_REF),
            "corrected_orbit_proposal_ref": ORBIT_PROPOSAL_REF,
            "corrected_orbit_proposal_sha256": sha256(ORBIT_PROPOSAL_REF),
            "corrected_orbit_bundle_ref": ORBIT_BUNDLE_REF,
            "corrected_orbit_bundle_sha256": sha256(ORBIT_BUNDLE_REF),
            "corrected_orbit_contract_ref": ORBIT_CONTRACT_REF,
            "corrected_orbit_contract_sha256": sha256(ORBIT_CONTRACT_REF),
            "corrected_orbit_blank_response_ref": ORBIT_BLANK_REF,
            "corrected_orbit_blank_response_sha256": sha256(ORBIT_BLANK_REF),
        },
        "route_states": {
            "optical": "terminal_block_preserved",
            "radar_source": "pass_custody_materialization_header_only",
            "aggregate_m2_verify": "deferred",
        },
        "assertions": {
            "old_orbit_proposal_and_bundle_preserved": True,
            "corrected_orbit_human_decision_count": 0,
            "orbit_recovery_authorized": False,
            "dem_action_authorized": False,
            "radar_pixel_readiness_authorized": False,
            "optical_retry_or_alternate_route_authorized": False,
            "network_requests_performed": False,
            "credential_values_read_or_recorded": False,
            "external_data_mutated": False,
            "real_product_pixels_examined": False,
            "baseline_or_change_analysis_performed": False,
        },
    }
    write_new(CONTROL_REF, control)
    control_sha = sha256(CONTROL_REF)

    review = unit_by_id(milestone, "M2-RADAR-FIRST-PATH-001-REVIEW")
    review["status"] = "complete"
    review["outputs"] = [RECONCILIATION_REF, APPROVAL_REF, ACTIVATION_REF, CONTROL_REF]
    review["gates"].update({
        "human_decision_count": 1,
        "attestation": True,
        "control_amendment_authorized": True,
        "approval_ref": APPROVAL_REF,
        "approval_sha256": sha256(APPROVAL_REF),
        "review_reconciliation_ref": RECONCILIATION_REF,
        "review_reconciliation_sha256": sha256(RECONCILIATION_REF),
        "activation_ref": ACTIVATION_REF,
        "activation_sha256": sha256(ACTIVATION_REF),
        "control_reconciliation_ref": CONTROL_REF,
        "control_reconciliation_sha256": control_sha,
    })
    review["disposition"] = "pass"
    review["exit_condition_delta"] = {
        "expected": [],
        "observed": [],
        "decision_value": "enables_dependency",
        "rationale": "One exact attested approval releases only the route-specific control correction and preparation of a corrected blank orbit-recovery review.",
    }
    review["next_dependency"] = "M2-RADAR-SOURCE-READINESS"

    optical = unit_by_id(milestone, "M2-OPTICAL-PIXEL-RECOVERY-001")
    optical["next_dependency"] = "M2-OPTICAL-ROUTE-DISPOSITION"
    add_unique_unit(milestone, {
        "id": "M2-OPTICAL-ROUTE-DISPOSITION",
        "purpose": "Preserve the exact terminal optical INVALID and BLOCK outcomes without retry, tuning, date shopping, or source substitution.",
        "depends_on": ["M2-OPTICAL-PIXEL-RECOVERY-001"],
        "action_class": "project_control",
        "human_gate": False,
        "status": "complete",
        "inputs": ["records/readiness/m2-optical-pixel-real-001-reconciliation.json", "records/readiness/m2-optical-pixel-recovery-001-reconciliation.json", APPROVAL_REF],
        "outputs": [OPTICAL_REF],
        "gates": {"disposition_ref": OPTICAL_REF, "disposition_sha256": sha256(OPTICAL_REF), "retry_authorized": False, "alternate_route_authorized": False},
        "disposition": "block",
        "retained_failures": ["records/readiness/m2-optical-pixel-real-001-reconciliation.json", "records/readiness/m2-optical-pixel-recovery-001-reconciliation.json"],
        "exit_condition_delta": {"expected": ["EXIT-202-PIXEL-AND-RIGHTS-QA", "EXIT-204-REGISTRATION-QA"], "observed": [], "decision_value": "block", "rationale": "The only approved optical recovery is consumed and terminal BLOCK; the branch remains evidence rather than being reclassified."},
        "next_dependency": "M2-VERIFY",
    })
    review["depends_on"] = ["M2-OPTICAL-ROUTE-DISPOSITION"]

    add_unique_unit(milestone, {
        "id": "M2-RADAR-SOURCE-READINESS",
        "purpose": "Bind the six exact Sentinel-1 sources to promoted custody, materialization identity, and passing header readiness without decoding measurement pixels.",
        "depends_on": ["M2-FULL-INPUT-READINESS", "M2-RADAR-FIRST-PATH-001-REVIEW"],
        "action_class": "project_control",
        "human_gate": False,
        "status": "complete",
        "inputs": ["records/acquisition/sentinel-continuation-001-postsuccess-reconciliation.json", "records/acquisition/sentinel-materialization-reconciliation-002.json", "records/readiness/m2-full-header-readiness-reconciliation.json", "records/readiness/radar-input/m2-s1-input-readiness-real-003.json", APPROVAL_REF],
        "outputs": [RADAR_REF],
        "gates": {"readiness_ref": RADAR_REF, "readiness_sha256": sha256(RADAR_REF), "source_count": 6, "measurement_pixels_decoded": False, "orbit_amendment_approval": "active_exact"},
        "disposition": "pass",
        "retained_failures": [],
        "exit_condition_delta": {"expected": ["EXIT-201-VERIFIED-CUSTODY"], "observed": ["EXIT-201-VERIFIED-CUSTODY", "six-source materialization identity", "six-source header readiness"], "decision_value": "enables_dependency", "rationale": "All six exact radar sources pass custody, materialization, and header-only readiness; pixel, orbit, DEM, and terrain fitness remain separate."},
        "next_dependency": "M2-ORBIT-RECOVERY-002-REVIEW",
    })

    verify = unit_by_id(milestone, "M2-VERIFY")
    verify["depends_on"] = ["M2-ACQUIRE", "M2-OPTICAL-ROUTE-DISPOSITION", "M2-RADAR-SOURCE-READINESS"]
    for output in (OPTICAL_REF, RADAR_REF):
        if output not in verify["outputs"]:
            verify["outputs"].append(output)
    verify["gates"].update({
        "materialization_and_pixel_readiness": "route_split_optical_terminal_block_radar_source_header_ready_aggregate_deferred",
        "optical_route_disposition_ref": OPTICAL_REF,
        "optical_route_disposition_sha256": sha256(OPTICAL_REF),
        "radar_source_readiness_ref": RADAR_REF,
        "radar_source_readiness_sha256": sha256(RADAR_REF),
        "radar_first_control_reconciliation_ref": CONTROL_REF,
        "radar_first_control_reconciliation_sha256": control_sha,
    })
    verify["next_dependency"] = None

    add_unique_unit(milestone, {
        "id": "M2-ORBIT-RECOVERY-002-REVIEW",
        "purpose": "Obtain one exact owner decision on a corrected recovery-only implementation and at most one future byte-zero M2-ORB-001 attempt.",
        "depends_on": ["M2-RADAR-SOURCE-READINESS", "M2-ORBIT-PREFLIGHT"],
        "action_class": "authority_broadening",
        "human_gate": True,
        "status": "ready",
        "inputs": [ORBIT_PROPOSAL_REF, ORBIT_BUNDLE_REF, ORBIT_CONTRACT_REF, RADAR_REF, STALE_REF],
        "outputs": ["records/source-gates/m2-orbit-recovery-002-review-reconciliation.json", "records/source-gates/m2-orbit-recovery-002-approval.json"],
        "gates": {"proposal_sha256": sha256(ORBIT_PROPOSAL_REF), "review_bundle_sha256": sha256(ORBIT_BUNDLE_REF), "review_contract_sha256": sha256(ORBIT_CONTRACT_REF), "blank_response_sha256": sha256(ORBIT_BLANK_REF), "human_decision_count": 0, "attestation": False, "recovery_authorized": False, "maximum_future_attempts_if_approved": 1, "other_orbit_source_requests_authorized_by_this_review": False},
        "disposition": None,
        "retained_failures": ["records/acquisition/orbit-attempts/m2-orb-001-20260904t050937z-8ed21d05.json", STALE_REF],
        "exit_condition_delta": {"expected": [], "observed": [], "decision_value": "awaiting_owner_decision", "rationale": "The corrected packet is blank and creates no recovery, credential, catalogue, or payload authority."},
        "next_dependency": None,
    })
    add_unique_unit(milestone, {
        "id": "M2-ORBIT-RECOVERY-002-IMPLEMENTATION",
        "purpose": "If separately approved, implement and publicly validate the exact recovery-only worker before any real access.",
        "depends_on": ["M2-ORBIT-RECOVERY-002-REVIEW"],
        "action_class": "external_publication",
        "human_gate": False,
        "status": "planned",
        "inputs": [], "outputs": [], "gates": {"public_ci": "required", "final_no_payload_preflight": "required_after_public_ci"},
        "disposition": None, "retained_failures": [],
        "exit_condition_delta": {"expected": [], "observed": [], "decision_value": "unknown", "rationale": "No approval or recovery implementation exists."},
        "next_dependency": "M2-ORBIT-RECOVERY-002",
    })
    add_unique_unit(milestone, {
        "id": "M2-ORBIT-RECOVERY-002",
        "purpose": "If every later gate passes, perform at most one fresh byte-zero attempt for exact M2-ORB-001 under a distinct identity.",
        "depends_on": ["M2-ORBIT-RECOVERY-002-IMPLEMENTATION"],
        "action_class": "data_acquisition",
        "human_gate": False,
        "status": "planned",
        "inputs": [], "outputs": [], "gates": {"maximum_real_attempts": 1, "automatic_retry_authorized": False, "source_id": "M2-ORB-001", "other_orbit_source_requests_authorized_by_this_unit": False},
        "disposition": None, "retained_failures": ["records/acquisition/orbit-attempts/m2-orb-001-20260904t050937z-8ed21d05.json"],
        "exit_condition_delta": {"expected": ["EXIT-201-VERIFIED-CUSTODY"], "observed": [], "decision_value": "unknown", "rationale": "The corrected review has zero decisions and no recovery attempt is authorized."},
        "next_dependency": "M2-ORBIT-ACQUIRE",
    })

    orbit_acquire = unit_by_id(milestone, "M2-ORBIT-ACQUIRE")
    orbit_acquire["depends_on"] = ["M2-ORBIT-PREFLIGHT", "M2-RADAR-SOURCE-READINESS", "M2-ORBIT-RECOVERY-002"]
    orbit_acquire["gates"].update({
        "matching_sentinel_promoted_and_verified": "six_radar_sources_promoted_materialized_and_header_ready_only",
        "radar_source_readiness": "complete",
        "radar_source_readiness_ref": RADAR_REF,
        "radar_source_readiness_sha256": sha256(RADAR_REF),
        "superseded_milestone_dependency_m2_verify": "preserved_in_stale_unapproved_orbit_packet_only",
        "retained_failure_review": "corrected_review_ready_zero_decisions",
        "retained_failure_review_ref": ORBIT_CONTRACT_REF,
        "retained_failure_review_bundle_sha256": sha256(ORBIT_BUNDLE_REF),
        "retained_failure_recovery_proposal_sha256": sha256(ORBIT_PROPOSAL_REF),
        "orbit_recovery_002_status": "planned_not_authorized",
    })
    orbit_acquire["gates"].pop("milestone_dependency_m2_verify", None)
    orbit_acquire["exit_condition_delta"]["rationale"] = "The route-specific Sentinel prerequisite now passes, but the corrected recovery review is blank and no orbit catalogue, token, or payload action is released."
    orbit_acquire["rationale"] = "Orbit acquisition remains deferred until the corrected M2-ORB-001 review, implementation, public CI, no-payload preflight, and one-attempt recovery all pass; DEM and radar-pixel gates remain separate."

    amendment = {
        "approval_ref": APPROVAL_REF,
        "approval_sha256": sha256(APPROVAL_REF),
        "proposal_ref": PROPOSAL_REF,
        "proposal_sha256": sha256(PROPOSAL_REF),
        "review_bundle_sha256": "5a5bd80f724841f9558ad5ff966ed0d49222419f7310b345492172e4639421ad",
        "control_reconciliation_ref": CONTROL_REF,
        "control_reconciliation_sha256": control_sha,
        "optical_route_status": "terminal_block_preserved",
        "radar_source_status": "pass_header_readiness_only",
        "orbit_recovery_authorized": False,
    }
    milestone["authority"].setdefault("amendments", []).append(amendment)
    profile["authority"].setdefault("amendments", []).append(amendment)
    milestone["scope"]["active_amendments"].append(APPROVAL_REF)
    next_action = f"Review corrected M2 orbit recovery-002 bundle SHA-256 {sha256(ORBIT_BUNDLE_REF)} and proposal SHA-256 {sha256(ORBIT_PROPOSAL_REF)}; approve, revise, or defer one recovery-only implementation and at most one future byte-zero M2-ORB-001 attempt. No orbit, token, DEM, radar-pixel, baseline, change, or scientific action is authorized before an attested decision."
    milestone["handoff"]["current_checkpoint"] = "M2-ORBIT-RECOVERY-002-REVIEW"
    milestone["handoff"]["next_action"] = next_action
    milestone["handoff"]["do_not_carry_forward"].extend([
        "The approved radar-first amendment preserves optical real-001 as INVALID and recovery-001 as terminal BLOCK; it does not authorize retry, tuning, alternate dates, or source substitution.",
        "The old orbit-recovery proposal and bundle remain immutable stale evidence and are not actionable.",
        "The corrected orbit-recovery-002 review is blank and authorizes no catalogue access, token lookup, payload request, DEM action, radar pixel read, baseline, change analysis, or scientific publication.",
    ])

    controls = profile["control_surfaces"]
    controls["proposed_amendments"] = [ORBIT_PROPOSAL_REF]
    controls["activated_amendments"].append(APPROVAL_REF)
    profile["current_checkpoint"] = {"checkpoint_id": "M2-ORBIT-RECOVERY-002-REVIEW", "expected_branch": "main", "expected_head": None, "next_action": next_action}
    explicit = profile["gate_policy"]["explicit_human_gates"]
    explicit.append({"unit_id": "M2-ORBIT-RECOVERY-002-REVIEW", "reason": "Would authorize only a recovery-only implementation, public-CI gate, final no-payload preflight, and at most one fresh byte-zero attempt for exact M2-ORB-001.", "authority_ref": ORBIT_CONTRACT_REF})

    goal["current_checkpoint"] = "M2-ORBIT-RECOVERY-002-REVIEW"
    goal["proposed_amendments"] = [ORBIT_PROPOSAL_REF]
    goal["active_amendments"].append(APPROVAL_REF)

    replace_json(MILESTONE_REF, milestone)
    replace_json(PROFILE_REF, profile)
    replace_json(GOAL_REF, goal)
    print(json.dumps({"status": "reconciled_route_split_and_corrected_review", "control_sha256": control_sha, "orbit_proposal_sha256": sha256(ORBIT_PROPOSAL_REF), "orbit_bundle_sha256": sha256(ORBIT_BUNDLE_REF)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
