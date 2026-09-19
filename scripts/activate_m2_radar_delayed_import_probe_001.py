#!/usr/bin/env python3
"""Lock the exact owner approval and activate delayed-import probe implementation."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from m2_radar_delayed_import_probe_001_core import (
    ATTEMPT_ID,
    FILE_COUNT,
    STAGE_ORDER,
    TOTAL_LOGICAL_BYTES,
    canonical_bytes,
    sha256_file,
    write_new_json,
)


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-delayed-import-probe-001"
PROPOSAL_REF = "contracts/milestone-002-radar-delayed-import-probe-001-proposal.json"
PROPOSAL_SHA256 = "7d3474eeed2dd679ca1f755d1ebcf6542b977b87418b40f4b40204ae5ac02de9"
BUNDLE_REF = f"reviews/{PREFIX}/review-bundle.json"
BUNDLE_SHA256 = "1084597b5db7b20e24ad241c5550a58623571747d5ef7d37a086298830bd45e5"
REVIEW_CONTRACT_REF = f"reviews/{PREFIX}/review-contract.json"
REVIEW_CONTRACT_SHA256 = "204e4d95d196bf2c08beb83aba78a295a89af26f51e3d5513b72ea158ae8118a"
REVIEW_PUBLICATION_REF = f"records/readiness/{PREFIX}-review-publication-gate.json"
REVIEW_RECONCILIATION_REF = f"records/source-gates/{PREFIX}-review-reconciliation.json"
APPROVAL_REF = f"records/source-gates/{PREFIX}-approval.json"
ACTIVATION_REF = f"records/readiness/{PREFIX}-approval-activation.json"
PROBE_CONTRACT_REF = f"config/qa/{PREFIX}-contract.json"
REVIEW_UNIT = "M2-RADAR-DELAYED-IMPORT-PROBE-001-REVIEW"
IMPLEMENTATION_UNIT = "M2-RADAR-DELAYED-IMPORT-PROBE-001-IMPLEMENTATION"
EXECUTION_UNIT = "M2-RADAR-DELAYED-IMPORT-PROBE-001-EXECUTION"
CHECKPOINT = IMPLEMENTATION_UNIT
NEXT_ACTION = (
    "Implement and validate only the approved disposable delayed-import probe and portable synthetic tests, then require "
    "successful public default-branch CI. Do not create the corpus or import ArcPy before that public gate and the final no-content preflight."
)
RAW_APPROVAL = (
    "I approve M2 radar delayed-import probe-001 review bundle `1084597b5db7b20e24ad241c5550a58623571747d5ef7d37a086298830bd45e5` "
    "and proposal `7d3474eeed2dd679ca1f755d1ebcf6542b977b87418b40f4b40204ae5ac02de9`. I authorize only the bounded probe-only "
    "implementation, portable synthetic tests, public-CI gate, one final no-content preflight, and only on pass one fresh single-process "
    "`radar-delayed-import-probe-001-real-001` execution using 156 locally generated disposable sparse files totaling exactly 10,367,157,634 "
    "logical bytes, the full stable-order hash scan before ArcPy import, durable stage markers, two tiny disposable rasters, one "
    "`MosaicToNewRaster` operation, extension check-in, terminal receipt, cleanup record, and exact reconciliation stated in the reviewed "
    "proposal. I understand recovery-001 remains terminal and cannot be reused or retried, and that project-data or external-custody access, "
    "network or credential actions, installation or UAC actions, radar processing, baseline or change analysis, interpretation, attribution, "
    "publication, and any historical-root-cause or recovery-readiness claim remain unauthorized. I attest this is my completed decision."
)


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
    }
    if any(not (ROOT / ref).is_file() or sha256_file(ROOT / ref) != expected for ref, expected in exact.items()):
        raise SystemExit("review input identity drift")
    publication = load(REVIEW_PUBLICATION_REF)
    if publication.get("status") != "pass_public_default_branch_ci_zero_decision_review_ready" or publication.get("public_ci_conclusion") != "success":
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
            "item_id": "M2-RADAR-DELAYED-IMPORT-PROBE-001",
            "decision": "approve",
            "rationale": "Exact bounded disposable diagnostic approved with every reviewed prohibition retained.",
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
        "receipt_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-001-REVIEW-CONTRACT-LOCK-001",
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
        "item_decisions": [{"item_id": "M2-RADAR-DELAYED-IMPORT-PROBE-001", "decision": "approve"}],
    }
    reconciliation_bytes = canonical_bytes(reconciliation)
    reconciliation_sha = hashlib.sha256(reconciliation_bytes).hexdigest()
    proposal = load(PROPOSAL_REF)
    approval = {
        "schema_version": "1.0",
        "approval_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-001-APPROVAL",
        "status": "approved_bounded_disposable_delayed_import_probe",
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
        "authorized_bounded_actions": copy.deepcopy(proposal["proposed_bounded_actions"]),
        "exact_probe_contract": copy.deepcopy(proposal["exact_probe_contract"]),
        "limits": copy.deepcopy(proposal["limits"]),
        "frozen_without_change": copy.deepcopy(proposal["frozen_without_change"]),
        "does_not_authorize": copy.deepcopy(proposal["does_not_authorize"]),
        "human_decisions_fabricated": False,
    }
    approval_bytes = canonical_bytes(approval)
    approval_sha = hashlib.sha256(approval_bytes).hexdigest()
    activation = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-001-APPROVAL-ACTIVATION",
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
            "bounded_probe_implementation": True,
            "portable_synthetic_tests": True,
            "public_ci": True,
            "final_no_content_preflight": False,
            "live_probe_execution": False,
            "project_data_content_read": False,
            "external_custody_access": False,
            "radar_processing": False,
            "baseline_or_change_analysis": False,
            "scientific_publication": False,
        },
        "assertions": {
            "probe_process_started": False,
            "disposable_corpus_created": False,
            "arcpy_imported": False,
            "network_request_performed": False,
            "credential_value_read": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "recovery_attempt_reused_or_retried": False,
            "scientific_result_established": False,
        },
    }
    probe_contract = {
        "schema_version": "1.0",
        "contract_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-001-CONTRACT",
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
            "external_local_path_class": "local_appdata_probe_specific_outside_git_and_external_custody",
        },
        "corpus": {
            "content_class": "deterministic_disposable_zero_bytes",
            "file_count": FILE_COUNT,
            "total_logical_bytes": TOTAL_LOGICAL_BYTES,
            "sparse_regular_files_required": True,
            "stable_name_order_hash_before_arcpy_import": True,
        },
        "stage_order": list(STAGE_ORDER),
        "geoprocessing": {
            "raster_count": 2,
            "raster_shape": [2, 2],
            "operation": "arcpy.management.MosaicToNewRaster",
            "mosaic_count": 1,
            "project_crs_or_aoi_used": False,
        },
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
            "recovery_retry_or_reuse": True,
            "radar_processing": True,
            "baseline_or_change_analysis": True,
            "interpretation_or_attribution": True,
            "publication": True,
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
        raise SystemExit("probe implementation units already exist")

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
        "implementation_authorized": True,
        "probe_execution_authorized": True,
        "approval_sha256": approval_sha,
        "review_reconciliation_sha256": reconciliation_sha,
    })
    review["exit_condition_delta"] = {
        "expected": [],
        "observed": ["one exact attested approval"],
        "decision_value": "enables_dependency",
        "rationale": "Implementation and public CI are released now; the one live probe remains conditional on final preflight.",
    }
    milestone["units"].extend([
        {
            "id": IMPLEMENTATION_UNIT,
            "purpose": "Implement and publicly validate the exact disposable delayed-import probe without invoking ArcPy or creating the corpus.",
            "depends_on": [REVIEW_UNIT],
            "action_class": "routine_qa",
            "human_gate": False,
            "status": "in_progress",
            "inputs": [APPROVAL_REF, PROPOSAL_REF, REVIEW_RECONCILIATION_REF],
            "outputs": [PROBE_CONTRACT_REF, "scripts/m2_radar_delayed_import_probe_001_core.py", "scripts/run_m2_radar_delayed_import_probe_001.py", "tests/test_m2_radar_delayed_import_probe_001.py"],
            "gates": {"portable_synthetic_tests": "pending", "repository_validation": "pending", "public_ci": "pending", "arcpy_invoked": False, "probe_process_started": False},
            "exit_condition_delta": {"expected": ["public CI success"], "observed": [], "decision_value": "pending", "rationale": "Implementation does not itself release the live probe."},
            "next_dependency": EXECUTION_UNIT,
        },
        {
            "id": EXECUTION_UNIT,
            "purpose": "Run the one approved probe only after public CI and a final no-content preflight, then reconcile its diagnostic-only result.",
            "depends_on": [IMPLEMENTATION_UNIT],
            "action_class": "data_processing",
            "human_gate": False,
            "status": "planned",
            "inputs": [APPROVAL_REF, PROBE_CONTRACT_REF],
            "outputs": ["records/readiness/m2-radar-delayed-import-probe-001-final-preflight.json", "records/processing/m2-radar-delayed-import-probe-001-outcome-reconciliation.json"],
            "gates": {"public_ci": "pending", "final_no_content_preflight": "pending", "maximum_live_attempts": 1, "live_attempts_started": 0},
            "exit_condition_delta": {"expected": ["terminal diagnostic receipt and cleanup record"], "observed": [], "decision_value": "pending", "rationale": "Either PASS or BLOCK is diagnostic only."},
            "next_dependency": None,
        },
    ])
    milestone["handoff"].update({"current_checkpoint": CHECKPOINT, "next_action": NEXT_ACTION, "parallel_checkpoint": CHECKPOINT, "parallel_next_action": NEXT_ACTION})

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
    profile["authority"].setdefault("amendments", []).append(amendment)
    profile.setdefault("control_surfaces", {})["proposed_amendments"] = []
    profile["control_surfaces"].setdefault("activated_amendments", []).append(APPROVAL_REF)
    profile["current_checkpoint"].update({"checkpoint_id": CHECKPOINT, "expected_branch": "main", "expected_head": None, "next_action": NEXT_ACTION})
    profile["parallel_checkpoints"] = [{"checkpoint_id": CHECKPOINT, "authority_ref": APPROVAL_REF, "next_action": NEXT_ACTION}]
    review_gates = profile["human_gates"].get("review_gates", [])
    profile["human_gates"]["review_gates"] = [item for item in review_gates if item.get("unit_id") != REVIEW_UNIT]

    goal.update({"current_checkpoint": CHECKPOINT, "proposed_amendments": [], "parallel_checkpoints": [CHECKPOINT]})
    goal.setdefault("active_amendments", []).append(APPROVAL_REF)

    nonce = response_sha[:12]
    replace_json("contracts/milestone-002.json", milestone, nonce)
    replace_json("records/project-control-profile.json", profile, nonce)
    replace_json("records/long-term-goal.json", goal, nonce)
    print(json.dumps({"status": "pass_exact_approval_activated", "response_ref": response_ref, "response_sha256": response_sha, "approval_sha256": approval_sha, "checkpoint": CHECKPOINT}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
