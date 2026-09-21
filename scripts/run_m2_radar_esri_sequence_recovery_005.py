#!/usr/bin/env python3
"""Run the one approved radar Esri-sequence recovery-005 attempt."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
from typing import Any, Callable

import m2_radar_pixel_orbit_application_001_core as base_core
import m2_radar_esri_sequence_processing_005 as short_runner
from m2_radar_esri_sequence_recovery_005_core import (
    ATTEMPT_ID,
    BASE_CONTRACT_REF,
    CONTRACT_REF,
    ROUTE_ORDER,
    SOURCE_ORDER,
    append_jsonl,
    is_subst_drive,
    load_execution_plan,
    path_chain_has_reparse,
    project_short_paths,
    safe_error,
    verify_external_identities,
    write_new_json,
)


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-esri-sequence-recovery-005"
PUBLICATION_GATE_REF = f"records/readiness/{PREFIX}-implementation-publication-gate.json"
GATE_STATE_REF = f"records/readiness/{PREFIX}-gate-state-publication.json"
FINAL_PREFLIGHT_REF = f"records/readiness/{PREFIX}-final-preflight.json"
TERMINAL_REF = f"records/processing/{PREFIX}-terminal-reconciliation.json"
CORE_REF = f"scripts/{PREFIX.replace('-', '_')}_core.py"
RUNNER_REF = f"scripts/run_{PREFIX.replace('-', '_')}.py"
VALIDATOR_REF = f"scripts/validate_{PREFIX.replace('-', '_')}_arcgis.py"
TEST_REF = f"tests/test_{PREFIX.replace('-', '_')}.py"
BASE_CORE_REF = "scripts/m2_radar_pixel_orbit_application_001_core.py"
BASE_RUNNER_REF = "scripts/run_m2_radar_pixel_orbit_application_001.py"
SHORT_PROCESSING_REF = "scripts/m2_radar_esri_sequence_processing_005.py"


def now_utc() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def repo_sha(ref: str) -> str:
    return base_core.sha256_file(ROOT / ref)


def repository_bindings() -> dict[str, str]:
    return {
        "recovery_contract_sha256": repo_sha(CONTRACT_REF),
        "recovery_core_sha256": repo_sha(CORE_REF),
        "recovery_runner_sha256": repo_sha(RUNNER_REF),
        "arcgis_validator_sha256": repo_sha(VALIDATOR_REF),
        "portable_test_sha256": repo_sha(TEST_REF),
        "base_contract_sha256": repo_sha(BASE_CONTRACT_REF),
        "base_core_sha256": repo_sha(BASE_CORE_REF),
        "base_runner_sha256": repo_sha(BASE_RUNNER_REF),
        "esri_sequence_processing_sha256": repo_sha(SHORT_PROCESSING_REF),
    }


def publication_gate() -> dict[str, Any]:
    path = ROOT / PUBLICATION_GATE_REF
    if not path.is_file():
        raise base_core.RadarRouteError("esri_sequence_recovery_005_implementation_publication_gate_missing")
    gate = base_core.load_object(path)
    if (
        gate.get("status") != "pass_public_default_branch_ci_esri_sequence_recovery_005_implementation_ready"
        or gate.get("public_ci_conclusion") != "success"
        or any(gate.get("bindings", {}).get(key) != value for key, value in repository_bindings().items())
    ):
        raise base_core.RadarRouteError("esri_sequence_recovery_005_implementation_publication_gate_not_exact_pass")
    return gate


def gate_state_publication() -> dict[str, Any]:
    path = ROOT / GATE_STATE_REF
    if not path.is_file():
        raise base_core.RadarRouteError("esri_sequence_recovery_005_gate_state_publication_missing")
    state = base_core.load_object(path)
    if (
        state.get("status") != "pass_public_default_branch_ci_one_final_preflight_released"
        or state.get("bindings", {}).get("implementation_publication_gate_sha256") != repo_sha(PUBLICATION_GATE_REF)
        or state.get("bindings", {}).get("recovery_contract_sha256") != repo_sha(CONTRACT_REF)
    ):
        raise base_core.RadarRouteError("esri_sequence_recovery_005_gate_state_publication_not_exact_pass")
    return state


def attempt_root(plan: dict[str, Any]) -> Path:
    return base_core.require_external_child(
        plan["data_root"],
        Path(plan["contract"]["attempt"]["external_attempt_root"]),
        must_exist=False,
    )


def _nearest_existing_parent(path: Path) -> Path:
    candidate = path
    while not candidate.exists():
        if candidate.parent == candidate:
            raise base_core.RadarRouteError("attempt_parent_unavailable")
        candidate = candidate.parent
    return candidate


def build_final_preflight(checked_at_utc: str) -> dict[str, Any]:
    if (ROOT / FINAL_PREFLIGHT_REF).exists():
        raise base_core.RadarRouteError("final_preflight_collision")
    gate = publication_gate()
    gate_state = gate_state_publication()
    plan = load_execution_plan(ROOT)
    target = attempt_root(plan)
    if target.exists() or (ROOT / TERMINAL_REF).exists():
        raise base_core.RadarRouteError("esri_sequence_recovery_005_attempt_or_terminal_collision")
    if is_subst_drive(target):
        raise base_core.RadarRouteError("raster_function_subst_drive_prohibited")
    if path_chain_has_reparse(target):
        raise base_core.RadarRouteError("raster_function_reparse_point_prohibited")
    existing_parent = _nearest_existing_parent(target.parent)
    free_bytes = shutil.disk_usage(existing_parent).free
    minimum = plan["contract"]["attempt"]["minimum_free_space_bytes"]
    if free_bytes < minimum:
        raise base_core.RadarRouteError("insufficient_free_space_no_content_read", f"{free_bytes} < {minimum}")
    return {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-RADAR-ESRI-SEQUENCE-RECOVERY-005-FINAL-PREFLIGHT",
        "checked_at_utc": checked_at_utc,
        "status": "pass_final_no_content_preflight_one_fresh_attempt_released",
        "attempt_id": ATTEMPT_ID,
        "attempt_root": str(target),
        "bindings": {
            **repository_bindings(),
            "implementation_commit_sha": gate["implementation_commit_sha"],
            "implementation_public_ci_run_id": gate["public_ci_run_id"],
            "gate_state_commit_sha": gate_state["gate_state_commit_sha"],
            "gate_state_public_ci_run_id": gate_state["public_ci_run_id"],
            "implementation_publication_gate_sha256": repo_sha(PUBLICATION_GATE_REF),
            "gate_state_publication_sha256": repo_sha(GATE_STATE_REF),
        },
        "assertions": {
            "contract_validated": True,
            "implementation_public_ci_passed": True,
            "gate_state_public_ci_passed": True,
            "attempt_root_absent": True,
            "attempt_root_exact": str(target) == str(plan["contract"]["attempt"]["external_attempt_root"]),
            "attempt_root_not_subst_drive": True,
            "attempt_root_chain_has_no_reparse_point": True,
            "terminal_reconciliation_absent": True,
            "minimum_free_space_bytes": minimum,
            "observed_free_space_bytes": free_bytes,
            "project_data_content_read": False,
            "external_custody_content_read": False,
            "arcpy_invoked": False,
            "fresh_attempt_process_started": False,
            "network_request_performed": False,
            "credential_value_read": False,
            "consumed_attempt_reused_or_retried": False,
            "baseline_or_change_analysis_executed": False,
            "scientific_result_established": False,
        },
    }


def run_final_preflight(checked_at_utc: str) -> int:
    receipt = build_final_preflight(checked_at_utc)
    write_new_json(ROOT / FINAL_PREFLIGHT_REF, receipt)
    print(json.dumps({"status": receipt["status"], "receipt": FINAL_PREFLIGHT_REF}, indent=2))
    return 0


def _record_stage(path: Path, stage: str, **details: Any) -> None:
    append_jsonl(path, {"stage": stage, "at_utc": now_utc(), **details})


def _reserve_attempt(target: Path, executed_at_utc: str, bindings: dict[str, Any]) -> tuple[Path, Path]:
    if target.exists():
        raise base_core.RadarRouteError("esri_sequence_recovery_005_attempt_collision")
    target.mkdir(parents=True)
    stages_path = target / "stages.jsonl"
    fallback_path = target / "fallback.jsonl"
    _record_stage(stages_path, "attempt_reserved", attempt_id=ATTEMPT_ID)
    terminal_reservation = {
        "schema_version": "1.0",
        "reservation_id": "NEPAL-M2-RADAR-ESRI-SEQUENCE-RECOVERY-005-TERMINAL-RESERVATION",
        "reserved_at_utc": executed_at_utc,
        "attempt_id": ATTEMPT_ID,
        "target_name": "terminal.json",
        "append_only": True,
    }
    cleanup_reservation = {
        "schema_version": "1.0",
        "reservation_id": "NEPAL-M2-RADAR-ESRI-SEQUENCE-RECOVERY-005-CLEANUP-RESERVATION",
        "reserved_at_utc": executed_at_utc,
        "attempt_id": ATTEMPT_ID,
        "target_name": "cleanup.json",
        "append_only": True,
    }
    write_new_json(target / "terminal-reservation.json", terminal_reservation)
    write_new_json(target / "cleanup-reservation.json", cleanup_reservation)
    _record_stage(stages_path, "terminal_and_cleanup_receipts_reserved")
    append_jsonl(fallback_path, {
        "event": "fallback_journal_initialized",
        "at_utc": executed_at_utc,
        "attempt_id": ATTEMPT_ID,
        "fallback_is_success_evidence": False,
    })
    _record_stage(stages_path, "fallback_journal_initialized")
    write_new_json(target / "started.json", {
        "schema_version": "1.0",
        "status": "started_single_stage_evidenced_esri_sequence_recovery_005_attempt",
        "started_at_utc": executed_at_utc,
        "attempt_id": ATTEMPT_ID,
        "bindings": bindings,
        "terminal_reservation_sha256": base_core.sha256_file(target / "terminal-reservation.json"),
        "cleanup_reservation_sha256": base_core.sha256_file(target / "cleanup-reservation.json"),
    })
    return stages_path, fallback_path


def _fallback_error(path: Path, event: str, error: dict[str, str]) -> None:
    append_jsonl(path, {"event": event, "at_utc": now_utc(), "error": error})


def _load_arcpy() -> Any:
    import arcpy  # type: ignore[import-not-found]

    return arcpy


def execute_attempt_body(
    executed_at_utc: str,
    *,
    plan: dict[str, Any],
    target: Path,
    bindings: dict[str, Any],
    identity_verifier: Callable[[dict[str, Any]], dict[str, Any]] = verify_external_identities,
    path_projector: Callable[[dict[str, Any], Path], dict[str, Any]] = project_short_paths,
    arcpy_loader: Callable[[], Any] = _load_arcpy,
    dem_builder: Callable[[Any, dict[str, Any], Path], Any] = short_runner.create_dem_mosaic,
    support_builder: Callable[[Any, dict[str, Any], Path], Any] = short_runner.create_analysis_support,
    source_processor: Callable[..., dict[str, Any]] = short_runner.process_source,
    route_processor: Callable[..., dict[str, Any]] = short_runner.process_route,
    terminal_writer: Callable[[Path, object], None] = write_new_json,
    cleanup_writer: Callable[[Path, object], None] = write_new_json,
) -> int:
    stages_path, fallback_path = _reserve_attempt(target, executed_at_utc, bindings)
    replacements = (target, ROOT, plan.get("data_root", Path(".")))
    arcpy: Any | None = None
    image_checked_out = False
    spatial_checked_out = False
    identities_before: dict[str, Any] | None = None
    identities_after: dict[str, Any] | None = None
    path_projection: dict[str, Any] | None = None
    sources: dict[str, Any] = {"status": "not_started", "results": [], "stopped_source_id": None}
    routes: list[dict[str, Any]] = []
    stopped_route_id: str | None = None
    primary_failure: dict[str, str] | None = None
    terminal_status = "block_esri_sequence_recovery_005_failure_no_retry"
    terminal_persisted = False
    terminal_persistence_failure = False
    cleanup_persistence_failure = False
    cleanup_warnings: list[str] = []

    def capture(exc: BaseException, event: str) -> None:
        nonlocal primary_failure
        sanitized = safe_error(exc, replacements)
        if primary_failure is None:
            primary_failure = sanitized
            _fallback_error(fallback_path, "processing_exception_captured", sanitized)
        else:
            _fallback_error(fallback_path, event, sanitized)

    try:
        try:
            _record_stage(stages_path, "identity_scan_started")
            identities_before = identity_verifier(plan)
            _record_stage(stages_path, "identity_scan_completed")
            _record_stage(stages_path, "path_projection_started")
            path_projection = path_projector(plan, target)
            _record_stage(
                stages_path,
                "path_projection_completed",
                projected_path_count=path_projection["projected_path_count"],
                maximum_projected_path_characters=path_projection["maximum_projected_path_characters"],
            )
            _record_stage(stages_path, "arcpy_import_started")
            arcpy = arcpy_loader()
            _record_stage(stages_path, "arcpy_import_completed")
            _record_stage(stages_path, "product_info_started")
            product_info = str(arcpy.ProductInfo())
            if not product_info or product_info.casefold() in {"notinitialized", "none"}:
                raise base_core.RadarRouteError("product_info_not_initialized", product_info)
            _record_stage(stages_path, "product_info_completed", product_info=product_info)
            arcpy.env.overwriteOutput = False
            _record_stage(stages_path, "image_analyst_checkout_started")
            image_result = str(arcpy.CheckOutExtension("ImageAnalyst"))
            if image_result != "CheckedOut":
                raise base_core.RadarRouteError("image_analyst_checkout_not_checked_out", image_result)
            image_checked_out = True
            _record_stage(stages_path, "image_analyst_checkout_completed")
            _record_stage(stages_path, "spatial_checkout_started")
            spatial_result = str(arcpy.CheckOutExtension("Spatial"))
            if spatial_result != "CheckedOut":
                raise base_core.RadarRouteError("spatial_checkout_not_checked_out", spatial_result)
            spatial_checked_out = True
            _record_stage(stages_path, "spatial_checkout_completed")
            _record_stage(stages_path, "dem_mosaic_started")
            dem_mosaic = dem_builder(arcpy, plan, target)
            _record_stage(stages_path, "dem_mosaic_completed")
            _record_stage(stages_path, "analysis_support_started")
            support = support_builder(arcpy, plan, target)
            _record_stage(stages_path, "analysis_support_completed")
            _record_stage(stages_path, "source_processing_fixed_order")

            def worker(source_id: str) -> dict[str, Any]:
                _record_stage(stages_path, "source_processing_fixed_order", source_id=source_id)
                return source_processor(
                    arcpy=arcpy,
                    plan=plan,
                    identities_before=identities_before,
                    attempt_root=target,
                    dem_mosaic=dem_mosaic,
                    support=support,
                    source_id=source_id,
                    started_at_utc=now_utc(),
                    stage_recorder=lambda **details: _record_stage(
                        stages_path, "source_processing_fixed_order", **details
                    ),
                )

            sources = base_core.execute_fixed_order(SOURCE_ORDER, worker)
            if sources["status"] == "pass_all_sources":
                _record_stage(stages_path, "route_evaluation_fixed_order")
                for route_id in ROUTE_ORDER:
                    _record_stage(stages_path, "route_evaluation_fixed_order", route_id=route_id)
                    result = route_processor(
                        arcpy=arcpy,
                        plan=plan,
                        attempt_root=target,
                        support=support,
                        route_id=route_id,
                        started_at_utc=now_utc(),
                    )
                    routes.append(result)
                    if result.get("status") != "pass_route_evaluated_qa_only":
                        stopped_route_id = route_id
                        break
        except BaseException as exc:
            capture(exc, "secondary_processing_exception_captured")
        finally:
            if identities_before is not None:
                try:
                    _record_stage(stages_path, "postattempt_identity_scan_started")
                    identities_after = identity_verifier(plan)
                    if identities_before != identities_after:
                        raise base_core.RadarRouteError("external_custody_changed_during_attempt")
                    _record_stage(stages_path, "postattempt_identity_scan_completed")
                except BaseException as exc:
                    capture(exc, "postattempt_identity_exception_captured")

        terminal_status = (
            "pass_six_sources_two_routes_qa_only"
            if primary_failure is None
            and sources.get("status") == "pass_all_sources"
            and len(routes) == 2
            and stopped_route_id is None
            else "block_esri_sequence_recovery_005_failure_no_retry"
        )
        try:
            terminal: dict[str, Any] = {
                "schema_version": "1.0",
                "receipt_id": "NEPAL-M2-RADAR-ESRI-SEQUENCE-RECOVERY-005-TERMINAL",
                "status": terminal_status,
                "completed_at_utc": now_utc(),
                "attempt_id": ATTEMPT_ID,
                "bindings": bindings,
                "reservations": {
                    "terminal_sha256": base_core.sha256_file(target / "terminal-reservation.json"),
                    "cleanup_sha256": base_core.sha256_file(target / "cleanup-reservation.json"),
                },
                "fallback_journal_sha256_before_terminal": base_core.sha256_file(fallback_path),
                "source_execution": sources,
                "route_evaluations": routes,
                "stopped_route_id": stopped_route_id,
                "external_custody_unchanged": identities_before is not None and identities_before == identities_after,
                "path_projection": path_projection,
                "assertions": {
                    "attempt_consumed": True,
                    "source_order_exact": [item.get("source_id") for item in sources.get("results", [])]
                    == SOURCE_ORDER[: len(sources.get("results", []))],
                    "route_order_exact": [item.get("route_id") for item in routes] == ROUTE_ORDER[: len(routes)],
                    "automatic_retry_performed": False,
                    "consumed_attempt_reused_or_retried": False,
                    "network_request_performed_by_runner": False,
                    "credential_value_read": False,
                    "source_orbit_or_dem_custody_mutated": False,
                    "historical_root_cause_established": False,
                    "radar_recovery_readiness_established": False,
                    "baseline_admission_authorized": False,
                    "change_analysis_executed": False,
                    "interpretation_or_attribution_executed": False,
                    "derived_pixel_publication_authorized": False,
                    "scientific_publication_authorized": False,
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
        try:
            _record_stage(stages_path, "cleanup_started")
        except BaseException as exc:
            _fallback_error(fallback_path, "cleanup_stage_marker_exception_captured", safe_error(exc, replacements))
        if arcpy is not None and spatial_checked_out:
            try:
                result = str(arcpy.CheckInExtension("Spatial"))
                if result != "CheckedIn":
                    raise base_core.RadarRouteError("spatial_checkin_not_checked_in", result)
            except BaseException as exc:
                cleanup_warnings.append(safe_error(exc, replacements)["failure_message"])
                _fallback_error(fallback_path, "spatial_checkin_exception_captured", safe_error(exc, replacements))
        if arcpy is not None and image_checked_out:
            try:
                result = str(arcpy.CheckInExtension("ImageAnalyst"))
                if result != "CheckedIn":
                    raise base_core.RadarRouteError("image_analyst_checkin_not_checked_in", result)
            except BaseException as exc:
                cleanup_warnings.append(safe_error(exc, replacements)["failure_message"])
                _fallback_error(fallback_path, "image_analyst_checkin_exception_captured", safe_error(exc, replacements))
        try:
            cleanup = {
                "schema_version": "1.0",
                "receipt_id": "NEPAL-M2-RADAR-ESRI-SEQUENCE-RECOVERY-005-CLEANUP",
                "status": "cleanup_completed" if not cleanup_warnings else "cleanup_completed_with_warning",
                "completed_at_utc": now_utc(),
                "attempt_id": ATTEMPT_ID,
                "warnings": cleanup_warnings,
                "terminal_persisted": terminal_persisted,
                "terminal_sha256": base_core.sha256_file(target / "terminal.json") if (target / "terminal.json").is_file() else None,
                "fallback_journal_sha256_before_cleanup_receipt": base_core.sha256_file(fallback_path),
                "cleanup_reservation_sha256": base_core.sha256_file(target / "cleanup-reservation.json"),
            }
            cleanup_writer(target / "cleanup.json", cleanup)
            _record_stage(stages_path, "cleanup_completed_or_warning", status=cleanup["status"])
            append_jsonl(fallback_path, {
                "event": "cleanup_disposition_recorded",
                "at_utc": now_utc(),
                "status": cleanup["status"],
                "cleanup_receipt_persisted": True,
                "fallback_is_success_evidence": False,
            })
        except BaseException as exc:
            cleanup_persistence_failure = True
            _fallback_error(fallback_path, "cleanup_persistence_exception_captured", safe_error(exc, replacements))

    if cleanup_persistence_failure:
        return 22
    if terminal_persistence_failure:
        return 21
    if primary_failure is not None or terminal_status != "pass_six_sources_two_routes_qa_only" or cleanup_warnings:
        return 20
    return 0


def execute_attempt(executed_at_utc: str) -> int:
    gate = publication_gate()
    state = gate_state_publication()
    preflight_path = ROOT / FINAL_PREFLIGHT_REF
    if not preflight_path.is_file():
        raise base_core.RadarRouteError("final_preflight_missing")
    preflight = base_core.load_object(preflight_path)
    if (
        preflight.get("status") != "pass_final_no_content_preflight_one_fresh_attempt_released"
        or preflight.get("attempt_id") != ATTEMPT_ID
        or preflight.get("bindings", {}).get("implementation_publication_gate_sha256") != repo_sha(PUBLICATION_GATE_REF)
        or preflight.get("bindings", {}).get("gate_state_publication_sha256") != repo_sha(GATE_STATE_REF)
    ):
        raise base_core.RadarRouteError("final_preflight_not_exact_pass")
    plan = load_execution_plan(ROOT)
    target = attempt_root(plan)
    if target.exists() or (ROOT / TERMINAL_REF).exists():
        raise base_core.RadarRouteError("esri_sequence_recovery_005_attempt_or_terminal_collision")
    bindings = {
        **repository_bindings(),
        "implementation_commit_sha": gate["implementation_commit_sha"],
        "implementation_public_ci_run_id": gate["public_ci_run_id"],
        "gate_state_commit_sha": state["gate_state_commit_sha"],
        "gate_state_public_ci_run_id": state["public_ci_run_id"],
        "implementation_publication_gate_sha256": repo_sha(PUBLICATION_GATE_REF),
        "gate_state_publication_sha256": repo_sha(GATE_STATE_REF),
        "final_preflight_sha256": repo_sha(FINAL_PREFLIGHT_REF),
    }
    return execute_attempt_body(executed_at_utc, plan=plan, target=target, bindings=bindings)


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
    try:
        if args.command == "preflight":
            return run_final_preflight(timestamp)
        result = execute_attempt(timestamp)
        print(json.dumps({"status": "attempt_complete", "attempt_id": ATTEMPT_ID, "return_code": result}, indent=2))
        return result
    except base_core.RadarRouteError as exc:
        print(json.dumps({"status": "stopped", "code": exc.code, "detail": exc.detail}, indent=2))
        return 12


if __name__ == "__main__":
    raise SystemExit(main())
