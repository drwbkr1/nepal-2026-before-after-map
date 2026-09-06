#!/usr/bin/env python3
"""Reconcile the passing recovery-003 final preflight into current controls."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from m2_orbit_recovery_003_core import (
    ACTIVE_INTAKE_REF,
    FINAL_PREFLIGHT_REF,
    PUBLICATION_GATE_REF,
    ROOT,
    load_object,
    replace_json,
    sha256_file,
    write_new_json,
)


MILESTONE = ROOT / "contracts/milestone-002.json"
PROFILE = ROOT / "records/project-control-profile.json"
GOAL = ROOT / "records/long-term-goal.json"
OUTPUT = ROOT / "records/readiness/m2-orbit-recovery-003-final-preflight-reconciliation.json"
NEXT_ACTION = "Run the owner-side secret-safe PowerShell handoff exactly once for M2-ORB-001, then reconcile the detached supervisor outcome. Do not retry after any failure or request M2-ORB-002 through M2-ORB-004."


def _unit(milestone: dict, unit_id: str) -> dict:
    matches = [item for item in milestone.get("units", []) if item.get("id") == unit_id]
    if len(matches) != 1:
        raise SystemExit(f"milestone unit missing or ambiguous: {unit_id}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconciled-at-utc", required=True)
    args = parser.parse_args()
    if OUTPUT.exists():
        raise SystemExit("refusing final-preflight reconciliation collision")
    preflight = load_object(ROOT / FINAL_PREFLIGHT_REF)
    gate = load_object(ROOT / PUBLICATION_GATE_REF)
    if (
        preflight.get("status") != "pass_no_payload_ready_for_single_secret_pipe_handoff"
        or preflight.get("bindings", {}).get("publication_gate_sha256") != sha256_file(ROOT / PUBLICATION_GATE_REF)
        or preflight.get("bindings", {}).get("active_intake_sha256") != sha256_file(ROOT / ACTIVE_INTAKE_REF)
        or preflight.get("assertions", {}).get("credential_values_read_or_recorded") is not False
        or preflight.get("assertions", {}).get("orbit_payload_requested") is not False
        or gate.get("github_actions", {}).get("conclusion") != "success"
    ):
        raise SystemExit("final preflight or publication gate differs")
    milestone = load_object(MILESTONE)
    profile = load_object(PROFILE)
    goal = load_object(GOAL)
    implementation = _unit(milestone, "M2-ORBIT-RECOVERY-003-IMPLEMENTATION")
    recovery = _unit(milestone, "M2-ORBIT-RECOVERY-003")
    acquire = _unit(milestone, "M2-ORBIT-ACQUIRE")
    if implementation.get("status") != "complete" or recovery.get("status") != "ready":
        raise SystemExit("recovery-003 controls are not ready for preflight reconciliation")
    implementation["gates"]["final_no_payload_preflight"] = "pass"
    recovery["gates"].update({
        "final_no_payload_preflight": "pass",
        "final_preflight_ref": FINAL_PREFLIGHT_REF,
        "final_preflight_sha256": sha256_file(ROOT / FINAL_PREFLIGHT_REF),
        "owner_handoff_count": 0,
        "authority_consumed": False,
    })
    recovery["exit_condition_delta"]["rationale"] = "Public CI and the exact final no-payload preflight pass; one deliberate owner-side handoff remains."
    acquire["gates"]["orbit_recovery_003_status"] = "ready_one_owner_handoff"
    milestone["handoff"]["current_checkpoint"] = "M2-ORBIT-RECOVERY-003"
    milestone["handoff"]["next_action"] = NEXT_ACTION
    profile["current_checkpoint"] = {
        "checkpoint_id": "M2-ORBIT-RECOVERY-003",
        "expected_branch": "main",
        "expected_head": gate["github_actions"]["head_sha"],
        "next_action": NEXT_ACTION,
    }
    goal["current_checkpoint"] = "M2-ORBIT-RECOVERY-003"
    before = {"milestone": sha256_file(MILESTONE), "profile": sha256_file(PROFILE), "goal": sha256_file(GOAL)}
    nonce = "orbit-recovery-003-preflight"
    replace_json(MILESTONE, milestone, nonce)
    replace_json(PROFILE, profile, nonce)
    replace_json(GOAL, goal, nonce)
    payload = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ORBIT-RECOVERY-003-FINAL-PREFLIGHT-RECONCILIATION",
        "reconciled_at_utc": args.reconciled_at_utc,
        "status": "pass_ready_exactly_one_owner_handoff",
        "bindings": {
            "publication_gate_sha256": sha256_file(ROOT / PUBLICATION_GATE_REF),
            "final_preflight_sha256": sha256_file(ROOT / FINAL_PREFLIGHT_REF),
            "milestone_sha256_before": before["milestone"],
            "milestone_sha256_after": sha256_file(MILESTONE),
            "profile_sha256_before": before["profile"],
            "profile_sha256_after": sha256_file(PROFILE),
            "goal_sha256_before": before["goal"],
            "goal_sha256_after": sha256_file(GOAL),
        },
        "assertions": {
            "owner_handoff_count": 0,
            "authority_consumed": False,
            "credential_values_read_or_recorded": False,
            "orbit_payload_requested": False,
            "other_orbit_source_requested": False,
            "automatic_retry_authorized": False,
        },
        "next_gate": "one deliberate owner-side secret-safe handoff",
    }
    write_new_json(OUTPUT, payload)
    print(json.dumps({"status": payload["status"], "output": str(OUTPUT.relative_to(ROOT)).replace("\\", "/")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
