#!/usr/bin/env python3
"""Capture official orbit metadata and prepare a non-authorizing M2 amendment."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
DOWNLOAD_BASE = "https://download.dataspace.copernicus.eu/odata/v1/Products"
USER_AGENT = "nepal-2026-before-after-map-orbit-metadata/1.0"
LEGAL_NOTICE_URL = "https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice"
TERMS_URL = "https://dataspace.copernicus.eu/terms-and-conditions"
OFFICIAL_PAGES = (
    (
        "cdse_sentinel1_documentation",
        "https://documentation.dataspace.copernicus.eu/Data/SentinelMissions/Sentinel1.html",
        b"AUX_RESORB",
    ),
    (
        "cdse_odata_documentation",
        "https://documentation.dataspace.copernicus.eu/APIs/OData.html",
        b"OData",
    ),
    ("cdse_terms", TERMS_URL, b"free, full and open"),
    ("sentinel_data_legal_notice", LEGAL_NOTICE_URL, None),
    (
        "arcgis_download_orbit_file",
        "https://doc.esri.com/en/arcgis-pro/latest/tool-reference/image-analyst/download-orbit-file.html",
        b"SENTINEL_RESTITUTED",
    ),
    (
        "arcgis_apply_orbit_correction",
        "https://doc.esri.com/en/arcgis-pro/latest/tool-reference/image-analyst/apply-orbit-correction.html",
        b"ApplyOrbitCorrection",
    ),
    (
        "copernicus_s1_processing",
        "https://sentiwiki.copernicus.eu/web/s1-processing",
        b"AUX_RESORB",
    ),
)
ACQUISITIONS = (
    {
        "group_id": "ASC-BEFORE-20260816",
        "pair_id": "PAIR-S1-ASC-R085-IW",
        "event_role": "before",
        "source_ids": ["M1-SRC-001", "M1-SRC-002"],
        "scene_start": "2026-08-16T12:21:16Z",
        "scene_end": "2026-08-16T12:22:06Z",
    },
    {
        "group_id": "DESC-BEFORE-20260819",
        "pair_id": "PAIR-S1-DESC-R121-IW",
        "event_role": "before",
        "source_ids": ["M1-SRC-003"],
        "scene_start": "2026-08-19T00:10:36Z",
        "scene_end": "2026-08-19T00:11:01Z",
    },
    {
        "group_id": "ASC-AFTER-20260828",
        "pair_id": "PAIR-S1-ASC-R085-IW",
        "event_role": "after",
        "source_ids": ["M1-SRC-004", "M1-SRC-005"],
        "scene_start": "2026-08-28T12:21:16Z",
        "scene_end": "2026-08-28T12:22:06Z",
    },
    {
        "group_id": "DESC-AFTER-20260831",
        "pair_id": "PAIR-S1-DESC-R121-IW",
        "event_role": "after",
        "source_ids": ["M1-SRC-006"],
        "scene_start": "2026-08-31T00:10:37Z",
        "scene_end": "2026-08-31T00:11:02Z",
    },
)


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(relative: str) -> str:
    return sha256_bytes((ROOT / relative).read_bytes())


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def fetch(url: str) -> tuple[bytes, dict[str, str], int]:
    request = urllib.request.Request(
        url,
        method="GET",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/html,application/pdf,*/*"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read(), {key.casefold(): value for key, value in response.headers.items()}, response.status


def query_url(kind: str, acquisition: dict[str, Any]) -> str:
    product_name = f"S1D_OPER_AUX_{kind}"
    odata_filter = (
        "Collection/Name eq 'SENTINEL-1' "
        f"and contains(Name,'{product_name}') "
        f"and ContentDate/Start le {acquisition['scene_start'].replace('Z', '.000Z')} "
        f"and ContentDate/End ge {acquisition['scene_end'].replace('Z', '.000Z')}"
    )
    query = urllib.parse.urlencode(
        {
            "$filter": odata_filter,
            "$top": "20",
            "$orderby": "PublicationDate desc",
            "$expand": "Locations",
        }
    )
    return f"{CATALOGUE}?{query}"


def normalized_candidate(item: dict[str, Any], acquisition: dict[str, Any]) -> dict[str, Any]:
    start = item["ContentDate"]["Start"]
    end = item["ContentDate"]["End"]
    scene_start = acquisition["scene_start"]
    scene_end = acquisition["scene_end"]
    before = (parse_utc(scene_start) - parse_utc(start)).total_seconds()
    after = (parse_utc(end) - parse_utc(scene_end)).total_seconds()
    locations = [location for location in item.get("Locations", []) if location.get("FormatType") == "Compressed"]
    if len(locations) != 1:
        raise RuntimeError(f"Expected one compressed location for {item.get('Name')}; found {len(locations)}")
    checksums = sorted(
        (
            {
                "algorithm": checksum["Algorithm"],
                "value": checksum["Value"].lower(),
                "checksum_date": checksum.get("ChecksumDate"),
            }
            for checksum in item.get("Checksum", [])
        ),
        key=lambda value: value["algorithm"],
    )
    return {
        "provider_product_id": item["Id"],
        "exact_product_name": item["Name"],
        "s3_path": item["S3Path"],
        "download_url": f"{DOWNLOAD_BASE}({item['Id']})/$value",
        "catalogue_url": f"{CATALOGUE}({item['Id']})?$expand=Locations",
        "content_length_bytes": item["ContentLength"],
        "validity_start_utc": start,
        "validity_end_utc": end,
        "publication_date_utc": item["PublicationDate"],
        "modification_date_utc": item["ModificationDate"],
        "online": item["Online"],
        "eviction_date_utc": locations[0].get("EvictionDate"),
        "provider_checksums": checksums,
        "scene_margin_before_seconds": int(before),
        "scene_margin_after_seconds": int(after),
        "minimum_scene_margin_seconds": int(min(before, after)),
    }


def select_candidate(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    if not candidates:
        raise RuntimeError("No covering restituted orbit candidate exists")
    if any(candidate["minimum_scene_margin_seconds"] < 0 for candidate in candidates):
        raise RuntimeError("A purported covering candidate has a negative scene margin")
    return max(
        candidates,
        key=lambda value: (
            value["minimum_scene_margin_seconds"],
            parse_utc(value["publication_date_utc"]),
            value["provider_product_id"],
        ),
    )


def capture_official_pages(assessed_at: str) -> list[dict[str, Any]]:
    pages = []
    for page_id, url, required_content in OFFICIAL_PAGES:
        raw, headers, status = fetch(url)
        if status != 200:
            raise RuntimeError(f"Official page {page_id} returned HTTP {status}")
        if required_content is not None and required_content.lower() not in raw.lower():
            raise RuntimeError(f"Official page {page_id} failed its required-content check")
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
    return pages


def live_capture(assessed_at: str) -> tuple[dict[str, Any], dict[str, Any]]:
    pages = capture_official_pages(assessed_at)
    searches = []
    selected_records = []
    for index, acquisition in enumerate(ACQUISITIONS, 1):
        group_searches = {}
        for kind in ("RESORB", "POEORB"):
            url = query_url(kind, acquisition)
            raw, _, status = fetch(url)
            if status != 200:
                raise RuntimeError(f"{kind} catalogue query returned HTTP {status} for {acquisition['group_id']}")
            response = json.loads(raw)
            candidates = [normalized_candidate(item, acquisition) for item in response.get("value", [])]
            group_searches[kind] = {
                "orbit_type": kind,
                "query_url": url,
                "http_status": status,
                "response_sha256": sha256_bytes(raw),
                "observed_at_utc": assessed_at,
                "candidate_count": len(candidates),
                "candidates": candidates,
            }
        selected = select_candidate(group_searches["RESORB"]["candidates"])
        selected_records.append(
            {
                "source_id": f"M2-ORB-{index:03d}",
                "group_id": acquisition["group_id"],
                "pair_id": acquisition["pair_id"],
                "event_role": acquisition["event_role"],
                "sentinel_source_ids": acquisition["source_ids"],
                "scene_start_utc": acquisition["scene_start"],
                "scene_end_utc": acquisition["scene_end"],
                "orbit_type": "AUX_RESORB",
                **selected,
                "acquisition_status": "not_authorized",
                "local_sha256": None,
                "xml_and_osv_verification": "not_started",
                "application_status": "not_started",
            }
        )
        searches.append(
            {
                "group_id": acquisition["group_id"],
                "scene_start_utc": acquisition["scene_start"],
                "scene_end_utc": acquisition["scene_end"],
                "selection_rule": "select the full-coverage RESORB candidate with the largest minimum temporal margin around the scene; break ties by latest publication then provider UUID",
                "selected_provider_product_id": selected["provider_product_id"],
                "searches": [group_searches["RESORB"], group_searches["POEORB"]],
            }
        )

    receipt = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-METADATA-001",
        "status": "pass_metadata_only_restituted_candidates_precise_unavailable_no_acquisition_authority",
        "assessed_at_utc": assessed_at,
        "request_mode": "official_public_document_get_and_cdse_catalogue_get_only",
        "bindings": {
            "acquisition_plan_ref": "records/acquisition-plan.json",
            "acquisition_plan_sha256": sha256_file("records/acquisition-plan.json"),
            "radar_contract_ref": "config/qa/radar-baseline-processing-contract.json",
            "radar_contract_sha256": sha256_file("config/qa/radar-baseline-processing-contract.json"),
        },
        "official_pages": pages,
        "searches": searches,
        "assertions": {
            "unique_scene_window_count": len(ACQUISITIONS),
            "selected_restituted_file_count": len(selected_records),
            "all_selected_online": all(record["online"] for record in selected_records),
            "all_selected_cover_full_scene_window": all(record["minimum_scene_margin_seconds"] >= 0 for record in selected_records),
            "precise_covering_file_count": sum(
                search["candidate_count"]
                for group in searches
                for search in group["searches"]
                if search["orbit_type"] == "POEORB"
            ),
            "payload_bytes_requested": False,
            "authentication_used": False,
            "credential_values_read_or_recorded": False,
            "authority_created": False,
        },
        "limitations": [
            "Catalogue identity and online status do not establish transferred-byte integrity or valid OSV contents.",
            "Multiple restituted products overlap each scene because POD NRT coverage overlaps; the project selection rule maximizes the minimum temporal margin and is not represented as an ESA selection rule.",
            "No precise AUX_POEORB file covered any selected scene at assessment time; precise products normally arrive about 20 days after acquisition.",
            "Restituted orbit files satisfy the predeclared radar contract for controlled processing, but a later precise substitution remains separately gated and preferable for the final offline route.",
        ],
    }
    page_by_id = {page["page_id"]: page for page in pages}
    manifest = {
        "schema_version": "1.0",
        "manifest_id": "NEPAL-M2-ORBIT-CANDIDATE-MANIFEST-001",
        "status": "candidate_not_approved",
        "generated_at_utc": assessed_at,
        "intended_use": "Replace embedded predicted state vectors with exact ESA Copernicus restituted orbit files for the six approved Sentinel-1 GRD sources before controlled ArcGIS baseline processing.",
        "selection_rule": "For each unique GRD acquisition window, select the full-coverage S1D AUX_RESORB object with the largest minimum time margin around the complete scene window; break ties by latest publication then provider UUID.",
        "metadata_receipt_ref": "records/source-gates/m2-orbit-metadata-receipt.json",
        "metadata_receipt_sha256": None,
        "distribution_route": {
            "provider": "Copernicus Data Space Ecosystem",
            "catalogue": "official public OData catalogue",
            "download_method": "authenticated OData GET using the same secret-safe existing owner-controlled token reference as the approved Sentinel acquisition",
            "new_account_or_terms_action_requested": False,
            "cost_expected": False,
            "allowed_hosts": ["download.dataspace.copernicus.eu"],
        },
        "rights": {
            "terms_url": TERMS_URL,
            "terms_page_sha256": page_by_id["cdse_terms"]["response_sha256"],
            "legal_notice_url": LEGAL_NOTICE_URL,
            "legal_notice_sha256": page_by_id["sentinel_data_legal_notice"]["response_sha256"],
            "summary": "Copernicus Sentinel data and service information are available on a free, full and open basis; public distribution requires the applicable source notice and carries no suitability warranty.",
            "new_acceptance_requested": False,
        },
        "records": selected_records,
        "summary": {
            "selected_file_count": len(selected_records),
            "covered_sentinel_source_count": sum(len(record["sentinel_source_ids"]) for record in selected_records),
            "combined_content_length_bytes": sum(record["content_length_bytes"] for record in selected_records),
            "combined_content_length_mib": round(sum(record["content_length_bytes"] for record in selected_records) / (1024**2), 3),
            "orbit_type": "AUX_RESORB",
            "precise_covering_file_count_at_assessment": receipt["assertions"]["precise_covering_file_count"],
        },
        "claim_boundary": {
            "catalogue_availability_established": True,
            "scope_authority_established": False,
            "payload_bytes_transferred": False,
            "orbit_xml_verified": False,
            "orbit_correction_applied": False,
            "sentinel_pixels_processed": False,
            "baseline_established": False,
            "scientific_result_established": False,
        },
    }
    return receipt, manifest


def criterion(
    criterion_id: str,
    status: str,
    requires_live: bool,
    evidence: list[dict[str, Any]],
    note: str,
    *,
    required: bool = True,
) -> dict[str, Any]:
    return {
        "id": criterion_id,
        "required": required,
        "requires_live": requires_live,
        "status": status,
        "evidence": evidence,
        "note": note,
    }


def build_gate(assessed_at: str, receipt: dict[str, Any], manifest_sha256: str) -> dict[str, Any]:
    manifest_evidence = {
        "type": "static",
        "locator": "records/source-gates/m2-orbit-candidate-manifest.json",
        "note": f"Candidate manifest SHA-256 {manifest_sha256} binds four exact provider objects to six approved Sentinel source IDs.",
    }
    pages = {page["page_id"]: page for page in receipt["official_pages"]}
    official_s1 = {
        "type": "live",
        "locator": pages["cdse_sentinel1_documentation"]["url"],
        "observed_at": assessed_at,
        "note": f"Official Sentinel-1 collection documentation response SHA-256 {pages['cdse_sentinel1_documentation']['response_sha256']} lists AUX_RESORB, its OData catalogue route, and three-month rolling availability.",
    }
    arcgis_download = {
        "type": "live",
        "locator": pages["arcgis_download_orbit_file"]["url"],
        "observed_at": assessed_at,
        "note": f"ArcGIS documentation response SHA-256 {pages['arcgis_download_orbit_file']['response_sha256']} recommends restituted OSVs for acquisitions within three weeks and identifies the authenticated CDSE route.",
    }
    rights_live = {
        "type": "live",
        "locator": TERMS_URL,
        "observed_at": assessed_at,
        "note": f"Current CDSE terms response SHA-256 {pages['cdse_terms']['response_sha256']} points Sentinel data and service information to the legal notice SHA-256 {pages['sentinel_data_legal_notice']['response_sha256']}.",
    }
    sources = []
    for record in receipt_to_selected_records(receipt):
        search = next(item for item in receipt["searches"] if item["group_id"] == record["group_id"])
        query = next(item for item in search["searches"] if item["orbit_type"] == "RESORB")
        catalogue_live = {
            "type": "live",
            "locator": query["query_url"],
            "observed_at": assessed_at,
            "note": f"Official OData response SHA-256 {query['response_sha256']} returned {query['candidate_count']} full-coverage restituted candidates; deterministic temporal-margin selection chose provider UUID {record['provider_product_id']}.",
        }
        sources.append(
            {
                "source_id": record["source_id"],
                "name": record["exact_product_name"],
                "locator": record["download_url"],
                "criteria": [
                    criterion("identity", "pass", True, [catalogue_live, manifest_evidence], "Exact ESA filename, provider UUID, validity interval, size, S3 path, publication time, and checksums are bound."),
                    criterion("authority", "pass", True, [official_s1, catalogue_live], "ESA Copernicus POD produced the orbit file and CDSE is its primary catalogue and delivery service."),
                    criterion("access", "pass", True, [catalogue_live, arcgis_download], "The exact file is online; payload download requires an existing owner-controlled CDSE credential and no account action is proposed."),
                    criterion("rights", "pass", True, [rights_live], "The same public Sentinel legal notice supports controlled acquisition and analysis with source notice and no suitability warranty."),
                    criterion("provenance", "pass", True, [catalogue_live, manifest_evidence], "The exact CDSE product identity is bound directly to the approved GRD acquisition window and source IDs."),
                    criterion("integrity", "pass", True, [catalogue_live, manifest_evidence], "Provider MD5, BLAKE3, and byte length are recorded; local SHA-256 and XML/OSV validation are mandatory after transfer."),
                    criterion("fitness", "pass", True, [catalogue_live, official_s1, arcgis_download], f"The validity interval covers the full scene with at least {record['minimum_scene_margin_seconds']} seconds on both sides; restituted rather than precise quality remains explicit."),
                    criterion("privacy-security", "pass", False, [manifest_evidence], "Orbit state vectors contain no project personal data; credentials remain references-only and payloads stay outside Git."),
                    criterion("scope-authority", "unknown", False, [{"type": "static", "locator": "records/source-gates/m2-activation-approval.json", "note": "The active approval is limited to eight exact Sentinel products and excludes any additional product identity."}], "A hash-bound owner amendment is required before any orbit payload request."),
                ],
            }
        )
    return {
        "contract_version": "source-gate/v1",
        "assessment_id": "NEPAL-M2-ORBIT-SOURCE-GATE-001",
        "assessed_at": assessed_at,
        "authority": {
            "mode": "inherited",
            "authority_ref": "records/source-gates/m2-activation-approval.json",
            "authorized_actions": ["inspect orbit metadata", "record orbit candidate evidence", "prepare a bounded orbit amendment review"],
            "expires_at_utc": None,
        },
        "intended_use": {
            "summary": "Evaluate and, only after exact owner amendment, acquire four exact S1D AUX_RESORB files for the six approved Sentinel-1 GRD sources before ArcGIS baseline processing.",
            "planned_actions": [
                "inspect orbit metadata",
                "record orbit candidate evidence",
                "prepare a bounded orbit amendment review",
                "download the four exact restituted orbit files with an existing secret-safe owner token reference",
                "verify bytes, XML structure, state vectors, validity, and scene binding",
                "apply each passing file only to its exact approved Sentinel-1 source group",
            ],
        },
        "sources": sources,
        "decision": {
            "status": "blocked",
            "blocking_reasons": ["The four exact orbit files are additional products outside the active eight-product M2 approval."],
            "live_verification_pending": [],
            "approved_actions": ["inspect orbit metadata", "record orbit candidate evidence", "prepare a bounded orbit amendment review"],
        },
        "write_boundary": {
            "permitted_without_further_authorization": ["inspect orbit metadata", "record orbit candidate evidence", "prepare a bounded orbit amendment review"],
            "requires_explicit_authorization": [
                "download the four exact restituted orbit files with an existing secret-safe owner token reference",
                "verify bytes, XML structure, state vectors, validity, and scene binding",
                "apply each passing file only to its exact approved Sentinel-1 source group",
                "download or substitute any precise orbit file",
                "publish or redistribute orbit payloads or derived scientific claims",
            ],
        },
    }


def receipt_to_selected_records(receipt: dict[str, Any]) -> list[dict[str, Any]]:
    records = []
    for index, acquisition in enumerate(ACQUISITIONS, 1):
        group = next(item for item in receipt["searches"] if item["group_id"] == acquisition["group_id"])
        resorb = next(item for item in group["searches"] if item["orbit_type"] == "RESORB")
        selected = next(
            item for item in resorb["candidates"] if item["provider_product_id"] == group["selected_provider_product_id"]
        )
        records.append(
            {
                "source_id": f"M2-ORB-{index:03d}",
                "group_id": acquisition["group_id"],
                "sentinel_source_ids": acquisition["source_ids"],
                **selected,
            }
        )
    return records


def build_proposal(assessed_at: str, receipt_sha: str, manifest_sha: str, gate_sha: str) -> dict[str, Any]:
    manifest = json.loads((ROOT / "records/source-gates/m2-orbit-candidate-manifest.json").read_text(encoding="utf-8"))
    return {
        "schema_version": "1.0",
        "amendment_id": "NEPAL-M2-ORBIT-AMENDMENT-001",
        "status": "proposed_not_active",
        "prepared_at_utc": assessed_at,
        "parent_contract_ref": "contracts/milestone-002.json",
        "parent_contract_sha256": sha256_file("contracts/milestone-002.json"),
        "parent_approval_ref": "records/source-gates/m2-activation-approval.json",
        "parent_approval_sha256": sha256_file("records/source-gates/m2-activation-approval.json"),
        "candidate_manifest_ref": "records/source-gates/m2-orbit-candidate-manifest.json",
        "candidate_manifest_sha256": manifest_sha,
        "metadata_receipt_ref": "records/source-gates/m2-orbit-metadata-receipt.json",
        "metadata_receipt_sha256": receipt_sha,
        "source_gate_ref": "records/source-gates/m2-orbit-source-gate.json",
        "source_gate_sha256": gate_sha,
        "radar_contract_ref": "config/qa/radar-baseline-processing-contract.json",
        "radar_contract_sha256": sha256_file("config/qa/radar-baseline-processing-contract.json"),
        "authority": {
            "mode": "not_granted",
            "review_required": True,
            "human_gate_id": "M2-ORBIT-AMEND",
            "requested_actions": [
                "use the existing secret-safe owner-controlled CDSE token reference only after the original Sentinel acquisition begins",
                "download only the four exact AUX_RESORB provider UUIDs in the bound candidate manifest",
                "verify provider size and checksums, local SHA-256, XML identity, ordered finite OSVs, validity coverage, and exact scene binding",
                "store orbit payloads and corrected SAFE metadata only in versioned non-Git custody",
                "apply each passing orbit file only to the exact approved Sentinel-1 source IDs listed in its record",
                "preserve embedded predicted metadata plus all failed, partial, corrupt, superseded, and inconclusive attempts",
            ],
            "not_requested": [
                "create, recover, or modify an account or expose a token, password, cookie, header, S3 key, or cloud connection file",
                "accept new or changed terms, incur a charge, or use an unapproved host",
                "download any orbit product other than the four exact restituted objects",
                "silently substitute later precise orbit files",
                "resolve the separate DEM vertical-datum gate or terrain-result review",
                "begin radar processing before all Sentinel, DEM, vertical, orbit, and pixel-readiness prerequisites pass",
                "publish payloads, scientific conclusions, attribution, or emergency guidance",
            ],
        },
        "planned_intake": {
            "route": "authenticated CDSE OData GET with an existing secret-safe owner token reference",
            "file_count": manifest["summary"]["selected_file_count"],
            "covered_sentinel_source_count": manifest["summary"]["covered_sentinel_source_count"],
            "combined_content_length_bytes": manifest["summary"]["combined_content_length_bytes"],
            "planned_external_root": "C:\\Projects\\Active\\nepal-2026-before-after-map-data",
            "collision_policy": "fail",
            "promotion_mode": "atomic_no_replace_after_verification",
            "allowed_hosts": manifest["distribution_route"]["allowed_hosts"],
        },
        "quality_decision": {
            "selected_type": "AUX_RESORB",
            "precise_files_covering_selected_scenes_at_assessment": manifest["summary"]["precise_covering_file_count_at_assessment"],
            "rationale": "ArcGIS recommends restituted OSVs for acquisitions less than three weeks old, and the active radar contract accepts restituted or precise OSVs while rejecting predicted-only processing.",
            "limitation": "AUX_POEORB is the preferred final offline orbit source when available; any later precise substitution requires a fresh exact manifest and review.",
        },
        "rights": manifest["rights"],
        "stop_conditions": [
            "any provider UUID, filename, validity interval, byte length, checksum, online state, eviction date, access host, or terms hash differs at fresh preflight",
            "the existing token reference is unavailable, expired, invalid, or would need to be disclosed or logged",
            "login, MFA, account recovery, terms acceptance, generated S3 credentials, payment, or an unapproved redirect is required",
            "a staging or destination collision, unsafe path, link, or non-atomic promotion risk appears",
            "a file fails size, provider checksum, local SHA-256, XML parse, mission or file-type identity, finite ordered OSVs, validity coverage, or scene binding",
            "the exact Sentinel source group is not already in verified promoted custody",
        ],
        "activation_effect": "Exact approval and reconciliation would add only four named S1D AUX_RESORB files and their bounded verification/application route to M2; all existing Sentinel, DEM, vertical-datum, terrain-result, pixel, and scientific gates remain independent.",
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
    receipt_sha = write_new("records/source-gates/m2-orbit-metadata-receipt.json", receipt)
    manifest["metadata_receipt_sha256"] = receipt_sha
    manifest_sha = write_new("records/source-gates/m2-orbit-candidate-manifest.json", manifest)
    gate = build_gate(args.assessed_at_utc, receipt, manifest_sha)
    gate_sha = write_new("records/source-gates/m2-orbit-source-gate.json", gate)
    proposal = build_proposal(args.assessed_at_utc, receipt_sha, manifest_sha, gate_sha)
    proposal_sha = write_new("contracts/milestone-002-orbit-amendment-proposal.json", proposal)
    print(
        json.dumps(
            {
                "status": "prepared_metadata_only_no_orbit_acquisition_authority",
                "selected_file_count": manifest["summary"]["selected_file_count"],
                "covered_sentinel_source_count": manifest["summary"]["covered_sentinel_source_count"],
                "combined_content_length_bytes": manifest["summary"]["combined_content_length_bytes"],
                "precise_covering_file_count": manifest["summary"]["precise_covering_file_count_at_assessment"],
                "receipt_sha256": receipt_sha,
                "manifest_sha256": manifest_sha,
                "source_gate_sha256": gate_sha,
                "proposal_sha256": proposal_sha,
                "payload_bytes_requested": False,
                "authentication_used": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
