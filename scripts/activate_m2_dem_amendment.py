#!/usr/bin/env python3
"""Activate the exact reconciled M2 DEM amendment without mutating its proposal evidence."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BUNDLE_SHA256 = "caecbdfe69ec1a6c8c39401b63756005820a727cb8f9e7e0084753e2d6afb39e"
PROPOSAL_SHA256 = "92f48680c0b779398d8bbebd872a60bc3850f008f5c9b68d5bf45a2448abdd69"
LICENSE_SHA256 = "9cd37d37ea654bbcaf0a2e059e6a3a5b5f76072824d8dd860ccf274ada8951bd"
RECONCILIATION_REF = "records/source-gates/m2-dem-amendment-review-reconciliation.json"
APPROVAL_REF = "records/source-gates/m2-dem-amendment-approval.json"
INTAKE_REF = "contracts/m2-dem-intake.json"
VERIFICATION_REF = "contracts/m2-dem-offline-verification.json"
ACTIVATION_RECEIPT_REF = "records/acquisition/dem-amendment-activation.json"


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(relative: str) -> str:
    return sha256_bytes((ROOT / relative).read_bytes())


def load(relative: str) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {relative}")
    return value


def make_unit(
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


def build_outputs(activated_at_utc: str) -> dict[str, dict[str, Any]]:
    proposal = load("contracts/milestone-002-dem-amendment-proposal.json")
    bundle = load("reviews/m2-dem-amendment/review-bundle.json")
    review_contract = load("reviews/m2-dem-amendment/review-contract.json")
    reconciliation = load(RECONCILIATION_REF)
    intake_candidate = load("contracts/m2-dem-intake-candidate.json")
    verification_candidate = load("contracts/m2-dem-offline-verification-candidate.json")
    active_m2 = load("contracts/milestone-002.json")
    profile = load("records/project-control-profile.json")
    goal = load("records/long-term-goal.json")

    if sha256_file("reviews/m2-dem-amendment/review-bundle.json") != BUNDLE_SHA256:
        raise ValueError("DEM review bundle hash drift")
    if sha256_file("contracts/milestone-002-dem-amendment-proposal.json") != PROPOSAL_SHA256:
        raise ValueError("DEM proposal hash drift")
    if proposal.get("license_decision", {}).get("license_document_sha256") != LICENSE_SHA256:
        raise ValueError("DEM license hash drift")
    if bundle.get("candidate_identity") != f"M2-DEM-AMENDMENT-PROPOSAL-SHA256:{PROPOSAL_SHA256}":
        raise ValueError("DEM review bundle candidate identity drift")
    if review_contract.get("review_bundle", {}).get("manifest_sha256") != BUNDLE_SHA256:
        raise ValueError("DEM review contract bundle binding drift")
    if reconciliation.get("status") != "reconciled_exact_human_response":
        raise ValueError("DEM review response is not reconciled")
    if reconciliation.get("contract_sha256") != sha256_file("reviews/m2-dem-amendment/review-contract.json"):
        raise ValueError("DEM reconciliation contract binding drift")
    if reconciliation.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}:
        raise ValueError("DEM reconciliation is not one exact approval")
    if reconciliation.get("human_decisions_fabricated") is not False:
        raise ValueError("DEM reconciliation reports fabricated decisions")
    if active_m2.get("status") != "active" or profile.get("control_surfaces", {}).get("active_contract") != "contracts/milestone-002.json":
        raise ValueError("M2 is not the active contract")
    if profile.get("control_surfaces", {}).get("proposed_amendments") != [
        "contracts/milestone-002-dem-amendment-proposal.json"
    ]:
        raise ValueError("profile does not expose exactly the pending DEM amendment")
    if any(unit.get("id", "").startswith("M2-DEM-") for unit in active_m2.get("units", [])):
        raise ValueError("active M2 already contains DEM units")

    approval = {
        "schema_version": "1.0",
        "approval_id": "NEPAL-M2-DEM-AMENDMENT-APPROVAL-001",
        "status": "approved",
        "approved_at_utc": activated_at_utc,
        "review_id": "m2-dem-amendment-review-001",
        "review_bundle_id": "m2-dem-amendment-review-bundle-001",
        "review_bundle_manifest_sha256": BUNDLE_SHA256,
        "amendment_proposal_ref": "contracts/milestone-002-dem-amendment-proposal.json",
        "amendment_proposal_sha256": PROPOSAL_SHA256,
        "review_reconciliation_ref": RECONCILIATION_REF,
        "review_reconciliation_sha256": sha256_file(RECONCILIATION_REF),
        "locked_response_sha256": reconciliation["response_sha256"],
        "lock_receipt_sha256": reconciliation["receipt_sha256"],
        "human_decision_count": 1,
        "decision_counts": {"approve": 1, "revise": 0, "defer": 0},
        "license": {
            "name": proposal["license_decision"]["license_name"],
            "url": proposal["license_decision"]["license_url"],
            "document_sha256": LICENSE_SHA256,
            "acceptance_status": "accepted_exact_hash_bound_document",
        },
        "authorized_source_ids": ["M2-DEM-001", "M2-DEM-002", "M2-DEM-003", "M2-DEM-004"],
        "authorized_next_actions": copy.deepcopy(proposal["authority"]["requested_actions"]),
        "does_not_authorize": copy.deepcopy(proposal["authority"]["not_requested"]),
        "human_decisions_fabricated": False,
    }
    approval_bytes = canonical_bytes(approval)
    approval_sha256 = sha256_bytes(approval_bytes)

    intake = copy.deepcopy(intake_candidate)
    for asset in intake["assets"]:
        asset["source"]["authorization_ref"] = APPROVAL_REF
        asset["state"] = "authorized"
    intake["extensions"].update(
        {
            "status": "active_authorized_unattempted",
            "authority_status": "inherited_exact_dem_amendment_approval",
            "amendment_approval_ref": APPROVAL_REF,
            "amendment_approval_sha256": approval_sha256,
            "review_reconciliation_ref": RECONCILIATION_REF,
            "review_reconciliation_sha256": sha256_file(RECONCILIATION_REF),
            "license_acceptance_status": "accepted_exact_hash_bound_document",
            "static_only_no_network_or_external_filesystem_mutation": False,
        }
    )
    intake_bytes = canonical_bytes(intake)
    intake_sha256 = sha256_bytes(intake_bytes)

    verification = copy.deepcopy(verification_candidate)
    verification["created_at"] = activated_at_utc
    verification["status"] = "active_gate_deferred_no_promoted_rasters"
    verification["inputs"].update(
        {
            "intake_contract_ref": INTAKE_REF,
            "intake_contract_sha256": intake_sha256,
            "amendment_approval_ref": APPROVAL_REF,
            "amendment_approval_sha256": approval_sha256,
            "review_reconciliation_ref": RECONCILIATION_REF,
            "review_reconciliation_sha256": sha256_file(RECONCILIATION_REF),
        }
    )
    verification["authority"] = {
        "dem_amendment_status": "approved",
        "license_acceptance_established": True,
        "network_access_authorized": False,
        "custody_mutation_authorized": False,
        "dem_download_authorized": False,
        "dem_pixel_processing_authorized": True,
        "this_contract_creates_authority": False,
    }
    verification_bytes = canonical_bytes(verification)
    verification_sha256 = sha256_bytes(verification_bytes)

    amendment_binding = {
        "approval_ref": APPROVAL_REF,
        "approval_sha256": approval_sha256,
        "proposal_ref": "contracts/milestone-002-dem-amendment-proposal.json",
        "proposal_sha256": PROPOSAL_SHA256,
        "review_bundle_sha256": BUNDLE_SHA256,
        "license_document_sha256": LICENSE_SHA256,
    }

    amended_m2 = copy.deepcopy(active_m2)
    amended_m2["authority"]["amendments"] = [amendment_binding]
    amended_m2["scope"]["active_amendments"] = [APPROVAL_REF]
    old_forbidden = "download any product outside the eight exact approved identities"
    if old_forbidden not in amended_m2["scope"]["forbidden_work"]:
        raise ValueError("active M2 forbidden-work boundary drift")
    amended_m2["scope"]["forbidden_work"].remove(old_forbidden)
    amended_m2["scope"]["forbidden_work"].append(
        "download any Sentinel product outside the eight exact approved identities or any DEM tile outside the four exact amendment identities"
    )
    amended_m2["scope"]["reversible_actions"].extend(
        [
            "write append-only DEM transfer attempts for only the four exact approved tiles",
            "verify and promote exact DEM GeoTIFFs without replacement",
            "use verified DEM pixels only for approved radar terrain correction and terrain-geometry masks",
        ]
    )
    amended_m2["scope"]["stop_conditions"].extend(copy.deepcopy(proposal["stop_conditions"]))
    amended_m2["units"].extend(
        [
            make_unit(
                "M2-DEM-AMEND",
                "Lock and reconcile the exact owner license and four-tile amendment decision.",
                ["M2-ACTIVATE"],
                "authority_broadening",
                True,
                "complete",
                ["reviews/m2-dem-amendment/review-bundle.json", "reviews/m2-dem-amendment/review-contract.json"],
                [APPROVAL_REF, RECONCILIATION_REF],
                {
                    "owner_decision": "approve",
                    "attestation": True,
                    "review_bundle_sha256": BUNDLE_SHA256,
                    "proposal_sha256": PROPOSAL_SHA256,
                    "license_document_sha256": LICENSE_SHA256,
                },
                "pass",
                [],
                [],
                "enables_dependency",
                "One exact completed approval was locked and reconciled; license acceptance and tile scope are hash-bound.",
                "M2-DEM-PREFLIGHT",
            ),
            make_unit(
                "M2-DEM-PREFLIGHT",
                "Revalidate license bytes, four object identities, anonymous access, paths, collisions, and storage before DEM transfer.",
                ["M2-DEM-AMEND"],
                "data_acquisition",
                False,
                "ready",
                [APPROVAL_REF, "records/source-gates/m2-dem-candidate-manifest.json", INTAKE_REF],
                ["records/source-gates/m2-dem-live-source-gate.json", "records/acquisition/dem-preflight.json"],
                {},
                None,
                [],
                [],
                "unknown",
                "The amendment makes a fresh non-mutating DEM preflight eligible; it has not run.",
                "M2-DEM-ACQUIRE",
            ),
            make_unit(
                "M2-DEM-ACQUIRE",
                "Acquire only the four exact anonymous GLO-30 tiles into append-only non-Git custody.",
                ["M2-DEM-PREFLIGHT"],
                "data_acquisition",
                False,
                "planned",
                ["records/source-gates/m2-dem-live-source-gate.json", "records/acquisition/dem-preflight.json", INTAKE_REF],
                ["external DEM custody", "records/acquisition DEM transfer receipts"],
                {},
                None,
                ["EXIT-201-VERIFIED-CUSTODY"],
                [],
                "unknown",
                "DEM transfer cannot begin until fresh source and custody controls pass.",
                "M2-DEM-VERIFY",
            ),
            make_unit(
                "M2-DEM-VERIFY",
                "Verify exact DEM bytes, GeoTIFF structure, CRS, dimensions, nodata, and approved-AOI coverage.",
                ["M2-DEM-ACQUIRE"],
                "routine_qa",
                False,
                "planned",
                ["external DEM custody", VERIFICATION_REF],
                ["records/acquisition/dem-verification-summary.json"],
                {},
                None,
                ["EXIT-201-VERIFIED-CUSTODY", "EXIT-202-PIXEL-AND-RIGHTS-QA"],
                [],
                "unknown",
                "No DEM bytes have been transferred or inspected.",
                "M2-BASELINE",
            ),
        ]
    )
    baseline = next(unit for unit in amended_m2["units"] if unit["id"] == "M2-BASELINE")
    baseline["depends_on"] = ["M2-VERIFY", "M2-DEM-VERIFY"]
    baseline["inputs"].append(VERIFICATION_REF)
    amended_m2["verification"]["required_checks"].extend(
        [
            "exact DEM amendment and license binding",
            "fresh anonymous four-tile source preflight",
            "per-tile SHA-256 and GeoTIFF verification",
        ]
    )
    amended_m2["verification"]["completed_checks"].append("exact DEM amendment and license binding")
    amended_m2["handoff"]["parallel_checkpoint"] = "M2-DEM-FRESH-PREFLIGHT"
    amended_m2["handoff"]["parallel_next_action"] = (
        "Run the fresh anonymous DEM source, license, storage, path, collision, and redirect preflight."
    )
    amended_m2_bytes = canonical_bytes(amended_m2)

    amended_profile = copy.deepcopy(profile)
    amended_profile["authority"]["amendments"] = [amendment_binding]
    amended_profile["control_surfaces"]["proposed_amendments"] = []
    amended_profile["control_surfaces"]["activated_amendments"] = [APPROVAL_REF]
    gate_by_id = {
        gate["unit_id"]: gate for gate in amended_profile["gate_policy"]["explicit_human_gates"]
    }
    gate_by_id["M2-DEM-AMEND"]["authority_ref"] = APPROVAL_REF
    for unit_id, reason in (
        ("M2-DEM-PREFLIGHT", "The exact DEM amendment authorizes fresh non-mutating preflight for four named tiles."),
        ("M2-DEM-ACQUIRE", "The exact DEM amendment authorizes anonymous acquisition of only four named tiles."),
    ):
        amended_profile["gate_policy"]["explicit_human_gates"].append(
            {"unit_id": unit_id, "reason": reason, "authority_ref": APPROVAL_REF}
        )
    amended_profile["parallel_checkpoints"] = [
        {
            "checkpoint_id": "M2-DEM-FRESH-PREFLIGHT",
            "authority_ref": APPROVAL_REF,
            "next_action": "Run the fresh anonymous DEM preflight before requesting any tile bytes.",
        }
    ]
    amended_profile_bytes = canonical_bytes(amended_profile)

    amended_goal = copy.deepcopy(goal)
    amended_goal["active_amendments"] = [APPROVAL_REF]
    amended_goal["parallel_checkpoints"] = ["M2-DEM-FRESH-PREFLIGHT"]
    amended_goal_bytes = canonical_bytes(amended_goal)

    output_bytes = {
        APPROVAL_REF: approval_bytes,
        INTAKE_REF: intake_bytes,
        VERIFICATION_REF: verification_bytes,
        "contracts/milestone-002.json": amended_m2_bytes,
        "records/project-control-profile.json": amended_profile_bytes,
        "records/long-term-goal.json": amended_goal_bytes,
    }
    receipt = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-DEM-AMENDMENT-ACTIVATION-001",
        "activated_at_utc": activated_at_utc,
        "status": "pass_exact_dem_amendment_activated_preflight_pending",
        "bindings": {
            "reconciliation_ref": RECONCILIATION_REF,
            "reconciliation_sha256": sha256_file(RECONCILIATION_REF),
            "approval_ref": APPROVAL_REF,
            "approval_sha256": approval_sha256,
            "active_intake_ref": INTAKE_REF,
            "active_intake_sha256": intake_sha256,
            "active_verification_ref": VERIFICATION_REF,
            "active_verification_sha256": verification_sha256,
            "active_milestone_ref": "contracts/milestone-002.json",
            "active_milestone_sha256": sha256_bytes(amended_m2_bytes),
            "project_profile_ref": "records/project-control-profile.json",
            "project_profile_sha256": sha256_bytes(amended_profile_bytes),
            "long_term_goal_ref": "records/long-term-goal.json",
            "long_term_goal_sha256": sha256_bytes(amended_goal_bytes),
            "activation_script_ref": "scripts/activate_m2_dem_amendment.py",
            "activation_script_sha256": sha256_file("scripts/activate_m2_dem_amendment.py"),
        },
        "assertions": {
            "exact_owner_approval_reconciled": True,
            "exact_license_accepted": True,
            "authorized_dem_tile_count": 4,
            "candidate_proposal_mutated": False,
            "candidate_intake_mutated": False,
            "candidate_verification_mutated": False,
            "network_requests_performed": False,
            "dem_payload_bytes_requested": False,
            "dem_pixels_examined": False,
            "sentinel_checkpoint_preserved": True,
            "scientific_result_established": False,
        },
        "next_gate": "M2-DEM-FRESH-PREFLIGHT",
    }
    output_bytes[ACTIVATION_RECEIPT_REF] = canonical_bytes(receipt)
    return {path: json.loads(data) for path, data in output_bytes.items()}


def write_activation(activated_at_utc: str) -> dict[str, Any]:
    outputs = build_outputs(activated_at_utc)
    new_paths = [APPROVAL_REF, INTAKE_REF, VERIFICATION_REF, ACTIVATION_RECEIPT_REF]
    for relative in new_paths:
        if (ROOT / relative).exists():
            raise ValueError(f"refusing to replace existing activation output: {relative}")
    ledger_path = ROOT / "records/evidence-ledger.jsonl"
    ledger = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if any(item.get("record_id") == "EVID-0031" for item in ledger):
        raise ValueError("EVID-0031 already exists")

    for relative in new_paths:
        path = ROOT / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as handle:
            handle.write(canonical_bytes(outputs[relative]))
            handle.flush()
    for relative in ("contracts/milestone-002.json", "records/project-control-profile.json", "records/long-term-goal.json"):
        path = ROOT / relative
        temporary = path.with_name(path.name + ".dem-activation-tmp")
        with temporary.open("xb") as handle:
            handle.write(canonical_bytes(outputs[relative]))
            handle.flush()
        temporary.replace(path)

    evidence = {
        "record_id": "EVID-0031",
        "type": "m2_dem_amendment_activation",
        "status": "pass_exact_dem_amendment_activated_preflight_pending",
        "verified_at_utc": activated_at_utc,
        "claim": "One exact completed owner decision activates only the four named Copernicus DEM tiles, exact license, bounded verification, custody, and radar-processing scope; live preflight and payload transfer remain pending.",
        "activation_receipt_ref": ACTIVATION_RECEIPT_REF,
        "activation_receipt_sha256": sha256_file(ACTIVATION_RECEIPT_REF),
        "approval_ref": APPROVAL_REF,
        "approval_sha256": sha256_file(APPROVAL_REF),
        "active_intake_ref": INTAKE_REF,
        "active_intake_sha256": sha256_file(INTAKE_REF),
        "active_verification_ref": VERIFICATION_REF,
        "active_verification_sha256": sha256_file(VERIFICATION_REF),
        "reconciliation_ref": RECONCILIATION_REF,
        "reconciliation_sha256": sha256_file(RECONCILIATION_REF),
        "activation_script_ref": "scripts/activate_m2_dem_amendment.py",
        "activation_script_sha256": sha256_file("scripts/activate_m2_dem_amendment.py"),
        "assertions": outputs[ACTIVATION_RECEIPT_REF]["assertions"],
        "limitations": [
            "Activation does not establish current remote identity, transferred-byte integrity, GeoTIFF fitness, DEM pixel validity, or radar-processing success.",
            "The EGM2008-to-ArcGIS-EGM96 vertical-datum mismatch remains unresolved.",
            "The original eight-product Sentinel acquisition still awaits its separate owner-controlled credential reference.",
        ],
    }
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(evidence, separators=(",", ":")) + "\n")
    return {
        "status": "m2_dem_amendment_activated",
        "approval_sha256": sha256_file(APPROVAL_REF),
        "active_intake_sha256": sha256_file(INTAKE_REF),
        "active_verification_sha256": sha256_file(VERIFICATION_REF),
        "activation_receipt_sha256": sha256_file(ACTIVATION_RECEIPT_REF),
        "next_gate": "M2-DEM-FRESH-PREFLIGHT",
        "network_requests_performed": False,
        "dem_payload_bytes_requested": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activated-at-utc", required=True)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if not args.activated_at_utc.endswith("Z"):
        raise SystemExit("--activated-at-utc must be RFC 3339 UTC ending in Z")
    if args.verify_only:
        outputs = build_outputs(args.activated_at_utc)
        print(
            json.dumps(
                {
                    "status": "pass_activation_derivation_only",
                    "output_count": len(outputs),
                    "authorized_dem_tile_count": len(outputs[INTAKE_REF]["assets"]),
                    "network_requests_performed": False,
                    "dem_payload_bytes_requested": False,
                },
                indent=2,
            )
        )
        return
    print(json.dumps(write_activation(args.activated_at_utc), indent=2))


if __name__ == "__main__":
    main()
