#!/usr/bin/env python3
"""Portable validation for the predeclared final ArcGIS delivery contract."""

from __future__ import annotations

import re
from typing import Any


HEX64 = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_DATASETS = {
    "StudyAreas",
    "SourceProducts",
    "ObservedChange",
    "AnalysisExclusions",
    "StableControls",
    "ObservationSources",
    "Interpretations",
    "AttributionAssessments",
    "AnalysisQA",
}
EXPECTED_RELATIONSHIPS = {
    "StudyAreas_ObservedChange",
    "StudyAreas_StableControls",
    "ObservedChange_ObservationSources",
    "SourceProducts_ObservationSources",
    "ObservedChange_Interpretations",
    "Interpretations_Attribution",
    "ObservedChange_AnalysisQA",
    "SourceProducts_Exclusions",
}
EXPECTED_MAPS = {
    "regional_overview",
    "source_area_comparison",
    "upper_corridor_comparison",
    "evidence_map",
    "limitations_map",
}
EXPECTED_LAYOUT_ELEMENTS = {
    "title",
    "before_after_dates",
    "legend",
    "scale_bar",
    "north_arrow",
    "crs_statement",
    "source_credits",
    "limitations_statement",
    "review_status",
    "attribution_disclaimer",
}


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _nonnegative_int(value: Any) -> bool:
    return _is_int(value) and value >= 0


def validate_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "contract_version", "contract_id", "status", "prepared_at_utc", "applies_at_milestone",
        "analysis_crs", "authoritative_inputs", "required_artifacts", "required_maps",
        "required_layout_elements", "required_dataset_names", "required_relationship_names",
        "evidence_integrity", "spatial_acceptance", "package_acceptance", "decision_semantics",
        "claim_boundary",
    }
    if set(contract) != required:
        errors.append("contract fields differ")
        return errors
    if contract["contract_version"] != "1.0" or contract["contract_id"] != "NEPAL-M6-ARCGIS-FINAL-DELIVERY-001":
        errors.append("contract identity differs")
    if contract["status"] != "predeclared_not_executed" or contract["applies_at_milestone"] != "M6":
        errors.append("contract must remain predeclared for M6")
    if contract["analysis_crs"] != {"wkid": 32645, "name": "WGS 1984 UTM Zone 45N", "linear_unit": "Meter"}:
        errors.append("analysis CRS differs")
    inputs = contract["authoritative_inputs"]
    if not isinstance(inputs, dict) or len(inputs) != 4:
        errors.append("authoritative input bindings differ")
    else:
        for name, binding in inputs.items():
            if not isinstance(binding, dict) or set(binding) != {"ref", "sha256"}:
                errors.append(f"input binding differs: {name}")
            elif not isinstance(binding["ref"], str) or not binding["ref"] or not HEX64.fullmatch(str(binding["sha256"])):
                errors.append(f"input binding is invalid: {name}")
    artifacts = contract["required_artifacts"]
    classes: set[str] = set()
    if not isinstance(artifacts, list) or len(artifacts) < 10:
        errors.append("required artifacts are incomplete")
    else:
        for item in artifacts:
            if not isinstance(item, dict) or set(item) != {"artifact_class", "suffix", "minimum_count"}:
                errors.append("required artifact entry differs")
                continue
            name = item["artifact_class"]
            if name in classes or not isinstance(name, str) or not name:
                errors.append("required artifact classes must be unique")
            classes.add(name)
            if not isinstance(item["suffix"], str) or not item["suffix"].startswith("."):
                errors.append(f"artifact suffix is invalid: {name}")
            if not _is_int(item["minimum_count"]) or item["minimum_count"] < 1:
                errors.append(f"artifact minimum is invalid: {name}")
    if set(contract["required_maps"]) != EXPECTED_MAPS or len(contract["required_maps"]) != len(EXPECTED_MAPS):
        errors.append("required map set differs")
    if set(contract["required_layout_elements"]) != EXPECTED_LAYOUT_ELEMENTS or len(contract["required_layout_elements"]) != len(EXPECTED_LAYOUT_ELEMENTS):
        errors.append("required layout elements differ")
    if set(contract["required_dataset_names"]) != EXPECTED_DATASETS or len(contract["required_dataset_names"]) != len(EXPECTED_DATASETS):
        errors.append("required evidence datasets differ")
    if set(contract["required_relationship_names"]) != EXPECTED_RELATIONSHIPS or len(contract["required_relationship_names"]) != len(EXPECTED_RELATIONSHIPS):
        errors.append("required evidence relationships differ")
    integrity = contract["evidence_integrity"]
    required_integrity_flags = {
        "require_before_and_after_source_per_observation",
        "require_exact_source_identity_and_acquisition_dates",
        "require_uncertainty_and_limitation_per_observation",
        "require_interpretation_links",
        "require_attribution_links_and_status",
        "require_observation_interpretation_attribution_separation",
        "require_failed_deferred_inconclusive_reconciliation",
        "require_qa_records",
        "require_owner_review",
        "require_completed_m5_review",
    }
    if not isinstance(integrity, dict) or any(integrity.get(key) is not True for key in required_integrity_flags):
        errors.append("evidence-integrity requirements are weakened")
    elif integrity.get("minimum_scientific_record_count") != 1 or integrity.get("minimum_preserved_non_success_records", 0) < 2:
        errors.append("evidence-integrity minimums differ")
    spatial = contract["spatial_acceptance"]
    if (
        spatial.get("required_vector_wkid") != 32645
        or spatial.get("required_raster_wkid") != 32645
        or spatial.get("require_grid_metadata") is not True
        or spatial.get("require_passing_registration_qa") is not True
        or spatial.get("require_visible_exclusion_masks") is not True
    ):
        errors.append("spatial acceptance is weakened")
    package = contract["package_acceptance"]
    if (
        package.get("independent_environment_required") is not True
        or set(package.get("allowed_independent_environment_types", [])) != {"clean_machine", "clean_local_profile"}
        or package.get("original_workspace_must_be_absent") is not True
        or package.get("package_extract_reopen_and_reexport_required") is not True
        or package.get("broken_source_maximum") != 0
        or package.get("external_operational_source_maximum") != 0
        or package.get("unsafe_path_maximum") != 0
        or package.get("missing_artifact_maximum") != 0
        or package.get("rights_conflict_maximum") != 0
        or package.get("artifact_sha256_verification_required") is not True
        or package.get("visual_review_required_for_every_map") is not True
    ):
        errors.append("package acceptance is weakened")
    semantics = contract["decision_semantics"]
    if semantics.get("precedence") != ["invalid", "block", "defer", "pass_m6_delivery_only"]:
        errors.append("decision precedence differs")
    if semantics.get("pass_does_not_authorize_publication") is not True or semantics.get("pass_does_not_replace_m5_scientific_review") is not True:
        errors.append("pass boundary is weakened")
    boundary = contract["claim_boundary"]
    for key in (
        "current_m6_complete", "scientific_evidence_currently_packaged",
        "clean_environment_test_currently_complete", "public_release_authorized",
        "emergency_guidance_authorized", "current_checkpoint_changed",
    ):
        if boundary.get(key) is not False:
            errors.append(f"claim boundary overstates current result: {key}")
    return errors


