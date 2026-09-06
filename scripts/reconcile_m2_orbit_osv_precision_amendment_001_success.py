#!/usr/bin/env python3
"""Reconcile the single successful local M2-ORB-001 validation and promotion."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from m2_orbit_osv_precision_amendment_001_core import (
    ATTEMPT_ID,
    DESTINATION_PATH,
    EXTERNAL_RECEIPT_PATH,
    EXPECTED_BLAKE3,
    EXPECTED_MD5,
    EXPECTED_SHA256,
    EXPECTED_SIZE_BYTES,
    STAGING_PATH,
    exact_file_identity,
)


ROOT = Path(__file__).resolve().parents[1]
MILESTONE_REF = "contracts/milestone-002.json"
PROFILE_REF = "records/project-control-profile.json"
GOAL_REF = "records/long-term-goal.json"
INTAKE_REF = "contracts/m2-orbit-intake.json"
SENTINEL_INTAKE_REF = "contracts/m2-intake.json"
APPROVAL_REF = "records/source-gates/m2-orbit-osv-precision-amendment-001-approval.json"
PUBLICATION_REF = "records/readiness/m2-orbit-osv-precision-amendment-001-implementation-publication-gate.json"
PREFLIGHT_REF = "records/readiness/m2-orbit-osv-precision-amendment-001-final-preflight.json"
RESULT_REF = "records/acquisition/m2-orbit-osv-precision-amendment-001-local-validation.json"
OUTPUT_REF = "records/readiness/m2-orbit-osv-precision-amendment-001-terminal-reconciliation.json"
CHECKPOINT = "M2-ORBIT-REMAINING-SOURCES-REVIEW-PREPARATION"
NEXT_ACTION = (
    "Prepare a separately governed zero-decision review for exact M2-ORB-002 through M2-ORB-004. "
    "Do not request an orbit file, obtain or read a token, retry recovery-003, apply orbit data, read radar pixels, act on DEMs, or perform baseline, change, attribution, or scientific-publication work."
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconciled-at-utc", required=True)
    args = parser.parse_args()
    if not args.reconciled_at_utc.endswith("Z") or (ROOT / OUTPUT_REF).exists():
        raise SystemExit("terminal reconciliation output collision or invalid time")

    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    origin = subprocess.run(["git", "rev-parse", "origin/main"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    publication = load(PUBLICATION_REF)
    preflight = load(PREFLIGHT_REF)
    result = load(RESULT_REF)
    external = json.loads(EXTERNAL_RECEIPT_PATH.read_text(encoding="utf-8"))
    if (
        head != origin
        or publication.get("status") != "pass_public_one_second_implementation_before_local_validation"
        or publication.get("github_actions", {}).get("head_sha") != head
        or publication.get("github_actions", {}).get("conclusion") != "success"
        or preflight.get("status") != "pass_no_network_ready_for_one_local_validation"
        or result.get("status") != "pass_exact_m2_orb_001_input_promoted_no_replace"
        or result.get("attempt_id") != ATTEMPT_ID
        or result.get("assertions", {}).get("local_validation_attempt_count") != 1
        or result.get("assertions", {}).get("automatic_retry_performed") is not False
        or result.get("assertions", {}).get("network_requests_performed") is not False
        or external.get("status") != "pass_exact_bytes_promoted_no_replace_staging_preserved"
        or external.get("attempt_id") != ATTEMPT_ID
        or result.get("bindings", {}).get("external_receipt_sha256") != sha256_path(EXTERNAL_RECEIPT_PATH)
    ):
        raise SystemExit("publication, preflight, local result, or external receipt differs")

    expected_identity = {
        "size_bytes": EXPECTED_SIZE_BYTES,
        "sha256": EXPECTED_SHA256,
        "md5": EXPECTED_MD5,
        "blake3": EXPECTED_BLAKE3,
    }
    staging_identity = exact_file_identity(STAGING_PATH)
    destination_identity = exact_file_identity(DESTINATION_PATH)
    if (
        staging_identity != expected_identity
        or destination_identity != expected_identity
        or result.get("result", {}).get("source_identity_after") != expected_identity
        or result.get("result", {}).get("destination_identity") != expected_identity
        or result.get("result", {}).get("inspection", {}).get("status") != "pass_orbit_input_only"
        or result.get("result", {}).get("inspection", {}).get("xml", {}).get("endpoint_tolerance_seconds") != 1.0
        or result.get("result", {}).get("inspection", {}).get("xml", {}).get("last_endpoint_shortfall_seconds") != 0.031829
        or result.get("result", {}).get("staging_preserved") is not True
        or result.get("result", {}).get("destination_created_without_replace") is not True
    ):
        raise SystemExit("promoted or preserved byte identity and input-only inspection differ")

    intake = load(INTAKE_REF)
    sentinel_intake = load(SENTINEL_INTAKE_REF)
    milestone = load(MILESTONE_REF)
    profile = load(PROFILE_REF)
    goal = load(GOAL_REF)
    assets = intake.get("assets", [])
    if len(assets) != 4 or [item.get("asset_id") for item in assets] != [f"m2-orb-{index:03d}" for index in range(1, 5)]:
        raise SystemExit("orbit intake asset identity differs")
    asset = assets[0]
    prior_attempts = asset.get("attempts", [])
    if (
        asset.get("state") != "failed"
        or len(prior_attempts) != 2
        or [item.get("outcome") for item in prior_attempts] != ["failed", "failed"]
        or asset.get("failure", {}).get("code") != "osv_times_do_not_span_validity"
        or any(item.get("state") != "authorized" or item.get("attempts") != [] for item in assets[1:])
    ):
        raise SystemExit("active orbit intake is not at the exact pre-reconciliation state")
    sentinel_assets = sentinel_intake.get("assets", [])
    if any(
        next((item for item in sentinel_assets if item.get("asset_id") == f"m1-src-{index:03d}"), {}).get("state") != "promoted"
        for index in range(1, 7)
    ):
        raise SystemExit("six bound Sentinel sources are not promoted")

    before = {
        "intake": sha256(INTAKE_REF),
        "milestone": sha256(MILESTONE_REF),
        "profile": sha256(PROFILE_REF),
        "goal": sha256(GOAL_REF),
    }
    asset["observed"] = {
        "staged_sha256": EXPECTED_SHA256,
        "staged_size_bytes": EXPECTED_SIZE_BYTES,
        "promoted_sha256": EXPECTED_SHA256,
        "promoted_size_bytes": EXPECTED_SIZE_BYTES,
    }
    asset["state"] = "promoted"
    asset["attempts"].append({
        "attempt_id": ATTEMPT_ID,
        "started_at": result["executed_at_utc"],
        "completed_at": result["executed_at_utc"],
        "outcome": "promoted",
        "extensions": {
            "source_id": "M2-ORB-001",
            "amendment_id": "M2-ORBIT-OSV-PRECISION-AMENDMENT-001",
            "local_validation_result_ref": RESULT_REF,
            "local_validation_result_sha256": sha256(RESULT_REF),
            "external_receipt_path": str(EXTERNAL_RECEIPT_PATH),
            "external_receipt_sha256": sha256_path(EXTERNAL_RECEIPT_PATH),
            "preserved_staging_path": str(STAGING_PATH),
            "network_requests_performed": False,
            "credential_value_recorded": False,
            "no_replace_promotion": True,
        },
    })
    asset["failure"] = None
    extension = asset.setdefault("extensions", {})
    extension["retained_failed_attempt_ids"] = [
        "m2-orb-001-20260904t050937z-8ed21d05",
        "m2-orb-001-recovery-002-20260906t183804z-e5883324",
    ]
    extension["retained_recovery_003_outcome_ref"] = "records/acquisition/m2-orbit-recovery-003-outcome-reconciliation.json"
    extension["retained_recovery_003_outcome_sha256"] = sha256(extension["retained_recovery_003_outcome_ref"])
    extension["osv_precision_amendment_001"] = {
        "approval_ref": APPROVAL_REF,
        "approval_sha256": sha256(APPROVAL_REF),
        "maximum_endpoint_tolerance_seconds": 1.0,
        "local_validation_attempt_count": 1,
        "input_only_verification_status": "pass_orbit_input_only",
        "result_ref": RESULT_REF,
        "result_sha256": sha256(RESULT_REF),
        "staging_preserved": True,
    }
    intake_extensions = intake.setdefault("extensions", {})
    intake_extensions.update({
        "payload_bytes_transferred": EXPECTED_SIZE_BYTES,
        "status": "active_remaining_orbit_sources_review_required",
        "sentinel_custody_prerequisite_status": "all_six_promoted_and_container_verified",
        "current_orbit_state_counts": {"authorized": 3, "failed": 0, "promoted": 1},
        "current_sentinel_state_counts": {"authorized": 0, "failed": 0, "promoted": 6},
        "osv_precision_amendment_001_result_ref": RESULT_REF,
        "osv_precision_amendment_001_result_sha256": sha256(RESULT_REF),
    })

    implementation = unit_by_id(milestone, "M2-ORBIT-OSV-PRECISION-AMENDMENT-001-IMPLEMENTATION")
    local_action = unit_by_id(milestone, "M2-ORBIT-OSV-PRECISION-AMENDMENT-001")
    orbit_acquire = unit_by_id(milestone, "M2-ORBIT-ACQUIRE")
    orbit_verify = unit_by_id(milestone, "M2-ORBIT-VERIFY")
    implementation.update({"status": "complete", "disposition": "pass"})
    implementation["gates"].update({
        "public_ci": "pass",
        "publication_commit": head,
        "public_ci_run_id": publication["github_actions"]["run_id"],
        "publication_gate_sha256": sha256(PUBLICATION_REF),
        "final_no_network_preflight": "pass",
        "final_preflight_sha256": sha256(PREFLIGHT_REF),
        "real_staged_file_read": True,
        "local_validation_started": True,
    })
    implementation["exit_condition_delta"] = {
        "expected": [],
        "observed": ["exact implementation passed public default-branch CI", "final no-network preflight passed"],
        "decision_value": "enables_dependency",
        "rationale": "Public CI passed before the first real staged-byte read and the final preflight released only one local validation.",
    }
    local_action.update({
        "status": "complete",
        "disposition": "pass",
        "inputs": [APPROVAL_REF, PUBLICATION_REF, PREFLIGHT_REF, RESULT_REF],
        "outputs": [RESULT_REF, OUTPUT_REF],
    })
    local_action["gates"].update({
        "public_ci": "pass",
        "final_no_network_preflight": "pass",
        "local_validation_attempt_count": 1,
        "input_only_verification": "pass_orbit_input_only",
        "staged_file_promoted": True,
        "staging_preserved": True,
    })
    local_action["exit_condition_delta"] = {
        "expected": ["EXIT-201-VERIFIED-CUSTODY"],
        "observed": ["EXIT-201-VERIFIED-CUSTODY"],
        "decision_value": "pass_input_only",
        "rationale": "The single approved local action validated and promoted exact M2-ORB-001 without replacement or network access while preserving staging evidence.",
    }
    orbit_acquire["gates"].update({
        "retained_failure_review": "m2_orb_001_promoted_remaining_sources_review_required",
        "osv_precision_amendment_status": "pass_exact_m2_orb_001_promoted",
        "promoted_source_ids": ["M2-ORB-001"],
        "remaining_source_ids": ["M2-ORB-002", "M2-ORB-003", "M2-ORB-004"],
        "remaining_source_requests_authorized_by_current_amendment": False,
    })
    orbit_acquire["exit_condition_delta"] = {
        "expected": ["EXIT-201-VERIFIED-CUSTODY"],
        "observed": ["M2-ORB-001 exact input-only custody"],
        "decision_value": "partial_progress_defer_remaining",
        "rationale": "M2-ORB-001 is promoted and input-only verified; no current bounded decision releases requests for M2-ORB-002 through M2-ORB-004.",
    }
    orbit_acquire["rationale"] = "One of four exact restituted orbit files is promoted and input-only verified. The other three remain unrequested pending a separate zero-decision review."
    orbit_verify["gates"].update({
        "input_only_verified_source_ids": ["M2-ORB-001"],
        "remaining_source_ids": ["M2-ORB-002", "M2-ORB-003", "M2-ORB-004"],
    })
    milestone["handoff"]["current_checkpoint"] = CHECKPOINT
    milestone["handoff"]["next_action"] = NEXT_ACTION
    carry = "The OSV precision amendment is consumed after one successful local validation and promotion of M2-ORB-001; it authorizes no request for M2-ORB-002 through M2-ORB-004 and no downstream processing."
    if carry not in milestone["handoff"]["do_not_carry_forward"]:
        milestone["handoff"]["do_not_carry_forward"].append(carry)
    profile["current_checkpoint"] = {"checkpoint_id": CHECKPOINT, "expected_branch": "main", "expected_head": None, "next_action": NEXT_ACTION}
    profile["gate_policy"]["explicit_human_gates"] = [
        item for item in profile["gate_policy"]["explicit_human_gates"]
        if item.get("unit_id") != "M2-ORBIT-OSV-PRECISION-AMENDMENT-001-REVIEW"
    ]
    goal["current_checkpoint"] = CHECKPOINT

    nonce = "osv-precision-amendment-001-terminal-success"
    replace_json(INTAKE_REF, intake, nonce)
    replace_json(MILESTONE_REF, milestone, nonce)
    replace_json(PROFILE_REF, profile, nonce)
    replace_json(GOAL_REF, goal, nonce)
    receipt = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ORBIT-OSV-PRECISION-AMENDMENT-001-TERMINAL-RECONCILIATION-001",
        "reconciled_at_utc": args.reconciled_at_utc,
        "status": "pass_exact_m2_orb_001_promoted_remaining_sources_review_required",
        "bindings": {
            "approval_sha256": sha256(APPROVAL_REF),
            "publication_gate_sha256": sha256(PUBLICATION_REF),
            "final_preflight_sha256": sha256(PREFLIGHT_REF),
            "local_validation_result_sha256": sha256(RESULT_REF),
            "external_receipt_sha256": sha256_path(EXTERNAL_RECEIPT_PATH),
            "intake_sha256_before": before["intake"],
            "intake_sha256_after": sha256(INTAKE_REF),
            "milestone_sha256_before": before["milestone"],
            "milestone_sha256_after": sha256(MILESTONE_REF),
            "profile_sha256_before": before["profile"],
            "profile_sha256_after": sha256(PROFILE_REF),
            "goal_sha256_before": before["goal"],
            "goal_sha256_after": sha256(GOAL_REF),
        },
        "observations": {
            "source_id": "M2-ORB-001",
            "attempt_id": ATTEMPT_ID,
            "promoted_identity": destination_identity,
            "preserved_staging_identity": staging_identity,
            "input_only_verification_status": "pass_orbit_input_only",
            "endpoint_tolerance_seconds": 1.0,
            "last_endpoint_shortfall_seconds": 0.031829,
            "orbit_state_counts": {"authorized": 3, "failed": 0, "promoted": 1},
        },
        "assertions": {
            "local_validation_attempt_count": 1,
            "automatic_retry_performed": False,
            "network_requests_performed_by_reconciliation": False,
            "credential_values_read_or_recorded": False,
            "staging_preserved": True,
            "destination_created_without_replace": True,
            "other_orbit_source_requested": False,
            "orbit_application_performed": False,
            "dem_or_radar_pixels_processed": False,
            "baseline_or_change_analysis_performed": False,
            "scientific_result_established": False,
        },
        "next_checkpoint": CHECKPOINT,
        "next_action": NEXT_ACTION,
    }
    write_new(OUTPUT_REF, receipt)
    print(json.dumps({"status": receipt["status"], "checkpoint": CHECKPOINT, "output": OUTPUT_REF}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
