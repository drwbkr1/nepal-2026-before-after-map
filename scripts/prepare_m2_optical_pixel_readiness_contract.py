#!/usr/bin/env python3
"""Build the exact preobservation optical pixel-readiness contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from optical_pixel_readiness_core_001 import validate_contract


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_REF = "config/qa/optical-pixel-readiness-contract-001.json"
INPUTS = {
    "approval": "records/source-gates/m2-materialization-pixel-readiness-approval.json",
    "header_reconciliation": "records/readiness/m2-full-header-readiness-reconciliation.json",
    "optical_header_receipt": "records/readiness/optical-input/m2-s2-input-readiness-real-001.json",
    "pixel_readiness": "config/qa/pixel-readiness-contract.json",
    "optical_processing": "config/qa/optical-baseline-processing-contract.json",
    "approved_aoi": "config/aoi/approved-study-areas-epsg32645.json",
}
IMPLEMENTATION = {
    "core": "scripts/optical_pixel_readiness_core_001.py",
    "runner": "scripts/run_m2_optical_pixel_readiness_001.py",
    "stage_gate": "scripts/m2_optical_pixel_stage_gate.py",
    "final_preflight": "scripts/preflight_m2_optical_pixel_readiness.py",
    "publication_gate_recorder": "scripts/record_m2_optical_pixel_publication_gate.py",
    "arcgis_adapter": "scripts/validate_optical_pixel_readiness_arcgis_001.py",
    "portable_tests": "tests/test_m2_optical_pixel_readiness.py",
}


def load(ref: str) -> dict:
    return json.loads((ROOT / ref).read_text(encoding="utf-8"))


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def bindings(values: dict[str, str]) -> dict[str, str]:
    result = {}
    for key, ref in values.items():
        result[f"{key}_ref"] = ref
        result[f"{key}_sha256"] = sha256(ref)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--created-at-utc", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    header = load(INPUTS["optical_header_receipt"])
    processing = load(INPUTS["optical_processing"])
    products = {}
    for role, source_id in (("before", "M1-SRC-010"), ("after", "M1-SRC-008")):
        observed = header["products"][source_id]
        selected = {key: observed["inventory"]["members"][key] for key in ("SCL", "B11", "quality_classification")}
        products[role] = {
            "source_id": source_id,
            "materialization_receipt_ref": observed["materialization_receipt_ref"],
            "materialization_receipt_sha256": observed["materialization_receipt_sha256"],
            "external_manifest_sha256": observed["external_manifest_sha256"],
            "selected_members": selected,
        }
    value = {
        "schema_version": "1.0",
        "contract_id": "NEPAL-S2-PIXEL-READINESS-REAL-001",
        "created_at_utc": args.created_at_utc,
        "status": "active_preobservation_exact_pair_one_attempt",
        "inputs": bindings(INPUTS),
        "implementation": bindings(IMPLEMENTATION),
        "authority": {
            "authority_ref": INPUTS["approval"],
            "conditional_optical_pixel_stage_released_by_header_pass": True,
            "network_access_authorized": False,
            "authentication_authorized": False,
            "source_substitution_authorized": False,
            "retry_authorized": False,
            "radar_pixel_access_authorized": False,
            "baseline_or_change_analysis_authorized": False,
            "scientific_publication_authorized": False,
            "this_contract_creates_authority": False,
        },
        "exact_pair": {"before_source_id": "M1-SRC-010", "after_source_id": "M1-SRC-008", "pair_id": "PAIR-S2-RUM-R119"},
        "approved_aoi_ids": ["AOI-OVERVIEW", "AOI-SOURCE", "AOI-UPPER-CORRIDOR"],
        "products": products,
        "analysis_grid": {**processing["analysis_grid"]},
        "mask": {
            "valid_scl_classes": [4, 5, 6],
            "scl_exclusion_classes": [0, 1, 2, 3, 7, 8, 9, 10, 11],
            "quality_classification_role": "MSK_CLASSI_B00 three-band opaque-cloud, cirrus-cloud, snow-or-ice mask",
            "quality_classification_clear_value": 0,
            "dn_zero_excluded_for_registration": True,
            "pair_valid_requires_both_dates_valid": True,
            "exclusive_reason_precedence": ["coverage", "before_scl", "after_scl", "before_quality", "after_quality", "before_dn_zero", "after_dn_zero", "valid_pair"],
            "unknown_scl_policy": "exclude_and_defer_review",
        },
        "registration": {
            "band_role": "B11",
            "candidate_grid_rows": 30,
            "candidate_grid_columns": 30,
            "patch_radius_pixels": 10,
            "search_radius_pixels": 2,
            "minimum_pair_valid_fraction": 0.8,
            "minimum_patch_standard_deviation_dn": 20.0,
            "minimum_correlation": 0.6,
            "event_aoi_exclusion_buffer_m": 1000.0,
            "selection_rule": "use every deterministic candidate meeting the frozen mask texture and correlation filters; do not rank or cherry-pick controls",
            "subpixel_rule": "three-point parabolic refinement around the integer correlation maximum when both neighbors exist",
            "decision_threshold_source": "config/qa/pixel-readiness-contract.json#registration",
        },
        "attempt": {
            "attempt_id": "optical-pixel-readiness-real-001",
            "maximum_real_invocations": 1,
            "automatic_retry_authorized": False,
            "external_attempt_root": r"C:\Projects\Active\nepal-2026-before-after-map-data\derived\optical-pixel-readiness-real-001",
            "public_receipt_ref": "records/readiness/optical-pixel/m2-s2-pixel-readiness-real-001.json",
            "minimum_free_space_bytes": 2147483648,
            "collision_policy": "fail",
        },
        "execution_boundary": {
            "external_data_root": r"C:\Projects\Active\nepal-2026-before-after-map-data",
            "source_materializations": "read_only_and_inventory_compared_before_after",
            "derived_outputs": "append_only_exact_attempt_root",
            "network_requests": "prohibited",
            "authentication": "prohibited",
            "public_imagery": "prohibited",
            "spectral_index_or_change_rasters": "prohibited",
            "candidate_change_polygons": "prohibited",
        },
        "decision_domain": ["pass_qa_only", "defer", "block", "invalid"],
        "history": {
            "preflight_attempt_001_status": "fail_preflight_implementation_path_parent_mismatch",
            "failure_ref": "records/readiness/m2-optical-pixel-final-preflight-attempt-001-failure.json",
            "failure_sha256": "02cfc771bf8414e20dd0d240b826bb59d10606fb6a9cc9fddc7f9870c5f1b8f0",
            "superseded_contract_ref": "config/qa/optical-pixel-readiness-contract-001-preflight-attempt-001-superseded.json",
            "superseded_contract_sha256": "13e99ad4c158122e9c862c9247f85d4bfbca1b949469468a38c6c57905acd5b4",
            "superseded_readiness_ref": "records/readiness/m2-optical-pixel-implementation-readiness-attempt-001-superseded.json",
            "superseded_readiness_sha256": "2644bebb1d85c33ffbaf80f769d0e3c35c6f5febbe31a98f67096b2146116002",
            "superseded_publication_gate_ref": "records/readiness/m2-optical-pixel-publication-gate-attempt-001-superseded.json",
            "superseded_publication_gate_sha256": "c8e18232928477a7a171fb457939daabe6cd91da61b517c976e35aa48a9e7ba3",
            "correction": "validate the frozen derived parent instead of a nonexistent processing parent; no scientific thresholds or source identities changed",
            "real_attempt_started": False
        },
        "claim_boundary": {
            "coverage_mask_grid_and_registration_qa_measured": False,
            "spectral_indices_computed": False,
            "candidate_change_polygons_created": False,
            "baseline_established": False,
            "change_established": False,
            "event_attribution_established": False,
            "scientific_admission_authorized": False,
        },
        "limitations": [
            "The attempt can establish QA fitness only for the exact Sentinel-2 pair and three approved AOIs.",
            "The conservative pair mask requires valid SCL surface classes and clear three-band classification masks on both dates; high post-event cloud may defer or block the route.",
            "Registration controls are deterministic B11 patches outside buffered event AOIs; the method does not prove radiometric comparability or landscape stability everywhere.",
            "No threshold may be changed after real pixels are observed, and no retry, date shopping, or source substitution is authorized.",
            "A pass does not release spectral indices, a baseline, change detection, interpretation, attribution, emergency guidance, or publication.",
        ],
    }
    errors = validate_contract(value)
    if errors:
        raise SystemExit("contract validation failed: " + "; ".join(errors))
    payload = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    if args.write:
        with (ROOT / OUTPUT_REF).open("xb") as stream:
            stream.write(payload)
    print(json.dumps({"status": "pass_contract_build", "output": OUTPUT_REF, "sha256": hashlib.sha256(payload).hexdigest(), "written": args.write, "real_product_pixels_examined": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