def evaluate_report(report: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    invalid = validate_contract(contract)
    required_report = {"report_version", "runtime", "project", "artifacts", "maps", "evidence", "spatial", "claim_boundary"}
    if not isinstance(report, dict) or set(report) != required_report:
        invalid.append("report fields differ")
        return {"status": "invalid", "errors": invalid, "block_reasons": [], "defer_reasons": []}

    runtime = report.get("runtime", {})
    project = report.get("project", {})
    artifacts = report.get("artifacts", {})
    maps = report.get("maps", {})
    evidence = report.get("evidence", {})
    spatial = report.get("spatial", {})
    boundary = report.get("claim_boundary", {})
    if report.get("report_version") != "1.0":
        invalid.append("report version differs")
    if any(not isinstance(section, dict) for section in (runtime, project, artifacts, maps, evidence, spatial, boundary)):
        invalid.append("report sections must be objects")
        return {"status": "invalid", "errors": invalid, "block_reasons": [], "defer_reasons": []}
    count_fields = [
        project.get("broken_source_count"), project.get("external_operational_source_count"),
        project.get("operational_source_count"), project.get("domain_count"), project.get("relationship_count"),
        artifacts.get("unsafe_path_count"), artifacts.get("missing_count"), artifacts.get("rights_conflict_count"),
        evidence.get("scientific_record_count"), evidence.get("non_success_record_count"),
    ]
    if any(not _nonnegative_int(value) for value in count_fields):
        invalid.append("report counts must be nonnegative integers")
    if boundary.get("public_release_authorized_by_report") is not False or boundary.get("emergency_guidance") is not False:
        invalid.append("report overstates publication or emergency authority")
    if invalid:
        return {"status": "invalid", "errors": invalid, "block_reasons": [], "defer_reasons": []}

    block: list[str] = []
    defer: list[str] = []
    if project.get("map_wkid") != 32645:
        block.append("project map is not EPSG:32645")
    if project.get("broken_source_count") != 0:
        block.append("project has broken sources")
    if project.get("external_operational_source_count") != 0:
        block.append("project has operational sources outside the package")
    if project.get("operational_source_count") < 1:
        block.append("project has no operational sources")
    if set(project.get("dataset_names", [])) != EXPECTED_DATASETS or len(project.get("dataset_names", [])) != len(EXPECTED_DATASETS):
        block.append("evidence dataset set differs")
    if set(project.get("relationship_names", [])) != EXPECTED_RELATIONSHIPS or len(project.get("relationship_names", [])) != len(EXPECTED_RELATIONSHIPS):
        block.append("evidence relationship set differs")
    if project.get("domain_count") < 14 or project.get("relationship_count") < 8:
        block.append("evidence schema domain or relationship count is incomplete")

    required_counts = {item["artifact_class"]: item["minimum_count"] for item in contract["required_artifacts"]}
    by_class = artifacts.get("by_class", {})
    if not isinstance(by_class, dict) or any(not _nonnegative_int(value) for value in by_class.values()):
        return {"status": "invalid", "errors": ["artifact class counts are invalid"], "block_reasons": [], "defer_reasons": []}
    for name, minimum in required_counts.items():
        if by_class.get(name, 0) < minimum:
            block.append(f"required artifact class is incomplete: {name}")
    if artifacts.get("manifest_verified") is not True or artifacts.get("all_sha256_verified") is not True:
        block.append("artifact manifest or SHA-256 verification is incomplete")
    if artifacts.get("unsafe_path_count") != 0 or artifacts.get("missing_count") != 0 or artifacts.get("rights_conflict_count") != 0:
        block.append("artifact path, presence, or rights checks failed")

    if set(maps) != EXPECTED_MAPS:
        block.append("required map set is incomplete")
    else:
        for map_id, item in maps.items():
            if not isinstance(item, dict):
                block.append(f"map report is invalid: {map_id}")
                continue
            if item.get("layout_exists") is not True or item.get("png_exists") is not True or item.get("pdf_exists") is not True:
                block.append(f"map exports are incomplete: {map_id}")
            if set(item.get("elements", [])) != EXPECTED_LAYOUT_ELEMENTS:
                block.append(f"layout elements are incomplete: {map_id}")
            if item.get("visual_review") != "pass":
                defer.append(f"visual review is pending or inconclusive: {map_id}")

    integrity_flags = {
        "observed_source_links_complete",
        "every_observation_has_before_after",
        "source_identity_reconciled",
        "acquisition_dates_present",
        "uncertainty_complete",
        "limitations_complete",
        "interpretation_links_complete",
        "attribution_links_complete",
        "observation_interpretation_attribution_separate",
        "all_failed_deferred_inconclusive_reconciled",
        "qa_records_complete",
        "owner_review_complete",
    }
    for key in sorted(integrity_flags):
        if evidence.get(key) is not True:
            block.append(f"evidence integrity is incomplete: {key}")
    if evidence.get("non_success_record_count") < contract["evidence_integrity"]["minimum_preserved_non_success_records"]:
        block.append("retained failed, deferred, or inconclusive history is incomplete")
    if evidence.get("scientific_record_count") < contract["evidence_integrity"]["minimum_scientific_record_count"]:
        defer.append("no reviewed scientific observation is available for final delivery")
    if boundary.get("m5_review_complete") is not True:
        defer.append("M5 scientific review is incomplete")

    vector_wkids = spatial.get("scientific_vector_wkids", [])
    raster_wkids = spatial.get("analysis_raster_wkids", [])
    if not vector_wkids or any(value != 32645 for value in vector_wkids):
        block.append("scientific vector CRS differs from EPSG:32645")
    if not raster_wkids or any(value != 32645 for value in raster_wkids):
        block.append("analysis raster CRS differs from EPSG:32645")
    if spatial.get("grid_metadata_complete") is not True:
        block.append("grid metadata is incomplete")
    if spatial.get("registration_qa_pass") is not True:
        block.append("registration QA has not passed")
    if spatial.get("exclusion_masks_present") is not True:
        block.append("visible exclusion masks are absent")

    if runtime.get("environment_type") not in {"clean_machine", "clean_local_profile"}:
        defer.append("independent environment test is missing")
    if runtime.get("original_workspace_absent") is not True:
        defer.append("original workspace was available during portability test")
    for key in ("package_created", "package_extracted", "project_reopened", "reexport_succeeded"):
        if runtime.get(key) is not True:
            defer.append(f"runtime package check is incomplete: {key}")

    status = "block" if block else ("defer" if defer else "pass_m6_delivery_only")
    return {
        "status": status,
        "errors": [],
        "block_reasons": block,
        "defer_reasons": defer,
        "m6_delivery_acceptance_established": status == "pass_m6_delivery_only",
        "public_release_authorized": False,
        "emergency_guidance_authorized": False,
    }
