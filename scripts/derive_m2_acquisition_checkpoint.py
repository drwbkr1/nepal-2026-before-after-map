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
    "post_container": {
        "checkpoint_id": "M2-VERIFY",
        "next_action": "Prepare and review an exact bounded materialization and pixel-readiness plan for the five not-yet-materialized products. Do not materialize, decode pixels, run baselines, or start orbit recovery before the separate gates are satisfied.",
    },
}
CONTINUATION_REVIEW_CHECKPOINT = {
    "checkpoint_id": "M2-ACQUISITION-REVIEW",
    "next_action": "Publish the exact continuation-001 implementation and verify successful public CI; do not activate, request a token, or access payload bytes before the publication gate and final no-payload preflight pass.",
}
MATERIALIZATION_PIXEL_REVIEW_CHECKPOINT = {
    "checkpoint_id": "M2-MATERIALIZATION-PIXEL-READINESS-REVIEW",
    "next_action": "Review M2 materialization and pixel-readiness bundle SHA-256 8da456e9e0a0e378210b3d9b017e88990f1711da334f27b4cd3886211a97369a and proposal SHA-256 3dbbea5b16eeb297635d6487268cf8b619234fff14755668ac959f778b8e360c; approve, revise, or defer the single bounded plan. No materialization, real header access, or pixel read is authorized before a completed decision.",
}
MATERIALIZATION_PIXEL_IMPLEMENTATION_CHECKPOINT = {
    "checkpoint_id": "M2-MATERIALIZATION-PIXEL-READINESS-IMPLEMENTATION",
    "next_action": "Publish the exact approved stage-1 materialization controls and require successful public CI before the final no-mutation preflight or any SAFE extraction.",
}
FULL_HEADER_IMPLEMENTATION_CHECKPOINT = {
    "checkpoint_id": "M2-FULL-INPUT-READINESS",
    "next_action": "Publish the exact six-source radar and two-source optical header-readiness implementation and require successful public CI before the final no-header preflight or either real inspection.",
}
OPTICAL_PIXEL_IMPLEMENTATION_CHECKPOINT = {
    "checkpoint_id": "M2-OPTICAL-PIXEL-READINESS",
    "next_action": "Publish the exact optical pixel-readiness implementation and require successful public CI before the final no-pixel preflight or the one real pixel attempt.",
}
OPTICAL_PIXEL_RECOVERY_REVIEW_CHECKPOINT = {
    "checkpoint_id": "M2-OPTICAL-PIXEL-RECOVERY-001-REVIEW",
    "next_action": "Review M2 optical pixel recovery-001 bundle SHA-256 d137b8ac1d46531ae42e7944955829eb2df37985428431b39863f4a157e83ac2 and proposal SHA-256 96f0125628e894061fc5da55faff94e92e51b0385293576177c1e15bd009b3da; approve, revise, or defer. No correction or second pixel attempt is authorized before an attested decision.",
}
OPTICAL_PIXEL_RECOVERY_IMPLEMENTATION_CHECKPOINT = {
    "checkpoint_id": "M2-OPTICAL-PIXEL-RECOVERY-001-IMPLEMENTATION",
    "next_action": "Publish the exact optical pixel recovery-001 implementation and require fresh successful public CI; do not run the final no-pixel preflight or recovery attempt before the public gate passes.",
}
OPTICAL_PIXEL_RECOVERY_EXECUTION_CHECKPOINT = {
    "checkpoint_id": "M2-OPTICAL-PIXEL-RECOVERY-001",
    "next_action": "Record the exact passing public-CI gate, run the final no-pixel preflight, and only if it passes invoke optical-pixel-readiness-recovery-001 once with no automatic retry.",
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
    gates = review.get("gates", {})
    blank_review = bool(
        review.get("status") == "ready"
        and review.get("human_gate") is True
        and gates.get("human_decision_count") == 0
        and gates.get("continuation_authorized") is False
        and blank.get("completed") is False
        and blank.get("reviewer", {}).get("attestation") is False
    )
    approved_implementation_pending = bool(
        review.get("status") == "complete"
        and review.get("human_gate") is True
        and gates.get("human_decision_count") == 1
        and gates.get("attestation") is True
        and gates.get("continuation_authorized") is True
        and gates.get("implementation_authorized") is True
    )
    return blank_review or approved_implementation_pending


def current_container_verification_complete(root: Path, state_counts: dict[str, int]) -> bool:
    if state_counts != {"promoted": 8}:
        return False
    try:
        reconciliation = load(root / "records/acquisition/sentinel-continuation-001-success-reconciliation.json")
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    sources = reconciliation.get("bindings", {}).get("sources", {})
    return bool(
        reconciliation.get("status") == "reconciled_all_eight_promoted_container_pass"
        and reconciliation.get("assertions", {}).get("promoted_container_verified_source_count") == 8
        and set(sources) == {f"M1-SRC-{index:03d}" for index in (1, 2, 3, 4, 5, 6, 8, 10)}
        and all(
            isinstance(item, dict)
            and isinstance(item.get("container_receipt_ref"), str)
            and (root / item["container_receipt_ref"]).is_file()
            for item in sources.values()
        )
    )


def current_materialization_pixel_review_required(root: Path, state_counts: dict[str, int]) -> bool:
    if not current_container_verification_complete(root, state_counts):
        return False
    try:
        milestone = load(root / "contracts/milestone-002.json")
        blank = load(root / "reviews/m2-materialization-pixel-readiness/blank-response.json")
        readiness = load(root / "records/readiness/m2-materialization-pixel-readiness-review-readiness.json")
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    units = {unit.get("id"): unit for unit in milestone.get("units", []) if isinstance(unit, dict)}
    review = units.get("M2-MATERIALIZATION-PIXEL-READINESS-REVIEW", {})
    gates = review.get("gates", {})
    responses = blank.get("responses", [])
    return bool(
        review.get("status") == "ready"
        and review.get("human_gate") is True
        and gates.get("review_bundle_sha256") == "8da456e9e0a0e378210b3d9b017e88990f1711da334f27b4cd3886211a97369a"
        and gates.get("proposal_sha256") == "3dbbea5b16eeb297635d6487268cf8b619234fff14755668ac959f778b8e360c"
        and gates.get("human_decision_count") == 0
        and gates.get("attestation") is False
        and gates.get("execution_authorized") is False
        and blank.get("completed") is False
        and blank.get("reviewer", {}).get("attestation") is False
        and len(responses) == 1
        and responses[0].get("decision") is None
        and readiness.get("status") == "pass_ready_owner_review_zero_decisions"
        and readiness.get("review", {}).get("ready_for_handoff") is True
    )


def current_materialization_pixel_implementation_pending(root: Path, state_counts: dict[str, int]) -> bool:
    if not current_container_verification_complete(root, state_counts):
        return False
    try:
        milestone = load(root / "contracts/milestone-002.json")
        approval = load(root / "records/source-gates/m2-materialization-pixel-readiness-approval.json")
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    units = {unit.get("id"): unit for unit in milestone.get("units", []) if isinstance(unit, dict)}
    review = units.get("M2-MATERIALIZATION-PIXEL-READINESS-REVIEW", {})
    implementation = units.get("M2-MATERIALIZATION-PIXEL-READINESS-IMPLEMENTATION", {})
    gates = review.get("gates", {})
    return bool(
        review.get("status") == "complete"
        and review.get("disposition") == "pass"
        and gates.get("human_decision_count") == 1
        and gates.get("attestation") is True
        and gates.get("execution_authorized") is True
        and approval.get("status") == "approved_exact_dependency_ordered_bounded_actions"
        and approval.get("human_decisions_fabricated") is False
        and implementation.get("status") == "in_progress"
        and implementation.get("gates", {}).get("public_ci") == "pending_stage_1"
    )


def current_full_header_implementation_pending(root: Path, state_counts: dict[str, int]) -> bool:
    if not current_container_verification_complete(root, state_counts):
        return False
    try:
        milestone = load(root / "contracts/milestone-002.json")
        reconciliation = load(root / "records/acquisition/sentinel-materialization-reconciliation-002.json")
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    units = {unit.get("id"): unit for unit in milestone.get("units", []) if isinstance(unit, dict)}
    materialize = units.get("M2-MATERIALIZE-REMAINING", {})
    header = units.get("M2-FULL-INPUT-READINESS", {})
    return bool(
        reconciliation.get("status") == "pass_all_eight_materialized_identity_only"
        and materialize.get("status") == "complete"
        and materialize.get("disposition") == "pass_materialization_identity_only"
        and header.get("status") == "in_progress"
        and header.get("gates", {}).get("public_ci") == "pending"
        and header.get("gates", {}).get("measurement_pixel_decoding") is False
    )


def current_optical_pixel_implementation_pending(root: Path, state_counts: dict[str, int]) -> bool:
    if not current_container_verification_complete(root, state_counts):
        return False
    try:
        milestone = load(root / "contracts/milestone-002.json")
        reconciliation = load(root / "records/readiness/m2-full-header-readiness-reconciliation.json")
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    units = {unit.get("id"): unit for unit in milestone.get("units", []) if isinstance(unit, dict)}
    header = units.get("M2-FULL-INPUT-READINESS", {})
    pixel = units.get("M2-OPTICAL-PIXEL-READINESS", {})
    return bool(
        reconciliation.get("status") == "pass_both_exact_header_routes_only"
        and header.get("status") == "complete"
        and header.get("disposition") == "pass_header_readiness_only"
        and pixel.get("status") == "in_progress"
        and pixel.get("gates", {}).get("public_ci") in {"pending", "pending_after_failed_preflight_001"}
        and pixel.get("gates", {}).get("maximum_real_invocations") == 1
        and pixel.get("gates", {}).get("radar_pixel_readiness_authorized") is False
    )


def current_optical_pixel_recovery_review_required(root: Path, state_counts: dict[str, int]) -> bool:
    if not current_container_verification_complete(root, state_counts):
        return False
    try:
        milestone = load(root / "contracts/milestone-002.json")
        reconciliation = load(root / "records/readiness/m2-optical-pixel-real-001-reconciliation.json")
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    units = {unit.get("id"): unit for unit in milestone.get("units", []) if isinstance(unit, dict)}
    pixel = units.get("M2-OPTICAL-PIXEL-READINESS", {})
    review = units.get("M2-OPTICAL-PIXEL-RECOVERY-001-REVIEW", {})
    return bool(
        reconciliation.get("status") == "invalid_terminal_real_001_no_retry_released"
        and pixel.get("status") == "complete"
        and pixel.get("disposition") == "invalid"
        and review.get("status") == "ready"
        and review.get("gates", {}).get("human_decision_count") == 0
        and review.get("gates", {}).get("recovery_authorized") is False
    )


def current_optical_pixel_recovery_implementation_pending(root: Path, state_counts: dict[str, int]) -> bool:
    if not current_container_verification_complete(root, state_counts):
        return False
    try:
        milestone = load(root / "contracts/milestone-002.json")
        approval = load(root / "records/source-gates/m2-optical-pixel-recovery-001-approval.json")
        activation = load(root / "records/readiness/m2-optical-pixel-recovery-001-activation.json")
        readiness = load(root / "records/readiness/m2-optical-pixel-recovery-001-implementation-readiness.json")
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    units = {unit.get("id"): unit for unit in milestone.get("units", []) if isinstance(unit, dict)}
    review = units.get("M2-OPTICAL-PIXEL-RECOVERY-001-REVIEW", {})
    implementation = units.get("M2-OPTICAL-PIXEL-RECOVERY-001-IMPLEMENTATION", {})
    recovery = units.get("M2-OPTICAL-PIXEL-RECOVERY-001", {})
    return bool(
        approval.get("status") == "approved_exact_post_observation_operational_correction_and_one_recovery"
        and approval.get("human_decision_count") == 1
        and approval.get("human_decisions_fabricated") is False
        and activation.get("status") == "pass_exact_approval_activated_implementation_and_publication_only"
        and readiness.get("status") == "pass_exact_shape_local_and_arcgis_synthetic_ready_public_ci_pending"
        and review.get("status") == "complete"
        and review.get("disposition") == "pass"
        and review.get("gates", {}).get("recovery_authorized") is True
        and implementation.get("status") == "in_progress"
        and implementation.get("gates", {}).get("public_ci") == "pending"
        and implementation.get("gates", {}).get("real_recovery_invocation_count") == 0
        and recovery.get("status") == "planned"
    )


def current_optical_pixel_recovery_execution_pending(root: Path, state_counts: dict[str, int]) -> bool:
    if not current_container_verification_complete(root, state_counts):
        return False
    try:
        milestone = load(root / "contracts/milestone-002.json")
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    units = {unit.get("id"): unit for unit in milestone.get("units", []) if isinstance(unit, dict)}
    implementation = units.get("M2-OPTICAL-PIXEL-RECOVERY-001-IMPLEMENTATION", {})
    recovery = units.get("M2-OPTICAL-PIXEL-RECOVERY-001", {})
    return bool(
        implementation.get("status") == "complete"
        and implementation.get("gates", {}).get("public_ci") == "pass"
        and recovery.get("status") == "in_progress"
        and recovery.get("gates", {}).get("real_invocation_count") == 0
        and recovery.get("gates", {}).get("automatic_retry_authorized") is False
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
        if current_optical_pixel_recovery_execution_pending(ROOT, progress["state_counts"]):
            checkpoint = dict(OPTICAL_PIXEL_RECOVERY_EXECUTION_CHECKPOINT)
        elif current_optical_pixel_recovery_implementation_pending(ROOT, progress["state_counts"]):
            checkpoint = dict(OPTICAL_PIXEL_RECOVERY_IMPLEMENTATION_CHECKPOINT)
        elif current_optical_pixel_recovery_review_required(ROOT, progress["state_counts"]):
            checkpoint = dict(OPTICAL_PIXEL_RECOVERY_REVIEW_CHECKPOINT)
        elif current_optical_pixel_implementation_pending(ROOT, progress["state_counts"]):
            checkpoint = dict(OPTICAL_PIXEL_IMPLEMENTATION_CHECKPOINT)
        elif current_full_header_implementation_pending(ROOT, progress["state_counts"]):
            checkpoint = dict(FULL_HEADER_IMPLEMENTATION_CHECKPOINT)
        elif current_materialization_pixel_implementation_pending(ROOT, progress["state_counts"]):
            checkpoint = dict(MATERIALIZATION_PIXEL_IMPLEMENTATION_CHECKPOINT)
        elif current_materialization_pixel_review_required(ROOT, progress["state_counts"]):
            checkpoint = dict(MATERIALIZATION_PIXEL_REVIEW_CHECKPOINT)
        elif current_container_verification_complete(ROOT, progress["state_counts"]):
            checkpoint = dict(CHECKPOINTS["post_container"])
        elif current_continuation_review_required(ROOT, progress["state_counts"]):
            checkpoint = dict(CONTINUATION_REVIEW_CHECKPOINT)
        else:
            checkpoint = derive_checkpoint(progress["state_counts"])
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
