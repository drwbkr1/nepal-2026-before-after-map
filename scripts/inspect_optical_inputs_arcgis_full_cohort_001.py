#!/usr/bin/env python3
"""Inspect one exact materialized Sentinel-2 pair with ArcGIS header reads only."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
from typing import Any

from m2_header_stage_gate import validate_header_stage_execution

from m2_materialization_core import sha256_file, write_new_json
from optical_input_readiness_core_full_cohort_001 import (
    RASTER_ROLES,
    decide_header_readiness,
    select_required_members,
    validate_pair_grids,
)
from optical_processing_core import parse_l2a_scaling_metadata, processing_baseline_from_product_id


ROOT = Path(__file__).resolve().parents[1]
UTC_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


def load_path(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def stop(code: str) -> None:
    print(json.dumps({"status": "stopped", "code": code, "external_data_mutated": False}, indent=2))
    raise SystemExit(12)


def repository_receipt_path(value: str, *, output: bool = False) -> tuple[str, Path]:
    posix = PurePosixPath(value)
    if posix.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/")):
        stop("unsafe_repository_receipt_path")
    expected_parent = PurePosixPath("records/readiness/optical-input") if output else PurePosixPath("records/acquisition/materialization")
    if posix.parent != expected_parent or posix.suffix.casefold() != ".json":
        stop("repository_receipt_path_outside_expected_root")
    return value, ROOT.joinpath(*posix.parts)


def inventory(root: Path) -> list[dict[str, Any]]:
    result = []
    for path in sorted((item for item in root.rglob("*") if item.is_file()), key=lambda item: str(item).casefold()):
        result.append({
            "relative_path": path.relative_to(root).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    return result


def describe_raster(arcpy: Any, path: Path) -> dict[str, Any]:
    description = arcpy.Describe(str(path))
    extent = description.extent
    children = sorted(
        list(getattr(description, "children", []) or []),
        key=lambda item: str(getattr(item, "name", "")),
    )
    header_source = children[0] if children else description
    result = {
        "format": getattr(description, "format", None),
        "wkid": getattr(description.spatialReference, "factoryCode", None),
        "band_count": getattr(description, "bandCount", None),
        "width": getattr(header_source, "width", None),
        "height": getattr(header_source, "height", None),
        "cell_width": getattr(header_source, "meanCellWidth", None),
        "cell_height": getattr(header_source, "meanCellHeight", None),
        "pixel_type": getattr(header_source, "pixelType", None),
        "xmin": extent.XMin,
        "ymin": extent.YMin,
        "xmax": extent.XMax,
        "ymax": extent.YMax,
    }
    if children:
        result["band_details"] = [
            {
                "name": getattr(child, "name", None),
                "width": getattr(child, "width", None),
                "height": getattr(child, "height", None),
                "cell_width": getattr(child, "meanCellWidth", None),
                "cell_height": getattr(child, "meanCellHeight", None),
                "pixel_type": getattr(child, "pixelType", None),
            }
            for child in children
        ]
    return result


def inspect_one(
    *,
    arcpy: Any,
    source_id: str,
    expected_product_id: str,
    materialization_receipt_ref: str,
    materialization_receipt_path: Path,
    contract: dict[str, Any],
    data_root: Path,
) -> dict[str, Any]:
    receipt = load_path(materialization_receipt_path)
    if receipt.get("status") != "pass_materialization_only" or receipt.get("source_id") != source_id:
        stop("materialization_receipt_not_passing_exact_source")
    if receipt.get("exact_product_id") != expected_product_id:
        stop("materialization_receipt_product_identity_mismatch")
    if receipt.get("bindings", {}).get("contract_sha256") != digest("contracts/m2-materialization.json"):
        stop("materialization_receipt_contract_mismatch")
    manifest_path = Path(receipt["bindings"]["external_manifest_path"])
    safe_root = Path(receipt["external_safe_root"])
    for candidate in (manifest_path, safe_root):
        try:
            candidate.resolve(strict=True).relative_to(data_root.resolve(strict=True))
        except (FileNotFoundError, ValueError):
            stop("materialized_input_outside_exact_external_root")
    if not manifest_path.is_file() or not safe_root.is_dir():
        stop("materialized_manifest_or_safe_root_missing")
    if sha256_file(manifest_path) != receipt["bindings"].get("external_manifest_sha256"):
        stop("external_materialization_manifest_hash_mismatch")
    completed_path = safe_root.parent / "completed.json"
    if not completed_path.is_file():
        stop("materialization_complete_marker_missing")
    completed = load_path(completed_path)
    if completed.get("status") != "complete" or completed.get("manifest_sha256") != sha256_file(manifest_path):
        stop("materialization_complete_marker_mismatch")
    manifest = load_path(manifest_path)
    if manifest.get("source_id") != source_id or manifest.get("exact_product_id") != expected_product_id:
        stop("external_materialization_manifest_identity_mismatch")
    external_before = inventory(safe_root.parent)
    member_inventory = select_required_members(manifest, contract)
    if member_inventory["status"] != "pass_inventory_only":
        return {
            "source_id": source_id,
            "materialization_receipt_ref": materialization_receipt_ref,
            "inventory": member_inventory,
            "metadata_errors": ["required member inventory did not pass"],
            "descriptions": {},
            "external_materialization_inventory_unchanged": external_before == inventory(safe_root.parent),
        }
    selected = member_inventory["members"]
    for role, item in selected.items():
        path = safe_root.joinpath(*PurePosixPath(item["relative_path"]).parts)
        try:
            path.resolve(strict=True).relative_to(safe_root.resolve(strict=True))
        except (FileNotFoundError, ValueError):
            stop("selected_materialized_member_outside_safe_root")
        if not path.is_file() or path.stat().st_size != item["size_bytes"] or sha256_file(path) != item["sha256"]:
            stop("selected_materialized_member_identity_mismatch")
    metadata_path = safe_root.joinpath(*PurePosixPath(selected["metadata_product"]["relative_path"]).parts)
    try:
        parsed = parse_l2a_scaling_metadata(metadata_path.read_text(encoding="utf-8"))
        metadata_errors = list(parsed["errors"])
    except Exception as exc:
        parsed = {"processing_baseline": None, "quantification_value": None, "offsets_by_band": {}, "errors": []}
        metadata_errors = [f"product metadata parse failed: {type(exc).__name__}: {exc}"]
    if parsed.get("processing_baseline") != contract["route"]["processing_baseline"]:
        metadata_errors.append("internal processing baseline differs from the exact route")
    if processing_baseline_from_product_id(expected_product_id) != contract["route"]["processing_baseline"]:
        metadata_errors.append("product-name processing baseline differs from the exact route")
    descriptions = {}
    for role in sorted(RASTER_ROLES):
        try:
            descriptions[role] = describe_raster(
                arcpy,
                safe_root.joinpath(*PurePosixPath(selected[role]["relative_path"]).parts),
            )
        except Exception as exc:
            metadata_errors.append(f"{role} ArcGIS header open failed: {type(exc).__name__}: {exc}")
    external_after = inventory(safe_root.parent)
    return {
        "source_id": source_id,
        "materialization_receipt_ref": materialization_receipt_ref,
        "materialization_receipt_sha256": sha256_file(materialization_receipt_path),
        "external_manifest_sha256": sha256_file(manifest_path),
        "inventory": member_inventory,
        "metadata": parsed,
        "metadata_errors": metadata_errors,
        "descriptions": descriptions,
        "selected_member_count": len(selected),
        "external_materialization_inventory_unchanged": external_before == external_after,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before-materialization-receipt", required=True)
    parser.add_argument("--after-materialization-receipt", required=True)
    parser.add_argument("--checked-at-utc", required=True)
    parser.add_argument("--receipt-output", required=True)
    args = parser.parse_args()
    if not UTC_TIMESTAMP.fullmatch(args.checked_at_utc):
        stop("invalid_checked_timestamp")
    try:
        validate_header_stage_execution()
    except Exception:
        stop("header_stage_gate_not_pass")
    if args.before_materialization_receipt != "records/acquisition/materialization/m1-src-010-m1-src-010-materialization-001.json" or args.after_materialization_receipt != "records/acquisition/materialization/m1-src-008-m1-src-008-materialization-001.json":
        stop("unexpected_optical_materialization_pair")
    if args.receipt_output != "records/readiness/optical-input/m2-s2-input-readiness-real-001.json":
        stop("unexpected_optical_real_001_receipt_identity")
    before_ref, before_path = repository_receipt_path(args.before_materialization_receipt)
    after_ref, after_path = repository_receipt_path(args.after_materialization_receipt)
    output_ref, output_path = repository_receipt_path(args.receipt_output, output=True)
    if output_path.exists():
        stop("optical_input_receipt_collision")
    if not before_path.is_file() or not after_path.is_file():
        stop("materialization_receipt_missing")

    contract = load_path(ROOT / "config/qa/optical-input-readiness-contract-full-cohort-001.json")
    expected_materializations = contract.get("materializations", {})
    if expected_materializations.get("before", {}).get("receipt_ref") != before_ref or expected_materializations.get("after", {}).get("receipt_ref") != after_ref or expected_materializations.get("before", {}).get("receipt_sha256") != sha256_file(before_path) or expected_materializations.get("after", {}).get("receipt_sha256") != sha256_file(after_path):
        stop("optical_materialization_binding_mismatch")
    for ref_key, hash_key in (
        ("materialization_contract_ref", "materialization_contract_sha256"),
        ("optical_processing_contract_ref", "optical_processing_contract_sha256"),
        ("pixel_readiness_contract_ref", "pixel_readiness_contract_sha256"),
        ("core_ref", "core_sha256"),
        ("runner_ref", "runner_sha256"),
    ):
        relative = contract.get("inputs", {}).get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file() or contract["inputs"].get(hash_key) != digest(relative):
            stop("optical_input_contract_binding_mismatch")
    milestone = load_path(ROOT / "contracts/milestone-002.json")
    if milestone.get("status") != "active" or "data_processing" not in milestone.get("authority", {}).get("authorized_action_classes", []):
        stop("m2_data_processing_authority_not_active")
    data_root = Path(contract["execution_boundary"]["external_data_root"])
    expected_root = ROOT.parent / f"{ROOT.name}-data"
    if not data_root.is_dir() or data_root.resolve(strict=True) != expected_root.resolve(strict=True):
        stop("external_data_root_mismatch")

    os.environ.setdefault("GDAL_PAM_ENABLED", "NO")
    import arcpy  # type: ignore[import-not-found]

    install = arcpy.GetInstallInfo()
    before = inspect_one(
        arcpy=arcpy,
        source_id=contract["route"]["before_source_id"],
        expected_product_id=contract["route"]["before_product_id"],
        materialization_receipt_ref=before_ref,
        materialization_receipt_path=before_path,
        contract=contract,
        data_root=data_root,
    )
    after = inspect_one(
        arcpy=arcpy,
        source_id=contract["route"]["after_source_id"],
        expected_product_id=contract["route"]["after_product_id"],
        materialization_receipt_ref=after_ref,
        materialization_receipt_path=after_path,
        contract=contract,
        data_root=data_root,
    )
    grid_errors = validate_pair_grids(before["descriptions"], after["descriptions"], contract)
    decision = decide_header_readiness(
        {
            before["source_id"]: before["inventory"]["status"],
            after["source_id"]: after["inventory"]["status"],
        },
        {
            before["source_id"]: before["metadata_errors"],
            after["source_id"]: after["metadata_errors"],
        },
        grid_errors,
    )
    external_inventory_unchanged = all(
        product.get("external_materialization_inventory_unchanged") is True
        for product in (before, after)
    )
    if not external_inventory_unchanged:
        decision = {
            **decision,
            "status": "block",
            "reasons": decision["reasons"] + ["external materialization inventory changed during read-only inspection"],
        }
    all_selected_headers_opened = all(
        len(product.get("descriptions", {})) == len(RASTER_ROLES)
        for product in (before, after)
    )
    receipt = {
        "receipt_version": "1.0",
        "receipt_id": "NEPAL-S2-MATERIALIZED-INPUT-READINESS-REAL-001",
        "checked_at_utc": args.checked_at_utc,
        "status": decision["status"],
        "runtime": {
            "product": install.get("ProductName", "ArcGISPro"),
            "version": install.get("Version"),
            "license_level": install.get("LicenseLevel", arcpy.ProductInfo()),
        },
        "bindings": {
            "contract_ref": "config/qa/optical-input-readiness-contract-full-cohort-001.json",
            "contract_sha256": digest("config/qa/optical-input-readiness-contract-full-cohort-001.json"),
            "before_materialization_receipt_ref": before_ref,
            "before_materialization_receipt_sha256": sha256_file(before_path),
            "after_materialization_receipt_ref": after_ref,
            "after_materialization_receipt_sha256": sha256_file(after_path),
        },
        "products": {before["source_id"]: before, after["source_id"]: after},
        "decision": decision,
        "activity": {
            "network_requests_performed": False,
            "authentication_performed": False,
            "external_data_mutated": not external_inventory_unchanged,
            "external_materialization_inventory_unchanged": external_inventory_unchanged,
            "selected_materialized_files_rehashed": True,
            "raster_header_open_attempted_with_arcgis": True,
            "all_selected_raster_headers_opened_with_arcgis": all_selected_headers_opened,
            "pixel_values_examined": False,
        },
        "limitations": contract["limitations"],
        "next_gate": "pixel_coverage_mask_and_registration_qa" if decision["status"] == "pass_header_readability_only" else "resolve retained optical input block",
    }
    write_new_json(output_path, receipt)
    print(json.dumps({"status": receipt["status"], "receipt": output_ref}, indent=2))
    return 0 if receipt["status"] == "pass_header_readability_only" else 20


if __name__ == "__main__":
    raise SystemExit(main())
