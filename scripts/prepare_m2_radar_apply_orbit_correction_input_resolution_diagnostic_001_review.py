#!/usr/bin/env python3
"""Prepare the local zero-decision ApplyOrbitCorrection input-resolution review packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-apply-orbit-correction-input-resolution-diagnostic-001"
PREPARATION_APPROVAL_REF = f"records/source-gates/{PREFIX}-review-preparation-approval.json"
PROPOSAL_REF = "contracts/milestone-002-radar-apply-orbit-correction-input-resolution-diagnostic-001-proposal.json"
PREFLIGHT_REF = f"records/readiness/{PREFIX}-review-preflight.json"
DOC_REF = "docs/M2_RADAR_APPLY_ORBIT_CORRECTION_INPUT_RESOLUTION_DIAGNOSTIC_001_REVIEW.md"
BUNDLE_REF = f"reviews/{PREFIX}/review-bundle.json"
CONTRACT_REF = f"reviews/{PREFIX}/review-contract.json"
BLANK_REF = f"reviews/{PREFIX}/blank-response.json"
READINESS_REF = f"records/readiness/{PREFIX}-review-readiness.json"

CURRENT_CHECKPOINT = "M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-002-TERMINAL-REVIEW"
BASE_COMMIT = "9570dcad5b84673fb503955e255845b21f69c46f"
ATTEMPT_ID = "radar-pixel-orbit-application-recovery-002-real-001"
SOURCE_ID = "M1-SRC-001"
ORBIT_ID = "M2-ORB-001"

SOURCE_STARTED_REF = "records/processing/radar-pixel-orbit-application-001/m1-src-001-real-001-started.json"
SOURCE_TERMINAL_REF = "records/processing/radar-pixel-orbit-application-001/m1-src-001-real-001-terminal.json"
TERMINAL_RECONCILIATION_REF = "records/processing/m2-radar-pixel-orbit-application-recovery-002-terminal-reconciliation.json"
OUTCOME_RECONCILIATION_REF = "records/processing/m2-radar-pixel-orbit-application-recovery-002-outcome-reconciliation.json"
FINAL_PREFLIGHT_REF = "records/readiness/m2-radar-pixel-orbit-application-recovery-002-final-preflight.json"
GATE_STATE_REF = "records/readiness/m2-radar-pixel-orbit-application-recovery-002-gate-state-publication.json"
RECOVERY_CONTRACT_REF = "config/qa/m2-radar-pixel-orbit-application-recovery-002-contract.json"
BASE_CONTRACT_REF = "config/qa/m2-radar-pixel-orbit-application-001-contract.json"
BASE_RUNNER_REF = "scripts/run_m2_radar_pixel_orbit_application_001.py"
BASE_CORE_REF = "scripts/m2_radar_pixel_orbit_application_001_core.py"

PROTECTED_HASHES = {
    SOURCE_STARTED_REF: "764c297d3e745e54769d07f4c048c706919cbc1cd282d3ff26000f92b036cb1e",
    SOURCE_TERMINAL_REF: "d1a16548fd0ec13df3802f6a7cf62f4a884f93a6efc8d0be630c3be2b9ac786d",
    TERMINAL_RECONCILIATION_REF: "32babf925933b46c88870d5648bb39fd32596bc1b86d1f5fe01c52de84cffdfb",
    OUTCOME_RECONCILIATION_REF: "371030851c44810ff2d5d06390c27c76af5b47ee1d8865b8e310025317331339",
    FINAL_PREFLIGHT_REF: "42e41c84ae9c2a826f185bfaa251a47ffad1f46679b97b6048275e6231a39f01",
    GATE_STATE_REF: "057d3e09b006e3ad3ddd54b48cb599dba598dd277a26303a0b3335c242b76d3b",
    RECOVERY_CONTRACT_REF: "6482f01722f39455d6150df79186385de532cb22f33d079c651711129eb35c6e",
    BASE_CONTRACT_REF: "a25f86588979fd4b5cfb45c999a862d83d71be31925a5b39565970de526f8fb1",
    BASE_RUNNER_REF: "0b65fbecbeab373d8bbbf2cbbc28f8817e3c3bb08584dbf1a9720dcbb19ceb06",
    BASE_CORE_REF: "fd192878acf33e2c73eeeba1ec42865eac48dfc5742b3ae4cf54b51de42755ba",
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
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def artifact(ref: str, role: str) -> dict[str, Any]:
    return {"path": ref, "sha256": sha256(ref), "role": role}


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
        BUNDLE_REF,
        CONTRACT_REF,
        BLANK_REF,
        READINESS_REF,
    ]
    collisions = [ref for ref in outputs if (ROOT / ref).exists()]
    if collisions:
        raise SystemExit("review output collision: " + ", ".join(collisions))

    if git_value("rev-parse", "HEAD") != BASE_COMMIT or git_value("rev-parse", "origin/main") != BASE_COMMIT:
        raise SystemExit("preparation base is not the exact public terminal checkpoint")
    preexisting = set(
        subprocess.run(
            ["git", "status", "--porcelain=v1"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    )
    allowed_preexisting = {
        " M docs/ROADMAP.md",
        "?? docs/GEOSPATIAL_HELPER_REUSE.md",
        "?? scripts/prepare_m2_radar_apply_orbit_correction_input_resolution_diagnostic_001_review.py",
        "?? tests/test_m2_radar_apply_orbit_correction_input_resolution_diagnostic_001_review.py",
    }
    if preexisting != allowed_preexisting:
        raise SystemExit("unexpected preexisting worktree changes")
    if {ref: sha256(ref) for ref in PROTECTED_HASHES} != PROTECTED_HASHES:
        raise SystemExit("protected terminal or implementation evidence changed")

    source_started = load(SOURCE_STARTED_REF)
    source_terminal = load(SOURCE_TERMINAL_REF)
    terminal = load(TERMINAL_RECONCILIATION_REF)
    outcome = load(OUTCOME_RECONCILIATION_REF)
    milestone = load("contracts/milestone-002.json")
    profile = load("records/project-control-profile.json")
    goal = load("records/long-term-goal.json")
    if (
        source_started.get("status") != "started_single_attempt_reserved_before_source_content_copy"
        or source_started.get("source_id") != SOURCE_ID
        or source_started.get("orbit_source_id") != ORBIT_ID
        or source_terminal.get("status") != "failed_source_execution_no_retry"
        or source_terminal.get("failure_type") != "ExecuteError"
        or source_terminal.get("failure_code") != "unexpected_processing_failure"
        or "ApplyOrbitCorrection" not in source_terminal.get("failure_message", "")
        or "The system cannot locate the object specified" not in source_terminal.get("failure_message", "")
        or terminal.get("status") != "block_recovery_002_attempt_no_retry"
        or terminal.get("assertions", {}).get("attempt_consumed") is not True
        or outcome.get("execution_result", {}).get("source_ids_attempted") != [SOURCE_ID]
        or outcome.get("execution_result", {}).get("route_ids_attempted") != []
        or milestone.get("handoff", {}).get("current_checkpoint") != CURRENT_CHECKPOINT
        or profile.get("current_checkpoint", {}).get("checkpoint_id") != CURRENT_CHECKPOINT
        or goal.get("current_checkpoint") != CURRENT_CHECKPOINT
    ):
        raise SystemExit("terminal evidence or canonical checkpoint differs")

    preparation_approval = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-REVIEW-PREPARATION-APPROVAL",
        "recorded_at_utc": args.prepared_at_utc,
        "status": "approved_local_zero_decision_review_preparation_only",
        "authority_basis": {
            "assistant_question": "Would you like to authorize preparation of a zero-decision review packet for the ApplyOrbitCorrection object-resolution failure?",
            "owner_response": "yes",
            "explicit_affirmation": True,
            "interpreted_scope": "local zero-decision proposal and review preparation and validation only",
        },
        "approved_scope": [
            "prepare one local zero-decision input-resolution diagnostic proposal and review packet",
            "validate the packet against the exact public terminal evidence and current control state",
            "record exact proposal and review-bundle identities for a later publication decision",
        ],
        "authority_boundary": {
            "local_review_packet_preparation_authorized": True,
            "local_validation_authorized": True,
            "git_commit_authorized": False,
            "git_push_authorized": False,
            "public_ci_authorized": False,
            "owner_proposal_decision_recording_authorized": False,
            "diagnostic_implementation_authorized": False,
            "arcpy_invocation_authorized": False,
            "project_data_or_external_custody_access_authorized": False,
            "new_real_attempt_authorized": False,
            "radar_processing_authorized": False,
            "baseline_or_change_analysis_authorized": False,
            "scientific_publication_authorized": False,
        },
        "bindings": {"base_commit": BASE_COMMIT, **{ref: digest for ref, digest in PROTECTED_HASHES.items()}},
    }
    write_json(PREPARATION_APPROVAL_REF, preparation_approval)

    protected = [
        {"path": ref, "sha256": digest, "must_remain_unchanged_during_preparation": True}
        for ref, digest in PROTECTED_HASHES.items()
    ]
    proposal = {
        "schema_version": "1.0",
        "proposal_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001",
        "prepared_at_utc": args.prepared_at_utc,
        "status": "proposed_zero_decision_not_authorized_for_implementation",
        "human_decision_count": 0,
        "preparation_authority": {
            "ref": PREPARATION_APPROVAL_REF,
            "sha256": sha256(PREPARATION_APPROVAL_REF),
            "local_preparation_authorized": True,
            "git_publication_authorized": False,
            "public_ci_authorized": False,
            "implementation_authorized": False,
        },
        "trigger": {
            "terminal_reconciliation_ref": TERMINAL_RECONCILIATION_REF,
            "terminal_reconciliation_sha256": PROTECTED_HASHES[TERMINAL_RECONCILIATION_REF],
            "outcome_reconciliation_ref": OUTCOME_RECONCILIATION_REF,
            "outcome_reconciliation_sha256": PROTECTED_HASHES[OUTCOME_RECONCILIATION_REF],
            "source_terminal_ref": SOURCE_TERMINAL_REF,
            "source_terminal_sha256": PROTECTED_HASHES[SOURCE_TERMINAL_REF],
        },
        "observed_state": {
            "attempt_id": ATTEMPT_ID,
            "attempt_terminal_and_consumed": True,
            "automatic_retry_performed": False,
            "setup_stages_completed": [
                "identity_scan",
                "arcpy_import",
                "ArcInfo_product_check",
                "ImageAnalyst_checkout",
                "Spatial_checkout",
                "DEM_mosaic",
                "analysis_support",
            ],
            "source_id_started": SOURCE_ID,
            "orbit_source_id_bound": ORBIT_ID,
            "later_sources_started": False,
            "route_evaluations_started": False,
            "failing_tool": "ApplyOrbitCorrection",
            "failure_type": "ExecuteError",
            "failure_code": "unexpected_processing_failure",
            "failure_message": source_terminal["failure_message"],
            "static_call_shape": "arcpy.ia.ApplyOrbitCorrection(str(copied_safe / 'manifest.safe'), str(exact_orbit_custody_path))",
            "python_filesystem_manifest_presence_checked_before_call": True,
            "python_filesystem_orbit_presence_verified_by_frozen_input_controls": True,
            "arcgis_catalog_recognition_of_safe_directory_observed": False,
            "arcgis_catalog_recognition_of_manifest_safe_observed": False,
            "arcgis_catalog_recognition_of_orbit_eof_observed": False,
            "attempt_root_current_presence_observed": False,
            "exact_unresolved_object_identified": False,
            "historical_root_cause_established": False,
            "radar_recovery_readiness_established": False,
            "post_observation_bias": "The proposed questions were selected after observing the ApplyOrbitCorrection failure and therefore may diagnose only the preserved failure boundary; they cannot retrospectively prove an unrecorded cause.",
        },
        "protected_public_evidence": protected,
        "proposed_diagnostic_contract": {
            "diagnostic_id": "radar-apply-orbit-correction-input-resolution-diagnostic-001-real-001",
            "mode": "read_only_single_process_no_geoprocessing",
            "exact_inputs": {
                "terminal_attempt_id": ATTEMPT_ID,
                "source_id": SOURCE_ID,
                "orbit_source_id": ORBIT_ID,
                "attempt_root_path_source": "exact external attempt root frozen by the approved recovery-002 contract",
                "attempt_root_current_presence": "not observed under preparation-only authority; diagnostic must establish it before content inspection",
                "candidate_radar_paths": ["copied_SAFE_directory", "copied_SAFE_manifest.safe"],
                "candidate_orbit_path": "exact_M2-ORB-001_EOF",
            },
            "fixed_check_order": [
                "reserve_terminal_receipt_before_content_access",
                "verify_exact protected public evidence",
                "verify existence and filesystem identity of the exact append-only attempt-root SAFE candidate, manifest.safe candidate, and exact orbit EOF",
                "import ArcPy and record install, product, extension, and ApplyOrbitCorrection usage identity",
                "evaluate arcpy.Exists for copied SAFE directory",
                "evaluate arcpy.Exists for copied manifest.safe",
                "evaluate arcpy.Exists for exact orbit EOF",
                "for each ArcGIS-recognized object only, record sanitized Describe dataType, datasetType, catalogPath class, and children count",
                "persist terminal and cleanup receipts",
            ],
            "maximum_real_diagnostic_processes": 1,
            "maximum_apply_orbit_correction_calls": 0,
            "maximum_geoprocessing_tool_calls": 0,
            "automatic_retry": False,
            "network_requests": 0,
            "credential_actions": 0,
            "source_orbit_or_dem_copies": 0,
            "source_orbit_or_dem_mutations": 0,
            "derived_raster_outputs": 0,
            "baseline_or_change_actions": 0,
            "scientific_outputs": 0,
            "implementation_gates": [
                "exact owner approval of the public review packet",
                "bounded implementation with synthetic no-content tests",
                "successful public default-branch CI",
                "one final no-content preflight",
            ],
            "result_semantics": {
                "pass_may_establish": "current filesystem presence plus ArcGIS catalog recognition or nonrecognition of the exact frozen input path forms in one diagnostic process",
                "missing_attempt_root_or_candidate_semantics": "terminal block without reconstruction, substitution, copy, or processing",
                "pass_does_not_establish": [
                    "historical root cause",
                    "corrected ApplyOrbitCorrection call",
                    "radar recovery readiness",
                    "authorization for a correction or retry",
                    "usable radar pixels",
                    "baseline admission",
                    "change analysis",
                    "interpretation or attribution",
                    "scientific result",
                ],
            },
        },
        "stop_rules": [
            "Stop before Git commit, push, public CI, implementation, ArcPy invocation, or project/external-custody access under the present preparation-only authority.",
            "Do not call ApplyOrbitCorrection or any other geoprocessing tool in the proposed diagnostic.",
            "Do not alter the input path, source, orbit, DEM, AOI, CRS, grid, mask, threshold, registration, or scientific contracts.",
            "Do not reuse, resume, retry, mutate, or reconstruct the consumed recovery-002 attempt.",
            "Any correction, path substitution, or new processing attempt requires a separate post-diagnostic review and exact owner decision.",
        ],
        "does_not_authorize_now": [
            "Git publication or public CI",
            "owner approval of this proposal",
            "diagnostic implementation or ArcPy invocation",
            "project-data or external-custody access",
            "ApplyOrbitCorrection or any geoprocessing call",
            "new radar attempt, source substitution, or path correction",
            "baseline, change analysis, attribution, derived-pixel publication, or scientific publication",
        ],
    }
    write_json(PROPOSAL_REF, proposal)

    preflight = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-REVIEW-PREFLIGHT",
        "checked_at_utc": args.prepared_at_utc,
        "status": "pass_ready_local_zero_decision_packet_preparation_only",
        "bindings": {
            "preparation_approval_sha256": sha256(PREPARATION_APPROVAL_REF),
            "proposal_sha256": sha256(PROPOSAL_REF),
            "preparation_script_sha256": sha256("scripts/prepare_m2_radar_apply_orbit_correction_input_resolution_diagnostic_001_review.py"),
            "base_commit": BASE_COMMIT,
        },
        "checks": {
            "exact_public_terminal_commit": True,
            "terminal_attempt_consumed": True,
            "first_failure_is_apply_orbit_correction": True,
            "later_source_or_route_absent": True,
            "protected_public_evidence_exact": True,
            "canonical_checkpoint_unchanged": True,
            "proposal_human_decision_count": 0,
            "publication_or_implementation_authorized": False,
        },
        "assertions": {
            "git_commit_created": False,
            "git_push_performed": False,
            "public_ci_started": False,
            "arcpy_invoked": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "apply_orbit_correction_invoked": False,
            "new_attempt_created": False,
            "radar_processing_executed": False,
            "historical_root_cause_established": False,
            "scientific_result_established": False,
        },
    }
    write_json(PREFLIGHT_REF, preflight)

    proposal_sha = sha256(PROPOSAL_REF)
    document = f"""# M2 ApplyOrbitCorrection input-resolution diagnostic-001 review

