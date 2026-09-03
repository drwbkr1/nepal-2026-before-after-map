#!/usr/bin/env python3
"""Advance the active M2 contract after the exact live preflight passes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
APPROVAL_REF = "records/source-gates/m2-activation-approval.json"
CONTRACT_REF = "contracts/milestone-002.json"
INTAKE_REF = "contracts/m2-intake.json"
PREFLIGHT_REF = "records/acquisition/preflight.json"
SOURCE_GATE_REF = "records/source-gates/m2-live-source-gate.json"
PROFILE_REF = "records/project-control-profile.json"
GOAL_REF = "records/long-term-goal.json"


def load(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def serialized(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2) + "\n").encode("utf-8")


def replace(relative: str, value: dict[str, Any]) -> None:
    path = ROOT / relative
    temporary = path.with_name(path.name + ".preflight-complete-tmp")
    if temporary.exists():
        raise SystemExit(f"temporary update path already exists: {temporary}")
    with temporary.open("xb") as handle:
        handle.write(serialized(value))
        handle.flush()
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--completed-at-utc", required=True)
    args = parser.parse_args()

    approval = load(APPROVAL_REF)
    contract = load(CONTRACT_REF)
    intake = load(INTAKE_REF)
    preflight = load(PREFLIGHT_REF)
    source_gate = load(SOURCE_GATE_REF)
    profile = load(PROFILE_REF)
    goal = load(GOAL_REF)

    if approval.get("status") != "approved":
        raise SystemExit("M2 approval is not active")
    if contract.get("status") != "active" or contract.get("authority", {}).get("authority_ref") != APPROVAL_REF:
        raise SystemExit("active M2 contract differs")
    if preflight.get("status") != "pass_no_external_mutation":
        raise SystemExit("M2 preflight did not pass")
    if preflight.get("source_gate", {}).get("sha256") != sha256(SOURCE_GATE_REF):
        raise SystemExit("preflight source-gate binding differs")
    if source_gate.get("decision", {}).get("status") != "ready":
        raise SystemExit("live source gate is not ready")
    if intake.get("extensions", {}).get("preflight_sha256") != sha256(PREFLIGHT_REF):
        raise SystemExit("active intake preflight binding differs")

    units = {unit["id"]: unit for unit in contract["units"]}
    preflight_unit = units["M2-CUSTODY-PREFLIGHT"]
    acquire_unit = units["M2-ACQUIRE"]
    if preflight_unit.get("status") != "ready" or acquire_unit.get("status") != "planned":
        raise SystemExit("M2 units are not at the expected preflight checkpoint")

    preflight_unit.update({
        "status": "complete",
        "outputs": [PREFLIGHT_REF, SOURCE_GATE_REF, INTAKE_REF],
        "gates": {
            "preflight_status": "pass_no_external_mutation",
            "source_gate_status": "ready",
            "exact_products_online_and_unchanged": 8,
            "free_space_gib": preflight["storage"]["free_gib"],
            "minimum_free_space_gib": preflight["storage"]["minimum_free_gib"],
            "external_root_absent": preflight["paths"]["external_data_root_exists_before_preflight"] is False,
            "credential_values_read_or_recorded": preflight["access"]["credential_values_read_or_recorded"],
        },
        "disposition": "pass",
        "exit_condition_delta": {
            "expected": [],
            "observed": [],
            "decision_value": "enables_dependency",
            "rationale": "The live source gate and non-mutating custody preflight passed under the exact activated authority.",
        },
        "next_dependency": "M2-ACQUIRE",
    })
    acquire_unit.update({
        "status": "ready",
        "inputs": [PREFLIGHT_REF, SOURCE_GATE_REF, INTAKE_REF, "records/acquisition-plan.json"],
        "gates": {
            "custody_initialization": "pending",
            "authentication": "pending_no_credential_reference_present_at_preflight",
            "new_terms_or_account_action": "stop",
        },
        "disposition": None,
        "exit_condition_delta": {
            "expected": ["EXIT-201-VERIFIED-CUSTODY"],
            "observed": [],
            "decision_value": "unknown",
            "rationale": "The approved external root may now be initialized; product transfer still requires a secret-safe existing owner-controlled credential or session.",
        },
    })

    completed_checks = contract["verification"]["completed_checks"]
    for check in (
        "fresh terms and availability review",
        "60 GiB free-space minimum",
        "path and collision safety",
    ):
        if check not in completed_checks:
            completed_checks.append(check)
    contract["handoff"].update({
        "current_checkpoint": "M2-CUSTODY-INITIALIZATION",
        "next_action": "Create only the approved external data, custody, and staging roots with an append-only initialization receipt; do not authenticate or download without a secret-safe owner-controlled credential reference.",
    })

    profile["current_checkpoint"].update({
        "checkpoint_id": "M2-CUSTODY-INITIALIZATION",
        "expected_head": None,
        "next_action": contract["handoff"]["next_action"],
    })
    goal["current_checkpoint"] = "M2-CUSTODY-INITIALIZATION"

    replace(CONTRACT_REF, contract)
    replace(PROFILE_REF, profile)
    replace(GOAL_REF, goal)
    print(json.dumps({
        "status": "m2_preflight_recorded",
        "completed_at_utc": args.completed_at_utc,
        "preflight_sha256": sha256(PREFLIGHT_REF),
        "source_gate_sha256": sha256(SOURCE_GATE_REF),
        "next_unit": "M2-ACQUIRE",
        "next_checkpoint": "M2-CUSTODY-INITIALIZATION",
    }, indent=2))


if __name__ == "__main__":
    main()
