#!/usr/bin/env python3
"""Activate the exact alternate vertical-datum approval through implementation only."""

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
PROPOSAL_REF = "contracts/m2-dem-vertical-datum-alternate-method-001-proposal.json"
PROPOSAL_SHA256 = "dd920e205cb34f812dbbed422909acd9d3357d2f7b53f6843eccf03259e226d7"
BUNDLE_REF = "reviews/m2-dem-vertical-datum-alternate-method-001/review-bundle.json"
BUNDLE_SHA256 = "caa27cad02aa78caeb38c511ea3cae7ebb637833bd4d54881b8a557a38eb1702"
CONTRACT_REF = "reviews/m2-dem-vertical-datum-alternate-method-001/review-contract.json"
CONTRACT_SHA256 = "306eb3fa56ba0feb58818947b5f2dcac7cc8c9ac9ebcade47adb3bc08132e8e1"
PUBLICATION_REF = "records/readiness/m2-dem-vertical-datum-alternate-method-001-review-publication-gate.json"
RESPONSE_SHA256 = "7244844792ae5ec619e0aacbfec905b178745cfd1dd878b8e0642d77f59ac9a9"
RECEIPT_SHA256 = "c544589c8fac7e56619a207f55a638099ad553586090f3e2cde6828387b80cb2"
LOCKED = DATA_ROOT / "private-review-responses/m2-dem-vertical-datum-alternate-method-001/locked"
RESPONSE = LOCKED / f"m2-dem-vertical-datum-alternate-method-001-review-response-{RESPONSE_SHA256[:16]}.json"
RECEIPT = LOCKED / f"m2-dem-vertical-datum-alternate-method-001-review-receipt-{RESPONSE_SHA256[:16]}.json"
RECONCILIATION_REF = "records/source-gates/m2-dem-vertical-datum-alternate-method-001-review-reconciliation.json"
APPROVAL_REF = "records/source-gates/m2-dem-vertical-datum-alternate-method-001-approval.json"
ACTIVATION_REF = "records/readiness/m2-dem-vertical-datum-alternate-method-001-approval-activation.json"
CHECKPOINT = "M2-DEM-VERTICAL-DATUM-ALTERNATE-METHOD-001-IMPLEMENTATION"
NEXT_ACTION = (
    "Implement and synthetically validate only the approved exact-grid acquisition, verification, no-network "
    "vertical conversion, and ArcGIS-readability controls, then require fresh public default-branch CI. Do not "
    "request the grid or read a DEM pixel before that public gate and the final no-payload preflight pass."
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
        RESPONSE: RESPONSE_SHA256,
        RECEIPT: RECEIPT_SHA256,
    }
    if any(not path.is_file() or sha(path) != expected for path, expected in exact.items()):
        raise SystemExit("approval input identity drift or missing locked response")
    if load(ROOT / PUBLICATION_REF).get("public_ci_conclusion") != "success":
        raise SystemExit("review publication gate is not successful")
    response = load(RESPONSE)
    receipt = load(RECEIPT)
    if (
        response.get("review_id") != "m2-dem-vertical-datum-alternate-method-001-review"
        or response.get("completed") is not True
        or response.get("reviewer", {}).get("attestation") is not True
        or len(response.get("responses", [])) != 1
        or response["responses"][0].get("item_id") != "M2-DEM-VERTICAL-DATUM-PROJ-EGM2008-2_5-PRECONVERSION"
        or response["responses"][0].get("evidence_sha256") != BUNDLE_SHA256
        or response["responses"][0].get("decision") != "approve"
        or receipt.get("response_sha256") != RESPONSE_SHA256
        or receipt.get("contract_sha256") != CONTRACT_SHA256
    ):
        raise SystemExit("locked response is not the exact attested approval")
    proposal = load(ROOT / PROPOSAL_REF)
    reconciliation = {
        "reconciliation_version": "human-review-reconciliation-v1",
        "status": "reconciled_exact_human_response",
        "review_id": response["review_id"],
        "contract_sha256": CONTRACT_SHA256,
        "response_sha256": RESPONSE_SHA256,
        "receipt_sha256": RECEIPT_SHA256,
        "human_decision_count": 1,
        "decision_counts": {"approve": 1, "revise": 0, "defer": 0},
        "notes_included": False,
        "human_decisions_fabricated": False,
        "downstream_authorization_created": False,
        "authority_ref": "records/source-gates/m2-dem-vertical-datum-approval.json",
        "authorized_next_actions": ["evidence_recording", "project_control", "update_project_records"],
    }
    reconciliation_bytes = canonical(reconciliation)
    reconciliation_sha = hashlib.sha256(reconciliation_bytes).hexdigest()
    approval = {
        "schema_version": "1.0",
        "approval_id": "NEPAL-M2-DEM-VERTICAL-DATUM-ALTERNATE-METHOD-001-APPROVAL",
        "status": "approved_exact_proj_egm2008_2_5_bounded_route",
        "approved_at_utc": args.activated_at_utc,
        "review_id": response["review_id"],
        "review_bundle_manifest_sha256": BUNDLE_SHA256,
        "proposal_ref": PROPOSAL_REF,
        "proposal_sha256": PROPOSAL_SHA256,
        "review_contract_ref": CONTRACT_REF,
        "review_contract_sha256": CONTRACT_SHA256,
        "review_reconciliation_ref": RECONCILIATION_REF,
        "review_reconciliation_sha256": reconciliation_sha,
        "locked_response_sha256": RESPONSE_SHA256,
        "lock_receipt_sha256": RECEIPT_SHA256,
        "human_decision_count": 1,
        "decision_counts": {"approve": 1, "revise": 0, "defer": 0},
        "attestation": True,
        "exact_source": copy.deepcopy(proposal["exact_source_if_approved"]),
        "authorized_execution": copy.deepcopy(proposal["bounded_execution_if_approved"]),
        "acceptance_thresholds": copy.deepcopy(proposal["acceptance_thresholds"]),
        "does_not_authorize": copy.deepcopy(proposal["actions_not_authorized"]),
        "human_decisions_fabricated": False,
    }
    approval_bytes = canonical(approval)
    approval_sha = hashlib.sha256(approval_bytes).hexdigest()
    activation = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-DEM-VERTICAL-DATUM-ALTERNATE-METHOD-001-APPROVAL-ACTIVATION",
        "activated_at_utc": args.activated_at_utc,
        "status": "pass_exact_approval_activated_implementation_publication_only",
        "bindings": {"approval_sha256": approval_sha, "reconciliation_sha256": reconciliation_sha,
                     "proposal_sha256": PROPOSAL_SHA256, "review_bundle_sha256": BUNDLE_SHA256},
        "released_now": {"bounded_implementation": True, "synthetic_tests": True, "public_ci": True,
                         "final_no_payload_preflight": False, "grid_request": False, "dem_pixel_read": False,
                         "dem_conversion": False, "orbit_or_radar_action": False, "scientific_publication": False},
        "assertions": {"network_requests_performed": False, "grid_payload_bytes_read": 0,
                       "dem_pixels_read": False, "external_data_mutated": False},
    }
    outputs = {
        RECONCILIATION_REF: reconciliation_bytes,
        APPROVAL_REF: approval_bytes,
        ACTIVATION_REF: canonical(activation),
    }
    collisions = [ref for ref in outputs if (ROOT / ref).exists()]
    if collisions:
        raise SystemExit("refusing output collision: " + ", ".join(collisions))
    for ref, payload in outputs.items():
        write_new(ROOT / ref, payload)
    milestone_path = ROOT / "contracts/milestone-002.json"
    profile_path = ROOT / "records/project-control-profile.json"
    goal_path = ROOT / "records/long-term-goal.json"
    milestone, profile, goal = load(milestone_path), load(profile_path), load(goal_path)
    review = unit(milestone, "M2-DEM-VERTICAL-DATUM-ALTERNATE-METHOD-001-REVIEW")
    if review.get("status") != "planned" or review.get("gates", {}).get("human_decision_count") != 0:
        raise SystemExit("alternate-method review is not at the exact zero-decision checkpoint")
    review.update({"status": "complete", "disposition": "pass", "outputs": [RECONCILIATION_REF, APPROVAL_REF, ACTIVATION_REF]})
    review["gates"].update({"human_decision_count": 1, "attestation": True, "alternate_method_authorized": True,
                            "approval_sha256": approval_sha, "review_reconciliation_sha256": reconciliation_sha})
    review["exit_condition_delta"] = {"expected": [], "observed": ["one exact attested approval"],
                                      "decision_value": "enables_dependency",
                                      "rationale": "Only bounded implementation, synthetic validation, and public CI are released now."}
    implementation = {
        "id": CHECKPOINT,
        "purpose": "Implement and publicly validate the approved exact PROJ-grid intake and local no-network DEM conversion route.",
        "depends_on": ["M2-DEM-VERTICAL-DATUM-ALTERNATE-METHOD-001-REVIEW"],
        "action_class": "reversible_remediation", "human_gate": False, "status": "in_progress",
        "inputs": [APPROVAL_REF, PROPOSAL_REF],
        "outputs": ["versioned implementation", "synthetic test receipts", "implementation readiness", "public-CI gate"],
        "gates": {"approval_sha256": approval_sha, "public_ci": "pending", "grid_request_before_public_ci": False,
                  "dem_pixel_read_before_public_ci": False, "proj_network_enabled": False},
        "disposition": None, "retained_failures": ["records/readiness/m2-dem-egm2008-component-access-closure-001.json"],
        "exit_condition_delta": {"expected": [], "observed": ["exact approval locked and reconciled"],
                                 "decision_value": "unknown", "rationale": "Implementation is active; real data remains gated."},
        "next_dependency": "M2-DEM-EGM2008-PROJ25-ACQUISITION",
    }
    acquisition = {
        "id": "M2-DEM-EGM2008-PROJ25-ACQUISITION",
        "purpose": "After public CI and final no-payload preflight, acquire and verify the one exact approved grid without replacement.",
        "depends_on": [CHECKPOINT], "action_class": "data_acquisition", "human_gate": False, "status": "planned",
        "inputs": [APPROVAL_REF], "outputs": ["verified non-Git us_nga_egm08_25.tif", "append-only receipts"],
        "gates": {"public_ci": "pending", "final_no_payload_preflight": "blocked_by_public_ci", "maximum_requests": 1,
                  "automatic_retry": False, "resume": False, "expected_length_bytes": 80585622,
                  "expected_sha256": "4191d471eefebf24091b56dbc604353cb3b8cf8cc70e448bb9ae56a272bef17a"},
        "disposition": None, "retained_failures": [],
        "exit_condition_delta": {"expected": [], "observed": [], "decision_value": "unknown",
                                 "rationale": "No real request is permitted before public CI and final preflight."},
        "next_dependency": "M2-DEM-VERTICAL-DATUM-CONVERSION",
    }
    ids = {item.get("id") for item in milestone["units"]}
    if CHECKPOINT in ids or acquisition["id"] in ids:
        raise SystemExit("implementation units already exist")
    conversion = unit(milestone, "M2-DEM-VERTICAL-DATUM-CONVERSION")
    milestone["units"].insert(milestone["units"].index(conversion), implementation)
    milestone["units"].insert(milestone["units"].index(conversion), acquisition)
    conversion["depends_on"] = [acquisition["id"]]
    conversion["gates"].update({"selected_method": "local_proj_egm2008_2_5_preconversion_then_none",
                                "approval_sha256": approval_sha, "required_transformation_wkid": None,
                                "required_grid_sha256": approval["exact_source"]["sha256"]})
    conversion["inputs"] = [APPROVAL_REF, "verified non-Git us_nga_egm08_25.tif"]
    conversion["outputs"] = [
        r"C:\Projects\Active\nepal-2026-before-after-map-data\derived\dem\egm2008-ellipsoidal-proj25",
        "append-only conversion receipts",
    ]
    milestone["handoff"].update({"current_checkpoint": CHECKPOINT, "next_action": NEXT_ACTION,
                                  "parallel_checkpoint": CHECKPOINT, "parallel_next_action": NEXT_ACTION})
    amendment = {"approval_ref": APPROVAL_REF, "approval_sha256": approval_sha, "proposal_ref": PROPOSAL_REF,
                 "proposal_sha256": PROPOSAL_SHA256, "review_bundle_sha256": BUNDLE_SHA256,
                 "review_reconciliation_ref": RECONCILIATION_REF, "review_reconciliation_sha256": reconciliation_sha,
                 "selected_method": "local_proj_egm2008_2_5_preconversion_then_none",
                 "maximum_grid_requests": 1, "maximum_conversion_attempts_per_dem": 1,
                 "automatic_retry_authorized": False, "proj_network_enabled": False}
    for authority in (milestone["authority"], profile["authority"]):
        authority["amendments"].append(copy.deepcopy(amendment))
    milestone["scope"]["active_amendments"].append(APPROVAL_REF)
    profile["control_surfaces"]["proposed_amendments"] = []
    profile["control_surfaces"]["activated_amendments"].append(APPROVAL_REF)
    goal["proposed_amendments"] = []
    goal["active_amendments"].append(APPROVAL_REF)
    gate = [item for item in profile["gate_policy"]["explicit_human_gates"] if item.get("unit_id") == "M2-DEM-VERTICAL-DATUM-ALTERNATE-METHOD-001-REVIEW"]
    if len(gate) != 1:
        raise SystemExit("profile review gate missing or ambiguous")
    gate[0].update({"authority_ref": APPROVAL_REF, "reason": "The exact owner decision authorizes only the bounded PROJ-grid implementation, public gate, one request, verification, and conditional fixed-order conversion."})
    profile["current_checkpoint"] = {"checkpoint_id": CHECKPOINT, "expected_branch": "main", "expected_head": None, "next_action": NEXT_ACTION}
    profile["parallel_checkpoints"] = [{"checkpoint_id": CHECKPOINT, "authority_ref": APPROVAL_REF, "next_action": NEXT_ACTION}]
    goal["current_checkpoint"] = CHECKPOINT
    goal["parallel_checkpoints"] = [CHECKPOINT]
    nonce = "m2-dem-vertical-datum-alternate-method-001"
    replace_json(milestone_path, milestone, nonce)
    replace_json(profile_path, profile, nonce)
    replace_json(goal_path, goal, nonce)
    print(json.dumps({"status": "activated_implementation_publication_only", "approval_sha256": approval_sha,
                      "reconciliation_sha256": reconciliation_sha, "current_checkpoint": CHECKPOINT}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
