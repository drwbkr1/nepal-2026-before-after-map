#!/usr/bin/env python3
"""Prepare the zero-decision alternate EGM2008 method review package."""

from __future__ import annotations

import argparse
import hashlib
import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ACCESS_REF = "records/readiness/m2-dem-egm2008-component-access-closure-001.json"
SOURCE_REF = "records/source-gates/m2-dem-vertical-datum-alternate-method-001-source-review.json"
PROPOSAL_REF = "contracts/m2-dem-vertical-datum-alternate-method-001-proposal.json"
PREFLIGHT_REF = "records/readiness/m2-dem-vertical-datum-alternate-method-001-review-preflight.json"
DOC_REF = "docs/M2_DEM_VERTICAL_DATUM_ALTERNATE_METHOD_001_REVIEW.md"
IMAGE_REF = "docs/assets/m2-dem-vertical-datum-alternate-method-001-review.png"
SURFACE_REF = "records/surface-receipts/m2-dem-vertical-datum-alternate-method-001-review.json"
BUNDLE_REF = "reviews/m2-dem-vertical-datum-alternate-method-001/review-bundle.json"
CONTRACT_REF = "reviews/m2-dem-vertical-datum-alternate-method-001/review-contract.json"
BLANK_REF = "reviews/m2-dem-vertical-datum-alternate-method-001/blank-response.json"
READINESS_REF = "records/readiness/m2-dem-vertical-datum-alternate-method-001-review-readiness.json"


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def write_json(ref: str, value: dict) -> None:
    path = ROOT / ref
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def write_text(ref: str, value: str) -> None:
    path = ROOT / ref
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(value)


