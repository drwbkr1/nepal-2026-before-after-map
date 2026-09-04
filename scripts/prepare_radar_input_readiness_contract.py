#!/usr/bin/env python3
"""Build the exact read-only Sentinel-1 materialized-input readiness contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from radar_input_readiness_core import ROLE_PATTERNS, validate_contract


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = "config/qa/radar-input-readiness-contract.json"
MATERIALIZATION_RECEIPTS = {
    "M1-SRC-001": "records/acquisition/materialization/m1-src-001-fixture-must-not-run.json",
    "M1-SRC-002": "records/acquisition/materialization/m1-src-002-m1-src-002-materialization-001.json",
    "M1-SRC-003": "records/acquisition/materialization/m1-src-003-m1-src-003-materialization-001.json",
}
ROUTES = {
    "M1-SRC-001": "PAIR-S1-ASC-R085-IW",
    "M1-SRC-002": "PAIR-S1-ASC-R085-IW",
    "M1-SRC-003": "PAIR-S1-DESC-R121-IW",
}
PROVENANCE = {
    "M1-SRC-001": "retained_unintended_test_execution",
    "M1-SRC-002": "planned_authorized_offline_materialization",
    "M1-SRC-003": "planned_authorized_offline_materialization",
}


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def load_json(relative: str) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {relative}")
    return value


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def build_contract(created_at_utc: str) -> dict[str, Any]:
    manifest = load_json("records/source-manifest.json")
    source_by_id = {item["source_id"]: item for item in manifest["records"]}
    sources = []
    for source_id in MATERIALIZATION_RECEIPTS:
        source = source_by_id[source_id]
        receipt_ref = MATERIALIZATION_RECEIPTS[source_id]
        receipt = load_json(receipt_ref)
        product_parts = source["exact_product_id"].split("_")
        sources.append({
            "source_id": source_id,
            "event_role": source["event_role"],
            "route_id": ROUTES[source_id],
            "exact_product_id": source["exact_product_id"],
            "acquisition_start_utc": source["acquisition_start_utc"],
            "acquisition_end_utc": source["acquisition_end_utc"],
            "orbit_direction": source["orbit_or_tile"]["orbit_direction"],
            "relative_orbit_number": source["orbit_or_tile"]["relative_orbit_number"],
            "absolute_orbit_number": int(product_parts[6]),
            "operational_mode": source["orbit_or_tile"]["operational_mode"],
            "polarizations": ["VV", "VH"],
            "materialization_provenance": PROVENANCE[source_id],
            "materialization_receipt_ref": receipt_ref,
            "materialization_receipt_sha256": sha256(receipt_ref),
            "external_manifest_sha256": receipt["bindings"]["external_manifest_sha256"],
        })
    inputs = {
        "materialization_contract_ref": "contracts/m2-materialization.json",
        "radar_processing_contract_ref": "config/qa/radar-baseline-processing-contract.json",
        "pixel_readiness_contract_ref": "config/qa/pixel-readiness-contract.json",
        "source_manifest_ref": "records/source-manifest.json",
        "active_m2_ref": "contracts/milestone-002.json",
        "activation_approval_ref": "records/source-gates/m2-activation-approval.json",
        "core_ref": "scripts/radar_input_readiness_core.py",
        "runner_ref": "scripts/inspect_radar_inputs_arcgis.py",
        "arcgis_adapter_ref": "scripts/validate_radar_input_readiness_arcgis.py",
    }
    for key, relative in list(inputs.items()):
        if key.endswith("_ref"):
            inputs[key.removesuffix("_ref") + "_sha256"] = sha256(relative)
    return {
        "contract_version": "1.0",
        "contract_id": "NEPAL-S1-MATERIALIZED-INPUT-READINESS-001",
        "created_at_utc": created_at_utc,
        "status": "predeclared_active_exact_three_pre_event_sources",
        "inputs": inputs,
        "authority": {
            "mode": "inherited",
            "authority_ref": "records/source-gates/m2-activation-approval.json",
            "required_action_classes": ["read_only_inspection", "routine_qa", "metadata_capture", "evidence_recording"],
            "this_contract_creates_authority": False,
            "network_access_authorized": False,
            "baseline_processing_authorized_by_this_contract": False,
        },
        "sources": sources,
        "analysis_crs": {
            "wkid": 32645,
            "name": "WGS 1984 UTM Zone 45N",
            "note": "The raw GRD measurement TIFFs are inspected in native product form; EPSG:32645 applies only after the separately gated terrain-correction chain.",
        },
        "execution_boundary": {
            "external_data_root": "C:\\Projects\\Active\\nepal-2026-before-after-map-data",
            "receipt_root": "records/readiness/radar-input",
            "network_requests": "prohibited",
            "authentication": "prohibited",
            "credential_access": "prohibited",
            "external_data_mutation": "prohibited",
            "pixel_value_decoding": "prohibited_header_and_metadata_reads_only",
            "derived_raster_writes": "prohibited",
            "receipt_replacement": "prohibited",
        },
        "prerequisites": {
            "exact_materialization_receipt_hash_required": True,
            "materialization_receipt_status": "pass_materialization_only",
            "external_manifest_status": "complete",
            "external_complete_marker_required": True,
            "selected_member_size_and_sha256_reverification_required": True,
            "source_archive_mutation_prohibited": True,
        },
        "required_members": {
            "exactly_one_per_role": True,
            "role_patterns": ROLE_PATTERNS,
        },
        "metadata_checks": {
            "mission_id": "S1D",
            "product_type": "GRD",
            "mode": "IW",
            "swath": "IW",
            "polarizations": ["VV", "VH"],
            "pixel_value": "AMPLITUDE",
            "output_pixels": "16 bit unsigned integer",
            "minimum_embedded_orbit_vectors": 2,
            "finite_embedded_position_and_velocity_required": True,
            "strictly_increasing_embedded_orbit_times_required": True,
            "embedded_orbit_vectors_must_bracket_acquisition": True,
            "acquisition_time_tolerance_seconds": 1.0,
            "absolute_orbit_and_direction_must_match_approved_source": True,
        },
        "header_checks": {
            "formats": ["TIFF"],
            "band_count": 1,
            "pixel_types": ["U16"],
            "raster_dimensions_must_match_annotation": True,
            "vv_vh_dimensions_and_pixel_type_must_match_within_source": True,
            "vv_vh_annotation_identity_and_spacing_must_match_within_source": True,
            "raw_measurement_spatial_reference_not_used_as_analysis_crs": True,
        },
        "decision_semantics": {
            "per_source_pass": "pass_header_readability_only",
            "any_identity_inventory_metadata_or_header_failure": "block",
            "all_three_pass_status": "pass_partial_pre_event_header_readiness_only",
            "all_three_pass_reconciles_only_available_pre_event_sources": True,
            "pass_releases_baseline_processing": False,
            "pass_creates_scientific_admission": False,
        },
        "claim_boundary": {
            "member_inventory_established": False,
            "annotation_metadata_established": False,
            "raster_headers_readable": False,
            "pixel_values_examined": False,
            "pixel_usability_established": False,
            "complete_pair_established": False,
            "baseline_established": False,
            "change_established": False,
            "scientific_admission_authorized": False,
        },
        "limitations": [
            "A pass establishes exact selected-member identity, SAFE annotation consistency, embedded state-vector structure, and ArcGIS measurement-header readability for only the three available pre-event radar sources.",
            "It does not decode measurement pixels, establish AOI coverage, apply updated orbit data, terrain-correct a raster, evaluate layover or shadow, or establish registration.",
            "No before-after radar route is complete because M1-SRC-004 through M1-SRC-006 are not in promoted verified custody.",
            "M1-SRC-001 retains unintended-test materialization provenance even if its metadata and headers pass.",
            "The Sentinel recovery, orbit recovery, DEM vertical-datum, terrain-result, pixel-readiness, baseline, change, and scientific gates remain independent.",
        ],
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
    payload = canonical_bytes(contract)
    if args.write:
        output = ROOT / OUTPUT
        try:
            with output.open("xb") as handle:
                handle.write(payload)
        except FileExistsError as exc:
            raise SystemExit(f"REFUSED: output already exists: {OUTPUT}") from exc
    print(json.dumps({
        "status": "pass_predeclaration_only",
        "contract_sha256": hashlib.sha256(payload).hexdigest(),
        "source_count": len(contract["sources"]),
        "real_product_data_read": False,
        "baseline_processing_released": False,
    }, indent=2))


if __name__ == "__main__":
    main()
