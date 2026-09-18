#!/usr/bin/env python3
"""Run the one final no-payload preflight after the implementation public gate."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from m2_dem_vertical_datum_proj25_core import NoRedirectHandler, ROOT, controlled_path, load_contract, sha256_file, write_new_json


PUBLICATION = ROOT / "records/readiness/m2-dem-vertical-datum-proj25-implementation-publication-gate.json"
OUTPUT = ROOT / "records/acquisition/m2-dem-vertical-datum-proj25-final-preflight.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observed-at-utc", default=None)
    args = parser.parse_args()
    if OUTPUT.exists():
        raise SystemExit("refusing final-preflight output collision")
    if not PUBLICATION.is_file():
        raise SystemExit("implementation public gate is missing")
    publication = json.loads(PUBLICATION.read_text(encoding="utf-8"))
    if publication.get("status") != "pass_public_default_branch_ci_real_actions_released":
        raise SystemExit("implementation public gate does not release real actions")
    contract = load_contract()
    grid = contract["grid"]
    staging = controlled_path(grid["staging_relative_path"])
    destination = controlled_path(grid["destination_relative_path"])
    if staging.exists() or destination.exists():
        raise SystemExit("grid staging or destination collision")
    output_collisions = [item["source_id"] for item in contract["dem_sources_in_exact_order"]
                         if controlled_path(item["output_relative_path"]).exists()]
    if output_collisions:
        raise SystemExit("derived output collision: " + ", ".join(output_collisions))
    source_checks = []
    for item in contract["dem_sources_in_exact_order"]:
        source = controlled_path(item["source_relative_path"])
        observed = sha256_file(source)
        if observed != item["source_sha256"]:
            raise SystemExit(f"source DEM identity drift: {item['source_id']}")
        source_checks.append({"source_id": item["source_id"], "size_bytes": source.stat().st_size,
                              "sha256": observed, "pixels_read": False})
    request = urllib.request.Request(grid["url"], method="HEAD", headers={"User-Agent": "nepal-map-controlled-preflight/1.0"})
    opener = urllib.request.build_opener(NoRedirectHandler())
    with opener.open(request, timeout=60) as response:
        status = int(getattr(response, "status", 200))
        final_url = response.geturl()
        content_length = int(response.headers.get("Content-Length", "-1"))
        last_modified = response.headers.get("Last-Modified")
        etag = response.headers.get("ETag")
    if status != 200 or final_url != grid["url"] or content_length != grid["expected_size_bytes"]:
        raise SystemExit("exact grid HEAD identity drift")
    space_probe = next(parent for parent in [destination.parent, *destination.parents] if parent.exists())
    free_bytes = shutil.disk_usage(space_probe).free
    if free_bytes < 2_000_000_000:
        raise SystemExit("insufficient free space for grid and four derived DEMs")
    record = {
        "schema_version": "1.0", "record_id": "NEPAL-M2-DEM-VERTICAL-DATUM-PROJ25-FINAL-PREFLIGHT",
        "observed_at_utc": args.observed_at_utc or utc_now(), "status": "pass_no_payload_real_actions_released",
        "publication_gate_sha256": sha256_file(PUBLICATION),
        "grid": {"url": grid["url"], "http_status": status, "final_url": final_url,
                 "content_length_bytes": content_length, "last_modified": last_modified, "etag": etag,
                 "staging_absent": True, "destination_absent": True},
        "source_checks": source_checks, "free_bytes": free_bytes,
        "assertions": {"payload_bytes_read": 0, "grid_request_performed": False, "dem_pixels_read": False,
                       "external_data_mutated": False, "maximum_future_grid_requests": 1,
                       "automatic_retry_authorized": False, "proj_network_enabled": False},
    }
    write_new_json(OUTPUT, record)
    print(json.dumps({"status": record["status"], "output": str(OUTPUT.relative_to(ROOT)).replace("\\", "/")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
