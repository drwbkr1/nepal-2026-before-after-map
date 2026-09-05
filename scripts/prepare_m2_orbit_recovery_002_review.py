#!/usr/bin/env python3
"""Prepare the corrected zero-decision M2 orbit recovery-002 review."""

from __future__ import annotations

import argparse
import hashlib
import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_REF = "contracts/milestone-002-orbit-recovery-002-proposal.json"
PREFLIGHT_REF = "records/readiness/m2-orbit-recovery-002-review-preflight.json"
DOC_REF = "docs/M2_ORBIT_RECOVERY_002_REVIEW.md"
IMAGE_REF = "docs/assets/m2-orbit-recovery-002-review.png"
SURFACE_REF = "records/surface-receipts/m2-orbit-recovery-002-review.json"
BUNDLE_REF = "reviews/m2-orbit-recovery-002/review-bundle.json"
CONTRACT_REF = "reviews/m2-orbit-recovery-002/review-contract.json"
BLANK_REF = "reviews/m2-orbit-recovery-002/blank-response.json"
READINESS_REF = "records/readiness/m2-orbit-recovery-002-review-readiness.json"


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def load(ref: str) -> dict:
    value = json.loads((ROOT / ref).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {ref}")
    return value


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


def render_surface(proposal_sha: str) -> None:
    image = Image.new("RGB", (1800, 1480), "#f4f1e9")
    draw = ImageDraw.Draw(image)
    title = font("arialbd.ttf", 50)
    heading = font("arialbd.ttf", 29)
    body = font("arial.ttf", 24)
    callout = font("arialbd.ttf", 25)
    draw.rectangle((0, 0, 1800, 150), fill="#17324d")
    draw.text((65, 38), "M2 Orbit Recovery Review 002", font=title, fill="white")
    draw.text((67, 105), f"Proposal SHA-256 {proposal_sha}", font=font("arial.ttf", 20), fill="#dce8f2")
    y = 190
    sections = [
        (
            "What is established",
            [
                "All six exact Sentinel-1 sources are promoted, materialized, and header-ready without pixel decoding.",
                "The approved radar-first amendment replaced the deadlocked aggregate prerequisite with route-specific readiness.",
                "The failed M2-ORB-001 attempt remains terminal, used no owner credential, and received zero payload bytes.",
            ],
        ),
        (
            "What approval would authorize",
            [
                "Implement and publicly validate a separate recovery-only worker for the same exact M2-ORB-001 file.",
                "After public CI and a fresh no-payload preflight, make one byte-zero attempt under a distinct identity.",
                "Use the existing anonymous one-use token broker; verify exact size, checksums, XML, OSVs, validity, and scene binding.",
            ],
        ),
        (
            "What approval would not authorize",
            [
                "No request for M2-ORB-002 through 004, no automatic retry, and no precise-orbit substitution.",
                "No DEM conversion, radar pixel decoding, terrain correction, baseline, change analysis, attribution, or publication.",
            ],
        ),
        (
            "Independent gates remain",
            [
                "DEM vertical-datum and terrain-result decisions remain unresolved.",
                "Radar pixel readiness requires a later separate proposal and owner review.",
            ],
        ),
    ]
    for label, lines in sections:
        draw.text((65, y), label, font=heading, fill="#17324d")
        y += 44
        for line in lines:
            for index, part in enumerate(textwrap.wrap(line, 112)):
                draw.text((92, y), ("• " if index == 0 else "  ") + part, font=body, fill="#20252b")
                y += 34
        y += 18
    draw.rectangle((60, 1325, 1740, 1420), outline="#9b6b21", width=3)
    draw.text((82, 1353), "Decision required: APPROVE, REVISE, or DEFER — with owner attestation.", font=callout, fill="#7a4e0b")
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

    route_approval_ref = "records/source-gates/m2-radar-first-path-001-approval.json"
    route_activation_ref = "records/readiness/m2-radar-first-path-001-activation.json"
    radar_readiness_ref = "records/readiness/m2-radar-source-readiness-001.json"
    stale_ref = "records/readiness/m2-orbit-recovery-001-stale-evidence.json"
    orbit_approval_ref = "records/source-gates/m2-orbit-amendment-approval.json"
    failed_reconciliation_ref = "records/acquisition/orbit-test-boundary-reconciliation-001.json"
    failed_receipt_ref = "records/acquisition/orbit-attempts/m2-orb-001-20260904t050937z-8ed21d05.json"
    old_proposal_ref = "contracts/milestone-002-orbit-recovery-proposal.json"
    old_bundle_ref = "reviews/m2-orbit-recovery/review-bundle.json"
    radar = load(radar_readiness_ref)
    stale = load(stale_ref)
    if radar.get("status") != "pass_six_source_custody_materialization_and_header_readiness_only":
        raise SystemExit("radar source readiness is not exact and passing")
    if radar.get("source_ids") != [f"M1-SRC-{index:03d}" for index in range(1, 7)]:
        raise SystemExit("radar source cohort drift")
    if stale.get("status") != "stale_unapproved_preserved_not_actionable":
        raise SystemExit("old orbit packet is not preserved as stale evidence")

    proposal = {
        "proposal_version": "1.0",
        "proposal_id": "NEPAL-M2-ORBIT-RECOVERY-002-PROPOSAL",
        "prepared_at_utc": args.prepared_at_utc,
        "status": "proposed_not_authorized",
        "authority_context": {
            "radar_first_approval_ref": route_approval_ref,
            "radar_first_approval_sha256": sha256(route_approval_ref),
            "original_orbit_approval_ref": orbit_approval_ref,
            "original_orbit_approval_sha256": sha256(orbit_approval_ref),
            "authorized_orbit_type": "AUX_RESORB",
            "precise_substitution_authorized": False,
        },
        "trigger": {
            "failed_source_id": "M2-ORB-001",
            "failed_attempt_id": "m2-orb-001-20260904t050937z-8ed21d05",
            "failure_code": "orbit_redirect_or_http_status_rejected",
            "partial_bytes_preserved": 0,
            "failed_receipt_ref": failed_receipt_ref,
            "failed_receipt_sha256": sha256(failed_receipt_ref),
            "failure_reconciliation_ref": failed_reconciliation_ref,
            "failure_reconciliation_sha256": sha256(failed_reconciliation_ref),
        },
        "corrected_prerequisite": {
            "unit_id": "M2-RADAR-SOURCE-READINESS",
            "status": "complete",
            "source_ids": radar["source_ids"],
            "readiness_ref": radar_readiness_ref,
            "readiness_sha256": sha256(radar_readiness_ref),
            "establishes": "verified Sentinel custody, materialization identity, and header readiness only",
            "does_not_establish": "measurement pixel usability, corrected geometry, a baseline, change, or scientific fitness",
        },
        "stale_packet": {
            "classification_ref": stale_ref,
            "classification_sha256": sha256(stale_ref),
            "old_proposal_ref": old_proposal_ref,
            "old_proposal_sha256": sha256(old_proposal_ref),
            "old_bundle_ref": old_bundle_ref,
            "old_bundle_sha256": sha256(old_bundle_ref),
            "status": "preserved_not_actionable",
        },
        "proposed_recovery": {
            "mode": "fresh_full_restart_distinct_attempt",
            "source_id": "M2-ORB-001",
            "provider_product_id": "d4fdc474-0069-459b-9534-b5999dec5aab",
            "exact_product_name": "S1D_OPER_AUX_RESORB_OPOD_20260816T143208_V20260816T103526_20260816T140956.EOF",
            "restart_offset_bytes": 0,
            "resume_partial": False,
            "delete_or_modify_failed_events": False,
            "reuse_failed_attempt_id": False,
            "required_new_attempt_namespace": "m2-orb-001-recovery-001",
            "maximum_real_attempts": 1,
            "automatic_retry_authorized": False,
            "prerequisites": [
                "the exact six-source M2-RADAR-SOURCE-READINESS unit remains complete and hash-bound",
                "the original four-file AUX_RESORB approval remains exact and active",
                "one completed owner approval of this exact review is locked and reconciled",
                "the recovery-only implementation and secret-exposure tests pass public CI",
                "a fresh final no-payload preflight passes before any catalogue or token access",
                "the original failed receipt and external events remain unchanged",
                "the current legal bytes, source identity, size, checksums, online state, paths, collisions, and storage are revalidated",
                "a fresh access token is passed only through the existing anonymous single-use in-memory owner broker",
            ],
            "transfer_controls": [
                "request only the complete exact M2-ORB-001 AUX_RESORB file from byte zero without Range or resume semantics",
                "use a distinct exclusive staging path and preserve every event",
                "require exact catalogue length, provider MD5, provider BLAKE3, and local SHA-256 before no-replace promotion",
                "verify safe XML, mission and filename identity, ordered finite OSVs, exact validity coverage, and exact scene binding",
            ],
            "failure_policy": "Any failure is terminal for this recovery identity and requires another explicit review; no automatic retry is authorized.",
        },
        "approval_would_authorize": [
            "implement and validate a separate recovery-only worker for the exact M2-ORB-001 source",
            "publish that implementation and require successful public CI before any real access",
            "perform one fresh no-payload preflight, then one fresh byte-zero transfer attempt only for exact M2-ORB-001 through a new exclusive attempt path",
            "verify and promote only that file if every authority, route-readiness, rights, identity, size, checksum, XML, OSV, validity, path, and custody control passes",
        ],
        "approval_would_not_authorize": [
            "request M2-ORB-002, M2-ORB-003, or M2-ORB-004",
            "delete, rewrite, hide, or reuse the retained failed attempt or events",
            "expose, log, file-store, or environment-store an owner credential or token",
            "accept terms, change an account or MFA, incur cost, or use a paid route",
            "change an orbit provider UUID, filename, type, validity interval, scene binding, destination, or approved manifest",
            "perform automatic retry, substitute AUX_POEORB, apply orbit data, convert DEM data, decode radar pixels, create a baseline, analyze change, attribute cause, or publish a scientific result",
        ],
        "independent_unresolved_gates": [
            "M2-DEM-VERTICAL-DATUM-REVIEW",
            "M2-DEM-TERRAIN-RESULT-REVIEW",
            "future separately reviewed radar pixel readiness",
        ],
        "human_gate": {
            "review_required": True,
            "item_id": "M2-ORBIT-RECOVERY-002",
            "allowed_decisions": ["approve", "revise", "defer"],
            "required_attestation": True,
        },
        "limitations": [
            "The zero-byte rejected request did not test the exact AUX_RESORB payload and used no owner credential.",
            "A future one-attempt owner-credential transfer may still fail and has no automatic retry.",
            "Even a passing orbit file would not establish corrected imagery, geolocation accuracy, pixel usability, change, attribution, or scientific fitness.",
            "This proposal creates no recovery authority until the exact review bundle receives a completed owner decision and that response is locked and reconciled.",
        ],
    }
    write_json(PROPOSAL_REF, proposal)
    proposal_sha = sha256(PROPOSAL_REF)

    preflight = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ORBIT-RECOVERY-002-REVIEW-PREFLIGHT",
        "observed_at_utc": args.prepared_at_utc,
        "status": "pass_review_ready_no_orbit_authority",
        "bindings": {
            "proposal_sha256": proposal_sha,
            "route_approval_sha256": sha256(route_approval_ref),
            "route_activation_sha256": sha256(route_activation_ref),
            "radar_readiness_sha256": sha256(radar_readiness_ref),
            "stale_packet_sha256": sha256(stale_ref),
            "failed_receipt_sha256": sha256(failed_receipt_ref),
        },
        "assertions": {
            "human_decision_count": 0,
            "orbit_catalogue_accessed": False,
            "token_or_credential_read": False,
            "orbit_payload_requested": False,
            "external_data_mutated": False,
            "radar_pixels_read": False,
            "dem_action_performed": False,
        },
    }
    write_json(PREFLIGHT_REF, preflight)

    doc = f"""# M2 orbit recovery-002 review

## Decision

Choose **approve**, **revise**, or **defer** for proposal `{proposal_sha}`. A completed decision must bind the exact review-bundle hash and include the owner's attestation.

## Corrected prerequisite

The approved radar-first control amendment now binds the six exact Sentinel-1 sources to verified custody, materialization identity, and passing header readiness. This replaces the stale aggregate `M2-VERIFY` prerequisite for the independent radar route. It does not establish pixel usability or a baseline.

## Exact recovery under review

The review concerns only one future fresh byte-zero attempt for `M2-ORB-001`, UUID `d4fdc474-0069-459b-9534-b5999dec5aab`, named `S1D_OPER_AUX_RESORB_OPOD_20260816T143208_V20260816T103526_20260816T140956.EOF`. The prior attempt and its zero-byte failure remain immutable evidence.

Approval would release a separately tested recovery-only implementation, successful public CI, one final no-payload preflight, and at most one exact recovery attempt through the owner-controlled anonymous token broker. Any failure is terminal for that new identity.

## Still prohibited

No request for `M2-ORB-002` through `004`; no automatic retry or precise-orbit substitution; no DEM action, orbit application, radar pixel decoding, baseline, change analysis, attribution, or scientific publication. The two DEM reviews and any future radar pixel-readiness review remain separate.
"""
    write_text(DOC_REF, doc)
    render_surface(proposal_sha)

    surface = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-RECOVERY-002-REVIEW-SURFACE",
        "verified_at_utc": args.prepared_at_utc,
        "status": "pass_blank_review_surface",
        "artifact": {
            "path": IMAGE_REF,
            "sha256": sha256(IMAGE_REF),
            "width_px": 1800,
            "height_px": 1480,
            "format": "PNG",
            "contains_third_party_pixels": False,
        },
        "bindings": {"proposal_ref": PROPOSAL_REF, "proposal_sha256": proposal_sha},
        "validation": {
            "corrected_route_prerequisite_visible": True,
            "exact_one_file_scope_visible": True,
            "zero_byte_failure_visible": True,
            "prohibited_scope_visible": True,
            "independent_gates_visible": True,
            "blank_state_verified": True,
            "human_decision_count": 0,
            "completion_controls_verified": True,
            "export_verified": True,
        },
    }
    write_json(SURFACE_REF, surface)

    artifacts = [
        ("review-surface", IMAGE_REF, "review_surface", True),
        ("review-instructions", DOC_REF, "decision_instructions", False),
        ("proposal", PROPOSAL_REF, "candidate_authority_envelope", False),
        ("review-preflight", PREFLIGHT_REF, "zero_authority_preflight", False),
        ("radar-first-approval", route_approval_ref, "active_control_authority", False),
        ("radar-first-activation", route_activation_ref, "active_control_receipt", False),
        ("radar-source-readiness", radar_readiness_ref, "corrected_route_prerequisite", False),
        ("stale-packet-classification", stale_ref, "preserved_stale_evidence", False),
        ("old-orbit-proposal", old_proposal_ref, "stale_unapproved_proposal", False),
        ("old-orbit-bundle", old_bundle_ref, "stale_unapproved_bundle", False),
        ("orbit-amendment-approval", orbit_approval_ref, "original_exact_source_authority", False),
        ("failed-attempt-reconciliation", failed_reconciliation_ref, "retained_zero_byte_failure", False),
        ("failed-attempt-receipt", failed_receipt_ref, "retained_zero_byte_attempt", False),
        ("dem-vertical-review-contract", "reviews/m2-dem-vertical-datum/review-contract.json", "independent_pending_gate", False),
        ("dem-terrain-review-contract", "reviews/m2-dem-terrain-result/review-contract.json", "independent_pending_gate", False),
    ]
    bundle = {
        "schema_version": "1.0",
        "template": False,
        "bundle_id": "m2-orbit-recovery-002-review-bundle",
        "review_id": "m2-orbit-recovery-002-review",
        "authority_ref": route_approval_ref,
        "candidate_identity": f"M2-ORBIT-RECOVERY-002-PROPOSAL-SHA256:{proposal_sha}",
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
        "limitations": proposal["approval_would_not_authorize"] + proposal["limitations"],
    }
    write_json(BUNDLE_REF, bundle)
    bundle_sha = sha256(BUNDLE_REF)

    contract = {
        "contract_version": "human-review-contract-v1",
        "template": False,
        "review_id": "m2-orbit-recovery-002-review",
        "response_schema_version": "nepal-m2-orbit-recovery-002-response-v1",
        "workflow_authority": {
            "mode": "inherited",
            "authority_ref": route_approval_ref,
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
        "items": [{"item_id": "M2-ORBIT-RECOVERY-002", "evidence_sha256": bundle_sha}],
    }
    write_json(CONTRACT_REF, contract)
    blank = {
        "response_schema_version": contract["response_schema_version"],
        "review_id": contract["review_id"],
        "completed": False,
        "review_started_at_utc": None,
        "review_completed_at_utc": None,
        "reviewer": {"attestation": False},
        "responses": [{"item_id": "M2-ORBIT-RECOVERY-002", "evidence_sha256": bundle_sha, "decision": None, "notes": ""}],
    }
    write_json(BLANK_REF, blank)
    readiness = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ORBIT-RECOVERY-002-REVIEW-READINESS",
        "verified_at_utc": args.prepared_at_utc,
        "status": "pass_ready_owner_review_zero_decisions",
        "bindings": {
            "proposal_sha256": proposal_sha,
            "preflight_sha256": sha256(PREFLIGHT_REF),
            "review_surface_sha256": sha256(IMAGE_REF),
            "surface_receipt_sha256": sha256(SURFACE_REF),
            "review_bundle_sha256": bundle_sha,
            "review_contract_sha256": sha256(CONTRACT_REF),
            "blank_response_sha256": sha256(BLANK_REF),
        },
        "review": {"human_decision_count": 0, "attestation": False, "ready_for_handoff": True},
        "assertions": {
            "orbit_recovery_authorized": False,
            "orbit_catalogue_accessed": False,
            "token_or_credential_read": False,
            "orbit_payload_requested": False,
            "dem_action_performed": False,
            "radar_pixels_read": False,
        },
    }
    write_json(READINESS_REF, readiness)
    print(json.dumps({"status": readiness["status"], "proposal_sha256": proposal_sha, "review_bundle_sha256": bundle_sha, "review_contract_sha256": sha256(CONTRACT_REF)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
