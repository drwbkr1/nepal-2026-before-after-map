#!/usr/bin/env python3
"""One supervised, append-only recovery of the frozen Landsat visual route.

The supervisor reserves evidence outside the worker root before one subprocess.
The worker reuses the hash-bound prior scientific implementation with only its
attempt root and approval controls rebound in its private process. No retry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Callable

import run_m2_landsat9_pixel_visual_panel_001 as frozen

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(r"C:\Projects\Active\nepal-2026-before-after-map-data")
PRIOR = DATA / "processing/landsat9-pixel-visual-panel-001/real-001"
ATTEMPT = DATA / "processing/landsat9-pixel-visual-recovery-001/real-002"
EVENTS = DATA / ".attempt-events/landsat9-pixel-visual-recovery-001/real-002"
FALLBACK = DATA / ".attempt-fallback/landsat9-pixel-visual-recovery-001/real-002"
APPROVAL = ROOT / "records/source-gates/m2-landsat9-pixel-visual-recovery-001-approval.json"
APPROVAL_SHA = "d49822fe1f9531c1b531033d1f93806225f16369dd1095682611007cac9f74d9"
PROPOSAL = ROOT / "contracts/milestone-002-landsat9-pixel-visual-recovery-001-proposal.json"
PROPOSAL_SHA = "9437ea0dea7222118a88e5d8157987d22afcfaf33d765e954745142abbe6694c"
BUNDLE = ROOT / "reviews/m2-landsat9-pixel-visual-recovery-001/review-bundle.json"
BUNDLE_SHA = "92fe8c191eb854a09e7e5e5f45494e324f9b1feee186528fd620bfa6ca4de2f3"
PRIOR_RUNNER = ROOT / "scripts/run_m2_landsat9_pixel_visual_panel_001.py"
PRIOR_RUNNER_SHA = "8f73dc48f8b2b669c85d6bf76c1cfe0b816d91e4acf63b07aa247111f4340c00"
PRIOR_TERMINAL = ROOT / "records/readiness/m2-landsat9-pixel-visual-panel-001-terminal-reconciliation.json"
PRIOR_TERMINAL_SHA = "e0270f75233b8c80b9559c5b70936d07f7e7787f28957a8db54697d848ea46ae"
PRIOR_POST_CI = ROOT / "records/readiness/m2-landsat9-pixel-visual-panel-001-post-ci-reconciliation.json"
PRIOR_POST_CI_SHA = "032b367420f2ffd6c69b7fd3832929365e41cb58193e38e3bfd92e004668df4c"
RUNTIME = Path(r"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe")
WORKER_CODES = frozenset("""required_control_missing_or_unsafe frozen_control_hash_drift
owner_approval_invalid closed_container_intake_invalid prior_verification_receipt_drift
prior_verification_identity_invalid public_ci_reference_invalid controlled_data_root_unsafe
real_attempt_already_consumed installed_arcgis_runtime_missing insufficient_non_git_space
promoted_archive_identity_drift exact_member_missing_or_size_drift exact_member_unreadable
materialized_member_hash_drift promoted_archive_changed_during_materialization
mtl_field_duplicate_disagreement mtl_acquisition_date_mismatch mtl_scene_center_time_invalid
mtl_reflectance_scale_missing mtl_reflectance_scale_mismatch tiff_byte_order_invalid
bigtiff_header_invalid tiff_magic_invalid tiff_ifd_offset_invalid tiff_ifd_tag_count_invalid
tiff_ifd_truncated tiff_georeference_tag_invalid tiff_georeference_tag_offset_invalid
tiff_transform_shape_invalid tiff_scale_or_tiepoint_invalid tiff_georeference_tags_missing
tiff_georeference_nonfinite tiff_arcgis_georeference_disagreement aoi_window_empty
pixel_window_lattice_mismatch pixel_window_shape_or_type_invalid within_scene_pixel_footprint_mismatch
final_preflight_gate_invalid approved_aoi_ids_missing aoi_ring_invalid aoi_area_invalid
aoi_window_invalid aoi_geometry_not_approved_quadrilateral aoi_area_accounting_invalid
source_roles_invalid required_tiff_members_missing tiff_header_grid_or_nodata_invalid
within_scene_grid_mismatch cross_scene_lattice_mismatch cross_scene_extent_disjoint
pixel_array_shape_invalid reason_area_accounting_invalid stretch_population_empty
stretch_range_degenerate""".split())
WORKER_STATUSES = frozenset(("blocked_terminal_no_retry", "block_reservation_receipt_persistence_failure",
                           "block_terminal_receipt_persistence_failure",
                           "pass_pixel_qa_visual_only_no_panel_qualified",
                           "pass_local_arcgis_visual_panel_only"))
ALLOWED_EXCEPTIONS = frozenset(("FileExistsError", "FileNotFoundError", "PermissionError",
                               "OSError", "RuntimeError", "TimeoutExpired", "RouteStop", "PixelMethodError"))


def now() -> str:
    from datetime import datetime as timestamp, timezone as time_zone
    return timestamp.now(time_zone.utc).isoformat().replace("+00:00", "Z")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path: Path, payload: dict) -> None:
    data = json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n"
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    if path.read_bytes() != data.encode("utf-8"):
        raise OSError("receipt_readback_failed")


def safe_exception(exc: BaseException) -> str:
    name = type(exc).__name__
    return name if name in ALLOWED_EXCEPTIONS else "UnclassifiedError"


def safe_worker_code(exc: BaseException) -> str:
    if isinstance(exc, (frozen.RouteStop, frozen.PixelMethodError)):
        code = str(exc)
        if code in WORKER_CODES:
            return code
    return "local_io_or_unexpected_failure"


@contextmanager
def bind_controls(attempt: Path = ATTEMPT):
    # A private-process binding reuses the exact frozen method and restores it
    # on exit. The prior script and consumed filesystem root are never written.
    replacements = {"ATTEMPT": attempt, "APPROVAL": APPROVAL, "APPROVAL_SHA": APPROVAL_SHA,
                    "PROPOSAL": PROPOSAL, "PROPOSAL_SHA": PROPOSAL_SHA,
                    "BUNDLE": BUNDLE, "BUNDLE_SHA": BUNDLE_SHA, "now": now}
    original = {key: getattr(frozen, key) for key in replacements}
    try:
        for key, value in replacements.items():
            setattr(frozen, key, value)
        yield
    finally:
        for key, value in original.items():
            setattr(frozen, key, value)


def controls() -> None:
    for path, expected in ((APPROVAL, APPROVAL_SHA), (PROPOSAL, PROPOSAL_SHA),
                           (BUNDLE, BUNDLE_SHA), (PRIOR_RUNNER, PRIOR_RUNNER_SHA),
                           (PRIOR_TERMINAL, PRIOR_TERMINAL_SHA),
                           (PRIOR_POST_CI, PRIOR_POST_CI_SHA)):
        if sha(path) != expected:
            raise frozen.RouteStop("frozen_control_hash_drift")
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    if any(sha(ROOT / item["ref"]) != item["sha256"] for item in bundle["bound_files"]):
        raise frozen.RouteStop("review_bundle_bound_file_drift")
    if (not PRIOR.is_dir() or PRIOR.is_symlink() or frozen.is_reparse_point(PRIOR)
            or list(PRIOR.iterdir())):
        raise frozen.RouteStop("consumed_real_001_observation_drift")
    for path in (ATTEMPT, EVENTS, FALLBACK):
        for parent in (path, *path.parents):
            if parent == DATA.parent:
                break
            if parent.is_symlink() or (parent.exists() and frozen.is_reparse_point(parent)):
                raise frozen.RouteStop("recovery_path_unsafe")
    with bind_controls():
        frozen._check_controls()


def preflight(commit: str, run_id: str) -> dict:
    controls()
    if any(p.exists() or p.is_symlink() for p in (ATTEMPT, EVENTS, FALLBACK)):
        raise frozen.RouteStop("recovery_attempt_or_receipt_collision")
    with bind_controls():
        gate = frozen.preflight(commit, run_id)
    gate["recovery_approval_sha256"] = APPROVAL_SHA
    gate["prior_terminal_sha256"] = PRIOR_TERMINAL_SHA
    gate["prior_post_ci_sha256"] = PRIOR_POST_CI_SHA
    gate["recovery_attempt_root_absent"] = True
    gate["independent_event_roots_absent"] = True
    gate["recovery_runner_sha256"] = sha(Path(__file__).resolve())
    return gate


def _default_worker(gate_path: Path) -> int:
    # No shell, credentials, provider URL, stdout capture, or automatic retry.
    with open(os.devnull, "wb") as sink:
        completed = subprocess.run([str(RUNTIME), str(Path(__file__).resolve()),
                                    "worker", "--gate", str(gate_path)],
                                   stdout=sink, stderr=sink, check=False, timeout=14400)
    return completed.returncode


def supervise(gate_path: Path, *, attempt: Path = ATTEMPT, events: Path = EVENTS,
              fallback: Path = FALLBACK,
              worker: Callable[[Path], int] = _default_worker,
              after_intent: Callable[[], None] | None = None) -> dict:
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    if (gate.get("status") != "pass_final_no_content_preflight"
            or gate.get("recovery_approval_sha256") != APPROVAL_SHA
            or not gate.get("recovery_attempt_root_absent")
            or not gate.get("independent_event_roots_absent")):
        raise frozen.RouteStop("final_preflight_gate_invalid")
    if any(p.exists() or p.is_symlink() for p in (attempt, events, fallback)):
        raise frozen.RouteStop("recovery_attempt_or_receipt_collision")
    result = {"status": "blocked_terminal_no_retry", "stage": "reservation",
              "reason": "worker_not_launched", "worker_invocations": 0}
    invocations = 0
    try:
        # Reserve an independent fallback before creating the primary events.
        fallback.mkdir(parents=True, exist_ok=False)
        write_new(fallback / "ready.json", {"status": "independent_fallback_reserved",
                                            "at_utc": now(), "real_content_read": False})
        events.mkdir(parents=True, exist_ok=False)
        write_new(events / "intent.json", {
            "status": "reserved_before_worker_launch", "at_utc": now(),
            "approval_sha256": APPROVAL_SHA, "gate_sha256": sha(gate_path),
            "implementation_public_ci_commit": gate["implementation_public_ci_commit"],
            "implementation_public_ci_run_id": gate["implementation_public_ci_run_id"],
            "real_content_read": False})
        if after_intent is not None:
            after_intent()
        result["stage"] = "worker_launch"
        write_new(events / "worker-start.json", {"status": "launching_one_worker",
                                                 "at_utc": now(), "worker_invocations": 1})
        invocations = 1
        code = worker(gate_path)
        result["stage"] = "worker"
        worker_terminal = attempt / "terminal.json"
        if worker_terminal.is_file() and not worker_terminal.is_symlink():
            payload = json.loads(worker_terminal.read_text(encoding="utf-8"))
            status = payload.get("status")
            if status in WORKER_STATUSES and (not status.startswith("pass_") or code == 0):
                result = {"status": status, "stage": "worker", "worker_invocations": 1,
                          "worker_exit_code": code, "worker_terminal_sha256": sha(worker_terminal)}
            else:
                result = {"status": "blocked_terminal_no_retry", "stage": "worker",
                          "reason": "worker_terminal_invalid", "worker_invocations": 1}
        else:
            result = {"status": "blocked_terminal_no_retry", "stage": "worker",
                      "reason": "worker_terminal_missing", "worker_invocations": 1,
                      "worker_exit_code": code,
                      "worker_started_receipt_present": (attempt / "started.json").is_file()}
    except BaseException as exc:
        result = {"status": "blocked_terminal_no_retry", "stage": result["stage"],
                  "reason": "worker_process_failed", "exception_class": safe_exception(exc),
                  "worker_invocations": invocations,
                  "worker_started_receipt_present": (attempt / "started.json").is_file()}
    result.update({"terminal_at_utc": now(), "automatic_retries": 0,
                   "provider_requests": 0, "change_analysis_or_attribution": False,
                   "public_derived_pixel_publication": False})
    terminal_path = None
    for parent in (events, fallback):
        try:
            parent.mkdir(parents=True, exist_ok=True)
            candidate = parent / "terminal.json"
            write_new(candidate, result)
            terminal_path = candidate
            break
        except BaseException:
            continue
    cleanup = {"status": "retained_outputs_for_audit", "recorded_at_utc": now(),
               "source_archives_overwritten_or_removed": False, "automatic_retries": 0}
    cleanup_path = None
    for parent in (events, fallback):
        try:
            parent.mkdir(parents=True, exist_ok=True)
            candidate = parent / "cleanup.json"
            write_new(candidate, cleanup)
            cleanup_path = candidate
            break
        except BaseException:
            continue
    return {"status": result["status"] if terminal_path and cleanup_path else
                       "block_supervisor_receipt_persistence_failure",
            "stage": result["stage"], "worker_invocations": invocations,
            "terminal_receipt_sha256": sha(terminal_path) if terminal_path else None,
            "terminal_receipt_location": ("primary" if terminal_path.parent == events else "fallback")
                                         if terminal_path else None,
            "cleanup_receipt_persisted": cleanup_path is not None}


def worker_once(gate_path: Path) -> int:
    controls()
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    intent = json.loads((EVENTS / "intent.json").read_text(encoding="utf-8"))
    if (gate.get("recovery_approval_sha256") != APPROVAL_SHA
            or gate.get("recovery_runner_sha256") != sha(Path(__file__).resolve())
            or intent.get("gate_sha256") != sha(gate_path)
            or not (EVENTS / "worker-start.json").is_file()
            or not (FALLBACK / "ready.json").is_file()):
        return 12
    # An exclusive claim consumes the invocation even if ArcPy import crashes.
    write_new(EVENTS / "worker-claim.json", {"status": "one_worker_claimed",
                                            "at_utc": now(), "gate_sha256": sha(gate_path)})
    try:
        write_new(EVENTS / "arcpy-import-start.json", {"status": "starting_arcpy_import",
                                                     "at_utc": now()})
        import arcpy  # type: ignore[import-not-found]
        write_new(EVENTS / "arcpy-import-pass.json", {"status": "arcpy_import_passed",
                                                    "at_utc": now()})
        with bind_controls(), worker_stage_markers():
            result = frozen.run_once(gate, arcpy)
        return 0 if result["status"].startswith("pass_") else 20
    except BaseException as exc:
        payload = {"status": "worker_error_preserved_no_retry", "at_utc": now(),
                   "exception_class": safe_exception(exc)}
        try:
            write_new(EVENTS / "worker-error.json", payload)
        except BaseException:
            write_new(FALLBACK / "worker-error.json", payload)
        return 20


@contextmanager
def worker_stage_markers(events: Path = EVENTS):
    """Flush a fixed stage marker before every materialization/header/pixel step."""
    original = {name: getattr(frozen, name) for name in
                ("extract_exact", "raster_headers", "read_aoi_date", "build_panel", "fresh_reopen", "write_new", "_safe_code")}
    sequence = 0
    headers = 0
    pixels = 0

    def mark(stage):
        nonlocal sequence
        sequence += 1
        write_new(events / f"stage-{sequence:02d}.json", {"stage": stage, "at_utc": now()})

    def extract(role, root):
        mark(role + "_materialization")
        return original["extract_exact"](role, root)

    def header(*args):
        nonlocal headers
        role = ("before", "after")[headers]
        headers += 1
        mark(role + "_headers")
        return original["raster_headers"](*args)

    def pixel(*args):
        nonlocal pixels
        stage = ("aoi_source_before_pixels", "aoi_source_after_pixels",
                 "aoi_upper_corridor_before_pixels", "aoi_upper_corridor_after_pixels")[pixels]
        pixels += 1
        mark(stage)
        return original["read_aoi_date"](*args)

    def build(*args):
        mark("conditional_visual_panel")
        return original["build_panel"](*args)

    def reopen(*args):
        mark("panel_fresh_reopen")
        return original["fresh_reopen"](*args)

    def receipt(path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        write_new(path, payload)

    def error_code(exc):
        mark("terminal_error_" + safe_exception(exc).lower())
        return safe_worker_code(exc)

    replacements = {"extract_exact": extract, "raster_headers": header,
                    "read_aoi_date": pixel, "build_panel": build,
                    "fresh_reopen": reopen, "write_new": receipt, "_safe_code": error_code}
    try:
        for name, value in replacements.items():
            setattr(frozen, name, value)
        yield
    finally:
        for name, value in original.items():
            setattr(frozen, name, value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("preflight", "supervise", "worker"))
    parser.add_argument("--public-ci-commit")
    parser.add_argument("--public-ci-run")
    parser.add_argument("--gate")
    args = parser.parse_args()
    try:
        if args.mode == "preflight":
            print(json.dumps(preflight(args.public_ci_commit or "", args.public_ci_run or ""),
                             sort_keys=True))
            return 0
        gate = Path(args.gate or "")
        if args.mode == "worker":
            return worker_once(gate)
        controls()
        if json.loads(gate.read_text(encoding="utf-8")).get("recovery_runner_sha256") != sha(Path(__file__).resolve()):
            raise frozen.RouteStop("implementation_hash_drift")
        result = supervise(gate)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"].startswith("pass_") else 20
    except BaseException as exc:
        print(json.dumps({"status": "stopped", "code": "recovery_control_or_persistence_failure",
                          "exception_class": safe_exception(exc)}, sort_keys=True))
        return 12


if __name__ == "__main__":
    raise SystemExit(main())
