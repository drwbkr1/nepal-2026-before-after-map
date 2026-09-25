#!/usr/bin/env python3
"""Append-only ArcGIS CRF-format test of coverage and a single aligned Clip."""

from __future__ import annotations

import hashlib
import json
import math
import os
import traceback
from pathlib import Path

from m2_map_route_feasibility_001_core import TARGET, project_then_clip


ROOT = Path(__file__).resolve().parents[1]
ATTEMPT = ROOT / "scratch/map-route-feasibility-disposable-003"
PROPOSAL = ROOT / "contracts/milestone-002-map-route-feasibility-001-proposal.json"
BUNDLE = ROOT / "reviews/m2-map-route-feasibility-001/review-bundle.json"
APPROVAL = ROOT / "records/source-gates/m2-map-route-feasibility-001-approval.json"
PACKET_GATE = ROOT / "records/readiness/m2-map-route-feasibility-001-packet-publication-gate.json"
PUBLIC_RECEIPT = ROOT / "records/readiness/m2-map-route-feasibility-001-arcgis-disposable-003.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now_utc() -> str:
    # ArcPy can rebind module-global datetime names while importing. Resolve
    # the class locally for both normal and fallback terminal persistence.
    import datetime as datetime_module

    return datetime_module.datetime.now(datetime_module.timezone.utc).isoformat(
        timespec="seconds").replace("+00:00", "Z")


