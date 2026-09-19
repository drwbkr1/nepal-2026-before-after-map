#!/usr/bin/env python3
"""Prepare a local zero-decision review packet for probe receipt recovery-001."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import textwrap
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-delayed-import-probe-receipt-recovery-001"
PROPOSAL_REF = "contracts/milestone-002-radar-delayed-import-probe-receipt-recovery-001-proposal.json"
PREPARATION_APPROVAL_REF = f"records/source-gates/{PREFIX}-review-preparation-approval.json"
PREFLIGHT_REF = f"records/readiness/{PREFIX}-review-preflight.json"
DOC_REF = "docs/M2_RADAR_DELAYED_IMPORT_PROBE_RECEIPT_RECOVERY_001_REVIEW.md"
IMAGE_REF = f"docs/assets/{PREFIX}-review.png"
SURFACE_REF = f"records/surface-receipts/{PREFIX}-review.json"
BUNDLE_REF = f"reviews/{PREFIX}/review-bundle.json"
CONTRACT_REF = f"reviews/{PREFIX}/review-contract.json"
BLANK_REF = f"reviews/{PREFIX}/blank-response.json"
READINESS_REF = f"records/readiness/{PREFIX}-review-readiness.json"

TERMINAL_REF = "records/processing/m2-radar-delayed-import-probe-001-terminal-reconciliation.json"
OUTCOME_REF = "records/processing/m2-radar-delayed-import-probe-001-outcome-reconciliation.json"
TERMINAL_GATE_REF = "records/readiness/m2-radar-delayed-import-probe-001-terminal-publication-gate.json"
PROBE_CONTRACT_REF = "config/qa/m2-radar-delayed-import-probe-001-contract.json"
PROBE_CORE_REF = "scripts/m2_radar_delayed_import_probe_001_core.py"
PROBE_RUNNER_REF = "scripts/run_m2_radar_delayed_import_probe_001.py"
PROBE_TEST_REF = "tests/test_m2_radar_delayed_import_probe_001.py"
MILESTONE_REF = "contracts/milestone-002.json"
PROFILE_REF = "records/project-control-profile.json"
GOAL_REF = "records/long-term-goal.json"

BASE_COMMIT = "4e47ddc0b201ca86381234e851b58d0c72733211"
CURRENT_CHECKPOINT = "M2-RADAR-DELAYED-IMPORT-PROBE-001-TERMINAL-REVIEW"
CONSUMED_ATTEMPT_ID = "radar-delayed-import-probe-001-real-001"
PROPOSED_ATTEMPT_ID = "radar-delayed-import-probe-receipt-recovery-001-real-001"
CORPUS_FILE_COUNT = 156
CORPUS_LOGICAL_BYTES = 10_367_157_634
CORPUS_SHA256 = "dd56f8b28a1ed1c6e2b4b1d7d8f5db4fd86dab80a910fe79c8d018d58942430b"
PROTECTED_HASHES = {
    PROBE_CONTRACT_REF: "c9bf8154bfb44cf6a76a9cdfc695c30b7e2bf2349d64ab9e8c0e922ca0b70ac0",
    PROBE_CORE_REF: "b15bcc4f6ec4034aa890d551f3d700977367e9f1bc7e28c69cbdd50f17588d2a",
    PROBE_RUNNER_REF: "189f59a81733e163c07d72abacf917b9e8482af871b323402a84047ec816792c",
    PROBE_TEST_REF: "b6d01b9e18d6a0448fb53581d7ae522ca97db17ec337420ca8ccce226b0cfa02",
}


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


def git_value(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def render_surface(proposal_sha: str, terminal_sha: str) -> None:
    from PIL import Image, ImageDraw, ImageFont

    def font(name: str, size: int):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            return ImageFont.load_default()

    image = Image.new("RGB", (1800, 1880), "#f4f1e9")
    draw = ImageDraw.Draw(image)
    title = font("arialbd.ttf", 42)
    heading = font("arialbd.ttf", 28)
    body = font("arial.ttf", 22)
    small = font("arial.ttf", 18)
    callout = font("arialbd.ttf", 24)
    draw.rectangle((0, 0, 1800, 178), fill="#17324d")
    draw.text((62, 26), "M2 Probe Receipt Recovery 001", font=title, fill="white")
    draw.text((64, 98), f"Proposal {proposal_sha}", font=small, fill="#dce8f2")
    draw.text((64, 130), f"Consumed probe terminal {terminal_sha}", font=small, fill="#dce8f2")
    sections = [
        (
            "Observed terminal state",
            [
                "The consumed probe created and fully hashed 156 disposable sparse files totaling 10,367,157,634 logical bytes.",
                "Its last durable marker is arcpy_import_started. A later timestamp AttributeError masked the original caught exception, so ArcPy import completion and the original failure cannot be reconstructed.",
                "The corpus was removed by postprocess cleanup. No project data, external custody, radar pixels, baseline, or change analysis was accessed.",
            ],
        ),
        (
            "Proposed correction",
            [
                "Use a function-local datetime-module binding for every receipt timestamp; change no probe stage, corpus, geoprocessing, source, or scientific rule.",
                "Before any corpus creation, reserve terminal and cleanup receipt identities and create a minimal append-only fallback journal.",
                "Snapshot and sanitize the original caught exception before normal terminal assembly. If normal serialization fails, retain both the original exception and the persistence failure in the fallback journal.",
                "Make cleanup evidence independent of normal terminal serialization and test timestamp rebinding, terminal-write failure, interruption, exact order, and secret or project-path rejection.",
            ],
        ),
        (
            "Future gated attempt",
            [
                "Only after separate publication authority, successful public CI, exact owner approval, and a final no-content preflight: run at most one fresh append-only attempt with the same 156 files, byte total, stable-order full hash, two tiny rasters, and one mosaic.",
                "The consumed attempt remains unchanged and cannot be resumed, reused, or retried. The proposed attempt has a new exact identity and no automatic retry.",
                "PASS or BLOCK would describe only that new disposable diagnostic. Neither result would establish historical cause, radar recovery readiness, or a scientific claim.",
            ],
        ),
    ]
    y = 220
    for label, lines in sections:
        draw.text((64, y), label, font=heading, fill="#17324d")
        y += 46
        for line in lines:
            wrapped = textwrap.wrap(line, 105)
            for index, part in enumerate(wrapped):
                draw.text((92, y), ("• " if index == 0 else "  ") + part, font=body, fill="#20252b")
                y += 34
        y += 18
    draw.rectangle((60, 1672, 1740, 1808), outline="#9b6b21", width=3)
    draw.text((82, 1698), "Current authority: local packet preparation only.", font=callout, fill="#7a4e0b")
    draw.text((82, 1740), "Next gate: explicit publication and public-CI authorization.", font=callout, fill="#7a4e0b")
    draw.text((82, 1782), "Implementation, ArcPy, corpus creation, and a new attempt remain prohibited.", font=small, fill="#7a4e0b")
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
        PREPARATION_APPROVAL_REF,
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

    head = git_value("rev-parse", "HEAD")
    origin = git_value("rev-parse", "origin/main")
    terminal = load(TERMINAL_REF)
    outcome = load(OUTCOME_REF)
    terminal_gate = load(TERMINAL_GATE_REF)
    milestone = load(MILESTONE_REF)
    profile = load(PROFILE_REF)
    goal = load(GOAL_REF)
    if head != BASE_COMMIT or origin != BASE_COMMIT:
        raise SystemExit("preparation base commit is not the exact public terminal checkpoint")
    if {ref: sha256(ref) for ref in PROTECTED_HASHES} != PROTECTED_HASHES:
        raise SystemExit("protected delayed-import probe implementation changed")
    if (
        terminal.get("status") != "block_terminal_receipt_persistence_failure_no_retry"
        or terminal.get("attempt_id") != CONSUMED_ATTEMPT_ID
        or terminal.get("process_failure", {}).get("failure_code") != "terminal_timestamp_construction_failed"
        or terminal.get("process_failure", {}).get("original_caught_exception_recoverable") is not False
        or terminal.get("durable_stage_evidence", {}).get("last_durable_stage") != "arcpy_import_started"
        or outcome.get("status") != "block_probe_terminal_persistence_failure_no_retry"
        or outcome.get("assertions", {}).get("attempt_consumed") is not True
        or terminal_gate.get("status") != "pass_public_terminal_state_owner_review_only"
        or terminal_gate.get("released_now", {}).get("follow_on_review_preparation") is not False
        or milestone.get("handoff", {}).get("current_checkpoint") != CURRENT_CHECKPOINT
        or profile.get("current_checkpoint", {}).get("checkpoint_id") != CURRENT_CHECKPOINT
        or goal.get("current_checkpoint") != CURRENT_CHECKPOINT
    ):
        raise SystemExit("terminal evidence or canonical checkpoint is not the exact preparation base")

    preparation_approval = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-REVIEW-PREPARATION-APPROVAL",
        "recorded_at_utc": args.prepared_at_utc,
        "status": "approved_local_review_preparation_only",
        "authority_basis": {
            "owner_instruction": "I authorize preparation.",
            "instruction_context": "terminal review of the consumed radar delayed-import probe-001 outcome",
            "attestation_claimed": False,
        },
        "approved_scope": [
            "prepare one local zero-decision follow-on review packet",
            "render and locally validate that packet",
            "record exact proposal and bundle identities for a later publication decision",
        ],
        "authority_boundary": {
            "local_review_packet_preparation_authorized": True,
            "local_validation_authorized": True,
            "git_commit_authorized": False,
            "public_review_packet_publication_authorized": False,
            "public_ci_authorized": False,
            "owner_proposal_decision_recording_authorized": False,
            "recovery_implementation_authorized": False,
            "arcpy_invocation_authorized": False,
            "disposable_corpus_creation_authorized": False,
            "new_probe_attempt_authorized": False,
            "project_data_or_external_custody_access_authorized": False,
            "radar_processing_authorized": False,
            "baseline_or_change_authorized": False,
            "scientific_publication_authorized": False,
        },
        "bindings": {
            "terminal_reconciliation_ref": TERMINAL_REF,
            "terminal_reconciliation_sha256": sha256(TERMINAL_REF),
            "outcome_reconciliation_ref": OUTCOME_REF,
            "outcome_reconciliation_sha256": sha256(OUTCOME_REF),
            "terminal_publication_gate_ref": TERMINAL_GATE_REF,
            "terminal_publication_gate_sha256": sha256(TERMINAL_GATE_REF),
            "base_commit": head,
        },
    }
    write_json(PREPARATION_APPROVAL_REF, preparation_approval)

    proposal = {
        "schema_version": "1.0",
        "proposal_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-PROPOSAL",
        "prepared_at_utc": args.prepared_at_utc,
        "status": "proposed_inactive_local_review_prepared_publication_and_owner_approval_required",
        "preparation_base_commit": head,
        "preparation_authority": {
            "ref": PREPARATION_APPROVAL_REF,
            "sha256": sha256(PREPARATION_APPROVAL_REF),
            "local_preparation_only": True,
            "public_publication_authorized": False,
            "implementation_authorized": False,
            "new_attempt_authorized": False,
        },
        "trigger": {
            "terminal_reconciliation_ref": TERMINAL_REF,
            "terminal_reconciliation_sha256": sha256(TERMINAL_REF),
            "outcome_reconciliation_ref": OUTCOME_REF,
            "outcome_reconciliation_sha256": sha256(OUTCOME_REF),
            "terminal_publication_gate_ref": TERMINAL_GATE_REF,
            "terminal_publication_gate_sha256": sha256(TERMINAL_GATE_REF),
            "consumed_attempt_id": CONSUMED_ATTEMPT_ID,
            "last_durable_stage": "arcpy_import_started",
            "terminal_failure_code": "terminal_timestamp_construction_failed",
            "terminal_failure_type": "AttributeError",
            "terminal_failure_message": "module 'datetime' has no attribute 'now'",
            "original_caught_exception_recoverable": False,
        },
        "observed_state": {
            "consumed_attempt_terminal": True,
            "consumed_attempt_retry_or_reuse_authorized": False,
            "corpus_create_completed": True,
            "corpus_hash_completed": True,
            "corpus_file_count": CORPUS_FILE_COUNT,
            "corpus_total_logical_bytes": CORPUS_LOGICAL_BYTES,
            "corpus_aggregate_sha256": CORPUS_SHA256,
            "arcpy_import_started_durable": True,
            "arcpy_import_completed_durable": False,
            "runner_terminal_receipt_persisted": False,
            "runner_cleanup_receipt_persisted": False,
            "postprocess_cleanup_completed": True,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "historical_root_cause_established": False,
            "post_observation_bias": "This proposal is informed by the consumed probe's terminal behavior and is not blind or independent validation.",
        },
        "protected_public_implementation": [
            {"path": ref, "sha256": digest, "must_remain_unchanged_during_preparation": True}
            for ref, digest in PROTECTED_HASHES.items()
        ],
        "proposed_exact_changes": [
            "preserve the consumed delayed-import probe attempt, its public contract, runner, core, tests, receipts, reconciliations, and cleanup evidence unchanged",
            "replace module-global datetime class reliance in the proposed recovery implementation with a function-local datetime-module import for each timestamp construction; change no diagnostic or scientific predicate",
            "before any disposable corpus creation, exclusively reserve the new attempt root plus immutable terminal-receipt and cleanup-receipt identity records and initialize one minimal append-only fallback journal",
            "immediately reduce any caught probe exception to sanitized primitive fields and append it to the fallback journal before ordinary terminal payload construction or timestamping",
            "if ordinary terminal construction or persistence fails, append the terminal-persistence exception without replacing the preserved original exception; never reconstruct a missing success",
            "run cleanup from an outer finally path independent of ordinary terminal serialization and append its disposition even when terminal persistence fails",
            "add portable synthetic tests for timestamp-name rebinding, forced terminal-write failure, original-error retention, cleanup persistence, interruption, exact stage order, one-attempt enforcement, and secret or project-path rejection",
            "add one installed ArcGIS-runtime synthetic test that exercises timestamp rebinding and receipt fallback without project data, external custody, or geoprocessing inputs",
            "require successful local validation, a separately authorized public default-branch publication and CI gate, exact attested owner approval, and one final no-content preflight before any new live attempt",
            "only on all gates run at most one fresh append-only diagnostic attempt using the unchanged exact disposable corpus, stage order, two tiny rasters, and one MosaicToNewRaster operation",
            "reconcile that new attempt without changing any radar, source, orbit, DEM, AOI, CRS, threshold, mask, route, or QA contract",
        ],
        "future_gate_sequence": [
            "explicit owner authorization to commit and publish this exact zero-decision packet and run public default-branch CI",
            "successful public default-branch CI on the exact packet commit",
            "exact attested owner approval of the published review bundle and proposal",
            "bounded recovery implementation and synthetic validation",
            "successful public default-branch CI on the exact implementation commit",
            "one final no-content preflight",
            "at most one fresh append-only real attempt",
        ],
        "exact_recovery_contract": {
            "attempt_id": PROPOSED_ATTEMPT_ID,
            "distinct_from_consumed_attempt": True,
            "process_count": 1,
            "corpus": {
                "content_class": "deterministic_disposable_zero_bytes",
                "file_count": CORPUS_FILE_COUNT,
                "total_logical_bytes": CORPUS_LOGICAL_BYTES,
                "expected_stable_order_aggregate_sha256": CORPUS_SHA256,
                "source_names_or_source_bytes_used": False,
                "path_class": "new probe-specific local temporary root outside Git and external custody",
            },
            "stage_order_unchanged_from_probe_001_contract": True,
            "geoprocessing_unchanged": {
                "inputs": "two deterministic 2 by 2 disposable rasters",
                "operation": "arcpy.management.MosaicToNewRaster",
                "output": "one disposable local raster",
                "project_crs_or_project_aoi_used": False,
            },
            "receipt_durability": {
                "terminal_identity_reserved_before_corpus": True,
                "cleanup_identity_reserved_before_corpus": True,
                "fallback_journal_initialized_before_corpus": True,
                "original_sanitized_exception_recorded_before_normal_terminal_assembly": True,
                "normal_terminal_and_cleanup_receipts_remain_required": True,
                "fallback_is_not_success_evidence": True,
            },
            "result_semantics": {
                "pass": "the current host completed the exact fresh disposable diagnostic sequence at that time only",
                "block": "the fresh attempt's durable markers and receipts identify its observed boundary only",
                "historical_root_cause_claim_allowed": False,
                "radar_recovery_readiness_claim_allowed": False,
                "scientific_claim_allowed": False,
            },
        },
        "limits": {
            "consumed_attempt_retries_or_reuses": 0,
            "future_live_attempts": 1,
            "automatic_retry": False,
            "processes": 1,
            "network_requests": 0,
            "credential_or_token_actions": 0,
            "software_installations": 0,
            "uac_actions": 0,
            "project_data_content_reads": 0,
            "external_custody_reads": 0,
            "external_custody_mutations": 0,
            "orbit_applications": 0,
            "radar_pixel_reads": 0,
            "baseline_or_change_actions": 0,
            "scientific_outputs": 0,
        },
        "stop_rules": [
            "Stop before Git commit, push, public CI, implementation, ArcPy import, corpus creation, or a new attempt under the present preparation-only authority.",
            "Stop if any protected public probe artifact or terminal evidence identity differs from this proposal.",
            "Do not reconstruct the original caught exception or reinterpret the consumed attempt as retryable.",
            "Do not run a second recovery attempt after any pass, block, interruption, or persistence failure.",
        ],
        "does_not_authorize_now": [
            "Git commit, push, public review publication, or public CI",
            "owner proposal approval, response locking, activation, implementation, tests that invoke ArcPy, preflight, corpus creation, or a live attempt",
            "reuse, resume, retry, mutation, or reconstruction of the consumed probe attempt",
            "project-data or external-custody access, network, credentials, account, terms, installation, or UAC action",
            "orbit application, DEM action, radar pixel processing, route evaluation, baseline, change analysis, interpretation, attribution, emergency guidance, derived-pixel publication, or scientific publication",
            "a historical root-cause, radar-recovery-readiness, or scientific claim",
        ],
        "decision_domain_after_public_ci": ["approve", "revise", "defer"],
        "attestation_required_after_public_ci": True,
        "human_decision_count": 0,
    }
    write_json(PROPOSAL_REF, proposal)
    proposal_sha = sha256(PROPOSAL_REF)

    preflight = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-REVIEW-PREFLIGHT",
        "checked_at_utc": args.prepared_at_utc,
        "status": "pass_ready_local_zero_decision_packet_preparation_only",
        "bindings": {
            "preparation_approval_ref": PREPARATION_APPROVAL_REF,
            "preparation_approval_sha256": sha256(PREPARATION_APPROVAL_REF),
            "proposal_ref": PROPOSAL_REF,
            "proposal_sha256": proposal_sha,
            "terminal_reconciliation_sha256": sha256(TERMINAL_REF),
            "outcome_reconciliation_sha256": sha256(OUTCOME_REF),
            "terminal_publication_gate_sha256": sha256(TERMINAL_GATE_REF),
            "preparation_script_sha256": sha256("scripts/prepare_m2_radar_delayed_import_probe_receipt_recovery_001_review.py"),
            "base_commit": head,
        },
        "checks": {
            "terminal_attempt_consumed": True,
            "original_caught_exception_unrecoverable": True,
            "protected_public_implementation_exact": True,
            "canonical_checkpoint_unchanged": True,
            "local_preparation_authorized": True,
            "publication_or_implementation_authorized": False,
        },
        "assertions": {
            "git_commit_created": False,
            "git_push_performed": False,
            "public_ci_started": False,
            "protected_probe_code_modified": False,
            "arcpy_invoked": False,
            "disposable_corpus_created": False,
            "new_attempt_created": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "implementation_authorized": False,
            "scientific_result_established": False,
        },
    }
    write_json(PREFLIGHT_REF, preflight)

    document = f"""# M2 radar delayed-import probe receipt recovery-001 review

