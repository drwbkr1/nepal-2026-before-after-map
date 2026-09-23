#!/usr/bin/env python3
"""Reconcile the one DEM-supplied diagnostic without decoding its output pixels."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

import m2_radar_dem_fitness_comparison_001 as comparison


ROOT = Path(__file__).resolve().parents[1]
TERMINAL_REF = f"records/processing/{comparison.PREFIX}-terminal-reconciliation.json"
STAGES = (
    "one_process_started", "arcpy_interface_ready", "image_analyst_checked_out",
    "exact_inputs_and_aoi_constructed", "native_validity_audit_started",
    "native_validity_audit_persisted", "gtc_call_started_with_existing_dem",
    "gtc_returned", "single_output_save_started", "single_output_save_completed",
)


def inventory(directory: Path) -> tuple[int, int, str]:
    files = sorted((path for path in directory.rglob("*") if path.is_file()), key=lambda path: path.relative_to(directory).as_posix())
    rows = [[path.relative_to(directory).as_posix(), path.stat().st_size, comparison.sha256(path)] for path in files]
    digest = hashlib.sha256(json.dumps(rows, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
    return len(rows), sum(row[1] for row in rows), digest


def main() -> int:
    if (ROOT / TERMINAL_REF).exists():
        raise SystemExit("terminal reconciliation already exists")
    comparison.verify_authority()
    preflight = comparison.load_json(ROOT / comparison.PREFLIGHT_REF)
    if preflight.get("status") != "pass_final_no_content_preflight_one_attempt_ready":
        raise SystemExit("final preflight does not pass")
    attempt = comparison.ATTEMPT_ROOT
    if not attempt.is_dir():
        raise SystemExit("exact attempt root missing")
    expected = {"terminal-reservation.json", "cleanup-reservation.json", "coverage-audit.json", "terminal.json", "cleanup.json", comparison.OUTPUT.name}
    expected |= {f"stage-{number:03d}.json" for number in range(len(STAGES))}
    if {item.name for item in attempt.iterdir()} != expected:
        raise SystemExit("attempt-root member set differs")
    terminal = comparison.load_json(attempt / "terminal.json")
    cleanup = comparison.load_json(attempt / "cleanup.json")
    coverage = comparison.load_json(attempt / "coverage-audit.json")
    if (
        terminal.get("attempt_id") != comparison.ATTEMPT_ID
        or terminal.get("status") != "pass_dem_supplied_gtc_diagnostic_only_output_quarantined"
        or terminal.get("coverage_audit_persisted") is not True
        or terminal.get("coverage_gate_passed") is not True
        or terminal.get("gtc_call_started") is not True
        or terminal.get("gtc_returned_raster") is not True
        or terminal.get("output_save_started") is not True
        or terminal.get("output_save_completed") is not True
        or terminal.get("output_exists") is not True
        or terminal.get("assertions", {}).get("automatic_retry") is not False
        or terminal.get("assertions", {}).get("scientific_result_established") is not False
        or cleanup.get("attempt_id") != comparison.ATTEMPT_ID
        or cleanup.get("status") != "extension_checked_in_or_not_checked_out"
        or coverage.get("attempt_id") != comparison.ATTEMPT_ID
        or coverage.get("status") != "pass_counts_complete_diagnostic_only"
        or not comparison.coverage_gate(coverage["gamma"], coverage["dem"])
    ):
        raise SystemExit("terminal, cleanup, or coverage evidence differs")
    stages = [comparison.load_json(attempt / f"stage-{number:03d}.json") for number in range(len(STAGES))]
    if any(item.get("attempt_id") != comparison.ATTEMPT_ID or item.get("stage") != STAGES[number] for number, item in enumerate(stages)):
        raise SystemExit("durable stage sequence differs")
    started_at = dt.datetime.fromisoformat(stages[0]["at_utc"].replace("Z", "+00:00"))
    gamma_files = [path for path in comparison.GAMMA.rglob("*") if path.is_file()]
    gamma_late_writes = sum(dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc) > started_at for path in gamma_files)
    dem_late_write = dt.datetime.fromtimestamp(comparison.DEM.stat().st_mtime, dt.timezone.utc) > started_at
    if gamma_late_writes or dem_late_write:
        raise SystemExit("preserved input file has later write time")
    if not comparison.OUTPUT.is_dir():
        raise SystemExit("quarantined output missing")
    output_count, output_bytes, output_identity = inventory(comparison.OUTPUT)
    if output_count == 0 or output_bytes == 0:
        raise SystemExit("quarantined output empty")
    receipt_names = sorted(name for name in expected if name.endswith(".json"))
    receipts = {name: {"size_bytes": (attempt / name).stat().st_size, "sha256": comparison.sha256(attempt / name)} for name in receipt_names}
    gamma_overview = coverage["gamma"]["aois"]["AOI-OVERVIEW"]
    dem_overview = coverage["dem"]["aois"]["AOI-OVERVIEW"]
    result = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-DEM-FITNESS-COMPARISON-001-TERMINAL-RECONCILIATION",
        "reconciled_at_utc": comparison.now_utc(),
        "status": "pass_terminal_receipts_reconciled_diagnostic_only",
        "disposition": "pass_diagnostic_only_no_scientific_admission",
        "attempt_id": comparison.ATTEMPT_ID,
        "attempt_consumed": True,
        "bindings": {
            "proposal_sha256": comparison.PROPOSAL_SHA,
            "review_bundle_sha256": comparison.BUNDLE_SHA,
            "approval_sha256": comparison.sha256(ROOT / comparison.APPROVAL_REF),
            "final_preflight_sha256": comparison.sha256(ROOT / comparison.PREFLIGHT_REF),
            "external_receipts": receipts,
        },
        "observation": {
            "gamma_overview_native_cell_centers": gamma_overview["total_native_cell_centers"],
            "gamma_overview_valid_both_bands": gamma_overview["valid_all_bands"],
            "gamma_source_aoi_status": coverage["gamma"]["aois"]["AOI-SOURCE"]["status"],
            "gamma_upper_corridor_aoi_status": coverage["gamma"]["aois"]["AOI-UPPER-CORRIDOR"]["status"],
            "dem_overview_native_cell_centers": dem_overview["total_native_cell_centers"],
            "dem_overview_valid_cells": dem_overview["valid_all_bands"],
            "gtc_called_with_exact_existing_dem_and_geoid_none": True,
            "gtc_returned_raster": True,
            "one_explicit_save_completed": True,
            "quarantined_output_file_count": output_count,
            "quarantined_output_total_file_bytes": output_bytes,
            "quarantined_output_inventory_sha256": output_identity,
            "preserved_gamma_file_count": len(gamma_files),
            "preserved_gamma_file_writes_after_attempt_start": gamma_late_writes,
            "preserved_dem_file_write_after_attempt_start": dem_late_write,
            "cleanup_status": cleanup["status"],
        },
        "limits": {
            "positive_valid_envelope_intersection_is_only_a_diagnostic_floor": True,
            "dem_sufficiency_for_full_six_source_radar_route_established": False,
            "no_dem_vs_dem_historical_error_cause_isolated": False,
            "land_scene_scientific_fitness_established": False,
            "usable_baseline_or_change_evidence_established": False,
            "derived_pixels_published": False,
            "automatic_retry_performed": False,
            "further_radar_processing_authorized_by_this_result": False,
        },
        "method": "Receipt SHA-256 and output-byte inventory hashing only; no output raster pixel decoding, map use, or pixel publication.",
    }
    comparison.write_new_json(ROOT / TERMINAL_REF, result)
    print(json.dumps({"status": result["status"], "attempt_id": comparison.ATTEMPT_ID, "output_inventory_sha256": output_identity}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
