#!/usr/bin/env python3
"""Build the predeclared Sentinel-2 optical baseline processing contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from optical_processing_core import REQUIRED_CHANGE_BANDS, validate_contract


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = "config/qa/optical-baseline-processing-contract.json"


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
    pixel_contract = load_json("config/qa/pixel-readiness-contract.json")
    source_manifest = load_json("records/source-manifest.json")
    optical_pair = next(item for item in pair_plan["pairs"] if item["pair_id"] == "PAIR-S2-RUM-R119")
    sources = {item["source_id"]: item for item in source_manifest["records"]}
    before = sources[optical_pair["before_source_ids"][0]]
    after = sources[optical_pair["after_source_ids"][0]]
    aoi_projected = load_json("config/aoi/approved-study-areas-epsg32645.json")
    extent = aoi_projected["projectMetadata"]["extent"]
    cell = 20.0
    snapped_extent = {
        "xmin": math.floor(extent["xmin"] / cell) * cell,
        "ymin": math.floor(extent["ymin"] / cell) * cell,
        "xmax": math.ceil(extent["xmax"] / cell) * cell,
        "ymax": math.ceil(extent["ymax"] / cell) * cell,
    }
    return {
        "schema_version": "1.0",
        "contract_id": "NEPAL-S2-BASELINE-PROCESSING-001",
        "status": "predeclared_no_real_processing",
        "created_at_utc": created_at,
        "bindings": {
            "source_manifest_ref": "records/source-manifest.json",
            "source_manifest_sha256": sha256_file("records/source-manifest.json"),
            "source_manifest_approval_ref": "records/source-gates/source-manifest-approval.json",
            "source_manifest_approval_sha256": sha256_file("records/source-gates/source-manifest-approval.json"),
            "acquisition_plan_ref": "records/acquisition-plan.json",
            "acquisition_plan_sha256": sha256_file("records/acquisition-plan.json"),
            "active_verification_ref": "contracts/m2-offline-verification.json",
            "active_verification_sha256": sha256_file("contracts/m2-offline-verification.json"),
            "pair_plan_ref": "config/qa/candidate-pair-plan.json",
            "pair_plan_sha256": sha256_file("config/qa/candidate-pair-plan.json"),
            "pixel_readiness_ref": "config/qa/pixel-readiness-contract.json",
            "pixel_readiness_sha256": sha256_file("config/qa/pixel-readiness-contract.json"),
            "approved_aoi_ref": "config/aoi/approved-study-areas-epsg32645.json",
            "approved_aoi_sha256": sha256_file("config/aoi/approved-study-areas-epsg32645.json"),
        },
        "runtime": {
            "product": "ArcGISPro",
            "version": "3.7.1",
            "license_level": "Advanced",
            "spatial_analyst": "required",
        },
        "authority": {
            "authority_ref": "records/source-gates/m2-activation-approval.json",
            "processing_permitted_only_after_verified_custody": True,
            "real_pixel_processing_started": False,
            "additional_product_acquisition_authorized": False,
            "threshold_tuning_to_strengthen_visual_result_authorized": False,
            "scientific_publication_authorized": False,
            "this_contract_creates_authority": False,
        },
        "route": {
            "pair_id": optical_pair["pair_id"],
            "before_source_id": before["source_id"],
            "before_product_id": before["exact_product_id"],
            "before_platform": "Sentinel-2C",
            "before_acquisition_start_utc": before["acquisition_start_utc"],
            "before_catalog_cloud_cover_percent": before["catalog_cloud_cover_percent"],
            "after_source_id": after["source_id"],
            "after_product_id": after["exact_product_id"],
            "after_platform": "Sentinel-2B",
            "after_acquisition_start_utc": after["acquisition_start_utc"],
            "after_catalog_cloud_cover_percent": after["catalog_cloud_cover_percent"],
            "tile_id": "45RUM",
            "relative_orbit_number": 119,
            "processing_baseline_from_product_name": "05.12",
            "pixel_status": "not_evaluated_no_pixels",
        },
        "input_requirements": {
            "custody_state": "promoted_and_offline_verification_passed",
            "internal_product_identity_matches_manifest": True,
            "internal_processing_baseline_matches_product_name": True,
            "required_metadata": [
                "MTD_MSIL2A.xml",
                "GRANULE/*/MTD_TL.xml",
                "PROCESSING_BASELINE",
                "BOA_QUANTIFICATION_VALUE",
                "BOA_ADD_OFFSET for every used band",
                "Special_Values including NoData",
            ],
            "required_quality_inputs": [
                "GRANULE/*/IMG_DATA/R20m/*_SCL_20m.jp2",
                "GRANULE/*/QI_DATA/*",
            ],
            "source_crs_wkid": 32645,
        },
        "reflectance_scaling": {
            "processing_baseline_minimum_for_offset_rule": "04.00",
            "formula": "(DN + BOA_ADD_OFFSET_band) / BOA_QUANTIFICATION_VALUE",
            "dn_zero_policy": "NoData_before_offset_or_scaling",
            "offset_source": "MTD_MSIL2A.xml per-band metadata",
            "quantification_source": "MTD_MSIL2A.xml product metadata",
            "hardcoded_offset_prohibited": True,
            "hardcoded_divide_by_10000_without_metadata_check_prohibited": True,
            "output_pixel_type": "F32",
            "unit": "unitless_bottom_of_atmosphere_surface_reflectance",
            "negative_reflectance_policy": "retain_if_valid_and_unmasked; do not clamp silently",
            "above_one_policy": "retain_if valid_and_unmasked; do not clamp silently",
        },
        "bands": {
            "change_core": sorted(REQUIRED_CHANGE_BANDS),
            "native_10m": ["B02", "B03", "B04", "B08"],
            "native_20m": ["B11", "B12", "SCL"],
            "true_color_display": ["B04", "B03", "B02"],
            "false_color_display": ["B08", "B04", "B03"],
            "resample_10m_to_20m": "BILINEAR",
            "categorical_resampling": "NEAREST",
        },
        "analysis_grid": {
            "wkid": 32645,
            "name": "WGS 1984 UTM Zone 45N",
            "cell_size_m": 20.0,
            "snap_basis": "approved AOI union extent snapped outward to 20 metre multiples",
            "extent": snapped_extent,
            "columns": int(round((snapped_extent["xmax"] - snapped_extent["xmin"]) / cell)),
            "rows": int(round((snapped_extent["ymax"] - snapped_extent["ymin"]) / cell)),
            "continuous_resampling": "BILINEAR",
            "categorical_resampling": "NEAREST",
            "grid_drift_disposition": "block",
        },
        "mask": {
            "profile_ref": "config/qa/pixel-readiness-contract.json#optical_scl",
            "valid_scl_classes": pixel_contract["optical_scl"]["valid_surface_classes"],
            "excluded_scl_classes": pixel_contract["optical_scl"]["excluded_classes"],
            "unknown_class_policy": "exclude_and_defer_review",
            "apply_before_index_calculation": True,
            "dn_zero_always_excluded": True,
            "saturation_and_quality_masks_required": True,
            "primary_cloud_edge_dilation_pixels": 0,
            "cloud_edge_sensitivity_dilation_pixels": [1, 3],
            "sensitivity_outputs_may_replace_primary": False,
            "record_excluded_area_by_reason": True,
        },
        "indices": {
            "NDVI": {"formula": "(B08 - B04) / (B08 + B04)", "role": "vegetation response context"},
            "MNDWI": {"formula": "(B03 - B11) / (B03 + B11)", "role": "open water and wet-surface context"},
            "NBR": {"formula": "(B08 - B12) / (B08 + B12)", "role": "disturbance context; not a fire-specific claim here"},
            "denominator_absolute_minimum": 1e-6,
            "invalid_denominator_policy": "NoData_and_record_count",
            "index_range_check": [-1.0, 1.0],
        },
        "cross_platform": {
            "before_platform": "Sentinel-2C",
            "after_platform": "Sentinel-2B",
            "spectral_response_review_required": True,
            "stable_control_bias_measurement_required": True,
            "unmeasured_harmonization": "prohibited",
            "histogram_matching_over_event_aoi": "prohibited",
            "normalization_if_later_admitted": "derive on stable controls only; retain raw and normalized routes separately",
        },
        "processing_chain": [
            "verify promoted product and internal metadata identity",
            "parse processing baseline, quantification, offsets, and special values",
            "set DN zero and required quality exclusions to NoData",
            "scale each used band to float32 BOA reflectance",
            "resample continuous 10 metre bands to the fixed 20 metre grid",
            "project or copy native EPSG:32645 inputs to the exact grid without changing the mask semantics",
            "apply the conservative SCL and quality mask",
            "derive NDVI, MNDWI, and NBR only where both operands are valid",
            "measure AOI coverage, grid compatibility, and stable-control registration",
            "retain raw, masked, index, exclusion, and QA outputs in versioned external custody",
        ],
        "qa_and_admission": {
            "aoi_coverage_contract_ref": "config/qa/pixel-readiness-contract.json",
            "full_coverage_pass_minimum": pixel_contract["aoi_coverage"]["full_coverage_pass_minimum"],
            "usable_fraction_pass_minimum": pixel_contract["aoi_coverage"]["usable_fraction_pass_minimum"],
            "minimum_stable_control_pairs": pixel_contract["registration"]["minimum_stable_control_pairs"],
            "pass_max_registration_rmse_pixels": pixel_contract["registration"]["pass_max_rmse_pixels"],
            "pass_max_absolute_bias_pixels": pixel_contract["registration"]["pass_max_absolute_bias_pixels"],
            "post_event_high_cloud_risk": True,
            "inconclusive_route_must_be_preserved": True,
            "qa_pass_creates_scientific_admission": False,
        },
        "output_boundary": {
            "root": "C:\\Projects\\Active\\nepal-2026-before-after-map-data",
            "versioned_attempt_paths": True,
            "analysis_raster_format": "GeoTIFF",
            "compression": "LZW",
            "build_pyramids_for_display_copy": True,
            "raw_and_derived_rasters_in_git": False,
            "processing_receipts_in_git": True,
            "overwrite_existing_outputs": False,
        },
        "source_references": [
            {
                "role": "sentinel2_l2a_products_and_scaling",
                "url": "https://sentiwiki.copernicus.eu/web/s2-products",
                "checked_at_utc": created_at,
            },
            {
                "role": "sentinel2_product_specification_v15_1",
                "url": "https://sentinels.copernicus.eu/documents/d/sentinel/sentinel-2-products-specification-document-15_1",
                "checked_at_utc": created_at,
            },
            {
                "role": "cdse_sentinel2_l2a_bands_and_scl",
                "url": "https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html",
                "checked_at_utc": created_at,
            },
        ],
        "claim_boundary": {
            "parameters_predeclared": True,
            "real_product_metadata_parsed": False,
            "real_product_pixels_examined": False,
            "usable_aoi_coverage_established": False,
            "registration_established": False,
            "optical_baseline_established": False,
            "change_established": False,
            "scientific_admission_authorized": False,
        },
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
    print(json.dumps({
        "status": "pass_predeclaration_only",
        "contract_sha256": hashlib.sha256(canonical_bytes(contract)).hexdigest(),
        "pair_id": contract["route"]["pair_id"],
        "real_product_pixels_examined": False,
        "scientific_admission_authorized": False,
    }, indent=2))


if __name__ == "__main__":
    main()
