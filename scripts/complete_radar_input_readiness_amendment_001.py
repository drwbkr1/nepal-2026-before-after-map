#!/usr/bin/env python3
"""Reconcile the completed radar label amendment into current project control."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
APPROVAL_REF = "records/source-gates/m2-radar-input-readiness-amendment-approval.json"
PROPOSAL_REF = "contracts/milestone-002-radar-input-readiness-amendment-proposal.json"
BUNDLE_REF = "reviews/m2-radar-input-readiness-amendment/review-bundle.json"
CONTRACT_REF = "config/qa/radar-input-readiness-contract-amendment-001.json"
REAL_REF = "records/readiness/radar-input/m2-s1-input-readiness-real-002.json"
RECONCILIATION_REF = "records/surface-receipts/radar-input-readiness-amendment-real-002-reconciliation.json"


def load(relative: str) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {relative}")
    return value


def digest(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def write_atomic(relative: str, value: dict[str, Any]) -> None:
    path = ROOT / relative
    temp = path.with_name(path.name + ".radar-amendment-001.tmp")
    if temp.exists():
        raise ValueError(f"temporary path collision: {temp}")
    payload = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    with temp.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--completed-at-utc", required=True)
    args = parser.parse_args()
    approval = load(APPROVAL_REF)
    reconciliation = load(RECONCILIATION_REF)
    if approval.get("status") != "approved_exact_bounded_post_observation_correction":
        raise SystemExit("exact amendment approval is not active")
    if reconciliation.get("status") != "pass_partial_pre_event_header_readiness_only_post_observation_no_downstream_release":
        raise SystemExit("real-002 reconciliation is not the bounded pass")
    if reconciliation.get("disposition", {}).get("real_002_maximum_invocations_consumed") != 1:
        raise SystemExit("real-002 invocation has not been consumed exactly once")

    amendment_ref = {
        "approval_ref": APPROVAL_REF,
        "approval_sha256": digest(APPROVAL_REF),
        "proposal_ref": PROPOSAL_REF,
        "proposal_sha256": digest(PROPOSAL_REF),
        "review_bundle_sha256": digest(BUNDLE_REF),
        "amended_contract_ref": CONTRACT_REF,
        "amended_contract_sha256": digest(CONTRACT_REF),
        "real_002_receipt_ref": REAL_REF,
        "real_002_receipt_sha256": digest(REAL_REF),
        "reconciliation_ref": RECONCILIATION_REF,
        "reconciliation_sha256": digest(RECONCILIATION_REF),
        "post_observation": True,
        "baseline_processing_released": False,
    }
    approval_refs = [
        "records/source-gates/m2-dem-amendment-approval.json",
        "records/source-gates/m2-orbit-amendment-approval.json",
    ]

    milestone = load("contracts/milestone-002.json")
    profile = load("records/project-control-profile.json")
    goal = load("records/long-term-goal.json")
    if milestone.get("authority", {}).get("amendments", [])[-2:] != profile.get("authority", {}).get("amendments", [])[-2:]:
        raise SystemExit("existing milestone and profile amendment bindings differ")
    if milestone.get("scope", {}).get("active_amendments") != approval_refs:
        raise SystemExit("existing milestone active amendment list differs")
    if profile.get("control_surfaces", {}).get("activated_amendments") != approval_refs:
        raise SystemExit("existing profile active amendment list differs")
    if goal.get("active_amendments") != approval_refs:
        raise SystemExit("existing goal active amendment list differs")
    if any(unit.get("id") == "M2-RADAR-INPUT-LABEL-AMEND" for unit in milestone.get("units", [])):
        raise SystemExit("radar input amendment unit already exists")

    milestone["authority"]["amendments"].append(amendment_ref)
    milestone["scope"]["active_amendments"].append(APPROVAL_REF)
    milestone["units"].append(
        {
            "id": "M2-RADAR-INPUT-LABEL-AMEND",
            "purpose": "Preserve real-001 and apply the exact owner-approved Detected-label correction through one publication-gated real-002 inspection.",
            "depends_on": ["M2-ACTIVATE"],
            "action_class": "authority_broadening",
            "human_gate": True,
            "status": "complete",
            "inputs": [BUNDLE_REF, PROPOSAL_REF, APPROVAL_REF, CONTRACT_REF],
            "outputs": [REAL_REF, RECONCILIATION_REF],
            "gates": {
                "owner_decision": "approve",
                "attestation": True,
                "review_bundle_sha256": digest(BUNDLE_REF),
                "proposal_sha256": digest(PROPOSAL_REF),
                "publication_commit_sha": "c05e1e26c8ee8dd8755573524da90c2080de4bd7",
                "publication_ci_run_id": 33910395201,
                "real_002_invocation_count": 1,
            },
            "disposition": "pass_partial_pre_event_header_readiness_only",
            "retained_failures": [
                {
                    "receipt_ref": "records/readiness/radar-input/m2-s1-input-readiness-real-001.json",
                    "receipt_sha256": "feab3645709df16306c81dae959a8693925a7c6f919f2a1e414cf3765c3a5b0c",
                    "status": "block",
                    "reclassified": False,
                }
            ],
            "exit_condition_delta": {
                "expected": [],
                "observed": [
                    "three exact pre-event sources pass member, annotation, embedded-vector, and ArcGIS header readiness",
                    "no measurement pixels decoded and no complete before-after pair established",
                ],
                "decision_value": "no_downstream_release",
                "rationale": "The post-observation correction clears only the exact label mismatch; every pixel, pair-completion, terrain, registration, baseline, and scientific gate remains independent.",
            },
            "next_dependency": "M2-ACQUIRE",
            "completed_at_utc": args.completed_at_utc,
        }
    )
    milestone["verification"]["required_checks"].append("exact radar input label amendment and public-CI binding")
    milestone["verification"]["completed_checks"].extend(
        ["exact radar input label amendment and public-CI binding", "three-source partial pre-event radar header readiness"]
    )
    milestone["handoff"]["do_not_carry_forward"].append(
        "The one post-observation radar label amendment run passed only three-source pre-event member, annotation, vector, and header readiness; real-001 remains BLOCK and no pixel or baseline action is released."
    )

    profile["authority"]["amendments"].append(amendment_ref)
    profile["control_surfaces"]["activated_amendments"].append(APPROVAL_REF)
    profile["gate_policy"]["explicit_human_gates"].append(
        {
            "unit_id": "M2-RADAR-INPUT-LABEL-AMEND",
            "reason": "The exact owner decision authorized only the post-observation Detected-label correction, publication gate, one real-002 inspection, and reconciliation.",
            "authority_ref": APPROVAL_REF,
        }
    )
    goal["active_amendments"].append(APPROVAL_REF)

    write_atomic("contracts/milestone-002.json", milestone)
    write_atomic("records/project-control-profile.json", profile)
    write_atomic("records/long-term-goal.json", goal)
    print(json.dumps({"status": "reconciled_into_project_control", "updated": [
        "contracts/milestone-002.json", "records/project-control-profile.json", "records/long-term-goal.json"
    ]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
