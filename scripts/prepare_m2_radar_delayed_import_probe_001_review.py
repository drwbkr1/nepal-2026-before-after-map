#!/usr/bin/env python3
"""Prepare the zero-decision M2 radar delayed-import probe-001 review."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import textwrap
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-delayed-import-probe-001"
PROPOSAL_REF = "contracts/milestone-002-radar-delayed-import-probe-001-proposal.json"
PREPARATION_APPROVAL_REF = "records/source-gates/m2-radar-delayed-import-probe-001-review-preparation-approval.json"
PREFLIGHT_REF = f"records/readiness/{PREFIX}-review-preflight.json"
DOC_REF = "docs/M2_RADAR_DELAYED_IMPORT_PROBE_001_REVIEW.md"
IMAGE_REF = f"docs/assets/{PREFIX}-review.png"
SURFACE_REF = f"records/surface-receipts/{PREFIX}-review.json"
BUNDLE_REF = f"reviews/{PREFIX}/review-bundle.json"
CONTRACT_REF = f"reviews/{PREFIX}/review-contract.json"
BLANK_REF = f"reviews/{PREFIX}/blank-response.json"
READINESS_REF = f"records/readiness/{PREFIX}-review-readiness.json"
TERMINAL_REF = "records/processing/m2-radar-pixel-orbit-application-recovery-001-terminal-reconciliation.json"
OUTCOME_REF = "records/processing/m2-radar-pixel-orbit-application-recovery-001-outcome-reconciliation.json"
TERMINAL_GATE_REF = "records/readiness/m2-radar-pixel-orbit-application-recovery-001-terminal-publication-gate.json"
OBSERVATION_REFS = [
    "records/readiness/m2-radar-pixel-orbit-application-recovery-001-terminal-owner-review-observation-001.json",
    "records/readiness/m2-radar-pixel-orbit-application-recovery-001-terminal-static-call-path-observation-002.json",
    "records/readiness/m2-radar-pixel-orbit-application-recovery-001-terminal-evidence-triangulation-observation-003.json",
    "records/readiness/m2-radar-pixel-orbit-application-recovery-001-terminal-launch-context-observation-004.json",
    "records/readiness/m2-radar-pixel-orbit-application-recovery-001-terminal-local-log-observation-005.json",
]
MILESTONE_REF = "contracts/milestone-002.json"
PROFILE_REF = "records/project-control-profile.json"
GOAL_REF = "records/long-term-goal.json"
BASE_COMMIT = "58d837ece04245fa132b4c65c713a1a68f698525"
CHECKPOINT = "M2-RADAR-DELAYED-IMPORT-PROBE-001-REVIEW-PUBLICATION"
UNIT_ID = "M2-RADAR-DELAYED-IMPORT-PROBE-001-REVIEW"
CORPUS_FILE_COUNT = 156
CORPUS_LOGICAL_BYTES = 10_367_157_634
NEXT_ACTION = (
    "Publish and publicly validate the exact zero-decision radar delayed-import probe-001 review packet. "
    "Do not implement or execute the probe, access project data, reuse recovery-001, or begin radar processing "
    "before one exact attested owner decision on the public packet."
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

    image = Image.new("RGB", (1800, 1660), "#f4f1e9")
    draw = ImageDraw.Draw(image)
    title = font("arialbd.ttf", 44)
    heading = font("arialbd.ttf", 28)
    body = font("arial.ttf", 22)
    callout = font("arialbd.ttf", 25)
    draw.rectangle((0, 0, 1800, 168), fill="#17324d")
    draw.text((62, 28), "M2 Radar Delayed-Import Probe 001", font=title, fill="white")
    draw.text((64, 98), f"Proposal {proposal_sha}", font=font("arial.ttf", 18), fill="#dce8f2")
    draw.text((64, 128), f"Consumed recovery {terminal_sha}", font=font("arial.ttf", 18), fill="#dce8f2")
    sections = [
        ("Why this probe is proposed", [
            "Recovery-001 is terminal and consumed. Its ArcGIS license failure occurred after a 156-file, 10,367,157,634-byte identity scan and before any DEM or radar operation.",
            "Current license checks and the earlier synthetic raster run pass, while the exact historical failing ArcPy statement remains unknown.",
        ]),
        ("Exact disposable sequence", [
            "One fresh process creates 156 local sparse files with the exact observed total logical size, then hashes all files before importing ArcPy.",
            "Durable markers bracket ArcPy import, ProductInfo, overwriteOutput, Image Analyst checkout, Spatial checkout, and one tiny disposable raster mosaic.",
            "The corpus and rasters contain deterministic synthetic bytes only; project data, external custody, network, credentials, installation, and UAC are excluded.",
        ]),
        ("How results may be used", [
            "PASS means only that the current machine completed the delayed-import sequence at that time; it does not explain the consumed failure.",
            "BLOCK identifies the last durable stage and sanitized exception for this probe only. No automatic retry is allowed.",
            "Neither result authorizes recovery-001 reuse, a new radar attempt, orbit application, pixel processing, baseline, change analysis, attribution, or publication.",
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
    draw.rectangle((60, 1490, 1740, 1592), outline="#9b6b21", width=3)
    draw.text((82, 1526), "Decision required: APPROVE, REVISE, or DEFER with owner attestation.", font=callout, fill="#7a4e0b")
    path = ROOT / IMAGE_REF
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared-at-utc", required=True)
    args = parser.parse_args()
    if not args.prepared_at_utc.endswith("Z"):
        raise SystemExit("prepared time must be UTC")
    outputs = [
        PROPOSAL_REF,
        PREPARATION_APPROVAL_REF,
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

    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    origin = subprocess.run(["git", "rev-parse", "origin/main"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    terminal = load(TERMINAL_REF)
    outcome = load(OUTCOME_REF)
    terminal_gate = load(TERMINAL_GATE_REF)
    observations = [load(ref) for ref in OBSERVATION_REFS]
    milestone = load(MILESTONE_REF)
    profile = load(PROFILE_REF)
    goal = load(GOAL_REF)
    if (
        head != origin
        or head != BASE_COMMIT
        or terminal.get("status") != "failed_supervisor_no_retry"
        or terminal.get("failure_message") != "The Product License has not been initialized."
        or terminal.get("assertions", {}).get("attempt_consumed") is not True
        or outcome.get("status") != "block_terminal_arcgis_product_license_not_initialized_no_retry"
        or terminal_gate.get("status") != "pass_public_terminal_state_owner_review_only"
        or terminal_gate.get("public_ci_conclusion") != "success"
        or observations[0].get("status") != "defer_current_license_initialized_prior_failure_not_reproduced_at_license_api_boundary"
        or any(item.get("assertions", {}).get("root_cause_resolved") is not False for item in observations[1:])
        or milestone.get("handoff", {}).get("current_checkpoint") != "M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-001-TERMINAL-REVIEW"
        or profile.get("current_checkpoint", {}).get("checkpoint_id") != "M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-001-TERMINAL-REVIEW"
        or goal.get("current_checkpoint") != "M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-001-TERMINAL-REVIEW"
    ):
        raise SystemExit("terminal state is not the exact delayed-import review preparation base")

    preparation_approval = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-001-REVIEW-PREPARATION-APPROVAL",
        "recorded_at_utc": args.prepared_at_utc,
        "status": "approved_review_preparation_only",
        "decision": "approve",
        "human_decision_count": 1,
        "attestation_required": False,
        "approved_scope": "prepare and publish, but do not implement or execute, a zero-decision review packet for one stage-marked delayed-import probe using only disposable bytes and no project data",
        "authority_boundary": {
            "review_packet_preparation_authorized": True,
            "public_review_packet_publication_authorized": True,
            "probe_implementation_authorized": False,
            "probe_execution_authorized": False,
            "project_data_content_read_authorized": False,
            "recovery_retry_or_reuse_authorized": False,
            "radar_processing_authorized": False,
            "baseline_or_change_authorized": False,
            "scientific_publication_authorized": False,
        },
    }
    write_json(PREPARATION_APPROVAL_REF, preparation_approval)

    proposal = {
        "schema_version": "1.0",
        "proposal_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-001-PROPOSAL",
        "prepared_at_utc": args.prepared_at_utc,
        "status": "proposed_inactive_owner_review_required",
        "preparation_base_commit": head,
        "preparation_authority": {
            "ref": PREPARATION_APPROVAL_REF,
            "sha256": sha256(PREPARATION_APPROVAL_REF),
            "review_preparation_only": True,
            "probe_execution_authorized": False,
        },
        "trigger": {
            "terminal_reconciliation_ref": TERMINAL_REF,
            "terminal_reconciliation_sha256": sha256(TERMINAL_REF),
            "outcome_reconciliation_ref": OUTCOME_REF,
            "outcome_reconciliation_sha256": sha256(OUTCOME_REF),
            "terminal_publication_gate_ref": TERMINAL_GATE_REF,
            "terminal_publication_gate_sha256": sha256(TERMINAL_GATE_REF),
            "owner_review_observations": [{"path": ref, "sha256": sha256(ref)} for ref in OBSERVATION_REFS],
            "consumed_attempt_id": "radar-pixel-orbit-application-recovery-001-real-001",
            "failure_code": "unexpected_processing_failure",
            "failure_message": "The Product License has not been initialized.",
            "source_processing_attempts_started": 0,
            "route_evaluations_started": 0,
            "derived_raster_count": 0,
        },
        "evidence_assessment": {
            "historical_candidate_statements": [
                "import arcpy",
                "arcpy.env.overwriteOutput = False",
                "arcpy.CheckOutExtension('ImageAnalyst')",
                "arcpy.CheckOutExtension('Spatial')",
            ],
            "historical_exact_failing_statement_identified": False,
            "root_cause_resolved": False,
            "current_product_and_extension_checks_passed": True,
            "existing_synthetic_geoprocessing_passed": True,
            "persistent_install_wide_license_absence_supported": False,
            "only_observed_sequence_difference": "the consumed execute process delayed ArcPy import until after hashing 156 files totaling 10,367,157,634 bytes",
            "sequence_difference_causal": False,
        },
        "proposed_bounded_actions": [
            "implement a probe-only runner that reserves append-only started, stage, terminal, and cleanup receipts before any disposable corpus creation",
            "add portable synthetic tests for exact stage order, durable pre-call and post-call markers, sanitized exception persistence, cleanup reporting, one-attempt enforcement, and secret and project-path rejection",
            "require successful public default-branch CI and one final no-content preflight before the one live probe",
            "only on those passes create one fresh process and one disposable corpus of exactly 156 deterministic sparse regular files totaling exactly 10,367,157,634 logical bytes under a probe-specific local temporary root",
            "hash all 156 disposable files in stable name order before importing ArcPy and record only synthetic file names, lengths, aggregate digest, elapsed timing, and stage state",
            "write and flush durable before and after markers around ArcPy import, ProductInfo, overwriteOutput assignment, Image Analyst checkout, Spatial checkout, two tiny disposable raster creations, and one MosaicToNewRaster operation",
            "check extensions in in reverse order, write one terminal diagnostic receipt, then attempt cleanup and record cleanup disposition without retrying the probe",
            "reconcile the diagnostic outcome without changing the terminal recovery, processing contracts, or scientific state",
        ],
        "exact_probe_contract": {
            "attempt_id": "radar-delayed-import-probe-001-real-001",
            "process_count": 1,
            "corpus": {
                "content_class": "deterministic_disposable_zero_bytes",
                "file_count": CORPUS_FILE_COUNT,
                "total_logical_bytes": CORPUS_LOGICAL_BYTES,
                "allocation": "sparse_regular_files_when_supported_with exact logical lengths; fail closed if exact lengths or local free-space guard cannot be established",
                "path_class": "probe-specific local temporary root outside external custody and outside tracked repository content",
                "source_names_or_source_bytes_used": False,
            },
            "stage_order": [
                "attempt_reserved",
                "corpus_create_started",
                "corpus_create_completed",
                "corpus_hash_started",
                "corpus_hash_completed",
                "arcpy_import_started",
                "arcpy_import_completed",
                "product_info_started",
                "product_info_completed",
                "overwrite_output_started",
                "overwrite_output_completed",
                "image_analyst_checkout_started",
                "image_analyst_checkout_completed",
                "spatial_checkout_started",
                "spatial_checkout_completed",
                "disposable_raster_a_started",
                "disposable_raster_a_completed",
                "disposable_raster_b_started",
                "disposable_raster_b_completed",
                "disposable_mosaic_started",
                "disposable_mosaic_completed",
                "spatial_checkin_started",
                "spatial_checkin_completed",
                "image_analyst_checkin_started",
                "image_analyst_checkin_completed",
                "terminal_receipt_persisted",
                "cleanup_started",
                "cleanup_completed_or_warning",
            ],
            "geoprocessing": {
                "inputs": "two deterministic 2 by 2 disposable rasters",
                "operation": "arcpy.management.MosaicToNewRaster",
                "output": "one disposable local raster",
                "project_crs_or_project_aoi_used": False,
            },
            "result_semantics": {
                "pass": "current host completed the exact delayed-import diagnostic sequence at that time only",
                "block": "the last durable stage and sanitized exception identify this probe failure boundary only",
                "historical_root_cause_claim_allowed": False,
                "recovery_readiness_claim_allowed": False,
            },
        },
        "limits": {
            "live_probe_attempts": 1,
            "automatic_retry": False,
            "processes": 1,
            "network_requests": 0,
            "credential_or_token_actions": 0,
            "software_installations": 0,
            "uac_actions": 0,
            "project_data_content_reads": 0,
            "external_custody_reads": 0,
            "external_custody_mutations": 0,
            "recovery_attempts": 0,
            "orbit_applications": 0,
            "radar_pixel_reads": 0,
            "scientific_outputs": 0,
        },
        "frozen_without_change": [
            "the consumed recovery-001 terminal status, attempt path, reconciliations, and five owner-review observations",
            "all Sentinel, orbit, DEM, AOI, EPSG:32645, 10 metre grid, masks, thresholds, route, and QA contracts",
            "all existing custody and derived outputs",
        ],
        "does_not_authorize": [
            "probe implementation, tests, preflight, ArcPy invocation, corpus creation, or live probe before exact attested owner approval",
            "recovery-001 request, reuse, resume, retry, path mutation, or reconstruction",
            "project-data or external-custody access, source substitution, network, credential, account, terms, installation, or UAC action",
            "orbit application, DEM action, radar pixel processing, route evaluation, baseline, change analysis, interpretation, attribution, emergency guidance, derived-pixel publication, or scientific publication",
            "a historical root-cause or recovery-readiness claim from either a passing or failing probe",
        ],
        "decision_domain": ["approve", "revise", "defer"],
        "attestation_required": True,
        "human_decision_count": 0,
    }
    write_json(PROPOSAL_REF, proposal)
    proposal_sha = sha256(PROPOSAL_REF)

    preflight = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-001-REVIEW-PREFLIGHT",
        "checked_at_utc": args.prepared_at_utc,
        "status": "pass_ready_prepare_zero_decision_review",
        "bindings": {
            "preparation_approval_sha256": sha256(PREPARATION_APPROVAL_REF),
            "proposal_sha256": proposal_sha,
            "terminal_reconciliation_sha256": sha256(TERMINAL_REF),
            "outcome_reconciliation_sha256": sha256(OUTCOME_REF),
            "terminal_publication_gate_sha256": sha256(TERMINAL_GATE_REF),
            "owner_review_observation_sha256": [sha256(ref) for ref in OBSERVATION_REFS],
        },
        "checks": {
            "terminal_attempt_consumed": True,
            "historical_root_cause_unresolved": True,
            "delayed_import_sequence_difference_observed_not_proven": True,
            "preparation_authority_exactly_review_only": True,
            "current_authority_allows_probe_implementation_or_execution": False,
        },
        "assertions": {
            "probe_process_started": False,
            "disposable_corpus_created": False,
            "arcpy_invoked": False,
            "geoprocessing_tool_invoked": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "external_custody_mutated": False,
            "recovery_attempt_reused_or_retried": False,
            "implementation_authorized": False,
            "probe_execution_authorized": False,
            "scientific_result_established": False,
        },
    }
    write_json(PREFLIGHT_REF, preflight)

    doc = f"""# M2 radar delayed-import probe-001 review

