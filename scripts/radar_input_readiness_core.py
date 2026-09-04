#!/usr/bin/env python3
"""Portable decisions for read-only Sentinel-1 SAFE input readiness."""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any


ROLE_PATTERNS = {
    "manifest_safe": "manifest.safe",
    "annotation_vv": "annotation/*-vv-*.xml",
    "annotation_vh": "annotation/*-vh-*.xml",
    "calibration_vv": "annotation/calibration/calibration-*-vv-*.xml",
    "calibration_vh": "annotation/calibration/calibration-*-vh-*.xml",
    "noise_vv": "annotation/calibration/noise-*-vv-*.xml",
    "noise_vh": "annotation/calibration/noise-*-vh-*.xml",
    "measurement_vv": "measurement/*-vv-*.tiff",
    "measurement_vh": "measurement/*-vh-*.tiff",
}
POLARIZATIONS = ("VV", "VH")
RASTER_ROLES = {"measurement_vv", "measurement_vh"}
HEX64 = re.compile(r"[0-9a-f]{64}")


def validate_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if contract.get("contract_id") != "NEPAL-S1-MATERIALIZED-INPUT-READINESS-001":
        errors.append("contract identity differs")
    if contract.get("status") != "predeclared_active_exact_three_pre_event_sources":
        errors.append("contract status differs")
    if contract.get("analysis_crs", {}).get("wkid") != 32645:
        errors.append("analysis CRS differs")
    if contract.get("required_members", {}).get("role_patterns") != ROLE_PATTERNS:
        errors.append("required Sentinel-1 member patterns differ")
    sources = contract.get("sources")
    if not isinstance(sources, list) or [item.get("source_id") for item in sources] != [
        "M1-SRC-001", "M1-SRC-002", "M1-SRC-003"
    ]:
        errors.append("exact materialized source order differs")
    else:
        expected_products = [
            "S1D_IW_GRDH_1SDV_20260816T122116_20260816T122141_004151_007980_B057.SAFE",
            "S1D_IW_GRDH_1SDV_20260816T122141_20260816T122206_004151_007980_C3AB.SAFE",
            "S1D_IW_GRDH_1SDV_20260819T001036_20260819T001101_004187_007ABD_DC16.SAFE",
        ]
        if [item.get("exact_product_id") for item in sources] != expected_products:
            errors.append("exact materialized product boundary differs")
        if [item.get("event_role") for item in sources] != ["before", "before", "before"]:
            errors.append("pre-event source role differs")
    boundary = contract.get("execution_boundary", {})
    if boundary.get("network_requests") != "prohibited" or boundary.get("authentication") != "prohibited":
        errors.append("input readiness must remain offline and unauthenticated")
    if boundary.get("external_data_mutation") != "prohibited":
        errors.append("input readiness must remain read-only")
    if boundary.get("pixel_value_decoding") != "prohibited_header_and_metadata_reads_only":
        errors.append("pixel decoding boundary differs")
    decision = contract.get("decision_semantics", {})
    if decision.get("all_three_pass_status") != "pass_partial_pre_event_header_readiness_only":
        errors.append("partial readiness decision differs")
    if decision.get("pass_releases_baseline_processing") is not False:
        errors.append("input readiness must not release baseline processing")
    claim = contract.get("claim_boundary", {})
    if any(claim.get(key) is not False for key in (
        "pixel_values_examined",
        "pixel_usability_established",
        "complete_pair_established",
        "baseline_established",
        "change_established",
        "scientific_admission_authorized",
    )):
        errors.append("contract invents downstream evidence")
    return errors


