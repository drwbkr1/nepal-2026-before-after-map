#!/usr/bin/env python3
"""Integrate the exact authorized receipt-recovery review packet for publication."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-apply-orbit-correction-input-resolution-diagnostic-receipt-persistence-recovery-001"
PROPOSAL_REF = "contracts/milestone-002-radar-apply-orbit-correction-input-resolution-diagnostic-receipt-persistence-recovery-001-proposal.json"
BUNDLE_REF = f"reviews/{PREFIX}/review-bundle.json"
CONTRACT_REF = f"reviews/{PREFIX}/review-contract.json"
BLANK_REF = f"reviews/{PREFIX}/blank-response.json"
READINESS_REF = f"records/readiness/{PREFIX}-review-readiness.json"
PREFLIGHT_REF = f"records/readiness/{PREFIX}-review-preflight.json"
PREPARATION_APPROVAL_REF = f"records/source-gates/{PREFIX}-review-preparation-approval.json"
PUBLICATION_APPROVAL_REF = f"records/source-gates/{PREFIX}-review-publication-approval.json"
ACTIVATION_REF = f"records/readiness/{PREFIX}-review-publication-activation.json"
FAILURE_REF = "records/readiness/m2-radar-apply-orbit-correction-input-resolution-diagnostic-001-terminal-receipt-persistence-failure-observation.json"
LOCAL_VALIDATION_REF = f"records/readiness/{PREFIX}-local-validation.json"
TERMINAL_REF = "records/processing/m2-radar-apply-orbit-correction-input-resolution-diagnostic-001-terminal.json"
CLEANUP_REF = "records/processing/m2-radar-apply-orbit-correction-input-resolution-diagnostic-001-cleanup.json"
FINAL_PREFLIGHT_REF = "records/readiness/m2-radar-apply-orbit-correction-input-resolution-diagnostic-001-final-preflight.json"
GATE_STATE_REF = "records/readiness/m2-radar-apply-orbit-correction-input-resolution-diagnostic-001-gate-state-publication.json"
MILESTONE_REF = "contracts/milestone-002.json"
PROFILE_REF = "records/project-control-profile.json"
GOAL_REF = "records/long-term-goal.json"
LEDGER_REF = "records/evidence-ledger.jsonl"

BASE_COMMIT = "b705dadd8ab989e1dcbfa04d9a3bd082064a6177"
PROPOSAL_SHA256 = "607c1ba872f91226afc5b3b1c2ce69f111979d20d2f6c611dac9b496f5ed1a28"
BUNDLE_SHA256 = "006ffc48f7344f43b073404163962dbe6f821273b21f4c80a448a11777deb847"
OLD_CHECKPOINT = "M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-EXECUTION"
CHECKPOINT = "M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-REVIEW-PUBLICATION"
UNIT_ID = "M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-REVIEW"
NEXT_ACTION = (
    "Publish and publicly validate the exact zero-decision ApplyOrbitCorrection input-resolution diagnostic "
    "receipt-persistence recovery-001 review packet. Keep the owner proposal response closed until the exact packet "
    "commit passes public default-branch CI. Preserve the consumed diagnostic and its zero-byte reserved receipts. "
    "Do not implement the correction, invoke ArcPy, access project data or external custody, start a new process, "
    "retry, reconstruct lost observations, mutate either receipt, call geoprocessing, process radar data, run baseline "
    "or change analysis, attribute cause, or publish science."
)
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


def path(ref: str) -> Path:
    return ROOT / ref


def sha256(ref: str) -> str:
    return hashlib.sha256(path(ref).read_bytes()).hexdigest()


def load(ref: str) -> dict[str, Any]:
    value = json.loads(path(ref).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {ref}")
    return value


def write_json_exclusive(ref: str, value: dict[str, Any]) -> None:
    destination = path(ref)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def write_json_atomic(ref: str, value: dict[str, Any]) -> None:
    destination = path(ref)
    handle, temporary = tempfile.mkstemp(prefix=destination.name + ".", suffix=".tmp", dir=destination.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        os.replace(temporary, destination)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def git_value(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--integrated-at-utc", required=True)
    args = parser.parse_args()
    if not args.integrated_at_utc.endswith("Z"):
        raise SystemExit("integration time must be UTC")
    if path(ACTIVATION_REF).exists():
        raise SystemExit("publication activation already exists")

    head = git_value("rev-parse", "HEAD")
    origin = git_value("rev-parse", "origin/main")
    if head != BASE_COMMIT or origin != BASE_COMMIT:
        raise SystemExit("publication integration base is not the exact terminal commit")
    if sha256(PROPOSAL_REF) != PROPOSAL_SHA256 or sha256(BUNDLE_REF) != BUNDLE_SHA256:
        raise SystemExit("exact authorized packet identity drift")

    approval = load(PUBLICATION_APPROVAL_REF)
    preparation = load(PREPARATION_APPROVAL_REF)
    contract = load(CONTRACT_REF)
    blank = load(BLANK_REF)
    readiness = load(READINESS_REF)
    failure = load(FAILURE_REF)
    local_validation = load(LOCAL_VALIDATION_REF)
    final_preflight = load(FINAL_PREFLIGHT_REF)
    gate_state = load(GATE_STATE_REF)
    milestone = load(MILESTONE_REF)
    profile = load(PROFILE_REF)
    goal = load(GOAL_REF)

    boundary = approval.get("authority_boundary", {})
    if (
        approval.get("status") != "approved_exact_zero_decision_review_publication_only"
        or approval.get("human_decision_count") != 1
        or approval.get("attestation") is not True
        or approval.get("bindings", {}).get("proposal_sha256") != PROPOSAL_SHA256
        or approval.get("bindings", {}).get("review_bundle_sha256") != BUNDLE_SHA256
        or any(boundary.get(key) is not True for key in (
            "repository_control_integration_authorized",
            "public_default_branch_publication_authorized",
            "public_ci_authorized",
            "post_ci_publication_reconciliation_authorized",
        ))
        or any(boundary.get(key) is not False for key in (
            "owner_proposal_approval_authorized",
            "recovery_implementation_authorized",
            "arcpy_invocation_authorized",
            "new_diagnostic_process_authorized",
            "consumed_attempt_retry_or_reuse_authorized",
            "input_resolution_reconstruction_authorized",
            "reserved_receipt_mutation_authorized",
            "geoprocessing_authorized",
            "project_data_or_external_custody_access_authorized",
            "radar_processing_authorized",
            "baseline_or_change_authorized",
            "attribution_authorized",
            "scientific_publication_authorized",
        ))
    ):
        raise SystemExit("publication authority is absent, mismatched, or too broad")

    if (
        preparation.get("status") != "approved_local_zero_decision_review_preparation_only"
        or contract.get("status") != "locally_prepared_not_public_owner_response_not_yet_open"
        or contract.get("workflow_authority", {}).get("review_response_open") is not False
        or blank.get("completed") is not False
        or blank.get("human_decision_count") != 0
        or blank.get("response_not_open_until_public_ci") is not True
        or readiness.get("status") != "pass_local_zero_decision_packet_ready_publication_authority_required"
        or failure.get("status") != "terminal_process_consumed_reserved_receipts_empty_result_indeterminate"
        or failure.get("assertions", {}).get("diagnostic_process_consumed") is not True
        or failure.get("assertions", {}).get("automatic_retry_performed") is not False
        or failure.get("assertions", {}).get("input_resolution_result_reconstructed") is not False
        or local_validation.get("status") != "pass_packet_specific_validation_repository_reconciliation_block_retained"
        or local_validation.get("interpretation", {}).get("block_is_the_preserved_unreconciled_consumed_diagnostic_state") is not True
        or final_preflight.get("status") != "pass_final_no_content_preflight_one_read_only_diagnostic_released"
        or gate_state.get("status") != "pass_public_gate_state_final_no_content_preflight_released"
        or not path(TERMINAL_REF).exists()
        or not path(CLEANUP_REF).exists()
        or path(TERMINAL_REF).stat().st_size != 0
        or path(CLEANUP_REF).stat().st_size != 0
        or sha256(TERMINAL_REF) != EMPTY_SHA256
        or sha256(CLEANUP_REF) != EMPTY_SHA256
        or milestone.get("handoff", {}).get("current_checkpoint") != OLD_CHECKPOINT
        or profile.get("current_checkpoint", {}).get("checkpoint_id") != OLD_CHECKPOINT
        or goal.get("current_checkpoint") != OLD_CHECKPOINT
        or profile.get("control_surfaces", {}).get("proposed_amendments") != []
        or goal.get("proposed_amendments") != []
    ):
        raise SystemExit("local packet, terminal persistence block, or canonical checkpoint differs")

    proposal = load(PROPOSAL_REF)
    for protected in proposal.get("protected_public_implementation", []):
        if protected.get("must_remain_unchanged_during_preparation") is not True or sha256(protected["path"]) != protected["sha256"]:
            raise SystemExit(f"protected terminal evidence drift: {protected.get('path')}")

    unit_ids = {item.get("id") for item in milestone.get("units", []) if isinstance(item, dict)}
    if UNIT_ID in unit_ids:
        raise SystemExit("receipt-recovery review unit collision")

    activation = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-REVIEW-PUBLICATION-ACTIVATION",
        "activated_at_utc": args.integrated_at_utc,
        "status": "pass_exact_publication_authority_activated_public_ci_pending",
        "bindings": {
            "publication_approval_ref": PUBLICATION_APPROVAL_REF,
            "publication_approval_sha256": sha256(PUBLICATION_APPROVAL_REF),
            "proposal_ref": PROPOSAL_REF,
            "proposal_sha256": PROPOSAL_SHA256,
            "review_bundle_ref": BUNDLE_REF,
            "review_bundle_sha256": BUNDLE_SHA256,
            "review_contract_ref": CONTRACT_REF,
            "review_contract_sha256": sha256(CONTRACT_REF),
            "blank_response_ref": BLANK_REF,
            "blank_response_sha256": sha256(BLANK_REF),
            "review_readiness_ref": READINESS_REF,
            "review_readiness_sha256": sha256(READINESS_REF),
            "base_commit": head,
        },
        "released_now": {
            "repository_control_integration": True,
            "public_default_branch_publication": True,
            "public_ci": True,
            "post_ci_publication_reconciliation": True,
            "owner_proposal_review": False,
            "implementation": False,
            "arcpy_invocation": False,
            "new_diagnostic_process": False,
            "consumed_attempt_retry_or_reuse": False,
            "input_resolution_reconstruction": False,
            "reserved_receipt_mutation": False,
            "geoprocessing": False,
            "project_data_or_external_custody_access": False,
            "radar_processing": False,
            "baseline_or_change_analysis": False,
            "attribution": False,
            "scientific_publication": False,
        },
        "assertions": {
            "packet_human_decision_count": 0,
            "owner_proposal_decision_recorded": False,
            "public_ci_passed": False,
            "owner_review_open": False,
            "protected_diagnostic_code_modified": False,
            "arcpy_invoked": False,
            "new_diagnostic_process_started": False,
            "consumed_attempt_retried_or_reused": False,
            "input_resolution_reconstructed": False,
            "reserved_receipt_mutated": False,
            "geoprocessing_invoked": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "scientific_result_established": False,
        },
        "next_action": NEXT_ACTION,
    }
    write_json_exclusive(ACTIVATION_REF, activation)

    unit = {
        "id": UNIT_ID,
        "purpose": "Publish and review one exact diagnostic receipt-persistence recovery proposal while preserving the consumed process and both zero-byte reserved receipts.",
        "depends_on": ["M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-EXECUTION"],
        "action_class": "authority_broadening",
        "human_gate": True,
        "status": "planned",
        "inputs": [
            PREPARATION_APPROVAL_REF,
            PUBLICATION_APPROVAL_REF,
            ACTIVATION_REF,
            PROPOSAL_REF,
            PREFLIGHT_REF,
            READINESS_REF,
            BUNDLE_REF,
            CONTRACT_REF,
            BLANK_REF,
            TERMINAL_REF,
            CLEANUP_REF,
            FAILURE_REF,
            LOCAL_VALIDATION_REF,
            FINAL_PREFLIGHT_REF,
            GATE_STATE_REF,
        ],
        "outputs": [],
        "gates": {
            "public_ci": "pending",
            "human_decision_count": 0,
            "attestation": False,
            "review_response_open": False,
            "owner_proposal_approval_authorized": False,
            "implementation_authorized": False,
            "arcpy_invocation_authorized": False,
            "new_diagnostic_process_authorized": False,
            "consumed_attempt_retry_or_reuse_authorized": False,
            "input_resolution_reconstruction_authorized": False,
            "reserved_receipt_mutation_authorized": False,
            "geoprocessing_authorized": False,
            "project_data_or_external_custody_access_authorized": False,
            "radar_processing_authorized": False,
            "baseline_or_change_authorized": False,
            "attribution_authorized": False,
            "scientific_publication_authorized": False,
        },
        "disposition": None,
        "retained_failures": [FAILURE_REF, TERMINAL_REF, CLEANUP_REF],
        "exit_condition_delta": {
            "expected": ["successful public default-branch CI", "one later exact attested owner proposal decision"],
            "observed": ["exact zero-decision packet publication authorized; public CI pending"],
            "decision_value": "unknown",
            "rationale": "Publication authority opens no substantive proposal decision and releases no implementation or execution.",
        },
        "next_dependency": "M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-IMPLEMENTATION",
    }
    milestone["units"].append(unit)
    milestone["handoff"].update(
        {
            "current_checkpoint": CHECKPOINT,
            "next_action": NEXT_ACTION,
            "parallel_checkpoint": CHECKPOINT,
            "parallel_next_action": NEXT_ACTION,
        }
    )
    milestone["handoff"].setdefault("do_not_carry_forward", []).append(
        "The diagnostic receipt-persistence recovery packet has zero decisions and is publication-only; its owner response stays closed until public CI, both zero-byte reserved receipts remain immutable, and no implementation, ArcPy, data access, new process, retry, reconstruction, geoprocessing, radar processing, or scientific action is released."
    )

    profile["control_surfaces"]["proposed_amendments"] = [PROPOSAL_REF]
    profile["current_checkpoint"] = {
        "checkpoint_id": CHECKPOINT,
        "expected_branch": "main",
        "expected_head": None,
        "next_action": NEXT_ACTION,
    }
    profile["parallel_checkpoints"] = [
        {"checkpoint_id": CHECKPOINT, "authority_ref": PUBLICATION_APPROVAL_REF, "next_action": NEXT_ACTION}
    ]
    profile["human_gates"]["review_gates"].append(
        {
            "unit_id": UNIT_ID,
            "reason": "Diagnostic receipt-persistence recovery implementation or a distinct new read-only process requires a later exact attested owner decision after public CI.",
            "authority_ref": CONTRACT_REF,
        }
    )

    goal["current_checkpoint"] = CHECKPOINT
    goal["proposed_amendments"] = [PROPOSAL_REF]
    goal["parallel_checkpoints"] = [CHECKPOINT]

    write_json_atomic(MILESTONE_REF, milestone)
    write_json_atomic(PROFILE_REF, profile)
    write_json_atomic(GOAL_REF, goal)

    evidence = {
        "record_id": "EVID-0197",
        "type": "m2_radar_apply_orbit_correction_input_resolution_diagnostic_receipt_persistence_recovery_001_review_publication_authority",
        "verified_at_utc": args.integrated_at_utc,
        "status": "pass_exact_zero_decision_review_publication_authorized_public_ci_pending",
        "claim": "The owner authorized only repository-control integration preserving the terminal persistence block, public default-branch publication, public CI, and exact post-CI reconciliation for the exact zero-decision diagnostic receipt-persistence recovery packet. The owner proposal response remains closed; both consumed zero-byte receipts remain immutable; and no implementation, ArcPy, data access, new process, retry, reconstruction, geoprocessing, radar processing, baseline, change analysis, attribution, or scientific publication is released.",
        "publication_approval_sha256": sha256(PUBLICATION_APPROVAL_REF),
        "publication_activation_sha256": sha256(ACTIVATION_REF),
        "proposal_sha256": PROPOSAL_SHA256,
        "review_bundle_sha256": BUNDLE_SHA256,
        "assertions": {
            "human_decision_count": 1,
            "packet_human_decision_count": 0,
            "public_ci_pending": True,
            "owner_proposal_decision_recorded": False,
            "owner_review_open": False,
            "implementation_authorized": False,
            "arcpy_invoked": False,
            "new_diagnostic_process_started": False,
            "consumed_attempt_retried_or_reused": False,
            "input_resolution_reconstructed": False,
            "reserved_receipt_mutated": False,
            "geoprocessing_invoked": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "radar_processing_executed": False,
            "scientific_result_established": False,
            "current_checkpoint": CHECKPOINT,
        },
        "next_action": NEXT_ACTION,
    }
    with path(LEDGER_REF).open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(evidence, separators=(",", ":"), ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {
                "status": activation["status"],
                "publication_approval_sha256": sha256(PUBLICATION_APPROVAL_REF),
                "publication_activation_sha256": sha256(ACTIVATION_REF),
                "checkpoint": CHECKPOINT,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
