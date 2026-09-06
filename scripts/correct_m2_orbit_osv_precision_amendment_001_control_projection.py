#!/usr/bin/env python3
"""Repair omitted active-amendment projections after the initial reconciliation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "contracts/milestone-002.json"
PROFILE = ROOT / "records/project-control-profile.json"
GOAL = ROOT / "records/long-term-goal.json"
INITIAL = ROOT / "records/readiness/m2-orbit-osv-precision-amendment-001-implementation-control-reconciliation.json"
OUTPUT = ROOT / "records/readiness/m2-orbit-osv-precision-amendment-001-implementation-control-projection-correction-001.json"
PROPOSAL_REF = "contracts/milestone-002-orbit-osv-precision-amendment-001-proposal.json"
APPROVAL_REF = "records/source-gates/m2-orbit-osv-precision-amendment-001-approval.json"


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace(path: Path, value: dict) -> None:
    temporary = path.with_name(f".{path.name}.osv-projection-correction.tmp")
    if temporary.exists():
        raise ValueError(f"temporary collision: {temporary}")
    with temporary.open("xb") as stream:
        stream.write((json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corrected-at-utc", required=True)
    args = parser.parse_args()
    if OUTPUT.exists() or not args.corrected_at_utc.endswith("Z"):
        raise SystemExit("correction output collision or invalid time")
    initial = load(INITIAL)
    milestone = load(MILESTONE)
    profile = load(PROFILE)
    goal = load(GOAL)
    if (
        initial.get("status") != "pass_approved_local_implementation_ready_public_ci_pending"
        or APPROVAL_REF not in goal.get("active_amendments", [])
        or PROPOSAL_REF in goal.get("proposed_amendments", [])
        or APPROVAL_REF in milestone.get("scope", {}).get("active_amendments", [])
        or APPROVAL_REF in profile.get("control_surfaces", {}).get("activated_amendments", [])
        or profile.get("control_surfaces", {}).get("proposed_amendments") != [PROPOSAL_REF]
    ):
        raise SystemExit("current projection state does not match the bounded omission")
    before = {"milestone": sha256(MILESTONE), "profile": sha256(PROFILE), "goal": sha256(GOAL)}
    milestone["scope"]["active_amendments"].append(APPROVAL_REF)
    profile["control_surfaces"]["proposed_amendments"] = []
    profile["control_surfaces"]["activated_amendments"].append(APPROVAL_REF)
    replace(MILESTONE, milestone)
    replace(PROFILE, profile)
    receipt = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ORBIT-OSV-PRECISION-AMENDMENT-001-IMPLEMENTATION-CONTROL-PROJECTION-CORRECTION-001",
        "corrected_at_utc": args.corrected_at_utc,
        "status": "pass_missing_active_amendment_projections_added_without_scope_change",
        "bindings": {
            "initial_reconciliation_sha256": sha256(INITIAL),
            "approval_sha256": sha256(ROOT / APPROVAL_REF),
            "milestone_sha256_before": before["milestone"],
            "milestone_sha256_after": sha256(MILESTONE),
            "profile_sha256_before": before["profile"],
            "profile_sha256_after": sha256(PROFILE),
            "goal_sha256_unchanged": before["goal"],
        },
        "correction": {
            "added_milestone_scope_active_amendment": APPROVAL_REF,
            "added_profile_activated_amendment": APPROVAL_REF,
            "removed_profile_proposed_amendment": PROPOSAL_REF,
        },
        "assertions": {
            "authority_broadened": False,
            "approval_or_reconciliation_mutated": False,
            "real_staged_file_read": False,
            "network_requests_performed": False,
            "external_data_mutated": False,
            "local_validation_started": False,
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(receipt, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"status": receipt["status"], "output": str(OUTPUT.relative_to(ROOT)).replace("\\", "/")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
