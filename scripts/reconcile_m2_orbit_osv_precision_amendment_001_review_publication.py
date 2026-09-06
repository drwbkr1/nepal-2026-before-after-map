#!/usr/bin/env python3
"""Advance the public OSV precision packet to its still-blank owner-review gate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "contracts/milestone-002.json"
PROFILE = ROOT / "records/project-control-profile.json"
GOAL = ROOT / "records/long-term-goal.json"
GATE = ROOT / "records/readiness/m2-orbit-osv-precision-amendment-001-review-publication-gate.json"
PROPOSAL = ROOT / "contracts/milestone-002-orbit-osv-precision-amendment-001-proposal.json"
BUNDLE = ROOT / "reviews/m2-orbit-osv-precision-amendment-001/review-bundle.json"
BLANK = ROOT / "reviews/m2-orbit-osv-precision-amendment-001/blank-response.json"
OUTPUT = ROOT / "records/readiness/m2-orbit-osv-precision-amendment-001-review-publication-reconciliation.json"
PROPOSAL_SHA256 = "0eb9e60f3cd26365cc447eb007e28186470a778928730b055b633c5e88d344e4"
BUNDLE_SHA256 = "71b3eea557cbd027fecec299b8661ce555a8fa993bccd8ffaea8f525d79d01a7"
CHECKPOINT = "M2-ORBIT-OSV-PRECISION-AMENDMENT-001-REVIEW"
NEXT_ACTION = (
    "Review M2 orbit OSV precision amendment-001 bundle SHA-256 "
    f"{BUNDLE_SHA256} and proposal SHA-256 {PROPOSAL_SHA256}; approve, revise, or defer the exact one-second "
    "local-only endpoint rule. No token, network request, recovery retry, staged-byte promotion, other orbit source, "
    "processing, or scientific action is authorized before an attested decision."
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return value


def write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconciled-at-utc", required=True)
    args = parser.parse_args()
    if OUTPUT.exists():
        raise SystemExit("refusing publication-reconciliation output collision")
    if not args.reconciled_at_utc.endswith("Z"):
        raise SystemExit("reconciled time must be UTC")
    gate = load(GATE)
    proposal = load(PROPOSAL)
    bundle = load(BUNDLE)
    blank = load(BLANK)
    if (
        gate.get("status") != "pass_exact_blank_review_packet_public_ci"
        or gate.get("github_actions", {}).get("conclusion") != "success"
        or gate.get("bindings", {}).get("proposal_sha256") != PROPOSAL_SHA256
        or gate.get("bindings", {}).get("review_bundle_sha256") != BUNDLE_SHA256
        or proposal.get("status") != "proposed_not_authorized"
        or bundle.get("candidate_identity") != f"M2-ORBIT-OSV-PRECISION-AMENDMENT-001-PROPOSAL-SHA256:{PROPOSAL_SHA256}"
        or blank.get("completed") is not False
        or blank.get("reviewer", {}).get("attestation") is not False
        or blank.get("responses", [{}])[0].get("decision") is not None
    ):
        raise SystemExit("publication gate or blank review identity differs")
    milestone = load(MILESTONE)
    profile = load(PROFILE)
    goal = load(GOAL)
    before = {"milestone": sha256(MILESTONE), "profile": sha256(PROFILE), "goal": sha256(GOAL)}
    units = {unit.get("id"): unit for unit in milestone.get("units", []) if isinstance(unit, dict)}
    publication = units.get("M2-ORBIT-OSV-PRECISION-AMENDMENT-001-REVIEW-PUBLICATION")
    review = units.get("M2-ORBIT-OSV-PRECISION-AMENDMENT-001-REVIEW")
    orbit_acquire = units.get("M2-ORBIT-ACQUIRE")
    if not all(isinstance(item, dict) for item in (publication, review, orbit_acquire)):
        raise SystemExit("required milestone units are absent")
    publication["status"] = "complete"
    publication["disposition"] = "pass"
    publication["outputs"] = ["records/readiness/m2-orbit-osv-precision-amendment-001-review-publication-gate.json"]
    publication["gates"].update(
        {
            "public_ci": "pass",
            "publication_commit": gate["github_actions"]["head_sha"],
            "public_ci_run_id": gate["github_actions"]["run_id"],
            "publication_gate_sha256": sha256(GATE),
        }
    )
    publication["exit_condition_delta"] = {
        "expected": [],
        "observed": ["exact blank review packet passed public default-branch CI"],
        "decision_value": "enables_dependency",
        "rationale": "Public validation passed without creating a human decision or amendment authority.",
    }
    review["status"] = "ready"
    review["disposition"] = None
    review["gates"].update({"public_ci": "pass", "publication_gate_sha256": sha256(GATE)})
    review["exit_condition_delta"] = {
        "expected": [],
        "observed": [],
        "decision_value": "unknown",
        "rationale": "The exact review is public and blank; one attested owner decision is required.",
    }
    orbit_acquire["gates"]["retained_failure_review"] = "osv_precision_amendment_review_ready_zero_decisions"
    milestone["handoff"]["current_checkpoint"] = CHECKPOINT
    milestone["handoff"]["next_action"] = NEXT_ACTION
    profile["current_checkpoint"] = {
        "checkpoint_id": CHECKPOINT,
        "expected_branch": "main",
        "expected_head": None,
        "next_action": NEXT_ACTION,
    }
    goal["current_checkpoint"] = CHECKPOINT
    write(MILESTONE, milestone)
    write(PROFILE, profile)
    write(GOAL, goal)
    after = {"milestone": sha256(MILESTONE), "profile": sha256(PROFILE), "goal": sha256(GOAL)}
    receipt = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ORBIT-OSV-PRECISION-AMENDMENT-001-REVIEW-PUBLICATION-RECONCILIATION",
        "reconciled_at_utc": args.reconciled_at_utc,
        "status": "pass_public_packet_owner_review_ready_zero_decisions",
        "bindings": {
            "publication_gate_sha256": sha256(GATE),
            "proposal_sha256": sha256(PROPOSAL),
            "review_bundle_sha256": sha256(BUNDLE),
            "blank_response_sha256": sha256(BLANK),
            "milestone_sha256_before": before["milestone"],
            "milestone_sha256_after": after["milestone"],
            "profile_sha256_before": before["profile"],
            "profile_sha256_after": after["profile"],
            "goal_sha256_before": before["goal"],
            "goal_sha256_after": after["goal"],
        },
        "assertions": {
            "human_decision_count": 0,
            "attestation": False,
            "amendment_authorized": False,
            "credential_values_read_or_recorded": False,
            "network_requests_performed": False,
            "payload_mutated": False,
            "staged_file_promoted": False,
            "other_orbit_source_requested": False,
            "scientific_result_established": False,
        },
        "next_gate": NEXT_ACTION,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(receipt, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"status": receipt["status"], "checkpoint": CHECKPOINT}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
