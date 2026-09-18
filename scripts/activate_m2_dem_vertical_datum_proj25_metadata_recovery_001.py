#!/usr/bin/env python3
"""Activate the exact approved PROJ25 metadata recovery through public CI only."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path(r"C:\Projects\Active\nepal-2026-before-after-map-data")
PROPOSAL_REF = "contracts/m2-dem-vertical-datum-proj25-metadata-recovery-001-proposal.json"
PROPOSAL_SHA256 = "729d36da013a9bf987486e18f7c6bac75865eda5b75dc963e8fd31ff4ddb13cd"
BUNDLE_REF = "reviews/m2-dem-vertical-datum-proj25-metadata-recovery-001/review-bundle.json"
BUNDLE_SHA256 = "10d55916113e2b9e578e5845a75886f6688c112adc3e0f4b6bbb035f8658460d"
CONTRACT_REF = "reviews/m2-dem-vertical-datum-proj25-metadata-recovery-001/review-contract.json"
CONTRACT_SHA256 = "f6aef3d7dcb9035cfd5224a07cc6888027c7003b28f013254fabb61a8ddaeb4a"
REVIEW_PUBLICATION_REF = "records/readiness/m2-dem-vertical-datum-proj25-metadata-recovery-001-review-publication-gate.json"
RESPONSE_SHA256 = "97dc8475b9b7a6892a79a1f0d519bbc32e87bea91346f5f1dec0d07432e0a1ee"
RECEIPT_SHA256 = "c1a1403fe574130588aea1ba892571fd5cde8c8a7f7d35ebe22548135cf9fccd"
LOCKED = DATA_ROOT / "private-review-responses/m2-dem-vertical-datum-proj25-metadata-recovery-001/locked"
RESPONSE = LOCKED / f"m2-dem-vertical-datum-proj25-metadata-recovery-001-review-response-{RESPONSE_SHA256[:16]}.json"
RECEIPT = LOCKED / f"m2-dem-vertical-datum-proj25-metadata-recovery-001-review-receipt-{RESPONSE_SHA256[:16]}.json"
RECONCILIATION_REF = "records/source-gates/m2-dem-vertical-datum-proj25-metadata-recovery-001-review-reconciliation.json"
RECONCILIATION_SHA256 = "17f63ff5834ce89a500f5cf1408f1bc967a7462e766b86e8f5197205eda5e9d1"
APPROVAL_REF = "records/source-gates/m2-dem-vertical-datum-proj25-metadata-recovery-001-approval.json"
ACTIVATION_REF = "records/readiness/m2-dem-vertical-datum-proj25-metadata-recovery-001-approval-activation.json"
CHECKPOINT = "M2-DEM-PROJ25-METADATA-RECOVERY-001-IMPLEMENTATION"
NEXT_ACTION = (
    "Implement and validate only the approved metadata-key interpretation correction and offline recovery controls, "
    "then require fresh public default-branch CI. Do not read or promote the preserved grid bytes, inspect DEM "
    "pixels, convert a DEM, or perform downstream processing before that public gate and a final no-content preflight."
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return value


def canonical(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def replace_json(path: Path, value: dict[str, Any], nonce: str) -> None:
    temporary = path.with_name(f".{path.name}.{nonce}.tmp")
    if temporary.exists():
        raise ValueError(f"temporary collision: {temporary}")
    with temporary.open("xb") as stream:
        stream.write(canonical(value))
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
    parser.add_argument("--activated-at-utc", required=True)
    args = parser.parse_args()
    if not args.activated_at_utc.endswith("Z"):
        raise SystemExit("activation timestamp must be UTC")

    exact = {
        ROOT / PROPOSAL_REF: PROPOSAL_SHA256,
        ROOT / BUNDLE_REF: BUNDLE_SHA256,
        ROOT / CONTRACT_REF: CONTRACT_SHA256,
        ROOT / RECONCILIATION_REF: RECONCILIATION_SHA256,
        RESPONSE: RESPONSE_SHA256,
        RECEIPT: RECEIPT_SHA256,
    }
    if any(not path.is_file() or sha(path) != expected for path, expected in exact.items()):
        raise SystemExit("approval input identity drift or missing locked response")
    publication = load(ROOT / REVIEW_PUBLICATION_REF)
    if (
        publication.get("status") != "pass_public_default_branch_ci_zero_decision_review_ready"
        or publication.get("public_ci_conclusion") != "success"
    ):
        raise SystemExit("review publication gate is not successful")
    response = load(RESPONSE)
    receipt = load(RECEIPT)
    reconciliation = load(ROOT / RECONCILIATION_REF)
    if (
        response.get("review_id") != "m2-dem-vertical-datum-proj25-metadata-recovery-001-review"
        or response.get("completed") is not True
        or response.get("reviewer", {}).get("attestation") is not True
        or len(response.get("responses", [])) != 1
        or response["responses"][0].get("item_id") != "M2-DEM-PROJ25-METADATA-RECOVERY-001"
        or response["responses"][0].get("evidence_sha256") != BUNDLE_SHA256
        or response["responses"][0].get("decision") != "approve"
        or receipt.get("response_sha256") != RESPONSE_SHA256
        or receipt.get("contract_sha256") != CONTRACT_SHA256
        or reconciliation.get("response_sha256") != RESPONSE_SHA256
        or reconciliation.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}
    ):
        raise SystemExit("locked response is not the exact attested approval")

    proposal = load(ROOT / PROPOSAL_REF)
    approval = {
        "schema_version": "1.0",
        "approval_id": "NEPAL-M2-DEM-VERTICAL-DATUM-PROJ25-METADATA-RECOVERY-001-APPROVAL",
        "status": "approved_exact_post_observation_metadata_recovery_bounded_route",
        "approved_at_utc": response["review_completed_at_utc"],
        "review_id": response["review_id"],
        "review_bundle_manifest_sha256": BUNDLE_SHA256,
        "proposal_ref": PROPOSAL_REF,
        "proposal_sha256": PROPOSAL_SHA256,
        "review_contract_ref": CONTRACT_REF,
        "review_contract_sha256": CONTRACT_SHA256,
        "review_reconciliation_ref": RECONCILIATION_REF,
        "review_reconciliation_sha256": RECONCILIATION_SHA256,
        "locked_response_sha256": RESPONSE_SHA256,
        "lock_receipt_sha256": RECEIPT_SHA256,
        "human_decision_count": 1,
        "decision_counts": {"approve": 1, "revise": 0, "defer": 0},
        "attestation": True,
        "preserved_failure": copy.deepcopy(proposal["preserved_failure"]),
        "observed_representation": copy.deepcopy(proposal["observed_representation"]),
        "authorized_metadata_change": copy.deepcopy(proposal["proposed_exact_change"]),
        "authorized_actions": copy.deepcopy(proposal["bounded_actions_if_approved"]),
        "limits": copy.deepcopy(proposal["limits"]),
        "stop_rules": copy.deepcopy(proposal["stop_rules"]),
        "does_not_authorize": copy.deepcopy(proposal["explicitly_not_authorized"]),
        "post_observation_correction_acknowledged": True,
        "human_decisions_fabricated": False,
    }
    approval_bytes = canonical(approval)
    approval_sha = hashlib.sha256(approval_bytes).hexdigest()
    activation = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-DEM-VERTICAL-DATUM-PROJ25-METADATA-RECOVERY-001-APPROVAL-ACTIVATION",
        "activated_at_utc": args.activated_at_utc,
        "status": "pass_exact_approval_activated_implementation_publication_only",
        "bindings": {
            "approval_sha256": approval_sha,
            "reconciliation_sha256": RECONCILIATION_SHA256,
            "proposal_sha256": PROPOSAL_SHA256,
            "review_bundle_sha256": BUNDLE_SHA256,
        },
        "released_now": {
            "bounded_implementation": True,
            "synthetic_and_arcgis_tests": True,
            "public_ci": True,
            "final_no_content_preflight": False,
            "preserved_byte_read": False,
            "grid_promotion": False,
            "dem_pixel_read": False,
            "dem_conversion": False,
            "orbit_or_radar_action": False,
            "scientific_publication": False,
        },
        "assertions": {
            "network_requests_performed": False,
            "preserved_grid_bytes_read": False,
            "grid_promoted": False,
            "dem_pixels_read": False,
            "external_data_mutated": False,
        },
    }
    outputs = {APPROVAL_REF: approval_bytes, ACTIVATION_REF: canonical(activation)}
    collisions = [ref for ref in outputs if (ROOT / ref).exists()]
    if collisions:
        raise SystemExit("refusing output collision: " + ", ".join(collisions))
    for ref, payload in outputs.items():
        write_new(ROOT / ref, payload)

    milestone_path = ROOT / "contracts/milestone-002.json"
    profile_path = ROOT / "records/project-control-profile.json"
    goal_path = ROOT / "records/long-term-goal.json"
    milestone, profile, goal = load(milestone_path), load(profile_path), load(goal_path)
    review = unit(milestone, "M2-DEM-PROJ25-METADATA-RECOVERY-001-REVIEW")
    implementation = unit(milestone, CHECKPOINT)
    if (
        review.get("status") != "ready"
        or review.get("gates", {}).get("human_decision_count") != 0
        or implementation.get("status") != "planned"
    ):
        raise SystemExit("metadata recovery is not at the exact zero-decision checkpoint")
    review.update({"status": "complete", "disposition": "pass"})
    review["outputs"] = [RECONCILIATION_REF, APPROVAL_REF, ACTIVATION_REF]
    review["gates"].update({
        "human_decision_count": 1,
        "attestation": True,
        "correction_authorized": True,
        "approval_sha256": approval_sha,
        "review_reconciliation_sha256": RECONCILIATION_SHA256,
    })
    review["exit_condition_delta"] = {
        "expected": [],
        "observed": ["one exact attested approval"],
        "decision_value": "enables_dependency",
        "rationale": "Only the bounded implementation, tests, and public CI are released now.",
    }
    implementation.update({"status": "in_progress", "disposition": None})
    implementation["inputs"] = [APPROVAL_REF, PROPOSAL_REF, RECONCILIATION_REF]
    implementation["gates"].update({
        "approval_sha256": approval_sha,
        "public_ci": "pending",
        "final_no_content_preflight": "blocked_by_public_ci",
        "preserved_byte_read": False,
        "grid_promotion": False,
    })
    implementation["exit_condition_delta"] = {
        "expected": [],
        "observed": ["exact approval locked and reconciled"],
        "decision_value": "unknown",
        "rationale": "Implementation is active; real preserved-byte access remains gated.",
    }
    amendment = {
        "approval_ref": APPROVAL_REF,
        "approval_sha256": approval_sha,
        "proposal_ref": PROPOSAL_REF,
        "proposal_sha256": PROPOSAL_SHA256,
        "review_bundle_sha256": BUNDLE_SHA256,
        "review_reconciliation_ref": RECONCILIATION_REF,
        "review_reconciliation_sha256": RECONCILIATION_SHA256,
        "network_requests_authorized": 0,
        "recovery_verification_attempts": 1,
        "maximum_conversion_attempts_per_dem": 1,
        "stop_on_first_failure": True,
        "automatic_retry_authorized": False,
    }
    for authority in (milestone["authority"], profile["authority"]):
        authority["amendments"].append(copy.deepcopy(amendment))
    milestone["scope"]["active_amendments"].append(APPROVAL_REF)
    profile["control_surfaces"]["proposed_amendments"] = []
    profile["control_surfaces"]["activated_amendments"].append(APPROVAL_REF)
    goal["proposed_amendments"] = []
    goal["active_amendments"].append(APPROVAL_REF)
    gate = [item for item in profile["gate_policy"]["explicit_human_gates"] if item.get("unit_id") == "M2-DEM-PROJ25-METADATA-RECOVERY-001-REVIEW"]
    if len(gate) != 1:
        raise SystemExit("profile review gate missing or ambiguous")
    gate[0].update({
        "authority_ref": APPROVAL_REF,
        "reason": "The exact owner approval authorizes only the bounded metadata correction, offline recovery, conditional promotion, and fixed-order conversions.",
    })
    milestone["handoff"].update({
        "current_checkpoint": CHECKPOINT,
        "next_action": NEXT_ACTION,
        "parallel_checkpoint": CHECKPOINT,
        "parallel_next_action": NEXT_ACTION,
    })
    profile["current_checkpoint"] = {"checkpoint_id": CHECKPOINT, "expected_branch": "main", "expected_head": None, "next_action": NEXT_ACTION}
    profile["parallel_checkpoints"] = [{"checkpoint_id": CHECKPOINT, "authority_ref": APPROVAL_REF, "next_action": NEXT_ACTION}]
    goal["current_checkpoint"] = CHECKPOINT
    goal["parallel_checkpoints"] = [CHECKPOINT]
    nonce = "m2-dem-proj25-metadata-recovery-001"
    replace_json(milestone_path, milestone, nonce)
    replace_json(profile_path, profile, nonce)
    replace_json(goal_path, goal, nonce)
    print(json.dumps({
        "status": "activated_implementation_publication_only",
        "approval_sha256": approval_sha,
        "reconciliation_sha256": RECONCILIATION_SHA256,
        "current_checkpoint": CHECKPOINT,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
