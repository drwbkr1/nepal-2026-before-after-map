#!/usr/bin/env python3
"""Build the decision-ready M1 candidate source manifest from controlled evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


EVENT_DATE = datetime.fromisoformat("2026-08-26T00:00:00+00:00")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sensor_route(record: dict) -> tuple[str, str]:
    attributes = record["attributes"]
    if attributes["platformShortName"] == "SENTINEL-1":
        return "Sentinel-1 IW GRD", "radar"
    if attributes["platformShortName"] == "SENTINEL-2":
        return "Sentinel-2 MSI Level-2A", "optical"
    raise ValueError(f"unsupported platform: {attributes['platformShortName']}")


def proposal(record: dict, quicklook: dict) -> dict:
    attributes = record["attributes"]
    detailed = record["draft_aoi_bbox_intersection"]["AOI-SOURCE-DRAFT"] or record["draft_aoi_bbox_intersection"]["AOI-UPPER-CORRIDOR-DRAFT"]
    if attributes["platformShortName"] == "SENTINEL-1":
        return {
            "disposition": "accept_for_controlled_acquisition_planning",
            "acquisition_priority": "primary" if detailed else "supporting",
            "analysis_role": "event_aoi_radar_pair" if detailed else "regional_context_and_swath_continuity",
            "reason": "Exact orbit-paired GRD candidate retained for product-level terrain, coverage, and backscatter QA.",
        }
    if attributes.get("tileId") == "45RUM":
        return {
            "disposition": "accept_for_controlled_acquisition_planning",
            "acquisition_priority": "primary",
            "analysis_role": "event_aoi_optical_pair",
            "reason": "Tile intersects the approved source and upper-corridor AOIs; pixel masks must determine actual usability.",
        }
    return {
        "disposition": "defer_context_only",
        "acquisition_priority": "deferred",
        "analysis_role": "regional_context_optical",
        "reason": "Tile intersects only the regional overview bounding box and is cloud limited; retain evidence without acquiring in the initial route.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--quicklook-review", type=Path, required=True)
    parser.add_argument("--source-gate", type=Path, required=True)
    parser.add_argument("--aoi-approval", type=Path, required=True)
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    quicklook_review = json.loads(args.quicklook_review.read_text(encoding="utf-8"))
    source_gate = json.loads(args.source_gate.read_text(encoding="utf-8"))
    aoi_approval = json.loads(args.aoi_approval.read_text(encoding="utf-8"))
    if aoi_approval.get("status") != "approved":
        raise SystemExit("AOI approval is not complete")
    if source_gate.get("decision", {}).get("status") != "ready":
        raise SystemExit("source gate is not ready")
    if catalog["candidate_count"] != quicklook_review["candidate_count"]:
        raise SystemExit("catalog and quicklook candidate counts differ")

    quicklooks = {record["product_stem"]: record for record in quicklook_review["records"]}
    records = []
    for index, source in enumerate(catalog["records"], 1):
        stem = source["product_stem"]
        if stem not in quicklooks:
            raise SystemExit(f"missing quicklook evidence for {stem}")
        quicklook = quicklooks[stem]
        collection, route = sensor_route(source)
        proposed = proposal(source, quicklook)
        start = datetime.fromisoformat(source["content_date"]["Start"].replace("Z", "+00:00"))
        attributes = source["attributes"]
        record = {
            "source_id": f"M1-SRC-{index:03d}",
            "provider": source["provider"],
            "collection": collection,
            "sensor_route": route,
            "exact_product_id": source["name"],
            "provider_product_id": source["provider_product_id"],
            "event_role": "before" if start < EVENT_DATE else "after",
            "acquisition_start_utc": source["content_date"]["Start"],
            "acquisition_end_utc": source["content_date"]["End"],
            "processing_level": attributes.get("processingLevel") or attributes.get("productType"),
            "orbit_or_tile": {
                "tile_id": attributes.get("tileId"),
                "orbit_direction": attributes.get("orbitDirection"),
                "relative_orbit_number": attributes.get("relativeOrbitNumber"),
                "operational_mode": attributes.get("operationalMode"),
            },
            "catalog_cloud_cover_percent": attributes.get("cloudCover"),
            "footprint": source["footprint"],
            "coverage_status": {
                "method": "catalog footprint bounding-box intersection only",
                "approved_aoi_intersections": {
                    key.replace("-DRAFT", ""): value for key, value in source["draft_aoi_bbox_intersection"].items()
                },
                "usable_pixels": "not_established",
            },
            "query": {
                "catalog_endpoint": catalog["catalog_endpoint"],
                "query_url": source["query_url"],
                "queried_at_utc": catalog["retrieved_at_utc"],
                "result_count": source["query_result_count"],
                "authentication": catalog["request_authentication"],
            },
            "access": {
                "metadata": "public_no_authentication",
                "full_product": "authenticated_flow_requires_separate_authority",
                "download_status": "not_authorized",
            },
            "rights": {
                "status": "source_gate_pass_for_sentinel_data_with_required_notice",
                "notice": "Sentinel Data Legal Notice and required Copernicus/Sentinel source notices",
                "terms_url": "https://dataspace.copernicus.eu/terms-and-conditions",
                "quicklook_redistribution": "not_authorized",
            },
            "catalog_content_length_bytes": source["content_length_bytes"],
            "provider_checksums": source["provider_checksums"],
            "local_custody": {
                "path": None,
                "byte_size": None,
                "sha256": None,
                "status": "not_acquired",
            },
            "quality": {
                "quicklook_review_status": quicklook["visual_review_status"],
                "quicklook_disposition": quicklook["disposition"],
                "pixel_inspection_status": quicklook["pixel_usability_status"],
                "mask_status": "not_started",
                "limitations": quicklook["visual_observations"],
            },
            "proposed_disposition": proposed,
            "rejection_reason": None,
            "reviewer": "owner_review_pending",
            "review_status": "candidate_manifest_not_approved",
        }
        records.append(record)

    accepted = [r for r in records if r["proposed_disposition"]["disposition"] == "accept_for_controlled_acquisition_planning"]
    deferred = [r for r in records if r["proposed_disposition"]["disposition"] == "defer_context_only"]
    output = {
        "schema_version": "1.0",
        "manifest_id": "NEPAL-M1-CANDIDATE-SOURCE-MANIFEST-001",
        "status": "candidate_for_owner_review",
        "generated_at_utc": args.generated_at_utc,
        "event_date": "2026-08-26",
        "analysis_crs": "EPSG:32645",
        "aoi_approval_ref": str(args.aoi_approval).replace("\\", "/"),
        "aoi_approval_sha256": sha256(args.aoi_approval),
        "input_evidence": [
            {"path": str(args.catalog).replace("\\", "/"), "sha256": sha256(args.catalog)},
            {"path": str(args.quicklook_review).replace("\\", "/"), "sha256": sha256(args.quicklook_review)},
            {"path": str(args.source_gate).replace("\\", "/"), "sha256": sha256(args.source_gate)},
        ],
        "decision_scope": {
            "requested": "Lock proposed accepted and deferred candidates for later controlled acquisition planning.",
            "does_not_authorize": [
                "credentials or account-session use",
                "terms acceptance",
                "full-product downloads",
                "pixel-usability claims",
                "scientific conclusions or public emergency guidance",
            ],
        },
        "summary": {
            "candidate_count": len(records),
            "proposed_accept_count": len(accepted),
            "proposed_defer_count": len(deferred),
            "proposed_reject_count": 0,
            "proposed_acquisition_catalog_bytes": sum(r["catalog_content_length_bytes"] for r in accepted),
            "proposed_acquisition_catalog_gib": round(sum(r["catalog_content_length_bytes"] for r in accepted) / (1024 ** 3), 3),
            "pixel_usability_established_count": 0,
        },
        "records": records,
        "manifest_limitations": [
            "Catalog footprint intersections do not establish usable pixels.",
            "Post-event Sentinel-2 RUM is high-cloud-risk and may be inconclusive after mask review.",
            "Sentinel-1 terrain effects, layover, shadow, speckle, and registration remain untested.",
            "Deferred RUL optical records remain preserved and may be reconsidered with a documented later decision.",
            "No source has entered local full-product custody.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": output["status"], "summary": output["summary"], "output": str(args.output), "sha256": sha256(args.output)}, indent=2))


if __name__ == "__main__":
    main()
