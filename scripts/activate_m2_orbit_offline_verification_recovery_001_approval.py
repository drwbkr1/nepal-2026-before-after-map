#!/usr/bin/env python3
"""Activate the exact reconciled orbit-verification recovery-001 approval for implementation only."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BUNDLE_REF = "reviews/m2-orbit-offline-verification-recovery-001/review-bundle.json"
BUNDLE_SHA256 = "d2f0f75f40614c56bc0e62c6eecb1588f7504f50927448192673e6e403b5933f"
PROPOSAL_REF = "contracts/milestone-002-orbit-offline-verification-recovery-001-proposal.json"
PROPOSAL_SHA256 = "0be64071cfe718ca758155ff0422cfee48af342c8a560528746adc653e6a2fcf"
REVIEW_CONTRACT_REF = "reviews/m2-orbit-offline-verification-recovery-001/review-contract.json"
REVIEW_CONTRACT_SHA256 = "73ae6dd33ad0c251792414594c2688652c919358d72422eacb193f759c422b49"
RECONCILIATION_REF = "records/source-gates/m2-orbit-offline-verification-recovery-001-review-reconciliation.json"
RECONCILIATION_SHA256 = "a07e67160e592093498d44e9ec76f607837f4a7e6b25784458898fa63a8a0fe3"
APPROVAL_REF = "records/source-gates/m2-orbit-offline-verification-recovery-001-approval.json"
ACTIVATION_REF = "records/readiness/m2-orbit-offline-verification-recovery-001-approval-activation.json"
SOURCE_IDS = ["M2-ORB-001", "M2-ORB-002", "M2-ORB-003", "M2-ORB-004"]


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
    exact_hashes = {
        BUNDLE_REF: BUNDLE_SHA256,
        PROPOSAL_REF: PROPOSAL_SHA256,
        REVIEW_CONTRACT_REF: REVIEW_CONTRACT_SHA256,
        RECONCILIATION_REF: RECONCILIATION_SHA256,
    }
    for relative, expected in exact_hashes.items():
        if sha256_file(relative) != expected:
            raise ValueError(f"bound input identity drift: {relative}")
    proposal = load(PROPOSAL_REF)
    reconciliation = load(RECONCILIATION_REF)
    recovery = proposal.get("proposed_recovery", {})
    if (
        proposal.get("status") != "proposed_not_authorized"
        or recovery.get("source_ids_in_exact_order") != SOURCE_IDS
        or recovery.get("m2_orb_001_new_recovery_attempts") != 1
        or recovery.get("remaining_source_existing_attempts_per_source") != 1
        or recovery.get("stop_on_first_failure") is not True
        or recovery.get("automatic_retry_authorized") is not False
        or recovery.get("network_requests_authorized") != 0
        or recovery.get("credential_handoffs_authorized") != 0
        or recovery.get("external_custody_mutation_authorized") is not False
        or recovery.get("maximum_osv_endpoint_tolerance_seconds") != 1.0
        or reconciliation.get("status") != "reconciled_exact_human_response"
        or reconciliation.get("contract_sha256") != REVIEW_CONTRACT_SHA256
        or reconciliation.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}
        or reconciliation.get("human_decision_count") != 1
        or reconciliation.get("human_decisions_fabricated") is not False
    ):
        raise ValueError("review reconciliation is not the exact bounded approval")
    approval = {
        "schema_version": "1.0",
        "approval_id": "NEPAL-M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-APPROVAL",
        "status": "approved_exact_pre_read_receipt_reservation_recovery_only",
        "approved_at_utc": activated_at_utc,
        "review_id": "m2-orbit-offline-verification-recovery-001-review",
        "review_bundle_id": "m2-orbit-offline-verification-recovery-001-review-bundle",
        "review_bundle_manifest_sha256": BUNDLE_SHA256,
        "proposal_ref": PROPOSAL_REF,
        "proposal_sha256": PROPOSAL_SHA256,
        "review_contract_ref": REVIEW_CONTRACT_REF,
        "review_contract_sha256": REVIEW_CONTRACT_SHA256,
        "review_reconciliation_ref": RECONCILIATION_REF,
        "review_reconciliation_sha256": RECONCILIATION_SHA256,
        "locked_response_sha256": reconciliation["response_sha256"],
        "lock_receipt_sha256": reconciliation["receipt_sha256"],
        "human_decision_count": 1,
        "decision_counts": {"approve": 1, "revise": 0, "defer": 0},
        "authorized_recovery": copy.deepcopy(recovery),
        "authorized_next_actions": copy.deepcopy(proposal["approval_would_authorize"]),
        "does_not_authorize": copy.deepcopy(proposal["approval_would_not_authorize"]),
        "human_decisions_fabricated": False,
    }
    approval_bytes = canonical_bytes(approval)
    activation = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-APPROVAL-ACTIVATION",
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
            "review_reconciliation_sha256": RECONCILIATION_SHA256,
        },
        "released_now": {
            "pre_read_receipt_reservation_implementation": True,
            "synthetic_persistence_interruption_order_stop_tests": True,
            "public_ci": True,
            "final_no_content_preflight": False,
            "real_eof_read": False,
            "network_or_credential_action": False,
            "external_custody_mutation": False,
            "second_recovery_or_automatic_retry": False,
            "orbit_application": False,
            "dem_or_radar_pixel_action": False,
            "baseline_change_attribution_or_publication": False,
        },
        "assertions": {
            "network_requests_performed": False,
            "credential_values_read_or_recorded": False,
            "new_eof_content_read": False,
            "remaining_source_eof_content_read": False,
            "external_data_mutated": False,
            "recovery_attempt_started": False,
            "scientific_validation_rules_changed": False,
        },
        "next_gate": "implement and test the exact persistence-order correction, then require successful public default-branch CI before final no-content preflight or any EOF read",
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
