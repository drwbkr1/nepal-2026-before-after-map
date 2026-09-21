#!/usr/bin/env python3
"""Exact controls for M2 radar raster-function call-shape recovery-004."""

from __future__ import annotations

import ctypes
import json
import os
import re
import stat
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

import m2_radar_pixel_orbit_application_001_core as base
import m2_radar_pixel_orbit_application_recovery_002_core as recovery_002


CONTRACT_REF = "config/qa/m2-radar-raster-function-call-shape-recovery-004-contract.json"
BASE_CONTRACT_REF = "config/qa/m2-radar-pixel-orbit-application-001-contract.json"
RECOVERY_002_CONTRACT_REF = "config/qa/m2-radar-pixel-orbit-application-recovery-002-contract.json"
ATTEMPT_ID = "radar-pixel-orbit-application-raster-function-recovery-004-real-001"
SOURCE_ORDER = [f"M1-SRC-{index:03d}" for index in range(1, 7)]
ROUTE_ORDER = ["PAIR-S1-ASC-R085-IW", "PAIR-S1-DESC-R121-IW"]
SOURCE_ALIASES = {source_id: str(index) for index, source_id in enumerate(SOURCE_ORDER, start=1)}
ATTEMPT_ROOT = Path(r"C:\Projects\Active\nepal-2026-before-after-map-data\r4\a1")
MAXIMUM_PATH_CHARACTERS = 240
STAGE_ORDER = (
    "attempt_reserved",
    "terminal_and_cleanup_receipts_reserved",
    "fallback_journal_initialized",
    "identity_scan_started",
    "identity_scan_completed",
    "path_projection_started",
    "path_projection_completed",
    "arcpy_import_started",
    "arcpy_import_completed",
    "product_info_started",
    "product_info_completed",
    "image_analyst_checkout_started",
    "image_analyst_checkout_completed",
    "spatial_checkout_started",
    "spatial_checkout_completed",
    "dem_mosaic_started",
    "dem_mosaic_completed",
    "analysis_support_started",
    "analysis_support_completed",
    "source_processing_fixed_order",
    "route_evaluation_fixed_order",
    "postattempt_identity_scan_started",
    "postattempt_identity_scan_completed",
    "terminal_receipt_persisted",
    "cleanup_started",
    "cleanup_completed_or_warning",
)
EXPECTED_AUTHORITY = {
    "approval_ref": "records/source-gates/m2-radar-raster-function-call-shape-recovery-004-approval.json",
    "approval_sha256": "b7133be0ee697895d45ba5702dae046c183472f2c93bf81029f130d333aa460a",
    "review_reconciliation_ref": "records/source-gates/m2-radar-raster-function-call-shape-recovery-004-review-reconciliation.json",
    "review_reconciliation_sha256": "1218d0732ae7794fc0efbe17dc680d02caed30a70baef4409f6d54ae9880acdf",
    "activation_ref": "records/readiness/m2-radar-raster-function-call-shape-recovery-004-approval-activation.json",
    "activation_sha256": "f4539c9707a5935cee0189867ba966a665becc14dccf3bc35a617b981a913a4b",
    "proposal_ref": "contracts/milestone-002-radar-raster-function-call-shape-recovery-004-proposal.json",
    "proposal_sha256": "bee3b46d05bf671b8b6657ee12629dfeaa5f04a9adce40bd0593823a664429ed",
    "review_bundle_ref": "reviews/m2-radar-raster-function-call-shape-recovery-004/review-bundle.json",
    "review_bundle_sha256": "46c52b15d939a2ca7536205b61ec06158a84708e59425a92224a5a6dad7969c5",
}
SOURCE_OUTPUT_NAMES = (
    "thermal_noise_removed.crf",
    "beta0_linear.crf",
    "gamma0_linear_slant.crf",
    "scattering_area.crf",
    "geometric_distortion.crf",
    "geometric_distortion_mask_slant.crf",
    "gamma0_linear_gtc_raw.crf",
    "gamma0_db_gtc_raw.crf",
    "geometric_distortion_mask_gtc_raw.crf",
    "gamma0_linear_epsg32645_10m.crf",
    "gamma0_db_epsg32645_10m.crf",
    "geometric_distortion_mask_epsg32645_10m.crf",
)
ROUTE_OUTPUT_NAMES = (
    "before_gamma0_linear.crf",
    "after_gamma0_linear.crf",
    "before_gamma0_db.crf",
    "after_gamma0_db.crf",
    "before_native_distortion_mask.crf",
    "after_native_distortion_mask.crf",
    "pair_exclusion_mask.tif",
)

