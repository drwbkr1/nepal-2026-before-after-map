#!/usr/bin/env python3
"""Dependency-free Sentinel-2 scaling, mask, and readiness decisions."""

from __future__ import annotations

import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


BAND_ID_TO_NAME = {
    0: "B01",
    1: "B02",
    2: "B03",
    3: "B04",
    4: "B05",
    5: "B06",
    6: "B07",
    7: "B08",
    8: "B8A",
    9: "B09",
    10: "B10",
    11: "B11",
    12: "B12",
}
PRODUCT_BASELINE = re.compile(r"_N(?P<baseline>\d{4})_")
REQUIRED_CHANGE_BANDS = {"B02", "B03", "B04", "B08", "B11", "B12"}


def load_contract(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_contract(value)
    if errors:
        raise ValueError("invalid optical processing contract: " + "; ".join(errors))
    return value


def validate_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if contract.get("contract_id") != "NEPAL-S2-BASELINE-PROCESSING-001":
        errors.append("contract identity differs")
    if contract.get("status") != "predeclared_no_real_processing":
        errors.append("contract must remain predeclared")
    if contract.get("analysis_grid", {}).get("wkid") != 32645:
        errors.append("analysis grid must use EPSG:32645")
    if contract.get("analysis_grid", {}).get("cell_size_m") != 20.0:
        errors.append("analysis grid must use 20 metre cells")
    route = contract.get("route", {})
    if route.get("pair_id") != "PAIR-S2-RUM-R119":
        errors.append("optical pair identity differs")
    if route.get("before_source_id") != "M1-SRC-010" or route.get("after_source_id") != "M1-SRC-008":
        errors.append("optical source boundary differs")
    if route.get("processing_baseline_from_product_name") != "05.12":
        errors.append("processing baseline differs")
    scaling = contract.get("reflectance_scaling", {})
    if scaling.get("formula") != "(DN + BOA_ADD_OFFSET_band) / BOA_QUANTIFICATION_VALUE":
        errors.append("reflectance formula differs")
    if scaling.get("dn_zero_policy") != "NoData_before_offset_or_scaling":
        errors.append("DN zero policy differs")
    if set(contract.get("bands", {}).get("change_core", [])) != REQUIRED_CHANGE_BANDS:
        errors.append("required change-band set differs")
    valid_classes = {int(value) for value in contract.get("mask", {}).get("valid_scl_classes", {})}
    excluded_classes = {int(value) for value in contract.get("mask", {}).get("excluded_scl_classes", {})}
    if valid_classes != {4, 5, 6} or valid_classes & excluded_classes or valid_classes | excluded_classes != set(range(12)):
        errors.append("SCL class partition differs")
    if contract.get("cross_platform", {}).get("unmeasured_harmonization") != "prohibited":
        errors.append("unmeasured S2C to S2B harmonization must be prohibited")
    if contract.get("authority", {}).get("real_pixel_processing_started") is not False:
        errors.append("contract invents real processing")
    if contract.get("claim_boundary", {}).get("scientific_admission_authorized") is not False:
        errors.append("contract creates scientific admission")
    return errors


def processing_baseline_from_product_id(product_id: str) -> str | None:
    matched = PRODUCT_BASELINE.search(product_id)
    if not matched:
        return None
    digits = matched.group("baseline")
    return f"{digits[:2]}.{digits[2:]}"


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_l2a_scaling_metadata(xml_text: str) -> dict[str, Any]:
    root = ET.fromstring(xml_text)
    baseline: str | None = None
    quantification: float | None = None
    quantification_count = 0
    offsets: dict[str, float] = {}
    duplicate_offset_bands: list[str] = []
    special_values: dict[str, int] = {}
    pending_special_name: str | None = None
    for element in root.iter():
        name = _local_name(element.tag)
        text = (element.text or "").strip()
        if not text:
            continue
        if name == "PROCESSING_BASELINE":
            baseline = text
        elif name == "BOA_QUANTIFICATION_VALUE":
            quantification_count += 1
            quantification = float(text)
        elif name == "BOA_ADD_OFFSET":
            band_id_raw = element.attrib.get("band_id")
            if band_id_raw is None or not band_id_raw.isdigit() or int(band_id_raw) not in BAND_ID_TO_NAME:
                raise ValueError("BOA_ADD_OFFSET has an invalid band_id")
            band_name = BAND_ID_TO_NAME[int(band_id_raw)]
            if band_name in offsets:
                duplicate_offset_bands.append(band_name)
            offsets[band_name] = float(text)
        elif name == "SPECIAL_VALUE_TEXT":
            pending_special_name = text.upper()
        elif name == "SPECIAL_VALUE_INDEX" and pending_special_name:
            special_values[pending_special_name] = int(text)
            pending_special_name = None
    errors: list[str] = []
    if baseline is None:
        errors.append("PROCESSING_BASELINE is missing")
    if quantification is None or not math.isfinite(quantification) or quantification <= 0:
        errors.append("positive BOA_QUANTIFICATION_VALUE is missing")
    elif quantification_count != 1:
        errors.append("BOA_QUANTIFICATION_VALUE must occur exactly once")
    missing_offsets = sorted(REQUIRED_CHANGE_BANDS - set(offsets))
    if missing_offsets:
        errors.append("missing BOA_ADD_OFFSET values for " + ", ".join(missing_offsets))
    if duplicate_offset_bands:
        errors.append("duplicate BOA_ADD_OFFSET values for " + ", ".join(sorted(set(duplicate_offset_bands))))
    if special_values.get("NODATA") != 0 and special_values.get("NO_DATA") != 0:
        errors.append("metadata does not identify DN zero as NoData")
    return {
        "processing_baseline": baseline,
        "quantification_value": quantification,
        "offsets_by_band": offsets,
        "special_values": special_values,
        "errors": errors,
    }


def scale_reflectance_dn(dn: int | float, offset: int | float, quantification: int | float) -> float | None:
    if not all(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) for value in (dn, offset, quantification)):
        raise ValueError("DN, offset, and quantification must be finite numbers")
    if dn < 0 or quantification <= 0:
        raise ValueError("DN must be nonnegative and quantification must be positive")
    if dn == 0:
        return None
    return (float(dn) + float(offset)) / float(quantification)


