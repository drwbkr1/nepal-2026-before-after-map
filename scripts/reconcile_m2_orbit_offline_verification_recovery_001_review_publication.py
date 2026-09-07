#!/usr/bin/env python3
"""Advance the public blank recovery packet to its owner-review checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "contracts/milestone-002.json"
PROFILE = ROOT / "records/project-control-profile.json"
GOAL = ROOT / "records/long-term-goal.json"
GATE = ROOT / "records/readiness/m2-orbit-offline-verification-recovery-001-review-publication-gate.json"
PROPOSAL = ROOT / "contracts/milestone-002-orbit-offline-verification-recovery-001-proposal.json"
BUNDLE = ROOT / "reviews/m2-orbit-offline-verification-recovery-001/review-bundle.json"
BLANK = ROOT / "reviews/m2-orbit-offline-verification-recovery-001/blank-response.json"
OUTPUT = ROOT / "records/readiness/m2-orbit-offline-verification-recovery-001-review-publication-reconciliation.json"
PROPOSAL_SHA256 = "0be64071cfe718ca758155ff0422cfee48af342c8a560528746adc653e6a2fcf"
BUNDLE_SHA256 = "d2f0f75f40614c56bc0e62c6eecb1588f7504f50927448192673e6e403b5933f"
CHECKPOINT = "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-REVIEW"
NEXT_ACTION = (
    f"Review M2 orbit offline-verification recovery-001 bundle SHA-256 {BUNDLE_SHA256} and proposal SHA-256 "
    f"{PROPOSAL_SHA256}; approve, revise, or defer the exact pre-read receipt-reservation correction and one "
    "M2-ORB-001 recovery attempt before conditional fixed-order continuation. No implementation, new EOF read, "
    "network or credential action, custody mutation, orbit application, DEM or radar-pixel action, baseline, change "
    "analysis, attribution, or scientific publication is authorized before an attested decision."
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
    if OUTPUT.exists() or not args.reconciled_at_utc.endswith("Z"):
        raise SystemExit("publication-reconciliation output collision or invalid time")
    gate = load(GATE)
    proposal = load(PROPOSAL)
    bundle = load(BUNDLE)
    blank = load(BLANK)
    if (
        gate.get("status") != "pass_exact_blank_recovery_packet_public_ci_owner_review_ready"
        or gate.get("github_actions", {}).get("conclusion") != "success"
        or gate.get("bindings", {}).get("proposal_sha256") != PROPOSAL_SHA256
        or gate.get("bindings", {}).get("review_bundle_sha256") != BUNDLE_SHA256
        or proposal.get("status") != "proposed_not_authorized"
        or bundle.get("candidate_identity")
        != f"M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-PROPOSAL-SHA256:{PROPOSAL_SHA256}"
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
    publication = units.get("M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-REVIEW-PUBLICATION")
    review = units.get("M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-REVIEW")
    if not all(isinstance(item, dict) for item in (publication, review)):
        raise SystemExit("required recovery review units are absent")
    if (
        publication.get("status") != "in_progress"
        or publication.get("gates", {}).get("public_ci") != "pending"
        or review.get("status") != "blocked"
        or review.get("gates", {}).get("human_decision_count") != 0
        or review.get("gates", {}).get("recovery_authorized") is not False
    ):
        raise SystemExit("recovery review publication state differs")
    publication["status"] = "complete"
    publication["disposition"] = "pass"
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
        "observed": ["exact blank recovery packet passed public default-branch CI"],
        "decision_value": "enables_dependency",
        "rationale": "Public validation passed without creating a human decision or recovery authority.",
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
        "record_id": "NEPAL-M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-REVIEW-PUBLICATION-RECONCILIATION",
        "reconciled_at_utc": args.reconciled_at_utc,
        "status": "pass_exact_public_packet_owner_review_ready_zero_decisions",
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
            "recovery_authorized": False,
            "new_eof_content_read": False,
            "remaining_source_eof_content_read": False,
            "network_or_credential_action_performed": False,
            "external_custody_mutated": False,
            "orbit_application_performed": False,
            "dem_or_radar_pixel_action_performed": False,
            "baseline_change_attribution_or_publication_performed": False,
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
