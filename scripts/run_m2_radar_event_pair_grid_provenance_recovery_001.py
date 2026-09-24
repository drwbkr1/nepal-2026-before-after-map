#!/usr/bin/env python3
"""One distinct, durable, read-only metadata recovery over five frozen CRFs."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO

from m2_radar_event_pair_grid_provenance_recovery_001_core import (
    APPROVAL, BUNDLE, DATA_ROOT, DiagnosticError, NAMES, OLD_ATTEMPT,
    PACKET_GATE, PREFIX, PROPOSAL, ROOT, SOURCE_ROOT, append_stage,
    candidate_paths, check_authority, first_declared_coarse_stage,
    inspect_raster, inventory_gtc_configuration, load_json, reserve, sha256_file,
)

GATE = ROOT / "records" / "readiness" / f"{PREFIX}-implementation-publication-gate.json"
EXECUTION_GATE = ROOT / "records" / "readiness" / f"{PREFIX}-execution-publication-gate.json"
PREFLIGHT = ROOT / "records" / "readiness" / f"{PREFIX}-final-no-content-preflight.json"
PROCESSING = ROOT / "records" / "processing"
RECEIPTS = {name: PROCESSING / f"{PREFIX}-real-001-{name}.json" for name in
            ("started", "terminal", "cleanup", "error", "fallback-error")}
RECEIPTS["stage-journal"] = PROCESSING / f"{PREFIX}-real-001-stage-journal.jsonl"
IMPLEMENTATION_REFS = (
    "scripts/m2_radar_event_pair_grid_provenance_recovery_001_core.py",
    "scripts/run_m2_radar_event_pair_grid_provenance_recovery_001.py",
    "scripts/validate_m2_radar_event_pair_grid_provenance_recovery_001_arcgis.py",
    "tests/test_m2_radar_event_pair_grid_provenance_recovery_001.py",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_once(stream: BinaryIO, value: dict[str, Any]) -> None:
    stream.write((json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8"))
    stream.flush()
    import os
    os.fsync(stream.fileno())
    stream.close()


def _bindings() -> dict[str, str]:
    return {
        "proposal_sha256": sha256_file(PROPOSAL),
        "review_bundle_sha256": sha256_file(BUNDLE),
        "approval_sha256": sha256_file(APPROVAL),
        "packet_gate_sha256": sha256_file(PACKET_GATE),
        **{Path(ref).stem + "_sha256": sha256_file(ROOT / ref) for ref in IMPLEMENTATION_REFS},
    }


def check_implementation_gate() -> dict[str, Any]:
    check_authority()
    gate = load_json(GATE)
    if (gate.get("status") != "pass_public_default_branch_ci_read_only_recovery_implementation"
            or gate.get("public_ci_conclusion") != "success"
            or gate.get("bindings") != _bindings()):
        raise DiagnosticError("implementation_gate_not_pass_or_drift")
    return gate


def check_execution_gate() -> dict[str, Any]:
    implementation = check_implementation_gate()
    gate = load_json(EXECUTION_GATE)
    if (gate.get("status") != "pass_public_default_branch_ci_read_only_recovery_execution"
            or gate.get("public_ci_conclusion") != "success"
            or gate.get("bindings", {}).get("implementation_gate_sha256") != sha256_file(GATE)
            or gate.get("bindings", {}).get("implementation_commit_sha") != implementation.get("implementation_commit_sha")):
        raise DiagnosticError("execution_gate_not_pass_or_drift")
    return gate


def _no_content_checks() -> None:
    if any(path.exists() for path in RECEIPTS.values()) or PREFLIGHT.exists():
        raise DiagnosticError("recovery_receipt_collision")
    if (DATA_ROOT / "e1" / "a2").exists():
        raise DiagnosticError("new_radar_attempt_root_unexpected")
    for name in ("terminal", "cleanup"):
        old = ROOT / "records" / "processing" / f"m2-radar-event-area-pair-grid-provenance-diagnostic-001-real-001-{name}.json"
        if not old.is_file() or old.stat().st_size != 0:
            raise DiagnosticError("old_diagnostic_zero_byte_receipt_drift")
    for name in ("terminal.json", "error.json", "cleanup.json"):
        old = OLD_ATTEMPT / name
        if not old.is_file() or old.stat().st_size != 0:
            raise DiagnosticError("old_radar_receipt_drift")
    if not SOURCE_ROOT.is_dir() or SOURCE_ROOT.is_symlink():
        raise DiagnosticError("exact_preserved_source_root_missing")
    for path in candidate_paths():
        if path.parent != SOURCE_ROOT or path.name not in NAMES or not path.is_dir() or path.is_symlink():
            raise DiagnosticError("exact_preserved_candidate_missing")
        if path.resolve() != SOURCE_ROOT.resolve() / path.name:
            raise DiagnosticError("exact_preserved_candidate_escape")


def no_content_preflight() -> dict[str, Any]:
    gate = check_execution_gate()
    _no_content_checks()
    record = {
        "schema_version": "1.0", "record_id": "NEPAL-M2-RADAR-EVENT-AREA-PAIR-GRID-PROVENANCE-RECOVERY-001-FINAL-NO-CONTENT-PREFLIGHT",
        "status": "pass_no_content_read_only_recovery_preflight", "checked_at_utc": now_utc(),
        "bindings": {"execution_gate_sha256": sha256_file(EXECUTION_GATE),
                     "execution_commit_sha": gate["execution_commit_sha"]},
        "assertions": {"exact_five_crf_paths_present": True,
                       "old_zero_byte_receipts_unchanged": True,
                       "new_receipt_identities_absent": True, "e1_a2_absent": True,
                       "preserved_content_read": False, "arcpy_invoked": False},
    }
    stream = reserve(PREFLIGHT)
    _write_once(stream, record)
    return record


def _require_preflight() -> None:
    check_execution_gate()
    preflight = load_json(PREFLIGHT)
    if (preflight.get("status") != "pass_no_content_read_only_recovery_preflight"
            or preflight.get("bindings", {}).get("execution_gate_sha256") != sha256_file(EXECUTION_GATE)):
        raise DiagnosticError("final_preflight_not_pass_or_drift")
    if any(path.exists() for path in RECEIPTS.values()):
        raise DiagnosticError("recovery_process_already_consumed")


def _safe_write(stream: BinaryIO, value: dict[str, Any], name: str,
                errors: list[str]) -> None:
    try:
        _write_once(stream, value)
    except Exception:
        errors.append(f"{name}_persistence_failed")
    finally:
        if not stream.closed:
            stream.close()


def execute() -> dict[str, Any]:
    _require_preflight()
    handles: dict[str, BinaryIO] = {}
    try:
        for name in ("started", "stage-journal", "terminal", "cleanup", "error", "fallback-error"):
            handles[name] = reserve(RECEIPTS[name])
    except Exception:
        for stream in handles.values():
            stream.close()
        raise
    started_at = now_utc()
    errors: list[str] = []
    result: dict[str, Any] = {"status": "block_indeterminate_no_retry"}
    failure: dict[str, str] | None = None
    try:
        _write_once(handles["started"], {
            "schema_version": "1.0", "status": "started_read_only_metadata_recovery",
            "started_at_utc": started_at, "final_preflight_sha256": sha256_file(PREFLIGHT),
            "source_id": "M1-SRC-002", "raster_names_in_order": list(NAMES),
        })
        append_stage(handles["stage-journal"], {"stage": "started", "at_utc": started_at})
        import arcpy  # type: ignore
        records = []
        for path in candidate_paths():
            # The stage marker is durable before each ArcPy metadata read.
            append_stage(handles["stage-journal"], {"stage": "raster_metadata_started", "name": path.name})
            item = inspect_raster(arcpy, path)
            append_stage(handles["stage-journal"], {"stage": "raster_metadata_completed", **item})
            records.append(item)
        append_stage(handles["stage-journal"], {"stage": "configuration_inventory_started"})
        config = inventory_gtc_configuration(SOURCE_ROOT / "gamma0_linear_gtc_raw.crf")
        append_stage(handles["stage-journal"], {"stage": "configuration_inventory_completed", **config})
        result = {
            "status": ("diagnostic_complete_metadata_only" if config["historical_configuration_identity"] == "unique_match"
                       else "block_configuration_identity_unresolved_no_retry"),
            "arcgis_version": arcpy.GetInstallInfo().get("Version"),
            "source_id": "M1-SRC-002", "raster_metadata": records,
            "saved_gtc_configuration": config,
            "first_declared_coarse_stage": first_declared_coarse_stage(records),
            "pixel_reads": 0, "geoprocessing_calls": 0, "raster_function_calls": 0,
            "source_qa_or_pixel_validity_established": False,
        }
    except Exception as exc:
        failure = {"failure_type": type(exc).__name__,
                   "failure_code": getattr(exc, "code", "unexpected_read_only_recovery_failure")}
        result = {"status": "block_read_only_metadata_recovery_no_retry", "failure": failure,
                  "pixel_reads": 0, "geoprocessing_calls": 0, "raster_function_calls": 0}
    finally:
        handles["stage-journal"].close()
        _safe_write(handles["error"], {
            "schema_version": "1.0", "status": "sanitized_recovery_error" if failure else "no_error",
            **(failure or {}),
        }, "error", errors)
        _safe_write(handles["terminal"], {
            "schema_version": "1.0", "started_at_utc": started_at,
            "ended_at_utc": now_utc(), **result,
        }, "terminal", errors)
        _safe_write(handles["cleanup"], {
            "schema_version": "1.0", "status": "pass_read_only_no_temporary_payload_created",
            "completed_at_utc": now_utc(), "write_calls_to_preserved_attempt": 0,
            "new_radar_attempt_started": False,
        }, "cleanup", errors)
        if errors:
            _safe_write(handles["fallback-error"], {
                "schema_version": "1.0", "status": "receipt_persistence_failure_no_retry",
                "failure_codes": errors,
            }, "fallback-error", errors)
        else:
            handles["fallback-error"].close()
    if errors:
        return {"status": "block_receipt_persistence_no_retry", "failure_codes": errors}
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preflight", "run"), required=True)
    args = parser.parse_args()
    try:
        result = no_content_preflight() if args.mode == "preflight" else execute()
    except Exception as exc:
        result = {"status": "block_before_preserved_metadata_access",
                  "failure_type": type(exc).__name__,
                  "failure_code": getattr(exc, "code", "unexpected_preflight_failure")}
    print(json.dumps({"status": result["status"]}, sort_keys=True))
    return 0 if result["status"] in {"pass_no_content_read_only_recovery_preflight",
                                       "diagnostic_complete_metadata_only"} else 20


if __name__ == "__main__":
    raise SystemExit(main())
