#!/usr/bin/env python3
"""Record successful public CI for the blank radar pixel and orbit review."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_REF = "contracts/milestone-002-radar-pixel-orbit-application-001-proposal.json"
BUNDLE_REF = "reviews/m2-radar-pixel-orbit-application-001/review-bundle.json"
CONTRACT_REF = "reviews/m2-radar-pixel-orbit-application-001/review-contract.json"
BLANK_REF = "reviews/m2-radar-pixel-orbit-application-001/blank-response.json"
READINESS_REF = "records/readiness/m2-radar-pixel-orbit-application-001-review-readiness.json"
GATE_REF = "records/readiness/m2-radar-pixel-orbit-application-001-review-publication-gate.json"
RECONCILIATION_REF = "records/readiness/m2-radar-pixel-orbit-application-001-review-publication-reconciliation.json"
MILESTONE_REF = "contracts/milestone-002.json"
PROFILE_REF = "records/project-control-profile.json"
GOAL_REF = "records/long-term-goal.json"
LEDGER_REF = "records/evidence-ledger.jsonl"
PROPOSAL_SHA256 = "3a0f03c5269f4e3e6822c1e31bbe5f19cd288e9e17db67b42990d96b27a4f490"
BUNDLE_SHA256 = "84af38b7e325e862272b97c9f198dc7a3c3aa2371f4c428e36aaaac6e937f633"
CHECKPOINT = "M2-RADAR-PIXEL-ORBIT-APPLICATION-001-REVIEW"
NEXT_ACTION = (
    "Review the exact public M2 radar pixel and orbit application-001 bundle and proposal; "
    "approve, revise, or defer the bounded fixed-order QA route. No implementation, orbit "
    "application, radar pixel processing, baseline, change analysis, attribution, or scientific "
    "publication is authorized before an attested decision."
)


def path(ref: str) -> Path:
    return ROOT / ref


def load(ref: str) -> dict:
    value = json.loads(path(ref).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {ref}")
    return value


def sha256(ref: str) -> str:
    return hashlib.sha256(path(ref).read_bytes()).hexdigest()


def write_json_exclusive(ref: str, value: dict) -> None:
    destination = path(ref)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def write_json_atomic(ref: str, value: dict) -> None:
    destination = path(ref)
    handle, temporary = tempfile.mkstemp(prefix=destination.name + ".", suffix=".tmp", dir=destination.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        os.replace(temporary, destination)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verified-at-utc", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--run-url", required=True)
    parser.add_argument("--required-file-count", required=True, type=int)
    parser.add_argument("--public-test-count", required=True, type=int)
    parser.add_argument("--public-skip-count", required=True, type=int)
    args = parser.parse_args()

    if path(GATE_REF).exists() or path(RECONCILIATION_REF).exists():
        raise SystemExit("publication record collision")
    if not args.verified_at_utc.endswith("Z") or re.fullmatch(r"[0-9a-f]{40}", args.commit_sha) is None:
        raise SystemExit("invalid time or commit SHA")
    if (args.required_file_count, args.public_test_count, args.public_skip_count) != (980, 552, 13):
        raise SystemExit("public validation counts differ from the observed run")
    expected_url = f"https://github.com/drwbkr1/nepal-2026-before-after-map/actions/runs/{args.run_id}"
    if args.run_id <= 0 or args.run_url != expected_url:
        raise SystemExit("invalid GitHub Actions identity")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    origin = subprocess.run(["git", "rev-parse", "origin/main"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    if head != args.commit_sha or origin != args.commit_sha:
        raise SystemExit("publication commit is not current HEAD and origin/main")
    if sha256(PROPOSAL_REF) != PROPOSAL_SHA256 or sha256(BUNDLE_REF) != BUNDLE_SHA256:
        raise SystemExit("exact review packet identity drift")

    blank = load(BLANK_REF)
    readiness = load(READINESS_REF)
    milestone = load(MILESTONE_REF)
    profile = load(PROFILE_REF)
    goal = load(GOAL_REF)
    units = {unit.get("id"): unit for unit in milestone.get("units", []) if isinstance(unit, dict)}
    review = units.get("M2-RADAR-PIXEL-ORBIT-APPLICATION-001-REVIEW")
    if not isinstance(review, dict):
        raise SystemExit("review unit missing")
    if (
        blank.get("completed") is not False
        or blank.get("reviewer", {}).get("attestation") is not False
        or blank.get("responses", [{}])[0].get("decision") is not None
        or readiness.get("status") != "pass_ready_publication_zero_decisions"
        or review.get("gates", {}).get("public_ci") != "pending"
        or review.get("gates", {}).get("human_decision_count") != 0
        or review.get("gates", {}).get("orbit_application_authorized") is not False
        or review.get("gates", {}).get("radar_pixel_processing_authorized") is not False
    ):
        raise SystemExit("review packet is not blank and publication-pending")

    bindings = {
        "proposal_ref": PROPOSAL_REF,
        "proposal_sha256": PROPOSAL_SHA256,
        "review_bundle_ref": BUNDLE_REF,
        "review_bundle_sha256": BUNDLE_SHA256,
        "review_contract_ref": CONTRACT_REF,
        "review_contract_sha256": sha256(CONTRACT_REF),
        "blank_response_ref": BLANK_REF,
        "blank_response_sha256": sha256(BLANK_REF),
        "review_readiness_ref": READINESS_REF,
        "review_readiness_sha256": sha256(READINESS_REF),
    }
    gate = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-001-REVIEW-PUBLICATION-GATE",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_public_default_branch_ci_zero_decision_review_ready",
        "commit_sha": args.commit_sha,
        "public_ci_run_id": args.run_id,
        "public_ci_url": args.run_url,
        "public_ci_conclusion": "success",
        "public_ci_event": "push",
        "repository_required_file_count": args.required_file_count,
        "public_test_count": args.public_test_count,
        "public_intentional_skip_count": args.public_skip_count,
        "bindings": bindings,
        "assertions": {
            "repository_validation_passed": True,
            "full_public_test_suite_passed": True,
            "human_decision_count": 0,
            "owner_review_ready": True,
            "route_implementation_authorized": False,
            "project_data_content_read_after_publication": False,
            "orbit_application_performed": False,
            "radar_pixel_processing_performed": False,
            "external_data_mutated": False,
            "baseline_or_change_analysis_performed": False,
            "scientific_result_established": False,
        },
        "next_action": NEXT_ACTION,
    }
    write_json_exclusive(GATE_REF, gate)
    reconciliation = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-001-REVIEW-PUBLICATION-RECONCILIATION",
        "reconciled_at_utc": args.verified_at_utc,
        "status": "pass_public_gate_owner_review_ready",
        "publication_gate_ref": GATE_REF,
        "publication_gate_sha256": sha256(GATE_REF),
        "commit_sha": args.commit_sha,
        "public_ci_run_id": args.run_id,
        "review_bundle_sha256": BUNDLE_SHA256,
        "proposal_sha256": PROPOSAL_SHA256,
        "current_checkpoint": CHECKPOINT,
        "released_now": {
            "owner_review": True,
            "implementation": False,
            "project_data_content_read": False,
            "orbit_application": False,
            "radar_pixel_processing": False,
            "baseline_or_change_analysis": False,
            "scientific_publication": False,
        },
        "assertions": {
            "human_decision_count": 0,
            "attestation": False,
            "orbit_application_authorized": False,
            "radar_pixel_processing_authorized": False,
            "baseline_or_change_authorized": False,
            "external_data_mutated": False,
            "scientific_result_established": False,
        },
        "next_action": NEXT_ACTION,
    }
    write_json_exclusive(RECONCILIATION_REF, reconciliation)

    review["gates"].update({
        "public_ci": "success",
        "publication_gate_sha256": sha256(GATE_REF),
        "publication_reconciliation_sha256": sha256(RECONCILIATION_REF),
        "publication_commit": args.commit_sha,
        "public_ci_run_id": args.run_id,
    })
    milestone["handoff"]["current_checkpoint"] = CHECKPOINT
    milestone["handoff"]["next_action"] = NEXT_ACTION
    milestone["handoff"]["parallel_checkpoint"] = CHECKPOINT
    milestone["handoff"]["parallel_next_action"] = NEXT_ACTION
    profile["current_checkpoint"]["checkpoint_id"] = CHECKPOINT
    profile["current_checkpoint"]["next_action"] = NEXT_ACTION
    profile["parallel_checkpoints"] = [{"checkpoint_id": CHECKPOINT, "authority_ref": CONTRACT_REF, "next_action": NEXT_ACTION}]
    goal["current_checkpoint"] = CHECKPOINT
    goal["parallel_checkpoints"] = [CHECKPOINT]
    write_json_atomic(MILESTONE_REF, milestone)
    write_json_atomic(PROFILE_REF, profile)
    write_json_atomic(GOAL_REF, goal)

    ledger = {
        "record_id": "EVID-0145",
        "type": "m2_radar_pixel_orbit_application_001_review_publication_gate",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_public_ci_zero_decision_owner_review_ready",
        "claim": "The exact blank radar pixel and orbit application-001 packet passed public default-branch CI. Only owner review is released; no route implementation, project pixel read, orbit application, radar processing, baseline, change analysis, attribution, or scientific publication occurred.",
        "publication_gate_ref": GATE_REF,
        "publication_gate_sha256": sha256(GATE_REF),
        "publication_reconciliation_ref": RECONCILIATION_REF,
        "publication_reconciliation_sha256": sha256(RECONCILIATION_REF),
        "proposal_sha256": PROPOSAL_SHA256,
        "review_bundle_sha256": BUNDLE_SHA256,
        "assertions": {
            "publication_commit": args.commit_sha,
            "public_ci_run_id": args.run_id,
            "public_ci_conclusion": "success",
            "repository_required_file_count": args.required_file_count,
            "public_test_count": args.public_test_count,
            "public_intentional_skip_count": args.public_skip_count,
            "human_decision_count": 0,
            "owner_review_ready": True,
            "route_implementation_authorized": False,
            "project_data_content_read": False,
            "orbit_application_performed": False,
            "radar_pixel_processing_performed": False,
            "baseline_or_change_analysis_performed": False,
            "scientific_result_established": False,
            "current_checkpoint": CHECKPOINT,
        },
        "next_action": NEXT_ACTION,
    }
    with path(LEDGER_REF).open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(ledger, separators=(",", ":"), ensure_ascii=False) + "\n")

    print(json.dumps({"status": reconciliation["status"], "checkpoint": CHECKPOINT, "publication_gate_sha256": sha256(GATE_REF), "publication_reconciliation_sha256": sha256(RECONCILIATION_REF)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
