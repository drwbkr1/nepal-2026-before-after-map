#!/usr/bin/env python3
"""Capture anonymous ASF catalog rows for the two adjacent ascending GRDs.

No authentication, HyP3 request, product acquisition, or pixel read occurs.
The observation identity is append-only and cannot be rerun in place.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "scratch" / "asf-ascending-adjacent-001" / "response.json"
RECEIPT = ROOT / "records" / "observations" / "m2-asf-ascending-adjacent-001-local.json"
SCENES = {
    "M1-SRC-001": "S1D_IW_GRDH_1SDV_20260816T122116_20260816T122141_004151_007980_B057",
    "M1-SRC-004": "S1D_IW_GRDH_1SDV_20260828T122116_20260828T122141_004326_007FA4_C523",
}


def main() -> None:
    if PAYLOAD.exists() or RECEIPT.exists():
        raise RuntimeError("append-only ASF adjacent-scene observation already exists")
    url = "https://api.daac.asf.alaska.edu/services/search/param?" + urlencode(
        {"granule_list": ",".join(SCENES.values()), "output": "geojson"}
    )
    request = Request(url, headers={"User-Agent": "nepal-map-metadata-research/1.0"})
    with urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"ASF catalog HTTP {response.status}")
        body = response.read(2_000_001)
    if len(body) > 2_000_000:
        raise RuntimeError("ASF metadata response exceeded 2 MB bound")
    result = json.loads(body)
    if not isinstance(result, dict) or not isinstance(result.get("features"), list):
        raise RuntimeError("unexpected ASF GeoJSON response")
    rows = [
        {
            "scene_name": feature.get("properties", {}).get("sceneName"),
            "start_utc": feature.get("properties", {}).get("startTime"),
            "platform": feature.get("properties", {}).get("platform"),
            "processing_level": feature.get("properties", {}).get("processingLevel"),
            "flight_direction": feature.get("properties", {}).get("flightDirection"),
        }
        for feature in result["features"]
    ]
    exact_grd_present = {
        source_id: any(
            row["scene_name"] == name
            and row["processing_level"] == "GRD_HD"
            and row["flight_direction"] == "ASCENDING"
            for row in rows
        )
        for source_id, name in SCENES.items()
    }
    receipt = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ASF-ASCENDING-ADJACENT-001-LOCAL",
        "status": "public_metadata_only_no_source_adoption",
        "retrieved_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "url": url,
        "payload_ref": "scratch/asf-ascending-adjacent-001/response.json",
        "payload_sha256": hashlib.sha256(body).hexdigest(),
        "payload_bytes": len(body),
        "exact_grd_present": exact_grd_present,
        "rows": rows,
        "limits": {
            "hyp3_eligibility_verified": False,
            "rtc_product_exists": False,
            "aoi_pixel_coverage_verified": False,
            "account_or_credential_used": False,
            "job_submitted": False,
            "product_acquired": False,
            "project_pixels_read": False,
            "scientific_method_or_route_changed": False,
        },
    }
    PAYLOAD.parent.mkdir(parents=True, exist_ok=False)
    with PAYLOAD.open("xb") as output:
        output.write(body)
    with RECEIPT.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(receipt, output, ensure_ascii=False, indent=2)
        output.write("\n")
    print("PASS: anonymous adjacent-scene metadata captured; no product or job action")


if __name__ == "__main__":
    main()
