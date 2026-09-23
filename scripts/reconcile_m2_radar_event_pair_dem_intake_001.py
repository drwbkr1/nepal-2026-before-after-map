#!/usr/bin/env python3
"""Independently reconcile seven exact promoted DEM tiles before conversion."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from m2_dem_vertical_datum_proj25_core import controlled_path
from m2_radar_event_pair_dem_intake_001 import (
    ROOT, IntakeError, exact_assets, paths_for, sha256,
)


OUTPUT = ROOT / "records" / "acquisition" / "m2-radar-event-area-pair-001-seven-dem-terminal-reconciliation.json"
OLD_CONTRACT = ROOT / "config" / "qa" / "m2-dem-vertical-datum-proj25-contract.json"


def validate_tile(asset: dict[str, Any], paths: dict[str, Path]) -> dict[str, Any]:
    if paths["staging"].exists() or not paths["terminal"].is_file() or not paths["error"].is_file() or not paths["cleanup"].is_file() or not paths["destination"].is_file():
        raise IntakeError("tile_attempt_or_custody_state_incomplete")
    terminal = json.loads(paths["terminal"].read_text(encoding="utf-8"))
    cleanup = json.loads(paths["cleanup"].read_text(encoding="utf-8"))
    if (
        terminal.get("status") != "pass_verified_and_promoted"
        or terminal.get("item_id") != asset["item_id"]
        or cleanup.get("status") != "no_cleanup_required"
        or paths["error"].stat().st_size != 0
        or terminal.get("size_bytes") != asset["observed_head_content_length_bytes"]
        or terminal.get("geotiff", {}).get("width") != 3600
        or terminal.get("geotiff", {}).get("height") != 3600
        or terminal.get("geotiff", {}).get("epsg") != 4326
        or terminal.get("geotiff", {}).get("valid_pixels") != 12960000
        or terminal.get("geotiff", {}).get("nonfinite_pixels") != 0
    ):
        raise IntakeError("tile_terminal_or_structure_drift")
    destination = paths["destination"]
    if destination.stat().st_size != terminal["size_bytes"] or sha256(destination) != terminal["sha256"]:
        raise IntakeError("promoted_tile_byte_identity_drift")
    return {
        "item_id": asset["item_id"],
        "attempt_id": terminal["attempt"],
        "status": "pass_verified_and_promoted",
        "size_bytes": terminal["size_bytes"],
        "sha256": terminal["sha256"],
        "valid_pixels": terminal["geotiff"]["valid_pixels"],
        "terminal_receipt_sha256": sha256(paths["terminal"]),
        "cleanup_receipt_sha256": sha256(paths["cleanup"]),
    }


def reconcile() -> dict[str, Any]:
    if OUTPUT.exists():
        raise IntakeError("seven_tile_reconciliation_already_written")
    assets = exact_assets()
    results = [validate_tile(asset, paths_for(asset["item_id"])) for asset in assets]
    old = json.loads(OLD_CONTRACT.read_text(encoding="utf-8"))
    if len(old["dem_sources_in_exact_order"]) != 4:
        raise IntakeError("prior_four_dem_contract_drift")
    old_results = []
    for item in old["dem_sources_in_exact_order"]:
        source = controlled_path(item["source_relative_path"])
        derivative = controlled_path(item["output_relative_path"])
        terminal_ref = ROOT / "records" / "processing" / f"{item['source_id'].lower()}-proj25-conversion-001-terminal.json"
        receipt = json.loads(terminal_ref.read_text(encoding="utf-8"))
        if (
            not source.is_file() or sha256(source) != item["source_sha256"]
            or not derivative.is_file() or sha256(derivative) != receipt.get("promoted", {}).get("sha256")
        ):
            raise IntakeError("prior_four_dem_custody_drift")
        old_results.append({"source_id": item["source_id"], "raw_sha256": item["source_sha256"], "ellipsoidal_sha256": receipt["promoted"]["sha256"]})
    return {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-EVENT-AREA-PAIR-001-SEVEN-DEM-TERMINAL-RECONCILIATION",
        "checked_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": "pass_seven_exact_tiles_verified_custody_only",
        "fixed_order": [asset["item_id"] for asset in assets],
        "results": results,
        "total_bytes": sum(item["size_bytes"] for item in results),
        "prior_four_read_only_identity": old_results,
        "assertions": {"initial_requests": 7, "transport_recovery_requests": 0, "all_staging_paths_absent": True, "all_terminal_receipts_persisted": True, "new_conversion_attempts_started": 0, "mosaic_attempts_started": 0, "radar_processing_started": False, "baseline_or_change_analysis_released": False},
    }


def main() -> int:
    try:
        result = reconcile()
        with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        print(json.dumps({"status": result["status"], "tile_count": len(result["results"]), "total_bytes": result["total_bytes"]}))
        return 0
    except IntakeError as exc:
        print(json.dumps({"status": "stop_before_conversion", "code": exc.code}))
        return 12


if __name__ == "__main__":
    raise SystemExit(main())
