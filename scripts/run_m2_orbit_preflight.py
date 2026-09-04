#!/usr/bin/env python3
"""Run the approved fresh no-payload preflight for four exact S1D orbit files."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
from pathlib import Path, PurePosixPath
from typing import Any

from acquire_m2_orbit_file import public_catalog_check
from prepare_m2_orbit_amendment import LEGAL_NOTICE_URL, TERMS_URL, fetch


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent.resolve()
APPROVAL_REF = "records/source-gates/m2-orbit-amendment-approval.json"
PROPOSAL_REF = "contracts/milestone-002-orbit-amendment-proposal.json"
MANIFEST_REF = "records/source-gates/m2-orbit-candidate-manifest.json"
HISTORICAL_GATE_REF = "records/source-gates/m2-orbit-source-gate.json"
LIVE_GATE_REF = "records/source-gates/m2-orbit-live-source-gate.json"
PREFLIGHT_REF = "records/acquisition/orbit-preflight.json"
INTAKE_REF = "contracts/m2-orbit-intake.json"
MILESTONE_REF = "contracts/milestone-002.json"
PROFILE_REF = "records/project-control-profile.json"
GOAL_REF = "records/long-term-goal.json"
BUNDLE_SHA256 = "ee5fbf4933b52be8f97441b78a73559a973bd975efc21b43625f1ceca54e2ff1"
PROPOSAL_SHA256 = "b17e256068759946be611bf4e7beffe0d3121e9e731b6c42163525eca2cf0292"
EXPECTED_SOURCE_IDS = [f"M2-ORB-{index:03d}" for index in range(1, 5)]
EXPECTED_SENTINEL_SOURCE_IDS = [f"M1-SRC-{index:03d}" for index in range(1, 7)]
MINIMUM_FREE_BYTES = 60 * 1024**3


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


def has_reparse_component(path: Path) -> bool:
    current = path
    while True:
        if current.exists():
            stat = current.lstat()
            if current.is_symlink() or bool(getattr(stat, "st_file_attributes", 0) & 0x400):
                return True
        if current.parent == current:
            return False
        current = current.parent


def resolved_external_path(relative: str) -> Path:
    posix = PurePosixPath(relative)
    if posix.is_absolute() or ".." in posix.parts:
        raise ValueError("external custody path is absolute or contains traversal")
    target = (PROJECT_ROOT / Path(*posix.parts)).resolve(strict=False)
    target.relative_to(PROJECT_ROOT)
    if target == ROOT or ROOT in target.parents:
        raise ValueError("external custody path resolves inside Git repository")
    if has_reparse_component(target):
        raise ValueError("external custody path contains a symlink or reparse point")
    return target


def criterion(
    criterion_id: str,
    evidence: list[dict[str, Any]],
    note: str,
    *,
    requires_live: bool,
) -> dict[str, Any]:
    return {
        "id": criterion_id,
        "required": True,
        "requires_live": requires_live,
        "status": "pass",
        "evidence": evidence,
        "note": note,
    }


def build_outputs(assessed_at_utc: str) -> dict[str, dict[str, Any]]:
    approval = load(APPROVAL_REF)
    proposal = load(PROPOSAL_REF)
    manifest = load(MANIFEST_REF)
    historical_gate = load(HISTORICAL_GATE_REF)
    intake = load(INTAKE_REF)
    milestone = load(MILESTONE_REF)
    profile = load(PROFILE_REF)
    goal = load(GOAL_REF)
    sentinel_intake = load("contracts/m2-intake.json")

    if approval.get("status") != "approved":
        raise ValueError("orbit amendment approval is absent")
    if approval.get("review_bundle_manifest_sha256") != BUNDLE_SHA256:
        raise ValueError("orbit approval bundle binding drift")
    if approval.get("amendment_proposal_sha256") != PROPOSAL_SHA256 or sha256_file(PROPOSAL_REF) != PROPOSAL_SHA256:
        raise ValueError("orbit approval proposal binding drift")
    if approval.get("authorized_source_ids") != EXPECTED_SOURCE_IDS:
        raise ValueError("orbit approval source boundary drift")
    if approval.get("authorized_orbit_type") != "AUX_RESORB":
        raise ValueError("orbit approval type drift")
    if approval.get("orbit_quality", {}).get("later_precise_substitution_status") != "separately_gated_not_authorized":
        raise ValueError("precise-substitution boundary drift")
    if proposal.get("source_gate_sha256") != sha256_file(HISTORICAL_GATE_REF):
        raise ValueError("historical source-gate proposal binding drift")
    if intake.get("extensions", {}).get("status") != "active_authorized_unattempted_fresh_preflight_and_sentinel_custody_pending":
        raise ValueError("active orbit intake is not at its preflight-ready checkpoint")
    if [asset.get("extensions", {}).get("source_id") for asset in intake.get("assets", [])] != EXPECTED_SOURCE_IDS:
        raise ValueError("active orbit intake source identity drift")
    if any(asset.get("state") != "authorized" or asset.get("attempts") for asset in intake["assets"]):
        raise ValueError("orbit intake contains an attempted or non-authorized asset")

    product_checks: list[dict[str, Any]] = []
    for record in manifest["records"]:
        live = public_catalog_check(record)
        product_checks.append(
            {
                "source_id": record["source_id"],
                "catalogue_url": record["catalogue_url"],
                "observed_at_utc": assessed_at_utc,
                "response_sha256": live["response_sha256"],
                "identity": live["identity"],
                "status": "pass_exact_identity_online_unchanged",
            }
        )

    page_checks: list[dict[str, Any]] = []
    for page_id, url, expected_sha in (
        ("cdse_terms", TERMS_URL, manifest["rights"]["terms_page_sha256"]),
        ("sentinel_legal_notice", LEGAL_NOTICE_URL, manifest["rights"]["legal_notice_sha256"]),
    ):
        raw, headers, status = fetch(url)
        actual_sha = sha256_bytes(raw)
        if status != 200 or actual_sha != expected_sha:
            raise ValueError(f"{page_id} response differs from reviewed bytes")
        page_checks.append(
            {
                "page_id": page_id,
                "url": url,
                "observed_at_utc": assessed_at_utc,
                "http_status": status,
                "response_sha256": actual_sha,
                "content_length_bytes": len(raw),
                "content_type": headers.get("content-type"),
                "status": "pass_exact_reviewed_bytes",
            }
        )

    custody_root = resolved_external_path(intake["custody_root"])
    staging_root = resolved_external_path(intake["staging_root"])
    expected_data_root = (PROJECT_ROOT / "nepal-2026-before-after-map-data").resolve(strict=True)
    custody_root.relative_to(expected_data_root)
    staging_root.relative_to(expected_data_root)
    checked_paths: list[dict[str, Any]] = []
    for asset in intake["assets"]:
        destination = (custody_root / Path(*PurePosixPath(asset["destination_relative_path"]).parts)).resolve(strict=False)
        staging = (staging_root / Path(*PurePosixPath(asset["staging_relative_path"]).parts)).resolve(strict=False)
        destination.relative_to(custody_root)
        staging.relative_to(staging_root)
        if destination.exists() or staging.exists():
            raise ValueError(f"orbit destination or staging collision for {asset['asset_id']}")
        if has_reparse_component(destination) or has_reparse_component(staging):
            raise ValueError(f"unsafe link or reparse component for {asset['asset_id']}")
        checked_paths.append(
            {
                "source_id": asset["extensions"]["source_id"],
                "destination_path": str(destination),
                "staging_path": str(staging),
                "destination_exists": False,
                "staging_exists": False,
                "path_contained": True,
                "reparse_component_present": False,
            }
        )
    free_bytes = shutil.disk_usage(PROJECT_ROOT).free
    if free_bytes < MINIMUM_FREE_BYTES:
        raise ValueError("free space is below the inherited 60 GiB acquisition floor")

    sentinel_states: list[dict[str, Any]] = []
    for source_id in EXPECTED_SENTINEL_SOURCE_IDS:
        matches = [
            asset
            for asset in sentinel_intake.get("assets", [])
            if asset.get("extensions", {}).get("source_id") == source_id
        ]
        if len(matches) != 1:
            raise ValueError(f"bound Sentinel source is absent or ambiguous: {source_id}")
        asset = matches[0]
        sentinel_states.append(
            {
                "source_id": source_id,
                "state": asset.get("state"),
                "promoted": asset.get("state") == "promoted",
                "offline_container_verification_passed": False,
            }
        )
    promoted_count = sum(1 for item in sentinel_states if item["promoted"])
    if promoted_count != 0:
        raise ValueError("preflight expected zero bound Sentinel sources promoted at this checkpoint")

    approval_evidence = {
        "type": "static",
        "locator": APPROVAL_REF,
        "note": f"Exact owner amendment approval SHA-256 {sha256_file(APPROVAL_REF)} authorizes only four named AUX_RESORB files and forbids precise substitution.",
    }
    rights_evidence = {
        "type": "live",
        "locator": TERMS_URL,
        "observed_at": assessed_at_utc,
        "note": f"CDSE terms and Sentinel legal notice match the reviewed hashes {page_checks[0]['response_sha256']} and {page_checks[1]['response_sha256']}.",
    }
    manifest_evidence = {
        "type": "static",
        "locator": MANIFEST_REF,
        "note": f"Candidate manifest SHA-256 {sha256_file(MANIFEST_REF)} binds four exact files to six approved Sentinel sources.",
    }
    sources = []
    live_by_id = {item["source_id"]: item for item in product_checks}
    for record in manifest["records"]:
        live = live_by_id[record["source_id"]]
        live_evidence = {
            "type": "live",
            "locator": record["catalogue_url"],
            "observed_at": assessed_at_utc,
            "note": f"Exact OData response SHA-256 {live['response_sha256']} confirms unchanged identity, checksums, size, validity, and online state.",
        }
        sources.append(
            {
                "source_id": record["source_id"],
                "name": record["exact_product_name"],
                "locator": record["download_url"],
                "criteria": [
                    criterion("identity", [live_evidence, manifest_evidence], "Exact provider identity is unchanged.", requires_live=True),
                    criterion("authority", [live_evidence, approval_evidence], "Primary provider and exact owner scope are bound.", requires_live=True),
                    criterion("access", [live_evidence, approval_evidence], "Object is online; only the existing secret-safe token reference may be used later.", requires_live=True),
                    criterion("rights", [rights_evidence, approval_evidence], "Reviewed terms and legal-notice bytes remain unchanged.", requires_live=True),
                    criterion("provenance", [live_evidence, manifest_evidence], "Orbit-to-scene bindings remain exact.", requires_live=True),
                    criterion("integrity", [live_evidence, manifest_evidence], "Provider MD5, BLAKE3, and length are fixed for later byte verification.", requires_live=True),
                    criterion("fitness", [live_evidence, manifest_evidence], "Validity coverage and restituted quality remain explicit.", requires_live=True),
                    criterion("privacy-security", [approval_evidence], "No credential value was read or recorded and payloads remain outside Git.", requires_live=False),
                    criterion("scope-authority", [approval_evidence], "The exact four-file amendment is approved; later precise substitution is excluded.", requires_live=False),
                ],
            }
        )

    live_gate = {
        "contract_version": "source-gate/v1",
        "assessment_id": "NEPAL-M2-ORBIT-LIVE-SOURCE-GATE-001",
        "assessed_at": assessed_at_utc,
        "authority": {
            "mode": "inherited",
            "authority_ref": APPROVAL_REF,
            "authority_sha256": sha256_file(APPROVAL_REF),
            "authorized_actions": copy.deepcopy(approval["authorized_next_actions"]),
            "expires_at_utc": None,
        },
        "intended_use": {
            "summary": "Acquire, verify, and conditionally apply four exact S1D AUX_RESORB files only to their six bound approved radar sources.",
            "planned_actions": copy.deepcopy(approval["authorized_next_actions"]),
        },
        "sources": sources,
        "decision": {
            "status": "ready",
            "blocking_reasons": [],
            "live_verification_pending": [],
            "approved_actions": copy.deepcopy(approval["authorized_next_actions"]),
            "downstream_prerequisite_status": "blocked_on_matching_verified_sentinel_custody",
        },
        "write_boundary": {
            "permitted_without_further_authorization": copy.deepcopy(approval["authorized_next_actions"]),
            "still_prohibited": copy.deepcopy(approval["does_not_authorize"]),
        },
        "limitations": [
            "Source readiness does not establish transferred-byte integrity, XML fitness, or correction quality.",
            "The files are restituted rather than precise; later precise substitution remains separately gated.",
            "Payload transfer remains blocked until every Sentinel source bound to the selected orbit is promoted and offline container-verified.",
        ],
    }
    live_gate_bytes = canonical_bytes(live_gate)
    live_gate_sha = sha256_bytes(live_gate_bytes)

    preflight = {
        "schema_version": "1.0",
        "preflight_id": "NEPAL-M2-ORBIT-PREFLIGHT-001",
        "assessed_at_utc": assessed_at_utc,
        "status": "pass_no_payload_no_external_mutation_sentinel_custody_pending",
        "review_bundle_sha256": BUNDLE_SHA256,
        "proposal_ref": PROPOSAL_REF,
        "proposal_sha256": PROPOSAL_SHA256,
        "approval_ref": APPROVAL_REF,
        "approval_sha256": sha256_file(APPROVAL_REF),
        "candidate_manifest_ref": MANIFEST_REF,
        "candidate_manifest_sha256": sha256_file(MANIFEST_REF),
        "historical_source_gate_ref": HISTORICAL_GATE_REF,
        "historical_source_gate_sha256": sha256_file(HISTORICAL_GATE_REF),
        "source_gate_ref": LIVE_GATE_REF,
        "source_gate_sha256": live_gate_sha,
        "live_products": product_checks,
        "live_rights_pages": page_checks,
        "path_checks": {
            "project_root": str(PROJECT_ROOT),
            "external_data_root": str(expected_data_root),
            "custody_root": str(custody_root),
            "staging_root": str(staging_root),
            "asset_paths": checked_paths,
            "collision_policy": "fail",
            "promotion_mode": "atomic-no-replace",
            "status": "pass",
        },
        "storage_check": {
            "minimum_free_bytes": MINIMUM_FREE_BYTES,
            "observed_free_bytes": free_bytes,
            "observed_free_gib": round(free_bytes / 1024**3, 3),
            "status": "pass",
        },
        "sentinel_custody_prerequisite": {
            "required_source_ids": EXPECTED_SENTINEL_SOURCE_IDS,
            "sources": sentinel_states,
            "promoted_and_verified_count": 0,
            "required_count": 6,
            "status": "pending_blocks_orbit_payload_transfer",
        },
        "assertions": {
            "exact_approved_orbit_count": 4,
            "exact_live_unchanged_online_count": 4,
            "terms_hash_match": True,
            "legal_notice_hash_match": True,
            "path_and_collision_safety": "pass",
            "free_space_floor": "pass",
            "network_requests_performed": True,
            "authentication_performed": False,
            "credential_reference_checked": False,
            "credential_values_read_or_recorded": False,
            "orbit_payload_bytes_requested": 0,
            "external_directories_created": 0,
            "sentinel_custody_prerequisite_satisfied": False,
            "precise_substitution_authorized": False,
            "orbit_xml_verified": False,
            "orbit_correction_applied": False,
            "scientific_result_established": False,
        },
        "next_gate": "M2-ORBIT-CUSTODY-INITIALIZATION",
    }
    preflight_bytes = canonical_bytes(preflight)
    preflight_sha = sha256_bytes(preflight_bytes)

    amended_intake = copy.deepcopy(intake)
    live_sha_by_id = {item["source_id"]: item["response_sha256"] for item in product_checks}
    for asset in amended_intake["assets"]:
        asset["extensions"]["fresh_catalogue_response_sha256"] = live_sha_by_id[asset["extensions"]["source_id"]]
    amended_intake["extensions"].update(
        {
            "status": "active_authorized_preflight_passed_custody_not_initialized_sentinel_custody_pending",
            "scope_authority": "granted_exact_four_resorb_files",
            "approval_sha256": sha256_file(APPROVAL_REF),
            "preflight_ref": PREFLIGHT_REF,
            "preflight_sha256": preflight_sha,
            "source_gate_ref": LIVE_GATE_REF,
            "source_gate_sha256": live_gate_sha,
            "custody_initialized": False,
            "sentinel_custody_prerequisite_status": "pending_zero_of_six_promoted_and_verified",
        }
    )
    amended_intake_bytes = canonical_bytes(amended_intake)

    amended_milestone = copy.deepcopy(milestone)
    orbit_preflight_unit = next(unit for unit in amended_milestone["units"] if unit["id"] == "M2-ORBIT-PREFLIGHT")
    orbit_preflight_unit["status"] = "complete"
    orbit_preflight_unit["gates"] = {
        "preflight_status": preflight["status"],
        "source_gate_status": "ready",
        "exact_files_online_and_unchanged": 4,
        "terms_and_legal_notice_hashes": "pass",
        "free_space_gib": preflight["storage_check"]["observed_free_gib"],
        "path_and_collision_safety": "pass",
        "sentinel_custody_prerequisite": "pending_zero_of_six",
    }
    orbit_preflight_unit["disposition"] = "pass"
    orbit_preflight_unit["exit_condition_delta"]["decision_value"] = "enables_dependency"
    orbit_preflight_unit["exit_condition_delta"]["rationale"] = (
        "The four exact sources, rights bytes, storage, and paths pass; payload transfer remains blocked on matching Sentinel custody."
    )
    orbit_acquire_unit = next(unit for unit in amended_milestone["units"] if unit["id"] == "M2-ORBIT-ACQUIRE")
    orbit_acquire_unit["gates"].update(
        {
            "fresh_source_preflight": "pass",
            "orbit_custody_initialized": False,
            "matching_sentinel_promoted_and_verified": False,
        }
    )
    amended_milestone_bytes = canonical_bytes(amended_milestone)

    amended_profile = copy.deepcopy(profile)
    for checkpoint in amended_profile["parallel_checkpoints"]:
        if checkpoint["checkpoint_id"] == "M2-ORBIT-FRESH-PREFLIGHT":
            checkpoint.update(
                {
                    "checkpoint_id": "M2-ORBIT-CUSTODY-INITIALIZATION",
                    "authority_ref": APPROVAL_REF,
                    "next_action": "Create and verify only the empty no-reparse orbit custody, staging, event, and per-source directories; do not read a token or request payload bytes.",
                }
            )
            break
    else:
        raise ValueError("project profile orbit preflight checkpoint is absent")
    amended_profile_bytes = canonical_bytes(amended_profile)

    amended_goal = copy.deepcopy(goal)
    amended_goal["parallel_checkpoints"] = [
        "M2-ORBIT-CUSTODY-INITIALIZATION" if value == "M2-ORBIT-FRESH-PREFLIGHT" else value
        for value in amended_goal["parallel_checkpoints"]
    ]
    amended_goal_bytes = canonical_bytes(amended_goal)
    return {
        LIVE_GATE_REF: live_gate,
        PREFLIGHT_REF: preflight,
        INTAKE_REF: json.loads(amended_intake_bytes),
        MILESTONE_REF: json.loads(amended_milestone_bytes),
        PROFILE_REF: json.loads(amended_profile_bytes),
        GOAL_REF: json.loads(amended_goal_bytes),
    }


def write_outputs(assessed_at_utc: str) -> dict[str, Any]:
    outputs = build_outputs(assessed_at_utc)
    for relative in (LIVE_GATE_REF, PREFLIGHT_REF):
        if (ROOT / relative).exists():
            raise ValueError(f"refusing to replace preflight output: {relative}")
    for relative in (LIVE_GATE_REF, PREFLIGHT_REF):
        path = ROOT / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as handle:
            handle.write(canonical_bytes(outputs[relative]))
            handle.flush()
            os.fsync(handle.fileno())
    for relative in (INTAKE_REF, MILESTONE_REF, PROFILE_REF, GOAL_REF):
        path = ROOT / relative
        temporary = path.with_name(path.name + ".orbit-preflight-tmp")
        with temporary.open("xb") as handle:
            handle.write(canonical_bytes(outputs[relative]))
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)

    ledger_path = ROOT / "records/evidence-ledger.jsonl"
    ledger = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if any(item.get("record_id") == "EVID-0054" for item in ledger):
        raise ValueError("EVID-0054 already exists")
    preflight = outputs[PREFLIGHT_REF]
    evidence = {
        "record_id": "EVID-0054",
        "type": "m2_sentinel1_orbit_fresh_preflight",
        "status": preflight["status"],
        "verified_at_utc": assessed_at_utc,
        "claim": "All four exact approved S1D AUX_RESORB catalogue identities remain online and unchanged; reviewed rights bytes, storage, paths, and collision controls pass without authentication or payload transfer, while matching Sentinel custody still blocks transfer.",
        "preflight_ref": PREFLIGHT_REF,
        "preflight_sha256": sha256_file(PREFLIGHT_REF),
        "source_gate_ref": LIVE_GATE_REF,
        "source_gate_sha256": sha256_file(LIVE_GATE_REF),
        "approval_ref": APPROVAL_REF,
        "approval_sha256": sha256_file(APPROVAL_REF),
        "active_intake_ref": INTAKE_REF,
        "active_intake_sha256": sha256_file(INTAKE_REF),
        "preflight_script_ref": "scripts/run_m2_orbit_preflight.py",
        "preflight_script_sha256": sha256_file("scripts/run_m2_orbit_preflight.py"),
        "assertions": preflight["assertions"],
        "limitations": [
            "Preflight metadata and rights checks do not establish transferred-byte integrity or XML fitness.",
            "The bound Sentinel sources remain unpromoted and unverified, so no orbit payload request is eligible.",
            "No token presence or validity check occurred and no credential value was read.",
        ],
        "next_action": "Initialize only empty external orbit custody directories, then wait for the bound Sentinel acquisition and offline container verification.",
    }
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(evidence, separators=(",", ":")) + "\n")
    return {
        "status": preflight["status"],
        "live_source_gate_sha256": sha256_file(LIVE_GATE_REF),
        "preflight_sha256": sha256_file(PREFLIGHT_REF),
        "active_intake_sha256": sha256_file(INTAKE_REF),
        "sentinel_promoted_and_verified_count": 0,
        "network_requests_performed": True,
        "authentication_performed": False,
        "orbit_payload_bytes_requested": 0,
        "next_gate": "M2-ORBIT-CUSTODY-INITIALIZATION",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assessed-at-utc", required=True)
    args = parser.parse_args()
    if not args.assessed_at_utc.endswith("Z"):
        raise SystemExit("--assessed-at-utc must be RFC 3339 UTC ending in Z")
    print(json.dumps(write_outputs(args.assessed_at_utc), indent=2))


if __name__ == "__main__":
    main()
