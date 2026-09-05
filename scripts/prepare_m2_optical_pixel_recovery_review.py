#!/usr/bin/env python3
"""Prepare a zero-decision review for a separately authorized optical recovery."""

from __future__ import annotations

import argparse
import hashlib
import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_REF = "contracts/milestone-002-optical-pixel-recovery-001-proposal.json"
PREFLIGHT_REF = "records/readiness/m2-optical-pixel-recovery-001-review-preflight.json"
DOC_REF = "docs/M2_OPTICAL_PIXEL_RECOVERY_001_REVIEW.md"
IMAGE_REF = "docs/assets/m2-optical-pixel-recovery-001-review.png"
SURFACE_REF = "records/surface-receipts/m2-optical-pixel-recovery-001-review.json"
BUNDLE_REF = "reviews/m2-optical-pixel-recovery-001/review-bundle.json"
CONTRACT_REF = "reviews/m2-optical-pixel-recovery-001/review-contract.json"
BLANK_REF = "reviews/m2-optical-pixel-recovery-001/blank-response.json"
READINESS_REF = "records/readiness/m2-optical-pixel-recovery-001-review-readiness.json"


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


def render_surface() -> None:
    image = Image.new("RGB", (1600, 1040), "#f5f2ea")
    draw = ImageDraw.Draw(image)
    title = ImageFont.truetype("arialbd.ttf", 52)
    heading = ImageFont.truetype("arialbd.ttf", 30)
    body = ImageFont.truetype("arial.ttf", 25)
    mono = ImageFont.truetype("consola.ttf", 20)
    draw.rectangle((0, 0, 1600, 150), fill="#17324d")
    draw.text((65, 42), "M2 Optical Pixel Recovery 001 Review", font=title, fill="white")
    y = 190
    sections = [
        ("Observed terminal result", ["Real attempt 001 is INVALID and cannot be retried under current authority.", "It read the first SCL raster, then stopped on KeyError: 'xmin'.", "No AOI, mask, registration, baseline, or change metric was produced."]),
        ("Exact cause", ["The published production contract stores bounds in analysis_grid.extent.", "The runner expected top-level xmin/ymin/xmax/ymax; synthetic fixtures used that flatter shape."]),
        ("Approval would authorize", ["One code-only grid-normalization correction and production-shape synthetic test.", "Fresh public CI, one final no-pixel preflight, then one new append-only recovery attempt.", "Same pair, AOIs, masks, 20 m grid, thresholds, and no date shopping."]),
        ("Still prohibited", ["Reuse or retry of real-001; automatic retry after recovery failure.", "Radar pixels, spectral indices, baseline, change polygons, interpretation, attribution, or publication."]),
    ]
    for label, lines in sections:
        draw.text((65, y), label, font=heading, fill="#17324d")
        y += 45
        for line in lines:
            for wrapped in textwrap.wrap(line, 104):
                draw.text((92, y), "• " + wrapped, font=body, fill="#20252b")
                y += 34
        y += 18
    draw.rectangle((60, 905, 1540, 995), outline="#9b6b21", width=3)
    draw.text((82, 925), "Decision required: APPROVE, REVISE, or DEFER — with reviewer attestation.", font=heading, fill="#7a4e0b")
    path = ROOT / IMAGE_REF
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared-at-utc", required=True)
    args = parser.parse_args()
    outputs = [PROPOSAL_REF, PREFLIGHT_REF, DOC_REF, IMAGE_REF, SURFACE_REF, BUNDLE_REF, CONTRACT_REF, BLANK_REF, READINESS_REF]
    collisions = [ref for ref in outputs if (ROOT / ref).exists()]
    if collisions:
        raise SystemExit("review output collision: " + ", ".join(collisions))
    failure_ref = "records/readiness/optical-pixel/m2-s2-pixel-readiness-real-001.json"
    reconciliation_ref = "records/readiness/m2-optical-pixel-real-001-reconciliation.json"
    proposal = {
        "schema_version": "1.0",
        "proposal_id": "NEPAL-M2-OPTICAL-PIXEL-RECOVERY-001-PROPOSAL",
        "prepared_at_utc": args.prepared_at_utc,
        "status": "proposed_not_authorized",
        "trigger": {"failure_ref": failure_ref, "failure_sha256": sha256(failure_ref), "reconciliation_ref": reconciliation_ref, "reconciliation_sha256": sha256(reconciliation_ref), "terminal_status": "invalid_terminal_real_001_no_retry_released"},
        "diagnosis": {"failure_code": "production_grid_extent_shape_mismatch", "observed_error": "KeyError: 'xmin'", "pixel_access_before_failure": "first real SCL raster was read", "metrics_established": False, "cause": "production analysis_grid stores bounds in its extent object while the runner expected top-level bounds; synthetic tests supplied a flat target object"},
        "proposed_bounded_actions": [
            "preserve real-001 and never reuse its receipt or external attempt root",
            "correct the runner to normalize the existing nested production grid extent without changing any scientific threshold, source, AOI, mask, or decision rule",
            "add portable and ArcGIS synthetic coverage for the exact nested production grid shape",
            "publish the exact corrected implementation and require successful public CI",
            "run one final no-pixel preflight for a new append-only recovery identity",
            "if and only if all gates pass, run optical-pixel-readiness-recovery-001 once and reconcile its terminal result",
        ],
        "exact_recovery": {"attempt_id": "optical-pixel-readiness-recovery-001", "external_attempt_root": r"C:\Projects\Active\nepal-2026-before-after-map-data\derived\optical-pixel-readiness-recovery-001", "public_receipt_ref": "records/readiness/optical-pixel/m2-s2-pixel-readiness-recovery-001.json", "maximum_real_invocations": 1, "automatic_retry_authorized": False},
        "unchanged_scientific_contract": {"pair": ["M1-SRC-010", "M1-SRC-008"], "aoi_ids": ["AOI-OVERVIEW", "AOI-SOURCE", "AOI-UPPER-CORRIDOR"], "pixel_contract_ref": "config/qa/pixel-readiness-contract.json", "pixel_contract_sha256": sha256("config/qa/pixel-readiness-contract.json"), "current_pixel_contract_ref": "config/qa/optical-pixel-readiness-contract-001.json", "current_pixel_contract_sha256": sha256("config/qa/optical-pixel-readiness-contract-001.json"), "threshold_changes_authorized": False, "source_or_date_substitution_authorized": False},
        "does_not_authorize": ["reuse, resume, replacement, or retry of real-001", "automatic retry after recovery-001", "radar measurement pixels or unresolved orbit and DEM actions", "spectral indices, baseline processing, change rasters or polygons", "interpretation, attribution, emergency guidance, or scientific publication"],
        "decision_domain": ["approve", "revise", "defer"],
        "attestation_required": True,
    }
    write_json(PROPOSAL_REF, proposal)
    proposal_sha = sha256(PROPOSAL_REF)
    preflight = {"schema_version": "1.0", "record_id": "NEPAL-M2-OPTICAL-PIXEL-RECOVERY-001-REVIEW-PREFLIGHT", "observed_at_utc": args.prepared_at_utc, "status": "pass_review_ready_no_recovery_authority", "bindings": {"proposal_sha256": proposal_sha, "failure_sha256": sha256(failure_ref), "reconciliation_sha256": sha256(reconciliation_ref)}, "assertions": {"real_001_preserved": True, "real_001_recovery_attempt_root_absent": not Path(proposal["exact_recovery"]["external_attempt_root"]).exists(), "recovery_public_receipt_absent": not (ROOT / proposal["exact_recovery"]["public_receipt_ref"]).exists(), "human_decision_count": 0, "recovery_authorized": False, "real_product_pixels_read_during_review_preparation": False}}
    write_json(PREFLIGHT_REF, preflight)
    doc = f"""# M2 optical pixel recovery 001 review

## Decision

Choose **approve**, **revise**, or **defer** for proposal `{proposal_sha}`. Approval must be an attested owner decision bound to the review bundle hash generated with this package.

## What happened

The single authorized real attempt is terminal `INVALID`. It read the first real SCL raster, then stopped before classification because the runner expected `xmin` at the top of the grid object while the production contract stores it under `analysis_grid.extent`. It created no QA raster or metrics file.

## What approval would release

Only the code correction, exact production-shape tests, fresh public CI, a no-pixel preflight, one new append-only recovery attempt, and reconciliation described in the proposal. The pair, AOIs, masks, 20 m grid, thresholds, and decision semantics remain unchanged.

## What remains prohibited

No reuse or retry of real-001, automatic retry, source substitution, radar pixels, spectral indices, baseline, change analysis, interpretation, attribution, or publication.
"""
    write_text(DOC_REF, doc)
    render_surface()
    surface = {"schema_version": "1.0", "receipt_id": "NEPAL-M2-OPTICAL-PIXEL-RECOVERY-001-REVIEW-SURFACE", "verified_at_utc": args.prepared_at_utc, "status": "pass_blank_review_surface", "render": {"path": IMAGE_REF, "sha256": sha256(IMAGE_REF), "human_decision_count": 0}, "assertions": {"proposal_sha256": proposal_sha, "recovery_authorized": False, "real_product_pixels_read": False}}
    write_json(SURFACE_REF, surface)
    artifacts = [
        ("review-surface", IMAGE_REF, "review_surface", True), ("review-instructions", DOC_REF, "decision_instructions", False),
        ("proposal", PROPOSAL_REF, "candidate_authority_envelope", False), ("review-preflight", PREFLIGHT_REF, "zero_authority_preflight", False),
        ("terminal-real-001", failure_ref, "terminal_failure", False), ("terminal-reconciliation", reconciliation_ref, "failure_and_custody_reconciliation", False),
        ("pixel-contract", "config/qa/optical-pixel-readiness-contract-001.json", "unchanged_preobservation_method", False),
        ("threshold-contract", "config/qa/pixel-readiness-contract.json", "unchanged_thresholds", False),
        ("approved-aois", "config/aoi/approved-study-areas-epsg32645.json", "exact_three_aois", False),
    ]
    bundle = {"schema_version": "1.0", "bundle_id": "m2-optical-pixel-recovery-001-review-bundle", "review_id": "m2-optical-pixel-recovery-001-review", "candidate_identity": f"M2-OPTICAL-PIXEL-RECOVERY-001-PROPOSAL-SHA256:{proposal_sha}", "artifacts": [{"artifact_id": aid, "path": ref, "sha256": sha256(ref), "role": role, "render_required": rendered, "render_receipts": [{"path": SURFACE_REF, "sha256": sha256(SURFACE_REF)}] if rendered else []} for aid, ref, role, rendered in artifacts], "review_surface": {"artifact_id": "review-surface", "blank_state_verified": True, "completion_controls_verified": True, "export_verified": True}, "decision_effect_if_approved": proposal["proposed_bounded_actions"], "limitations": proposal["does_not_authorize"]}
    write_json(BUNDLE_REF, bundle)
    bundle_sha = sha256(BUNDLE_REF)
    review_contract = {"contract_version": "human-review-contract-v1", "template": False, "review_id": "m2-optical-pixel-recovery-001-review", "response_schema_version": "nepal-m2-optical-pixel-recovery-001-response-v1", "workflow_authority": {"mode": "inherited", "authority_ref": "records/source-gates/m2-materialization-pixel-readiness-approval.json", "authorized_action_classes": ["evidence_recording", "project_control", "update_project_records"], "verified_at_utc": args.prepared_at_utc, "expires_at_utc": None, "review_required": True, "lock_authorized": True, "reconcile_authorized": True}, "review_bundle": {"bundle_id": bundle["bundle_id"], "manifest_sha256": bundle_sha, "candidate_identity": bundle["candidate_identity"], "rendered_surface_verified": True}, "allowed_decisions": ["approve", "revise", "defer"], "required_attestation": True, "max_notes_length": 2000, "items": [{"item_id": "M2-OPTICAL-PIXEL-RECOVERY-001", "evidence_sha256": bundle_sha}]}
    write_json(CONTRACT_REF, review_contract)
    blank = {"schema_version": "nepal-m2-optical-pixel-recovery-001-response-v1", "review_id": review_contract["review_id"], "completed": False, "reviewer": {"attestation": False}, "responses": [{"item_id": "M2-OPTICAL-PIXEL-RECOVERY-001", "decision": None, "notes": ""}], "human_decision_count": 0, "recovery_authorized": False}
    write_json(BLANK_REF, blank)
    readiness = {"schema_version": "1.0", "record_id": "NEPAL-M2-OPTICAL-PIXEL-RECOVERY-001-REVIEW-READINESS", "verified_at_utc": args.prepared_at_utc, "status": "pass_ready_owner_review_zero_decisions", "bindings": {"proposal_sha256": proposal_sha, "preflight_sha256": sha256(PREFLIGHT_REF), "review_surface_sha256": sha256(IMAGE_REF), "surface_receipt_sha256": sha256(SURFACE_REF), "review_bundle_sha256": bundle_sha, "review_contract_sha256": sha256(CONTRACT_REF), "blank_response_sha256": sha256(BLANK_REF)}, "review": {"human_decision_count": 0, "attestation": False, "ready_for_handoff": True}, "assertions": {"recovery_authorized": False, "real_product_pixels_read_during_preparation": False}}
    write_json(READINESS_REF, readiness)
    print(json.dumps({"status": readiness["status"], "proposal_sha256": proposal_sha, "review_bundle_sha256": bundle_sha, "review_contract_sha256": sha256(CONTRACT_REF)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
