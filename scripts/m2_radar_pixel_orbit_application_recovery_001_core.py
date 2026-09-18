#!/usr/bin/env python3
"""Strict recovery controls for radar SAFE inventory identity verification."""

from __future__ import annotations

import copy
import re
from pathlib import Path, PurePosixPath
from typing import Any

import m2_radar_pixel_orbit_application_001_core as base


CONTRACT_REF = "config/qa/m2-radar-pixel-orbit-application-recovery-001-contract.json"
BASE_CONTRACT_REF = "config/qa/m2-radar-pixel-orbit-application-001-contract.json"
EXPECTED_AUTHORITY_HASHES = {
    "approval_sha256": "4a1fe442f678c354c13f7e255ea459db2ec2d0368c35b72b32170ae8a3dc7d8f",
    "activation_sha256": "1b42eb0f5eb977a7889333eca9ff9f8c25d14116c3baf1cefd51c2a4af94796b",
    "proposal_sha256": "cacda42d4eba2d60f3725bf2933fa00ea5ede6f33e6fed4133ca4d3e1476cd04",
}
EXPECTED_AUTHORITY_REFS = {
    "approval_ref": "records/source-gates/m2-radar-pixel-orbit-application-recovery-001-approval.json",
    "activation_ref": "records/readiness/m2-radar-pixel-orbit-application-recovery-001-approval-activation.json",
    "proposal_ref": "contracts/milestone-002-radar-pixel-orbit-application-recovery-001-proposal.json",
}
EXPECTED_BASE_CONTRACT_SHA256 = "a25f86588979fd4b5cfb45c999a862d83d71be31925a5b39565970de526f8fb1"
EXPECTED_ATTEMPT_ROOT = (
    r"C:\Projects\Active\nepal-2026-before-after-map-data\derived\radar-pixel-orbit-application-recovery-001"
    r"\radar-pixel-orbit-application-recovery-001-real-001"
)
SHA256 = re.compile(r"[0-9a-fA-F]{64}")


def _safe_repo_file(root: Path, ref: str) -> Path:
    posix = PurePosixPath(ref)
    if posix.is_absolute() or any(part in {"", ".", ".."} for part in posix.parts):
        raise base.RadarRouteError("unsafe_repository_ref", ref)
    try:
        path = root.joinpath(*posix.parts).resolve(strict=True)
        path.relative_to(root.resolve(strict=True))
    except (FileNotFoundError, ValueError) as exc:
        raise base.RadarRouteError("missing_or_unsafe_repository_ref", ref) from exc
    if not path.is_file():
        raise base.RadarRouteError("repository_ref_not_file", ref)
    return path


def project_inventory(items: Any, *, label: str) -> list[dict[str, Any]]:
    """Project an inventory to strict byte-identity fields and stable path order."""
    if not isinstance(items, list):
        raise base.RadarRouteError("inventory_not_list", label)
    projected: list[dict[str, Any]] = []
    normalized_paths: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise base.RadarRouteError("inventory_entry_not_object", f"{label}:{index}")
        relative = item.get("relative_path")
        size = item.get("size_bytes")
        digest = item.get("sha256")
        if not isinstance(relative, str) or not relative or "\\" in relative:
            raise base.RadarRouteError("inventory_path_unsafe", f"{label}:{index}")
        posix = PurePosixPath(relative)
        if (
            posix.is_absolute()
            or relative != posix.as_posix()
            or any(part in {"", ".", ".."} or ":" in part for part in posix.parts)
        ):
            raise base.RadarRouteError("inventory_path_unsafe", f"{label}:{index}")
        normalized = relative.casefold()
        if normalized in normalized_paths:
            raise base.RadarRouteError("inventory_duplicate_normalized_path", f"{label}:{relative}")
        normalized_paths.add(normalized)
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise base.RadarRouteError("inventory_size_invalid", f"{label}:{relative}")
        if not isinstance(digest, str) or SHA256.fullmatch(digest) is None:
            raise base.RadarRouteError("inventory_sha256_invalid", f"{label}:{relative}")
        projected.append(
            {
                "relative_path": relative,
                "size_bytes": size,
                "sha256": digest.lower(),
            }
        )
    return sorted(projected, key=lambda item: item["relative_path"].casefold())


