#!/usr/bin/env python3
"""Reconcile the two one-time real header inspections without opening pixels."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "records/readiness/m2-full-header-readiness-reconciliation.json"
REFS = {
    "approval": "records/source-gates/m2-materialization-pixel-readiness-approval.json",
    "publication_gate": "records/readiness/m2-header-stage-publication-gate.json",
    "final_preflight": "records/readiness/m2-header-stage-final-preflight.json",
    "radar": "records/readiness/radar-input/m2-s1-input-readiness-real-003.json",
    "optical": "records/readiness/optical-input/m2-s2-input-readiness-real-001.json",
}


def load(ref: str) -> dict:
    value = json.loads((ROOT / ref).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {ref}")
    return value


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconciled-at-utc", required=True)
    args = parser.parse_args()
    if OUTPUT.exists():
        raise SystemExit("refusing header reconciliation collision")
    values = {key: load(ref) for key, ref in REFS.items()}
    radar = values["radar"]
    optical = values["optical"]
    if values["approval"].get("status") != "approved_exact_dependency_ordered_bounded_actions":
        raise SystemExit("exact approval is not active")
    if values["publication_gate"].get("status") != "pass_public_controls_verified_before_real_header_inspections":
        raise SystemExit("header publication gate is not passing")
    if values["final_preflight"].get("status") != "pass_exact_header_inputs_ready_no_real_header_access":
        raise SystemExit("header final preflight is not passing")
    if (
        radar.get("receipt_id") != "NEPAL-S1-MATERIALIZED-INPUT-READINESS-REAL-003"
        or radar.get("status") != "pass_full_radar_header_readiness_only"
        or radar.get("activity", {}).get("external_materialization_inventory_unchanged") is not True
        or radar.get("activity", {}).get("all_real_measurement_raster_headers_opened_with_arcgis") is not True
        or radar.get("activity", {}).get("real_product_pixel_values_examined") is not False
    ):
        raise SystemExit("radar real-003 receipt is not the exact passing header-only result")
    if set(radar.get("products", {})) != {f"M1-SRC-{value:03d}" for value in range(1, 7)}:
        raise SystemExit("radar real-003 source cohort differs")
    if (
        optical.get("receipt_id") != "NEPAL-S2-MATERIALIZED-INPUT-READINESS-REAL-001"
        or optical.get("status") != "pass_header_readability_only"
        or set(optical.get("products", {})) != {"M1-SRC-010", "M1-SRC-008"}
        or optical.get("activity", {}).get("external_materialization_inventory_unchanged") is not True
        or optical.get("activity", {}).get("all_selected_raster_headers_opened_with_arcgis") is not True
        or optical.get("activity", {}).get("pixel_values_examined") is not False
    ):
        raise SystemExit("optical real-001 receipt is not the exact passing header-only result")
    record = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-FULL-HEADER-READINESS-RECONCILIATION-001",
        "reconciled_at_utc": args.reconciled_at_utc,
        "status": "pass_both_exact_header_routes_only",
        "bindings": {f"{key}_ref": ref for key, ref in REFS.items()} | {f"{key}_sha256": sha256(ref) for key, ref in REFS.items()},
        "results": {
            "radar": {"status": radar["status"], "source_count": 6, "real_invocation_count": 1},
            "optical": {"status": optical["status"], "source_count": 2, "real_invocation_count": 1},
        },
        "assertions": {
            "route_results_preserved_independently": True,
            "external_materializations_unchanged": True,
            "measurement_pixels_decoded": False,
            "pixel_usability_established": False,
            "baseline_established": False,
            "change_established": False,
            "scientific_admission_authorized": False,
        },
        "next_gate": "implement and publish the exact conditional optical pixel-readiness attempt before any real pixel access",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"status": record["status"], "output": OUTPUT.relative_to(ROOT).as_posix()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
