#!/usr/bin/env python3
"""Record public CI and open owner review for the exact receipt-recovery packet."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-delayed-import-probe-receipt-recovery-001"
PROPOSAL_REF = "contracts/milestone-002-radar-delayed-import-probe-receipt-recovery-001-proposal.json"
BUNDLE_REF = f"reviews/{PREFIX}/review-bundle.json"
CONTRACT_REF = f"reviews/{PREFIX}/review-contract.json"
BLANK_REF = f"reviews/{PREFIX}/blank-response.json"
READINESS_REF = f"records/readiness/{PREFIX}-review-readiness.json"
PUBLICATION_APPROVAL_REF = f"records/source-gates/{PREFIX}-review-publication-approval.json"
ACTIVATION_REF = f"records/readiness/{PREFIX}-review-publication-activation.json"
GATE_REF = f"records/readiness/{PREFIX}-review-publication-gate.json"
RECONCILIATION_REF = f"records/readiness/{PREFIX}-review-publication-reconciliation.json"
MILESTONE_REF = "contracts/milestone-002.json"
PROFILE_REF = "records/project-control-profile.json"
GOAL_REF = "records/long-term-goal.json"
LEDGER_REF = "records/evidence-ledger.jsonl"

PROPOSAL_SHA256 = "9bbe934bd1dcbe7d1b0700b83473db2ab1a130c13fa6d183d3b1a247dfe88e09"
BUNDLE_SHA256 = "df43e0d93f1d40aa85fb1f8730cc57d596fcc4345299b0939b22f822321a9695"
PUBLICATION_CHECKPOINT = "M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-REVIEW-PUBLICATION"
CHECKPOINT = "M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-REVIEW"
UNIT_ID = "M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-REVIEW"
NEXT_ACTION = (
    "Review the exact public M2 radar delayed-import probe receipt-recovery-001 bundle and proposal; approve, "
    "revise, or defer the bounded receipt-durability correction and one fresh disposable attempt. No "
    "implementation, ArcPy invocation, corpus creation, new attempt, project-data or external-custody access, radar "
    "processing, baseline or change analysis, attribution, or scientific publication is authorized before an exact "
    "attested decision."
)


def path(ref: str) -> Path:
    return ROOT / ref


def sha256(ref: str) -> str:
    return hashlib.sha256(path(ref).read_bytes()).hexdigest()


def load(ref: str) -> dict[str, Any]:
    value = json.loads(path(ref).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {ref}")
    return value


def write_json_exclusive(ref: str, value: dict[str, Any]) -> None:
    destination = path(ref)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def write_json_atomic(ref: str, value: dict[str, Any]) -> None:
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


def git_value(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


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
    if (args.required_file_count, args.public_test_count, args.public_skip_count) != (1098, 600, 13):
        raise SystemExit("public validation counts differ from the expected exact packet run")
    expected_url = f"https://github.com/drwbkr1/nepal-2026-before-after-map/actions/runs/{args.run_id}"
    if args.run_id <= 0 or args.run_url != expected_url:
        raise SystemExit("invalid GitHub Actions identity")

    head = git_value("rev-parse", "HEAD")
    origin = git_value("rev-parse", "origin/main")
    if head != args.commit_sha or origin != args.commit_sha:
        raise SystemExit("publication commit is not current HEAD and origin/main")
    if sha256(PROPOSAL_REF) != PROPOSAL_SHA256 or sha256(BUNDLE_REF) != BUNDLE_SHA256:
        raise SystemExit("exact authorized packet identity drift")

    approval = load(PUBLICATION_APPROVAL_REF)
    activation = load(ACTIVATION_REF)
    contract = load(CONTRACT_REF)
    blank = load(BLANK_REF)
    readiness = load(READINESS_REF)
    milestone = load(MILESTONE_REF)
    profile = load(PROFILE_REF)
    goal = load(GOAL_REF)
    units = {item.get("id"): item for item in milestone.get("units", []) if isinstance(item, dict)}
    review = units.get(UNIT_ID)
    if not isinstance(review, dict):
        raise SystemExit("receipt-recovery review unit missing")
    if (
        approval.get("status") != "approved_exact_zero_decision_review_publication_only"
        or activation.get("status") != "pass_exact_publication_authority_activated_public_ci_pending"
        or contract.get("status") != "locally_prepared_not_public_owner_response_not_yet_open"
        or contract.get("workflow_authority", {}).get("review_response_open") is not False
        or blank.get("completed") is not False
        or blank.get("human_decision_count") != 0
        or blank.get("responses", [{}])[0].get("decision") is not None
        or readiness.get("status") != "pass_local_zero_decision_packet_ready_publication_authority_required"
        or review.get("status") != "planned"
        or review.get("gates", {}).get("public_ci") != "pending"
        or review.get("gates", {}).get("review_response_open") is not False
        or review.get("gates", {}).get("human_decision_count") != 0
        or review.get("gates", {}).get("implementation_authorized") is not False
        or review.get("gates", {}).get("new_probe_attempt_authorized") is not False
        or milestone.get("handoff", {}).get("current_checkpoint") != PUBLICATION_CHECKPOINT
        or profile.get("current_checkpoint", {}).get("checkpoint_id") != PUBLICATION_CHECKPOINT
        or goal.get("current_checkpoint") != PUBLICATION_CHECKPOINT
    ):
        raise SystemExit("packet is not in exact publication-pending state")

    bindings = {
        "publication_approval_ref": PUBLICATION_APPROVAL_REF,
        "publication_approval_sha256": sha256(PUBLICATION_APPROVAL_REF),
        "publication_activation_ref": ACTIVATION_REF,
        "publication_activation_sha256": sha256(ACTIVATION_REF),
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
        "record_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-REVIEW-PUBLICATION-GATE",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_public_default_branch_ci_zero_decision_owner_review_ready",
        "commit_sha": args.commit_sha,
        "public_ci_run_id": args.run_id,
        "public_ci_url": args.run_url,
        "public_ci_conclusion": "success",
        "public_ci_event": "push",
        "repository_required_file_count": args.required_file_count,
        "public_test_count": args.public_test_count,
        "public_intentional_skip_count": args.public_skip_count,
        "bindings": bindings,
        "released_now": {
            "owner_proposal_review": True,
            "implementation": False,
            "arcpy_invocation": False,
            "disposable_corpus_creation": False,
            "new_probe_attempt": False,
            "project_data_or_external_custody_access": False,
            "radar_processing": False,
            "baseline_or_change_analysis": False,
            "attribution": False,
            "scientific_publication": False,
        },
        "assertions": {
            "repository_validation_passed": True,
            "full_public_test_suite_passed": True,
            "packet_human_decision_count": 0,
            "owner_proposal_decision_recorded": False,
            "owner_review_ready": True,
            "protected_probe_code_modified": False,
            "arcpy_invoked": False,
            "disposable_corpus_created": False,
            "new_attempt_created": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "radar_processing_executed": False,
            "historical_root_cause_established": False,
            "radar_recovery_readiness_established": False,
            "scientific_result_established": False,
        },
        "next_action": NEXT_ACTION,
    }
    write_json_exclusive(GATE_REF, gate)

    reconciliation = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-REVIEW-PUBLICATION-RECONCILIATION",
        "reconciled_at_utc": args.verified_at_utc,
        "status": "pass_public_gate_owner_review_ready",
        "publication_gate_ref": GATE_REF,
        "publication_gate_sha256": sha256(GATE_REF),
        "commit_sha": args.commit_sha,
        "public_ci_run_id": args.run_id,
        "review_bundle_sha256": BUNDLE_SHA256,
        "proposal_sha256": PROPOSAL_SHA256,
        "current_checkpoint": CHECKPOINT,
        "released_now": dict(gate["released_now"]),
        "assertions": dict(gate["assertions"]),
        "next_action": NEXT_ACTION,
    }
    write_json_exclusive(RECONCILIATION_REF, reconciliation)

    review["status"] = "in_progress"
    review["outputs"] = [GATE_REF, RECONCILIATION_REF]
    review["gates"].update(
        {
            "public_ci": "success",
            "review_response_open": True,
            "publication_gate_sha256": sha256(GATE_REF),
            "publication_reconciliation_sha256": sha256(RECONCILIATION_REF),
            "publication_commit": args.commit_sha,
            "public_ci_run_id": args.run_id,
        }
    )
    milestone["handoff"].update(
        {
            "current_checkpoint": CHECKPOINT,
            "next_action": NEXT_ACTION,
            "parallel_checkpoint": CHECKPOINT,
            "parallel_next_action": NEXT_ACTION,
        }
    )
    profile["current_checkpoint"] = {
        "checkpoint_id": CHECKPOINT,
        "expected_branch": "main",
        "expected_head": None,
        "next_action": NEXT_ACTION,
    }
    profile["parallel_checkpoints"] = [
        {"checkpoint_id": CHECKPOINT, "authority_ref": CONTRACT_REF, "next_action": NEXT_ACTION}
    ]
    goal["current_checkpoint"] = CHECKPOINT
    goal["parallel_checkpoints"] = [CHECKPOINT]
    write_json_atomic(MILESTONE_REF, milestone)
    write_json_atomic(PROFILE_REF, profile)
    write_json_atomic(GOAL_REF, goal)

    evidence = {
        "record_id": "EVID-0174",
        "type": "m2_radar_delayed_import_probe_receipt_recovery_001_review_publication_gate",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_public_ci_zero_decision_owner_review_ready",
        "claim": "The exact blank receipt-recovery packet passed public default-branch CI. Only owner proposal review is released; no implementation, ArcPy, corpus, new attempt, project-data or external-custody access, radar processing, baseline, change analysis, attribution, or scientific publication occurred.",
        "publication_gate_sha256": sha256(GATE_REF),
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
            "packet_human_decision_count": 0,
            "owner_review_ready": True,
            "owner_proposal_decision_recorded": False,
            "implementation_authorized": False,
            "arcpy_invoked": False,
            "disposable_corpus_created": False,
            "new_attempt_created": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "radar_processing_executed": False,
            "scientific_result_established": False,
            "current_checkpoint": CHECKPOINT,
        },
        "next_action": NEXT_ACTION,
    }
    with path(LEDGER_REF).open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(evidence, separators=(",", ":"), ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {
                "status": reconciliation["status"],
                "checkpoint": CHECKPOINT,
                "publication_gate_sha256": sha256(GATE_REF),
                "publication_reconciliation_sha256": sha256(RECONCILIATION_REF),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
