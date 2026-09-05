#!/usr/bin/env python3
"""Activate the exact reconciled optical pixel recovery-001 decision."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BUNDLE_REF = "reviews/m2-optical-pixel-recovery-001/review-bundle.json"
BUNDLE_SHA256 = "d137b8ac1d46531ae42e7944955829eb2df37985428431b39863f4a157e83ac2"
PROPOSAL_REF = "contracts/milestone-002-optical-pixel-recovery-001-proposal.json"
PROPOSAL_SHA256 = "96f0125628e894061fc5da55faff94e92e51b0385293576177c1e15bd009b3da"
REVIEW_CONTRACT_REF = "reviews/m2-optical-pixel-recovery-001/review-contract-lock-002.json"
REVIEW_CONTRACT_SHA256 = "552de54d12eca297ce94166453d697bea928a1b780803d8a111555bc29621761"
RECONCILIATION_REF = "records/source-gates/m2-optical-pixel-recovery-001-review-reconciliation.json"
APPROVAL_REF = "records/source-gates/m2-optical-pixel-recovery-001-approval.json"
ACTIVATION_REF = "records/readiness/m2-optical-pixel-recovery-001-activation.json"


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
    if sha256_file(REVIEW_CONTRACT_REF) != REVIEW_CONTRACT_SHA256:
        raise ValueError("operational review contract identity drift")
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

    recovery = proposal["exact_recovery"]
    approval = {
        "schema_version": "1.0",
        "approval_id": "NEPAL-M2-OPTICAL-PIXEL-RECOVERY-001-APPROVAL",
        "status": "approved_exact_post_observation_operational_correction_and_one_recovery",
        "approved_at_utc": activated_at_utc,
        "review_id": "m2-optical-pixel-recovery-001-review",
        "review_bundle_id": "m2-optical-pixel-recovery-001-review-bundle",
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
        "authorized_recovery": {
            "attempt_id": recovery["attempt_id"],
            "external_attempt_root": recovery["external_attempt_root"],
            "public_receipt_ref": recovery["public_receipt_ref"],
            "maximum_real_invocations": recovery["maximum_real_invocations"],
            "automatic_retry_authorized": recovery["automatic_retry_authorized"],
        },
        "authorized_next_actions": copy.deepcopy(proposal["proposed_bounded_actions"]),
        "unchanged_scientific_contract": copy.deepcopy(proposal["unchanged_scientific_contract"]),
        "does_not_authorize": copy.deepcopy(proposal["does_not_authorize"]),
        "human_decisions_fabricated": False,
    }
    approval_bytes = canonical_bytes(approval)
    approval_sha256 = sha256_bytes(approval_bytes)
    activation = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-OPTICAL-PIXEL-RECOVERY-001-ACTIVATION",
        "activated_at_utc": activated_at_utc,
        "status": "pass_exact_approval_activated_implementation_and_publication_only",
        "bindings": {
            "approval_ref": APPROVAL_REF,
            "approval_sha256": approval_sha256,
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
            "production_grid_normalization_correction": True,
            "exact_shape_portable_tests": True,
            "exact_shape_arcgis_synthetic_test": True,
            "public_ci": True,
            "final_no_pixel_preflight_before_public_ci": False,
            "real_recovery_attempt_before_public_ci_and_preflight": False,
            "real_001_reuse_or_retry": False,
            "radar_pixels": False,
            "baseline_or_change_analysis": False,
        },
        "assertions": {
            "real_001_preserved": True,
            "network_requests_performed": False,
            "authentication_performed": False,
            "external_data_mutated": False,
            "real_product_pixels_examined": False,
            "recovery_attempt_started": False,
            "scientific_publication_released": False,
        },
        "next_gate": "implement the exact correction and tests, then publish and require successful public CI before any no-pixel preflight or real recovery attempt",
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
    print(json.dumps({"status": "activated_implementation_and_publication_only", "outputs": list(outputs)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
