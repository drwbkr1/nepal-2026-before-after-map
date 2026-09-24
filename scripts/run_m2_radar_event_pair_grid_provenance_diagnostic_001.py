#!/usr/bin/env python3
"""One gated read-only inspection of exact preserved event-pair raster metadata."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from m2_radar_event_pair_grid_provenance_diagnostic_001_core import (
    APPROVAL, BUNDLE, DATA_ROOT, DiagnosticError, EXPECTED_BUNDLE_SHA256,
    EXPECTED_PROPOSAL_SHA256, OLD_ATTEMPT, PACKET_GATE, PREFIX, PROPOSAL,
    ROOT, SOURCE_ROOT, candidate_paths, check_authority,
    first_declared_coarse_stage, inspect_raster, load_json, persist, reserve,
    sha256_file, verify_gtc_configuration,
)


GATE = ROOT / "records" / "readiness" / f"{PREFIX}-implementation-publication-gate.json"
PREFLIGHT = ROOT / "records" / "readiness" / f"{PREFIX}-final-no-content-preflight.json"
PROCESSING = ROOT / "records" / "processing"
STARTED = PROCESSING / f"{PREFIX}-real-001-started.json"
TERMINAL = PROCESSING / f"{PREFIX}-real-001-terminal.json"
CLEANUP = PROCESSING / f"{PREFIX}-real-001-cleanup.json"
ERROR = PROCESSING / f"{PREFIX}-real-001-error.json"
CORE_REF = "scripts/m2_radar_event_pair_grid_provenance_diagnostic_001_core.py"
RUNNER_REF = "scripts/run_m2_radar_event_pair_grid_provenance_diagnostic_001.py"
VALIDATOR_REF = "scripts/validate_m2_radar_event_pair_grid_provenance_diagnostic_001_arcgis.py"
TEST_REF = "tests/test_m2_radar_event_pair_grid_provenance_diagnostic_001.py"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def expected_implementation_bindings() -> dict[str, str]:
    return {
        "proposal_sha256": EXPECTED_PROPOSAL_SHA256,
        "review_bundle_sha256": EXPECTED_BUNDLE_SHA256,
        "approval_sha256": sha256_file(APPROVAL),
        "packet_gate_sha256": sha256_file(PACKET_GATE),
        "core_sha256": sha256_file(ROOT / CORE_REF),
        "runner_sha256": sha256_file(ROOT / RUNNER_REF),
        "arcgis_validator_sha256": sha256_file(ROOT / VALIDATOR_REF),
        "synthetic_tests_sha256": sha256_file(ROOT / TEST_REF),
    }


def check_implementation_gate() -> dict[str, Any]:
    check_authority()
    gate = load_json(GATE)
    if gate.get("status") != "pass_public_default_branch_ci_diagnostic_implementation_only":
        raise DiagnosticError("implementation_gate_not_pass")
    if gate.get("public_ci_conclusion") != "success" or gate.get("bindings") != expected_implementation_bindings():
        raise DiagnosticError("implementation_gate_binding_drift")
    return gate


def no_content_preflight() -> dict[str, Any]:
    gate = check_implementation_gate()
    if any(path.exists() for path in (PREFLIGHT, STARTED, TERMINAL, CLEANUP, ERROR)):
        raise DiagnosticError("diagnostic_receipt_collision")
    if (DATA_ROOT / "e1" / "a2").exists():
        raise DiagnosticError("new_radar_attempt_root_unexpected")
    for name in ("terminal.json", "error.json", "cleanup.json"):
        path = OLD_ATTEMPT / name
        if not path.is_file() or path.stat().st_size != 0:
            raise DiagnosticError("old_reserved_receipt_identity_drift")
    if not SOURCE_ROOT.is_dir() or SOURCE_ROOT.is_symlink():
        raise DiagnosticError("exact_preserved_source_root_missing")
    for path in candidate_paths():
        if not path.is_dir() or path.is_symlink():
            raise DiagnosticError("exact_preserved_candidate_missing")
    record = {
        "schema_version": "1.0", "record_id": "NEPAL-M2-RADAR-EVENT-AREA-PAIR-GRID-PROVENANCE-DIAGNOSTIC-001-FINAL-NO-CONTENT-PREFLIGHT",
        "checked_at_utc": now_utc(), "status": "pass_no_content_preflight_metadata_diagnostic_only",
        "bindings": {"implementation_gate_sha256": sha256_file(GATE),
                     "implementation_commit_sha": gate["implementation_commit_sha"],
                     "proposal_sha256": sha256_file(PROPOSAL), "review_bundle_sha256": sha256_file(BUNDLE)},
        "assertions": {"old_reserved_receipts_zero_bytes": True, "five_exact_candidates_present": True,
                       "new_e1_a2_attempt_root_absent": True, "diagnostic_receipt_collision": False,
                       "raster_or_configuration_content_read": False, "arcgis_invoked": False},
    }
    stream = reserve(PREFLIGHT)
    persist(stream, record)
    return record


def _require_preflight() -> None:
    check_implementation_gate()
    receipt = load_json(PREFLIGHT)
    if receipt.get("status") != "pass_no_content_preflight_metadata_diagnostic_only":
        raise DiagnosticError("final_preflight_not_pass")
    if receipt.get("bindings", {}).get("implementation_gate_sha256") != sha256_file(GATE):
        raise DiagnosticError("final_preflight_gate_drift")
    if any(path.exists() for path in (STARTED, TERMINAL, CLEANUP, ERROR)):
        raise DiagnosticError("diagnostic_attempt_already_consumed")


def execute() -> dict[str, Any]:
    _require_preflight()
    handles = {"started": reserve(STARTED), "terminal": reserve(TERMINAL),
               "cleanup": reserve(CLEANUP), "error": reserve(ERROR)}
    started_at = now_utc()
    persist(handles["started"], {"schema_version": "1.0", "record_id": "NEPAL-M2-RADAR-EVENT-AREA-PAIR-GRID-PROVENANCE-DIAGNOSTIC-001-STARTED",
                                 "started_at_utc": started_at, "status": "started_read_only_metadata_diagnostic",
                                 "final_preflight_sha256": sha256_file(PREFLIGHT)})
    result: dict[str, Any] = {"status": "block_indeterminate_no_retry"}
    failure: dict[str, Any] | None = None
    try:
        import arcpy  # type: ignore

        records = []
        for path in candidate_paths():
            records.append(inspect_raster(arcpy, path))
        config = verify_gtc_configuration(SOURCE_ROOT / "gamma0_linear_gtc_raw.crf")
        result = {
            "status": "diagnostic_complete_metadata_only",
            "arcgis_version": arcpy.GetInstallInfo().get("Version"),
            "source_id": "M1-SRC-002", "raster_metadata": records,
            "saved_gtc_configuration": config,
            "first_declared_coarse_stage": first_declared_coarse_stage(records),
            "pixel_reads": 0, "geoprocessing_calls": 0, "raster_function_calls": 0,
            "source_qa_or_pixel_validity_established": False,
        }
    except Exception as exc:
        failure = {"failure_type": type(exc).__name__, "failure_code": getattr(exc, "code", "unexpected_diagnostic_failure")}
        result = {"status": "block_read_only_metadata_diagnostic_no_retry", "failure": failure,
                  "pixel_reads": 0, "geoprocessing_calls": 0, "raster_function_calls": 0}
    finally:
        if failure is not None:
            persist(handles["error"], {"schema_version": "1.0", "record_id": "NEPAL-M2-RADAR-EVENT-AREA-PAIR-GRID-PROVENANCE-DIAGNOSTIC-001-ERROR",
                                       "status": "sanitized_diagnostic_error", **failure})
        else:
            persist(handles["error"], {"schema_version": "1.0", "record_id": "NEPAL-M2-RADAR-EVENT-AREA-PAIR-GRID-PROVENANCE-DIAGNOSTIC-001-ERROR",
                                       "status": "no_error"})
        persist(handles["terminal"], {"schema_version": "1.0", "record_id": "NEPAL-M2-RADAR-EVENT-AREA-PAIR-GRID-PROVENANCE-DIAGNOSTIC-001-TERMINAL",
                                      "started_at_utc": started_at, "ended_at_utc": now_utc(), **result})
        persist(handles["cleanup"], {"schema_version": "1.0", "record_id": "NEPAL-M2-RADAR-EVENT-AREA-PAIR-GRID-PROVENANCE-DIAGNOSTIC-001-CLEANUP",
                                     "status": "pass_read_only_no_temporary_payload_created", "completed_at_utc": now_utc(),
                                     "write_calls_to_preserved_attempt": 0,
                                     "post_process_external_inventory_comparison_performed": False,
                                     "new_radar_attempt_started": False})
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preflight", "run"), required=True)
    args = parser.parse_args()
    try:
        outcome = no_content_preflight() if args.mode == "preflight" else execute()
    except Exception as exc:
        outcome = {"status": "block_before_raster_metadata_access", "failure_type": type(exc).__name__,
                   "failure_code": getattr(exc, "code", "unexpected_preflight_failure")}
    print(json.dumps({"status": outcome["status"]}, sort_keys=True))
    return 0 if outcome["status"] in {"pass_no_content_preflight_metadata_diagnostic_only", "diagnostic_complete_metadata_only"} else 20


if __name__ == "__main__":
    raise SystemExit(main())
