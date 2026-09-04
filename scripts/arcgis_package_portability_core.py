#!/usr/bin/env python3
"""Portable validation helpers for the metadata-only ArcGIS package fixture."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any


HEX64 = re.compile(r"[0-9a-f]{64}")
FORBIDDEN_EXTRACTED_SUFFIXES = {
    ".tif", ".tiff", ".jp2", ".img", ".vrt", ".crf", ".nc", ".hdf", ".h5"
}
EXPECTED_DATASET_COUNTS = {
    "StudyAreas": 3,
    "SourceProducts": 10,
    "ObservedChange": 0,
    "AnalysisExclusions": 0,
    "StableControls": 0,
    "ObservationSources": 0,
    "Interpretations": 0,
    "AttributionAssessments": 0,
    "AnalysisQA": 0,
}
SCIENTIFIC_DATASETS = {
    "ObservedChange",
    "AnalysisExclusions",
    "StableControls",
    "ObservationSources",
    "Interpretations",
    "AttributionAssessments",
    "AnalysisQA",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_inventory(root: Path) -> list[dict[str, Any]]:
    """Hash every stable file beneath *root*, excluding only ArcGIS lock files."""
    if not root.is_dir():
        raise ValueError("inventory root is not a directory")
    result: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix().casefold()):
        if path.is_symlink():
            raise ValueError(f"inventory contains a symbolic link: {path.relative_to(root).as_posix()}")
        if not path.is_file() or path.name.casefold().endswith(".lock"):
            continue
        result.append({
            "relative_path": path.relative_to(root).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    return result


def inventory_sha256(items: list[dict[str, Any]]) -> str:
    payload = json.dumps(items, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def inventory_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "file_count": len(items),
        "total_bytes": sum(int(item["size_bytes"]) for item in items),
        "inventory_sha256": inventory_sha256(items),
    }


def _safe_relative(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    posix = PurePosixPath(value)
    return not posix.is_absolute() and all(part not in {"", ".", ".."} for part in value.split("/"))


def validate_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if contract.get("contract_id") != "NEPAL-M6-ARCGIS-PACKAGE-PORTABILITY-001":
        errors.append("contract identity differs")
    if contract.get("status") != "predeclared_not_executed":
        errors.append("contract status differs")
    if contract.get("analysis_crs", {}).get("wkid") != 32645:
        errors.append("analysis CRS differs")
    source = contract.get("source_workspace", {})
    if source.get("expected_inventory") != {
        "file_count": 110,
        "total_bytes": 1171536,
        "inventory_sha256": "f8f3c94f77c904954d729c7340d82a09183ad52671736e3d1d80f6609b67617a",
    }:
        errors.append("source workspace inventory identity differs")
    if source.get("expected_dataset_counts") != EXPECTED_DATASET_COUNTS:
        errors.append("source dataset counts differ")
    for key in ("root", "project", "geodatabase", "overview_png", "overview_pdf"):
        if not isinstance(source.get(key), str) or not source[key]:
            errors.append(f"source workspace {key} is missing")
    for key in ("project_sha256", "overview_png_sha256", "overview_pdf_sha256"):
        if not isinstance(source.get(key), str) or not HEX64.fullmatch(source[key]):
            errors.append(f"source workspace {key} is not SHA-256")
    output = contract.get("external_output", {})
    if output.get("root") != r"C:\Projects\Active\nepal-2026-before-after-map-data\derived\arcgis-package-portability\attempt-001":
        errors.append("external output root differs")
    for key in ("package", "extract_root", "reexport_png", "reexport_pdf", "manifest", "receipt", "failure_receipt"):
        if not _safe_relative(output.get(key)):
            errors.append(f"external output {key} is unsafe")
    operation = contract.get("operation", {})
    expected_operation = {
        "sharing_internal": "EXTERNAL",
        "package_as_template": "PROJECT_PACKAGE",
        "version": "3.7",
        "include_toolboxes": "NO_TOOLBOXES",
        "include_history_items": "NO_HISTORY_ITEMS",
        "read_only": "READ_WRITE",
        "select_related_rows": "KEEP_ALL_RELATED_ROWS",
        "preserve_sqlite": "CONVERT_SQLITE",
        "extract_cache": "NO_CACHE",
    }
    if operation != expected_operation:
        errors.append("ArcGIS package operation differs")
    boundary = contract.get("execution_boundary", {})
    required_boundary = {
        "network_requests": "prohibited",
        "authentication": "prohibited",
        "credential_access": "prohibited",
        "source_workspace_mutation": "prohibited",
        "scientific_data_inclusion": "prohibited_metadata_only",
        "output_collision": "stop",
        "output_location": "external_non_git_append_only",
    }
    for key, expected in required_boundary.items():
        if boundary.get(key) != expected:
            errors.append(f"execution boundary differs at {key}")
    checks = contract.get("required_checks", {})
    if checks.get("expected_dataset_counts") != EXPECTED_DATASET_COUNTS:
        errors.append("required extracted dataset counts differ")
    if checks.get("forbidden_extracted_suffixes") != sorted(FORBIDDEN_EXTRACTED_SUFFIXES):
        errors.append("forbidden extracted suffixes differ")
    if checks.get("required_operational_layer_count") != 3 or checks.get("required_basemap_layer_count") != 0:
        errors.append("required layer counts differ")
    if checks.get("maximum_package_bytes") != 50_000_000 or checks.get("maximum_extracted_stable_files") != 500:
        errors.append("bounded output limits differ")
    claim = contract.get("claim_boundary", {})
    false_claims = (
        "clean_machine_portability_established",
        "cross_version_portability_established",
        "satellite_pixels_packaged",
        "dem_pixels_packaged",
        "scientific_evidence_packaged",
        "mapped_change_established",
        "scientific_admission_authorized",
        "m6_complete",
        "current_checkpoint_changed",
    )
    if any(claim.get(key) is not False for key in false_claims):
        errors.append("claim boundary overstates the fixture")
    return errors


def evaluate_runtime(report: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    """Apply the predeclared, portable decision rule to an ArcGIS runtime report."""
    errors = validate_contract(contract)
    source = report.get("source", {})
    expected_source = contract.get("source_workspace", {}).get("expected_inventory", {})
    if source.get("before") != expected_source:
        errors.append("source inventory before packaging differs")
    if source.get("after") != expected_source or source.get("unchanged") is not True:
        errors.append("source workspace changed during packaging")
    package = report.get("package", {})
    if package.get("exists") is not True:
        errors.append("project package is missing")
    size = package.get("size_bytes")
    if not isinstance(size, int) or size <= 0 or size > contract["required_checks"]["maximum_package_bytes"]:
        errors.append("project package size is invalid or exceeds the bound")
    if not isinstance(package.get("sha256"), str) or not HEX64.fullmatch(package["sha256"]):
        errors.append("project package SHA-256 is missing")
    extracted = report.get("extracted", {})
    if extracted.get("stable_file_count", 0) <= 0 or extracted.get("stable_file_count", 0) > contract["required_checks"]["maximum_extracted_stable_files"]:
        errors.append("extracted stable file count is invalid or exceeds the bound")
    if extracted.get("forbidden_raster_files") != []:
        errors.append("package contains a forbidden raster artifact")
    if extracted.get("symlink_count") != 0:
        errors.append("package extraction contains a symbolic link")
    project = report.get("extracted_project", {})
    if project.get("project_count") != 1:
        errors.append("extraction does not contain exactly one ArcGIS project")
    if project.get("map_count") != 1 or project.get("layout_count") != 1:
        errors.append("extracted project map or layout identity differs")
    if project.get("map_wkid") != 32645:
        errors.append("extracted map is not EPSG:32645")
    if len(project.get("layers", [])) != contract["required_checks"]["required_operational_layer_count"]:
        errors.append("extracted operational layer count differs")
    if project.get("basemap_layer_count") != contract["required_checks"]["required_basemap_layer_count"]:
        errors.append("extracted basemap layer count differs")
    if project.get("broken_layer_count") != 0 or project.get("external_operational_source_count") != 0:
        errors.append("extracted operational layers are broken or externally referenced")
    if project.get("operational_geodatabase_count") != 1:
        errors.append("extracted operational geodatabase count differs")
    if project.get("dataset_counts") != EXPECTED_DATASET_COUNTS:
        errors.append("extracted dataset counts differ")
    if project.get("scientific_record_count") != 0:
        errors.append("extracted package contains scientific records")
    if project.get("relationship_count") != 8 or project.get("domain_count") != 14:
        errors.append("extracted geodatabase relationships or domains differ")
    exports = report.get("reexports", {})
    if exports.get("png_exists") is not True or exports.get("pdf_exists") is not True:
        errors.append("round-trip layout exports are missing")
    for label in ("png", "pdf"):
        size = exports.get(f"{label}_size_bytes")
        digest = exports.get(f"{label}_sha256")
        if not isinstance(size, int) or size <= 0:
            errors.append(f"round-trip {label.upper()} is empty")
        if not isinstance(digest, str) or not HEX64.fullmatch(digest):
            errors.append(f"round-trip {label.upper()} SHA-256 is missing")
    if exports.get("png_dimensions") != [1760, 1360]:
        errors.append("round-trip PNG dimensions differ")
    if exports.get("png_pixel_sha256_matches_source") is not True:
        errors.append("round-trip PNG pixels differ from the source overview")
    return {
        "status": "pass_same_machine_runtime_manual_visual_review_pending" if not errors else "fail_retained",
        "errors": errors,
        "same_machine_round_trip_established": not errors,
        "manual_visual_review_required": True,
        "m6_complete": False,
        "scientific_admission_authorized": False,
    }
