#!/usr/bin/env python3
"""Reconcile four passing ArcGIS DEM receipts and advance to vertical-datum review."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterator

from m2_transfer_core import replace_json, sha256_file, write_new_json


ROOT = Path(__file__).resolve().parents[1]
INTAKE_PATH = ROOT / "contracts/m2-dem-intake.json"
VERIFICATION_PATH = ROOT / "contracts/m2-dem-offline-verification.json"
MILESTONE_PATH = ROOT / "contracts/milestone-002.json"
PROFILE_PATH = ROOT / "records/project-control-profile.json"
GOAL_PATH = ROOT / "records/long-term-goal.json"
AOI_PATH = ROOT / "config/aoi/approved-study-areas.geojson"
RECEIPT_ROOT = ROOT / "records/acquisition/dem-verification"
SUMMARY_PATH = ROOT / "records/acquisition/dem-verification-summary.json"
EXPECTED_SOURCE_IDS = ["M2-DEM-001", "M2-DEM-002", "M2-DEM-003", "M2-DEM-004"]


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return value


def serialized(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_value(value: object) -> str:
    return hashlib.sha256(serialized(value)).hexdigest()


def coordinate_pairs(value: Any) -> Iterator[tuple[float, float]]:
    if (
        isinstance(value, list)
        and len(value) >= 2
        and isinstance(value[0], (int, float))
        and isinstance(value[1], (int, float))
    ):
        yield float(value[0]), float(value[1])
        return
    if isinstance(value, list):
        for item in value:
            yield from coordinate_pairs(item)


def feature_bbox(feature: dict[str, Any]) -> list[float]:
    points = list(coordinate_pairs(feature.get("geometry", {}).get("coordinates")))
    if not points:
        raise ValueError(f"AOI has no coordinate pairs: {feature.get('id')}")
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return [min(xs), min(ys), max(xs), max(ys)]


def validate_pass_receipts(
    contract: dict[str, Any],
    intake: dict[str, Any],
    *,
    contract_sha: str | None = None,
    intake_sha: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    contract_sha = contract_sha or sha256_file(VERIFICATION_PATH)
    intake_sha = intake_sha or sha256_file(INTAKE_PATH)
    all_receipts = [load(path) | {"_path": path} for path in sorted(RECEIPT_ROOT.glob("*.json"))]
    passes = [receipt for receipt in all_receipts if receipt.get("status") == "pass_structural_only"]
    failures = [receipt for receipt in all_receipts if receipt.get("status") == "fail"]
    summaries: list[dict[str, Any]] = []
    intake_by_source = {asset["extensions"]["source_id"]: asset for asset in intake.get("assets", [])}
    contract_by_source = {asset["source_id"]: asset for asset in contract.get("assets", [])}
    if list(contract_by_source) != EXPECTED_SOURCE_IDS or list(intake_by_source) != EXPECTED_SOURCE_IDS:
        raise ValueError("contract or intake source order differs")
    for source_id in EXPECTED_SOURCE_IDS:
        matches = [receipt for receipt in passes if receipt.get("source_id") == source_id]
        if len(matches) != 1:
            raise ValueError(f"expected exactly one passing ArcGIS receipt for {source_id}")
        receipt = matches[0]
        path = receipt.pop("_path")
        asset = intake_by_source[source_id]
        expected = contract_by_source[source_id]
        stats = receipt.get("observed", {}).get("statistics", {})
        expected_cells = expected["expected_shape"][0] * expected["expected_shape"][1]
        checks = receipt.get("evaluation", {}).get("checks", {})
        if (
            receipt.get("asset_id") != expected["asset_id"]
            or receipt.get("contract_sha256") != contract_sha
            or receipt.get("active_intake_sha256") != intake_sha
            or receipt.get("transfer_receipt_ref") != asset["extensions"].get("successful_attempt_receipt")
            or receipt.get("transfer_receipt_sha256") != asset["extensions"].get("successful_attempt_receipt_sha256")
            or receipt.get("observed", {}).get("sha256") != asset["observed"].get("promoted_sha256")
            or receipt.get("observed", {}).get("size_bytes") != asset["observed"].get("promoted_size_bytes")
            or receipt.get("evaluation", {}).get("status") != "pass_structural_only"
            or receipt.get("evaluation", {}).get("failures") != []
            or any(result.get("status") != "pass" for result in checks.values())
            or receipt.get("custody_inventory_before") != receipt.get("custody_inventory_after")
            or stats.get("source") != "arcpy.RasterToNumPyArray_read_only_full_raster"
            or stats.get("total_cell_count") != expected_cells
            or stats.get("valid_cell_count") != expected_cells
            or stats.get("nodata_or_nonfinite_cell_count") != 0
            or receipt.get("claim_boundary", {}).get("structural_raster_fitness_established") is not True
            or receipt.get("claim_boundary", {}).get("full_raster_pixel_statistics_captured") is not True
            or receipt.get("claim_boundary", {}).get("valid_pixel_coverage_established") is not False
        ):
            raise ValueError(f"passing ArcGIS receipt differs for {source_id}")
        summaries.append({
            "source_id": source_id,
            "asset_id": expected["asset_id"],
            "receipt_ref": path.relative_to(ROOT).as_posix(),
            "receipt_sha256": sha256_file(path),
            "local_size_bytes": receipt["observed"]["size_bytes"],
            "local_sha256": receipt["observed"]["sha256"],
            "shape": receipt["observed"]["shape"],
            "crs_wkid": receipt["observed"]["crs_wkid"],
            "minimum": stats["minimum"],
            "maximum": stats["maximum"],
            "valid_cell_count": stats["valid_cell_count"],
            "nodata_or_nonfinite_cell_count": stats["nodata_or_nonfinite_cell_count"],
        })
    failure_summaries = [
        {
            "source_id": receipt.get("source_id"),
            "receipt_ref": receipt["_path"].relative_to(ROOT).as_posix(),
            "receipt_sha256": sha256_file(receipt["_path"]),
            "status": "fail_retained_superseded_as_data_result",
        }
        for receipt in failures
    ]
    return summaries, failure_summaries


def evaluate_aoi_coverage(contract: dict[str, Any], aois: dict[str, Any], asset_summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    required_ids = contract["mosaic_controls"]["required_aoi_ids"]
    features = {feature["properties"]["aoi_id"]: feature for feature in aois.get("features", [])}
    if list(features) != required_ids:
        raise ValueError("approved AOI order or identity differs")
    footprint = contract["mosaic_controls"]["expected_union_bbox_wgs84"]
    all_tiles_full_valid = all(item["nodata_or_nonfinite_cell_count"] == 0 for item in asset_summaries)
    results = []
    for aoi_id in required_ids:
        bounds = feature_bbox(features[aoi_id])
        within = bounds[0] >= footprint[0] and bounds[1] >= footprint[1] and bounds[2] <= footprint[2] and bounds[3] <= footprint[3]
        results.append({
            "aoi_id": aoi_id,
            "bbox_wgs84": bounds,
            "within_verified_four_tile_footprint": within,
            "all_footprint_tiles_full_finite_non_nodata": all_tiles_full_valid,
            "status": "pass_valid_coverage" if within and all_tiles_full_valid else "fail",
        })
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--completed-at-utc", required=True)
    args = parser.parse_args()
    if not args.completed_at_utc.endswith("Z"):
        raise SystemExit("--completed-at-utc must end in Z")
    if SUMMARY_PATH.exists():
        raise SystemExit(f"REFUSED: summary already exists: {SUMMARY_PATH}")

    intake = load(INTAKE_PATH)
    verification = load(VERIFICATION_PATH)
    milestone = load(MILESTONE_PATH)
    profile = load(PROFILE_PATH)
    goal = load(GOAL_PATH)
    aois = load(AOI_PATH)
    if verification.get("status") != "active_gate_ready_for_geotiff_verification":
        raise SystemExit("active DEM verification gate is not ready")
    if verification.get("inputs", {}).get("intake_contract_sha256") != sha256_file(INTAKE_PATH):
        raise SystemExit("active DEM verification intake binding differs")
    if any(asset.get("state") != "promoted" for asset in intake.get("assets", [])):
        raise SystemExit("all four DEM assets must be promoted")

    asset_summaries, failure_summaries = validate_pass_receipts(verification, intake)
    aoi_results = evaluate_aoi_coverage(verification, aois, asset_summaries)
    if any(result["status"] != "pass_valid_coverage" for result in aoi_results):
        raise SystemExit("approved AOI coverage did not pass")
    summary = {
        "schema_version": "1.0",
        "summary_id": "NEPAL-M2-DEM-GEOTIFF-VERIFICATION-SUMMARY-001",
        "status": "pass_structural_and_valid_aoi_coverage_vertical_datum_deferred",
        "completed_at_utc": args.completed_at_utc,
        "bindings": {
            "active_verification_ref": "contracts/m2-dem-offline-verification.json",
            "active_verification_sha256_before_completion": sha256_file(VERIFICATION_PATH),
            "active_intake_ref": "contracts/m2-dem-intake.json",
            "active_intake_sha256_before_completion": sha256_file(INTAKE_PATH),
            "approved_aoi_ref": "config/aoi/approved-study-areas.geojson",
            "approved_aoi_sha256": sha256_file(AOI_PATH),
            "completion_script_ref": "scripts/complete_m2_dem_verification.py",
            "completion_script_sha256": sha256_file(ROOT / "scripts/complete_m2_dem_verification.py"),
        },
        "passing_assets": asset_summaries,
        "retained_failed_attempts": failure_summaries,
        "aoi_coverage": aoi_results,
        "totals": {
            "passing_tile_count": len(asset_summaries),
            "retained_failed_attempt_count": len(failure_summaries),
            "verified_bytes": sum(item["local_size_bytes"] for item in asset_summaries),
            "finite_non_nodata_cells": sum(item["valid_cell_count"] for item in asset_summaries),
            "nodata_or_nonfinite_cells": sum(item["nodata_or_nonfinite_cell_count"] for item in asset_summaries),
        },
        "claim_boundary": {
            "exact_local_byte_identity_established": True,
            "arcgis_geotiff_structural_fitness_established": True,
            "approved_aoi_valid_pixel_coverage_established": True,
            "void_seam_artifact_review_established": False,
            "vertical_datum_route_established": False,
            "radar_processing_executed": False,
            "scientific_result_established": False,
        },
        "next_checkpoint": "M2-DEM-VERTICAL-DATUM-REVIEW",
    }
    if summary["totals"] != {"passing_tile_count": 4, "retained_failed_attempt_count": 2, "verified_bytes": 170302058, "finite_non_nodata_cells": 51840000, "nodata_or_nonfinite_cells": 0}:
        raise SystemExit("DEM aggregate totals differ")
    write_new_json(SUMMARY_PATH, summary)
    summary_sha = sha256_file(SUMMARY_PATH)

    for asset, verified in zip(intake["assets"], asset_summaries):
        asset["extensions"].update({
            "geotiff_verification_status": "pass_structural_and_full_tile_finite",
            "geotiff_verification_receipt": verified["receipt_ref"],
            "geotiff_verification_receipt_sha256": verified["receipt_sha256"],
        })
    intake["extensions"].update({
        "status": "active_geotiff_verified_vertical_datum_deferred",
        "dem_verification_summary_ref": SUMMARY_PATH.relative_to(ROOT).as_posix(),
        "dem_verification_summary_sha256": summary_sha,
    })
    new_intake_sha = sha256_value(intake)
    verification["inputs"]["intake_contract_sha256"] = new_intake_sha
    verification["status"] = "complete_structural_and_valid_coverage_vertical_datum_deferred"
    verification["result"] = {
        "summary_ref": SUMMARY_PATH.relative_to(ROOT).as_posix(),
        "summary_sha256": summary_sha,
        "next_checkpoint": "M2-DEM-VERTICAL-DATUM-REVIEW",
    }

    units = {unit["id"]: unit for unit in milestone["units"]}
    dem_verify = units["M2-DEM-VERIFY"]
    dem_verify.update({
        "status": "complete",
        "disposition": "pass",
        "gates": {
            "passing_tile_count": 4,
            "retained_failed_attempt_count": 2,
            "approved_aoi_valid_coverage": True,
            "summary_ref": SUMMARY_PATH.relative_to(ROOT).as_posix(),
            "summary_sha256": summary_sha,
        },
        "exit_condition_delta": {
            "expected": ["EXIT-201-VERIFIED-CUSTODY", "EXIT-202-PIXEL-AND-RIGHTS-QA"],
            "observed": ["EXIT-201-VERIFIED-CUSTODY", "EXIT-202-PIXEL-AND-RIGHTS-QA"],
            "decision_value": "enables_dependency",
            "rationale": "Four exact ArcGIS structural passes and full-tile finite scans cover every approved AOI; vertical-datum and radar-processing fitness remain separate.",
        },
    })
    next_action = "Review and explicitly resolve the EGM2008-to-ArcGIS-EGM96 vertical-datum route before any Sentinel-1 terrain correction; do not silently select GEOID or NONE."
    milestone["handoff"].update({"parallel_checkpoint": "M2-DEM-VERTICAL-DATUM-REVIEW", "parallel_next_action": next_action})
    profile["parallel_checkpoints"] = [{"checkpoint_id": "M2-DEM-VERTICAL-DATUM-REVIEW", "authority_ref": "records/source-gates/m2-dem-amendment-approval.json", "next_action": next_action}]
    goal["parallel_checkpoints"] = ["M2-DEM-VERTICAL-DATUM-REVIEW"]

    replace_json(INTAKE_PATH, intake, ".dem-verification-complete-intake-tmp")
    replace_json(VERIFICATION_PATH, verification, ".dem-verification-complete-contract-tmp")
    replace_json(MILESTONE_PATH, milestone, ".dem-verification-complete-milestone-tmp")
    replace_json(PROFILE_PATH, profile, ".dem-verification-complete-profile-tmp")
    replace_json(GOAL_PATH, goal, ".dem-verification-complete-goal-tmp")
    print(json.dumps({
        "status": summary["status"],
        "summary_ref": SUMMARY_PATH.relative_to(ROOT).as_posix(),
        "summary_sha256": summary_sha,
        "passing_tile_count": 4,
        "retained_failed_attempt_count": 2,
        "next_checkpoint": "M2-DEM-VERTICAL-DATUM-REVIEW",
    }, indent=2))


if __name__ == "__main__":
    main()
