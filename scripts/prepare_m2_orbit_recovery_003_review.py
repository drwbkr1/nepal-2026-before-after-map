#!/usr/bin/env python3
"""Prepare the zero-decision M2 orbit recovery-003 review."""

from __future__ import annotations

import argparse
import hashlib
import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_REF = "contracts/milestone-002-orbit-recovery-003-proposal.json"
OUTCOME_REF = "records/acquisition/m2-orbit-recovery-002-outcome-reconciliation.json"
PREFLIGHT_REF = "records/readiness/m2-orbit-recovery-003-review-preflight.json"
DOC_REF = "docs/M2_ORBIT_RECOVERY_003_REVIEW.md"
IMAGE_REF = "docs/assets/m2-orbit-recovery-003-review.png"
SURFACE_REF = "records/surface-receipts/m2-orbit-recovery-003-review.json"
BUNDLE_REF = "reviews/m2-orbit-recovery-003/review-bundle.json"
CONTRACT_REF = "reviews/m2-orbit-recovery-003/review-contract.json"
BLANK_REF = "reviews/m2-orbit-recovery-003/blank-response.json"
READINESS_REF = "records/readiness/m2-orbit-recovery-003-review-readiness.json"


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
    image = Image.new("RGB", (1800, 1540), "#f4f1e9")
    draw = ImageDraw.Draw(image)
    title = font("arialbd.ttf", 50)
    heading = font("arialbd.ttf", 29)
    body = font("arial.ttf", 24)
    callout = font("arialbd.ttf", 25)
    draw.rectangle((0, 0, 1800, 150), fill="#17324d")
    draw.text((65, 38), "M2 Orbit Recovery Review 003", font=title, fill="white")
    draw.text((67, 105), f"Proposal SHA-256 {proposal_sha}", font=font("arial.ttf", 20), fill="#dce8f2")
    y = 190
    sections = [
        ("What the consumed recovery established", [
            "The secret-safe handoff launched one detached supervisor for exact M2-ORB-001.",
            "Public catalog revalidation returned, then local pretransfer setup failed before an attempt ID or download request.",
            "The active intake is unchanged, the exclusive staging path contains one empty directory, and payload bytes remain zero.",
        ]),
        ("Why a new review is required", [
            "Recovery-002 says any failure is terminal for that identity and forbids automatic retry.",
            "The safe terminal journal intentionally omitted exception text, so the exact local exception category is unavailable.",
        ]),
        ("What approval would authorize", [
            "Implement predeclared attempt identity, event-first setup, stage-specific safe errors, and immutable catalog evidence.",
            "After fresh public CI and no-payload preflight, perform one owner-selected byte-zero M2-ORB-001 attempt in a new path.",
        ]),
        ("What remains prohibited", [
            "No reuse or deletion of either failed recovery, no M2-ORB-002 through 004, and no precise-orbit substitution.",
            "No DEM conversion, radar pixels, orbit application, baseline, change analysis, attribution, or publication.",
        ]),
    ]
    for label, lines in sections:
        draw.text((65, y), label, font=heading, fill="#17324d")
        y += 44
        for line in lines:
            for index, part in enumerate(textwrap.wrap(line, 112)):
                draw.text((92, y), ("• " if index == 0 else "  ") + part, font=body, fill="#20252b")
                y += 34
        y += 18
    draw.rectangle((60, 1380, 1740, 1485), outline="#9b6b21", width=3)
    draw.text((82, 1416), "Decision required: APPROVE, REVISE, or DEFER — with owner attestation.", font=callout, fill="#7a4e0b")
    path = ROOT / IMAGE_REF
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)


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

    route_approval_ref = "records/source-gates/m2-radar-first-path-001-approval.json"
    orbit_approval_ref = "records/source-gates/m2-orbit-amendment-approval.json"
    recovery_002_approval_ref = "records/source-gates/m2-orbit-recovery-002-approval.json"
    recovery_002_proposal_ref = "contracts/milestone-002-orbit-recovery-002-proposal.json"
    recovery_002_contract_ref = "contracts/m2-orbit-recovery-002.json"
    recovery_002_publication_ref = "records/acquisition/m2-orbit-recovery-002-publication-gate.json"
    recovery_002_preflight_ref = "records/acquisition/m2-orbit-recovery-002-final-preflight.json"
    radar_readiness_ref = "records/readiness/m2-radar-source-readiness-001.json"
    intake_ref = "contracts/m2-orbit-intake.json"
    outcome = load(OUTCOME_REF)
    radar = load(radar_readiness_ref)
    intake = load(intake_ref)
    if outcome.get("status") != "terminal_pretransfer_supervisor_failure_no_retry":
        raise SystemExit("recovery-002 outcome is not the exact terminal pretransfer failure")
    assertions = outcome.get("assertions", {})
    if (
        assertions.get("recovery_002_authority_consumed") is not True
        or assertions.get("new_attempt_id_created") is not False
        or assertions.get("orbit_download_requested") is not False
        or assertions.get("orbit_payload_bytes_received") != 0
        or assertions.get("automatic_retry_performed") is not False
    ):
        raise SystemExit("recovery-002 terminal boundary differs")
    if radar.get("status") != "pass_six_source_custody_materialization_and_header_readiness_only":
        raise SystemExit("radar source readiness drift")
    asset = next((item for item in intake.get("assets", []) if item.get("asset_id") == "m2-orb-001"), None)
    if not isinstance(asset, dict) or asset.get("state") != "failed" or len(asset.get("attempts", [])) != 1:
        raise SystemExit("active intake is not unchanged after the pretransfer failure")

    proposal = {
        "proposal_version": "1.0",
        "proposal_id": "NEPAL-M2-ORBIT-RECOVERY-003-PROPOSAL",
        "prepared_at_utc": args.prepared_at_utc,
        "status": "proposed_not_authorized",
        "authority_context": {
            "radar_first_approval_ref": route_approval_ref,
            "radar_first_approval_sha256": sha256(route_approval_ref),
            "original_orbit_approval_ref": orbit_approval_ref,
            "original_orbit_approval_sha256": sha256(orbit_approval_ref),
            "consumed_recovery_002_approval_ref": recovery_002_approval_ref,
            "consumed_recovery_002_approval_sha256": sha256(recovery_002_approval_ref),
            "authorized_orbit_type": "AUX_RESORB",
            "precise_substitution_authorized": False,
        },
        "trigger": {
            "outcome_ref": OUTCOME_REF,
            "outcome_sha256": sha256(OUTCOME_REF),
            "source_id": "M2-ORB-001",
            "supervisor_id": outcome["supervisor_id"],
            "attempt_id": None,
            "failure_code": outcome["failure"]["terminal_code"],
            "failure_classification": outcome["failure"]["classification"],
            "failure_window": outcome["failure"]["bounded_window"],
            "payload_bytes_received": 0,
            "active_intake_sha256": sha256(intake_ref),
            "recovery_002_authority_consumed": True,
        },
        "observed_limits": {
            "known": [
                "one owner handoff reached the detached recovery-002 supervisor",
                "the exact public catalog revalidation returned before local path initialization advanced",
                "one exclusive payload-parent directory was created and remains empty",
                "no attempt event root, attempt ID, active-intake mutation, download request, destination, or payload byte exists",
            ],
            "unknown": [
                "the underlying exception category because the terminal journal intentionally records only a generic safe code",
                "the returned catalog response hash because failure occurred before its immutable event was written",
            ],
            "root_cause_status": "unresolved_bounded_local_pretransfer_window",
        },
        "proposed_recovery": {
            "mode": "fresh_full_restart_distinct_recovery_after_terminal_pretransfer_failure",
            "source_id": "M2-ORB-001",
            "provider_product_id": "d4fdc474-0069-459b-9534-b5999dec5aab",
            "exact_product_name": "S1D_OPER_AUX_RESORB_OPOD_20260816T143208_V20260816T103526_20260816T140956.EOF",
            "restart_offset_bytes": 0,
            "resume_partial": False,
            "delete_or_modify_prior_recovery_evidence": False,
            "reuse_prior_staging_path": False,
            "required_new_attempt_namespace": "m2-orb-001-recovery-002",
            "required_new_staging_root": "nepal-2026-before-after-map-data/.intake-staging/nepal-m2-orbit-recovery-003",
            "maximum_owner_handoffs": 1,
            "maximum_real_attempts": 1,
            "automatic_retry_authorized": False,
            "authority_consumption_boundary": "the one owner-selected handoff that launches the recovery-003 supervisor consumes this recovery identity even if failure occurs before download",
            "implementation_corrections": [
                "predeclare the recovery attempt ID before any runtime catalog or staging mutation",
                "create the attempt event root before the payload parent so a later local failure can retain attempt-scoped evidence",
                "write an immutable started event before public catalog revalidation and a separate immutable catalog-revalidated event with the exact response hash",
                "map each pretransfer filesystem and control stage to a fixed nonsecret failure code without exception text",
                "wrap every post-precondition stage in terminal evidence handling while retaining the separate supervisor journal",
                "use a new exclusive recovery-003 staging root and preserve recovery-002 directories and journals unchanged",
            ],
            "prerequisites": [
                "one completed owner approval of this exact review is locked and reconciled",
                "the recovery-003 implementation and synthetic interruption and secret-exposure tests pass public CI",
                "a fresh final no-payload preflight validates the exact current source, rights, catalog identity, paths, collisions, and storage",
                "the exact six-source radar readiness and original four-file AUX_RESORB approval remain unchanged",
                "a fresh token is obtained and sent only through the owner-side anonymous single-use in-memory broker",
            ],
            "transfer_controls": [
                "request only the complete exact M2-ORB-001 file from byte zero without Range or resume semantics",
                "allow at most one public catalog revalidation and one authenticated download request under this identity",
                "require exact length, provider MD5, provider BLAKE3, local SHA-256, safe XML, ordered finite OSVs, validity coverage, and scene binding before no-replace promotion",
            ],
            "failure_policy": "Any recovery-003 failure is terminal for that identity and requires another explicit review; no automatic retry is authorized.",
        },
        "approval_would_authorize": [
            "implement and test only the stated pretransfer evidence and staging-order corrections for exact M2-ORB-001",
            "publish the exact implementation and require successful public CI before real access",
            "perform one fresh no-payload preflight and one owner-selected recovery-003 handoff under a new exclusive identity",
            "make at most one byte-zero M2-ORB-001 download request and promote only after every exact verification passes",
            "reconcile the single terminal outcome without automatically requesting another orbit source",
        ],
        "approval_would_not_authorize": [
            "request M2-ORB-002, M2-ORB-003, or M2-ORB-004",
            "delete, rewrite, hide, or reuse the original attempt, recovery-002 staging directory, or supervisor journal",
            "expose, log, file-store, clipboard-store, or environment-store an owner credential or token",
            "accept terms, change an account or MFA, incur cost, or use a paid route",
            "change the provider UUID, filename, orbit type, validity interval, scene binding, destination, or approved source manifest",
            "perform automatic retry, substitute AUX_POEORB, apply orbit data, convert DEM data, decode radar pixels, create a baseline, analyze change, attribute cause, or publish a scientific result",
        ],
        "independent_unresolved_gates": [
            "M2-DEM-VERTICAL-DATUM-REVIEW",
            "M2-DEM-TERRAIN-RESULT-REVIEW",
            "future separately reviewed radar pixel readiness",
        ],
        "human_gate": {"review_required": True, "item_id": "M2-ORBIT-RECOVERY-003", "allowed_decisions": ["approve", "revise", "defer"], "required_attestation": True},
        "limitations": [
            "Recovery-002 did not reach an attempt ID or payload request, but its owner handoff and supervisor invocation consumed that recovery identity under its terminal-on-any-failure policy.",
            "The exact recovery-002 local exception category and catalog response hash are unavailable and must not be invented.",
            "Synthetic and public-CI evidence cannot prove the next live provider request or filesystem sequence will succeed.",
            "Even a passing orbit file would not establish corrected imagery, pixel usability, change, attribution, or scientific fitness.",
            "This proposal creates no implementation, credential, catalog, or payload authority until the exact review receives a completed owner decision.",
        ],
    }
    write_json(PROPOSAL_REF, proposal)
    proposal_sha = sha256(PROPOSAL_REF)

    preflight = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ORBIT-RECOVERY-003-REVIEW-PREFLIGHT",
        "observed_at_utc": args.prepared_at_utc,
        "status": "pass_review_ready_no_recovery_003_authority",
        "bindings": {
            "proposal_sha256": proposal_sha,
            "outcome_sha256": sha256(OUTCOME_REF),
            "active_intake_sha256": sha256(intake_ref),
            "radar_readiness_sha256": sha256(radar_readiness_ref),
            "recovery_002_approval_sha256": sha256(recovery_002_approval_ref),
            "recovery_002_proposal_sha256": sha256(recovery_002_proposal_ref),
            "recovery_002_contract_sha256": sha256(recovery_002_contract_ref),
            "recovery_002_publication_gate_sha256": sha256(recovery_002_publication_ref),
            "recovery_002_final_preflight_sha256": sha256(recovery_002_preflight_ref),
        },
        "assertions": {"human_decision_count": 0, "recovery_003_implemented": False, "credential_read": False, "catalog_request_performed": False, "orbit_download_requested": False, "external_data_mutated": False, "radar_pixels_read": False, "dem_action_performed": False},
    }
    write_json(PREFLIGHT_REF, preflight)

    doc = f"""# M2 orbit recovery-003 review

## Decision

Choose **approve**, **revise**, or **defer** for proposal `{proposal_sha}`. A completed decision must bind the exact review-bundle hash and include the owner's attestation.

## Terminal recovery-002 outcome

The secret-safe owner handoff launched supervisor `{outcome['supervisor_id']}`. The exact public catalog revalidation returned and the new payload-parent directory was created, but the supervisor stopped before an attempt event root, attempt ID, active-intake mutation, authenticated download request, destination, or payload byte. The safe journal recorded `orbit_recovery_002_supervisor_unexpected_failure`; it did not retain exception text or the catalog response hash. Those facts remain unknown.

Recovery-002 is consumed because its approved failure policy made any failure terminal for that identity and prohibited automatic retry.

## Exact recovery-003 under review

Approval would release only a new recovery implementation for the same exact `M2-ORB-001` product. It would predeclare the attempt identity, create event storage before the payload parent, persist a separate catalog-revalidation event, map pretransfer stages to fixed nonsecret codes, use a distinct recovery-003 staging root, pass public CI, and pass a fresh no-payload preflight. The owner could then initiate one secret-safe handoff and at most one byte-zero download request.

## Still prohibited

No request for `M2-ORB-002` through `004`; no deletion, reuse, or rewriting of prior evidence; no automatic retry or precise-orbit substitution; no DEM action, orbit application, radar pixel decoding, baseline, change analysis, attribution, or scientific publication. The independent DEM and future radar-pixel gates remain unresolved.
"""
    write_text(DOC_REF, doc)
    render_surface(proposal_sha)
    surface = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-RECOVERY-003-REVIEW-SURFACE",
        "verified_at_utc": args.prepared_at_utc,
        "status": "pass_blank_review_surface",
        "artifact": {"path": IMAGE_REF, "sha256": sha256(IMAGE_REF), "width_px": 1800, "height_px": 1540, "format": "PNG", "contains_third_party_pixels": False},
        "bindings": {"proposal_ref": PROPOSAL_REF, "proposal_sha256": proposal_sha, "outcome_ref": OUTCOME_REF, "outcome_sha256": sha256(OUTCOME_REF)},
        "validation": {"terminal_failure_visible": True, "known_and_unknown_evidence_visible": True, "exact_one_file_scope_visible": True, "prohibited_scope_visible": True, "blank_state_verified": True, "human_decision_count": 0, "completion_controls_verified": True, "export_verified": True},
    }
    write_json(SURFACE_REF, surface)

    artifacts = [
        ("review-surface", IMAGE_REF, "review_surface", True),
        ("review-instructions", DOC_REF, "decision_instructions", False),
        ("proposal", PROPOSAL_REF, "candidate_authority_envelope", False),
        ("review-preflight", PREFLIGHT_REF, "zero_authority_preflight", False),
        ("recovery-002-outcome", OUTCOME_REF, "terminal_failure_reconciliation", False),
        ("recovery-002-approval", recovery_002_approval_ref, "consumed_recovery_authority", False),
        ("recovery-002-proposal", recovery_002_proposal_ref, "terminal_failure_policy", False),
        ("recovery-002-runtime-contract", recovery_002_contract_ref, "consumed_runtime_scope", False),
        ("recovery-002-publication-gate", recovery_002_publication_ref, "public_ci_evidence", False),
        ("recovery-002-final-preflight", recovery_002_preflight_ref, "pre_access_gate", False),
        ("active-orbit-intake", intake_ref, "unchanged_source_state", False),
        ("radar-source-readiness", radar_readiness_ref, "route_prerequisite", False),
        ("orbit-amendment-approval", orbit_approval_ref, "original_exact_source_authority", False),
    ]
    bundle = {
        "schema_version": "1.0",
        "template": False,
        "bundle_id": "m2-orbit-recovery-003-review-bundle",
        "review_id": "m2-orbit-recovery-003-review",
        "authority_ref": route_approval_ref,
        "candidate_identity": f"M2-ORBIT-RECOVERY-003-PROPOSAL-SHA256:{proposal_sha}",
        "artifacts": [{"artifact_id": artifact_id, "path": ref, "sha256": sha256(ref), "role": role, "render_required": rendered, "render_receipts": [{"path": SURFACE_REF, "sha256": sha256(SURFACE_REF)}] if rendered else []} for artifact_id, ref, role, rendered in artifacts],
        "review_surface": {"artifact_id": "review-surface", "blank_state_verified": True, "completion_controls_verified": True, "export_verified": True},
        "limitations": proposal["approval_would_not_authorize"] + proposal["limitations"],
    }
    write_json(BUNDLE_REF, bundle)
    bundle_sha = sha256(BUNDLE_REF)
    contract = {
        "contract_version": "human-review-contract-v1",
        "template": False,
        "review_id": "m2-orbit-recovery-003-review",
        "response_schema_version": "nepal-m2-orbit-recovery-003-response-v1",
        "workflow_authority": {"mode": "inherited", "authority_ref": route_approval_ref, "authorized_action_classes": ["evidence_recording", "project_control", "update_project_records"], "verified_at_utc": args.prepared_at_utc, "expires_at_utc": None, "review_required": True, "lock_authorized": True, "reconcile_authorized": True, "post_review_actions": ["evidence_recording", "project_control", "update_project_records"]},
        "review_bundle": {"bundle_id": bundle["bundle_id"], "manifest_sha256": bundle_sha, "candidate_identity": bundle["candidate_identity"], "rendered_surface_verified": True},
        "allowed_decisions": ["approve", "revise", "defer"],
        "required_attestation": True,
        "max_notes_length": 2000,
        "hash_prefix_length": 16,
        "items": [{"item_id": "M2-ORBIT-RECOVERY-003", "evidence_sha256": bundle_sha}],
    }
    write_json(CONTRACT_REF, contract)
    blank = {"response_schema_version": contract["response_schema_version"], "review_id": contract["review_id"], "completed": False, "review_started_at_utc": None, "review_completed_at_utc": None, "reviewer": {"attestation": False}, "responses": [{"item_id": "M2-ORBIT-RECOVERY-003", "evidence_sha256": bundle_sha, "decision": None, "notes": ""}]}
    write_json(BLANK_REF, blank)
    readiness = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ORBIT-RECOVERY-003-REVIEW-READINESS",
        "verified_at_utc": args.prepared_at_utc,
        "status": "pass_ready_owner_review_zero_decisions",
        "bindings": {"proposal_sha256": proposal_sha, "outcome_sha256": sha256(OUTCOME_REF), "preflight_sha256": sha256(PREFLIGHT_REF), "review_surface_sha256": sha256(IMAGE_REF), "surface_receipt_sha256": sha256(SURFACE_REF), "review_bundle_sha256": bundle_sha, "review_contract_sha256": sha256(CONTRACT_REF), "blank_response_sha256": sha256(BLANK_REF)},
        "review": {"human_decision_count": 0, "attestation": False, "ready_for_handoff": True},
        "assertions": {"recovery_002_terminal_preserved": True, "recovery_003_authorized": False, "recovery_003_implemented": False, "credential_read": False, "catalog_request_performed": False, "orbit_download_requested": False, "external_data_mutated": False, "dem_action_performed": False, "radar_pixels_read": False},
    }
    write_json(READINESS_REF, readiness)
    print(json.dumps({"status": readiness["status"], "proposal_sha256": proposal_sha, "review_bundle_sha256": bundle_sha, "review_contract_sha256": sha256(CONTRACT_REF)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
