"""Prepare an unpublished source assessment for seven exact DEM candidates."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "records/source-gates/m2-radar-event-pair-seven-dem-source-assessment-001.json"
INPUTS = {
    "records/source-manifest.json": "6c67a1a6cb3411bd9ccab5f837e2c060757ddc5f1317f171bc5f62f9b1a22eef",
    "records/observations/m2-radar-event-pair-catalog-triage-001.json": "5c19d4edc3210ac7474ffc58aa2224801dd57ff32db9a51e386e48cee02f76db",
    "records/observations/m2-radar-dem-swath-catalog-001.json": "ed2c7653a656e7eb274d2f1fc1e510ec48d065112b5fbeab8986548240b17f83",
    "records/observations/m2-radar-dem-candidate-heads-001.json": "41a3dfece724e2c6177afcdcd20fff4f07368f2de767bb53deedab3563b6ccc8",
    "records/observations/m2-radar-dem-license-recheck-001.json": "cb903c464a72cc729ff103b11f19b2756f7af1869e0e1c2d37952eb24a4a093a",
    "records/source-gates/m2-dem-amendment-approval.json": "6d1fc7e05854bc149ace177d89e84a7651cc049efd530cab650a9464222769d0",
}
PAIR = {"M1-SRC-002", "M1-SRC-005"}


def evidence(kind, locator, note, observed_at=None):
    item = {"type": kind, "locator": locator, "note": note}
    if observed_at:
        item["observed_at"] = observed_at
    return item


def criterion(name, note, items, live=False):
    return {"id": name, "required": True, "requires_live": live, "status": "pass", "evidence": items, "note": note}


def main():
    bindings = []
    for ref, expected in INPUTS.items():
        actual = hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Frozen input identity changed: {ref}")
        bindings.append({"ref": ref, "sha256": actual})

    swath = json.loads((ROOT / "records/observations/m2-radar-dem-swath-catalog-001.json").read_text(encoding="utf-8"))
    heads = json.loads((ROOT / "records/observations/m2-radar-dem-candidate-heads-001.json").read_text(encoding="utf-8"))
    license_check = json.loads((ROOT / "records/observations/m2-radar-dem-license-recheck-001.json").read_text(encoding="utf-8"))
    cells = {(row["latitude"], row["longitude"]) for row in swath["intersecting_cells"] if not row["already_approved"] and PAIR.intersection(row["source_ids"])}
    if cells != {(27, 86), (28, 83), (28, 86), (29, 83), (29, 84), (29, 85), (29, 86)}:
        raise ValueError("Event-pair DEM candidate cell set changed")
    head_by_item = {row["item_id"]: row for row in heads["observations"]}
    stac_by_item = {row["item_id"]: row for row in swath["public_stac_observations"]}
    assets = []
    for lat, lon in sorted(cells):
        item_id = f"Copernicus_DSM_COG_10_N{lat:02d}_00_E{lon:03d}_00_DEM"
        head = head_by_item[item_id]
        stac = stac_by_item[item_id]
        if head["http_status"] != 200 or stac["http_status"] != 200 or head["redirect_followed"] or head["response_body_read"]:
            raise ValueError(f"Incomplete public metadata observation: {item_id}")
        assets.append({
            "item_id": item_id,
            "cell_wgs84": [lon, lat, lon + 1, lat + 1],
            "stac_item_url": stac["stac_item_url"],
            "anonymous_https_url": head["anonymous_https_url"],
            "observed_head_content_length_bytes": head["content_length_bytes"],
            "observed_head_etag": head["etag"],
            "head_checked_at_utc": head["checked_at_utc"],
            "stac_checked_at_utc": stac["checked_at_utc"],
            "payload_acquired": False,
            "payload_sha256": None,
        })

    if len(assets) != 7 or sum(row["observed_head_content_length_bytes"] for row in assets) != 273055703:
        raise ValueError("Exact seven-candidate byte estimate changed")
    if license_check["observed_document_sha256"] != "9cd37d37ea654bbcaf0a2e059e6a3a5b5f76072824d8dd860ccf274ada8951bd":
        raise ValueError("Previously accepted license document identity changed")

    source = {
        "source_id": "M2-DEM-ASC-R085-SEVEN-CANDIDATES",
        "name": "Seven exact Copernicus DEM GLO-30 COG candidate cells for M1-SRC-002/005 full catalog swaths",
        "locator": "https://stac.dataspace.copernicus.eu/v1/collections/cop-dem-glo-30-dged-cog",
        "exact_assets": assets,
        "criteria": [
            criterion("identity", "The seven item IDs and byte estimates are exact metadata bindings; no payload identity is established.", [evidence("static", "records/observations/m2-radar-dem-swath-catalog-001.json", "Exact seven cells intersect the event-pair catalog polygons."), evidence("static", "records/observations/m2-radar-dem-candidate-heads-001.json", "Exact public asset URL, length, and ETag observations.")]),
            criterion("authority", "Official CDSE STAC identifies the Copernicus DEM collection; the AWS mirror is a distribution route, not the publisher.", [evidence("live", assets[0]["stac_item_url"], "Official STAC item observation retained in the bound swath catalog.", stac_by_item[assets[0]["item_id"]]["checked_at_utc"])], live=True),
            criterion("access", "Yesterday's anonymous HEAD observations returned 200 without redirects or body reads; recheck immediately before any approved acquisition.", [evidence("live", assets[0]["anonymous_https_url"], "All seven exact anonymous HEAD observations are retained in the bound candidate-head record.", head_by_item[assets[0]["item_id"]]["checked_at_utc"])], live=True),
            criterion("rights", "The same public license document bytes were rechecked, but owner approval covered only four earlier tiles; seven new requests need an explicit scope decision.", [evidence("live", license_check["document_url"], "Exact license PDF SHA-256 matches the owner's previously accepted document; acquisition scope remains four tiles.", license_check["checked_at_utc"]), evidence("static", "records/source-gates/m2-dem-amendment-approval.json", "Prior owner acceptance and its four-tile limit.")], live=True),
            criterion("provenance", "Official STAC metadata and the previously observed anonymous distribution mirror bind each candidate locator; bytes have not entered custody.", [evidence("static", "records/observations/m2-radar-dem-swath-catalog-001.json", "Official item identities and bboxes."), evidence("static", "records/observations/m2-radar-dem-candidate-heads-001.json", "Mirror asset metadata; no redirect or body read.")]),
            criterion("integrity", "For candidate acquisition only, require fresh no-redirect HEAD, expected length, complete byte-zero download, SHA-256, GeoTIFF structure, no-replace non-Git promotion, and a durable receipt before any conversion or use; ETag is not accepted as a content checksum.", [evidence("static", "records/observations/m2-radar-dem-candidate-heads-001.json", "Expected length and ETag are pre-acquisition comparators; post-acquisition checks remain pending.")]),
            criterion("fitness", "The seven one-degree cells cover the public catalog swaths missing from the approved four-tile set for this pair. This establishes only acquisition-candidate fit, not valid DEM pixels, exact SAR raster extent, GTC fitness, or elevation accuracy.", [evidence("static", "records/observations/m2-radar-event-pair-catalog-triage-001.json", "Event AOI and DEM-box overlap is catalog geometry only."), evidence("static", "records/observations/m2-radar-dem-swath-catalog-001.json", "Seven additional cells intersect M1-SRC-002/005 catalog swaths.")]),
            criterion("privacy-security", "Public elevation tiles contain no identified personal records. Candidate payloads require non-Git custody and structural checks; no credentials or account action are planned.", [evidence("static", "records/source-gates/m2-dem-candidate-manifest.json", "Same public DEM product family and controlled external-custody pattern.")]),
        ],
    }
    record = {
        "contract_version": "source-gate/v2",
        "assessment_id": "NEPAL-M2-RADAR-EVENT-PAIR-SEVEN-DEM-SOURCE-ASSESSMENT-001",
        "assessed_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "authority": {"mode": "not_granted", "authority_ref": "", "authorized_actions": [], "expires_at_utc": None},
        "intended_use": {"summary": "Evaluate acquisition of seven exact DEM candidates to test full-swath terrain-processing fitness for the approved M1-SRC-002/005 event pair; no payload access or processing now.", "planned_actions": ["metadata review", "download seven exact DEM payloads to controlled non-Git custody"]},
        "input_bindings": bindings,
        "sources": [source],
        "decision": {"status": "ready", "blocking_reasons": [], "live_verification_pending": [], "approved_actions": ["metadata review"]},
        "write_boundary": {"permitted_without_further_authorization": ["read already-public metadata", "record local zero-decision assessment"], "requires_explicit_authorization": ["download seven exact DEM payloads", "convert or use DEM pixels", "change the frozen radar method or source order", "run ArcPy on project data", "publish review or derived data"]},
        "candidate_summary": {"exact_asset_count": 7, "observed_head_total_bytes": 273055703, "license_document_sha256": license_check["observed_document_sha256"], "prior_owner_approval_tile_count": 4, "new_tile_acquisition_authorized": False, "payload_integrity_verified": False, "valid_pixel_fitness_established": False, "full_radar_processing_route_authorized": False},
    }
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(OUTPUT)


if __name__ == "__main__":
    main()
