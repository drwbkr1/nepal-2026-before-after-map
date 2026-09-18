#!/usr/bin/env python3
"""Advance only from the public implementation gate to the final preflight checkpoint."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from m2_dem_vertical_datum_proj25_core import ROOT, load_json, sha256_file, write_new_json


GATE_REF = "records/readiness/m2-dem-vertical-datum-proj25-implementation-publication-gate.json"
OUTPUT_REF = "records/readiness/m2-dem-vertical-datum-proj25-publication-reconciliation.json"
CHECKPOINT = "M2-DEM-EGM2008-PROJ25-ACQUISITION"
NEXT_ACTION = (
    "Publish this exact public-gate transition and require successful default-branch CI. Then run the one final "
    "no-payload preflight; only on its pass may the exact grid be requested once and verified before any fixed-order DEM conversion."
)


def replace_json(path: Path, value: dict[str, Any], nonce: str) -> None:
    temporary = path.with_name(f".{path.name}.{nonce}.tmp")
    with temporary.open("xb") as stream:
        stream.write((json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def unit(milestone: dict[str, Any], unit_id: str) -> dict[str, Any]:
    matches = [item for item in milestone["units"] if item.get("id") == unit_id]
    if len(matches) != 1:
        raise ValueError(f"unit missing or ambiguous: {unit_id}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconciled-at-utc", required=True)
    args = parser.parse_args()
    output = ROOT / OUTPUT_REF
    if output.exists():
        raise SystemExit("publication-reconciliation output collision")
    gate = load_json(ROOT / GATE_REF)
    if (
        gate.get("status") != "pass_public_default_branch_ci_real_actions_released"
        or gate.get("implementation_commit") != "961d58ec8b7099df6f68705ec3c22ee53894cd91"
        or gate.get("public_ci_run_id") != 35300447490
        or gate.get("public_ci_conclusion") != "success"
        or gate.get("assertions", {}).get("grid_request_performed") is not False
        or gate.get("assertions", {}).get("dem_pixels_read") is not False
    ):
        raise SystemExit("implementation publication gate differs")
    milestone_path = ROOT / "contracts/milestone-002.json"
    profile_path = ROOT / "records/project-control-profile.json"
    goal_path = ROOT / "records/long-term-goal.json"
    milestone, profile, goal = load_json(milestone_path), load_json(profile_path), load_json(goal_path)
    implementation = unit(milestone, "M2-DEM-VERTICAL-DATUM-ALTERNATE-METHOD-001-IMPLEMENTATION")
    acquisition = unit(milestone, CHECKPOINT)
    if implementation.get("status") != "in_progress" or acquisition.get("status") != "planned":
        raise SystemExit("milestone is not at the implementation-publication boundary")
    gate_sha = sha256_file(ROOT / GATE_REF)
    implementation.update({"status": "complete", "disposition": "pass_public_default_branch_ci"})
    implementation["outputs"] = [
        "records/readiness/m2-dem-vertical-datum-proj25-implementation-readiness.json",
        GATE_REF,
        OUTPUT_REF,
    ]
    implementation["gates"].update({
        "public_ci": "success",
        "implementation_commit": gate["implementation_commit"],
        "public_ci_run_id": gate["public_ci_run_id"],
        "publication_gate_sha256": gate_sha,
    })
    implementation["exit_condition_delta"] = {
        "expected": [],
        "observed": ["exact implementation commit passed public default-branch CI"],
        "decision_value": "enables_dependency",
        "rationale": "Only the final no-payload preflight and its already-approved conditional successors are released.",
    }
    acquisition["status"] = "in_progress"
    acquisition["gates"].update({
        "public_ci": "success",
        "publication_gate_sha256": gate_sha,
        "final_no_payload_preflight": "ready_not_run",
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
        "authority_ref": "records/source-gates/m2-dem-vertical-datum-alternate-method-001-approval.json",
        "next_action": NEXT_ACTION,
    }]
    goal["current_checkpoint"] = CHECKPOINT
    goal["parallel_checkpoints"] = [CHECKPOINT]
    reconciliation = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-DEM-VERTICAL-DATUM-PROJ25-PUBLICATION-RECONCILIATION",
        "reconciled_at_utc": args.reconciled_at_utc,
        "status": "pass_public_gate_final_no_payload_preflight_ready",
        "publication_gate_sha256": gate_sha,
        "implementation_commit": gate["implementation_commit"],
        "public_ci_run_id": gate["public_ci_run_id"],
        "current_checkpoint": CHECKPOINT,
        "released_now": {"final_no_payload_preflight": True, "grid_request": False, "dem_pixel_read": False},
        "assertions": {"network_requests_performed": False, "grid_payload_bytes_read": 0,
                       "dem_pixels_read": False, "external_data_mutated": False},
    }
    write_new_json(output, reconciliation)
    nonce = "m2-dem-proj25-publication"
    replace_json(milestone_path, milestone, nonce)
    replace_json(profile_path, profile, nonce)
    replace_json(goal_path, goal, nonce)
    print(json.dumps(reconciliation, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