def select_required_members(external_manifest: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if external_manifest.get("status") != "complete":
        errors.append("external materialization manifest is not complete")
    files = external_manifest.get("files")
    if not isinstance(files, list):
        return {"status": "block", "members": {}, "errors": ["external manifest files are missing"]}
    indexed: dict[str, dict[str, Any]] = {}
    for item in files:
        relative = item.get("relative_path") if isinstance(item, dict) else None
        if not isinstance(relative, str):
            errors.append("external manifest contains a missing relative path")
            continue
        posix = PurePosixPath(relative)
        if posix.is_absolute() or any(part in {"", ".", ".."} for part in relative.split("/")):
            errors.append(f"external manifest contains an unsafe path: {relative}")
            continue
        folded = relative.casefold()
        if folded in indexed:
            errors.append(f"external manifest contains a case-insensitive duplicate: {relative}")
            continue
        if not isinstance(item.get("size_bytes"), int) or item["size_bytes"] <= 0:
            errors.append(f"external manifest member is empty or has invalid size: {relative}")
        if not isinstance(item.get("sha256"), str) or not HEX64.fullmatch(item["sha256"]):
            errors.append(f"external manifest member lacks SHA-256: {relative}")
        indexed[folded] = item
    selected: dict[str, dict[str, Any]] = {}
    for role, pattern in contract["required_members"]["role_patterns"].items():
        matches = [item for folded, item in indexed.items() if PurePosixPath(folded).match(pattern.casefold())]
        if len(matches) != 1:
            errors.append(f"{role} requires exactly one member; observed {len(matches)}")
        else:
            selected[role] = matches[0]
    return {"status": "pass_inventory_only" if not errors else "block", "members": selected, "errors": errors}


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _first_descendant(root: ET.Element, name: str) -> ET.Element | None:
    return next((node for node in root.iter() if _local_name(node.tag) == name), None)


def _direct_text(root: ET.Element | None, name: str) -> str | None:
    if root is None:
        return None
    for child in list(root):
        if _local_name(child.tag) == name:
            value = (child.text or "").strip()
            return value or None
    return None


def _number(value: str | None, *, integer: bool = False) -> int | float | None:
    try:
        return int(value) if integer else float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _timestamp(value: str | None) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_s1_annotation(payload: bytes) -> dict[str, Any]:
    errors: list[str] = []
    upper = payload.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        return {"errors": ["annotation XML contains a prohibited DTD or entity declaration"]}
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        return {"errors": [f"annotation XML parse failed: {exc}"]}
    ads = _first_descendant(root, "adsHeader")
    info = _first_descendant(root, "imageInformation")
    product = _first_descendant(root, "productInformation")
    orbit_list = _first_descendant(root, "orbitList")
    if ads is None:
        errors.append("adsHeader is missing")
    if info is None:
        errors.append("imageInformation is missing")
    if product is None:
        errors.append("productInformation is missing")
    if orbit_list is None:
        errors.append("orbitList is missing")
    orbit_nodes = [] if orbit_list is None else [node for node in list(orbit_list) if _local_name(node.tag) == "orbit"]
    declared_orbit_count = _number(None if orbit_list is None else orbit_list.attrib.get("count"), integer=True)
    orbit_times: list[datetime] = []
    orbit_values_finite = True
    for orbit in orbit_nodes:
        time_value = _timestamp(_direct_text(orbit, "time"))
        if time_value is None:
            orbit_values_finite = False
        else:
            orbit_times.append(time_value)
        for group_name in ("position", "velocity"):
            group = next((node for node in list(orbit) if _local_name(node.tag) == group_name), None)
            values = [_number(_direct_text(group, axis)) for axis in ("x", "y", "z")]
            if group is None or any(value is None or not math.isfinite(float(value)) for value in values):
                orbit_values_finite = False
    orbit_times_increasing = len(orbit_times) == len(orbit_nodes) and all(
        left < right for left, right in zip(orbit_times, orbit_times[1:])
    )
    result = {
        "mission_id": _direct_text(ads, "missionId"),
        "product_type": _direct_text(ads, "productType"),
        "polarization": _direct_text(ads, "polarisation"),
        "mode": _direct_text(ads, "mode"),
        "swath": _direct_text(ads, "swath"),
        "start_time": _direct_text(ads, "startTime"),
        "stop_time": _direct_text(ads, "stopTime"),
        "absolute_orbit_number": _number(_direct_text(ads, "absoluteOrbitNumber"), integer=True),
        "orbit_direction": _direct_text(product, "pass"),
        "number_of_samples": _number(_direct_text(info, "numberOfSamples"), integer=True),
        "number_of_lines": _number(_direct_text(info, "numberOfLines"), integer=True),
        "pixel_value": _direct_text(info, "pixelValue"),
        "output_pixels": _direct_text(info, "outputPixels"),
        "range_pixel_spacing": _number(_direct_text(info, "rangePixelSpacing")),
        "azimuth_pixel_spacing": _number(_direct_text(info, "azimuthPixelSpacing")),
        "orbit_vector_count_declared": declared_orbit_count,
        "orbit_vector_count_observed": len(orbit_nodes),
        "orbit_time_start": None if not orbit_times else orbit_times[0].isoformat().replace("+00:00", "Z"),
        "orbit_time_end": None if not orbit_times else orbit_times[-1].isoformat().replace("+00:00", "Z"),
        "orbit_times_strictly_increasing": orbit_times_increasing,
        "orbit_vectors_finite": orbit_values_finite,
        "errors": errors,
    }
    return result


def validate_annotation(
    parsed: dict[str, Any],
    expected: dict[str, Any],
    polarization: str,
    contract: dict[str, Any],
) -> list[str]:
    errors = list(parsed.get("errors", []))
    expected_fields = {
        "mission_id": "S1D",
        "product_type": "GRD",
        "polarization": polarization,
        "mode": "IW",
        "swath": "IW",
        "absolute_orbit_number": expected["absolute_orbit_number"],
    }
    for key, value in expected_fields.items():
        observed = parsed.get(key)
        if isinstance(observed, str) and isinstance(value, str):
            matches = observed.casefold() == value.casefold()
        else:
            matches = observed == value
        if not matches:
            errors.append(f"{polarization} annotation {key} differs")
    direction = parsed.get("orbit_direction")
    if not isinstance(direction, str) or direction.upper() != expected["orbit_direction"]:
        errors.append(f"{polarization} annotation orbit direction differs")
    tolerance = float(contract["metadata_checks"]["acquisition_time_tolerance_seconds"])
    for key, expected_key in (("start_time", "acquisition_start_utc"), ("stop_time", "acquisition_end_utc")):
        observed_time = _timestamp(parsed.get(key))
        expected_time = _timestamp(expected.get(expected_key))
        if observed_time is None or expected_time is None or abs((observed_time - expected_time).total_seconds()) > tolerance:
            errors.append(f"{polarization} annotation {key} differs from the approved source time")
    for key in ("number_of_samples", "number_of_lines"):
        value = parsed.get(key)
        if not isinstance(value, int) or value <= 0:
            errors.append(f"{polarization} annotation {key} is invalid")
    for key in ("range_pixel_spacing", "azimuth_pixel_spacing"):
        value = parsed.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)) or value <= 0:
            errors.append(f"{polarization} annotation {key} is invalid")
    if str(parsed.get("pixel_value", "")).upper() != "AMPLITUDE":
        errors.append(f"{polarization} annotation pixel value is not AMPLITUDE")
    output_pixels = str(parsed.get("output_pixels", "")).casefold()
    if not all(token in output_pixels for token in ("16", "unsigned", "integer")):
        errors.append(f"{polarization} annotation output pixel encoding is not 16-bit unsigned integer")
    declared = parsed.get("orbit_vector_count_declared")
    observed = parsed.get("orbit_vector_count_observed")
    if not isinstance(observed, int) or observed < int(contract["metadata_checks"]["minimum_embedded_orbit_vectors"]):
        errors.append(f"{polarization} embedded orbit vector count is insufficient")
    if declared != observed:
        errors.append(f"{polarization} embedded orbit vector count differs from the declaration")
    if parsed.get("orbit_times_strictly_increasing") is not True:
        errors.append(f"{polarization} embedded orbit times are not strictly increasing")
    orbit_start = _timestamp(parsed.get("orbit_time_start"))
    orbit_end = _timestamp(parsed.get("orbit_time_end"))
    acquisition_start = _timestamp(expected.get("acquisition_start_utc"))
    acquisition_end = _timestamp(expected.get("acquisition_end_utc"))
    if (
        orbit_start is None
        or orbit_end is None
        or acquisition_start is None
        or acquisition_end is None
        or orbit_start > acquisition_start
        or orbit_end < acquisition_end
    ):
        errors.append(f"{polarization} embedded orbit vectors do not bracket the acquisition window")
    if parsed.get("orbit_vectors_finite") is not True:
        errors.append(f"{polarization} embedded orbit vectors are incomplete or nonfinite")
    return errors


