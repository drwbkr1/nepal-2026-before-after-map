#!/usr/bin/env python3
"""Portable decision logic for predeclared optical and radar change evidence."""

from __future__ import annotations

from math import isfinite
from statistics import median
from typing import Any, Iterable


EXPECTED_ROUTES = {
    "PAIR-S1-ASC-R085-IW": ("radar", "RADAR-ROBUST-DELTA-DB-001"),
    "PAIR-S1-DESC-R121-IW": ("radar", "RADAR-ROBUST-DELTA-DB-001"),
    "PAIR-S2-RUM-R119": ("optical", "OPTICAL-ROBUST-INDEX-DELTA-001"),
}
ROUTE_STATUSES = {"invalid", "block", "defer", "pass_no_candidate_observed", "pass_candidate_only"}


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(float(value))


def robust_location_scale(values: Iterable[float], consistency_factor: float = 1.4826) -> tuple[float, float]:
    sample = [float(value) for value in values]
    if not sample or any(not isfinite(value) for value in sample):
        raise ValueError("stable reference values must be finite and nonempty")
    location = float(median(sample))
    mad = float(median(abs(value - location) for value in sample))
    return location, mad * float(consistency_factor)


def _positive_candidate(signal: float, controls: Iterable[float], minimum_delta: float, minimum_z: float, factor: float) -> tuple[bool, float, float, float]:
    location, scale = robust_location_scale(controls, factor)
    if not isfinite(scale) or scale <= 0:
        raise ValueError("stable reference scale is zero or nonfinite")
    anomaly = float(signal) - location
    robust_z = anomaly / scale
    return anomaly >= minimum_delta and robust_z >= minimum_z, anomaly, robust_z, scale


def classify_optical_sample(signals: dict[str, float], controls: dict[str, list[float]], contract: dict[str, Any]) -> dict[str, Any]:
    profile = contract["threshold_profiles"]["OPTICAL-ROBUST-INDEX-DELTA-001"]
    factor = float(contract["stable_reference"]["mad_consistency_factor"])
    classes: list[str] = []
    metrics: dict[str, dict[str, Any]] = {}
    try:
        for metric, rule in profile["metrics"].items():
            if metric not in signals or metric not in controls or not _finite_number(signals[metric]):
                return {"status": "invalid", "classes": [], "metrics": {}, "reason": f"missing or invalid metric: {metric}"}
            candidate, anomaly, robust_z, scale = _positive_candidate(
                float(signals[metric]), controls[metric], float(rule["minimum_delta"]),
                float(rule["minimum_robust_z"]), factor,
            )
            metrics[metric] = {"anomaly_from_control_median": anomaly, "robust_z": robust_z, "stable_scale": scale, "candidate": candidate}
            if candidate:
                classes.append(rule["class"])
    except ValueError as exc:
        return {"status": "defer", "classes": [], "metrics": metrics, "reason": str(exc)}
    return {"status": "candidate" if classes else "no_candidate", "classes": classes, "metrics": metrics, "reason": None}


