#!/usr/bin/env python3
"""Verify and conditionally promote the exact preserved PROJ grid without network access."""

from __future__ import annotations

import argparse
import json

from m2_dem_vertical_datum_proj25_core import (
    EXPECTED_APPROVAL_SHA256,
    ROOT,
    controlled_path,
    inspect_arcgis_readability,
    inspect_grid,
    load_contract,
    load_json,
    promote_no_replace,
    snapshot,
    write_new_json,
)


PREFLIGHT = ROOT / "records/acquisition/m2-dem-vertical-datum-proj25-metadata-recovery-001-final-preflight.json"
ATTEMPT_ID = "m2-geoid-001-metadata-recovery-001"
PUBLIC_STARTED = ROOT / f"records/acquisition/{ATTEMPT_ID}-started.json"
PUBLIC_TERMINAL = ROOT / f"records/acquisition/{ATTEMPT_ID}-terminal.json"


def utc_now() -> str:
    import datetime as datetime_module

    return datetime_module.datetime.now(datetime_module.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_preconditions() -> tuple[dict, object, object, object]:
    if PUBLIC_STARTED.exists() or PUBLIC_TERMINAL.exists():
        raise ValueError("fixed offline recovery receipt collision")
    if not PREFLIGHT.is_file():
        raise ValueError("final no-content recovery preflight is absent")
    preflight = load_json(PREFLIGHT)
    if (
        preflight.get("status") != "pass_no_content_offline_recovery_released"
        or preflight.get("assertions", {}).get("network_requests_performed") != 0
        or preflight.get("assertions", {}).get("preserved_content_bytes_read") != 0
        or preflight.get("assertions", {}).get("dem_pixels_read") is not False
    ):
        raise ValueError("final no-content preflight does not release exact offline recovery")
    contract = load_contract()
    grid = contract["grid"]
    recovery = contract["metadata_recovery"]
    if recovery.get("attempt_id") != ATTEMPT_ID or recovery.get("network_requests") != 0:
        raise ValueError("offline recovery contract drift")
    staged = controlled_path(grid["staging_relative_path"])
    destination = controlled_path(grid["destination_relative_path"])
    events = controlled_path(f"derived/control-events/m2-dem-vertical-datum-proj25/{ATTEMPT_ID}")
    if not staged.is_file() or destination.exists() or events.exists():
        raise ValueError("offline recovery staging, destination, or event collision")
    return contract, staged, destination, events


def run(started_at: str) -> dict:
    contract, staged, destination, events = validate_preconditions()
    grid = contract["grid"]
    events.mkdir(parents=True, exist_ok=False)
    external_started = events / "started.json"
    external_terminal = events / "terminal.json"
    started = {
        "schema_version": "1.0",
        "event": "m2_dem_vertical_grid_offline_recovery_started",
        "attempt_id": ATTEMPT_ID,
        "source_id": grid["source_id"],
        "started_at_utc": started_at,
        "terminal_attempt_id": contract["metadata_recovery"]["terminal_attempt_id"],
        "staged_path": str(staged),
        "destination_path": str(destination),
        "network_requests_authorized": 0,
        "maximum_offline_verification_attempts": 1,
        "automatic_retry_authorized": False,
        "approval_sha256": EXPECTED_APPROVAL_SHA256,
    }
    write_new_json(external_started, started)
    write_new_json(PUBLIC_STARTED, {**started, "external_started_event": str(external_started)})
    stage = "staged_identity"
    try:
        observed = snapshot(staged)
        if observed != {"size_bytes": grid["expected_size_bytes"], "sha256": grid["expected_sha256"]}:
            raise ValueError("preserved staged byte identity differs")
        stage = "gdal_metadata_verification"
        gdal_metadata = inspect_grid(staged)
        stage = "arcgis_readability"
        arcgis = inspect_arcgis_readability(staged)
        if (
            not arcgis["readable"]
            or arcgis["width"] != 8640
            or arcgis["height"] != 4321
            or arcgis["band_count"] != 1
        ):
            raise ValueError("ArcGIS grid readability differs")
        stage = "conditional_no_replace_promotion"
        promoted = promote_no_replace(staged, destination, grid["expected_size_bytes"], grid["expected_sha256"])
        terminal = {
            "schema_version": "1.0",
            "event": "m2_dem_vertical_grid_offline_recovery_succeeded",
            "status": "pass_offline_verified_promoted_input_only",
            "attempt_id": ATTEMPT_ID,
            "source_id": grid["source_id"],
            "started_at_utc": started_at,
            "completed_at_utc": utc_now(),
            "network_request_count": 0,
            "offline_verification_attempt_count": 1,
            "automatic_retry_performed": False,
            "staged": observed,
            "promoted": promoted,
            "gdal_metadata": gdal_metadata,
            "arcgis_readability": arcgis,
            "destination_path": str(destination),
            "staging_bytes_preserved": True,
            "proj_network_enabled": False,
            "dem_pixels_read": False,
            "conversion_attempts_started": 0,
        }
        write_new_json(external_terminal, terminal)
        write_new_json(PUBLIC_TERMINAL, {**terminal, "external_terminal_event": str(external_terminal)})
        return terminal
    except BaseException as exc:
        terminal = {
            "schema_version": "1.0",
            "event": "m2_dem_vertical_grid_offline_recovery_failed",
            "status": "terminal_failure_no_retry",
            "attempt_id": ATTEMPT_ID,
            "source_id": grid["source_id"],
            "started_at_utc": started_at,
            "completed_at_utc": utc_now(),
            "last_stage": stage,
            "failure_type": type(exc).__name__,
            "failure_message": str(exc),
            "network_request_count": 0,
            "offline_verification_attempt_count": 1,
            "automatic_retry_authorized": False,
            "staged_bytes_preserved": staged.stat().st_size if staged.exists() else 0,
            "destination_created": destination.exists(),
            "conversion_attempts_started": 0,
        }
        try:
            write_new_json(external_terminal, terminal)
        finally:
            write_new_json(PUBLIC_TERMINAL, {**terminal, "external_terminal_event": str(external_terminal)})
        return terminal


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--started-at-utc", default=None)
    args = parser.parse_args()
    started_at = args.started_at_utc or utc_now()
    if not started_at.endswith("Z"):
        raise SystemExit("--started-at-utc must be UTC")
    result = run(started_at)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "pass_offline_verified_promoted_input_only" else 20


if __name__ == "__main__":
    raise SystemExit(main())