**Proposal SHA-256:** `{proposal_sha}`  
**Consumed probe terminal SHA-256:** `{sha256(TERMINAL_REF)}`  
**Decision state:** zero decisions; prepared locally; publication is not authorized

## Observed terminal state

The single authorized delayed-import probe is terminal and consumed. It created and fully hashed {CORPUS_FILE_COUNT} disposable sparse files totaling {CORPUS_LOGICAL_BYTES:,} logical bytes, with aggregate SHA-256 `{CORPUS_SHA256}`. Its last durable stage is `arcpy_import_started`.

After the probe caught an underlying exception, ordinary terminal construction failed with `AttributeError: module 'datetime' has no attribute 'now'`. That second failure masked the original caught exception. No runner terminal or cleanup receipt was written, although postprocess reconciliation removed the disposable corpus and retained the started and stage records. ArcPy import completion and the original exception cannot be reconstructed.

No project data, external custody, network credential, radar pixel, baseline, change-analysis, interpretation, attribution, or scientific action occurred.

## Proposed bounded correction

The proposed implementation would change only receipt durability and error retention. Every timestamp would use a function-local datetime-module binding. Before any corpus creation, the fresh attempt would reserve immutable terminal and cleanup receipt identities and initialize a minimal append-only fallback journal. A caught exception would be reduced immediately to sanitized primitive fields and appended before ordinary terminal assembly. If normal terminal construction or persistence also failed, the fallback journal would retain both errors. Cleanup evidence would run from an outer `finally` path independent of normal terminal serialization.