def classify_radar_sample(signals: dict[str, float], controls: dict[str, list[float]], contract: dict[str, Any]) -> dict[str, Any]:
    profile = contract["threshold_profiles"]["RADAR-ROBUST-DELTA-DB-001"]
    factor = float(contract["stable_reference"]["mad_consistency_factor"])
    results: dict[str, dict[str, Any]] = {}
    directions: list[str] = []
    try:
        for polarization in profile["polarizations"]:
            if polarization not in signals or polarization not in controls or not _finite_number(signals[polarization]):
                return {"status": "invalid", "classes": [], "polarizations": {}, "reason": f"missing or invalid polarization: {polarization}"}
            location, scale = robust_location_scale(controls[polarization], factor)
            if not isfinite(scale) or scale <= 0:
                raise ValueError("stable reference scale is zero or nonfinite")
            anomaly = float(signals[polarization]) - location
            robust_z = anomaly / scale
            candidate = abs(anomaly) >= float(profile["minimum_absolute_delta_db"]) and abs(robust_z) >= float(profile["minimum_absolute_robust_z"])
            direction = "positive" if anomaly > 0 else "negative"
            results[polarization] = {"anomaly_from_control_median_db": anomaly, "robust_z": robust_z, "stable_scale_db": scale, "candidate": candidate, "direction": direction if candidate else None}
            if candidate:
                directions.append(direction)
    except ValueError as exc:
        return {"status": "defer", "classes": [], "polarizations": results, "reason": str(exc)}
    classes = sorted({profile["classes"][direction] for direction in directions})
    agreement = "same_direction" if len(directions) == 2 and len(set(directions)) == 1 else ("opposite_direction" if len(set(directions)) == 2 else "single_or_none")
    return {"status": "candidate" if classes else "no_candidate", "classes": classes, "polarizations": results, "polarization_agreement": agreement, "reason": None}


def validate_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "contract_version", "contract_id", "status", "prepared_at_utc", "analysis_crs", "bindings",
        "routes", "stable_reference", "input_qa", "threshold_profiles", "object_formation",
        "cross_route_synthesis", "required_outputs_per_route", "decision_semantics", "authority", "claim_boundary",
    }
    if set(contract) != required:
        return ["contract fields differ"]
    if contract["contract_version"] != "1.0" or contract["contract_id"] != "NEPAL-M4-CHANGE-EVIDENCE-001":
        errors.append("contract identity differs")
    if contract["status"] != "predeclared_no_real_change_processing":
        errors.append("contract status differs")
    if contract["analysis_crs"].get("wkid") != 32645 or contract["analysis_crs"].get("linear_unit") != "Meter":
        errors.append("analysis CRS differs")
    routes = contract["routes"]
    observed_routes = {item.get("route_id"): (item.get("route_kind"), item.get("threshold_profile")) for item in routes if isinstance(item, dict)}
    if observed_routes != EXPECTED_ROUTES or len(routes) != len(EXPECTED_ROUTES):
        errors.append("route identities or profiles differ")
    stable = contract["stable_reference"]
    if (
        stable.get("selection_must_be_locked_before_change_metrics") is not True
        or stable.get("event_corridor_excluded") is not True
        or stable.get("minimum_control_zones") != 30
        or stable.get("minimum_valid_pixels_per_route") != 10000
        or stable.get("location_estimator") != "median"
        or stable.get("scale_estimator") != "MAD"
        or stable.get("mad_consistency_factor") != 1.4826
        or stable.get("date_shopping_authorized") is not False
        or stable.get("post_observation_control_reselection_authorized") is not False
    ):
        errors.append("stable-reference controls differ")
    qa = contract["input_qa"]
    if qa.get("required_status") != "pass_qa_only" or qa.get("minimum_coverage_fraction") != 0.99 or qa.get("minimum_usable_fraction") != 0.8 or qa.get("maximum_registration_rmse_pixels") != 0.5 or qa.get("maximum_absolute_registration_bias_pixels") != 0.5:
        errors.append("input QA thresholds differ")
    radar = contract["threshold_profiles"].get("RADAR-ROBUST-DELTA-DB-001", {})
    if radar.get("minimum_absolute_delta_db") != 1.5 or radar.get("minimum_absolute_robust_z") != 3.5 or radar.get("two_sided") is not True:
        errors.append("radar thresholds differ")
    optical = contract["threshold_profiles"].get("OPTICAL-ROBUST-INDEX-DELTA-001", {})
    expected_optical = {
        "dndvi_pre_minus_post": (0.2, 3.5),
        "dnbr_pre_minus_post": (0.15, 3.5),
        "dmndwi_post_minus_pre": (0.2, 3.5),
    }
    observed_optical = {name: (rule.get("minimum_delta"), rule.get("minimum_robust_z")) for name, rule in optical.get("metrics", {}).items()}
    if observed_optical != expected_optical or optical.get("class_names_are_observations_not_interpretations") is not True:
        errors.append("optical thresholds or semantics differ")
    objects = contract["object_formation"]
    if objects.get("connectivity") != 8 or objects.get("minimum_mapping_unit_m2") != 5000.0 or objects.get("candidate_raster_area_consistency_tolerance_fraction") != 0.01 or objects.get("threshold_tuning_after_observation_authorized") is not False or objects.get("manual_rescue_of_subthreshold_objects_authorized") is not False:
        errors.append("object-formation controls differ")
    synthesis = contract["cross_route_synthesis"]
    if synthesis.get("require_all_route_dispositions") is not True or synthesis.get("minimum_overlap_fraction_of_smaller_polygon") != 0.25 or synthesis.get("missing_or_masked_route_is_not_disagreement") is not True or synthesis.get("agreement_does_not_establish_attribution") is not True:
        errors.append("cross-route synthesis controls differ")
    semantics = contract["decision_semantics"]
    if semantics.get("route_precedence") != ["invalid", "block", "defer", "pass_no_candidate_observed", "pass_candidate_only"] or semantics.get("candidate_is_not_interpretation") is not True or semantics.get("candidate_is_not_attribution") is not True or semantics.get("failed_and_inconclusive_routes_must_remain_visible") is not True:
        errors.append("decision semantics differ")
    if any(contract["authority"].get(key) is not False for key in contract["authority"]):
        errors.append("contract creates or broadens authority")
    return errors


