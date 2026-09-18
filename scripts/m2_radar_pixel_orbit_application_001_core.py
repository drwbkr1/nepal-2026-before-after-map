#!/usr/bin/env python3
"""Portable controls for the approved M2 radar orbit-application and pixel-QA route."""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import stat
from pathlib import Path, PurePosixPath
from typing import Any, Callable

import numpy as np

from pixel_qa_core import (
    combine_statuses,
    evaluate_aoi_coverage,
    evaluate_grid_pair,
    evaluate_registration,
)


SOURCE_ORDER = [f"M1-SRC-{index:03d}" for index in range(1, 7)]
ROUTE_ORDER = ["PAIR-S1-ASC-R085-IW", "PAIR-S1-DESC-R121-IW"]
SOURCE_TO_ORBIT = {
    "M1-SRC-001": "M2-ORB-001",
    "M1-SRC-002": "M2-ORB-001",
    "M1-SRC-003": "M2-ORB-002",
    "M1-SRC-004": "M2-ORB-003",
    "M1-SRC-005": "M2-ORB-003",
    "M1-SRC-006": "M2-ORB-004",
}
EXPECTED_BINDING_HASHES = {
    "approval_sha256": "1d6522a0a340e3237c29b8489e742c6a8b376314c358ee9ae0d323621cf4b6fe",
    "proposal_sha256": "3a0f03c5269f4e3e6822c1e31bbe5f19cd288e9e17db67b42990d96b27a4f490",
    "candidate_manifest_sha256": "dc4ff8a70c3eb115ee78069afbfd759cc1532fce58de6970584d6b7e5fa34af7",
    "readiness_audit_sha256": "f3b9ab47d459fe602f2d88d1f771c13256167abfd1e44b23eef1497da75440da",
    "radar_header_receipt_sha256": "3513098380204268c0fb9c1eb154db36df71f47a1a11fe05e577a12f915ad3da",
    "pair_plan_sha256": "c346af2e575a21e4931991935c0acc21ba70083c4613255456ced77b71bb1560",
    "radar_processing_contract_sha256": "d70bda6235511f30185558d18e5902d69be81dcfa02517117f1dc404e450f26f",
    "pixel_readiness_contract_sha256": "5a66ae11288813868f362c342027ce0e4850d435dfbb2cfec3f5098b17d123e2",
    "approved_aoi_projected_sha256": "3d6c9bb39fa9b3ffeddfb0048ddabf30ee4472c0006b78c5c7d58193693ac615",
    "capability_sha256": "78140554ab6571070de5051ed98cd2eac4a6c8a40bec5aca6983d74b6c0f879b",
}


class RadarRouteError(RuntimeError):
    """Fail-closed route error with a stable machine-readable code."""

    def __init__(self, code: str, detail: str | None = None):
        super().__init__(code if detail is None else f"{code}: {detail}")
        self.code = code
        self.detail = detail


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RadarRouteError("json_root_not_object", str(path))
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_new_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(canonical_bytes(value))
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise RadarRouteError("output_collision", str(path)) from exc


