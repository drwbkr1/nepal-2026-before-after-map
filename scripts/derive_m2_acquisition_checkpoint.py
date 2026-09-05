#!/usr/bin/env python3
"""Derive the project checkpoint from validated M2 acquisition progress."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from validate_m2_acquisition_progress import load, validate_progress


ROOT = Path(__file__).resolve().parents[1]
CHECKPOINTS = {
    "authentication": {
        "checkpoint_id": "M2-AUTHENTICATION-REFERENCE",
        "next_action": "Provide a secret-safe reference to an existing owner-controlled CDSE access token or authenticated session; then revalidate the exact first product before transfer. Do not place a token, password, cookie, or header in Git or chat.",
    },
    "in_progress": {
        "checkpoint_id": "M2-ACQUISITION-IN-PROGRESS",
        "next_action": "Continue the exact one-product transfer, offline container verification, and SAFE materialization sequence for the remaining authorized products. Preserve terminal failures and do not retry automatically.",
    },
    "review": {
        "checkpoint_id": "M2-ACQUISITION-REVIEW",
        "next_action": "Review the retained failed transfer and external state. Do not delete partial evidence or retry automatically; any recovery must preserve the exact approved product boundary.",
    },
    "container": {
        "checkpoint_id": "M2-CONTAINER-VERIFICATION",
        "next_action": "Run the offline container verifier for every promoted product and preserve any blocked archive. Do not treat promoted bytes as usable pixels.",
    },
}
CONTINUATION_REVIEW_CHECKPOINT = {
    "checkpoint_id": "M2-ACQUISITION-REVIEW",
    "next_action": "Review exact Sentinel continuation-001 bundle 018adc5c9edad48beb665f717c0c39fc5b63b93c0127c1f571df59d30c25f192 and proposal d58706dc0961816191a76f420d993bdc28be8f140358dc1638f6cc937366e7b1; do not implement, request a token, or acquire another product before a completed owner decision.",
}


def derive_checkpoint(state_counts: dict[str, int]) -> dict[str, str]:
    total = sum(state_counts.values())
    if total != 8:
        raise ValueError("exactly eight acquisition assets are required")
    if state_counts == {"authorized": 8}:
        return dict(CHECKPOINTS["authentication"])
    if state_counts.get("failed", 0):
        return dict(CHECKPOINTS["review"])
    if state_counts.get("authorized", 0) or state_counts.get("staging", 0):
        return dict(CHECKPOINTS["in_progress"])
    if state_counts.get("promoted") == 8:
        return dict(CHECKPOINTS["container"])
    raise ValueError("acquisition state counts cannot determine a safe checkpoint")


def current_continuation_review_required(root: Path, state_counts: dict[str, int]) -> bool:
    if state_counts != {"authorized": 4, "promoted": 4}:
        return False
    try:
        milestone = load(root / "contracts/milestone-002.json")
        blank = load(root / "reviews/m2-sentinel-continuation-001/blank-response.json")
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    units = {unit.get("id"): unit for unit in milestone.get("units", []) if isinstance(unit, dict)}
    review = units.get("M2-SENTINEL-CONTINUATION-001-REVIEW", {})
    return bool(
        review.get("status") == "ready"
        and review.get("human_gate") is True
        and review.get("gates", {}).get("human_decision_count") == 0
        and review.get("gates", {}).get("continuation_authorized") is False
        and blank.get("completed") is False
        and blank.get("reviewer", {}).get("attestation") is False
    )


def candidate_controls(
    profile: dict[str, Any],
    goal: dict[str, Any],
    checkpoint: dict[str, str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    candidate_profile = json.loads(json.dumps(profile))
    candidate_goal = json.loads(json.dumps(goal))
    candidate_profile["current_checkpoint"] = {
        "checkpoint_id": checkpoint["checkpoint_id"],
        "expected_branch": "main",
        "expected_head": None,
        "next_action": checkpoint["next_action"],
    }
    candidate_goal["current_checkpoint"] = checkpoint["checkpoint_id"]
    return candidate_profile, candidate_goal


def write_new_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-external", action="store_true")
    parser.add_argument(
        "--candidate-output-root",
        type=Path,
        help="Write new, reviewable profile and goal candidates without replacing tracked controls.",
    )
    args = parser.parse_args()
    progress = validate_progress(
        load(ROOT / "contracts/m2-intake.json"),
        load(ROOT / "records/acquisition/active-intake-initial-snapshot.json"),
        load(ROOT / "records/acquisition-plan.json"),
        root=ROOT,
        verify_external=args.verify_external,
    )
    if progress["status"] != "pass":
        print(json.dumps({"status": "blocked_invalid_acquisition_progress", "progress": progress}, indent=2))
        return 12
    try:
        checkpoint = (
            dict(CONTINUATION_REVIEW_CHECKPOINT)
            if current_continuation_review_required(ROOT, progress["state_counts"])
            else derive_checkpoint(progress["state_counts"])
        )
    except ValueError as exc:
        print(json.dumps({"status": "blocked_ambiguous_checkpoint", "error": str(exc), "progress": progress}, indent=2))
        return 12
    profile = load(ROOT / "records/project-control-profile.json")
    goal = load(ROOT / "records/long-term-goal.json")
    candidate_profile, candidate_goal = candidate_controls(profile, goal, checkpoint)
    current_profile_checkpoint = profile.get("current_checkpoint", {})
    matches = (
        current_profile_checkpoint.get("checkpoint_id") == checkpoint["checkpoint_id"]
        and current_profile_checkpoint.get("expected_branch") == "main"
        and current_profile_checkpoint.get("expected_head") is None
        and current_profile_checkpoint.get("next_action") == checkpoint["next_action"]
        and goal.get("current_checkpoint") == candidate_goal["current_checkpoint"]
    )
    output_refs: dict[str, str] = {}
    if args.candidate_output_root is not None:
        output_root = args.candidate_output_root
        if not output_root.is_absolute():
            output_root = ROOT / output_root
        try:
            output_root.resolve(strict=False).relative_to((ROOT / "scratch").resolve(strict=False))
        except ValueError:
            print(json.dumps({"status": "stopped", "code": "candidate_output_outside_scratch", "files_mutated": False}, indent=2))
            return 12
        if output_root.exists():
            print(json.dumps({"status": "stopped", "code": "candidate_output_collision", "files_mutated": False}, indent=2))
            return 12
        write_new_json(output_root / "project-control-profile.json", candidate_profile)
        write_new_json(output_root / "long-term-goal.json", candidate_goal)
        output_refs = {
            "profile_candidate": str(output_root / "project-control-profile.json"),
            "goal_candidate": str(output_root / "long-term-goal.json"),
        }
    result = {
        "status": "pass" if matches else "needs_reconciliation",
        "checkpoint": checkpoint,
        "state_counts": progress["state_counts"],
        "current_controls_match": matches,
        "candidate_outputs": output_refs,
        "tracked_files_mutated": False,
        "credential_values_read": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if matches else 20


if __name__ == "__main__":
    raise SystemExit(main())
