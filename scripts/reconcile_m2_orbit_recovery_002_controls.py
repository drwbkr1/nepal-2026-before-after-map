#!/usr/bin/env python3
"""Reconcile the exact approved orbit recovery-002 into active project controls after public CI."""

from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path

from m2_orbit_recovery_002_core import (
    APPROVAL_REF,
    APPROVAL_SHA256,
    BUNDLE_SHA256,
    PROPOSAL_REF,
    PROPOSAL_SHA256,
    PUBLICATION_GATE_REF,
    RECONCILIATION_REF,
    RECONCILIATION_SHA256,
    ROOT,
    load_object,
    replace_json,
    sha256_file,
    validate_approval,
    write_new_json,
)


MILESTONE = ROOT / "contracts/milestone-002.json"
PROFILE = ROOT / "records/project-control-profile.json"
GOAL = ROOT / "records/long-term-goal.json"
OUTPUT = ROOT / "records/readiness/m2-orbit-recovery-002-control-reconciliation.json"
CHECKPOINT = "M2-ORBIT-RECOVERY-002"
NEXT_ACTION = "Run the exact final no-payload preflight and, only if it passes, use the owner-side secret-safe token handoff once for M2-ORB-001. Do not request M2-ORB-002 through M2-ORB-004 or retry after failure."


