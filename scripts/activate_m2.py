#!/usr/bin/env python3
"""Activate M2 from the exact locked and reconciled owner approval."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BUNDLE_SHA256 = "e8d105970d64c43d955ff459ba9e5d5a3a1e4fb4f95874aa67f384e6b293a35d"
PLAN_SHA256 = "6261dc61061cb962f22163755047f080e309ed2d746cdcdd61e6cf61d7ec2a8d"
PROPOSAL_SHA256 = "a71f36fd667a26ff3cfabb12828ce719f566ba9c39db4b3c82adfad84c7b853c"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def serialized(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2) + "\n").encode("utf-8")


def create_new(relative: str, value: dict[str, Any]) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(serialized(value))
        handle.flush()


def replace(relative: str, value: dict[str, Any]) -> None:
    path = ROOT / relative
    temporary = path.with_name(path.name + ".activation-tmp")
    if temporary.exists():
        raise SystemExit(f"temporary activation path already exists: {temporary}")
    with temporary.open("xb") as handle:
        handle.write(serialized(value))
        handle.flush()
    temporary.replace(path)


def unit(
    *,
    unit_id: str,
    purpose: str,
    depends_on: list[str],
    action_class: str,
    human_gate: bool,
    status: str,
    inputs: list[str],
    outputs: list[str],
    gates: dict[str, Any],
    disposition: str | None,
    expected: list[str],
    observed: list[str],
    decision_value: str,
    rationale: str,
    next_dependency: str | None,
) -> dict[str, Any]:
    return {
        "id": unit_id,
        "purpose": purpose,
        "depends_on": depends_on,
        "action_class": action_class,
        "human_gate": human_gate,
        "status": status,
        "inputs": inputs,
        "outputs": outputs,
        "gates": gates,
        "disposition": disposition,
        "retained_failures": [],
        "exit_condition_delta": {
            "expected": expected,
            "observed": observed,
            "decision_value": decision_value,
            "rationale": rationale,
        },
        "next_dependency": next_dependency,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activated-at-utc", required=True)
    args = parser.parse_args()

    for relative, expected in (
        ("reviews/m2-activation/review-bundle.json", BUNDLE_SHA256),
        ("records/acquisition-plan.json", PLAN_SHA256),
        ("contracts/milestone-002-proposal.json", PROPOSAL_SHA256),
    ):
        if sha256(ROOT / relative) != expected:
            raise SystemExit(f"approved artifact hash differs: {relative}")

    reconciliation_ref = "records/source-gates/m2-activation-review-reconciliation.json"
    reconciliation = load(reconciliation_ref)
    review_contract = load("reviews/m2-activation/review-contract.json")
    if reconciliation.get("status") != "reconciled_exact_human_response":
        raise SystemExit("M2 activation response is not reconciled")
    if reconciliation.get("review_id") != "m2-activation-review-001":
        raise SystemExit("M2 activation review identity differs")
    if reconciliation.get("contract_sha256") != sha256(ROOT / "reviews/m2-activation/review-contract.json"):
        raise SystemExit("M2 reconciliation does not bind the review contract")
    if reconciliation.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}:
        raise SystemExit("M2 activation is not a single exact approval")
    if reconciliation.get("human_decisions_fabricated") is not False:
        raise SystemExit("M2 reconciliation reports fabricated human decisions")
    if review_contract.get("review_bundle", {}).get("manifest_sha256") != BUNDLE_SHA256:
        raise SystemExit("M2 review contract bundle binding differs")

    response_sha = reconciliation["response_sha256"]
    receipt_sha = reconciliation["receipt_sha256"]
    locked_root = ROOT / "reviews/m2-activation/locked"
    response_candidates = list(locked_root.glob(f"*response-{response_sha[:16]}.json"))
    receipt_candidates = list(locked_root.glob(f"*receipt-{response_sha[:16]}.json"))
    if len(response_candidates) != 1 or sha256(response_candidates[0]) != response_sha:
        raise SystemExit("exact locked M2 response is missing or ambiguous")
    if len(receipt_candidates) != 1 or sha256(receipt_candidates[0]) != receipt_sha:
        raise SystemExit("exact M2 lock receipt is missing or ambiguous")

    approval_ref = "records/source-gates/m2-activation-approval.json"
    active_contract_ref = "contracts/milestone-002.json"
    if (ROOT / approval_ref).exists() or (ROOT / active_contract_ref).exists():
        raise SystemExit("M2 activation output already exists; refusing replacement")

    approval = {
        "schema_version": "1.0",
        "approval_id": "NEPAL-M2-ACTIVATION-APPROVAL-001",
        "status": "approved",
        "approved_at_utc": args.activated_at_utc,
        "review_id": "m2-activation-review-001",
        "review_bundle_id": "m2-activation-review-bundle-001",
        "review_bundle_manifest_sha256": BUNDLE_SHA256,
        "acquisition_plan_ref": "records/acquisition-plan.json",
        "acquisition_plan_sha256": PLAN_SHA256,
        "review_reconciliation_ref": reconciliation_ref,
        "review_reconciliation_sha256": sha256(ROOT / reconciliation_ref),
        "locked_response_sha256": response_sha,
        "lock_receipt_sha256": receipt_sha,
        "human_decision_count": 1,
        "decision_counts": {"approve": 1, "revise": 0, "defer": 0},
        "approval_scope": "Activate only the bounded M2 actions stated in the exact reviewed acquisition plan and proposal.",
        "authorized_next_actions": [
            "perform a fresh storage and path preflight",
            "create the exact external non-Git custody root after that preflight passes",
            "use an owner-controlled existing Copernicus account or authenticated session",
            "download only the eight exact approved provider products",
            "verify checksums, archive structure, bands, pixels, coverage, access-time rights, baseline fitness, and registration",
            "preserve failed, partial, corrupt, deferred, inconclusive, and superseded attempts",
        ],
        "does_not_authorize": [
            "accept new or changed provider terms",
            "create or recover an account or change account security",
            "disclose, copy, log, or commit credentials, tokens, cookies, or authorization headers",
            "incur cost or use a paid route",
            "download any product outside the eight exact approved identities",
            "use or redistribute restricted high-resolution imagery",
            "select a repository license",
            "publish scientific conclusions, event attribution, or emergency guidance",
            "store imagery, rasters, geodatabases, or ArcGIS packages in Git",
        ],
        "human_decisions_fabricated": False,
    }
    approval_sha = hashlib.sha256(serialized(approval)).hexdigest()

    action_classes = [
        "read_only_inspection",
        "deterministic_validation",
        "metadata_capture",
        "routine_qa",
        "evidence_recording",
        "project_control",
        "update_project_records",
        "reversible_remediation",
        "external_publication",
        "credential_or_identity",
        "data_acquisition",
        "data_processing",
    ]
    active_contract = {
        "schema_version": "1.0",
        "milestone_id": "NEPAL-MAP-M002",
        "project_profile_ref": "records/project-control-profile.json",
        "status": "active",
        "authority": {
            "mode": "inherited",
            "authority_ref": approval_ref,
            "authorized_action_classes": action_classes,
            "user_instruction": "I authorize only the bounded actions stated in the reviewed plan.",
            "repository_controls": ["AGENTS.md", "records/acquisition-plan.json", "docs/M2_EXECUTION_RUNBOOK.md"],
            "active_contract": active_contract_ref,
            "verified_at_utc": args.activated_at_utc,
            "expires_at_utc": None,
            "approval_sha256": approval_sha,
            "review_bundle_sha256": BUNDLE_SHA256,
            "acquisition_plan_sha256": PLAN_SHA256,
        },
        "scope": {
            "objective": "Acquire the eight approved Sentinel products into verified non-Git custody and build a reproducible pre-event optical and radar baseline in EPSG:32645.",
            "allowed_paths": [
                "records/acquisition",
                "records/baseline",
                "records/readiness",
                "records/source-gates",
                "contracts",
                "config/qa",
                "docs",
                "scripts",
                "tests",
                "C:/Projects/Active/nepal-2026-before-after-map-data",
            ],
            "forbidden_work": approval["does_not_authorize"],
            "reversible_actions": [
                "create the approved external custody structure after a passing fresh preflight",
                "write append-only transfer attempts to unique staging paths",
                "resume only when server range and remote identity controls pass",
                "build derived baseline rasters in external versioned attempt paths",
                "update public control records and validation tooling",
            ],
            "stop_conditions": [
                "login, multi-factor authentication, or account recovery requires owner action",
                "new or changed terms require acceptance",
                "any product identity, size, checksum, entitlement, online state, or access route differs from the approved plan",
                "available free space is below 60 GiB before acquisition begins",
                "a transfer redirects to an unapproved provider or paid route",
                "a destination collision, symlink, traversal, or non-atomic promotion risk is detected",
            ],
        },
        "entry_conditions": [
            {"id": "ENTRY-201-M1-COMPLETE", "status": "pass", "evidence": ["contracts/milestone-001.json", "records/source-gates/source-manifest-approval.json"]},
            {"id": "ENTRY-202-PLAN-HASH-BOUND", "status": "pass", "evidence": ["records/acquisition-plan.json", "reviews/m2-activation/review-bundle.json"]},
            {"id": "ENTRY-203-OWNER-ACTIVATION", "status": "pass", "evidence": [approval_ref, reconciliation_ref]},
        ],
        "exit_conditions": [
            {"id": "EXIT-201-VERIFIED-CUSTODY", "status": "pending", "evidence": []},
            {"id": "EXIT-202-PIXEL-AND-RIGHTS-QA", "status": "pending", "evidence": []},
            {"id": "EXIT-203-PRE-EVENT-BASELINE", "status": "pending", "evidence": []},
            {"id": "EXIT-204-REGISTRATION-QA", "status": "pending", "evidence": []},
        ],
        "units": [
            unit(
                unit_id="M2-ACTIVATE", purpose="Lock and reconcile the exact owner decision that activates the reviewed M2 boundary.", depends_on=[], action_class="authority_broadening", human_gate=True, status="complete",
                inputs=["reviews/m2-activation/review-bundle.json", "reviews/m2-activation/review-contract.json"], outputs=[approval_ref, reconciliation_ref],
                gates={"owner_decision": "approve", "attestation": True, "response_locked_before_reconciliation": True, "review_bundle_sha256": BUNDLE_SHA256, "acquisition_plan_sha256": PLAN_SHA256}, disposition="pass",
                expected=[], observed=[], decision_value="enables_dependency", rationale="One exact completed and attested approval was locked and reconciled without fabricated decisions.", next_dependency="M2-CUSTODY-PREFLIGHT",
            ),
            unit(
                unit_id="M2-CUSTODY-PREFLIGHT", purpose="Revalidate terms, product availability, local paths, collisions, and free space before any custody mutation.", depends_on=["M2-ACTIVATE"], action_class="data_acquisition", human_gate=False, status="ready",
                inputs=[approval_ref, "records/acquisition-plan.json", "contracts/m2-intake-candidate.json"], outputs=["records/acquisition/preflight.json"], gates={}, disposition=None,
                expected=[], observed=[], decision_value="unknown", rationale="Owner activation makes a fresh non-mutating preflight eligible; its live checks have not run.", next_dependency="M2-ACQUIRE",
            ),
            unit(
                unit_id="M2-ACQUIRE", purpose="Download only the eight exact products into append-only external custody with collision-safe promotion.", depends_on=["M2-CUSTODY-PREFLIGHT"], action_class="data_acquisition", human_gate=False, status="planned",
                inputs=["records/acquisition/preflight.json", "records/acquisition-plan.json"], outputs=["external custody products", "records/acquisition/product receipts"], gates={}, disposition=None,
                expected=["EXIT-201-VERIFIED-CUSTODY"], observed=[], decision_value="unknown", rationale="Acquisition cannot begin until the fresh preflight passes.", next_dependency="M2-VERIFY",
            ),
            unit(
                unit_id="M2-VERIFY", purpose="Verify exact bytes, provider checksum, archive safety, SAFE structure, access-time rights, and analysis-critical content.", depends_on=["M2-ACQUIRE"], action_class="routine_qa", human_gate=False, status="planned",
                inputs=["external custody products", "contracts/m2-offline-verification-candidate.json"], outputs=["records/acquisition/verification-summary.json"], gates={}, disposition=None,
                expected=["EXIT-201-VERIFIED-CUSTODY", "EXIT-202-PIXEL-AND-RIGHTS-QA"], observed=[], decision_value="unknown", rationale="No acquired bytes are available for verification yet.", next_dependency="M2-BASELINE",
            ),
            unit(
                unit_id="M2-BASELINE", purpose="Create and validate independent pre-event optical and radar reference layers in EPSG:32645.", depends_on=["M2-VERIFY"], action_class="data_processing", human_gate=False, status="planned",
                inputs=["records/acquisition/verification-summary.json", "config/qa/pixel-readiness-contract.json"], outputs=["external baseline rasters", "records/baseline/baseline-summary.json"], gates={}, disposition=None,
                expected=["EXIT-202-PIXEL-AND-RIGHTS-QA", "EXIT-203-PRE-EVENT-BASELINE", "EXIT-204-REGISTRATION-QA"], observed=[], decision_value="unknown", rationale="Baseline processing awaits verified product custody.", next_dependency=None,
            ),
        ],
        "path_efficiency": {"max_consecutive_no_progress_units": 2, "review_action_class": "project_control", "review_human_gate": False},
        "verification": {
            "changed_risks": ["authenticated external access", "large external data custody", "third-party rights", "raster preprocessing", "scientific quality"],
            "required_checks": ["exact activation binding", "fresh terms and availability review", "60 GiB free-space minimum", "path and collision safety", "per-product transfer receipts", "local SHA-256 and provider checksum", "ZIP and SAFE verification", "AOI pixel and mask QA", "EPSG:32645 baseline and registration QA"],
            "completed_checks": ["exact activation binding"],
        },
        "activation_evidence": {
            "proposal_ref": "contracts/milestone-002-proposal.json",
            "proposal_sha256": PROPOSAL_SHA256,
            "approval_ref": approval_ref,
            "approval_sha256": approval_sha,
            "reconciliation_ref": reconciliation_ref,
            "reconciliation_sha256": sha256(ROOT / reconciliation_ref),
        },
        "handoff": {
            "current_checkpoint": "M2-FRESH-CUSTODY-PREFLIGHT",
            "next_action": "Run the live terms, product availability, free-space, path, collision, and access-route preflight before creating external custody.",
            "do_not_carry_forward": [
                "Activation does not accept provider terms, authorize account changes, incur cost, or permit products outside the exact eight.",
                "Catalog byte counts and checksums remain metadata until transferred bytes are independently verified.",
                "No full-product bytes are yet in custody and no pixel usability or scientific change is established.",
                "The post-event optical route remains high-cloud-risk and may be inconclusive.",
            ],
        },
    }

    profile = load("records/project-control-profile.json")
    if profile.get("control_surfaces", {}).get("active_contract") is not None:
        raise SystemExit("project profile already names an active contract")
    if profile.get("control_surfaces", {}).get("proposed_contract") != "contracts/milestone-002-proposal.json":
        raise SystemExit("project profile does not point to the exact M2 proposal")
    profile["authority"] = {
        "mode": "inherited",
        "authority_ref": approval_ref,
        "authorized_action_classes": action_classes,
        "verified_at_utc": args.activated_at_utc,
        "expires_at_utc": None,
        "scope_ref": active_contract_ref,
    }
    profile["control_surfaces"].update({
        "active_contract": active_contract_ref,
        "proposed_contract": None,
        "activated_from_contract": "contracts/milestone-002-proposal.json",
    })
    profile["current_checkpoint"].update({
        "checkpoint_id": "M2-FRESH-CUSTODY-PREFLIGHT",
        "expected_head": None,
        "next_action": "Run the authorized fresh M2 preflight; do not create custody or authenticate until its non-mutating checks pass.",
    })

    goal = load("records/long-term-goal.json")
    if goal.get("active_milestone") is not None or goal.get("proposed_milestone") != "contracts/milestone-002-proposal.json":
        raise SystemExit("long-term goal does not show the expected pre-activation state")
    goal.update({
        "active_milestone": active_contract_ref,
        "proposed_milestone": None,
        "current_checkpoint": "M2-FRESH-CUSTODY-PREFLIGHT",
    })

    create_new(approval_ref, approval)
    create_new(active_contract_ref, active_contract)
    replace("records/project-control-profile.json", profile)
    replace("records/long-term-goal.json", goal)
    print(json.dumps({
        "status": "m2_activated",
        "activated_at_utc": args.activated_at_utc,
        "approval_sha256": approval_sha,
        "active_contract": active_contract_ref,
        "next_unit": "M2-CUSTODY-PREFLIGHT",
        "custody_created": False,
        "authentication_used": False,
    }, indent=2))


if __name__ == "__main__":
    main()