Portable tests would cover timestamp-name rebinding, forced terminal-write failure, retention of the original error, cleanup persistence, interruption, exact stage order, one-attempt enforcement, and secret or project-path rejection. One installed ArcGIS-runtime synthetic test would exercise the timestamp and fallback behavior without project data or external custody.

## Proposed future attempt

Only after separate authorization to publish this packet, successful public default-branch CI, exact attested owner approval, bounded implementation, successful implementation CI, and a final no-content preflight would the project run at most one fresh append-only attempt: `{PROPOSED_ATTEMPT_ID}`.

That attempt would use the unchanged {CORPUS_FILE_COUNT}-file, {CORPUS_LOGICAL_BYTES:,}-byte disposable corpus, the same stable-order full hash, the same stage order, two tiny disposable rasters, and one `MosaicToNewRaster` operation. It would use no source names or bytes, project data, external custody, network, credential, installation, or UAC action. The consumed `{CONSUMED_ATTEMPT_ID}` path would remain untouched and could not be resumed, reused, or retried.

## Claim limits

A pass would show only that the current host completed the fresh disposable diagnostic at that time. A block would identify the new attempt's durable boundary. Neither result would establish the historical failure cause, radar recovery readiness, baseline admission, change, interpretation, attribution, or a scientific claim.

