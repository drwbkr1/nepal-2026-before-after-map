#!/usr/bin/env python3
"""Reconcile the approved OSV amendment to public-CI-pending implementation state."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "contracts/milestone-002.json"
PROFILE = ROOT / "records/project-control-profile.json"
GOAL = ROOT / "records/long-term-goal.json"
APPROVAL_REF = "records/source-gates/m2-orbit-osv-precision-amendment-001-approval.json"
RECONCILIATION_REF = "records/source-gates/m2-orbit-osv-precision-amendment-001-review-reconciliation.json"
READINESS_REF = "records/readiness/m2-orbit-osv-precision-amendment-001-implementation-readiness.json"
OUTPUT = ROOT / "records/readiness/m2-orbit-osv-precision-amendment-001-implementation-control-reconciliation.json"
PROPOSAL_REF = "contracts/milestone-002-orbit-osv-precision-amendment-001-proposal.json"
BUNDLE_SHA256 = "71b3eea557cbd027fecec299b8661ce555a8fa993bccd8ffaea8f525d79d01a7"
PROPOSAL_SHA256 = "0eb9e60f3cd26365cc447eb007e28186470a778928730b055b633c5e88d344e4"
CHECKPOINT = "M2-ORBIT-OSV-PRECISION-AMENDMENT-001-IMPLEMENTATION-PUBLICATION"
NEXT_ACTION = (
    "Publish the exact approved one-second OSV endpoint implementation and require successful public default-branch CI. "
    "Do not read or mutate preserved staged bytes, run the local validation, promote an orbit file, request a token or network resource, or touch another orbit source before that gate passes."
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return value


def unit(milestone: dict, unit_id: str) -> dict:
    matches = [item for item in milestone.get("units", []) if item.get("id") == unit_id]
    if len(matches) != 1:
        raise ValueError(f"milestone unit missing or ambiguous: {unit_id}")
    return matches[0]


def replace_json(path: Path, value: dict, nonce: str) -> None:
    temporary = path.with_name(f".{path.name}.{nonce}.tmp")
    if temporary.exists():
        raise ValueError(f"temporary output collision: {temporary}")
    with temporary.open("xb") as stream:
        stream.write((json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconciled-at-utc", required=True)
    args = parser.parse_args()
    if OUTPUT.exists() or not args.reconciled_at_utc.endswith("Z"):
        raise SystemExit("control-reconciliation output collision or invalid time")
    approval = load(ROOT / APPROVAL_REF)
    reconciliation = load(ROOT / RECONCILIATION_REF)
    readiness = load(ROOT / READINESS_REF)
    if (
        approval.get("status") != "approved_exact_one_second_endpoint_rule_and_one_local_validation"
        or approval.get("proposal_sha256") != PROPOSAL_SHA256
        or approval.get("review_bundle_manifest_sha256") != BUNDLE_SHA256
        or reconciliation.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}
        or reconciliation.get("human_decision_count") != 1
        or reconciliation.get("human_decisions_fabricated") is not False
        or readiness.get("status") != "pass_local_synthetic_ready_public_ci_pending"
        or readiness.get("assertions", {}).get("real_staged_file_read") is not False
    ):
        raise SystemExit("approval, reconciliation, or local readiness drift")
    milestone = load(MILESTONE)
    profile = load(PROFILE)
    goal = load(GOAL)
    review = unit(milestone, "M2-ORBIT-OSV-PRECISION-AMENDMENT-001-REVIEW")
    implementation = unit(milestone, "M2-ORBIT-OSV-PRECISION-AMENDMENT-001-IMPLEMENTATION")
    local_action = unit(milestone, "M2-ORBIT-OSV-PRECISION-AMENDMENT-001")
    acquire = unit(milestone, "M2-ORBIT-ACQUIRE")
    if (review.get("status"), implementation.get("status"), local_action.get("status")) != ("ready", "planned", "planned"):
        raise SystemExit("OSV precision milestone is not at its exact owner-review checkpoint")
    approval_sha = sha256(ROOT / APPROVAL_REF)
    reconciliation_sha = sha256(ROOT / RECONCILIATION_REF)
    readiness_sha = sha256(ROOT / READINESS_REF)
    review.update({"status": "complete", "disposition": "pass", "outputs": [RECONCILIATION_REF, APPROVAL_REF]})
    review["gates"].update({
        "human_decision_count": 1,
        "attestation": True,
        "amendment_authorized": True,
        "approval_sha256": approval_sha,
        "review_reconciliation_sha256": reconciliation_sha,
    })
    review["exit_condition_delta"] = {
        "expected": [],
        "observed": ["one exact attested approval"],
        "decision_value": "enables_dependency",
        "rationale": "The exact one-second local-only amendment is approved; implementation and publication may proceed while real staged bytes remain untouched.",
    }
    implementation.update({
        "status": "ready",
        "disposition": None,
        "inputs": [APPROVAL_REF, READINESS_REF, "contracts/m2-orbit-offline-verification-osv-precision-amendment-001.json"],
        "outputs": ["records/readiness/m2-orbit-osv-precision-amendment-001-implementation-publication-gate.json"],
    })
    implementation["gates"].update({
        "public_ci": "pending",
        "local_synthetic_tests": "pass",
        "implementation_readiness_sha256": readiness_sha,
        "final_no_network_preflight": "blocked_until_public_ci",
        "real_staged_file_read": False,
        "local_validation_started": False,
    })
    implementation["exit_condition_delta"] = {
        "expected": [],
        "observed": ["approved versioned contract", "nine passing synthetic tests", "full local repository suite"],
        "decision_value": "awaiting_public_ci",
        "rationale": "Local implementation is ready; public default-branch CI remains required before any real staged-byte access.",
    }
    local_action["status"] = "planned"
    local_action["disposition"] = None
    local_action["gates"].update({"public_ci": "pending", "final_no_network_preflight": "blocked", "local_validation_attempt_count": 0})
    acquire["gates"]["retained_failure_review"] = "approved_exact_one_second_implementation_public_ci_pending"
    acquire["gates"]["osv_precision_amendment_status"] = "approved_exact_one_second_implementation_public_ci_pending"
    amendment = {
        "approval_ref": APPROVAL_REF,
        "approval_sha256": approval_sha,
        "proposal_ref": PROPOSAL_REF,
        "proposal_sha256": PROPOSAL_SHA256,
        "review_bundle_sha256": BUNDLE_SHA256,
        "review_reconciliation_ref": RECONCILIATION_REF,
        "review_reconciliation_sha256": reconciliation_sha,
        "source_id": "M2-ORB-001",
        "maximum_endpoint_tolerance_seconds": 1.0,
        "maximum_network_requests": 0,
        "maximum_local_validation_attempts": 1,
        "automatic_retry_authorized": False,
        "other_orbit_source_requests_authorized": False,
    }
    if not any(item.get("approval_ref") == APPROVAL_REF for item in milestone["authority"]["amendments"]):
        milestone["authority"]["amendments"].append(copy.deepcopy(amendment))
    if not any(item.get("approval_ref") == APPROVAL_REF for item in profile["authority"]["amendments"]):
        profile["authority"]["amendments"].append(copy.deepcopy(amendment))
    if APPROVAL_REF not in milestone["scope"]["active_amendments"]:
        milestone["scope"]["active_amendments"].append(APPROVAL_REF)
    profile["control_surfaces"]["proposed_amendments"] = [
        item for item in profile["control_surfaces"].get("proposed_amendments", []) if item != PROPOSAL_REF
    ]
    if APPROVAL_REF not in profile["control_surfaces"]["activated_amendments"]:
        profile["control_surfaces"]["activated_amendments"].append(APPROVAL_REF)
    gates = [item for item in profile["gate_policy"]["explicit_human_gates"] if item.get("unit_id") == "M2-ORBIT-OSV-PRECISION-AMENDMENT-001-REVIEW"]
    if len(gates) != 1:
        raise SystemExit("OSV precision profile gate missing or ambiguous")
    gates[0].update({
        "reason": "The exact owner decision authorizes only the one-second implementation, public-CI gate, final no-network preflight, and one local validation with conditional no-replace M2-ORB-001 promotion.",
        "authority_ref": APPROVAL_REF,
    })
    milestone["handoff"]["current_checkpoint"] = CHECKPOINT
    milestone["handoff"]["next_action"] = NEXT_ACTION
    carry = "The OSV precision amendment permits no real staged-byte access before its implementation passes public CI and permits no token, network request, other orbit source, retry, orbit application, radar pixels, baseline, change, or scientific action."
    if carry not in milestone["handoff"]["do_not_carry_forward"]:
        milestone["handoff"]["do_not_carry_forward"].append(carry)
    profile["current_checkpoint"] = {"checkpoint_id": CHECKPOINT, "expected_branch": "main", "expected_head": None, "next_action": NEXT_ACTION}
    goal["current_checkpoint"] = CHECKPOINT
    goal["proposed_amendments"] = [item for item in goal.get("proposed_amendments", []) if item != PROPOSAL_REF]
    if APPROVAL_REF not in goal["active_amendments"]:
        goal["active_amendments"].append(APPROVAL_REF)
    before = {"milestone": sha256(MILESTONE), "profile": sha256(PROFILE), "goal": sha256(GOAL)}
    nonce = "osv-precision-amendment-001-implementation"
    replace_json(MILESTONE, milestone, nonce)
    replace_json(PROFILE, profile, nonce)
    replace_json(GOAL, goal, nonce)
    receipt = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-OSV-PRECISION-AMENDMENT-001-IMPLEMENTATION-CONTROL-RECONCILIATION-001",
        "reconciled_at_utc": args.reconciled_at_utc,
        "status": "pass_approved_local_implementation_ready_public_ci_pending",
        "bindings": {
            "approval_sha256": approval_sha,
            "review_reconciliation_sha256": reconciliation_sha,
            "implementation_readiness_sha256": readiness_sha,
            "milestone_sha256_before": before["milestone"],
            "milestone_sha256_after": sha256(MILESTONE),
            "profile_sha256_before": before["profile"],
            "profile_sha256_after": sha256(PROFILE),
            "goal_sha256_before": before["goal"],
            "goal_sha256_after": sha256(GOAL),
        },
        "assertions": {
            "human_decision_count": 1,
            "attestation": True,
            "maximum_endpoint_tolerance_seconds": 1.0,
            "real_staged_file_read": False,
            "network_requests_performed": False,
            "local_validation_started": False,
            "staged_file_promoted": False,
            "other_orbit_source_requested": False,
        },
        "next_gate": "public default-branch CI for the exact implementation",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(receipt, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"status": receipt["status"], "checkpoint": CHECKPOINT}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
