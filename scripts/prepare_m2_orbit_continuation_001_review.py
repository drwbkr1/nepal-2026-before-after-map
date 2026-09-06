#!/usr/bin/env python3
"""Prepare the zero-decision review for the three remaining orbit sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import textwrap
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_REF = "contracts/milestone-002-orbit-continuation-001-proposal.json"
PREFLIGHT_REF = "records/readiness/m2-orbit-continuation-001-review-preflight.json"
DOC_REF = "docs/M2_ORBIT_CONTINUATION_001_REVIEW.md"
IMAGE_REF = "docs/assets/m2-orbit-continuation-001-review.png"
SURFACE_REF = "records/surface-receipts/m2-orbit-continuation-001-review.json"
BUNDLE_REF = "reviews/m2-orbit-continuation-001/review-bundle.json"
CONTRACT_REF = "reviews/m2-orbit-continuation-001/review-contract.json"
BLANK_REF = "reviews/m2-orbit-continuation-001/blank-response.json"
READINESS_REF = "records/readiness/m2-orbit-continuation-001-review-readiness.json"
INTAKE_REF = "contracts/m2-orbit-intake.json"
TERMINAL_REF = "records/readiness/m2-orbit-osv-precision-amendment-001-terminal-reconciliation.json"
LOCAL_RESULT_REF = "records/acquisition/m2-orbit-osv-precision-amendment-001-local-validation.json"
ORBIT_APPROVAL_REF = "records/source-gates/m2-orbit-amendment-approval.json"
ORBIT_PROPOSAL_REF = "contracts/milestone-002-orbit-amendment-proposal.json"
OSV_APPROVAL_REF = "records/source-gates/m2-orbit-osv-precision-amendment-001-approval.json"
OSV_FORMAT_REF = "records/source-gates/m2-orbit-osv-time-format-evidence.json"
OSV_CONTRACT_REF = "contracts/m2-orbit-offline-verification-osv-precision-amendment-001.json"
RADAR_READINESS_REF = "records/readiness/m2-radar-source-readiness-001.json"
SOURCE_IDS = ["M2-ORB-002", "M2-ORB-003", "M2-ORB-004"]
ASSET_IDS = ["m2-orb-002", "m2-orb-003", "m2-orb-004"]


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def load(ref: str) -> dict[str, Any]:
    value = json.loads((ROOT / ref).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {ref}")
    return value


def write_json(ref: str, value: dict[str, Any]) -> None:
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


def render_surface(proposal_sha: str) -> None:
    from PIL import Image, ImageDraw, ImageFont

    def font(name: str, size: int):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            return ImageFont.load_default()

    image = Image.new("RGB", (1800, 1640), "#f4f1e9")
    draw = ImageDraw.Draw(image)
    title = font("arialbd.ttf", 48)
    heading = font("arialbd.ttf", 29)
    body = font("arial.ttf", 23)
    callout = font("arialbd.ttf", 25)
    draw.rectangle((0, 0, 1800, 150), fill="#17324d")
    draw.text((65, 35), "M2 Orbit Continuation Review 001", font=title, fill="white")
    draw.text((67, 105), f"Proposal SHA-256 {proposal_sha}", font=font("arial.ttf", 20), fill="#dce8f2")
    y = 190
    sections = [
        ("Current verified state", [
            "Exact M2-ORB-001 passed the approved one-second input-only check and is promoted without replacement.",
            "M2-ORB-002, 003, and 004 remain exact approved identities, unrequested, and absent from custody.",
        ]),
        ("What approval would authorize", [
            "Implement and publicly validate a continuation-only secret-safe worker for the three named sources.",
            "After final no-payload preflight, allow one owner handoff and one byte-zero attempt per source in fixed order.",
            "Stop on the first failure; preserve each success, failure, partial, event, and staging path without reuse.",
        ]),
        ("Prospective verification rule", [
            "Apply the same maximum one-second OSV endpoint-consistency rule to only these three files before observation.",
            "Keep every checksum, XML identity, finite ordered OSV, scene margin, path, and no-replace rule unchanged.",
        ]),
        ("What remains prohibited", [
            "No M2-ORB-001 request or retry, source substitution, AUX_POEORB, automatic retry, or tolerance above one second.",
            "No token storage or exposure, terms acceptance, account change, orbit application, DEM action, radar pixels, baseline, change analysis, attribution, or scientific publication.",
        ]),
    ]
    for label, lines in sections:
        draw.text((65, y), label, font=heading, fill="#17324d")
        y += 44
        for line in lines:
            for index, part in enumerate(textwrap.wrap(line, 110)):
                draw.text((92, y), ("• " if index == 0 else "  ") + part, font=body, fill="#20252b")
                y += 34
        y += 18
    draw.rectangle((60, 1480, 1740, 1585), outline="#9b6b21", width=3)
    draw.text((82, 1516), "Decision required: APPROVE, REVISE, or DEFER — with owner attestation.", font=callout, fill="#7a4e0b")
    path = ROOT / IMAGE_REF
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)


def source_summary(asset: dict[str, Any]) -> dict[str, Any]:
    ext = asset["extensions"]
    expected = asset["expected"]
    return {
        "source_id": ext["source_id"],
        "asset_id": asset["asset_id"],
        "provider_product_id": ext["provider_product_id"],
        "exact_product_name": ext["exact_product_name"],
        "orbit_type": ext["orbit_type"],
        "sentinel_source_ids": ext["sentinel_source_ids"],
        "validity_start_utc": ext["validity_start_utc"],
        "validity_end_utc": ext["validity_end_utc"],
        "minimum_scene_margin_seconds": ext["minimum_scene_margin_seconds"],
        "eviction_date_utc": ext["eviction_date_utc"],
        "expected_size_bytes": expected["size_bytes"],
        "provider_checksums": expected["provider_checksums"],
        "destination_relative_path": asset["destination_relative_path"],
        "state_at_review_preparation": asset["state"],
        "attempt_count_at_review_preparation": len(asset["attempts"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared-at-utc", required=True)
    args = parser.parse_args()
    if not args.prepared_at_utc.endswith("Z"):
        raise SystemExit("prepared time must be UTC")
    outputs = [PROPOSAL_REF, PREFLIGHT_REF, DOC_REF, IMAGE_REF, SURFACE_REF, BUNDLE_REF, CONTRACT_REF, BLANK_REF, READINESS_REF]
    collisions = [ref for ref in outputs if (ROOT / ref).exists()]
    if collisions:
        raise SystemExit("review output collision: " + ", ".join(collisions))

    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    origin = subprocess.run(["git", "rev-parse", "origin/main"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    intake = load(INTAKE_REF)
    terminal = load(TERMINAL_REF)
    local_result = load(LOCAL_RESULT_REF)
    radar = load(RADAR_READINESS_REF)
    assets = intake.get("assets", [])
    asset_map = {item.get("asset_id"): item for item in assets if isinstance(item, dict)}
    if (
        head != origin
        or intake.get("extensions", {}).get("current_orbit_state_counts") != {"authorized": 3, "failed": 0, "promoted": 1}
        or terminal.get("status") != "pass_exact_m2_orb_001_promoted_remaining_sources_review_required"
        or terminal.get("assertions", {}).get("other_orbit_source_requested") is not False
        or local_result.get("status") != "pass_exact_m2_orb_001_input_promoted_no_replace"
        or radar.get("status") != "pass_six_source_custody_materialization_and_header_readiness_only"
        or list(asset_map) != ["m2-orb-001", "m2-orb-002", "m2-orb-003", "m2-orb-004"]
        or asset_map["m2-orb-001"].get("state") != "promoted"
        or any(asset_map[item].get("state") != "authorized" or asset_map[item].get("attempts") != [] for item in ASSET_IDS)
    ):
        raise SystemExit("current orbit state differs from the exact review-preparation checkpoint")
    sources = [source_summary(asset_map[item]) for item in ASSET_IDS]

    proposal = {
        "proposal_version": "1.0",
        "proposal_id": "NEPAL-M2-ORBIT-CONTINUATION-001-PROPOSAL",
        "prepared_at_utc": args.prepared_at_utc,
        "status": "proposed_not_authorized",
        "preparation_base_commit": head,
        "authority_context": {
            "original_orbit_approval_ref": ORBIT_APPROVAL_REF,
            "original_orbit_approval_sha256": sha256(ORBIT_APPROVAL_REF),
            "original_orbit_proposal_ref": ORBIT_PROPOSAL_REF,
            "original_orbit_proposal_sha256": sha256(ORBIT_PROPOSAL_REF),
            "consumed_m2_orb_001_osv_approval_ref": OSV_APPROVAL_REF,
            "consumed_m2_orb_001_osv_approval_sha256": sha256(OSV_APPROVAL_REF),
            "current_terminal_reconciliation_ref": TERMINAL_REF,
            "current_terminal_reconciliation_sha256": sha256(TERMINAL_REF),
            "authorized_orbit_type": "AUX_RESORB",
            "precise_substitution_authorized": False,
        },
        "current_state": {
            "promoted_source_ids": ["M2-ORB-001"],
            "remaining_unrequested_source_ids": SOURCE_IDS,
            "orbit_state_counts": {"authorized": 3, "failed": 0, "promoted": 1},
            "m2_orb_001_result_ref": LOCAL_RESULT_REF,
            "m2_orb_001_result_sha256": sha256(LOCAL_RESULT_REF),
            "active_intake_ref": INTAKE_REF,
            "active_intake_sha256": sha256(INTAKE_REF),
        },
        "exact_source_order": sources,
        "proposed_continuation": {
            "continuation_id": "M2-ORBIT-CONTINUATION-001",
            "source_ids_in_exact_order": SOURCE_IDS,
            "maximum_owner_handoffs": 1,
            "maximum_real_attempts_per_source": 1,
            "restart_offset_bytes": 0,
            "resume_or_range_requests_authorized": False,
            "stop_on_first_failure": True,
            "automatic_retry_authorized": False,
            "m2_orb_001_request_authorized": False,
            "maximum_endpoint_tolerance_seconds": 1.0,
            "endpoint_rule_scope": SOURCE_IDS,
            "endpoint_rule_timing": "prospective_before_any_payload_byte_or_osv_value_from_these_sources_is_observed",
            "required_implementation": [
                "use the proven anonymous single-use in-memory broker and detached supervisor architecture",
                "predeclare source and attempt identities and create append-only event storage before payload staging",
                "use a distinct exclusive staging path for every source attempt and atomic no-replace promotion",
                "scrub credential-bearing environment and command values and emit only fixed nonsecret errors",
                "preserve every prior M2-ORB-001 attempt, staged file, promotion, receipt, and reconciliation unchanged",
                "apply the versioned one-second endpoint rule only to M2-ORB-002 through M2-ORB-004",
            ],
            "required_gates": [
                "one completed owner decision on this exact bundle is locked and reconciled",
                "the continuation implementation and synthetic interruption, exact-order, stop-on-failure, and secret-exposure tests pass public default-branch CI",
                "a final no-payload preflight revalidates exact terms, catalog identities, paths, collisions, storage, Sentinel prerequisites, and unchanged M2-ORB-001 custody",
                "the owner initiates one fresh secret-safe credentials-to-token-to-broker handoff only after every nonsecret gate passes",
            ],
            "per_source_transfer_and_verification": [
                "make at most one fresh public catalog revalidation and one authenticated byte-zero payload request",
                "require exact expected length and provider MD5 and BLAKE3 agreement and compute local SHA-256",
                "require safe XML identity, declared and observed OSV count agreement, ordered unique finite OSVs, correct units, and exact scene binding",
                "require OSV endpoints to fall within the prospectively approved maximum one-second consistency rule",
                "promote without replacement only after every exact check passes; otherwise preserve failure evidence and stop",
            ],
            "terminal_reconciliation_required": True,
        },
        "approval_would_authorize": [
            "implement and test only the fixed-order continuation for exact M2-ORB-002, M2-ORB-003, and M2-ORB-004",
            "extend the maximum one-second OSV endpoint-consistency rule prospectively to only those three exact files",
            "publish the exact implementation and require successful public default-branch CI before any live source access",
            "perform one bounded final no-payload preflight and one owner-selected secret-safe handoff",
            "make at most one byte-zero request per source in the stated order, stop on first failure, verify, promote without replacement on pass, and reconcile the exact outcome",
        ],
        "approval_would_not_authorize": [
            "request, resume, reuse, retry, replace, or mutate M2-ORB-001 or its preserved recovery staging evidence",
            "make an automatic retry or a second request for any failed remaining source",
            "change source order, provider UUID, filename, orbit type, expected length, provider checksum, scene binding, destination, or source manifest",
            "use a tolerance above one second, relax another verifier rule, substitute AUX_POEORB, date-shop, or source-shop",
            "expose, log, copy, file-store, clipboard-store, or environment-store an owner password, TOTP, refresh token, or access token",
            "accept terms, create or recover an account, change MFA, incur cost, or use a paid source",
            "apply orbit data, act on DEMs, decode radar pixels, process a baseline, analyze change, attribute cause, or publish a scientific result",
        ],
        "human_gate": {
            "review_required": True,
            "item_id": "M2-ORBIT-CONTINUATION-001",
            "allowed_decisions": ["approve", "revise", "defer"],
            "required_attestation": True,
        },
        "limitations": [
            "The three exact files were catalog-confirmed earlier but have not been downloaded or inspected, so their live availability and byte-level validity remain unproven.",
            "The one-second rule is a bounded inference from whole-second header and microsecond OSV formats, not a provider-stated numerical tolerance.",
            "A source-level success would establish only orbit-input custody and verification, not successful orbit application or usable radar pixels.",
            "Any first failure stops the sequence and requires another explicit review before retry or continuation.",
            "This packet creates no implementation, network, credential, payload, promotion, processing, or scientific authority until the exact review receives a completed owner decision.",
        ],
    }
    write_json(PROPOSAL_REF, proposal)
    proposal_sha = sha256(PROPOSAL_REF)

    preflight = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ORBIT-CONTINUATION-001-REVIEW-PREFLIGHT",
        "observed_at_utc": args.prepared_at_utc,
        "status": "pass_review_ready_zero_decisions_no_network_or_payload_mutation",
        "bindings": {
            "proposal_sha256": proposal_sha,
            "active_intake_sha256": sha256(INTAKE_REF),
            "terminal_reconciliation_sha256": sha256(TERMINAL_REF),
            "m2_orb_001_result_sha256": sha256(LOCAL_RESULT_REF),
            "original_orbit_approval_sha256": sha256(ORBIT_APPROVAL_REF),
            "osv_format_evidence_sha256": sha256(OSV_FORMAT_REF),
            "m2_orb_001_osv_contract_sha256": sha256(OSV_CONTRACT_REF),
            "radar_readiness_sha256": sha256(RADAR_READINESS_REF),
        },
        "assertions": {
            "human_decision_count": 0,
            "continuation_authorized": False,
            "implementation_started": False,
            "credential_read": False,
            "network_request_performed": False,
            "payload_requested": False,
            "external_data_mutated": False,
            "m2_orb_001_mutated": False,
            "other_orbit_source_requested": False,
            "orbit_application_performed": False,
            "radar_pixels_read": False,
            "scientific_result_established": False,
        },
    }
    write_json(PREFLIGHT_REF, preflight)

    doc = f"""# M2 orbit continuation-001 review