def validate_raster_description(
    description: dict[str, Any],
    annotation: dict[str, Any],
    polarization: str,
    contract: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if str(description.get("format", "")).upper() not in {value.upper() for value in contract["header_checks"]["formats"]}:
        errors.append(f"{polarization} measurement format is not TIFF")
    if description.get("band_count") != 1:
        errors.append(f"{polarization} measurement band count differs from one")
    if description.get("pixel_type") not in contract["header_checks"]["pixel_types"]:
        errors.append(f"{polarization} measurement pixel type is not U16")
    if description.get("width") != annotation.get("number_of_samples"):
        errors.append(f"{polarization} raster width differs from annotation samples")
    if description.get("height") != annotation.get("number_of_lines"):
        errors.append(f"{polarization} raster height differs from annotation lines")
    return errors


def decide_source_readiness(
    inventory_status: str,
    annotations: dict[str, dict[str, Any]],
    descriptions: dict[str, dict[str, Any]],
    expected: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    if inventory_status != "pass_inventory_only":
        errors.append("required member inventory did not pass")
    for polarization in POLARIZATIONS:
        key = polarization.casefold()
        if key not in annotations:
            errors.append(f"{polarization} annotation result is missing")
            continue
        errors.extend(validate_annotation(annotations[key], expected, polarization, contract))
        if key not in descriptions:
            errors.append(f"{polarization} ArcGIS raster description is missing")
            continue
        errors.extend(validate_raster_description(descriptions[key], annotations[key], polarization, contract))
    if all(key.casefold() in descriptions for key in POLARIZATIONS):
        vv, vh = descriptions["vv"], descriptions["vh"]
        for field in ("width", "height", "band_count", "pixel_type"):
            if vv.get(field) != vh.get(field):
                errors.append(f"VV and VH raster headers differ at {field}")
    if all(key.casefold() in annotations for key in POLARIZATIONS):
        vv_annotation, vh_annotation = annotations["vv"], annotations["vh"]
        for field in (
            "mission_id", "product_type", "mode", "swath", "start_time", "stop_time",
            "absolute_orbit_number", "orbit_direction", "number_of_samples", "number_of_lines",
            "range_pixel_spacing", "azimuth_pixel_spacing",
        ):
            if vv_annotation.get(field) != vh_annotation.get(field):
                errors.append(f"VV and VH annotations differ at {field}")
    return {
        "status": "pass_header_readability_only" if not errors else "block",
        "errors": errors,
        "pixel_values_examined": False,
        "baseline_processing_released": False,
        "scientific_admission_authorized": False,
    }


def summarize_partial_readiness(source_decisions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    expected = ["M1-SRC-001", "M1-SRC-002", "M1-SRC-003"]
    errors = []
    for source_id in expected:
        decision = source_decisions.get(source_id)
        if not isinstance(decision, dict) or decision.get("status") != "pass_header_readability_only":
            errors.append(f"{source_id} did not pass header readiness")
    return {
        "status": "pass_partial_pre_event_header_readiness_only" if not errors else "block",
        "errors": errors,
        "ready_source_count": 3 - len(errors),
        "complete_before_after_pair": False,
        "baseline_processing_released": False,
        "pixel_usability_established": False,
        "scientific_admission_authorized": False,
    }