def evaluate_route_report(report: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    errors = validate_contract(contract)
    expected_fields = {
        "route_id", "route_kind", "threshold_profile", "input_qa_status", "stable_control_zone_count",
        "stable_valid_pixel_count", "stable_scale_valid", "coverage_fraction", "usable_fraction",
        "registration_rmse_pixels", "registration_bias_abs_pixels", "candidate_pixel_count",
        "candidate_area_m2", "output_manifest_verified", "failed_history_preserved",
    }
    if not isinstance(report, dict) or set(report) != expected_fields:
        errors.append("route report fields differ")
    if errors:
        return {"status": "invalid", "reasons": errors, "candidate_admitted": False, "interpretation_created": False, "attribution_created": False}
    route_id = report["route_id"]
    if route_id not in EXPECTED_ROUTES or (report["route_kind"], report["threshold_profile"]) != EXPECTED_ROUTES.get(route_id):
        return {"status": "invalid", "reasons": ["route identity or threshold profile differs"], "candidate_admitted": False, "interpretation_created": False, "attribution_created": False}
    numeric = [report[key] for key in ("coverage_fraction", "usable_fraction", "registration_rmse_pixels", "registration_bias_abs_pixels", "candidate_area_m2")]
    integer = [report[key] for key in ("stable_control_zone_count", "stable_valid_pixel_count", "candidate_pixel_count")]
    if any(not _finite_number(value) or float(value) < 0 for value in numeric) or any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in integer):
        return {"status": "invalid", "reasons": ["route metrics are invalid"], "candidate_admitted": False, "interpretation_created": False, "attribution_created": False}
    block: list[str] = []
    defer: list[str] = []
    qa = contract["input_qa"]
    stable = contract["stable_reference"]
    if report["input_qa_status"] in {"invalid", "block"}:
        block.append("input QA blocks the route")
    elif report["input_qa_status"] != qa["required_status"]:
        defer.append("input QA is not pass_qa_only")
    if report["coverage_fraction"] < qa["minimum_coverage_fraction"] or report["usable_fraction"] < qa["minimum_usable_fraction"]:
        defer.append("coverage or usable fraction is below the admission threshold")
    if report["registration_rmse_pixels"] > qa["maximum_registration_rmse_pixels"] or report["registration_bias_abs_pixels"] > qa["maximum_absolute_registration_bias_pixels"]:
        block.append("registration exceeds the candidate threshold")
    if report["stable_control_zone_count"] < stable["minimum_control_zones"] or report["stable_valid_pixel_count"] < stable["minimum_valid_pixels_per_route"] or report["stable_scale_valid"] is not True:
        defer.append("stable-reference evidence is insufficient")
    if report["output_manifest_verified"] is not True:
        block.append("route output manifest is not verified")
    if report["failed_history_preserved"] is not True:
        block.append("failed or inconclusive history is not preserved")
    if report["candidate_pixel_count"] == 0 and report["candidate_area_m2"] != 0:
        return {"status": "invalid", "reasons": ["zero candidate pixels have nonzero area"], "candidate_admitted": False, "interpretation_created": False, "attribution_created": False}
    route = next(item for item in contract["routes"] if item["route_id"] == route_id)
    expected_candidate_area = report["candidate_pixel_count"] * float(route["cell_size_m"]) ** 2
    if expected_candidate_area > 0 and abs(report["candidate_area_m2"] - expected_candidate_area) / expected_candidate_area > contract["object_formation"]["candidate_raster_area_consistency_tolerance_fraction"]:
        return {"status": "invalid", "reasons": ["candidate raster area is inconsistent with pixel count and cell size"], "candidate_admitted": False, "interpretation_created": False, "attribution_created": False}
    if report["candidate_pixel_count"] > 0 and report["candidate_area_m2"] < contract["object_formation"]["minimum_mapping_unit_m2"]:
        defer.append("candidate objects are below the minimum mapping unit")
    status = "block" if block else ("defer" if defer else ("pass_candidate_only" if report["candidate_pixel_count"] > 0 else "pass_no_candidate_observed"))
    return {
        "status": status,
        "reasons": block if block else defer,
        "candidate_admitted": status == "pass_candidate_only",
        "interpretation_created": False,
        "attribution_created": False,
    }