def _unit(milestone: dict, unit_id: str) -> dict:
    matches = [item for item in milestone.get("units", []) if item.get("id") == unit_id]
    if len(matches) != 1:
        raise ValueError(f"milestone unit missing or ambiguous: {unit_id}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconciled-at-utc", required=True)
    args = parser.parse_args()
    if OUTPUT.exists():
        raise SystemExit("refusing control-reconciliation output collision")
    validate_approval()
    gate = load_object(ROOT / PUBLICATION_GATE_REF)
    if (
        gate.get("status") != "pass_public_controls_verified_before_orbit_recovery_002"
        or gate.get("github_actions", {}).get("conclusion") != "success"
        or gate.get("assertions", {}).get("real_recovery_started") is not False
    ):
        raise SystemExit("public-CI gate does not release control reconciliation")
    milestone = load_object(MILESTONE)
    profile = load_object(PROFILE)
    goal = load_object(GOAL)
    review = _unit(milestone, "M2-ORBIT-RECOVERY-002-REVIEW")
    implementation = _unit(milestone, "M2-ORBIT-RECOVERY-002-IMPLEMENTATION")
    recovery = _unit(milestone, "M2-ORBIT-RECOVERY-002")
    acquire = _unit(milestone, "M2-ORBIT-ACQUIRE")
    if review.get("status") != "ready" or implementation.get("status") != "planned" or recovery.get("status") != "planned":
        raise SystemExit("orbit recovery-002 milestone is not at the reviewed checkpoint")
    review.update({
        "status": "complete",
        "disposition": "pass",
        "outputs": [RECONCILIATION_REF, APPROVAL_REF],
        "next_dependency": "M2-ORBIT-RECOVERY-002-IMPLEMENTATION",
    })
    review["gates"].update({
        "human_decision_count": 1,
        "attestation": True,
        "recovery_authorized": True,
        "approval_sha256": APPROVAL_SHA256,
        "review_reconciliation_sha256": RECONCILIATION_SHA256,
    })
    review["exit_condition_delta"] = {
        "expected": [], "observed": ["one exact attested approval"],
        "decision_value": "enables_dependency",
        "rationale": "The exact approval is locked and reconciled; only the reviewed implementation, public-CI, preflight, and one M2-ORB-001 attempt are released.",
    }
    implementation.update({
        "status": "complete",
        "disposition": "pass",
        "inputs": [APPROVAL_REF, "records/acquisition/m2-orbit-recovery-002-implementation-readiness.json"],
        "outputs": [PUBLICATION_GATE_REF],
    })
    implementation["gates"].update({
        "public_ci": "pass",
        "publication_gate_sha256": sha256_file(ROOT / PUBLICATION_GATE_REF),
        "final_no_payload_preflight": "pending",
        "credential_read": False,
        "orbit_payload_requested": False,
    })
    implementation["exit_condition_delta"] = {
        "expected": [], "observed": ["local synthetic tests", "public default-branch CI"],
        "decision_value": "enables_dependency",
        "rationale": "The exact recovery-only implementation passed local controls and public CI without credentials or orbit bytes.",
    }
    recovery.update({
        "status": "ready",
        "disposition": None,
        "inputs": [PUBLICATION_GATE_REF, "contracts/m2-orbit-recovery-002.json", "records/acquisition/m2-orbit-recovery-002-final-preflight.json"],
        "outputs": ["external recovery attempt events", "records/acquisition/orbit-attempts recovery receipt"],
    })
    recovery["gates"].update({
        "public_ci": "pass",
        "final_no_payload_preflight": "pending",
        "credential_values_read_or_recorded": False,
        "other_orbit_source_requests_authorized_by_this_unit": False,
    })
    recovery["exit_condition_delta"]["rationale"] = "Public CI passes; the exact final no-payload preflight and single owner-side handoff remain."
    acquire["gates"]["retained_failure_review"] = "approved_exact_one_file_recovery_002"
    acquire["gates"]["orbit_recovery_002_status"] = "ready_final_no_payload_preflight_pending"
    milestone["handoff"]["current_checkpoint"] = CHECKPOINT
    milestone["handoff"]["next_action"] = NEXT_ACTION
    milestone["handoff"]["do_not_carry_forward"].append(
        "Orbit recovery-002 authorizes one byte-zero M2-ORB-001 attempt only after final preflight; it authorizes no later orbit source request or retry."
    )
    amendment = {
        "approval_ref": APPROVAL_REF,
        "approval_sha256": APPROVAL_SHA256,
        "proposal_ref": PROPOSAL_REF,
        "proposal_sha256": PROPOSAL_SHA256,
        "review_bundle_sha256": BUNDLE_SHA256,
        "review_reconciliation_ref": RECONCILIATION_REF,
        "review_reconciliation_sha256": RECONCILIATION_SHA256,
        "source_id": "M2-ORB-001",
        "maximum_real_attempts": 1,
        "automatic_retry_authorized": False,
        "other_orbit_source_requests_authorized": False,
        "secret_transport": "anonymous_pipe_single_use_memory_only",
    }
    milestone["authority"]["amendments"].append(copy.deepcopy(amendment))
    profile["authority"]["amendments"].append(copy.deepcopy(amendment))
    profile["current_checkpoint"] = {
        "checkpoint_id": CHECKPOINT,
        "expected_branch": "main",
        "expected_head": None,
        "next_action": NEXT_ACTION,
    }
    goal["current_checkpoint"] = CHECKPOINT
    goal["proposed_amendments"] = []
    goal["active_amendments"].append(APPROVAL_REF)
    before = {"milestone": sha256_file(MILESTONE), "profile": sha256_file(PROFILE), "goal": sha256_file(GOAL)}
    nonce = "orbit-recovery-002-controls"
    replace_json(MILESTONE, milestone, nonce)
    replace_json(PROFILE, profile, nonce)
    replace_json(GOAL, goal, nonce)
    receipt = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-RECOVERY-002-CONTROL-RECONCILIATION-001",
        "reconciled_at_utc": args.reconciled_at_utc,
        "status": "pass_approved_public_ci_recovery_ready_final_preflight_pending",
        "bindings": {
            "approval_sha256": APPROVAL_SHA256,
            "review_reconciliation_sha256": RECONCILIATION_SHA256,
            "publication_gate_sha256": sha256_file(ROOT / PUBLICATION_GATE_REF),
            "milestone_sha256_before": before["milestone"], "milestone_sha256_after": sha256_file(MILESTONE),
            "profile_sha256_before": before["profile"], "profile_sha256_after": sha256_file(PROFILE),
            "goal_sha256_before": before["goal"], "goal_sha256_after": sha256_file(GOAL),
        },
        "assertions": {
            "human_decision_count": 1,
            "credential_values_read_or_recorded": False,
            "orbit_payload_requested": False,
            "other_orbit_source_requested": False,
            "automatic_retry_authorized": False,
            "dem_pixel_baseline_change_or_scientific_action_released": False,
        },
        "next_gate": "final no-payload preflight",
    }
    write_new_json(OUTPUT, receipt)
    print(json.dumps({"status": receipt["status"], "output": str(OUTPUT.relative_to(ROOT)).replace("\\", "/")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
