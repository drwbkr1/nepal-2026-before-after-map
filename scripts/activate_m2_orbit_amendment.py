#!/usr/bin/env python3
"""Activate the exact reconciled M2 Sentinel-1 orbit amendment."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BUNDLE_SHA256 = "ee5fbf4933b52be8f97441b78a73559a973bd975efc21b43625f1ceca54e2ff1"
PROPOSAL_SHA256 = "b17e256068759946be611bf4e7beffe0d3121e9e731b6c42163525eca2cf0292"
RECONCILIATION_REF = "records/source-gates/m2-orbit-amendment-review-reconciliation.json"
APPROVAL_REF = "records/source-gates/m2-orbit-amendment-approval.json"
INTAKE_REF = "contracts/m2-orbit-intake.json"
VERIFICATION_REF = "contracts/m2-orbit-offline-verification.json"
ACTIVATION_RECEIPT_REF = "records/acquisition/orbit-amendment-activation.json"
PROPOSAL_REF = "contracts/milestone-002-orbit-amendment-proposal.json"
MANIFEST_REF = "records/source-gates/m2-orbit-candidate-manifest.json"
EXPECTED_SOURCE_IDS = [f"M2-ORB-{index:03d}" for index in range(1, 5)]
EXPECTED_SENTINEL_SOURCE_IDS = [f"M1-SRC-{index:03d}" for index in range(1, 7)]


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


def replace_checkpoint(checkpoints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    replacement = {
        "checkpoint_id": "M2-ORBIT-FRESH-PREFLIGHT",
        "authority_ref": APPROVAL_REF,
        "next_action": (
            "Revalidate the four exact AUX_RESORB identities, checksums, online state, terms, "
            "paths, collisions, storage, and Sentinel-custody prerequisite without requesting payload bytes."
        ),
    }
    result: list[dict[str, Any]] = []
    replaced = False
    for item in checkpoints:
        if item.get("checkpoint_id") == "M2-ORBIT-AMENDMENT-REVIEW":
            result.append(replacement)
            replaced = True
        else:
            result.append(copy.deepcopy(item))
    if not replaced:
        raise ValueError("orbit review checkpoint is absent or already consumed")
    return result


def build_outputs(activated_at_utc: str) -> dict[str, dict[str, Any]]:
    proposal = load(PROPOSAL_REF)
    manifest = load(MANIFEST_REF)
    bundle = load("reviews/m2-orbit-amendment/review-bundle.json")
    review_contract = load("reviews/m2-orbit-amendment/review-contract.json")
    reconciliation = load(RECONCILIATION_REF)
    intake_candidate = load("contracts/m2-orbit-intake-candidate.json")
    verification_candidate = load("contracts/m2-orbit-offline-verification-candidate.json")
    active_sentinel_intake = load("contracts/m2-intake.json")
    active_m2 = load("contracts/milestone-002.json")
    profile = load("records/project-control-profile.json")
    goal = load("records/long-term-goal.json")

    if sha256_file("reviews/m2-orbit-amendment/review-bundle.json") != BUNDLE_SHA256:
        raise ValueError("orbit review bundle hash drift")
    if sha256_file(PROPOSAL_REF) != PROPOSAL_SHA256:
        raise ValueError("orbit proposal hash drift")
    if bundle.get("candidate_identity") != f"M2-ORBIT-AMENDMENT-PROPOSAL-SHA256:{PROPOSAL_SHA256}":
        raise ValueError("orbit review bundle candidate identity drift")
    if review_contract.get("review_bundle", {}).get("manifest_sha256") != BUNDLE_SHA256:
        raise ValueError("orbit review contract bundle binding drift")
    if reconciliation.get("status") != "reconciled_exact_human_response":
        raise ValueError("orbit review response is not reconciled")
    if reconciliation.get("contract_sha256") != sha256_file("reviews/m2-orbit-amendment/review-contract.json"):
        raise ValueError("orbit reconciliation contract binding drift")
    if reconciliation.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}:
        raise ValueError("orbit reconciliation is not one exact approval")
    if reconciliation.get("human_decisions_fabricated") is not False:
        raise ValueError("orbit reconciliation reports fabricated decisions")
    manifest_source_ids = [record.get("source_id") for record in manifest.get("records", [])]
    if manifest_source_ids != EXPECTED_SOURCE_IDS:
        raise ValueError("orbit manifest source boundary drift")
    if any(record.get("orbit_type") != "AUX_RESORB" for record in manifest.get("records", [])):
        raise ValueError("orbit manifest type drift")
    covered_sentinel_ids = sorted(
        {source_id for record in manifest["records"] for source_id in record.get("sentinel_source_ids", [])}
    )
    if covered_sentinel_ids != EXPECTED_SENTINEL_SOURCE_IDS:
        raise ValueError("orbit-to-Sentinel source binding drift")
    if active_m2.get("status") != "active" or profile.get("control_surfaces", {}).get("active_contract") != "contracts/milestone-002.json":
        raise ValueError("M2 is not the active contract")
    if profile.get("control_surfaces", {}).get("proposed_amendments") != [PROPOSAL_REF]:
        raise ValueError("profile does not expose exactly the pending orbit amendment")
    if profile.get("control_surfaces", {}).get("activated_amendments") != [
        "records/source-gates/m2-dem-amendment-approval.json"
    ]:
        raise ValueError("existing activated amendment boundary drift")
    if any(unit.get("id", "").startswith("M2-ORBIT-") for unit in active_m2.get("units", [])):
        raise ValueError("active M2 already contains orbit units")
    sentinel_assets = active_sentinel_intake.get("assets", [])
    if [asset.get("extensions", {}).get("source_id") for asset in sentinel_assets[:6]] != EXPECTED_SENTINEL_SOURCE_IDS:
        raise ValueError("active Sentinel intake source order or identity drift")
    if any(asset.get("state") == "promoted" for asset in sentinel_assets[:6]):
        raise ValueError("activation derivation expected the six radar sources to remain unpromoted")

    approval = {
        "schema_version": "1.0",
        "approval_id": "NEPAL-M2-ORBIT-AMENDMENT-APPROVAL-001",
        "status": "approved",
        "approved_at_utc": activated_at_utc,
        "review_id": "m2-orbit-amendment-review-001",
        "review_bundle_id": "m2-orbit-amendment-review-bundle-001",
        "review_bundle_manifest_sha256": BUNDLE_SHA256,
        "amendment_proposal_ref": PROPOSAL_REF,
        "amendment_proposal_sha256": PROPOSAL_SHA256,
        "review_reconciliation_ref": RECONCILIATION_REF,
        "review_reconciliation_sha256": sha256_file(RECONCILIATION_REF),
        "locked_response_sha256": reconciliation["response_sha256"],
        "lock_receipt_sha256": reconciliation["receipt_sha256"],
        "human_decision_count": 1,
        "decision_counts": {"approve": 1, "revise": 0, "defer": 0},
        "authorized_source_ids": EXPECTED_SOURCE_IDS,
        "authorized_provider_product_ids": [record["provider_product_id"] for record in manifest["records"]],
        "authorized_sentinel_source_ids": EXPECTED_SENTINEL_SOURCE_IDS,
        "authorized_orbit_type": "AUX_RESORB",
        "orbit_quality": {
            "selected_type": "restituted",
            "precise_equivalence_established": False,
            "later_precise_substitution_status": "separately_gated_not_authorized",
        },
        "credential_policy": {
            "reference": "existing secret-safe owner-controlled CDSE token reference",
            "value_recorded": False,
            "may_be_read_only_after_all_nonsecret_prerequisites_pass": True,
        },
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
        asset["extensions"]["sentinel_custody_prerequisite"] = "not_satisfied_at_activation"
    intake["extensions"].update(
        {
            "status": "active_authorized_unattempted_fresh_preflight_and_sentinel_custody_pending",
            "authority_status": "inherited_exact_orbit_amendment_approval",
            "scope_authority": "granted_exact_four_resorb_files",
            "amendment_approval_ref": APPROVAL_REF,
            "amendment_approval_sha256": approval_sha256,
            "review_reconciliation_ref": RECONCILIATION_REF,
            "review_reconciliation_sha256": sha256_file(RECONCILIATION_REF),
            "sentinel_custody_prerequisite_status": "not_satisfied_zero_bound_radar_sources_promoted",
            "static_only_no_network_or_external_filesystem_mutation": False,
        }
    )
    intake_bytes = canonical_bytes(intake)
    intake_sha256 = sha256_bytes(intake_bytes)

    verification = copy.deepcopy(verification_candidate)
    verification["created_at_utc"] = activated_at_utc
    verification["status"] = "active_gate_deferred_no_promoted_orbits"
    verification["authority"] = {
        "mode": "inherited_exact_orbit_amendment_approval",
        "authority_ref": APPROVAL_REF,
        "authority_sha256": approval_sha256,
        "orbit_payload_acquisition_authorized": True,
        "orbit_input_verification_authorized": True,
        "exact_source_orbit_application_authorized": True,
        "radar_pixel_processing_authorized_by_this_contract": False,
        "precise_orbit_substitution_authorized": False,
        "this_contract_creates_authority": False,
    }
    verification["bindings"].update(
        {
            "active_intake_ref": INTAKE_REF,
            "active_intake_sha256": intake_sha256,
            "amendment_approval_ref": APPROVAL_REF,
            "amendment_approval_sha256": approval_sha256,
            "review_reconciliation_ref": RECONCILIATION_REF,
            "review_reconciliation_sha256": sha256_file(RECONCILIATION_REF),
        }
    )
    verification_bytes = canonical_bytes(verification)
    verification_sha256 = sha256_bytes(verification_bytes)

    amendment_binding = {
        "approval_ref": APPROVAL_REF,
        "approval_sha256": approval_sha256,
        "proposal_ref": PROPOSAL_REF,
        "proposal_sha256": PROPOSAL_SHA256,
        "review_bundle_sha256": BUNDLE_SHA256,
        "authorized_orbit_type": "AUX_RESORB",
        "authorized_source_count": 4,
        "precise_substitution_authorized": False,
    }

    amended_m2 = copy.deepcopy(active_m2)
    amended_m2["authority"]["amendments"].append(amendment_binding)
    amended_m2["scope"]["active_amendments"].append(APPROVAL_REF)
    old_forbidden = (
        "download any Sentinel product outside the eight exact approved identities or any DEM tile outside the four exact amendment identities"
    )
    if old_forbidden not in amended_m2["scope"]["forbidden_work"]:
        raise ValueError("active M2 product-identity boundary drift")
    amended_m2["scope"]["forbidden_work"].remove(old_forbidden)
    amended_m2["scope"]["forbidden_work"].append(
        "download any Sentinel product outside the eight exact approved identities, any DEM tile outside the four exact DEM amendment identities, or any orbit file outside the four exact AUX_RESORB amendment identities"
    )
    amended_m2["scope"]["reversible_actions"].extend(
        [
            "write append-only orbit transfer attempts for only the four exact approved AUX_RESORB files after fresh preflight and matching Sentinel custody",
            "verify and promote exact orbit EOF files without replacement",
            "apply each verified orbit file only to its bound verified Sentinel source in a new versioned non-Git attempt",
        ]
    )
    amended_m2["scope"]["stop_conditions"].extend(copy.deepcopy(proposal["stop_conditions"]))
    amended_m2["units"].extend(
        [
            make_unit(
                "M2-ORBIT-AMEND",
                "Lock and reconcile the exact owner four-file restituted-orbit amendment decision.",
                ["M2-ACTIVATE"],
                "authority_broadening",
                True,
                "complete",
                ["reviews/m2-orbit-amendment/review-bundle.json", "reviews/m2-orbit-amendment/review-contract.json"],
                [APPROVAL_REF, RECONCILIATION_REF],
                {
                    "owner_decision": "approve",
                    "attestation": True,
                    "review_bundle_sha256": BUNDLE_SHA256,
                    "proposal_sha256": PROPOSAL_SHA256,
                    "authorized_orbit_type": "AUX_RESORB",
                    "authorized_source_count": 4,
                    "precise_substitution_authorized": False,
                },
                "pass",
                [],
                [],
                "enables_dependency",
                "One exact completed approval was locked and reconciled; four restituted identities and their limits are hash-bound.",
                "M2-ORBIT-PREFLIGHT",
            ),
            make_unit(
                "M2-ORBIT-PREFLIGHT",
                "Revalidate four exact orbit identities, checksums, availability, terms, paths, collisions, storage, and prerequisite custody without payload transfer.",
                ["M2-ORBIT-AMEND"],
                "data_acquisition",
                False,
                "ready",
                [APPROVAL_REF, MANIFEST_REF, INTAKE_REF],
                ["records/source-gates/m2-orbit-live-source-gate.json", "records/acquisition/orbit-preflight.json"],
                {},
                None,
                [],
                [],
                "unknown",
                "The approval makes a fresh non-payload preflight eligible; it has not run.",
                "M2-ORBIT-ACQUIRE",
            ),
            make_unit(
                "M2-ORBIT-ACQUIRE",
                "Acquire only the four exact S1D AUX_RESORB files into append-only non-Git custody.",
                ["M2-ORBIT-PREFLIGHT", "M2-VERIFY"],
                "data_acquisition",
                False,
                "planned",
                ["records/source-gates/m2-orbit-live-source-gate.json", "records/acquisition/orbit-preflight.json", INTAKE_REF],
                ["external orbit custody", "records/acquisition orbit transfer receipts"],
                {"matching_sentinel_promoted_and_verified": False},
                None,
                ["EXIT-201-VERIFIED-CUSTODY"],
                [],
                "unknown",
                "Orbit transfer remains blocked until fresh preflight passes and each bound Sentinel source is promoted and verified.",
                "M2-ORBIT-VERIFY",
            ),
            make_unit(
                "M2-ORBIT-VERIFY",
                "Verify exact orbit bytes, provider checksums, EOF XML identity, OSVs, validity, and scene binding.",
                ["M2-ORBIT-ACQUIRE"],
                "routine_qa",
                False,
                "planned",
                ["external orbit custody", VERIFICATION_REF],
                ["records/acquisition orbit verification receipts"],
                {},
                None,
                ["EXIT-201-VERIFIED-CUSTODY", "EXIT-202-PIXEL-AND-RIGHTS-QA"],
                [],
                "unknown",
                "No orbit payload has been transferred or structurally verified.",
                "M2-ORBIT-APPLY",
            ),
            make_unit(
                "M2-ORBIT-APPLY",
                "Apply each verified restituted orbit only to its exact bound Sentinel source in new versioned non-Git output.",
                ["M2-ORBIT-VERIFY", "M2-DEM-VERIFY"],
                "data_processing",
                False,
                "planned",
                ["verified Sentinel custody", "verified orbit custody", VERIFICATION_REF],
                ["external corrected SAFE metadata attempts", "records/baseline orbit-application receipts"],
                {
                    "dem_vertical_datum_gate": "pending",
                    "terrain_result_review": "pending",
                    "radar_pixel_readiness": "pending",
                    "precise_substitution_authorized": False,
                },
                None,
                ["EXIT-203-PRE-EVENT-BASELINE", "EXIT-204-REGISTRATION-QA"],
                [],
                "unknown",
                "Application cannot begin until Sentinel, DEM, vertical, orbit, terrain-review, and radar-readiness prerequisites pass.",
                "M2-BASELINE",
            ),
        ]
    )
    baseline = next(unit for unit in amended_m2["units"] if unit["id"] == "M2-BASELINE")
    baseline["depends_on"].append("M2-ORBIT-APPLY")
    baseline["inputs"].append(VERIFICATION_REF)
    amended_m2["verification"]["required_checks"].extend(
        [
            "exact Sentinel-1 orbit amendment binding",
            "fresh four-file orbit source preflight",
            "per-file provider checksum and EOF XML verification",
            "exact-source orbit application without SAFE overwrite",
        ]
    )
    amended_m2["verification"]["completed_checks"].append("exact Sentinel-1 orbit amendment binding")
    amended_m2_bytes = canonical_bytes(amended_m2)

    amended_profile = copy.deepcopy(profile)
    amended_profile["authority"]["amendments"].append(amendment_binding)
    amended_profile["control_surfaces"]["proposed_amendments"] = []
    amended_profile["control_surfaces"]["activated_amendments"].append(APPROVAL_REF)
    gate_by_id = {
        gate["unit_id"]: gate for gate in amended_profile["gate_policy"]["explicit_human_gates"]
    }
    gate_by_id["M2-ORBIT-AMEND"]["authority_ref"] = APPROVAL_REF
    for unit_id, reason in (
        ("M2-ORBIT-PREFLIGHT", "The exact orbit amendment authorizes a fresh non-payload preflight for four named restituted files."),
        ("M2-ORBIT-ACQUIRE", "The exact orbit amendment authorizes acquisition only after fresh preflight and matching verified Sentinel custody."),
        ("M2-ORBIT-VERIFY", "The exact orbit amendment authorizes offline verification only for the four promoted named files."),
        ("M2-ORBIT-APPLY", "The exact orbit amendment authorizes exact-source application only after all independent radar prerequisites pass."),
    ):
        amended_profile["gate_policy"]["explicit_human_gates"].append(
            {"unit_id": unit_id, "reason": reason, "authority_ref": APPROVAL_REF}
        )
    amended_profile["parallel_checkpoints"] = replace_checkpoint(profile["parallel_checkpoints"])
    amended_profile_bytes = canonical_bytes(amended_profile)

    amended_goal = copy.deepcopy(goal)
    amended_goal["active_amendments"].append(APPROVAL_REF)
    amended_goal["parallel_checkpoints"] = [
        "M2-ORBIT-FRESH-PREFLIGHT" if value == "M2-ORBIT-AMENDMENT-REVIEW" else value
        for value in amended_goal["parallel_checkpoints"]
    ]
    if "M2-ORBIT-FRESH-PREFLIGHT" not in amended_goal["parallel_checkpoints"]:
        raise ValueError("long-term goal orbit checkpoint was not replaced")
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
        "receipt_id": "NEPAL-M2-ORBIT-AMENDMENT-ACTIVATION-001",
        "activated_at_utc": activated_at_utc,
        "status": "pass_exact_orbit_amendment_activated_preflight_and_sentinel_custody_pending",
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
            "activation_script_ref": "scripts/activate_m2_orbit_amendment.py",
            "activation_script_sha256": sha256_file("scripts/activate_m2_orbit_amendment.py"),
        },
        "assertions": {
            "exact_owner_approval_reconciled": True,
            "authorized_orbit_type": "AUX_RESORB",
            "authorized_orbit_file_count": 4,
            "bound_sentinel_source_count": 6,
            "candidate_proposal_mutated": False,
            "candidate_intake_mutated": False,
            "candidate_verification_mutated": False,
            "network_requests_performed": False,
            "authentication_performed": False,
            "credential_values_read_or_recorded": False,
            "orbit_payload_bytes_requested": 0,
            "orbit_xml_verified": False,
            "orbit_correction_applied": False,
            "matching_sentinel_sources_promoted_at_activation": 0,
            "precise_substitution_authorized": False,
            "dem_vertical_and_terrain_review_gates_preserved": True,
            "scientific_result_established": False,
        },
        "next_gate": "M2-ORBIT-FRESH-PREFLIGHT",
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
    if any(item.get("record_id") == "EVID-0053" for item in ledger):
        raise ValueError("EVID-0053 already exists")

    for relative in new_paths:
        path = ROOT / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as handle:
            handle.write(canonical_bytes(outputs[relative]))
            handle.flush()
    for relative in ("contracts/milestone-002.json", "records/project-control-profile.json", "records/long-term-goal.json"):
        path = ROOT / relative
        temporary = path.with_name(path.name + ".orbit-activation-tmp")
        with temporary.open("xb") as handle:
            handle.write(canonical_bytes(outputs[relative]))
            handle.flush()
        temporary.replace(path)

    evidence = {
        "record_id": "EVID-0053",
        "type": "m2_sentinel1_orbit_amendment_activation",
        "status": "pass_exact_orbit_amendment_activated_preflight_and_sentinel_custody_pending",
        "verified_at_utc": activated_at_utc,
        "claim": "One exact completed owner decision activates only four named S1D AUX_RESORB files and their bounded verification, custody, and exact-source application route; fresh preflight and matching verified Sentinel custody remain prerequisites.",
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
        "activation_script_ref": "scripts/activate_m2_orbit_amendment.py",
        "activation_script_sha256": sha256_file("scripts/activate_m2_orbit_amendment.py"),
        "assertions": outputs[ACTIVATION_RECEIPT_REF]["assertions"],
        "limitations": [
            "Activation does not establish current remote identity, transferred-byte integrity, XML fitness, or orbit-correction success.",
            "The selected files are restituted rather than precise and later precise substitution remains separately gated.",
            "The six bound Sentinel radar sources are not yet in verified promoted custody, so orbit transfer and application remain blocked.",
            "DEM vertical-datum, terrain-result review, radar pixel-readiness, registration, and scientific gates remain independent.",
        ],
        "next_action": "Run only the fresh no-payload orbit preflight; do not read the token or request orbit payload bytes while matching Sentinel custody is absent.",
    }
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(evidence, separators=(",", ":")) + "\n")
    return {
        "status": "m2_orbit_amendment_activated",
        "approval_sha256": sha256_file(APPROVAL_REF),
        "active_intake_sha256": sha256_file(INTAKE_REF),
        "active_verification_sha256": sha256_file(VERIFICATION_REF),
        "activation_receipt_sha256": sha256_file(ACTIVATION_RECEIPT_REF),
        "next_gate": "M2-ORBIT-FRESH-PREFLIGHT",
        "network_requests_performed": False,
        "authentication_performed": False,
        "orbit_payload_bytes_requested": 0,
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
                    "authorized_orbit_file_count": len(outputs[INTAKE_REF]["assets"]),
                    "network_requests_performed": False,
                    "authentication_performed": False,
                    "orbit_payload_bytes_requested": 0,
                },
                indent=2,
            )
        )
        return
    print(json.dumps(write_activation(args.activated_at_utc), indent=2))


if __name__ == "__main__":
    main()