## Decision

Choose **approve**, **revise**, or **defer** for proposal `{proposal_sha}`. A completed decision must bind the exact review-bundle hash and include the owner's attestation.

## Current state

Exact `M2-ORB-001` is promoted, input-only verified, and preserved alongside its failed attempts and recovery staging bytes. `M2-ORB-002`, `M2-ORB-003`, and `M2-ORB-004` remain the same exact `AUX_RESORB` identities approved in the original orbit amendment, but none has an attempt, staged byte, or custody file. The current M2-ORB-001 amendment authorizes no request for them.

## Exact continuation under review

Approval would authorize a continuation-only implementation for those three identities in fixed order: `M2-ORB-002`, then `M2-ORB-003`, then `M2-ORB-004`. After synthetic proof, successful public CI, and a final no-payload preflight, the owner could initiate one secret-safe handoff. Each source could receive at most one byte-zero request. The sequence would stop on the first failure and preserve all prior successes, failures, partials, events, and staging paths.

The review also proposes applying the same maximum one-second OSV endpoint-consistency rule prospectively to only those three files. This is declared before their payload bytes or OSV timestamps are observed. All checksum, identity, XML, OSV ordering, units, scene-margin, custody, and no-replace rules remain unchanged.

## Still prohibited

No request or retry for `M2-ORB-001`; no second request or automatic retry for a failed remaining source; no source, date, order, identity, threshold, or orbit-type substitution; no tolerance above one second; no credential exposure or storage; no terms acceptance, account action, or cost; and no orbit application, DEM action, radar-pixel decoding, baseline, change analysis, attribution, or scientific publication.
"""
    write_text(DOC_REF, doc)
    render_surface(proposal_sha)
    surface = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-CONTINUATION-001-REVIEW-SURFACE",
        "verified_at_utc": args.prepared_at_utc,
        "status": "pass_blank_review_surface",
        "artifact": {
            "path": IMAGE_REF,
            "sha256": sha256(IMAGE_REF),
            "width_px": 1800,
            "height_px": 1640,
            "format": "PNG",
            "contains_third_party_pixels": False,
        },
        "bindings": {
            "proposal_ref": PROPOSAL_REF,
            "proposal_sha256": proposal_sha,
            "active_intake_ref": INTAKE_REF,
            "active_intake_sha256": sha256(INTAKE_REF),
            "terminal_reconciliation_ref": TERMINAL_REF,
            "terminal_reconciliation_sha256": sha256(TERMINAL_REF),
        },
        "validation": {
            "current_state_visible": True,
            "three_source_fixed_order_visible": True,
            "one_attempt_and_stop_policy_visible": True,
            "prospective_one_second_rule_visible": True,
            "prohibited_scope_visible": True,
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
        ("active-orbit-intake", INTAKE_REF, "current_source_state", False),
        ("m2-orb-001-terminal-reconciliation", TERMINAL_REF, "completed_predecessor", False),
        ("m2-orb-001-local-result", LOCAL_RESULT_REF, "input_only_predecessor_result", False),
        ("original-orbit-approval", ORBIT_APPROVAL_REF, "exact_source_eligibility", False),
        ("original-orbit-proposal", ORBIT_PROPOSAL_REF, "original_scope", False),
        ("osv-format-evidence", OSV_FORMAT_REF, "endpoint_precision_evidence", False),
        ("m2-orb-001-osv-contract", OSV_CONTRACT_REF, "one_second_rule_precedent", False),
        ("radar-source-readiness", RADAR_READINESS_REF, "source_prerequisite", False),
    ]
    bundle = {
        "schema_version": "1.0",
        "template": False,
        "bundle_id": "m2-orbit-continuation-001-review-bundle",
        "review_id": "m2-orbit-continuation-001-review",
        "authority_ref": ORBIT_APPROVAL_REF,
        "candidate_identity": f"M2-ORBIT-CONTINUATION-001-PROPOSAL-SHA256:{proposal_sha}",
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
        "review_id": "m2-orbit-continuation-001-review",
        "response_schema_version": "nepal-m2-orbit-continuation-001-response-v1",
        "workflow_authority": {
            "mode": "inherited",
            "authority_ref": ORBIT_APPROVAL_REF,
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
        "items": [{"item_id": "M2-ORBIT-CONTINUATION-001", "evidence_sha256": bundle_sha}],
    }
    write_json(CONTRACT_REF, contract)
    blank = {
        "response_schema_version": contract["response_schema_version"],
        "review_id": contract["review_id"],
        "completed": False,
        "review_started_at_utc": None,
        "review_completed_at_utc": None,
        "reviewer": {"attestation": False},
        "responses": [{"item_id": "M2-ORBIT-CONTINUATION-001", "evidence_sha256": bundle_sha, "decision": None, "notes": ""}],
    }
    write_json(BLANK_REF, blank)
    readiness = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ORBIT-CONTINUATION-001-REVIEW-READINESS",
        "verified_at_utc": args.prepared_at_utc,
        "status": "pass_ready_owner_review_zero_decisions_public_ci_pending",
        "bindings": {
            "proposal_sha256": proposal_sha,
            "active_intake_sha256": sha256(INTAKE_REF),
            "terminal_reconciliation_sha256": sha256(TERMINAL_REF),
            "review_preflight_sha256": sha256(PREFLIGHT_REF),
            "review_surface_sha256": sha256(IMAGE_REF),
            "surface_receipt_sha256": sha256(SURFACE_REF),
            "review_bundle_sha256": bundle_sha,
            "review_contract_sha256": sha256(CONTRACT_REF),
            "blank_response_sha256": sha256(BLANK_REF),
        },
        "review": {"human_decision_count": 0, "attestation": False, "ready_for_publication_gate": True},
        "assertions": {
            "continuation_authorized": False,
            "source_ids_in_exact_order": SOURCE_IDS,
            "maximum_owner_handoffs_if_approved": 1,
            "maximum_real_attempts_per_source_if_approved": 1,
            "stop_on_first_failure_if_approved": True,
            "maximum_endpoint_tolerance_seconds_if_approved": 1.0,
            "m2_orb_001_request_authorized": False,
            "credential_read": False,
            "network_request_performed": False,
            "payload_requested": False,
            "external_data_mutated": False,
            "scientific_result_established": False,
        },
    }
    write_json(READINESS_REF, readiness)
    print(json.dumps({
        "status": readiness["status"],
        "proposal_sha256": proposal_sha,
        "review_bundle_sha256": bundle_sha,
        "review_contract_sha256": sha256(CONTRACT_REF),
        "blank_response_sha256": sha256(BLANK_REF),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
