#!/usr/bin/env python3
"""Reconcile the exact authorized receipt recovery and four DEM conversions."""

from __future__ import annotations

import json
from pathlib import Path

from m2_dem_vertical_datum_proj25_core import ROOT, load_json, sha256_file, write_new_json


OUTPUT = ROOT / "records/readiness/m2-dem-proj25-receipt-persistence-recovery-002-terminal-reconciliation.json"
FINAL_PREFLIGHT = ROOT / "records/acquisition/m2-dem-vertical-datum-proj25-receipt-persistence-recovery-002-final-preflight.json"
GRID_RECEIPT = ROOT / "records/acquisition/m2-geoid-001-receipt-recovery-002.json"
OPERATION_PREFLIGHT = ROOT / "records/acquisition/m2-dem-vertical-datum-proj25-operation-selection-sign-preflight.json"
BATCH = ROOT / "records/processing/m2-dem-vertical-datum-proj25-conversion-batch-001.json"
SOURCE_IDS = ["M2-DEM-001", "M2-DEM-002", "M2-DEM-003", "M2-DEM-004"]


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("receipt-persistence recovery-002 terminal reconciliation collision")
    final_preflight = load_json(FINAL_PREFLIGHT)
    grid_receipt = load_json(GRID_RECEIPT)
    operation = load_json(OPERATION_PREFLIGHT)
    batch = load_json(BATCH)
    if final_preflight.get("status") != "pass_no_content_receipt_recovery_002_released":
        raise SystemExit("final no-content preflight differs")
    if grid_receipt.get("status") != "pass_exact_promoted_grid_receipt_recovered_input_only":
        raise SystemExit("grid receipt recovery did not pass")
    if operation.get("status") != "pass_exact_local_inverse_operation_h_equals_H_plus_N":
        raise SystemExit("operation/sign preflight did not pass")
    if (
        batch.get("status") != "pass_four_fixed_order_conversions_verified"
        or batch.get("source_order") != SOURCE_IDS
        or batch.get("attempted_order") != SOURCE_IDS
        or len(batch.get("results", [])) != 4
        or any(item.get("status") != "pass_converted_verified_promoted" for item in batch["results"])
        or batch.get("seam_failure") is not None
        or batch.get("assertions", {}).get("maximum_attempts_per_dem") != 1
        or batch.get("assertions", {}).get("automatic_retry_performed") is not False
        or batch.get("assertions", {}).get("source_files_immutable") is not True
        or batch.get("assertions", {}).get("proj_network_enabled") is not False
        or batch.get("assertions", {}).get("scientific_result_established") is not False
    ):
        raise SystemExit("conversion batch differs from the exact authorized successful result")

    source_results = []
    bindings = {
        "final_no_content_preflight_sha256": sha256_file(FINAL_PREFLIGHT),
        "grid_receipt_recovery_sha256": sha256_file(GRID_RECEIPT),
        "operation_sign_preflight_sha256": sha256_file(OPERATION_PREFLIGHT),
        "conversion_batch_sha256": sha256_file(BATCH),
    }
    for source_id in SOURCE_IDS:
        stem = source_id.lower()
        started_path = ROOT / f"records/processing/{stem}-proj25-conversion-001-started.json"
        terminal_path = ROOT / f"records/processing/{stem}-proj25-conversion-001-terminal.json"
        started = load_json(started_path)
        terminal = load_json(terminal_path)
        expected_attempt = f"{stem}-proj25-conversion-001"
        if (
            started.get("attempt_id") != expected_attempt
            or terminal.get("attempt_id") != expected_attempt
            or started.get("source_id") != source_id
            or terminal.get("source_id") != source_id
            or terminal.get("status") != "pass_converted_verified_promoted"
            or terminal.get("attempt_count") != 1
            or terminal.get("automatic_retry_performed") is not False
            or terminal.get("source_immutable") is not True
            or terminal.get("source_before") != terminal.get("source_after")
            or terminal.get("staged") != terminal.get("promoted")
            or terminal.get("verification", {}).get("same_dimensions") is not True
            or terminal.get("verification", {}).get("same_geotransform") is not True
            or terminal.get("verification", {}).get("nodata_mismatch_count") != 0
            or terminal.get("verification", {}).get("approved_aoi_nonfinite_count") != 0
            or terminal.get("arcgis_readability", {}).get("readable") is not True
            or terminal.get("proj_network_enabled") is not False
        ):
            raise SystemExit(f"terminal conversion receipt differs for {source_id}")
        started_ref = str(started_path.relative_to(ROOT)).replace("\\", "/")
        terminal_ref = str(terminal_path.relative_to(ROOT)).replace("\\", "/")
        bindings[f"{source_id.lower()}_started_sha256"] = sha256_file(started_path)
        bindings[f"{source_id.lower()}_terminal_sha256"] = sha256_file(terminal_path)
        source_results.append({
            "source_id": source_id,
            "attempt_id": expected_attempt,
            "started_ref": started_ref,
            "terminal_ref": terminal_ref,
            "source_sha256": terminal["source_after"]["sha256"],
            "output_sha256": terminal["promoted"]["sha256"],
            "output_size_bytes": terminal["promoted"]["size_bytes"],
            "status": terminal["status"],
        })

    record = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-DEM-PROJ25-RECEIPT-PERSISTENCE-RECOVERY-002-TERMINAL-RECONCILIATION",
        "reconciled_at_utc": batch["completed_at_utc"],
        "status": "pass_receipt_recovered_operation_confirmed_four_conversions_verified",
        "bindings": bindings,
        "source_order": SOURCE_IDS,
        "source_results": source_results,
        "seams": batch["seams"],
        "assertions": {
            "final_no_content_preflight_passed": True,
            "receipt_reserved_before_grid_content_read": True,
            "grid_identity_verified": True,
            "new_grid_promotion_performed": False,
            "operation_height_relation": "h = H + N",
            "maximum_conversion_attempts_per_dem": 1,
            "automatic_retry_performed": False,
            "all_four_sources_immutable": True,
            "proj_network_enabled": False,
            "orbit_or_radar_action_performed": False,
            "baseline_or_change_analysis_performed": False,
            "scientific_result_established": False,
        },
        "next_checkpoint": "M2-ORBIT-APPLY",
        "next_action": "Stop before orbit application. Radar pixel readiness and an executable exact-source orbit-application route remain unresolved; prepare a separately governed review before any orbit application, radar pixel read, baseline, change analysis, attribution, or scientific publication.",
    }
    write_new_json(OUTPUT, record)
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
