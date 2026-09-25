#!/usr/bin/env python3
"""Single-use detached owner of the exact optical pilot sequence."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

from m2_optical_pair_pilot_001_core import PilotControlError, load_contract, require_execution_release
from m2_materialization_core import MaterializationError
from m2_optical_pair_pilot_001_offline import PILOT_ROOT, materialize_one
from m2_optical_pair_pilot_001_pixel import HEADER_RECEIPT, PUBLIC_RECEIPT
from m2_optical_pair_pilot_001_preflight import final_preflight
from m2_optical_pair_pilot_001_transfer import now_utc, one_transfer, read_json, write_new_json
from m2_sentinel_continuation_001_core import read_single_use_secret, sanitized_child_environment


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_TERMINAL = ROOT / "records/readiness/m2-optical-pair-pilot-001-terminal.json"
ARCGIS_PYTHON = Path(r"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe")


def arcgis_runtime(secret: str) -> dict[str, str]:
    if not ARCGIS_PYTHON.is_file():
        raise PilotControlError("pilot_arcgis_python_missing")
    command = [str(ARCGIS_PYTHON), "-c", "import arcpy,json; print(json.dumps({'version':arcpy.GetInstallInfo().get('Version',''),'spatial':arcpy.CheckExtension('Spatial')}))"]
    result = subprocess.run(
        command, cwd=ROOT, env=sanitized_child_environment(os.environ, secret),
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120, check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
    )
    if result.returncode != 0 or len(result.stdout) > 2048:
        raise PilotControlError("pilot_arcgis_runtime_probe_failed")
    try:
        value = json.loads(result.stdout.strip())
    except (ValueError, UnicodeError) as exc:
        raise PilotControlError("pilot_arcgis_runtime_probe_invalid") from exc
    if not isinstance(value, dict):
        raise PilotControlError("pilot_arcgis_runtime_probe_invalid")
    return {"version": str(value.get("version", "")), "spatial": str(value.get("spatial", ""))}


def run_arcgis_worker(secret: str) -> int:
    command = [str(ARCGIS_PYTHON), str(ROOT / "scripts/m2_optical_pair_pilot_001_arcgis_worker.py")]
    result = subprocess.run(
        command, cwd=ROOT, env=sanitized_child_environment(os.environ, secret),
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
    )
    return int(result.returncode)


def _terminal(status: str, stage: str, *, code: str | None = None, products: list[str] | None = None) -> dict[str, Any]:
    return {
        "schema_version": "1.0", "receipt_id": "NEPAL-M2-OPTICAL-PAIR-PILOT-001-TERMINAL",
        "status": status, "stage": stage, "terminal_code": code,
        "completed_at_utc": now_utc(), "promoted_product_source_ids": products or [],
        "credential_value_recorded": False, "account_response_or_pii_recorded": False,
        "exception_text_recorded": False, "automatic_source_substitution": False,
        "old_attempt_reused": False, "baseline_or_change_analysis": False,
        "interpretation_or_attribution": False, "derived_pixel_or_scientific_publication": False,
    }


def run_sequence(secret: str, *, journal: Path) -> dict[str, Any]:
    contract = load_contract()
    if contract.get("status") != "conditional_public_ci_and_final_preflight_pending":
        raise PilotControlError("pilot_contract_not_activated")
    sources = contract["sources_in_order"]
    runtime = arcgis_runtime(secret)
    completed: list[str] = []
    for source in sources:
        try:
            final_preflight(source, secret, arcgis_runtime=runtime)
            require_execution_release(source["source_id"])
        except PilotControlError as exc:
            return _terminal("stopped", "preflight", code=exc.code, products=completed)
        write_new_json(journal / f"{source['source_id'].casefold()}-preflight-complete.json", {
            "source_id": source["source_id"], "status": "pass_no_payload", "observed_at_utc": now_utc(),
            "credential_value_recorded": False,
        })
        for ordinal in (1, 2):
            result = one_transfer(source, secret, event_root=PILOT_ROOT)
            write_new_json(journal / f"{source['source_id'].casefold()}-request-{ordinal}-terminal.json", {
                "source_id": source["source_id"], "request_ordinal": ordinal,
                "status": result["status"], "attempt_id": result["attempt_id"],
                "observed_at_utc": now_utc(), "credential_value_recorded": False,
            })
            if result["status"] == "promoted_verified":
                completed.append(source["source_id"])
                break
            if result["status"] != "transport_interrupted":
                return _terminal("stopped", "transfer", code=result["status"], products=completed)
            if ordinal == 2:
                return _terminal("stopped", "transfer", code="pilot_transport_attempts_exhausted", products=completed)
    for source in sources:
        try:
            materialize_one(source)
        except (MaterializationError, PilotControlError) as exc:
            return _terminal("stopped", "materialization", code=exc.code, products=completed)
        write_new_json(journal / f"{source['source_id'].casefold()}-materialized.json", {
            "source_id": source["source_id"], "status": "complete", "observed_at_utc": now_utc(),
            "credential_value_recorded": False,
        })
    arcgis_exit = run_arcgis_worker(secret)
    if not HEADER_RECEIPT.is_file():
        return _terminal("stopped", "header", code="pilot_arcgis_worker_no_header_receipt", products=completed)
    header = read_json(HEADER_RECEIPT)
    if header["status"] != "pass_header_readability_only" or arcgis_exit not in (0, 20):
        return _terminal("stopped", "header", code="pilot_header_block", products=completed)
    if not PUBLIC_RECEIPT.is_file():
        return _terminal("stopped", "pixel_qa", code="pilot_pixel_receipt_missing", products=completed)
    pixel = read_json(PUBLIC_RECEIPT)
    result = _terminal("complete_qa_only", "pixel_qa", code=pixel["status"], products=completed)
    result["localized_source_corridor_status"] = pixel.get("localized_source_corridor_status")
    result["overview_full_coverage_claim"] = False
    result["pixel_receipt_ref"] = "records/readiness/optical-pixel/m2-optical-pair-pilot-001-pixel-qa.json"
    return result


def main() -> int:
    secret = read_single_use_secret(sys.stdin.buffer)
    run_id = f"pilot-{now_utc().replace(':', '').replace('-', '')}-{uuid.uuid4().hex[:8]}"
    journal = PILOT_ROOT / "supervisor" / run_id
    journal.mkdir(parents=True, exist_ok=False)
    write_new_json(journal / "started.json", {
        "run_id": run_id, "status": "started", "started_at_utc": now_utc(),
        "source_ids_in_order": ["M2-OPT-001", "M2-OPT-002"],
        "credential_value_recorded": False,
    })
    try:
        terminal = run_sequence(secret, journal=journal)
    except BaseException as exc:
        code = exc.code if isinstance(exc, PilotControlError) else "pilot_supervisor_unexpected_failure"
        terminal = _terminal("stopped", "supervisor", code=code)
    finally:
        secret = ""
    write_new_json(journal / "terminal.json", terminal)
    write_new_json(PUBLIC_TERMINAL, terminal)
    return 0 if terminal["status"] == "complete_qa_only" else 20


if __name__ == "__main__":
    raise SystemExit(main())
