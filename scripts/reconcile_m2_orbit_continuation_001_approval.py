#!/usr/bin/env python3
"""Reconcile the exact orbit continuation approval into implementation-only controls."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "contracts/milestone-002.json"
PROFILE = ROOT / "records/project-control-profile.json"
GOAL = ROOT / "records/long-term-goal.json"
APPROVAL_REF = "records/source-gates/m2-orbit-continuation-001-approval.json"
APPROVAL_SHA256 = "66c40db57082ed29c1dfd3e00a163ab072fe9f14b8e0ed4455df188673de84ba"
RECONCILIATION_REF = "records/source-gates/m2-orbit-continuation-001-review-reconciliation.json"
RECONCILIATION_SHA256 = "11e29c1e6a259201b745b802f59219234e4bfec2433f1caf909f2202e3b9f0fa"
ACTIVATION_REF = "records/readiness/m2-orbit-continuation-001-approval-activation.json"
ACTIVATION_SHA256 = "c3a0751b5c51de24ef94a694f6e8c522088d159b5303c1c5a0fb24a044c1626c"
OUTPUT = ROOT / "records/readiness/m2-orbit-continuation-001-approval-reconciliation.json"
CHECKPOINT = "M2-ORBIT-CONTINUATION-001-IMPLEMENTATION"
NEXT_ACTION = (
    "Implement and synthetically validate only the approved fixed-order M2-ORB-002, M2-ORB-003, and M2-ORB-004 "
    "continuation, then require successful public default-branch CI. No credential, catalog, payload, orbit application, "
    "DEM, radar-pixel, baseline, change, attribution, or scientific-publication action is released before that gate."
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return value


def write_new(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def replace(path: Path, value: dict[str, Any], nonce: str) -> None:
    temporary = path.with_name(f".{path.name}.{nonce}.tmp")
    if temporary.exists():
        raise ValueError(f"temporary output collision: {temporary}")
    with temporary.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def unit(milestone: dict[str, Any], unit_id: str) -> dict[str, Any]:
    matches = [item for item in milestone.get("units", []) if item.get("id") == unit_id]
    if len(matches) != 1:
        raise ValueError(f"milestone unit missing or ambiguous: {unit_id}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconciled-at-utc", required=True)
    args = parser.parse_args()
    if not args.reconciled_at_utc.endswith("Z"):
        raise SystemExit("reconciled time must be UTC")
    if OUTPUT.exists():
        raise SystemExit("refusing approval-reconciliation output collision")
    exact = {
        ROOT / APPROVAL_REF: APPROVAL_SHA256,
        ROOT / RECONCILIATION_REF: RECONCILIATION_SHA256,
        ROOT / ACTIVATION_REF: ACTIVATION_SHA256,
    }
    if any(not path.is_file() or sha256(path) != expected for path, expected in exact.items()):
        raise SystemExit("approval, response reconciliation, or activation identity drift")
    approval = load(ROOT / APPROVAL_REF)
    reconciliation = load(ROOT / RECONCILIATION_REF)
    activation = load(ROOT / ACTIVATION_REF)
    if (
        approval.get("status") != "approved_exact_bounded_fixed_order_orbit_continuation_only"
        or approval.get("source_ids_in_exact_order") != ["M2-ORB-002", "M2-ORB-003", "M2-ORB-004"]
        or approval.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}
        or reconciliation.get("status") != "reconciled_exact_human_response"
        or activation.get("status") != "pass_exact_approval_activated_implementation_and_publication_only"
        or activation.get("released_now", {}).get("catalog_or_payload_request") is not False
    ):
        raise SystemExit("exact approval boundary is not active")
    milestone = load(MILESTONE)
    profile = load(PROFILE)
    goal = load(GOAL)
    review = unit(milestone, "M2-ORBIT-CONTINUATION-001-REVIEW")
    implementation = unit(milestone, "M2-ORBIT-CONTINUATION-001-IMPLEMENTATION")
    continuation = unit(milestone, "M2-ORBIT-CONTINUATION-001")
    acquire = unit(milestone, "M2-ORBIT-ACQUIRE")
    if (review.get("status"), implementation.get("status"), continuation.get("status")) != ("ready", "planned", "planned"):
        raise SystemExit("continuation units are not at the exact review checkpoint")
    review.update({
        "status": "complete",
        "disposition": "pass",
        "outputs": [RECONCILIATION_REF, APPROVAL_REF, ACTIVATION_REF],
    })
    review["gates"].update({
        "human_decision_count": 1,
        "attestation": True,
        "continuation_authorized": True,
        "approval_sha256": APPROVAL_SHA256,
        "review_reconciliation_sha256": RECONCILIATION_SHA256,
    })
    review["exit_condition_delta"] = {
        "expected": [],
        "observed": ["one exact attested approval"],
        "decision_value": "enables_dependency",
        "rationale": "The exact response is locked and reconciled; only implementation, synthetic tests, and public CI are released now.",
    }
    implementation.update({"status": "in_progress", "disposition": None})
    implementation["gates"].update({
        "approval_sha256": APPROVAL_SHA256,
        "review_reconciliation_sha256": RECONCILIATION_SHA256,
        "public_ci": "pending",
        "credential_or_source_access_before_public_ci": False,
    })
    implementation["exit_condition_delta"] = {
        "expected": [],
        "observed": ["exact approval locked and reconciled"],
        "decision_value": "unknown",
        "rationale": "Implementation and synthetic validation are active; no live source action is released before public CI.",
    }
    continuation["gates"].update({"public_ci": "pending", "final_no_payload_preflight": "blocked_by_public_ci"})
    acquire["gates"].update({
        "retained_failure_review": "orbit_continuation_001_implementation_public_ci_pending",
        "remaining_source_requests_authorized_by_current_review": True,
        "remaining_source_requests_released_now": False,
        "remaining_source_approval_ref": APPROVAL_REF,
        "remaining_source_approval_sha256": APPROVAL_SHA256,
    })
    acquire["rationale"] = "The three-source continuation is approved, but no request is released until implementation, public CI, and final no-payload preflight pass."
    milestone["handoff"]["current_checkpoint"] = CHECKPOINT
    milestone["handoff"]["next_action"] = NEXT_ACTION
    amendment = {
        "approval_ref": APPROVAL_REF,
        "approval_sha256": APPROVAL_SHA256,
        "proposal_ref": "contracts/milestone-002-orbit-continuation-001-proposal.json",
        "proposal_sha256": "01a2c3521625f8f219909b8d69476dbc3355292ff12e59fd0917ed52bc371e8b",
        "review_bundle_sha256": "f4712a3ffd65eb9cbd1955ccd854423607a384800931004ae10da174a4880dd6",
        "review_reconciliation_ref": RECONCILIATION_REF,
        "review_reconciliation_sha256": RECONCILIATION_SHA256,
        "source_ids_in_exact_order": ["M2-ORB-002", "M2-ORB-003", "M2-ORB-004"],
        "maximum_owner_handoffs": 1,
        "maximum_real_attempts_per_source": 1,
        "stop_on_first_failure": True,
        "maximum_endpoint_tolerance_seconds": 1.0,
        "m2_orb_001_request_authorized": False,
        "secret_transport": "anonymous_pipe_single_use_memory_only",
    }
    for authority in (milestone["authority"], profile["authority"]):
        if not any(item.get("approval_ref") == APPROVAL_REF for item in authority["amendments"]):
            authority["amendments"].append(copy.deepcopy(amendment))
    if APPROVAL_REF not in milestone["scope"]["active_amendments"]:
        milestone["scope"]["active_amendments"].append(APPROVAL_REF)
    if APPROVAL_REF not in profile["control_surfaces"]["activated_amendments"]:
        profile["control_surfaces"]["activated_amendments"].append(APPROVAL_REF)
    gates = [item for item in profile["gate_policy"]["explicit_human_gates"] if item.get("unit_id") == "M2-ORBIT-CONTINUATION-001-REVIEW"]
    if len(gates) != 1:
        raise SystemExit("continuation review gate missing or ambiguous")
    gates[0].update({
        "reason": "The exact owner decision authorizes only the fixed-order implementation, synthetic tests, public-CI gate, final preflight, one owner handoff, and one attempt per remaining source with stop on first failure.",
        "authority_ref": APPROVAL_REF,
    })
    profile["current_checkpoint"] = {"checkpoint_id": CHECKPOINT, "expected_branch": "main", "expected_head": None, "next_action": NEXT_ACTION}
    goal["current_checkpoint"] = CHECKPOINT
    if APPROVAL_REF not in goal["active_amendments"]:
        goal["active_amendments"].append(APPROVAL_REF)
    before = {"milestone": sha256(MILESTONE), "profile": sha256(PROFILE), "goal": sha256(GOAL)}
    nonce = "orbit-continuation-001-approval"
    replace(MILESTONE, milestone, nonce)
    replace(PROFILE, profile, nonce)
    replace(GOAL, goal, nonce)
    receipt = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-CONTINUATION-001-APPROVAL-RECONCILIATION",
        "reconciled_at_utc": args.reconciled_at_utc,
        "status": "pass_exact_approval_reconciled_implementation_publication_only",
        "bindings": {
            "approval_sha256": APPROVAL_SHA256,
            "review_reconciliation_sha256": RECONCILIATION_SHA256,
            "activation_sha256": ACTIVATION_SHA256,
            "milestone_sha256_before": before["milestone"],
            "milestone_sha256_after": sha256(MILESTONE),
            "profile_sha256_before": before["profile"],
            "profile_sha256_after": sha256(PROFILE),
            "goal_sha256_before": before["goal"],
            "goal_sha256_after": sha256(GOAL),
        },
        "assertions": {
            "human_decision_count": 1,
            "credential_values_read_or_recorded": False,
            "network_or_payload_request_performed": False,
            "m2_orb_001_mutated": False,
            "external_data_mutated": False,
            "live_continuation_released_before_public_ci": False,
        },
        "current_checkpoint": CHECKPOINT,
        "next_gate": "implementation and successful public default-branch CI",
    }
    write_new(OUTPUT, receipt)
    print(json.dumps({"status": receipt["status"], "output": str(OUTPUT.relative_to(ROOT)).replace("\\", "/")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