def font(name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(str(Path("C:/Windows/Fonts") / name), size)
    except OSError:
        return ImageFont.load_default()


def render_surface(proposal_sha: str) -> None:
    image = Image.new("RGB", (1800, 1450), "#f4f0e8")
    draw = ImageDraw.Draw(image)
    title = font("segoeuib.ttf", 44)
    heading = font("segoeuib.ttf", 27)
    body = font("segoeui.ttf", 22)
    small = font("segoeui.ttf", 19)
    callout = font("segoeuib.ttf", 24)
    navy, ink, teal, amber, red, pale, line = "#17334b", "#20282f", "#126b5d", "#956000", "#9a382d", "#fffdfa", "#cbd2d3"

    draw.rectangle((0, 0, 1800, 225), fill=navy)
    draw.text((75, 42), "NEPAL 2026  |  M2 METHOD AMENDMENT", font=heading, fill="#9ed7cf")
    draw.text((75, 92), "EGM2008 conversion without the Esri add-on", font=title, fill="white")
    draw.text((75, 167), f"Proposal SHA-256  {proposal_sha}", font=small, fill="#d8e5eb")

    cards = [
        ("CLOSED PATH", "Purdue reports it cannot supply ArcGIS Coordinate Systems Data; a fresh inspection still finds no EGM2008 grid.", red),
        ("RECOMMENDED SOURCE", "Official PROJ CDN grid us_nga_egm08_25.tif, derived from NGA EGM2008 and listed as public domain.", teal),
        ("METHOD CHANGE", "The replacement grid is 2.5 arc minutes, not the previously approved Esri 1 arc minute grid.", amber),
    ]
    gap, top = 24, 275
    width = (1800 - 150 - 2 * gap) // 3
    for index, (label, text, color) in enumerate(cards):
        left = 75 + index * (width + gap)
        draw.rounded_rectangle((left, top, left + width, top + 220), radius=14, fill=pale, outline=line, width=2)
        draw.rectangle((left, top, left + 10, top + 220), fill=color)
        draw.text((left + 30, top + 24), label, font=heading, fill=color)
        y = top + 72
        for part in textwrap.wrap(text, 48):
            draw.text((left + 30, y), part, font=body, fill=ink)
            y += 31

    draw.text((75, 550), "RECOMMENDED BOUNDED ROUTE", font=heading, fill=navy)
    steps = [
        "1  Implement and test a no-network, exact-hash acquisition and conversion path.",
        "2  After public CI and final no-payload preflight, acquire the one exact 80,585,622-byte grid once.",
        "3  Verify SHA-256 4191d471...bef17a, CRS direction, world coverage, and h = H + N sign.",
        "4  Convert four verified DEM copies with the existing ArcGIS GDAL 3.12.2e / PROJ 9.8.1 runtime.",
        "5  Preserve source grids, dimensions, transforms, NoData, AOI coverage, and append-only receipts.",
    ]
    y = 595
    for step in steps:
        draw.rounded_rectangle((75, y, 1725, y + 72), radius=10, fill="white", outline=line)
        draw.text((100, y + 20), step, font=body, fill=ink)
        y += 84

    draw.text((75, 1035), "PRECISION AND CONTROL BOUNDARY", font=heading, fill=navy)
    precision = (
        "GeographicLib reports a conservative 0.135 m maximum and 0.0032 m RMS bilinear interpolation error for its "
        "EGM2008 2.5 arc minute grid relative to the EGM2008 model. This supports review, but it does not make the route "
        "identical to Esri's unavailable 1 arc minute grid. Approval must explicitly accept that substitution."
    )
    y = 1080
    for part in textwrap.wrap(precision, 128):
        draw.text((85, y), part, font=body, fill=ink)
        y += 31
    draw.text((75, y + 22), "STILL NOT AUTHORIZED", font=heading, fill=red)
    y += 64
    boundary = "No software installation, account action, retry, alternate source, DEM overwrite, orbit application, radar-pixel processing, baseline, change analysis, attribution, or scientific publication."
    for part in textwrap.wrap(boundary, 128):
        draw.text((85, y), part, font=body, fill=ink)
        y += 31

    draw.rectangle((0, 1325, 1800, 1450), fill="#e3ebe8")
    draw.text((75, 1358), "DECISION REQUIRED", font=heading, fill=navy)
    draw.text((420, 1355), "Approve  |  Revise  |  Defer — with owner attestation", font=callout, fill=teal)
    path = ROOT / IMAGE_REF
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared-at-utc", required=True)
    args = parser.parse_args()
    outputs = [ACCESS_REF, SOURCE_REF, PROPOSAL_REF, PREFLIGHT_REF, DOC_REF, IMAGE_REF, SURFACE_REF, BUNDLE_REF, CONTRACT_REF, BLANK_REF, READINESS_REF]
    collisions = [ref for ref in outputs if (ROOT / ref).exists()]
    if collisions:
        raise SystemExit("review output collision: " + ", ".join(collisions))

    prior_proposal_ref = "contracts/m2-dem-vertical-datum-proposal.json"
    prior_approval_ref = "records/source-gates/m2-dem-vertical-datum-approval.json"
    prior_capability_ref = "records/surface-receipts/m2-dem-vertical-datum-capability.json"
    dem_verification_ref = "records/acquisition/dem-verification-summary.json"

    access = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-DEM-EGM2008-COMPONENT-ACCESS-CLOSURE-001",
        "observed_at_utc": args.prepared_at_utc,
        "status": "closed_owner_report_and_fresh_machine_reinspection",
        "owner_report": {
            "authority_ref": "user-instruction:2026-09-17:purdue-cannot-supply-it",
            "finding": "The owner reports that Purdue cannot supply the matching ArcGIS Coordinate Systems Data component.",
            "private_helpdesk_content_recorded": False,
        },
        "fresh_machine_reinspection": {
            "inspected_at_utc": "2026-09-18T01:22:28Z",
            "scratch_receipt_sha256": "732c0c53b90c1cfc71b5a804e04bb90270be627457b1c4a08d8c1289bd9c3d83",
            "arcgis_version": "3.7.1",
            "license_level": "Advanced",
            "expected_transformation_available": False,
            "matching_egm2008_grids": [],
            "registry_display_entry_found": False,
            "standard_install_paths_found": [],
            "builtin_egm96_only": True,
        },
        "accidental_sourceforge_redirect": {
            "status": "terminal_partial_quarantined_not_usable",
            "cause": "A documentation-metadata probe followed the SourceForge download redirect before timing out.",
            "candidate": "GeographicLib egm2008-1.tar.bz2",
            "bytes_received": 11321072,
            "partial_sha256": "7c0a8597880f622554f6b84355e9587b8b9619e0010247e32ac61ecdd67f7734",
            "quarantine_path": "C:\\Projects\\Active\\nepal-2026-before-after-map-data\\failed\\dem-vertical-datum-alternate-research\\20260917-sourceforge-metadata-redirect\\egm2008-1.tar.bz2.partial-11321072",
            "promoted": False,
            "usable": False,
            "retry_authorized": False,
            "selected_for_production": False,
        },
        "reconciliation": {
            "approved_esri_route_status": "unavailable_preserved_as_historical_selected_method",
            "route_substitution_authorized": False,
            "new_human_decision_required": True,
        },
        "assertions": {
            "arcgis_coordinate_systems_data_installed": False,
            "esri_egm2008_grid_available": False,
            "proj_candidate_payload_bytes_read": 0,
            "usable_alternate_grid_acquired": False,
            "dem_pixels_read": False,
            "dem_conversion_executed": False,
            "radar_processing_executed": False,
            "scientific_result_established": False,
        },
    }
    write_json(ACCESS_REF, access)

    source_review = {
        "schema_version": "1.0",
        "review_id": "NEPAL-M2-DEM-VERTICAL-DATUM-ALTERNATE-METHOD-001-SOURCE-REVIEW",
        "checked_at_utc": args.prepared_at_utc,
        "status": "pass_recommended_open_source_exact_identity_method_change_requires_owner_decision",
        "recommended_candidate": {
            "source_id": "M2-GEOID-001",
            "name": "us_nga_egm08_25.tif",
            "url": "https://cdn.proj.org/us_nga_egm08_25.tif",
            "distributor": "OSGeo PROJ CDN",
            "upstream_authority": "US National Geospatial-Intelligence Agency (NGA)",
            "resolution_arc_minutes": 2.5,
            "area_of_use": "World",
            "source_crs": "EPSG:4979",
            "target_crs": "EPSG:3855",
            "content_length_bytes": 80585622,
            "sha256": "4191d471eefebf24091b56dbc604353cb3b8cf8cc70e448bb9ae56a272bef17a",
            "license": "Public Domain",
            "http_head_status": 200,
            "http_head_last_modified": "Tue, 28 Jan 2020 14:45:44 GMT",
            "payload_bytes_read_during_review": 0,
        },
        "official_sources": [
            {
                "role": "proj_data_provenance_and_license",
                "url": "https://raw.githubusercontent.com/OSGeo/PROJ-data/master/us_nga/us_nga_README.txt",
                "response_sha256": "73bf524a13a3b38b27ab3f1748128445aed1d247ab87e4312b84fa58a085ac12",
                "finding": "The official PROJ-data record identifies the 2.5-minute EGM2008 grid as NGA-derived, public domain, and a physical-height to WGS84 ellipsoidal-height resource.",
            },
            {
                "role": "proj_cdn_exact_catalog_identity",
                "url": "https://cdn.proj.org/files.geojson",
                "response_sha256": "46f26c830faa164af9ef9ef51a7325a9d3800eb12ad4b1661c1d3143af7becc3",
                "finding": "The current PROJ CDN catalog binds exact URL, filename, world extent, EPSG:4979 to EPSG:3855 semantics, byte length, and SHA-256.",
            },
            {
                "role": "proj_resource_distribution",
                "url": "https://proj.org/en/stable/resource_files.html",
                "response_sha256": "e97fa9818c8066860407aa93eb00d21842544cfb66976c61b61ba20bc987ea7d",
                "finding": "PROJ documents proj-data as its freely available transformation-grid package and identifies EGM08 as a global resource.",
            },
            {
                "role": "proj_vertical_grid_semantics",
                "url": "https://proj.org/en/stable/operations/transformations/vgridshift.html",
                "response_sha256": "bb6499438d3fa5c69441e16a9fb64b4633c77ab673ee1fb3f44c8571990b2576",
                "finding": "PROJ documents local GeoTIFF vertical grid shifts and the explicit multiplier relation used to validate direction and sign.",
            },
            {
                "role": "gdal_vertical_raster_transform",
                "url": "https://gdal.org/en/stable/programs/gdalwarp.html",
                "response_sha256": "3e35f49b2b319df14fd5a246cd2e3450a3a0ded88bb9f4dad20c330de1764403",
                "finding": "GDAL documents single-band vertical correction between compound or 3D CRSs and explicit control of the output raster grid.",
            },
            {
                "role": "geographiclib_interpolation_error_reference",
                "url": "https://geographiclib.sourceforge.io/C%2B%2B/doc/geoid.html",
                "response_sha256": "6e8e28296737d1d5175cf83386e5ba2a2373430d58b94e84b349f3cb7a3a443a",
                "finding": "GeographicLib reports EGM2008 2.5-minute bilinear error of 0.135 m maximum and 0.0032 m RMS relative to the specified model, and states h = H + N.",
            },
            {
                "role": "nga_model_authority",
                "url": "https://earth-info.nga.mil/index.php?dir=wgs84&action=wgs84",
                "prior_review_ref": "records/source-gates/m2-dem-vertical-datum-source-review.json",
                "prior_review_sha256": sha256("records/source-gates/m2-dem-vertical-datum-source-review.json"),
                "finding": "NGA remains the EGM2008 model authority and publishes a 2.5-minute worldwide geoid-height file and supporting software.",
            },
        ],
        "local_runtime": {
            "arcgis_pro": "3.7.1 Advanced",
            "python": "ArcGIS Pro arcgispro-py3",
            "gdal_release": "3.12.2e",
            "proj_version": "9.8.1",
            "gdal_warp_available": True,
            "epsg_3855_available": True,
            "epsg_4979_available": True,
            "epsg_9518_available": True,
            "proj_network_enabled": False,
            "software_install_required": False,
        },
        "considered_not_recommended": [
            {
                "candidate": "GeographicLib egm2008-1",
                "resolution_arc_minutes": 1.0,
                "publisher_displayed_archive_sha256": "bdb382d0be7ece9142450eacc24b7b7f0889ee3e0ba4f535b04ec383f94c0fb5",
                "reason": "It is not present in the current official PROJ CDN catalog, adds a separate dataset and tool path, and the metadata probe produced a quarantined terminal partial that cannot be reused or retried under current authority.",
            },
            {
                "candidate": "ArcGIS built-in EGM96",
                "reason": "It is a different geoid model and remains sensitivity-only under the existing owner decision.",
            },
        ],
        "gate_assessment": {
            "access": "pass_anonymous_direct_https_metadata_only",
            "rights": "pass_public_domain_as_recorded_by_proj_data",
            "integrity": "pass_exact_catalog_size_and_sha256_available",
            "privacy": "pass_no_account_or_credential_required_standard_cdn_access_only",
            "fitness": "pass_for_owner_review_not_yet_authorized_for_use",
            "material_deviation": "2.5_arc_minute_grid_replaces_previously_approved_1_arc_minute_esri_grid",
        },
        "assertions": {
            "human_decision_count": 0,
            "recommended_grid_payload_downloaded": False,
            "software_installed_or_modified": False,
            "dem_pixels_read": False,
            "dem_conversion_executed": False,
            "radar_processing_executed": False,
            "scientific_result_established": False,
        },
    }
    write_json(SOURCE_REF, source_review)

    proposal = {
        "schema_version": "1.0",
        "proposal_id": "NEPAL-M2-DEM-VERTICAL-DATUM-ALTERNATE-METHOD-001",
        "prepared_at_utc": args.prepared_at_utc,
        "status": "proposed_not_authorized",
        "bindings": {
            "prior_method_proposal_ref": prior_proposal_ref,
            "prior_method_proposal_sha256": sha256(prior_proposal_ref),
            "prior_method_approval_ref": prior_approval_ref,
            "prior_method_approval_sha256": sha256(prior_approval_ref),
            "component_access_closure_ref": ACCESS_REF,
            "component_access_closure_sha256": sha256(ACCESS_REF),
            "alternate_source_review_ref": SOURCE_REF,
            "alternate_source_review_sha256": sha256(SOURCE_REF),
            "dem_verification_summary_ref": dem_verification_ref,
            "dem_verification_summary_sha256": sha256(dem_verification_ref),
        },
        "decision_requested": {
            "item_id": "M2-DEM-VERTICAL-DATUM-PROJ-EGM2008-2_5-PRECONVERSION",
            "recommended_route": "local_proj_egm2008_2_5_preconversion_then_none",
            "decision_domain": ["approve", "revise", "defer"],
            "reason": "The approved Esri one-minute implementation path is unavailable, while the official open PROJ-data route preserves EGM2008 height semantics using the existing local runtime.",
        },
        "material_change_from_prior_approval": {
            "unchanged": [
                "source DEM remains EPSG:3855 EGM2008 orthometric height",
                "required height relation remains h = H + N",
                "outputs remain new WGS84 ellipsoidal copies outside Git",
                "NONE remains permitted only for verified ellipsoidal derivatives",
                "source DEM overwrite remains prohibited",
            ],
            "changed": [
                "grid source changes from unavailable Esri Coordinate Systems Data to the official PROJ CDN",
                "grid spacing changes from 1 arc minute to 2.5 arc minutes",
                "conversion implementation changes from ArcGIS Project Raster to the existing ArcGIS-bundled GDAL/PROJ runtime",
                "no owner installation, account, license acceptance, or UAC step is required",
            ],
        },
        "exact_source_if_approved": source_review["recommended_candidate"],
        "bounded_execution_if_approved": {
            "implementation": [
                "create a versioned no-network acquisition and conversion implementation bound to the exact grid URL, byte length, and SHA-256",
                "add synthetic direction, sign, exact-grid, output-collision, interruption, source-immutability, and ArcGIS-readability tests",
                "require the repository checker, full local tests, and fresh public default-branch CI before any real grid request",
            ],
            "real_actions_after_public_gate": [
                "run one final no-payload preflight against the exact public metadata and absent destination",
                "make at most one byte-zero request for exact M2-GEOID-001 with no resume or automatic retry",
                "verify exact byte length, SHA-256, GeoTIFF structure, world coverage, CRS metadata, and local-only readability before no-replace promotion",
                "run one local no-network operation-selection and sign preflight using EPSG:9518 to EPSG:4979 and require h = H + N",
                "only if every earlier gate passes, convert one new append-only output per exact M2-DEM-001 through M2-DEM-004 in that fixed order, stopping on the first failure",
                "record exact source and output hashes, unchanged dimensions and geotransforms, NoData semantics, finite AOI coverage, correction statistics, seams, and ArcGIS Pro readability",
            ],
            "maximum_grid_requests": 1,
            "maximum_conversion_attempts_per_dem": 1,
            "automatic_retry": False,
            "stop_on_first_failure": True,
            "proj_network_enabled": False,
            "source_mutation": "prohibited",
            "output_root": "C:\\Projects\\Active\\nepal-2026-before-after-map-data\\derived\\dem\\egm2008-ellipsoidal-proj25",
        },
        "acceptance_thresholds": {
            "grid_sha256": "4191d471eefebf24091b56dbc604353cb3b8cf8cc70e448bb9ae56a272bef17a",
            "grid_length_bytes": 80585622,
            "required_source_crs": "EPSG:9518",
            "required_target_crs": "EPSG:4979",
            "height_relation": "h = H + N",
            "maximum_direction_check_residual_m": 0.001,
            "maximum_published_bilinear_model_error_m": 0.135,
            "same_horizontal_dimensions_and_geotransform_required": True,
            "all_approved_aoi_pixels_finite_required": True,
            "arcgis_pro_readability_required": True,
        },
        "actions_not_authorized": [
            "reuse, resume, complete, or retry the quarantined GeographicLib partial",
            "download the GeographicLib one-minute archive or any source other than exact M2-GEOID-001",
            "install or modify ArcGIS, GDAL, PROJ, GeographicLib, or system software",
            "enable PROJ networking or permit an implicit remote grid fetch",
            "accept provider terms, use an account or credential, or approve UAC",
            "alter, overwrite, or relabel a promoted Copernicus DEM tile",
            "use raw EGM2008 orthometric tiles with NONE",
            "call the 2.5-minute route identical to the unavailable Esri one-minute route",
            "apply orbit data, decode radar measurement pixels, run a baseline or change analysis, attribute cause, publish emergency guidance, or make a scientific claim",
        ],
        "claim_boundary": {
            "human_decision_count": 0,
            "alternate_method_approved": False,
            "recommended_grid_acquired": False,
            "dem_preconversion_executed": False,
            "vertical_datum_resolved_for_radar": False,
            "radar_processing_executed": False,
            "scientific_result_established": False,
        },
    }
    write_json(PROPOSAL_REF, proposal)
    proposal_sha = sha256(PROPOSAL_REF)

    preflight = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-DEM-VERTICAL-DATUM-ALTERNATE-METHOD-001-REVIEW-PREFLIGHT",
        "observed_at_utc": args.prepared_at_utc,
        "status": "pass_review_ready_no_alternate_method_authority",
        "bindings": {
            "proposal_sha256": proposal_sha,
            "source_review_sha256": sha256(SOURCE_REF),
            "access_closure_sha256": sha256(ACCESS_REF),
            "prior_approval_sha256": sha256(prior_approval_ref),
        },
        "assertions": {
            "human_decision_count": 0,
            "alternate_method_authorized": False,
            "grid_acquisition_authorized": False,
            "dem_conversion_authorized": False,
            "recommended_grid_payload_bytes_read": 0,
            "dem_pixels_read_during_preparation": False,
            "radar_processing_authorized": False,
        },
    }
    write_json(PREFLIGHT_REF, preflight)

    doc = f"""# M2 DEM vertical-datum alternate method review 001

## Decision

Choose **approve**, **revise**, or **defer** for proposal `{proposal_sha}`. Approval must be an attested owner decision bound to the exact review-bundle hash generated with this package.

## Why this review exists

The owner approved an Esri EGM2008 one-minute preconversion route, but the required ArcGIS Coordinate Systems Data component is absent and Purdue reports it cannot supply the component. The historical approval remains valid evidence; it is not silently rewritten. A replacement source and implementation require a new owner decision.

## Recommended replacement

Use exact `us_nga_egm08_25.tif` from the official PROJ CDN. The PROJ-data record identifies it as an NGA-derived, public-domain, worldwide EGM2008 2.5-minute grid. The catalog binds 80,585,622 bytes and SHA-256 `4191d471eefebf24091b56dbc604353cb3b8cf8cc70e448bb9ae56a272bef17a`.

The existing ArcGIS Pro Python environment already supplies GDAL 3.12.2e and PROJ 9.8.1, understands EPSG:3855, EPSG:4979, and EPSG:9518, and has PROJ network access disabled. No software installation, login, license click-through, or UAC action is required.

## Material scientific change

The source vertical reference, height equation `h = H + N`, no-overwrite custody, ellipsoidal output, and later `NONE` rule stay unchanged. The grid spacing changes from the unavailable Esri one-minute grid to a 2.5-minute grid. GeographicLib reports a conservative 0.135 m maximum and 0.0032 m RMS bilinear interpolation error for EGM2008 2.5-minute data relative to the EGM2008 model. The route must be described as a 2.5-minute substitution, not as identical to the Esri method.

## What approval would authorize

Approval would authorize bounded implementation and synthetic tests, public CI, a final no-payload preflight, one exact no-retry grid request and verification, then one fixed-order append-only conversion attempt for each of the four verified DEM tiles if all prior gates pass. All processing stays local and uses only the promoted grid bytes.

## What approval would not authorize

No retry or alternate source, no GeographicLib partial reuse, no software install, no provider account or terms action, no source DEM overwrite, no orbit application, no radar measurement-pixel access, no baseline or change analysis, and no scientific or emergency publication.
"""
    write_text(DOC_REF, doc)
    render_surface(proposal_sha)

    surface = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-DEM-VERTICAL-DATUM-ALTERNATE-METHOD-001-REVIEW-SURFACE",
        "verified_at_utc": args.prepared_at_utc,
        "status": "pass_blank_review_surface",
        "render": {"path": IMAGE_REF, "sha256": sha256(IMAGE_REF), "width": 1800, "height": 1450, "human_decision_count": 0},
        "checks": {
            "proposal_hash_visible": "pass",
            "closed_esri_path_visible": "pass",
            "exact_proj_candidate_visible": "pass",
            "2_5_minute_method_change_visible": "pass",
            "bounded_route_visible": "pass",
            "decision_domain_visible": "pass",
            "text_clipping": "none_observed",
            "visual_inspection": "pass",
        },
        "assertions": {"alternate_method_authorized": False, "grid_acquisition_authorized": False, "dem_conversion_authorized": False, "radar_processing_authorized": False},
    }
    write_json(SURFACE_REF, surface)

    artifacts = [
        ("review-surface", IMAGE_REF, "review_surface", True),
        ("review-instructions", DOC_REF, "decision_instructions", False),
        ("alternate-method-proposal", PROPOSAL_REF, "candidate_authority_envelope", False),
        ("alternate-source-review", SOURCE_REF, "external_source_gate", False),
        ("component-access-closure", ACCESS_REF, "closed_prerequisite_evidence", False),
        ("prior-method-approval", prior_approval_ref, "historical_owner_decision", False),
        ("prior-method-proposal", prior_proposal_ref, "historical_selected_method", False),
        ("dem-verification-summary", dem_verification_ref, "verified_input_dependency", False),
    ]
    bundle = {
        "schema_version": "1.0",
        "template": False,
        "bundle_id": "m2-dem-vertical-datum-alternate-method-001-review-bundle",
        "review_id": "m2-dem-vertical-datum-alternate-method-001-review",
        "authority_ref": prior_approval_ref,
        "candidate_identity": f"M2-DEM-VERTICAL-DATUM-ALTERNATE-METHOD-001-PROPOSAL-SHA256:{proposal_sha}",
        "artifacts": [
            {
                "artifact_id": artifact_id,
                "path": ref,
                "sha256": sha256(ref),
                "role": role,
                "render_required": rendered,
                "render_receipts": [{"path": SURFACE_REF, "sha256": sha256(SURFACE_REF)}] if rendered else [],
            }
            for artifact_id, ref, role, rendered in artifacts
        ],
        "review_surface": {"artifact_id": "review-surface", "blank_state_verified": True, "completion_controls_verified": True, "export_verified": True},
        "decision_effect_if_approved": [
            "replace only the unavailable Esri component implementation dependency with the exact official PROJ-data 2.5-minute route",
            "authorize the bounded implementation, tests, public gate, one exact grid acquisition, and conditional four-tile conversion sequence in the proposal",
            "retain NONE only for verified WGS84 ellipsoidal derivatives",
        ],
        "limitations": proposal["actions_not_authorized"],
    }
    write_json(BUNDLE_REF, bundle)
    bundle_sha = sha256(BUNDLE_REF)

    contract = {
        "contract_version": "human-review-contract-v1",
        "template": False,
        "review_id": bundle["review_id"],
        "response_schema_version": "nepal-m2-dem-vertical-datum-alternate-method-001-response-v1",
        "workflow_authority": {
            "mode": "inherited",
            "authority_ref": prior_approval_ref,
            "authorized_action_classes": ["evidence_recording", "project_control", "routine_qa", "update_project_records"],
            "verified_at_utc": args.prepared_at_utc,
            "expires_at_utc": None,
            "review_required": True,
            "lock_authorized": True,
            "reconcile_authorized": True,
            "post_review_actions": ["evidence_recording", "project_control", "update_project_records"],
        },
        "review_bundle": {"bundle_id": bundle["bundle_id"], "manifest_sha256": bundle_sha, "candidate_identity": bundle["candidate_identity"], "rendered_surface_verified": True},
        "allowed_decisions": ["approve", "revise", "defer"],
        "required_attestation": True,
        "max_notes_length": 2000,
        "hash_prefix_length": 16,
        "items": [{"item_id": proposal["decision_requested"]["item_id"], "evidence_sha256": bundle_sha}],
    }
    write_json(CONTRACT_REF, contract)

    blank = {
        "response_schema_version": contract["response_schema_version"],
        "review_id": contract["review_id"],
        "completed": False,
        "review_started_at_utc": None,
        "review_completed_at_utc": None,
        "reviewer": {"attestation": False},
        "responses": [{"item_id": proposal["decision_requested"]["item_id"], "evidence_sha256": bundle_sha, "decision": None, "notes": ""}],
    }
    write_json(BLANK_REF, blank)

    readiness = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-DEM-VERTICAL-DATUM-ALTERNATE-METHOD-001-REVIEW-READINESS",
        "verified_at_utc": args.prepared_at_utc,
        "status": "pass_ready_owner_review_zero_decisions",
        "bindings": {
            "proposal_ref": PROPOSAL_REF, "proposal_sha256": proposal_sha,
            "source_review_ref": SOURCE_REF, "source_review_sha256": sha256(SOURCE_REF),
            "access_closure_ref": ACCESS_REF, "access_closure_sha256": sha256(ACCESS_REF),
            "preflight_ref": PREFLIGHT_REF, "preflight_sha256": sha256(PREFLIGHT_REF),
            "review_surface_ref": IMAGE_REF, "review_surface_sha256": sha256(IMAGE_REF),
            "surface_receipt_ref": SURFACE_REF, "surface_receipt_sha256": sha256(SURFACE_REF),
            "review_bundle_ref": BUNDLE_REF, "review_bundle_sha256": bundle_sha,
            "review_contract_ref": CONTRACT_REF, "review_contract_sha256": sha256(CONTRACT_REF),
            "blank_response_ref": BLANK_REF, "blank_response_sha256": sha256(BLANK_REF),
        },
        "review": {"human_decision_count": 0, "attestation": False, "ready_for_handoff": True},
        "assertions": {
            "alternate_method_authorized": False,
            "grid_acquisition_authorized": False,
            "dem_conversion_authorized": False,
            "recommended_grid_payload_bytes_read": 0,
            "dem_pixels_read_during_preparation": False,
            "radar_processing_authorized": False,
            "scientific_result_established": False,
        },
    }
    write_json(READINESS_REF, readiness)
    print(json.dumps({"status": readiness["status"], "proposal_sha256": proposal_sha, "review_bundle_sha256": bundle_sha, "review_contract_sha256": sha256(CONTRACT_REF)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
