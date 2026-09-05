#!/usr/bin/env python3
"""Build exact six-source radar and two-source optical header contracts."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from optical_input_readiness_core_full_cohort_001 import ROLE_PATTERNS as OPTICAL_ROLE_PATTERNS, validate_contract as validate_optical
from radar_input_readiness_core_full_cohort_001 import ROLE_PATTERNS as RADAR_ROLE_PATTERNS, validate_contract as validate_radar


ROOT = Path(__file__).resolve().parents[1]
RADAR_OUTPUT = "config/qa/radar-input-readiness-contract-full-cohort-001.json"
OPTICAL_OUTPUT = "config/qa/optical-input-readiness-contract-full-cohort-001.json"
APPROVAL_REF = "records/source-gates/m2-materialization-pixel-readiness-approval.json"
MATERIALIZATION_RECONCILIATION_REF = "records/acquisition/sentinel-materialization-reconciliation-002.json"
RADAR_SOURCE_ORDER = ["M1-SRC-001", "M1-SRC-002", "M1-SRC-003", "M1-SRC-004", "M1-SRC-005", "M1-SRC-006"]
RADAR_RECEIPTS = {
    "M1-SRC-001": "records/acquisition/materialization/m1-src-001-fixture-must-not-run.json",
    "M1-SRC-002": "records/acquisition/materialization/m1-src-002-m1-src-002-materialization-001.json",
    "M1-SRC-003": "records/acquisition/materialization/m1-src-003-m1-src-003-materialization-001.json",
    "M1-SRC-004": "records/acquisition/materialization/m1-src-004-m1-src-004-materialization-001.json",
    "M1-SRC-005": "records/acquisition/materialization/m1-src-005-m1-src-005-materialization-001.json",
    "M1-SRC-006": "records/acquisition/materialization/m1-src-006-m1-src-006-materialization-001.json",
}
OPTICAL_RECEIPTS = {
    "before": "records/acquisition/materialization/m1-src-010-m1-src-010-materialization-001.json",
    "after": "records/acquisition/materialization/m1-src-008-m1-src-008-materialization-001.json",
}
ROUTES = {
    "M1-SRC-001": "PAIR-S1-ASC-R085-IW",
    "M1-SRC-002": "PAIR-S1-ASC-R085-IW",
    "M1-SRC-003": "PAIR-S1-DESC-R121-IW",
    "M1-SRC-004": "PAIR-S1-ASC-R085-IW",
    "M1-SRC-005": "PAIR-S1-ASC-R085-IW",
    "M1-SRC-006": "PAIR-S1-DESC-R121-IW",
}


def load(ref: str) -> dict[str, Any]:
    value = json.loads((ROOT / ref).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {ref}")
    return value


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def input_bindings(refs: dict[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, ref in refs.items():
        result[f"{key}_ref"] = ref
        result[f"{key}_sha256"] = sha256(ref)
    return result


def build_radar(created_at_utc: str) -> dict[str, Any]:
    manifest = load("records/source-manifest.json")
    by_source = {item["source_id"]: item for item in manifest["records"]}
    sources = []
    for source_id in RADAR_SOURCE_ORDER:
        source = by_source[source_id]
        receipt_ref = RADAR_RECEIPTS[source_id]
        receipt = load(receipt_ref)
        sources.append({
            "source_id": source_id,
            "event_role": source["event_role"],
            "route_id": ROUTES[source_id],
            "exact_product_id": source["exact_product_id"],
            "acquisition_start_utc": source["acquisition_start_utc"],
            "acquisition_end_utc": source["acquisition_end_utc"],
            "orbit_direction": source["orbit_or_tile"]["orbit_direction"],
            "relative_orbit_number": source["orbit_or_tile"]["relative_orbit_number"],
            "absolute_orbit_number": int(source["exact_product_id"].split("_")[6]),
            "operational_mode": source["orbit_or_tile"]["operational_mode"],
            "polarizations": ["VV", "VH"],
            "materialization_provenance": "retained_unintended_test_execution" if source_id == "M1-SRC-001" else "approved_append_only_materialization",
            "materialization_receipt_ref": receipt_ref,
            "materialization_receipt_sha256": sha256(receipt_ref),
            "external_manifest_sha256": receipt["bindings"]["external_manifest_sha256"],
        })
    inputs = input_bindings({
        "materialization_contract": "contracts/m2-materialization.json",
        "radar_processing_contract": "config/qa/radar-baseline-processing-contract.json",
        "pixel_readiness_contract": "config/qa/pixel-readiness-contract.json",
        "source_manifest": "records/source-manifest.json",
        "approval": APPROVAL_REF,
        "materialization_reconciliation": MATERIALIZATION_RECONCILIATION_REF,
        "prior_amended_contract": "config/qa/radar-input-readiness-contract-amendment-001.json",
        "prior_real_001": "records/readiness/radar-input/m2-s1-input-readiness-real-001.json",
        "prior_real_002": "records/readiness/radar-input/m2-s1-input-readiness-real-002.json",
        "official_label_source_gate": "records/source-gates/m2-radar-input-label-specification-source-gate.json",
        "core": "scripts/radar_input_readiness_core_full_cohort_001.py",
        "runner": "scripts/inspect_radar_inputs_arcgis_full_cohort_001.py",
        "arcgis_adapter": "scripts/validate_radar_input_readiness_arcgis_full_cohort_001.py",
    })
    contract = {
        "contract_version": "2.0",
        "contract_id": "NEPAL-S1-MATERIALIZED-INPUT-READINESS-003",
        "created_at_utc": created_at_utc,
        "status": "active_full_cohort_001_exact_six_sources",
        "inputs": inputs,
        "authority": {
            "mode": "inherited",
            "authority_ref": APPROVAL_REF,
            "required_action_classes": ["read_only_inspection", "routine_qa", "metadata_capture", "evidence_recording"],
            "this_contract_creates_authority": False,
            "network_access_authorized": False,
            "measurement_pixel_decoding_authorized": False,
            "baseline_processing_authorized_by_this_contract": False,
        },
        "sources": sources,
        "analysis_crs": {"wkid": 32645, "name": "WGS 1984 UTM Zone 45N", "note": "Raw GRD TIFF headers remain in native product form; analysis projection occurs only in separately gated processing."},
        "execution_boundary": {
            "external_data_root": r"C:\Projects\Active\nepal-2026-before-after-map-data",
            "receipt_root": "records/readiness/radar-input",
            "network_requests": "prohibited",
            "authentication": "prohibited",
            "credential_access": "prohibited",
            "external_data_mutation": "prohibited",
            "pixel_value_decoding": "prohibited_header_and_metadata_reads_only",
            "derived_raster_writes": "prohibited",
            "receipt_replacement": "prohibited",
        },
        "prerequisites": copy.deepcopy(load("config/qa/radar-input-readiness-contract-amendment-001.json")["prerequisites"]),
        "required_members": {"exactly_one_per_role": True, "role_patterns": RADAR_ROLE_PATTERNS},
        "metadata_checks": copy.deepcopy(load("config/qa/radar-input-readiness-contract-amendment-001.json")["metadata_checks"]),
        "header_checks": copy.deepcopy(load("config/qa/radar-input-readiness-contract-amendment-001.json")["header_checks"]),
        "decision_semantics": {
            "per_source_pass": "pass_header_readability_only",
            "any_identity_inventory_metadata_or_header_failure": "block",
            "all_six_pass_status": "pass_full_radar_header_readiness_only",
            "all_six_pass_reconciles_exact_before_after_sources": True,
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
        "history": {
            "real_001_status": "block_preserved",
            "real_002_status": "pass_partial_pre_event_header_readiness_only_preserved",
            "detected_label_correction_preserved": True,
            "superseded_prepublication_contract_ref": "config/qa/radar-input-readiness-contract-full-cohort-001-prepublication-001-superseded.json",
            "superseded_prepublication_contract_sha256": "9d6262f0ad5e6ada88d0067642606d4c7a60981f6b8999929ea30413067d9486",
            "superseded_reason": "the first generated contract bound the real runner before its final publication-gate error handling was added",
            "real_003_maximum_invocations": 1,
        },
        "limitations": [
            "A pass establishes selected-member identity, annotation consistency, embedded state-vector structure, and ArcGIS TIFF header readability for the six exact radar sources only.",
            "It does not decode measurement pixels, establish AOI coverage, apply external orbit data, terrain-correct a raster, evaluate layover or shadow, establish registration, or release a baseline.",
            "Real-001 remains BLOCK and real-002 remains a post-observation three-source confirmation; neither is reclassified.",
            "M1-SRC-001 retains unintended-test materialization provenance.",
        ],
    }
    errors = validate_radar(contract)
    if errors:
        raise ValueError("; ".join(errors))
    return contract


def build_optical(created_at_utc: str) -> dict[str, Any]:
    old = load("config/qa/optical-input-readiness-contract.json")
    contract = copy.deepcopy(old)
    contract["contract_version"] = "2.0"
    contract["contract_id"] = "NEPAL-S2-MATERIALIZED-INPUT-READINESS-002"
    contract["created_at_utc"] = created_at_utc
    contract["status"] = "active_full_cohort_001_exact_materialized_pair"
    contract["inputs"] = input_bindings({
        "materialization_contract": "contracts/m2-materialization.json",
        "optical_processing_contract": "config/qa/optical-baseline-processing-contract.json",
        "pixel_readiness_contract": "config/qa/pixel-readiness-contract.json",
        "source_manifest": "records/source-manifest.json",
        "approval": APPROVAL_REF,
        "materialization_reconciliation": MATERIALIZATION_RECONCILIATION_REF,
        "prior_contract": "config/qa/optical-input-readiness-contract.json",
        "core": "scripts/optical_input_readiness_core_full_cohort_001.py",
        "runner": "scripts/inspect_optical_inputs_arcgis_full_cohort_001.py",
        "arcgis_adapter": "scripts/validate_optical_input_readiness_arcgis_full_cohort_001.py",
    })
    contract["authority"] = {
        "mode": "inherited",
        "authority_ref": APPROVAL_REF,
        "required_action_classes": ["read_only_inspection", "routine_qa", "metadata_capture", "evidence_recording"],
        "this_contract_creates_authority": False,
        "network_access_authorized": False,
        "measurement_pixel_decoding_authorized": False,
    }
    contract["required_members"]["role_patterns"] = OPTICAL_ROLE_PATTERNS
    contract["materializations"] = {
        role: {
            "source_id": contract["route"][f"{role}_source_id"],
            "receipt_ref": ref,
            "receipt_sha256": sha256(ref),
            "external_manifest_sha256": load(ref)["bindings"]["external_manifest_sha256"],
        }
        for role, ref in OPTICAL_RECEIPTS.items()
    }
    contract["history"] = {
        "prior_contract_preserved": True,
        "superseded_prepublication_contract_ref": "config/qa/optical-input-readiness-contract-full-cohort-001-prepublication-001-superseded.json",
        "superseded_prepublication_contract_sha256": "54a04bf3d419767659e8006c7cd3888e5a8a774a832ad86d7689a474c6cd7cfc",
        "superseded_reason": "the first generated contract bound the real runner before its final publication-gate error handling was added",
        "real_001_maximum_invocations": 1,
    }
    contract["limitations"].append("This version binds the two exact passing materialization receipts and the eight-source materialization reconciliation; it weakens no prior check.")
    errors = validate_optical(contract)
    if errors:
        raise ValueError("; ".join(errors))
    return contract


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--created-at-utc", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    values = {RADAR_OUTPUT: build_radar(args.created_at_utc), OPTICAL_OUTPUT: build_optical(args.created_at_utc)}
    hashes = {}
    for ref, value in values.items():
        payload = canonical(value)
        hashes[ref] = hashlib.sha256(payload).hexdigest()
        if args.write:
            path = ROOT / ref
            with path.open("xb") as stream:
                stream.write(payload)
    print(json.dumps({"status": "pass_contract_build", "written": bool(args.write), "hashes": hashes, "real_data_read": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
