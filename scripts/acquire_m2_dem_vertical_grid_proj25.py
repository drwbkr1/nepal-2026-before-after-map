#!/usr/bin/env python3
"""Acquire the one approved PROJ EGM2008 grid after its public release gates."""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from m2_dem_vertical_datum_proj25_core import (
    NoRedirectHandler,
    ROOT,
    controlled_path,
    inspect_arcgis_readability,
    inspect_grid,
    load_contract,
    load_json,
    promote_no_replace,
    sha256_file,
    stream_to_exclusive_staging,
    write_new_json,
)


PREFLIGHT = ROOT / "records/acquisition/m2-dem-vertical-datum-proj25-final-preflight.json"
ATTEMPT_ID = "m2-geoid-001-real-001"
PUBLIC_STARTED = ROOT / f"records/acquisition/{ATTEMPT_ID}-started.json"
PUBLIC_TERMINAL = ROOT / f"records/acquisition/{ATTEMPT_ID}-terminal.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_preconditions() -> tuple[dict[str, Any], Path, Path]:
    if PUBLIC_STARTED.exists() or PUBLIC_TERMINAL.exists():
        raise ValueError("fixed grid attempt receipt collision")
    if not PREFLIGHT.is_file():
        raise ValueError("final no-payload preflight is absent")
    preflight = load_json(PREFLIGHT)
    if (
        preflight.get("status") != "pass_no_payload_real_actions_released"
        or preflight.get("assertions", {}).get("payload_bytes_read") != 0
        or preflight.get("assertions", {}).get("grid_request_performed") is not False
        or preflight.get("assertions", {}).get("dem_pixels_read") is not False
    ):
        raise ValueError("final no-payload preflight does not release the exact request")
    contract = load_contract()
    grid = contract["grid"]
    staging = controlled_path(grid["staging_relative_path"])
    destination = controlled_path(grid["destination_relative_path"])
    if staging.exists() or destination.exists() or staging.parent.exists():
        raise ValueError("fixed grid staging or destination collision")
    return contract, staging, destination


def run(started_at: str, opener_factory: Any = urllib.request.build_opener) -> dict[str, Any]:
    contract, staging, destination = validate_preconditions()
    grid = contract["grid"]
    external_events = controlled_path(f"derived/control-events/m2-dem-vertical-datum-proj25/{ATTEMPT_ID}")
    external_events.mkdir(parents=True, exist_ok=False)
    external_started = external_events / "started.json"
    external_terminal = external_events / "terminal.json"
    started = {
        "schema_version": "1.0",
        "event": "m2_dem_vertical_grid_request_started",
        "attempt_id": ATTEMPT_ID,
        "source_id": grid["source_id"],
        "started_at_utc": started_at,
        "url": grid["url"],
        "restart_offset_bytes": 0,
        "range_or_resume_used": False,
        "maximum_requests": 1,
        "automatic_retry_authorized": False,
        "staging_path": str(staging),
        "destination_path": str(destination),
        "credential_or_account_used": False,
    }
    write_new_json(external_started, started)
    write_new_json(PUBLIC_STARTED, {**started, "external_started_event": str(external_started)})
    stage = "request"
    try:
        request = urllib.request.Request(
            grid["url"], method="GET", headers={"User-Agent": "nepal-map-controlled-intake/1.0"}
        )
        opener = opener_factory(NoRedirectHandler())
        with opener.open(request, timeout=180) as response:
            if int(getattr(response, "status", 0)) != 200 or response.geturl() != grid["url"]:
                raise ValueError("grid redirect or HTTP identity rejected")
            if response.headers.get("Content-Range"):
                raise ValueError("range response rejected")
            content_length = response.headers.get("Content-Length")
            if content_length is None or int(content_length) != grid["expected_size_bytes"]:
                raise ValueError("grid Content-Length differs")
            if "text/html" in (response.headers.get("Content-Type") or "").casefold():
                raise ValueError("HTML payload rejected")
            stage = "stream"
            observed = stream_to_exclusive_staging(response, staging, grid["expected_size_bytes"])
        if observed != {
            "size_bytes": grid["expected_size_bytes"],
            "sha256": grid["expected_sha256"],
        }:
            raise ValueError("grid staged byte identity differs")
        stage = "gdal_verification"
        gdal_metadata = inspect_grid(staging)
        stage = "arcgis_readability"
        arcgis = inspect_arcgis_readability(staging)
        if (
            not arcgis["readable"]
            or arcgis["width"] != 8640
            or arcgis["height"] != 4321
            or arcgis["band_count"] != 1
        ):
            raise ValueError("ArcGIS grid readability differs")
        stage = "promotion"
        promoted = promote_no_replace(
            staging, destination, grid["expected_size_bytes"], grid["expected_sha256"]
        )
        terminal = {
            "schema_version": "1.0",
            "event": "m2_dem_vertical_grid_request_succeeded",
            "status": "pass_verified_promoted_input_only",
            "attempt_id": ATTEMPT_ID,
            "source_id": grid["source_id"],
            "started_at_utc": started_at,
            "completed_at_utc": utc_now(),
            "request_count": 1,
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
            "event": "m2_dem_vertical_grid_request_failed",
            "status": "terminal_failure_no_retry",
            "attempt_id": ATTEMPT_ID,
            "source_id": grid["source_id"],
            "started_at_utc": started_at,
            "completed_at_utc": utc_now(),
            "last_stage": stage,
            "failure_type": type(exc).__name__,
            "failure_message": str(exc),
            "request_count": 1,
            "automatic_retry_authorized": False,
            "partial_bytes_preserved": staging.stat().st_size if staging.exists() else 0,
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
    return 0 if result["status"] == "pass_verified_promoted_input_only" else 20


if __name__ == "__main__":
    raise SystemExit(main())
