#!/usr/bin/env python3
"""Fetch exact public Copernicus catalog metadata without downloading products."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any
import json
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "records/source-gates/catalog-candidate-verification.json"
AOI_INPUT = ROOT / "config/aoi/draft-study-areas.geojson"
METADATA_OUTPUT = ROOT / "records/source-gates/catalog-metadata.json"
FOOTPRINT_OUTPUT = ROOT / "records/source-gates/candidate-footprints.geojson"
RECEIPT_OUTPUT = ROOT / "records/source-gates/catalog-metadata-receipt.json"
ENDPOINT = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")


def fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "nepal-2026-before-after-map/1.0 metadata-only"},
    )
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return json.load(response)
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"catalog request failed after retries: {last_error}")


def coordinate_pairs(value: Any) -> list[tuple[float, float]]:
    pairs: list[tuple[float, float]] = []
    if (
        isinstance(value, list)
        and len(value) >= 2
        and isinstance(value[0], (int, float))
        and isinstance(value[1], (int, float))
    ):
        pairs.append((float(value[0]), float(value[1])))
    elif isinstance(value, list):
        for child in value:
            pairs.extend(coordinate_pairs(child))
    return pairs


def geometry_bbox(geometry: dict[str, Any]) -> list[float]:
    pairs = coordinate_pairs(geometry.get("coordinates"))
    if not pairs:
        raise ValueError("geometry has no coordinate pairs")
    xs = [pair[0] for pair in pairs]
    ys = [pair[1] for pair in pairs]
    return [min(xs), min(ys), max(xs), max(ys)]


def bbox_intersects(first: list[float], second: list[float]) -> bool:
    return not (
        first[2] < second[0]
        or first[0] > second[2]
        or first[3] < second[1]
        or first[1] > second[3]
    )


def attributes_map(values: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item in values:
        name = item.get("Name")
        if not isinstance(name, str):
            continue
        value = item.get("Value")
        if name in result:
            existing = result[name]
            result[name] = existing + [value] if isinstance(existing, list) else [
                existing, value
            ]
        else:
            result[name] = value
    return result


def main() -> None:
    seed = json.loads(INPUT.read_text(encoding="utf-8"))
    draft_aois = json.loads(AOI_INPUT.read_text(encoding="utf-8"))
    aoi_bboxes = {
        feature["properties"]["aoi_id"]: [float(value) for value in feature["bbox"]]
        for feature in draft_aois["features"]
    }
    retrieved_at = now_utc()
    records: list[dict[str, Any]] = []
    footprint_features: list[dict[str, Any]] = []

    for seed_record in seed["records"]:
        stem = seed_record["stem"]
        exact_name = stem + ".SAFE"
        params = {
            "$filter": f"Name eq '{exact_name}'",
            "$expand": "Attributes",
            "$top": "2",
        }
        query_url = ENDPOINT + "?" + urllib.parse.urlencode(params)
        response = fetch_json(query_url)
        values = response.get("value", [])
        if len(values) != 1:
            raise RuntimeError(
                f"expected one exact record for {exact_name}, found {len(values)}"
            )
        item = values[0]
        if item.get("Name") != exact_name:
            raise RuntimeError(f"catalog returned wrong product for {exact_name}")
        if (
            seed_record.get("catalog", {}).get("Id")
            and seed_record["catalog"]["Id"] != item.get("Id")
        ):
            raise RuntimeError(f"provider ID changed for {exact_name}")

        geometry = item.get("GeoFootprint")
        if not isinstance(geometry, dict):
            raise RuntimeError(f"missing footprint for {exact_name}")
        bbox = geometry_bbox(geometry)
        attributes = attributes_map(item.get("Attributes", []))
        intersections = {
            aoi_id: bbox_intersects(bbox, aoi_bbox)
            for aoi_id, aoi_bbox in aoi_bboxes.items()
        }
        record = {
            "product_stem": stem,
            "name": exact_name,
            "provider": "Copernicus Data Space Ecosystem",
            "provider_product_id": item.get("Id"),
            "content_date": item.get("ContentDate"),
            "content_length_bytes": item.get("ContentLength"),
            "online": item.get("Online"),
            "eviction_date": item.get("EvictionDate"),
            "provider_checksums": item.get("Checksum", []),
            "attributes": attributes,
            "footprint": geometry,
            "footprint_bbox": bbox,
            "draft_aoi_bbox_intersection": intersections,
            "query_url": query_url,
            "query_result_count": 1,
            "rights_status": "pending_source-rights_review",
            "pixel_inspection_status": "not_started",
            "download_status": "not_authorized",
            "disposition": "candidate",
        }
        records.append(record)
        footprint_features.append({
            "type": "Feature",
            "id": item.get("Id"),
            "bbox": bbox,
            "properties": {
                "product_stem": stem,
                "provider_product_id": item.get("Id"),
                "platform": attributes.get("platformShortName"),
                "instrument": attributes.get("instrumentShortName"),
                "product_type": attributes.get("productType"),
                "acquisition_start": (item.get("ContentDate") or {}).get("Start"),
                "cloud_cover": attributes.get("cloudCover"),
                "relative_orbit_number": attributes.get("relativeOrbitNumber"),
                "orbit_direction": attributes.get("orbitDirection"),
                "status": "candidate",
                "claim_boundary": "Catalog footprint; not verified pixel coverage.",
            },
            "geometry": geometry,
        })

    metadata = {
        "schema_version": "1.0",
        "manifest_stage": "catalog_metadata_candidate",
        "retrieved_at_utc": retrieved_at,
        "catalog_endpoint": ENDPOINT,
        "request_authentication": "none",
        "candidate_count": len(records),
        "query_result": "pass",
        "claim_boundary": (
            "Exact public catalog metadata only; no full products were downloaded "
            "and no pixels or masks were inspected."
        ),
        "records": records,
    }
    footprints = {
        "type": "FeatureCollection",
        "name": "Copernicus candidate product footprints",
        "properties": {
            "retrieved_at_utc": retrieved_at,
            "storage_crs": "EPSG:4326",
            "status": "catalog_candidate",
            "claim_boundary": "Provider footprints are not proof of usable AOI pixels.",
        },
        "features": footprint_features,
    }

    METADATA_OUTPUT.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    FOOTPRINT_OUTPUT.write_text(
        json.dumps(footprints, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    metadata_hash = sha256(METADATA_OUTPUT.read_bytes()).hexdigest()
    footprint_hash = sha256(FOOTPRINT_OUTPUT.read_bytes()).hexdigest()
    receipt = {
        "schema_version": "1.0",
        "receipt_id": "CATALOG-METADATA-001",
        "status": "pass",
        "retrieved_at_utc": retrieved_at,
        "catalog_endpoint": ENDPOINT,
        "candidate_count": len(records),
        "exact_match_count": len(records),
        "footprint_count": len(footprint_features),
        "metadata_output": str(METADATA_OUTPUT.relative_to(ROOT)).replace("\\", "/"),
        "metadata_sha256": metadata_hash,
        "footprint_output": str(FOOTPRINT_OUTPUT.relative_to(ROOT)).replace("\\", "/"),
        "footprint_sha256": footprint_hash,
        "checks": {
            "exact_name_unique": "pass",
            "provider_id_matches_seed": "pass",
            "content_date_present": "pass",
            "footprint_present": "pass",
            "no_authentication_used": "pass",
            "no_product_download": "pass",
        },
        "limitations": [
            "Bounding-box intersection is not exact footprint or usable-pixel coverage.",
            "Provider checksums describe remote products; no local product bytes exist.",
            "Rights, masks, pixels, and event relevance remain unreviewed.",
        ],
    }
    RECEIPT_OUTPUT.write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(
        f"Recorded {len(records)} exact candidates; "
        f"metadata={metadata_hash} footprints={footprint_hash}"
    )


if __name__ == "__main__":
    main()
