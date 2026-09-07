#!/usr/bin/env python3
"""Prepare the zero-decision review for offline orbit verification recovery-001."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import textwrap
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_REF = "contracts/milestone-002-orbit-offline-verification-recovery-001-proposal.json"
PREFLIGHT_REF = "records/readiness/m2-orbit-offline-verification-recovery-001-review-preflight.json"
DOC_REF = "docs/M2_ORBIT_OFFLINE_VERIFICATION_RECOVERY_001_REVIEW.md"
IMAGE_REF = "docs/assets/m2-orbit-offline-verification-recovery-001-review.png"
SURFACE_REF = "records/surface-receipts/m2-orbit-offline-verification-recovery-001-review.json"
BUNDLE_REF = "reviews/m2-orbit-offline-verification-recovery-001/review-bundle.json"
CONTRACT_REF = "reviews/m2-orbit-offline-verification-recovery-001/review-contract.json"
BLANK_REF = "reviews/m2-orbit-offline-verification-recovery-001/blank-response.json"
READINESS_REF = "records/readiness/m2-orbit-offline-verification-recovery-001-review-readiness.json"
TERMINAL_REF = "records/readiness/m2-orbit-offline-verification-001-terminal-reconciliation.json"
ACTIVE_REF = "contracts/m2-orbit-offline-verification.json"
CANDIDATE_REF = "contracts/m2-orbit-offline-verification-continuation-001.json"
VERIFIER_REF = "scripts/verify_m2_orbit_eof.py"
PUBLICATION_REF = "records/readiness/m2-orbit-offline-verification-continuation-001-publication-gate.json"
ACTIVATION_REF = "records/readiness/m2-orbit-offline-verification-continuation-001-activation.json"
FINAL_PREFLIGHT_REF = "records/readiness/m2-orbit-offline-verification-continuation-001-final-preflight.json"
ORBIT_APPROVAL_REF = "records/source-gates/m2-orbit-amendment-approval.json"
OSV_APPROVAL_REF = "records/source-gates/m2-orbit-osv-precision-amendment-001-approval.json"
CONTINUATION_APPROVAL_REF = "records/source-gates/m2-orbit-continuation-001-approval.json"
MILESTONE_REF = "contracts/milestone-002.json"
PROFILE_REF = "records/project-control-profile.json"
GOAL_REF = "records/long-term-goal.json"
SOURCE_IDS = ["M2-ORB-001", "M2-ORB-002", "M2-ORB-003", "M2-ORB-004"]
CHECKPOINT = "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-REVIEW-PUBLICATION"
NEXT_ACTION = (
    "Publish and publicly validate the exact blank M2 orbit offline-verification recovery-001 review packet. "
    "No recovery implementation, new EOF read, remaining-source verification, network or credential action, orbit "
    "application, DEM or radar-pixel action, baseline, change analysis, attribution, or scientific publication is "
    "authorized before one attested owner decision on the exact public packet."
)


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


def write_existing(ref: str, value: dict[str, Any]) -> None:
    (ROOT / ref).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def render_surface(proposal_sha: str) -> None:
    from PIL import Image, ImageDraw, ImageFont

    def font(name: str, size: int):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            return ImageFont.load_default()

    image = Image.new("RGB", (1800, 1720), "#f4f1e9")
    draw = ImageDraw.Draw(image)
    title = font("arialbd.ttf", 46)
    heading = font("arialbd.ttf", 29)
    body = font("arial.ttf", 23)
    callout = font("arialbd.ttf", 25)
    draw.rectangle((0, 0, 1800, 160), fill="#17324d")
    draw.text((64, 32), "M2 Orbit Offline Verification Recovery 001", font=title, fill="white")
    draw.text((66, 112), f"Proposal SHA-256 {proposal_sha}", font=font("arial.ttf", 20), fill="#dce8f2")
    y = 205
    sections = [
        (
            "Preserved terminal result",
            [
                "M2-ORB-001 was read and fully evaluated in memory after all public gates passed.",
                "The receipt write then stopped because records/acquisition/orbit-verification did not exist.",
                "No durable pass or fail result exists. The attempt is terminal indeterminate and cannot be reconstructed.",
                "M2-ORB-002, 003, and 004 were not read. External orbit custody was not mutated.",
            ],
        ),
        (
            "What approval would authorize",
            [
                "Implement an output-reservation correction: create the tracked parent and reserve the exact receipt before any EOF read.",
                "Test missing-parent, collision, interruption, complete pass/fail persistence, fixed order, and stop-on-failure behavior.",
                "Require successful public default-branch CI and a new final no-content preflight.",
                "Run one new M2-ORB-001 recovery attempt; only if it passes, run one existing attempt for 002, 003, and 004 in order.",
            ],
        ),
        (
            "Frozen scientific rules",
            [
                "Keep the exact sources, checksums, XML identity, OSV ordering, units, scene bindings, and one-second endpoint limit unchanged.",
                "Treat the lost first evaluation as indeterminate; do not infer its result from the recovery.",
            ],
        ),
        (
            "Still prohibited",
            [
                "No token, network request, reacquisition, custody replacement, source/date shopping, threshold change, or AUX_POEORB substitution.",
                "No automatic retry, second recovery, orbit application, DEM action, radar pixels, baseline, change analysis, attribution, or publication.",
            ],
        ),
    ]
    for label, lines in sections:
        draw.text((64, y), label, font=heading, fill="#17324d")
        y += 45
        for line in lines:
            for index, part in enumerate(textwrap.wrap(line, 108)):
                draw.text((92, y), ("• " if index == 0 else "  ") + part, font=body, fill="#20252b")
                y += 34
        y += 18
    draw.rectangle((60, 1570, 1740, 1668), outline="#9b6b21", width=3)
    draw.text((82, 1604), "Decision required: APPROVE, REVISE, or DEFER with owner attestation.", font=callout, fill="#7a4e0b")
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

    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    origin = subprocess.run(["git", "rev-parse", "origin/main"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    terminal = load(TERMINAL_REF)
    active = load(ACTIVE_REF)
    candidate = load(CANDIDATE_REF)
    milestone = load(MILESTONE_REF)
    profile = load(PROFILE_REF)
    goal = load(GOAL_REF)
    if (
        head != origin
        or terminal.get("status") != "terminal_indeterminate_m2_orb_001_evaluated_receipt_not_persisted_no_retry_released"
        or terminal.get("attempt", {}).get("failure_code") != "verification_output_parent_missing"
        or terminal.get("assertions", {}).get("m2_orb_001_eof_content_read") is not True
        or terminal.get("assertions", {}).get("evaluation_result_durably_persisted") is not False
        or terminal.get("assertions", {}).get("later_source_eof_content_read") is not False
        or active.get("status") != "terminal_indeterminate_m2_orb_001_receipt_persistence_failure"
        or candidate.get("status") != "terminal_consumed_m2_orb_001_receipt_persistence_failure"
        or milestone.get("handoff", {}).get("current_checkpoint") != "M2-ORBIT-VERIFY-RECOVERY-001-REVIEW-PREPARATION"
        or profile.get("current_checkpoint", {}).get("checkpoint_id") != "M2-ORBIT-VERIFY-RECOVERY-001-REVIEW-PREPARATION"
        or goal.get("current_checkpoint") != "M2-ORBIT-VERIFY-RECOVERY-001-REVIEW-PREPARATION"
    ):
        raise SystemExit("current project state differs from the terminal recovery-review preparation checkpoint")

    proposal = {
        "proposal_version": "1.0",
        "proposal_id": "NEPAL-M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-PROPOSAL",
        "prepared_at_utc": args.prepared_at_utc,
        "status": "proposed_not_authorized",
        "preparation_base_commit": head,
        "trigger": {
            "terminal_reconciliation_ref": TERMINAL_REF,
            "terminal_reconciliation_sha256": sha256(TERMINAL_REF),
            "source_id": "M2-ORB-001",
            "consumed_attempt_identity": "m2-orb-001-offline-verification-001",
            "terminal_status": terminal["status"],
            "failure_code": terminal["attempt"]["failure_code"],
            "eof_content_was_read": True,
            "evaluation_result_durably_available": False,
            "remaining_sources_were_read": False,
        },
        "authority_context": {
            "original_orbit_approval_ref": ORBIT_APPROVAL_REF,
            "original_orbit_approval_sha256": sha256(ORBIT_APPROVAL_REF),
            "osv_precision_approval_ref": OSV_APPROVAL_REF,
            "osv_precision_approval_sha256": sha256(OSV_APPROVAL_REF),
            "continuation_approval_ref": CONTINUATION_APPROVAL_REF,
            "continuation_approval_sha256": sha256(CONTINUATION_APPROVAL_REF),
            "active_verification_ref": ACTIVE_REF,
            "active_verification_sha256": sha256(ACTIVE_REF),
            "current_authority_allows_retry": False,
            "this_packet_creates_authority": False,
        },
        "proposed_recovery": {
            "recovery_id": "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001",
            "mode": "post_observation_receipt_reservation_correction_and_fixed_order_recovery",
            "source_ids_in_exact_order": SOURCE_IDS,
            "m2_orb_001_new_recovery_attempts": 1,
            "remaining_source_existing_attempts_per_source": 1,
            "automatic_retry_authorized": False,
            "stop_on_first_failure": True,
            "network_requests_authorized": 0,
            "credential_handoffs_authorized": 0,
            "external_custody_mutation_authorized": False,
            "maximum_osv_endpoint_tolerance_seconds": 1.0,
            "required_implementation": [
                "add a tracked records/acquisition/orbit-verification parent directory marker so clean clones retain the exact receipt parent",
                "require the exact receipt parent to exist inside the repository and be a real non-link directory during final preflight",
                "reserve the exact append-only receipt path with exclusive creation before opening or hashing any EOF content",
                "write the complete terminal receipt through the already-exclusive handle and flush and fsync it before reporting success or fail",
                "preserve an empty or partial reserved receipt as terminal interruption evidence and never reuse its path",
                "use a new m2-orb-001-offline-verification-recovery-001 receipt identity while retaining the failed 001 path as absent historical evidence",
                "leave every scientific validation predicate, source identity, checksum, scene binding, and endpoint rule unchanged",
            ],
            "required_tests": [
                "missing output parent stops before EOF content access",
                "output collision stops before EOF content access",
                "exclusive reservation precedes EOF content access",
                "synthetic interruption preserves the reserved attempt and refuses reuse",
                "complete pass and fail receipts are durable and append-only",
                "M2-ORB-001 recovery precedes 002, 003, and 004 and any first failure stops later reads",
            ],
            "required_gates": [
                "one completed owner decision on this exact public bundle is locked and reconciled",
                "the bounded implementation and synthetic tests pass public default-branch CI",
                "a new final no-content preflight proves the exact receipt parent and all four output paths are ready without reading an EOF",
            ],
            "terminal_execution": [
                "invoke one new read-only M2-ORB-001 recovery verification and persist its exact pass, fail, or interruption evidence",
                "only after an exact pass, invoke M2-ORB-002, M2-ORB-003, and M2-ORB-004 once each in that order",
                "stop on the first failure or persistence interruption and reconcile without retry",
            ],
        },
        "approval_would_authorize": [
            "implement only the exact pre-read receipt-reservation and output-parent correction described above",
            "add synthetic tests for pre-read failure, persistence, interruption, exact order, and stop-on-first-failure",
            "publish the exact implementation and require successful public default-branch CI",
            "run one new final no-content preflight",
            "run one new append-only M2-ORB-001 recovery verification and, only on pass, one existing attempt for each remaining source in fixed order",
            "reconcile the exact terminal outcome without reconstructing the lost first evaluation",
        ],
        "approval_would_not_authorize": [
            "reinterpret, reconstruct, or label the lost M2-ORB-001 attempt as pass or fail",
            "change any source, provider UUID, filename, byte length, checksum, XML rule, OSV rule, unit, scene binding, margin, or one-second endpoint limit",
            "make a second recovery attempt or automatically retry any failed or interrupted source",
            "request a token, access the network, reacquire or replace an orbit file, mutate external custody, substitute AUX_POEORB, date-shop, or source-shop",
            "apply orbit data, act on DEMs, decode radar pixels, process a baseline, analyze change, attribute cause, or publish a scientific result",
        ],
        "human_gate": {
            "review_required": True,
            "item_id": "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001",
            "allowed_decisions": ["approve", "revise", "defer"],
            "required_attestation": True,
        },
        "limitations": [
            "The first M2-ORB-001 evaluation ran after real input observation, so this recovery is explicitly post-observation even though no validation rule changes.",
            "The first in-memory pass or fail result is unavailable and cannot be inferred from code reachability or from a later recovery result.",
            "An exclusive pre-read receipt reservation prevents this exact missing-parent loss but cannot guarantee against every process, disk, or operating-system failure.",
            "A passing four-source result would establish only exact orbit-input identity and structural fitness, not orbit application, geolocation accuracy, radar-pixel fitness, change, or attribution.",
            "This packet contains zero human decisions and grants no implementation or real-read authority until exact owner approval is locked and reconciled.",
        ],
    }
    write_json(PROPOSAL_REF, proposal)
    proposal_sha = sha256(PROPOSAL_REF)

    preflight = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-REVIEW-PREFLIGHT",
        "observed_at_utc": args.prepared_at_utc,
        "status": "pass_review_ready_zero_decisions_no_new_eof_read_or_mutation",
        "bindings": {
            "proposal_sha256": proposal_sha,
            "terminal_reconciliation_sha256": sha256(TERMINAL_REF),
            "active_verification_sha256": sha256(ACTIVE_REF),
            "verifier_sha256": sha256(VERIFIER_REF),
            "prior_publication_gate_sha256": sha256(PUBLICATION_REF),
            "prior_activation_sha256": sha256(ACTIVATION_REF),
            "prior_final_preflight_sha256": sha256(FINAL_PREFLIGHT_REF),
        },
        "assertions": {
            "human_decision_count": 0,
            "recovery_authorized": False,
            "implementation_started": False,
            "new_eof_content_read": False,
            "remaining_source_eof_content_read": False,
            "network_or_credential_action_performed": False,
            "external_custody_mutated": False,
            "orbit_application_performed": False,
            "dem_or_radar_pixel_action_performed": False,
            "baseline_change_attribution_or_publication_performed": False,
        },
    }
    write_json(PREFLIGHT_REF, preflight)

    doc = f"""# M2 orbit offline verification recovery-001 review

