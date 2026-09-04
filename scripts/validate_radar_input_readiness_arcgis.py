#!/usr/bin/env python3
"""Validate the Sentinel-1 input-readiness rules with synthetic ArcGIS TIFFs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime as DateTime, timedelta as TimeDelta, timezone as Timezone
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np

from inspect_radar_inputs_arcgis import describe_raster
from m2_materialization_core import write_new_json
from radar_input_readiness_core import (
    ROLE_PATTERNS,
    decide_source_readiness,
    parse_s1_annotation,
    select_required_members,
    summarize_partial_readiness,
    validate_contract,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REF = "config/qa/radar-input-readiness-contract.json"
UTC_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


def load_json(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def digest(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def repository_child(value: str, parent: str) -> tuple[str, Path]:
    posix = PurePosixPath(value)
    expected = PurePosixPath(parent)
    if posix.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/")):
        raise SystemExit("unsafe repository path")
    if expected not in posix.parents:
        raise SystemExit(f"path must be beneath {parent}")
    return value, ROOT.joinpath(*posix.parts)


def annotation_xml(expected: dict[str, Any], polarization: str, width: int, height: int) -> bytes:
    direction = expected["orbit_direction"].title()
    acquisition_start = DateTime.fromisoformat(expected["acquisition_start_utc"].replace("Z", "+00:00")).astimezone(Timezone.utc)
    acquisition_end = DateTime.fromisoformat(expected["acquisition_end_utc"].replace("Z", "+00:00")).astimezone(Timezone.utc)
    orbit_start = (acquisition_start - TimeDelta(minutes=1)).isoformat().replace("+00:00", "Z")
    orbit_end = (acquisition_end + TimeDelta(minutes=1)).isoformat().replace("+00:00", "Z")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<product>
  <adsHeader>
    <missionId>S1D</missionId><productType>GRD</productType><polarisation>{polarization}</polarisation>
    <mode>IW</mode><swath>IW</swath><startTime>{expected['acquisition_start_utc']}</startTime>
    <stopTime>{expected['acquisition_end_utc']}</stopTime><absoluteOrbitNumber>{expected['absolute_orbit_number']}</absoluteOrbitNumber>
  </adsHeader>
  <generalAnnotation>
    <productInformation><pass>{direction}</pass></productInformation>
    <orbitList count="2">
      <orbit><time>{orbit_start}</time><frame>Earth Fixed</frame><position><x>1</x><y>2</y><z>3</z></position><velocity><x>4</x><y>5</y><z>6</z></velocity></orbit>
      <orbit><time>{orbit_end}</time><frame>Earth Fixed</frame><position><x>2</x><y>3</y><z>4</z></position><velocity><x>5</x><y>6</y><z>7</z></velocity></orbit>
    </orbitList>
  </generalAnnotation>
  <imageAnnotation><imageInformation><numberOfSamples>{width}</numberOfSamples><numberOfLines>{height}</numberOfLines>
    <pixelValue>AMPLITUDE</pixelValue><outputPixels>16 bit Unsigned Integer</outputPixels>
    <rangePixelSpacing>10.0</rangePixelSpacing><azimuthPixelSpacing>10.0</azimuthPixelSpacing>
  </imageInformation></imageAnnotation>
</product>
""".encode("utf-8")


