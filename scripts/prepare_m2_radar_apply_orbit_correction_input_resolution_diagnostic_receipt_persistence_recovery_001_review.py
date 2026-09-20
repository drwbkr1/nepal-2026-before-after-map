#!/usr/bin/env python3
"""Prepare the local zero-decision review packet for diagnostic receipt recovery-001."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import textwrap
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-apply-orbit-correction-input-resolution-diagnostic-receipt-persistence-recovery-001"
SOURCE_PREFIX = "m2-radar-apply-orbit-correction-input-resolution-diagnostic-001"
PROPOSAL_REF = f"contracts/milestone-002-{PREFIX.removeprefix('m2-')}-proposal.json"
PREPARATION_APPROVAL_REF = f"records/source-gates/{PREFIX}-review-preparation-approval.json"
FAILURE_OBSERVATION_REF = f"records/readiness/{SOURCE_PREFIX}-terminal-receipt-persistence-failure-observation.json"
PREFLIGHT_REF = f"records/readiness/{PREFIX}-review-preflight.json"
DOC_REF = "docs/M2_RADAR_APPLY_ORBIT_CORRECTION_INPUT_RESOLUTION_DIAGNOSTIC_RECEIPT_PERSISTENCE_RECOVERY_001_REVIEW.md"
IMAGE_REF = f"docs/assets/{PREFIX}-review.png"
SURFACE_REF = f"records/surface-receipts/{PREFIX}-review.json"
BUNDLE_REF = f"reviews/{PREFIX}/review-bundle.json"
CONTRACT_REF = f"reviews/{PREFIX}/review-contract.json"
BLANK_REF = f"reviews/{PREFIX}/blank-response.json"
PREVISUAL_READINESS_REF = f"records/readiness/{PREFIX}-review-readiness-previsual.json"
PREPARATION_SCRIPT_REF = f"scripts/{Path(__file__).name}"
VISUAL_FINALIZER_REF = f"scripts/finalize_{PREFIX.replace('-', '_')}_review.py"
TEST_REF = f"tests/test_{PREFIX.replace('-', '_')}_review.py"

SOURCE_CONTRACT_REF = f"config/qa/{SOURCE_PREFIX}-contract.json"
SOURCE_CORE_REF = f"scripts/{SOURCE_PREFIX.replace('-', '_')}_core.py"
SOURCE_RUNNER_REF = f"scripts/run_{SOURCE_PREFIX.replace('-', '_')}.py"
SOURCE_TEST_REF = f"tests/test_{SOURCE_PREFIX.replace('-', '_')}.py"
SOURCE_APPROVAL_REF = f"records/source-gates/{SOURCE_PREFIX}-approval.json"
IMPLEMENTATION_GATE_REF = f"records/readiness/{SOURCE_PREFIX}-implementation-publication-gate.json"
GATE_STATE_REF = f"records/readiness/{SOURCE_PREFIX}-gate-state-publication.json"
FINAL_PREFLIGHT_REF = f"records/readiness/{SOURCE_PREFIX}-final-preflight.json"
TERMINAL_REF = f"records/processing/{SOURCE_PREFIX}-terminal.json"
CLEANUP_REF = f"records/processing/{SOURCE_PREFIX}-cleanup.json"
MILESTONE_REF = "contracts/milestone-002.json"
PROFILE_REF = "records/project-control-profile.json"
GOAL_REF = "records/long-term-goal.json"

BASE_COMMIT = "b705dadd8ab989e1dcbfa04d9a3bd082064a6177"
CURRENT_CHECKPOINT = "M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-EXECUTION"
CONSUMED_ATTEMPT_ID = "radar-apply-orbit-correction-input-resolution-diagnostic-001-real-001"
PROPOSED_ATTEMPT_ID = (
    "radar-apply-orbit-correction-input-resolution-diagnostic-receipt-persistence-recovery-001-real-001"
)
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
OWNER_INSTRUCTION = (
    "I authorize preparation of an M2 radar ApplyOrbitCorrection input-resolution diagnostic "
    "receipt-persistence recovery-001 review packet based on the preserved terminal failure evidence. "
    "I authorize only local zero-decision proposal and review preparation and validation. This does not "
    "authorize Git publication, ArcPy invocation, project-data or external-custody access, a new diagnostic "
    "process, retry, reconstruction, mutation of the reserved receipts, geoprocessing, radar processing, "
    "baseline or change analysis, attribution, or scientific publication. I attest this is my completed decision."
)
PROTECTED_HASHES = {
    SOURCE_CONTRACT_REF: "e390c0918947eaac49df025bf1b3c6c0ee35804c04404b12a42597dc4411e724",
    SOURCE_CORE_REF: "9d6ca7be8514b62d088eea3e1648b002ae40f25555ab620ca298efa37b7d5129",
    SOURCE_RUNNER_REF: "34239fb9669559f1668887c89b08db5f7e213cfea3132ef0eeb3dffebd041d8f",
    SOURCE_TEST_REF: "3741af9396bf25b3fc22d35560e92ad1cea90cf964a4ba99384e6fe78014ca1d",
    SOURCE_APPROVAL_REF: "be935d0011e2819debf45f4bc335ec035bc6e718380a3ad0429d5be88b269287",
    IMPLEMENTATION_GATE_REF: "e448a17b4aefef44d7e6bd3ba45838bcbda1e0b6df8569ef948511fd8aaba61d",
    GATE_STATE_REF: "2b6d21637c715084e7281a1d8259c66a45b742793a5f26594cc56960bd446953",
    FINAL_PREFLIGHT_REF: "70a8005d3646b06a5d205c829362a2556a77d0ba37901545aed3ffca3ef956a8",
    TERMINAL_REF: EMPTY_SHA256,
    CLEANUP_REF: EMPTY_SHA256,
}


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def load(ref: str) -> dict[str, Any]:
    value = json.loads((ROOT / ref).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {ref}")
    return value


def write_json(ref: str, value: object) -> None:
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


def wrap_lines(value: str, width: int) -> list[str]:
    return textwrap.wrap(value, width=width, break_long_words=False, break_on_hyphens=False)


def render_surface(proposal_sha: str, failure_sha: str) -> None:
    from PIL import Image, ImageDraw, ImageFont

    def font(name: str, size: int):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            return ImageFont.load_default()

    image = Image.new("RGB", (1800, 2060), "#f3f0e7")
    draw = ImageDraw.Draw(image)
    title_font = font("arialbd.ttf", 42)
    heading_font = font("arialbd.ttf", 27)
    body_font = font("arial.ttf", 21)
    bold_font = font("arialbd.ttf", 21)
    small_font = font("arial.ttf", 17)
    red = "#a33a32"
    navy = "#18384f"
    green = "#2d6553"
    ink = "#202b31"
    muted = "#53636b"

    draw.rectangle((0, 0, 1800, 150), fill=navy)
    draw.text((80, 42), "M2 diagnostic receipt-persistence recovery-001", font=title_font, fill="white")
    draw.text((82, 103), "LOCAL ZERO-DECISION REVIEW  •  PUBLICATION NOT AUTHORIZED", font=small_font, fill="#d7e6eb")

    y = 195

    def section(title: str, body: list[tuple[str, str]], color: str = navy) -> None:
        nonlocal y
        draw.text((80, y), title, font=heading_font, fill=color)
        y += 48
        for label, text in body:
            lines = wrap_lines(text, 102)
            draw.text((98, y), label, font=bold_font, fill=ink)
            label_width = draw.textbbox((0, 0), label, font=bold_font)[2]
            first_x = 112 + label_width
            if lines:
                draw.text((first_x, y), lines[0], font=body_font, fill=ink)
                y += 32
                for line in lines[1:]:
                    draw.text((112, y), line, font=body_font, fill=ink)
                    y += 32
            else:
                y += 32
            y += 8
        y += 26

    section(
        "Observed terminal boundary",
        [
            ("Process:", "The one authorized read-only diagnostic process is consumed and cannot be retried."),
            ("Failure:", "Terminal timestamp construction raised AttributeError because ArcPy rebound the module-level datetime name."),
            ("Receipts:", "The terminal and cleanup identities were reserved before external reads, but both remain zero-byte; no JSON result survived."),
            ("Meaning:", "Current filesystem and ArcGIS catalog observations are indeterminate and must not be reconstructed."),
        ],
        red,
    )
    section(
        "Evidence preserved without mutation",
        [
            ("Consumed attempt:", CONSUMED_ATTEMPT_ID),
            ("Empty receipt SHA-256:", EMPTY_SHA256),
            ("Failure observation:", failure_sha),
            ("Original runner:", PROTECTED_HASHES[SOURCE_RUNNER_REF]),
        ],
        green,
    )
    section(
        "Proposed future recovery — inactive",
        [
            ("Correction:", "Use function-local datetime imports, pre-reserved receipts, an append-only fallback journal, and cleanup independent of ordinary terminal serialization."),
            ("Scope:", "One distinct future process over the same exact SAFE directory, manifest.safe, and M2-ORB-001 only; no path or source substitution."),
            ("ArcGIS calls:", "GetInstallInfo, ProductInfo, CheckExtension, Usage, Exists, and Describe only. ApplyOrbitCorrection and every geoprocessing call remain forbidden."),
            ("Result limit:", "A pass could describe current path recognition at that time only. It could not establish historical cause, recovery readiness, or science."),
        ],
    )
    section(
        "Current authority",
        [
            ("Allowed now:", "Local zero-decision packet preparation, rendering, and portable validation."),
            ("Not allowed:", "Git commit or push, public CI, owner proposal response, implementation, ArcPy, data access, retry, reconstruction, or processing."),
            ("Next gate:", "Separate authorization to publish this exact packet and require successful public default-branch CI before owner review opens."),
        ],
        red,
    )

    draw.line((80, 1900, 1720, 1900), fill="#a6b2b6", width=2)
    draw.text((80, 1930), f"Proposal SHA-256  {proposal_sha}", font=small_font, fill=muted)
    draw.text((80, 1963), f"Failure observation SHA-256  {failure_sha}", font=small_font, fill=muted)
    draw.text((80, 1996), "Human decision count: 0  •  Response closed until public CI", font=small_font, fill=muted)
    output = ROOT / IMAGE_REF
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="PNG", optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared-at-utc", required=True)
    args = parser.parse_args()
    if not args.prepared_at_utc.endswith("Z"):
        raise SystemExit("--prepared-at-utc must be UTC")

    output_refs = (
        PROPOSAL_REF,
        PREPARATION_APPROVAL_REF,
        FAILURE_OBSERVATION_REF,
        PREFLIGHT_REF,
        DOC_REF,
        IMAGE_REF,
        SURFACE_REF,
        BUNDLE_REF,
        CONTRACT_REF,
        BLANK_REF,
        PREVISUAL_READINESS_REF,
    )
    collisions = [ref for ref in output_refs if (ROOT / ref).exists()]
    if collisions:
        raise SystemExit("packet output collision: " + ", ".join(collisions))

    head = git_value("rev-parse", "HEAD")
    origin = git_value("rev-parse", "origin/main")
    if head != BASE_COMMIT or origin != BASE_COMMIT:
        raise SystemExit("public preparation base differs")
    if {ref: sha256(ref) for ref in PROTECTED_HASHES} != PROTECTED_HASHES:
        raise SystemExit("protected diagnostic evidence differs")
    if (ROOT / TERMINAL_REF).stat().st_size != 0 or (ROOT / CLEANUP_REF).stat().st_size != 0:
        raise SystemExit("reserved receipt bytes changed")

    implementation_gate = load(IMPLEMENTATION_GATE_REF)
    gate_state = load(GATE_STATE_REF)
    final_preflight = load(FINAL_PREFLIGHT_REF)
    milestone = load(MILESTONE_REF)
    profile = load(PROFILE_REF)
    goal = load(GOAL_REF)
    if (
        implementation_gate.get("status") != "pass_public_default_branch_ci_read_only_diagnostic_implementation_ready"
        or gate_state.get("status") != "pass_public_gate_state_final_no_content_preflight_released"
        or final_preflight.get("status") != "pass_final_no_content_preflight_one_read_only_diagnostic_released"
        or milestone.get("handoff", {}).get("current_checkpoint") != CURRENT_CHECKPOINT
        or profile.get("current_checkpoint", {}).get("checkpoint_id") != CURRENT_CHECKPOINT
        or goal.get("current_checkpoint") != CURRENT_CHECKPOINT
    ):
        raise SystemExit("diagnostic gates or canonical checkpoint differ")

    preparation_approval = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-REVIEW-PREPARATION-APPROVAL",
        "recorded_at_utc": args.prepared_at_utc,
        "status": "approved_local_zero_decision_review_preparation_only",
        "authority_basis": {
            "owner_instruction": OWNER_INSTRUCTION,
            "attestation_claimed": True,
            "instruction_context": "preserved terminal receipt-persistence failure of the consumed read-only diagnostic",
        },
        "approved_scope": [
            "prepare one local zero-decision receipt-persistence recovery review packet",
            "render and locally validate that packet",
            "record exact proposal and review-bundle identities for a later publication decision",
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
            "project_data_or_external_custody_access_authorized": False,
            "new_diagnostic_process_authorized": False,
            "retry_or_reconstruction_authorized": False,
            "reserved_receipt_mutation_authorized": False,
            "geoprocessing_authorized": False,
            "radar_processing_authorized": False,
            "baseline_or_change_authorized": False,
            "attribution_authorized": False,
            "scientific_publication_authorized": False,
        },
        "bindings": {
            "base_commit": BASE_COMMIT,
            "implementation_publication_gate_sha256": sha256(IMPLEMENTATION_GATE_REF),
            "gate_state_publication_sha256": sha256(GATE_STATE_REF),
            "final_preflight_sha256": sha256(FINAL_PREFLIGHT_REF),
            "reserved_terminal_sha256": sha256(TERMINAL_REF),
            "reserved_cleanup_sha256": sha256(CLEANUP_REF),
            "reserved_terminal_bytes": 0,
            "reserved_cleanup_bytes": 0,
        },
    }
    write_json(PREPARATION_APPROVAL_REF, preparation_approval)

    failure_observation = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-TERMINAL-RECEIPT-PERSISTENCE-FAILURE-OBSERVATION",
        "recorded_at_utc": args.prepared_at_utc,
        "status": "terminal_process_consumed_reserved_receipts_empty_result_indeterminate",
        "diagnostic_id": CONSUMED_ATTEMPT_ID,
        "process_observation": {
            "runtime": "installed ArcGIS Pro Python environment",
            "process_exit_code": 1,
            "failure_type": "AttributeError",
            "failure_code": "terminal_timestamp_construction_failed",
            "failure_message": "module 'datetime' has no attribute 'now'",
            "traceback_boundary": "run_m2_radar_apply_orbit_correction_input_resolution_diagnostic_001.py execute_diagnostic terminal completed_at_utc construction at line 326",
            "exact_failure_time_persisted": False,
            "reserved_receipt_creation_time_utc": "2026-09-20T00:20:59Z",
        },
        "durable_evidence": {
            "final_preflight_ref": FINAL_PREFLIGHT_REF,
            "final_preflight_sha256": sha256(FINAL_PREFLIGHT_REF),
            "terminal_ref": TERMINAL_REF,
            "terminal_sha256": sha256(TERMINAL_REF),
            "terminal_bytes": 0,
            "cleanup_ref": CLEANUP_REF,
            "cleanup_sha256": sha256(CLEANUP_REF),
            "cleanup_bytes": 0,
            "runner_ref": SOURCE_RUNNER_REF,
            "runner_sha256": sha256(SOURCE_RUNNER_REF),
        },
        "assertions": {
            "diagnostic_process_started": True,
            "diagnostic_process_consumed": True,
            "automatic_retry_performed": False,
            "second_process_started": False,
            "runner_terminal_json_persisted": False,
            "runner_cleanup_json_persisted": False,
            "reserved_receipts_mutated_after_failure": False,
            "arcpy_import_initiated_by_runner": True,
            "arcpy_catalog_observations_persisted": False,
            "project_data_content_read_durably_established": False,
            "external_custody_access_durably_established": False,
            "apply_orbit_correction_invoked": False,
            "geoprocessing_invoked": False,
            "input_resolution_result_reconstructed": False,
            "current_input_resolution_established": False,
            "historical_root_cause_established": False,
            "radar_recovery_readiness_established": False,
            "scientific_result_established": False,
        },
        "limitations": [
            "The empty reserved receipts prove their identities were allocated but preserve no JSON observations.",
            "Whether individual filesystem or ArcGIS recognition checks completed cannot be reconstructed from durable evidence.",
            "The observed timestamp failure does not establish the historical ApplyOrbitCorrection failure cause.",
        ],
    }
    write_json(FAILURE_OBSERVATION_REF, failure_observation)
    failure_sha = sha256(FAILURE_OBSERVATION_REF)

    proposal = {
        "schema_version": "1.0",
        "proposal_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-PROPOSAL",
        "prepared_at_utc": args.prepared_at_utc,
        "status": "proposed_inactive_local_review_prepared_publication_and_owner_approval_required",
        "preparation_base_commit": BASE_COMMIT,
        "preparation_authority": {
            "ref": PREPARATION_APPROVAL_REF,
            "sha256": sha256(PREPARATION_APPROVAL_REF),
            "local_preparation_only": True,
            "public_publication_authorized": False,
            "implementation_authorized": False,
            "new_process_authorized": False,
        },
        "trigger": {
            "failure_observation_ref": FAILURE_OBSERVATION_REF,
            "failure_observation_sha256": failure_sha,
            "consumed_attempt_id": CONSUMED_ATTEMPT_ID,
            "terminal_failure_code": "terminal_timestamp_construction_failed",
            "terminal_failure_type": "AttributeError",
            "terminal_failure_message": "module 'datetime' has no attribute 'now'",
            "runner_terminal_receipt_persisted": False,
            "runner_cleanup_receipt_persisted": False,
            "input_resolution_result_recoverable": False,
        },
        "observed_state": {
            "consumed_attempt_terminal": True,
            "consumed_attempt_retry_or_reuse_authorized": False,
            "terminal_identity_reserved": True,
            "cleanup_identity_reserved": True,
            "terminal_bytes": 0,
            "cleanup_bytes": 0,
            "terminal_sha256": EMPTY_SHA256,
            "cleanup_sha256": EMPTY_SHA256,
            "arcgis_catalog_observations_persisted": False,
            "current_input_resolution_established": False,
            "project_data_content_read_durably_established": False,
            "external_custody_access_durably_established": False,
            "historical_root_cause_established": False,
            "radar_recovery_readiness_established": False,
            "post_observation_bias": "The proposal was designed after observing the receipt-persistence failure and can only address receipt durability in a distinct future process; it cannot recover or validate the lost in-memory observations.",
        },
        "protected_public_implementation": [
            {"path": ref, "sha256": expected, "must_remain_unchanged_during_preparation": True}
            for ref, expected in PROTECTED_HASHES.items()
        ],
        "proposed_exact_changes": [
            "preserve the consumed diagnostic, its public gates, final preflight, original contract, runner, tests, and two zero-byte reserved receipts unchanged",
            "use a distinct recovery attempt and distinct append-only output identities; never reuse, fill, replace, rename, or delete either consumed reserved receipt",
            "replace module-global datetime class reliance only in the proposed recovery implementation with function-local datetime-module imports for every timestamp construction",
            "reserve the new terminal and cleanup identities and initialize one append-only fallback journal before any project-data or external-custody read",
            "append a sanitized original failure before ordinary terminal assembly and append any later persistence failure without replacing the original failure",
            "run cleanup recording from an outer finally path independent of ordinary terminal serialization",
            "preserve the exact approved SAFE-directory, manifest.safe, and M2-ORB-001 identities, check order, sanitization, ArcGIS read-only calls, and zero-geoprocessing rule",
            "add portable synthetic tests for datetime rebinding, terminal-write failure, original-error retention, empty-receipt preservation, one-process enforcement, exact stop behavior, and path or secret sanitization",
            "add one installed ArcGIS-runtime synthetic test using disposable paths only and no project data, external custody, ApplyOrbitCorrection, or geoprocessing",
            "require separate publication authority, successful public default-branch CI, exact attested owner approval, bounded implementation, a second public gate, and one final no-content preflight before any new process",
            "only after every gate, run at most one distinct read-only recovery process over the same exact three candidate forms and stop terminally on any missing input or failure",
        ],
        "future_gate_sequence": [
            "explicit owner authorization to commit and publish this exact zero-decision packet and run public default-branch CI",
            "successful public default-branch CI on the exact packet commit",
            "exact attested owner approval of the public review bundle and proposal",
            "bounded receipt-durability implementation plus portable and ArcGIS-runtime synthetic validation",
            "successful public default-branch CI on the exact implementation commit",
            "publication and public validation of the exact execution-gate state",
            "one final no-content preflight",
            "at most one distinct read-only real recovery process with no retry",
        ],
        "exact_recovery_contract": {
            "attempt_id": PROPOSED_ATTEMPT_ID,
            "distinct_from_consumed_attempt": True,
            "maximum_processes": 1,
            "automatic_retry": False,
            "exact_inputs_unchanged": {
                "attempt_root_source": "the exact external recovery-002 attempt root already frozen by the approved diagnostic contract",
                "candidate_radar_paths": ["copied_SAFE_directory", "copied_SAFE_manifest.safe"],
                "candidate_orbit_path": "exact_M2-ORB-001_EOF",
                "path_reconstruction_or_substitution": False,
            },
            "fixed_check_order_unchanged": True,
            "arcgis_read_only_calls": ["GetInstallInfo", "ProductInfo", "CheckExtension", "Usage", "Exists", "Describe"],
            "maximum_apply_orbit_correction_calls": 0,
            "maximum_geoprocessing_calls": 0,
            "receipt_durability": {
                "new_terminal_identity_reserved_before_external_reads": True,
                "new_cleanup_identity_reserved_before_external_reads": True,
                "fallback_journal_initialized_before_external_reads": True,
                "function_local_datetime_imports": True,
                "original_sanitized_exception_recorded_before_normal_terminal_assembly": True,
                "later_persistence_error_cannot_replace_original_error": True,
                "cleanup_recording_independent_of_terminal_serialization": True,
                "fallback_is_not_success_evidence": True,
                "consumed_empty_receipts_remain_immutable": True,
            },
            "result_semantics": {
                "pass": "current filesystem presence and ArcGIS catalog recognition or nonrecognition for the exact frozen paths at the recovery time only",
                "block": "the distinct recovery process's durable boundary only",
                "historical_root_cause_claim_allowed": False,
                "corrected_apply_orbit_correction_call_claim_allowed": False,
                "radar_recovery_readiness_claim_allowed": False,
                "scientific_claim_allowed": False,
            },
        },
        "current_authority_limits": {
            "git_commits_or_pushes": 0,
            "public_ci_runs": 0,
            "owner_proposal_decisions": 0,
            "implementation_actions": 0,
            "arcpy_invocations": 0,
            "project_data_content_reads": 0,
            "external_custody_reads": 0,
            "new_diagnostic_processes": 0,
            "consumed_attempt_retries_or_reuses": 0,
            "reserved_receipt_mutations": 0,
            "geoprocessing_calls": 0,
            "radar_processing_actions": 0,
            "baseline_or_change_actions": 0,
            "scientific_outputs": 0,
        },
        "stop_rules": [
            "Stop before Git staging, commit, push, public CI, owner proposal response, implementation, ArcPy invocation, project-data or external-custody access, or a new diagnostic process under the present authority.",
            "Stop if either consumed zero-byte receipt, any protected public diagnostic artifact, or any public gate identity differs.",
            "Do not reconstruct the lost filesystem or ArcGIS observations or infer a pass, missing-input result, or historical cause.",
            "Do not reuse, resume, retry, mutate, replace, or fill the consumed diagnostic or either reserved receipt.",
            "Any future recovery implementation, publication, or execution requires the separately gated sequence in this proposal.",
        ],
        "does_not_authorize_now": [
            "Git staging, commit, push, public review publication, or public CI",
            "owner proposal approval, response locking, activation, implementation, ArcPy invocation, final preflight, or a new process",
            "project-data or external-custody access, reconstruction, source or path substitution, or mutation of the consumed receipts",
            "ApplyOrbitCorrection or any geoprocessing, radar processing, baseline, change analysis, interpretation, attribution, derived-pixel publication, or scientific publication",
            "a current input-resolution, historical-root-cause, radar-recovery-readiness, or scientific claim",
        ],
        "decision_domain_after_public_ci": ["approve", "revise", "defer"],
        "attestation_required_after_public_ci": True,
        "human_decision_count": 0,
    }
    write_json(PROPOSAL_REF, proposal)
    proposal_sha = sha256(PROPOSAL_REF)

    preflight = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-REVIEW-PREFLIGHT",
        "checked_at_utc": args.prepared_at_utc,
        "status": "pass_ready_local_zero_decision_packet_preparation_only",
        "bindings": {
            "preparation_approval_ref": PREPARATION_APPROVAL_REF,
            "preparation_approval_sha256": sha256(PREPARATION_APPROVAL_REF),
            "failure_observation_ref": FAILURE_OBSERVATION_REF,
            "failure_observation_sha256": failure_sha,
            "proposal_ref": PROPOSAL_REF,
            "proposal_sha256": proposal_sha,
            "preparation_script_sha256": sha256(PREPARATION_SCRIPT_REF),
            "visual_finalizer_sha256": sha256(VISUAL_FINALIZER_REF),
            "portable_test_sha256": sha256(TEST_REF),
            "base_commit": BASE_COMMIT,
        },
        "checks": {
            "diagnostic_process_consumed": True,
            "reserved_terminal_exactly_zero_bytes": True,
            "reserved_cleanup_exactly_zero_bytes": True,
            "input_resolution_result_unrecoverable": True,
            "protected_public_implementation_exact": True,
            "canonical_checkpoint_intentionally_unchanged": True,
            "local_preparation_authorized": True,
            "publication_or_implementation_authorized": False,
        },
        "assertions": {
            "git_staging_performed": False,
            "git_commit_created": False,
            "git_push_performed": False,
            "public_ci_started": False,
            "protected_diagnostic_code_modified": False,
            "arcpy_invoked": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "new_diagnostic_process_started": False,
            "consumed_attempt_retried_or_reused": False,
            "reserved_receipt_mutated": False,
            "implementation_authorized": False,
            "scientific_result_established": False,
        },
    }
    write_json(PREFLIGHT_REF, preflight)

    document = f"""# M2 ApplyOrbitCorrection input-resolution diagnostic receipt-persistence recovery-001