write_new_json = recovery_002.write_new_json
append_jsonl = recovery_002.append_jsonl
safe_error = recovery_002.safe_error


def _repo_file(root: Path, ref: str) -> Path:
    candidate = root / ref
    resolved_root = root.resolve()
    resolved = candidate.resolve(strict=False)
    if resolved == resolved_root or resolved_root not in resolved.parents or not candidate.is_file():
        raise base.RadarRouteError("repository_binding_missing_or_unsafe", ref)
    return candidate


def validate_contract(contract: dict[str, Any], root: Path) -> list[str]:
    errors: list[str] = []
    if contract.get("contract_id") != "NEPAL-M2-RADAR-RASTER-FUNCTION-CALL-SHAPE-RECOVERY-004":
        errors.append("contract identity differs")
    if contract.get("status") != "approved_implementation_publication_pending":
        errors.append("contract status differs")
    authority = contract.get("authority", {})
    for key, expected in EXPECTED_AUTHORITY.items():
        if authority.get(key) != expected:
            errors.append(f"authority binding differs: {key}")
    for stem in ("approval", "review_reconciliation", "activation", "proposal", "review_bundle"):
        ref = EXPECTED_AUTHORITY[f"{stem}_ref"]
        expected = EXPECTED_AUTHORITY[f"{stem}_sha256"]
        try:
            if base.sha256_file(_repo_file(root, ref)) != expected:
                errors.append(f"authority bytes differ: {stem}")
        except base.RadarRouteError:
            errors.append(f"authority file missing: {stem}")
    for ref_key, hash_key, expected_ref in (
        ("base_contract_ref", "base_contract_sha256", BASE_CONTRACT_REF),
        ("recovery_002_contract_ref", "recovery_002_contract_sha256", RECOVERY_002_CONTRACT_REF),
    ):
        if contract.get(ref_key) != expected_ref:
            errors.append(f"{ref_key} differs")
        else:
            try:
                if contract.get(hash_key) != base.sha256_file(_repo_file(root, expected_ref)):
                    errors.append(f"{hash_key} differs")
            except base.RadarRouteError:
                errors.append(f"{expected_ref} missing")
    if contract.get("fixed_source_order") != SOURCE_ORDER:
        errors.append("source order differs")
    if contract.get("fixed_route_order") != ROUTE_ORDER:
        errors.append("route order differs")
    if contract.get("source_to_orbit") != {
        "M1-SRC-001": "M2-ORB-001", "M1-SRC-002": "M2-ORB-001",
        "M1-SRC-003": "M2-ORB-002", "M1-SRC-004": "M2-ORB-003",
        "M1-SRC-005": "M2-ORB-003", "M1-SRC-006": "M2-ORB-004",
    }:
        errors.append("source-to-orbit mapping differs")
    if contract.get("stage_order") != list(STAGE_ORDER):
        errors.append("stage order differs")
    if contract.get("short_path_source_aliases") != SOURCE_ALIASES:
        errors.append("source aliases differ")
    if contract.get("attempt_local_receipts") is not True:
        errors.append("attempt-local receipt policy differs")
    if contract.get("receipt_namespace") != "RADAR-RASTER-FUNCTION-CALL-SHAPE-RECOVERY-004":
        errors.append("receipt namespace differs")
    short = contract.get("short_path", {})
    expected_short = {
        "observed_failed_manifest_path_characters": 260,
        "external_attempt_root": str(ATTEMPT_ROOT),
        "external_attempt_root_characters": 57,
        "source_subdirectory_template": "s/<one-digit-fixed-order-index>/<exact-product-id>.SAFE",
        "source_aliases": SOURCE_ALIASES,
        "m1_src_001_manifest_path_characters": 148,
        "maximum_predicted_full_path_characters": 240,
        "first_blocked_path_characters": 241,
        "project_every_verified_safe_member_before_copy": True,
        "project_every_declared_output_and_attempt_control_path": True,
        "preserve_exact_safe_directory_names": True,
        "preserve_exact_source_member_bytes": True,
        "reparse_points_prohibited": True,
        "subst_drive_prohibited": True,
        "alternate_root_prohibited": True,
        "path_traversal_prohibited": True,
    }
    if short != expected_short:
        errors.append("short-path boundary differs")
    attempt = contract.get("attempt", {})
    if (
        attempt.get("attempt_id") != ATTEMPT_ID
        or attempt.get("external_attempt_root") != str(ATTEMPT_ROOT)
        or attempt.get("maximum_final_preflights") != 1
        or attempt.get("maximum_real_attempts") != 1
        or attempt.get("process_count") != 1
        or attempt.get("automatic_retry_authorized") is not False
        or attempt.get("stop_on_first_failure") is not True
        or attempt.get("collision_policy") != "fail"
    ):
        errors.append("attempt boundary differs")
    for key in ("network_requests", "authentication", "source_overwrite", "output_overwrite", "automatic_retry"):
        if contract.get("execution_boundary", {}).get(key) != "prohibited":
            errors.append(f"execution boundary differs: {key}")
    prior_ref = contract.get("prior_short_path_contract_ref")
    if prior_ref != "config/qa/m2-radar-short-path-recovery-003-contract.json":
        errors.append("prior short-path contract ref differs")
    else:
        try:
            if contract.get("prior_short_path_contract_sha256") != base.sha256_file(_repo_file(root, prior_ref)):
                errors.append("prior short-path contract bytes differ")
        except base.RadarRouteError:
            errors.append("prior short-path contract missing")
    call_shape = contract.get("raster_function_call_shape", {})
    if call_shape.get("apply_orbit_correction") != "unchanged_in_place":
        errors.append("ApplyOrbitCorrection boundary differs")
    if call_shape.get("returned_raster_save_exactly_once") is not True:
        errors.append("exclusive Raster save requirement differs")
    if call_shape.get("output_must_be_absent_before_call") is not True or call_shape.get("output_must_exist_after_save") is not True:
        errors.append("Raster output presence guards differ")
    if call_shape.get("exact_argument_counts") != {
        "RemoveThermalNoise": 2,
        "ApplyRadiometricCalibration": 3,
        "ApplyRadiometricTerrainFlattening": 8,
        "ApplyGeometricTerrainCorrection_gamma": 4,
        "ConvertSARUnits": 2,
        "ApplyGeometricTerrainCorrection_mask": 4,
    }:
        errors.append("Raster function argument counts differ")
    if any(value is not False for value in contract.get("claim_boundary", {}).values()):
        errors.append("claim boundary releases prohibited work")
    return errors