**Proposal SHA-256:** `{proposal_sha}`  
**Consumed recovery terminal SHA-256:** `{sha256(TERMINAL_REF)}`  
**Decision state:** zero decisions; owner review required

## Why this is proposed

The one authorized radar recovery is terminal and cannot be reused or retried. It completed the full 156-file, 10,367,157,634-byte identity scan and then failed before DEM creation or source processing with `The Product License has not been initialized.` Read-only review narrowed the historical failure to ArcPy import, `overwriteOutput`, Image Analyst checkout, or Spatial checkout. Current product and extension checks pass, the earlier disposable raster test passed, and default local logs contain no relevant failure artifact. The only evidenced sequence difference is delayed ArcPy import after the large scan; that difference is not proven causal.

## Proposed diagnostic

Approval would authorize implementation, portable synthetic tests, public CI, one final no-content preflight, and only on all passes one live probe in one fresh process. The probe would create 156 deterministic sparse files totaling exactly 10,367,157,634 logical bytes in a probe-specific local temporary directory, hash all of them before importing ArcPy, then write and flush durable before-and-after stage markers around each candidate setup statement. It would finish with two tiny disposable rasters and one `MosaicToNewRaster` operation, check the extensions back in, persist one terminal receipt, and record cleanup. It would use no source bytes, source names, project data, external custody, network, token, installation, or UAC action.

