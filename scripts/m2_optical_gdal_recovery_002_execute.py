#!/usr/bin/env python3
"""Independent one-attempt GDAL supervisor with reserved durable receipts."""

from __future__ import annotations

import os
import re
import subprocess
from typing import Any, Callable

from m2_optical_gdal_recovery_002_core import (
    ATTEMPT_ROOT, FINAL_PREFLIGHT, HEADER_RECEIPT, PIXEL_RECEIPT, PUBLIC_TERMINAL,
    ROOT, PilotControlError, exact_sources, now_utc, read_json,
    require_execution_release, sha256_file, write_new_json,
)
from m2_optical_gdal_recovery_002_preflight import ARCGIS_PYTHON, inventory_materialized


WORKER = ROOT / "scripts/m2_optical_gdal_recovery_002_worker.py"
SENSITIVE_KEY = re.compile(r"TOKEN|SECRET|PASSWORD|AUTHORIZATION|CREDENTIAL|API[_-]?KEY|CDSE", re.I)
STAGES = {"child_bootstrap", "project_imports", "execution_release", "gdal_import",
          "header", "pixel_qa", "child_no_terminal_receipt", "supervisor_spawn_or_receipt",
          "cleanup_or_input_identity", "receipt_persistence"}
STATUSES = {"pass_qa_only", "block", "defer", "invalid"}
AOI_IDS = ("AOI-SOURCE", "AOI-UPPER-CORRIDOR", "AOI-OVERVIEW")


def child_environment(source: dict[str, str]) -> dict[str, str]:
    return {key: value for key, value in source.items() if not SENSITIVE_KEY.search(key)}


def safe_error_class(value: Any) -> str | None:
    allowed = {"PilotControlError", "OSError", "FileNotFoundError", "PermissionError",
               "ImportError", "ModuleNotFoundError", "RuntimeError", "ValueError",
               "TypeError", "AttributeError", "KeyError", "MemoryError", "Exception"}
    return value if value in allowed else None


def safe_aoi_dispositions(receipt: dict[str, Any]) -> dict[str, str]:
    metrics = receipt.get("aoi_metrics", [])
    if not isinstance(metrics, list) or len(metrics) != 3:
        return {}
    mapping = {item.get("aoi_id"): item.get("status") for item in metrics if isinstance(item, dict)}
    if set(mapping) != set(AOI_IDS) or any(mapping[key] not in STATUSES for key in AOI_IDS):
        return {}
    return {key: mapping[key] for key in AOI_IDS}


def terminal_from_child(exit_code: int | None) -> dict[str, Any]:
    try:
        child = read_json(ATTEMPT_ROOT / "worker-terminal.json")
    except (OSError, ValueError, UnicodeError):
        child = {}
    stage = child.get("stage") if child.get("stage") in STAGES else "child_no_terminal_receipt"
    terminal: dict[str, Any] = {
        "schema_version": "1.0", "receipt_id": "NEPAL-M2-OPTICAL-GDAL-RECOVERY-002-TERMINAL",
        "status": "stopped", "stage": stage, "completed_at_utc": now_utc(),
        "child_exit_code": exit_code if isinstance(exit_code, int) and -1000 < exit_code < 1000 else None,
        "child_terminal_receipt_present": bool(child),
        "header_receipt_present": HEADER_RECEIPT.is_file(),
        "pixel_receipt_present": PIXEL_RECEIPT.is_file(),
        "error_class": safe_error_class(child.get("error_class")),
        "safe_code": child.get("safe_code") if isinstance(child.get("safe_code"), str)
                     and re.fullmatch(r"[a-z0-9_]{3,96}", child["safe_code"]) else None,
        "header_status": None, "pixel_status": None, "aoi_dispositions": {},
        "exception_text_recorded": False, "network_or_credential_action": False,
        "automatic_retry": False, "arcpy_imported": False,
        "old_attempt_reused_or_mutated": False, "baseline_or_change_analysis": False,
        "derived_pixel_or_scientific_publication": False,
    }
    if HEADER_RECEIPT.is_file():
        try:
            header = read_json(HEADER_RECEIPT)
            terminal["header_status"] = header.get("status") if header.get("status") in {
                "pass_header_readability_only", "block"} else "invalid_receipt"
            terminal["header_sha256"] = sha256_file(HEADER_RECEIPT)
        except (OSError, ValueError, UnicodeError):
            terminal["header_status"] = "invalid_receipt"
    if PIXEL_RECEIPT.is_file():
        try:
            pixel = read_json(PIXEL_RECEIPT)
            terminal["pixel_status"] = pixel.get("status") if pixel.get("status") in STATUSES else "invalid_receipt"
            terminal["aoi_dispositions"] = safe_aoi_dispositions(pixel)
            terminal["pixel_receipt_sha256"] = sha256_file(PIXEL_RECEIPT)
        except (OSError, ValueError, UnicodeError):
            terminal["pixel_status"] = "invalid_receipt"
    if (exit_code == 0 and child.get("status") == "completed_qa_evaluation"
            and terminal["header_status"] == "pass_header_readability_only"
            and terminal["pixel_status"] in STATUSES and terminal["aoi_dispositions"]):
        terminal["status"] = "completed_qa_evaluation"
        terminal["stage"] = "pixel_qa"
    return terminal