def load_execution_plan(root: Path, contract_ref: str = CONTRACT_REF) -> dict[str, Any]:
    contract_path = _repo_file(root, contract_ref)
    contract = base.load_object(contract_path)
    errors = validate_contract(contract, root)
    if errors:
        raise base.RadarRouteError("raster_function_recovery_004_contract_invalid", "; ".join(errors))
    plan = recovery_002.load_execution_plan(root, RECOVERY_002_CONTRACT_REF)
    merged = dict(plan["contract"])
    merged.update({
        "contract_id": contract["contract_id"],
        "status": contract["status"],
        "attempt": contract["attempt"],
        "short_path": contract["short_path"],
        "short_path_source_aliases": contract["short_path_source_aliases"],
        "attempt_local_receipts": contract["attempt_local_receipts"],
        "receipt_namespace": contract["receipt_namespace"],
        "recovery_authority": contract["authority"],
        "receipt_durability": contract["receipt_durability"],
        "stage_order": contract["stage_order"],
    })
    plan.update({"contract": merged, "contract_ref": contract_ref, "contract_sha256": base.sha256_file(contract_path)})
    return plan


def _is_reparse_point(path: Path) -> bool:
    try:
        attributes = path.lstat().st_file_attributes  # type: ignore[attr-defined]
    except (AttributeError, FileNotFoundError, OSError):
        return path.is_symlink()
    return bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def path_chain_has_reparse(path: Path) -> bool:
    candidate = path
    while True:
        if candidate.exists() and _is_reparse_point(candidate):
            return True
        parent = candidate.parent
        if parent == candidate:
            return False
        candidate = parent


def is_subst_drive(path: Path) -> bool:
    if os.name != "nt" or not path.drive:
        return False
    buffer = ctypes.create_unicode_buffer(32768)
    result = ctypes.windll.kernel32.QueryDosDeviceW(path.drive, buffer, len(buffer))  # type: ignore[attr-defined]
    if result == 0:
        raise base.RadarRouteError("drive_mapping_query_failed")
    mapping = buffer.value.casefold()
    return mapping.startswith("\\??\\") and not mapping.startswith("\\device\\")


def _safe_relative(value: object) -> PurePosixPath:
    text = str(value).replace("\\", "/")
    relative = PurePosixPath(text)
    if relative.is_absolute() or not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
        raise base.RadarRouteError("unsafe_inventory_relative_path", text)
    return relative