## Review status

This is a **local zero-decision review packet**. It has not been staged, committed, published, or validated by public CI. The owner proposal response is closed. Human decision count: **0**.

## What happened

The one authorized read-only diagnostic process `{CONSUMED_ATTEMPT_ID}` was started and is consumed. Before external reads, the runner exclusively reserved its terminal and cleanup receipt identities. Both files remain exactly zero bytes with SHA-256 `{EMPTY_SHA256}`.

After the ArcGIS phase was initiated, the process reached ordinary terminal construction and failed at `completed_at_utc = now_utc()`. ArcPy had rebound the runner's module-level `datetime` name, producing `AttributeError: module 'datetime' has no attribute 'now'`. The process exited with code 1.

No terminal JSON, cleanup JSON, filesystem observations, or ArcGIS catalog-recognition observations survived. The current input-resolution result is therefore **indeterminate**. This packet does not reconstruct a missing pass, block, candidate presence result, or catalog-recognition result.

## Preserved evidence

- Failure observation: `{FAILURE_OBSERVATION_REF}`
- Failure observation SHA-256: `{failure_sha}`
- Final preflight SHA-256: `{sha256(FINAL_PREFLIGHT_REF)}`
- Original runner SHA-256: `{sha256(SOURCE_RUNNER_REF)}`
- Reserved terminal and cleanup SHA-256: `{EMPTY_SHA256}` each

