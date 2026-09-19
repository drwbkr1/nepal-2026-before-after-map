#!/usr/bin/env python3
"""Preflight and execute the one approved read-only input-resolution diagnostic."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from m2_radar_apply_orbit_correction_input_resolution_diagnostic_001_core import (
    ATTEMPT_ID,
    CONTRACT_REF,
    DiagnosticError,
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
PREFIX = "m2-radar-apply-orbit-correction-input-resolution-diagnostic-001"
APPROVAL_REF = f"records/source-gates/{PREFIX}-approval.json"
IMPLEMENTATION_GATE_REF = f"records/readiness/{PREFIX}-implementation-publication-gate.json"
IMPLEMENTATION_RECONCILIATION_REF = f"records/readiness/{PREFIX}-implementation-publication-reconciliation.json"
GATE_STATE_REF = f"records/readiness/{PREFIX}-gate-state-publication.json"
FINAL_PREFLIGHT_REF = f"records/readiness/{PREFIX}-final-preflight.json"
TERMINAL_REF = f"records/processing/{PREFIX}-terminal.json"
CLEANUP_REF = f"records/processing/{PREFIX}-cleanup.json"
CORE_REF = "scripts/m2_radar_apply_orbit_correction_input_resolution_diagnostic_001_core.py"
RUNNER_REF = "scripts/run_m2_radar_apply_orbit_correction_input_resolution_diagnostic_001.py"
TEST_REF = "tests/test_m2_radar_apply_orbit_correction_input_resolution_diagnostic_001.py"
ARCGIS_PYTHON = Path(r"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def repository_bindings() -> dict[str, str]:
    return {
        "diagnostic_contract_sha256": sha256_file(ROOT / CONTRACT_REF),
        "diagnostic_core_sha256": sha256_file(ROOT / CORE_REF),
        "diagnostic_runner_sha256": sha256_file(ROOT / RUNNER_REF),
        "synthetic_test_sha256": sha256_file(ROOT / TEST_REF),
        "approval_sha256": sha256_file(ROOT / APPROVAL_REF),
    }


def implementation_publication_gate() -> dict[str, Any]:
    path = ROOT / IMPLEMENTATION_GATE_REF
    if not path.is_file():
        raise DiagnosticError("implementation_publication_gate_missing")
    gate = load_object(path)
    if (
        gate.get("status") != "pass_public_default_branch_ci_read_only_diagnostic_implementation_ready"
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
        state.get("status") != "pass_public_gate_state_final_no_content_preflight_released"
        or state.get("public_ci_conclusion") != "success"
        or state.get("bindings", {}).get("implementation_publication_gate_sha256") != sha256_file(ROOT / IMPLEMENTATION_GATE_REF)
        or state.get("bindings", {}).get("implementation_publication_reconciliation_sha256")
        != sha256_file(ROOT / IMPLEMENTATION_RECONCILIATION_REF)
        or state.get("bindings", {}).get("implementation_commit_sha") != gate.get("implementation_commit_sha")
    ):
        raise DiagnosticError("gate_state_publication_not_exact_pass")
    return state


def protected_evidence_bindings(contract: dict[str, Any]) -> dict[str, str]:
    bindings: dict[str, str] = {}
    for item in contract["protected_public_evidence"]:
        ref = item["path"]
        expected = item["sha256"]
        observed = sha256_file(ROOT / ref)
        if observed != expected:
            raise DiagnosticError("protected_public_evidence_drift", ref)
        bindings[ref] = observed
    return bindings


def build_final_preflight(checked_at_utc: str) -> dict[str, Any]:
    gate = implementation_publication_gate()
    state = gate_state_publication()
    contract = load_contract(ROOT)
    profile = load_object(ROOT / "records/project-control-profile.json")
    expected_checkpoint = "M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-EXECUTION"
    checks = {
        "implementation_publication_gate_exact_pass": True,
        "gate_state_publication_exact_pass": True,
        "contract_exact_and_zero_geoprocessing": contract["limits"]["geoprocessing_tool_calls"] == 0,
        "protected_public_evidence_exact": bool(protected_evidence_bindings(contract)),
        "current_checkpoint_exact": profile.get("current_checkpoint", {}).get("checkpoint_id") == expected_checkpoint,
        "arcgis_python_exists": ARCGIS_PYTHON.is_file(),
        "final_preflight_receipt_absent": not (ROOT / FINAL_PREFLIGHT_REF).exists(),
        "terminal_receipt_absent": not (ROOT / TERMINAL_REF).exists(),
        "cleanup_receipt_absent": not (ROOT / CLEANUP_REF).exists(),
        "arcpy_imported_by_preflight": "arcpy" in sys.modules,
        "external_attempt_root_presence_checked": False,
        "project_or_external_content_read": False,
    }
    required_true = (
        "implementation_publication_gate_exact_pass", "gate_state_publication_exact_pass",
        "contract_exact_and_zero_geoprocessing", "protected_public_evidence_exact",
        "current_checkpoint_exact", "arcgis_python_exists", "final_preflight_receipt_absent",
        "terminal_receipt_absent", "cleanup_receipt_absent",
    )
    if any(checks[key] is not True for key in required_true):
        raise DiagnosticError("final_no_content_preflight_failed")
    if checks["arcpy_imported_by_preflight"] or checks["external_attempt_root_presence_checked"] or checks["project_or_external_content_read"]:
        raise DiagnosticError("final_no_content_preflight_boundary_violation")
    return {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-FINAL-PREFLIGHT",
        "checked_at_utc": checked_at_utc,
        "status": "pass_final_no_content_preflight_one_read_only_diagnostic_released",
        "bindings": {
            **repository_bindings(),
            "implementation_publication_gate_sha256": sha256_file(ROOT / IMPLEMENTATION_GATE_REF),
            "gate_state_publication_sha256": sha256_file(ROOT / GATE_STATE_REF),
            "implementation_commit_sha": gate["implementation_commit_sha"],
            "implementation_public_ci_run_id": gate["public_ci_run_id"],
            "gate_state_commit_sha": state["gate_state_commit_sha"],
            "gate_state_public_ci_run_id": state["public_ci_run_id"],
        },
        "checks": checks,
        "diagnostic_id": ATTEMPT_ID,
        "assertions": {
            "diagnostic_process_started": False,
            "arcpy_imported": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "attempt_root_current_presence_observed": False,
            "apply_orbit_correction_invoked": False,
            "geoprocessing_invoked": False,
            "attempt_root_reconstructed_or_substituted": False,
            "new_radar_attempt_created": False,
            "historical_root_cause_established": False,
            "radar_recovery_readiness_established": False,
            "scientific_result_established": False,
        },
        "next_action": "Run the one exact read-only input-resolution diagnostic once in the ArcGIS Pro Python environment; never retry it.",
    }


def run_final_preflight(checked_at_utc: str) -> int:
    receipt = build_final_preflight(checked_at_utc)
    write_new_json(ROOT / FINAL_PREFLIGHT_REF, receipt)
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


def execute_diagnostic(
    executed_at_utc: str,
    *,
    arcpy_loader: Callable[[], Any] = _load_arcpy,
    paths_override: dict[str, Path] | None = None,
) -> int:
    gate = implementation_publication_gate()
    state = gate_state_publication()
    preflight_path = ROOT / FINAL_PREFLIGHT_REF
    if not preflight_path.is_file():
        raise DiagnosticError("final_preflight_missing")
    preflight = load_object(preflight_path)
    if (
        preflight.get("status") != "pass_final_no_content_preflight_one_read_only_diagnostic_released"
        or preflight.get("bindings", {}).get("implementation_publication_gate_sha256") != sha256_file(ROOT / IMPLEMENTATION_GATE_REF)
        or preflight.get("bindings", {}).get("gate_state_publication_sha256") != sha256_file(ROOT / GATE_STATE_REF)
        or preflight.get("diagnostic_id") != ATTEMPT_ID
    ):
        raise DiagnosticError("final_preflight_not_exact_pass")
    contract = load_contract(ROOT)
    if (ROOT / TERMINAL_REF).exists() or (ROOT / CLEANUP_REF).exists():
        raise DiagnosticError("diagnostic_receipt_collision")

    terminal_handle = reserve_output(ROOT / TERMINAL_REF)
    cleanup_handle = reserve_output(ROOT / CLEANUP_REF)
    paths = paths_override if paths_override is not None else external_paths(contract)
    replacements = tuple(paths.values())
    filesystem: dict[str, Any] | None = None
    arcgis: dict[str, Any] | None = None
    protected: dict[str, str] | None = None
    project_data_content_read = False
    external_custody_accessed = False
    failure: BaseException | None = None
    try:
        protected = protected_evidence_bindings(contract)
        project_data_content_read = True
        filesystem = filesystem_observations(paths, contract)
        external_custody_accessed = True
        arcpy = arcpy_loader()
        arcgis = arcpy_observations(arcpy, paths)
    except BaseException as exc:
        failure = exc
        if getattr(exc, "code", "") in {
            "exact_orbit_candidate_missing",
            "exact_orbit_identity_mismatch",
        }:
            external_custody_accessed = True

    if failure is None:
        status = "pass_current_input_resolution_diagnostic_only"
        disposition = "pass_diagnostic_only"
    elif getattr(failure, "code", "").endswith("_missing"):
        status = "block_missing_exact_input_no_retry"
        disposition = "block"
    else:
        status = "block_read_only_diagnostic_failure_no_retry"
        disposition = "block"
    terminal: dict[str, Any] = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-TERMINAL",
        "status": status,
        "disposition": disposition,
        "started_at_utc": executed_at_utc,
        "completed_at_utc": now_utc(),
        "diagnostic_id": ATTEMPT_ID,
        "bindings": {
            **repository_bindings(),
            "implementation_commit_sha": gate["implementation_commit_sha"],
            "implementation_public_ci_run_id": gate["public_ci_run_id"],
            "gate_state_commit_sha": state["gate_state_commit_sha"],
            "gate_state_public_ci_run_id": state["public_ci_run_id"],
            "implementation_publication_gate_sha256": sha256_file(ROOT / IMPLEMENTATION_GATE_REF),
            "gate_state_publication_sha256": sha256_file(ROOT / GATE_STATE_REF),
            "final_preflight_sha256": sha256_file(preflight_path),
        },
        "protected_public_evidence": protected,
        "filesystem_observations": filesystem,
        "arcgis_observations": arcgis,
        "assertions": {
            "diagnostic_process_consumed": True,
            "automatic_retry_performed": False,
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
    if failure is not None:
        terminal.update(safe_error(failure, replacements))
    persist_reserved(terminal_handle, terminal)
    cleanup = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-CLEANUP",
        "status": "pass_no_payload_or_temporary_artifact_cleanup_required",
        "completed_at_utc": now_utc(),
        "diagnostic_id": ATTEMPT_ID,
        "terminal_sha256": sha256_file(ROOT / TERMINAL_REF),
        "assertions": {
            "temporary_payload_created": False,
            "source_orbit_or_dem_copied": False,
            "source_orbit_or_dem_mutated": False,
            "derived_raster_created": False,
            "external_cleanup_attempted": False,
        },
    }
    persist_reserved(cleanup_handle, cleanup)
    print(json.dumps({"status": status, "diagnostic_id": ATTEMPT_ID, "cleanup_status": cleanup["status"]}, indent=2))
    return 0 if failure is None else 20


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
    return execute_diagnostic(timestamp)


if __name__ == "__main__":
    raise SystemExit(main())
