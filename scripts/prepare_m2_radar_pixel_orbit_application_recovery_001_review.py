#!/usr/bin/env python3
"""Prepare the zero-decision radar inventory-normalization recovery-001 review."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import textwrap
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-pixel-orbit-application-recovery-001"
PROPOSAL_REF = "contracts/milestone-002-radar-pixel-orbit-application-recovery-001-proposal.json"
PREFLIGHT_REF = f"records/readiness/{PREFIX}-review-preflight.json"
DOC_REF = "docs/M2_RADAR_PIXEL_ORBIT_APPLICATION_RECOVERY_001_REVIEW.md"
IMAGE_REF = f"docs/assets/{PREFIX}-review.png"
SURFACE_REF = f"records/surface-receipts/{PREFIX}-review.json"
BUNDLE_REF = f"reviews/{PREFIX}/review-bundle.json"
CONTRACT_REF = f"reviews/{PREFIX}/review-contract.json"
BLANK_REF = f"reviews/{PREFIX}/blank-response.json"
READINESS_REF = f"records/readiness/{PREFIX}-review-readiness.json"
TERMINAL_REF = "records/processing/m2-radar-pixel-orbit-application-001-terminal-reconciliation.json"
DIAGNOSTIC_REF = "records/processing/radar-pixel-orbit-application-001/m1-src-001-identity-failure-diagnostic.json"
TERMINAL_GATE_REF = "records/readiness/m2-radar-pixel-orbit-application-001-terminal-publication-gate.json"
MILESTONE_REF = "contracts/milestone-002.json"
PROFILE_REF = "records/project-control-profile.json"
GOAL_REF = "records/long-term-goal.json"
CHECKPOINT = "M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-001-REVIEW-PUBLICATION"
UNIT_ID = "M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-001-REVIEW"
NEXT_ACTION = (
    "Publish and publicly validate the exact zero-decision radar inventory-normalization recovery-001 review packet. "
    "No correction, new real attempt, orbit application, or radar pixel processing is authorized before one exact "
    "attested owner decision on the public packet."
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


def replace_json(ref: str, value: dict[str, Any]) -> None:
    (ROOT / ref).write_bytes((json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))


def render_surface(proposal_sha: str, terminal_sha: str) -> None:
    from PIL import Image, ImageDraw, ImageFont

    def font(name: str, size: int):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            return ImageFont.load_default()

    image = Image.new("RGB", (1800, 1540), "#f4f1e9")
    draw = ImageDraw.Draw(image)
    title = font("arialbd.ttf", 44)
    heading = font("arialbd.ttf", 28)
    body = font("arial.ttf", 22)
    callout = font("arialbd.ttf", 25)
    draw.rectangle((0, 0, 1800, 168), fill="#17324d")
    draw.text((62, 28), "M2 Radar Inventory Recovery 001", font=title, fill="white")
    draw.text((64, 98), f"Proposal {proposal_sha}", font=font("arial.ttf", 18), fill="#dce8f2")
    draw.text((64, 128), f"Terminal real-001 {terminal_sha}", font=font("arial.ttf", 18), fill="#dce8f2")
    sections = [
        ("Preserved terminal result", [
            "Real-001 is consumed. It stopped on the first M1-SRC-001 identity guard before source processing.",
            "All 26 paths, sizes, and SHA-256 values match after normalization; no source copy or ArcGIS operation began.",
            "The mismatch was representation-only: zip_crc32 plus archive order versus a three-field sorted runtime inventory.",
        ]),
        ("What approval would authorize", [
            "Normalize both sides to relative_path, size_bytes, and sha256, then sort case-insensitively before exact equality.",
            "Keep added, missing, size, and SHA-256 differences as hard failures; do not weaken source identity.",
            "Place identity verification inside durable terminal-error handling and prove the behavior with synthetic tests and public CI.",
            "After one final no-content preflight, create one new recovery-001 attempt and process the same six sources in the same order once.",
        ]),
        ("Still prohibited", [
            "No reuse or retry of real-001, automatic retry, source/orbit/DEM substitution, threshold change, network, or credential action.",
            "No baseline admission, change analysis, interpretation, attribution, derived-pixel publication, or scientific claim.",
        ]),
    ]
    y = 210
    for label, lines in sections:
        draw.text((64, y), label, font=heading, fill="#17324d")
        y += 44
        for line in lines:
            for index, part in enumerate(textwrap.wrap(line, 106)):
                draw.text((92, y), ("• " if index == 0 else "  ") + part, font=body, fill="#20252b")
                y += 33
        y += 18
    draw.rectangle((60, 1382, 1740, 1482), outline="#9b6b21", width=3)
    draw.text((82, 1417), "Decision required: APPROVE, REVISE, or DEFER with owner attestation.", font=callout, fill="#7a4e0b")
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
    diagnostic = load(DIAGNOSTIC_REF)
    terminal_gate = load(TERMINAL_GATE_REF)
    milestone = load(MILESTONE_REF)
    profile = load(PROFILE_REF)
    goal = load(GOAL_REF)
    if (
        head != origin
        or head != "05010532745c7dd361a3ee8af34cb8c96a42b95f"
        or terminal.get("status") != "block_terminal_inventory_representation_mismatch_no_retry"
        or diagnostic.get("status") != "confirmed_schema_and_order_only_inventory_mismatch"
        or diagnostic.get("comparison", {}).get("byte_identity_mismatch_count") != 0
        or diagnostic.get("comparison", {}).get("normalized_sorted_expected_matches_actual") is not True
        or terminal_gate.get("status") != "pass_public_terminal_state_recovery_review_preparation_released"
        or terminal_gate.get("public_ci_conclusion") != "success"
        or milestone.get("handoff", {}).get("current_checkpoint") != "M2-ORBIT-APPLY"
        or profile.get("current_checkpoint", {}).get("checkpoint_id") != "M2-ORBIT-APPLY"
        or goal.get("current_checkpoint") != "M2-ORBIT-APPLY"
    ):
        raise SystemExit("terminal state is not the exact recovery-review preparation base")

    proposal = {
        "schema_version": "1.0",
        "proposal_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-001-PROPOSAL",
        "prepared_at_utc": args.prepared_at_utc,
        "status": "proposed_inactive_owner_review_required",
        "preparation_base_commit": head,
        "trigger": {
            "terminal_reconciliation_ref": TERMINAL_REF,
            "terminal_reconciliation_sha256": sha256(TERMINAL_REF),
            "identity_failure_diagnostic_ref": DIAGNOSTIC_REF,
            "identity_failure_diagnostic_sha256": sha256(DIAGNOSTIC_REF),
            "terminal_publication_gate_ref": TERMINAL_GATE_REF,
            "terminal_publication_gate_sha256": sha256(TERMINAL_GATE_REF),
            "consumed_attempt_id": "radar-pixel-orbit-application-001-real-001",
            "failure_code": "materialized_safe_inventory_mismatch",
            "stopped_source_id": "M1-SRC-001",
            "source_processing_attempts_started": 0,
            "route_evaluations_started": 0,
        },
        "observed_mismatch": {
            "expected_file_count": 26,
            "actual_file_count": 26,
            "added_path_count": 0,
            "missing_path_count": 0,
            "byte_identity_mismatch_count": 0,
            "representation_only_mismatch_count": 26,
            "ordering_position_mismatch_count": 17,
            "expected_only_field": "zip_crc32",
            "normalized_sorted_expected_matches_actual": True,
        },
        "proposed_bounded_actions": [
            "implement one inventory comparator that projects manifest and runtime entries to the exact relative_path, size_bytes, and sha256 fields and sorts both case-insensitively before equality",
            "retain hard failure for any added path, missing path, size mismatch, SHA-256 mismatch, duplicate normalized path, unsafe path, or reparse point",
            "move pre-processing external identity verification under durable terminal-error handling so every started attempt receives a terminal receipt",
            "add synthetic tests for extra zip_crc32 fields, archive-order differences, duplicate paths, real byte mismatches, interruption, terminal persistence, fixed order, and stop on first failure",
            "require successful public default-branch CI and one fresh no-content preflight before any new project-data read",
            "only on those passes create one fresh radar-pixel-orbit-application-recovery-001-real-001 attempt and run the same six sources and two routes under the unchanged processing and QA contracts",
            "reconcile the terminal outcome and stop before baseline admission or change analysis",
        ],
        "fixed_sequence": {
            "source_ids": [f"M1-SRC-{index:03d}" for index in range(1, 7)],
            "route_ids": ["PAIR-S1-ASC-R085-IW", "PAIR-S1-DESC-R121-IW"],
            "new_attempt_id": "radar-pixel-orbit-application-recovery-001-real-001",
            "consumed_attempt_id": "radar-pixel-orbit-application-001-real-001",
        },
        "limits": {
            "new_real_attempts": 1,
            "orbit_application_attempts_per_source": 1,
            "qa_processing_attempts_per_source": 1,
            "route_qa_attempts_per_pair": 1,
            "automatic_retry": False,
            "stop_on_first_execution_failure": True,
            "network_requests": 0,
            "credential_or_token_actions": 0,
            "source_overwrites": 0,
            "output_overwrites": 0,
        },
        "frozen_without_change": [
            "six source identities, source order, source-to-AUX_RESORB map, four AUX_RESORB identities, four ellipsoidal DEM identities",
            "EPSG:32645, 10 metre grid, AOIs, polarization handling, processing chain, masks, thresholds, registration method, route order, and all QA predicates",
            "real-001 terminal status and every prior receipt",
        ],
        "does_not_authorize": [
            "implementation, preflight, project-data read, new attempt, retry, or reuse before exact attested owner approval and later public implementation CI",
            "source, date, orbit, DEM, AOI, CRS, resolution, threshold, mask, stable-control, or route substitution",
            "network, credential, account, terms, installation, or UAC action",
            "baseline admission, change analysis, interpretation, attribution, emergency guidance, derived-pixel publication, or scientific publication",
        ],
        "decision_domain": ["approve", "revise", "defer"],
        "attestation_required": True,
        "human_decision_count": 0,
    }
    write_json(PROPOSAL_REF, proposal)
    proposal_sha = sha256(PROPOSAL_REF)

    preflight = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-001-REVIEW-PREFLIGHT",
        "checked_at_utc": args.prepared_at_utc,
        "status": "pass_ready_prepare_zero_decision_review",
        "bindings": {"proposal_sha256": proposal_sha, "terminal_reconciliation_sha256": sha256(TERMINAL_REF), "identity_failure_diagnostic_sha256": sha256(DIAGNOSTIC_REF)},
        "checks": {"terminal_attempt_consumed": True, "byte_identity_mismatch_count": 0, "normalization_defect_bounded": True, "current_authority_allows_retry": False},
        "assertions": {"project_data_content_read": False, "external_custody_accessed": False, "external_custody_mutated": False, "implementation_authorized": False, "new_attempt_authorized": False, "scientific_result_established": False},
    }
    write_json(PREFLIGHT_REF, preflight)
    doc = f"""# M2 radar inventory-normalization recovery-001 review\n\n**Proposal SHA-256:** `{proposal_sha}`\n**Terminal reconciliation SHA-256:** `{sha256(TERMINAL_REF)}`\n**Decision state:** zero decisions; owner review required\n\n## Terminal evidence\n\nReal-001 is consumed. It stopped on the first `M1-SRC-001` identity guard before source processing. The diagnostic confirms 26 expected and 26 actual files, no additions or omissions, and zero size or SHA-256 differences after projection and sorting. Direct list equality failed because manifest entries include `zip_crc32` and archive order while the runtime inventory uses three fields and case-insensitive path order.\n\n## Proposed bounded recovery\n\nApproval would authorize one exact comparator correction: project both inventories to `relative_path`, `size_bytes`, and `sha256`, reject duplicates or any byte-identity difference, then sort case-insensitively before equality. It would also move identity verification under durable terminal-error handling, add synthetic and ArcGIS-safe tests, require public CI and one final no-content preflight, and only then allow one fresh recovery-001 attempt with the same six sources and two routes in the same order.\n\n## Unchanged restrictions\n\nReal-001 cannot be retried or reused. No source, orbit, DEM, AOI, CRS, threshold, mask, or route substitution is proposed. No network or credential action, baseline admission, change analysis, interpretation, attribution, derived-pixel publication, or scientific claim is authorized.\n\n## Decision\n\nChoose `approve`, `revise`, or `defer` for the exact proposal above and attest that the decision is complete.\n"""
    write_text(DOC_REF, doc)
    render_surface(proposal_sha, sha256(TERMINAL_REF))
    from PIL import Image
    with Image.open(ROOT / IMAGE_REF) as image:
        width, height = image.size
    surface = {
        "schema_version": "1.0", "receipt_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-001-REVIEW-SURFACE",
        "rendered_at_utc": args.prepared_at_utc, "status": "pass_static_review_surface",
        "artifact_ref": IMAGE_REF, "artifact_sha256": sha256(IMAGE_REF), "width_px": width, "height_px": height,
        "bindings": {"proposal_sha256": proposal_sha, "terminal_reconciliation_sha256": sha256(TERMINAL_REF)},
        "assertions": {"human_decision_count": 0, "attestation": False, "implementation_authorized": False, "new_attempt_authorized": False},
    }
    write_json(SURFACE_REF, surface)
    bundle = {
        "schema_version": "1.0", "bundle_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-001-REVIEW-BUNDLE",
        "prepared_at_utc": args.prepared_at_utc, "status": "ready_zero_decisions",
        "human_decision_count": 0,
        "artifacts": [
            {"path": PROPOSAL_REF, "sha256": proposal_sha, "purpose": "normative recovery proposal", "render_receipts": [{"path": SURFACE_REF, "sha256": sha256(SURFACE_REF)}]},
            {"path": PREFLIGHT_REF, "sha256": sha256(PREFLIGHT_REF), "purpose": "terminal-state review preflight", "render_receipts": []},
            {"path": DOC_REF, "sha256": sha256(DOC_REF), "purpose": "human-readable review", "render_receipts": [{"path": SURFACE_REF, "sha256": sha256(SURFACE_REF)}]},
            {"path": IMAGE_REF, "sha256": sha256(IMAGE_REF), "purpose": "rendered review surface", "render_receipts": [{"path": SURFACE_REF, "sha256": sha256(SURFACE_REF)}]},
        ],
        "decision_items": [{"item_id": "M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-001", "allowed_decisions": ["approve", "revise", "defer"], "evidence_ref": PROPOSAL_REF, "evidence_sha256": proposal_sha}],
    }
    write_json(BUNDLE_REF, bundle)
    bundle_sha = sha256(BUNDLE_REF)
    contract = {
        "schema_version": "1.0", "contract_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-001-REVIEW-CONTRACT",
        "status": "open_zero_decisions", "review_bundle": {"manifest_ref": BUNDLE_REF, "manifest_sha256": bundle_sha},
        "required_response_path_pattern": f"reviews/{PREFIX}/response-<sha256>.json", "required_attestation": True,
        "decision_items": [{"item_id": "M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-001", "allowed_decisions": ["approve", "revise", "defer"], "evidence_sha256": bundle_sha}],
        "authority_boundary": {"packet_creates_authority": False, "implementation_authorized": False, "new_attempt_authorized": False, "baseline_or_change_authorized": False, "scientific_publication_authorized": False},
    }
    write_json(CONTRACT_REF, contract)
    blank = {
        "schema_version": "1.0", "contract_ref": CONTRACT_REF, "contract_sha256": sha256(CONTRACT_REF),
        "review_bundle_sha256": bundle_sha, "completed": False,
        "reviewer": {"name": None, "attestation": False},
        "responses": [{"item_id": "M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-001", "decision": None, "rationale": None, "evidence_sha256": bundle_sha}],
        "human_decision_count": 0,
    }
    write_json(BLANK_REF, blank)

    unit = {
        "id": UNIT_ID, "purpose": "Review one bounded inventory-normalization correction and fresh exact-source attempt without releasing baseline or change analysis.",
        "depends_on": ["M2-RADAR-PIXEL-ORBIT-APPLICATION-001-EXECUTION"], "action_class": "authority_broadening", "human_gate": True, "status": "planned",
        "inputs": [PROPOSAL_REF, PREFLIGHT_REF, BUNDLE_REF, CONTRACT_REF, BLANK_REF, TERMINAL_REF, DIAGNOSTIC_REF, TERMINAL_GATE_REF],
        "outputs": [], "gates": {"public_ci": "pending", "human_decision_count": 0, "attestation": False, "implementation_authorized": False, "new_attempt_authorized": False, "baseline_or_change_authorized": False},
        "disposition": None, "retained_failures": [TERMINAL_REF],
        "exit_condition_delta": {"expected": ["successful public CI", "one exact attested owner decision"], "observed": ["zero-decision packet prepared"], "decision_value": "unknown", "rationale": "The packet creates no recovery authority."},
        "next_dependency": "M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-001-IMPLEMENTATION",
    }
    if any(item.get("id") == UNIT_ID for item in milestone.get("units", [])):
        raise SystemExit("recovery review unit collision")
    milestone["units"].append(unit)
    milestone["handoff"].update({"current_checkpoint": CHECKPOINT, "next_action": NEXT_ACTION, "parallel_checkpoint": CHECKPOINT, "parallel_next_action": NEXT_ACTION})
    replace_json(MILESTONE_REF, milestone)
    profile["current_checkpoint"] = {"checkpoint_id": CHECKPOINT, "expected_branch": "main", "expected_head": None, "next_action": NEXT_ACTION}
    profile["parallel_checkpoints"] = [{"checkpoint_id": CHECKPOINT, "authority_ref": CONTRACT_REF, "next_action": NEXT_ACTION}]
    gates = profile.setdefault("human_gates", {}).setdefault("review_gates", [])
    gates.append({"unit_id": UNIT_ID, "reason": "A new real attempt requires exact owner approval after terminal real-001.", "authority_ref": CONTRACT_REF})
    profile["control_surfaces"]["proposed_amendments"] = [PROPOSAL_REF]
    replace_json(PROFILE_REF, profile)
    goal["current_checkpoint"] = CHECKPOINT
    goal["parallel_checkpoints"] = [CHECKPOINT]
    goal["proposed_amendments"] = [PROPOSAL_REF]
    replace_json(GOAL_REF, goal)

    readiness = {
        "schema_version": "1.0", "record_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-001-REVIEW-READINESS",
        "recorded_at_utc": args.prepared_at_utc, "status": "pass_ready_publication_zero_decisions",
        "bindings": {ref: sha256(ref) for ref in [PROPOSAL_REF, PREFLIGHT_REF, DOC_REF, IMAGE_REF, SURFACE_REF, BUNDLE_REF, CONTRACT_REF, BLANK_REF, TERMINAL_REF, DIAGNOSTIC_REF, TERMINAL_GATE_REF, MILESTONE_REF, PROFILE_REF, GOAL_REF]},
        "checks": {"proposal_sha256": proposal_sha, "review_bundle_sha256": bundle_sha, "human_decision_count": 0, "blank_response": True, "terminal_real_001_preserved": True},
        "released_now": {"public_review_packet_ci": True, "owner_review_after_public_ci": True, "implementation": False, "project_data_content_read": False, "new_real_attempt": False},
        "assertions": {"human_decisions_fabricated": False, "project_data_content_read": False, "external_custody_accessed": False, "external_custody_mutated": False, "implementation_authorized": False, "new_attempt_authorized": False, "scientific_result_established": False},
    }
    write_json(READINESS_REF, readiness)
    print(json.dumps({"proposal_sha256": proposal_sha, "review_bundle_sha256": bundle_sha, "readiness_sha256": sha256(READINESS_REF), "checkpoint": CHECKPOINT}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())