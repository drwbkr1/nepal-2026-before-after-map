#!/usr/bin/env python3
"""Activate public-CI-passed offline orbit-verification recovery-001 controls."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_REF = "contracts/m2-orbit-offline-verification.json"
INTAKE_REF = "contracts/m2-orbit-intake.json"
MILESTONE_REF = "contracts/milestone-002.json"
PROFILE_REF = "records/project-control-profile.json"
GOAL_REF = "records/long-term-goal.json"
CANDIDATE_REF = "contracts/m2-orbit-offline-verification-recovery-001.json"
CANDIDATE_SHA256 = "8db4774dfb36ce9718988c23d9a480a01028055a6a28a1bbf301a926e466df68"
APPROVAL_REF = "records/source-gates/m2-orbit-offline-verification-recovery-001-approval.json"
APPROVAL_SHA256 = "315812935fe725b5c2928a27abc2b51faf561c423065de6216f975cecbe81f30"
PUBLICATION_REF = "records/readiness/m2-orbit-offline-verification-recovery-001-implementation-publication-gate.json"
OUTPUT_REF = "records/readiness/m2-orbit-offline-verification-recovery-001-activation.json"
SOURCE_IDS = ["M2-ORB-001", "M2-ORB-002", "M2-ORB-003", "M2-ORB-004"]
CHECKPOINT = "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001"
NEXT_ACTION = "Run the exact final no-content preflight and, only if it passes, run one M2-ORB-001 recovery verification followed conditionally by M2-ORB-002, M2-ORB-003, and M2-ORB-004 in fixed order, stopping on the first failure."


def load(ref: str) -> dict[str, Any]:
    value = json.loads((ROOT / ref).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {ref}")
    return value


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def replace(ref: str, value: dict[str, Any], nonce: str) -> None:
    path = ROOT / ref
    temporary = path.with_name(f".{path.name}.{nonce}.tmp")
    if temporary.exists():
        raise ValueError(f"temporary output collision: {temporary}")
    with temporary.open("xb") as stream:
        stream.write(canonical(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def unit(milestone: dict[str, Any], unit_id: str) -> dict[str, Any]:
    matches = [item for item in milestone.get("units", []) if item.get("id") == unit_id]
    if len(matches) != 1:
        raise ValueError(f"milestone unit missing or ambiguous: {unit_id}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activated-at-utc", required=True)
    args = parser.parse_args()
    if not args.activated_at_utc.endswith("Z") or (ROOT / OUTPUT_REF).exists():
        raise SystemExit("invalid activation time or output collision")
    candidate = load(CANDIDATE_REF)
    approval = load(APPROVAL_REF)
    publication = load(PUBLICATION_REF)
    active = load(ACTIVE_REF)
    milestone = load(MILESTONE_REF)
    profile = load(PROFILE_REF)
    goal = load(GOAL_REF)
    if (
        sha256(CANDIDATE_REF) != CANDIDATE_SHA256
        or sha256(APPROVAL_REF) != APPROVAL_SHA256
        or candidate.get("status") != "candidate_public_ci_pending"
        or candidate.get("source_ids_in_exact_order") != SOURCE_IDS
        or approval.get("status") != "approved_exact_pre_read_receipt_reservation_recovery_only"
        or publication.get("status") != "pass_public_recovery_controls_before_eof_reads"
        or publication.get("github_actions", {}).get("conclusion") != "success"
        or publication.get("assertions", {}).get("real_eof_content_read") is not False
        or active.get("status") != "terminal_indeterminate_m2_orb_001_receipt_persistence_failure"
        or sha256(ACTIVE_REF) != candidate.get("bindings", {}).get("base_active_verification_sha256")
        or active.get("bindings", {}).get("active_intake_sha256_current") != sha256(INTAKE_REF)
        or milestone.get("handoff", {}).get("current_checkpoint") != "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-IMPLEMENTATION"
        or profile.get("current_checkpoint", {}).get("checkpoint_id") != "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-IMPLEMENTATION"
        or goal.get("current_checkpoint") != "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-IMPLEMENTATION"
    ):
        raise SystemExit("candidate, approval, public gate, active verifier, or checkpoint differs")
    output_parent = ROOT / "records/acquisition/orbit-verification"
    if not output_parent.is_dir() or sorted(path.name for path in output_parent.iterdir()) != [".gitkeep"]:
        raise SystemExit("tracked receipt parent is not exact and collision-free")
    implementation = unit(milestone, "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-IMPLEMENTATION")
    recovery = unit(milestone, "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001")
    orbit_verify = unit(milestone, "M2-ORBIT-VERIFY")
    if (implementation.get("status"), recovery.get("status")) != ("in_progress", "planned"):
        raise SystemExit("recovery units are not at the implementation checkpoint")
    before = {ref: sha256(ref) for ref in [ACTIVE_REF, MILESTONE_REF, PROFILE_REF, GOAL_REF]}
    active["status"] = "active_recovery_ready_for_offline_verification"
    active["activated_at_utc"] = args.activated_at_utc
    active.setdefault("extensions", {})["offline_verification_recovery_001"] = {
        "candidate_ref": CANDIDATE_REF,
        "candidate_sha256": CANDIDATE_SHA256,
        "approval_ref": APPROVAL_REF,
        "approval_sha256": APPROVAL_SHA256,
        "publication_gate_ref": PUBLICATION_REF,
        "publication_gate_sha256": sha256(PUBLICATION_REF),
        "public_ci": "pass",
        "final_no_content_preflight": "required",
        "source_ids_in_exact_order": SOURCE_IDS,
        "m2_orb_001_recovery_attempts_remaining": 1,
        "remaining_source_attempts_per_source_remaining": 1,
        "stop_on_first_failure": True,
        "automatic_retry_authorized": False,
        "real_eof_content_read_count": 0,
        "network_request_count": 0,
        "external_custody_mutation_count": 0,
    }
    implementation.update({"status": "complete", "disposition": "pass"})
    implementation["gates"].update({
        "public_ci": "pass",
        "publication_gate_sha256": sha256(PUBLICATION_REF),
        "final_no_content_preflight": "pending",
        "real_eof_reads_before_public_ci": False,
    })
    implementation["exit_condition_delta"] = {
        "expected": [],
        "observed": ["local synthetic tests", "successful public default-branch CI"],
        "decision_value": "enables_dependency",
        "rationale": "The exact persistence-order implementation passed public CI without reading an EOF or touching external custody.",
    }
    recovery.update({"status": "ready", "disposition": None})
    recovery["gates"].update({"public_ci": "pass", "final_no_content_preflight": "pending"})
    recovery["exit_condition_delta"]["rationale"] = "Public CI passes; one exact final no-content preflight remains before the fixed-order recovery sequence."
    orbit_verify["gates"]["recovery_001_status"] = "ready_final_no_content_preflight_pending"
    milestone["handoff"]["current_checkpoint"] = CHECKPOINT
    milestone["handoff"]["next_action"] = NEXT_ACTION
    profile["current_checkpoint"] = {"checkpoint_id": CHECKPOINT, "expected_branch": "main", "expected_head": None, "next_action": NEXT_ACTION}
    goal["current_checkpoint"] = CHECKPOINT
    nonce = "orbit-offline-verification-recovery-001-activation"
    replace(ACTIVE_REF, active, nonce)
    replace(MILESTONE_REF, milestone, nonce)
    replace(PROFILE_REF, profile, nonce)
    replace(GOAL_REF, goal, nonce)
    receipt = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-ACTIVATION",
        "activated_at_utc": args.activated_at_utc,
        "status": "pass_public_recovery_controls_activated_final_preflight_pending",
        "bindings": {
            "candidate_contract_sha256": CANDIDATE_SHA256,
            "approval_sha256": APPROVAL_SHA256,
            "publication_gate_sha256": sha256(PUBLICATION_REF),
            "active_verification_sha256_before": before[ACTIVE_REF],
            "active_verification_sha256_after": sha256(ACTIVE_REF),
            "milestone_sha256_before": before[MILESTONE_REF],
            "milestone_sha256_after": sha256(MILESTONE_REF),
            "profile_sha256_before": before[PROFILE_REF],
            "profile_sha256_after": sha256(PROFILE_REF),
            "goal_sha256_before": before[GOAL_REF],
            "goal_sha256_after": sha256(GOAL_REF),
        },
        "assertions": {
            "real_eof_content_read": False,
            "network_request_performed": False,
            "credential_value_read_or_recorded": False,
            "external_custody_mutated": False,
            "verification_receipt_created": False,
            "orbit_application_performed": False,
            "dem_or_radar_pixel_action_performed": False,
            "baseline_change_attribution_or_publication_performed": False,
        },
        "next_gate": "one final no-content preflight",
    }
    path = ROOT / OUTPUT_REF
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(receipt, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    print(json.dumps({"status": receipt["status"], "checkpoint": CHECKPOINT, "output": OUTPUT_REF}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
