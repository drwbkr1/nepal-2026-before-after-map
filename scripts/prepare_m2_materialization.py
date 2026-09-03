#!/usr/bin/env python3
"""Build the active, gate-deferred M2 SAFE materialization contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "contracts/m2-materialization.json"


def load(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def digest(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def build_contract(created_at_utc: str) -> dict[str, Any]:
    plan = load("records/acquisition-plan.json")
    verification = load("contracts/m2-offline-verification.json")
    approval = load("records/source-gates/m2-activation-approval.json")
    milestone = load("contracts/milestone-002.json")
    if approval.get("status") != "approved" or milestone.get("status") != "active":
        raise ValueError("M2 authority is not active")
    if "data_processing" not in milestone.get("authority", {}).get("authorized_action_classes", []):
        raise ValueError("M2 does not authorize bounded data processing")
    by_source = {item["source_id"]: item for item in plan["records"]}
    assets = []
    for item in verification["assets"]:
        source_id = item["source_id"]
        planned = by_source[source_id]
        assets.append(
            {
                "source_id": source_id,
                "sensor_route": planned["sensor_route"],
                "event_role": planned["event_role"],
                "exact_product_id": item["exact_product_id"],
                "archive_relative_path": item["archive_relative_path"],
                "output_relative_path_template": f"{source_id.casefold()}/<materialization-attempt-id>/{item['exact_product_id']}",
            }
        )
    contract = {
        "contract_version": "1.0",
        "materialization_id": "NEPAL-M2-SAFE-MATERIALIZATION-001",
        "created_at_utc": created_at_utc,
        "status": "active_authorized_gate_deferred",
        "inputs": {
            "acquisition_plan_ref": "records/acquisition-plan.json",
            "acquisition_plan_sha256": digest("records/acquisition-plan.json"),
            "activation_approval_ref": "records/source-gates/m2-activation-approval.json",
            "activation_approval_sha256": digest("records/source-gates/m2-activation-approval.json"),
            "active_verification_ref": "contracts/m2-offline-verification.json",
            "active_verification_sha256": digest("contracts/m2-offline-verification.json"),
            "materialization_core_ref": "scripts/m2_materialization_core.py",
            "materialization_core_sha256": digest("scripts/m2_materialization_core.py"),
            "runner_ref": "scripts/materialize_m2_product.py",
            "runner_sha256": digest("scripts/materialize_m2_product.py"),
        },
        "authority": {
            "mode": "inherited",
            "authority_ref": "records/source-gates/m2-activation-approval.json",
            "required_action_class": "data_processing",
            "exact_product_boundary": "the eight approved Sentinel products only",
            "this_contract_creates_authority": False,
            "dem_products_authorized": False,
            "network_access_authorized": False,
        },
        "execution_boundary": {
            "external_data_root": "C:\\Projects\\Active\\nepal-2026-before-after-map-data",
            "materialization_root": "C:\\Projects\\Active\\nepal-2026-before-after-map-data\\materialized",
            "receipt_root": "records/acquisition/materialization",
            "network_requests": "prohibited",
            "authentication": "prohibited",
            "source_archive_mutation": "prohibited",
            "attempt_policy": "exclusive_append_only_retain_partial_and_failed",
            "overwrite_existing_attempt_or_receipt": False,
            "complete_marker_required_for_downstream_use": True,
            "external_file_manifest_hashes_every_extracted_file": True,
        },
        "prerequisites": {
            "active_intake_asset_state": "promoted",
            "successful_transfer_attempt_count": 1,
            "container_receipt_status": "pass_container_only",
            "archive_sha256_and_size_must_match_intake_and_container_receipt": True,
            "member_safety_revalidated_before_output_creation": True,
        },
        "member_controls": {
            **verification["archive_controls"],
            "reject_windows_reserved_names": True,
            "reject_windows_forbidden_characters": True,
            "reject_trailing_dot_or_space": True,
            "reject_case_insensitive_collisions": True,
            "reject_file_directory_collisions": True,
        },
        "assets": assets,
        "claim_boundary": {
            "safe_materialization_is_source_identity_evidence_only": True,
            "raster_readability_established": False,
            "pixel_usability_established": False,
            "baseline_established": False,
            "change_established": False,
            "scientific_admission_authorized": False,
        },
        "limitations": [
            "A complete materialization proves extracted file bytes and paths against one verified archive; it does not prove raster readability or usable pixels.",
            "Each attempt is append-only. Partial and failed attempts remain external evidence and cannot be relabeled complete.",
            "The public receipt binds an external complete manifest; raw archives, SAFE files, and per-file manifests remain outside Git.",
            "DEM products are outside this contract and remain subject to the separate unapproved amendment.",
        ],
    }
    errors = validate_contract(contract)
    if errors:
        raise ValueError("; ".join(errors))
    return contract


def validate_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if contract.get("materialization_id") != "NEPAL-M2-SAFE-MATERIALIZATION-001":
        errors.append("materialization identity differs")
    if contract.get("status") != "active_authorized_gate_deferred":
        errors.append("materialization must remain gate-deferred")
    authority = contract.get("authority", {})
    if authority.get("mode") != "inherited" or authority.get("this_contract_creates_authority") is not False:
        errors.append("authority semantics differ")
    if authority.get("dem_products_authorized") is not False or authority.get("network_access_authorized") is not False:
        errors.append("contract broadens product or network scope")
    boundary = contract.get("execution_boundary", {})
    if boundary.get("network_requests") != "prohibited" or boundary.get("authentication") != "prohibited":
        errors.append("materialization must remain offline")
    if boundary.get("source_archive_mutation") != "prohibited":
        errors.append("source archive must remain read-only")
    if len(contract.get("assets", [])) != 8:
        errors.append("materialization contract must contain eight exact assets")
    if len({item.get("source_id") for item in contract.get("assets", [])}) != 8:
        errors.append("materialization source identities are not unique")
    claim = contract.get("claim_boundary", {})
    if any(claim.get(key) is not False for key in (
        "raster_readability_established",
        "pixel_usability_established",
        "baseline_established",
        "change_established",
        "scientific_admission_authorized",
    )):
        errors.append("materialization contract invents a scientific result")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--created-at-utc", required=True)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    value = build_contract(args.created_at_utc)
    expected = canonical_bytes(value)
    if args.verify_only:
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != expected:
            raise SystemExit("VERIFY FAIL: materialization contract differs from deterministic derivation")
        print(f"PASS: {OUTPUT.relative_to(ROOT)}")
        return
    if OUTPUT.exists() and OUTPUT.read_bytes() != expected:
        raise SystemExit("REFUSED: materialization contract exists with different bytes")
    if not OUTPUT.exists():
        OUTPUT.write_bytes(expected)
    print(json.dumps({"status": value["status"], "contract": str(OUTPUT.relative_to(ROOT)), "asset_count": len(value["assets"])}, indent=2))


if __name__ == "__main__":
    main()
