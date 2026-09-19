#!/usr/bin/env python3
"""Lock the exact owner approval and activate receipt-recovery-001 implementation."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from m2_radar_delayed_import_probe_receipt_recovery_001_core import (
    ATTEMPT_ID,
    EXPECTED_AGGREGATE_SHA256,
    FILE_COUNT,
    STAGE_ORDER,
    TOTAL_LOGICAL_BYTES,
    canonical_bytes,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-delayed-import-probe-receipt-recovery-001"
PROPOSAL_REF = "contracts/milestone-002-radar-delayed-import-probe-receipt-recovery-001-proposal.json"
PROPOSAL_SHA256 = "9bbe934bd1dcbe7d1b0700b83473db2ab1a130c13fa6d183d3b1a247dfe88e09"
BUNDLE_REF = f"reviews/{PREFIX}/review-bundle.json"
BUNDLE_SHA256 = "df43e0d93f1d40aa85fb1f8730cc57d596fcc4345299b0939b22f822321a9695"
REVIEW_CONTRACT_REF = f"reviews/{PREFIX}/review-contract.json"
REVIEW_CONTRACT_SHA256 = "e371ee3658993cd43112daa3e10407e66ca9739636976d921cd2d605c3f4c331"
REVIEW_PUBLICATION_REF = f"records/readiness/{PREFIX}-review-publication-gate.json"
REVIEW_RECONCILIATION_REF = f"records/source-gates/{PREFIX}-review-reconciliation.json"
APPROVAL_REF = f"records/source-gates/{PREFIX}-approval.json"
ACTIVATION_REF = f"records/readiness/{PREFIX}-approval-activation.json"
PROBE_CONTRACT_REF = f"config/qa/{PREFIX}-contract.json"
REVIEW_UNIT = "M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-REVIEW"
IMPLEMENTATION_UNIT = "M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-IMPLEMENTATION"
EXECUTION_UNIT = "M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-EXECUTION"
CHECKPOINT = IMPLEMENTATION_UNIT
NEXT_ACTION = (
    "Implement and validate only the approved receipt-durability correction, portable synthetic tests, and installed ArcGIS-runtime "
    "synthetic test, then require successful public default-branch CI. Do not create the production corpus or start the fresh attempt "
    "before the public gate and final no-content preflight."
)
RAW_APPROVAL = (
    "I approve M2 radar delayed-import probe receipt recovery-001 review bundle `df43e0d93f1d40aa85fb1f8730cc57d596fcc4345299b0939b22f822321a9695` "
    "and proposal `9bbe934bd1dcbe7d1b0700b83473db2ab1a130c13fa6d183d3b1a247dfe88e09`. I authorize only the bounded function-local timestamp "
    "correction, pre-reserved terminal and cleanup receipt identities, append-only fallback error preservation, cleanup independence, "
    "synthetic and ArcGIS-runtime tests, public-CI gate, final no-content preflight, and at most one fresh append-only "
    "`radar-delayed-import-probe-receipt-recovery-001-real-001` attempt stated in the reviewed proposal. I understand the consumed "
    "`radar-delayed-import-probe-001-real-001` remains terminal and cannot be resumed, reused, or retried, and that project-data or "
    "external-custody access, radar processing, baseline or change analysis, attribution, and scientific publication remain unauthorized. "
    "I attest this is my completed decision."
)
PROTECTED = {
    "config/qa/m2-radar-delayed-import-probe-001-contract.json": "c9bf8154bfb44cf6a76a9cdfc695c30b7e2bf2349d64ab9e8c0e922ca0b70ac0",
    "scripts/m2_radar_delayed_import_probe_001_core.py": "b15bcc4f6ec4034aa890d551f3d700977367e9f1bc7e28c69cbdd50f17588d2a",
    "scripts/run_m2_radar_delayed_import_probe_001.py": "189f59a81733e163c07d72abacf917b9e8482af871b323402a84047ec816792c",
    "tests/test_m2_radar_delayed_import_probe_001.py": "b6d01b9e18d6a0448fb53581d7ae522ca97db17ec337420ca8ccce226b0cfa02",
    "records/processing/m2-radar-delayed-import-probe-001-terminal-reconciliation.json": "90e7b9ff1fa823f9be805e1fba843e7af9dd34c313d4e5c6c75077c8aee81892",
    "records/processing/m2-radar-delayed-import-probe-001-outcome-reconciliation.json": "2fe63d80af49baa8a0c92948a3284a4b769fd1c61a10e6b32391a392f0f3cd4c",
}


def load(ref: str) -> dict[str, Any]:
    value = json.loads((ROOT / ref).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {ref}")
    return value


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
    drift = [ref for ref, expected in exact.items() if not (ROOT / ref).is_file() or sha256_file(ROOT / ref) != expected]
    if drift:
        raise SystemExit("review or protected input identity drift: " + ", ".join(drift))
    publication = load(REVIEW_PUBLICATION_REF)
    if (
        publication.get("status") != "pass_public_default_branch_ci_zero_decision_owner_review_ready"
        or publication.get("public_ci_conclusion") != "success"
        or publication.get("review_bundle_sha256") not in {None, BUNDLE_SHA256}
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
            "item_id": "M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001",
            "decision": "approve",
            "rationale": "Exact bounded receipt-durability recovery and one conditional fresh disposable attempt approved.",
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
        "receipt_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-REVIEW-CONTRACT-LOCK-001",
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
        "authorized_next_actions": ["bounded_implementation", "synthetic_tests", "arcgis_runtime_test", "public_ci"],
        "item_decisions": [{"item_id": "M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001", "decision": "approve"}],
    }
    reconciliation_bytes = canonical_bytes(reconciliation)
    reconciliation_sha = hashlib.sha256(reconciliation_bytes).hexdigest()
    proposal = load(PROPOSAL_REF)
    approval = {
        "schema_version": "1.0",
        "approval_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-APPROVAL",
        "status": "approved_bounded_receipt_recovery_and_one_conditional_fresh_probe",
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
        "authorized_bounded_actions": copy.deepcopy(proposal["proposed_exact_changes"]),
        "exact_recovery_contract": copy.deepcopy(proposal["exact_recovery_contract"]),
        "limits": copy.deepcopy(proposal["limits"]),
        "protected_public_implementation": copy.deepcopy(proposal["protected_public_implementation"]),
        "reviewed_does_not_authorize_now": copy.deepcopy(proposal["does_not_authorize_now"]),
        "human_decisions_fabricated": False,
    }
    approval_bytes = canonical_bytes(approval)
    approval_sha = hashlib.sha256(approval_bytes).hexdigest()
    activation = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-APPROVAL-ACTIVATION",
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
            "bounded_receipt_recovery_implementation": True,
            "portable_synthetic_tests": True,
            "installed_arcgis_runtime_synthetic_test": True,
            "public_ci": True,
            "final_no_content_preflight": False,
            "fresh_probe_execution": False,
            "project_data_content_read": False,
            "external_custody_access": False,
            "radar_processing": False,
            "baseline_or_change_analysis": False,
            "scientific_publication": False,
        },
        "assertions": {
            "probe_process_started": False,
            "disposable_corpus_created": False,
            "arcpy_invoked": False,
            "network_request_performed": False,
            "credential_value_read": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "consumed_probe_reused_or_retried": False,
            "scientific_result_established": False,
        },
    }
    probe_contract = {
        "schema_version": "1.0",
        "contract_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-CONTRACT",
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
        },
        "attempt": {
            "attempt_id": ATTEMPT_ID,
            "maximum_attempts": 1,
            "automatic_retry": False,
            "process_count": 1,
            "distinct_from_consumed_attempt": True,
            "external_local_path_class": "local_appdata_probe_specific_outside_git_and_external_custody",
        },
        "corpus": {
            "content_class": "deterministic_disposable_zero_bytes",
            "file_count": FILE_COUNT,
            "total_logical_bytes": TOTAL_LOGICAL_BYTES,
            "expected_stable_order_aggregate_sha256": EXPECTED_AGGREGATE_SHA256,
            "sparse_regular_files_required": True,
            "stable_name_order_hash_before_arcpy_import": True,
        },
        "receipt_durability": {
            "function_local_datetime_import": True,
            "terminal_identity_reserved_before_corpus": True,
            "cleanup_identity_reserved_before_corpus": True,
            "fallback_journal_initialized_before_corpus": True,
            "original_sanitized_exception_recorded_before_terminal_assembly": True,
            "terminal_persistence_error_appended_without_replacing_original": True,
            "cleanup_outer_finally_independent_of_terminal_serialization": True,
            "fallback_is_success_evidence": False,
        },
        "stage_order": list(STAGE_ORDER),
        "geoprocessing": copy.deepcopy(proposal["exact_recovery_contract"]["geoprocessing_unchanged"]),
        "claim_boundary": {
            "historical_root_cause_claim_allowed": False,
            "recovery_readiness_claim_allowed": False,
            "radar_processing_claim_allowed": False,
            "scientific_claim_allowed": False,
        },
        "forbidden": {
            "project_data_or_external_custody_access": True,
            "network_or_credential_action": True,
            "installation_or_uac_action": True,
            "consumed_attempt_retry_or_reuse": True,
            "radar_processing": True,
            "baseline_or_change_analysis": True,
            "interpretation_or_attribution": True,
            "scientific_publication": True,
        },
    }

    outputs = {
        response_ref: response_bytes,
        lock_ref: lock_bytes,
        REVIEW_RECONCILIATION_REF: reconciliation_bytes,
        APPROVAL_REF: approval_bytes,
        ACTIVATION_REF: canonical_bytes(activation),
        PROBE_CONTRACT_REF: canonical_bytes(probe_contract),
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
        raise SystemExit("receipt-recovery implementation units already exist")

    for ref, payload in outputs.items():
        path = ROOT / ref
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())

    review.update({"status": "complete", "disposition": "pass"})
    review["outputs"] = [response_ref, lock_ref, REVIEW_RECONCILIATION_REF, APPROVAL_REF, ACTIVATION_REF]
    review["gates"].update({
        "human_decision_count": 1,
        "attestation": True,
        "owner_proposal_approval_authorized": True,
        "implementation_authorized": True,
        "new_probe_attempt_authorized": True,
        "approval_sha256": approval_sha,
        "review_reconciliation_sha256": reconciliation_sha,
    })
    review["exit_condition_delta"] = {
        "expected": [],
        "observed": ["one exact attested owner approval"],
        "decision_value": "enables_dependency",
        "rationale": "Implementation and public CI are released now; the fresh attempt remains conditional on public CI and final preflight.",
    }
    milestone["units"].extend([
        {
            "id": IMPLEMENTATION_UNIT,
            "purpose": "Implement and publicly validate the exact receipt-durability correction without creating the production corpus or fresh attempt.",
            "depends_on": [REVIEW_UNIT],
            "action_class": "routine_qa",
            "human_gate": False,
            "status": "in_progress",
            "inputs": [APPROVAL_REF, PROPOSAL_REF, REVIEW_RECONCILIATION_REF],
            "outputs": [
                PROBE_CONTRACT_REF,
                "scripts/m2_radar_delayed_import_probe_receipt_recovery_001_core.py",
                "scripts/run_m2_radar_delayed_import_probe_receipt_recovery_001.py",
                "scripts/validate_m2_radar_delayed_import_probe_receipt_recovery_001_arcgis.py",
                "tests/test_m2_radar_delayed_import_probe_receipt_recovery_001.py",
            ],
            "gates": {
                "portable_synthetic_tests": "pending",
                "installed_arcgis_runtime_test": "pending",
                "repository_validation": "pending",
                "public_ci": "pending",
                "production_corpus_created": False,
                "fresh_probe_process_started": False,
            },
            "exit_condition_delta": {
                "expected": ["successful public default-branch CI"],
                "observed": [],
                "decision_value": "pending",
                "rationale": "Implementation does not itself release the fresh probe.",
            },
            "next_dependency": EXECUTION_UNIT,
        },
        {
            "id": EXECUTION_UNIT,
            "purpose": "Run the one fresh disposable probe only after public CI and final no-content preflight, then reconcile its diagnostic-only result.",
            "depends_on": [IMPLEMENTATION_UNIT],
            "action_class": "data_processing",
            "human_gate": False,
            "status": "planned",
            "inputs": [APPROVAL_REF, PROBE_CONTRACT_REF],
            "outputs": [
                f"records/readiness/{PREFIX}-final-preflight.json",
                f"records/processing/{PREFIX}-outcome-reconciliation.json",
            ],
            "gates": {
                "public_ci": "pending",
                "gate_state_publication": "pending",
                "final_no_content_preflight": "pending",
                "maximum_live_attempts": 1,
                "live_attempts_started": 0,
            },
            "exit_condition_delta": {
                "expected": ["terminal diagnostic evidence and cleanup disposition"],
                "observed": [],
                "decision_value": "pending",
                "rationale": "Either PASS or BLOCK is diagnostic only and consumes the one fresh attempt.",
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
        "maximum_live_attempts": 1,
        "automatic_retry_authorized": False,
        "project_data_content_read_authorized": False,
    }
    milestone.setdefault("authority", {}).setdefault("amendments", []).append(copy.deepcopy(amendment))
    milestone.setdefault("scope", {}).setdefault("active_amendments", []).append(APPROVAL_REF)
    profile["authority"].setdefault("amendments", []).append(copy.deepcopy(amendment))
    profile.setdefault("control_surfaces", {})["proposed_amendments"] = []
    profile["control_surfaces"].setdefault("activated_amendments", []).append(APPROVAL_REF)
    profile["current_checkpoint"].update({"checkpoint_id": CHECKPOINT, "expected_branch": "main", "expected_head": None, "next_action": NEXT_ACTION})
    profile["parallel_checkpoints"] = [{"checkpoint_id": CHECKPOINT, "authority_ref": APPROVAL_REF, "next_action": NEXT_ACTION}]
    review_gates = profile.get("human_gates", {}).get("review_gates", [])
    profile["human_gates"]["review_gates"] = [item for item in review_gates if item.get("unit_id") != REVIEW_UNIT]
    goal.setdefault("active_amendments", []).append(APPROVAL_REF)
    goal.update({"current_checkpoint": CHECKPOINT, "proposed_amendments": [], "parallel_checkpoints": [CHECKPOINT]})

    nonce = args.approved_at_utc.replace(":", "").replace("-", "")
    replace_json("contracts/milestone-002.json", milestone, nonce)
    replace_json("records/project-control-profile.json", profile, nonce)
    replace_json("records/long-term-goal.json", goal, nonce)
    evidence = {
        "record_id": "EVID-0175",
        "type": "m2_radar_delayed_import_probe_receipt_recovery_001_owner_approval_activation",
        "verified_at_utc": args.approved_at_utc,
        "status": "pass_exact_approval_implementation_publication_only",
        "claim": "The owner approved the exact public receipt-recovery-001 packet. Only bounded implementation, portable and installed ArcGIS-runtime synthetic tests, and public CI are released now; the production corpus and fresh attempt remain blocked behind the public gate and final preflight.",
        "approval_ref": APPROVAL_REF,
        "approval_sha256": approval_sha,
        "activation_ref": ACTIVATION_REF,
        "activation_sha256": sha256_file(ROOT / ACTIVATION_REF),
        "locked_response_sha256": response_sha,
        "review_reconciliation_sha256": reconciliation_sha,
        "assertions": {
            "human_decision_count": 1,
            "attestation": True,
            "implementation_authorized": True,
            "public_ci_authorized": True,
            "final_no_content_preflight_released": False,
            "fresh_probe_attempt_released": False,
            "production_corpus_created": False,
            "fresh_probe_process_started": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "consumed_probe_reused_or_retried": False,
            "radar_processing_executed": False,
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
        "activation_sha256": sha256_file(ROOT / ACTIVATION_REF),
        "checkpoint": CHECKPOINT,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
