#!/usr/bin/env python3
"""One-shot secret-filtered supervisor for the exact before-scene screen."""

from __future__ import annotations

import json
import math
import os
import subprocess
from typing import Any, Callable

from m2_optical_alternate_pair_002_control import (
    BEFORE_TERMINAL, EXECUTION_GATE, FINAL_PREFLIGHT, ROOT, PairControlError,
    attempt_path, child_environment, now_utc, read_json, require_public_ci,
    sha256_file, write_new_json,
)
from m2_optical_alternate_pair_002_preflight import ARCGIS_PYTHON


ATTEMPT = attempt_path("before_single_date_screen")
WORKER = ROOT / "scripts/m2_optical_alternate_pair_002_before_worker.py"
VALID_SCREEN = {"pass_acquisition_prerequisite_only", "block"}


def terminal_from_child(exit_code: int | None) -> dict[str, Any]:
    try:
        child = read_json(ATTEMPT / "worker-terminal.json")
    except (OSError, ValueError, UnicodeError):
        child = {}
    try:
        screen = read_json(ATTEMPT / "screen.json")
    except (OSError, ValueError, UnicodeError):
        screen = {}
    status = screen.get("status") if screen.get("status") in VALID_SCREEN else None
    aoi = screen.get("aoi_results")
    fractions = {}
    if isinstance(aoi, dict) and set(aoi) == {"AOI-SOURCE", "AOI-UPPER-CORRIDOR"}:
        for identifier, item in aoi.items():
            value = item.get("usable_fraction_of_aoi") if isinstance(item, dict) else None
            count = item.get("aoi_cell_count") if isinstance(item, dict) else None
            usable = item.get("usable_cell_count") if isinstance(item, dict) else None
            covered = item.get("covered_cell_count") if isinstance(item, dict) else None
            if (isinstance(value, (int, float)) and not isinstance(value, bool)
                    and isinstance(count, int) and not isinstance(count, bool)
                    and isinstance(usable, int) and not isinstance(usable, bool)
                    and isinstance(covered, int) and not isinstance(covered, bool)
                    and count > 0 and 0 <= usable <= covered <= count
                    and math.isclose(value, usable / count, abs_tol=1e-12)):
                fractions[identifier] = value
    completed = (exit_code == 0 and child.get("status") == "completed_single_date_screen"
                 and child.get("header_status") == "pass_single_source_header_only"
                 and screen.get("source_id") == "M2-OPT-001"
                 and screen.get("threshold") == .8
                 and screen.get("new_source_requested") is False
                 and screen.get("pair_pixel_qa_or_scientific_admission") is False
                 and status in VALID_SCREEN and len(fractions) == 2
                 and (status != "pass_acquisition_prerequisite_only"
                      or (screen.get("unknown_scl_present") is False
                          and all(value >= .8 for value in fractions.values()))))
    return {
        "schema_version": "1.0",
        "status": "completed_single_date_screen" if completed else "stopped",
        "stage": "pixel_screen" if completed else "child_or_receipt",
        "completed_at_utc": now_utc(),
        "child_exit_code": exit_code if isinstance(exit_code, int) and -1000 < exit_code < 1000 else None,
        "child_terminal_present": bool(child),
        "header_receipt_present": (ATTEMPT / "header.json").is_file(),
        "screen_receipt_present": bool(screen),
        "screen_status": status if completed else None,
        "target_aoi_usable_fractions": fractions if completed else {},
        "screen_receipt_sha256": sha256_file(ATTEMPT / "screen.json") if completed else None,
        "exception_text_recorded": False,
        "network_or_credential_action": False,
        "automatic_retry": False,
        "old_attempt_reused_or_mutated": False,
        "baseline_or_change_analysis": False,
        "derived_pixel_or_scientific_publication": False,
    }