## Review status

This is a local zero-decision review packet. Proposal SHA-256: `{proposal_sha}`. It is not published, approved, or authorized for implementation.

## Exact observed boundary

Recovery-002 attempt `{ATTEMPT_ID}` is terminal and consumed. Identity scanning, ArcPy import, the `ArcInfo` product check, both extension checkouts, DEM mosaic creation, and analysis-support creation completed. The first fixed-order source, `{SOURCE_ID}`, then failed inside `ApplyOrbitCorrection` while bound to `{ORBIT_ID}`. ArcGIS returned `ERROR 999999`, including “The system cannot locate the object specified.” No later source or route started, no retry occurred, cleanup completed, and external custody remained unchanged.

The frozen runner called `arcpy.ia.ApplyOrbitCorrection` with the copied SAFE's `manifest.safe` path and the exact orbit EOF path. Python-level controls established filesystem presence and identity, but the terminal evidence did not record whether ArcGIS catalog resolution recognized the SAFE directory, `manifest.safe`, the orbit EOF, or which object the error referred to. Historical root cause and recovery readiness remain unestablished.

## Proposed bounded diagnostic

After separate publication, owner approval, implementation, public CI, and final preflight gates, run at most one read-only diagnostic process. It would first establish whether the exact append-only recovery-002 attempt-root candidates for `{SOURCE_ID}` currently exist, then inspect only any exact candidate found there and exact `{ORBIT_ID}`. The packet does not claim those external candidates still exist because current project-data access is unauthorized. It would record:

