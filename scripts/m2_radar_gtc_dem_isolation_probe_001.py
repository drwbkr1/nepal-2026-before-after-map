#!/usr/bin/env python3
"""One quarantined GTC call on the exact preserved gamma raster, without a DEM."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib
import inspect
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable

from m2_radar_esri_sequence_recovery_005_core import is_subst_drive, path_chain_has_reparse


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-gtc-dem-isolation-probe-001"
PROPOSAL_REF = f"contracts/milestone-002-radar-gtc-dem-isolation-probe-001-proposal.json"
BUNDLE_REF = f"reviews/{PREFIX}/review-bundle.json"
APPROVAL_REF = f"records/source-gates/{PREFIX}-approval.json"
IMPLEMENTATION_GATE_REF = f"records/readiness/{PREFIX}-implementation-publication-gate.json"
EXECUTION_GATE_REF = f"records/readiness/{PREFIX}-execution-publication-gate.json"
PREFLIGHT_REF = f"records/readiness/{PREFIX}-final-preflight.json"
RUNTIME_REF = f"records/readiness/{PREFIX}-arcgis-runtime-validation.json"
RUNNER_REF = f"scripts/{PREFIX.replace('-', '_')}.py"
VALIDATOR_REF = f"scripts/validate_{PREFIX.replace('-', '_')}_arcgis.py"
TEST_REF = f"tests/test_{PREFIX.replace('-', '_')}.py"
PROPOSAL_SHA = "2cac9f72dc21bcda9e0bdff571de681ad7efe5b4c0c86ac26a0c5fd4aea9f984"
BUNDLE_SHA = "e0438080c30e7073e94af012121b94db1c0cc193854cc43f7f5fc5339bdfe536"
SOURCE = Path(r"C:\Projects\Active\nepal-2026-before-after-map-data\r5\a1\s\1\gamma0_linear_despeckled.crf")
ATTEMPT_ROOT = Path(r"C:\Projects\Active\nepal-2026-before-after-map-data\r5\d2")
OUTPUT = ATTEMPT_ROOT / "gtc_no_dem_diagnostic.crf"
ATTEMPT_ID = "radar-gtc-dem-isolation-probe-001-real-001"
MIN_FREE_BYTES = 60 * 1024**3
GTC_PARAMETERS = ("in_radar_data", "polarization_bands", "in_dem_raster", "geoid")


class ProbeError(Exception):
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
        raise ProbeError("invalid_json_object")
    return value


def write_new_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def verified_authority() -> dict[str, Any]:
    if sha256(ROOT / PROPOSAL_REF) != PROPOSAL_SHA or sha256(ROOT / BUNDLE_REF) != BUNDLE_SHA:
        raise ProbeError("review_identity_mismatch")
    bundle = load_json(ROOT / BUNDLE_REF)
    if any(sha256(ROOT / item["path"]) != item["sha256"] for item in bundle["artifacts"]):
        raise ProbeError("frozen_evidence_drift")
    proposal = load_json(ROOT / PROPOSAL_REF)
    scope = proposal.get("proposed_single_authority_envelope", {})
    if (
        scope.get("attempt_id") != ATTEMPT_ID
        or scope.get("exact_input") != str(SOURCE)
        or scope.get("prospective_attempt_root") != str(ATTEMPT_ROOT)
        or scope.get("output_ref_within_attempt_root") != OUTPUT.name
        or scope.get("exact_call") != "arcpy.ia.ApplyGeometricTerrainCorrection(gamma_despeckled, 'VV;VH')"
        or scope.get("maximum_processes") != 1
        or scope.get("maximum_gtc_calls") != 1
        or scope.get("maximum_output_saves") != 1
        or scope.get("automatic_retry") is not False
        or scope.get("no_dem_and_no_geoid_argument") is not True
    ):
        raise ProbeError("proposal_scope_mismatch")
    approval = load_json(ROOT / APPROVAL_REF)
    if (
        approval.get("attestation") is not True
        or approval.get("human_decision_count") != 1
        or approval.get("bindings", {}).get("proposal_sha256") != PROPOSAL_SHA
        or approval.get("bindings", {}).get("review_bundle_sha256") != BUNDLE_SHA
        or approval.get("authorized_scope", {}).get("maximum_gtc_calls") != 1
        or approval.get("authorized_scope", {}).get("automatic_retry") is not False
    ):
        raise ProbeError("approval_scope_mismatch")
    return approval


def code_bindings() -> dict[str, str]:
    return {
        "approval_sha256": sha256(ROOT / APPROVAL_REF),
        "runner_sha256": sha256(ROOT / RUNNER_REF),
        "validator_sha256": sha256(ROOT / VALIDATOR_REF),
        "test_sha256": sha256(ROOT / TEST_REF),
        "runtime_validation_sha256": sha256(ROOT / RUNTIME_REF),
    }


def verified_gates() -> tuple[dict[str, Any], dict[str, Any]]:
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
        raise ProbeError("public_ci_gate_invalid")
    return implementation, execution


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def inspect_no_content(arcpy: Any) -> dict[str, Any]:
    target = arcpy.ia.ApplyGeometricTerrainCorrection
    signature = inspect.signature(target)
    if tuple(signature.parameters) != GTC_PARAMETERS:
        raise ProbeError("installed_gtc_signature_mismatch")
    if not hasattr(arcpy, "Raster") or not callable(arcpy.Raster):
        raise ProbeError("installed_raster_constructor_missing")
    if arcpy.CheckExtension("ImageAnalyst") != "Available":
        raise ProbeError("image_analyst_unavailable")
    install = arcpy.GetInstallInfo()
    return {"product": install.get("ProductName"), "version": install.get("Version"), "gtc_parameters": list(signature.parameters), "image_analyst": "Available"}


def no_content_paths() -> dict[str, int | bool]:
    if ATTEMPT_ROOT.exists() or OUTPUT.exists():
        raise ProbeError("attempt_root_collision")
    if not SOURCE.is_dir() or SOURCE.is_symlink():
        raise ProbeError("exact_preserved_input_missing_or_unsafe")
    if path_chain_has_reparse(SOURCE) or path_chain_has_reparse(ATTEMPT_ROOT) or is_subst_drive(ATTEMPT_ROOT):
        raise ProbeError("input_or_output_path_reparse_or_subst")
    if not ATTEMPT_ROOT.parent.is_dir():
        raise ProbeError("attempt_parent_missing")
    free = shutil.disk_usage(ATTEMPT_ROOT.parent).free
    if free < MIN_FREE_BYTES:
        raise ProbeError("insufficient_free_space")
    max_path = max(len(str(path)) for path in (SOURCE, ATTEMPT_ROOT / "terminal-reservation.json", OUTPUT))
    if max_path > 240:
        raise ProbeError("unsafe_path_length")
    return {"exact_input_present": True, "attempt_root_absent": True, "free_bytes": free, "minimum_free_bytes": MIN_FREE_BYTES, "maximum_path_characters": max_path}


def run_preflight(import_arcpy: Callable[[], Any] | None = None) -> dict[str, Any]:
    if (ROOT / PREFLIGHT_REF).exists():
        raise ProbeError("preflight_collision")
    verified_authority()
    implementation, execution = verified_gates()
    if git_head() != subprocess.check_output(["git", "rev-parse", "origin/main"], cwd=ROOT, text=True).strip():
        raise ProbeError("public_default_branch_not_current")
    if subprocess.run(["git", "merge-base", "--is-ancestor", execution["execution_commit_sha"], "HEAD"], cwd=ROOT).returncode:
        raise ProbeError("execution_commit_not_in_public_history")
    paths = no_content_paths()
    arcpy = import_arcpy() if import_arcpy is not None else importlib.import_module("arcpy")
    runtime = inspect_no_content(arcpy)
    receipt = {
        "schema_version": "1.0", "record_id": "NEPAL-M2-RADAR-GTC-DEM-ISOLATION-PROBE-001-FINAL-PREFLIGHT",
        "checked_at_utc": now_utc(), "status": "pass_final_no_content_preflight_one_attempt_ready",
        "attempt_id": ATTEMPT_ID,
        "bindings": {"approval_sha256": sha256(ROOT / APPROVAL_REF), "implementation_gate_sha256": sha256(ROOT / IMPLEMENTATION_GATE_REF), "execution_gate_sha256": sha256(ROOT / EXECUTION_GATE_REF), "public_head_sha": git_head()},
        "checks": paths, "runtime": runtime,
        "assertions": {"project_data_content_read": False, "arcpy_raster_constructed": False, "gtc_called": False, "attempt_root_created": False, "network_or_credentials_used": False},
    }
    write_new_json(ROOT / PREFLIGHT_REF, receipt)
    return receipt


def write_stage(root: Path, number: int, stage: str) -> None:
    write_new_json(root / f"stage-{number:03d}.json", {"at_utc": now_utc(), "attempt_id": ATTEMPT_ID, "stage": stage})


def run_probe(import_arcpy: Callable[[], Any] | None = None) -> dict[str, Any]:
    verified_authority()
    verified_gates()
    preflight = load_json(ROOT / PREFLIGHT_REF)
    if preflight.get("status") != "pass_final_no_content_preflight_one_attempt_ready":
        raise ProbeError("preflight_not_pass")
    if preflight.get("bindings", {}).get("execution_gate_sha256") != sha256(ROOT / EXECUTION_GATE_REF):
        raise ProbeError("preflight_gate_drift")
    no_content_paths()
    ATTEMPT_ROOT.mkdir(exist_ok=False)
    reserve = {"schema_version": "1.0", "attempt_id": ATTEMPT_ID, "reserved_at_utc": now_utc(), "status": "reserved_before_project_content_read", "preflight_sha256": sha256(ROOT / PREFLIGHT_REF)}
    write_new_json(ATTEMPT_ROOT / "terminal-reservation.json", reserve)
    write_new_json(ATTEMPT_ROOT / "cleanup-reservation.json", reserve)
    write_stage(ATTEMPT_ROOT, 0, "one_process_started")
    status = "block_unknown_failure_no_retry"
    error_type: str | None = None
    arcgis_error_code: str | None = None
    checked_out = False
    gtc_started = False
    gtc_returned = False
    save_started = False
    save_completed = False
    cleanup_status = "not_started"
    arcpy: Any = None
    try:
        arcpy = import_arcpy() if import_arcpy is not None else importlib.import_module("arcpy")
        inspect_no_content(arcpy)
        write_stage(ATTEMPT_ROOT, 1, "arcpy_and_signature_ready")
        if arcpy.CheckOutExtension("ImageAnalyst") != "CheckedOut":
            raise ProbeError("image_analyst_checkout_failed")
        checked_out = True
        arcpy.env.overwriteOutput = False
        arcpy.env.scratchWorkspace = str(ATTEMPT_ROOT)
        write_stage(ATTEMPT_ROOT, 2, "image_analyst_checked_out")
        gamma_despeckled = arcpy.Raster(str(SOURCE))
        write_stage(ATTEMPT_ROOT, 3, "exact_preserved_raster_constructed")
        write_stage(ATTEMPT_ROOT, 4, "gtc_call_started_no_dem")
        gtc_started = True
        corrected = arcpy.ia.ApplyGeometricTerrainCorrection(gamma_despeckled, 'VV;VH')
        write_stage(ATTEMPT_ROOT, 5, "gtc_returned")
        if corrected.__class__.__name__ != "Raster" or not callable(getattr(corrected, "save", None)):
            raise ProbeError("gtc_returned_non_raster")
        gtc_returned = True
        if OUTPUT.exists():
            raise ProbeError("output_collision_before_save")
        write_stage(ATTEMPT_ROOT, 6, "single_output_save_started")
        save_started = True
        corrected.save(str(OUTPUT))
        if not OUTPUT.exists():
            raise ProbeError("save_returned_without_output")
        save_completed = True
        write_stage(ATTEMPT_ROOT, 7, "single_output_save_completed")
        status = "pass_no_dem_gtc_diagnostic_only_output_quarantined"
    except BaseException as exc:
        error_type = type(exc).__name__
        if isinstance(exc, ProbeError):
            error_type = exc.code
        match = re.search(r"ERROR\s+(\d{6})\b", str(exc))
        arcgis_error_code = match.group(1) if match else None
        status = "block_no_dem_gtc_or_runtime_failure_no_retry"
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
            "schema_version": "1.0", "receipt_id": "NEPAL-M2-RADAR-GTC-DEM-ISOLATION-PROBE-001-TERMINAL",
            "attempt_id": ATTEMPT_ID, "recorded_at_utc": now_utc(), "status": status,
            "error_type_or_code": error_type, "arcgis_error_code": arcgis_error_code,
            "gtc_call_started": gtc_started, "gtc_returned_raster": gtc_returned,
            "output_save_started": save_started, "output_save_completed": save_completed,
            "output_exists": OUTPUT.exists(), "cleanup_status": cleanup_status,
            "assertions": {"attempt_consumed": True, "maximum_gtc_calls": 1, "dem_argument_supplied": False, "geoid_argument_supplied": False, "automatic_retry": False, "output_quarantined": True, "scientific_result_established": False, "historical_root_cause_established": False},
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
            terminal["status"] = "indeterminate_cleanup_persistence_failure_no_retry"
            with (ATTEMPT_ROOT / "fallback.jsonl").open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps({"at_utc": now_utc(), "stage": "cleanup_write_failed", "error_type": type(exc).__name__}) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
    return terminal


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("preflight", "execute"))
    args = parser.parse_args()
    result = run_preflight() if args.command == "preflight" else run_probe()
    print(json.dumps({"status": result["status"], "attempt_id": ATTEMPT_ID}))
    return 0 if result["status"].startswith("pass_") else 12


if __name__ == "__main__":
    raise SystemExit(main())
