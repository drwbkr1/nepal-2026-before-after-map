#!/usr/bin/env python3
"""Preflight and execute the one approved receipt-recovery diagnostic probe."""

from __future__ import annotations

import argparse
import importlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Callable, Iterable

from m2_radar_delayed_import_probe_receipt_recovery_001_core import (
    ATTEMPT_ID,
    EXPECTED_AGGREGATE_SHA256,
    FILE_COUNT,
    MIN_FREE_BYTES,
    ProbeError,
    TOTAL_LOGICAL_BYTES,
    append_jsonl,
    cleanup_payload,
    create_corpus,
    local_attempt_root,
    require_outside,
    safe_error,
    scan_corpus,
    sha256_file,
    validate_scan,
    write_new_json,
)


ROOT = Path(__file__).resolve().parents[1]
EXTERNAL_CUSTODY_ROOT = Path(r"C:\Projects\Active\nepal-2026-before-after-map-data")
PREFIX = "m2-radar-delayed-import-probe-receipt-recovery-001"
CONTRACT_REF = f"config/qa/{PREFIX}-contract.json"
PUBLICATION_GATE_REF = f"records/readiness/{PREFIX}-implementation-publication-gate.json"
GATE_STATE_REF = f"records/readiness/{PREFIX}-gate-state-publication.json"
FINAL_PREFLIGHT_REF = f"records/readiness/{PREFIX}-final-preflight.json"
CORE_REF = f"scripts/{PREFIX.replace('-', '_')}_core.py"
RUNNER_REF = f"scripts/run_{PREFIX.replace('-', '_')}.py"
TEST_REF = f"tests/test_{PREFIX.replace('-', '_')}.py"
ARCGIS_VALIDATOR_REF = f"scripts/validate_{PREFIX.replace('-', '_')}_arcgis.py"
ARCGIS_PYTHON = Path(r"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe")


