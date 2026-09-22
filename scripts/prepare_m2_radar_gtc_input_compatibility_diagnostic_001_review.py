#!/usr/bin/env python3
"""Prepare the local zero-decision GTC input-compatibility diagnostic packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-gtc-input-compatibility-diagnostic-001"
PREPARATION_REF = f"records/source-gates/{PREFIX}-review-preparation-authority.json"
PROPOSAL_REF = "contracts/milestone-002-radar-gtc-input-compatibility-diagnostic-001-proposal.json"
PREFLIGHT_REF = f"records/readiness/{PREFIX}-review-preflight.json"
DOC_REF = "docs/M2_RADAR_GTC_INPUT_COMPATIBILITY_DIAGNOSTIC_001_REVIEW.md"
BUNDLE_REF = f"reviews/{PREFIX}/review-bundle.json"
CONTRACT_REF = f"reviews/{PREFIX}/review-contract.json"
BLANK_REF = f"reviews/{PREFIX}/blank-response.json"
READINESS_REF = f"records/readiness/{PREFIX}-review-readiness.json"

BASE_COMMIT = "a9e94dc02f4024f88399daab9620faa81f198e08"
CURRENT_CHECKPOINT = "M2-RADAR-ESRI-SEQUENCE-RECOVERY-005-TERMINAL-REVIEW"
ATTEMPT_ID = "radar-pixel-orbit-application-esri-sequence-recovery-005-real-001"
DIAGNOSTIC_ID = "radar-gtc-input-compatibility-diagnostic-001-real-001"
ATTEMPT_ROOT = r"C:\Projects\Active\nepal-2026-before-after-map-data\r5\a1"
DIAGNOSTIC_ROOT = r"C:\Projects\Active\nepal-2026-before-after-map-data\r5\d1"

TERMINAL_REF = "records/processing/m2-radar-esri-sequence-recovery-005-terminal-reconciliation.json"
OUTCOME_REF = "records/processing/m2-radar-esri-sequence-recovery-005-outcome-reconciliation.json"
FINAL_PREFLIGHT_REF = "records/readiness/m2-radar-esri-sequence-recovery-005-final-preflight.json"
TERMINAL_GATE_REF = "records/readiness/m2-radar-esri-sequence-recovery-005-terminal-publication-gate.json"
TERMINAL_PUBLICATION_REF = "records/readiness/m2-radar-esri-sequence-recovery-005-terminal-publication-reconciliation.json"
RECOVERY_CONTRACT_REF = "config/qa/m2-radar-esri-sequence-recovery-005-contract.json"
RECOVERY_RUNNER_REF = "scripts/m2_radar_esri_sequence_processing_005.py"
AGENTS_REF = "AGENTS.md"

PROTECTED_HASHES = {
    TERMINAL_REF: "9c2b7588584616bbf66cab857ea755052304d033c992d6643e24581228c41521",
    OUTCOME_REF: "dc7412b95b6174182eaab2ca6274b981d5f98c6ea1df40a3ff34f74e91e5fb00",
    FINAL_PREFLIGHT_REF: "9c732541fefb2229635074b30b950b1e8449925e508f99cc2ee4cc09478f1ba0",
    TERMINAL_GATE_REF: "2dc779265cbdf8aa38bbf6da9b24ab146bc468a47ed39be515ba3e74d3b1a618",
    TERMINAL_PUBLICATION_REF: "a9e778403184b151e47566963529c020fae23be5572dc1e54165c730bf6e40ab",
    RECOVERY_CONTRACT_REF: "e388f84dd97db781e89d9115e03a7cda92895e1dfb9c4adf9a35e1ce494e1b0b",
    RECOVERY_RUNNER_REF: "faadf83f4ae1c35209ed104ab3ba2c97ad233615655aaa31dfc72851b968e0fd",
    AGENTS_REF: "a4630c53af4fcfff730b6a006923698f177f8939f78cf62e2a602770574682ba",
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

    outputs = [PREPARATION_REF, PROPOSAL_REF, PREFLIGHT_REF, DOC_REF, BUNDLE_REF, CONTRACT_REF, BLANK_REF, READINESS_REF]
    collisions = [ref for ref in outputs if (ROOT / ref).exists()]
    if collisions:
        raise SystemExit("review output collision: " + ", ".join(collisions))
    if git_value("rev-parse", "HEAD") != BASE_COMMIT or git_value("rev-parse", "origin/main") != BASE_COMMIT:
        raise SystemExit("preparation base is not the exact public terminal checkpoint")
    if {ref: sha256(ref) for ref in PROTECTED_HASHES} != PROTECTED_HASHES:
        raise SystemExit("protected terminal evidence or frozen implementation changed")

    terminal = load(TERMINAL_REF)
    outcome = load(OUTCOME_REF)
    milestone = load("contracts/milestone-002.json")
    profile = load("records/project-control-profile.json")
    goal = load("records/long-term-goal.json")
    if (
        terminal.get("attempt_id") != ATTEMPT_ID
        or terminal.get("attempt_consumed") is not True
        or terminal.get("execution_result", {}).get("stopped_tool") != "ApplyGeometricTerrainCorrection_gamma"
        or terminal.get("call_boundary_observation", {}).get("approved_refined_lee_output_created") is not True
        or terminal.get("call_boundary_observation", {}).get("gamma_geometric_terrain_correction_output_created") is not False
        or outcome.get("disposition") != "block"
        or milestone.get("handoff", {}).get("current_checkpoint") != CURRENT_CHECKPOINT
        or profile.get("current_checkpoint", {}).get("checkpoint_id") != CURRENT_CHECKPOINT
        or goal.get("current_checkpoint") != CURRENT_CHECKPOINT
    ):
        raise SystemExit("terminal evidence or canonical checkpoint differs")

    preparation = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-GTC-INPUT-COMPATIBILITY-DIAGNOSTIC-001-REVIEW-PREPARATION-AUTHORITY",
        "recorded_at_utc": args.prepared_at_utc,
        "status": "standing_authority_local_zero_decision_preparation_only",
        "authority_basis": {
            "project_instruction_ref": AGENTS_REF,
            "project_instruction_sha256": PROTECTED_HASHES[AGENTS_REF],
            "standing_rule": "batch genuinely new owner decisions at a coherent milestone boundary",
            "local_follow_on_design_released": True,
            "interpretation": "prepare and validate one local zero-decision packet; reserve publication, implementation, data access, execution, and terminal publication for one later owner decision",
        },
        "authority_boundary": {
            "local_review_packet_preparation_authorized": True,
            "local_validation_authorized": True,
            "git_commit_or_push_authorized": False,
            "public_ci_authorized": False,
            "owner_proposal_decision_recording_authorized": False,
            "diagnostic_implementation_authorized": False,
            "arcpy_invocation_authorized": False,
            "project_data_or_external_custody_access_authorized": False,
            "geoprocessing_authorized": False,
            "new_radar_processing_attempt_authorized": False,
            "baseline_or_change_analysis_authorized": False,
            "scientific_publication_authorized": False,
        },
        "bindings": {"base_commit": BASE_COMMIT, **PROTECTED_HASHES},
    }
    write_json(PREPARATION_REF, preparation)

    protected = [{"path": ref, "sha256": digest, "must_remain_unchanged": True} for ref, digest in PROTECTED_HASHES.items()]
    proposal = {
        "schema_version": "1.0",
        "proposal_id": "NEPAL-M2-RADAR-GTC-INPUT-COMPATIBILITY-DIAGNOSTIC-001",
        "prepared_at_utc": args.prepared_at_utc,
        "status": "proposed_zero_decision_not_authorized",
        "human_decision_count": 0,
        "preparation_authority": {"ref": PREPARATION_REF, "sha256": sha256(PREPARATION_REF)},
        "trigger": {
            "terminal_reconciliation_ref": TERMINAL_REF,
            "terminal_reconciliation_sha256": PROTECTED_HASHES[TERMINAL_REF],
            "outcome_reconciliation_ref": OUTCOME_REF,
            "outcome_reconciliation_sha256": PROTECTED_HASHES[OUTCOME_REF],
            "terminal_publication_reconciliation_ref": TERMINAL_PUBLICATION_REF,
            "terminal_publication_reconciliation_sha256": PROTECTED_HASHES[TERMINAL_PUBLICATION_REF],
        },
        "observed_state": {
            "attempt_id": ATTEMPT_ID,
            "attempt_terminal_and_consumed": True,
            "source_id": "M1-SRC-001",
            "completed_sequence": ["ApplyOrbitCorrection", "RemoveThermalNoise", "ApplyRadiometricCalibration", "ApplyRadiometricTerrainFlattening", "Despeckle_REFINED_LEE"],
            "failing_tool": "ApplyGeometricTerrainCorrection_gamma",
            "failure_message": terminal["execution_result"]["failure_message"],
            "despeckled_output_created": True,
            "gtc_output_created": False,
            "historical_root_cause_established": False,
            "radar_recovery_readiness_established": False,
            "post_observation_limit": "The proposed checks were selected after the GTC failure and can characterize only the preserved current inputs; they cannot prove an unrecorded historical cause.",
        },
        "protected_public_evidence": protected,
        "proposed_single_authority_envelope": {
            "covers_without_intermediate_reconfirmation": [
                "bounded diagnostic implementation",
                "portable synthetic no-content tests",
                "installed ArcGIS runtime synthetic test using disposable inputs only",
                "public default-branch publication and CI gates",
                "one final no-content preflight",
                "at most one fresh read-only diagnostic process",
                "exact reconciliation and sanitized terminal publication",
            ],
            "diagnostic_id": DIAGNOSTIC_ID,
            "diagnostic_root": DIAGNOSTIC_ROOT,
            "mode": "single_process_read_only_metadata_no_pixel_read_no_geoprocessing",
            "exact_preserved_root": ATTEMPT_ROOT,
            "exact_candidates": [
                "s/1/gamma0_linear_slant.crf",
                "s/1/gamma0_linear_despeckled.crf",
                "s/1/scattering_area.crf",
                "s/1/geometric_distortion.crf",
                "s/1/geometric_distortion_mask_slant.crf",
                "dem/ellipsoidal_dem_mosaic.tif",
            ],
            "fixed_check_order": [
                "reserve append-only terminal and cleanup receipt identities before content access",
                "verify exact protected public evidence",
                "require the exact preserved attempt root and every candidate without reconstruction or substitution",
                "record sanitized filesystem type and size metadata without opening pixel blocks",
                "import ArcPy and record product, extensions, and exact GTC signature identity",
                "evaluate arcpy.Exists for each exact candidate",
                "record sanitized arcpy.Describe metadata for recognized candidates: dataType, datasetType, format, bandCount, pixelType, spatial reference identity, cell size, extent dimensions, and multidimensional flag when exposed",
                "compare only structural metadata among slant gamma, despeckled gamma, terrain-flattening support outputs, and DEM",
                "persist terminal and cleanup receipts and publish only sanitized findings",
            ],
            "maximum_diagnostic_processes": 1,
            "maximum_arcpy_imports": 1,
            "maximum_geoprocessing_calls": 0,
            "maximum_raster_function_calls": 0,
            "maximum_pixel_reads": 0,
            "maximum_network_requests": 0,
            "maximum_credential_actions": 0,
            "automatic_retry": False,
            "missing_or_unrecognized_candidate_semantics": "terminal block without reconstruction, substitution, mutation, or processing",
            "result_may_establish": "current structural and ArcGIS catalog compatibility observations for the exact preserved inputs",
            "result_does_not_establish": ["historical root cause", "a corrected GTC method", "radar recovery readiness", "authorization for another processing attempt", "usable baseline", "change evidence", "interpretation", "attribution", "scientific result"],
        },
        "does_not_authorize_now": [
            "Git publication or public CI",
            "proposal approval or implementation",
            "ArcPy invocation or project-data access",
            "geoprocessing, raster-function, or pixel-read calls",
            "attempt reuse, retry, reconstruction, mutation, or a new radar-processing attempt",
            "source, orbit, DEM, AOI, CRS, grid, mask, threshold, registration, route, or method substitution",
            "baseline, change analysis, interpretation, attribution, derived-pixel publication, or scientific publication",
        ],
    }
    write_json(PROPOSAL_REF, proposal)

    preflight = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-GTC-INPUT-COMPATIBILITY-DIAGNOSTIC-001-REVIEW-PREFLIGHT",
        "checked_at_utc": args.prepared_at_utc,
        "status": "pass_local_zero_decision_packet_preparation_only",
        "bindings": {"preparation_authority_sha256": sha256(PREPARATION_REF), "proposal_sha256": sha256(PROPOSAL_REF), "preparation_script_sha256": sha256("scripts/prepare_m2_radar_gtc_input_compatibility_diagnostic_001_review.py"), "base_commit": BASE_COMMIT},
        "checks": {"terminal_attempt_consumed": True, "refined_lee_output_created": True, "gtc_output_absent": True, "protected_public_evidence_exact": True, "canonical_checkpoint_unchanged": True, "human_decision_count_zero": True},
        "assertions": {"git_commit_created": False, "git_push_performed": False, "public_ci_started": False, "arcpy_invoked": False, "project_data_read": False, "external_custody_accessed": False, "geoprocessing_invoked": False, "pixel_data_read": False, "new_attempt_created": False, "scientific_result_established": False},
    }
    write_json(PREFLIGHT_REF, preflight)

    proposal_sha = sha256(PROPOSAL_REF)
    document = f"""# M2 radar GTC input-compatibility diagnostic-001 review

