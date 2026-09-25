#!/usr/bin/env python3
"""One bounded public CDSE Sentinel-2 L2A metadata inventory after radar stop."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any
import json
import urllib.parse
import urllib.request

from shapely.geometry import shape


ROOT = Path(__file__).resolve().parents[1]
AOI = ROOT / "config/aoi/approved-study-areas.geojson"
OUTPUT = ROOT / "records/observations/m2-map-route-feasibility-001-optical-fallback-catalog.json"
ENDPOINT = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
WINDOWS = (
    ("before", "2026-08-01T00:00:00.000Z", "2026-08-26T00:00:00.000Z"),
    ("after", "2026-08-27T00:00:00.000Z", "2026-09-25T00:00:00.000Z"),
)
MAX_PER_WINDOW = 100


def digest(value: bytes) -> str:
    return sha256(value).hexdigest()


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def overview_wkt(aoi: dict[str, Any]) -> str:
    overview = next(feature for feature in aoi["features"] if feature["properties"]["aoi_id"] == "AOI-OVERVIEW")
    if overview["geometry"]["type"] != "Polygon":
        raise ValueError("approved overview is not a polygon")
    rings = overview["geometry"]["coordinates"]
    if len(rings) != 1 or rings[0][0] != rings[0][-1]:
        raise ValueError("approved overview must have one closed ring")
    coordinates = ",".join(f"{float(x):.8f} {float(y):.8f}" for x, y in rings[0])
    return f"POLYGON(({coordinates}))"


def query_url(wkt: str, start: str, end_exclusive: str) -> str:
    filter_text = (
        "Collection/Name eq 'SENTINEL-2' and "
        "Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' "
        "and att/OData.CSC.StringAttribute/Value eq 'S2MSI2A') and "
        f"OData.CSC.Intersects(area=geography'SRID=4326;{wkt}') and "
        f"ContentDate/Start ge {start} and ContentDate/Start lt {end_exclusive}"
    )
    return ENDPOINT + "?" + urllib.parse.urlencode({
        "$filter": filter_text,
        "$orderby": "ContentDate/Start asc",
        "$top": str(MAX_PER_WINDOW),
        "$count": "true",
        "$expand": "Attributes",
    })


def attributes(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {item["Name"]: item.get("Value") for item in items if isinstance(item.get("Name"), str)}


def normalize_rows(items: list[dict[str, Any]], features: list[dict[str, Any]], window: str) -> list[dict[str, Any]]:
    areas = {feature["properties"]["aoi_id"]: shape(feature["geometry"]) for feature in features}
    rows = []
    for item in items:
        name, identifier, footprint = item.get("Name"), item.get("Id"), item.get("GeoFootprint")
        if not isinstance(name, str) or not isinstance(identifier, str) or not isinstance(footprint, dict):
            raise ValueError("catalog row missing product identity or footprint")
        if "_MSIL2A_" not in name:
            raise ValueError("catalog returned non-L2A product")
        geometry = shape(footprint)
        if geometry.is_empty or not geometry.is_valid:
            raise ValueError("catalog returned invalid footprint")
        attrs = attributes(item.get("Attributes", []))
        if attrs.get("productType") != "S2MSI2A":
            raise ValueError("catalog returned unexpected productType")
        intersections = {aoi_id: bool(geometry.intersects(area)) for aoi_id, area in areas.items()}
        if not intersections["AOI-OVERVIEW"]:
            raise ValueError("catalog returned footprint outside approved overview")
        rows.append({
            "window": window,
            "provider_product_id": identifier,
            "name": name,
            "content_start_utc": item.get("ContentDate", {}).get("Start"),
            "content_end_utc": item.get("ContentDate", {}).get("End"),
            "online": item.get("Online"),
            "catalog_cloud_cover_percent": attrs.get("cloudCover"),
            "processing_baseline": attrs.get("processingBaseline"),
            "relative_orbit_number": attrs.get("relativeOrbitNumber"),
            "platform": attrs.get("platformShortName"),
            "aoi_footprint_intersects": intersections,
            "footprint": footprint,
            "pixel_fitness": "not_inspected",
            "source_adoption": "not_authorized",
        })
    return rows


def run(fetch: Any = None) -> dict[str, Any]:
    if OUTPUT.exists():
        raise FileExistsError("optical fallback output already exists; no replacement")
    aoi_bytes = AOI.read_bytes()
    aoi = json.loads(aoi_bytes)
    if aoi["properties"]["status"] != "approved_m1_search_review":
        raise ValueError("approved AOI status mismatch")
    wkt = overview_wkt(aoi)
    if fetch is None:
        def fetch(url: str) -> bytes:
            request = urllib.request.Request(url, headers={
                "User-Agent": "nepal-2026-before-after-map/1.0 metadata-only",
                "Accept": "application/json",
            })
            with urllib.request.urlopen(request, timeout=60) as response:
                if response.status != 200:
                    raise ValueError("catalog non-200 response")
                return response.read(12_000_001)
    requests = []
    rows = []
    status = "catalog_metadata_inventory_complete"
    for window, start, end in WINDOWS:
        url = query_url(wkt, start, end)
        body = fetch(url)
        if len(body) > 12_000_000:
            raise ValueError("catalog response exceeds metadata size limit")
        payload = json.loads(body)
        values = payload.get("value")
        count = payload.get("@odata.count")
        if not isinstance(values, list) or len(values) > MAX_PER_WINDOW:
            raise ValueError("catalog row limit or schema violation")
        if count is not None and (not isinstance(count, int) or count < len(values)):
            raise ValueError("catalog count inconsistent")
        normalized = normalize_rows(values, aoi["features"], window)
        if any(not (start <= row["content_start_utc"] < end) for row in normalized):
            raise ValueError("catalog row outside approved UTC window")
        if len(values) == MAX_PER_WINDOW and (count is None or count > len(values)):
            status = "catalog_metadata_inventory_truncated_at_200_maximum"
        requests.append({"window": window, "url": url, "response_sha256": digest(body),
                         "returned_rows": len(values), "reported_total_rows": count})
        rows.extend(normalized)
    if len(rows) > 200 or len({row["provider_product_id"] for row in rows}) != len(rows):
        raise ValueError("catalog maximum or duplicate identity violation")
    result = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-MAP-ROUTE-FEASIBILITY-001-OPTICAL-FALLBACK-CATALOG",
        "status": status,
        "retrieved_at_utc": now_utc(),
        "catalog_endpoint": ENDPOINT,
        "request_authentication": "none",
        "approved_aoi_ref": "config/aoi/approved-study-areas.geojson",
        "approved_aoi_sha256": digest(aoi_bytes),
        "geometry_query": "approved AOI-OVERVIEW polygon; per-row exact footprint intersects all approved AOIs",
        "requests": requests,
        "row_count": len(rows),
        "rights_review": {
            "cdse_terms": "https://dataspace.copernicus.eu/terms-and-conditions",
            "sentinel_legal_notice": "https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice",
            "status": "public Sentinel metadata only; any new product adoption or acquisition requires later exact source and current-terms review",
            "third_party_quicklooks_published": False,
        },
        "comparability_review": "Catalog footprint and cloud percentage are tile-level metadata, not AOI clear-pixel, registration, or scientific suitability evidence. No date or product selected.",
        "rows": rows,
        "assertions": {"product_downloaded": False, "pixels_read": False,
                       "new_source_adopted": False, "change_analysis_executed": False},
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    return result


if __name__ == "__main__":
    result = run()
    print(json.dumps({"status": result["status"], "row_count": result["row_count"]}))
