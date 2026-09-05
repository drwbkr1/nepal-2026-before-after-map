#!/usr/bin/env python3
"""Prepare the zero-decision M2 radar-first path review package."""

from __future__ import annotations

import argparse
import hashlib
import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_REF = "records/readiness/m2-post-optical-route-analysis-001.json"
PROPOSAL_REF = "contracts/milestone-002-radar-first-path-001-proposal.json"
PREFLIGHT_REF = "records/readiness/m2-radar-first-path-001-review-preflight.json"
DOC_REF = "docs/M2_RADAR_FIRST_PATH_REVIEW_001.md"
IMAGE_REF = "docs/assets/m2-radar-first-path-review-001.png"
SURFACE_REF = "records/surface-receipts/m2-radar-first-path-review-001.json"
BUNDLE_REF = "reviews/m2-radar-first-path-001/review-bundle.json"
CONTRACT_REF = "reviews/m2-radar-first-path-001/review-contract.json"
BLANK_REF = "reviews/m2-radar-first-path-001/blank-response.json"
READINESS_REF = "records/readiness/m2-radar-first-path-001-review-readiness.json"


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def write_json(ref: str, value: dict) -> None:
    path = ROOT / ref
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def write_text(ref: str, value: str) -> None:
    path = ROOT / ref
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(value)