1. Current existence and exact filesystem identities for the attempt-root SAFE candidate, its `manifest.safe` candidate, and the orbit EOF.
2. ArcGIS installation, product, extensions, and `ApplyOrbitCorrection` usage identity.
3. `arcpy.Exists` for the SAFE directory, `manifest.safe`, and orbit EOF.
4. Sanitized `arcpy.Describe` fields only for objects ArcGIS recognizes.

The diagnostic would make zero `ApplyOrbitCorrection` calls, zero geoprocessing calls, zero copies, zero custody mutations, and zero derived rasters. A missing attempt root or candidate would terminate the diagnostic without reconstruction or substitution. A result could describe current filesystem presence and ArcGIS object recognition only. Any path correction or new processing attempt would require another exact review and owner decision.

## Still prohibited

Git publication, public CI, owner approval, implementation, ArcPy invocation, project-data or external-custody access, a diagnostic process, any `ApplyOrbitCorrection` call, any new radar attempt, source or path substitution, baseline admission, change analysis, interpretation, attribution, derived-pixel publication, and scientific publication remain unauthorized.
"""
    write_text(DOC_REF, document)

    bundle = {
        "schema_version": "1.0",
        "bundle_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-REVIEW-BUNDLE",
        "prepared_at_utc": args.prepared_at_utc,
        "status": "ready_local_zero_decision_publication_not_authorized",
        "human_decision_count": 0,
        "artifacts": [
            artifact(PREPARATION_APPROVAL_REF, "preparation_authority"),
            artifact(PROPOSAL_REF, "proposal"),
            artifact(PREFLIGHT_REF, "preparation_preflight"),
            artifact(DOC_REF, "human_readable_review"),
            artifact(SOURCE_TERMINAL_REF, "exact_source_failure"),
            artifact(TERMINAL_RECONCILIATION_REF, "terminal_reconciliation"),
            artifact(OUTCOME_RECONCILIATION_REF, "outcome_reconciliation"),
        ],
        "decision_requested_after_publication": {
            "decision_id": "D-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001",
            "question": "Approve, revise, or defer the bounded one-process read-only input-resolution diagnostic?",
            "choices": ["approve", "revise", "defer"],
            "response_open": False,
        },
        "authority_boundary": {
            "publication_authorized": False,
            "owner_review_open": False,
            "implementation_authorized": False,
            "arcpy_invocation_authorized": False,
            "project_data_access_authorized": False,
            "new_attempt_authorized": False,
        },
    }
    write_json(BUNDLE_REF, bundle)

    contract = {
        "schema_version": "1.0",
        "contract_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-REVIEW-CONTRACT",
        "prepared_at_utc": args.prepared_at_utc,
        "review_bundle": {"ref": BUNDLE_REF, "manifest_sha256": sha256(BUNDLE_REF)},
        "proposal": {"ref": PROPOSAL_REF, "sha256": proposal_sha},
        "workflow_authority": {
            "local_preparation_complete": True,
            "public_review_publication_authorized": False,
            "review_response_open": False,
        },
        "authority_boundary": {
            "owner_proposal_decision_authorized": False,
            "diagnostic_implementation_authorized": False,
            "arcpy_invocation_authorized": False,
            "project_data_or_external_custody_access_authorized": False,
            "apply_orbit_correction_authorized": False,
            "new_radar_attempt_authorized": False,
            "baseline_or_change_analysis_authorized": False,
            "scientific_publication_authorized": False,
        },
        "response_requirements": {
            "exact_proposal_sha256_required": proposal_sha,
            "exact_review_bundle_sha256_required": sha256(BUNDLE_REF),
            "explicit_decision_required": True,
            "attestation_required": True,
        },
    }
    write_json(CONTRACT_REF, contract)

    blank = {
        "schema_version": "1.0",
        "response_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-BLANK-RESPONSE",
        "completed": False,
        "reviewer": {"name": None, "reviewed_at_utc": None, "attestation": False},
        "responses": [{"decision_id": bundle["decision_requested_after_publication"]["decision_id"], "decision": None, "comment": None}],
        "human_decision_count": 0,
        "response_not_open_until_public_ci": True,
        "bindings": {"proposal_sha256": proposal_sha, "review_bundle_sha256": sha256(BUNDLE_REF)},
    }
    write_json(BLANK_REF, blank)

    readiness = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-REVIEW-READINESS",
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
            "review_bundle_ref": BUNDLE_REF,
            "review_bundle_sha256": sha256(BUNDLE_REF),
            "review_contract_ref": CONTRACT_REF,
            "review_contract_sha256": sha256(CONTRACT_REF),
            "blank_response_ref": BLANK_REF,
            "blank_response_sha256": sha256(BLANK_REF),
            "terminal_reconciliation_sha256": PROTECTED_HASHES[TERMINAL_RECONCILIATION_REF],
            "outcome_reconciliation_sha256": PROTECTED_HASHES[OUTCOME_RECONCILIATION_REF],
        },
        "validation": {
            "terminal_attempt_record_preserved": True,
            "external_attempt_root_current_presence_not_claimed": True,
            "protected_public_evidence_preserved": True,
            "post_observation_limit_disclosed": True,
            "human_decision_count": 0,
            "blank_response_verified": True,
            "canonical_checkpoint_intentionally_unchanged": True,
            "maximum_proposed_apply_orbit_correction_calls": 0,
            "maximum_proposed_geoprocessing_calls": 0,
        },
        "released_now": {
            "local_packet_preparation": True,
            "local_packet_validation": True,
            "git_commit_or_push": False,
            "public_ci": False,
            "owner_proposal_review": False,
            "diagnostic_implementation": False,
            "arcpy_invocation": False,
            "project_data_or_external_custody_access": False,
            "apply_orbit_correction": False,
            "new_radar_attempt": False,
            "baseline_or_change_analysis": False,
            "scientific_publication": False,
        },
        "assertions": preflight["assertions"],
        "next_action": "Obtain explicit owner authorization to commit and publish this exact zero-decision packet and run public default-branch CI; do not open the owner proposal response before that gate passes.",
    }
    write_json(READINESS_REF, readiness)

    print(json.dumps({
        "status": readiness["status"],
        "proposal_sha256": proposal_sha,
        "review_bundle_sha256": sha256(BUNDLE_REF),
        "review_readiness_sha256": sha256(READINESS_REF),
        "current_checkpoint": CURRENT_CHECKPOINT,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
