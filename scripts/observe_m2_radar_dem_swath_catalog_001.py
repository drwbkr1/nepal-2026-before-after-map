#!/usr/bin/env python3
"""Local zero-decision public STAC inventory for DEM cells touching six SAR footprints."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import urllib.error
import urllib.request
from pathlib import Path

from audit_m2_radar_gtc_public_coverage_001 import clip_to_box, sha256, spherical_equal_area_km2


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REF = "records/source-manifest.json"
DEM_REF = "records/source-gates/m2-dem-candidate-manifest.json"
RECOVERY_REF = "records/processing/m2-radar-esri-sequence-recovery-005-terminal-reconciliation.json"
PROBE_REF = "records/processing/m2-radar-gtc-dem-isolation-probe-001-terminal-reconciliation.json"
OLD_CODE_REF = "scripts/m2_radar_esri_sequence_processing_005.py"
NEW_CODE_REF = "scripts/m2_radar_gtc_dem_isolation_probe_001.py"
OUTPUT_REF = "records/observations/m2-radar-dem-swath-catalog-001.json"
COLLECTION = "cop-dem-glo-30-dged-cog"
SOURCE_IDS = tuple(f"M1-SRC-{number:03d}" for number in range(1, 7))
OLD_DEM_IDS = tuple(f"M2-DEM-{number:03d}" for number in range(1, 5))
MAX_METADATA_BYTES = 2_000_000


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def candidate_cells() -> tuple[list[dict[str, object]], list[tuple[int, int]]]:
    source_manifest = json.loads((ROOT / SOURCE_REF).read_text(encoding="utf-8"))
    dem_manifest = json.loads((ROOT / DEM_REF).read_text(encoding="utf-8"))
    sources = [row for row in source_manifest["records"] if row.get("source_id") in SOURCE_IDS]
    if tuple(row["source_id"] for row in sources) != SOURCE_IDS:
        raise ValueError("six approved radar source identities or order differ")
    dem = dem_manifest["records"]
    if tuple(row["source_id"] for row in dem) != OLD_DEM_IDS:
        raise ValueError("four approved DEM identities or order differ")
    approved = {(int(row["bbox_wgs84"][1]), int(row["bbox_wgs84"][0])) for row in dem}
    if approved != {(27, 84), (27, 85), (28, 84), (28, 85)}:
        raise ValueError("approved four-tile grid differs")
    polygons = []
    xs, ys = [], []
    for row in sources:
        footprint = row["footprint"]
        if footprint.get("type") != "Polygon" or len(footprint.get("coordinates", [])) != 1:
            raise ValueError("unexpected source catalog polygon")
        ring = [tuple(map(float, point)) for point in footprint["coordinates"][0]]
        if ring[0] != ring[-1]:
            raise ValueError("source catalog polygon is not closed")
        ring.pop()
        polygons.append((row["source_id"], ring))
        xs.extend(point[0] for point in ring)
        ys.extend(point[1] for point in ring)
    touched = []
    for latitude in range(math.floor(min(ys)), math.ceil(max(ys))):
        for longitude in range(math.floor(min(xs)), math.ceil(max(xs))):
            bbox = (longitude, latitude, longitude + 1, latitude + 1)
            source_ids = [source_id for source_id, ring in polygons if spherical_equal_area_km2(clip_to_box(ring, bbox)) > 0]
            if source_ids:
                touched.append({"latitude": latitude, "longitude": longitude, "source_ids": source_ids, "already_approved": (latitude, longitude) in approved})
    return touched, sorted((row["latitude"], row["longitude"]) for row in touched if not row["already_approved"])


def read_stac(latitude: int, longitude: int) -> dict[str, object]:
    item_id = f"Copernicus_DSM_COG_10_N{latitude:02d}_00_E{longitude:03d}_00_DEM"
    url = f"https://stac.dataspace.copernicus.eu/v1/collections/{COLLECTION}/items/{item_id}"
    request = urllib.request.Request(url, headers={"Accept": "application/geo+json", "User-Agent": "Nepal-evidence-map-source-review/1.0"})
    observation: dict[str, object] = {"item_id": item_id, "stac_item_url": url, "checked_at_utc": now_utc()}
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=20) as response:
            raw = response.read(MAX_METADATA_BYTES + 1)
            if len(raw) > MAX_METADATA_BYTES:
                raise ValueError("public metadata response exceeded byte cap")
            body = json.loads(raw)
            observation.update({
                "http_status": response.status,
                "response_sha256": hashlib.sha256(raw).hexdigest(),
                "response_bytes": len(raw),
                "returned_item_id": body.get("id"),
                "returned_collection": body.get("collection"),
                "returned_bbox_wgs84": body.get("bbox"),
                "asset_keys": sorted(body.get("assets", {})),
                "redirect_followed": False,
            })
    except urllib.error.HTTPError as exc:
        observation.update({"http_status": exc.code, "error_type": "HTTPError", "redirect_followed": False})
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        observation.update({"http_status": None, "error_type": type(exc).__name__, "redirect_followed": False})
    return observation


def main() -> int:
    output = ROOT / OUTPUT_REF
    if output.exists():
        raise SystemExit("public swath catalog observation already exists")
    touched, additional = candidate_cells()
    if len(touched) != 18 or len(additional) != 14:
        raise SystemExit("candidate geometry count differs from reviewed source footprints")
    observations = [read_stac(latitude, longitude) for latitude, longitude in additional]
    value = {
        "schema_version": "1.0",
        "observation_id": "NEPAL-M2-RADAR-DEM-SWATH-CATALOG-001",
        "observed_at_utc": now_utc(),
        "status": "local_zero_decision_public_metadata_inventory_only",
        "input_bindings": [{"ref": ref, "sha256": sha256(ref)} for ref in (SOURCE_REF, DEM_REF, RECOVERY_REF, PROBE_REF, OLD_CODE_REF, NEW_CODE_REF)],
        "method": "Clip six approved public SAR catalog polygons against integer WGS84 one-degree cells and inspect public CDSE STAC item metadata for cells not in the four-tile approval. No DEM or SAR payload was requested or read.",
        "intersecting_cells": touched,
        "additional_candidate_cells": [{"latitude": latitude, "longitude": longitude} for latitude, longitude in additional],
        "public_stac_observations": observations,
        "controlled_comparison_limitation": "Recovery-005 used a saved-CRF path, a DEM and geoid argument, and a 10m bilinear snap environment; the successful no-DEM probe reopened the saved CRF as a Raster in a separate process without that environment. The changed variables prevent attributing the earlier failure to DEM coverage or bytes.",
        "official_esri_guidance": {
            "gtc_url": "https://doc.esri.com/en/arcgis-pro/latest/tool-reference/image-analyst/apply-geometric-terrain-correction.html",
            "rtf_url": "https://doc.esri.com/en/arcgis-pro/latest/tool-reference/image-analyst/apply-radiometric-terrain-flattening.html",
            "checked_at_utc": now_utc(),
            "summary": "Esri says GTC without a DEM uses metadata tie points and directs users to specify a DEM for land scenes. GTC can interpolate outside a partial DEM; RTF emits NoData outside DEM extent. These rules do not establish the current input's valid-pixel coverage or the earlier ERROR 000425 cause.",
        },
        "boundaries": {
            "new_dem_tiles_selected_or_approved": False,
            "additional_tiles_available_or_fit": False,
            "dem_payload_or_source_pixels_read": False,
            "historical_failure_cause_established": False,
            "scientific_radar_output_admitted": False,
            "acquisition_or_processing_authorized": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"status": value["status"], "intersecting_cells": len(touched), "additional_candidates": len(additional), "http_200": sum(item.get("http_status") == 200 for item in observations)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