## Current authority and next gate

The current owner instruction authorizes local packet preparation and validation only. It does not authorize a Git commit, push, public CI, implementation, ArcPy invocation, corpus creation, or a new attempt.

The next required decision is whether to commit and publish this exact zero-decision packet and run public default-branch CI. The later `approve`, `revise`, or `defer` proposal decision remains unavailable until that public gate passes.
"""
    write_text(DOC_REF, document)
    render_surface(proposal_sha, sha256(TERMINAL_REF))

    surface = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-REVIEW-SURFACE",
        "rendered_at_utc": args.prepared_at_utc,
        "status": "pass_static_review_surface_generated_pending_agent_visual_inspection",
        "artifact_ref": IMAGE_REF,
        "artifact_sha256": sha256(IMAGE_REF),
        "width_px": 1800,
        "height_px": 1880,
        "bindings": {
            "proposal_sha256": proposal_sha,
            "terminal_reconciliation_sha256": sha256(TERMINAL_REF),
        },
        "assertions": {
            "human_decision_count": 0,
            "attestation": False,
            "publication_authorized": False,
            "implementation_authorized": False,
            "new_attempt_authorized": False,
            "project_data_content_read": False,
        },
    }
    write_json(SURFACE_REF, surface)

    bundle = {
        "schema_version": "1.0",
        "bundle_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-REVIEW-BUNDLE",
        "prepared_at_utc": args.prepared_at_utc,
        "status": "locally_prepared_zero_decisions_publication_authority_required",
        "human_decision_count": 0,
        "artifacts": [
            {
                "path": PROPOSAL_REF,
                "sha256": proposal_sha,
                "purpose": "normative receipt-recovery proposal",
                "render_receipts": [{"path": SURFACE_REF, "sha256": sha256(SURFACE_REF)}],
            },
            {
                "path": PREFLIGHT_REF,
                "sha256": sha256(PREFLIGHT_REF),
                "purpose": "terminal-state and preparation-authority preflight",
                "render_receipts": [],
            },
            {
                "path": DOC_REF,
                "sha256": sha256(DOC_REF),
                "purpose": "human-readable local review",
                "render_receipts": [{"path": SURFACE_REF, "sha256": sha256(SURFACE_REF)}],
            },
            {
                "path": IMAGE_REF,
                "sha256": sha256(IMAGE_REF),
                "purpose": "rendered local review surface",
                "render_receipts": [{"path": SURFACE_REF, "sha256": sha256(SURFACE_REF)}],
            },
        ],
        "decision_items": [
            {
                "item_id": "M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001",
                "allowed_decisions_after_public_ci": ["approve", "revise", "defer"],
                "decision_currently_open": False,
                "evidence_ref": PROPOSAL_REF,
                "evidence_sha256": proposal_sha,
            }
        ],
    }
    write_json(BUNDLE_REF, bundle)
    bundle_sha = sha256(BUNDLE_REF)

    contract = {
        "contract_version": "human-review-contract-v1",
        "template": False,
        "review_id": f"{PREFIX}-review",
        "response_schema_version": "nepal-m2-radar-delayed-import-probe-receipt-recovery-001-response-v1",
        "status": "locally_prepared_not_public_owner_response_not_yet_open",
        "workflow_authority": {
            "mode": "local_preparation_only",
            "authority_ref": PREPARATION_APPROVAL_REF,
            "authorized_action_classes": ["local_evidence_preparation", "local_validation"],
            "verified_at_utc": args.prepared_at_utc,
            "expires_at_utc": None,
            "public_review_publication_authorized": False,
            "review_response_open": False,
            "lock_authorized": False,
            "reconcile_authorized": False,
        },
        "review_bundle": {
            "bundle_id": bundle["bundle_id"],
            "manifest_sha256": bundle_sha,
            "candidate_identity": f"M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-PROPOSAL-SHA256:{proposal_sha}",
            "rendered_surface_generated": True,
            "public_ci_verified": False,
        },
        "allowed_decisions_after_public_ci": ["approve", "revise", "defer"],
        "required_attestation": True,
        "items": [
            {
                "item_id": "M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001",
                "evidence_sha256": bundle_sha,
            }
        ],
        "authority_boundary": {
            "packet_creates_authority": False,
            "git_commit_or_push_authorized": False,
            "public_ci_authorized": False,
            "implementation_authorized": False,
            "arcpy_invocation_authorized": False,
            "new_attempt_authorized": False,
            "project_data_or_external_custody_access_authorized": False,
            "radar_processing_authorized": False,
            "baseline_or_change_authorized": False,
            "scientific_publication_authorized": False,
        },
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
                "item_id": "M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001",
                "evidence_sha256": bundle_sha,
                "decision": None,
                "notes": "",
            }
        ],
        "human_decision_count": 0,
        "response_not_open_until_public_ci": True,
    }
    write_json(BLANK_REF, blank)

    readiness = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-REVIEW-READINESS",
        "verified_at_utc": args.prepared_at_utc,
        "status": "pass_local_zero_decision_packet_ready_publication_authority_required",
        "bindings": {
            "preparation_approval_ref": PREPARATION_APPROVAL_REF,
            "preparation_approval_sha256": sha256(PREPARATION_APPROVAL_REF),
            "proposal_ref": PROPOSAL_REF,
            "proposal_sha256": proposal_sha,
            "review_preflight_ref": PREFLIGHT_REF,
            "review_preflight_sha256": sha256(PREFLIGHT_REF),
            "review_document_ref": DOC_REF,
            "review_document_sha256": sha256(DOC_REF),
            "review_surface_ref": IMAGE_REF,
            "review_surface_sha256": sha256(IMAGE_REF),
            "surface_receipt_ref": SURFACE_REF,
            "surface_receipt_sha256": sha256(SURFACE_REF),
            "review_bundle_ref": BUNDLE_REF,
            "review_bundle_sha256": bundle_sha,
            "review_contract_ref": CONTRACT_REF,
            "review_contract_sha256": sha256(CONTRACT_REF),
            "blank_response_ref": BLANK_REF,
            "blank_response_sha256": sha256(BLANK_REF),
            "terminal_reconciliation_ref": TERMINAL_REF,
            "terminal_reconciliation_sha256": sha256(TERMINAL_REF),
            "outcome_reconciliation_ref": OUTCOME_REF,
            "outcome_reconciliation_sha256": sha256(OUTCOME_REF),
        },
        "validation": {
            "consumed_attempt_preserved": True,
            "protected_public_implementation_preserved": True,
            "post_observation_limit_disclosed": True,
            "human_decision_count": 0,
            "blank_response_verified": True,
            "rendered_surface_generated": True,
            "canonical_checkpoint_intentionally_unchanged": True,
        },
        "released_now": {
            "local_packet_preparation": True,
            "local_packet_validation": True,
            "git_commit_or_push": False,
            "public_ci": False,
            "owner_proposal_review": False,
            "implementation": False,
            "arcpy_invocation": False,
            "disposable_corpus_creation": False,
            "new_probe_attempt": False,
            "project_data_or_external_custody_access": False,
            "radar_processing": False,
            "baseline_or_change_analysis": False,
            "scientific_publication": False,
        },
        "assertions": {
            "human_decisions_fabricated": False,
            "git_commit_created": False,
            "git_push_performed": False,
            "public_ci_started": False,
            "protected_probe_code_modified": False,
            "arcpy_invoked": False,
            "disposable_corpus_created": False,
            "new_attempt_created": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "implementation_authorized": False,
            "scientific_result_established": False,
        },
        "next_action": "Obtain explicit owner authorization to commit and publish this exact zero-decision packet and run public default-branch CI; do not open the owner proposal response before that gate passes.",
    }
    write_json(READINESS_REF, readiness)

    print(
        json.dumps(
            {
                "status": readiness["status"],
                "proposal_sha256": proposal_sha,
                "review_bundle_sha256": bundle_sha,
                "readiness_sha256": sha256(READINESS_REF),
                "canonical_checkpoint": CURRENT_CHECKPOINT,
                "next_gate": "explicit publication and public-CI authorization",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
