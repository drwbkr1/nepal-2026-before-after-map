#!/usr/bin/env python3
"""Derive non-authorizing DEM intake and offline-verification controls."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INTAKE_PATH = "contracts/m2-dem-intake-candidate.json"
VERIFICATION_PATH = "contracts/m2-dem-offline-verification-candidate.json"


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_file(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def load_json(relative: str) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {relative}")
    return value


def build_intake(manifest: dict[str, Any], proposal: dict[str, Any]) -> dict[str, Any]:
    assets = []
    for record in manifest["records"]:
        filename = record["item_id"] + ".tif"
        assets.append(
            {
                "asset_id": record["source_id"].lower(),
                "source": {
                    "kind": "https",
                    "uri": record["anonymous_https_url"],
                    "authorization_ref": "pending:contracts/milestone-002-dem-amendment-proposal.json",
                    "terms_ref": manifest["license"]["url"],
                    "transport_exception_ref": None,
                },
                "destination_relative_path": f"dem/copernicus-glo30/{filename}",
                "staging_relative_path": f"{record['source_id'].lower()}/{filename}.part",
                "expected": {
                    "sha256": None,
                    "size_bytes": record["anonymous_head"]["content_length_bytes"],
                    "unavailable_reason": (
                        "The publisher route exposes a byte length and ETag but no upstream SHA-256. "
                        "Revalidate the remote identity and compute SHA-256 locally before promotion."
                    ),
                },
                "observed": {
                    "staged_sha256": None,
                    "staged_size_bytes": None,
                    "promoted_sha256": None,
                    "promoted_size_bytes": None,
                },
                "state": "planned",
                "attempts": [],
                "failure": None,
                "superseded_by": None,
                "extensions": {
                    "source_id": record["source_id"],
                    "item_id": record["item_id"],
                    "collection": record["collection"],
                    "remote_etag_metadata": record["anonymous_head"]["etag"],
                    "remote_last_modified_metadata": record["anonymous_head"]["last_modified"],
                    "remote_accept_ranges_metadata": record["anonymous_head"]["accept_ranges"],
                    "expected_bbox_wgs84": record["bbox_wgs84"],
                    "expected_shape": record["shape"],
                    "expected_data_type": record["data_type"],
                    "intended_use": "Sentinel-1 terrain correction and terrain-geometry screening only",
                },
            }
        )

    return {
        "contract_version": "1.0",
        "intake_id": "nepal-m2-dem-intake-001",
        "created_at": manifest["generated_at_utc"],
        "collision_policy": "fail",
        "promotion_mode": "atomic-no-replace",
        "secret_policy": "references-only",
        "custody_root": "nepal-2026-before-after-map-data/custody",
        "staging_root": "nepal-2026-before-after-map-data/.intake-staging/nepal-m2-dem-intake-001",
        "assets": assets,
        "extensions": {
            "status": "candidate_static_control_not_authorized",
            "project_root_basis": "parent_of_repository",
            "candidate_manifest_ref": "records/source-gates/m2-dem-candidate-manifest.json",
            "candidate_manifest_sha256": sha256_file("records/source-gates/m2-dem-candidate-manifest.json"),
            "amendment_proposal_ref": "contracts/milestone-002-dem-amendment-proposal.json",
            "amendment_proposal_sha256": sha256_file("contracts/milestone-002-dem-amendment-proposal.json"),
            "review_bundle_ref": "reviews/m2-dem-amendment/review-bundle.json",
            "review_bundle_sha256": sha256_file("reviews/m2-dem-amendment/review-bundle.json"),
            "license_document_sha256": manifest["license"]["document_sha256"],
            "authority_status": proposal["authority"]["mode"],
            "resume_policy": (
                "disabled_until_fresh_accept_ranges_and_unchanged_remote_etag_and_length_are_verified"
            ),
            "redirect_policy": "refuse",
            "static_only_no_network_or_external_filesystem_mutation": True,
        },
    }


def build_verification(
    manifest: dict[str, Any], intake: dict[str, Any]
) -> dict[str, Any]:
    intake_by_source = {
        item["extensions"]["source_id"]: item for item in intake["assets"]
    }
    assets = []
    for record in manifest["records"]:
        intake_asset = intake_by_source[record["source_id"]]
        assets.append(
            {
                "source_id": record["source_id"],
                "asset_id": intake_asset["asset_id"],
                "item_id": record["item_id"],
                "raster_relative_path": intake_asset["destination_relative_path"],
                "expected_size_bytes": record["anonymous_head"]["content_length_bytes"],
                "expected_shape": record["shape"],
                "expected_band_count": 1,
                "expected_pixel_type": "F32",
                "expected_crs_wkid": 4326,
                "expected_bbox_wgs84": record["bbox_wgs84"],
                "expected_transform": record["transform"],
                "expected_cell_size_degrees": [
                    abs(record["transform"][1]),
                    abs(record["transform"][5]),
                ],
                "intersects_approved_aois": record["intersects_approved_aois"],
            }
        )

    return {
        "contract_version": "1.0",
        "verification_id": "NEPAL-M2-DEM-OFFLINE-VERIFICATION-001",
        "created_at": manifest["generated_at_utc"],
        "status": "candidate_static_control_not_authorized",
        "inputs": {
            "candidate_manifest_ref": "records/source-gates/m2-dem-candidate-manifest.json",
            "candidate_manifest_sha256": sha256_file("records/source-gates/m2-dem-candidate-manifest.json"),
            "intake_contract_ref": INTAKE_PATH,
            "intake_contract_sha256": hashlib.sha256(canonical_bytes(intake)).hexdigest(),
            "amendment_proposal_ref": "contracts/milestone-002-dem-amendment-proposal.json",
            "amendment_proposal_sha256": sha256_file("contracts/milestone-002-dem-amendment-proposal.json"),
            "review_bundle_ref": "reviews/m2-dem-amendment/review-bundle.json",
            "review_bundle_sha256": sha256_file("reviews/m2-dem-amendment/review-bundle.json"),
            "approved_aoi_ref": "config/aoi/approved-study-areas.geojson",
            "approved_aoi_sha256": sha256_file("config/aoi/approved-study-areas.geojson"),
        },
        "authority": {
            "dem_amendment_status": "not_granted",
            "license_acceptance_authorized": False,
            "network_access_authorized": False,
            "custody_mutation_authorized": False,
            "dem_download_authorized": False,
            "dem_pixel_processing_authorized": False,
            "this_contract_creates_authority": False,
        },
        "execution_boundary": {
            "runtime": "ArcGIS Pro 3.7.1 Python with ArcPy",
            "custody_root_from_proposal": "C:\\Projects\\Active\\nepal-2026-before-after-map-data\\custody",
            "custody_root_must_already_exist": True,
            "source_rasters_are_read_only": True,
            "network_requests": "prohibited",
            "archive_extraction": "not_applicable_direct_geotiff",
            "output_parent_must_already_exist": True,
            "overwrite_existing_receipt": False,
        },
        "raster_controls": {
            "required_container": "GeoTIFF",
            "tiff_signatures": ["49492a00", "4d4d002a"],
            "local_identity_algorithm": "SHA-256",
            "require_exact_remote_metadata_size": True,
            "require_single_band": True,
            "require_float32": True,
            "require_epsg_4326": True,
            "shape_tolerance_pixels": 0,
            "cell_size_absolute_tolerance_degrees": 1e-12,
            "extent_absolute_tolerance_degrees": 1e-9,
            "require_nodata_property_inspection": True,
            "require_statistics_capture": True,
            "require_each_approved_aoi_geometrically_covered": True,
            "valid_pixel_coverage_is_a_separate_later_gate": True,
        },
        "assets": assets,
        "mosaic_controls": {
            "required_source_ids": [item["source_id"] for item in assets],
            "expected_union_bbox_wgs84": [84.0, 27.0, 86.0, 29.0],
            "required_aoi_ids": ["AOI-OVERVIEW", "AOI-SOURCE", "AOI-UPPER-CORRIDOR"],
            "mosaic_creation_during_offline_verification": False,
        },
        "post_container_gates": [
            "valid and nodata pixel fraction within each approved AOI",
            "void, seam, artifact, and terrain plausibility review",
            "vertical datum treatment for ArcGIS terrain flattening",
            "sensitivity of radar outputs to any accepted vertical datum route",
            "scientific fitness and admission review",
        ],
        "limitations": [
            "A pass establishes local identity and structural raster fitness only.",
            "Geometric AOI coverage does not establish valid DEM pixels inside an AOI.",
            "Copernicus GLO-30 orthometric heights use EGM2008, while ArcGIS built-in GEOID handling is documented as EGM96; production terrain correction remains deferred until that mismatch is resolved and recorded.",
            "No scan may run against the candidate contract and no output receipt may replace an existing file.",
        ],
    }


def validate_derivation(
    manifest: dict[str, Any], proposal: dict[str, Any], intake: dict[str, Any], verification: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    records = manifest.get("records", [])
    if len(records) != 4 or len(intake.get("assets", [])) != 4 or len(verification.get("assets", [])) != 4:
        errors.append("manifest, intake, and verification must each contain exactly four DEM assets")
    source_ids = {item.get("source_id") for item in records}
    if source_ids != {"M2-DEM-001", "M2-DEM-002", "M2-DEM-003", "M2-DEM-004"}:
        errors.append("unexpected DEM source identity set")
    if proposal.get("authority", {}).get("mode") != "not_granted":
        errors.append("DEM proposal unexpectedly grants authority")
    if intake.get("extensions", {}).get("authority_status") != "not_granted":
        errors.append("candidate intake must preserve not_granted authority")
    if any(item.get("state") != "planned" or item.get("attempts") != [] for item in intake.get("assets", [])):
        errors.append("candidate intake assets must remain planned with no attempts")
    if any(item.get("expected", {}).get("sha256") is not None for item in intake.get("assets", [])):
        errors.append("candidate intake must not invent upstream SHA-256 values")
    if any(value is True for value in verification.get("authority", {}).values()):
        errors.append("candidate verification authority flags must all be false")
    if verification.get("status") != "candidate_static_control_not_authorized":
        errors.append("candidate verification status differs")
    return errors


def write_new(relative: str, value: object) -> None:
    path = ROOT / relative
    if path.exists():
        raise SystemExit(f"REFUSED: output already exists: {relative}")
    path.write_bytes(canonical_bytes(value))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write the two candidate contracts without replacement.")
    args = parser.parse_args()

    manifest = load_json("records/source-gates/m2-dem-candidate-manifest.json")
    proposal = load_json("contracts/milestone-002-dem-amendment-proposal.json")
    intake = build_intake(manifest, proposal)
    verification = build_verification(manifest, intake)
    errors = validate_derivation(manifest, proposal, intake, verification)
    if errors:
        raise SystemExit("INVALID: " + "; ".join(errors))
    if args.write:
        write_new(INTAKE_PATH, intake)
        write_new(VERIFICATION_PATH, verification)
    print(
        json.dumps(
            {
                "status": "pass_static_candidate_only",
                "assets": len(intake["assets"]),
                "intake_sha256": hashlib.sha256(canonical_bytes(intake)).hexdigest(),
                "verification_sha256": hashlib.sha256(canonical_bytes(verification)).hexdigest(),
                "payload_bytes_requested": False,
                "authority_created": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
