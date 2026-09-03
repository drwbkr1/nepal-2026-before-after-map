#!/usr/bin/env python3
"""Run the authorized, non-payload M2 DEM source and custody preflight."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
APPROVAL_REF = "records/source-gates/m2-dem-amendment-approval.json"
MILESTONE_REF = "contracts/milestone-002.json"
PROFILE_REF = "records/project-control-profile.json"
PROPOSAL_REF = "contracts/milestone-002-dem-amendment-proposal.json"
MANIFEST_REF = "records/source-gates/m2-dem-candidate-manifest.json"
INTAKE_REF = "contracts/m2-dem-intake.json"
SOURCE_GATE_REF = "records/source-gates/m2-dem-live-source-gate.json"
PREFLIGHT_REF = "records/acquisition/dem-preflight.json"
LICENSE_SHA256 = "9cd37d37ea654bbcaf0a2e059e6a3a5b5f76072824d8dd860ccf274ada8951bd"
USER_AGENT = "nepal-2026-before-after-map-dem-preflight/1.0"


class RefuseRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(relative: str) -> str:
    return sha256_bytes((ROOT / relative).read_bytes())


def load(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def normalized_headers(headers: Any) -> dict[str, str]:
    return {str(key).casefold(): str(value) for key, value in headers.items()}


def open_exact(url: str, *, method: str = "GET") -> tuple[bytes, dict[str, str], int, str]:
    request = urllib.request.Request(
        url,
        method=method,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json,application/pdf,image/tiff,*/*"},
    )
    opener = urllib.request.build_opener(RefuseRedirect())
    try:
        with opener.open(request, timeout=60) as response:
            body = response.read()
            return body, normalized_headers(response.headers), int(response.status), response.geturl()
    except urllib.error.HTTPError as exc:
        if 300 <= exc.code < 400:
            raise RuntimeError(f"redirect refused for {url}: HTTP {exc.code}") from exc
        raise


def is_reparse_point(path: Path) -> bool:
    details = path.stat(follow_symlinks=False)
    attributes = getattr(details, "st_file_attributes", 0)
    return path.is_symlink() or bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def existing_path_evidence(paths: list[Path]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    evidence: list[dict[str, Any]] = []
    for path in paths:
        current = path
        while True:
            key = os.path.normcase(str(current))
            if key not in seen and current.exists():
                seen.add(key)
                evidence.append({"path": str(current), "is_reparse_point": is_reparse_point(current)})
            if current == current.parent:
                break
            current = current.parent
    return evidence


def validate_stac(record: dict[str, Any], item: dict[str, Any]) -> dict[str, bool]:
    data = item.get("assets", {}).get("data", {})
    properties = item.get("properties", {})
    return {
        "item_id_match": item.get("id") == record["item_id"],
        "collection_match": item.get("collection") == record["collection"],
        "bbox_match": item.get("bbox") == record["bbox_wgs84"],
        "grid_code_match": properties.get("grid:code") == record["grid_code"],
        "gsd_match": properties.get("gsd") == record["gsd_m"],
        "source_crs_match": properties.get("proj:code") == record["source_crs"],
        "shape_match": data.get("proj:shape") == record["shape"],
        "transform_match": data.get("proj:transform") == record["transform"],
        "data_type_match": data.get("data_type") == record["data_type"],
        "media_type_match": data.get("type") == record["media_type"],
        "catalog_asset_match": data.get("href") == record["cdse_s3_href"],
    }


def validate_head(record: dict[str, Any], headers: dict[str, str], status: int, resolved_url: str, body: bytes) -> dict[str, bool]:
    expected = record["anonymous_head"]
    etag = headers.get("etag", "").strip('"')
    return {
        "http_200": status == 200,
        "exact_url_no_redirect": resolved_url == record["anonymous_https_url"],
        "zero_response_body_bytes": len(body) == 0,
        "content_length_match": int(headers.get("content-length", "-1")) == expected["content_length_bytes"],
        "content_type_match": headers.get("content-type", "").split(";", 1)[0].casefold() == "image/tiff",
        "etag_match": etag == expected["etag"],
        "last_modified_match": headers.get("last-modified") == expected["last_modified"],
        "accept_ranges_bytes": headers.get("accept-ranges", "").casefold() == "bytes",
        "anonymous_no_requester_charge": "x-amz-request-charged" not in headers,
    }


def criterion(identifier: str, evidence: list[dict[str, Any]], note: str, *, live: bool = True) -> dict[str, Any]:
    return {"id": identifier, "required": True, "requires_live": live, "status": "pass", "evidence": evidence, "note": note}


def live(locator: str, observed_at: str, note: str) -> dict[str, Any]:
    return {"type": "live", "locator": locator, "observed_at": observed_at, "note": note}


def static(locator: str, note: str) -> dict[str, Any]:
    return {"type": "static", "locator": locator, "note": note}


def create_new(relative: str, value: object) -> str:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_bytes(value)
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
    return sha256_bytes(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assessed-at-utc", required=True)
    args = parser.parse_args()
    if not args.assessed_at_utc.endswith("Z"):
        raise SystemExit("--assessed-at-utc must be an RFC 3339 UTC timestamp ending in Z")
    for relative in (SOURCE_GATE_REF, PREFLIGHT_REF):
        if (ROOT / relative).exists():
            raise SystemExit(f"preflight output already exists; refusing replacement: {relative}")

    approval = load(APPROVAL_REF)
    milestone = load(MILESTONE_REF)
    profile = load(PROFILE_REF)
    proposal = load(PROPOSAL_REF)
    manifest = load(MANIFEST_REF)
    intake = load(INTAKE_REF)
    expected_ids = ["M2-DEM-001", "M2-DEM-002", "M2-DEM-003", "M2-DEM-004"]
    if approval.get("status") != "approved" or approval.get("authorized_source_ids") != expected_ids:
        raise SystemExit("exact DEM amendment approval is missing or differs")
    if approval.get("amendment_proposal_sha256") != sha256_file(PROPOSAL_REF):
        raise SystemExit("approval does not bind the exact proposal")
    if approval.get("license", {}).get("document_sha256") != LICENSE_SHA256 or approval.get("license", {}).get("acceptance_status") != "accepted_exact_hash_bound_document":
        raise SystemExit("exact license acceptance is absent or differs")
    if approval.get("review_bundle_manifest_sha256") != "caecbdfe69ec1a6c8c39401b63756005820a727cb8f9e7e0084753e2d6afb39e":
        raise SystemExit("approved DEM review bundle differs")
    if proposal.get("candidate_manifest_sha256") != sha256_file(MANIFEST_REF):
        raise SystemExit("proposal does not bind the exact candidate manifest")
    units = {unit["id"]: unit for unit in milestone.get("units", [])}
    if units.get("M2-DEM-PREFLIGHT", {}).get("status") != "ready" or units.get("M2-DEM-ACQUIRE", {}).get("status") != "planned":
        raise SystemExit("DEM milestone units are not at the fresh-preflight checkpoint")
    checkpoints = {item.get("checkpoint_id") for item in profile.get("parallel_checkpoints", [])}
    if "M2-DEM-FRESH-PREFLIGHT" not in checkpoints:
        raise SystemExit("project profile is not at the DEM fresh-preflight checkpoint")
    intake_ids = [asset.get("extensions", {}).get("source_id") for asset in intake.get("assets", [])]
    if intake_ids != expected_ids or any(asset.get("state") != "authorized" or asset.get("attempts") for asset in intake.get("assets", [])):
        raise SystemExit("active DEM intake is not the exact authorized, unattempted four-tile set")
    if intake.get("extensions", {}).get("amendment_approval_sha256") != sha256_file(APPROVAL_REF):
        raise SystemExit("active DEM intake does not bind the current approval")

    license_url = proposal["license_decision"]["license_url"]
    license_body, license_headers, license_status, license_resolved = open_exact(license_url)
    license_checks = {
        "http_200": license_status == 200,
        "exact_url_no_redirect": license_resolved == license_url,
        "pdf_magic": license_body.startswith(b"%PDF"),
        "sha256_match": sha256_bytes(license_body) == LICENSE_SHA256,
        "approval_hash_match": approval["license"]["document_sha256"] == LICENSE_SHA256,
    }
    if not all(license_checks.values()):
        raise SystemExit(f"exact license preflight failed: {license_checks}")

    tile_checks: list[dict[str, Any]] = []
    source_entries: list[dict[str, Any]] = []
    approval_static = static(APPROVAL_REF, f"Exact amendment approval SHA-256 {sha256_file(APPROVAL_REF)} binds the four tiles and accepted license.")
    manifest_static = static(MANIFEST_REF, f"Immutable candidate manifest SHA-256 {sha256_file(MANIFEST_REF)} binds exact tile metadata and AOI intersections.")
    license_live = live(license_url, args.assessed_at_utc, f"Exact license returned HTTP 200 without redirect and matched SHA-256 {LICENSE_SHA256}.")
    for record in manifest["records"]:
        stac_body, stac_headers, stac_status, stac_resolved = open_exact(record["stac_item_url"])
        if stac_status != 200 or stac_resolved != record["stac_item_url"]:
            raise SystemExit(f"STAC request failed or redirected for {record['source_id']}")
        item = json.loads(stac_body.decode("utf-8"))
        stac_checks = validate_stac(record, item)
        head_body, head_headers, head_status, head_resolved = open_exact(record["anonymous_https_url"], method="HEAD")
        head_checks = validate_head(record, head_headers, head_status, head_resolved, head_body)
        if not all(stac_checks.values()) or not all(head_checks.values()):
            raise SystemExit(f"live tile identity failed for {record['source_id']}: stac={stac_checks}, head={head_checks}")
        stac_sha = sha256_bytes(stac_body)
        tile = {
            "source_id": record["source_id"],
            "item_id": record["item_id"],
            "stac_url": record["stac_item_url"],
            "stac_response_sha256": stac_sha,
            "stac_content_length_bytes": len(stac_body),
            "stac_last_modified": stac_headers.get("last-modified"),
            "anonymous_https_url": record["anonymous_https_url"],
            "head": {
                "status_code": head_status,
                "content_length_bytes": int(head_headers["content-length"]),
                "content_type": head_headers.get("content-type"),
                "etag": head_headers.get("etag", "").strip('"'),
                "last_modified": head_headers.get("last-modified"),
                "accept_ranges": head_headers.get("accept-ranges"),
                "version_id": head_headers.get("x-amz-version-id"),
                "resolved_url": head_resolved,
                "response_body_bytes": len(head_body),
            },
            "stac_checks": stac_checks,
            "head_checks": head_checks,
            "status": "pass",
        }
        tile_checks.append(tile)
        stac_live = live(record["stac_item_url"], args.assessed_at_utc, f"Exact STAC identity and grid metadata matched; response SHA-256 {stac_sha}.")
        head_live = live(record["anonymous_https_url"], args.assessed_at_utc, f"Anonymous HEAD returned the reviewed {tile['head']['content_length_bytes']} bytes, ETag {tile['head']['etag']}, Last-Modified {tile['head']['last_modified']}, and Accept-Ranges bytes without redirect or requester charge.")
        source_entries.append({
            "source_id": record["source_id"],
            "name": record["item_id"],
            "locator": record["anonymous_https_url"],
            "criteria": [
                criterion("identity", [stac_live, head_live, manifest_static], "Exact catalog and object identities match the reviewed tile."),
                criterion("authority", [approval_static], "The exact owner amendment authorizes only this four-tile route.", live=False),
                criterion("access", [head_live], "Anonymous no-cost HTTPS access is available without redirect or account action."),
                criterion("rights", [license_live, approval_static], "The fetched license bytes match the exact document accepted by the owner."),
                criterion("provenance", [stac_live, head_live, manifest_static], "The official catalog identity and public mirror object remain linked by the exact tile name."),
                criterion("integrity", [head_live, static(INTAKE_REF, "Local SHA-256, size verification, retained attempts, and no-replace promotion remain mandatory after transfer.")], "Remote identity metadata match; local byte integrity remains untested."),
                criterion("fitness", [stac_live, static("contracts/m2-dem-offline-verification.json", "GeoTIFF and AOI checks remain gate-deferred until promoted local bytes exist.")], "Fit for bounded acquisition and later terrain evaluation only."),
                criterion("privacy-security", [approval_static], "Public terrain data use an anonymous route; payloads remain untrusted and outside Git.", live=False),
                criterion("terms-acceptance", [license_live, approval_static], "Exact hash-bound license acceptance is recorded."),
                criterion("scope-authority", [approval_static, manifest_static], "Only the four exact named tiles and bounded radar use are authorized.", live=False),
            ],
        })

    project_root = ROOT.parent.resolve()
    external_root = Path(proposal["planned_intake"]["planned_external_root"]).resolve(strict=False)
    expected_external_root = (project_root / "nepal-2026-before-after-map-data").resolve(strict=False)
    custody_root = (project_root / intake["custody_root"]).resolve(strict=False)
    staging_root = (project_root / intake["staging_root"]).resolve(strict=False)
    if external_root != expected_external_root:
        raise SystemExit("approved external root differs from the canonical sibling root")
    try:
        external_root.relative_to(ROOT.resolve())
        raise SystemExit("DEM external root resolves inside the Git repository")
    except ValueError:
        pass
    for path, root in ((custody_root, external_root), (staging_root, external_root)):
        path.relative_to(root)
        if path == root:
            raise SystemExit("DEM custody or staging root must be a child of the external root")
    path_evidence = existing_path_evidence([external_root, custody_root, staging_root])
    if any(item["is_reparse_point"] for item in path_evidence):
        raise SystemExit("DEM custody path has a symlink or reparse-point ancestor")

    resolved_paths: list[str] = []
    collisions: list[str] = []
    for asset in intake["assets"]:
        destination = (custody_root / asset["destination_relative_path"]).resolve(strict=False)
        staging = (staging_root / asset["staging_relative_path"]).resolve(strict=False)
        destination.relative_to(custody_root)
        staging.relative_to(staging_root)
        resolved_paths.extend([str(destination), str(staging)])
        if destination.exists():
            collisions.append(str(destination))
        if staging.exists():
            collisions.append(str(staging))
    normalized = [os.path.normcase(path) for path in resolved_paths]
    casefold_collision = len(normalized) != len(set(normalized))
    total_bytes = sum(int(asset["expected"]["size_bytes"]) for asset in intake["assets"])
    required_working_bytes = total_bytes * 3
    free_bytes = shutil.disk_usage(project_root).free
    if collisions or casefold_collision or free_bytes < required_working_bytes:
        raise SystemExit("DEM path, collision, or storage preflight failed")

    approved_actions = [
        "record exact DEM live source and custody preflight evidence",
        "download only the four exact approved DEM tiles after this preflight passes",
        "verify and promote exact DEM bytes in non-Git custody",
        "run the active offline GeoTIFF checks on promoted tiles",
    ]
    source_gate = {
        "contract_version": "source-gate/v1",
        "assessment_id": "NEPAL-M2-DEM-LIVE-SOURCE-GATE-001",
        "assessed_at": args.assessed_at_utc,
        "authority": {"mode": "inherited", "authority_ref": APPROVAL_REF, "authorized_actions": approved_actions, "expires_at_utc": None},
        "intended_use": {"summary": "Acquire and verify only four exact public Copernicus DEM GLO-30 tiles for the already bounded Sentinel-1 terrain route.", "planned_actions": approved_actions},
        "sources": source_entries,
        "decision": {"status": "ready", "blocking_reasons": [], "live_verification_pending": [], "approved_actions": approved_actions},
        "write_boundary": {
            "permitted_without_further_authorization": approved_actions,
            "requires_explicit_authorization": ["use any different tile, route, or license", "create or change an account", "use credentials or a paid or requester-pays route", "redistribute raw DEM data", "publish scientific claims or emergency guidance"],
        },
    }
    source_gate_sha = sha256_bytes(canonical_bytes(source_gate))
    path_checks = {
        "project_root": str(project_root),
        "repository_root": str(ROOT.resolve()),
        "external_data_root": str(external_root),
        "external_data_root_exists": external_root.exists(),
        "custody_root": str(custody_root),
        "custody_root_exists": custody_root.exists(),
        "dem_staging_root": str(staging_root),
        "dem_staging_root_exists": staging_root.exists(),
        "outside_git": True,
        "existing_path_evidence": path_evidence,
        "existing_destination_or_staging_paths": collisions,
        "case_insensitive_path_collision": casefold_collision,
        "resolved_asset_path_count": len(resolved_paths),
    }
    preflight = {
        "schema_version": "1.0",
        "preflight_id": "NEPAL-M2-DEM-PREFLIGHT-001",
        "status": "pass_no_payload_no_external_mutation",
        "assessed_at_utc": args.assessed_at_utc,
        "authority": {"approval_ref": APPROVAL_REF, "approval_sha256": sha256_file(APPROVAL_REF), "active_milestone_ref": MILESTONE_REF, "active_milestone_sha256": sha256_file(MILESTONE_REF)},
        "source_gate": {"ref": SOURCE_GATE_REF, "sha256": source_gate_sha, "decision": "ready", "exact_tile_count": len(tile_checks)},
        "license_check": {"url": license_url, "status_code": license_status, "resolved_url": license_resolved, "content_length_bytes": len(license_body), "content_type": license_headers.get("content-type"), "last_modified": license_headers.get("last-modified"), "sha256": sha256_bytes(license_body), "checks": license_checks, "status": "pass"},
        "tile_checks": tile_checks,
        "paths": path_checks,
        "storage": {"volume": project_root.drive, "free_bytes": free_bytes, "free_gib": round(free_bytes / (1024 ** 3), 3), "exact_tile_bytes": total_bytes, "minimum_working_bytes": required_working_bytes, "minimum_formula": "three_times_exact_tile_bytes_for_staging_promotion_and_headroom", "status": "pass"},
        "access": {"anonymous_https": True, "authentication_performed": False, "account_action_performed": False, "requester_pays_encountered": False, "redirect_encountered": False, "cost_incurred": False},
        "checks": {"exact_approval_and_license": "pass", "four_exact_stac_items": "pass", "four_exact_anonymous_objects": "pass", "remote_identity_unchanged": "pass", "free_space": "pass", "path_containment_and_reparse_safety": "pass", "destination_and_staging_collisions": "pass"},
        "eligible_next_actions": ["create only missing DEM custody and staging directories beneath the approved existing external root", "acquire the first exact tile through append-only staging and no-replace promotion"],
        "mutations_performed": {"external_directory_created": False, "dem_payload_requested": False, "dem_payload_bytes_received": 0, "authentication": False, "account_or_terms_action": False},
        "limitations": ["License and STAC GETs plus object HEADs establish current legal and remote identity controls only.", "No DEM payload byte, local file identity, GeoTIFF readability, valid-pixel coverage, vertical-datum fitness, terrain correction, or scientific result is established.", "The S3 ETag is remote identity metadata and is not asserted to be a content checksum."],
    }
    preflight_sha = sha256_bytes(canonical_bytes(preflight))
    create_new(SOURCE_GATE_REF, source_gate)
    create_new(PREFLIGHT_REF, preflight)
    print(json.dumps({"status": preflight["status"], "assessed_at_utc": args.assessed_at_utc, "source_gate_sha256": source_gate_sha, "preflight_sha256": preflight_sha, "tile_count": len(tile_checks), "exact_tile_bytes": total_bytes, "free_gib": preflight["storage"]["free_gib"], "dem_payload_bytes_received": 0, "external_mutation": False}, indent=2))


if __name__ == "__main__":
    main()