## Review status

This is a local zero-decision packet. Proposal SHA-256: `{proposal_sha}`. It is not published, approved, or authorized for implementation or data access.

## Exact observed boundary

Recovery-005 attempt `{ATTEMPT_ID}` is terminal and consumed. `M1-SRC-001` completed orbit correction, thermal-noise removal, calibration, radiometric terrain flattening, and the approved exact `REFINED_LEE` despeckle. ArcGIS then raised `ERROR 000425` inside gamma `ApplyGeometricTerrainCorrection` before returning a Raster. No GTC output, later source, route, or retry exists.

This establishes a precise call boundary, not its cause. The preserved terminal evidence does not record whether the saved despeckled CRF and terrain-support inputs retain the structural metadata ArcGIS expects at that boundary.

## Proposed single bounded diagnostic envelope

One later approval would cover implementation, synthetic tests, public CI, one final no-content preflight, at most one fresh read-only diagnostic process, reconciliation, and sanitized terminal publication without intermediate owner reconfirmation.

The diagnostic would inspect only the six exact preserved recovery-005 candidates listed in the proposal. It would record filesystem metadata, `arcpy.Exists`, and sanitized `arcpy.Describe` metadata. It would perform zero geoprocessing calls, zero raster-function calls, zero pixel reads, zero network requests, and zero mutations. Missing or unrecognized input terminates the diagnostic without reconstruction or substitution.

