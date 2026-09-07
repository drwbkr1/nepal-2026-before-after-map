#!/usr/bin/env python3
"""Reconcile the completed three-source orbit continuation into project control truth."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent.resolve()
SOURCE_ORDER = ["M2-ORB-002", "M2-ORB-003", "M2-ORB-004"]
ALL_SOURCES = ["M2-ORB-001", *SOURCE_ORDER]
SUCCESS_REF = "records/acquisition/m2-orbit-continuation-001-success-reconciliation.json"
INTAKE_REF = "contracts/m2-orbit-intake.json"
VERIFICATION_REF = "contracts/m2-orbit-offline-verification.json"
MILESTONE_REF = "contracts/milestone-002.json"
PROFILE_REF = "records/project-control-profile.json"
GOAL_REF = "records/long-term-goal.json"
PUBLICATION_REF = "records/readiness/m2-orbit-continuation-001-publication-gate.json"
ACTIVATION_REF = "records/readiness/m2-orbit-continuation-001-activation.json"
CONTROL_REF = "records/readiness/m2-orbit-continuation-001-control-reconciliation.json"
PREFLIGHT_REF = "records/readiness/m2-orbit-continuation-001-final-preflight.json"
OUTPUT_REF = "records/readiness/m2-orbit-continuation-001-terminal-project-reconciliation.json"
CHECKPOINT = "M2-ORBIT-VERIFY-IMPLEMENTATION"
NEXT_ACTION = (
    "Project the already approved one-second endpoint rules and continuation receipt identities into the four-source offline verifier, "
    "test and publish that exact implementation, and require successful public default-branch CI before reading the four promoted EOF files. "
    "Do not apply orbit data, act on DEMs or radar pixels, run a baseline or change analysis, attribute cause, or publish a scientific result."
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


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def replace_json(ref: str, value: dict[str, Any], nonce: str) -> None:
    path = ROOT / ref
    temporary = path.with_name(path.name + f".{nonce}.tmp")
    if temporary.exists():
        raise ValueError(f"temporary path collision: {temporary}")
    with temporary.open("xb") as stream:
        stream.write(canonical_bytes(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def write_new(ref: str, value: dict[str, Any]) -> None:
    path = ROOT / ref
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(canonical_bytes(value))
        stream.flush()
        os.fsync(stream.fileno())


def unit_by_id(milestone: dict[str, Any], unit_id: str) -> dict[str, Any]:
    matches = [item for item in milestone.get("units", []) if item.get("id") == unit_id]
    if len(matches) != 1:
        raise ValueError(f"milestone unit missing or ambiguous: {unit_id}")
    return matches[0]


def validate_live_success(success: dict[str, Any], intake: dict[str, Any], verification: dict[str, Any]) -> list[dict[str, Any]]:
    if (
        success.get("status") != "pass_all_three_exact_remaining_orbits_promoted_input_verified"
        or success.get("source_ids_in_exact_order") != SOURCE_ORDER
        or success.get("assertions", {}).get("owner_handoff_count") != 1
        or success.get("assertions", {}).get("real_attempt_count") != 3
        or success.get("assertions", {}).get("automatic_retry_performed") is not False
        or success.get("assertions", {}).get("m2_orb_001_requested_or_mutated") is not False
        or success.get("assertions", {}).get("credential_values_read_or_recorded") is not False
        or success.get("bindings", {}).get("active_intake_sha256") != sha256(INTAKE_REF)
        or success.get("bindings", {}).get("active_verification_sha256") != sha256(VERIFICATION_REF)
        or success.get("bindings", {}).get("publication_gate_sha256") != sha256(PUBLICATION_REF)
        or success.get("bindings", {}).get("final_preflight_sha256") != sha256(PREFLIGHT_REF)
    ):
        raise ValueError("continuation success reconciliation differs")
    if (
        intake.get("extensions", {}).get("orbit_continuation_001_status") != "succeeded_all_three_exact_sources"
        or intake.get("extensions", {}).get("current_orbit_state_counts") != {"authorized": 0, "failed": 0, "promoted": 4}
        or verification.get("status") != "active_gate_ready_for_offline_verification"
        or verification.get("bindings", {}).get("active_intake_sha256_current") != sha256(INTAKE_REF)
        or verification.get("bindings", {}).get("latest_promoted_source_id") != "M2-ORB-004"
    ):
        raise ValueError("active orbit controls do not reflect the exact acquisition success")

    results = success.get("results", [])
    if [item.get("source_id") for item in results] != SOURCE_ORDER:
        raise ValueError("continuation result order differs")
    assets = intake.get("assets", [])
    if [item.get("extensions", {}).get("source_id") for item in assets] != ALL_SOURCES:
        raise ValueError("orbit intake source order differs")
    custody_root = (PROJECT_ROOT / Path(*PurePosixPath(intake["custody_root"]).parts)).resolve(strict=True)
    validated: list[dict[str, Any]] = []
    for asset in assets:
        source_id = asset["extensions"]["source_id"]
        observed = asset.get("observed", {})
        destination = (custody_root / Path(*PurePosixPath(asset["destination_relative_path"]).parts)).resolve(strict=True)
        destination.relative_to(custody_root)
        identity = {"size_bytes": destination.stat().st_size, "sha256": sha256_path(destination)}
        if (
            asset.get("state") != "promoted"
            or identity["size_bytes"] != observed.get("promoted_size_bytes")
            or identity["sha256"] != observed.get("promoted_sha256")
            or observed.get("staged_size_bytes") != observed.get("promoted_size_bytes")
            or observed.get("staged_sha256") != observed.get("promoted_sha256")
        ):
            raise ValueError(f"promoted orbit identity differs: {source_id}")
        validated.append({"source_id": source_id, "path": str(destination), **identity})
    return validated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconciled-at-utc", required=True)
    args = parser.parse_args()
    if not args.reconciled_at_utc.endswith("Z") or (ROOT / OUTPUT_REF).exists():
        raise SystemExit("terminal project reconciliation output collision or invalid time")

    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    origin = subprocess.run(["git", "rev-parse", "origin/main"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    publication = load(PUBLICATION_REF)
    activation = load(ACTIVATION_REF)
    control = load(CONTROL_REF)
    preflight = load(PREFLIGHT_REF)
    success = load(SUCCESS_REF)
    intake = load(INTAKE_REF)
    verification = load(VERIFICATION_REF)
    milestone = load(MILESTONE_REF)
    profile = load(PROFILE_REF)
    goal = load(GOAL_REF)
    if (
        head != origin
        or publication.get("github_actions", {}).get("head_sha") != head
        or publication.get("github_actions", {}).get("conclusion") != "success"
        or activation.get("status") != "pass_exact_orbit_continuation_001_activated_final_no_payload_preflight_pending"
        or control.get("status") != "pass_public_ci_exact_continuation_ready_final_preflight_pending"
        or preflight.get("status") != "pass_no_payload_ready_for_single_secret_pipe_handoff"
        or milestone.get("handoff", {}).get("current_checkpoint") != "M2-ORBIT-CONTINUATION-001-IMPLEMENTATION"
        or profile.get("current_checkpoint", {}).get("checkpoint_id") != "M2-ORBIT-CONTINUATION-001-IMPLEMENTATION"
        or goal.get("current_checkpoint") != "M2-ORBIT-CONTINUATION-001-IMPLEMENTATION"
    ):
        raise SystemExit("publication, activation, preflight, or tracked checkpoint differs")
    validated = validate_live_success(success, intake, verification)

    before = {ref: sha256(ref) for ref in [VERIFICATION_REF, MILESTONE_REF, PROFILE_REF, GOAL_REF]}
    implementation = unit_by_id(milestone, "M2-ORBIT-CONTINUATION-001-IMPLEMENTATION")
    continuation = unit_by_id(milestone, "M2-ORBIT-CONTINUATION-001")
    acquire = unit_by_id(milestone, "M2-ORBIT-ACQUIRE")
    orbit_verify = unit_by_id(milestone, "M2-ORBIT-VERIFY")
    if (implementation.get("status"), continuation.get("status"), acquire.get("status"), orbit_verify.get("status")) != (
        "in_progress", "planned", "deferred", "planned"
    ):
        raise SystemExit("orbit milestone units are not at the exact pre-reconciliation state")

    implementation.update({"status": "complete", "disposition": "pass"})
    implementation["outputs"] = [
        "bounded continuation implementation",
        "records/readiness/m2-orbit-continuation-001-implementation-readiness-002.json",
        PUBLICATION_REF,
        ACTIVATION_REF,
        CONTROL_REF,
        PREFLIGHT_REF,
    ]
    implementation["gates"].update({
        "public_ci": "pass",
        "publication_commit": head,
        "public_ci_run_id": publication["github_actions"]["run_id"],
        "publication_gate_sha256": sha256(PUBLICATION_REF),
        "final_no_payload_preflight": "pass",
        "final_preflight_sha256": sha256(PREFLIGHT_REF),
        "synthetic_interruption_and_secret_exposure_tests": "pass",
        "exact_order_and_stop_on_first_failure_tests": "pass",
        "credential_or_source_access_before_public_ci": False,
    })
    implementation["exit_condition_delta"] = {
        "expected": [],
        "observed": ["exact implementation passed public default-branch CI", "final no-payload preflight passed"],
        "decision_value": "enables_dependency",
        "rationale": "The corrected implementation passed public CI before the one owner handoff and three-source sequence.",
    }

    continuation.update({"status": "complete", "disposition": "pass"})
    continuation["inputs"] = [
        "records/source-gates/m2-orbit-continuation-001-approval.json",
        PUBLICATION_REF,
        PREFLIGHT_REF,
        INTAKE_REF,
    ]
    continuation["outputs"] = [
        "external append-only supervisor and attempt evidence",
        *[item["receipt_ref"] for item in success["results"]],
        SUCCESS_REF,
        OUTPUT_REF,
    ]
    continuation["gates"].update({
        "public_ci": "pass",
        "final_no_payload_preflight": "pass",
        "owner_handoff_count": 1,
        "real_attempt_count": 3,
        "completed_source_ids_in_exact_order": SOURCE_ORDER,
        "input_only_verified_source_ids": SOURCE_ORDER,
        "automatic_retry_performed": False,
        "m2_orb_001_requested_or_mutated": False,
        "success_reconciliation_sha256": sha256(SUCCESS_REF),
    })
    continuation["exit_condition_delta"] = {
        "expected": ["EXIT-201-VERIFIED-CUSTODY"],
        "observed": ["EXIT-201-VERIFIED-CUSTODY"],
        "decision_value": "pass_input_only",
        "rationale": "All three remaining exact AUX_RESORB files passed one attempt in fixed order and were promoted without replacement.",
    }

    acquire.update({"status": "complete", "disposition": "pass"})
    acquire["gates"].update({
        "retained_failure_review": "historical_failures_preserved_continuation_complete",
        "promoted_source_ids": ALL_SOURCES,
        "remaining_source_ids": [],
        "remaining_source_requests_authorized_by_current_review": True,
        "remaining_source_requests_released_now": False,
        "continuation_status": "succeeded_all_three_exact_sources",
        "continuation_success_ref": SUCCESS_REF,
        "continuation_success_sha256": sha256(SUCCESS_REF),
        "owner_handoff_count": 1,
        "continuation_real_attempt_count": 3,
    })
    acquire["exit_condition_delta"] = {
        "expected": ["EXIT-201-VERIFIED-CUSTODY"],
        "observed": ["EXIT-201-VERIFIED-CUSTODY"],
        "decision_value": "pass_input_only",
        "rationale": "All four exact restituted orbit files are promoted; failed and superseded M2-ORB-001 evidence remains preserved.",
    }
    acquire["rationale"] = "All four exact S1D AUX_RESORB files are in promoted non-Git custody. Offline set verification remains separate."

    orbit_verify.update({"status": "in_progress", "disposition": None})
    orbit_verify["gates"].update({
        "input_only_verified_source_ids": ALL_SOURCES,
        "remaining_source_ids": [],
        "offline_set_verification": "pending_compatibility_implementation_and_public_ci",
        "continuation_success_ref": SUCCESS_REF,
        "continuation_success_sha256": sha256(SUCCESS_REF),
        "real_eof_reads_started": False,
    })
    orbit_verify["exit_condition_delta"] = {
        "expected": ["EXIT-201-VERIFIED-CUSTODY", "EXIT-202-PIXEL-AND-RIGHTS-QA"],
        "observed": ["EXIT-201-VERIFIED-CUSTODY"],
        "decision_value": "unknown",
        "rationale": "All four inputs are promoted, but the set-level read-only verifier compatibility gate and public CI remain pending.",
    }

    verification["status"] = "active_gate_pending_continuation_compatibility_public_ci"
    verification.setdefault("extensions", {})["continuation_001"] = {
        "success_ref": SUCCESS_REF,
        "success_sha256": sha256(SUCCESS_REF),
        "promoted_source_ids": ALL_SOURCES,
        "offline_file_reads_started": False,
        "next_gate": "project approved endpoint rules and receipt identities into the verifier, then require public CI",
    }
    milestone["handoff"]["current_checkpoint"] = CHECKPOINT
    milestone["handoff"]["next_action"] = NEXT_ACTION
    carry = (
        "Orbit continuation-001 is consumed after one handoff and three successful fixed-order requests. All four AUX_RESORB files are promoted input-only; "
        "this does not authorize another request, orbit application, DEM or radar-pixel action, baseline, change analysis, attribution, or scientific publication."
    )
    if carry not in milestone["handoff"]["do_not_carry_forward"]:
        milestone["handoff"]["do_not_carry_forward"].append(carry)
    profile["current_checkpoint"] = {"checkpoint_id": CHECKPOINT, "expected_branch": "main", "expected_head": None, "next_action": NEXT_ACTION}
    goal["current_checkpoint"] = CHECKPOINT

    nonce = "orbit-continuation-001-postsuccess"
    replace_json(VERIFICATION_REF, verification, nonce)
    replace_json(MILESTONE_REF, milestone, nonce)
    replace_json(PROFILE_REF, profile, nonce)
    replace_json(GOAL_REF, goal, nonce)
    receipt = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ORBIT-CONTINUATION-001-TERMINAL-PROJECT-RECONCILIATION",
        "reconciled_at_utc": args.reconciled_at_utc,
        "status": "pass_all_four_orbits_promoted_offline_verifier_public_ci_pending",
        "bindings": {
            "publication_gate_sha256": sha256(PUBLICATION_REF),
            "activation_sha256": sha256(ACTIVATION_REF),
            "control_reconciliation_sha256": sha256(CONTROL_REF),
            "final_preflight_sha256": sha256(PREFLIGHT_REF),
            "success_reconciliation_sha256": sha256(SUCCESS_REF),
            "active_intake_sha256": sha256(INTAKE_REF),
            "verification_sha256_before": before[VERIFICATION_REF],
            "verification_sha256_after": sha256(VERIFICATION_REF),
            "milestone_sha256_before": before[MILESTONE_REF],
            "milestone_sha256_after": sha256(MILESTONE_REF),
            "profile_sha256_before": before[PROFILE_REF],
            "profile_sha256_after": sha256(PROFILE_REF),
            "goal_sha256_before": before[GOAL_REF],
            "goal_sha256_after": sha256(GOAL_REF),
        },
        "observations": {
            "source_ids": ALL_SOURCES,
            "promoted_identities": validated,
            "owner_handoff_count": 1,
            "continuation_real_attempt_count": 3,
            "automatic_retry_performed": False,
            "current_orbit_state_counts": {"authorized": 0, "failed": 0, "promoted": 4},
        },
        "assertions": {
            "credential_values_read_or_recorded": False,
            "additional_network_request_performed": False,
            "additional_orbit_payload_request_performed": False,
            "m2_orb_001_requested_or_mutated_by_continuation": False,
            "offline_eof_content_read_by_reconciliation": False,
            "orbit_application_performed": False,
            "dem_or_radar_pixel_action_performed": False,
            "baseline_change_attribution_or_publication_performed": False,
        },
        "next_checkpoint": CHECKPOINT,
        "next_action": NEXT_ACTION,
    }
    write_new(OUTPUT_REF, receipt)
    print(json.dumps({"status": receipt["status"], "checkpoint": CHECKPOINT, "output": OUTPUT_REF}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
