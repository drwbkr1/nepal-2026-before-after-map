#!/usr/bin/env python3
"""Record the successful implementation CI gate and activate final-preflight execution."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from m2_radar_pixel_orbit_application_001_core import canonical_bytes, load_object, sha256_file, write_new_json


ROOT = Path(__file__).resolve().parents[1]
GATE_REF = "records/readiness/m2-radar-pixel-orbit-application-001-implementation-publication-gate.json"
RECONCILIATION_REF = "records/readiness/m2-radar-pixel-orbit-application-001-implementation-publication-reconciliation.json"
CHECKPOINT = "M2-RADAR-PIXEL-ORBIT-APPLICATION-001-EXECUTION"
NEXT_ACTION = (
    "Run the one final no-content preflight and, only on pass, the single fixed-order six-source orbit-application "
    "and QA attempt with two independent route evaluations. Stop on the first execution failure and do not run "
    "baseline or change analysis."
)


def unit(milestone: dict[str, Any], unit_id: str) -> dict[str, Any]:
    matches = [item for item in milestone.get("units", []) if item.get("id") == unit_id]
    if len(matches) != 1:
        raise ValueError(f"unit missing or ambiguous: {unit_id}")
    return matches[0]


def replace_json(path: Path, value: dict[str, Any], nonce: str) -> None:
    temporary = path.with_name(f".{path.name}.{nonce}.tmp")
    if temporary.exists():
        raise ValueError(f"temporary collision: {temporary}")
    with temporary.open("xb") as stream:
        stream.write(canonical_bytes(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activated-at-utc", required=True)
    args = parser.parse_args()
    if not args.activated_at_utc.endswith("Z"):
        raise SystemExit("activation timestamp must be UTC")
    gate_path = ROOT / GATE_REF
    gate = load_object(gate_path)
    expected_bindings = {
        "implementation_contract_sha256": sha256_file(ROOT / "config/qa/m2-radar-pixel-orbit-application-001-contract.json"),
        "core_sha256": sha256_file(ROOT / "scripts/m2_radar_pixel_orbit_application_001_core.py"),
        "runner_sha256": sha256_file(ROOT / "scripts/run_m2_radar_pixel_orbit_application_001.py"),
        "arcgis_validator_sha256": sha256_file(ROOT / "scripts/validate_m2_radar_pixel_orbit_application_001_arcgis.py"),
        "portable_test_sha256": sha256_file(ROOT / "tests/test_m2_radar_pixel_orbit_application_001.py"),
        "implementation_readiness_sha256": sha256_file(ROOT / "records/readiness/m2-radar-pixel-orbit-application-001-implementation-readiness.json"),
    }
    if (
        gate.get("status") != "pass_public_default_branch_ci_implementation_ready"
        or gate.get("implementation_commit_sha") != "ff2e26f5d28d59b02c78f4d16d14ddccb3ff987e"
        or gate.get("public_ci_run_id") != 35395320916
        or gate.get("public_ci_conclusion") != "success"
        or any(gate.get("bindings", {}).get(key) != value for key, value in expected_bindings.items())
    ):
        raise SystemExit("implementation publication gate differs")

    milestone_path = ROOT / "contracts/milestone-002.json"
    profile_path = ROOT / "records/project-control-profile.json"
    goal_path = ROOT / "records/long-term-goal.json"
    milestone = load_object(milestone_path)
    profile = load_object(profile_path)
    goal = load_object(goal_path)
    implementation = unit(milestone, "M2-RADAR-PIXEL-ORBIT-APPLICATION-001-IMPLEMENTATION")
    execution = unit(milestone, CHECKPOINT)
    if (
        implementation.get("status") != "in_progress"
        or implementation.get("gates", {}).get("public_ci") != "pending"
        or implementation.get("gates", {}).get("project_data_content_read") is not False
        or execution.get("status") != "planned"
        or execution.get("gates", {}).get("source_attempts_started") != 0
        or profile.get("current_checkpoint", {}).get("checkpoint_id") != "M2-RADAR-PIXEL-ORBIT-APPLICATION-001-IMPLEMENTATION"
    ):
        raise SystemExit("control plane is not at exact implementation checkpoint")

    if GATE_REF not in implementation["outputs"]:
        implementation["outputs"].append(GATE_REF)
    if RECONCILIATION_REF not in implementation["outputs"]:
        implementation["outputs"].append(RECONCILIATION_REF)
    implementation.update({"status": "complete", "disposition": "pass"})
    implementation["gates"].update({
        "public_ci": "success",
        "public_ci_run_id": 35395320916,
        "implementation_commit_sha": "ff2e26f5d28d59b02c78f4d16d14ddccb3ff987e",
        "final_no_content_preflight": False,
        "project_data_content_read": False,
        "orbit_application_started": False,
        "radar_pixel_processing_started": False,
    })
    implementation["exit_condition_delta"] = {
        "expected": [],
        "observed": ["portable tests pass", "installed ArcGIS synthetic validation passes", "public default-branch CI succeeds"],
        "decision_value": "enables_dependency",
        "rationale": "Only publication of this gate state and the final no-content preflight are released before project-data access.",
    }
    execution.update({"status": "in_progress", "disposition": None})
    execution["inputs"] = [
        "records/source-gates/m2-radar-pixel-orbit-application-001-approval.json",
        "contracts/milestone-002-radar-pixel-orbit-application-001-proposal.json",
        GATE_REF,
    ]
    execution["gates"].update({
        "public_ci": "success",
        "gate_record_publication": "pending",
        "final_no_content_preflight": "pending_after_gate_record_publication",
        "source_attempts_started": 0,
        "automatic_retry": False,
        "baseline_or_change_authorized": False,
    })
    milestone["handoff"].update({
        "current_checkpoint": CHECKPOINT,
        "next_action": NEXT_ACTION,
        "parallel_checkpoint": CHECKPOINT,
        "parallel_next_action": NEXT_ACTION,
    })
    profile["current_checkpoint"] = {
        "checkpoint_id": CHECKPOINT,
        "expected_branch": "main",
        "expected_head": None,
        "next_action": NEXT_ACTION,
    }
    profile["parallel_checkpoints"] = [{
        "checkpoint_id": CHECKPOINT,
        "authority_ref": "records/source-gates/m2-radar-pixel-orbit-application-001-approval.json",
        "next_action": NEXT_ACTION,
    }]
    goal["current_checkpoint"] = CHECKPOINT
    goal["parallel_checkpoints"] = [CHECKPOINT]
    nonce = "m2-radar-pixel-orbit-application-001-execution"
    replace_json(milestone_path, milestone, nonce)
    replace_json(profile_path, profile, nonce)
    replace_json(goal_path, goal, nonce)

    reconciliation = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-001-IMPLEMENTATION-PUBLICATION-RECONCILIATION",
        "activated_at_utc": args.activated_at_utc,
        "status": "pass_public_implementation_gate_execution_checkpoint_pending_gate_record_ci",
        "publication_gate_ref": GATE_REF,
        "publication_gate_sha256": sha256_file(gate_path),
        "implementation_commit_sha": gate["implementation_commit_sha"],
        "public_ci_run_id": gate["public_ci_run_id"],
        "current_checkpoint": CHECKPOINT,
        "control_sha256": {
            "milestone": sha256_file(milestone_path),
            "project_control_profile": sha256_file(profile_path),
            "long_term_goal": sha256_file(goal_path),
        },
        "released_now": {
            "gate_record_publication": True,
            "final_no_content_preflight_after_gate_record_publication": True,
            "project_data_content_read": False,
            "orbit_application": False,
            "radar_pixel_processing": False,
            "route_evaluation": False,
            "baseline_or_change_analysis": False,
            "scientific_publication": False,
        },
    }
    write_new_json(ROOT / RECONCILIATION_REF, reconciliation)
    print(json.dumps(reconciliation, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