The consumed attempt, original public implementation, public gates, final preflight, and both reserved receipts remain unchanged.

## Proposed future correction

The proposed recovery would create a **distinct** attempt `{PROPOSED_ATTEMPT_ID}`. It would change receipt durability only:

1. Use function-local datetime-module imports for every timestamp.
2. Reserve new terminal and cleanup identities and initialize an append-only fallback journal before any external read.
3. Persist a sanitized original exception before normal terminal assembly.
4. Append later persistence errors without replacing the original error.
5. Record cleanup independently from ordinary terminal serialization.
6. Preserve the exact candidate identities, read-only ArcGIS call set, check order, sanitization, and zero-geoprocessing rule.

The proposed future process would inspect only the same exact SAFE directory, `manifest.safe`, and M2-ORB-001 EOF already frozen by the approved diagnostic contract. It would make no path, source, orbit, DEM, AOI, CRS, threshold, registration, route, or scientific-predicate substitution.

## Result limits

A later passing recovery could establish only current filesystem presence and ArcGIS catalog recognition or nonrecognition for those exact paths at that time. It would not establish the historical ApplyOrbitCorrection failure cause, a corrected ApplyOrbitCorrection call, radar recovery readiness, usable radar pixels, baseline admission, change, interpretation, attribution, or a scientific result.

