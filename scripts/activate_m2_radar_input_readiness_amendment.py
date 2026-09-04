#!/usr/bin/env python3
"""Activate the exact reconciled one-field radar readiness amendment."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BUNDLE_REF = "reviews/m2-radar-input-readiness-amendment/review-bundle.json"
BUNDLE_SHA256 = "831df5d5aae06862514667ad861c815154085fa3c546039e60f517d38ee442ff"
PROPOSAL_REF = "contracts/milestone-002-radar-input-readiness-amendment-proposal.json"
PROPOSAL_SHA256 = "ebdcb763afd99ea23090c9bd83fd9e9cb6cb8dfbb2b5fed60edb80f1fa61c731"
FAILED_CONTRACT_REF = "config/qa/radar-input-readiness-contract.json"
FAILED_CONTRACT_SHA256 = "ad478b8abd4e4a47c8d16012fffc2b67770681538bddc23b500ce5b32b17428a"
FAILED_RECEIPT_REF = "records/readiness/radar-input/m2-s1-input-readiness-real-001.json"
FAILED_RECEIPT_SHA256 = "feab3645709df16306c81dae959a8693925a7c6f919f2a1e414cf3765c3a5b0c"
FAILED_RECONCILIATION_REF = "records/surface-receipts/radar-input-readiness-real-reconciliation.json"
FAILED_RECONCILIATION_SHA256 = "5e4f703b938f9adaf10a6f37ec5195d1e1fc426197ffa1fa6a712ba0cb4de0a6"
SOURCE_GATE_REF = "records/source-gates/m2-radar-input-label-specification-source-gate.json"
SOURCE_GATE_SHA256 = "0bf61ef4d72444bcba3bd753fe15511cdebc87288d0d4dfeda9a9bbaeaeb2daf"
REVIEW_CONTRACT_REF = "reviews/m2-radar-input-readiness-amendment/review-contract.json"
REVIEW_RECONCILIATION_REF = "records/source-gates/m2-radar-input-readiness-amendment-review-reconciliation.json"
APPROVAL_REF = "records/source-gates/m2-radar-input-readiness-amendment-approval.json"
AMENDED_CONTRACT_REF = "config/qa/radar-input-readiness-contract-amendment-001.json"
ACTIVATION_REF = "records/readiness/radar-input/m2-radar-input-readiness-amendment-activation.json"
CORE_REF = "scripts/radar_input_readiness_core_amendment_001.py"
RUNNER_REF = "scripts/inspect_radar_inputs_arcgis_amendment_001.py"
ADAPTER_REF = "scripts/validate_radar_input_readiness_arcgis_amendment_001.py"


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(relative: str) -> str:
    return sha256_bytes((ROOT / relative).read_bytes())


def load(relative: str) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {relative}")
    return value


def write_new(relative: str, payload: bytes) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()


def build_outputs(activated_at_utc: str) -> dict[str, bytes]:
    expected_hashes = {
        BUNDLE_REF: BUNDLE_SHA256,
        PROPOSAL_REF: PROPOSAL_SHA256,
        FAILED_CONTRACT_REF: FAILED_CONTRACT_SHA256,
        FAILED_RECEIPT_REF: FAILED_RECEIPT_SHA256,
        FAILED_RECONCILIATION_REF: FAILED_RECONCILIATION_SHA256,
        SOURCE_GATE_REF: SOURCE_GATE_SHA256,
    }
    for relative, expected in expected_hashes.items():
        if sha256_file(relative) != expected:
            raise ValueError(f"immutable input hash drift: {relative}")

    proposal = load(PROPOSAL_REF)
    reconciliation = load(REVIEW_RECONCILIATION_REF)
    if reconciliation.get("status") != "reconciled_exact_human_response":
        raise ValueError("review response is not reconciled")
    if reconciliation.get("contract_sha256") != sha256_file(REVIEW_CONTRACT_REF):
        raise ValueError("review reconciliation contract binding drift")
    if reconciliation.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}:
        raise ValueError("review reconciliation is not one exact approval")
    if reconciliation.get("human_decisions_fabricated") is not False:
        raise ValueError("review reconciliation reports a fabricated decision")

    approval = {
        "schema_version": "1.0",
        "approval_id": "NEPAL-M2-RADAR-INPUT-READINESS-AMENDMENT-APPROVAL-001",
        "status": "approved_exact_bounded_post_observation_correction",
        "approved_at_utc": activated_at_utc,
        "review_id": "m2-radar-input-readiness-amendment-review-001",
        "review_bundle_id": "m2-radar-input-readiness-amendment-review-bundle-001",
        "review_bundle_manifest_sha256": BUNDLE_SHA256,
        "amendment_proposal_ref": PROPOSAL_REF,
        "amendment_proposal_sha256": PROPOSAL_SHA256,
        "review_reconciliation_ref": REVIEW_RECONCILIATION_REF,
        "review_reconciliation_sha256": sha256_file(REVIEW_RECONCILIATION_REF),
        "locked_response_sha256": reconciliation["response_sha256"],
        "lock_receipt_sha256": reconciliation["receipt_sha256"],
        "human_decision_count": 1,
        "decision_counts": {"approve": 1, "revise": 0, "defer": 0},
        "exact_correction": {
            "field": "metadata_checks.pixel_value",
            "from": "AMPLITUDE",
            "to": "Detected",
            "post_observation": True,
        },
        "authorized_next_actions": copy.deepcopy(proposal["bounded_actions_if_approved"]),
        "does_not_authorize": copy.deepcopy(proposal["explicitly_not_authorized"]),
        "human_decisions_fabricated": False,
    }
    approval_bytes = canonical_bytes(approval)
    approval_sha256 = sha256_bytes(approval_bytes)

    original = load(FAILED_CONTRACT_REF)
    amended = copy.deepcopy(original)
    amended["contract_version"] = "1.1"
    amended["contract_id"] = "NEPAL-S1-MATERIALIZED-INPUT-READINESS-002"
    amended["created_at_utc"] = activated_at_utc
    amended["status"] = "active_amendment_001_exact_three_pre_event_sources"
    amended["inputs"].update(
        {
            "failed_contract_ref": FAILED_CONTRACT_REF,
            "failed_contract_sha256": FAILED_CONTRACT_SHA256,
            "failed_real_receipt_ref": FAILED_RECEIPT_REF,
            "failed_real_receipt_sha256": FAILED_RECEIPT_SHA256,
            "failed_result_reconciliation_ref": FAILED_RECONCILIATION_REF,
            "failed_result_reconciliation_sha256": FAILED_RECONCILIATION_SHA256,
            "amendment_proposal_ref": PROPOSAL_REF,
            "amendment_proposal_sha256": PROPOSAL_SHA256,
            "amendment_approval_ref": APPROVAL_REF,
            "amendment_approval_sha256": approval_sha256,
            "official_source_gate_ref": SOURCE_GATE_REF,
            "official_source_gate_sha256": SOURCE_GATE_SHA256,
            "review_bundle_ref": BUNDLE_REF,
            "review_bundle_sha256": BUNDLE_SHA256,
            "review_reconciliation_ref": REVIEW_RECONCILIATION_REF,
            "review_reconciliation_sha256": sha256_file(REVIEW_RECONCILIATION_REF),
            "core_ref": CORE_REF,
            "core_sha256": sha256_file(CORE_REF),
            "runner_ref": RUNNER_REF,
            "runner_sha256": sha256_file(RUNNER_REF),
            "arcgis_adapter_ref": ADAPTER_REF,
            "arcgis_adapter_sha256": sha256_file(ADAPTER_REF),
        }
    )
    amended["authority"] = {
        **amended["authority"],
        "authority_ref": APPROVAL_REF,
        "amendment_approval_sha256": approval_sha256,
        "post_observation_correction": True,
    }
    amended["metadata_checks"]["pixel_value"] = "Detected"
    amended["amendment"] = {
        "proposal_ref": PROPOSAL_REF,
        "proposal_sha256": PROPOSAL_SHA256,
        "approval_ref": APPROVAL_REF,
        "approval_sha256": approval_sha256,
        "source_gate_ref": SOURCE_GATE_REF,
        "source_gate_sha256": SOURCE_GATE_SHA256,
        "only_observed_data_semantic_change": "metadata_checks.pixel_value: AMPLITUDE -> Detected",
        "original_real_001_status": "block_preserved_unchanged",
        "real_002_maximum_invocations": 1,
    }
    amended["limitations"].append(
        "The Detected label correction follows observation of that value in real-001; real-002 is confirmatory and is not blind or independent."
    )
    amended_bytes = canonical_bytes(amended)
    amended_sha256 = sha256_bytes(amended_bytes)

    activation = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-RADAR-INPUT-READINESS-AMENDMENT-ACTIVATION-001",
        "activated_at_utc": activated_at_utc,
        "status": "pass_exact_bounded_amendment_activated_publication_pending",
        "bindings": {
            "approval_ref": APPROVAL_REF,
            "approval_sha256": approval_sha256,
            "amended_contract_ref": AMENDED_CONTRACT_REF,
            "amended_contract_sha256": amended_sha256,
            "failed_contract_ref": FAILED_CONTRACT_REF,
            "failed_contract_sha256": FAILED_CONTRACT_SHA256,
            "failed_real_receipt_ref": FAILED_RECEIPT_REF,
            "failed_real_receipt_sha256": FAILED_RECEIPT_SHA256,
            "failed_result_reconciliation_ref": FAILED_RECONCILIATION_REF,
            "failed_result_reconciliation_sha256": FAILED_RECONCILIATION_SHA256,
        },
        "assertions": {
            "exact_owner_approval_reconciled": True,
            "one_field_semantic_correction": "metadata_checks.pixel_value: AMPLITUDE -> Detected",
            "original_contract_receipt_and_reconciliation_preserved": True,
            "real_002_executed": False,
            "network_requests_performed": False,
            "external_custody_accessed": False,
            "pixel_values_examined": False,
            "baseline_processing_released": False,
            "scientific_action_released": False,
        },
        "next_gate": "local_and_synthetic_validation_then_public_ci_before_real_002",
    }
    return {
        APPROVAL_REF: approval_bytes,
        AMENDED_CONTRACT_REF: amended_bytes,
        ACTIVATION_REF: canonical_bytes(activation),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activated-at-utc", required=True)
    args = parser.parse_args()
    outputs = build_outputs(args.activated_at_utc)
    collisions = [relative for relative in outputs if (ROOT / relative).exists()]
    if collisions:
        raise SystemExit("refusing output collision: " + ", ".join(collisions))
    for relative, payload in outputs.items():
        write_new(relative, payload)
    print(json.dumps({"status": "activated", "outputs": list(outputs)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