## Result limits

A pass would show only that the current host completed this sequence at that time. A block would identify the last durable stage and sanitized exception for this probe. Neither result would prove the historical root cause, establish recovery readiness, release another radar attempt, or change any satellite, orbit, DEM, AOI, CRS, threshold, mask, route, or QA contract.

## Still prohibited

No recovery-001 reuse or retry, project-data access, orbit application, DEM action, radar pixel processing, route evaluation, baseline, change analysis, interpretation, attribution, derived-pixel publication, or scientific claim is authorized by this packet.

## Decision

Choose `approve`, `revise`, or `defer` for this exact proposal and attest that the decision is complete.
"""
    write_text(DOC_REF, doc)
    render_surface(proposal_sha, sha256(TERMINAL_REF))

    from PIL import Image
    with Image.open(ROOT / IMAGE_REF) as image:
        width, height = image.size
    surface = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-001-REVIEW-SURFACE",
        "rendered_at_utc": args.prepared_at_utc,
        "status": "pass_static_review_surface",
        "artifact_ref": IMAGE_REF,
        "artifact_sha256": sha256(IMAGE_REF),
        "width_px": width,
        "height_px": height,
        "bindings": {
            "proposal_sha256": proposal_sha,
            "terminal_reconciliation_sha256": sha256(TERMINAL_REF),
        },
        "assertions": {
            "human_decision_count": 0,
            "attestation": False,
            "implementation_authorized": False,
            "probe_execution_authorized": False,
            "project_data_content_read": False,
        },
    }
    write_json(SURFACE_REF, surface)

    bundle = {
        "schema_version": "1.0",
        "bundle_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-001-REVIEW-BUNDLE",
        "prepared_at_utc": args.prepared_at_utc,
        "status": "ready_zero_decisions",
        "human_decision_count": 0,
        "artifacts": [
            {"path": PROPOSAL_REF, "sha256": proposal_sha, "purpose": "normative diagnostic proposal", "render_receipts": [{"path": SURFACE_REF, "sha256": sha256(SURFACE_REF)}]},
            {"path": PREFLIGHT_REF, "sha256": sha256(PREFLIGHT_REF), "purpose": "terminal-state and preparation-authority preflight", "render_receipts": []},
            {"path": DOC_REF, "sha256": sha256(DOC_REF), "purpose": "human-readable review", "render_receipts": [{"path": SURFACE_REF, "sha256": sha256(SURFACE_REF)}]},
            {"path": IMAGE_REF, "sha256": sha256(IMAGE_REF), "purpose": "rendered review surface", "render_receipts": [{"path": SURFACE_REF, "sha256": sha256(SURFACE_REF)}]},
        ],
        "decision_items": [{
            "item_id": "M2-RADAR-DELAYED-IMPORT-PROBE-001",
            "allowed_decisions": ["approve", "revise", "defer"],
            "evidence_ref": PROPOSAL_REF,
            "evidence_sha256": proposal_sha,
        }],
    }
    write_json(BUNDLE_REF, bundle)
    bundle_sha = sha256(BUNDLE_REF)

    contract = {
        "schema_version": "1.0",
        "contract_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-001-REVIEW-CONTRACT",
        "status": "open_zero_decisions",
        "review_bundle": {"manifest_ref": BUNDLE_REF, "manifest_sha256": bundle_sha},
        "required_response_path_pattern": f"reviews/{PREFIX}/response-<sha256>.json",
        "required_attestation": True,
        "decision_items": [{
            "item_id": "M2-RADAR-DELAYED-IMPORT-PROBE-001",
            "allowed_decisions": ["approve", "revise", "defer"],
            "evidence_sha256": bundle_sha,
        }],
        "authority_boundary": {
            "packet_creates_authority": False,
            "implementation_authorized": False,
            "probe_execution_authorized": False,
            "project_data_content_read_authorized": False,
            "recovery_retry_or_reuse_authorized": False,
            "radar_processing_authorized": False,
            "baseline_or_change_authorized": False,
            "scientific_publication_authorized": False,
        },
    }
    write_json(CONTRACT_REF, contract)
    blank = {
        "schema_version": "1.0",
        "contract_ref": CONTRACT_REF,
        "contract_sha256": sha256(CONTRACT_REF),
        "review_bundle_sha256": bundle_sha,
        "completed": False,
        "reviewer": {"name": None, "attestation": False},
        "responses": [{
            "item_id": "M2-RADAR-DELAYED-IMPORT-PROBE-001",
            "decision": None,
            "rationale": None,
            "evidence_sha256": bundle_sha,
        }],
        "human_decision_count": 0,
    }
    write_json(BLANK_REF, blank)

    unit = {
        "id": UNIT_ID,
        "purpose": "Review one exact disposable delayed-import diagnostic without releasing recovery or radar processing.",
        "depends_on": ["M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-001-EXECUTION"],
        "action_class": "authority_broadening",
        "human_gate": True,
        "status": "planned",
        "inputs": [
            PREPARATION_APPROVAL_REF,
            PROPOSAL_REF,
            PREFLIGHT_REF,
            BUNDLE_REF,
            CONTRACT_REF,
            BLANK_REF,
            TERMINAL_REF,
            OUTCOME_REF,
            TERMINAL_GATE_REF,
            *OBSERVATION_REFS,
        ],
        "outputs": [],
        "gates": {
            "public_ci": "pending",
            "human_decision_count": 0,
            "attestation": False,
            "implementation_authorized": False,
            "probe_execution_authorized": False,
            "project_data_content_read_authorized": False,
            "recovery_retry_or_reuse_authorized": False,
            "radar_processing_authorized": False,
            "baseline_or_change_authorized": False,
        },
        "disposition": None,
        "retained_failures": [TERMINAL_REF, OUTCOME_REF],
        "exit_condition_delta": {
            "expected": ["successful public CI", "one exact attested owner decision"],
            "observed": ["zero-decision packet prepared under review-preparation-only authority"],
            "decision_value": "unknown",
            "rationale": "The packet creates no implementation, diagnostic-execution, recovery, or scientific authority.",
        },
        "next_dependency": "M2-RADAR-DELAYED-IMPORT-PROBE-001-IMPLEMENTATION",
    }
    if any(item.get("id") == UNIT_ID for item in milestone.get("units", [])):
        raise SystemExit("delayed-import probe review unit collision")
    milestone["units"].append(unit)
    milestone["handoff"].update({
        "current_checkpoint": CHECKPOINT,
        "next_action": NEXT_ACTION,
        "parallel_checkpoint": CHECKPOINT,
        "parallel_next_action": NEXT_ACTION,
    })
    milestone["handoff"].setdefault("do_not_carry_forward", []).append(
        "The delayed-import probe packet is blank and creates no implementation or execution authority; the consumed radar recovery remains terminal and no project data may be read."
    )
    replace_json(MILESTONE_REF, milestone)

    profile["current_checkpoint"] = {
        "checkpoint_id": CHECKPOINT,
        "expected_branch": "main",
        "expected_head": None,
        "next_action": NEXT_ACTION,
    }
    profile["parallel_checkpoints"] = [{
        "checkpoint_id": CHECKPOINT,
        "authority_ref": CONTRACT_REF,
        "next_action": NEXT_ACTION,
    }]
    gates = profile.setdefault("human_gates", {}).setdefault("review_gates", [])
    gates.append({
        "unit_id": UNIT_ID,
        "reason": "Any ArcPy delayed-import diagnostic execution requires exact owner approval of the public zero-decision packet.",
        "authority_ref": CONTRACT_REF,
    })
    profile["control_surfaces"]["proposed_amendments"] = [PROPOSAL_REF]
    replace_json(PROFILE_REF, profile)

    goal["current_checkpoint"] = CHECKPOINT
    goal["parallel_checkpoints"] = [CHECKPOINT]
    goal["proposed_amendments"] = [PROPOSAL_REF]
    replace_json(GOAL_REF, goal)

    readiness = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-001-REVIEW-READINESS",
        "recorded_at_utc": args.prepared_at_utc,
        "status": "pass_ready_publication_zero_decisions",
        "bindings": {ref: sha256(ref) for ref in [
            PREPARATION_APPROVAL_REF,
            PROPOSAL_REF,
            PREFLIGHT_REF,
            DOC_REF,
            IMAGE_REF,
            SURFACE_REF,
            BUNDLE_REF,
            CONTRACT_REF,
            BLANK_REF,
            TERMINAL_REF,
            OUTCOME_REF,
            TERMINAL_GATE_REF,
            *OBSERVATION_REFS,
            MILESTONE_REF,
            PROFILE_REF,
            GOAL_REF,
        ]},
        "checks": {
            "proposal_sha256": proposal_sha,
            "review_bundle_sha256": bundle_sha,
            "human_decision_count": 0,
            "blank_response": True,
            "terminal_recovery_001_preserved": True,
            "exact_disposable_corpus_file_count": CORPUS_FILE_COUNT,
            "exact_disposable_corpus_logical_bytes": CORPUS_LOGICAL_BYTES,
        },
        "released_now": {
            "public_review_packet_ci": True,
            "owner_review_after_public_ci": True,
            "implementation": False,
            "probe_execution": False,
            "project_data_content_read": False,
            "recovery_retry_or_reuse": False,
            "radar_processing": False,
        },
        "assertions": {
            "human_decisions_fabricated": False,
            "probe_process_started": False,
            "disposable_corpus_created": False,
            "arcpy_invoked": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "external_custody_mutated": False,
            "implementation_authorized": False,
            "probe_execution_authorized": False,
            "recovery_attempt_reused_or_retried": False,
            "scientific_result_established": False,
        },
    }
    write_json(READINESS_REF, readiness)
    print(json.dumps({
        "proposal_sha256": proposal_sha,
        "review_bundle_sha256": bundle_sha,
        "readiness_sha256": sha256(READINESS_REF),
        "checkpoint": CHECKPOINT,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
