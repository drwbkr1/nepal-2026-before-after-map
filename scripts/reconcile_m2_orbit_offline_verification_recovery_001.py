#!/usr/bin/env python3
"""Reconcile the exact terminal result of offline orbit-verification recovery-001."""

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
APPROVAL_SHA256 = "315812935fe725b5c2928a27abc2b51faf561c423065de6216f975cecbe81f30"
PREFLIGHT_REF = "records/readiness/m2-orbit-offline-verification-recovery-001-final-preflight.json"
OUTPUT_REF = "records/readiness/m2-orbit-offline-verification-recovery-001-terminal-reconciliation.json"
SOURCE_IDS = ["M2-ORB-001", "M2-ORB-002", "M2-ORB-003", "M2-ORB-004"]
RECEIPT_REFS = {
    "M2-ORB-001": "records/acquisition/orbit-verification/m2-orb-001-offline-verification-recovery-001.json",
    "M2-ORB-002": "records/acquisition/orbit-verification/m2-orb-002-offline-verification-001.json",
    "M2-ORB-003": "records/acquisition/orbit-verification/m2-orb-003-offline-verification-001.json",
    "M2-ORB-004": "records/acquisition/orbit-verification/m2-orb-004-offline-verification-001.json",
}
PASS_CHECKPOINT = "M2-DEM-VERTICAL-DATUM-REVIEW"
PASS_NEXT_ACTION = "Conduct the exact pending owner review of the EGM2008-to-ArcGIS-EGM96 vertical-datum route. Do not apply orbit data, reinterpret DEM heights, read radar pixels, run a baseline or change analysis, attribute cause, or publish a scientific result before that human gate is resolved."
FAIL_CHECKPOINT = "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-TERMINAL"
FAIL_NEXT_ACTION = "Preserve the terminal recovery result and prepare a separately governed path decision. No second recovery, retry, rule change, source substitution, processing, or scientific publication is authorized."


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


