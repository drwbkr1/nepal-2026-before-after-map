#!/usr/bin/env python3
"""Repair two omitted active-amendment projections without broadening authority."""

from __future__ import annotations

import argparse
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
RECONCILIATION_REF = "records/readiness/m2-orbit-continuation-001-approval-reconciliation.json"
RECONCILIATION_SHA256 = "e9518c9c000feee919c69cb5b3445413a98457d5d7bbf791cf4831cfb7014b09"
OUTPUT = ROOT / "records/readiness/m2-orbit-continuation-001-active-amendment-projection-correction-001.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return value


def replace(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.orbit-continuation-001-projection.tmp")
    if temporary.exists():
        raise ValueError(f"temporary output collision: {temporary}")
    with temporary.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def write_new(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corrected-at-utc", required=True)
    args = parser.parse_args()
    if not args.corrected_at_utc.endswith("Z"):
        raise SystemExit("correction time must be UTC")
    if OUTPUT.exists():
        raise SystemExit("refusing projection-correction output collision")
    if sha256(ROOT / APPROVAL_REF) != APPROVAL_SHA256 or sha256(ROOT / RECONCILIATION_REF) != RECONCILIATION_SHA256:
        raise SystemExit("approval or initial reconciliation identity drift")

    milestone = load(MILESTONE)
    profile = load(PROFILE)
    goal = load(GOAL)
    milestone_active = milestone.get("scope", {}).get("active_amendments", [])
    profile_active = profile.get("control_surfaces", {}).get("activated_amendments", [])
    goal_active = goal.get("active_amendments", [])
    if APPROVAL_REF in milestone_active or APPROVAL_REF in profile_active:
        raise SystemExit("projection is not at the exact omitted-field state")
    if APPROVAL_REF not in goal_active:
        raise SystemExit("canonical goal projection does not contain the approved amendment")
    if not any(item.get("approval_ref") == APPROVAL_REF for item in milestone.get("authority", {}).get("amendments", [])):
        raise SystemExit("milestone authority binding is absent")
    if not any(item.get("approval_ref") == APPROVAL_REF for item in profile.get("authority", {}).get("amendments", [])):
        raise SystemExit("profile authority binding is absent")

    before = {"milestone": sha256(MILESTONE), "profile": sha256(PROFILE), "goal": sha256(GOAL)}
    milestone_active.append(APPROVAL_REF)
    profile_active.append(APPROVAL_REF)
    replace(MILESTONE, milestone)
    replace(PROFILE, profile)
    after = {"milestone": sha256(MILESTONE), "profile": sha256(PROFILE), "goal": sha256(GOAL)}
    receipt = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-CONTINUATION-001-ACTIVE-AMENDMENT-PROJECTION-CORRECTION-001",
        "corrected_at_utc": args.corrected_at_utc,
        "status": "pass_two_omitted_active_amendment_projections_added_without_scope_change",
        "bindings": {
            "approval_ref": APPROVAL_REF,
            "approval_sha256": APPROVAL_SHA256,
            "initial_reconciliation_ref": RECONCILIATION_REF,
            "initial_reconciliation_sha256": RECONCILIATION_SHA256,
            "milestone_sha256_before": before["milestone"],
            "milestone_sha256_after": after["milestone"],
            "profile_sha256_before": before["profile"],
            "profile_sha256_after": after["profile"],
            "goal_sha256_unchanged": after["goal"],
        },
        "corrected_fields": [
            "contracts/milestone-002.json#/scope/active_amendments",
            "records/project-control-profile.json#/control_surfaces/activated_amendments",
        ],
        "assertions": {
            "authority_broadened": False,
            "approval_content_changed": False,
            "credential_values_read_or_recorded": False,
            "network_or_payload_request_performed": False,
            "m2_orb_001_mutated": False,
            "external_data_mutated": False,
        },
        "next_gate": "implementation and successful public default-branch CI",
    }
    write_new(OUTPUT, receipt)
    print(json.dumps({"status": receipt["status"], "output": str(OUTPUT.relative_to(ROOT)).replace("\\", "/")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