def _safe_fallback(stage: str) -> dict[str, Any]:
    return {"schema_version": "1.0", "status": "stopped", "stage": stage,
            "completed_at_utc": now_utc(), "child_exit_code": None,
            "child_terminal_present": False, "header_receipt_present": False,
            "screen_receipt_present": False, "screen_status": None,
            "target_aoi_usable_fractions": {}, "exception_text_recorded": False,
            "network_or_credential_action": False, "automatic_retry": False,
            "old_attempt_reused_or_mutated": False,
            "baseline_or_change_analysis": False,
            "derived_pixel_or_scientific_publication": False}


def run_once(*, runner: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    require_public_ci()
    if ATTEMPT.exists() or BEFORE_TERMINAL.exists():
        raise PairControlError("pair_before_attempt_consumed_or_collision")
    preflight = read_json(FINAL_PREFLIGHT)
    if (preflight.get("status") != "pass_exact_no_payload_preflight_before_screen_only"
            or preflight.get("public_execution_gate_sha256") != sha256_file(EXECUTION_GATE)
            or not ARCGIS_PYTHON.is_file() or not WORKER.is_file()):
        raise PairControlError("pair_before_preflight_or_runtime_invalid")
    ATTEMPT.mkdir(parents=True, exist_ok=False)
    try:
        for name, payload in (
            ("started.json", {"status": "started", "attempt_id": ATTEMPT.name,
                              "started_at_utc": now_utc(), "automatic_retry": False}),
            ("terminal-reserved.json", {"status": "reserved", "terminal_ref": "terminal.json",
                                        "reserved_at_utc": now_utc()}),
            ("cleanup-reserved.json", {"status": "reserved", "cleanup_ref": "cleanup.json",
                                       "reserved_at_utc": now_utc()}),
            ("stage-plan.json", {"status": "reserved", "stages_in_order": [
                "child_bootstrap", "identity", "header", "pixel_screen"],
                                 "new_source_request": False}),
        ):
            write_new_json(ATTEMPT / name, payload)
    except BaseException:
        terminal = _safe_fallback("receipt_reservation")
        for name, value in (("reservation-failure.json", terminal),
                            ("terminal.json", terminal),
                            ("cleanup.json", {"status": "not_run_no_child_spawned",
                                              "at_utc": now_utc(), "source_mutation": False})):
            try:
                write_new_json(ATTEMPT / name, value)
            except BaseException:
                pass
        write_new_json(BEFORE_TERMINAL, terminal)
        return terminal
    terminal: dict[str, Any]
    try:
        write_new_json(ATTEMPT / "spawn-reserved.json", {"status": "reserved", "at_utc": now_utc()})
        process = runner([str(ARCGIS_PYTHON), str(WORKER)], cwd=ROOT,
                         env=child_environment(dict(os.environ)),
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, check=False,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                         if os.name == "nt" else 0)
        terminal = terminal_from_child(int(process.returncode))
    except BaseException:
        terminal = _safe_fallback("supervisor_spawn_or_receipt")
    try:
        write_new_json(ATTEMPT / "terminal.json", terminal)
    except BaseException:
        write_new_json(ATTEMPT / "terminal-fallback.json", _safe_fallback("terminal_persistence"))
        terminal = _safe_fallback("terminal_persistence")
    cleanup = {"status": "pass_no_temporary_payload_cleanup_required",
               "at_utc": now_utc(), "source_mutation": False,
               "automatic_retry": False}
    try:
        write_new_json(ATTEMPT / "cleanup.json", cleanup)
    except BaseException:
        terminal = _safe_fallback("cleanup_persistence")
    write_new_json(BEFORE_TERMINAL, terminal)
    return terminal


if __name__ == "__main__":
    try:
        result = run_once()
        print(json.dumps({"status": result["status"],
                          "screen_status": result.get("screen_status")}))
        raise SystemExit(0 if result["status"] == "completed_single_date_screen" else 20)
    except PairControlError as exc:
        print(json.dumps({"status": "stopped", "safe_code": exc.code,
                          "exception_text_recorded": False}))
        raise SystemExit(20)