def write_new(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _write_reserved(path: Path, value: dict) -> None:
    with path.open("r+b") as stream:
        if stream.seek(0, os.SEEK_END) != 0:
            raise RuntimeError("disposable_terminal_already_written")
        stream.write((json.dumps(value, indent=2) + "\n").encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())


def check_packet_gate() -> None:
    gate = json.loads(PACKET_GATE.read_text(encoding="utf-8"))
    approval = json.loads(APPROVAL.read_text(encoding="utf-8"))
    if (sha(PROPOSAL) != "6a0e568e7db0af2fbbd8d317a4324c4fda4c9784d069c9aaaa2697e3e12d436a"
            or sha(BUNDLE) != "9419b4c0dc4272f14ec59521fa268d592368ccab6b8411c3a868f12e6739756e"
            or approval.get("decision") != "approve"
            or gate.get("status") != "pass_exact_public_packet_and_approval_ci_implementation_eligible"
            or gate.get("bindings", {}).get("approval_sha256") != sha(APPROVAL)
            or gate.get("bindings", {}).get("public_ci_conclusion") != "success"):
        raise RuntimeError("exact_public_packet_gate_missing")


def _source_bounds(arcpy) -> tuple[float, float, float, float]:
    projected = arcpy.SpatialReference(32645)
    geographic = arcpy.SpatialReference(4326)
    corners = ((TARGET[0], TARGET[1]), (TARGET[0], TARGET[3]),
               (TARGET[2], TARGET[1]), (TARGET[2], TARGET[3]))
    points = [arcpy.PointGeometry(arcpy.Point(x, y), projected).projectAs(geographic).firstPoint
              for x, y in corners]
    return (min(point.X for point in points) - 0.002,
            min(point.Y for point in points) - 0.002,
            max(point.X for point in points) + 0.002,
            max(point.Y for point in points) + 0.002)


def _make_sources(arcpy, np) -> dict[str, Path]:
    west, south, east, north = _source_bounds(arcpy)
    cell = 0.001
    columns = math.ceil((east - west) / cell)
    rows = math.ceil((north - south) / cell)
    if rows * columns > 2_000_000:
        raise RuntimeError("generated_source_too_large")
    row = np.arange(rows, dtype=np.float32)[:, None]
    column = np.arange(columns, dtype=np.float32)[None, :]
    continuous = np.stack((7.0 + row * 0.001 + column * 0.0001,
                           9.0 + row * 0.0002 + column * 0.001)).astype(np.float32)
    mask = np.where((np.arange(rows)[:, None] // 17 + np.arange(columns)[None, :] // 17) % 2 == 0,
                    1, 3).astype(np.uint8)
    outputs = {}
    for name, array in (("continuous", continuous), ("categorical", mask)):
        path = ATTEMPT / f"generated_{name}_4326.tif"
        arcpy.NumPyArrayToRaster(array, arcpy.Point(west, south), cell, cell).save(str(path))
        arcpy.management.DefineProjection(str(path), arcpy.SpatialReference(4326))
        outputs[name] = path
    snap = ATTEMPT / "snap_10m.tif"
    arcpy.NumPyArrayToRaster(np.zeros((2, 2), dtype=np.uint8),
                            arcpy.Point(TARGET[0], TARGET[1]), 10.0, 10.0).save(str(snap))
    arcpy.management.DefineProjection(str(snap), arcpy.SpatialReference(32645))
    outputs["snap"] = snap
    outputs["source_shape"] = [rows, columns]
    return outputs


def _compare_windows(arcpy, np, intermediate: Path, final: Path, *, categorical: bool) -> dict:
    lower_lefts = ((TARGET[0] + 1000, TARGET[1] + 1000),
                   (TARGET[0] + 40000, TARGET[1] + 20000),
                   (TARGET[2] - 3000, TARGET[3] - 3000))
    checks = []
    for x, y in lower_lefts:
        kwargs = {"lower_left_corner": arcpy.Point(x, y), "ncols": 128,
                  "nrows": 128, "nodata_to_value": 255 if categorical else -9999.0}
        middle = arcpy.RasterToNumPyArray(str(intermediate), **kwargs)
        clipped = arcpy.RasterToNumPyArray(str(final), **kwargs)
        same = bool(np.array_equal(middle, clipped)) and middle.shape == clipped.shape
        classes = sorted(int(value) for value in np.unique(clipped)) if categorical else []
        finite = bool(np.isfinite(clipped).all())
        checks.append({"lower_left_m": [x, y], "shape": list(clipped.shape),
                       "retained_values_identical": same, "finite": finite,
                       "mask_classes": classes})
    if not all(item["retained_values_identical"] and item["finite"] for item in checks):
        raise RuntimeError("sampled_retained_pixels_changed")
    if categorical and not {1, 3}.issubset(set(value for item in checks for value in item["mask_classes"])):
        raise RuntimeError("generated_mask_classes_missing")
    return {"window_size_cells": [128, 128], "windows": checks,
            "retained_values_identical_on_all_windows": True}


def run() -> dict:
    check_packet_gate()
    if ATTEMPT.exists() or PUBLIC_RECEIPT.exists():
        raise RuntimeError("append_only_disposable_identity_collision")
    ATTEMPT.mkdir(parents=True, exist_ok=False)
    terminal_path = ATTEMPT / "terminal.json"
    with terminal_path.open("xb") as stream:
        stream.flush()
        os.fsync(stream.fileno())
    write_new(ATTEMPT / "started.json", {"status": "started_generated_inputs_only", "at_utc": now_utc(),
                                           "project_data_or_external_custody_accessed": False})
    stage = "arcgis_import"
    arcpy = None
    checked_out = False
    try:
        os.environ["PROJ_NETWORK"] = "OFF"
        os.environ["GDAL_PAM_ENABLED"] = "NO"
        import arcpy as arcpy_module  # type: ignore
        import numpy as np

        arcpy = arcpy_module
        arcpy.env.overwriteOutput = False
        if arcpy.CheckOutExtension("Spatial") != "CheckedOut":
            raise RuntimeError("spatial_analyst_unavailable")
        checked_out = True
        stage = "create_generated_inputs"
        source = _make_sources(arcpy, np)
        results = {}
        for name, categorical, bands in (("continuous", False, 2), ("categorical", True, 1)):
            stage = f"project_then_clip_{name}"
            intermediate = ATTEMPT / f"{name}_intermediate_32645.crf"
            final = ATTEMPT / f"{name}_final_32645.crf"
            result = project_then_clip(arcpy, source[name], intermediate, final,
                                       source["snap"], categorical=categorical,
                                       expected_bands=bands)
            result["sampled_pixel_equivalence"] = _compare_windows(
                arcpy, np, intermediate, final, categorical=categorical)
            results[name] = result
        terminal = {"schema_version": "1.0", "status": "pass_disposable_grid_and_sampled_pixels_only",
                    "completed_at_utc": now_utc(), "arcgis_version": arcpy.GetInstallInfo().get("Version"),
                    "generated_source_shape": source["source_shape"], "results": results,
                    "core_sha256": sha(ROOT / "scripts/m2_map_route_feasibility_001_core.py"),
                    "validator_sha256": sha(Path(__file__)),
                    "project_data_or_external_custody_accessed": False,
                    "sar_specific_gtc_fitness_proven": False,
                    "real_radar_pixel_fitness_proven": False,
                    "baseline_or_change_analysis_authorized": False}
    except BaseException as exc:
        frame = traceback.extract_tb(exc.__traceback__)[-1]
        code = str(exc) if type(exc) is RuntimeError and str(exc) in {
            "spatial_analyst_unavailable", "generated_source_too_large",
            "sampled_retained_pixels_changed", "generated_mask_classes_missing"} else getattr(exc, "args", ["disposable_error"])[0]
        if not isinstance(code, str) or len(code) > 80 or any(char in code for char in ("\\", "/", ":", "@")):
            code = "disposable_error"
        terminal = {"schema_version": "1.0", "status": "block_disposable_no_real_attempt",
                    "completed_at_utc": now_utc(), "last_stage": stage,
                    "failure_type": type(exc).__name__, "failure_code": code,
                    "failure_site": {"function": frame.name, "line": frame.lineno},
                    "project_data_or_external_custody_accessed": False,
                    "sar_specific_gtc_fitness_proven": False,
                    "real_radar_pixel_fitness_proven": False,
                    "baseline_or_change_analysis_authorized": False}
    finally:
        if checked_out and arcpy is not None:
            try:
                arcpy.CheckInExtension("Spatial")
            except Exception:
                pass
    _write_reserved(terminal_path, terminal)
    public = {"schema_version": "1.0", "record_id": "NEPAL-M2-MAP-ROUTE-FEASIBILITY-001-ARCGIS-DISPOSABLE-003",
              "status": terminal["status"], "attempt_terminal_sha256": sha(terminal_path),
              "attempt_terminal_ref": str(terminal_path),
              "project_data_or_external_custody_accessed": False,
              "sar_specific_gtc_fitness_proven": False,
              "real_radar_pixel_fitness_proven": False,
              "baseline_or_change_analysis_authorized": False}
    write_new(PUBLIC_RECEIPT, public)
    return terminal


def main() -> int:
    result = run()
    print(json.dumps({"status": result["status"]}))
    return 0 if result["status"] == "pass_disposable_grid_and_sampled_pixels_only" else 20


if __name__ == "__main__":
    raise SystemExit(main())