The result may characterize current structural and ArcGIS catalog compatibility only. It cannot establish historical root cause, a corrected method, recovery readiness, a usable baseline, change evidence, interpretation, attribution, or a scientific result.

## Current boundary

Preparation changed no canonical checkpoint and accessed no project data. Publication, implementation, ArcPy, external custody, the diagnostic process, another radar-processing attempt, baseline work, change analysis, attribution, and scientific publication remain unauthorized.
"""
    write_text(DOC_REF, document)

    bundle = {
        "schema_version": "1.0",
        "bundle_id": "NEPAL-M2-RADAR-GTC-INPUT-COMPATIBILITY-DIAGNOSTIC-001-REVIEW-BUNDLE",
        "prepared_at_utc": args.prepared_at_utc,
        "status": "ready_local_zero_decision_publication_not_authorized",
        "human_decision_count": 0,
        "artifacts": [artifact(PREPARATION_REF, "preparation_authority"), artifact(PROPOSAL_REF, "proposal"), artifact(PREFLIGHT_REF, "preparation_preflight"), artifact(DOC_REF, "human_readable_review"), artifact(TERMINAL_REF, "terminal_reconciliation"), artifact(OUTCOME_REF, "outcome_reconciliation"), artifact(TERMINAL_PUBLICATION_REF, "terminal_publication_reconciliation")],
        "decision_requested_after_publication": {"decision_id": "D-M2-RADAR-GTC-INPUT-COMPATIBILITY-DIAGNOSTIC-001", "question": "Approve, revise, or defer the single bounded diagnostic envelope?", "choices": ["approve", "revise", "defer"], "response_open": False},
        "authority_boundary": {"publication_authorized": False, "owner_review_open": False, "implementation_authorized": False, "arcpy_invocation_authorized": False, "project_data_access_authorized": False, "geoprocessing_authorized": False, "new_radar_processing_attempt_authorized": False},
    }
    write_json(BUNDLE_REF, bundle)

    bundle_sha = sha256(BUNDLE_REF)
    contract = {
        "schema_version": "1.0",
        "contract_id": "NEPAL-M2-RADAR-GTC-INPUT-COMPATIBILITY-DIAGNOSTIC-001-REVIEW-CONTRACT",
        "prepared_at_utc": args.prepared_at_utc,
        "review_bundle": {"ref": BUNDLE_REF, "sha256": bundle_sha},
        "proposal": {"ref": PROPOSAL_REF, "sha256": proposal_sha},
        "workflow_authority": {"local_preparation_complete": True, "public_review_publication_authorized": False, "review_response_open": False},
        "response_requirements": {"exact_proposal_sha256_required": proposal_sha, "exact_review_bundle_sha256_required": bundle_sha, "explicit_decision_required": True, "attestation_required": True},
        "authority_boundary": bundle["authority_boundary"],
    }
    write_json(CONTRACT_REF, contract)

    blank = {
        "schema_version": "1.0",
        "response_id": "NEPAL-M2-RADAR-GTC-INPUT-COMPATIBILITY-DIAGNOSTIC-001-BLANK-RESPONSE",
        "completed": False,
        "reviewer": {"name": None, "reviewed_at_utc": None, "attestation": False},
        "responses": [{"decision_id": bundle["decision_requested_after_publication"]["decision_id"], "decision": None, "comment": None}],
        "human_decision_count": 0,
        "response_not_open_until_public_ci": True,
        "bindings": {"proposal_sha256": proposal_sha, "review_bundle_sha256": bundle_sha},
    }
    write_json(BLANK_REF, blank)

    readiness = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-GTC-INPUT-COMPATIBILITY-DIAGNOSTIC-001-REVIEW-READINESS",
        "verified_at_utc": args.prepared_at_utc,
        "status": "pass_local_zero_decision_packet_ready_publication_authority_required",
        "bindings": {"preparation_authority_ref": PREPARATION_REF, "preparation_authority_sha256": sha256(PREPARATION_REF), "proposal_ref": PROPOSAL_REF, "proposal_sha256": proposal_sha, "review_preflight_ref": PREFLIGHT_REF, "review_preflight_sha256": sha256(PREFLIGHT_REF), "review_document_ref": DOC_REF, "review_document_sha256": sha256(DOC_REF), "review_bundle_ref": BUNDLE_REF, "review_bundle_sha256": bundle_sha, "review_contract_ref": CONTRACT_REF, "review_contract_sha256": sha256(CONTRACT_REF), "blank_response_ref": BLANK_REF, "blank_response_sha256": sha256(BLANK_REF)},
        "validation": {"terminal_attempt_preserved": True, "external_candidates_not_inspected_or_claimed": True, "post_observation_limit_disclosed": True, "human_decision_count": 0, "canonical_checkpoint_unchanged": True, "single_later_owner_decision_designed": True},
        "released_now": {"local_packet_preparation": True, "local_packet_validation": True, "git_commit_or_push": False, "public_ci": False, "owner_proposal_review": False, "diagnostic_implementation": False, "arcpy_invocation": False, "project_data_access": False, "geoprocessing": False, "new_radar_processing_attempt": False, "baseline_or_change_analysis": False, "scientific_publication": False},
        "assertions": preflight["assertions"],
        "next_action": "Obtain one owner authorization covering publication of this exact packet, implementation, tests, public CI, one final no-content preflight, at most one fresh read-only diagnostic process, exact reconciliation, and sanitized terminal publication without intermediate reconfirmation.",
    }
    write_json(READINESS_REF, readiness)

    print(json.dumps({"status": readiness["status"], "proposal_sha256": proposal_sha, "review_bundle_sha256": bundle_sha, "review_readiness_sha256": sha256(READINESS_REF), "current_checkpoint": CURRENT_CHECKPOINT}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
