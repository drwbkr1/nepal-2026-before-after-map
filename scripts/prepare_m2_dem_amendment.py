#!/usr/bin/env python3
"""Capture metadata-only evidence and prepare a non-authorizing M2 DEM amendment."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
STAC_COLLECTION = "cop-dem-glo-30-dged-cog"
STAC_BASE = f"https://stac.dataspace.copernicus.eu/v1/collections/{STAC_COLLECTION}"
AWS_BASE = "https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com"
LICENSE_URL = "https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM/resources/license/License-COPDEM-30.pdf"
OFFICIAL_PAGES = (
    ("cdse_dem_documentation", "https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM.html"),
    ("cdse_stac_documentation", "https://documentation.dataspace.copernicus.eu/APIs/STAC.html"),
    ("aws_open_data_registry", "https://registry.opendata.aws/copernicus-dem/"),
    ("aws_dataset_readme", "https://copernicus-dem-30m.s3.amazonaws.com/readme.html"),
    ("copernicus_worlddem_30_license", LICENSE_URL),
)
TILE_IDS = (
    "Copernicus_DSM_COG_10_N27_00_E084_00_DEM",
    "Copernicus_DSM_COG_10_N27_00_E085_00_DEM",
    "Copernicus_DSM_COG_10_N28_00_E084_00_DEM",
    "Copernicus_DSM_COG_10_N28_00_E085_00_DEM",
)
USER_AGENT = "nepal-2026-before-after-map-dem-metadata/1.0"


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(relative: str) -> str:
    return sha256_bytes((ROOT / relative).read_bytes())


def fetch(url: str, *, method: str = "GET") -> tuple[bytes, dict[str, str], int]:
    request = urllib.request.Request(
        url,
        method=method,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/html,application/pdf,*/*"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read(), {key.casefold(): value for key, value in response.headers.items()}, response.status


def intersects(a: list[float], b: list[float]) -> bool:
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def load_aoi() -> tuple[list[dict[str, Any]], list[float]]:
    document = json.loads((ROOT / "config/aoi/approved-study-areas.geojson").read_text(encoding="utf-8"))
    areas = []
    all_x: list[float] = []
    all_y: list[float] = []
    for feature in document["features"]:
        coordinates = feature["geometry"]["coordinates"][0]
        xs = [point[0] for point in coordinates]
        ys = [point[1] for point in coordinates]
        bbox = [min(xs), min(ys), max(xs), max(ys)]
        all_x.extend(xs)
        all_y.extend(ys)
        areas.append({"aoi_id": feature["properties"]["aoi_id"], "bbox": bbox})
    return areas, [min(all_x), min(all_y), max(all_x), max(all_y)]


def live_capture(assessed_at: str) -> tuple[dict[str, Any], dict[str, Any]]:
    aoi_areas, overall_bbox = load_aoi()
    pages = []
    for page_id, url in OFFICIAL_PAGES:
        raw, headers, status = fetch(url)
        pages.append(
            {
                "page_id": page_id,
                "url": url,
                "http_status": status,
                "response_sha256": sha256_bytes(raw),
                "content_length_bytes": len(raw),
                "content_type": headers.get("content-type"),
                "last_modified": headers.get("last-modified"),
                "observed_at_utc": assessed_at,
            }
        )

    tiles = []
    for index, tile_id in enumerate(TILE_IDS, 1):
        item_url = f"{STAC_BASE}/items/{tile_id}"
        item_raw, item_headers, item_status = fetch(item_url)
        item = json.loads(item_raw)
        data_asset = item["assets"]["data"]
        aws_url = f"{AWS_BASE}/{tile_id}/{tile_id}.tif"
        _, object_headers, object_status = fetch(aws_url, method="HEAD")
        bbox = item["bbox"]
        tiles.append(
            {
                "source_id": f"M2-DEM-{index:03d}",
                "item_id": tile_id,
                "collection": item["collection"],
                "stac_item_url": item_url,
                "stac_http_status": item_status,
                "stac_response_sha256": sha256_bytes(item_raw),
                "stac_last_modified": item_headers.get("last-modified"),
                "bbox_wgs84": bbox,
                "intersects_approved_aois": [area["aoi_id"] for area in aoi_areas if intersects(bbox, area["bbox"])],
                "grid_code": item["properties"].get("grid:code"),
                "gsd_m": item["properties"].get("gsd"),
                "source_crs": item["properties"].get("proj:code"),
                "shape": data_asset.get("proj:shape"),
                "transform": data_asset.get("proj:transform"),
                "data_type": data_asset.get("data_type"),
                "media_type": data_asset.get("type"),
                "cdse_s3_href": data_asset.get("href"),
                "anonymous_https_url": aws_url,
                "anonymous_head": {
                    "http_status": object_status,
                    "content_length_bytes": int(object_headers["content-length"]),
                    "content_type": object_headers.get("content-type"),
                    "etag": object_headers.get("etag", "").strip('"'),
                    "last_modified": object_headers.get("last-modified"),
                    "accept_ranges": object_headers.get("accept-ranges"),
                    "version_id": object_headers.get("x-amz-version-id"),
                    "observed_at_utc": assessed_at,
                },
                "acquisition_status": "not_authorized",
                "local_sha256": None,
                "geotiff_validation": "not_started",
                "pixel_fitness": "unknown",
            }
        )
    receipt = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-DEM-METADATA-001",
        "status": "pass_metadata_only_no_dem_acquisition_authority",
        "assessed_at_utc": assessed_at,
        "request_mode": "public_metadata_get_and_anonymous_object_head_only",
        "approved_aoi": {
            "ref": "config/aoi/approved-study-areas.geojson",
            "sha256": sha256_file("config/aoi/approved-study-areas.geojson"),
            "overall_bbox_wgs84": overall_bbox,
            "areas": aoi_areas,
        },
        "official_pages": pages,
        "tiles": tiles,
        "assertions": {
            "exact_tile_count": len(tiles),
            "all_stac_items_found": all(tile["stac_http_status"] == 200 for tile in tiles),
            "all_anonymous_object_heads_found": all(tile["anonymous_head"]["http_status"] == 200 for tile in tiles),
            "combined_content_length_bytes": sum(tile["anonymous_head"]["content_length_bytes"] for tile in tiles),
            "payload_bytes_requested": False,
            "account_or_authentication_used": False,
            "license_accepted": False,
            "authority_created": False,
        },
        "limitations": [
            "HTTP HEAD and catalog metadata establish current object availability, not transferred-byte integrity or pixel fitness.",
            "The S3 ETag is retained as remote object metadata and is not asserted to be a content checksum.",
            "Copernicus DEM is a digital surface model; buildings, infrastructure, and vegetation may be represented.",
            "The four tiles and the DEM license are outside the active eight-product M2 approval.",
        ],
    }
    manifest = {
        "schema_version": "1.0",
        "manifest_id": "NEPAL-M2-DEM-CANDIDATE-MANIFEST-001",
        "status": "candidate_not_approved",
        "generated_at_utc": assessed_at,
        "intended_use": "Terrain correction and terrain-geometry screening for the approved Sentinel-1 route; no elevation-change analysis.",
        "selection_rule": "Include every 1 degree GLO-30 COG tile whose STAC bbox intersects any approved AOI bbox.",
        "approved_aoi_ref": receipt["approved_aoi"]["ref"],
        "approved_aoi_sha256": receipt["approved_aoi"]["sha256"],
        "metadata_receipt_ref": "records/source-gates/m2-dem-metadata-receipt.json",
        "metadata_receipt_sha256": None,
        "collection": STAC_COLLECTION,
        "distribution_route": {
            "provider": "AWS Registry of Open Data mirror managed by Sinergise",
            "method": "anonymous HTTPS GET after approval and fresh preflight",
            "account_required": False,
            "cost_expected": False,
            "redirect_policy": "refuse",
        },
        "license": {
            "name": "Licence for Copernicus DEM instance COP-DEM-GLO-30-F Global 30m Full, Free & Open",
            "url": LICENSE_URL,
            "document_sha256": next(page["response_sha256"] for page in pages if page["page_id"] == "copernicus_worlddem_30_license"),
            "acceptance_required": True,
            "acceptance_status": "not_accepted_by_this_workflow",
            "rights_summary": ["reproduction", "distribution", "communication to the general public", "adaptation, modification, and combination"],
            "obligations_summary": [
                "Use the prescribed source notice when distributing or communicating unmodified data.",
                "Use the prescribed produced-using notice for adapted or modified data.",
                "Include the prescribed no-liability notice for public distribution or communication.",
                "Do not imply official endorsement and bind downstream distributors to the same obligations.",
            ],
        },
        "records": tiles,
        "summary": {
            "tile_count": len(tiles),
            "combined_content_length_bytes": receipt["assertions"]["combined_content_length_bytes"],
            "combined_content_length_mib": round(receipt["assertions"]["combined_content_length_bytes"] / (1024**2), 3),
            "source_crs": sorted({tile["source_crs"] for tile in tiles}),
            "target_analysis_crs": "EPSG:32645",
        },
        "claim_boundary": {
            "availability_established": True,
            "license_acceptance_established": False,
            "transferred_bytes_verified": False,
            "dem_pixels_examined": False,
            "sentinel_terrain_correction_executed": False,
            "scientific_result_established": False,
        },
    }
    return receipt, manifest


def criterion(criterion_id: str, status: str, requires_live: bool, evidence: list[dict[str, Any]], note: str) -> dict[str, Any]:
    return {
        "id": criterion_id,
        "required": True,
        "requires_live": requires_live,
        "status": status,
        "evidence": evidence,
        "note": note,
    }


def build_gate(assessed_at: str, receipt: dict[str, Any], manifest_sha256: str) -> dict[str, Any]:
    sources = []
    static_manifest = {
        "type": "static",
        "locator": "records/source-gates/m2-dem-candidate-manifest.json",
        "note": f"Candidate manifest SHA-256 {manifest_sha256} binds the four exact tile records and AOI intersections.",
    }
    license_page = next(page for page in receipt["official_pages"] if page["page_id"] == "copernicus_worlddem_30_license")
    registry_page = next(page for page in receipt["official_pages"] if page["page_id"] == "aws_open_data_registry")
    dem_page = next(page for page in receipt["official_pages"] if page["page_id"] == "cdse_dem_documentation")
    for tile in receipt["tiles"]:
        stac_live = {
            "type": "live",
            "locator": tile["stac_item_url"],
            "observed_at": assessed_at,
            "note": f"Official STAC item returned HTTP 200 with response SHA-256 {tile['stac_response_sha256']}.",
        }
        head_live = {
            "type": "live",
            "locator": tile["anonymous_https_url"],
            "observed_at": assessed_at,
            "note": f"Anonymous HEAD returned HTTP 200, {tile['anonymous_head']['content_length_bytes']} bytes, ETag {tile['anonymous_head']['etag']}, and Accept-Ranges {tile['anonymous_head']['accept_ranges']}.",
        }
        license_live = {
            "type": "live",
            "locator": LICENSE_URL,
            "observed_at": assessed_at,
            "note": f"The exact three-page license was fetched for review with SHA-256 {license_page['response_sha256']}; Article 1 requires user acceptance.",
        }
        sources.append(
            {
                "source_id": tile["source_id"],
                "name": tile["item_id"],
                "locator": tile["anonymous_https_url"],
                "criteria": [
                    criterion("identity", "pass", True, [stac_live, static_manifest], "Exact item, collection, bbox, grid code, COG asset name, and dimensions are bound."),
                    criterion("authority", "pass", True, [stac_live, {"type": "live", "locator": "https://registry.opendata.aws/copernicus-dem/", "observed_at": assessed_at, "note": f"AWS Registry response SHA-256 {registry_page['response_sha256']} identifies the public GLO-30 bucket and manager."}], "CDSE is the primary catalog and the AWS Registry documents the public mirror."),
                    criterion("access", "pass", True, [head_live], "The exact object is currently reachable without an AWS account; acquisition remains unauthorized."),
                    criterion("rights", "pass", True, [license_live], "The license grants the needed use rights without charge but imposes acceptance, notices, non-endorsement, and downstream obligations."),
                    criterion("provenance", "pass", True, [stac_live, head_live, static_manifest], "The CDSE item and AWS object share the exact tile identity; byte equivalence remains for post-transfer verification."),
                    criterion("integrity", "pass", True, [head_live, static_manifest], "Content length, ETag, and last-modified metadata are captured; local SHA-256 and GeoTIFF checks are mandatory after acquisition."),
                    criterion("fitness", "pass", True, [stac_live, {"type": "live", "locator": "https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM.html", "observed_at": assessed_at, "note": f"Official DEM documentation response SHA-256 {dem_page['response_sha256']} identifies the dataset as a 30 m DSM usable for Sentinel-1 orthorectification."}], "Fit for controlled acquisition and terrain-correction evaluation only; vertical datum, voids, artifacts, and result quality remain untested."),
                    criterion("privacy-security", "pass", False, [static_manifest], "Public terrain data contain no project personal data; payloads remain untrusted and outside Git until verified."),
                    criterion("terms-acceptance", "unknown", False, [license_live], "No person accepted the exact license in this metadata-only preparation stage."),
                    criterion("scope-authority", "unknown", False, [{"type": "static", "locator": "contracts/milestone-002.json", "note": "The active M2 contract permits only the eight exact reviewed Sentinel products and forbids new terms acceptance or additional products."}], "A hash-bound owner amendment is required before any DEM payload request or license acceptance."),
                ],
            }
        )
    return {
        "contract_version": "source-gate/v1",
        "assessment_id": "NEPAL-M2-DEM-SOURCE-GATE-001",
        "assessed_at": assessed_at,
        "authority": {
            "mode": "inherited",
            "authority_ref": "records/source-gates/m2-activation-approval.json",
            "authorized_actions": ["inspect DEM metadata", "record DEM candidate evidence", "prepare bounded M2 DEM amendment review"],
            "expires_at_utc": None,
        },
        "intended_use": {
            "summary": "Evaluate and, only after a separate exact owner amendment, acquire four public Copernicus DEM GLO-30 COG tiles for Sentinel-1 terrain correction and terrain-geometry screening.",
            "planned_actions": [
                "inspect DEM metadata",
                "record DEM candidate evidence",
                "prepare bounded M2 DEM amendment review",
                "accept the exact Copernicus WorldDEM-30 license",
                "acquire the four exact DEM tiles",
                "verify DEM bytes and GeoTIFF structure",
                "use the verified DEM only for approved radar preprocessing",
            ],
        },
        "sources": sources,
        "decision": {
            "status": "blocked",
            "blocking_reasons": [
                "The exact license requires user acceptance, and no acceptance is recorded.",
                "The four DEM tiles are additional products outside the active eight-product M2 approval.",
            ],
            "live_verification_pending": [],
            "approved_actions": ["inspect DEM metadata", "record DEM candidate evidence", "prepare bounded M2 DEM amendment review"],
        },
        "write_boundary": {
            "permitted_without_further_authorization": ["inspect DEM metadata", "record DEM candidate evidence", "prepare bounded M2 DEM amendment review"],
            "requires_explicit_authorization": [
                "accept the exact Copernicus WorldDEM-30 license",
                "acquire the four exact DEM tiles",
                "verify DEM bytes and GeoTIFF structure",
                "use the verified DEM only for approved radar preprocessing",
                "publish or redistribute DEM data or derived scientific claims",
            ],
        },
    }


def build_proposal(assessed_at: str, receipt_sha: str, manifest_sha: str, gate_sha: str) -> dict[str, Any]:
    manifest = json.loads((ROOT / "records/source-gates/m2-dem-candidate-manifest.json").read_text(encoding="utf-8"))
    return {
        "schema_version": "1.0",
        "amendment_id": "NEPAL-M2-DEM-AMENDMENT-001",
        "status": "proposed_not_active",
        "prepared_at_utc": assessed_at,
        "parent_contract_ref": "contracts/milestone-002.json",
        "parent_contract_sha256": sha256_file("contracts/milestone-002.json"),
        "parent_approval_ref": "records/source-gates/m2-activation-approval.json",
        "parent_approval_sha256": sha256_file("records/source-gates/m2-activation-approval.json"),
        "candidate_manifest_ref": "records/source-gates/m2-dem-candidate-manifest.json",
        "candidate_manifest_sha256": manifest_sha,
        "metadata_receipt_ref": "records/source-gates/m2-dem-metadata-receipt.json",
        "metadata_receipt_sha256": receipt_sha,
        "source_gate_ref": "records/source-gates/m2-dem-source-gate.json",
        "source_gate_sha256": gate_sha,
        "arcgis_capability_ref": "records/surface-receipts/arcgis-sar-processing-capability.json",
        "arcgis_capability_sha256": sha256_file("records/surface-receipts/arcgis-sar-processing-capability.json"),
        "authority": {
            "mode": "not_granted",
            "review_required": True,
            "human_gate_id": "M2-DEM-AMEND",
            "requested_actions": [
                "accept only the exact hash-bound Copernicus WorldDEM-30 license",
                "download only the four exact public GLO-30 COG tiles from their anonymous HTTPS URLs",
                "verify content length, remote identity metadata, local SHA-256, GeoTIFF readability, CRS, dimensions, nodata, and AOI coverage",
                "store raw and derived DEM files only in versioned non-Git custody",
                "use verified DEM pixels only for Sentinel-1 terrain correction and terrain-geometry exclusion masks",
                "record all failed, partial, corrupt, superseded, and inconclusive attempts",
            ],
            "not_requested": [
                "create, register, recover, or modify any account",
                "use CDSE CCM credentials or generated S3 secrets",
                "incur any charge or use a requester-pays route",
                "download any DEM tile other than the exact four",
                "redistribute raw DEM tiles or commit them to Git",
                "publish scientific conclusions, attribution, or emergency guidance",
                "select a repository license or authorize unrelated products",
            ],
        },
        "planned_intake": {
            "route": "anonymous HTTPS from the AWS Registry of Open Data GLO-30 bucket",
            "tile_count": manifest["summary"]["tile_count"],
            "combined_content_length_bytes": manifest["summary"]["combined_content_length_bytes"],
            "planned_external_root": "C:\\Projects\\Active\\nepal-2026-before-after-map-data",
            "collision_policy": "fail",
            "promotion_mode": "atomic_no_replace_after_verification",
            "redirect_policy": "refuse",
        },
        "license_decision": {
            "license_name": manifest["license"]["name"],
            "license_url": manifest["license"]["url"],
            "license_document_sha256": manifest["license"]["document_sha256"],
            "acceptance_required": True,
            "acceptance_status": "pending_exact_owner_decision",
            "obligations_summary": manifest["license"]["obligations_summary"],
        },
        "stop_conditions": [
            "license bytes or published obligations differ from the reviewed hash",
            "any tile URL, identity, bbox, byte length, ETag, last-modified value, access mode, or cost differs at preflight",
            "an account, authentication, generated secret, paid route, redirect, or requester-pays mode appears",
            "a staging or destination collision, unsafe path, symlink, or non-atomic promotion risk appears",
            "a downloaded file fails size, local SHA-256 capture, GeoTIFF readability, CRS, dimension, nodata, or AOI-coverage checks",
        ],
        "activation_effect": "If exactly approved and reconciled, this amendment adds only the four named DEM assets and exact license acceptance to M2. It does not replace or weaken the original eight-product controls.",
        "claim_boundary": manifest["claim_boundary"],
    }


def write_new(relative: str, value: object) -> str:
    path = ROOT / relative
    payload = canonical_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise SystemExit(f"REFUSED: output already exists: {relative}")
    path.write_bytes(payload)
    return sha256_bytes(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assessed-at-utc", required=True)
    args = parser.parse_args()
    if not args.assessed_at_utc.endswith("Z"):
        raise SystemExit("--assessed-at-utc must be an RFC 3339 UTC timestamp ending in Z")

    receipt, manifest = live_capture(args.assessed_at_utc)
    receipt_sha = write_new("records/source-gates/m2-dem-metadata-receipt.json", receipt)
    manifest["metadata_receipt_sha256"] = receipt_sha
    manifest_sha = write_new("records/source-gates/m2-dem-candidate-manifest.json", manifest)
    gate = build_gate(args.assessed_at_utc, receipt, manifest_sha)
    gate_sha = write_new("records/source-gates/m2-dem-source-gate.json", gate)
    proposal = build_proposal(args.assessed_at_utc, receipt_sha, manifest_sha, gate_sha)
    proposal_sha = write_new("contracts/milestone-002-dem-amendment-proposal.json", proposal)
    print(
        json.dumps(
            {
                "status": "prepared_metadata_only_no_dem_acquisition_authority",
                "tile_count": len(manifest["records"]),
                "combined_content_length_bytes": manifest["summary"]["combined_content_length_bytes"],
                "receipt_sha256": receipt_sha,
                "manifest_sha256": manifest_sha,
                "source_gate_sha256": gate_sha,
                "proposal_sha256": proposal_sha,
                "payload_bytes_requested": False,
                "license_accepted": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
