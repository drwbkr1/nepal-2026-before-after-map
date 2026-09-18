#!/usr/bin/env python3
"""Activate the exact approved radar pixel and orbit application route through public CI only."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path(r"C:\Projects\Active\nepal-2026-before-after-map-data")
PROPOSAL_REF = "contracts/milestone-002-radar-pixel-orbit-application-001-proposal.json"
PROPOSAL_SHA256 = "3a0f03c5269f4e3e6822c1e31bbe5f19cd288e9e17db67b42990d96b27a4f490"
BUNDLE_REF = "reviews/m2-radar-pixel-orbit-application-001/review-bundle.json"
BUNDLE_SHA256 = "84af38b7e325e862272b97c9f198dc7a3c3aa2371f4c428e36aaaac6e937f633"
CONTRACT_REF = "reviews/m2-radar-pixel-orbit-application-001/review-contract.json"
CONTRACT_SHA256 = "cf846f8749052c172576c1e03fb46885a0795076beb16d604fcefe6c51b935a7"
PUBLICATION_REF = "records/readiness/m2-radar-pixel-orbit-application-001-review-publication-gate.json"
RECONCILIATION_REF = "records/source-gates/m2-radar-pixel-orbit-application-001-review-reconciliation.json"
RECONCILIATION_SHA256 = "cdb32247348c7e065103434c5b788c4d7ea4cf5356d64a5d2d4d5fbd3014dc4e"
RESPONSE_SHA256 = "49807e5113a9dc4beec16ae23631f4039e066f1713b338055adc24ee71240369"
RECEIPT_SHA256 = "75c0abd1fd237bbc092176b8faf4e094bd5b69e61f428a70f5108d608155de0b"
LOCKED_ROOT = DATA_ROOT / "private-review-responses/m2-radar-pixel-orbit-application-001/locked"
RESPONSE = LOCKED_ROOT / f"m2-radar-pixel-orbit-application-001-review-response-{RESPONSE_SHA256[:16]}.json"
RECEIPT = LOCKED_ROOT / f"m2-radar-pixel-orbit-application-001-review-receipt-{RESPONSE_SHA256[:16]}.json"
APPROVAL_REF = "records/source-gates/m2-radar-pixel-orbit-application-001-approval.json"
ACTIVATION_REF = "records/readiness/m2-radar-pixel-orbit-application-001-approval-activation.json"
MILESTONE_REF = "contracts/milestone-002.json"
PROFILE_REF = "records/project-control-profile.json"
GOAL_REF = "records/long-term-goal.json"
REVIEW_UNIT = "M2-RADAR-PIXEL-ORBIT-APPLICATION-001-REVIEW"
IMPLEMENTATION_UNIT = "M2-RADAR-PIXEL-ORBIT-APPLICATION-001-IMPLEMENTATION"
EXECUTION_UNIT = "M2-RADAR-PIXEL-ORBIT-APPLICATION-001-EXECUTION"
NEXT_ACTION = (
    "Implement and validate only the exact approved six-source route, synthetic controls, and ArcGIS-runtime tests, "
    "then require successful public default-branch CI. Do not run the final preflight, read project pixels, apply "
    "an orbit, or create a real processing attempt before that public gate."
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return value


def canonical(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def replace_json(path: Path, value: object, nonce: str) -> None:
    temporary = path.with_name(f".{path.name}.{nonce}.tmp")
    if temporary.exists():
        raise ValueError(f"temporary collision: {temporary}")
    with temporary.open("xb") as stream:
        stream.write(canonical(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def unit(milestone: dict[str, Any], unit_id: str) -> dict[str, Any]:
    matches = [item for item in milestone.get("units", []) if item.get("id") == unit_id]
    if len(matches) != 1:
        raise ValueError(f"unit missing or ambiguous: {unit_id}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activated-at-utc", required=True)
    args = parser.parse_args()
    if not args.activated_at_utc.endswith("Z"):
        raise SystemExit("activation timestamp must be UTC")
    exact = {
        ROOT / PROPOSAL_REF: PROPOSAL_SHA256,
        ROOT / BUNDLE_REF: BUNDLE_SHA256,
        ROOT / CONTRACT_REF: CONTRACT_SHA256,
        ROOT / RECONCILIATION_REF: RECONCILIATION_SHA256,
        RESPONSE: RESPONSE_SHA256,
        RECEIPT: RECEIPT_SHA256,
    }
    if any(not item.is_file() or sha(item) != expected for item, expected in exact.items()):
        raise SystemExit("approval input identity drift or missing locked response")
    publication = load(ROOT / PUBLICATION_REF)
    response = load(RESPONSE)
    receipt = load(RECEIPT)
    reconciliation = load(ROOT / RECONCILIATION_REF)
    if (
        publication.get("status") != "pass_public_default_branch_ci_zero_decision_review_ready"
        or publication.get("public_ci_conclusion") != "success"
        or response.get("review_id") != "m2-radar-pixel-orbit-application-001-review"
        or response.get("completed") is not True
        or response.get("reviewer", {}).get("attestation") is not True
        or response.get("responses", [{}])[0].get("item_id") != "M2-RADAR-PIXEL-ORBIT-APPLICATION-001"
        or response.get("responses", [{}])[0].get("evidence_sha256") != BUNDLE_SHA256
        or response.get("responses", [{}])[0].get("decision") != "approve"
        or receipt.get("response_sha256") != RESPONSE_SHA256
        or receipt.get("contract_sha256") != CONTRACT_SHA256
        or reconciliation.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}
        or reconciliation.get("human_decisions_fabricated") is not False
    ):
        raise SystemExit("locked response is not the exact attested approval")

    proposal = load(ROOT / PROPOSAL_REF)
    approval = {
        "schema_version": "1.0",
        "approval_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-001-APPROVAL",
        "status": "approved_dependency_ordered_exact_six_source_qa_route",
        "approved_at_utc": response["review_completed_at_utc"],
        "review_id": response["review_id"],
        "review_bundle_manifest_sha256": BUNDLE_SHA256,
        "proposal_ref": PROPOSAL_REF,
        "proposal_sha256": PROPOSAL_SHA256,
        "review_contract_ref": CONTRACT_REF,
        "review_contract_sha256": CONTRACT_SHA256,
        "review_reconciliation_ref": RECONCILIATION_REF,
        "review_reconciliation_sha256": RECONCILIATION_SHA256,
        "locked_response_sha256": RESPONSE_SHA256,
        "lock_receipt_sha256": RECEIPT_SHA256,
        "human_decision_count": 1,
        "decision_counts": {"approve": 1, "revise": 0, "defer": 0},
        "attestation": True,
        "authorized_bounded_actions": copy.deepcopy(proposal["proposed_bounded_actions"]),
        "fixed_sequence": copy.deepcopy(proposal["fixed_sequence"]),
        "limits": copy.deepcopy(proposal["limits"]),
        "does_not_authorize": copy.deepcopy(proposal["does_not_authorize"]),
        "claim_boundary": copy.deepcopy(proposal["claim_boundary"]),
        "human_decisions_fabricated": False,
    }
    approval_bytes = canonical(approval)
    approval_sha = hashlib.sha256(approval_bytes).hexdigest()
    activation = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-001-APPROVAL-ACTIVATION",
        "activated_at_utc": args.activated_at_utc,
        "status": "pass_exact_approval_activated_implementation_publication_only",
        "bindings": {
            "approval_ref": APPROVAL_REF,
            "approval_sha256": approval_sha,
            "reconciliation_sha256": RECONCILIATION_SHA256,
            "proposal_sha256": PROPOSAL_SHA256,
            "review_bundle_sha256": BUNDLE_SHA256,
        },
        "released_now": {
            "bounded_implementation": True,
            "synthetic_tests": True,
            "arcgis_runtime_tests": True,
            "public_ci": True,
            "final_no_content_preflight": False,
            "project_data_content_read": False,
            "orbit_application": False,
            "radar_pixel_processing": False,
            "route_qa": False,
            "baseline_or_change_analysis": False,
            "scientific_publication": False,
        },
        "assertions": {
            "network_requests_performed": False,
            "credential_values_read": False,
            "external_data_mutated": False,
            "project_pixels_read": False,
            "scientific_result_established": False,
        },
    }
    outputs = {APPROVAL_REF: approval_bytes, ACTIVATION_REF: canonical(activation)}
    collisions = [ref for ref in outputs if (ROOT / ref).exists()]
    if collisions:
        raise SystemExit("refusing output collision: " + ", ".join(collisions))

    milestone_path, profile_path, goal_path = ROOT / MILESTONE_REF, ROOT / PROFILE_REF, ROOT / GOAL_REF
    milestone, profile, goal = load(milestone_path), load(profile_path), load(goal_path)
    review = unit(milestone, REVIEW_UNIT)
    if (
        review.get("status") != "in_progress"
        or review.get("gates", {}).get("public_ci") != "success"
        or review.get("gates", {}).get("human_decision_count") != 0
        or any(item.get("id") in {IMPLEMENTATION_UNIT, EXECUTION_UNIT} for item in milestone.get("units", []))
    ):
        raise SystemExit("project is not at the exact zero-decision review checkpoint")

    for ref, payload in outputs.items():
        write_new(ROOT / ref, payload)
    review.update({"status": "complete", "disposition": "pass"})
    review["outputs"] = [RECONCILIATION_REF, APPROVAL_REF, ACTIVATION_REF]
    review["gates"].update({
        "human_decision_count": 1,
        "attestation": True,
        "route_authorized": True,
        "approval_sha256": approval_sha,
        "review_reconciliation_sha256": RECONCILIATION_SHA256,
    })
    review["exit_condition_delta"] = {
        "expected": [],
        "observed": ["one exact attested approval"],
        "decision_value": "enables_dependency",
        "rationale": "Only implementation, synthetic and ArcGIS-runtime tests, and public CI are released now.",
    }
    milestone["units"].extend([
        {
            "id": IMPLEMENTATION_UNIT,
            "purpose": "Implement and publicly validate the exact six-source append-only orbit application and QA route without reading project pixels.",
            "depends_on": [REVIEW_UNIT],
            "action_class": "routine_qa",
            "human_gate": False,
            "status": "in_progress",
            "inputs": [APPROVAL_REF, PROPOSAL_REF, RECONCILIATION_REF],
            "outputs": [
                "scripts/m2_radar_pixel_orbit_application_001_core.py",
                "scripts/run_m2_radar_pixel_orbit_application_001.py",
                "scripts/validate_m2_radar_pixel_orbit_application_001_arcgis.py",
                "tests/test_m2_radar_pixel_orbit_application_001.py",
                "records/readiness/m2-radar-pixel-orbit-application-001-implementation-readiness.json",
                "records/readiness/m2-radar-pixel-orbit-application-001-implementation-publication-gate.json"
            ],
            "gates": {
                "approval_sha256": approval_sha,
                "public_ci": "pending",
                "final_no_content_preflight": False,
                "project_data_content_read": False,
                "orbit_application_started": False,
                "radar_pixel_processing_started": False
            },
            "disposition": None,
            "retained_failures": ["records/readiness/m2-radar-pixel-orbit-application-001-review-lock-attempt-001-failure.json"],
            "exit_condition_delta": {"expected": ["portable and ArcGIS runtime tests pass", "public CI succeeds"], "observed": ["approval locked and reconciled"], "decision_value": "unknown", "rationale": "Implementation is active; all real data actions remain blocked."},
            "next_dependency": EXECUTION_UNIT
        },
        {
            "id": EXECUTION_UNIT,
            "purpose": "Run one final no-content preflight and, only on pass, process six exact sources once and evaluate two exact routes under the frozen QA contract.",
            "depends_on": [IMPLEMENTATION_UNIT],
            "action_class": "routine_qa",
            "human_gate": False,
            "status": "planned",
            "inputs": [APPROVAL_REF, PROPOSAL_REF],
            "outputs": [
                "records/readiness/m2-radar-pixel-orbit-application-001-final-preflight.json",
                "records/processing/m2-radar-pixel-orbit-application-001-terminal-reconciliation.json"
            ],
            "gates": {
                "public_ci": "blocked_by_implementation",
                "final_no_content_preflight": "pending_after_public_ci",
                "source_attempts_started": 0,
                "automatic_retry": False,
                "baseline_or_change_authorized": False
            },
            "disposition": None,
            "retained_failures": [],
            "exit_condition_delta": {"expected": ["six terminal source dispositions", "two independent route QA dispositions"], "observed": [], "decision_value": "unknown", "rationale": "Execution remains blocked by implementation and public CI."},
            "next_dependency": "M2-ORBIT-APPLY"
        }
    ])
    amendment = {
        "approval_ref": APPROVAL_REF,
        "approval_sha256": approval_sha,
        "proposal_ref": PROPOSAL_REF,
        "proposal_sha256": PROPOSAL_SHA256,
        "review_bundle_sha256": BUNDLE_SHA256,
        "review_reconciliation_ref": RECONCILIATION_REF,
        "review_reconciliation_sha256": RECONCILIATION_SHA256,
        "source_ids_in_exact_order": copy.deepcopy(proposal["fixed_sequence"]["source_ids"]),
        "route_ids_in_exact_order": copy.deepcopy(proposal["fixed_sequence"]["route_ids"]),
        "maximum_orbit_application_attempts_per_source": 1,
        "maximum_qa_processing_attempts_per_source": 1,
        "maximum_route_qa_attempts_per_pair": 1,
        "network_requests_authorized": 0,
        "automatic_retry_authorized": False,
    }
    for authority in (milestone["authority"], profile["authority"]):
        authority["amendments"].append(copy.deepcopy(amendment))
    milestone["scope"]["active_amendments"].append(APPROVAL_REF)
    profile["control_surfaces"]["proposed_amendments"] = []
    profile["control_surfaces"]["activated_amendments"].append(APPROVAL_REF)
    goal["proposed_amendments"] = []
    goal["active_amendments"].append(APPROVAL_REF)
    gate = [item for item in profile["gate_policy"]["explicit_human_gates"] if item.get("unit_id") == REVIEW_UNIT]
    if len(gate) != 1:
        raise SystemExit("profile review gate missing or ambiguous")
    gate[0].update({"authority_ref": APPROVAL_REF, "reason": "The exact owner approval authorizes only the bounded fixed-order six-source QA route and its dependency gates."})
    milestone["handoff"].update({"current_checkpoint": IMPLEMENTATION_UNIT, "next_action": NEXT_ACTION, "parallel_checkpoint": IMPLEMENTATION_UNIT, "parallel_next_action": NEXT_ACTION})
    profile["current_checkpoint"] = {"checkpoint_id": IMPLEMENTATION_UNIT, "expected_branch": "main", "expected_head": None, "next_action": NEXT_ACTION}
    profile["parallel_checkpoints"] = [{"checkpoint_id": IMPLEMENTATION_UNIT, "authority_ref": APPROVAL_REF, "next_action": NEXT_ACTION}]
    goal["current_checkpoint"] = IMPLEMENTATION_UNIT
    goal["parallel_checkpoints"] = [IMPLEMENTATION_UNIT]
    nonce = "m2-radar-pixel-orbit-application-001"
    replace_json(milestone_path, milestone, nonce)
    replace_json(profile_path, profile, nonce)
    replace_json(goal_path, goal, nonce)
    print(json.dumps({"status": "activated_implementation_publication_only", "approval_sha256": approval_sha, "current_checkpoint": IMPLEMENTATION_UNIT}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
