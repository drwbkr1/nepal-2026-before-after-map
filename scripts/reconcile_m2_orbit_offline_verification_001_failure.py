#!/usr/bin/env python3
"""Reconcile the terminal M2-ORB-001 verifier receipt-persistence failure."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_REF = "contracts/m2-orbit-offline-verification.json"
CANDIDATE_REF = "contracts/m2-orbit-offline-verification-continuation-001.json"
MILESTONE_REF = "contracts/milestone-002.json"
PROFILE_REF = "records/project-control-profile.json"
GOAL_REF = "records/long-term-goal.json"
PUBLICATION_REF = "records/readiness/m2-orbit-offline-verification-continuation-001-publication-gate.json"
ACTIVATION_REF = "records/readiness/m2-orbit-offline-verification-continuation-001-activation.json"
PREFLIGHT_REF = "records/readiness/m2-orbit-offline-verification-continuation-001-final-preflight.json"
VERIFIER_REF = "scripts/verify_m2_orbit_eof.py"
OUTPUT_REF = "records/readiness/m2-orbit-offline-verification-001-terminal-reconciliation.json"
EXPECTED_PUBLICATION_COMMIT = "308b6d079696a5f5973f7daa02e137e07a14eea3"
EXPECTED_PUBLIC_CI_RUN_ID = 34145814247
SOURCE_IDS = ["M2-ORB-001", "M2-ORB-002", "M2-ORB-003", "M2-ORB-004"]
RECEIPT_REFS = {
    source_id: f"records/acquisition/orbit-verification/{source_id.casefold()}-offline-verification-001.json"
    for source_id in SOURCE_IDS
}
CHECKPOINT = "M2-ORBIT-VERIFY-RECOVERY-001-REVIEW-PREPARATION"
NEXT_ACTION = (
    "Preserve the consumed M2-ORB-001 verifier invocation as terminal indeterminate because EOF content was evaluated "
    "but its receipt could not be written, then prepare a zero-decision review for an output-directory preflight "
    "correction and one separately authorized recovery attempt. Do not rerun any orbit verification, read another EOF, "
    "apply orbit data, act on DEMs or radar pixels, run a baseline or change analysis, attribute cause, or publish a "
    "scientific result."
)


def load(ref: str) -> dict[str, Any]:
    value = json.loads((ROOT / ref).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {ref}")
    return value


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def write_existing(ref: str, value: dict[str, Any]) -> None:
    (ROOT / ref).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recorded-at-utc", required=True)
    parser.add_argument("--failure-code", choices=["verification_output_parent_missing"], required=True)
    args = parser.parse_args()
    if not args.recorded_at_utc.endswith("Z") or (ROOT / OUTPUT_REF).exists():
        raise SystemExit("invalid time or terminal-reconciliation output collision")

    active = load(ACTIVE_REF)
    candidate = load(CANDIDATE_REF)
    milestone = load(MILESTONE_REF)
    profile = load(PROFILE_REF)
    goal = load(GOAL_REF)
    publication = load(PUBLICATION_REF)
    activation = load(ACTIVATION_REF)
    preflight = load(PREFLIGHT_REF)
    verifier_text = (ROOT / VERIFIER_REF).read_text(encoding="utf-8")

    if (
        active.get("status") != "active_gate_ready_for_offline_verification"
        or candidate.get("status") != "candidate_public_ci_pending"
        or publication.get("status") != "pass_public_offline_verifier_controls_before_eof_reads"
        or publication.get("github_actions", {}).get("head_sha") != EXPECTED_PUBLICATION_COMMIT
        or publication.get("github_actions", {}).get("run_id") != EXPECTED_PUBLIC_CI_RUN_ID
        or activation.get("status") != "pass_exact_four_source_offline_verifier_activated_final_preflight_pending"
        or preflight.get("status") != "pass_no_content_ready_for_four_fixed_order_offline_verifications"
        or preflight.get("source_ids_in_exact_order") != SOURCE_IDS
        or any((ROOT / ref).exists() for ref in RECEIPT_REFS.values())
        or (ROOT / "records/acquisition/orbit-verification").exists()
    ):
        raise SystemExit("live verifier gate differs from the observed receipt-persistence failure state")

    inspect_index = verifier_text.find("result = inspect_eof(eof_path, requirement)")
    inventory_after_index = verifier_text.find("after_inventory = inventory(eof_path.parent)")
    write_index = verifier_text.find("write_new(output, receipt)")
    parent_check_index = verifier_text.find('raise OrbitControlError("verification_output_parent_missing")')
    if min(inspect_index, inventory_after_index, write_index, parent_check_index) < 0 or not (
        inspect_index < inventory_after_index < write_index and parent_check_index < write_index
    ):
        raise SystemExit("verifier code path no longer proves content evaluation preceded the persistence failure")

    before = {
        "active_verification": sha256(ACTIVE_REF),
        "candidate_verification": sha256(CANDIDATE_REF),
        "milestone": sha256(MILESTONE_REF),
        "profile": sha256(PROFILE_REF),
        "goal": sha256(GOAL_REF),
    }

    failure_extension = {
        "source_id": "M2-ORB-001",
        "attempt_identity": "m2-orb-001-offline-verification-001",
        "failure_code": args.failure_code,
        "terminal_status": "indeterminate_evaluated_in_memory_receipt_not_persisted",
        "terminal_reconciliation_ref": OUTPUT_REF,
        "automatic_retry_authorized": False,
        "remaining_source_reads_authorized": False,
    }
    active["status"] = "terminal_indeterminate_m2_orb_001_receipt_persistence_failure"
    active["extensions"]["continuation_001"]["offline_file_reads_started"] = True
    active["extensions"]["offline_verification_continuation_001"].update(
        {
            "offline_file_reads_started": True,
            "attempted_source_ids": ["M2-ORB-001"],
            "unattempted_source_ids": SOURCE_IDS[1:],
            "attempt_001_failure": failure_extension,
        }
    )
    candidate["status"] = "terminal_consumed_m2_orb_001_receipt_persistence_failure"
    candidate["extensions"]["continuation_001"].update(
        {
            "offline_file_reads_started": True,
            "attempted_source_ids": ["M2-ORB-001"],
            "unattempted_source_ids": SOURCE_IDS[1:],
            "attempt_001_failure": failure_extension,
            "next_gate": "separate owner review for any local verification recovery or continuation",
        }
    )

    units = {unit.get("id"): unit for unit in milestone.get("units", []) if isinstance(unit, dict)}
    unit = units.get("M2-ORBIT-VERIFY")
    if not isinstance(unit, dict):
        raise SystemExit("M2-ORBIT-VERIFY unit is absent")
    unit["status"] = "blocked"
    unit["disposition"] = "terminal_indeterminate_receipt_persistence_failure"
    unit["gates"].update(
        {
            "offline_set_verification": "terminal_indeterminate_m2_orb_001_receipt_persistence_failure",
            "real_eof_reads_started": True,
            "attempted_source_ids": ["M2-ORB-001"],
            "durable_verification_receipt_source_ids": [],
            "unattempted_source_ids": SOURCE_IDS[1:],
            "automatic_retry_authorized": False,
        }
    )
    unit["retained_failures"] = list(dict.fromkeys(unit.get("retained_failures", []) + [OUTPUT_REF]))
    unit["exit_condition_delta"] = {
        "expected": ["EXIT-201-VERIFIED-CUSTODY", "EXIT-202-PIXEL-AND-RIGHTS-QA"],
        "observed": ["EXIT-201-VERIFIED-CUSTODY"],
        "decision_value": "blocked",
        "rationale": (
            "M2-ORB-001 EOF content was evaluated in memory, but the required append-only receipt could not be written "
            "because its output parent directory was missing. The result is indeterminate, the attempt is consumed, "
            "and M2-ORB-002 through M2-ORB-004 were not read."
        ),
    }
    milestone["handoff"]["current_checkpoint"] = CHECKPOINT
    milestone["handoff"]["next_action"] = NEXT_ACTION
    milestone["handoff"]["do_not_carry_forward"].append(
        "Offline verification attempt 001 read and evaluated M2-ORB-001 but lost the in-memory result when its "
        "append-only receipt parent was absent; treat it as terminal indeterminate, do not reconstruct a result, and "
        "do not run M2-ORB-002 through M2-ORB-004."
    )
    profile["current_checkpoint"] = {
        "checkpoint_id": CHECKPOINT,
        "expected_branch": "main",
        "expected_head": None,
        "next_action": NEXT_ACTION,
    }
    goal["current_checkpoint"] = CHECKPOINT

    write_existing(ACTIVE_REF, active)
    write_existing(CANDIDATE_REF, candidate)
    write_existing(MILESTONE_REF, milestone)
    write_existing(PROFILE_REF, profile)
    write_existing(GOAL_REF, goal)
    after = {
        "active_verification": sha256(ACTIVE_REF),
        "candidate_verification": sha256(CANDIDATE_REF),
        "milestone": sha256(MILESTONE_REF),
        "profile": sha256(PROFILE_REF),
        "goal": sha256(GOAL_REF),
    }

    receipt = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ORBIT-OFFLINE-VERIFICATION-001-TERMINAL-RECONCILIATION",
        "recorded_at_utc": args.recorded_at_utc,
        "status": "terminal_indeterminate_m2_orb_001_evaluated_receipt_not_persisted_no_retry_released",
        "attempt": {
            "attempt_identity": "m2-orb-001-offline-verification-001",
            "source_id": "M2-ORB-001",
            "planned_output_ref": RECEIPT_REFS["M2-ORB-001"],
            "failure_code": args.failure_code,
            "time_lower_bound_utc": preflight["verified_at_utc"],
            "exact_invocation_time_persisted": False,
            "result_disposition": "indeterminate",
            "reason": "The complete evaluation ran in memory, but no durable pass or fail receipt was written.",
        },
        "evidence": {
            "verifier_ref": VERIFIER_REF,
            "verifier_sha256": sha256(VERIFIER_REF),
            "publication_commit": EXPECTED_PUBLICATION_COMMIT,
            "public_ci_run_id": EXPECTED_PUBLIC_CI_RUN_ID,
            "publication_gate_ref": PUBLICATION_REF,
            "publication_gate_sha256": sha256(PUBLICATION_REF),
            "activation_ref": ACTIVATION_REF,
            "activation_sha256": sha256(ACTIVATION_REF),
            "final_preflight_ref": PREFLIGHT_REF,
            "final_preflight_sha256": sha256(PREFLIGHT_REF),
            "code_path_observation": (
                "inspect_eof and the post-read custody inventory execute before write_new checks the output parent"
            ),
        },
        "control_hashes": {"before": before, "after": after},
        "assertions": {
            "m2_orb_001_eof_content_read": True,
            "verification_evaluation_executed_in_memory": True,
            "evaluation_result_durably_persisted": False,
            "verification_receipt_written": False,
            "result_reconstructed_or_inferred": False,
            "external_orbit_custody_mutated": False,
            "later_source_eof_content_read": False,
            "automatic_retry_performed": False,
            "automatic_retry_authorized": False,
            "network_or_credential_action_performed": False,
            "orbit_application_performed": False,
            "dem_or_radar_pixel_action_performed": False,
            "baseline_change_attribution_or_publication_performed": False,
        },
        "next_gate": NEXT_ACTION,
    }
    path = ROOT / OUTPUT_REF
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(receipt, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"status": receipt["status"], "checkpoint": CHECKPOINT, "output": OUTPUT_REF}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