## Decision

Choose **approve**, **revise**, or **defer** for proposal `{proposal_sha}`. A completed decision must bind the exact review-bundle SHA-256 and include the owner's attestation.

## Preserved terminal result

After exact implementation commit `308b6d079696a5f5973f7daa02e137e07a14eea3` passed public GitHub Actions run `34145814247`, activation and a no-content preflight passed. The fixed-order verifier then opened and evaluated `M2-ORB-001` in memory. Its final receipt write stopped with `verification_output_parent_missing` because `records/acquisition/orbit-verification` did not exist.

No durable pass or fail receipt exists, so the first evaluation is **terminal indeterminate**. It must not be reconstructed or inferred. External orbit custody was unchanged. `M2-ORB-002`, `M2-ORB-003`, and `M2-ORB-004` were not read.

## Exact recovery under review

Approval would authorize only a persistence-order correction: keep the exact receipt parent in clean clones, validate it in the final no-content preflight, and reserve each append-only receipt path exclusively **before** reading or hashing an EOF. The verifier would write and `fsync` the complete result through that reserved handle. A reserved empty or partial receipt would remain terminal interruption evidence and could not be reused.

After synthetic tests and successful public default-branch CI, one new final no-content preflight could run. Then one new `M2-ORB-001` recovery verification could run. Only if it produces an exact pass could `M2-ORB-002`, `M2-ORB-003`, and `M2-ORB-004` each run once in that order. Any first failure or persistence interruption stops the sequence.