## Current authority and next gate

The current authorization permits only local packet preparation, rendering, and validation. It authorizes no Git staging, commit, push, public CI, owner proposal response, implementation, ArcPy invocation, project-data or external-custody access, new diagnostic process, retry, reconstruction, receipt mutation, geoprocessing, radar processing, or scientific action.

The next gate is a separate owner authorization to publish this exact zero-decision packet and run public default-branch CI. Only after that public gate may the owner review the proposal as `approve`, `revise`, or `defer` with an attestation.
"""
    write_text(DOC_REF, document)
    render_surface(proposal_sha, failure_sha)

    surface = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-REVIEW-SURFACE",
        "rendered_at_utc": args.prepared_at_utc,
        "status": "pass_static_review_surface_generated_pending_agent_visual_inspection",
        "artifact_ref": IMAGE_REF,
        "artifact_sha256": sha256(IMAGE_REF),
        "width_px": 1800,
        "height_px": 2060,
        "bindings": {
            "proposal_sha256": proposal_sha,
            "failure_observation_sha256": failure_sha,
        },
        "assertions": {
            "human_decision_count": 0,
            "attestation": False,
            "publication_authorized": False,
            "implementation_authorized": False,
            "arcpy_invoked": False,
            "new_process_authorized": False,
        },
    }
    write_json(SURFACE_REF, surface)

    bundle = {
        "schema_version": "1.0",
        "bundle_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-REVIEW-BUNDLE",
        "prepared_at_utc": args.prepared_at_utc,
        "status": "locally_prepared_zero_decisions_publication_authority_required",
        "human_decision_count": 0,
        "artifacts": [
            {"path": PROPOSAL_REF, "sha256": proposal_sha, "purpose": "normative receipt-persistence recovery proposal", "render_receipts": [{"path": SURFACE_REF, "sha256": sha256(SURFACE_REF)}]},
            {"path": FAILURE_OBSERVATION_REF, "sha256": failure_sha, "purpose": "preserved terminal receipt-persistence failure observation", "render_receipts": []},
            {"path": PREFLIGHT_REF, "sha256": sha256(PREFLIGHT_REF), "purpose": "terminal-state and preparation-authority preflight", "render_receipts": []},
            {"path": DOC_REF, "sha256": sha256(DOC_REF), "purpose": "human-readable local review", "render_receipts": [{"path": SURFACE_REF, "sha256": sha256(SURFACE_REF)}]},
            {"path": IMAGE_REF, "sha256": sha256(IMAGE_REF), "purpose": "rendered local review surface", "render_receipts": [{"path": SURFACE_REF, "sha256": sha256(SURFACE_REF)}]},
        ],
        "decision_items": [
            {
                "item_id": "M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001",
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
        "response_schema_version": "nepal-m2-radar-apply-orbit-correction-input-resolution-diagnostic-receipt-persistence-recovery-001-response-v1",
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
            "candidate_identity": f"M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-PROPOSAL-SHA256:{proposal_sha}",
            "rendered_surface_generated": True,
            "public_ci_verified": False,
        },
        "allowed_decisions_after_public_ci": ["approve", "revise", "defer"],
        "required_attestation": True,
        "items": [
            {
                "item_id": "M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001",
                "evidence_sha256": bundle_sha,
            }
        ],
        "authority_boundary": {
            "packet_creates_authority": False,
            "git_staging_authorized": False,
            "git_commit_or_push_authorized": False,
            "public_ci_authorized": False,
            "implementation_authorized": False,
            "arcpy_invocation_authorized": False,
            "project_data_or_external_custody_access_authorized": False,
            "new_diagnostic_process_authorized": False,
            "retry_or_reconstruction_authorized": False,
            "reserved_receipt_mutation_authorized": False,
            "geoprocessing_authorized": False,
            "radar_processing_authorized": False,
            "baseline_or_change_authorized": False,
            "attribution_authorized": False,
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
                "item_id": "M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001",
                "evidence_sha256": bundle_sha,
                "decision": None,
                "notes": "",
            }
        ],
        "human_decision_count": 0,
        "response_not_open_until_public_ci": True,
    }
    write_json(BLANK_REF, blank)

    previsual = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-REVIEW-READINESS-PREVISUAL",
        "verified_at_utc": args.prepared_at_utc,
        "status": "pass_local_zero_decision_packet_structurally_ready_visual_inspection_pending",
        "bindings": {
            "preparation_approval_ref": PREPARATION_APPROVAL_REF,
            "preparation_approval_sha256": sha256(PREPARATION_APPROVAL_REF),
            "failure_observation_ref": FAILURE_OBSERVATION_REF,
            "failure_observation_sha256": failure_sha,
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
        },
        "validation": {
            "consumed_attempt_preserved": True,
            "reserved_receipts_preserved_zero_byte": True,
            "protected_public_implementation_preserved": True,
            "post_observation_limit_disclosed": True,
            "human_decision_count": 0,
            "blank_response_verified": True,
            "rendered_surface_generated": True,
            "rendered_surface_visually_inspected": False,
            "canonical_checkpoint_intentionally_unchanged": True,
        },
        "released_now": {
            "local_packet_preparation": True,
            "local_packet_validation": True,
            "git_staging_commit_or_push": False,
            "public_ci": False,
            "owner_proposal_review": False,
            "implementation": False,
            "arcpy_invocation": False,
            "project_data_or_external_custody_access": False,
            "new_diagnostic_process": False,
            "retry_or_reconstruction": False,
            "reserved_receipt_mutation": False,
            "geoprocessing": False,
            "radar_processing": False,
            "baseline_or_change_analysis": False,
            "attribution": False,
            "scientific_publication": False,
        },
        "next_action": "Visually inspect the generated review surface, then seal local readiness. Stop before Git staging or publication.",
    }
    write_json(PREVISUAL_READINESS_REF, previsual)

    print(
        json.dumps(
            {
                "status": previsual["status"],
                "proposal_sha256": proposal_sha,
                "review_bundle_sha256": bundle_sha,
                "failure_observation_sha256": failure_sha,
                "review_surface": IMAGE_REF,
                "canonical_checkpoint": CURRENT_CHECKPOINT,
                "next_gate": "visual inspection then explicit publication authorization",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
