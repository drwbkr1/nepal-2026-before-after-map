#!/usr/bin/env python3
"""One append-only DEM/gamma coverage audit and conditional diagnostic GTC call."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib
import inspect
import json
import math
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable

import numpy as np

from m2_radar_esri_sequence_recovery_005_core import is_subst_drive, path_chain_has_reparse


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-dem-fitness-comparison-001"
PROPOSAL_REF = "contracts/milestone-002-m2-radar-dem-fitness-comparison-001-proposal.json"
BUNDLE_REF = f"reviews/{PREFIX}/review-bundle.json"
APPROVAL_REF = f"records/source-gates/{PREFIX}-approval.json"
PACKET_GATE_REF = f"records/readiness/{PREFIX}-packet-publication-gate.json"
RUNTIME_REF = f"records/readiness/{PREFIX}-arcgis-runtime-validation-final.json"
READINESS_REF = f"records/readiness/{PREFIX}-implementation-readiness.json"
IMPLEMENTATION_GATE_REF = f"records/readiness/{PREFIX}-implementation-publication-gate.json"
EXECUTION_GATE_REF = f"records/readiness/{PREFIX}-execution-publication-gate.json"
PREFLIGHT_REF = f"records/readiness/{PREFIX}-final-preflight.json"
AOI_REF = "config/aoi/approved-study-areas-epsg32645.json"
RUNNER_REF = "scripts/m2_radar_dem_fitness_comparison_001.py"
VALIDATOR_REF = "scripts/validate_m2_radar_dem_fitness_comparison_001_arcgis.py"
TEST_REF = "tests/test_m2_radar_dem_fitness_comparison_001.py"
PROPOSAL_SHA = "a918f784e4722dfa25ddf8c78b0dc98abab86bd4c2023e439293d4004baebf06"
BUNDLE_SHA = "f85cfa93c89deb4b50670ede59406bc8ff07b272cffcc2803a15fa5fb870a654"
GAMMA = Path(r"C:\Projects\Active\nepal-2026-before-after-map-data\r5\a1\s\1\gamma0_linear_despeckled.crf")
DEM = Path(r"C:\Projects\Active\nepal-2026-before-after-map-data\r5\a1\dem\ellipsoidal_dem_mosaic.tif")
ATTEMPT_ROOT = Path(r"C:\Projects\Active\nepal-2026-before-after-map-data\r5\d3")
OUTPUT = ATTEMPT_ROOT / "gtc_with_existing_dem_diagnostic.crf"
ATTEMPT_ID = "radar-dem-fitness-comparison-001-real-001"
MIN_FREE_BYTES = 60 * 1024**3
BLOCK_SIZE = 512
GTC_PARAMETERS = ("in_radar_data", "polarization_bands", "in_dem_raster", "geoid")
AOI_IDS = ("AOI-OVERVIEW", "AOI-SOURCE", "AOI-UPPER-CORRIDOR")


class ComparisonError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ComparisonError("invalid_json_object")
    return value


def write_new_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def git_head(ref: str = "HEAD") -> str:
    return subprocess.check_output(["git", "rev-parse", ref], cwd=ROOT, text=True).strip()


def verify_authority() -> dict[str, Any]:
    if sha256(ROOT / PROPOSAL_REF) != PROPOSAL_SHA or sha256(ROOT / BUNDLE_REF) != BUNDLE_SHA:
        raise ComparisonError("review_identity_mismatch")
    bundle = load_json(ROOT / BUNDLE_REF)
    if any(sha256(ROOT / item["path"]) != item["sha256"] for item in bundle["artifacts"]):
        raise ComparisonError("frozen_evidence_drift")
    proposal = load_json(ROOT / PROPOSAL_REF)
    scope = proposal.get("proposed_single_authority_envelope", {})
    if (
        scope.get("attempt_id") != ATTEMPT_ID
        or scope.get("exact_gamma_input") != str(GAMMA)
        or scope.get("exact_dem_input") != str(DEM)
        or scope.get("prospective_attempt_root") != str(ATTEMPT_ROOT)
        or scope.get("exact_aoi_ref") != AOI_REF
        or scope.get("output_ref_within_attempt_root") != OUTPUT.name
        or scope.get("maximum_new_processes") != 1
        or scope.get("maximum_gtc_calls") != 1
        or scope.get("maximum_output_saves") != 1
        or scope.get("automatic_retry") is not False
        or scope.get("additional_dem_tile_requests") != 0
    ):
        raise ComparisonError("proposal_scope_mismatch")
    approval = load_json(ROOT / APPROVAL_REF)
    if (
        approval.get("attestation") is not True
        or approval.get("human_decision_count") != 1
        or approval.get("bindings", {}).get("proposal_sha256") != PROPOSAL_SHA
        or approval.get("bindings", {}).get("review_bundle_sha256") != BUNDLE_SHA
        or approval.get("authorized_scope", {}).get("maximum_fresh_diagnostic_processes") != 1
        or approval.get("authorized_scope", {}).get("maximum_conditional_dem_supplied_gtc_calls") != 1
        or approval.get("authorized_scope", {}).get("automatic_retry") is not False
    ):
        raise ComparisonError("approval_scope_mismatch")
    packet_gate = load_json(ROOT / PACKET_GATE_REF)
    if (
        packet_gate.get("status") != "pass_exact_public_packet_and_approval_ci_implementation_eligible"
        or packet_gate.get("bindings", {}).get("approval_sha256") != sha256(ROOT / APPROVAL_REF)
        or packet_gate.get("bindings", {}).get("public_ci_conclusion") != "success"
    ):
        raise ComparisonError("packet_publication_gate_invalid")
    return approval


def code_bindings() -> dict[str, str]:
    return {
        "approval_sha256": sha256(ROOT / APPROVAL_REF),
        "runner_sha256": sha256(ROOT / RUNNER_REF),
        "validator_sha256": sha256(ROOT / VALIDATOR_REF),
        "test_sha256": sha256(ROOT / TEST_REF),
        "runtime_validation_sha256": sha256(ROOT / RUNTIME_REF),
    }


def verify_gates() -> tuple[dict[str, Any], dict[str, Any]]:
    implementation = load_json(ROOT / IMPLEMENTATION_GATE_REF)
    execution = load_json(ROOT / EXECUTION_GATE_REF)
    if (
        implementation.get("status") != "pass_public_default_branch_ci_implementation_ready"
        or implementation.get("public_ci_conclusion") != "success"
        or implementation.get("bindings") != code_bindings()
        or execution.get("status") != "pass_public_default_branch_ci_execution_ready"
        or execution.get("public_ci_conclusion") != "success"
        or execution.get("implementation_gate_sha256") != sha256(ROOT / IMPLEMENTATION_GATE_REF)
    ):
        raise ComparisonError("public_ci_gate_invalid")
    return implementation, execution


def inspect_no_content(arcpy: Any) -> dict[str, Any]:
    signature = inspect.signature(arcpy.ia.ApplyGeometricTerrainCorrection)
    if tuple(signature.parameters) != GTC_PARAMETERS:
        raise ComparisonError("installed_gtc_signature_mismatch")
    if not callable(getattr(arcpy, "RasterToNumPyArray", None)):
        raise ComparisonError("block_reader_missing")
    if not callable(getattr(arcpy, "AsShape", None)):
        raise ComparisonError("geometry_constructor_missing")
    if arcpy.CheckExtension("ImageAnalyst") != "Available":
        raise ComparisonError("image_analyst_unavailable")
    install = arcpy.GetInstallInfo()
    return {"product": install.get("ProductName"), "version": install.get("Version"), "gtc_parameters": list(signature.parameters), "image_analyst": "Available"}


def no_content_paths() -> dict[str, int | bool]:
    if ATTEMPT_ROOT.exists() or OUTPUT.exists():
        raise ComparisonError("attempt_root_collision")
    if not GAMMA.is_dir() or GAMMA.is_symlink() or not DEM.is_file() or DEM.is_symlink():
        raise ComparisonError("exact_input_missing_or_unsafe")
    if any(path_chain_has_reparse(path) for path in (GAMMA, DEM, ATTEMPT_ROOT)) or is_subst_drive(ATTEMPT_ROOT):
        raise ComparisonError("input_or_output_path_reparse_or_subst")
    if not ATTEMPT_ROOT.parent.is_dir():
        raise ComparisonError("attempt_parent_missing")
    free = shutil.disk_usage(ATTEMPT_ROOT.parent).free
    if free < MIN_FREE_BYTES:
        raise ComparisonError("insufficient_free_space")
    longest = max(len(str(path)) for path in (GAMMA, DEM, ATTEMPT_ROOT / "terminal-reservation.json", OUTPUT))
    if longest > 240:
        raise ComparisonError("unsafe_path_length")
    if sha256(ROOT / AOI_REF) != "3d6c9bb39fa9b3ffeddfb0048ddabf30ee4472c0006b78c5c7d58193693ac615":
        raise ComparisonError("aoi_identity_mismatch")
    return {"gamma_present": True, "dem_present": True, "attempt_root_absent": True, "free_bytes": free, "minimum_free_bytes": MIN_FREE_BYTES, "maximum_path_characters": longest}


def run_preflight(import_arcpy: Callable[[], Any] | None = None) -> dict[str, Any]:
    if (ROOT / PREFLIGHT_REF).exists():
        raise ComparisonError("preflight_collision")
    verify_authority()
    _, execution = verify_gates()
    if git_head() != git_head("origin/main"):
        raise ComparisonError("public_default_branch_not_current")
    if subprocess.run(["git", "merge-base", "--is-ancestor", execution["execution_commit_sha"], "HEAD"], cwd=ROOT).returncode:
        raise ComparisonError("execution_commit_not_in_public_history")
    paths = no_content_paths()
    arcpy = import_arcpy() if import_arcpy is not None else importlib.import_module("arcpy")
    runtime = inspect_no_content(arcpy)
    receipt = {
        "schema_version": "1.0", "record_id": "NEPAL-M2-RADAR-DEM-FITNESS-COMPARISON-001-FINAL-PREFLIGHT",
        "checked_at_utc": now_utc(), "status": "pass_final_no_content_preflight_one_attempt_ready",
        "attempt_id": ATTEMPT_ID,
        "bindings": {"approval_sha256": sha256(ROOT / APPROVAL_REF), "implementation_gate_sha256": sha256(ROOT / IMPLEMENTATION_GATE_REF), "execution_gate_sha256": sha256(ROOT / EXECUTION_GATE_REF), "public_head_sha": git_head()},
        "checks": paths, "runtime": runtime,
        "assertions": {"project_pixel_read": False, "arcpy_raster_constructed": False, "gtc_called": False, "attempt_root_created": False, "network_or_credentials_used": False},
    }
    write_new_json(ROOT / PREFLIGHT_REF, receipt)
    return receipt


def aoi_native_rings(arcpy: Any, aoi_definition: dict[str, Any], native_wkid: int) -> dict[str, list[list[list[float]]]]:
    if aoi_definition.get("spatialReference", {}).get("wkid") != 32645:
        raise ComparisonError("aoi_crs_mismatch")
    result: dict[str, list[list[list[float]]]] = {}
    for feature in aoi_definition.get("features", []):
        aoi_id = feature.get("attributes", {}).get("AOI_ID")
        if aoi_id not in AOI_IDS or aoi_id in result:
            raise ComparisonError("aoi_identity_or_duplicate")
        geometry = arcpy.AsShape(feature["geometry"], True)
        projected = geometry.projectAs(arcpy.SpatialReference(native_wkid))
        rings = json.loads(projected.JSON).get("rings")
        if not isinstance(rings, list) or not rings:
            raise ComparisonError("aoi_projection_invalid")
        result[aoi_id] = rings
    if set(result) != set(AOI_IDS):
        raise ComparisonError("aoi_member_set_mismatch")
    return result


def point_mask(xs: np.ndarray, ys: np.ndarray, rings: list[list[list[float]]]) -> np.ndarray:
    """Even-odd cell-center containment with a fixed strict crossing rule."""
    inside = np.zeros((ys.size, xs.size), dtype=bool)
    x_grid, y_grid = np.meshgrid(xs, ys)
    for ring in rings:
        if len(ring) < 4 or ring[0] != ring[-1]:
            raise ComparisonError("aoi_ring_invalid")
        for i in range(len(ring) - 1):
            x1, y1 = ring[i]
            x2, y2 = ring[i + 1]
            if y1 == y2:
                continue
            crossing = ((y1 > y_grid) != (y2 > y_grid)) & (x_grid < (x2 - x1) * (y_grid - y1) / (y2 - y1) + x1)
            inside ^= crossing
    return inside


def nodata_values(raster: Any, band_count: int) -> tuple[float, ...]:
    values = getattr(raster, "noDataValues", None)
    if not isinstance(values, (list, tuple)) or len(values) != band_count:
        raise ComparisonError("nodata_metadata_missing_or_ambiguous")
    try:
        result = tuple(float(value) for value in values)
    except (TypeError, ValueError) as exc:
        raise ComparisonError("nodata_metadata_missing_or_ambiguous") from exc
    return result


def validity(arr: np.ndarray, nodata: tuple[float, ...]) -> np.ndarray:
    if arr.ndim == 2:
        arr = arr[np.newaxis, :, :]
    if arr.ndim != 3 or arr.shape[0] != len(nodata):
        raise ComparisonError("raster_array_shape_mismatch")
    masks = np.isfinite(arr)
    for index, sentinel in enumerate(nodata):
        if not math.isnan(sentinel):
            masks[index] &= arr[index] != sentinel
    return masks


def _empty_counts(band_count: int) -> dict[str, Any]:
    return {"status": "pending", "total_native_cell_centers": 0, "valid_per_band": [0] * band_count, "nodata_or_nonfinite_per_band": [0] * band_count, "valid_all_bands": 0, "valid_envelope_native": None}


def _finish_counts(counts: dict[str, dict[str, Any]]) -> None:
    for aoi_id, item in counts.items():
        if item["total_native_cell_centers"] == 0:
            item["status"] = "no_native_grid_intersection" if aoi_id == "AOI-OVERVIEW" else "not_applicable_no_native_grid_intersection"
        elif item["valid_all_bands"] == 0:
            item["status"] = "no_valid_input_cells" if aoi_id == "AOI-OVERVIEW" else "not_applicable_no_valid_input_cells"
        else:
            item["status"] = "diagnostic_native_valid_cells_observed"


def _marker_json(marker: float) -> float | str:
    return marker if math.isfinite(marker) else ("NaN" if math.isnan(marker) else "Infinity" if marker > 0 else "-Infinity")


def _extend_envelope(existing: list[float] | None, x_values: np.ndarray, y_values: np.ndarray, dx: float, dy: float) -> list[float] | None:
    if not x_values.size:
        return existing
    box = [float(x_values.min() - dx / 2), float(y_values.min() - dy / 2), float(x_values.max() + dx / 2), float(y_values.max() + dy / 2)]
    if existing is None:
        return box
    return [min(existing[0], box[0]), min(existing[1], box[1]), max(existing[2], box[2]), max(existing[3], box[3])]


def scan_native_raster(arcpy: Any, raster: Any, rings_by_aoi: dict[str, list[list[list[float]]]], expected_bands: int) -> dict[str, Any]:
    if raster.bandCount != expected_bands or raster.spatialReference.factoryCode != 4326:
        raise ComparisonError("raster_band_or_crs_mismatch")
    if getattr(raster, "readOnly", None) is not True:
        raise ComparisonError("input_raster_not_read_only")
    dx, dy = float(raster.meanCellWidth), float(raster.meanCellHeight)
    if not (math.isfinite(dx) and math.isfinite(dy) and dx > 0 and dy > 0):
        raise ComparisonError("invalid_native_cell_size")
    width, height = int(raster.width), int(raster.height)
    extent = raster.extent
    x0, y0 = float(extent.XMin), float(extent.YMin)
    if width <= 0 or height <= 0:
        raise ComparisonError("empty_native_grid")
    markers = nodata_values(raster, expected_bands)
    overview = rings_by_aoi["AOI-OVERVIEW"]
    bbox = [min(x for ring in overview for x, _ in ring), min(y for ring in overview for _, y in ring), max(x for ring in overview for x, _ in ring), max(y for ring in overview for _, y in ring)]
    col_start = max(0, math.floor((bbox[0] - x0) / dx))
    col_stop = min(width, math.ceil((bbox[2] - x0) / dx))
    row_start = max(0, math.floor((bbox[1] - y0) / dy))
    row_stop = min(height, math.ceil((bbox[3] - y0) / dy))
    counts = {aoi_id: _empty_counts(expected_bands) for aoi_id in AOI_IDS}
    if col_start >= col_stop or row_start >= row_stop:
        _finish_counts(counts)
        return {"native_wkid": 4326, "band_count": expected_bands, "nodata_markers": [_marker_json(value) for value in markers], "block_count": 0, "aois": counts}
    block_count = 0
    for row in range(row_start, row_stop, BLOCK_SIZE):
        for col in range(col_start, col_stop, BLOCK_SIZE):
            nrows = min(BLOCK_SIZE, row_stop - row)
            ncols = min(BLOCK_SIZE, col_stop - col)
            lower_x, lower_y = x0 + col * dx, y0 + row * dy
            arr = arcpy.RasterToNumPyArray(raster, arcpy.Point(lower_x, lower_y), ncols, nrows)
            if arr.shape[-2:] != (nrows, ncols):
                raise ComparisonError("raster_window_shape_or_snap_mismatch")
            valid = validity(arr, markers)
            xs = lower_x + (np.arange(ncols) + 0.5) * dx
            ys = lower_y + (nrows - np.arange(nrows) - 0.5) * dy
            block_count += 1
            for aoi_id, rings in rings_by_aoi.items():
                in_aoi = point_mask(xs, ys, rings)
                if not in_aoi.any():
                    continue
                item = counts[aoi_id]
                item["total_native_cell_centers"] += int(in_aoi.sum())
                for band in range(expected_bands):
                    good = int((valid[band] & in_aoi).sum())
                    item["valid_per_band"][band] += good
                    item["nodata_or_nonfinite_per_band"][band] += int(in_aoi.sum()) - good
                all_good = np.all(valid, axis=0) & in_aoi
                item["valid_all_bands"] += int(all_good.sum())
                where = np.nonzero(all_good)
                item["valid_envelope_native"] = _extend_envelope(item["valid_envelope_native"], xs[where[1]], ys[where[0]], dx, dy)
    _finish_counts(counts)
    return {"native_wkid": 4326, "band_count": expected_bands, "nodata_markers": [_marker_json(value) for value in markers], "block_count": block_count, "aois": counts}


def coverage_gate(gamma_audit: dict[str, Any], dem_audit: dict[str, Any]) -> bool:
    gamma = gamma_audit["aois"]["AOI-OVERVIEW"]
    dem = dem_audit["aois"]["AOI-OVERVIEW"]
    if gamma["valid_all_bands"] <= 0 or dem["valid_all_bands"] <= 0:
        return False
    if any(count <= 0 for count in gamma["valid_per_band"]):
        return False
    a, b = gamma["valid_envelope_native"], dem["valid_envelope_native"]
    return a is not None and b is not None and min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def write_stage(number: int, stage: str) -> None:
    write_new_json(ATTEMPT_ROOT / f"stage-{number:03d}.json", {"at_utc": now_utc(), "attempt_id": ATTEMPT_ID, "stage": stage})


def run_comparison(import_arcpy: Callable[[], Any] | None = None) -> dict[str, Any]:
    verify_authority()
    verify_gates()
    preflight = load_json(ROOT / PREFLIGHT_REF)
    if preflight.get("status") != "pass_final_no_content_preflight_one_attempt_ready" or preflight.get("bindings", {}).get("execution_gate_sha256") != sha256(ROOT / EXECUTION_GATE_REF):
        raise ComparisonError("preflight_missing_or_drifted")
    no_content_paths()
    ATTEMPT_ROOT.mkdir(exist_ok=False)
    reservation = {"schema_version": "1.0", "attempt_id": ATTEMPT_ID, "reserved_at_utc": now_utc(), "preflight_sha256": sha256(ROOT / PREFLIGHT_REF), "status": "reserved_before_project_pixel_read"}
    write_new_json(ATTEMPT_ROOT / "terminal-reservation.json", reservation)
    write_new_json(ATTEMPT_ROOT / "cleanup-reservation.json", reservation)
    write_stage(0, "one_process_started")
    status = "block_unknown_failure_no_retry"
    error_type = None
    arcgis_error_code = None
    arcpy = None
    checked_out = False
    gtc_started = gtc_returned = save_started = save_completed = False
    gamma_audit = dem_audit = None
    cleanup_status = "not_started"
    try:
        arcpy = import_arcpy() if import_arcpy is not None else importlib.import_module("arcpy")
        inspect_no_content(arcpy)
        write_stage(1, "arcpy_interface_ready")
        if arcpy.CheckOutExtension("ImageAnalyst") != "CheckedOut":
            raise ComparisonError("image_analyst_checkout_failed")
        checked_out = True
        arcpy.env.overwriteOutput = False
        arcpy.env.scratchWorkspace = str(ATTEMPT_ROOT)
        write_stage(2, "image_analyst_checked_out")
        gamma = arcpy.Raster(str(GAMMA))
        dem = arcpy.Raster(str(DEM))
        aoi_definition = load_json(ROOT / AOI_REF)
        rings = aoi_native_rings(arcpy, aoi_definition, 4326)
        write_stage(3, "exact_inputs_and_aoi_constructed")
        write_stage(4, "native_validity_audit_started")
        gamma_audit = scan_native_raster(arcpy, gamma, rings, 2)
        dem_audit = scan_native_raster(arcpy, dem, rings, 1)
        write_new_json(ATTEMPT_ROOT / "coverage-audit.json", {"schema_version": "1.0", "attempt_id": ATTEMPT_ID, "status": "pass_counts_complete_diagnostic_only", "gamma": gamma_audit, "dem": dem_audit})
        write_stage(5, "native_validity_audit_persisted")
        if not coverage_gate(gamma_audit, dem_audit):
            status = "block_diagnostic_coverage_floor_no_gtc"
        else:
            write_stage(6, "gtc_call_started_with_existing_dem")
            gtc_started = True
            corrected = arcpy.ia.ApplyGeometricTerrainCorrection(gamma, "VV;VH", str(DEM), "NONE")
            if corrected.__class__.__name__ != "Raster" or not callable(getattr(corrected, "save", None)):
                raise ComparisonError("gtc_returned_non_raster")
            gtc_returned = True
            write_stage(7, "gtc_returned")
            if OUTPUT.exists():
                raise ComparisonError("output_collision_before_save")
            write_stage(8, "single_output_save_started")
            save_started = True
            corrected.save(str(OUTPUT))
            if not OUTPUT.exists():
                raise ComparisonError("save_returned_without_output")
            save_completed = True
            write_stage(9, "single_output_save_completed")
            status = "pass_dem_supplied_gtc_diagnostic_only_output_quarantined"
    except BaseException as exc:
        error_type = exc.code if isinstance(exc, ComparisonError) else type(exc).__name__
        match = re.search(r"ERROR\s+(\d{6})\b", str(exc))
        arcgis_error_code = match.group(1) if match else None
        status = "block_audit_gtc_or_runtime_failure_no_retry"
    finally:
        try:
            if checked_out and arcpy is not None:
                arcpy.CheckInExtension("ImageAnalyst")
            cleanup_status = "extension_checked_in_or_not_checked_out"
        except BaseException:
            cleanup_status = "extension_checkin_failed"
            if status.startswith("pass_"):
                status = "block_extension_checkin_failed_output_quarantined"
        terminal = {
            "schema_version": "1.0", "receipt_id": "NEPAL-M2-RADAR-DEM-FITNESS-COMPARISON-001-TERMINAL",
            "attempt_id": ATTEMPT_ID, "recorded_at_utc": now_utc(), "status": status,
            "error_type_or_code": error_type, "arcgis_error_code": arcgis_error_code,
            "coverage_audit_persisted": (ATTEMPT_ROOT / "coverage-audit.json").is_file(),
            "coverage_gate_passed": coverage_gate(gamma_audit, dem_audit) if gamma_audit is not None and dem_audit is not None else False,
            "gtc_call_started": gtc_started, "gtc_returned_raster": gtc_returned,
            "output_save_started": save_started, "output_save_completed": save_completed,
            "output_exists": OUTPUT.exists(), "cleanup_status": cleanup_status,
            "assertions": {"attempt_consumed": True, "maximum_gtc_calls": 1, "dem_argument_supplied_if_called": gtc_started, "automatic_retry": False, "output_quarantined": True, "scientific_result_established": False, "historical_root_cause_established": False},
        }
        try:
            write_new_json(ATTEMPT_ROOT / "terminal.json", terminal)
        except BaseException as exc:
            terminal["status"] = "indeterminate_terminal_persistence_failure_no_retry"
            with (ATTEMPT_ROOT / "fallback.jsonl").open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps({"at_utc": now_utc(), "stage": "terminal_write_failed", "error_type": type(exc).__name__}) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
        try:
            write_new_json(ATTEMPT_ROOT / "cleanup.json", {"schema_version": "1.0", "attempt_id": ATTEMPT_ID, "recorded_at_utc": now_utc(), "status": cleanup_status})
        except BaseException as exc:
            with (ATTEMPT_ROOT / "fallback.jsonl").open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps({"at_utc": now_utc(), "stage": "cleanup_write_failed", "error_type": type(exc).__name__}) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
        return terminal


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("preflight", "run"))
    args = parser.parse_args()
    result = run_preflight() if args.mode == "preflight" else run_comparison()
    print(json.dumps({"status": result["status"], "attempt_id": ATTEMPT_ID}))
    return 0 if result["status"].startswith("pass_") else 20


if __name__ == "__main__":
    raise SystemExit(main())
