#!/usr/bin/env python3
"""Reconcile the exact orbit-verification recovery-001 approval into implementation-only controls."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "contracts/milestone-002.json"
PROFILE = ROOT / "records/project-control-profile.json"
GOAL = ROOT / "records/long-term-goal.json"
PROPOSAL_REF = "contracts/milestone-002-orbit-offline-verification-recovery-001-proposal.json"
PROPOSAL_SHA256 = "0be64071cfe718ca758155ff0422cfee48af342c8a560528746adc653e6a2fcf"
BUNDLE_SHA256 = "d2f0f75f40614c56bc0e62c6eecb1588f7504f50927448192673e6e403b5933f"
RECONCILIATION_REF = "records/source-gates/m2-orbit-offline-verification-recovery-001-review-reconciliation.json"
RECONCILIATION_SHA256 = "a07e67160e592093498d44e9ec76f607837f4a7e6b25784458898fa63a8a0fe3"
APPROVAL_REF = "records/source-gates/m2-orbit-offline-verification-recovery-001-approval.json"
APPROVAL_SHA256 = "315812935fe725b5c2928a27abc2b51faf561c423065de6216f975cecbe81f30"
ACTIVATION_REF = "records/readiness/m2-orbit-offline-verification-recovery-001-approval-activation.json"
ACTIVATION_SHA256 = "ab99cbd6a8af39052a44973161d527a5e22688d6bad79fa5a2713416aecfbfb9"
OUTPUT = ROOT / "records/readiness/m2-orbit-offline-verification-recovery-001-approval-reconciliation.json"
SOURCE_IDS = ["M2-ORB-001", "M2-ORB-002", "M2-ORB-003", "M2-ORB-004"]
CHECKPOINT = "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-IMPLEMENTATION"
NEXT_ACTION = (
    "Implement and synthetically validate only the approved pre-read receipt reservation and fixed-order recovery, "
    "then require successful public default-branch CI. Do not run the final no-content preflight or read any EOF before that public gate."
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return value


def write_new(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def replace(path: Path, value: dict[str, Any], nonce: str) -> None:
    temporary = path.with_name(f".{path.name}.{nonce}.tmp")
    if temporary.exists():
        raise ValueError(f"temporary output collision: {temporary}")
    with temporary.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def unit(milestone: dict[str, Any], unit_id: str) -> dict[str, Any]:
    matches = [item for item in milestone.get("units", []) if item.get("id") == unit_id]
    if len(matches) != 1:
        raise ValueError(f"milestone unit missing or ambiguous: {unit_id}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconciled-at-utc", required=True)
    args = parser.parse_args()
    if not args.reconciled_at_utc.endswith("Z"):
        raise SystemExit("reconciled time must be UTC")
    if OUTPUT.exists():
        raise SystemExit("refusing approval-reconciliation output collision")
    exact = {
        ROOT / PROPOSAL_REF: PROPOSAL_SHA256,
        ROOT / RECONCILIATION_REF: RECONCILIATION_SHA256,
        ROOT / APPROVAL_REF: APPROVAL_SHA256,
        ROOT / ACTIVATION_REF: ACTIVATION_SHA256,
    }
    if any(not path.is_file() or sha256(path) != expected for path, expected in exact.items()):
        raise SystemExit("proposal, reconciliation, approval, or activation identity drift")
    approval = load(ROOT / APPROVAL_REF)
    reconciliation = load(ROOT / RECONCILIATION_REF)
    activation = load(ROOT / ACTIVATION_REF)
    authorized = approval.get("authorized_recovery", {})
    if (
        approval.get("status") != "approved_exact_pre_read_receipt_reservation_recovery_only"
        or approval.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}
        or authorized.get("source_ids_in_exact_order") != SOURCE_IDS
        or authorized.get("m2_orb_001_new_recovery_attempts") != 1
        or authorized.get("remaining_source_existing_attempts_per_source") != 1
        or authorized.get("stop_on_first_failure") is not True
        or authorized.get("automatic_retry_authorized") is not False
        or authorized.get("maximum_osv_endpoint_tolerance_seconds") != 1.0
        or reconciliation.get("status") != "reconciled_exact_human_response"
        or activation.get("status") != "pass_exact_approval_activated_implementation_and_publication_only"
        or activation.get("released_now", {}).get("real_eof_read") is not False
    ):
        raise SystemExit("exact approval boundary is not active")
    milestone = load(MILESTONE)
    profile = load(PROFILE)
    goal = load(GOAL)
    review = unit(milestone, "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-REVIEW")
    if review.get("status") != "ready":
        raise SystemExit("recovery review is not at the exact owner checkpoint")
    if any(
        item.get("id") in {
            "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-IMPLEMENTATION",
            "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001",
        }
        for item in milestone.get("units", [])
    ):
        raise SystemExit("recovery implementation units already exist")
    review.update({
        "status": "complete",
        "disposition": "pass",
        "outputs": [RECONCILIATION_REF, APPROVAL_REF, ACTIVATION_REF],
    })
    review["gates"].update({
        "human_decision_count": 1,
        "attestation": True,
        "recovery_authorized": True,
        "approval_sha256": APPROVAL_SHA256,
        "review_reconciliation_sha256": RECONCILIATION_SHA256,
    })
    review["exit_condition_delta"] = {
        "expected": [],
        "observed": ["one exact attested approval"],
        "decision_value": "enables_dependency",
        "rationale": "The exact response is locked and reconciled; only implementation, synthetic tests, and public CI are released now.",
    }
    milestone["units"].extend([
        {
            "id": "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-IMPLEMENTATION",
            "purpose": "Implement and publish the approved pre-read append-only receipt reservation without reading an EOF.",
            "depends_on": ["M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-REVIEW"],
            "action_class": "reversible_remediation",
            "human_gate": False,
            "status": "in_progress",
            "inputs": [APPROVAL_REF, PROPOSAL_REF, "scripts/verify_m2_orbit_eof.py"],
            "outputs": [
                "contracts/m2-orbit-offline-verification-recovery-001.json",
                "scripts/verify_m2_orbit_eof_recovery_001.py",
                "scripts/run_m2_orbit_offline_verification_recovery_001.py",
                "scripts/preflight_m2_orbit_offline_verification_recovery_001.py",
                "records/readiness/m2-orbit-offline-verification-recovery-001-implementation-readiness.json",
                "records/readiness/m2-orbit-offline-verification-recovery-001-implementation-publication-gate.json",
            ],
            "gates": {
                "approval_sha256": APPROVAL_SHA256,
                "public_ci": "pending",
                "output_parent_creation_authorized": True,
                "real_eof_reads_before_public_ci": False,
                "network_or_credential_action": False,
                "external_custody_mutation": False,
            },
            "disposition": None,
            "retained_failures": ["records/readiness/m2-orbit-offline-verification-001-terminal-reconciliation.json"],
            "exit_condition_delta": {
                "expected": [],
                "observed": ["exact approval locked and reconciled"],
                "decision_value": "unknown",
                "rationale": "Implementation and synthetic validation are active; real EOF reads remain blocked before public CI and final preflight.",
            },
            "next_dependency": "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001",
        },
        {
            "id": "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001",
            "purpose": "Run one new M2-ORB-001 verification and conditionally consume the three unattempted fixed-order verifications.",
            "depends_on": ["M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-IMPLEMENTATION"],
            "action_class": "routine_qa",
            "human_gate": False,
            "status": "planned",
            "inputs": ["external orbit custody", "contracts/m2-orbit-offline-verification-recovery-001.json"],
            "outputs": ["four exact append-only orbit verification receipts", "exact terminal reconciliation"],
            "gates": {
                "public_ci": "pending",
                "final_no_content_preflight": "blocked_by_public_ci",
                "source_ids_in_exact_order": SOURCE_IDS,
                "m2_orb_001_new_recovery_attempts": 1,
                "remaining_source_existing_attempts_per_source": 1,
                "stop_on_first_failure": True,
                "automatic_retry_authorized": False,
                "network_or_credential_action": False,
                "external_custody_mutation": False,
            },
            "disposition": None,
            "retained_failures": ["records/readiness/m2-orbit-offline-verification-001-terminal-reconciliation.json"],
            "exit_condition_delta": {
                "expected": ["EXIT-201-VERIFIED-CUSTODY"],
                "observed": [],
                "decision_value": "unknown",
                "rationale": "Real verification remains blocked until the exact implementation passes public CI and final no-content preflight.",
            },
            "next_dependency": "M2-ORBIT-APPLY",
        },
    ])
    orbit_verify = unit(milestone, "M2-ORBIT-VERIFY")
    orbit_verify["gates"]["recovery_001_status"] = "approved_implementation_public_ci_pending"
    orbit_verify["gates"]["recovery_001_approval_sha256"] = APPROVAL_SHA256
    milestone["handoff"]["current_checkpoint"] = CHECKPOINT
    milestone["handoff"]["next_action"] = NEXT_ACTION
    amendment = {
        "approval_ref": APPROVAL_REF,
        "approval_sha256": APPROVAL_SHA256,
        "proposal_ref": PROPOSAL_REF,
        "proposal_sha256": PROPOSAL_SHA256,
        "review_bundle_sha256": BUNDLE_SHA256,
        "review_reconciliation_ref": RECONCILIATION_REF,
        "review_reconciliation_sha256": RECONCILIATION_SHA256,
        "source_ids_in_exact_order": SOURCE_IDS,
        "m2_orb_001_new_recovery_attempts": 1,
        "remaining_source_existing_attempts_per_source": 1,
        "stop_on_first_failure": True,
        "automatic_retry_authorized": False,
        "network_requests_authorized": 0,
        "external_custody_mutation_authorized": False,
        "maximum_endpoint_tolerance_seconds": 1.0,
    }
    for authority in (milestone["authority"], profile["authority"]):
        if not any(item.get("approval_ref") == APPROVAL_REF for item in authority["amendments"]):
            authority["amendments"].append(copy.deepcopy(amendment))
    if APPROVAL_REF not in milestone["scope"]["active_amendments"]:
        milestone["scope"]["active_amendments"].append(APPROVAL_REF)
    proposed = profile["control_surfaces"].get("proposed_amendments", [])
    profile["control_surfaces"]["proposed_amendments"] = [item for item in proposed if item != PROPOSAL_REF]
    if APPROVAL_REF not in profile["control_surfaces"]["activated_amendments"]:
        profile["control_surfaces"]["activated_amendments"].append(APPROVAL_REF)
    gates = [item for item in profile["gate_policy"]["explicit_human_gates"] if item.get("unit_id") == "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-REVIEW"]
    if len(gates) != 1:
        raise SystemExit("recovery review profile gate missing or ambiguous")
    gates[0].update({
        "reason": "The exact owner decision authorizes only the pre-read receipt-reservation implementation, synthetic tests, public-CI gate, final no-content preflight, one M2-ORB-001 recovery, and conditional fixed-order remaining attempts.",
        "authority_ref": APPROVAL_REF,
    })
    profile["current_checkpoint"] = {"checkpoint_id": CHECKPOINT, "expected_branch": "main", "expected_head": None, "next_action": NEXT_ACTION}
    goal["current_checkpoint"] = CHECKPOINT
    goal["proposed_amendments"] = []
    if APPROVAL_REF not in goal["active_amendments"]:
        goal["active_amendments"].append(APPROVAL_REF)
    before = {"milestone": sha256(MILESTONE), "profile": sha256(PROFILE), "goal": sha256(GOAL)}
    nonce = "orbit-offline-verification-recovery-001-approval"
    replace(MILESTONE, milestone, nonce)
    replace(PROFILE, profile, nonce)
    replace(GOAL, goal, nonce)
    receipt = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-APPROVAL-RECONCILIATION",
        "reconciled_at_utc": args.reconciled_at_utc,
        "status": "pass_exact_approval_reconciled_implementation_publication_only",
        "bindings": {
            "approval_sha256": APPROVAL_SHA256,
            "review_reconciliation_sha256": RECONCILIATION_SHA256,
            "activation_sha256": ACTIVATION_SHA256,
            "milestone_sha256_before": before["milestone"],
            "milestone_sha256_after": sha256(MILESTONE),
            "profile_sha256_before": before["profile"],
            "profile_sha256_after": sha256(PROFILE),
            "goal_sha256_before": before["goal"],
            "goal_sha256_after": sha256(GOAL),
        },
        "assertions": {
            "human_decision_count": 1,
            "new_eof_content_read": False,
            "remaining_source_eof_content_read": False,
            "network_or_credential_action_performed": False,
            "external_custody_mutated": False,
            "live_verification_released_before_public_ci": False,
            "scientific_validation_rules_changed": False,
        },
        "current_checkpoint": CHECKPOINT,
        "next_gate": "implementation, synthetic validation, and successful public default-branch CI",
    }
    write_new(OUTPUT, receipt)
    print(json.dumps({"status": receipt["status"], "output": str(OUTPUT.relative_to(ROOT)).replace("\\", "/")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
