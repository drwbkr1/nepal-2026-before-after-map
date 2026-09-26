#!/usr/bin/env python3
"""Capture public catalog metadata for a possible external RTC map route.

This script does not authenticate, order jobs, acquire products, or read pixels.
The output identity is append-only: rerunning requires a new review identity.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_ROOT = ROOT / "scratch" / "external-rtc-feasibility-001"
RECEIPT = ROOT / "records" / "observations" / "m2-external-rtc-route-feasibility-001-local.json"
ASF_SCENES = (
    "S1D_IW_GRDH_1SDV_20260816T122141_20260816T122206_004151_007980_C3AB",
    "S1D_IW_GRDH_1SDV_20260828T122141_20260828T122206_004326_007FA4_01B4",
)


def request_url(base: str, params: dict[str, str]) -> str:
    return base + "?" + urlencode(params)


def fetch_json(url: str) -> tuple[bytes, dict]:
    request = Request(url, headers={"User-Agent": "nepal-map-metadata-research/1.0"})
    with urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"catalog HTTP {response.status}")
        body = response.read(5_000_001)
    if len(body) > 5_000_000:
        raise RuntimeError("metadata response exceeded 5 MB bound")
    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise RuntimeError("catalog response is not an object")
    return body, parsed


def main() -> None:
    if RECEIPT.exists() or PAYLOAD_ROOT.exists():
        raise RuntimeError("append-only metadata observation already exists")

    asf_url = request_url(
        "https://api.daac.asf.alaska.edu/services/search/param",
        {"granule_list": ",".join(ASF_SCENES), "output": "geojson"},
    )
    cdse_base = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
    cdse_window = request_url(
        cdse_base,
        {
            "$filter": "Collection/Name eq 'SENTINEL-1-RTC' and ContentDate/Start ge 2026-08-01T00:00:00.000Z and ContentDate/Start lt 2026-09-26T00:00:00.000Z",
            "$select": "Id,Name,ContentDate",
            "$top": "1",
            "$count": "true",
        },
    )
    cdse_latest = request_url(
        cdse_base,
        {
            "$filter": "Collection/Name eq 'SENTINEL-1-RTC'",
            "$select": "Id,Name,ContentDate",
            "$top": "1",
            "$orderby": "ContentDate/Start desc",
            "$count": "true",
        },
    )
    cmr_url = request_url(
        "https://cmr.earthdata.nasa.gov/search/granules.json",
        {
            "collection_concept_id": "C2777436413-ASF",
            "temporal": "2026-08-01T00:00:00Z,2026-09-26T00:00:00Z",
            "bounding_box": "84.7,27.75,85.65,28.45",
            "page_size": "1",
        },
    )
    queries = {
        "asf_exact_grd": asf_url,
        "cdse_rtc_window": cdse_window,
        "cdse_rtc_latest": cdse_latest,
        "cmr_opera_nepal_window": cmr_url,
    }
    responses = {key: fetch_json(url) for key, url in queries.items()}
    asf_features = responses["asf_exact_grd"][1].get("features", [])
    asf_exact = [
        {
            "scene_name": item.get("properties", {}).get("sceneName"),
            "start_utc": item.get("properties", {}).get("startTime"),
            "platform": item.get("properties", {}).get("platform"),
            "processing_level": item.get("properties", {}).get("processingLevel"),
            "flight_direction": item.get("properties", {}).get("flightDirection"),
        }
        for item in asf_features
    ]
    for scene in ASF_SCENES:
        if not any(row["scene_name"] == scene and row["processing_level"] == "GRD_HD" for row in asf_exact):
            raise RuntimeError("exact ASF GRD metadata missing")

    cdse_result = responses["cdse_rtc_window"][1]
    cdse_latest_result = responses["cdse_rtc_latest"][1]
    cmr_result = responses["cmr_opera_nepal_window"][1]
    receipt = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-EXTERNAL-RTC-ROUTE-FEASIBILITY-001-LOCAL",
        "status": "public_metadata_research_only_no_source_adoption",
        "retrieved_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "query_responses": {
            key: {
                "url": url,
                "payload_ref": f"scratch/external-rtc-feasibility-001/{key}.json",
                "payload_sha256": hashlib.sha256(responses[key][0]).hexdigest(),
                "payload_bytes": len(responses[key][0]),
            }
            for key, url in queries.items()
        },
        "asf_exact_scene_rows": asf_exact,
        "cdse_sentinel_1_rtc_window_count": cdse_result.get("@odata.count"),
        "cdse_sentinel_1_rtc_latest_count": cdse_latest_result.get("@odata.count"),
        "cdse_sentinel_1_rtc_latest_item": cdse_latest_result.get("value", [])[:1],
        "cmr_opera_nepal_window_rows": len(cmr_result.get("feed", {}).get("entry", [])),
        "assertions": {
            "requests_authenticated": False,
            "product_bytes_acquired": False,
            "hyp3_job_submitted": False,
            "new_source_adopted": False,
            "project_radar_pixels_read": False,
            "baseline_or_change_analysis": False,
        },
    }
    PAYLOAD_ROOT.mkdir(parents=True, exist_ok=False)
    for key, (body, _) in responses.items():
        with (PAYLOAD_ROOT / f"{key}.json").open("xb") as output:
            output.write(body)
    with RECEIPT.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(receipt, output, ensure_ascii=False, indent=2)
        output.write("\n")
    print("PASS: public metadata captured; no product or job action")


if __name__ == "__main__":
    main()
