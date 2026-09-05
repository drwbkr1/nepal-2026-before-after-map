#!/usr/bin/env python3
"""Activate the exact approved M2 radar-first control-path decision."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BUNDLE_REF = "reviews/m2-radar-first-path-001/review-bundle.json"
BUNDLE_SHA256 = "5a5bd80f724841f9558ad5ff966ed0d49222419f7310b345492172e4639421ad"
PROPOSAL_REF = "contracts/milestone-002-radar-first-path-001-proposal.json"
PROPOSAL_SHA256 = "ae2ddfa153a86b7acf7f8ec500690713d5ced9a8ddd58f5655d831e1eb282c77"
REVIEW_CONTRACT_REF = "reviews/m2-radar-first-path-001/review-contract.json"
REVIEW_CONTRACT_SHA256 = "872920524101856d3bcd1b964963ba9ad89118dc56a6be65849ef2432b226382"
RECONCILIATION_REF = "records/source-gates/m2-radar-first-path-001-review-reconciliation.json"
APPROVAL_REF = "records/source-gates/m2-radar-first-path-001-approval.json"
ACTIVATION_REF = "records/readiness/m2-radar-first-path-001-activation.json"
OPTICAL_REF = "records/readiness/m2-optical-route-disposition-001.json"
RADAR_REF = "records/readiness/m2-radar-source-readiness-001.json"
STALE_REF = "records/readiness/m2-orbit-recovery-001-stale-evidence.json"


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(ref: str) -> str:
    return sha256_bytes((ROOT / ref).read_bytes())


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


def build_outputs(activated_at_utc: str) -> dict[str, bytes]:
    if sha256_file(BUNDLE_REF) != BUNDLE_SHA256:
        raise ValueError("review bundle identity drift")
    if sha256_file(PROPOSAL_REF) != PROPOSAL_SHA256:
        raise ValueError("proposal identity drift")
    if sha256_file(REVIEW_CONTRACT_REF) != REVIEW_CONTRACT_SHA256:
        raise ValueError("review contract identity drift")
    proposal = load(PROPOSAL_REF)
    reconciliation = load(RECONCILIATION_REF)
    if reconciliation.get("status") != "reconciled_exact_human_response":
        raise ValueError("review response is not reconciled")
    if reconciliation.get("contract_sha256") != REVIEW_CONTRACT_SHA256:
        raise ValueError("review contract binding drift")
    if reconciliation.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}:
        raise ValueError("review reconciliation is not one exact approval")
    if reconciliation.get("human_decision_count") != 1:
        raise ValueError("review reconciliation human decision count differs")
    if reconciliation.get("human_decisions_fabricated") is not False:
        raise ValueError("review reconciliation reports a fabricated decision")

    optical_real_ref = "records/readiness/m2-optical-pixel-real-001-reconciliation.json"
    optical_recovery_ref = "records/readiness/m2-optical-pixel-recovery-001-reconciliation.json"
    optical_real = load(optical_real_ref)
    optical_recovery = load(optical_recovery_ref)
    if optical_real.get("status") != "invalid_terminal_real_001_no_retry_released":
        raise ValueError("optical real-001 terminal identity drift")
    if optical_recovery.get("status") != "terminal_block_recovery_001_no_retry_released":
        raise ValueError("optical recovery-001 terminal identity drift")

    transfer_ref = "records/acquisition/sentinel-continuation-001-postsuccess-reconciliation.json"
    materialization_ref = "records/acquisition/sentinel-materialization-reconciliation-002.json"
    full_header_ref = "records/readiness/m2-full-header-readiness-reconciliation.json"
    radar_header_ref = "records/readiness/radar-input/m2-s1-input-readiness-real-003.json"
    orbit_approval_ref = "records/source-gates/m2-orbit-amendment-approval.json"
    radar_header = load(radar_header_ref)
    radar_source_ids = sorted(radar_header.get("products", {}))
    if radar_header.get("status") != "pass_full_radar_header_readiness_only":
        raise ValueError("radar header readiness is not passing")
    if radar_source_ids != [f"M1-SRC-{index:03d}" for index in range(1, 7)]:
        raise ValueError("radar source cohort drift")
    if radar_header.get("decision", {}).get("ready_source_count") != 6:
        raise ValueError("radar ready source count drift")
    if radar_header.get("activity", {}).get("real_product_pixel_values_examined") is not False:
        raise ValueError("radar pixels were unexpectedly examined")

    approval = {
        "schema_version": "1.0",
        "approval_id": "NEPAL-M2-RADAR-FIRST-PATH-001-APPROVAL",
        "status": "approved_control_route_split_and_corrected_review_preparation_only",
        "approved_at_utc": activated_at_utc,
        "review_id": "m2-radar-first-path-001-review",
        "review_bundle_manifest_sha256": BUNDLE_SHA256,
        "proposal_ref": PROPOSAL_REF,
        "proposal_sha256": PROPOSAL_SHA256,
        "review_contract_ref": REVIEW_CONTRACT_REF,
        "review_contract_sha256": REVIEW_CONTRACT_SHA256,
        "review_reconciliation_ref": RECONCILIATION_REF,
        "review_reconciliation_sha256": sha256_file(RECONCILIATION_REF),
        "locked_response_sha256": reconciliation["response_sha256"],
        "lock_receipt_sha256": reconciliation["receipt_sha256"],
        "human_decision_count": 1,
        "decision_counts": {"approve": 1, "revise": 0, "defer": 0},
        "authorized_next_actions": proposal["proposed_bounded_actions"],
        "does_not_authorize": proposal["does_not_authorize"],
        "human_decisions_fabricated": False,
    }
    approval_bytes = canonical_bytes(approval)

    optical = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-OPTICAL-ROUTE-DISPOSITION-001",
        "recorded_at_utc": activated_at_utc,
        "status": "terminal_block_preserved_no_alternate_route_authorized",
        "bindings": {
            "real_001_ref": optical_real_ref,
            "real_001_sha256": sha256_file(optical_real_ref),
            "recovery_001_ref": optical_recovery_ref,
            "recovery_001_sha256": sha256_file(optical_recovery_ref),
            "radar_first_approval_ref": APPROVAL_REF,
            "radar_first_approval_sha256": sha256_bytes(approval_bytes),
        },
        "route": {
            "real_001_disposition": "INVALID",
            "recovery_001_disposition": "BLOCK",
            "recovery_authority_consumed": True,
            "retry_authorized": False,
            "threshold_change_authorized": False,
            "alternate_date_or_source_authorized": False,
        },
        "assertions": {
            "terminal_results_reclassified": False,
            "pixel_processing_performed_during_activation": False,
            "scientific_admission_authorized": False,
        },
    }
    optical_bytes = canonical_bytes(optical)

    radar = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-SOURCE-READINESS-001",
        "recorded_at_utc": activated_at_utc,
        "status": "pass_six_source_custody_materialization_and_header_readiness_only",
        "source_ids": radar_source_ids,
        "bindings": {
            "sentinel_transfer_reconciliation_ref": transfer_ref,
            "sentinel_transfer_reconciliation_sha256": sha256_file(transfer_ref),
            "materialization_reconciliation_ref": materialization_ref,
            "materialization_reconciliation_sha256": sha256_file(materialization_ref),
            "full_header_reconciliation_ref": full_header_ref,
            "full_header_reconciliation_sha256": sha256_file(full_header_ref),
            "radar_header_receipt_ref": radar_header_ref,
            "radar_header_receipt_sha256": sha256_file(radar_header_ref),
            "orbit_amendment_approval_ref": orbit_approval_ref,
            "orbit_amendment_approval_sha256": sha256_file(orbit_approval_ref),
            "radar_first_approval_ref": APPROVAL_REF,
            "radar_first_approval_sha256": sha256_bytes(approval_bytes),
        },
        "assertions": {
            "promoted_and_container_verified_source_count": 6,
            "materialized_source_count": 6,
            "header_ready_source_count": 6,
            "complete_before_after_radar_pair": True,
            "measurement_pixels_decoded": False,
            "external_orbit_applied": False,
            "terrain_correction_performed": False,
            "baseline_established": False,
            "scientific_admission_authorized": False,
        },
        "next_gates": [
            "M2-ORBIT-RECOVERY-002-REVIEW",
            "M2-DEM-VERTICAL-DATUM-REVIEW",
            "M2-DEM-TERRAIN-RESULT-REVIEW",
            "future separately reviewed radar pixel readiness",
        ],
    }
    radar_bytes = canonical_bytes(radar)

    old_proposal_ref = "contracts/milestone-002-orbit-recovery-proposal.json"
    old_bundle_ref = "reviews/m2-orbit-recovery/review-bundle.json"
    old_contract_ref = "reviews/m2-orbit-recovery/review-contract.json"
    old_blank_ref = "reviews/m2-orbit-recovery/blank-response.json"
    stale = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ORBIT-RECOVERY-001-STALE-EVIDENCE",
        "recorded_at_utc": activated_at_utc,
        "status": "stale_unapproved_preserved_not_actionable",
        "reason": "The old unapproved packet requires aggregate M2-VERIFY and conflicts with the approved independent radar route.",
        "bindings": {
            "proposal_ref": old_proposal_ref,
            "proposal_sha256": sha256_file(old_proposal_ref),
            "review_bundle_ref": old_bundle_ref,
            "review_bundle_sha256": sha256_file(old_bundle_ref),
            "review_contract_ref": old_contract_ref,
            "review_contract_sha256": sha256_file(old_contract_ref),
            "blank_response_ref": old_blank_ref,
            "blank_response_sha256": sha256_file(old_blank_ref),
        },
        "assertions": {
            "old_files_deleted_or_modified": False,
            "old_human_decision_count": 0,
            "old_packet_activated": False,
            "orbit_recovery_authorized_by_stale_packet": False,
        },
    }
    stale_bytes = canonical_bytes(stale)

    activation = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-RADAR-FIRST-PATH-001-ACTIVATION",
        "activated_at_utc": activated_at_utc,
        "status": "pass_control_route_split_and_corrected_review_preparation_only",
        "bindings": {
            "approval_ref": APPROVAL_REF,
            "approval_sha256": sha256_bytes(approval_bytes),
            "proposal_ref": PROPOSAL_REF,
            "proposal_sha256": PROPOSAL_SHA256,
            "review_bundle_ref": BUNDLE_REF,
            "review_bundle_sha256": BUNDLE_SHA256,
            "review_contract_ref": REVIEW_CONTRACT_REF,
            "review_contract_sha256": REVIEW_CONTRACT_SHA256,
            "review_reconciliation_ref": RECONCILIATION_REF,
            "review_reconciliation_sha256": sha256_file(RECONCILIATION_REF),
            "optical_route_disposition_ref": OPTICAL_REF,
            "optical_route_disposition_sha256": sha256_bytes(optical_bytes),
            "radar_source_readiness_ref": RADAR_REF,
            "radar_source_readiness_sha256": sha256_bytes(radar_bytes),
            "stale_orbit_packet_ref": STALE_REF,
            "stale_orbit_packet_sha256": sha256_bytes(stale_bytes),
        },
        "released_now": {
            "control_graph_route_split": True,
            "old_orbit_packet_stale_evidence_classification": True,
            "corrected_zero_decision_orbit_review_preparation": True,
            "optical_retry_or_alternate_search": False,
            "dem_action": False,
            "orbit_access_or_download": False,
            "radar_pixel_decoding": False,
            "baseline_or_change_analysis": False,
            "scientific_publication": False,
        },
        "assertions": {
            "network_requests_performed": False,
            "authentication_performed": False,
            "credential_values_read_or_recorded": False,
            "external_data_mutated": False,
            "real_product_pixels_examined": False,
        },
    }
    return {
        APPROVAL_REF: approval_bytes,
        OPTICAL_REF: optical_bytes,
        RADAR_REF: radar_bytes,
        STALE_REF: stale_bytes,
        ACTIVATION_REF: canonical_bytes(activation),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activated-at-utc", required=True)
    args = parser.parse_args()
    if not args.activated_at_utc.endswith("Z"):
        raise SystemExit("activated time must be UTC")
    outputs = build_outputs(args.activated_at_utc)
    collisions = [ref for ref in outputs if (ROOT / ref).exists()]
    if collisions:
        raise SystemExit("refusing output collision: " + ", ".join(collisions))
    for ref, payload in outputs.items():
        write_new(ref, payload)
    print(json.dumps({"status": "activated_control_only", "outputs": list(outputs)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
