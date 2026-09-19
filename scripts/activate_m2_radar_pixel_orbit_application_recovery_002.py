#!/usr/bin/env python3
"""Lock the exact owner approval and activate radar recovery-002 implementation."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from m2_radar_pixel_orbit_application_001_core import canonical_bytes, sha256_file


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-pixel-orbit-application-recovery-002"
PROPOSAL_REF = "contracts/milestone-002-radar-pixel-orbit-application-recovery-002-proposal.json"
PROPOSAL_SHA256 = "86366bca8681bbe90dfdd19d6c5b676e490e6dd87c8e04c2900e9fb1df4b29ca"
BUNDLE_REF = f"reviews/{PREFIX}/review-bundle.json"
BUNDLE_SHA256 = "e699dfc3c4f7dd5ca697581cf4a299c66128fda7691473d65749681e3dfc211c"
REVIEW_CONTRACT_REF = f"reviews/{PREFIX}/review-contract.json"
REVIEW_CONTRACT_SHA256 = "aca2ab770a5fa0af826a6c81e1ebf2eeade5afe8bfbab787809df124e47ff8e3"
REVIEW_PUBLICATION_REF = f"records/readiness/{PREFIX}-review-publication-gate.json"
REVIEW_RECONCILIATION_REF = f"records/source-gates/{PREFIX}-review-reconciliation.json"
APPROVAL_REF = f"records/source-gates/{PREFIX}-approval.json"
ACTIVATION_REF = f"records/readiness/{PREFIX}-approval-activation.json"
RUNTIME_CONTRACT_REF = f"config/qa/{PREFIX}-contract.json"
BASE_CONTRACT_REF = "config/qa/m2-radar-pixel-orbit-application-001-contract.json"
RECOVERY_001_CONTRACT_REF = "config/qa/m2-radar-pixel-orbit-application-recovery-001-contract.json"
REVIEW_UNIT = "M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-002-REVIEW"
IMPLEMENTATION_UNIT = "M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-002-IMPLEMENTATION"
EXECUTION_UNIT = "M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-002-EXECUTION"
CHECKPOINT = IMPLEMENTATION_UNIT
ATTEMPT_ID = "radar-pixel-orbit-application-recovery-002-real-001"
ATTEMPT_ROOT = (
    r"C:\Projects\Active\nepal-2026-before-after-map-data\derived\radar-pixel-orbit-application-recovery-002"
    r"\radar-pixel-orbit-application-recovery-002-real-001"
)
NEXT_ACTION = (
    "Implement and validate only the approved stage-evidenced recovery-002 wrapper, portable synthetic tests, and "
    "installed ArcGIS-runtime synthetic test, then require successful public default-branch CI. Do not run the final "
    "no-content preflight, access project data or external custody, or start the fresh attempt before that public gate."
)
RAW_APPROVAL = (
    "I approve M2 radar pixel and orbit application recovery-002 review bundle "
    "`e699dfc3c4f7dd5ca697581cf4a299c66128fda7691473d65749681e3dfc211c` and proposal "
    "`86366bca8681bbe90dfdd19d6c5b676e490e6dd87c8e04c2900e9fb1df4b29ca`. I authorize only the bounded recovery-002 "
    "implementation, portable synthetic tests, installed ArcGIS-runtime synthetic test using disposable inputs, public-CI gate, "
    "final no-content preflight, and only on every gate passing at most one fresh single-process "
    "`radar-pixel-orbit-application-recovery-002-real-001` attempt over exact M1-SRC-001 through M1-SRC-006 and the two frozen "
    "radar routes in their stated fixed order, stopping on the first failure, with exact terminal reconciliation. I understand "
    "this authorizes no reuse, resume, retry, or mutation of either consumed attempt; no automatic retry; no source, orbit, DEM, "
    "AOI, CRS, grid, mask, threshold, registration, route, or scientific-predicate substitution; and no baseline admission, change "
    "analysis, interpretation, attribution, derived-pixel publication, historical-root-cause claim, radar-recovery-readiness claim, "
    "or scientific publication. I attest this is my completed decision."
)


def load(ref: str) -> dict[str, Any]:
    value = json.loads((ROOT / ref).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {ref}")
    return value


def replace_json(ref: str, value: object, nonce: str) -> None:
    target = ROOT / ref
    temporary = target.with_name(f".{target.name}.{nonce}.tmp")
    with temporary.open("xb") as stream:
        stream.write(canonical_bytes(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, target)


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
    if sha256_file(ROOT / PROPOSAL_REF) != PROPOSAL_SHA256:
        raise SystemExit("proposal identity drift")
    if sha256_file(ROOT / BUNDLE_REF) != BUNDLE_SHA256:
        raise SystemExit("review-bundle identity drift")
    if sha256_file(ROOT / REVIEW_CONTRACT_REF) != REVIEW_CONTRACT_SHA256:
        raise SystemExit("review-contract identity drift")
    proposal = load(PROPOSAL_REF)
    protected = proposal.get("protected_public_evidence", [])
    drift = [
        item.get("path", "<missing>")
        for item in protected
        if not isinstance(item, dict)
        or not isinstance(item.get("path"), str)
        or not (ROOT / item["path"]).is_file()
        or sha256_file(ROOT / item["path"]) != item.get("sha256")
    ]
    if drift:
        raise SystemExit("protected evidence identity drift: " + ", ".join(drift))
    publication = load(REVIEW_PUBLICATION_REF)
    if (
        publication.get("status") != "pass_public_default_branch_ci_zero_decision_owner_review_ready"
        or publication.get("public_ci_conclusion") != "success"
        or publication.get("commit_sha") != "2de376ecd1ed4c226cd5fa2d2e39b763aa5c9438"
        or publication.get("bindings", {}).get("review_bundle_sha256") != BUNDLE_SHA256
    ):
        raise SystemExit("review publication gate is not the exact pass")

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
            "item_id": "M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-002",
            "decision": "approve",
            "rationale": "Exact bounded stage-evidenced recovery-002 path and one conditional fresh attempt approved.",
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
        "receipt_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-002-REVIEW-CONTRACT-LOCK-001",
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
            "bounded_implementation",
            "portable_synthetic_tests",
            "installed_arcgis_runtime_synthetic_test",
            "public_ci",
            "conditional_final_no_content_preflight",
            "conditional_one_fresh_attempt",
            "terminal_reconciliation",
        ],
        "item_decisions": [{
            "item_id": "M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-002",
            "decision": "approve",
        }],
    }
    reconciliation_bytes = canonical_bytes(reconciliation)
    reconciliation_sha = hashlib.sha256(reconciliation_bytes).hexdigest()
    approval = {
        "schema_version": "1.0",
        "approval_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-002-APPROVAL",
        "status": "approved_bounded_stage_evidenced_recovery_and_one_conditional_fresh_attempt",
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
        "protected_public_evidence": copy.deepcopy(protected),
        "reviewed_does_not_authorize_now": copy.deepcopy(proposal["does_not_authorize_now"]),
        "human_decisions_fabricated": False,
    }
    approval_bytes = canonical_bytes(approval)
    approval_sha = hashlib.sha256(approval_bytes).hexdigest()
    activation = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-002-APPROVAL-ACTIVATION",
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
            "bounded_recovery_implementation": True,
            "portable_synthetic_tests": True,
            "installed_arcgis_runtime_synthetic_test": True,
            "public_ci": True,
            "final_no_content_preflight": False,
            "fresh_attempt_execution": False,
            "project_data_or_external_custody_access": False,
            "radar_processing": False,
            "baseline_or_change_analysis": False,
            "attribution": False,
            "scientific_publication": False,
        },
        "assertions": {
            "fresh_attempt_process_started": False,
            "arcpy_invoked": False,
            "network_request_performed": False,
            "credential_value_read": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "consumed_attempt_reused_or_retried": False,
            "historical_root_cause_established": False,
            "radar_recovery_readiness_established": False,
            "scientific_result_established": False,
        },
    }
    exact = proposal["exact_recovery_contract"]
    recovery_001 = load(RECOVERY_001_CONTRACT_REF)
    runtime_contract = {
        "schema_version": "1.0",
        "contract_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-002",
        "status": "approved_implementation_publication_pending",
        "authority": {
            "approval_ref": APPROVAL_REF,
            "approval_sha256": approval_sha,
            "activation_ref": ACTIVATION_REF,
            "proposal_ref": PROPOSAL_REF,
            "proposal_sha256": PROPOSAL_SHA256,
            "review_bundle_ref": BUNDLE_REF,
            "review_bundle_sha256": BUNDLE_SHA256,
            "review_reconciliation_ref": REVIEW_RECONCILIATION_REF,
            "review_reconciliation_sha256": reconciliation_sha,
        },
        "base_contract_ref": BASE_CONTRACT_REF,
        "base_contract_sha256": sha256_file(ROOT / BASE_CONTRACT_REF),
        "recovery_001_contract_ref": RECOVERY_001_CONTRACT_REF,
        "recovery_001_contract_sha256": sha256_file(ROOT / RECOVERY_001_CONTRACT_REF),
        "fixed_source_order": copy.deepcopy(exact["fixed_source_order"]),
        "fixed_route_order": copy.deepcopy(exact["fixed_route_order"]),
        "source_to_orbit": copy.deepcopy(recovery_001["source_to_orbit"]),
        "inventory_comparison": copy.deepcopy(recovery_001["inventory_comparison"]),
        "attempt": {
            "attempt_id": ATTEMPT_ID,
            "consumed_attempt_ids": copy.deepcopy(exact["consumed_attempt_ids"]),
            "maximum_final_preflights": 1,
            "maximum_real_attempts": 1,
            "maximum_orbit_application_attempts_per_source": 1,
            "maximum_qa_processing_attempts_per_source": 1,
            "maximum_route_qa_attempts_per_pair": 1,
            "process_count": 1,
            "automatic_retry_authorized": False,
            "stop_on_first_failure": True,
            "external_attempt_root": ATTEMPT_ROOT,
            "minimum_free_space_bytes": 64_424_509_440,
            "collision_policy": "fail",
        },
        "stage_order": copy.deepcopy(exact["stage_order"]),
        "receipt_durability": copy.deepcopy(exact["receipt_durability"]),
        "execution_boundary": {
            "external_data_root": r"C:\Projects\Active\nepal-2026-before-after-map-data",
            "source_materializations": "read_only_inventory_before_after",
            "orbit_custody": "read_only_hash_before_after",
            "dem_custody": "read_only_hash_before_after",
            "derived_outputs": "append_only_exact_attempt_root",
            "network_requests": "prohibited",
            "authentication": "prohibited",
            "source_overwrite": "prohibited",
            "output_overwrite": "prohibited",
            "automatic_retry": "prohibited",
        },
        "claim_boundary": {
            "historical_root_cause_claim_allowed": False,
            "radar_recovery_readiness_claim_allowed": False,
            "baseline_admission_authorized": False,
            "change_analysis_authorized": False,
            "interpretation_authorized": False,
            "attribution_authorized": False,
            "derived_pixel_publication_authorized": False,
            "scientific_publication_authorized": False,
        },
    }

    outputs = {
        response_ref: response_bytes,
        lock_ref: lock_bytes,
        REVIEW_RECONCILIATION_REF: reconciliation_bytes,
        APPROVAL_REF: approval_bytes,
        ACTIVATION_REF: canonical_bytes(activation),
        RUNTIME_CONTRACT_REF: canonical_bytes(runtime_contract),
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
        raise SystemExit("recovery-002 implementation units already exist")
    for ref, payload in outputs.items():
        target = ROOT / ref
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
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
        "new_attempt_authorized": True,
        "approval_sha256": approval_sha,
        "review_reconciliation_sha256": reconciliation_sha,
    })
    review["exit_condition_delta"] = {
        "expected": [],
        "observed": ["one exact attested owner approval"],
        "decision_value": "enables_dependency",
        "rationale": "Implementation and public CI are released now; project-data access and the fresh attempt remain conditional.",
    }
    milestone["units"].extend([
        {
            "id": IMPLEMENTATION_UNIT,
            "purpose": "Implement and publicly validate the exact stage-evidenced recovery wrapper without project-data access or a fresh attempt.",
            "depends_on": [REVIEW_UNIT],
            "action_class": "routine_qa",
            "human_gate": False,
            "status": "in_progress",
            "inputs": [APPROVAL_REF, PROPOSAL_REF, REVIEW_RECONCILIATION_REF],
            "outputs": [
                RUNTIME_CONTRACT_REF,
                f"scripts/{PREFIX.replace('-', '_')}_core.py",
                f"scripts/run_{PREFIX.replace('-', '_')}.py",
                f"scripts/validate_{PREFIX.replace('-', '_')}_arcgis.py",
                f"tests/test_{PREFIX.replace('-', '_')}.py",
            ],
            "gates": {
                "portable_synthetic_tests": "pending",
                "installed_arcgis_runtime_test": "pending",
                "repository_validation": "pending",
                "public_ci": "pending",
                "project_data_content_read": False,
                "fresh_attempt_process_started": False,
            },
            "exit_condition_delta": {
                "expected": ["successful public default-branch CI"],
                "observed": [],
                "decision_value": "pending",
                "rationale": "Implementation does not itself release preflight or the fresh attempt.",
            },
            "next_dependency": EXECUTION_UNIT,
        },
        {
            "id": EXECUTION_UNIT,
            "purpose": "After public CI and final no-content preflight, run at most one exact fresh recovery attempt and reconcile it.",
            "depends_on": [IMPLEMENTATION_UNIT],
            "action_class": "data_processing",
            "human_gate": False,
            "status": "planned",
            "inputs": [APPROVAL_REF, RUNTIME_CONTRACT_REF],
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
                "expected": ["terminal evidence for one consumed fresh attempt"],
                "observed": [],
                "decision_value": "pending",
                "rationale": "Pass or block consumes the one attempt and releases no baseline or change analysis.",
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
        "project_data_content_read_authorized_only_after_public_gate_and_final_preflight": True,
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
    nonce = args.approved_at_utc.replace(":", "").replace("-", "")
    replace_json("contracts/milestone-002.json", milestone, nonce)
    replace_json("records/project-control-profile.json", profile, nonce)
    replace_json("records/long-term-goal.json", goal, nonce)
    evidence = {
        "record_id": "EVID-0183",
        "type": "m2_radar_pixel_orbit_application_recovery_002_owner_approval_activation",
        "verified_at_utc": args.approved_at_utc,
        "status": "pass_exact_approval_implementation_publication_only",
        "claim": "The owner approved the exact public recovery-002 packet. Only bounded implementation, portable and installed ArcGIS-runtime synthetic tests, and public CI are released now; project-data access, final preflight, and the fresh attempt remain blocked behind the public gate.",
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
            "fresh_attempt_released": False,
            "fresh_attempt_process_started": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "consumed_attempt_reused_or_retried": False,
            "arcpy_invoked": False,
            "radar_processing_executed": False,
            "historical_root_cause_established": False,
            "radar_recovery_readiness_established": False,
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
        "runtime_contract_sha256": sha256_file(ROOT / RUNTIME_CONTRACT_REF),
        "checkpoint": CHECKPOINT,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