def _assert_contained(root: Path, candidate: Path) -> None:
    resolved_root = root.resolve(strict=False)
    resolved = candidate.resolve(strict=False)
    if resolved == resolved_root or resolved_root not in resolved.parents:
        raise base.RadarRouteError("projected_path_escape")


def _declared_paths(plan: dict[str, Any], target: Path) -> Iterable[tuple[str, Path]]:
    for name in (
        "stages.jsonl", "fallback.jsonl", "terminal-reservation.json", "cleanup-reservation.json",
        "started.json", "terminal.json", "cleanup.json", "dem/ellipsoidal_dem_mosaic.tif",
        "support/qa.gdb", "support/qa.gdb/ApprovedStudyAreas", "support/snap_10m.tif",
    ):
        yield "declared_control_or_support", target / name
    for source in plan["sources"]:
        source_id = source["source_id"]
        root = target / "s" / SOURCE_ALIASES[source_id]
        yield "source_receipt", target / "receipts" / "sources" / f"{source_id.lower()}-started.json"
        yield "source_receipt", target / "receipts" / "sources" / f"{source_id.lower()}-terminal.json"
        for name in SOURCE_OUTPUT_NAMES:
            yield "declared_source_output", root / name
        manifest_path = base.require_external_child(plan["data_root"], Path(source["external_manifest_path"]))
        manifest = base.load_object(manifest_path)
        files = manifest.get("files")
        if not isinstance(files, list):
            raise base.RadarRouteError("materialization_manifest_inventory_missing", source_id)
        safe_copy = root / source["exact_product_id"]
        for item in files:
            if not isinstance(item, dict) or "relative_path" not in item:
                raise base.RadarRouteError("materialization_manifest_inventory_invalid", source_id)
            relative = _safe_relative(item["relative_path"])
            yield "verified_safe_member", safe_copy.joinpath(*relative.parts)
    for route_id in ROUTE_ORDER:
        route_root = target / "routes" / route_id.lower()
        yield "route_receipt", target / "receipts" / "routes" / f"{route_id.lower()}-started.json"
        yield "route_receipt", target / "receipts" / "routes" / f"{route_id.lower()}-terminal.json"
        for name in ROUTE_OUTPUT_NAMES:
            yield "declared_route_output", route_root / name


def project_short_paths(plan: dict[str, Any], target: Path) -> dict[str, Any]:
    expected = base.require_external_child(plan["data_root"], ATTEMPT_ROOT, must_exist=False)
    if target.resolve(strict=False) != expected.resolve(strict=False):
        raise base.RadarRouteError("short_path_attempt_root_mismatch")
    if is_subst_drive(target):
        raise base.RadarRouteError("short_path_subst_drive_prohibited")
    if path_chain_has_reparse(target):
        raise base.RadarRouteError("short_path_reparse_point_prohibited")
    seen: set[str] = set()
    reserved_before_projection = {
        "stages.jsonl",
        "fallback.jsonl",
        "terminal-reservation.json",
        "cleanup-reservation.json",
        "started.json",
    }
    maximum = 0
    longest_kind = ""
    count = 0
    for kind, path in _declared_paths(plan, target):
        _assert_contained(target, path)
        normalized = os.path.normcase(str(path.resolve(strict=False)))
        if normalized in seen:
            raise base.RadarRouteError("short_path_projected_collision")
        seen.add(normalized)
        relative_key = path.relative_to(target).as_posix()
        if path.exists() and relative_key not in reserved_before_projection:
            raise base.RadarRouteError("short_path_projected_destination_exists")
        length = len(str(path))
        if length > MAXIMUM_PATH_CHARACTERS:
            raise base.RadarRouteError("short_path_projection_exceeds_240", str(length))
        if length > maximum:
            maximum = length
            longest_kind = kind
        count += 1
    return {
        "status": "pass_all_projected_paths_at_or_below_240",
        "projected_path_count": count,
        "maximum_projected_path_characters": maximum,
        "maximum_allowed_path_characters": MAXIMUM_PATH_CHARACTERS,
        "longest_path_kind": longest_kind,
        "absolute_paths_recorded": False,
    }


def stage_positions(stages: Iterable[str]) -> list[int]:
    positions = {name: index for index, name in enumerate(STAGE_ORDER)}
    result: list[int] = []
    for stage in stages:
        if stage not in positions:
            raise base.RadarRouteError("unknown_raster_function_recovery_004_stage", stage)
        result.append(positions[stage])
    return result


verify_external_identities = recovery_002.verify_external_identities