def inventories_match(expected: Any, actual: Any) -> bool:
    return project_inventory(expected, label="expected") == project_inventory(actual, label="actual")


def validate_recovery_contract(contract: dict[str, Any], root: Path) -> list[str]:
    errors: list[str] = []
    if contract.get("contract_id") != "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-001":
        errors.append("contract identity differs")
    if contract.get("status") != "active_preobservation_strict_inventory_normalization_one_attempt":
        errors.append("contract status differs")
    if contract.get("base_contract_ref") != BASE_CONTRACT_REF:
        errors.append("base contract ref differs")
    if contract.get("base_contract_sha256") != EXPECTED_BASE_CONTRACT_SHA256:
        errors.append("base contract hash differs")
    if contract.get("fixed_source_order") != base.SOURCE_ORDER:
        errors.append("source order differs")
    if contract.get("fixed_route_order") != base.ROUTE_ORDER:
        errors.append("route order differs")
    if contract.get("source_to_orbit") != base.SOURCE_TO_ORBIT:
        errors.append("source-to-orbit map differs")
    expected_comparison = {
        "project_exact_fields": ["relative_path", "size_bytes", "sha256"],
        "sort_key": "relative_path_casefold",
        "ignore_unprojected_fields": ["zip_crc32"],
        "reject_added_path": True,
        "reject_missing_path": True,
        "reject_size_mismatch": True,
        "reject_sha256_mismatch": True,
        "reject_duplicate_normalized_path": True,
        "reject_unsafe_path": True,
        "reject_reparse_point": True,
    }
    if contract.get("inventory_comparison") != expected_comparison:
        errors.append("inventory comparison differs")
    attempt = contract.get("attempt", {})
    expected_attempt_values = {
        "attempt_id": "radar-pixel-orbit-application-recovery-001-real-001",
        "consumed_attempt_id": "radar-pixel-orbit-application-001-real-001",
        "maximum_final_preflights": 1,
        "maximum_real_attempts": 1,
        "maximum_orbit_application_attempts_per_source": 1,
        "maximum_qa_processing_attempts_per_source": 1,
        "maximum_route_qa_attempts_per_pair": 1,
        "automatic_retry_authorized": False,
        "stop_on_first_source_execution_failure": True,
        "external_attempt_root": EXPECTED_ATTEMPT_ROOT,
        "minimum_free_space_bytes": 64424509440,
        "collision_policy": "fail",
    }
    if attempt != expected_attempt_values:
        errors.append("attempt boundary differs")
    boundary = contract.get("execution_boundary", {})
    for key in ("network_requests", "authentication", "source_overwrite", "output_overwrite", "automatic_retry"):
        if boundary.get(key) != "prohibited":
            errors.append(f"execution boundary differs: {key}")
    if any(value is not False for value in contract.get("claim_boundary", {}).values()):
        errors.append("claim boundary releases prohibited work")
    authority = contract.get("authority", {})
    for key, expected in EXPECTED_AUTHORITY_REFS.items():
        if authority.get(key) != expected:
            errors.append(f"authority ref differs: {key}")
    for key, expected in EXPECTED_AUTHORITY_HASHES.items():
        if authority.get(key) != expected:
            errors.append(f"authority hash differs: {key}")
            continue
        ref = authority.get(key.removesuffix("_sha256") + "_ref")
        try:
            if not isinstance(ref, str) or base.sha256_file(_safe_repo_file(root, ref)) != expected:
                errors.append(f"bound authority file differs: {key}")
        except base.RadarRouteError:
            errors.append(f"bound authority file missing: {key}")
    try:
        base_path = _safe_repo_file(root, BASE_CONTRACT_REF)
        if base.sha256_file(base_path) != EXPECTED_BASE_CONTRACT_SHA256:
            errors.append("base contract bytes differ")
        else:
            errors.extend(f"base: {item}" for item in base.validate_contract(base.load_object(base_path), root))
    except base.RadarRouteError as exc:
        errors.append(f"base contract unavailable: {exc.code}")
    return errors


