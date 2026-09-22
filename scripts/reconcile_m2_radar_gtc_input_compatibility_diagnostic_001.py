#!/usr/bin/env python3
"""Reconcile the one external GTC metadata diagnostic into sanitized public evidence."""

from __future__ import annotations

import json
import re

from m2_radar_gtc_input_compatibility_diagnostic_001 import (
    APPROVAL_REF, ATTEMPT_ID, CANDIDATES, DIAGNOSTIC_ROOT, GATE_REF,
    PREFLIGHT_REF, ROOT, load_json, now_utc, sha256, verify_public_bindings,
    verify_gate, write_new_json,
)


PREFIX = "m2-radar-gtc-input-compatibility-diagnostic-001"
TERMINAL_REF = f"records/processing/{PREFIX}-terminal-reconciliation.json"
OUTCOME_REF = f"records/processing/{PREFIX}-outcome-reconciliation.json"
RECEIPTS = (
    "terminal-reservation.json", "cleanup-reservation.json", "started.json",
    "terminal.json", "cleanup.json",
)
SECRET = re.compile(r"(?i)(?:bearer\s+)?eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")
WINDOWS_PATH = re.compile(r"(?i)[A-Z]:\\")


def main() -> int:
    verify_public_bindings()
    verify_gate()
    preflight = load_json(ROOT / PREFLIGHT_REF)
    if preflight.get("status") != "pass_no_content_single_attempt_ready":
        raise SystemExit("final preflight is not pass")
    if (ROOT / TERMINAL_REF).exists() or (ROOT / OUTCOME_REF).exists():
        raise SystemExit("terminal reconciliation collision")
    if not DIAGNOSTIC_ROOT.is_dir():
        raise SystemExit("exact diagnostic root absent")
    if sorted(item.name for item in DIAGNOSTIC_ROOT.iterdir()) != sorted(RECEIPTS):
        raise SystemExit("diagnostic root members differ")
    receipts = {name: {"size_bytes": (DIAGNOSTIC_ROOT / name).stat().st_size, "sha256": sha256(DIAGNOSTIC_ROOT / name)} for name in RECEIPTS}
    terminal = load_json(DIAGNOSTIC_ROOT / "terminal.json")
    cleanup = load_json(DIAGNOSTIC_ROOT / "cleanup.json")
    started = load_json(DIAGNOSTIC_ROOT / "started.json")
    if (
        terminal.get("attempt_id") != ATTEMPT_ID
        or terminal.get("status") != "pass_current_structural_metadata_observed_only"
        or terminal.get("failure_code") is not None
        or cleanup.get("attempt_id") != ATTEMPT_ID
        or cleanup.get("status") != "metadata_process_exited_no_payload_cleanup_required"
        or started.get("attempt_id") != ATTEMPT_ID
        or started.get("preflight_sha256") != sha256(ROOT / PREFLIGHT_REF)
        or [item.get("candidate_ref") for item in terminal.get("candidate_observations", [])] != list(CANDIDATES)
        or [item.get("candidate_index") for item in terminal.get("candidate_observations", [])] != list(range(6))
        or not all(item.get("arcgis_exists") is True for item in terminal["candidate_observations"])
        or terminal.get("runtime", {}).get("gtc_parameters") != ["in_radar_data", "polarization_bands", "in_dem_raster", "geoid"]
        or terminal.get("structural_comparisons", {}).get("slant_vs_despeckled_band_count_equal") is not True
        or terminal.get("structural_comparisons", {}).get("slant_vs_despeckled_spatial_reference_equal") is not True
        or terminal.get("structural_comparisons", {}).get("dem_single_band_observed") is not True
    ):
        raise SystemExit("terminal metadata or one-attempt evidence differs")
    assertions = terminal.get("assertions", {})
    for key in ("geoprocessing_called", "raster_function_called", "pixel_data_read", "network_or_credentials_used", "preserved_inputs_mutated", "historical_root_cause_established", "radar_recovery_readiness_established", "scientific_result_established"):
        if assertions.get(key) is not False:
            raise SystemExit("diagnostic claim boundary differs")
    if assertions.get("one_process_consumed") is not True:
        raise SystemExit("diagnostic process not terminally consumed")
    public_observations = terminal["candidate_observations"]
    if SECRET.search(json.dumps(public_observations)) or WINDOWS_PATH.search(json.dumps(public_observations)):
        raise SystemExit("public observation contains a secret or absolute path")
    terminal_record = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-GTC-INPUT-COMPATIBILITY-DIAGNOSTIC-001-TERMINAL-RECONCILIATION",
        "reconciled_at_utc": now_utc(),
        "status": "pass_six_current_metadata_candidates_observed_only_no_retry",
        "disposition": "pass_diagnostic_only",
        "attempt_id": ATTEMPT_ID,
        "attempt_consumed": True,
        "bindings": {
            "approval_sha256": sha256(ROOT / APPROVAL_REF),
            "implementation_gate_sha256": sha256(ROOT / GATE_REF),
            "final_preflight_sha256": sha256(ROOT / PREFLIGHT_REF),
            "external_receipts": receipts,
        },
        "runtime": terminal["runtime"],
        "candidate_observations": public_observations,
        "structural_comparisons": terminal["structural_comparisons"],
        "limitations": {
            "some_crf_describe_pixel_type_and_cell_size_values_unavailable": True,
            "extent_dimensions_do_not_establish_spatial_overlap": True,
            "arcgis_catalog_recognition_does_not_prove_gtc_processing_fitness": True,
            "historical_failure_root_cause_established": False,
            "radar_recovery_readiness_established": False,
            "usable_baseline_established": False,
            "change_evidence_established": False,
        },
        "assertions": {
            "exact_six_candidates_observed_in_fixed_order": True,
            "one_diagnostic_process_consumed": True,
            "later_diagnostic_or_processing_attempt_started": False,
            "geoprocessing_or_raster_function_called": False,
            "pixel_data_read": False,
            "scientific_result_established": False,
        },
    }
    write_new_json(ROOT / TERMINAL_REF, terminal_record)
    outcome = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-GTC-INPUT-COMPATIBILITY-DIAGNOSTIC-001-OUTCOME-RECONCILIATION",
        "reconciled_at_utc": now_utc(),
        "status": "pass_current_metadata_observation_no_processing_release",
        "bindings": {"terminal_reconciliation_ref": TERMINAL_REF, "terminal_reconciliation_sha256": sha256(ROOT / TERMINAL_REF)},
        "finding": "ArcGIS recognized all six exact preserved candidates. Slant and despeckled gamma each reported two bands and EPSG:4326; the DEM reported one band and EPSG:4326. ArcGIS Describe did not expose pixel type or cell size for both gamma CRFs. These observations do not explain ERROR 000425 or establish GTC processing fitness.",
        "next_checkpoint": "M2-RADAR-ESRI-SEQUENCE-RECOVERY-005-TERMINAL-REVIEW",
        "next_action": "Review the metadata observation and select a separately scoped GTC investigation or other mapped-evidence path. The recovery-005 processing attempt and this diagnostic are consumed.",
        "assertions": {"historical_root_cause_established": False, "radar_recovery_readiness_established": False, "new_radar_processing_attempt_authorized": False, "baseline_or_change_analysis_authorized": False, "scientific_publication_authorized": False},
    }
    write_new_json(ROOT / OUTCOME_REF, outcome)
    print(json.dumps({"status": outcome["status"], "terminal_sha256": sha256(ROOT / TERMINAL_REF), "outcome_sha256": sha256(ROOT / OUTCOME_REF)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