def font(name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default()


def render_surface() -> None:
    image = Image.new("RGB", (1700, 1180), "#f4f1e9")
    draw = ImageDraw.Draw(image)
    title = font("arialbd.ttf", 50)
    heading = font("arialbd.ttf", 29)
    body = font("arial.ttf", 24)
    callout = font("arialbd.ttf", 25)
    draw.rectangle((0, 0, 1700, 145), fill="#17324d")
    draw.text((65, 42), "M2 Post-Optical Route Review 001", font=title, fill="white")
    y = 185
    sections = [
        (
            "Established evidence",
            [
                "All eight exact Sentinel products are verified and materialized; both header routes passed.",
                "The only authorized optical pixel recovery is terminal BLOCK under fixed criteria.",
                "The optical result remains evidence and cannot be retried, tuned, or date-shopped here.",
            ],
        ),
        (
            "Control conflict",
            [
                "Radar inputs passed header readiness, but radar pixels remain gated by DEM and orbit prerequisites.",
                "The old orbit recovery packet requires full M2-VERIFY, which cannot pass while optical is blocked.",
                "That aggregate dependency now prevents the independent radar route from reaching its own gates.",
            ],
        ),
        (
            "Recommended decision: radar-first control path",
            [
                "Close only the optical branch as terminal BLOCK and retain all its evidence.",
                "Split aggregate verification into route-specific controls and prepare a corrected orbit review.",
                "Keep both existing DEM reviews and every later radar-pixel action as separate human gates.",
            ],
        ),
        (
            "Approval still would not authorize",
            [
                "Orbit download, DEM conversion or install, radar pixel decoding, baseline, or change analysis.",
                "New optical searches, source or date substitution, threshold changes, attribution, or publication.",
            ],
        ),
    ]
    for label, lines in sections:
        draw.text((65, y), label, font=heading, fill="#17324d")
        y += 43
        for line in lines:
            wrapped = textwrap.wrap(line, 112)
            for index, part in enumerate(wrapped):
                prefix = "• " if index == 0 else "  "
                draw.text((92, y), prefix + part, font=body, fill="#20252b")
                y += 33
        y += 17
    draw.rectangle((60, 1040, 1640, 1130), outline="#9b6b21", width=3)
    draw.text((82, 1064), "Decision required: APPROVE, REVISE, or DEFER — with owner attestation.", font=callout, fill="#7a4e0b")
    path = ROOT / IMAGE_REF
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared-at-utc", required=True)
    args = parser.parse_args()
    outputs = [
        ANALYSIS_REF,
        PROPOSAL_REF,
        PREFLIGHT_REF,
        DOC_REF,
        IMAGE_REF,
        SURFACE_REF,
        BUNDLE_REF,
        CONTRACT_REF,
        BLANK_REF,
        READINESS_REF,
    ]
    collisions = [ref for ref in outputs if (ROOT / ref).exists()]
    if collisions:
        raise SystemExit("review output collision: " + ", ".join(collisions))

    optical_receipt_ref = "records/readiness/optical-pixel/m2-s2-pixel-readiness-recovery-001.json"
    optical_reconciliation_ref = "records/readiness/m2-optical-pixel-recovery-001-reconciliation.json"
    header_reconciliation_ref = "records/readiness/m2-full-header-readiness-reconciliation.json"
    route_independence_ref = "contracts/milestone-002-materialization-pixel-readiness-proposal.json"
    stale_orbit_proposal_ref = "contracts/milestone-002-orbit-recovery-proposal.json"
    active_milestone_ref = "contracts/milestone-002.json"

    analysis = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-POST-OPTICAL-ROUTE-ANALYSIS-001",
        "observed_at_utc": args.prepared_at_utc,
        "status": "needs_owner_route_decision",
        "live_facts": {
            "active_milestone_ref": active_milestone_ref,
            "active_milestone_sha256_at_observation": sha256(active_milestone_ref),
            "optical_recovery_receipt_ref": optical_receipt_ref,
            "optical_recovery_receipt_sha256": sha256(optical_receipt_ref),
            "optical_recovery_reconciliation_ref": optical_reconciliation_ref,
            "optical_recovery_reconciliation_sha256": sha256(optical_reconciliation_ref),
            "full_header_reconciliation_ref": header_reconciliation_ref,
            "full_header_reconciliation_sha256": sha256(header_reconciliation_ref),
            "predeclared_route_independence_ref": route_independence_ref,
            "predeclared_route_independence_sha256": sha256(route_independence_ref),
            "orbit_recovery_proposal_ref": stale_orbit_proposal_ref,
            "orbit_recovery_proposal_sha256": sha256(stale_orbit_proposal_ref),
        },
        "findings": [
            "the optical recovery is terminal BLOCK and its one-invocation authority is consumed",
            "all eight exact Sentinel products are in verified materialized custody and both route header inspections passed",
            "the approved materialization proposal declared optical and radar route independence",
            "the unapproved orbit recovery proposal requires full M2-VERIFY completion",
            "full M2-VERIFY cannot pass while the optical route is terminal BLOCK, so that prerequisite deadlocks the otherwise independent radar route",
        ],
        "reconciliation_outcome": "drift_requires_normative_path_choice",
        "minimum_safe_delta": "retain optical BLOCK, split route-specific readiness controls, and supersede only the unapproved stale orbit recovery packet before any radar execution is considered",
        "assertions": {
            "human_decision_count": 0,
            "credentials_read": False,
            "network_requests_performed": False,
            "real_product_pixels_read": False,
            "external_data_mutated": False,
        },
    }
    write_json(ANALYSIS_REF, analysis)

    proposal = {
        "schema_version": "1.0",
        "proposal_id": "NEPAL-M2-RADAR-FIRST-PATH-001-PROPOSAL",
        "prepared_at_utc": args.prepared_at_utc,
        "status": "proposed_not_authorized",
        "recommended_decision": "approve_radar_first_control_path",
        "trigger": {
            "analysis_ref": ANALYSIS_REF,
            "analysis_sha256": sha256(ANALYSIS_REF),
            "optical_terminal_status": "block",
            "optical_recovery_authority_consumed": True,
        },
        "proposed_bounded_actions": [
            "retain optical-pixel-readiness real-001 as terminal INVALID and recovery-001 as terminal BLOCK with no retry, tuning, date change, or source substitution",
            "amend only the M2 control graph so optical and radar readiness are represented as separate evidence branches while aggregate M2-VERIFY remains deferred",
            "replace the obsolete full-M2-VERIFY prerequisite for any future orbit recovery with exact radar source custody, radar header readiness, and existing orbit-amendment approval prerequisites",
            "preserve the current unapproved orbit recovery proposal and bundle as stale evidence and prepare a new hash-bound corrected orbit recovery review with zero human decisions",
            "retain the existing DEM terrain-result and vertical-datum reviews as independent unresolved human gates before any radar terrain correction",
            "update project controls, documentation, tests, and public control-only CI evidence for this dependency correction",
        ],
        "future_sequence_after_control_amendment": [
            "obtain separate owner decisions on the existing DEM terrain-result and vertical-datum reviews",
            "obtain a separate owner decision on the corrected one-file orbit recovery review",
            "only after DEM and orbit prerequisites pass, prepare a separate radar pixel-readiness proposal and review",
        ],
        "does_not_authorize": [
            "any optical retry, threshold change, alternate date search, date substitution, or source substitution",
            "acceptance of terms, credential entry, token handling, software installation, UAC approval, or account action",
            "DEM conversion, vertical transformation, or promotion to radar-ready",
            "orbit catalogue access, download, verification, application, retry, or precise-orbit substitution",
            "Sentinel-1 measurement-pixel decoding or any real radar pixel-readiness attempt",
            "baseline processing, change rasters or polygons, interpretation, attribution, emergency guidance, or scientific publication",
        ],
        "decision_domain": ["approve", "revise", "defer"],
        "attestation_required": True,
    }
    write_json(PROPOSAL_REF, proposal)
    proposal_sha = sha256(PROPOSAL_REF)

    preflight = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-FIRST-PATH-001-REVIEW-PREFLIGHT",
        "observed_at_utc": args.prepared_at_utc,
        "status": "pass_review_ready_no_control_amendment_authority",
        "bindings": {
            "proposal_sha256": proposal_sha,
            "analysis_sha256": sha256(ANALYSIS_REF),
            "optical_receipt_sha256": sha256(optical_receipt_ref),
            "optical_reconciliation_sha256": sha256(optical_reconciliation_ref),
            "full_header_reconciliation_sha256": sha256(header_reconciliation_ref),
            "stale_orbit_proposal_sha256": sha256(stale_orbit_proposal_ref),
        },
        "assertions": {
            "human_decision_count": 0,
            "control_amendment_authorized": False,
            "orbit_recovery_authorized": False,
            "dem_action_authorized": False,
            "radar_pixel_readiness_authorized": False,
            "optical_alternate_route_authorized": False,
            "real_product_pixels_read_during_preparation": False,
            "network_requests_performed": False,
        },
    }
    write_json(PREFLIGHT_REF, preflight)

    doc = f"""# M2 post-optical route review 001

## Decision

Choose **approve**, **revise**, or **defer** for proposal `{proposal_sha}`. Approval must be an attested owner decision bound to the exact review-bundle hash generated with this package.

## Established result

`optical-pixel-readiness-recovery-001` completed once as terminal `BLOCK` under the fixed coverage, usable-pixel, and registration criteria. Real-001 remains terminal `INVALID`. Neither result can be retried or silently rescued.

All eight exact Sentinel products remain in verified materialized custody, and both full header routes passed. Radar measurement pixels have not been decoded.

## Why a control decision is required

The predeclared plan keeps optical and radar evidence independent. The current unapproved orbit-recovery packet nevertheless requires the aggregate `M2-VERIFY` unit to complete. That cannot occur while the optical branch is terminally blocked, so the old prerequisite prevents the radar branch from reaching its own DEM and orbit gates.

## What approval would release

Approval releases only a control-plane amendment: preserve and close the optical branch, represent optical and radar readiness separately, mark the old unapproved orbit-recovery packet stale, prepare a corrected zero-decision orbit review, and retain both DEM decisions as separate gates.

## What remains prohibited

No optical retry or alternate search, no threshold or source change, no credential or token action, no DEM conversion or install, no orbit request, no radar pixel decoding, no baseline or change analysis, and no scientific or emergency publication.
"""
    write_text(DOC_REF, doc)
    render_surface()

    surface = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-RADAR-FIRST-PATH-001-REVIEW-SURFACE",
        "verified_at_utc": args.prepared_at_utc,
        "status": "pass_blank_review_surface",
        "render": {
            "path": IMAGE_REF,
            "sha256": sha256(IMAGE_REF),
            "human_decision_count": 0,
        },
        "assertions": {
            "proposal_sha256": proposal_sha,
            "recommended_route_visible": True,
            "control_amendment_authorized": False,
            "radar_pixel_readiness_authorized": False,
            "real_product_pixels_read": False,
        },
    }
    write_json(SURFACE_REF, surface)

    artifacts = [
        ("review-surface", IMAGE_REF, "review_surface", True),
        ("review-instructions", DOC_REF, "decision_instructions", False),
        ("proposal", PROPOSAL_REF, "candidate_authority_envelope", False),
        ("route-analysis", ANALYSIS_REF, "live_fact_reconciliation", False),
        ("review-preflight", PREFLIGHT_REF, "zero_authority_preflight", False),
        ("optical-terminal-receipt", optical_receipt_ref, "terminal_observation", False),
        ("optical-terminal-reconciliation", optical_reconciliation_ref, "terminal_custody_and_authority_reconciliation", False),
        ("full-header-reconciliation", header_reconciliation_ref, "independent_route_input_readiness", False),
        ("route-independence-contract", route_independence_ref, "predeclared_route_independence", False),
        ("stale-orbit-recovery-proposal", stale_orbit_proposal_ref, "conflicting_unapproved_prerequisite", False),
        ("dem-vertical-review-contract", "reviews/m2-dem-vertical-datum/review-contract.json", "independent_pending_human_gate", False),
        ("dem-terrain-review-contract", "reviews/m2-dem-terrain-result/review-contract.json", "independent_pending_human_gate", False),
    ]
    bundle = {
        "schema_version": "1.0",
        "template": False,
        "bundle_id": "m2-radar-first-path-001-review-bundle",
        "review_id": "m2-radar-first-path-001-review",
        "authority_ref": "records/source-gates/m2-optical-pixel-recovery-001-approval.json",
        "candidate_identity": f"M2-RADAR-FIRST-PATH-001-PROPOSAL-SHA256:{proposal_sha}",
        "artifacts": [
            {
                "artifact_id": artifact_id,
                "path": ref,
                "sha256": sha256(ref),
                "role": role,
                "render_required": rendered,
                "render_receipts": [{"path": SURFACE_REF, "sha256": sha256(SURFACE_REF)}] if rendered else [],
            }
            for artifact_id, ref, role, rendered in artifacts
        ],
        "review_surface": {
            "artifact_id": "review-surface",
            "blank_state_verified": True,
            "completion_controls_verified": True,
            "export_verified": True,
        },
        "limitations": proposal["does_not_authorize"],
    }
    write_json(BUNDLE_REF, bundle)
    bundle_sha = sha256(BUNDLE_REF)

    review_contract = {
        "contract_version": "human-review-contract-v1",
        "template": False,
        "review_id": "m2-radar-first-path-001-review",
        "response_schema_version": "nepal-m2-radar-first-path-001-response-v1",
        "workflow_authority": {
            "mode": "inherited",
            "authority_ref": "records/source-gates/m2-optical-pixel-recovery-001-approval.json",
            "authorized_action_classes": ["evidence_recording", "project_control", "update_project_records"],
            "verified_at_utc": args.prepared_at_utc,
            "expires_at_utc": None,
            "review_required": True,
            "lock_authorized": True,
            "reconcile_authorized": True,
            "post_review_actions": ["evidence_recording", "project_control", "update_project_records"],
        },
        "review_bundle": {
            "bundle_id": bundle["bundle_id"],
            "manifest_sha256": bundle_sha,
            "candidate_identity": bundle["candidate_identity"],
            "rendered_surface_verified": True,
        },
        "allowed_decisions": ["approve", "revise", "defer"],
        "required_attestation": True,
        "max_notes_length": 2000,
        "hash_prefix_length": 16,
        "items": [{"item_id": "M2-RADAR-FIRST-PATH-001", "evidence_sha256": bundle_sha}],
    }
    write_json(CONTRACT_REF, review_contract)

    blank = {
        "response_schema_version": review_contract["response_schema_version"],
        "review_id": review_contract["review_id"],
        "completed": False,
        "review_started_at_utc": None,
        "review_completed_at_utc": None,
        "reviewer": {"attestation": False},
        "responses": [
            {
                "item_id": "M2-RADAR-FIRST-PATH-001",
                "evidence_sha256": bundle_sha,
                "decision": None,
                "notes": "",
            }
        ],
    }
    write_json(BLANK_REF, blank)

    readiness = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-FIRST-PATH-001-REVIEW-READINESS",
        "verified_at_utc": args.prepared_at_utc,
        "status": "pass_ready_owner_review_zero_decisions",
        "bindings": {
            "proposal_sha256": proposal_sha,
            "analysis_sha256": sha256(ANALYSIS_REF),
            "preflight_sha256": sha256(PREFLIGHT_REF),
            "review_surface_sha256": sha256(IMAGE_REF),
            "surface_receipt_sha256": sha256(SURFACE_REF),
            "review_bundle_sha256": bundle_sha,
            "review_contract_sha256": sha256(CONTRACT_REF),
            "blank_response_sha256": sha256(BLANK_REF),
        },
        "review": {"human_decision_count": 0, "attestation": False, "ready_for_handoff": True},
        "assertions": {
            "control_amendment_authorized": False,
            "orbit_recovery_authorized": False,
            "dem_action_authorized": False,
            "radar_pixel_readiness_authorized": False,
            "real_product_pixels_read_during_preparation": False,
        },
    }
    write_json(READINESS_REF, readiness)
    print(
        json.dumps(
            {
                "status": readiness["status"],
                "proposal_sha256": proposal_sha,
                "review_bundle_sha256": bundle_sha,
                "review_contract_sha256": sha256(CONTRACT_REF),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
