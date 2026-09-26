#!/usr/bin/env python3
"""Capture anonymous HyP3 RTC API shape; never submit or validate a job."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "scratch" / "asf-rtc-api-schema-001"
RECEIPT = ROOT / "records" / "observations" / "m2-asf-rtc-api-schema-001-local.json"
URL = "https://hyp3-api.asf.alaska.edu/openapi.json"
SCENES = (
    "S1D_IW_GRDH_1SDV_20260816T122141_20260816T122206_004151_007980_C3AB",
    "S1D_IW_GRDH_1SDV_20260828T122141_20260828T122206_004326_007FA4_01B4",
)


def main() -> None:
    if RAW_ROOT.exists() or RECEIPT.exists():
        raise RuntimeError("append-only schema observation already exists")
    request = Request(URL, headers={"User-Agent": "nepal-map-metadata-research/1.0"})
    with urlopen(request, timeout=20) as response:
        if response.status != 200:
            raise RuntimeError("schema HTTP failure")
        body = response.read(3_000_001)
    if len(body) > 3_000_000:
        raise RuntimeError("schema size guard")
    specification = json.loads(body)
    choices = specification["paths"]["/jobs"]["post"]["requestBody"]["content"]["application/json"]["schema"]["properties"]["jobs"]["items"]["oneOf"]
    rtc = [item for item in choices if "RTC_GAMMA" in item.get("properties", {}).get("job_type", {}).get("enum", [])]
    if len(rtc) != 1:
        raise RuntimeError("RTC schema ambiguous")
    fields = rtc[0]["properties"]["job_parameters"]["properties"]
    candidates = []
    for role, scene in zip(("before", "after"), SCENES, strict=True):
        parameters = {
            "granules": [scene],
            "resolution": 10.0,
            "dem_name": "copernicus",
            "radiometry": "gamma0",
            "scale": "decibel",
            "speckle_filter": False,
            "dem_matching": False,
            "include_dem": True,
            "include_inc_map": True,
            "include_scattering_area": True,
            "include_rgb": False,
        }
        for name, value in parameters.items():
            field = fields[name]
            if "enum" in field and value not in field["enum"]:
                raise RuntimeError(f"option enum mismatch: {name}")
            if field["type"] == "boolean" and not isinstance(value, bool):
                raise RuntimeError(f"option type mismatch: {name}")
        # OpenAPI's pattern is an anchored prefix; it does not end in `$`.
        alternatives = fields["granules"]["items"]["anyOf"]
        if not any(re.match(option["pattern"], scene) and len(scene) == option["minLength"] for option in alternatives):
            raise RuntimeError("scene schema mismatch")
        candidates.append({
            "name": f"nepal-map-m2-rtc-001-{role}",
            "job_type": "RTC_GAMMA",
            "job_parameters": parameters,
        })

    RAW_ROOT.mkdir(parents=True, exist_ok=False)
    with (RAW_ROOT / "openapi.json").open("xb") as output:
        output.write(body)
    receipt = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ASF-RTC-API-SCHEMA-001-LOCAL",
        "status": "offline_candidate_shape_checked_no_authenticated_request",
        "retrieved_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_url": URL,
        "raw_schema_ref": "scratch/asf-rtc-api-schema-001/openapi.json",
        "raw_schema_sha256": hashlib.sha256(body).hexdigest(),
        "raw_schema_bytes": len(body),
        "candidate_jobs": candidates,
        "candidate_status": "unapproved_not_submitted",
        "checks": {
            "exact_two_s1d_grd_names_match_openapi_pattern": True,
            "proposed_options_match_openapi_types_and_enums": True,
            "validate_only_request_sent": False,
            "job_submission_sent": False,
            "account_or_credential_used": False,
            "credits_spent": False,
        },
    }
    with RECEIPT.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(receipt, output, indent=2)
        output.write("\n")
    print("PASS: anonymous HyP3 schema captured; two candidate shapes checked; no POST")


if __name__ == "__main__":
    main()