def inspect_results() -> tuple[str, str | None, list[dict[str, Any]]]:
    results: list[dict[str, Any]] = []
    terminal_kind = "pass"
    stopped_source: str | None = None
    for index, source_id in enumerate(SOURCE_IDS):
        ref = RECEIPT_REFS[source_id]
        path = ROOT / ref
        if not path.exists():
            if index == 0:
                raise ValueError("no recovery attempt evidence exists")
            terminal_kind = "interruption_between_sources"
            stopped_source = source_id
            if any((ROOT / RECEIPT_REFS[later]).exists() for later in SOURCE_IDS[index + 1 :]):
                raise ValueError("later receipt exists after an absent fixed-order receipt")
            break
        size = path.stat().st_size
        digest = sha256(ref)
        try:
            receipt = load(ref)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            terminal_kind = "reserved_receipt_interruption"
            stopped_source = source_id
            results.append({
                "source_id": source_id,
                "receipt_ref": ref,
                "receipt_sha256": digest,
                "receipt_size_bytes": size,
                "status": "terminal_reserved_receipt_incomplete",
            })
            if any((ROOT / RECEIPT_REFS[later]).exists() for later in SOURCE_IDS[index + 1 :]):
                raise ValueError("later receipt exists after an incomplete fixed-order receipt")
            break
        expected_attempt = (
            "m2-orb-001-offline-verification-recovery-001"
            if source_id == "M2-ORB-001"
            else f"{source_id.casefold()}-offline-verification-001"
        )
        claim = receipt.get("claim_boundary", {})
        if (
            receipt.get("verification_id") != "NEPAL-M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001"
            or receipt.get("source_id") != source_id
            or receipt.get("attempt_identity") != expected_attempt
            or receipt.get("approval_sha256") != APPROVAL_SHA256
            or receipt.get("candidate_contract_sha256") != CANDIDATE_SHA256
            or receipt.get("final_preflight_sha256") != sha256(PREFLIGHT_REF)
            or receipt.get("custody_unchanged") is not True
            or receipt.get("persistence", {}).get("receipt_reserved_before_eof_content_read") is not True
            or receipt.get("persistence", {}).get("exclusive_creation") is not True
            or receipt.get("persistence", {}).get("reuse_authorized") is not False
            or any(value for key, value in claim.items() if key != "exact_orbit_input_identity_and_structure_established")
        ):
            raise ValueError(f"verification receipt identity or claim boundary differs: {source_id}")
        result = {
            "source_id": source_id,
            "receipt_ref": ref,
            "receipt_sha256": digest,
            "receipt_size_bytes": size,
            "status": receipt.get("status"),
            "custody_sha256": receipt.get("evaluation", {}).get("observed", {}).get("sha256"),
            "custody_size_bytes": receipt.get("evaluation", {}).get("observed", {}).get("size_bytes"),
        }
        results.append(result)
        if receipt.get("status") != "pass_orbit_input_only":
            terminal_kind = "verification_failure"
            stopped_source = source_id
            if claim.get("exact_orbit_input_identity_and_structure_established") is not False:
                raise ValueError("failed receipt claim boundary differs")
            if any((ROOT / RECEIPT_REFS[later]).exists() for later in SOURCE_IDS[index + 1 :]):
                raise ValueError("later receipt exists after fixed-order failure")
            break
        if (
            receipt.get("promoted_identity_match") is not True
            or receipt.get("evaluation", {}).get("status") != "pass_orbit_input_only"
            or receipt.get("evaluation", {}).get("xml", {}).get("endpoint_tolerance_seconds") != 1.0
            or claim.get("exact_orbit_input_identity_and_structure_established") is not True
        ):
            raise ValueError(f"passing receipt validation differs: {source_id}")
    if terminal_kind == "pass" and len(results) != 4:
        raise ValueError("complete result count differs")
    return terminal_kind, stopped_source, results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconciled-at-utc", required=True)
    args = parser.parse_args()
    if not args.reconciled_at_utc.endswith("Z") or (ROOT / OUTPUT_REF).exists():
        raise SystemExit("invalid reconciliation time or output collision")
    active = load(ACTIVE_REF)
    milestone = load(MILESTONE_REF)
    profile = load(PROFILE_REF)
    goal = load(GOAL_REF)
    preflight = load(PREFLIGHT_REF)
    if (
        sha256(CANDIDATE_REF) != CANDIDATE_SHA256
        or active.get("status") != "active_recovery_ready_for_offline_verification"
        or preflight.get("status") != "pass_no_content_ready_for_exact_recovery_sequence"
        or preflight.get("bindings", {}).get("active_verification_sha256") != sha256(ACTIVE_REF)
        or milestone.get("handoff", {}).get("current_checkpoint") != "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001"
        or profile.get("current_checkpoint", {}).get("checkpoint_id") != "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001"
        or goal.get("current_checkpoint") != "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001"
    ):
        raise SystemExit("active recovery, preflight, or checkpoint differs")
    terminal_kind, stopped_source, results = inspect_results()
    passed = terminal_kind == "pass"
    checkpoint = PASS_CHECKPOINT if passed else FAIL_CHECKPOINT
    next_action = PASS_NEXT_ACTION if passed else FAIL_NEXT_ACTION
    recovery = unit(milestone, "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001")
    orbit_verify = unit(milestone, "M2-ORBIT-VERIFY")
    orbit_apply = unit(milestone, "M2-ORBIT-APPLY")
    if recovery.get("status") != "ready":
        raise SystemExit("recovery unit is not ready")
    before = {ref: sha256(ref) for ref in [ACTIVE_REF, MILESTONE_REF, PROFILE_REF, GOAL_REF]}
    active["status"] = "complete_pass_four_orbit_inputs_only" if passed else f"terminal_recovery_001_{terminal_kind}"
    active["completed_at_utc"] = args.reconciled_at_utc
    extension = active["extensions"]["offline_verification_recovery_001"]
    extension.update({
        "final_no_content_preflight": "pass",
        "real_eof_content_read_count": len([item for item in results if item.get("status") in {"pass_orbit_input_only", "fail"}]),
        "completed_source_ids_in_exact_order": [item["source_id"] for item in results if item.get("status") == "pass_orbit_input_only"],
        "terminal_kind": terminal_kind,
        "stopped_source_id": stopped_source,
        "verification_receipts": results,
        "m2_orb_001_recovery_attempts_remaining": 0,
        "remaining_source_attempts_per_source_remaining": 0 if passed else "no_further_action_released",
        "orbit_application_released": False,
    })
    recovery.update({"status": "complete", "disposition": "pass" if passed else "block"})
    recovery["outputs"] = [item["receipt_ref"] for item in results] + [OUTPUT_REF]
    recovery["gates"].update({
        "final_no_content_preflight": "pass",
        "terminal_kind": terminal_kind,
        "completed_source_ids_in_exact_order": extension["completed_source_ids_in_exact_order"],
        "stopped_source_id": stopped_source,
        "automatic_retry_authorized": False,
    })
    recovery["exit_condition_delta"] = {
        "expected": ["EXIT-201-VERIFIED-CUSTODY"],
        "observed": ["four exact orbit inputs verified structurally"] if passed else [f"terminal recovery result: {terminal_kind}"],
        "decision_value": "pass_input_only" if passed else "blocked",
        "rationale": "All four exact AUX_RESORB inputs passed without custody mutation; application remains blocked." if passed else "The authorized sequence stopped terminally without retry; the retained result cannot be broadened or reconstructed.",
    }
    if passed:
        orbit_verify.update({"status": "complete", "disposition": "pass"})
        orbit_verify["outputs"] = list(RECEIPT_REFS.values()) + [OUTPUT_REF]
        orbit_verify["gates"].update({
            "offline_set_verification": "pass_four_exact_orbit_inputs_only",
            "durable_verification_receipt_source_ids": SOURCE_IDS,
            "unattempted_source_ids": [],
            "automatic_retry_authorized": False,
            "recovery_001_status": "complete_pass_four_exact_orbit_inputs_only",
            "real_eof_read_count": 4,
            "custody_mutation_count": 0,
            "orbit_application_performed": False,
        })
        orbit_verify["exit_condition_delta"] = {
            "expected": ["EXIT-201-VERIFIED-CUSTODY", "EXIT-202-PIXEL-AND-RIGHTS-QA"],
            "observed": ["EXIT-201-VERIFIED-CUSTODY", "orbit input identity and structural fitness only"],
            "decision_value": "pass_input_only",
            "rationale": "All four exact AUX_RESORB files passed one durable read-only verification; application and radar fitness remain unproven.",
        }
        orbit_apply["gates"].update({
            "orbit_input_verification": "pass_four_exact_resorb_inputs_only",
            "orbit_input_verification_ref": OUTPUT_REF,
            "dem_vertical_datum_gate": "pending_owner_review",
            "terrain_result_review": "pending_owner_review",
            "radar_pixel_readiness": "pending",
            "orbit_application_started": False,
        })
    else:
        orbit_verify.update({"status": "blocked", "disposition": f"terminal_recovery_001_{terminal_kind}"})
        orbit_verify["gates"].update({
            "recovery_001_status": f"terminal_{terminal_kind}",
            "automatic_retry_authorized": False,
            "stopped_source_id": stopped_source,
        })
    milestone["handoff"]["current_checkpoint"] = checkpoint
    milestone["handoff"]["next_action"] = next_action
    profile["current_checkpoint"] = {"checkpoint_id": checkpoint, "expected_branch": "main", "expected_head": None, "next_action": next_action}
    goal["current_checkpoint"] = checkpoint
    nonce = "orbit-offline-verification-recovery-001-terminal"
    replace(ACTIVE_REF, active, nonce)
    replace(MILESTONE_REF, milestone, nonce)
    replace(PROFILE_REF, profile, nonce)
    replace(GOAL_REF, goal, nonce)
    output = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-TERMINAL-RECONCILIATION",
        "reconciled_at_utc": args.reconciled_at_utc,
        "status": "pass_four_exact_resorb_inputs_verified_no_application" if passed else f"terminal_{terminal_kind}_no_retry",
        "source_ids_in_exact_order": SOURCE_IDS,
        "terminal_kind": terminal_kind,
        "stopped_source_id": stopped_source,
        "results": results,
        "bindings": {
            "candidate_contract_sha256": CANDIDATE_SHA256,
            "final_preflight_sha256": sha256(PREFLIGHT_REF),
            "active_intake_sha256": sha256(INTAKE_REF),
            "active_verification_sha256_before": before[ACTIVE_REF],
            "active_verification_sha256_after": sha256(ACTIVE_REF),
            "milestone_sha256_before": before[MILESTONE_REF],
            "milestone_sha256_after": sha256(MILESTONE_REF),
            "profile_sha256_before": before[PROFILE_REF],
            "profile_sha256_after": sha256(PROFILE_REF),
            "goal_sha256_before": before[GOAL_REF],
            "goal_sha256_after": sha256(GOAL_REF),
        },
        "claim_boundary": {
            "exact_orbit_input_identity_and_structure_established": passed,
            "precise_orbit_equivalence_established": False,
            "geolocation_or_registration_accuracy_established": False,
            "vertical_datum_fitness_established": False,
            "radar_pixel_processing_executed": False,
            "baseline_established": False,
            "observable_event_change_established": False,
            "interpretation_or_attribution_established": False,
            "scientific_publication_authorized": False,
        },
        "assertions": {
            "network_request_count": 0,
            "credential_values_read_or_recorded": False,
            "external_custody_mutation_count": 0,
            "automatic_retry_performed": False,
            "second_recovery_authorized": False,
            "scientific_validation_rules_changed": False,
            "orbit_application_performed": False,
            "dem_or_radar_pixel_action_performed": False,
            "baseline_change_attribution_or_publication_performed": False,
        },
        "next_checkpoint": checkpoint,
        "next_action": next_action,
    }
    path = ROOT / OUTPUT_REF
    with path.open("xb") as stream:
        stream.write(canonical(output))
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"status": output["status"], "checkpoint": checkpoint, "output": OUTPUT_REF}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
