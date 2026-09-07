#!/usr/bin/env python3
"""Reconcile four passing read-only orbit EOF verification receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent.resolve()
SOURCE_IDS = ["M2-ORB-001", "M2-ORB-002", "M2-ORB-003", "M2-ORB-004"]
ACTIVE_REF = "contracts/m2-orbit-offline-verification.json"
INTAKE_REF = "contracts/m2-orbit-intake.json"
PREFLIGHT_REF = "records/readiness/m2-orbit-offline-verification-continuation-001-final-preflight.json"
MILESTONE_REF = "contracts/milestone-002.json"
PROFILE_REF = "records/project-control-profile.json"
GOAL_REF = "records/long-term-goal.json"
OUTPUT_REF = "records/readiness/m2-orbit-offline-verification-continuation-001-terminal-reconciliation.json"
RECEIPT_REFS = {
    source_id: f"records/acquisition/orbit-verification/{source_id.casefold()}-offline-verification-001.json"
    for source_id in SOURCE_IDS
}
CHECKPOINT = "M2-DEM-VERTICAL-DATUM-REVIEW"
NEXT_ACTION = (
    "Conduct the exact pending owner review of the EGM2008-to-ArcGIS-EGM96 vertical-datum route. "
    "Do not apply orbit data, convert or reinterpret DEM heights, read radar pixels, run a baseline or change analysis, attribute cause, or publish a scientific result before that human gate is resolved."
)


def load(ref: str) -> dict[str, Any]:
    value = json.loads((ROOT / ref).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {ref}")
    return value


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def replace_json(ref: str, value: dict[str, Any], nonce: str) -> None:
    path = ROOT / ref
    temporary = path.with_name(path.name + f".{nonce}.tmp")
    if temporary.exists():
        raise ValueError(f"temporary path collision: {temporary}")
    with temporary.open("xb") as stream:
        stream.write(canonical(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def unit_by_id(milestone: dict[str, Any], unit_id: str) -> dict[str, Any]:
    matches = [item for item in milestone.get("units", []) if item.get("id") == unit_id]
    if len(matches) != 1:
        raise ValueError(f"milestone unit missing or ambiguous: {unit_id}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconciled-at-utc", required=True)
    args = parser.parse_args()
    if not args.reconciled_at_utc.endswith("Z") or (ROOT / OUTPUT_REF).exists():
        raise SystemExit("offline verification terminal output collision or invalid time")
    active = load(ACTIVE_REF)
    intake = load(INTAKE_REF)
    preflight = load(PREFLIGHT_REF)
    milestone = load(MILESTONE_REF)
    profile = load(PROFILE_REF)
    goal = load(GOAL_REF)
    if (
        active.get("status") != "active_gate_ready_for_offline_verification"
        or active.get("bindings", {}).get("active_intake_sha256_current") != sha256(INTAKE_REF)
        or preflight.get("status") != "pass_no_content_ready_for_four_fixed_order_offline_verifications"
        or preflight.get("source_ids_in_exact_order") != SOURCE_IDS
        or preflight.get("bindings", {}).get("active_verification_sha256") != sha256(ACTIVE_REF)
        or milestone.get("handoff", {}).get("current_checkpoint") != "M2-ORBIT-VERIFY-IMPLEMENTATION"
        or profile.get("current_checkpoint", {}).get("checkpoint_id") != "M2-ORBIT-VERIFY-IMPLEMENTATION"
        or goal.get("current_checkpoint") != "M2-ORBIT-VERIFY-IMPLEMENTATION"
    ):
        raise SystemExit("active verification, preflight, or project checkpoint differs")
    assets = intake.get("assets", [])
    if [item.get("extensions", {}).get("source_id") for item in assets] != SOURCE_IDS:
        raise SystemExit("active intake source order differs")
    custody_root = (PROJECT_ROOT / Path(*PurePosixPath(intake["custody_root"]).parts)).resolve(strict=True)
    receipts: list[dict[str, Any]] = []
    for asset in assets:
        source_id = asset["extensions"]["source_id"]
        receipt_ref = RECEIPT_REFS[source_id]
        receipt = load(receipt_ref)
        path = (custody_root / Path(*PurePosixPath(asset["destination_relative_path"]).parts)).resolve(strict=True)
        path.relative_to(custody_root)
        observed = asset.get("observed", {})
        if (
            receipt.get("status") != "pass_orbit_input_only"
            or receipt.get("source_id") != source_id
            or receipt.get("custody_path", "").replace("\\", "/").casefold() != path.as_posix().casefold()
            or receipt.get("custody_unchanged") is not True
            or receipt.get("promoted_identity_match") is not True
            or receipt.get("evaluation", {}).get("status") != "pass_orbit_input_only"
            or receipt.get("evaluation", {}).get("xml", {}).get("endpoint_tolerance_seconds") != 1.0
            or receipt.get("evaluation", {}).get("observed", {}).get("sha256") != observed.get("promoted_sha256")
            or receipt.get("evaluation", {}).get("observed", {}).get("size_bytes") != observed.get("promoted_size_bytes")
            or sha256_path(path) != observed.get("promoted_sha256")
            or path.stat().st_size != observed.get("promoted_size_bytes")
            or any(value for key, value in receipt.get("claim_boundary", {}).items() if key != "exact_orbit_input_identity_and_structure_established")
            or receipt.get("claim_boundary", {}).get("exact_orbit_input_identity_and_structure_established") is not True
        ):
            raise SystemExit(f"offline orbit verification receipt or custody differs: {source_id}")
        receipts.append({
            "source_id": source_id,
            "receipt_ref": receipt_ref,
            "receipt_sha256": sha256(receipt_ref),
            "custody_sha256": observed["promoted_sha256"],
            "custody_size_bytes": observed["promoted_size_bytes"],
            "input_status": "pass_orbit_input_only",
        })

    before = {ref: sha256(ref) for ref in [ACTIVE_REF, MILESTONE_REF, PROFILE_REF, GOAL_REF]}
    active["status"] = "complete_pass_four_orbit_inputs_only"
    active["completed_at_utc"] = args.reconciled_at_utc
    active["extensions"]["offline_verification_continuation_001"].update({
        "offline_file_reads_started": True,
        "completed_source_ids_in_exact_order": SOURCE_IDS,
        "verification_receipts": receipts,
        "aggregate_status": "pass_four_exact_orbit_inputs_only",
        "orbit_application_released": False,
    })
    orbit_verify = unit_by_id(milestone, "M2-ORBIT-VERIFY")
    orbit_apply = unit_by_id(milestone, "M2-ORBIT-APPLY")
    if orbit_verify.get("status") != "in_progress" or orbit_apply.get("status") != "planned":
        raise SystemExit("orbit verify or apply unit state differs")
    orbit_verify.update({"status": "complete", "disposition": "pass"})
    orbit_verify["outputs"] = [*RECEIPT_REFS.values(), OUTPUT_REF]
    orbit_verify["gates"].update({
        "offline_set_verification": "pass_four_exact_orbit_inputs_only",
        "offline_verified_source_ids": SOURCE_IDS,
        "verification_receipts": receipts,
        "real_eof_read_count": 4,
        "custody_mutation_count": 0,
        "orbit_application_performed": False,
    })
    orbit_verify["exit_condition_delta"] = {
        "expected": ["EXIT-201-VERIFIED-CUSTODY", "EXIT-202-PIXEL-AND-RIGHTS-QA"],
        "observed": ["EXIT-201-VERIFIED-CUSTODY", "orbit input identity and structural fitness only"],
        "decision_value": "pass_input_only",
        "rationale": "All four exact AUX_RESORB files passed one read-only verification with unchanged custody; application and radar fitness remain unproven.",
    }
    orbit_apply["gates"].update({
        "orbit_input_verification": "pass_four_exact_resorb_inputs_only",
        "orbit_input_verification_ref": OUTPUT_REF,
        "dem_vertical_datum_gate": "pending_owner_review",
        "terrain_result_review": "pending_owner_review",
        "radar_pixel_readiness": "pending",
        "orbit_application_started": False,
    })
    orbit_apply["exit_condition_delta"] = {
        "expected": ["EXIT-203-PRE-EVENT-BASELINE", "EXIT-204-REGISTRATION-QA"],
        "observed": ["four exact orbit inputs verified structurally"],
        "decision_value": "unknown",
        "rationale": "Orbit inputs pass, but vertical-datum, terrain-result, and radar-pixel gates remain unresolved before application.",
    }
    milestone["handoff"]["current_checkpoint"] = CHECKPOINT
    milestone["handoff"]["next_action"] = NEXT_ACTION
    carry = (
        "Four-source offline orbit verification establishes exact input identity and structural fitness only. It does not establish precise-orbit equivalence, "
        "geolocation accuracy, radar-pixel fitness, a baseline, observable event change, interpretation, attribution, or scientific publication."
    )
    if carry not in milestone["handoff"]["do_not_carry_forward"]:
        milestone["handoff"]["do_not_carry_forward"].append(carry)
    profile["current_checkpoint"] = {"checkpoint_id": CHECKPOINT, "expected_branch": "main", "expected_head": None, "next_action": NEXT_ACTION}
    goal["current_checkpoint"] = CHECKPOINT

    nonce = "orbit-offline-verification-continuation-001-terminal"
    replace_json(ACTIVE_REF, active, nonce)
    replace_json(MILESTONE_REF, milestone, nonce)
    replace_json(PROFILE_REF, profile, nonce)
    replace_json(GOAL_REF, goal, nonce)
    output = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ORBIT-OFFLINE-VERIFICATION-CONTINUATION-001-TERMINAL-RECONCILIATION",
        "reconciled_at_utc": args.reconciled_at_utc,
        "status": "pass_four_exact_resorb_inputs_verified_no_application",
        "source_ids_in_exact_order": SOURCE_IDS,
        "results": receipts,
        "bindings": {
            "final_preflight_sha256": sha256(PREFLIGHT_REF),
            "active_verification_sha256_before": before[ACTIVE_REF],
            "active_verification_sha256_after": sha256(ACTIVE_REF),
            "active_intake_sha256": sha256(INTAKE_REF),
            "milestone_sha256_before": before[MILESTONE_REF],
            "milestone_sha256_after": sha256(MILESTONE_REF),
            "profile_sha256_before": before[PROFILE_REF],
            "profile_sha256_after": sha256(PROFILE_REF),
            "goal_sha256_before": before[GOAL_REF],
            "goal_sha256_after": sha256(GOAL_REF),
        },
        "claim_boundary": {
            "exact_orbit_input_identity_and_structure_established": True,
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
            "offline_eof_read_count": 4,
            "network_request_count": 0,
            "credential_values_read_or_recorded": False,
            "custody_mutation_count": 0,
            "orbit_application_performed": False,
            "radar_pixel_or_dem_action_performed": False,
            "baseline_change_attribution_or_publication_performed": False,
        },
        "next_checkpoint": CHECKPOINT,
        "next_action": NEXT_ACTION,
    }
    path = ROOT / OUTPUT_REF
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(canonical(output))
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"status": output["status"], "checkpoint": CHECKPOINT, "output": OUTPUT_REF}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
