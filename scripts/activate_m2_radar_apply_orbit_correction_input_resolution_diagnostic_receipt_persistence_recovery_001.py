#!/usr/bin/env python3
"""Lock the exact owner approval and activate diagnostic receipt recovery-001."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-apply-orbit-correction-input-resolution-diagnostic-receipt-persistence-recovery-001"
SOURCE_PREFIX = "m2-radar-apply-orbit-correction-input-resolution-diagnostic-001"
PROPOSAL_REF = f"contracts/milestone-002-{PREFIX.removeprefix('m2-')}-proposal.json"
PROPOSAL_SHA256 = "607c1ba872f91226afc5b3b1c2ce69f111979d20d2f6c611dac9b496f5ed1a28"
BUNDLE_REF = f"reviews/{PREFIX}/review-bundle.json"
BUNDLE_SHA256 = "006ffc48f7344f43b073404163962dbe6f821273b21f4c80a448a11777deb847"
REVIEW_CONTRACT_REF = f"reviews/{PREFIX}/review-contract.json"
REVIEW_CONTRACT_SHA256 = "2e39f323b0bc615ac36f9be2f0a6103454acbedfa8a689d996243a169dca5615"
REVIEW_PUBLICATION_REF = f"records/readiness/{PREFIX}-review-publication-gate.json"
REVIEW_PUBLICATION_RECONCILIATION_REF = f"records/readiness/{PREFIX}-review-publication-reconciliation.json"
REVIEW_RECONCILIATION_REF = f"records/source-gates/{PREFIX}-review-reconciliation.json"
APPROVAL_REF = f"records/source-gates/{PREFIX}-approval.json"
ACTIVATION_REF = f"records/readiness/{PREFIX}-approval-activation.json"
RECOVERY_CONTRACT_REF = f"config/qa/{PREFIX}-contract.json"
SOURCE_CONTRACT_REF = f"config/qa/{SOURCE_PREFIX}-contract.json"
SOURCE_TERMINAL_REF = f"records/processing/{SOURCE_PREFIX}-terminal.json"
SOURCE_CLEANUP_REF = f"records/processing/{SOURCE_PREFIX}-cleanup.json"
REVIEW_UNIT = "M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-REVIEW"
IMPLEMENTATION_UNIT = "M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-IMPLEMENTATION"
EXECUTION_UNIT = "M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-EXECUTION"
ATTEMPT_ID = "radar-apply-orbit-correction-input-resolution-diagnostic-receipt-persistence-recovery-001-real-001"
CHECKPOINT = IMPLEMENTATION_UNIT
NEXT_ACTION = (
    "Implement and validate only the approved diagnostic receipt-durability correction, portable synthetic tests, and installed "
    "ArcGIS-runtime disposable synthetic test, then require successful public default-branch CI. Do not run the final no-content "
    "preflight or inspect project data or external custody before the implementation and execution-gate publications pass."
)
RAW_APPROVAL = (
    "I approve M2 radar ApplyOrbitCorrection input-resolution diagnostic receipt-persistence recovery-001 review bundle "
    "`006ffc48f7344f43b073404163962dbe6f821273b21f4c80a448a11777deb847` and proposal "
    "`607c1ba872f91226afc5b3b1c2ce69f111979d20d2f6c611dac9b496f5ed1a28`. I authorize only the bounded receipt-durability "
    "implementation, portable synthetic tests, installed ArcGIS-runtime synthetic test using disposable inputs, public-CI and "
    "execution-gate publication, final no-content preflight, and at most one fresh distinct read-only "
    "`radar-apply-orbit-correction-input-resolution-diagnostic-receipt-persistence-recovery-001-real-001` process over the exact "
    "frozen SAFE directory, `manifest.safe`, and M2-ORB-001 EOF, with no automatic retry. I understand the consumed diagnostic "
    "remains terminal and cannot be resumed, reused, or retried; its two zero-byte reserved receipts remain immutable; and this "
    "authorizes no reconstruction, source or path substitution, ApplyOrbitCorrection or other geoprocessing, radar processing, "
    "baseline or change analysis, interpretation, attribution, derived-pixel publication, historical-root-cause claim, "
    "radar-recovery-readiness claim, or scientific publication. I attest this is my completed decision."
)
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
PROTECTED = {
    SOURCE_CONTRACT_REF: "e390c0918947eaac49df025bf1b3c6c0ee35804c04404b12a42597dc4411e724",
    f"scripts/{SOURCE_PREFIX.replace('-', '_')}_core.py": "9d6ca7be8514b62d088eea3e1648b002ae40f25555ab620ca298efa37b7d5129",
    f"scripts/run_{SOURCE_PREFIX.replace('-', '_')}.py": "34239fb9669559f1668887c89b08db5f7e213cfea3132ef0eeb3dffebd041d8f",
    f"tests/test_{SOURCE_PREFIX.replace('-', '_')}.py": "3741af9396bf25b3fc22d35560e92ad1cea90cf964a4ba99384e6fe78014ca1d",
    SOURCE_TERMINAL_REF: EMPTY_SHA256,
    SOURCE_CLEANUP_REF: EMPTY_SHA256,
}


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


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
        **PROTECTED,
    }
    drift = [ref for ref, expected in exact.items() if not (ROOT / ref).is_file() or sha256(ref) != expected]
    if drift:
        raise SystemExit("review or protected input identity drift: " + ", ".join(drift))
    if (ROOT / SOURCE_TERMINAL_REF).stat().st_size or (ROOT / SOURCE_CLEANUP_REF).stat().st_size:
        raise SystemExit("consumed reserved receipt size drift")
    publication = load(REVIEW_PUBLICATION_REF)
    publication_reconciliation = load(REVIEW_PUBLICATION_RECONCILIATION_REF)
    if (
        publication.get("status") != "pass_public_default_branch_ci_zero_decision_owner_review_ready"
        or publication.get("public_ci_conclusion") != "success"
        or publication.get("bindings", {}).get("review_bundle_sha256") != BUNDLE_SHA256
        or publication_reconciliation.get("status") != "pass_public_gate_owner_review_ready"
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
            "item_id": "M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001",
            "decision": "approve",
            "rationale": "Exact bounded receipt-durability implementation and one conditional distinct read-only process approved.",
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
        "receipt_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-REVIEW-CONTRACT-LOCK-001",
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
        "authority_ref": APPROVAL_REF,
        "authorized_next_actions": [
            "bounded_receipt_durability_implementation",
            "portable_synthetic_tests",
            "installed_arcgis_runtime_synthetic_test",
            "public_ci_and_execution_gate_publication",
            "conditional_final_preflight_and_one_distinct_process",
        ],
        "item_decisions": [{"item_id": response["responses"][0]["item_id"], "decision": "approve"}],
    }
    reconciliation_bytes = canonical_bytes(reconciliation)
    reconciliation_sha = hashlib.sha256(reconciliation_bytes).hexdigest()
    proposal = load(PROPOSAL_REF)
    source_contract = load(SOURCE_CONTRACT_REF)
    approval = {
        "schema_version": "1.0",
        "approval_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-APPROVAL",
        "status": "approved_bounded_receipt_durability_recovery_and_one_conditional_distinct_read_only_process",
        "approved_at_utc": args.approved_at_utc,
        "review_id": f"{PREFIX}-review",
        "review_bundle_manifest_sha256": BUNDLE_SHA256,
        "proposal_ref": PROPOSAL_REF,
        "proposal_sha256": PROPOSAL_SHA256,
        "review_contract_ref": REVIEW_CONTRACT_REF,
        "review_contract_sha256": REVIEW_CONTRACT_SHA256,
        "review_publication_gate_ref": REVIEW_PUBLICATION_REF,
        "review_publication_gate_sha256": sha256(REVIEW_PUBLICATION_REF),
        "review_reconciliation_ref": REVIEW_RECONCILIATION_REF,
        "review_reconciliation_sha256": reconciliation_sha,
        "locked_response_sha256": response_sha,
        "lock_receipt_sha256": lock_sha,
        "human_decision_count": 1,
        "decision_counts": {"approve": 1, "revise": 0, "defer": 0},
        "attestation": True,
        "authorized_bounded_actions": copy.deepcopy(proposal["proposed_exact_changes"]),
        "exact_recovery_contract": copy.deepcopy(proposal["exact_recovery_contract"]),
        "protected_public_implementation": copy.deepcopy(proposal["protected_public_implementation"]),
        "raw_attested_statement": RAW_APPROVAL,
        "human_decisions_fabricated": False,
    }
    approval_bytes = canonical_bytes(approval)
    approval_sha = hashlib.sha256(approval_bytes).hexdigest()
    activation = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-APPROVAL-ACTIVATION",
        "activated_at_utc": args.approved_at_utc,
        "status": "pass_exact_approval_activated_implementation_publication_only",
        "bindings": {
            "approval_ref": APPROVAL_REF,
            "approval_sha256": approval_sha,
            "reconciliation_sha256": reconciliation_sha,
            "proposal_sha256": PROPOSAL_SHA256,
            "review_bundle_sha256": BUNDLE_SHA256,
            "review_publication_gate_sha256": sha256(REVIEW_PUBLICATION_REF),
        },
        "released_now": {
            "bounded_receipt_durability_implementation": True,
            "portable_synthetic_tests": True,
            "installed_arcgis_runtime_synthetic_test": True,
            "public_ci": True,
            "execution_gate_publication": True,
            "final_no_content_preflight": False,
            "distinct_read_only_process": False,
            "project_data_or_external_custody_access": False,
            "arcpy_production_invocation": False,
            "apply_orbit_correction_or_geoprocessing": False,
            "radar_processing": False,
            "baseline_or_change_analysis": False,
            "scientific_publication": False,
        },
        "assertions": {
            "new_process_started": False,
            "arcpy_production_invoked": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "consumed_diagnostic_reused_or_retried": False,
            "consumed_reserved_receipts_mutated": False,
            "geoprocessing_invoked": False,
            "scientific_result_established": False,
        },
    }
    activation_bytes = canonical_bytes(activation)
    activation_sha = hashlib.sha256(activation_bytes).hexdigest()
    recovery_contract = {
        "schema_version": "1.0",
        "contract_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-CONTRACT",
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
        "attempt": {
            "attempt_id": ATTEMPT_ID,
            "maximum_processes": 1,
            "automatic_retry": False,
            "distinct_from_consumed_attempt": True,
            "mode": "read_only_single_process_no_geoprocessing",
        },
        "exact_inputs": copy.deepcopy(source_contract["exact_inputs"]),
        "fixed_check_order": copy.deepcopy(source_contract["fixed_check_order"]),
        "arcgis_read_only_calls": copy.deepcopy(source_contract["arcgis_read_only_calls"]),
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
        "protected_consumed_receipts": {
            "terminal_ref": SOURCE_TERMINAL_REF,
            "terminal_sha256": EMPTY_SHA256,
            "cleanup_ref": SOURCE_CLEANUP_REF,
            "cleanup_sha256": EMPTY_SHA256,
            "required_bytes_each": 0,
        },
        "limits": copy.deepcopy(source_contract["limits"]),
        "result_semantics": copy.deepcopy(proposal["exact_recovery_contract"]["result_semantics"]),
    }

    outputs = {
        response_ref: response_bytes,
        lock_ref: lock_bytes,
        REVIEW_RECONCILIATION_REF: reconciliation_bytes,
        APPROVAL_REF: approval_bytes,
        ACTIVATION_REF: activation_bytes,
        RECOVERY_CONTRACT_REF: canonical_bytes(recovery_contract),
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
        raise SystemExit("recovery implementation units already exist")
    for ref, payload in outputs.items():
        write_new(ref, payload)

    review.update({"status": "complete", "disposition": "pass"})
    review["outputs"].extend([response_ref, lock_ref, REVIEW_RECONCILIATION_REF, APPROVAL_REF, ACTIVATION_REF])
    review["gates"].update({
        "human_decision_count": 1,
        "attestation": True,
        "review_response_open": False,
        "owner_proposal_approval_authorized": True,
        "implementation_authorized": True,
        "new_diagnostic_process_authorized": True,
        "approval_sha256": approval_sha,
        "review_reconciliation_sha256": reconciliation_sha,
    })
    review["exit_condition_delta"] = {
        "expected": [],
        "observed": ["one exact attested owner approval"],
        "decision_value": "enables_dependency",
        "rationale": "Implementation and its public gates are released now; the distinct process remains conditional on all gates and final preflight.",
    }
    milestone["units"].extend([
        {
            "id": IMPLEMENTATION_UNIT,
            "purpose": "Implement and publicly validate the exact receipt-durability recovery without production ArcPy or external-input access.",
            "depends_on": [REVIEW_UNIT],
            "action_class": "routine_qa",
            "human_gate": False,
            "status": "in_progress",
            "inputs": [APPROVAL_REF, PROPOSAL_REF, REVIEW_RECONCILIATION_REF],
            "outputs": [
                RECOVERY_CONTRACT_REF,
                f"scripts/{PREFIX.replace('-', '_')}_core.py",
                f"scripts/run_{PREFIX.replace('-', '_')}.py",
                f"scripts/validate_{PREFIX.replace('-', '_')}_arcgis.py",
                f"tests/test_{PREFIX.replace('-', '_')}.py",
            ],
            "gates": {
                "portable_synthetic_tests": "pending",
                "installed_arcgis_runtime_synthetic_test": "pending",
                "repository_validation": "pending",
                "public_ci": "pending",
                "production_arcpy_invoked": False,
                "external_inputs_accessed": False,
                "distinct_process_started": False,
            },
            "exit_condition_delta": {
                "expected": ["successful public default-branch CI and execution-gate publication"],
                "observed": [],
                "decision_value": "pending",
                "rationale": "Implementation does not itself release the distinct process.",
            },
            "next_dependency": EXECUTION_UNIT,
        },
        {
            "id": EXECUTION_UNIT,
            "purpose": "Run the one distinct read-only process only after both public gates and one final no-content preflight.",
            "depends_on": [IMPLEMENTATION_UNIT],
            "action_class": "data_processing",
            "human_gate": False,
            "status": "planned",
            "inputs": [APPROVAL_REF, RECOVERY_CONTRACT_REF],
            "outputs": [
                f"records/readiness/{PREFIX}-final-preflight.json",
                f"records/processing/{PREFIX}-terminal-reconciliation.json",
                f"records/processing/{PREFIX}-outcome-reconciliation.json",
            ],
            "gates": {
                "public_ci": "pending",
                "execution_gate_publication": "pending",
                "final_no_content_preflight": "pending",
                "maximum_processes": 1,
                "processes_started": 0,
                "apply_orbit_correction_calls": 0,
                "geoprocessing_calls": 0,
            },
            "exit_condition_delta": {
                "expected": ["terminal read-only diagnostic and cleanup evidence"],
                "observed": [],
                "decision_value": "pending",
                "rationale": "Either PASS or BLOCK is diagnostic only and consumes the one distinct process.",
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
        "attempt_id": ATTEMPT_ID,
        "maximum_processes": 1,
        "automatic_retry_authorized": False,
        "apply_orbit_correction_authorized": False,
        "geoprocessing_authorized": False,
    }
    milestone.setdefault("authority", {}).setdefault("amendments", []).append(copy.deepcopy(amendment))
    milestone.setdefault("scope", {}).setdefault("active_amendments", []).append(APPROVAL_REF)
    profile["authority"].setdefault("amendments", []).append(copy.deepcopy(amendment))
    profile.setdefault("control_surfaces", {})["proposed_amendments"] = []
    profile["control_surfaces"].setdefault("activated_amendments", []).append(APPROVAL_REF)
    profile["current_checkpoint"].update({
        "checkpoint_id": CHECKPOINT,
        "expected_branch": "main",
        "expected_head": None,
        "next_action": NEXT_ACTION,
    })
    profile["parallel_checkpoints"] = [{"checkpoint_id": CHECKPOINT, "authority_ref": APPROVAL_REF, "next_action": NEXT_ACTION}]
    review_gates = profile.get("human_gates", {}).get("review_gates", [])
    profile["human_gates"]["review_gates"] = [item for item in review_gates if item.get("unit_id") != REVIEW_UNIT]
    goal.setdefault("active_amendments", []).append(APPROVAL_REF)
    goal.update({"current_checkpoint": CHECKPOINT, "proposed_amendments": [], "parallel_checkpoints": [CHECKPOINT]})
    nonce = response_sha[:12]
    replace_json("contracts/milestone-002.json", milestone, nonce)
    replace_json("records/project-control-profile.json", profile, nonce)
    replace_json("records/long-term-goal.json", goal, nonce)
    evidence = {
        "record_id": "EVID-0199",
        "type": "m2_radar_apply_orbit_correction_input_resolution_diagnostic_receipt_persistence_recovery_001_owner_approval_activation",
        "verified_at_utc": args.approved_at_utc,
        "status": "pass_exact_approval_implementation_publication_only",
        "claim": "The owner approved the exact public receipt-persistence recovery packet. Only bounded implementation, portable and installed ArcGIS-runtime synthetic tests, public CI, and execution-gate publication are released now; the distinct process remains gated.",
        "approval_ref": APPROVAL_REF,
        "approval_sha256": approval_sha,
        "activation_ref": ACTIVATION_REF,
        "activation_sha256": sha256(ACTIVATION_REF),
        "locked_response_sha256": response_sha,
        "review_reconciliation_sha256": reconciliation_sha,
        "assertions": {
            "human_decision_count": 1,
            "attestation": True,
            "implementation_authorized": True,
            "public_ci_authorized": True,
            "final_no_content_preflight_released": False,
            "distinct_process_released": False,
            "distinct_process_started": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "consumed_diagnostic_reused_or_retried": False,
            "consumed_reserved_receipts_mutated": False,
            "geoprocessing_invoked": False,
            "scientific_result_established": False,
            "current_checkpoint": CHECKPOINT,
        },
        "next_action": NEXT_ACTION,
    }
    with (ROOT / "records/evidence-ledger.jsonl").open("ab", buffering=0) as stream:
        stream.write(json.dumps(evidence, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n")
        os.fsync(stream.fileno())
    print(json.dumps({
        "status": "pass_exact_approval_activated",
        "response_ref": response_ref,
        "response_sha256": response_sha,
        "approval_sha256": approval_sha,
        "activation_sha256": sha256(ACTIVATION_REF),
        "checkpoint": CHECKPOINT,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