def now_utc() -> str:
    # ArcGIS can rebind module globals while importing. Resolve the module locally.
    import datetime as datetime_module

    return datetime_module.datetime.now(datetime_module.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ProbeError("json_root_not_object")
    return value


def repository_bindings() -> dict[str, str]:
    return {
        "probe_contract_sha256": sha256_file(ROOT / CONTRACT_REF),
        "probe_core_sha256": sha256_file(ROOT / CORE_REF),
        "probe_runner_sha256": sha256_file(ROOT / RUNNER_REF),
        "portable_test_sha256": sha256_file(ROOT / TEST_REF),
        "arcgis_validator_sha256": sha256_file(ROOT / ARCGIS_VALIDATOR_REF),
    }


def publication_gate() -> dict[str, Any]:
    path = ROOT / PUBLICATION_GATE_REF
    if not path.is_file():
        raise ProbeError("implementation_publication_gate_missing")
    gate = load_json(path)
    if (
        gate.get("status") != "pass_public_default_branch_ci_receipt_recovery_implementation_ready"
        or gate.get("public_ci_conclusion") != "success"
        or gate.get("bindings") != repository_bindings()
    ):
        raise ProbeError("implementation_publication_gate_not_exact_pass")
    return gate


def gate_state_publication() -> dict[str, Any]:
    path = ROOT / GATE_STATE_REF
    if not path.is_file():
        raise ProbeError("gate_state_publication_missing")
    value = load_json(path)
    if (
        value.get("status") != "pass_public_gate_state_final_preflight_released"
        or value.get("public_ci_conclusion") != "success"
        or value.get("bindings", {}).get("implementation_publication_gate_sha256")
        != sha256_file(ROOT / PUBLICATION_GATE_REF)
    ):
        raise ProbeError("gate_state_publication_not_exact_pass")
    return value


def attempt_root() -> Path:
    return require_outside(local_attempt_root(), (ROOT, EXTERNAL_CUSTODY_ROOT))


def _nearest_existing_parent(path: Path) -> Path:
    cursor = path
    while not cursor.exists() and cursor != cursor.parent:
        cursor = cursor.parent
    if not cursor.exists():
        raise ProbeError("probe_parent_volume_unavailable")
    return cursor


def build_final_preflight(checked_at_utc: str) -> dict[str, Any]:
    gate = publication_gate()
    gate_state = gate_state_publication()
    target = attempt_root()
    free_bytes = shutil.disk_usage(_nearest_existing_parent(target.parent)).free
    checks = {
        "implementation_publication_gate_exact_pass": True,
        "gate_state_publication_exact_pass": True,
        "arcgis_python_exists": ARCGIS_PYTHON.is_file(),
        "attempt_root_absent": not target.exists(),
        "tracked_outcome_reconciliation_absent": not (ROOT / f"records/processing/{PREFIX}-outcome-reconciliation.json").exists(),
        "probe_path_outside_repository": True,
        "probe_path_outside_external_custody": True,
        "local_free_space_guard_pass": free_bytes >= MIN_FREE_BYTES,
        "arcpy_imported_by_preflight": "arcpy" in sys.modules,
        "disposable_corpus_created": False,
        "project_or_external_content_read": False,
    }
    positive = {
        "implementation_publication_gate_exact_pass",
        "gate_state_publication_exact_pass",
        "arcgis_python_exists",
        "attempt_root_absent",
        "tracked_outcome_reconciliation_absent",
        "probe_path_outside_repository",
        "probe_path_outside_external_custody",
        "local_free_space_guard_pass",
    }
    if any(checks[key] is not True for key in positive):
        raise ProbeError("final_no_content_preflight_failed")
    if checks["arcpy_imported_by_preflight"] or checks["disposable_corpus_created"] or checks["project_or_external_content_read"]:
        raise ProbeError("final_no_content_preflight_boundary_violation")
    return {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-FINAL-PREFLIGHT",
        "checked_at_utc": checked_at_utc,
        "status": "pass_final_no_content_preflight_one_receipt_recovery_probe_released",
        "bindings": {
            **repository_bindings(),
            "implementation_publication_gate_sha256": sha256_file(ROOT / PUBLICATION_GATE_REF),
            "gate_state_publication_sha256": sha256_file(ROOT / GATE_STATE_REF),
            "implementation_commit_sha": gate["implementation_commit_sha"],
            "implementation_public_ci_run_id": gate["public_ci_run_id"],
            "gate_state_commit_sha": gate_state["gate_state_commit_sha"],
            "gate_state_public_ci_run_id": gate_state["public_ci_run_id"],
        },
        "checks": checks,
        "local_volume_free_bytes": free_bytes,
        "minimum_free_bytes": MIN_FREE_BYTES,
        "attempt_id": ATTEMPT_ID,
        "corpus_file_count": FILE_COUNT,
        "corpus_total_logical_bytes": TOTAL_LOGICAL_BYTES,
        "expected_stable_order_aggregate_sha256": EXPECTED_AGGREGATE_SHA256,
        "assertions": {
            "attempt_created": False,
            "arcpy_imported": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "network_request_performed": False,
            "credential_value_read": False,
            "consumed_probe_reused_or_retried": False,
            "radar_processing_executed": False,
            "scientific_result_established": False,
        },
        "next_action": "Run the one exact fresh disposable receipt-recovery probe once in the ArcGIS Pro Python environment; never retry it.",
    }


def run_final_preflight(checked_at_utc: str) -> int:
    output = ROOT / FINAL_PREFLIGHT_REF
    if output.exists():
        raise ProbeError("final_preflight_output_collision")
    receipt = build_final_preflight(checked_at_utc)
    write_new_json(output, receipt)
    print(json.dumps({"status": receipt["status"], "record": FINAL_PREFLIGHT_REF}, indent=2))
    return 0


def _load_arcpy() -> Any:
    return importlib.import_module("arcpy")


def _record_stage(stages_path: Path, stage: str, **details: Any) -> None:
    append_jsonl(stages_path, {"stage": stage, "at_utc": now_utc(), **details})


def _call_stage(stages_path: Path, label: str, operation: Callable[[], Any]) -> Any:
    _record_stage(stages_path, f"{label}_started")
    value = operation()
    detail: dict[str, Any] = {}
    if isinstance(value, str) and label in {
        "product_info",
        "image_analyst_checkout",
        "spatial_checkout",
        "spatial_checkin",
        "image_analyst_checkin",
    }:
        detail["result"] = value
    _record_stage(stages_path, f"{label}_completed", **detail)
    return value


def _create_disposable_raster(arcpy: Any, scratch: Path, name: str, values: list[list[float]]) -> str:
    import numpy as np

    path = scratch / name
    raster = arcpy.NumPyArrayToRaster(np.asarray(values, dtype=np.float32), arcpy.Point(0.0, 0.0), 1.0, 1.0)
    raster.save(str(path))
    return str(path)


def _mosaic(arcpy: Any, scratch: Path, raster_a: str, raster_b: str) -> str:
    output_name = "probe-mosaic.tif"
    arcpy.management.MosaicToNewRaster(
        [raster_a, raster_b],
        str(scratch),
        output_name,
        "",
        "32_BIT_FLOAT",
        1,
        1,
        "FIRST",
        "FIRST",
    )
    output = scratch / output_name
    if not output.exists():
        raise ProbeError("disposable_mosaic_missing")
    return str(output)


def _reserve_attempt(target: Path, executed_at_utc: str, bindings: dict[str, Any]) -> Path:
    if target.exists():
        raise ProbeError("probe_attempt_collision")
    target.mkdir(parents=True)
    fallback_path = target / "fallback.jsonl"
    terminal_reservation = {
        "schema_version": "1.0",
        "reservation_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-TERMINAL-RESERVATION",
        "reserved_at_utc": executed_at_utc,
        "attempt_id": ATTEMPT_ID,
        "receipt_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-TERMINAL",
        "target_name": "terminal.json",
        "append_only": True,
    }
    cleanup_reservation = {
        "schema_version": "1.0",
        "reservation_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-CLEANUP-RESERVATION",
        "reserved_at_utc": executed_at_utc,
        "attempt_id": ATTEMPT_ID,
        "receipt_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-CLEANUP",
        "target_name": "cleanup.json",
        "append_only": True,
    }
    write_new_json(target / "terminal-reservation.json", terminal_reservation)
    write_new_json(target / "cleanup-reservation.json", cleanup_reservation)
    append_jsonl(
        fallback_path,
        {
            "event": "fallback_journal_initialized",
            "at_utc": executed_at_utc,
            "attempt_id": ATTEMPT_ID,
            "fallback_is_success_evidence": False,
        },
    )
    write_new_json(
        target / "started.json",
        {
            "schema_version": "1.0",
            "status": "started_single_disposable_receipt_recovery_probe",
            "started_at_utc": executed_at_utc,
            "attempt_id": ATTEMPT_ID,
            "corpus_file_count": FILE_COUNT,
            "corpus_total_logical_bytes": TOTAL_LOGICAL_BYTES,
            "expected_stable_order_aggregate_sha256": EXPECTED_AGGREGATE_SHA256,
            "bindings": bindings,
            "terminal_reservation_sha256": sha256_file(target / "terminal-reservation.json"),
            "cleanup_reservation_sha256": sha256_file(target / "cleanup-reservation.json"),
        },
    )
    _record_stage(target / "stages.jsonl", "attempt_reserved")
    return fallback_path


def _fallback_error(fallback_path: Path, event: str, error: dict[str, str]) -> None:
    append_jsonl(fallback_path, {"event": event, "at_utc": now_utc(), "error": error})


def execute_probe_body(
    executed_at_utc: str,
    *,
    target: Path,
    bindings: dict[str, Any],
    arcpy_loader: Callable[[], Any] = _load_arcpy,
    corpus_creator: Callable[[Path], list[Path]] = create_corpus,
    corpus_scanner: Callable[[Iterable[Path]], dict[str, Any]] = scan_corpus,
    terminal_writer: Callable[[Path, object], None] = write_new_json,
    cleanup_writer: Callable[[Path, object], None] = write_new_json,
    enforce_expected_digest: bool = True,
) -> int:
    fallback_path = _reserve_attempt(target, executed_at_utc, bindings)
    stages_path = target / "stages.jsonl"
    replacements = (target, ROOT, EXTERNAL_CUSTODY_ROOT)
    arcpy: Any | None = None
    image_checked_out = False
    spatial_checked_out = False
    scan_summary: dict[str, Any] | None = None
    product_info: str | None = None
    raster_a: str | None = None
    raster_b: str | None = None
    mosaic: str | None = None
    primary_failure: dict[str, str] | None = None
    terminal_persisted = False
    terminal_persistence_failure = False
    cleanup_persistence_failure = False

    def capture(exc: BaseException, event: str) -> None:
        nonlocal primary_failure
        sanitized = safe_error(exc, replacements)
        if primary_failure is None:
            primary_failure = sanitized
            _fallback_error(fallback_path, "probe_exception_captured", sanitized)
        else:
            _fallback_error(fallback_path, event, sanitized)

    try:
        try:
            _record_stage(stages_path, "corpus_create_started")
            corpus_paths = corpus_creator(target / "corpus")
            _record_stage(
                stages_path,
                "corpus_create_completed",
                file_count=len(corpus_paths),
                total_logical_bytes=sum(item.stat().st_size for item in corpus_paths if item.exists()),
            )
            _record_stage(stages_path, "corpus_hash_started")
            scan_summary = corpus_scanner(corpus_paths)
            validate_scan(scan_summary, enforce_expected_digest=enforce_expected_digest)
            _record_stage(
                stages_path,
                "corpus_hash_completed",
                file_count=scan_summary["file_count"],
                total_logical_bytes=scan_summary["total_logical_bytes"],
                aggregate_sha256=scan_summary["aggregate_sha256"],
                elapsed_seconds=scan_summary["elapsed_seconds"],
            )
            arcpy = _call_stage(stages_path, "arcpy_import", arcpy_loader)
            product_info = _call_stage(stages_path, "product_info", lambda: str(arcpy.ProductInfo()))
            if not product_info or product_info.casefold() in {"notinitialized", "none"}:
                raise ProbeError("product_info_not_initialized")
            _call_stage(stages_path, "overwrite_output", lambda: setattr(arcpy.env, "overwriteOutput", False))
            image_result = _call_stage(stages_path, "image_analyst_checkout", lambda: str(arcpy.CheckOutExtension("ImageAnalyst")))
            if image_result != "CheckedOut":
                raise ProbeError("image_analyst_checkout_not_checked_out", image_result)
            image_checked_out = True
            spatial_result = _call_stage(stages_path, "spatial_checkout", lambda: str(arcpy.CheckOutExtension("Spatial")))
            if spatial_result != "CheckedOut":
                raise ProbeError("spatial_checkout_not_checked_out", spatial_result)
            spatial_checked_out = True
            scratch = target / "scratch"
            scratch.mkdir()
            raster_a = _call_stage(
                stages_path,
                "disposable_raster_a",
                lambda: _create_disposable_raster(arcpy, scratch, "probe-a.tif", [[1.0, 2.0], [3.0, 4.0]]),
            )
            raster_b = _call_stage(
                stages_path,
                "disposable_raster_b",
                lambda: _create_disposable_raster(arcpy, scratch, "probe-b.tif", [[5.0, 6.0], [7.0, 8.0]]),
            )
            mosaic = _call_stage(stages_path, "disposable_mosaic", lambda: _mosaic(arcpy, scratch, raster_a, raster_b))
        except BaseException as exc:
            capture(exc, "secondary_probe_exception_captured")
        finally:
            if arcpy is not None and spatial_checked_out:
                try:
                    result = _call_stage(stages_path, "spatial_checkin", lambda: str(arcpy.CheckInExtension("Spatial")))
                    if result != "CheckedIn":
                        raise ProbeError("spatial_checkin_not_checked_in", result)
                except BaseException as exc:
                    capture(exc, "secondary_probe_exception_captured")
            if arcpy is not None and image_checked_out:
                try:
                    result = _call_stage(stages_path, "image_analyst_checkin", lambda: str(arcpy.CheckInExtension("ImageAnalyst")))
                    if result != "CheckedIn":
                        raise ProbeError("image_analyst_checkin_not_checked_in", result)
                except BaseException as exc:
                    capture(exc, "secondary_probe_exception_captured")

        terminal_status = "pass_exact_disposable_delayed_import_sequence" if primary_failure is None else "block_probe_failure_no_retry"
        try:
            terminal: dict[str, Any] = {
                "schema_version": "1.0",
                "receipt_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-TERMINAL",
                "status": terminal_status,
                "completed_at_utc": now_utc(),
                "attempt_id": ATTEMPT_ID,
                "bindings": bindings,
                "reservations": {
                    "terminal_sha256": sha256_file(target / "terminal-reservation.json"),
                    "cleanup_sha256": sha256_file(target / "cleanup-reservation.json"),
                },
                "fallback_journal_sha256_before_terminal": sha256_file(fallback_path),
                "corpus": None
                if scan_summary is None
                else {
                    "file_count": scan_summary["file_count"],
                    "total_logical_bytes": scan_summary["total_logical_bytes"],
                    "aggregate_sha256": scan_summary["aggregate_sha256"],
                    "elapsed_seconds": scan_summary["elapsed_seconds"],
                    "inventory": [
                        {"name": item["name"], "logical_bytes": item["logical_bytes"]}
                        for item in scan_summary["files"]
                    ],
                },
                "product_info": product_info,
                "disposable_rasters_created": int(raster_a is not None) + int(raster_b is not None),
                "disposable_mosaic_created": mosaic is not None,
                "assertions": {
                    "attempt_consumed": True,
                    "automatic_retry_performed": False,
                    "consumed_probe_reused_or_retried": False,
                    "project_data_content_read": False,
                    "external_custody_accessed": False,
                    "network_request_performed_by_runner": False,
                    "credential_value_read": False,
                    "radar_processing_executed": False,
                    "historical_root_cause_established": False,
                    "recovery_readiness_established": False,
                    "scientific_result_established": False,
                },
            }
            if primary_failure is not None:
                terminal.update(primary_failure)
            terminal_writer(target / "terminal.json", terminal)
            terminal_persisted = True
            _record_stage(stages_path, "terminal_receipt_persisted", status=terminal_status)
        except BaseException as exc:
            terminal_persistence_failure = True
            _fallback_error(fallback_path, "terminal_persistence_exception_captured", safe_error(exc, replacements))
    finally:
        cleanup_status = "cleanup_not_started"
        cleanup_warnings: list[str] = []
        try:
            _record_stage(stages_path, "cleanup_started")
        except BaseException as exc:
            _fallback_error(fallback_path, "cleanup_stage_marker_exception_captured", safe_error(exc, replacements))
        try:
            cleanup_status, cleanup_warnings = cleanup_payload(target)
        except BaseException as exc:
            cleanup_status = "cleanup_failed"
            cleanup_warnings = [safe_error(exc, replacements)["failure_message"]]
            _fallback_error(fallback_path, "cleanup_exception_captured", safe_error(exc, replacements))
        try:
            cleanup = {
                "schema_version": "1.0",
                "receipt_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-CLEANUP",
                "status": cleanup_status,
                "completed_at_utc": now_utc(),
                "attempt_id": ATTEMPT_ID,
                "removed_children": ["corpus", "scratch"],
                "warnings": cleanup_warnings,
                "terminal_persisted": terminal_persisted,
                "terminal_sha256": sha256_file(target / "terminal.json") if (target / "terminal.json").is_file() else None,
                "fallback_journal_sha256_before_cleanup_receipt": sha256_file(fallback_path),
                "cleanup_reservation_sha256": sha256_file(target / "cleanup-reservation.json"),
            }
            cleanup_writer(target / "cleanup.json", cleanup)
            _record_stage(stages_path, "cleanup_completed_or_warning", status=cleanup_status)
            append_jsonl(
                fallback_path,
                {
                    "event": "cleanup_disposition_recorded",
                    "at_utc": now_utc(),
                    "status": cleanup_status,
                    "cleanup_receipt_persisted": True,
                    "fallback_is_success_evidence": False,
                },
            )
        except BaseException as exc:
            cleanup_persistence_failure = True
            _fallback_error(fallback_path, "cleanup_persistence_exception_captured", safe_error(exc, replacements))

    if cleanup_persistence_failure:
        return 22
    if terminal_persistence_failure:
        return 21
    if primary_failure is not None:
        return 20
    return 0


def execute_probe(
    executed_at_utc: str,
    *,
    arcpy_loader: Callable[[], Any] = _load_arcpy,
    corpus_creator: Callable[[Path], list[Path]] = create_corpus,
    corpus_scanner: Callable[[Iterable[Path]], dict[str, Any]] = scan_corpus,
) -> int:
    gate = publication_gate()
    gate_state = gate_state_publication()
    preflight_path = ROOT / FINAL_PREFLIGHT_REF
    if not preflight_path.is_file():
        raise ProbeError("final_preflight_missing")
    preflight = load_json(preflight_path)
    if (
        preflight.get("status") != "pass_final_no_content_preflight_one_receipt_recovery_probe_released"
        or preflight.get("bindings", {}).get("implementation_publication_gate_sha256") != sha256_file(ROOT / PUBLICATION_GATE_REF)
        or preflight.get("bindings", {}).get("gate_state_publication_sha256") != sha256_file(ROOT / GATE_STATE_REF)
        or preflight.get("attempt_id") != ATTEMPT_ID
    ):
        raise ProbeError("final_preflight_not_exact_pass")
    bindings = {
        **repository_bindings(),
        "implementation_commit_sha": gate["implementation_commit_sha"],
        "implementation_public_ci_run_id": gate["public_ci_run_id"],
        "gate_state_commit_sha": gate_state["gate_state_commit_sha"],
        "gate_state_public_ci_run_id": gate_state["public_ci_run_id"],
        "implementation_publication_gate_sha256": sha256_file(ROOT / PUBLICATION_GATE_REF),
        "gate_state_publication_sha256": sha256_file(ROOT / GATE_STATE_REF),
        "final_preflight_sha256": sha256_file(preflight_path),
    }
    return execute_probe_body(
        executed_at_utc,
        target=attempt_root(),
        bindings=bindings,
        arcpy_loader=arcpy_loader,
        corpus_creator=corpus_creator,
        corpus_scanner=corpus_scanner,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    preflight = subparsers.add_parser("preflight")
    preflight.add_argument("--checked-at-utc", required=True)
    execute = subparsers.add_parser("execute")
    execute.add_argument("--executed-at-utc", required=True)
    args = parser.parse_args()
    timestamp = args.checked_at_utc if args.command == "preflight" else args.executed_at_utc
    if not timestamp.endswith("Z"):
        raise SystemExit("timestamp must be UTC")
    if args.command == "preflight":
        return run_final_preflight(timestamp)
    result = execute_probe(timestamp)
    print(json.dumps({"status": "attempt_complete", "attempt_id": ATTEMPT_ID, "return_code": result}, indent=2))
    return result


if __name__ == "__main__":
    raise SystemExit(main())