def run_once(*, runner: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    require_execution_release()
    if ATTEMPT_ROOT.exists() or PUBLIC_TERMINAL.exists():
        raise PilotControlError("gdal_attempt_consumed_or_collision")
    preflight = read_json(FINAL_PREFLIGHT)
    sources = exact_sources()
    proposal = read_json(ROOT / "contracts/milestone-002-optical-gdal-header-pixel-recovery-002-proposal.json")
    reviewed = proposal["exact_existing_sources"]
    identities = preflight.get("sources_in_order")
    if (not isinstance(identities, list) or len(identities) != 2
            or [item.get("source_id") for item in identities] != ["M2-OPT-001", "M2-OPT-002"]
            or any(item.get("archive_sha256") != bound["archive_sha256"]
                   or item.get("manifest_sha256") != bound["materialization_manifest_sha256"]
                   for item, bound in zip(identities, reviewed, strict=True))
            or preflight.get("raster_pixel_values_decoded") is not False):
        raise PilotControlError("gdal_final_preflight_identity_drift")
    ATTEMPT_ROOT.mkdir(parents=True, exist_ok=False)
    try:
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
            "stages_in_order": ["child_bootstrap", "project_imports", "execution_release",
                                "gdal_import", "header", "pixel_qa"],
            "pixel_qa_conditional_on_both_headers_pass": True,
        })
    except BaseException as exc:
        # Root creation consumes this identity even when reservation stops. Keep
        # distinct best-effort evidence without ever launching the child.
        stopped = {
            "schema_version": "1.0", "receipt_id": "NEPAL-M2-OPTICAL-GDAL-RECOVERY-002-TERMINAL",
            "status": "stopped", "stage": "receipt_reservation", "completed_at_utc": now_utc(),
            "error_class": safe_error_class(type(exc).__name__),
            "child_exit_code": None, "child_terminal_receipt_present": False,
            "header_receipt_present": False, "pixel_receipt_present": False,
            "exception_text_recorded": False, "network_or_credential_action": False,
            "automatic_retry": False, "arcpy_imported": False,
            "old_attempt_reused_or_mutated": False, "baseline_or_change_analysis": False,
            "derived_pixel_or_scientific_publication": False,
            "cleanup_status": "not_run_no_child_spawned",
        }
        for name, value in (("reservation-failure.json", stopped),
                            ("terminal.json", stopped),
                            ("cleanup.json", {"status": "not_run_no_child_spawned",
                                              "at_utc": now_utc(), "source_mutation": False})):
            try:
                write_new_json(ATTEMPT_ROOT / name, value)
            except BaseException:
                pass
        stopped["non_git_terminal_sha256"] = sha256_file(ATTEMPT_ROOT / "terminal.json") if (ATTEMPT_ROOT / "terminal.json").is_file() else None
        write_new_json(PUBLIC_TERMINAL, stopped)
        return stopped
    exit_code: int | None = None
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
        terminal.update({"status": "stopped", "stage": "supervisor_spawn_or_receipt",
                         "error_class": safe_error_class(type(exc).__name__)})
    cleanup: dict[str, Any] = {
        "schema_version": "1.0", "status": "indeterminate", "at_utc": now_utc(),
        "source_materializations_unchanged": False, "exception_text_recorded": False,
        "network_or_credential_action": False, "deletion_or_overwrite_performed": False,
    }
    try:
        after = [inventory_materialized(source, {"verified_archive_sha256": bound["archive_sha256"],
                                                 "materialization_manifest_sha256": bound["materialization_manifest_sha256"]})
                 for source, bound in zip(sources, reviewed, strict=True)]
        cleanup["source_materializations_unchanged"] = after == identities
        cleanup["status"] = "pass_preserved_inputs" if after == identities else "block_input_identity_drift"
    except BaseException as exc:
        cleanup["status"] = "indeterminate_input_verification"
        cleanup["error_class"] = safe_error_class(type(exc).__name__)
    if cleanup["status"] != "pass_preserved_inputs":
        terminal.update({"status": "stopped", "stage": "cleanup_or_input_identity"})
    persistence_errors: list[str] = []
    for name, value in (("terminal.json", terminal), ("cleanup.json", cleanup)):
        try:
            write_new_json(ATTEMPT_ROOT / name, value)
        except BaseException:
            persistence_errors.append(name)
    public = {key: value for key, value in terminal.items()
              if key not in {"header_sha256", "pixel_receipt_sha256"}}
    if persistence_errors:
        public.update({"status": "stopped", "stage": "receipt_persistence"})
    public["non_git_terminal_sha256"] = sha256_file(ATTEMPT_ROOT / "terminal.json") if (ATTEMPT_ROOT / "terminal.json").is_file() else None
    public["cleanup_status"] = cleanup["status"]
    public["receipt_persistence_errors"] = persistence_errors
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
