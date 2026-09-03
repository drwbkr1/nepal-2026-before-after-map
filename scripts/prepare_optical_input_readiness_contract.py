#!/usr/bin/env python3
"""Build the gate-deferred Sentinel-2 materialized-input readiness contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from optical_input_readiness_core import ROLE_PATTERNS, validate_contract


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "config/qa/optical-input-readiness-contract.json"


def load(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def digest(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def build_contract(created_at_utc: str) -> dict[str, Any]:
    processing = load("config/qa/optical-baseline-processing-contract.json")
    contract = {
        "contract_version": "1.0",
        "contract_id": "NEPAL-S2-MATERIALIZED-INPUT-READINESS-001",
        "created_at_utc": created_at_utc,
        "status": "predeclared_gate_deferred_no_real_safe",
        "inputs": {
            "materialization_contract_ref": "contracts/m2-materialization.json",
            "materialization_contract_sha256": digest("contracts/m2-materialization.json"),
            "optical_processing_contract_ref": "config/qa/optical-baseline-processing-contract.json",
            "optical_processing_contract_sha256": digest("config/qa/optical-baseline-processing-contract.json"),
            "pixel_readiness_contract_ref": "config/qa/pixel-readiness-contract.json",
            "pixel_readiness_contract_sha256": digest("config/qa/pixel-readiness-contract.json"),
            "source_manifest_ref": "records/source-manifest.json",
            "source_manifest_sha256": digest("records/source-manifest.json"),
            "core_ref": "scripts/optical_input_readiness_core.py",
            "core_sha256": digest("scripts/optical_input_readiness_core.py"),
            "runner_ref": "scripts/inspect_optical_inputs_arcgis.py",
            "runner_sha256": digest("scripts/inspect_optical_inputs_arcgis.py"),
            "arcgis_adapter_ref": "scripts/validate_optical_input_readiness_arcgis.py",
            "arcgis_adapter_sha256": digest("scripts/validate_optical_input_readiness_arcgis.py"),
        },
        "authority": {
            "mode": "inherited",
            "authority_ref": "records/source-gates/m2-activation-approval.json",
            "required_action_class": "data_processing",
            "this_contract_creates_authority": False,
            "network_access_authorized": False,
            "dem_products_authorized": False,
        },
        "route": {
            "pair_id": processing["route"]["pair_id"],
            "before_source_id": processing["route"]["before_source_id"],
            "before_product_id": processing["route"]["before_product_id"],
            "after_source_id": processing["route"]["after_source_id"],
            "after_product_id": processing["route"]["after_product_id"],
            "processing_baseline": processing["route"]["processing_baseline_from_product_name"],
            "tile": processing["route"]["tile_id"],
            "relative_orbit": processing["route"]["relative_orbit_number"],
        },
        "analysis_crs": {"wkid": 32645, "name": "WGS 1984 UTM Zone 45N"},
        "execution_boundary": {
            "external_data_root": "C:\\Projects\\Active\\nepal-2026-before-after-map-data",
            "receipt_root": "records/readiness/optical-input",
            "network_requests": "prohibited",
            "authentication": "prohibited",
            "external_data_mutation": "prohibited",
            "pixel_value_reads": "prohibited_header_and_identity_reads_only",
            "receipt_replacement": "prohibited",
        },
        "prerequisites": {
            "materialization_receipt_status": "pass_materialization_only",
            "external_manifest_status": "complete",
            "external_complete_marker_required": True,
            "selected_member_size_and_sha256_reverification_required": True,
            "exact_source_pair_required": True,
        },
        "required_members": {
            "exactly_one_per_role": True,
            "role_patterns": ROLE_PATTERNS,
        },
        "header_checks": {
            "format": "JP2",
            "single_band_roles": sorted({"B02", "B03", "B04", "B08", "B11", "B12", "SCL"}),
            "reflectance_pixel_types": ["U12", "U16"],
            "scl_pixel_types": ["U8", "U16"],
            "ten_metre_roles": ["B02", "B03", "B04", "B08"],
            "twenty_metre_roles": ["B11", "B12", "SCL"],
            "cell_size_tolerance_m": 0.000001,
            "extent_tolerance_m": 0.001,
            "extent_must_equal_dimensions_times_cell_size": True,
            "same_extent_within_product_required": True,
            "same_role_grid_across_pair_required": True,
            "quality_classification": {
                "product_member": "MSK_CLASSI_B00.jp2",
                "band_count": 3,
                "cell_size_m": 60.0,
                "pixel_types": ["U1", "U8"],
                "band_semantics": {
                    "1": "opaque_cloud",
                    "2": "cirrus_cloud",
                    "3": "snow_or_ice",
                },
            },
        },
        "metadata_checks": {
            "product_name_baseline_matches_internal_metadata": True,
            "processing_baseline": "05.12",
            "boa_quantification_value_exactly_once": True,
            "all_used_band_offsets_exactly_once": True,
            "dn_zero_identified_as_nodata": True,
        },
        "source_references": [
            {
                "role": "sentinel2_multiband_mask_encoding",
                "url": "https://sentiwiki.copernicus.eu/web/s2-processing",
                "checked_at_utc": created_at_utc,
            },
            {
                "role": "sentinel2_product_specification_v15_1",
                "url": "https://sentinels.copernicus.eu/documents/d/sentinel/sentinel-2-products-specification-document-15_1",
                "checked_at_utc": created_at_utc,
            },
        ],
        "decision_semantics": {
            "pass": "pass_header_readability_only",
            "failure": "block",
            "pass_allows_pixel_qa_only": True,
            "pass_creates_scientific_admission": False,
        },
        "claim_boundary": {
            "member_inventory_established": False,
            "raster_headers_readable": False,
            "pixel_values_examined": False,
            "pixel_usability_established": False,
            "baseline_established": False,
            "change_established": False,
            "scientific_admission_authorized": False,
        },
        "limitations": [
            "A header-readiness pass establishes selected file identity, required inventory, metadata scaling fields, JP2 readability, CRS, dimensions, cell size, and pair grid compatibility only.",
            "It does not inspect pixel values, masks, AOI coverage, saturation, registration residuals, cross-platform bias, or observable change.",
            "The post-event optical scene remains high-cloud-risk and may be unusable after pixel-level mask review.",
            "A blocked or inconclusive optical route must be retained and cannot be rescued by substituting unapproved dates or products.",
        ],
    }
    errors = validate_contract(contract)
    if errors:
        raise ValueError("; ".join(errors))
    return contract


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--created-at-utc", required=True)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    value = build_contract(args.created_at_utc)
    expected = canonical_bytes(value)
    if args.verify_only:
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != expected:
            raise SystemExit("VERIFY FAIL: optical input-readiness contract differs")
        print(f"PASS: {OUTPUT.relative_to(ROOT)}")
        return
    if OUTPUT.exists() and OUTPUT.read_bytes() != expected:
        raise SystemExit("REFUSED: optical input-readiness contract exists with different bytes")
    if not OUTPUT.exists():
        OUTPUT.write_bytes(expected)
    print(json.dumps({"status": value["status"], "contract": str(OUTPUT.relative_to(ROOT)), "required_role_count": len(ROLE_PATTERNS)}, indent=2))


if __name__ == "__main__":
    main()