def normalized_difference(first: float | None, second: float | None, epsilon: float) -> float | None:
    if first is None or second is None:
        return None
    if not all(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) for value in (first, second, epsilon)):
        raise ValueError("normalized-difference inputs must be finite numbers")
    if epsilon <= 0:
        raise ValueError("epsilon must be positive")
    denominator = float(first) + float(second)
    if abs(denominator) <= epsilon:
        return None
    return (float(first) - float(second)) / denominator


def classify_scl(value: int, contract: dict[str, Any]) -> dict[str, Any]:
    valid = contract["mask"]["valid_scl_classes"]
    excluded = contract["mask"]["excluded_scl_classes"]
    key = str(value)
    if key in valid:
        return {"status": "valid", "reason": valid[key]}
    if key in excluded:
        return {"status": "excluded", "reason": excluded[key]}
    return {"status": "defer", "reason": f"unknown_scl_class_{value}"}


def evaluate_readiness(contract: dict[str, Any], observed: dict[str, Any]) -> dict[str, Any]:
    expected = {contract["route"]["before_source_id"], contract["route"]["after_source_id"]}
    actual = set(observed.get("verified_source_ids", []))
    reasons: list[str] = []
    status = "ready_for_controlled_processing"
    if actual - expected:
        status = "invalid"
        reasons.append("observed source identity is outside the exact optical pair")
    elif actual != expected:
        status = "defer"
        reasons.append("both exact optical products are not verified")
    metadata = observed.get("metadata_by_source", {})
    if status != "invalid" and set(metadata) != expected:
        status = "defer"
        reasons.append("internal product metadata is incomplete")
    elif status != "invalid":
        for source_id, item in metadata.items():
            if item.get("processing_baseline") != "05.12":
                status = "block"
                reasons.append(f"{source_id} internal processing baseline does not match 05.12")
            if item.get("source_crs_wkid") != 32645:
                status = "block"
                reasons.append(f"{source_id} source grid is not EPSG:32645")
            if not REQUIRED_CHANGE_BANDS.issubset(set(item.get("offset_bands", []))):
                status = "block"
                reasons.append(f"{source_id} is missing required BOA_ADD_OFFSET values")
            if not isinstance(item.get("quantification_value"), (int, float)) or item.get("quantification_value", 0) <= 0:
                status = "block"
                reasons.append(f"{source_id} has an invalid BOA quantification value")
    if status not in {"invalid", "block"} and observed.get("pixel_readiness_status") != "pass_qa_only":
        status = "defer"
        reasons.append("optical pixel-readiness QA has not passed")
    if status not in {"invalid", "block"} and observed.get("registration_status") != "pass_qa_only":
        status = "defer"
        reasons.append("before/after registration has not passed")
    return {
        "status": status,
        "reasons": reasons,
        "scientific_admission_authorized": False,
        "change_established": False,
    }
