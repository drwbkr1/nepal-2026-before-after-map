#!/usr/bin/env python3
"""Activate the exact reconciled materialization and pixel-readiness amendment."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BUNDLE_REF = "reviews/m2-materialization-pixel-readiness/review-bundle.json"
BUNDLE_SHA256 = "8da456e9e0a0e378210b3d9b017e88990f1711da334f27b4cd3886211a97369a"
PROPOSAL_REF = "contracts/milestone-002-materialization-pixel-readiness-proposal.json"
PROPOSAL_SHA256 = "3dbbea5b16eeb297635d6487268cf8b619234fff14755668ac959f778b8e360c"
REVIEW_CONTRACT_REF = "reviews/m2-materialization-pixel-readiness/review-contract.json"
RECONCILIATION_REF = "records/source-gates/m2-materialization-pixel-readiness-review-reconciliation.json"
APPROVAL_REF = "records/source-gates/m2-materialization-pixel-readiness-approval.json"
ACTIVATION_REF = "records/readiness/m2-materialization-pixel-readiness-activation.json"


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
        os.fsync(stream.fileno())


def build_outputs(activated_at_utc: str) -> dict[str, bytes]:
    if sha256_file(BUNDLE_REF) != BUNDLE_SHA256:
        raise ValueError("review bundle identity drift")
    if sha256_file(PROPOSAL_REF) != PROPOSAL_SHA256:
        raise ValueError("proposal identity drift")
    proposal = load(PROPOSAL_REF)
    reconciliation = load(RECONCILIATION_REF)
    if reconciliation.get("status") != "reconciled_exact_human_response":
        raise ValueError("review response is not reconciled")
    if reconciliation.get("contract_sha256") != sha256_file(REVIEW_CONTRACT_REF):
        raise ValueError("review contract binding drift")
    if reconciliation.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}:
        raise ValueError("review reconciliation is not one exact approval")
    if reconciliation.get("human_decision_count") != 1:
        raise ValueError("review reconciliation human decision count differs")
    if reconciliation.get("human_decisions_fabricated") is not False:
        raise ValueError("review reconciliation reports a fabricated decision")

    stage_1 = proposal["stage_1_exact_materialization"]
    stage_2 = proposal["stage_2_full_cohort_header_readiness"]
    stage_3 = proposal["stage_3_conditional_optical_pixel_readiness"]
    approval = {
        "schema_version": "1.0",
        "approval_id": "NEPAL-M2-MATERIALIZATION-PIXEL-READINESS-APPROVAL-001",
        "status": "approved_exact_dependency_ordered_bounded_actions",
        "approved_at_utc": activated_at_utc,
        "review_id": "m2-materialization-pixel-readiness-review-001",
        "review_bundle_id": "m2-materialization-pixel-readiness-review-bundle-001",
        "review_bundle_manifest_sha256": BUNDLE_SHA256,
        "proposal_ref": PROPOSAL_REF,
        "proposal_sha256": PROPOSAL_SHA256,
        "review_reconciliation_ref": RECONCILIATION_REF,
        "review_reconciliation_sha256": sha256_file(RECONCILIATION_REF),
        "locked_response_sha256": reconciliation["response_sha256"],
        "lock_receipt_sha256": reconciliation["receipt_sha256"],
        "human_decision_count": 1,
        "decision_counts": {"approve": 1, "revise": 0, "defer": 0},
        "authorized_sequence": {
            "stage_1_source_ids_in_exact_order": copy.deepcopy(stage_1["source_order"]),
            "stage_1_attempt_ids_in_exact_order": [item["planned_attempt_id"] for item in stage_1["sources"]],
            "maximum_materialization_attempts_per_source": 1,
            "stop_materialization_on_first_failure": True,
            "stage_2_inspection_ids": [item["inspection_id"] for item in stage_2["real_inspections"]],
            "maximum_header_invocations_per_inspection": 1,
            "stage_3_attempt_id": stage_3["real_attempt_id"],
            "maximum_optical_pixel_invocations": 1,
            "stage_3_is_conditional": True,
        },
        "authorized_next_actions": [
            "dependency-ordered implementation and synthetic validation of the exact bounded controls",
            "public-CI gates before each real stage",
            "five exact one-attempt SAFE materializations in the approved order with stop on first failure",
            "one exact six-source radar and one exact two-source optical header inspection without measurement-pixel decoding",
            "one conditional optical pixel-readiness attempt for the exact pair and three approved AOIs",
            "exact evidence reconciliation and project-control updates",
        ],
        "does_not_authorize": copy.deepcopy(proposal["explicitly_not_authorized"]),
        "human_decisions_fabricated": False,
    }
    approval_bytes = canonical_bytes(approval)
    approval_sha256 = sha256_bytes(approval_bytes)
    activation = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-MATERIALIZATION-PIXEL-READINESS-ACTIVATION-001",
        "activated_at_utc": activated_at_utc,
        "status": "pass_exact_approval_activated_stage_1_publication_pending",
        "bindings": {
            "approval_ref": APPROVAL_REF,
            "approval_sha256": approval_sha256,
            "proposal_ref": PROPOSAL_REF,
            "proposal_sha256": PROPOSAL_SHA256,
            "review_bundle_ref": BUNDLE_REF,
            "review_bundle_sha256": BUNDLE_SHA256,
            "review_reconciliation_ref": RECONCILIATION_REF,
            "review_reconciliation_sha256": sha256_file(RECONCILIATION_REF),
        },
        "released_now": {
            "stage_1_control_implementation": True,
            "stage_1_synthetic_validation": True,
            "stage_1_publication": True,
            "real_materialization_before_public_ci_and_final_preflight": False,
            "real_header_inspection": False,
            "optical_pixel_readiness": False,
            "radar_measurement_pixels": False,
        },
        "assertions": {
            "network_requests_performed": False,
            "authentication_performed": False,
            "external_data_mutated": False,
            "archive_extraction_performed": False,
            "measurement_pixels_read": False,
            "baseline_or_change_analysis_released": False,
            "scientific_publication_released": False,
        },
        "next_gate": "publish and pass public CI for the exact stage-1 controls, then pass one final no-mutation preflight",
    }
    return {APPROVAL_REF: approval_bytes, ACTIVATION_REF: canonical_bytes(activation)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activated-at-utc", required=True)
    args = parser.parse_args()
    if not args.activated_at_utc.endswith("Z"):
        raise SystemExit("activated time must be UTC")
    outputs = build_outputs(args.activated_at_utc)
    collisions = [relative for relative in outputs if (ROOT / relative).exists()]
    if collisions:
        raise SystemExit("refusing output collision: " + ", ".join(collisions))
    for relative, payload in outputs.items():
        write_new(relative, payload)
    print(json.dumps({"status": "activated_stage_1_publication_pending", "outputs": list(outputs)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
