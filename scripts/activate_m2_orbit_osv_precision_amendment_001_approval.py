#!/usr/bin/env python3
"""Activate one exact approved OSV precision amendment for implementation only."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BUNDLE_REF = "reviews/m2-orbit-osv-precision-amendment-001/review-bundle.json"
BUNDLE_SHA256 = "71b3eea557cbd027fecec299b8661ce555a8fa993bccd8ffaea8f525d79d01a7"
PROPOSAL_REF = "contracts/milestone-002-orbit-osv-precision-amendment-001-proposal.json"
PROPOSAL_SHA256 = "0eb9e60f3cd26365cc447eb007e28186470a778928730b055b633c5e88d344e4"
REVIEW_CONTRACT_REF = "reviews/m2-orbit-osv-precision-amendment-001/review-contract.json"
REVIEW_CONTRACT_SHA256 = "aeda5b43507f295fbc471e07c612555ebfc93a491e2ccd5b33a6c84a3d735ec0"
RECONCILIATION_REF = "records/source-gates/m2-orbit-osv-precision-amendment-001-review-reconciliation.json"
APPROVAL_REF = "records/source-gates/m2-orbit-osv-precision-amendment-001-approval.json"
ACTIVATION_REF = "records/readiness/m2-orbit-osv-precision-amendment-001-approval-activation.json"


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_file(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def load(relative: str) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {relative}")
    return value


def build_outputs(activated_at_utc: str) -> dict[str, bytes]:
    if sha256_file(BUNDLE_REF) != BUNDLE_SHA256:
        raise ValueError("review bundle identity drift")
    if sha256_file(PROPOSAL_REF) != PROPOSAL_SHA256:
        raise ValueError("proposal identity drift")
    if sha256_file(REVIEW_CONTRACT_REF) != REVIEW_CONTRACT_SHA256:
        raise ValueError("review contract identity drift")
    proposal = load(PROPOSAL_REF)
    reconciliation = load(RECONCILIATION_REF)
    if (
        reconciliation.get("status") != "reconciled_exact_human_response"
        or reconciliation.get("contract_sha256") != REVIEW_CONTRACT_SHA256
        or reconciliation.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}
        or reconciliation.get("human_decision_count") != 1
        or reconciliation.get("human_decisions_fabricated") is not False
        or proposal.get("status") != "proposed_not_authorized"
    ):
        raise ValueError("review reconciliation is not one exact approval")
    amendment = proposal["proposed_amendment"]
    approval = {
        "schema_version": "1.0",
        "approval_id": "NEPAL-M2-ORBIT-OSV-PRECISION-AMENDMENT-001-APPROVAL",
        "status": "approved_exact_one_second_endpoint_rule_and_one_local_validation",
        "approved_at_utc": activated_at_utc,
        "review_id": "m2-orbit-osv-precision-amendment-001-review",
        "review_bundle_id": "m2-orbit-osv-precision-amendment-001-review-bundle",
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
        "authorized_amendment": {
            "source_id": amendment["source_id"],
            "product_name": amendment["product_name"],
            "preserved_staged_sha256": amendment["preserved_staged_sha256"],
            "preserved_staged_size_bytes": amendment["preserved_staged_size_bytes"],
            "maximum_osv_endpoint_tolerance_seconds": amendment["maximum_osv_endpoint_tolerance_seconds"],
            "endpoint_rule": amendment["endpoint_rule"],
            "maximum_new_owner_handoffs": amendment["maximum_new_owner_handoffs"],
            "maximum_new_catalog_requests": amendment["maximum_new_catalog_requests"],
            "maximum_new_download_requests": amendment["maximum_new_download_requests"],
            "maximum_local_validation_attempts": amendment["maximum_local_validation_attempts"],
            "automatic_retry_authorized": amendment["automatic_retry_authorized"],
        },
        "authorized_next_actions": copy.deepcopy(proposal["approval_would_authorize"]),
        "does_not_authorize": copy.deepcopy(proposal["approval_would_not_authorize"]),
        "human_decisions_fabricated": False,
    }
    approval_bytes = canonical_bytes(approval)
    activation = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-OSV-PRECISION-AMENDMENT-001-APPROVAL-ACTIVATION",
        "activated_at_utc": activated_at_utc,
        "status": "pass_exact_approval_activated_implementation_and_publication_only",
        "bindings": {
            "approval_ref": APPROVAL_REF,
            "approval_sha256": hashlib.sha256(approval_bytes).hexdigest(),
            "proposal_ref": PROPOSAL_REF,
            "proposal_sha256": PROPOSAL_SHA256,
            "review_bundle_ref": BUNDLE_REF,
            "review_bundle_sha256": BUNDLE_SHA256,
            "review_contract_ref": REVIEW_CONTRACT_REF,
            "review_contract_sha256": REVIEW_CONTRACT_SHA256,
            "review_reconciliation_ref": RECONCILIATION_REF,
            "review_reconciliation_sha256": sha256_file(RECONCILIATION_REF),
        },
        "released_now": {
            "one_second_endpoint_implementation": True,
            "synthetic_tests": True,
            "public_ci": True,
            "final_no_network_preflight_before_public_ci": False,
            "local_validation_before_public_ci_and_preflight": False,
            "staged_file_promotion_before_public_ci_and_preflight": False,
            "network_or_token_action": False,
            "other_orbit_source_request": False,
            "orbit_application": False,
            "dem_or_radar_pixel_action": False,
            "baseline_or_change_analysis": False,
        },
        "assertions": {
            "network_requests_performed": False,
            "authentication_performed": False,
            "credential_values_read_or_recorded": False,
            "preserved_staged_file_read": False,
            "external_data_mutated": False,
            "orbit_payload_requested": False,
            "local_validation_started": False,
            "scientific_publication_released": False,
        },
        "next_gate": "implement and test the exact one-second rule, then require successful public CI before the no-network preflight or preserved-byte validation",
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
        path = ROOT / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    print(json.dumps({"status": "activated_implementation_and_publication_only", "outputs": list(outputs)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