def evaluate_synthesis(route_outcomes: list[dict[str, Any]], overlap_fraction_of_smaller: float | None, contract: dict[str, Any]) -> dict[str, Any]:
    if validate_contract(contract):
        return {"status": "invalid", "multisensor": False, "attribution_established": False}
    if not route_outcomes or any(not isinstance(item, dict) or item.get("route_id") not in EXPECTED_ROUTES or item.get("status") not in ROUTE_STATUSES for item in route_outcomes):
        return {"status": "invalid", "multisensor": False, "attribution_established": False}
    route_ids = [item["route_id"] for item in route_outcomes]
    if len(route_ids) != len(set(route_ids)) or set(route_ids) != set(EXPECTED_ROUTES):
        return {"status": "invalid", "multisensor": False, "attribution_established": False}
    if any(item["status"] in {"invalid", "block"} for item in route_outcomes):
        return {"status": "blocked", "multisensor": False, "attribution_established": False}
    candidates = [item for item in route_outcomes if item["status"] == "pass_candidate_only"]
    if len(candidates) >= 2:
        if not _finite_number(overlap_fraction_of_smaller) or not 0 <= float(overlap_fraction_of_smaller) <= 1:
            return {"status": "invalid", "multisensor": False, "attribution_established": False}
        coincident = float(overlap_fraction_of_smaller) >= contract["cross_route_synthesis"]["minimum_overlap_fraction_of_smaller_polygon"]
        route_kinds = {EXPECTED_ROUTES[item["route_id"]][0] for item in candidates}
        return {"status": "spatially_coincident_candidates" if coincident else "disagreement_retained", "multisensor": coincident and route_kinds == {"radar", "optical"}, "attribution_established": False}
    if len(candidates) == 1:
        return {"status": "single_route_candidate", "multisensor": False, "attribution_established": False}
    if all(item["status"] == "pass_no_candidate_observed" for item in route_outcomes):
        return {"status": "no_candidate_observed", "multisensor": False, "attribution_established": False}
    return {"status": "inconclusive", "multisensor": False, "attribution_established": False}
