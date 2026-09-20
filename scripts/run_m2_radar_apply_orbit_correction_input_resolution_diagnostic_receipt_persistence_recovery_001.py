#!/usr/bin/env python3
"""Preflight and run the one approved input-resolution receipt recovery process."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Any, BinaryIO, Callable

from m2_radar_apply_orbit_correction_input_resolution_diagnostic_receipt_persistence_recovery_001_core import (
    ATTEMPT_ID,
    CONTRACT_REF,
    DiagnosticError,
    append_jsonl,
    describe_summary,
    external_paths,
    load_contract,
    load_object,
    persist_reserved,
    reserve_output,
    safe_error,
    sanitize_text,
    sha256_file,
    write_new_json,
)


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-apply-orbit-correction-input-resolution-diagnostic-receipt-persistence-recovery-001"
CONSUMED_PREFIX = "m2-radar-apply-orbit-correction-input-resolution-diagnostic-001"
APPROVAL_REF = f"records/source-gates/{PREFIX}-approval.json"
IMPLEMENTATION_GATE_REF = f"records/readiness/{PREFIX}-implementation-publication-gate.json"
IMPLEMENTATION_RECONCILIATION_REF = f"records/readiness/{PREFIX}-implementation-publication-reconciliation.json"
GATE_STATE_REF = f"records/readiness/{PREFIX}-gate-state-publication.json"
FINAL_PREFLIGHT_REF = f"records/readiness/{PREFIX}-final-preflight.json"
TERMINAL_REF = f"records/processing/{PREFIX}-terminal.json"
CLEANUP_REF = f"records/processing/{PREFIX}-cleanup.json"
FALLBACK_REF = f"records/processing/{PREFIX}-fallback.jsonl"
CONSUMED_TERMINAL_REF = f"records/processing/{CONSUMED_PREFIX}-terminal.json"
CONSUMED_CLEANUP_REF = f"records/processing/{CONSUMED_PREFIX}-cleanup.json"
CORE_REF = f"scripts/{PREFIX.replace('-', '_')}_core.py"
RUNNER_REF = f"scripts/run_{PREFIX.replace('-', '_')}.py"
TEST_REF = f"tests/test_{PREFIX.replace('-', '_')}.py"
ARCGIS_VALIDATOR_REF = f"scripts/validate_{PREFIX.replace('-', '_')}_arcgis.py"
ARCGIS_PYTHON = Path(r"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe")
EXPECTED_CHECKPOINT = (
    "M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-"
    "RECEIPT-PERSISTENCE-RECOVERY-001-EXECUTION"
)


def now_utc() -> str:
    import datetime as datetime_module

    return (
        datetime_module.datetime.now(datetime_module.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def repository_bindings() -> dict[str, str]:
    return {
        "recovery_contract_sha256": sha256_file(ROOT / CONTRACT_REF),
        "recovery_core_sha256": sha256_file(ROOT / CORE_REF),
        "recovery_runner_sha256": sha256_file(ROOT / RUNNER_REF),
        "portable_test_sha256": sha256_file(ROOT / TEST_REF),
        "arcgis_validator_sha256": sha256_file(ROOT / ARCGIS_VALIDATOR_REF),
        "approval_sha256": sha256_file(ROOT / APPROVAL_REF),
    }


def implementation_publication_gate() -> dict[str, Any]:
    path = ROOT / IMPLEMENTATION_GATE_REF
    if not path.is_file():
        raise DiagnosticError("implementation_publication_gate_missing")
    gate = load_object(path)
    if (
        gate.get("status") != "pass_public_default_branch_ci_receipt_recovery_implementation_ready"
        or gate.get("public_ci_conclusion") != "success"
        or gate.get("bindings") != repository_bindings()
    ):
        raise DiagnosticError("implementation_publication_gate_not_exact_pass")
    return gate


def gate_state_publication() -> dict[str, Any]:
    gate = implementation_publication_gate()
    path = ROOT / GATE_STATE_REF
    if not path.is_file():
        raise DiagnosticError("gate_state_publication_missing")
    state = load_object(path)
    if (
        state.get("status") != "pass_public_execution_gate_final_no_content_preflight_released"
        or state.get("public_ci_conclusion") != "success"
        or state.get("bindings", {}).get("implementation_publication_gate_sha256")
        != sha256_file(ROOT / IMPLEMENTATION_GATE_REF)
        or state.get("bindings", {}).get("implementation_publication_reconciliation_sha256")
        != sha256_file(ROOT / IMPLEMENTATION_RECONCILIATION_REF)
        or state.get("bindings", {}).get("implementation_commit_sha") != gate.get("implementation_commit_sha")
    ):
        raise DiagnosticError("gate_state_publication_not_exact_pass")
    return state


def _consumed_receipts_exact() -> bool:
    for ref in (CONSUMED_TERMINAL_REF, CONSUMED_CLEANUP_REF):
        path = ROOT / ref
        if not path.is_file() or path.stat().st_size != 0 or sha256_file(path) != (
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        ):
            return False
    return True


def build_final_preflight(checked_at_utc: str) -> dict[str, Any]:
    gate = implementation_publication_gate()
    state = gate_state_publication()
    contract = load_contract(ROOT)
    profile = load_object(ROOT / "records/project-control-profile.json")
    checks = {
        "implementation_publication_gate_exact_pass": True,
        "execution_gate_publication_exact_pass": True,
        "contract_exact_and_zero_geoprocessing": contract["limits"]["geoprocessing_tool_calls"] == 0,
        "consumed_zero_byte_receipts_exact": _consumed_receipts_exact(),
        "current_checkpoint_exact": profile.get("current_checkpoint", {}).get("checkpoint_id") == EXPECTED_CHECKPOINT,
        "arcgis_python_exists": ARCGIS_PYTHON.is_file(),
        "final_preflight_receipt_absent": not (ROOT / FINAL_PREFLIGHT_REF).exists(),
        "new_terminal_receipt_absent": not (ROOT / TERMINAL_REF).exists(),
        "new_cleanup_receipt_absent": not (ROOT / CLEANUP_REF).exists(),
        "new_fallback_journal_absent": not (ROOT / FALLBACK_REF).exists(),
        "arcpy_imported_by_preflight": "arcpy" in sys.modules,
        "external_attempt_root_presence_checked": False,
        "project_or_external_content_read": False,
    }
    required_true = (
        "implementation_publication_gate_exact_pass",
        "execution_gate_publication_exact_pass",
        "contract_exact_and_zero_geoprocessing",
        "consumed_zero_byte_receipts_exact",
        "current_checkpoint_exact",
        "arcgis_python_exists",
        "final_preflight_receipt_absent",
        "new_terminal_receipt_absent",
        "new_cleanup_receipt_absent",
        "new_fallback_journal_absent",
    )
    if any(checks[key] is not True for key in required_true):
        raise DiagnosticError("final_no_content_preflight_failed")
    if checks["arcpy_imported_by_preflight"] or checks["external_attempt_root_presence_checked"] or checks["project_or_external_content_read"]:
        raise DiagnosticError("final_no_content_preflight_boundary_violation")
    return {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-FINAL-PREFLIGHT",
        "checked_at_utc": checked_at_utc,
        "status": "pass_final_no_content_preflight_one_distinct_read_only_process_released",
        "bindings": {
            **repository_bindings(),
            "implementation_publication_gate_sha256": sha256_file(ROOT / IMPLEMENTATION_GATE_REF),
            "execution_gate_publication_sha256": sha256_file(ROOT / GATE_STATE_REF),
            "implementation_commit_sha": gate["implementation_commit_sha"],
            "implementation_public_ci_run_id": gate["public_ci_run_id"],
            "execution_gate_commit_sha": state["gate_state_commit_sha"],
            "execution_gate_public_ci_run_id": state["public_ci_run_id"],
        },
        "checks": checks,
        "attempt_id": ATTEMPT_ID,
        "assertions": {
            "distinct_process_started": False,
            "arcpy_imported": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "consumed_diagnostic_reused_or_retried": False,
            "consumed_reserved_receipts_mutated": False,
            "apply_orbit_correction_invoked": False,
            "geoprocessing_invoked": False,
            "attempt_root_reconstructed_or_substituted": False,
            "historical_root_cause_established": False,
            "radar_recovery_readiness_established": False,
            "scientific_result_established": False,
        },
        "next_action": "Run the one exact distinct read-only recovery process once in ArcGIS Pro Python; never retry it.",
    }


def run_final_preflight(checked_at_utc: str) -> int:
    output = ROOT / FINAL_PREFLIGHT_REF
    if output.exists():
        raise DiagnosticError("final_preflight_output_collision")
    receipt = build_final_preflight(checked_at_utc)
    write_new_json(output, receipt)
    print(json.dumps({"status": receipt["status"], "record": FINAL_PREFLIGHT_REF}, indent=2))
    return 0


def _load_arcpy() -> Any:
    return importlib.import_module("arcpy")


def filesystem_observations(paths: dict[str, Path], contract: dict[str, Any]) -> dict[str, Any]:
    attempt_root = paths["attempt_root"]
    safe = paths["safe_directory"]
    manifest = paths["manifest"]
    orbit = paths["orbit"]
    if not attempt_root.is_dir():
        raise DiagnosticError("exact_recovery_attempt_root_missing")
    if not safe.is_dir():
        raise DiagnosticError("exact_safe_candidate_missing")
    if not manifest.is_file():
        raise DiagnosticError("exact_manifest_candidate_missing")
    if not orbit.is_file():
        raise DiagnosticError("exact_orbit_candidate_missing")
    attempt_stat = attempt_root.stat()
    safe_stat = safe.stat()
    manifest_stat = manifest.stat()
    orbit_stat = orbit.stat()
    orbit_sha = sha256_file(orbit)
    if orbit_stat.st_size != contract["exact_inputs"]["orbit_size_bytes"] or orbit_sha != contract["exact_inputs"]["orbit_sha256"]:
        raise DiagnosticError("exact_orbit_identity_mismatch")
    return {
        "attempt_root": {
            "exists": True,
            "entry_type": "directory",
            "path_class": "exact_frozen_recovery_002_attempt_root",
            "device": int(attempt_stat.st_dev),
            "inode": int(attempt_stat.st_ino),
        },
        "safe_directory": {
            "exists": True,
            "entry_type": "directory",
            "path_class": "exact_m1_src_001_copied_safe_candidate",
            "device": int(safe_stat.st_dev),
            "inode": int(safe_stat.st_ino),
        },
        "manifest": {
            "exists": True,
            "entry_type": "file",
            "path_class": "exact_m1_src_001_manifest_candidate",
            "size_bytes": int(manifest_stat.st_size),
            "sha256": sha256_file(manifest),
            "device": int(manifest_stat.st_dev),
            "inode": int(manifest_stat.st_ino),
        },
        "orbit": {
            "exists": True,
            "entry_type": "file",
            "path_class": "exact_m2_orb_001_eof",
            "size_bytes": int(orbit_stat.st_size),
            "sha256": orbit_sha,
            "device": int(orbit_stat.st_dev),
            "inode": int(orbit_stat.st_ino),
        },
    }


def arcpy_observations(arcpy: Any, paths: dict[str, Path]) -> dict[str, Any]:
    install = arcpy.GetInstallInfo()
    runtime = {
        "product_name": sanitize_text(install.get("ProductName"), paths.values()),
        "version": sanitize_text(install.get("Version"), paths.values()),
        "build_number": sanitize_text(install.get("BuildNumber"), paths.values()),
        "license_level": sanitize_text(arcpy.ProductInfo(), paths.values()),
        "extensions": {
            "image_analyst": sanitize_text(arcpy.CheckExtension("ImageAnalyst"), paths.values()),
            "spatial": sanitize_text(arcpy.CheckExtension("Spatial"), paths.values()),
        },
        "apply_orbit_correction_usage": sanitize_text(arcpy.Usage("ApplyOrbitCorrection_ia"), paths.values()),
    }
    recognized: dict[str, Any] = {}
    for name in ("safe_directory", "manifest", "orbit"):
        path = paths[name]
        exists = bool(arcpy.Exists(str(path)))
        item: dict[str, Any] = {"arcpy_exists": exists}
        if exists:
            try:
                item["describe"] = describe_summary(arcpy.Describe(str(path)), paths)
            except BaseException as exc:
                item["describe_error"] = safe_error(exc, paths.values())
        recognized[name] = item
    return {"runtime": runtime, "catalog_recognition": recognized}


def _close_quietly(stream: BinaryIO | None) -> None:
    if stream is not None and not stream.closed:
        try:
            stream.close()
        except BaseException:
            pass


def _fallback(path: Path, event: str, **fields: Any) -> None:
    append_jsonl(path, {"event": event, "at_utc": now_utc(), **fields})


def execute_diagnostic_body(
    executed_at_utc: str,
    *,
    contract: dict[str, Any],
    paths: dict[str, Path],
    terminal_path: Path,
    cleanup_path: Path,
    fallback_path: Path,
    bindings: dict[str, Any],
    arcpy_loader: Callable[[], Any] = _load_arcpy,
    terminal_persister: Callable[[BinaryIO, object], None] = persist_reserved,
    cleanup_persister: Callable[[BinaryIO, object], None] = persist_reserved,
) -> int:
    if terminal_path.exists() or cleanup_path.exists() or fallback_path.exists():
        raise DiagnosticError("diagnostic_recovery_output_collision")
    terminal_handle: BinaryIO | None = reserve_output(terminal_path)
    cleanup_handle: BinaryIO | None = reserve_output(cleanup_path)
    append_jsonl(
        fallback_path,
        {
            "event": "fallback_journal_initialized",
            "at_utc": executed_at_utc,
            "attempt_id": ATTEMPT_ID,
            "fallback_is_success_evidence": False,
        },
        initialize=True,
    )
    replacements = tuple(paths.values()) + (ROOT, terminal_path, cleanup_path, fallback_path)
    filesystem: dict[str, Any] | None = None
    arcgis: dict[str, Any] | None = None
    project_data_content_read = False
    external_custody_accessed = False
    primary_failure: dict[str, str] | None = None
    terminal_persisted = False
    terminal_persistence_failure = False
    cleanup_persistence_failure = False

    try:
        try:
            _fallback(fallback_path, "external_read_sequence_started", attempt_id=ATTEMPT_ID)
            project_data_content_read = True
            filesystem = filesystem_observations(paths, contract)
            external_custody_accessed = True
            arcpy = arcpy_loader()
            arcgis = arcpy_observations(arcpy, paths)
        except BaseException as exc:
            primary_failure = safe_error(exc, replacements)
            _fallback(fallback_path, "primary_diagnostic_exception_captured", error=primary_failure)
            if primary_failure["failure_code"] in {"exact_orbit_candidate_missing", "exact_orbit_identity_mismatch"}:
                external_custody_accessed = True

        if primary_failure is None:
            status = "pass_current_input_resolution_diagnostic_only"
            disposition = "pass_diagnostic_only"
        elif primary_failure["failure_code"].endswith("_missing"):
            status = "block_missing_exact_input_no_retry"
            disposition = "block"
        else:
            status = "block_read_only_diagnostic_failure_no_retry"
            disposition = "block"
        try:
            terminal: dict[str, Any] = {
                "schema_version": "1.0",
                "receipt_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-TERMINAL",
                "status": status,
                "disposition": disposition,
                "started_at_utc": executed_at_utc,
                "completed_at_utc": now_utc(),
                "attempt_id": ATTEMPT_ID,
                "bindings": bindings,
                "fallback_journal_sha256_before_terminal": sha256_file(fallback_path),
                "filesystem_observations": filesystem,
                "arcgis_observations": arcgis,
                "assertions": {
                    "distinct_process_consumed": True,
                    "automatic_retry_performed": False,
                    "consumed_diagnostic_reused_or_retried": False,
                    "consumed_reserved_receipts_mutated": False,
                    "project_data_content_read": project_data_content_read,
                    "external_custody_accessed": external_custody_accessed,
                    "apply_orbit_correction_invoked": False,
                    "geoprocessing_invoked": False,
                    "source_orbit_or_dem_copied": False,
                    "source_orbit_or_dem_mutated": False,
                    "attempt_root_reconstructed_or_substituted": False,
                    "new_radar_attempt_created": False,
                    "derived_raster_created": False,
                    "baseline_or_change_analysis_executed": False,
                    "historical_root_cause_established": False,
                    "radar_recovery_readiness_established": False,
                    "scientific_result_established": False,
                },
                "limitations": [
                    "This result describes current filesystem presence and ArcGIS catalog recognition only.",
                    "It does not establish the historical ApplyOrbitCorrection failure cause or a corrected call.",
                    "It does not authorize path correction, substitution, processing, retry, or scientific use.",
                ],
            }
            if primary_failure is not None:
                terminal.update(primary_failure)
            terminal_persister(terminal_handle, terminal)
            terminal_handle = None
            terminal_persisted = True
            _fallback(fallback_path, "terminal_receipt_persisted", status=status)
        except BaseException as exc:
            terminal_persistence_failure = True
            _close_quietly(terminal_handle)
            terminal_handle = None
            _fallback(
                fallback_path,
                "terminal_persistence_exception_captured",
                error=safe_error(exc, replacements),
                primary_error_preserved=primary_failure is not None,
            )
    finally:
        try:
            cleanup = {
                "schema_version": "1.0",
                "receipt_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-CLEANUP",
                "status": "pass_no_payload_or_temporary_artifact_cleanup_required",
                "completed_at_utc": now_utc(),
                "attempt_id": ATTEMPT_ID,
                "terminal_persisted": terminal_persisted,
                "terminal_sha256": sha256_file(terminal_path) if terminal_persisted else None,
                "fallback_journal_sha256_before_cleanup": sha256_file(fallback_path),
                "assertions": {
                    "temporary_payload_created": False,
                    "source_orbit_or_dem_copied": False,
                    "source_orbit_or_dem_mutated": False,
                    "derived_raster_created": False,
                    "external_cleanup_attempted": False,
                    "consumed_reserved_receipts_mutated": False,
                },
            }
            cleanup_persister(cleanup_handle, cleanup)
            cleanup_handle = None
            _fallback(
                fallback_path,
                "cleanup_disposition_recorded",
                status=cleanup["status"],
                cleanup_receipt_persisted=True,
                fallback_is_success_evidence=False,
            )
        except BaseException as exc:
            cleanup_persistence_failure = True
            _close_quietly(cleanup_handle)
            cleanup_handle = None
            _fallback(
                fallback_path,
                "cleanup_persistence_exception_captured",
                error=safe_error(exc, replacements),
                primary_error_preserved=primary_failure is not None,
            )
        finally:
            _close_quietly(terminal_handle)
            _close_quietly(cleanup_handle)

    if cleanup_persistence_failure:
        return 22
    if terminal_persistence_failure:
        return 21
    if primary_failure is not None:
        return 20
    return 0


def execute_diagnostic(executed_at_utc: str) -> int:
    gate = implementation_publication_gate()
    state = gate_state_publication()
    preflight_path = ROOT / FINAL_PREFLIGHT_REF
    if not preflight_path.is_file():
        raise DiagnosticError("final_preflight_missing")
    preflight = load_object(preflight_path)
    if (
        preflight.get("status") != "pass_final_no_content_preflight_one_distinct_read_only_process_released"
        or preflight.get("bindings", {}).get("implementation_publication_gate_sha256")
        != sha256_file(ROOT / IMPLEMENTATION_GATE_REF)
        or preflight.get("bindings", {}).get("execution_gate_publication_sha256") != sha256_file(ROOT / GATE_STATE_REF)
        or preflight.get("attempt_id") != ATTEMPT_ID
    ):
        raise DiagnosticError("final_preflight_not_exact_pass")
    contract = load_contract(ROOT)
    bindings = {
        **repository_bindings(),
        "implementation_commit_sha": gate["implementation_commit_sha"],
        "implementation_public_ci_run_id": gate["public_ci_run_id"],
        "execution_gate_commit_sha": state["gate_state_commit_sha"],
        "execution_gate_public_ci_run_id": state["public_ci_run_id"],
        "implementation_publication_gate_sha256": sha256_file(ROOT / IMPLEMENTATION_GATE_REF),
        "execution_gate_publication_sha256": sha256_file(ROOT / GATE_STATE_REF),
        "final_preflight_sha256": sha256_file(preflight_path),
    }
    return execute_diagnostic_body(
        executed_at_utc,
        contract=contract,
        paths=external_paths(contract),
        terminal_path=ROOT / TERMINAL_REF,
        cleanup_path=ROOT / CLEANUP_REF,
        fallback_path=ROOT / FALLBACK_REF,
        bindings=bindings,
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
    result = execute_diagnostic(timestamp)
    print(json.dumps({"status": "attempt_complete", "attempt_id": ATTEMPT_ID, "return_code": result}, indent=2))
    return result


if __name__ == "__main__":
    raise SystemExit(main())
