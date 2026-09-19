#!/usr/bin/env python3
"""Lock the exact owner decision and activate diagnostic-001 implementation."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-apply-orbit-correction-input-resolution-diagnostic-001"
PROPOSAL_REF = f"contracts/milestone-002-radar-apply-orbit-correction-input-resolution-diagnostic-001-proposal.json"
PROPOSAL_SHA256 = "bb318432bf3a63f2bb75d2b1ea69716b6fbade9917d7c35ff8388d3edaa41d84"
BUNDLE_REF = f"reviews/{PREFIX}/review-bundle.json"
BUNDLE_SHA256 = "88c5e50d2f8f223e1c148caa0212e1b28ba4c80eb3eacae23be7e4f63bd477af"
REVIEW_CONTRACT_REF = f"reviews/{PREFIX}/review-contract.json"
REVIEW_CONTRACT_SHA256 = "c3d0a2d59de816496d9e91f0a69cc789f264e5520278b715f5cd794439ec8203"
REVIEW_PUBLICATION_REF = f"records/readiness/{PREFIX}-review-publication-gate.json"
REVIEW_RECONCILIATION_REF = f"records/source-gates/{PREFIX}-review-reconciliation.json"
APPROVAL_REF = f"records/source-gates/{PREFIX}-approval.json"
ACTIVATION_REF = f"records/readiness/{PREFIX}-approval-activation.json"
DIAGNOSTIC_CONTRACT_REF = f"config/qa/{PREFIX}-contract.json"
REVIEW_UNIT = "M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-REVIEW"
IMPLEMENTATION_UNIT = "M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-IMPLEMENTATION"
EXECUTION_UNIT = "M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-EXECUTION"
CHECKPOINT = IMPLEMENTATION_UNIT
ATTEMPT_ID = "radar-apply-orbit-correction-input-resolution-diagnostic-001-real-001"
RECOVERY_ATTEMPT_ROOT = (
    r"C:\Projects\Active\nepal-2026-before-after-map-data\derived\radar-pixel-orbit-application-recovery-002"
    r"\radar-pixel-orbit-application-recovery-002-real-001"
)
PRODUCT_ID = "S1D_IW_GRDH_1SDV_20260816T122116_20260816T122141_004151_007980_B057.SAFE"
SAFE_RELATIVE = f"sources/m1-src-001/{PRODUCT_ID}"
MANIFEST_RELATIVE = f"{SAFE_RELATIVE}/manifest.safe"
ORBIT_PATH = (
    r"C:\Projects\Active\nepal-2026-before-after-map-data\custody\orbits\s1d\resorb\m2-orb-001"
    r"\S1D_OPER_AUX_RESORB_OPOD_20260816T143208_V20260816T103526_20260816T140956.EOF"
)
ORBIT_SHA256 = "a72c93e500a1c09b62b4cd31889837c9d57ccc41542b16397ff9f2c0fccba3f4"
ORBIT_SIZE_BYTES = 639533
NEXT_ACTION = (
    "Implement and validate only the approved read-only ApplyOrbitCorrection input-resolution diagnostic and synthetic "
    "no-content tests, then require successful public default-branch CI. Do not run the final no-content preflight, "
    "import production ArcPy, or access the recovery-002 attempt root or orbit custody before that public gate."
)
RAW_APPROVAL = (
    "I approve M2 radar ApplyOrbitCorrection input-resolution diagnostic-001 review bundle "
    "`88c5e50d2f8f223e1c148caa0212e1b28ba4c80eb3eacae23be7e4f63bd477af` and proposal "
    "`bb318432bf3a63f2bb75d2b1ea69716b6fbade9917d7c35ff8388d3edaa41d84`. I authorize only the bounded "
    "implementation, synthetic no-content tests, public-CI gate, final no-content preflight, and at most one read-only "
    "diagnostic process over the exact recovery-002 attempt-root candidates and exact M2-ORB-001 stated in the reviewed "
    "proposal. I understand the diagnostic must stop if the attempt root or candidate is missing and authorizes no "
    "reconstruction, substitution, copying, mutation, ApplyOrbitCorrection or other geoprocessing call, retry, new radar "
    "attempt, baseline or change analysis, interpretation, attribution, derived-pixel publication, historical-root-cause "
    "claim, radar-recovery-readiness claim, or scientific publication. I attest this is my completed decision."
)


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(ref: str) -> dict[str, Any]:
    value = json.loads((ROOT / ref).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {ref}")
    return value


def write_new(ref: str, payload: bytes) -> None:
    path = ROOT / ref
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def replace_json(ref: str, value: object, nonce: str) -> None:
    path = ROOT / ref
    temporary = path.with_name(f".{path.name}.{nonce}.tmp")
    with temporary.open("xb") as stream:
        stream.write(canonical_bytes(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def unit(milestone: dict[str, Any], unit_id: str) -> dict[str, Any]:
    matches = [item for item in milestone.get("units", []) if item.get("id") == unit_id]
    if len(matches) != 1:
        raise ValueError(f"unit missing or ambiguous: {unit_id}")
    return matches[0]


def append_evidence(value: dict[str, Any]) -> None:
    path = ROOT / "records/evidence-ledger.jsonl"
    with path.open("ab", buffering=0) as stream:
        stream.write(json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n")
        os.fsync(stream.fileno())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-at-utc", required=True)
    args = parser.parse_args()
    if not args.approved_at_utc.endswith("Z"):
        raise SystemExit("--approved-at-utc must be UTC")
    exact = {
        PROPOSAL_REF: PROPOSAL_SHA256,
        BUNDLE_REF: BUNDLE_SHA256,
        REVIEW_CONTRACT_REF: REVIEW_CONTRACT_SHA256,
    }
    if any(not (ROOT / ref).is_file() or sha256_file(ROOT / ref) != expected for ref, expected in exact.items()):
        raise SystemExit("review input identity drift")
    publication = load(REVIEW_PUBLICATION_REF)
    if (
        publication.get("status") != "pass_public_default_branch_ci_zero_decision_owner_review_ready"
        or publication.get("public_ci_conclusion") != "success"
    ):
        raise SystemExit("review publication gate is not an exact pass")

    response = {
        "schema_version": "1.0",
        "review_id": f"{PREFIX}-review",
        "contract_ref": REVIEW_CONTRACT_REF,
        "contract_sha256": REVIEW_CONTRACT_SHA256,
        "review_bundle_sha256": BUNDLE_SHA256,
        "completed": True,
        "review_completed_at_utc": args.approved_at_utc,
        "reviewer": {"name": "project_owner", "attestation": True},
        "responses": [{
            "item_id": "M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001",
            "decision": "approve",
            "rationale": "Exact bounded read-only diagnostic approved with every reviewed prohibition retained.",
            "evidence_sha256": BUNDLE_SHA256,
        }],
        "raw_attested_statement": RAW_APPROVAL,
        "human_decision_count": 1,
    }
    response_bytes = canonical_bytes(response)
    response_sha = hashlib.sha256(response_bytes).hexdigest()
    response_ref = f"reviews/{PREFIX}/response-{response_sha}.json"
    lock = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-REVIEW-CONTRACT-LOCK-001",
        "locked_at_utc": args.approved_at_utc,
        "status": "locked_exact_attested_response",
        "review_contract_ref": REVIEW_CONTRACT_REF,
        "review_contract_sha256": REVIEW_CONTRACT_SHA256,
        "review_bundle_sha256": BUNDLE_SHA256,
        "response_ref": response_ref,
        "response_sha256": response_sha,
        "human_decision_count": 1,
        "attestation": True,
    }
    lock_bytes = canonical_bytes(lock)
    lock_sha = hashlib.sha256(lock_bytes).hexdigest()
    lock_ref = f"reviews/{PREFIX}/review-contract-lock-001.json"
    reconciliation = {
        "reconciliation_version": "human-review-reconciliation-v1",
        "status": "reconciled_exact_human_response",
        "review_id": f"{PREFIX}-review",
        "contract_sha256": REVIEW_CONTRACT_SHA256,
        "response_sha256": response_sha,
        "receipt_sha256": lock_sha,
        "human_decision_count": 1,
        "decision_counts": {"approve": 1, "revise": 0, "defer": 0},
        "notes_included": False,
        "human_decisions_fabricated": False,
        "downstream_authorization_created": False,
        "authority_ref": APPROVAL_REF,
        "authorized_next_actions": ["evidence_recording", "project_control", "update_project_records"],
        "item_decisions": [{
            "item_id": "M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001",
            "decision": "approve",
        }],
    }
    reconciliation_bytes = canonical_bytes(reconciliation)
    reconciliation_sha = hashlib.sha256(reconciliation_bytes).hexdigest()
    proposal = load(PROPOSAL_REF)
    approval = {
        "schema_version": "1.0",
        "approval_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-APPROVAL",
        "status": "approved_bounded_read_only_input_resolution_diagnostic",
        "approved_at_utc": args.approved_at_utc,
        "review_id": f"{PREFIX}-review",
        "review_bundle_manifest_sha256": BUNDLE_SHA256,
        "proposal_ref": PROPOSAL_REF,
        "proposal_sha256": PROPOSAL_SHA256,
        "review_contract_ref": REVIEW_CONTRACT_REF,
        "review_contract_sha256": REVIEW_CONTRACT_SHA256,
        "review_publication_gate_ref": REVIEW_PUBLICATION_REF,
        "review_publication_gate_sha256": sha256_file(ROOT / REVIEW_PUBLICATION_REF),
        "review_reconciliation_ref": REVIEW_RECONCILIATION_REF,
        "review_reconciliation_sha256": reconciliation_sha,
        "locked_response_sha256": response_sha,
        "lock_receipt_sha256": lock_sha,
        "human_decision_count": 1,
        "decision_counts": {"approve": 1, "revise": 0, "defer": 0},
        "attestation": True,
        "proposed_diagnostic_contract": copy.deepcopy(proposal["proposed_diagnostic_contract"]),
        "stop_rules": copy.deepcopy(proposal["stop_rules"]),
        "does_not_authorize": copy.deepcopy(proposal["does_not_authorize_now"]),
        "human_decisions_fabricated": False,
    }
    approval_bytes = canonical_bytes(approval)
    approval_sha = hashlib.sha256(approval_bytes).hexdigest()
    activation = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-APPROVAL-ACTIVATION",
        "activated_at_utc": args.approved_at_utc,
        "status": "pass_exact_approval_activated_implementation_publication_only",
        "bindings": {
            "approval_ref": APPROVAL_REF,
            "approval_sha256": approval_sha,
            "reconciliation_sha256": reconciliation_sha,
            "proposal_sha256": PROPOSAL_SHA256,
            "review_bundle_sha256": BUNDLE_SHA256,
            "review_publication_gate_sha256": sha256_file(ROOT / REVIEW_PUBLICATION_REF),
        },
        "released_now": {
            "bounded_diagnostic_implementation": True,
            "synthetic_no_content_tests": True,
            "public_ci": True,
            "final_no_content_preflight": False,
            "diagnostic_process": False,
            "arcpy_invocation": False,
            "project_data_or_external_custody_access": False,
            "apply_orbit_correction": False,
            "geoprocessing": False,
            "new_radar_attempt": False,
        },
        "assertions": {
            "diagnostic_process_started": False,
            "arcpy_imported": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "attempt_root_current_presence_observed": False,
            "apply_orbit_correction_invoked": False,
            "geoprocessing_invoked": False,
            "attempt_root_reconstructed_or_substituted": False,
            "new_radar_attempt_created": False,
            "historical_root_cause_established": False,
            "radar_recovery_readiness_established": False,
            "scientific_result_established": False,
        },
    }
    activation_bytes = canonical_bytes(activation)
    activation_sha = hashlib.sha256(activation_bytes).hexdigest()
    diagnostic_contract = {
        "schema_version": "1.0",
        "contract_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-CONTRACT",
        "status": "approved_implementation_publication_pending",
        "authority": {
            "approval_ref": APPROVAL_REF,
            "approval_sha256": approval_sha,
            "proposal_ref": PROPOSAL_REF,
            "proposal_sha256": PROPOSAL_SHA256,
            "review_bundle_ref": BUNDLE_REF,
            "review_bundle_sha256": BUNDLE_SHA256,
            "review_reconciliation_ref": REVIEW_RECONCILIATION_REF,
            "review_reconciliation_sha256": reconciliation_sha,
            "activation_ref": ACTIVATION_REF,
            "activation_sha256": activation_sha,
        },
        "diagnostic": {
            "diagnostic_id": ATTEMPT_ID,
            "maximum_processes": 1,
            "maximum_final_preflights": 1,
            "automatic_retry": False,
            "mode": "read_only_single_process_no_geoprocessing",
        },
        "exact_inputs": {
            "terminal_attempt_id": "radar-pixel-orbit-application-recovery-002-real-001",
            "source_id": "M1-SRC-001",
            "orbit_source_id": "M2-ORB-001",
            "recovery_attempt_root": RECOVERY_ATTEMPT_ROOT,
            "safe_directory_relative": SAFE_RELATIVE,
            "manifest_relative": MANIFEST_RELATIVE,
            "orbit_path": ORBIT_PATH,
            "orbit_sha256": ORBIT_SHA256,
            "orbit_size_bytes": ORBIT_SIZE_BYTES,
        },
        "protected_public_evidence": copy.deepcopy(proposal["protected_public_evidence"]),
        "fixed_check_order": copy.deepcopy(proposal["proposed_diagnostic_contract"]["fixed_check_order"]),
        "arcgis_read_only_calls": [
            "GetInstallInfo", "ProductInfo", "CheckExtension", "Usage", "Exists", "Describe"
        ],
        "receipt_durability": {
            "terminal_identity_reserved_before_external_content_access": True,
            "cleanup_identity_reserved_before_external_content_access": True,
            "exclusive_no_replace": True,
            "reserved_handles_flushed_and_fsynced": True,
        },
        "limits": {
            "apply_orbit_correction_calls": 0,
            "geoprocessing_tool_calls": 0,
            "network_requests": 0,
            "credential_actions": 0,
            "source_orbit_or_dem_copies": 0,
            "source_orbit_or_dem_mutations": 0,
            "derived_raster_outputs": 0,
            "baseline_or_change_actions": 0,
            "scientific_outputs": 0,
        },
        "result_semantics": copy.deepcopy(proposal["proposed_diagnostic_contract"]["result_semantics"]),
    }

    outputs = {
        response_ref: response_bytes,
        lock_ref: lock_bytes,
        REVIEW_RECONCILIATION_REF: reconciliation_bytes,
        APPROVAL_REF: approval_bytes,
        ACTIVATION_REF: activation_bytes,
        DIAGNOSTIC_CONTRACT_REF: canonical_bytes(diagnostic_contract),
    }
    collisions = [ref for ref in outputs if (ROOT / ref).exists()]
    if collisions:
        raise SystemExit("refusing output collision: " + ", ".join(collisions))

    milestone = load("contracts/milestone-002.json")
    profile = load("records/project-control-profile.json")
    goal = load("records/long-term-goal.json")
    review = unit(milestone, REVIEW_UNIT)
    if review.get("status") != "in_progress" or review.get("gates", {}).get("human_decision_count") != 0:
        raise SystemExit("project is not at exact zero-decision review state")
    if any(item.get("id") in {IMPLEMENTATION_UNIT, EXECUTION_UNIT} for item in milestone.get("units", [])):
        raise SystemExit("diagnostic implementation units already exist")

    for ref, payload in outputs.items():
        write_new(ref, payload)

    review.update({"status": "complete", "disposition": "pass"})
    review["outputs"] = [response_ref, lock_ref, REVIEW_RECONCILIATION_REF, APPROVAL_REF, ACTIVATION_REF]
    review["gates"].update({
        "human_decision_count": 1,
        "attestation": True,
        "owner_proposal_approval_authorized": True,
        "diagnostic_implementation_authorized": True,
        "diagnostic_execution_conditionally_authorized": True,
        "arcpy_invocation_conditionally_authorized": True,
        "project_data_or_external_custody_access_conditionally_authorized": True,
        "approval_sha256": approval_sha,
        "review_reconciliation_sha256": reconciliation_sha,
    })
    review["exit_condition_delta"] = {
        "expected": [],
        "observed": ["one exact attested approval"],
        "decision_value": "enables_dependency",
        "rationale": "Implementation and public CI are released now; the diagnostic remains conditional on both public gates and final preflight.",
    }
    milestone["units"].extend([
        {
            "id": IMPLEMENTATION_UNIT,
            "purpose": "Implement and publicly validate the exact read-only input-resolution diagnostic without importing ArcPy or accessing external inputs.",
            "depends_on": [REVIEW_UNIT],
            "action_class": "routine_qa",
            "human_gate": False,
            "status": "in_progress",
            "inputs": [APPROVAL_REF, PROPOSAL_REF, REVIEW_RECONCILIATION_REF],
            "outputs": [
                DIAGNOSTIC_CONTRACT_REF,
                f"scripts/m2_radar_apply_orbit_correction_input_resolution_diagnostic_001_core.py",
                f"scripts/run_m2_radar_apply_orbit_correction_input_resolution_diagnostic_001.py",
                f"tests/test_m2_radar_apply_orbit_correction_input_resolution_diagnostic_001.py",
            ],
            "gates": {
                "synthetic_no_content_tests": "pending",
                "repository_validation": "pending",
                "public_ci": "pending",
                "arcpy_invoked": False,
                "external_inputs_accessed": False,
                "diagnostic_process_started": False,
            },
            "exit_condition_delta": {
                "expected": ["successful public default-branch CI"],
                "observed": [],
                "decision_value": "pending",
                "rationale": "Implementation does not itself release the diagnostic process.",
            },
            "next_dependency": EXECUTION_UNIT,
        },
        {
            "id": EXECUTION_UNIT,
            "purpose": "Run the one approved read-only diagnostic only after both public gates and a final no-content preflight.",
            "depends_on": [IMPLEMENTATION_UNIT],
            "action_class": "data_processing",
            "human_gate": False,
            "status": "planned",
            "inputs": [APPROVAL_REF, DIAGNOSTIC_CONTRACT_REF],
            "outputs": [
                f"records/readiness/{PREFIX}-final-preflight.json",
                f"records/processing/{PREFIX}-terminal.json",
                f"records/processing/{PREFIX}-cleanup.json",
            ],
            "gates": {
                "public_ci": "pending",
                "gate_state_publication": "pending",
                "final_no_content_preflight": "pending",
                "maximum_diagnostic_processes": 1,
                "diagnostic_processes_started": 0,
                "apply_orbit_correction_calls": 0,
                "geoprocessing_calls": 0,
            },
            "exit_condition_delta": {
                "expected": ["terminal diagnostic and cleanup receipts"],
                "observed": [],
                "decision_value": "pending",
                "rationale": "Either PASS or BLOCK remains diagnostic-only and creates no processing authority.",
            },
            "next_dependency": None,
        },
    ])
    milestone["handoff"].update({
        "current_checkpoint": CHECKPOINT,
        "next_action": NEXT_ACTION,
        "parallel_checkpoint": CHECKPOINT,
        "parallel_next_action": NEXT_ACTION,
    })
    amendment = {
        "approval_ref": APPROVAL_REF,
        "approval_sha256": approval_sha,
        "proposal_ref": PROPOSAL_REF,
        "proposal_sha256": PROPOSAL_SHA256,
        "review_bundle_sha256": BUNDLE_SHA256,
        "review_reconciliation_ref": REVIEW_RECONCILIATION_REF,
        "review_reconciliation_sha256": reconciliation_sha,
        "diagnostic_id": ATTEMPT_ID,
        "maximum_diagnostic_processes": 1,
        "automatic_retry_authorized": False,
        "apply_orbit_correction_authorized": False,
        "geoprocessing_authorized": False,
    }
    milestone.setdefault("authority", {}).setdefault("amendments", []).append(copy.deepcopy(amendment))
    milestone.setdefault("scope", {}).setdefault("active_amendments", []).append(APPROVAL_REF)
    profile["authority"].setdefault("amendments", []).append(amendment)
    profile.setdefault("control_surfaces", {})["proposed_amendments"] = []
    profile["control_surfaces"].setdefault("activated_amendments", []).append(APPROVAL_REF)
    profile["current_checkpoint"].update({
        "checkpoint_id": CHECKPOINT,
        "expected_branch": "main",
        "expected_head": None,
        "next_action": NEXT_ACTION,
    })
    profile["parallel_checkpoints"] = [{
        "checkpoint_id": CHECKPOINT,
        "authority_ref": APPROVAL_REF,
        "next_action": NEXT_ACTION,
    }]
    review_gates = profile["human_gates"].get("review_gates", [])
    profile["human_gates"]["review_gates"] = [item for item in review_gates if item.get("unit_id") != REVIEW_UNIT]
    goal.update({"current_checkpoint": CHECKPOINT, "proposed_amendments": [], "parallel_checkpoints": [CHECKPOINT]})
    goal.setdefault("active_amendments", []).append(APPROVAL_REF)

    nonce = response_sha[:12]
    replace_json("contracts/milestone-002.json", milestone, nonce)
    replace_json("records/project-control-profile.json", profile, nonce)
    replace_json("records/long-term-goal.json", goal, nonce)
    append_evidence({
        "record_id": "EVID-0190",
        "type": "m2_radar_apply_orbit_correction_input_resolution_diagnostic_001_owner_approval",
        "verified_at_utc": args.approved_at_utc,
        "status": "pass_exact_attested_approval_implementation_publication_only",
        "claim": "The owner approved the exact bounded read-only input-resolution diagnostic. Only implementation, synthetic no-content tests, and public CI are released now; ArcPy, external inputs, final preflight, and the one diagnostic process remain gated.",
        "approval_ref": APPROVAL_REF,
        "approval_sha256": approval_sha,
        "review_reconciliation_ref": REVIEW_RECONCILIATION_REF,
        "review_reconciliation_sha256": reconciliation_sha,
        "assertions": {
            "human_decision_count": 1,
            "attestation": True,
            "implementation_authorized": True,
            "public_ci_authorized": True,
            "final_no_content_preflight_released": False,
            "diagnostic_process_started": False,
            "arcpy_imported": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "apply_orbit_correction_invoked": False,
            "geoprocessing_invoked": False,
            "new_radar_attempt_created": False,
            "scientific_result_established": False,
            "current_checkpoint": CHECKPOINT,
        },
        "next_action": NEXT_ACTION,
    })
    print(json.dumps({
        "status": "pass_exact_approval_activated",
        "response_ref": response_ref,
        "response_sha256": response_sha,
        "approval_sha256": approval_sha,
        "activation_sha256": sha256_file(ROOT / ACTIVATION_REF),
        "checkpoint": CHECKPOINT,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
