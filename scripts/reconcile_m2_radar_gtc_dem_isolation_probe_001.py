#!/usr/bin/env python3
"""Reconcile the sole no-DEM GTC attempt without decoding or publishing pixels."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

import m2_radar_gtc_dem_isolation_probe_001 as probe


ROOT = Path(__file__).resolve().parents[1]
TERMINAL_REF = f"records/processing/{probe.PREFIX}-terminal-reconciliation.json"
STAGES = (
    "one_process_started", "arcpy_and_signature_ready", "image_analyst_checked_out",
    "exact_preserved_raster_constructed", "gtc_call_started_no_dem", "gtc_returned",
    "single_output_save_started", "single_output_save_completed",
)


def inventory(directory: Path) -> tuple[int, int, str]:
    files = sorted((path for path in directory.rglob("*") if path.is_file()), key=lambda path: path.relative_to(directory).as_posix())
    manifest = []
    for path in files:
        manifest.append([path.relative_to(directory).as_posix(), path.stat().st_size, probe.sha256(path)])
    identity = hashlib.sha256(json.dumps(manifest, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
    return len(files), sum(item[1] for item in manifest), identity


def main() -> int:
    if (ROOT / TERMINAL_REF).exists():
        raise SystemExit("terminal reconciliation already exists")
    probe.verified_authority()
    preflight = probe.load_json(ROOT / probe.PREFLIGHT_REF)
    if preflight.get("status") != "pass_final_no_content_preflight_one_attempt_ready":
        raise SystemExit("final preflight does not pass")
    attempt = probe.ATTEMPT_ROOT
    if not attempt.is_dir():
        raise SystemExit("exact attempt root missing")
    expected_names = {"terminal-reservation.json", "cleanup-reservation.json", "terminal.json", "cleanup.json", "gtc_no_dem_diagnostic.crf"}
    expected_names |= {f"stage-{number:03d}.json" for number in range(len(STAGES))}
    if {item.name for item in attempt.iterdir()} != expected_names:
        raise SystemExit("attempt root member set differs")
    terminal = probe.load_json(attempt / "terminal.json")
    cleanup = probe.load_json(attempt / "cleanup.json")
    if (
        terminal.get("attempt_id") != probe.ATTEMPT_ID
        or terminal.get("status") != "pass_no_dem_gtc_diagnostic_only_output_quarantined"
        or terminal.get("gtc_call_started") is not True
        or terminal.get("gtc_returned_raster") is not True
        or terminal.get("output_save_started") is not True
        or terminal.get("output_save_completed") is not True
        or terminal.get("output_exists") is not True
        or cleanup.get("attempt_id") != probe.ATTEMPT_ID
        or cleanup.get("status") != "extension_checked_in_or_not_checked_out"
    ):
        raise SystemExit("terminal or cleanup receipt differs")
    stages = [probe.load_json(attempt / f"stage-{number:03d}.json") for number in range(len(STAGES))]
    if any(item.get("attempt_id") != probe.ATTEMPT_ID or item.get("stage") != STAGES[number] for number, item in enumerate(stages)):
        raise SystemExit("durable stage sequence differs")
    started_at = dt.datetime.fromisoformat(stages[0]["at_utc"].replace("Z", "+00:00"))
    source_files = [path for path in probe.SOURCE.rglob("*") if path.is_file()]
    source_late_writes = sum(dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc) > started_at for path in source_files)
    if source_late_writes:
        raise SystemExit("preserved input has later file write times")
    if not probe.OUTPUT.is_dir() or (attempt / "gamma0_linear_despeckled_GTC.crf").exists():
        raise SystemExit("quarantined output or intermediate differs")
    output_count, output_bytes, output_identity = inventory(probe.OUTPUT)
    if output_count == 0 or output_bytes == 0:
        raise SystemExit("quarantined output empty")
    receipt_names = sorted(name for name in expected_names if name.endswith(".json"))
    receipts = {name: {"size_bytes": (attempt / name).stat().st_size, "sha256": probe.sha256(attempt / name)} for name in receipt_names}
    result = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-GTC-DEM-ISOLATION-PROBE-001-TERMINAL-RECONCILIATION",
        "reconciled_at_utc": probe.now_utc(),
        "status": "pass_terminal_receipts_reconciled_diagnostic_only",
        "disposition": "pass_diagnostic_only_no_scientific_admission",
        "attempt_id": probe.ATTEMPT_ID,
        "attempt_consumed": True,
        "bindings": {
            "proposal_sha256": probe.PROPOSAL_SHA,
            "review_bundle_sha256": probe.BUNDLE_SHA,
            "approval_sha256": probe.sha256(ROOT / probe.APPROVAL_REF),
            "final_preflight_sha256": probe.sha256(ROOT / probe.PREFLIGHT_REF),
            "external_receipts": receipts,
        },
        "observation": {
            "gtc_called_without_dem_or_geoid_argument": True,
            "gtc_returned_raster": True,
            "one_explicit_save_completed": True,
            "quarantined_output_file_count": output_count,
            "quarantined_output_total_file_bytes": output_bytes,
            "quarantined_output_inventory_sha256": output_identity,
            "arcgis_generated_intermediate_retained": False,
            "preserved_input_file_count": len(source_files),
            "preserved_input_file_writes_after_attempt_start": source_late_writes,
            "cleanup_status": cleanup["status"],
        },
        "limits": {
            "no_dem_result_is_diagnostic_only": True,
            "dem_coverage_historical_cause_established": False,
            "land_scene_scientific_fitness_established": False,
            "baseline_or_change_evidence_established": False,
            "derived_pixels_published": False,
            "automatic_retry_performed": False,
            "further_radar_processing_authorized_by_this_result": False,
        },
        "method": "Receipt SHA-256 and content-byte inventory hashing only; no raster pixel decoding, statistics, map use, or output publication.",
    }
    probe.write_new_json(ROOT / TERMINAL_REF, result)
    print(json.dumps({"status": result["status"], "attempt_id": probe.ATTEMPT_ID, "output_inventory_sha256": output_identity}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
