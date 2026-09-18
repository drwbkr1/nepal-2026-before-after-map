#!/usr/bin/env python3
"""Run the one final no-content preflight for approved offline grid recovery."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone

from m2_dem_vertical_datum_proj25_core import ROOT, controlled_path, load_contract, load_json, sha256_file, write_new_json


PUBLICATION = ROOT / "records/readiness/m2-dem-vertical-datum-proj25-metadata-recovery-001-implementation-publication-gate.json"
OUTPUT = ROOT / "records/acquisition/m2-dem-vertical-datum-proj25-metadata-recovery-001-final-preflight.json"
TERMINAL = ROOT / "records/acquisition/m2-geoid-001-real-001-terminal.json"
RECONCILIATION = ROOT / "records/acquisition/m2-dem-vertical-datum-proj25-acquisition-reconciliation-001.json"
RECOVERY_STARTED = ROOT / "records/acquisition/m2-geoid-001-metadata-recovery-001-started.json"
RECOVERY_TERMINAL = ROOT / "records/acquisition/m2-geoid-001-metadata-recovery-001-terminal.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observed-at-utc", default=None)
    args = parser.parse_args()
    if OUTPUT.exists():
        raise SystemExit("refusing recovery preflight output collision")
    if not PUBLICATION.is_file():
        raise SystemExit("metadata-recovery implementation public gate is missing")
    publication = load_json(PUBLICATION)
    if publication.get("status") != "pass_public_default_branch_ci_offline_recovery_released":
        raise SystemExit("metadata-recovery public gate does not release offline verification")
    contract = load_contract()
    grid = contract["grid"]
    recovery = contract["metadata_recovery"]
    staged = controlled_path(grid["staging_relative_path"])
    destination = controlled_path(grid["destination_relative_path"])
    if not staged.is_file() or staged.stat().st_size != grid["expected_size_bytes"]:
        raise SystemExit("preserved staged file or length differs")
    if destination.exists():
        raise SystemExit("grid destination collision")
    if RECOVERY_STARTED.exists() or RECOVERY_TERMINAL.exists():
        raise SystemExit("offline recovery receipt collision")
    events = controlled_path(f"derived/control-events/m2-dem-vertical-datum-proj25/{recovery['attempt_id']}")
    if events.exists():
        raise SystemExit("offline recovery event collision")
    terminal = load_json(TERMINAL)
    reconciliation = load_json(RECONCILIATION)
    if (
        terminal.get("attempt_id") != recovery["terminal_attempt_id"]
        or terminal.get("status") != "terminal_failure_no_retry"
        or terminal.get("request_count") != 1
        or reconciliation.get("status") != "block_terminal_metadata_representation_mismatch_review_required"
        or reconciliation.get("preserved_staged_bytes", {}).get("path") != str(staged)
        or reconciliation.get("preserved_staged_bytes", {}).get("sha256") != grid["expected_sha256"]
    ):
        raise SystemExit("terminal attempt or preserved-byte reconciliation differs")
    output_collisions = [
        item["source_id"] for item in contract["dem_sources_in_exact_order"]
        if controlled_path(item["output_relative_path"]).exists()
    ]
    if output_collisions:
        raise SystemExit("derived output collision: " + ", ".join(output_collisions))
    source_stats = []
    for item in contract["dem_sources_in_exact_order"]:
        source = controlled_path(item["source_relative_path"])
        if not source.is_file():
            raise SystemExit(f"source DEM missing: {item['source_id']}")
        source_stats.append({"source_id": item["source_id"], "size_bytes": source.stat().st_size, "content_read": False})
    space_probe = next(parent for parent in [destination.parent, *destination.parents] if parent.exists())
    free_bytes = shutil.disk_usage(space_probe).free
    if free_bytes < 2_000_000_000:
        raise SystemExit("insufficient free space for grid and four derived DEMs")
    record = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-DEM-VERTICAL-DATUM-PROJ25-METADATA-RECOVERY-001-FINAL-PREFLIGHT",
        "observed_at_utc": args.observed_at_utc or utc_now(),
        "status": "pass_no_content_offline_recovery_released",
        "publication_gate_sha256": sha256_file(PUBLICATION),
        "terminal_receipt_sha256": sha256_file(TERMINAL),
        "acquisition_reconciliation_sha256": sha256_file(RECONCILIATION),
        "preserved_staged_file": {
            "path": str(staged),
            "size_bytes": staged.stat().st_size,
            "expected_sha256": grid["expected_sha256"],
            "content_read": False,
        },
        "destination_absent": True,
        "source_stats": source_stats,
        "free_bytes": free_bytes,
        "assertions": {
            "network_requests_performed": 0,
            "preserved_content_bytes_read": 0,
            "grid_metadata_read": False,
            "grid_promoted": False,
            "dem_content_read": False,
            "dem_pixels_read": False,
            "external_data_mutated": False,
            "maximum_future_offline_recovery_attempts": 1,
            "automatic_retry_authorized": False,
            "proj_network_enabled": False,
        },
    }
    write_new_json(OUTPUT, record)
    print(json.dumps({"status": record["status"], "output": str(OUTPUT.relative_to(ROOT)).replace("\\", "/")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