def synthetic_manifest() -> dict[str, Any]:
    files = []
    for index, (role, pattern) in enumerate(ROLE_PATTERNS.items(), start=1):
        relative = {
            "manifest_safe": "manifest.safe",
            "annotation_vv": "annotation/s1d-iw-grd-vv-test.xml",
            "annotation_vh": "annotation/s1d-iw-grd-vh-test.xml",
            "calibration_vv": "annotation/calibration/calibration-s1d-iw-grd-vv-test.xml",
            "calibration_vh": "annotation/calibration/calibration-s1d-iw-grd-vh-test.xml",
            "noise_vv": "annotation/calibration/noise-s1d-iw-grd-vv-test.xml",
            "noise_vh": "annotation/calibration/noise-s1d-iw-grd-vh-test.xml",
            "measurement_vv": "measurement/s1d-iw-grd-vv-test.tiff",
            "measurement_vh": "measurement/s1d-iw-grd-vh-test.tiff",
        }[role]
        if not PurePosixPath(relative.casefold()).match(pattern.casefold()):
            raise AssertionError(f"synthetic member does not match {role}")
        files.append({"relative_path": relative, "size_bytes": index, "sha256": f"{index:064x}"})
    return {"status": "complete", "files": files}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--receipt-output", required=True)
    parser.add_argument("--verified-at-utc", required=True)
    args = parser.parse_args()
    if not UTC_TIMESTAMP.fullmatch(args.verified_at_utc):
        raise SystemExit("invalid verification timestamp")
    output_ref, output_root = repository_child(args.output_root, "scratch")
    receipt_ref, receipt_path = repository_child(args.receipt_output, "records/surface-receipts")
    if output_root.exists() or receipt_path.exists():
        raise SystemExit("synthetic output or receipt collision")
    output_root.mkdir(parents=True, exist_ok=False)
    contract = load_json(CONTRACT_REF)
    errors = validate_contract(contract)
    if errors:
        raise SystemExit("invalid contract: " + "; ".join(errors))

    import arcpy  # type: ignore[import-not-found]

    install = arcpy.GetInstallInfo()
    manifest = synthetic_manifest()
    inventory_result = select_required_members(manifest, contract)
    source_decisions: dict[str, Any] = {}
    header_examples: dict[str, Any] = {}
    for index, expected in enumerate(contract["sources"], start=1):
        source_root = output_root / expected["source_id"].casefold()
        source_root.mkdir()
        width, height = 11 + index, 7 + index
        descriptions = {}
        annotations = {}
        for polarization in ("VV", "VH"):
            key = polarization.casefold()
            raster_path = source_root / f"synthetic-{key}.tif"
            array = np.full((height, width), 100 + index, dtype=np.uint16)
            arcpy.NumPyArrayToRaster(array).save(str(raster_path))
            descriptions[key] = describe_raster(arcpy, raster_path)
            annotations[key] = parse_s1_annotation(annotation_xml(expected, polarization, width, height))
        decision = decide_source_readiness(
            inventory_result["status"], annotations, descriptions, expected, contract
        )
        source_decisions[expected["source_id"]] = decision
        header_examples[expected["source_id"]] = {
            "annotations": annotations,
            "raster_headers": descriptions,
        }
    aggregate = summarize_partial_readiness(source_decisions)
    mismatch_headers = json.loads(json.dumps(header_examples["M1-SRC-001"]["raster_headers"]))
    mismatch_headers["vh"]["width"] += 1
    mismatch = decide_source_readiness(
        inventory_result["status"],
        header_examples["M1-SRC-001"]["annotations"],
        mismatch_headers,
        contract["sources"][0],
        contract,
    )
    status = "pass_synthetic_arcgis_real_input_deferred" if (
        aggregate["status"] == "pass_partial_pre_event_header_readiness_only"
        and mismatch["status"] == "block"
    ) else "fail"
    receipt = {
        "receipt_version": "1.0",
        "receipt_id": "NEPAL-S1-MATERIALIZED-INPUT-READINESS-SYNTHETIC-001",
        "verified_at_utc": args.verified_at_utc,
        "status": status,
        "bindings": {
            "contract_ref": CONTRACT_REF,
            "contract_sha256": digest(CONTRACT_REF),
            "core_ref": "scripts/radar_input_readiness_core.py",
            "core_sha256": digest("scripts/radar_input_readiness_core.py"),
            "runner_ref": "scripts/inspect_radar_inputs_arcgis.py",
            "runner_sha256": digest("scripts/inspect_radar_inputs_arcgis.py"),
            "adapter_ref": "scripts/validate_radar_input_readiness_arcgis.py",
            "adapter_sha256": digest("scripts/validate_radar_input_readiness_arcgis.py"),
        },
        "runtime": {
            "product": install.get("ProductName", "ArcGISPro"),
            "version": install.get("Version"),
            "license_level": install.get("LicenseLevel", arcpy.ProductInfo()),
        },
        "validation": {
            "synthetic_source_count": 3,
            "synthetic_measurement_raster_count": 6,
            "required_member_role_count": len(ROLE_PATTERNS),
            "aligned_source_decisions": source_decisions,
            "aggregate_decision": aggregate,
            "intentional_cross_polarization_width_mismatch": mismatch,
            "header_examples": header_examples,
        },
        "activity": {
            "external_custody_accessed": False,
            "real_materialization_receipt_used": False,
            "real_product_metadata_read": False,
            "real_product_raster_header_opened": False,
            "synthetic_pixel_values_created": True,
            "real_product_pixel_values_examined": False,
            "network_requests_performed": False,
            "authentication_performed": False,
        },
        "limitations": contract["limitations"],
        "next_action": "Publish the immutable gate before any real Sentinel-1 SAFE metadata or measurement header inspection.",
    }
    write_new_json(receipt_path, receipt)
    print(json.dumps({"status": status, "receipt": receipt_ref, "output_root": output_ref}, indent=2))
    return 0 if status.startswith("pass_") else 20


if __name__ == "__main__":
    raise SystemExit(main())
