#!/usr/bin/env python3
"""One append-only offline recovery supervisor; no network or credentials."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any, Callable

from m2_optical_pair_header_recovery_001_core import (
    ATTEMPT_ROOT, FINAL_PREFLIGHT, HEADER_RECEIPT, PIXEL_RECEIPT, PUBLIC_TERMINAL,
    ROOT, PilotControlError, exact_sources, now_utc, read_json, require_execution_release,
    sha256_file, write_new_json,
)
from m2_optical_pair_header_recovery_001_preflight import ARCGIS_PYTHON, inventory_materialized


SENSITIVE_ENV_KEY = re.compile(r"TOKEN|SECRET|PASSWORD|AUTHORIZATION|CREDENTIAL|API[_-]?KEY|CDSE", re.I)
WORKER = ROOT / "scripts/m2_optical_pair_header_recovery_001_worker.py"
def safe_error_class(value: Any) -> str | None:
    allowed = {"PilotControlError", "OSError", "FileNotFoundError", "PermissionError",
               "ImportError", "ModuleNotFoundError", "RuntimeError", "ValueError",
               "TypeError", "AttributeError", "KeyError", "MemoryError", "KeyboardInterrupt",
               "SystemExit", "Exception"}
    return value if value in allowed else None


def safe_control_code(value: Any) -> str | None:
    if isinstance(value, str) and re.fullmatch(r"(?:pilot|recovery)_[a-z0-9_]{3,72}", value):
        return value
    return None


def fixed_status(value: Any, allowed: set[str]) -> str | None:
    return value if isinstance(value, str) and value in allowed else None


def child_environment(source: dict[str, str]) -> dict[str, str]:
    return {key: value for key, value in source.items() if not SENSITIVE_ENV_KEY.search(key)}


def safe_aoi_dispositions(pixel: dict[str, Any]) -> dict[str, str]:
    allowed = {"pass_qa_only", "block", "defer", "invalid"}
    results = pixel.get("aoi_metrics", [])
    mapping = {item.get("aoi_id"): item.get("status") for item in results if isinstance(item, dict)}
    expected = ("AOI-OVERVIEW", "AOI-SOURCE", "AOI-UPPER-CORRIDOR")
    if len(results) != 3 or set(mapping) != set(expected) or any(mapping[key] not in allowed for key in expected):
        return {}
    return {key: mapping[key] for key in expected}


def terminal_from_child(exit_code: int | None) -> dict[str, Any]:
    child_path = ATTEMPT_ROOT / "worker-terminal.json"
    try:
        child = read_json(child_path) if child_path.is_file() else {}
    except (OSError, ValueError, UnicodeError):
        child = {}
    phase = child.get("stage") if child.get("stage") in {
        "child_bootstrap", "project_imports", "execution_release", "arcpy_import", "header", "pixel_qa"
    } else "child_no_terminal_receipt"
    result: dict[str, Any] = {
        "schema_version": "1.0", "receipt_id": "NEPAL-M2-OPTICAL-PAIR-HEADER-RECEIPT-RECOVERY-001-TERMINAL",
        "status": "stopped", "stage": phase, "completed_at_utc": now_utc(),
        "child_exit_code": exit_code if isinstance(exit_code, int) and -1000 < exit_code < 1000 else None,
        "child_terminal_receipt_present": bool(child),
        "header_receipt_present": HEADER_RECEIPT.is_file(),
        "pixel_receipt_present": PIXEL_RECEIPT.is_file(),
        "error_class": safe_error_class(child.get("error_class")), "safe_code": safe_control_code(child.get("safe_code")),
        "header_status": fixed_status(child.get("header_status"), {"pass_header_readability_only", "block"}),
        "pixel_status": fixed_status(child.get("pixel_status"), {"pass_qa_only", "block", "defer", "invalid"}),
        "aoi_dispositions": {}, "exception_text_recorded": False,
        "network_or_credential_action": False, "automatic_retry": False,
        "original_pilot_reused_or_mutated": False,
        "baseline_or_change_analysis": False, "interpretation_or_attribution": False,
        "derived_pixel_or_scientific_publication": False,
    }
    if HEADER_RECEIPT.is_file():
        try:
            header = read_json(HEADER_RECEIPT)
            result["header_status"] = fixed_status(header.get("status"), {"pass_header_readability_only", "block"}) or "invalid_receipt"
            result["header_sha256"] = sha256_file(HEADER_RECEIPT)
        except (OSError, ValueError, UnicodeError):
            result["header_status"] = "invalid_receipt"
    if PIXEL_RECEIPT.is_file():
        try:
            pixel = read_json(PIXEL_RECEIPT)
            result["pixel_status"] = fixed_status(pixel.get("status"), {"pass_qa_only", "block", "defer", "invalid"}) or "invalid_receipt"
            result["pixel_receipt_sha256"] = sha256_file(PIXEL_RECEIPT)
            result["aoi_dispositions"] = safe_aoi_dispositions(pixel)
        except (OSError, ValueError, UnicodeError):
            result["pixel_status"] = "invalid_receipt"
    if (exit_code == 0 and child.get("status") == "completed_qa_evaluation"
            and result["header_status"] == "pass_header_readability_only"
            and result["pixel_status"] in {"pass_qa_only", "block", "defer", "invalid"}
            and result["aoi_dispositions"]):
        result["status"] = "completed_qa_evaluation"
        result["stage"] = "pixel_qa"
    return result


def run_once(*, runner: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    proposal = require_execution_release()
    if ATTEMPT_ROOT.exists() or PUBLIC_TERMINAL.exists():
        raise PilotControlError("recovery_attempt_consumed_or_collision")
    preflight = read_json(FINAL_PREFLIGHT)
    sources, reviewed = exact_sources(), proposal["exact_existing_inputs"]
    identities = preflight.get("sources_in_order")
    if (not isinstance(identities, list) or len(identities) != 2
            or [item.get("source_id") for item in identities if isinstance(item, dict)] != ["M2-OPT-001", "M2-OPT-002"]
            or any(item.get("archive_sha256") != bound["verified_archive_sha256"]
                   or item.get("manifest_sha256") != bound["materialization_manifest_sha256"]
                   for item, bound in zip(identities, reviewed, strict=True))
            or preflight.get("arcgis_runtime") != {"version": "3.7.1", "spatial": "Available"}):
        raise PilotControlError("recovery_final_preflight_identity_drift")
    # No project data is read by the supervisor before the fresh attempt is reserved.
    ATTEMPT_ROOT.mkdir(parents=True, exist_ok=False)
    write_new_json(ATTEMPT_ROOT / "started.json", {
        "status": "started", "at_utc": now_utc(), "attempt_id": "real-001",
        "source_ids_in_order": ["M2-OPT-001", "M2-OPT-002"], "automatic_retry": False,
    })
    write_new_json(ATTEMPT_ROOT / "terminal-reserved.json", {
        "status": "reserved", "at_utc": now_utc(), "terminal_ref": "terminal.json",
    })
    write_new_json(ATTEMPT_ROOT / "cleanup-reserved.json", {
        "status": "reserved", "at_utc": now_utc(), "cleanup_ref": "cleanup.json",
    })
    write_new_json(ATTEMPT_ROOT / "stage-plan.json", {
        "status": "reserved", "at_utc": now_utc(),
        "stages_in_order": ["child_bootstrap", "project_imports", "execution_release", "arcpy_import", "header", "pixel_qa"],
        "pixel_qa_conditional_on_header_pass": True,
    })
    exit_code: int | None = None
    terminal: dict[str, Any]
    try:
        write_new_json(ATTEMPT_ROOT / "spawn-reserved.json", {"status": "reserved", "at_utc": now_utc()})
        process = runner(
            [str(ARCGIS_PYTHON), str(WORKER), "--real"], cwd=ROOT,
            env=child_environment(dict(os.environ)), stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
        )
        exit_code = int(process.returncode)
        terminal = terminal_from_child(exit_code)
    except BaseException as exc:
        terminal = terminal_from_child(exit_code)
        terminal["status"] = "stopped"
        terminal["stage"] = "supervisor_spawn_or_receipt"
        terminal["error_class"] = type(exc).__name__ if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,79}", type(exc).__name__) else "unsafe_error_class"
    cleanup: dict[str, Any] = {
        "schema_version": "1.0", "status": "indeterminate", "at_utc": now_utc(),
        "source_materializations_unchanged": False, "exception_text_recorded": False,
        "network_or_credential_action": False, "deletion_or_overwrite_performed": False,
    }
    try:
        after = [inventory_materialized(source, bound) for source, bound in zip(sources, reviewed, strict=True)]
        before = preflight["sources_in_order"]
        cleanup["source_materializations_unchanged"] = after == before
        cleanup["status"] = "pass_preserved_inputs" if after == before else "block_input_identity_drift"
    except BaseException as exc:
        cleanup["status"] = "indeterminate_input_verification"
        cleanup["error_class"] = type(exc).__name__
    if cleanup["status"] != "pass_preserved_inputs":
        terminal["status"] = "stopped"
        terminal["stage"] = "cleanup_or_input_identity"
    persistence_errors: list[str] = []
    try:
        write_new_json(ATTEMPT_ROOT / "terminal.json", terminal)
    except BaseException:
        persistence_errors.append("terminal")
    try:
        write_new_json(ATTEMPT_ROOT / "cleanup.json", cleanup)
    except BaseException:
        persistence_errors.append("cleanup")
    public = {key: value for key, value in terminal.items() if key not in {"header_sha256", "pixel_receipt_sha256"}}
    if persistence_errors:
        public["status"] = "stopped"
        public["stage"] = "receipt_persistence"
    public["non_git_terminal_sha256"] = sha256_file(ATTEMPT_ROOT / "terminal.json") if (ATTEMPT_ROOT / "terminal.json").is_file() else None
    public["cleanup_status"] = cleanup["status"]
    public["receipt_persistence_errors"] = persistence_errors
    public["early_custody_read_observation_ref"] = "records/readiness/m2-optical-pair-header-receipt-recovery-001-early-custody-read-observation.json"
    write_new_json(PUBLIC_TERMINAL, public)
    return public


if __name__ == "__main__":
    try:
        result = run_once()
        print(result["status"])
        raise SystemExit(0 if result["status"] == "completed_qa_evaluation" else 20)
    except PilotControlError as exc:
        print(exc.code)
        raise SystemExit(20)
