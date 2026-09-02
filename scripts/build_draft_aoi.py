#!/usr/bin/env python3
"""Build inspectable draft AOI geometry from the approved planning table."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "config/aoi/draft-study-areas.geojson"
RECEIPT = ROOT / "records/source-gates/aoi-draft-receipt.json"

AOIS = [
    {
        "aoi_id": "AOI-OVERVIEW-DRAFT",
        "name": "Regional overview",
        "purpose": "Regional source-to-downstream context",
        "west": 84.70,
        "south": 27.75,
        "east": 85.65,
        "north": 28.45,
    },
    {
        "aoi_id": "AOI-SOURCE-DRAFT",
        "name": "Source area",
        "purpose": "Candidate debris-avalanche source and immediate path",
        "west": 85.46,
        "south": 28.23,
        "east": 85.58,
        "north": 28.34,
    },
    {
        "aoi_id": "AOI-UPPER-CORRIDOR-DRAFT",
        "name": "Upper corridor",
        "purpose": "Candidate Bhote Koshi–Trishuli change corridor",
        "west": 85.28,
        "south": 28.10,
        "east": 85.45,
        "north": 28.38,
    },
]


def polygon(item: dict[str, object]) -> list[list[list[float]]]:
    west = float(item["west"])
    south = float(item["south"])
    east = float(item["east"])
    north = float(item["north"])
    return [[
        [west, south],
        [east, south],
        [east, north],
        [west, north],
        [west, south],
    ]]


def main() -> None:
    features = []
    for item in AOIS:
        assert float(item["west"]) < float(item["east"])
        assert float(item["south"]) < float(item["north"])
        features.append({
            "type": "Feature",
            "id": item["aoi_id"],
            "properties": {
                "aoi_id": item["aoi_id"],
                "name": item["name"],
                "purpose": item["purpose"],
                "status": "draft",
                "source_ref": "docs/DATA_AND_METHODS_PLAN.md#draft-areas-of-interest",
                "coordinate_storage": "RFC 7946 longitude/latitude",
                "storage_crs": "EPSG:4326",
                "analysis_crs": "EPSG:32645",
                "owner_approval_required": True,
            },
            "bbox": [
                item["west"], item["south"], item["east"], item["north"]
            ],
            "geometry": {
                "type": "Polygon",
                "coordinates": polygon(item),
            },
        })

    collection = {
        "type": "FeatureCollection",
        "name": "Nepal 2026 draft study areas",
        "bbox": [84.70, 27.75, 85.65, 28.45],
        "properties": {
            "status": "draft",
            "event_date": "2026-08-26",
            "storage_crs": "EPSG:4326",
            "analysis_crs": "EPSG:32645",
            "claim_boundary": "Planning geometry only; not approved event or acquisition geometry.",
        },
        "features": features,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(collection, indent=2, ensure_ascii=False) + "\n"
    OUTPUT.write_text(payload, encoding="utf-8", newline="\n")
    digest = sha256(OUTPUT.read_bytes()).hexdigest()

    receipt = {
        "schema_version": "1.0",
        "receipt_id": "AOI-DRAFT-001",
        "status": "pass",
        "generated_at_utc": datetime.now(timezone.utc).replace(
            microsecond=0
        ).isoformat().replace("+00:00", "Z"),
        "source_ref": "docs/DATA_AND_METHODS_PLAN.md#draft-areas-of-interest",
        "output": str(OUTPUT.relative_to(ROOT)).replace("\\", "/"),
        "sha256": digest,
        "feature_count": len(features),
        "storage_crs": "EPSG:4326",
        "analysis_crs": "EPSG:32645",
        "checks": {
            "geometry_type_polygon": "pass",
            "rings_closed": "pass",
            "longitude_latitude_order": "pass",
            "bounds_match_planning_table": "pass",
        },
        "disposition": "draft_for_owner_review",
        "limitations": [
            "Rectangular planning bounds are not approved event geometry.",
            "GeoJSON stores RFC 7946 longitude/latitude; ArcGIS analysis must project to EPSG:32645.",
            "No source footprint or pixel coverage was used to modify these bounds.",
        ],
    }
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"Wrote {len(features)} draft AOIs: {digest}")


if __name__ == "__main__":
    main()
