#!/usr/bin/env python3
"""Build and validate the predeclared ArcGIS Sentinel-1 baseline contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = "config/qa/radar-baseline-processing-contract.json"


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_file(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def load_json(relative: str) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {relative}")
    return value


def build_contract(created_at: str) -> dict[str, Any]:
    pair_plan = load_json("config/qa/candidate-pair-plan.json")
    radar_pairs = [item for item in pair_plan["pairs"] if item["sensor_route"] == "radar"]
    dem_manifest = load_json("records/source-gates/m2-dem-candidate-manifest.json")
    return {
        "schema_version": "1.0",
        "contract_id": "NEPAL-S1-BASELINE-PROCESSING-001",
        "status": "predeclared_no_real_processing",
        "created_at_utc": created_at,
        "analysis_crs": {
            "wkid": 32645,
            "name": "WGS 1984 UTM Zone 45N",
            "target_cell_size_m": 10.0,
        },
        "bindings": {
            "pair_plan_ref": "config/qa/candidate-pair-plan.json",
            "pair_plan_sha256": sha256_file("config/qa/candidate-pair-plan.json"),
            "pixel_readiness_ref": "config/qa/pixel-readiness-contract.json",
            "pixel_readiness_sha256": sha256_file("config/qa/pixel-readiness-contract.json"),
            "arcgis_capability_ref": "records/surface-receipts/arcgis-sar-processing-capability.json",
            "arcgis_capability_sha256": sha256_file("records/surface-receipts/arcgis-sar-processing-capability.json"),
            "dem_manifest_ref": "records/source-gates/m2-dem-candidate-manifest.json",
            "dem_manifest_sha256": sha256_file("records/source-gates/m2-dem-candidate-manifest.json"),
            "dem_intake_candidate_ref": "contracts/m2-dem-intake-candidate.json",
            "dem_intake_candidate_sha256": sha256_file("contracts/m2-dem-intake-candidate.json"),
            "dem_verification_candidate_ref": "contracts/m2-dem-offline-verification-candidate.json",
            "dem_verification_candidate_sha256": sha256_file("contracts/m2-dem-offline-verification-candidate.json"),
            "dem_amendment_proposal_ref": "contracts/milestone-002-dem-amendment-proposal.json",
            "dem_amendment_proposal_sha256": sha256_file("contracts/milestone-002-dem-amendment-proposal.json"),
            "dem_review_bundle_ref": "reviews/m2-dem-amendment/review-bundle.json",
            "dem_review_bundle_sha256": sha256_file("reviews/m2-dem-amendment/review-bundle.json"),
        },
        "runtime": {
            "product": "ArcGISPro",
            "version": "3.7.1",
            "license_level": "Advanced",
            "extension": "Image Analyst",
            "capability_status": "available_not_executed_on_product_pixels",
        },
        "authority": {
            "active_m2_authority_ref": "records/source-gates/m2-activation-approval.json",
            "sentinel_processing_after_verified_custody": True,
            "dem_amendment_status": "pending_exact_owner_decision",
            "dem_download_or_pixel_use_authorized": False,
            "auxiliary_orbit_download_authorized": False,
            "credential_parameters_authorized_for_processing_tool": False,
            "scientific_publication_authorized": False,
            "this_contract_creates_authority": False,
        },
        "routes": [
            {
                "pair_id": pair["pair_id"],
                "before_source_ids": pair["before_source_ids"],
                "after_source_ids": pair["after_source_ids"],
                "orbit_direction": pair["comparability"]["orbit_direction"],
                "relative_orbit_number": pair["comparability"]["relative_orbit_number"],
                "polarizations": ["VV", "VH"],
                "date_mosaic_policy": (
                    "assemble same-date slices only after independent slice verification; retain seam and coverage QA"
                    if len(pair["before_source_ids"]) > 1 or len(pair["after_source_ids"]) > 1
                    else "single product per date; do not merge with the other orbit route"
                ),
                "route_independence": "do not combine ascending and descending evidence before independent QA dispositions",
            }
            for pair in radar_pairs
        ],
        "input_requirements": {
            "sentinel_assets": {
                "state": "promoted_and_offline_verification_passed",
                "exact_source_ids": sorted(
                    {
                        source_id
                        for pair in radar_pairs
                        for source_id in pair["before_source_ids"] + pair["after_source_ids"]
                    }
                ),
                "manifest_safe_readable": True,
                "embedded_orbit_metadata_captured": True,
            },
            "dem_assets": {
                "state": "promoted_and_structural_verification_passed",
                "exact_source_ids": [item["source_id"] for item in dem_manifest["records"]],
                "source_crs_wkid": 4326,
                "must_span_entire_processed_sar_extent": True,
                "valid_pixel_coverage_required": True,
            },
        },
        "orbit_policy": {
            "inspect_embedded_osv_first": True,
            "preferred_types": ["precise", "restituted"],
            "predicted_only_disposition": "defer",
            "missing_or_unreadable_disposition": "block",
            "external_osv_download_under_current_authority": False,
            "username_parameter": None,
            "password_parameter": None,
            "cloud_storage_connection_parameter": None,
            "reason": "Updated orbit files are separate auxiliary products and are not part of the current eight-product acquisition boundary.",
        },
        "vertical_datum": {
            "source_dem_height_type": "orthometric",
            "source_dem_model": "EGM2008",
            "source_dem_vertical_crs": "EPSG:3855",
            "arcgis_builtin_geoid_model": "EGM96",
            "status": "defer_pending_empirical_check_or_explicit_method_decision",
            "production_geoid_parameter": None,
            "allowed_evaluation_routes": [
                {
                    "id": "validated_egm2008_to_ellipsoidal_preconversion",
                    "arcgis_geoid_parameter_after_conversion": "NONE",
                    "requirements": [
                        "validated EGM2008 geoid grid or transformation source",
                        "source gate and custody record for any added external grid",
                        "reproducible conversion receipt and spot checks",
                    ],
                },
                {
                    "id": "documented_egm96_sensitivity_route",
                    "arcgis_geoid_parameter": "GEOID",
                    "requirements": [
                        "retain the EGM2008-to-EGM96 model mismatch as a limitation",
                        "quantify sensitivity on stable terrain",
                        "do not admit the route if registration or stable-control thresholds fail",
                    ],
                },
            ],
            "prohibited_shortcuts": [
                "silently treat EGM2008 orthometric heights as ellipsoidal with NONE",
                "silently label ArcGIS EGM96 correction as exact EGM2008 handling",
            ],
        },
        "processing_chain": [
            {
                "step": 1,
                "operation": "validate source identity and embedded orbit metadata",
                "output": "read-only inspection receipt",
            },
            {
                "step": 2,
                "operation": "remove thermal noise",
                "arcgis_tool": "RemoveThermalNoise",
                "output": "per-source per-date intermediate",
            },
            {
                "step": 3,
                "operation": "radiometric calibration",
                "arcgis_tool": "ApplyRadiometricCalibration",
                "calibration_type": "BETA_NOUGHT",
                "output": "linear beta nought",
            },
            {
                "step": 4,
                "operation": "radiometric terrain flattening",
                "arcgis_tool": "ApplyRadiometricTerrainFlattening",
                "calibration_type": "GAMMA_NOUGHT",
                "polarizations": ["VV", "VH"],
                "geoid_parameter": None,
                "outputs": [
                    "linear gamma nought",
                    "scattering area",
                    "native geometric distortion layers",
                    "native geometric distortion mask",
                ],
                "blocked_until": "vertical_datum.status is resolved",
            },
            {
                "step": 5,
                "operation": "geometric terrain correction",
                "arcgis_tool": "ApplyGeometricTerrainCorrection",
                "output_crs_wkid": 32645,
                "output_cell_size_m": 10.0,
                "continuous_resampling": "BILINEAR",
                "categorical_mask_resampling": "NEAREST",
            },
            {
                "step": 6,
                "operation": "derive decibel display and difference layers from positive linear gamma nought",
                "arcgis_tool": "ConvertSARUnits",
                "master_quantitative_units": "LINEAR",
                "derived_display_units": "DECIBEL",
                "nonpositive_policy": "set to NoData and record count",
            },
        ],
        "speckle_policy": {
            "primary_quantitative_route": "no despeckle",
            "reason": "Avoid unreviewed filter tuning and preserve the native quantitative route.",
            "optional_sensitivity_route": {
                "status": "not_selected_for_production",
                "filter": "REFINED_LEE",
                "filter_size": "7x7",
                "may_replace_primary": False,
                "required_label": "filtered sensitivity or display only",
            },
        },
        "geometric_distortion_translation": {
            "retain_native_mask": True,
            "native_to_project_qa": {
                "0": {"native": "undetermined", "project_class": 0, "action": "exclude"},
                "1": {"native": "foreshortening", "project_class": 1, "action": "retain_with_native_flag"},
                "2": {"native": "lengthening", "project_class": 1, "action": "retain_with_native_flag"},
                "3": {"native": "shadow", "project_class": 3, "action": "exclude"},
                "4": {"native": "layover", "project_class": 2, "action": "exclude"},
                "5": {"native": "layover_and_shadow", "project_class": 2, "action": "exclude_and_retain_combined_reason"},
            },
            "additional_project_exclusions": [
                "border noise",
                "residual speckle or unstable background",
                "water variability",
                "registration exclusion",
            ],
        },
        "qa_and_admission": {
            "apply_pixel_readiness_contract": True,
            "minimum_stable_control_pairs": 30,
            "pass_max_registration_rmse_pixels": 0.5,
            "defer_max_registration_rmse_pixels": 1.0,
            "pass_max_absolute_bias_pixels": 0.5,
            "slice_seam_and_date_mosaic_qa_required": True,
            "route_dispositions": ["invalid", "block", "defer", "pass_qa_only"],
            "pass_qa_only_creates_scientific_admission": False,
        },
        "output_boundary": {
            "root": "C:\\Projects\\Active\\nepal-2026-before-after-map-data",
            "versioned_attempt_paths": True,
            "raw_and_derived_rasters_in_git": False,
            "processing_receipts_in_git": True,
            "overwrite_existing_outputs": False,
        },
        "source_references": [
            {
                "role": "arcgis_rtc_tool",
                "url": "https://doc.esri.com/en/arcgis-pro/latest/tool-reference/image-analyst/generate-radiometric-terrain-corrected-data.html",
                "checked_at_utc": created_at,
            },
            {
                "role": "arcgis_radiometric_terrain_flattening",
                "url": "https://doc.esri.com/en/arcgis-pro/latest/tool-reference/image-analyst/apply-radiometric-terrain-flattening.html",
                "checked_at_utc": created_at,
            },
            {
                "role": "arcgis_sentinel1_grd_workflow",
                "url": "https://doc.esri.com/en/arcgis-pro/latest/help/analysis/image-analyst/analysis-ready-sentinel-1-grd-data-generation.html",
                "checked_at_utc": created_at,
            },
            {
                "role": "copernicus_dem_vertical_reference",
                "url": "https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM.html",
                "checked_at_utc": created_at,
            },
        ],
        "claim_boundary": {
            "processing_parameters_predeclared": True,
            "dem_amendment_approved": False,
            "dem_pixels_examined": False,
            "sentinel_pixels_processed": False,
            "baseline_established": False,
            "change_established": False,
            "scientific_admission_authorized": False,
        },
    }


def validate_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if contract.get("status") != "predeclared_no_real_processing":
        errors.append("contract status differs")
    if contract.get("analysis_crs", {}).get("wkid") != 32645:
        errors.append("analysis CRS differs")
    routes = contract.get("routes", [])
    if {item.get("pair_id") for item in routes} != {"PAIR-S1-ASC-R085-IW", "PAIR-S1-DESC-R121-IW"}:
        errors.append("radar route set differs")
    expected_sources = {"M1-SRC-001", "M1-SRC-002", "M1-SRC-003", "M1-SRC-004", "M1-SRC-005", "M1-SRC-006"}
    if set(contract.get("input_requirements", {}).get("sentinel_assets", {}).get("exact_source_ids", [])) != expected_sources:
        errors.append("Sentinel source boundary differs")
    if contract.get("authority", {}).get("dem_download_or_pixel_use_authorized") is not False:
        errors.append("contract must not authorize DEM use")
    if contract.get("authority", {}).get("auxiliary_orbit_download_authorized") is not False:
        errors.append("contract must not authorize auxiliary orbit download")
    if contract.get("vertical_datum", {}).get("status") != "defer_pending_empirical_check_or_explicit_method_decision":
        errors.append("vertical datum mismatch must remain deferred")
    chain = {item["operation"]: item for item in contract.get("processing_chain", [])}
    if chain.get("radiometric calibration", {}).get("calibration_type") != "BETA_NOUGHT":
        errors.append("radiometric calibration must use beta nought")
    if chain.get("radiometric terrain flattening", {}).get("calibration_type") != "GAMMA_NOUGHT":
        errors.append("terrain flattening must output gamma nought")
    if contract.get("speckle_policy", {}).get("primary_quantitative_route") != "no despeckle":
        errors.append("primary speckle policy differs")
    if contract.get("claim_boundary", {}).get("sentinel_pixels_processed") is not False:
        errors.append("contract invents processed pixels")
    return errors


def evaluate_readiness(contract: dict[str, Any], observed: dict[str, Any]) -> dict[str, Any]:
    expected_sentinel = set(contract["input_requirements"]["sentinel_assets"]["exact_source_ids"])
    expected_dem = set(contract["input_requirements"]["dem_assets"]["exact_source_ids"])
    actual_sentinel = set(observed.get("verified_sentinel_source_ids", []))
    actual_dem = set(observed.get("verified_dem_source_ids", []))
    reasons: list[str] = []
    status = "ready_for_controlled_processing"
    if actual_sentinel - expected_sentinel or actual_dem - expected_dem:
        status = "invalid"
        reasons.append("observed source identity falls outside the exact contract")
    elif actual_sentinel != expected_sentinel or actual_dem != expected_dem:
        status = "defer"
        reasons.append("not all exact Sentinel and DEM inputs are verified")
    if status != "invalid" and observed.get("vertical_datum_route_status") != "validated":
        status = "defer"
        reasons.append("vertical datum route is unresolved")
    orbit_types = observed.get("orbit_types_by_source", {})
    if status != "invalid" and set(orbit_types) != expected_sentinel:
        status = "defer"
        reasons.append("orbit metadata is incomplete")
    elif status != "invalid" and any(value not in {"precise", "restituted"} for value in orbit_types.values()):
        status = "defer"
        reasons.append("one or more products have only predicted or unsupported orbit vectors")
    if status != "invalid" and observed.get("pixel_readiness_status") != "pass_qa_only":
        status = "defer"
        reasons.append("pixel-readiness QA has not passed")
    return {
        "status": status,
        "reasons": reasons,
        "scientific_admission_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--created-at-utc", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if not args.created_at_utc.endswith("Z"):
        raise SystemExit("--created-at-utc must end in Z")
    contract = build_contract(args.created_at_utc)
    errors = validate_contract(contract)
    if errors:
        raise SystemExit("INVALID: " + "; ".join(errors))
    if args.write:
        output = ROOT / OUTPUT
        if output.exists():
            raise SystemExit(f"REFUSED: output already exists: {OUTPUT}")
        output.write_bytes(canonical_bytes(contract))
    print(
        json.dumps(
            {
                "status": "pass_predeclaration_only",
                "contract_sha256": hashlib.sha256(canonical_bytes(contract)).hexdigest(),
                "radar_routes": len(contract["routes"]),
                "sentinel_pixels_processed": False,
                "dem_pixels_examined": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