def load_execution_plan(root: Path, contract_ref: str = CONTRACT_REF) -> dict[str, Any]:
    contract_path = _safe_repo_file(root, contract_ref)
    recovery_contract = base.load_object(contract_path)
    errors = validate_recovery_contract(recovery_contract, root)
    if errors:
        raise base.RadarRouteError("recovery_contract_invalid", "; ".join(errors))
    plan = base.load_execution_plan(root, recovery_contract["base_contract_ref"])
    merged = copy.deepcopy(plan["contract"])
    merged["contract_id"] = recovery_contract["contract_id"]
    merged["status"] = recovery_contract["status"]
    merged["attempt"] = copy.deepcopy(recovery_contract["attempt"])
    merged["recovery_authority"] = copy.deepcopy(recovery_contract["authority"])
    merged["inventory_comparison"] = copy.deepcopy(recovery_contract["inventory_comparison"])
    plan.update(
        {
            "contract": merged,
            "contract_ref": contract_ref,
            "contract_sha256": base.sha256_file(contract_path),
            "base_contract_ref": recovery_contract["base_contract_ref"],
            "base_contract_sha256": recovery_contract["base_contract_sha256"],
            "recovery_contract": recovery_contract,
        }
    )
    return plan


def verify_external_identities(plan: dict[str, Any]) -> dict[str, Any]:
    """Verify the same sources with strict projected inventory equality."""
    data_root: Path = plan["data_root"]
    source_results: dict[str, Any] = {}
    for source in plan["sources"]:
        source_id = source["source_id"]
        manifest_path = base.require_external_child(data_root, Path(source["external_manifest_path"]))
        safe_root = base.require_external_child(data_root, Path(source["safe_root"]))
        if not manifest_path.is_file() or not safe_root.is_dir():
            raise base.RadarRouteError("materialized_input_missing", source_id)
        manifest_hash = base.sha256_file(manifest_path)
        if manifest_hash != source["external_manifest_sha256"]:
            raise base.RadarRouteError("materialization_manifest_hash_mismatch", source_id)
        manifest = base.load_object(manifest_path)
        if manifest.get("source_id") != source_id or manifest.get("exact_product_id") != source["exact_product_id"]:
            raise base.RadarRouteError("materialization_manifest_identity_mismatch", source_id)
        expected_inventory = project_inventory(manifest.get("files"), label=f"{source_id}:manifest")
        actual_inventory = project_inventory(base.stable_inventory(safe_root), label=f"{source_id}:runtime")
        if expected_inventory != actual_inventory:
            raise base.RadarRouteError("materialized_safe_inventory_mismatch", source_id)
        source_results[source_id] = {
            "safe_root": str(safe_root),
            "manifest_sha256": manifest_hash,
            "file_count": len(actual_inventory),
            "total_bytes": sum(item["size_bytes"] for item in actual_inventory),
            "inventory_sha256": base.inventory_sha256(actual_inventory),
        }

    orbit_results: dict[str, Any] = {}
    for source_id, orbit in plan["orbits"].items():
        path = base.require_external_child(data_root, Path(orbit["custody_path"]))
        if not path.is_file() or path.stat().st_size != orbit["custody_size_bytes"] or base.sha256_file(path) != orbit["custody_sha256"]:
            raise base.RadarRouteError("orbit_custody_identity_mismatch", source_id)
        orbit_results[source_id] = {
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "sha256": orbit["custody_sha256"],
        }

    dem_results: dict[str, Any] = {}
    for dem in plan["dems"]:
        source_id = dem["source_id"]
        path = base.require_external_child(data_root, Path(dem["destination_path"]))
        if not path.is_file() or path.stat().st_size != dem["ellipsoidal_derivative_size_bytes"] or base.sha256_file(path) != dem["ellipsoidal_derivative_sha256"]:
            raise base.RadarRouteError("dem_derivative_identity_mismatch", source_id)
        dem_results[source_id] = {
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "sha256": dem["ellipsoidal_derivative_sha256"],
        }
    return {"sources": source_results, "orbits": orbit_results, "dems": dem_results}


__all__ = [
    "CONTRACT_REF",
    "BASE_CONTRACT_REF",
    "inventories_match",
    "load_execution_plan",
    "project_inventory",
    "validate_recovery_contract",
    "verify_external_identities",
]
