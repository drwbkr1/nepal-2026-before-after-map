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
OPTICAL_PIXEL_RECOVERY_TERMINAL_CHECKPOINT = {
    "checkpoint_id": "M2-OPTICAL-PIXEL-RECOVERY-001",
    "next_action": "Review the reconciled terminal BLOCK from optical-pixel-readiness-recovery-001 and choose a separately scoped path forward. Do not retry, change thresholds, substitute dates or sources, or begin baseline or change analysis under the consumed recovery authority.",
}
RADAR_FIRST_PATH_REVIEW_CHECKPOINT = {
    "checkpoint_id": "M2-RADAR-FIRST-PATH-001-REVIEW",
    "next_action": "Review M2 radar-first path bundle SHA-256 5a5bd80f724841f9558ad5ff966ed0d49222419f7310b345492172e4639421ad and proposal SHA-256 ae2ddfa153a86b7acf7f8ec500690713d5ced9a8ddd58f5655d831e1eb282c77; approve, revise, or defer the control-only route split. No pixel, orbit, DEM, source-substitution, baseline, change, or scientific action is authorized before an attested decision.",
}
ORBIT_RECOVERY_002_REVIEW_CHECKPOINT = {
    "checkpoint_id": "M2-ORBIT-RECOVERY-002-REVIEW",
    "next_action": "Review corrected M2 orbit recovery-002 bundle SHA-256 6d43342b6bda2740667fa6e924a52f15313d8827cfb62563ea107bc483e87fa5 and proposal SHA-256 d30208c07deb66ef2c7487f8c901abd4fb5ff04aa56766bca8066d4c8d4f0db8; approve, revise, or defer one recovery-only implementation and at most one future byte-zero M2-ORB-001 attempt. No orbit, token, DEM, radar-pixel, baseline, change, or scientific action is authorized before an attested decision.",
}
ORBIT_RECOVERY_003_REVIEW_CHECKPOINT = {
    "checkpoint_id": "M2-ORBIT-RECOVERY-003-REVIEW",
    "next_action": "Review M2 orbit recovery-003 bundle SHA-256 bc3cdc22d16251c77b26d9903036b4317221e2b01207aa9db26436bfd091fe9d and proposal SHA-256 5aa4a0042024634a7ade191e0c5f36614216d8581a9c0535c0042be20583bfa3; approve, revise, or defer the evidence-first one-file recovery. No retry, credential, catalog, payload, DEM, radar-pixel, baseline, change, attribution, or scientific-publication action is authorized before an attested decision.",
}
ORBIT_OSV_PRECISION_REVIEW_PUBLICATION_CHECKPOINT = {
    "checkpoint_id": "M2-ORBIT-OSV-PRECISION-AMENDMENT-001-REVIEW-PUBLICATION",
    "next_action": "Publish the exact zero-decision OSV precision amendment packet at proposal SHA-256 0eb9e60f3cd26365cc447eb007e28186470a778928730b055b633c5e88d344e4 and bundle SHA-256 71b3eea557cbd027fecec299b8661ce555a8fa993bccd8ffaea8f525d79d01a7; require successful public CI before owner review. Do not retry recovery-003, touch credentials, request any orbit file, or promote staged bytes.",
}
ORBIT_OSV_PRECISION_REVIEW_CHECKPOINT = {
    "checkpoint_id": "M2-ORBIT-OSV-PRECISION-AMENDMENT-001-REVIEW",
    "next_action": "Review M2 orbit OSV precision amendment-001 bundle SHA-256 71b3eea557cbd027fecec299b8661ce555a8fa993bccd8ffaea8f525d79d01a7 and proposal SHA-256 0eb9e60f3cd26365cc447eb007e28186470a778928730b055b633c5e88d344e4; approve, revise, or defer the exact one-second local-only endpoint rule. No token, network request, recovery retry, staged-byte promotion, other orbit source, processing, or scientific action is authorized before an attested decision.",
}
ORBIT_OSV_PRECISION_IMPLEMENTATION_PUBLICATION_CHECKPOINT = {
    "checkpoint_id": "M2-ORBIT-OSV-PRECISION-AMENDMENT-001-IMPLEMENTATION-PUBLICATION",
    "next_action": "Publish the exact approved one-second OSV endpoint implementation and require successful public default-branch CI. Do not read or mutate preserved staged bytes, run the local validation, promote an orbit file, request a token or network resource, or touch another orbit source before that gate passes.",
}
ORBIT_REMAINING_SOURCES_REVIEW_PREPARATION_CHECKPOINT = {
    "checkpoint_id": "M2-ORBIT-REMAINING-SOURCES-REVIEW-PREPARATION",
    "next_action": "Prepare a separately governed zero-decision review for exact M2-ORB-002 through M2-ORB-004. Do not request an orbit file, obtain or read a token, retry recovery-003, apply orbit data, read radar pixels, act on DEMs, or perform baseline, change, attribution, or scientific-publication work.",
}
ORBIT_CONTINUATION_001_REVIEW_CHECKPOINT = {
    "checkpoint_id": "M2-ORBIT-CONTINUATION-001-REVIEW",
    "next_action": "Review M2 orbit continuation-001 bundle SHA-256 f4712a3ffd65eb9cbd1955ccd854423607a384800931004ae10da174a4880dd6 and proposal SHA-256 01a2c3521625f8f219909b8d69476dbc3355292ff12e59fd0917ed52bc371e8b; approve, revise, or defer the fixed-order one-attempt continuation. No implementation, credential, live query, payload request, custody mutation, orbit application, DEM or radar-pixel action, baseline, change analysis, attribution, or scientific publication is authorized before an attested decision.",
}
ORBIT_CONTINUATION_001_IMPLEMENTATION_CHECKPOINT = {
    "checkpoint_id": "M2-ORBIT-CONTINUATION-001-IMPLEMENTATION",
    "next_action": "Implement and synthetically validate only the approved fixed-order M2-ORB-002, M2-ORB-003, and M2-ORB-004 continuation, then require successful public default-branch CI. No credential, catalog, payload, orbit application, DEM, radar-pixel, baseline, change, attribution, or scientific-publication action is released before that gate.",
}
ORBIT_VERIFY_IMPLEMENTATION_CHECKPOINT = {
    "checkpoint_id": "M2-ORBIT-VERIFY-IMPLEMENTATION",
    "next_action": "Project the already approved one-second endpoint rules and continuation receipt identities into the four-source offline verifier, test and publish that exact implementation, and require successful public default-branch CI before reading the four promoted EOF files. Do not apply orbit data, act on DEMs or radar pixels, run a baseline or change analysis, attribute cause, or publish a scientific result.",
}
ORBIT_OFFLINE_VERIFICATION_RECOVERY_001_REVIEW_PUBLICATION_CHECKPOINT = {
    "checkpoint_id": "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-REVIEW-PUBLICATION",
    "next_action": "Publish and publicly validate the exact blank M2 orbit offline-verification recovery-001 review packet. No recovery implementation, new EOF read, remaining-source verification, network or credential action, orbit application, DEM or radar-pixel action, baseline, change analysis, attribution, or scientific publication is authorized before one attested owner decision on the exact public packet.",
}
ORBIT_OFFLINE_VERIFICATION_RECOVERY_001_REVIEW_CHECKPOINT = {
    "checkpoint_id": "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-REVIEW",
    "next_action": "Review M2 orbit offline-verification recovery-001 bundle SHA-256 d2f0f75f40614c56bc0e62c6eecb1588f7504f50927448192673e6e403b5933f and proposal SHA-256 0be64071cfe718ca758155ff0422cfee48af342c8a560528746adc653e6a2fcf; approve, revise, or defer the exact pre-read receipt-reservation correction and one M2-ORB-001 recovery attempt before conditional fixed-order continuation. No implementation, new EOF read, network or credential action, custody mutation, orbit application, DEM or radar-pixel action, baseline, change analysis, attribution, or scientific publication is authorized before an attested decision.",
}
ORBIT_OFFLINE_VERIFICATION_RECOVERY_001_IMPLEMENTATION_CHECKPOINT = {
    "checkpoint_id": "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-IMPLEMENTATION",
    "next_action": "Implement and synthetically validate only the approved pre-read receipt reservation and fixed-order recovery, then require successful public default-branch CI. Do not run the final no-content preflight or read any EOF before that public gate.",
}
ORBIT_OFFLINE_VERIFICATION_RECOVERY_001_EXECUTION_CHECKPOINT = {
    "checkpoint_id": "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001",
    "next_action": "Run the exact final no-content preflight and, only if it passes, run one M2-ORB-001 recovery verification followed conditionally by M2-ORB-002, M2-ORB-003, and M2-ORB-004 in fixed order, stopping on the first failure.",
}
ORBIT_OFFLINE_VERIFICATION_RECOVERY_001_TERMINAL_CHECKPOINT = {
    "checkpoint_id": "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-TERMINAL",
    "next_action": "Preserve the terminal recovery result and prepare a separately governed path decision. No second recovery, retry, rule change, source substitution, processing, or scientific publication is authorized.",
}
DEM_VERTICAL_DATUM_REVIEW_CHECKPOINT = {
    "checkpoint_id": "M2-DEM-VERTICAL-DATUM-REVIEW",
    "next_action": "Conduct the exact pending owner review of the EGM2008-to-ArcGIS-EGM96 vertical-datum route. Do not apply orbit data, reinterpret DEM heights, read radar pixels, run a baseline or change analysis, attribute cause, or publish a scientific result before that human gate is resolved.",
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


def current_optical_pixel_recovery_terminal(root: Path, state_counts: dict[str, int]) -> bool:
    if not current_container_verification_complete(root, state_counts):
        return False
    try:
        milestone = load(root / "contracts/milestone-002.json")
        receipt = load(root / "records/readiness/optical-pixel/m2-s2-pixel-readiness-recovery-001.json")
        reconciliation = load(root / "records/readiness/m2-optical-pixel-recovery-001-reconciliation.json")
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    units = {unit.get("id"): unit for unit in milestone.get("units", []) if isinstance(unit, dict)}
    recovery = units.get("M2-OPTICAL-PIXEL-RECOVERY-001", {})
    return bool(
        receipt.get("attempt_id") == "optical-pixel-readiness-recovery-001"
        and receipt.get("status") == "block"
        and reconciliation.get("status") == "terminal_block_recovery_001_no_retry_released"
        and reconciliation.get("assertions", {}).get("recovery_invocation_count") == 1
        and reconciliation.get("assertions", {}).get("automatic_retry_authorized") is False
        and recovery.get("status") == "complete"
        and recovery.get("disposition") == "block"
        and recovery.get("gates", {}).get("real_invocation_count") == 1
        and recovery.get("gates", {}).get("automatic_retry_authorized") is False
    )


def current_radar_first_path_review_required(root: Path, state_counts: dict[str, int]) -> bool:
    if not current_optical_pixel_recovery_terminal(root, state_counts):
        return False
    try:
        milestone = load(root / "contracts/milestone-002.json")
        proposal = load(root / "contracts/milestone-002-radar-first-path-001-proposal.json")
        bundle = load(root / "reviews/m2-radar-first-path-001/review-bundle.json")
        contract = load(root / "reviews/m2-radar-first-path-001/review-contract.json")
        blank = load(root / "reviews/m2-radar-first-path-001/blank-response.json")
        readiness = load(root / "records/readiness/m2-radar-first-path-001-review-readiness.json")
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    units = {unit.get("id"): unit for unit in milestone.get("units", []) if isinstance(unit, dict)}
    review = units.get("M2-RADAR-FIRST-PATH-001-REVIEW", {})
    bundle_sha = "5a5bd80f724841f9558ad5ff966ed0d49222419f7310b345492172e4639421ad"
    proposal_sha = "ae2ddfa153a86b7acf7f8ec500690713d5ced9a8ddd58f5655d831e1eb282c77"
    responses = blank.get("responses", [])
    return bool(
        proposal.get("status") == "proposed_not_authorized"
        and proposal.get("recommended_decision") == "approve_radar_first_control_path"
        and bundle.get("candidate_identity") == f"M2-RADAR-FIRST-PATH-001-PROPOSAL-SHA256:{proposal_sha}"
        and contract.get("review_bundle", {}).get("manifest_sha256") == bundle_sha
        and review.get("status") == "ready"
        and review.get("human_gate") is True
        and review.get("gates", {}).get("proposal_sha256") == proposal_sha
        and review.get("gates", {}).get("review_bundle_sha256") == bundle_sha
        and review.get("gates", {}).get("human_decision_count") == 0
        and review.get("gates", {}).get("control_amendment_authorized") is False
        and blank.get("completed") is False
        and blank.get("reviewer", {}).get("attestation") is False
        and len(responses) == 1
        and responses[0].get("decision") is None
        and readiness.get("status") == "pass_ready_owner_review_zero_decisions"
        and readiness.get("review", {}).get("ready_for_handoff") is True
    )


def current_orbit_recovery_002_review_required(root: Path, state_counts: dict[str, int]) -> bool:
    if not current_optical_pixel_recovery_terminal(root, state_counts):
        return False
    try:
        milestone = load(root / "contracts/milestone-002.json")
        proposal = load(root / "contracts/milestone-002-orbit-recovery-002-proposal.json")
        bundle = load(root / "reviews/m2-orbit-recovery-002/review-bundle.json")
        contract = load(root / "reviews/m2-orbit-recovery-002/review-contract.json")
        blank = load(root / "reviews/m2-orbit-recovery-002/blank-response.json")
        readiness = load(root / "records/readiness/m2-orbit-recovery-002-review-readiness.json")
        radar = load(root / "records/readiness/m2-radar-source-readiness-001.json")
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    units = {unit.get("id"): unit for unit in milestone.get("units", []) if isinstance(unit, dict)}
    path_review = units.get("M2-RADAR-FIRST-PATH-001-REVIEW", {})
    radar_unit = units.get("M2-RADAR-SOURCE-READINESS", {})
    review = units.get("M2-ORBIT-RECOVERY-002-REVIEW", {})
    proposal_sha = "d30208c07deb66ef2c7487f8c901abd4fb5ff04aa56766bca8066d4c8d4f0db8"
    bundle_sha = "6d43342b6bda2740667fa6e924a52f15313d8827cfb62563ea107bc483e87fa5"
    responses = blank.get("responses", [])
    return bool(
        path_review.get("status") == "complete"
        and path_review.get("gates", {}).get("human_decision_count") == 1
        and radar_unit.get("status") == "complete"
        and radar_unit.get("disposition") == "pass"
        and radar.get("status") == "pass_six_source_custody_materialization_and_header_readiness_only"
        and proposal.get("status") == "proposed_not_authorized"
        and bundle.get("candidate_identity") == f"M2-ORBIT-RECOVERY-002-PROPOSAL-SHA256:{proposal_sha}"
        and contract.get("review_bundle", {}).get("manifest_sha256") == bundle_sha
        and review.get("status") == "ready"
        and review.get("human_gate") is True
        and review.get("gates", {}).get("proposal_sha256") == proposal_sha
        and review.get("gates", {}).get("review_bundle_sha256") == bundle_sha
        and review.get("gates", {}).get("human_decision_count") == 0
        and review.get("gates", {}).get("recovery_authorized") is False
        and blank.get("completed") is False
        and blank.get("reviewer", {}).get("attestation") is False
        and len(responses) == 1
        and responses[0].get("decision") is None
        and readiness.get("status") == "pass_ready_owner_review_zero_decisions"
        and readiness.get("review", {}).get("ready_for_handoff") is True
    )


def current_orbit_recovery_003_review_required(root: Path, state_counts: dict[str, int]) -> bool:
    if not current_optical_pixel_recovery_terminal(root, state_counts):
        return False
    try:
        milestone = load(root / "contracts/milestone-002.json")
        outcome = load(root / "records/acquisition/m2-orbit-recovery-002-outcome-reconciliation.json")
        proposal = load(root / "contracts/milestone-002-orbit-recovery-003-proposal.json")
        bundle = load(root / "reviews/m2-orbit-recovery-003/review-bundle.json")
        contract = load(root / "reviews/m2-orbit-recovery-003/review-contract.json")
        blank = load(root / "reviews/m2-orbit-recovery-003/blank-response.json")
        readiness = load(root / "records/readiness/m2-orbit-recovery-003-review-readiness.json")
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    units = {unit.get("id"): unit for unit in milestone.get("units", []) if isinstance(unit, dict)}
    recovery_002 = units.get("M2-ORBIT-RECOVERY-002", {})
    review = units.get("M2-ORBIT-RECOVERY-003-REVIEW", {})
    proposal_sha = "5aa4a0042024634a7ade191e0c5f36614216d8581a9c0535c0042be20583bfa3"
    bundle_sha = "bc3cdc22d16251c77b26d9903036b4317221e2b01207aa9db26436bfd091fe9d"
    responses = blank.get("responses", [])
    return bool(
        recovery_002.get("status") == "complete"
        and recovery_002.get("disposition") == "block"
        and recovery_002.get("gates", {}).get("authority_consumed") is True
        and outcome.get("status") == "terminal_pretransfer_supervisor_failure_no_retry"
        and outcome.get("assertions", {}).get("orbit_payload_bytes_received") == 0
        and proposal.get("status") == "proposed_not_authorized"
        and bundle.get("candidate_identity") == f"M2-ORBIT-RECOVERY-003-PROPOSAL-SHA256:{proposal_sha}"
        and contract.get("review_bundle", {}).get("manifest_sha256") == bundle_sha
        and review.get("status") == "ready"
        and review.get("human_gate") is True
        and review.get("gates", {}).get("proposal_sha256") == proposal_sha
        and review.get("gates", {}).get("review_bundle_sha256") == bundle_sha
        and review.get("gates", {}).get("human_decision_count") == 0
        and review.get("gates", {}).get("recovery_authorized") is False
        and blank.get("completed") is False
        and blank.get("reviewer", {}).get("attestation") is False
        and len(responses) == 1
        and responses[0].get("decision") is None
        and readiness.get("status") == "pass_ready_owner_review_zero_decisions"
        and readiness.get("review", {}).get("ready_for_handoff") is True
    )


def current_orbit_osv_precision_review_publication_pending(
    root: Path, state_counts: dict[str, int]
) -> bool:
    if state_counts != {"promoted": 8}:
        return False
    try:
        milestone = load(root / "contracts/milestone-002.json")
        terminal = load(root / "records/readiness/m2-orbit-recovery-003-terminal-reconciliation.json")
        proposal = load(root / "contracts/milestone-002-orbit-osv-precision-amendment-001-proposal.json")
        bundle = load(root / "reviews/m2-orbit-osv-precision-amendment-001/review-bundle.json")
        contract = load(root / "reviews/m2-orbit-osv-precision-amendment-001/review-contract.json")
        blank = load(root / "reviews/m2-orbit-osv-precision-amendment-001/blank-response.json")
        readiness = load(root / "records/readiness/m2-orbit-osv-precision-amendment-001-review-readiness.json")
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    units = {unit.get("id"): unit for unit in milestone.get("units", []) if isinstance(unit, dict)}
    recovery = units.get("M2-ORBIT-RECOVERY-003", {})
    publication = units.get("M2-ORBIT-OSV-PRECISION-AMENDMENT-001-REVIEW-PUBLICATION", {})
    review = units.get("M2-ORBIT-OSV-PRECISION-AMENDMENT-001-REVIEW", {})
    proposal_sha = "0eb9e60f3cd26365cc447eb007e28186470a778928730b055b633c5e88d344e4"
    bundle_sha = "71b3eea557cbd027fecec299b8661ce555a8fa993bccd8ffaea8f525d79d01a7"
    responses = blank.get("responses", [])
    return bool(
        recovery.get("status") == "complete"
        and recovery.get("disposition") == "block"
        and recovery.get("gates", {}).get("authority_consumed") is True
        and terminal.get("status")
        == "terminal_validation_failure_preserved_osv_precision_review_publication_pending"
        and terminal.get("assertions", {}).get("orbit_file_promoted") is False
        and proposal.get("status") == "proposed_not_authorized"
        and proposal.get("proposed_amendment", {}).get("maximum_new_download_requests") == 0
        and bundle.get("candidate_identity")
        == f"M2-ORBIT-OSV-PRECISION-AMENDMENT-001-PROPOSAL-SHA256:{proposal_sha}"
        and contract.get("review_bundle", {}).get("manifest_sha256") == bundle_sha
        and publication.get("status") == "ready"
        and publication.get("gates", {}).get("human_decision_count") == 0
        and publication.get("gates", {}).get("amendment_authorized") is False
        and review.get("status") == "planned"
        and review.get("human_gate") is True
        and blank.get("completed") is False
        and blank.get("reviewer", {}).get("attestation") is False
        and len(responses) == 1
        and responses[0].get("decision") is None
        and readiness.get("status")
        == "pass_ready_owner_review_zero_decisions_public_ci_pending"
        and readiness.get("review", {}).get("ready_for_publication_gate") is True
    )


def current_orbit_osv_precision_review_required(root: Path, state_counts: dict[str, int]) -> bool:
    if state_counts != {"promoted": 8}:
        return False
    try:
        milestone = load(root / "contracts/milestone-002.json")
        gate = load(root / "records/readiness/m2-orbit-osv-precision-amendment-001-review-publication-gate.json")
        reconciliation = load(root / "records/readiness/m2-orbit-osv-precision-amendment-001-review-publication-reconciliation.json")
        proposal = load(root / "contracts/milestone-002-orbit-osv-precision-amendment-001-proposal.json")
        bundle = load(root / "reviews/m2-orbit-osv-precision-amendment-001/review-bundle.json")
        blank = load(root / "reviews/m2-orbit-osv-precision-amendment-001/blank-response.json")
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    units = {unit.get("id"): unit for unit in milestone.get("units", []) if isinstance(unit, dict)}
    publication = units.get("M2-ORBIT-OSV-PRECISION-AMENDMENT-001-REVIEW-PUBLICATION", {})
    review = units.get("M2-ORBIT-OSV-PRECISION-AMENDMENT-001-REVIEW", {})
    proposal_sha = "0eb9e60f3cd26365cc447eb007e28186470a778928730b055b633c5e88d344e4"
    bundle_sha = "71b3eea557cbd027fecec299b8661ce555a8fa993bccd8ffaea8f525d79d01a7"
    responses = blank.get("responses", [])
    return bool(
        publication.get("status") == "complete"
        and publication.get("disposition") == "pass"
        and publication.get("gates", {}).get("public_ci") == "pass"
        and review.get("status") == "ready"
        and review.get("human_gate") is True
        and review.get("gates", {}).get("human_decision_count") == 0
        and review.get("gates", {}).get("amendment_authorized") is False
        and gate.get("status") == "pass_exact_blank_review_packet_public_ci"
        and gate.get("github_actions", {}).get("conclusion") == "success"
        and reconciliation.get("status") == "pass_public_packet_owner_review_ready_zero_decisions"
        and proposal.get("status") == "proposed_not_authorized"
        and bundle.get("candidate_identity")
        == f"M2-ORBIT-OSV-PRECISION-AMENDMENT-001-PROPOSAL-SHA256:{proposal_sha}"
        and gate.get("bindings", {}).get("review_bundle_sha256") == bundle_sha
        and blank.get("completed") is False
        and blank.get("reviewer", {}).get("attestation") is False
        and len(responses) == 1
        and responses[0].get("decision") is None
    )


def current_orbit_osv_precision_implementation_publication_pending(
    root: Path, state_counts: dict[str, int]
) -> bool:
    if state_counts != {"promoted": 8}:
        return False
    try:
        milestone = load(root / "contracts/milestone-002.json")
        approval = load(root / "records/source-gates/m2-orbit-osv-precision-amendment-001-approval.json")
        reconciliation = load(root / "records/source-gates/m2-orbit-osv-precision-amendment-001-review-reconciliation.json")
        readiness = load(root / "records/readiness/m2-orbit-osv-precision-amendment-001-implementation-readiness.json")
        control = load(root / "records/readiness/m2-orbit-osv-precision-amendment-001-implementation-control-reconciliation.json")
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    units = {unit.get("id"): unit for unit in milestone.get("units", []) if isinstance(unit, dict)}
    review = units.get("M2-ORBIT-OSV-PRECISION-AMENDMENT-001-REVIEW", {})
    implementation = units.get("M2-ORBIT-OSV-PRECISION-AMENDMENT-001-IMPLEMENTATION", {})
    local_action = units.get("M2-ORBIT-OSV-PRECISION-AMENDMENT-001", {})
    return bool(
        review.get("status") == "complete"
        and review.get("disposition") == "pass"
        and review.get("gates", {}).get("human_decision_count") == 1
        and review.get("gates", {}).get("attestation") is True
        and review.get("gates", {}).get("amendment_authorized") is True
        and implementation.get("status") == "ready"
        and implementation.get("gates", {}).get("public_ci") == "pending"
        and implementation.get("gates", {}).get("real_staged_file_read") is False
        and local_action.get("status") == "planned"
        and local_action.get("gates", {}).get("local_validation_attempt_count") == 0
        and approval.get("status") == "approved_exact_one_second_endpoint_rule_and_one_local_validation"
        and approval.get("authorized_amendment", {}).get("maximum_osv_endpoint_tolerance_seconds") == 1.0
        and approval.get("authorized_amendment", {}).get("maximum_new_download_requests") == 0
        and reconciliation.get("decision_counts") == {"approve": 1, "revise": 0, "defer": 0}
        and reconciliation.get("human_decision_count") == 1
        and reconciliation.get("human_decisions_fabricated") is False
        and readiness.get("status") == "pass_local_synthetic_ready_public_ci_pending"
        and readiness.get("assertions", {}).get("real_staged_file_read") is False
        and readiness.get("assertions", {}).get("network_requests_performed") is False
        and control.get("status") == "pass_approved_local_implementation_ready_public_ci_pending"
        and control.get("assertions", {}).get("staged_file_promoted") is False
    )


def current_orbit_remaining_sources_review_preparation(
    root: Path, state_counts: dict[str, int]
) -> bool:
    if state_counts != {"promoted": 8}:
        return False
    try:
        milestone = load(root / "contracts/milestone-002.json")
        intake = load(root / "contracts/m2-orbit-intake.json")
        result = load(root / "records/acquisition/m2-orbit-osv-precision-amendment-001-local-validation.json")
        terminal = load(root / "records/readiness/m2-orbit-osv-precision-amendment-001-terminal-reconciliation.json")
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    units = {unit.get("id"): unit for unit in milestone.get("units", []) if isinstance(unit, dict)}
    assets = intake.get("assets", [])
    implementation = units.get("M2-ORBIT-OSV-PRECISION-AMENDMENT-001-IMPLEMENTATION", {})
    local_action = units.get("M2-ORBIT-OSV-PRECISION-AMENDMENT-001", {})
    return bool(
        terminal.get("status") == "pass_exact_m2_orb_001_promoted_remaining_sources_review_required"
        and terminal.get("assertions", {}).get("other_orbit_source_requested") is False
        and result.get("status") == "pass_exact_m2_orb_001_input_promoted_no_replace"
        and implementation.get("status") == "complete"
        and implementation.get("disposition") == "pass"
        and local_action.get("status") == "complete"
        and local_action.get("disposition") == "pass"
        and intake.get("extensions", {}).get("current_orbit_state_counts") == {"authorized": 3, "failed": 0, "promoted": 1}
        and len(assets) == 4
        and assets[0].get("state") == "promoted"
        and [item.get("state") for item in assets[1:]] == ["authorized", "authorized", "authorized"]
    )


def current_orbit_continuation_001_review_required(
    root: Path, state_counts: dict[str, int]
) -> bool:
    if state_counts != {"promoted": 8}:
        return False
    try:
        milestone = load(root / "contracts/milestone-002.json")
        intake = load(root / "contracts/m2-orbit-intake.json")
        publication = load(root / "records/readiness/m2-orbit-continuation-001-review-publication-gate.json")
        reconciliation = load(root / "records/readiness/m2-orbit-continuation-001-review-publication-reconciliation.json")
        blank = load(root / "reviews/m2-orbit-continuation-001/blank-response.json")
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    units = {unit.get("id"): unit for unit in milestone.get("units", []) if isinstance(unit, dict)}
    publication_unit = units.get("M2-ORBIT-CONTINUATION-001-REVIEW-PUBLICATION", {})
    review_unit = units.get("M2-ORBIT-CONTINUATION-001-REVIEW", {})
    assets = intake.get("assets", [])
    return bool(
        publication.get("status") == "pass_exact_blank_packet_public_ci_owner_review_ready"
        and publication.get("github_actions", {}).get("conclusion") == "success"
        and reconciliation.get("status") == "pass_exact_public_packet_owner_review_ready_zero_decisions"
        and reconciliation.get("review", {}).get("human_decision_count") == 0
        and reconciliation.get("review", {}).get("continuation_authorized") is False
        and blank.get("completed") is False
        and blank.get("responses", [{}])[0].get("decision") is None
        and publication_unit.get("status") == "complete"
        and publication_unit.get("disposition") == "pass"
        and review_unit.get("status") == "ready"
        and review_unit.get("human_gate") is True
        and review_unit.get("gates", {}).get("human_decision_count") == 0
        and review_unit.get("gates", {}).get("continuation_authorized") is False
        and intake.get("extensions", {}).get("current_orbit_state_counts") == {"authorized": 3, "failed": 0, "promoted": 1}
        and len(assets) == 4
        and [item.get("state") for item in assets] == ["promoted", "authorized", "authorized", "authorized"]
    )


def current_orbit_continuation_001_implementation_pending(
    root: Path, state_counts: dict[str, int]
) -> bool:
    if state_counts != {"promoted": 8}:
        return False
    try:
        milestone = load(root / "contracts/milestone-002.json")
        intake = load(root / "contracts/m2-orbit-intake.json")
        approval = load(root / "records/source-gates/m2-orbit-continuation-001-approval.json")
        review_reconciliation = load(root / "records/source-gates/m2-orbit-continuation-001-review-reconciliation.json")
        activation = load(root / "records/readiness/m2-orbit-continuation-001-approval-activation.json")
        approval_reconciliation = load(root / "records/readiness/m2-orbit-continuation-001-approval-reconciliation.json")
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    units = {unit.get("id"): unit for unit in milestone.get("units", []) if isinstance(unit, dict)}
    review = units.get("M2-ORBIT-CONTINUATION-001-REVIEW", {})
    implementation = units.get("M2-ORBIT-CONTINUATION-001-IMPLEMENTATION", {})
    action = units.get("M2-ORBIT-CONTINUATION-001", {})
    assets = intake.get("assets", [])
    return bool(
        approval.get("status") == "approved_exact_bounded_fixed_order_orbit_continuation_only"
        and approval.get("review_bundle_manifest_sha256") == "f4712a3ffd65eb9cbd1955ccd854423607a384800931004ae10da174a4880dd6"
        and approval.get("continuation_proposal_sha256") == "01a2c3521625f8f219909b8d69476dbc3355292ff12e59fd0917ed52bc371e8b"
        and approval.get("human_decision_count") == 1
        and approval.get("source_ids_in_exact_order") == ["M2-ORB-002", "M2-ORB-003", "M2-ORB-004"]
        and approval.get("maximum_owner_handoffs") == 1
        and approval.get("maximum_real_attempts_per_source") == 1
        and approval.get("stop_on_first_failure") is True
        and approval.get("maximum_osv_endpoint_tolerance_seconds") == 1.0
        and review_reconciliation.get("status") == "reconciled_exact_human_response"
        and review_reconciliation.get("human_decision_count") == 1
        and review_reconciliation.get("decision_counts") == {"approve": 1, "revise": 0, "defer": 0}
        and activation.get("status") == "pass_exact_approval_activated_implementation_and_publication_only"
        and approval_reconciliation.get("status") == "pass_exact_approval_reconciled_implementation_publication_only"
        and approval_reconciliation.get("current_checkpoint") == "M2-ORBIT-CONTINUATION-001-IMPLEMENTATION"
        and review.get("status") == "complete"
        and review.get("disposition") == "pass"
        and review.get("gates", {}).get("human_decision_count") == 1
        and review.get("gates", {}).get("continuation_authorized") is True
        and implementation.get("status") == "in_progress"
        and implementation.get("gates", {}).get("public_ci") == "pending"
        and action.get("status") == "planned"
        and action.get("gates", {}).get("public_ci") == "pending"
        and action.get("gates", {}).get("final_no_payload_preflight") == "blocked_by_public_ci"
        and intake.get("extensions", {}).get("current_orbit_state_counts") == {"authorized": 3, "failed": 0, "promoted": 1}
        and len(assets) == 4
        and [item.get("state") for item in assets] == ["promoted", "authorized", "authorized", "authorized"]
    )


def current_orbit_verify_implementation_pending(
    root: Path, state_counts: dict[str, int]
) -> bool:
    """Recognize the post-continuation, pre-offline-verification control state."""
    if state_counts != {"promoted": 8}:
        return False
    try:
        milestone = load(root / "contracts/milestone-002.json")
        intake = load(root / "contracts/m2-orbit-intake.json")
        verification = load(root / "contracts/m2-orbit-offline-verification.json")
        candidate = load(root / "contracts/m2-orbit-offline-verification-continuation-001.json")
        success = load(root / "records/acquisition/m2-orbit-continuation-001-success-reconciliation.json")
        project_reconciliation = load(
            root / "records/readiness/m2-orbit-continuation-001-terminal-project-reconciliation.json"
        )
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    units = {unit.get("id"): unit for unit in milestone.get("units", []) if isinstance(unit, dict)}
    assets = intake.get("assets", [])
    candidate_status = candidate.get("status")
    active_status = verification.get("status")
    return bool(
        success.get("status") == "pass_all_three_exact_remaining_orbits_promoted_input_verified"
        and success.get("source_ids_in_exact_order")
        == ["M2-ORB-002", "M2-ORB-003", "M2-ORB-004"]
        and project_reconciliation.get("status")
        == "pass_all_four_orbits_promoted_offline_verifier_public_ci_pending"
        and project_reconciliation.get("next_checkpoint") == "M2-ORBIT-VERIFY-IMPLEMENTATION"
        and intake.get("extensions", {}).get("current_orbit_state_counts")
        == {"authorized": 0, "failed": 0, "promoted": 4}
        and len(assets) == 4
        and [asset.get("state") for asset in assets] == ["promoted"] * 4
        and units.get("M2-ORBIT-ACQUIRE", {}).get("status") == "complete"
        and units.get("M2-ORBIT-ACQUIRE", {}).get("disposition") == "pass"
        and units.get("M2-ORBIT-VERIFY", {}).get("status") == "in_progress"
        and units.get("M2-ORBIT-VERIFY", {}).get("gates", {}).get("real_eof_reads_started") is False
        and candidate_status == "candidate_public_ci_pending"
        and [item.get("source_id") for item in candidate.get("asset_requirements", [])]
        == ["M2-ORB-001", "M2-ORB-002", "M2-ORB-003", "M2-ORB-004"]
        and all(
            item.get("maximum_osv_endpoint_tolerance_seconds") == 1.0
            for item in candidate.get("asset_requirements", [])
        )
        and active_status
        in {
            "active_gate_pending_continuation_compatibility_public_ci",
            "active_gate_ready_for_offline_verification",
        }
    )


def current_orbit_offline_verification_recovery_001_review_publication_pending(
    root: Path, state_counts: dict[str, int]
) -> bool:
    """Recognize the exact blank recovery packet before its public-CI gate."""
    if state_counts != {"promoted": 8}:
        return False
    try:
        milestone = load(root / "contracts/milestone-002.json")
        terminal = load(
            root / "records/readiness/m2-orbit-offline-verification-001-terminal-reconciliation.json"
        )
        proposal = load(
            root / "contracts/milestone-002-orbit-offline-verification-recovery-001-proposal.json"
        )
        readiness = load(
            root / "records/readiness/m2-orbit-offline-verification-recovery-001-review-readiness.json"
        )
        blank = load(
            root / "reviews/m2-orbit-offline-verification-recovery-001/blank-response.json"
        )
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    units = {unit.get("id"): unit for unit in milestone.get("units", []) if isinstance(unit, dict)}
    publication = units.get("M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-REVIEW-PUBLICATION", {})
    review = units.get("M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-REVIEW", {})
    return bool(
        terminal.get("status")
        == "terminal_indeterminate_m2_orb_001_evaluated_receipt_not_persisted_no_retry_released"
        and terminal.get("assertions", {}).get("m2_orb_001_eof_content_read") is True
        and terminal.get("assertions", {}).get("evaluation_result_durably_persisted") is False
        and terminal.get("assertions", {}).get("later_source_eof_content_read") is False
        and proposal.get("status") == "proposed_not_authorized"
        and proposal.get("human_gate", {}).get("review_required") is True
        and readiness.get("status") == "pass_ready_owner_review_zero_decisions_public_ci_pending"
        and readiness.get("review", {}).get("human_decision_count") == 0
        and readiness.get("assertions", {}).get("recovery_authorized") is False
        and blank.get("completed") is False
        and blank.get("reviewer", {}).get("attestation") is False
        and blank.get("responses", [{}])[0].get("decision") is None
        and publication.get("status") == "in_progress"
        and publication.get("gates", {}).get("public_ci") == "pending"
        and publication.get("gates", {}).get("human_decision_count") == 0
        and publication.get("gates", {}).get("recovery_authorized") is False
        and review.get("status") == "blocked"
        and review.get("human_gate") is True
        and review.get("gates", {}).get("human_decision_count") == 0
        and review.get("gates", {}).get("recovery_authorized") is False
    )


def current_orbit_offline_verification_recovery_001_review_required(
    root: Path, state_counts: dict[str, int]
) -> bool:
    """Recognize the public, still-blank recovery packet at the owner gate."""
    if state_counts != {"promoted": 8}:
        return False
    try:
        milestone = load(root / "contracts/milestone-002.json")
        gate = load(
            root / "records/readiness/m2-orbit-offline-verification-recovery-001-review-publication-gate.json"
        )
        reconciliation = load(
            root / "records/readiness/m2-orbit-offline-verification-recovery-001-review-publication-reconciliation.json"
        )
        blank = load(root / "reviews/m2-orbit-offline-verification-recovery-001/blank-response.json")
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    units = {unit.get("id"): unit for unit in milestone.get("units", []) if isinstance(unit, dict)}
    publication = units.get("M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-REVIEW-PUBLICATION", {})
    review = units.get("M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-REVIEW", {})
    return bool(
        gate.get("status") == "pass_exact_blank_recovery_packet_public_ci_owner_review_ready"
        and gate.get("github_actions", {}).get("conclusion") == "success"
        and reconciliation.get("status") == "pass_exact_public_packet_owner_review_ready_zero_decisions"
        and reconciliation.get("assertions", {}).get("human_decision_count") == 0
        and reconciliation.get("assertions", {}).get("recovery_authorized") is False
        and blank.get("completed") is False
        and blank.get("reviewer", {}).get("attestation") is False
        and blank.get("responses", [{}])[0].get("decision") is None
        and publication.get("status") == "complete"
        and publication.get("disposition") == "pass"
        and publication.get("gates", {}).get("public_ci") == "pass"
        and review.get("status") == "ready"
        and review.get("human_gate") is True
        and review.get("gates", {}).get("human_decision_count") == 0
        and review.get("gates", {}).get("attestation") is False
        and review.get("gates", {}).get("recovery_authorized") is False
    )


def current_orbit_offline_verification_recovery_001_implementation_pending(
    root: Path, state_counts: dict[str, int]
) -> bool:
    """Recognize the approved recovery while implementation awaits public CI."""
    if state_counts != {"promoted": 8}:
        return False
    try:
        milestone = load(root / "contracts/milestone-002.json")
        approval = load(root / "records/source-gates/m2-orbit-offline-verification-recovery-001-approval.json")
        activation = load(root / "records/readiness/m2-orbit-offline-verification-recovery-001-approval-activation.json")
        candidate = load(root / "contracts/m2-orbit-offline-verification-recovery-001.json")
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    units = {unit.get("id"): unit for unit in milestone.get("units", []) if isinstance(unit, dict)}
    review = units.get("M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-REVIEW", {})
    implementation = units.get("M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-IMPLEMENTATION", {})
    recovery = units.get("M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001", {})
    return bool(
        approval.get("status") == "approved_exact_pre_read_receipt_reservation_recovery_only"
        and approval.get("decision_counts") == {"approve": 1, "revise": 0, "defer": 0}
        and activation.get("status") == "pass_exact_approval_activated_implementation_and_publication_only"
        and activation.get("released_now", {}).get("real_eof_read") is False
        and candidate.get("status") == "candidate_public_ci_pending"
        and review.get("status") == "complete"
        and review.get("gates", {}).get("human_decision_count") == 1
        and review.get("gates", {}).get("attestation") is True
        and review.get("gates", {}).get("recovery_authorized") is True
        and implementation.get("status") == "in_progress"
        and implementation.get("gates", {}).get("public_ci") == "pending"
        and recovery.get("status") == "planned"
    )


def current_orbit_offline_verification_recovery_001_execution_pending(
    root: Path, state_counts: dict[str, int]
) -> bool:
    """Recognize public recovery controls before terminal reconciliation."""
    if state_counts != {"promoted": 8}:
        return False
    try:
        milestone = load(root / "contracts/milestone-002.json")
        active = load(root / "contracts/m2-orbit-offline-verification.json")
        publication = load(root / "records/readiness/m2-orbit-offline-verification-recovery-001-implementation-publication-gate.json")
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    units = {unit.get("id"): unit for unit in milestone.get("units", []) if isinstance(unit, dict)}
    implementation = units.get("M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-IMPLEMENTATION", {})
    recovery = units.get("M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001", {})
    return bool(
        active.get("status") == "active_recovery_ready_for_offline_verification"
        and active.get("extensions", {}).get("offline_verification_recovery_001", {}).get("public_ci") == "pass"
        and publication.get("status") == "pass_public_recovery_controls_before_eof_reads"
        and publication.get("github_actions", {}).get("conclusion") == "success"
        and implementation.get("status") == "complete"
        and implementation.get("gates", {}).get("public_ci") == "pass"
        and recovery.get("status") == "ready"
        and not (root / "records/readiness/m2-orbit-offline-verification-recovery-001-terminal-reconciliation.json").exists()
    )


def current_orbit_offline_verification_recovery_001_terminal(
    root: Path, state_counts: dict[str, int]
) -> str | None:
    """Return pass or blocked for the exact reconciled recovery terminal state."""
    if state_counts != {"promoted": 8}:
        return None
    try:
        milestone = load(root / "contracts/milestone-002.json")
        active = load(root / "contracts/m2-orbit-offline-verification.json")
        terminal = load(root / "records/readiness/m2-orbit-offline-verification-recovery-001-terminal-reconciliation.json")
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    units = {unit.get("id"): unit for unit in milestone.get("units", []) if isinstance(unit, dict)}
    recovery = units.get("M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001", {})
    if (
        terminal.get("status") == "pass_four_exact_resorb_inputs_verified_no_application"
        and active.get("status") == "complete_pass_four_orbit_inputs_only"
        and recovery.get("status") == "complete"
        and recovery.get("disposition") == "pass"
    ):
        return "pass"
    if (
        str(terminal.get("status", "")).startswith("terminal_")
        and str(active.get("status", "")).startswith("terminal_recovery_001_")
        and recovery.get("status") == "complete"
        and recovery.get("disposition") == "block"
    ):
        return "blocked"
    return None


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
        recovery_terminal = current_orbit_offline_verification_recovery_001_terminal(
            ROOT, progress["state_counts"]
        )
        if recovery_terminal == "pass":
            checkpoint = dict(DEM_VERTICAL_DATUM_REVIEW_CHECKPOINT)
        elif recovery_terminal == "blocked":
            checkpoint = dict(ORBIT_OFFLINE_VERIFICATION_RECOVERY_001_TERMINAL_CHECKPOINT)
        elif current_orbit_offline_verification_recovery_001_execution_pending(
            ROOT, progress["state_counts"]
        ):
            checkpoint = dict(ORBIT_OFFLINE_VERIFICATION_RECOVERY_001_EXECUTION_CHECKPOINT)
        elif current_orbit_offline_verification_recovery_001_implementation_pending(
            ROOT, progress["state_counts"]
        ):
            checkpoint = dict(ORBIT_OFFLINE_VERIFICATION_RECOVERY_001_IMPLEMENTATION_CHECKPOINT)
        elif current_orbit_offline_verification_recovery_001_review_required(
            ROOT, progress["state_counts"]
        ):
            checkpoint = dict(ORBIT_OFFLINE_VERIFICATION_RECOVERY_001_REVIEW_CHECKPOINT)
        elif current_orbit_offline_verification_recovery_001_review_publication_pending(
            ROOT, progress["state_counts"]
        ):
            checkpoint = dict(ORBIT_OFFLINE_VERIFICATION_RECOVERY_001_REVIEW_PUBLICATION_CHECKPOINT)
        elif current_orbit_verify_implementation_pending(ROOT, progress["state_counts"]):
            checkpoint = dict(ORBIT_VERIFY_IMPLEMENTATION_CHECKPOINT)
        elif current_orbit_continuation_001_implementation_pending(ROOT, progress["state_counts"]):
            checkpoint = dict(ORBIT_CONTINUATION_001_IMPLEMENTATION_CHECKPOINT)
        elif current_orbit_continuation_001_review_required(ROOT, progress["state_counts"]):
            checkpoint = dict(ORBIT_CONTINUATION_001_REVIEW_CHECKPOINT)
        elif current_orbit_remaining_sources_review_preparation(ROOT, progress["state_counts"]):
            checkpoint = dict(ORBIT_REMAINING_SOURCES_REVIEW_PREPARATION_CHECKPOINT)
        elif current_orbit_osv_precision_implementation_publication_pending(ROOT, progress["state_counts"]):
            checkpoint = dict(ORBIT_OSV_PRECISION_IMPLEMENTATION_PUBLICATION_CHECKPOINT)
        elif current_orbit_osv_precision_review_required(ROOT, progress["state_counts"]):
            checkpoint = dict(ORBIT_OSV_PRECISION_REVIEW_CHECKPOINT)
        elif current_orbit_osv_precision_review_publication_pending(ROOT, progress["state_counts"]):
            checkpoint = dict(ORBIT_OSV_PRECISION_REVIEW_PUBLICATION_CHECKPOINT)
        elif current_orbit_recovery_003_review_required(ROOT, progress["state_counts"]):
            checkpoint = dict(ORBIT_RECOVERY_003_REVIEW_CHECKPOINT)
        elif current_orbit_recovery_002_review_required(ROOT, progress["state_counts"]):
            checkpoint = dict(ORBIT_RECOVERY_002_REVIEW_CHECKPOINT)
        elif current_radar_first_path_review_required(ROOT, progress["state_counts"]):
            checkpoint = dict(RADAR_FIRST_PATH_REVIEW_CHECKPOINT)
        elif current_optical_pixel_recovery_terminal(ROOT, progress["state_counts"]):
            checkpoint = dict(OPTICAL_PIXEL_RECOVERY_TERMINAL_CHECKPOINT)
        elif current_optical_pixel_recovery_execution_pending(ROOT, progress["state_counts"]):
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
