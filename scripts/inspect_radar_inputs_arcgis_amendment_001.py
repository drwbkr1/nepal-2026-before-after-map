#!/usr/bin/env python3
"""Run the one authorized amended Sentinel-1 read-only real-002 inspection."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
from typing import Any

from m2_materialization_core import sha256_file, write_new_json
from radar_input_readiness_core_amendment_001 import (
    POLARIZATIONS,
    decide_source_readiness,
    parse_s1_annotation,
    select_required_members,
    summarize_partial_readiness,
    validate_contract,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REF = "config/qa/radar-input-readiness-contract-amendment-001.json"
UTC_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return value


def digest(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def stop(code: str) -> None:
    print(json.dumps({"status": "stopped", "code": code, "external_data_mutated": False}, indent=2))
    raise SystemExit(12)


def repository_output_path(value: str) -> tuple[str, Path]:
    posix = PurePosixPath(value)
    if posix.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/")):
        stop("unsafe_repository_receipt_path")
    if posix.parent != PurePosixPath("records/readiness/radar-input") or posix.suffix.casefold() != ".json":
        stop("repository_receipt_path_outside_expected_root")
    return value, ROOT.joinpath(*posix.parts)


def require_existing_external_child(data_root: Path, candidate: Path) -> Path:
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(data_root.resolve(strict=True))
    except (FileNotFoundError, ValueError):
        stop("materialized_input_outside_exact_external_root")
    return resolved


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
    children = sorted(
        list(getattr(description, "children", []) or []),
        key=lambda item: str(getattr(item, "name", "")),
    )
    header = children[0] if children else description
    spatial_reference = getattr(description, "spatialReference", None)
    extent = getattr(description, "extent", None)
    return {
        "format": getattr(description, "format", None),
        "band_count": getattr(description, "bandCount", None),
        "width": getattr(header, "width", None),
        "height": getattr(header, "height", None),
        "pixel_type": getattr(header, "pixelType", None),
        "cell_width": getattr(header, "meanCellWidth", None),
        "cell_height": getattr(header, "meanCellHeight", None),
        "spatial_reference_wkid": getattr(spatial_reference, "factoryCode", None),
        "spatial_reference_name": getattr(spatial_reference, "name", None),
        "extent": None if extent is None else {
            "xmin": extent.XMin,
            "ymin": extent.YMin,
            "xmax": extent.XMax,
            "ymax": extent.YMax,
        },
    }


def prepare_source(
    *,
    expected: dict[str, Any],
    contract: dict[str, Any],
    data_root: Path,
) -> tuple[dict[str, Any], Path, Path, dict[str, dict[str, Any]]]:
    receipt_ref = expected["materialization_receipt_ref"]
    receipt_path = ROOT.joinpath(*PurePosixPath(receipt_ref).parts)
    if not receipt_path.is_file() or sha256_file(receipt_path) != expected["materialization_receipt_sha256"]:
        stop("materialization_receipt_hash_mismatch")
    receipt = load_json(receipt_path)
    if (
        receipt.get("status") != "pass_materialization_only"
        or receipt.get("source_id") != expected["source_id"]
        or receipt.get("exact_product_id") != expected["exact_product_id"]
        or receipt.get("bindings", {}).get("contract_sha256") != digest("contracts/m2-materialization.json")
    ):
        stop("materialization_receipt_identity_or_contract_mismatch")
    manifest_path = require_existing_external_child(data_root, Path(receipt["bindings"]["external_manifest_path"]))
    safe_root = require_existing_external_child(data_root, Path(receipt["external_safe_root"]))
    if not manifest_path.is_file() or not safe_root.is_dir():
        stop("materialized_manifest_or_safe_root_missing")
    manifest_sha = sha256_file(manifest_path)
    if manifest_sha != receipt["bindings"].get("external_manifest_sha256") or manifest_sha != expected["external_manifest_sha256"]:
        stop("external_materialization_manifest_hash_mismatch")
    completed_path = safe_root.parent / "completed.json"
    if not completed_path.is_file():
        stop("materialization_complete_marker_missing")
    completed = load_json(completed_path)
    if completed.get("status") != "complete" or completed.get("manifest_sha256") != manifest_sha:
        stop("materialization_complete_marker_mismatch")
    manifest = load_json(manifest_path)
    if manifest.get("source_id") != expected["source_id"] or manifest.get("exact_product_id") != expected["exact_product_id"]:
        stop("external_materialization_manifest_identity_mismatch")
    inventory_result = select_required_members(manifest, contract)
    if inventory_result["status"] != "pass_inventory_only":
        return ({
            "source_id": expected["source_id"],
            "materialization_receipt_ref": receipt_ref,
            "materialization_receipt_sha256": sha256_file(receipt_path),
            "external_manifest_sha256": manifest_sha,
            "inventory": inventory_result,
            "annotations": {},
            "raster_headers": {},
        }, safe_root.parent, safe_root, {})
    selected = inventory_result["members"]
    for item in selected.values():
        path = require_existing_external_child(
            safe_root,
            safe_root.joinpath(*PurePosixPath(item["relative_path"]).parts),
        )
        if not path.is_file() or path.stat().st_size != item["size_bytes"] or sha256_file(path) != item["sha256"]:
            stop("selected_materialized_member_identity_mismatch")
    annotations: dict[str, dict[str, Any]] = {}
    for polarization in POLARIZATIONS:
        key = polarization.casefold()
        annotation_path = safe_root.joinpath(*PurePosixPath(selected[f"annotation_{key}"]["relative_path"]).parts)
        annotations[key] = parse_s1_annotation(annotation_path.read_bytes())
    return ({
        "source_id": expected["source_id"],
        "materialization_receipt_ref": receipt_ref,
        "materialization_receipt_sha256": sha256_file(receipt_path),
        "external_manifest_sha256": manifest_sha,
        "inventory": inventory_result,
        "annotations": annotations,
        "raster_headers": {},
    }, safe_root.parent, safe_root, selected)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checked-at-utc", required=True)
    parser.add_argument("--receipt-output", required=True)
    args = parser.parse_args()
    if not UTC_TIMESTAMP.fullmatch(args.checked_at_utc):
        stop("invalid_checked_timestamp")
    output_ref, output_path = repository_output_path(args.receipt_output)
    if output_path.exists():
        stop("radar_input_receipt_collision")
    contract = load_json(ROOT / CONTRACT_REF)
    if validate_contract(contract):
        stop("radar_input_contract_invalid")
    for ref_key, hash_key in (
        ("materialization_contract_ref", "materialization_contract_sha256"),
        ("radar_processing_contract_ref", "radar_processing_contract_sha256"),
        ("pixel_readiness_contract_ref", "pixel_readiness_contract_sha256"),
        ("source_manifest_ref", "source_manifest_sha256"),
        ("active_m2_ref", "active_m2_sha256"),
        ("activation_approval_ref", "activation_approval_sha256"),
        ("core_ref", "core_sha256"),
        ("runner_ref", "runner_sha256"),
    ):
        relative = contract.get("inputs", {}).get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file() or contract["inputs"].get(hash_key) != digest(relative):
            stop("radar_input_contract_binding_mismatch")
    milestone = load_json(ROOT / contract["inputs"]["active_m2_ref"])
    action_classes = milestone.get("authority", {}).get("authorized_action_classes", [])
    if milestone.get("status") != "active" or not {"read_only_inspection", "routine_qa"}.issubset(set(action_classes)):
        stop("m2_read_only_qa_authority_not_active")
    data_root = Path(contract["execution_boundary"]["external_data_root"])
    expected_root = ROOT.parent / f"{ROOT.name}-data"
    if not data_root.is_dir() or data_root.resolve(strict=True) != expected_root.resolve(strict=True):
        stop("external_data_root_mismatch")

    products: dict[str, Any] = {}
    actual_roots: dict[str, Path] = {}
    safe_roots: dict[str, Path] = {}
    selected_by_source: dict[str, dict[str, dict[str, Any]]] = {}
    for expected in contract["sources"]:
        product, attempt_root, safe_root, selected = prepare_source(
            expected=expected, contract=contract, data_root=data_root
        )
        source_id = expected["source_id"]
        products[source_id] = product
        actual_roots[source_id] = attempt_root
        safe_roots[source_id] = safe_root
        selected_by_source[source_id] = selected
    before = {source_id: inventory(root) for source_id, root in actual_roots.items()}

    arcgis_invoked = all(
        product.get("inventory", {}).get("status") == "pass_inventory_only"
        for product in products.values()
    )
    if arcgis_invoked:
        os.environ.setdefault("GDAL_PAM_ENABLED", "NO")
        import arcpy  # type: ignore[import-not-found]

        install = arcpy.GetInstallInfo()
        license_level = install.get("LicenseLevel") or arcpy.ProductInfo()
    else:
        arcpy = None
        install = {"ProductName": "not_invoked_due_pre_arc_block", "Version": None, "LicenseLevel": None}
        license_level = None
    for expected in contract["sources"]:
        source_id = expected["source_id"]
        product = products[source_id]
        descriptions: dict[str, dict[str, Any]] = {}
        if arcgis_invoked:
            for polarization in POLARIZATIONS:
                key = polarization.casefold()
                measurement_path = safe_roots[source_id].joinpath(
                    *PurePosixPath(selected_by_source[source_id][f"measurement_{key}"]["relative_path"]).parts
                )
                try:
                    descriptions[key] = describe_raster(arcpy, measurement_path)
                except Exception as exc:
                    descriptions[key] = {"open_error": f"{type(exc).__name__}: {exc}"}
        product["raster_headers"] = descriptions
        product["decision"] = decide_source_readiness(
            product["inventory"]["status"], product["annotations"], descriptions, expected, contract
        )
    after = {source_id: inventory(root) for source_id, root in actual_roots.items()}
    external_unchanged = before == after
    source_decisions = {source_id: value["decision"] for source_id, value in products.items()}
    summary = summarize_partial_readiness(source_decisions)
    if not external_unchanged:
        summary = {
            **summary,
            "status": "block",
            "errors": summary["errors"] + ["external materialization inventory changed during read-only inspection"],
        }
    all_annotations_parsed = all(
        set(product.get("annotations", {})) == {"vv", "vh"}
        and all(not value.get("errors") for value in product["annotations"].values())
        for product in products.values()
    )
    all_headers_opened = all(
        set(product.get("raster_headers", {})) == {"vv", "vh"}
        and all("open_error" not in value for value in product["raster_headers"].values())
        for product in products.values()
    )
    all_three_ready = summary["status"] == "pass_partial_pre_event_header_readiness_only"
    receipt = {
        "receipt_version": "1.0",
        "receipt_id": "NEPAL-S1-MATERIALIZED-INPUT-READINESS-REAL-002",
        "checked_at_utc": args.checked_at_utc,
        "status": summary["status"],
        "runtime": {
            "product": install.get("ProductName", "ArcGISPro"),
            "version": install.get("Version"),
            "license_level": license_level,
        },
        "bindings": {
            "contract_ref": CONTRACT_REF,
            "contract_sha256": digest(CONTRACT_REF),
            "materialization_receipt_sha256": {
                item["source_id"]: item["materialization_receipt_sha256"] for item in contract["sources"]
            },
            "external_manifest_sha256": {
                item["source_id"]: item["external_manifest_sha256"] for item in contract["sources"]
            },
        },
        "products": products,
        "decision": summary,
        "activity": {
            "network_requests_performed": False,
            "authentication_performed": False,
            "credential_values_read_or_recorded": False,
            "external_materialization_inventory_unchanged": external_unchanged,
            "selected_materialized_files_rehashed": True,
            "real_annotation_metadata_parse_attempted": True,
            "all_real_annotation_metadata_parsed": all_annotations_parsed,
            "real_measurement_raster_header_open_attempted_with_arcgis": arcgis_invoked,
            "all_real_measurement_raster_headers_opened_with_arcgis": all_headers_opened,
            "real_product_pixel_values_examined": False,
            "derived_raster_written": False,
        },
        "claim_boundary": {
            "exact_three_source_member_and_header_readiness_established": all_three_ready,
            "pixel_values_examined": False,
            "pixel_usability_established": False,
            "complete_pair_established": False,
            "baseline_established": False,
            "change_established": False,
            "scientific_admission_authorized": False,
        },
        "limitations": contract["limitations"],
        "next_gate": "complete exact Sentinel acquisition and all independent orbit, vertical-datum, terrain-result, and pixel gates",
    }
    write_new_json(output_path, receipt)
    print(json.dumps({"status": receipt["status"], "receipt": output_ref}, indent=2))
    return 0 if receipt["status"] == "pass_partial_pre_event_header_readiness_only" else 20


if __name__ == "__main__":
    raise SystemExit(main())