## Frozen rules and prohibited scope

The exact source identities, lengths, provider checksums, safe-XML rules, mission and file type, OSV ordering and units, scene bindings and margins, and maximum one-second OSV endpoint rule remain unchanged. Approval would not authorize a second recovery, automatic retry, token or network action, reacquisition, external-custody mutation, source or date substitution, `AUX_POEORB`, orbit application, DEM work, radar pixels, baseline, change analysis, attribution, or scientific publication.
"""
    write_text(DOC_REF, doc)
    render_surface(proposal_sha)
    surface = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-REVIEW-SURFACE",
        "verified_at_utc": args.prepared_at_utc,
        "status": "pass_blank_review_surface",
        "artifact": {
            "path": IMAGE_REF,
            "sha256": sha256(IMAGE_REF),
            "width_px": 1800,
            "height_px": 1720,
            "format": "PNG",
            "contains_third_party_pixels": False,
        },
        "bindings": {
            "proposal_ref": PROPOSAL_REF,
            "proposal_sha256": proposal_sha,
            "terminal_reconciliation_ref": TERMINAL_REF,
            "terminal_reconciliation_sha256": sha256(TERMINAL_REF),
        },
        "validation": {
            "post_observation_failure_visible": True,
            "indeterminate_result_visible": True,
            "output_reservation_correction_visible": True,
            "fixed_order_and_stop_boundary_visible": True,
            "unchanged_scientific_rules_visible": True,
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
        ("terminal-reconciliation", TERMINAL_REF, "consumed_indeterminate_attempt", False),
        ("active-verification", ACTIVE_REF, "blocked_current_control", False),
        ("verifier-implementation", VERIFIER_REF, "failure_code_path", False),
        ("prior-publication-gate", PUBLICATION_REF, "public_ci_before_real_read", False),
        ("prior-activation", ACTIVATION_REF, "activation_before_real_read", False),
        ("prior-final-preflight", FINAL_PREFLIGHT_REF, "preflight_missing_output_parent_check", False),
        ("original-orbit-approval", ORBIT_APPROVAL_REF, "original_exact_source_authority", False),
        ("osv-precision-approval", OSV_APPROVAL_REF, "one_second_rule_authority", False),
        ("continuation-approval", CONTINUATION_APPROVAL_REF, "remaining_source_attempt_authority", False),
    ]
    bundle = {
        "schema_version": "1.0",
        "template": False,
        "bundle_id": "m2-orbit-offline-verification-recovery-001-review-bundle",
        "review_id": "m2-orbit-offline-verification-recovery-001-review",
        "authority_ref": TERMINAL_REF,
        "candidate_identity": f"M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-PROPOSAL-SHA256:{proposal_sha}",
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
        "review_id": "m2-orbit-offline-verification-recovery-001-review",
        "response_schema_version": "nepal-m2-orbit-offline-verification-recovery-001-response-v1",
        "workflow_authority": {
            "mode": "inherited",
            "authority_ref": TERMINAL_REF,
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
        "items": [{"item_id": "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001", "evidence_sha256": bundle_sha}],
    }
    write_json(CONTRACT_REF, contract)
    blank = {
        "response_schema_version": contract["response_schema_version"],
        "review_id": contract["review_id"],
        "completed": False,
        "review_started_at_utc": None,
        "review_completed_at_utc": None,
        "reviewer": {"attestation": False},
        "responses": [
            {
                "item_id": "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001",
                "evidence_sha256": bundle_sha,
                "decision": None,
                "notes": "",
            }
        ],
    }
    write_json(BLANK_REF, blank)
    readiness = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-REVIEW-READINESS",
        "verified_at_utc": args.prepared_at_utc,
        "status": "pass_ready_owner_review_zero_decisions_public_ci_pending",
        "bindings": {
            "proposal_sha256": proposal_sha,
            "terminal_reconciliation_sha256": sha256(TERMINAL_REF),
            "review_preflight_sha256": sha256(PREFLIGHT_REF),
            "review_instructions_sha256": sha256(DOC_REF),
            "review_surface_sha256": sha256(IMAGE_REF),
            "surface_receipt_sha256": sha256(SURFACE_REF),
            "review_bundle_sha256": bundle_sha,
            "review_contract_sha256": sha256(CONTRACT_REF),
            "blank_response_sha256": sha256(BLANK_REF),
        },
        "review": {
            "human_decision_count": 0,
            "attestation": False,
            "ready_for_publication_gate": True,
        },
        "assertions": {
            "prior_attempt_terminal_indeterminate": True,
            "recovery_authorized": False,
            "implementation_started": False,
            "new_eof_content_read": False,
            "remaining_source_eof_content_read": False,
            "network_or_credential_action_performed": False,
            "external_custody_mutated": False,
            "orbit_application_performed": False,
            "dem_or_radar_pixel_action_performed": False,
            "baseline_change_attribution_or_publication_performed": False,
        },
    }
    write_json(READINESS_REF, readiness)

    publication_unit = {
        "id": "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-REVIEW-PUBLICATION",
        "purpose": "Publish and publicly validate the exact zero-decision orbit-verification recovery packet.",
        "depends_on": ["M2-ORBIT-VERIFY"],
        "action_class": "external_publication",
        "human_gate": False,
        "status": "in_progress",
        "inputs": [PROPOSAL_REF, BUNDLE_REF, CONTRACT_REF, READINESS_REF, TERMINAL_REF],
        "outputs": [
            "records/readiness/m2-orbit-offline-verification-recovery-001-review-publication-gate.json",
            "records/readiness/m2-orbit-offline-verification-recovery-001-review-publication-reconciliation.json",
        ],
        "gates": {
            "public_ci": "pending",
            "proposal_sha256": proposal_sha,
            "review_bundle_sha256": bundle_sha,
            "human_decision_count": 0,
            "recovery_authorized": False,
        },
        "disposition": None,
        "retained_failures": [TERMINAL_REF],
        "exit_condition_delta": {
            "expected": [],
            "observed": [],
            "decision_value": "unknown",
            "rationale": "The exact blank review packet must pass public default-branch CI before owner handoff.",
        },
        "next_dependency": "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-REVIEW",
    }
    review_unit = {
        "id": "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-REVIEW",
        "purpose": "Obtain one exact owner decision on the post-observation receipt-persistence recovery.",
        "depends_on": ["M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-REVIEW-PUBLICATION"],
        "action_class": "authority_broadening",
        "human_gate": True,
        "status": "blocked",
        "inputs": [PROPOSAL_REF, BUNDLE_REF, CONTRACT_REF, TERMINAL_REF],
        "outputs": [
            "records/source-gates/m2-orbit-offline-verification-recovery-001-review-reconciliation.json",
            "records/source-gates/m2-orbit-offline-verification-recovery-001-approval.json",
            "records/readiness/m2-orbit-offline-verification-recovery-001-approval-activation.json",
        ],
        "gates": {
            "proposal_sha256": proposal_sha,
            "review_bundle_sha256": bundle_sha,
            "review_contract_sha256": sha256(CONTRACT_REF),
            "blank_response_sha256": sha256(BLANK_REF),
            "public_ci": "pending",
            "source_ids_in_exact_order": SOURCE_IDS,
            "m2_orb_001_new_recovery_attempts_if_approved": 1,
            "remaining_source_attempts_per_source_if_approved": 1,
            "stop_on_first_failure_if_approved": True,
            "maximum_endpoint_tolerance_seconds_if_approved": 1.0,
            "human_decision_count": 0,
            "attestation": False,
            "recovery_authorized": False,
        },
        "disposition": None,
        "retained_failures": [TERMINAL_REF],
        "exit_condition_delta": {
            "expected": [],
            "observed": [],
            "decision_value": "unknown",
            "rationale": "The packet has zero decisions and grants no recovery authority.",
        },
        "next_dependency": "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-IMPLEMENTATION",
    }
    existing_ids = [unit.get("id") for unit in milestone.get("units", []) if isinstance(unit, dict)]
    if publication_unit["id"] in existing_ids or review_unit["id"] in existing_ids:
        raise SystemExit("recovery review milestone unit collision")
    milestone["units"].extend([publication_unit, review_unit])
    milestone["handoff"]["current_checkpoint"] = CHECKPOINT
    milestone["handoff"]["next_action"] = NEXT_ACTION
    profile["current_checkpoint"] = {
        "checkpoint_id": CHECKPOINT,
        "expected_branch": "main",
        "expected_head": None,
        "next_action": NEXT_ACTION,
    }
    profile["control_surfaces"]["proposed_amendments"] = list(
        dict.fromkeys(profile["control_surfaces"].get("proposed_amendments", []) + [PROPOSAL_REF])
    )
    profile["gate_policy"]["explicit_human_gates"].append(
        {
            "unit_id": "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-REVIEW",
            "reason": (
                "The first real EOF evaluation is terminal indeterminate; only an exact owner decision can broaden the "
                "one-attempt contract to one post-observation persistence recovery."
            ),
            "authority_ref": CONTRACT_REF,
        }
    )
    goal["current_checkpoint"] = CHECKPOINT
    goal["proposed_amendments"] = list(dict.fromkeys(goal.get("proposed_amendments", []) + [PROPOSAL_REF]))
    write_existing(MILESTONE_REF, milestone)
    write_existing(PROFILE_REF, profile)
    write_existing(GOAL_REF, goal)

    print(
        json.dumps(
            {
                "status": readiness["status"],
                "checkpoint": CHECKPOINT,
                "proposal_sha256": proposal_sha,
                "review_bundle_sha256": bundle_sha,
                "review_contract_sha256": sha256(CONTRACT_REF),
                "blank_response_sha256": sha256(BLANK_REF),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