def _is_reparse(path: Path) -> bool:
    information = path.stat(follow_symlinks=False)
    return path.is_symlink() or bool(
        getattr(information, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def require_external_child(root: Path, candidate: Path, *, must_exist: bool = True) -> Path:
    try:
        resolved_root = root.resolve(strict=True)
        resolved = candidate.resolve(strict=must_exist)
        resolved.relative_to(resolved_root)
    except (FileNotFoundError, ValueError) as exc:
        raise RadarRouteError("path_outside_exact_external_root", str(candidate)) from exc
    if resolved == resolved_root:
        raise RadarRouteError("path_must_be_external_root_child", str(candidate))
    current = resolved if resolved.exists() else resolved.parent
    while current != resolved_root:
        if current.exists() and _is_reparse(current):
            raise RadarRouteError("reparse_point_prohibited", str(current))
        current = current.parent
    return resolved


def stable_inventory(root: Path) -> list[dict[str, Any]]:
    if not root.is_dir() or _is_reparse(root):
        raise RadarRouteError("inventory_root_invalid", str(root))
    result: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().casefold()):
        if _is_reparse(path):
            raise RadarRouteError("inventory_reparse_point", str(path))
        if path.is_file():
            result.append(
                {
                    "relative_path": path.relative_to(root).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    return result


def inventory_sha256(items: list[dict[str, Any]]) -> str:
    return hashlib.sha256(canonical_bytes(items)).hexdigest()


def copy_safe_exclusive(source: Path, destination: Path) -> dict[str, Any]:
    if destination.exists():
        raise RadarRouteError("output_collision", str(destination))
    before = stable_inventory(source)
    try:
        shutil.copytree(source, destination, symlinks=False)
    except FileExistsError as exc:
        raise RadarRouteError("output_collision", str(destination)) from exc
    after = stable_inventory(source)
    copied = stable_inventory(destination)
    if before != after:
        raise RadarRouteError("source_changed_during_copy", str(source))
    if copied != before:
        raise RadarRouteError("copied_safe_inventory_mismatch", str(destination))
    return {
        "file_count": len(before),
        "total_bytes": sum(item["size_bytes"] for item in before),
        "inventory_sha256": inventory_sha256(before),
        "source_inventory_unchanged": True,
        "copied_inventory_matches_source": True,
    }


def _repo_path(root: Path, ref: str) -> Path:
    posix = PurePosixPath(ref)
    if posix.is_absolute() or any(part in {"", ".", ".."} for part in posix.parts):
        raise RadarRouteError("unsafe_repository_ref", ref)
    try:
        path = root.joinpath(*posix.parts).resolve(strict=True)
        path.relative_to(root.resolve(strict=True))
    except (FileNotFoundError, ValueError) as exc:
        raise RadarRouteError("missing_or_unsafe_repository_ref", ref) from exc
    return path


def validate_contract(contract: dict[str, Any], root: Path) -> list[str]:
    errors: list[str] = []
    if contract.get("contract_id") != "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-001":
        errors.append("contract identity differs")
    if contract.get("status") != "active_preobservation_exact_six_source_one_attempt":
        errors.append("contract status differs")
    if contract.get("fixed_source_order") != SOURCE_ORDER:
        errors.append("fixed source order differs")
    if contract.get("fixed_route_order") != ROUTE_ORDER:
        errors.append("fixed route order differs")
    if contract.get("source_to_orbit") != SOURCE_TO_ORBIT:
        errors.append("source-to-orbit map differs")
    if [item.get("source_id") for item in contract.get("sources", [])] != SOURCE_ORDER:
        errors.append("source binding order differs")
    if [item.get("source_id") for item in contract.get("orbits", [])] != [f"M2-ORB-{index:03d}" for index in range(1, 5)]:
        errors.append("orbit binding order differs")
    if [item.get("source_id") for item in contract.get("ellipsoidal_dem_inputs", [])] != [f"M2-DEM-{index:03d}" for index in range(1, 5)]:
        errors.append("DEM binding order differs")
    grid = contract.get("analysis_grid", {})
    if grid.get("wkid") != 32645 or grid.get("cell_size_m") != 10.0:
        errors.append("analysis grid differs")
    processing = contract.get("processing", {})
    expected_processing = {
        "copy_safe_before_orbit_application": True,
        "orbit_tool": "ApplyOrbitCorrection_ia",
        "orbit_file_explicit": True,
        "polarization_order": ["VV", "VH"],
        "thermal_noise_tool": "RemoveThermalNoise_ia",
        "calibration_tool": "ApplyRadiometricCalibration_ia",
        "calibration_type": "BETA_NOUGHT",
        "flattening_tool": "ApplyRadiometricTerrainFlattening_ia",
        "flattening_type": "GAMMA_NOUGHT",
        "geoid": "NONE",
        "geometric_tool": "ApplyGeometricTerrainCorrection_ia",
        "output_wkid": 32645,
        "output_cell_size_m": 10.0,
        "db_tool": "ConvertSARUnits_ia",
        "db_conversion": "LINEAR_TO_DB",
        "linear_master_retained": True,
        "primary_despeckle": "NONE",
        "route_independence": True,
    }
    for key, expected in expected_processing.items():
        if processing.get(key) != expected:
            errors.append(f"processing setting differs: {key}")
    attempt = contract.get("attempt", {})
    if attempt.get("attempt_id") != "radar-pixel-orbit-application-001-real-001":
        errors.append("attempt identity differs")
    for key in (
        "maximum_final_preflights",
        "maximum_orbit_application_attempts_per_source",
        "maximum_qa_processing_attempts_per_source",
        "maximum_route_qa_attempts_per_pair",
    ):
        if attempt.get(key) != 1:
            errors.append(f"attempt limit differs: {key}")
    if attempt.get("automatic_retry_authorized") is not False or attempt.get("stop_on_first_source_execution_failure") is not True:
        errors.append("retry or stop-on-failure policy differs")
    boundary = contract.get("execution_boundary", {})
    for key in ("network_requests", "authentication", "source_overwrite", "output_overwrite", "automatic_retry"):
        if boundary.get(key) != "prohibited":
            errors.append(f"execution boundary differs: {key}")
    if any(value is not False for value in contract.get("claim_boundary", {}).values()):
        errors.append("claim boundary releases prohibited work")
    bindings = contract.get("bindings", {})
    for hash_key, expected_hash in EXPECTED_BINDING_HASHES.items():
        ref_key = hash_key.removesuffix("_sha256") + "_ref"
        ref = bindings.get(ref_key)
        if bindings.get(hash_key) != expected_hash:
            errors.append(f"binding hash differs: {hash_key}")
            continue
        try:
            if not isinstance(ref, str) or sha256_file(_repo_path(root, ref)) != expected_hash:
                errors.append(f"bound file differs: {ref_key}")
        except RadarRouteError:
            errors.append(f"bound file missing or unsafe: {ref_key}")
    return errors


def load_execution_plan(root: Path, contract_ref: str) -> dict[str, Any]:
    contract_path = _repo_path(root, contract_ref)
    contract = load_object(contract_path)
    errors = validate_contract(contract, root)
    if errors:
        raise RadarRouteError("implementation_contract_invalid", "; ".join(errors))
    data_root = Path(contract["execution_boundary"]["external_data_root"])
    expected_data_root = root.parent / f"{root.name}-data"
    if data_root.resolve(strict=True) != expected_data_root.resolve(strict=True):
        raise RadarRouteError("external_data_root_mismatch")

    sources: list[dict[str, Any]] = []
    for expected in contract["sources"]:
        receipt_path = _repo_path(root, expected["materialization_receipt_ref"])
        if sha256_file(receipt_path) != expected["materialization_receipt_sha256"]:
            raise RadarRouteError("materialization_receipt_hash_mismatch", expected["source_id"])
        receipt = load_object(receipt_path)
        if receipt.get("status") != "pass_materialization_only" or receipt.get("source_id") != expected["source_id"] or receipt.get("exact_product_id") != expected["exact_product_id"]:
            raise RadarRouteError("materialization_receipt_identity_mismatch", expected["source_id"])
        sources.append(
            {
                **expected,
                "external_manifest_path": receipt["bindings"]["external_manifest_path"],
                "safe_root": receipt["external_safe_root"],
                "orbit_source_id": contract["source_to_orbit"][expected["source_id"]],
            }
        )

    orbits: dict[str, dict[str, Any]] = {}
    for expected in contract["orbits"]:
        receipt_path = _repo_path(root, expected["verification_receipt_ref"])
        if sha256_file(receipt_path) != expected["verification_receipt_sha256"]:
            raise RadarRouteError("orbit_receipt_hash_mismatch", expected["source_id"])
        receipt = load_object(receipt_path)
        if receipt.get("source_id") != expected["source_id"] or receipt.get("status") != "pass_orbit_input_only" or receipt.get("custody_path") != expected["custody_path"]:
            raise RadarRouteError("orbit_receipt_identity_mismatch", expected["source_id"])
        orbits[expected["source_id"]] = dict(expected)

    dems: list[dict[str, Any]] = []
    for expected in contract["ellipsoidal_dem_inputs"]:
        receipt_path = _repo_path(root, expected["terminal_receipt_ref"])
        if sha256_file(receipt_path) != expected["terminal_receipt_sha256"]:
            raise RadarRouteError("dem_receipt_hash_mismatch", expected["source_id"])
        receipt = load_object(receipt_path)
        if receipt.get("source_id") != expected["source_id"] or receipt.get("status") != "pass_converted_verified_promoted" or receipt.get("destination_path") != expected["destination_path"]:
            raise RadarRouteError("dem_receipt_identity_mismatch", expected["source_id"])
        dems.append(dict(expected))
    return {
        "contract": contract,
        "contract_ref": contract_ref,
        "contract_sha256": sha256_file(contract_path),
        "data_root": data_root,
        "sources": sources,
        "orbits": orbits,
        "dems": dems,
    }


def verify_external_identities(plan: dict[str, Any]) -> dict[str, Any]:
    data_root: Path = plan["data_root"]
    source_results: dict[str, Any] = {}
    for source in plan["sources"]:
        source_id = source["source_id"]
        manifest_path = require_external_child(data_root, Path(source["external_manifest_path"]))
        safe_root = require_external_child(data_root, Path(source["safe_root"]))
        if not manifest_path.is_file() or not safe_root.is_dir():
            raise RadarRouteError("materialized_input_missing", source_id)
        manifest_hash = sha256_file(manifest_path)
        if manifest_hash != source["external_manifest_sha256"]:
            raise RadarRouteError("materialization_manifest_hash_mismatch", source_id)
        manifest = load_object(manifest_path)
        if manifest.get("source_id") != source_id or manifest.get("exact_product_id") != source["exact_product_id"]:
            raise RadarRouteError("materialization_manifest_identity_mismatch", source_id)
        expected_inventory = manifest.get("files")
        actual_inventory = stable_inventory(safe_root)
        if expected_inventory != actual_inventory:
            raise RadarRouteError("materialized_safe_inventory_mismatch", source_id)
        source_results[source_id] = {
            "safe_root": str(safe_root),
            "manifest_sha256": manifest_hash,
            "file_count": len(actual_inventory),
            "total_bytes": sum(item["size_bytes"] for item in actual_inventory),
            "inventory_sha256": inventory_sha256(actual_inventory),
        }

    orbit_results: dict[str, Any] = {}
    for source_id, orbit in plan["orbits"].items():
        path = require_external_child(data_root, Path(orbit["custody_path"]))
        if not path.is_file() or path.stat().st_size != orbit["custody_size_bytes"] or sha256_file(path) != orbit["custody_sha256"]:
            raise RadarRouteError("orbit_custody_identity_mismatch", source_id)
        orbit_results[source_id] = {"path": str(path), "size_bytes": path.stat().st_size, "sha256": orbit["custody_sha256"]}

    dem_results: dict[str, Any] = {}
    for dem in plan["dems"]:
        source_id = dem["source_id"]
        path = require_external_child(data_root, Path(dem["destination_path"]))
        if not path.is_file() or path.stat().st_size != dem["ellipsoidal_derivative_size_bytes"] or sha256_file(path) != dem["ellipsoidal_derivative_sha256"]:
            raise RadarRouteError("dem_derivative_identity_mismatch", source_id)
        dem_results[source_id] = {"path": str(path), "size_bytes": path.stat().st_size, "sha256": dem["ellipsoidal_derivative_sha256"]}
    return {"sources": source_results, "orbits": orbit_results, "dems": dem_results}


def execute_fixed_order(
    source_ids: list[str],
    worker: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    if source_ids != SOURCE_ORDER:
        raise RadarRouteError("source_order_mismatch")
    results: list[dict[str, Any]] = []
    stopped_source_id: str | None = None
    for source_id in source_ids:
        try:
            result = worker(source_id)
        except Exception as exc:  # the supervisor must preserve and stop every failure
            result = {
                "source_id": source_id,
                "status": "failed",
                "failure_type": type(exc).__name__,
                "failure_code": getattr(exc, "code", "unexpected_source_failure"),
            }
        if result.get("source_id") != source_id:
            raise RadarRouteError("worker_source_identity_mismatch", source_id)
        results.append(result)
        if result.get("status") != "pass_source_qa_only":
            stopped_source_id = source_id
            break
    return {
        "status": "pass_all_sources" if stopped_source_id is None and len(results) == len(source_ids) else "stopped_on_first_failure",
        "results": results,
        "completed_source_ids": [item["source_id"] for item in results if item.get("status") == "pass_source_qa_only"],
        "stopped_source_id": stopped_source_id,
        "automatic_retry_performed": False,
    }


def classify_radar_pair(
    before_native_mask: np.ndarray,
    after_native_mask: np.ndarray,
    before_valid: np.ndarray,
    after_valid: np.ndarray,
) -> dict[str, Any]:
    if any(item.shape != before_native_mask.shape for item in (after_native_mask, before_valid, after_valid)):
        raise ValueError("radar pair arrays differ")
    classes = np.full(before_native_mask.shape, 90, dtype=np.int16)
    covered = before_valid & after_valid
    classes[~covered] = 0
    remaining = covered.copy()
    layover = remaining & (np.isin(before_native_mask, [4, 5]) | np.isin(after_native_mask, [4, 5]))
    classes[layover] = 2
    remaining &= ~layover
    shadow = remaining & ((before_native_mask == 3) | (after_native_mask == 3))
    classes[shadow] = 3
    remaining &= ~shadow
    undetermined = remaining & ((before_native_mask == 0) | (after_native_mask == 0))
    classes[undetermined] = 0
    remaining &= ~undetermined
    geometrically_valid = remaining & np.isin(before_native_mask, [1, 2]) & np.isin(after_native_mask, [1, 2])
    classes[geometrically_valid] = 1
    return {
        "classes": classes,
        "covered": covered,
        "pair_valid": classes == 1,
        "unknown_native_class_present": bool(np.any(classes == 90)),
        "class_counts": {str(value): int(np.count_nonzero(classes == value)) for value in sorted(set(classes.ravel().tolist()))},
    }


def _correlation(left: np.ndarray, right: np.ndarray, valid: np.ndarray, minimum_count: int) -> float | None:
    if int(valid.sum()) < minimum_count:
        return None
    x = left[valid].astype(np.float64)
    y = right[valid].astype(np.float64)
    x -= x.mean()
    y -= y.mean()
    denominator = float(np.sqrt(np.dot(x, x) * np.dot(y, y)))
    if not math.isfinite(denominator) or denominator <= 0:
        return None
    result = float(np.dot(x, y) / denominator)
    return result if math.isfinite(result) else None


def _parabolic(left: float | None, center: float, right: float | None) -> float:
    if left is None or right is None:
        return 0.0
    denominator = left - 2.0 * center + right
    if abs(denominator) < 1e-12:
        return 0.0
    return max(-0.5, min(0.5, 0.5 * (left - right) / denominator))


def measure_stable_registration(
    before: np.ndarray,
    after: np.ndarray,
    pair_valid: np.ndarray,
    *,
    grid: dict[str, float],
    overview_bbox: tuple[float, float, float, float],
    exclusion_bboxes: list[tuple[float, float, float, float]],
    settings: dict[str, Any],
    pixel_contract: dict[str, Any],
) -> dict[str, Any]:
    if before.shape != after.shape or before.shape != pair_valid.shape or before.ndim != 2:
        raise ValueError("registration arrays differ")
    rows, columns = before.shape
    radius = int(settings["patch_radius_pixels"])
    search = int(settings["search_radius_pixels"])
    margin = radius + search + 1
    if rows <= 2 * margin or columns <= 2 * margin:
        return {
            **evaluate_registration(stable_control_pair_count=None, rmse_pixels=None, bias_x_pixels=None, bias_y_pixels=None, contract=pixel_contract),
            "candidate_count": 0,
            "accepted_control_count": 0,
            "rejected_counts": {"insufficient_raster_size": 1},
            "controls": [],
            "method": "deterministic VV normalized local cross-correlation outside buffered event AOIs",
        }
    candidate_rows = np.linspace(margin, rows - margin - 1, int(settings["candidate_grid_rows"]), dtype=int)
    candidate_columns = np.linspace(margin, columns - margin - 1, int(settings["candidate_grid_columns"]), dtype=int)
    required = int(math.ceil((2 * radius + 1) ** 2 * float(settings["minimum_pair_valid_fraction"])))
    accepted: list[dict[str, Any]] = []
    rejected = {"outside_overview": 0, "event_exclusion": 0, "insufficient_valid": 0, "low_texture": 0, "low_correlation": 0}
    buffer_m = float(settings["event_aoi_exclusion_buffer_m"])
    for row in candidate_rows:
        y = float(grid["ymax"]) - (float(row) + 0.5) * float(grid["cell_size_m"])
        for column in candidate_columns:
            x = float(grid["xmin"]) + (float(column) + 0.5) * float(grid["cell_size_m"])
            if not (overview_bbox[0] <= x <= overview_bbox[2] and overview_bbox[1] <= y <= overview_bbox[3]):
                rejected["outside_overview"] += 1
                continue
            if any(xmin - buffer_m <= x <= xmax + buffer_m and ymin - buffer_m <= y <= ymax + buffer_m for xmin, ymin, xmax, ymax in exclusion_bboxes):
                rejected["event_exclusion"] += 1
                continue
            base = before[row - radius:row + radius + 1, column - radius:column + radius + 1]
            base_valid = pair_valid[row - radius:row + radius + 1, column - radius:column + radius + 1]
            if int(base_valid.sum()) < required:
                rejected["insufficient_valid"] += 1
                continue
            correlations: dict[tuple[int, int], float | None] = {}
            for dy in range(-search, search + 1):
                for dx in range(-search, search + 1):
                    shifted = after[row + dy - radius:row + dy + radius + 1, column + dx - radius:column + dx + radius + 1]
                    shifted_valid = pair_valid[row + dy - radius:row + dy + radius + 1, column + dx - radius:column + dx + radius + 1]
                    valid = base_valid & shifted_valid
                    if int(valid.sum()) < required:
                        correlations[(dx, dy)] = None
                    elif float(np.std(base[valid])) <= float(settings["minimum_patch_standard_deviation"]) or float(np.std(shifted[valid])) <= float(settings["minimum_patch_standard_deviation"]):
                        correlations[(dx, dy)] = None
                    else:
                        correlations[(dx, dy)] = _correlation(base, shifted, valid, required)
            usable = [(value, dx, dy) for (dx, dy), value in correlations.items() if value is not None]
            if not usable:
                rejected["low_texture"] += 1
                continue
            peak, dx, dy = max(usable, key=lambda item: (item[0], -abs(item[1]) - abs(item[2]), -abs(item[1]), -abs(item[2])))
            if peak < float(settings["minimum_correlation"]):
                rejected["low_correlation"] += 1
                continue
            accepted.append(
                {
                    "x": x,
                    "y": y,
                    "shift_x_pixels": dx + _parabolic(correlations.get((dx - 1, dy)), peak, correlations.get((dx + 1, dy))),
                    "shift_y_pixels": dy + _parabolic(correlations.get((dx, dy - 1)), peak, correlations.get((dx, dy + 1))),
                    "correlation": peak,
                }
            )
    if accepted:
        shifts_x = np.array([item["shift_x_pixels"] for item in accepted], dtype=np.float64)
        shifts_y = np.array([item["shift_y_pixels"] for item in accepted], dtype=np.float64)
        rmse = float(np.sqrt(np.mean(shifts_x ** 2 + shifts_y ** 2)))
        bias_x = float(np.mean(shifts_x))
        bias_y = float(np.mean(shifts_y))
    else:
        rmse = bias_x = bias_y = None
    decision = evaluate_registration(
        stable_control_pair_count=len(accepted),
        rmse_pixels=rmse,
        bias_x_pixels=bias_x,
        bias_y_pixels=bias_y,
        contract=pixel_contract,
    )
    return {
        **decision,
        "candidate_count": int(len(candidate_rows) * len(candidate_columns)),
        "accepted_control_count": len(accepted),
        "rejected_counts": rejected,
        "controls": accepted,
        "method": "deterministic VV normalized local cross-correlation outside buffered event AOIs",
    }


def evaluate_same_date_seam(left: np.ndarray, right: np.ndarray, valid: np.ndarray) -> dict[str, Any]:
    if left.shape != right.shape or left.shape != valid.shape:
        raise ValueError("seam arrays differ")
    usable = valid & np.isfinite(left) & np.isfinite(right)
    count = int(usable.sum())
    if count == 0:
        return {"status": "defer", "overlap_valid_pixel_count": 0, "median_absolute_difference": None, "p95_absolute_difference": None}
    difference = np.abs(left[usable].astype(np.float64) - right[usable].astype(np.float64))
    return {
        "status": "pass_qa_only",
        "overlap_valid_pixel_count": count,
        "median_absolute_difference": float(np.median(difference)),
        "p95_absolute_difference": float(np.percentile(difference, 95)),
        "threshold_applied": False,
    }


def evaluate_route(
    *,
    route_id: str,
    aoi_observations: list[dict[str, Any]],
    before_grid: dict[str, Any],
    after_grid: dict[str, Any],
    registration: dict[str, Any],
    seam_observations: list[dict[str, Any]],
    pixel_contract: dict[str, Any],
    unknown_mask_class_present: bool,
) -> dict[str, Any]:
    if route_id not in ROUTE_ORDER:
        raise ValueError("unknown route")
    aoi_results = [evaluate_aoi_coverage(contract=pixel_contract, **item) for item in aoi_observations]
    grid_result = evaluate_grid_pair(before_grid, after_grid, pixel_contract)
    statuses = [item["status"] for item in aoi_results] + [grid_result["status"], registration["status"]]
    if seam_observations:
        statuses.extend(item["status"] for item in seam_observations)
    if unknown_mask_class_present:
        statuses.append("defer")
    status = combine_statuses(statuses)
    return {
        "route_id": route_id,
        "status": status,
        "aoi_coverage": aoi_results,
        "grid_compatibility": grid_result,
        "registration": {key: value for key, value in registration.items() if key != "controls"},
        "registration_controls": registration.get("controls", []),
        "same_date_seams": seam_observations,
        "unknown_mask_class_present": unknown_mask_class_present,
        "baseline_admission_authorized": False,
        "change_analysis_authorized": False,
        "scientific_admission_authorized": False,
    }
