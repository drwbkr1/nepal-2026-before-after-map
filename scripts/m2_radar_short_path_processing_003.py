#!/usr/bin/env python3
"""Short-path-only processing functions derived from the frozen M2 radar route."""

from __future__ import annotations

import argparse
import datetime as datetime_module
import hashlib
import json
import math
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

import numpy as np

from m2_radar_pixel_orbit_application_001_core import (
    ROUTE_ORDER,
    SOURCE_ORDER,
    RadarRouteError,
    copy_safe_exclusive,
    evaluate_route,
    execute_fixed_order,
    inventory_sha256,
    load_execution_plan,
    load_object,
    require_external_child,
    sha256_file,
    stable_inventory,
    verify_external_identities,
    write_new_json,
)
from pixel_qa_core import evaluate_registration


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REF = "config/qa/m2-radar-pixel-orbit-application-001-contract.json"
PUBLICATION_GATE_REF = "records/readiness/m2-radar-pixel-orbit-application-001-implementation-publication-gate.json"
FINAL_PREFLIGHT_REF = "records/readiness/m2-radar-pixel-orbit-application-001-final-preflight.json"
PROCESSING_ROOT_REF = "records/processing/radar-pixel-orbit-application-001"
TERMINAL_REF = "records/processing/m2-radar-pixel-orbit-application-001-terminal-reconciliation.json"
UTC_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
VALUE_FIELD = re.compile(r"^VALUE_(-?\d+)$", re.IGNORECASE)
TOKEN_PATTERN = re.compile(r"(?i)(?:bearer\s+)?eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")
WINDOWS_PATH = re.compile(r"(?i)[A-Z]:\\[^\s\"']+")


def now_utc() -> str:
    return datetime_module.datetime.now(datetime_module.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def repo_sha(ref: str) -> str:
    return sha256_file(ROOT / ref)


def publication_gate() -> dict[str, Any]:
    path = ROOT / PUBLICATION_GATE_REF
    if not path.is_file():
        raise RadarRouteError("implementation_publication_gate_missing")
    gate = load_object(path)
    if gate.get("status") != "pass_public_default_branch_ci_implementation_ready" or gate.get("public_ci_conclusion") != "success":
        raise RadarRouteError("implementation_publication_gate_not_pass")
    expected = {
        "implementation_contract_sha256": repo_sha(CONTRACT_REF),
        "core_sha256": repo_sha("scripts/m2_radar_pixel_orbit_application_001_core.py"),
        "runner_sha256": repo_sha("scripts/run_m2_radar_pixel_orbit_application_001.py"),
        "arcgis_validator_sha256": repo_sha("scripts/validate_m2_radar_pixel_orbit_application_001_arcgis.py"),
        "portable_test_sha256": repo_sha("tests/test_m2_radar_pixel_orbit_application_001.py"),
    }
    if any(gate.get("bindings", {}).get(key) != value for key, value in expected.items()):
        raise RadarRouteError("implementation_publication_gate_binding_mismatch")
    return gate


def arcgis_signature_status(arcpy: Any) -> dict[str, Any]:
    prefixes = {
        "ApplyOrbitCorrection_ia": "ApplyOrbitCorrection_ia(in_radar_data, {in_orbit_file}, {folder})",
        "RemoveThermalNoise_ia": "RemoveThermalNoise_ia(in_radar_data, out_radar_data",
        "ApplyRadiometricCalibration_ia": "ApplyRadiometricCalibration_ia(in_radar_data, out_radar_data",
        "ApplyRadiometricTerrainFlattening_ia": "ApplyRadiometricTerrainFlattening_ia(in_radar_data, out_radar_data, in_dem_raster",
        "ApplyGeometricTerrainCorrection_ia": "ApplyGeometricTerrainCorrection_ia(in_radar_data, out_radar_data",
        "ConvertSARUnits_ia": "ConvertSARUnits_ia(in_radar_data, out_radar_data",
    }
    usage = {name: arcpy.Usage(name) for name in prefixes}
    return {"usage": usage, "all_match": all(usage[name].startswith(prefix) for name, prefix in prefixes.items())}


def run_final_preflight(checked_at_utc: str) -> int:
    output = ROOT / FINAL_PREFLIGHT_REF
    if output.exists():
        raise RadarRouteError("final_preflight_collision")
    gate = publication_gate()
    plan = load_execution_plan(ROOT, CONTRACT_REF)
    contract = plan["contract"]
    data_root: Path = plan["data_root"]
    attempt_root = require_external_child(data_root, Path(contract["attempt"]["external_attempt_root"]), must_exist=False)
    collisions = [str(path) for path in [attempt_root, ROOT / TERMINAL_REF] if path.exists()]
    collisions.extend(
        str(ROOT / PROCESSING_ROOT_REF / name)
        for source_id in SOURCE_ORDER
        for name in (f"{source_id.lower()}-real-001-started.json", f"{source_id.lower()}-real-001-terminal.json")
        if (ROOT / PROCESSING_ROOT_REF / name).exists()
    )
    collisions.extend(
        str(ROOT / PROCESSING_ROOT_REF / name)
        for route_id in ROUTE_ORDER
        for name in (f"{route_id.lower()}-real-001-started.json", f"{route_id.lower()}-real-001-terminal.json")
        if (ROOT / PROCESSING_ROOT_REF / name).exists()
    )
    free_bytes = shutil.disk_usage(data_root).free
    path_presence = {
        "source_paths_present": all(Path(item["safe_root"]).is_dir() and Path(item["external_manifest_path"]).is_file() for item in plan["sources"]),
        "orbit_paths_present": all(Path(item["custody_path"]).is_file() for item in plan["orbits"].values()),
        "dem_paths_present": all(Path(item["destination_path"]).is_file() for item in plan["dems"]),
    }
    os.environ.setdefault("GDAL_PAM_ENABLED", "NO")
    import arcpy  # type: ignore[import-not-found]

    signatures = arcgis_signature_status(arcpy)
    install = arcpy.GetInstallInfo()
    checks = {
        "implementation_publication_gate_passed": True,
        "exact_contract_and_repo_bindings_passed": True,
        "external_data_root_matches_project_sibling": True,
        "attempt_and_receipt_collision_count": len(collisions),
        "free_bytes": free_bytes,
        "minimum_free_bytes": contract["attempt"]["minimum_free_space_bytes"],
        **path_presence,
        "image_analyst": arcpy.CheckExtension("ImageAnalyst"),
        "spatial_analyst": arcpy.CheckExtension("Spatial"),
        "tool_signatures_match": signatures["all_match"],
    }
    passed = (
        not collisions
        and free_bytes >= contract["attempt"]["minimum_free_space_bytes"]
        and all(path_presence.values())
        and checks["image_analyst"] == "Available"
        and checks["spatial_analyst"] == "Available"
        and signatures["all_match"]
    )
    receipt = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-001-FINAL-PREFLIGHT",
        "checked_at_utc": checked_at_utc,
        "status": "pass_final_no_content_preflight" if passed else "block_final_no_content_preflight",
        "bindings": {
            "implementation_contract_ref": CONTRACT_REF,
            "implementation_contract_sha256": plan["contract_sha256"],
            "implementation_publication_gate_ref": PUBLICATION_GATE_REF,
            "implementation_publication_gate_sha256": repo_sha(PUBLICATION_GATE_REF),
            "implementation_commit_sha": gate["implementation_commit_sha"],
            "public_ci_run_id": gate["public_ci_run_id"],
        },
        "runtime": {
            "product": install.get("ProductName"),
            "version": install.get("Version"),
            "license_level": arcpy.ProductInfo(),
        },
        "checks": checks,
        "collisions": collisions,
        "assertions": {
            "project_data_content_read": False,
            "project_file_hash_computed": False,
            "project_raster_or_xml_opened": False,
            "external_custody_mutated": False,
            "attempt_root_created": False,
            "orbit_application_executed": False,
            "radar_pixel_processing_executed": False,
            "network_request_performed": False,
            "credential_value_read": False,
            "baseline_or_change_analysis_executed": False,
            "scientific_result_established": False,
        },
        "next_action": "Execute the exact one-attempt fixed-order route only if this receipt passes." if passed else "Stop without project-data content access.",
    }
    write_new_json(output, receipt)
    print(json.dumps({"status": receipt["status"], "receipt": FINAL_PREFLIGHT_REF}, indent=2))
    return 0 if passed else 12


def create_dem_mosaic(arcpy: Any, plan: dict[str, Any], attempt_root: Path) -> Path:
    output_dir = attempt_root / "dem"
    output_dir.mkdir()
    output = output_dir / "ellipsoidal_dem_mosaic.tif"
    paths = [item["destination_path"] for item in plan["dems"]]
    arcpy.management.MosaicToNewRaster(
        paths,
        str(output_dir),
        output.name,
        arcpy.SpatialReference(4326),
        "32_BIT_FLOAT",
        None,
        1,
        "FIRST",
        "FIRST",
    )
    description = arcpy.Describe(str(output))
    if int(description.spatialReference.factoryCode) != 4326 or int(description.bandCount) != 1:
        raise RadarRouteError("attempt_dem_mosaic_invalid")
    return output


def create_analysis_support(arcpy: Any, plan: dict[str, Any], attempt_root: Path) -> dict[str, Any]:
    contract = plan["contract"]
    aoi = load_object(ROOT / contract["bindings"]["approved_aoi_projected_ref"])
    extent = aoi["projectMetadata"]["extent"]
    cell = float(contract["analysis_grid"]["cell_size_m"])
    buffer_m = float(contract["analysis_grid"]["processing_buffer_m"])
    xmin = math.floor((float(extent["xmin"]) - buffer_m) / cell) * cell
    ymin = math.floor((float(extent["ymin"]) - buffer_m) / cell) * cell
    xmax = math.ceil((float(extent["xmax"]) + buffer_m) / cell) * cell
    ymax = math.ceil((float(extent["ymax"]) + buffer_m) / cell) * cell
    support = attempt_root / "support"
    support.mkdir()
    gdb = support / "qa.gdb"
    arcpy.management.CreateFileGDB(str(support), gdb.name)
    aoi_fc = gdb / "ApprovedStudyAreas"
    arcpy.conversion.JSONToFeatures(str(ROOT / contract["bindings"]["approved_aoi_projected_ref"]), str(aoi_fc))
    snap = support / "snap_10m.tif"
    raster = arcpy.NumPyArrayToRaster(np.zeros((2, 2), dtype=np.uint8), arcpy.Point(xmin, ymin), cell, cell)
    raster.save(str(snap))
    arcpy.management.DefineProjection(str(snap), arcpy.SpatialReference(32645))
    return {
        "gdb": gdb,
        "aoi_fc": aoi_fc,
        "snap": snap,
        "extent": f"{xmin} {ymin} {xmax} {ymax}",
        "xmin": xmin,
        "ymin": ymin,
        "xmax": xmax,
        "ymax": ymax,
        "cell_size_m": cell,
    }


def raster_identity(path: Path) -> dict[str, Any]:
    if path.is_file():
        return {"kind": "file", "size_bytes": path.stat().st_size, "sha256": sha256_file(path)}
    items = stable_inventory(path)
    return {
        "kind": "directory_dataset",
        "file_count": len(items),
        "total_bytes": sum(item["size_bytes"] for item in items),
        "inventory_sha256": inventory_sha256(items),
    }


def describe_raster(arcpy: Any, path: Path) -> dict[str, Any]:
    description = arcpy.Describe(str(path))
    extent = description.extent
    return {
        "wkid": int(description.spatialReference.factoryCode),
        "band_count": int(description.bandCount),
        "cell_size_x": float(description.meanCellWidth),
        "cell_size_y": float(description.meanCellHeight),
        "extent": {"xmin": float(extent.XMin), "ymin": float(extent.YMin), "xmax": float(extent.XMax), "ymax": float(extent.YMax)},
    }


def project_to_grid(arcpy: Any, source: Path, destination: Path, support: dict[str, Any], *, categorical: bool) -> None:
    method = "NEAREST" if categorical else "BILINEAR"
    with arcpy.EnvManager(
        outputCoordinateSystem=arcpy.SpatialReference(32645),
        snapRaster=str(support["snap"]),
        cellSize=support["cell_size_m"],
        extent=support["extent"],
        resamplingMethod=method,
        overwriteOutput=False,
    ):
        arcpy.management.ProjectRaster(
            str(source),
            str(destination),
            arcpy.SpatialReference(32645),
            method,
            support["cell_size_m"],
        )


def source_receipt_ref(source_id: str, kind: str) -> str:
    return f"{PROCESSING_ROOT_REF}/{source_id.lower()}-real-001-{kind}.json"


def safe_error(exc: BaseException, replacements: tuple[Path, ...] = ()) -> dict[str, Any]:
    message = str(exc).replace("\r", " ").replace("\n", " ")
    message = TOKEN_PATTERN.sub("[REDACTED_TOKEN]", message)
    for item in replacements:
        message = message.replace(str(item), "[REDACTED_PATH]")
    message = WINDOWS_PATH.sub("[REDACTED_PATH]", message)
    return {
        "failure_type": type(exc).__name__,
        "failure_code": getattr(exc, "code", "unexpected_processing_failure"),
        "failure_message": message[:4000],
    }


def source_output_root(plan: dict[str, Any], attempt_root: Path, source_id: str) -> Path:
    aliases = plan.get("contract", {}).get("short_path_source_aliases")
    if isinstance(aliases, dict):
        alias = aliases.get(source_id)
        if not isinstance(alias, str) or not re.fullmatch(r"[1-9]", alias):
            raise RadarRouteError("short_path_source_alias_missing_or_invalid", source_id)
        return attempt_root / "s" / alias
    return attempt_root / "sources" / source_id.lower()


def source_receipt_path(plan: dict[str, Any], attempt_root: Path, source_id: str, kind: str) -> tuple[Path, str]:
    if plan.get("contract", {}).get("attempt_local_receipts") is True:
        relative = Path("receipts") / "sources" / f"{source_id.lower()}-{kind}.json"
        return attempt_root / relative, relative.as_posix()
    ref = source_receipt_ref(source_id, kind)
    return ROOT / ref, ref


def route_receipt_path(plan: dict[str, Any], attempt_root: Path, route_id: str, kind: str) -> tuple[Path, str]:
    if plan.get("contract", {}).get("attempt_local_receipts") is True:
        relative = Path("receipts") / "routes" / f"{route_id.lower()}-{kind}.json"
        return attempt_root / relative, relative.as_posix()
    ref = route_receipt_ref(route_id, kind)
    return ROOT / ref, ref


def process_source(
    *,
    arcpy: Any,
    plan: dict[str, Any],
    identities_before: dict[str, Any],
    attempt_root: Path,
    dem_mosaic: Path,
    support: dict[str, Any],
    source_id: str,
    started_at_utc: str,
) -> dict[str, Any]:
    source = next(item for item in plan["sources"] if item["source_id"] == source_id)
    orbit_id = source["orbit_source_id"]
    orbit = plan["orbits"][orbit_id]
    started_path, started_ref = source_receipt_path(plan, attempt_root, source_id, "started")
    terminal_path, terminal_ref = source_receipt_path(plan, attempt_root, source_id, "terminal")
    source_root = source_output_root(plan, attempt_root, source_id)
    receipt_namespace = plan.get("contract", {}).get(
        "receipt_namespace", "RADAR-PIXEL-ORBIT-APPLICATION-001"
    )
    write_new_json(
        started_path,
        {
            "schema_version": "1.0",
            "receipt_id": f"NEPAL-{source_id}-{receipt_namespace}-STARTED",
            "status": "started_single_attempt_reserved_before_source_content_copy",
            "started_at_utc": started_at_utc,
            "source_id": source_id,
            "orbit_source_id": orbit_id,
            "attempt_id": plan["contract"]["attempt"]["attempt_id"],
            "implementation_contract_sha256": plan["contract_sha256"],
            "automatic_retry_authorized": False,
        },
    )
    source_root.mkdir(parents=True)
    copied_safe = source_root / source["exact_product_id"]
    try:
        copy_result = copy_safe_exclusive(Path(source["safe_root"]), copied_safe)
        manifest = copied_safe / "manifest.safe"
        if not manifest.is_file():
            raise RadarRouteError("copied_manifest_safe_missing", source_id)
        orbit_path = Path(orbit["custody_path"])
        arcpy.ia.ApplyOrbitCorrection(str(manifest), str(orbit_path))
        orbit_messages = arcpy.GetMessages()

        thermal = source_root / "thermal_noise_removed.crf"
        beta = source_root / "beta0_linear.crf"
        gamma_slant = source_root / "gamma0_linear_slant.crf"
        scattering = source_root / "scattering_area.crf"
        distortion = source_root / "geometric_distortion.crf"
        native_mask = source_root / "geometric_distortion_mask_slant.crf"
        gamma_gtc_raw = source_root / "gamma0_linear_gtc_raw.crf"
        db_gtc_raw = source_root / "gamma0_db_gtc_raw.crf"
        mask_gtc_raw = source_root / "geometric_distortion_mask_gtc_raw.crf"
        gamma_final = source_root / "gamma0_linear_epsg32645_10m.crf"
        db_final = source_root / "gamma0_db_epsg32645_10m.crf"
        mask_final = source_root / "geometric_distortion_mask_epsg32645_10m.crf"

        arcpy.ia.RemoveThermalNoise(str(manifest), str(thermal), "VV;VH")
        arcpy.ia.ApplyRadiometricCalibration(str(thermal), str(beta), "VV;VH", "BETA_NOUGHT")
        arcpy.ia.ApplyRadiometricTerrainFlattening(
            str(beta),
            str(gamma_slant),
            str(dem_mosaic),
            "NONE",
            "VV;VH",
            "GAMMA_NOUGHT",
            str(scattering),
            str(distortion),
            str(native_mask),
        )
        with arcpy.EnvManager(snapRaster=str(support["snap"]), cellSize=10.0, resamplingMethod="BILINEAR", overwriteOutput=False):
            arcpy.ia.ApplyGeometricTerrainCorrection(str(gamma_slant), str(gamma_gtc_raw), "VV;VH", str(dem_mosaic), "NONE")
        arcpy.ia.ConvertSARUnits(str(gamma_gtc_raw), str(db_gtc_raw), "LINEAR_TO_DB")
        with arcpy.EnvManager(snapRaster=str(support["snap"]), cellSize=10.0, resamplingMethod="NEAREST", overwriteOutput=False):
            arcpy.ia.ApplyGeometricTerrainCorrection(str(native_mask), str(mask_gtc_raw), "#", str(dem_mosaic), "NONE")
        project_to_grid(arcpy, gamma_gtc_raw, gamma_final, support, categorical=False)
        project_to_grid(arcpy, db_gtc_raw, db_final, support, categorical=False)
        project_to_grid(arcpy, mask_gtc_raw, mask_final, support, categorical=True)

        gamma_description = describe_raster(arcpy, gamma_final)
        db_description = describe_raster(arcpy, db_final)
        mask_description = describe_raster(arcpy, mask_final)
        if (
            gamma_description["wkid"] != 32645
            or gamma_description["band_count"] != 2
            or abs(gamma_description["cell_size_x"] - 10.0) > 1e-6
            or abs(gamma_description["cell_size_y"] - 10.0) > 1e-6
            or db_description["wkid"] != 32645
            or db_description["band_count"] != 2
            or mask_description["wkid"] != 32645
            or mask_description["band_count"] != 1
        ):
            raise RadarRouteError("source_output_grid_or_band_mismatch", source_id)
        original_now = stable_inventory(Path(source["safe_root"]))
        if inventory_sha256(original_now) != identities_before["sources"][source_id]["inventory_sha256"]:
            raise RadarRouteError("original_source_inventory_changed", source_id)
        receipt = {
            "schema_version": "1.0",
            "receipt_id": f"NEPAL-{source_id}-{receipt_namespace}-TERMINAL",
            "status": "pass_source_qa_only",
            "completed_at_utc": now_utc(),
            "source_id": source_id,
            "orbit_source_id": orbit_id,
            "orbit_type": "AUX_RESORB",
            "bindings": {
                "implementation_contract_sha256": plan["contract_sha256"],
                "source_inventory_sha256": identities_before["sources"][source_id]["inventory_sha256"],
                "orbit_sha256": orbit["custody_sha256"],
                "dem_sha256_by_source": {item["source_id"]: item["ellipsoidal_derivative_sha256"] for item in plan["dems"]},
            },
            "copy": copy_result,
            "orbit_application": {"explicit_orbit_file": orbit["custody_path"], "messages": orbit_messages[-4000:]},
            "outputs": {
                "linear_gamma_nought": {"path": str(gamma_final), "description": gamma_description, "identity": raster_identity(gamma_final)},
                "db_display_candidate": {"path": str(db_final), "description": db_description, "identity": raster_identity(db_final)},
                "native_distortion_mask": {"path": str(mask_final), "description": mask_description, "identity": raster_identity(mask_final)},
            },
            "assertions": {
                "source_copy_used_for_orbit_application": True,
                "explicit_exact_resorb_used": True,
                "original_materialized_safe_unchanged": True,
                "geoid_parameter_none": True,
                "linear_gamma_nought_retained": True,
                "despeckle_applied": False,
                "network_request_performed": False,
                "credential_value_read": False,
                "baseline_or_change_analysis_executed": False,
                "scientific_admission_authorized": False,
            },
        }
        write_new_json(terminal_path, receipt)
        return {"source_id": source_id, "status": receipt["status"], "receipt_ref": terminal_ref, "receipt_sha256": sha256_file(terminal_path)}
    except Exception as exc:
        failure = {
            "schema_version": "1.0",
            "receipt_id": f"NEPAL-{source_id}-{receipt_namespace}-TERMINAL",
            "status": "failed_source_execution_no_retry",
            "completed_at_utc": now_utc(),
            "source_id": source_id,
            "orbit_source_id": orbit_id,
            **safe_error(exc, (attempt_root, Path(plan["data_root"]))),
            "assertions": {
                "attempt_consumed": True,
                "automatic_retry_performed": False,
                "later_source_started": False,
                "network_request_performed_by_runner": False,
                "credential_value_read": False,
                "baseline_or_change_analysis_executed": False,
                "scientific_admission_authorized": False,
            },
        }
        write_new_json(terminal_path, failure)
        return {"source_id": source_id, "status": failure["status"], "receipt_ref": terminal_ref, "receipt_sha256": sha256_file(terminal_path)}


def make_band_layer(arcpy: Any, path: Path, name: str, band: int = 1) -> Any:
    result = arcpy.management.MakeRasterLayer(str(path), name, band_index=str(band))
    return arcpy.Raster(result.getOutput(0))


def mosaic_route_raster(
    arcpy: Any,
    inputs: list[Path],
    output: Path,
    *,
    bands: int,
    categorical: bool,
    support: dict[str, Any],
) -> None:
    pixel_type = "8_BIT_UNSIGNED" if categorical else "32_BIT_FLOAT"
    method = "NEAREST" if categorical else "BILINEAR"
    with arcpy.EnvManager(
        outputCoordinateSystem=arcpy.SpatialReference(32645),
        snapRaster=str(support["snap"]),
        cellSize=10.0,
        extent=support["extent"],
        resamplingMethod=method,
        overwriteOutput=False,
    ):
        arcpy.management.MosaicToNewRaster(
            [str(path) for path in inputs],
            str(output.parent),
            output.name,
            arcpy.SpatialReference(32645),
            pixel_type,
            10.0,
            bands,
            "FIRST",
            "FIRST",
        )


def route_receipt_ref(route_id: str, kind: str) -> str:
    return f"{PROCESSING_ROOT_REF}/{route_id.lower()}-real-001-{kind}.json"


def aoi_bounds(arcpy: Any, aoi_fc: Path) -> dict[str, tuple[float, float, float, float]]:
    result: dict[str, tuple[float, float, float, float]] = {}
    for aoi_id, geometry in arcpy.da.SearchCursor(str(aoi_fc), ["AOI_ID", "SHAPE@"]):
        extent = geometry.extent
        result[str(aoi_id)] = (float(extent.XMin), float(extent.YMin), float(extent.XMax), float(extent.YMax))
    return result


def tabulate_radar_aoi(
    arcpy: Any,
    *,
    aoi_fc: Path,
    mask: Path,
    table: Path,
    pixel_contract: dict[str, Any],
) -> tuple[list[dict[str, Any]], bool]:
    arcpy.sa.TabulateArea(str(aoi_fc), "AOI_ID", str(mask), "Value", str(table), 10.0, "CLASSES_AS_FIELDS")
    area_by_aoi = {str(aoi_id): float(area) for aoi_id, area in arcpy.da.SearchCursor(str(aoi_fc), ["AOI_ID", "SHAPE@AREA"])}
    fields: dict[str, int] = {}
    for field in arcpy.ListFields(str(table)):
        matched = VALUE_FIELD.match(field.name)
        if matched:
            fields[field.name] = int(matched.group(1))
    if not fields:
        raise RadarRouteError("tabulate_area_no_class_fields")
    reasons = {int(key): value for key, value in pixel_contract["radar_mask"]["excluded_classes"].items()}
    observations: list[dict[str, Any]] = []
    unknown = False
    cursor_fields = ["AOI_ID", *fields]
    for row in arcpy.da.SearchCursor(str(table), cursor_fields):
        aoi_id = str(row[0])
        areas = {fields[field]: float(value or 0.0) for field, value in zip(cursor_fields[1:], row[1:])}
        valid_area = areas.get(1, 0.0)
        excluded: dict[str, float] = {}
        for value, area in areas.items():
            if value == 1 or area == 0:
                continue
            reason = reasons.get(value)
            if reason is None:
                reason = f"unknown_radar_mask_class_{value}"
                unknown = True
            excluded[reason] = excluded.get(reason, 0.0) + area
        observations.append(
            {
                "aoi_id": aoi_id,
                "aoi_area_m2": area_by_aoi[aoi_id],
                "covered_area_m2": sum(areas.values()),
                "valid_area_m2": valid_area,
                "excluded_area_by_reason_m2": excluded,
            }
        )
    return sorted(observations, key=lambda item: item["aoi_id"]), unknown


def grid_for_raster(arcpy: Any, path: Path) -> dict[str, Any]:
    description = arcpy.Describe(str(path))
    extent = description.extent
    return {
        "wkid": int(description.spatialReference.factoryCode),
        "cell_size_x": float(description.meanCellWidth),
        "cell_size_y": float(description.meanCellHeight),
        "origin_x": float(extent.XMin),
        "origin_y": float(extent.YMin),
        "xmin": float(extent.XMin),
        "ymin": float(extent.YMin),
        "xmax": float(extent.XMax),
        "ymax": float(extent.YMax),
        "rotation_degrees": 0.0,
    }


def _correlation(left: np.ndarray, right: np.ndarray, valid: np.ndarray, minimum_count: int) -> float | None:
    if int(valid.sum()) < minimum_count:
        return None
    x = left[valid].astype(np.float64)
    y = right[valid].astype(np.float64)
    x -= x.mean()
    y -= y.mean()
    denominator = float(np.sqrt(np.dot(x, x) * np.dot(y, y)))
    if not math.isfinite(denominator) or denominator <= 0:
        return None
    result = float(np.dot(x, y) / denominator)
    return result if math.isfinite(result) else None


def _parabolic(left: float | None, center: float, right: float | None) -> float:
    if left is None or right is None:
        return 0.0
    denominator = left - 2.0 * center + right
    if abs(denominator) < 1e-12:
        return 0.0
    return max(-0.5, min(0.5, 0.5 * (left - right) / denominator))


def raster_window(
    arcpy: Any,
    raster: Any,
    *,
    xmin: float,
    ymax: float,
    cell_size: float,
    row_start: int,
    column_start: int,
    rows: int,
    columns: int,
    nodata: float,
) -> np.ndarray:
    lower_left = arcpy.Point(
        xmin + column_start * cell_size,
        ymax - (row_start + rows) * cell_size,
    )
    return arcpy.RasterToNumPyArray(
        raster,
        lower_left_corner=lower_left,
        ncols=columns,
        nrows=rows,
        nodata_to_value=nodata,
    )


def measure_stable_registration_windowed(
    arcpy: Any,
    *,
    before_path: Path,
    after_path: Path,
    pair_mask: Path,
    overview_bbox: tuple[float, float, float, float],
    exclusion_bboxes: list[tuple[float, float, float, float]],
    settings: dict[str, Any],
    pixel_contract: dict[str, Any],
) -> dict[str, Any]:
    description = arcpy.Describe(str(before_path))
    rows = int(description.height)
    columns = int(description.width)
    extent = description.extent
    cell = float(description.meanCellWidth)
    if abs(cell - float(description.meanCellHeight)) > 1e-6:
        raise RadarRouteError("registration_grid_non_square")
    radius = int(settings["patch_radius_pixels"])
    search = int(settings["search_radius_pixels"])
    margin = radius + search + 1
    if rows <= 2 * margin or columns <= 2 * margin:
        decision = evaluate_registration(
            stable_control_pair_count=None,
            rmse_pixels=None,
            bias_x_pixels=None,
            bias_y_pixels=None,
            contract=pixel_contract,
        )
        return {
            **decision,
            "candidate_count": 0,
            "accepted_control_count": 0,
            "rejected_counts": {"insufficient_raster_size": 1},
            "controls": [],
            "method": "deterministic windowed VV normalized local cross-correlation outside buffered event AOIs",
        }

    before_name = f"registration_before_{hashlib.sha256(str(before_path).encode()).hexdigest()[:10]}"
    after_name = f"registration_after_{hashlib.sha256(str(after_path).encode()).hexdigest()[:10]}"
    before_raster = make_band_layer(arcpy, before_path, before_name, 1)
    after_raster = make_band_layer(arcpy, after_path, after_name, 1)
    mask_raster = arcpy.Raster(str(pair_mask))
    candidate_rows = np.linspace(margin, rows - margin - 1, int(settings["candidate_grid_rows"]), dtype=int)
    candidate_columns = np.linspace(margin, columns - margin - 1, int(settings["candidate_grid_columns"]), dtype=int)
    required = int(math.ceil((2 * radius + 1) ** 2 * float(settings["minimum_pair_valid_fraction"])))
    accepted: list[dict[str, Any]] = []
    rejected = {"outside_overview": 0, "event_exclusion": 0, "insufficient_valid": 0, "low_texture": 0, "low_correlation": 0}
    buffer_m = float(settings["event_aoi_exclusion_buffer_m"])
    expanded_size = 2 * (radius + search) + 1
    base_size = 2 * radius + 1
    try:
        for row in candidate_rows:
            y = float(extent.YMax) - (float(row) + 0.5) * cell
            for column in candidate_columns:
                x = float(extent.XMin) + (float(column) + 0.5) * cell
                if not (overview_bbox[0] <= x <= overview_bbox[2] and overview_bbox[1] <= y <= overview_bbox[3]):
                    rejected["outside_overview"] += 1
                    continue
                if any(xmin - buffer_m <= x <= xmax + buffer_m and ymin - buffer_m <= y <= ymax + buffer_m for xmin, ymin, xmax, ymax in exclusion_bboxes):
                    rejected["event_exclusion"] += 1
                    continue
                before = raster_window(
                    arcpy,
                    before_raster,
                    xmin=float(extent.XMin),
                    ymax=float(extent.YMax),
                    cell_size=cell,
                    row_start=int(row) - radius,
                    column_start=int(column) - radius,
                    rows=base_size,
                    columns=base_size,
                    nodata=-9999.0,
                ).astype(np.float32)
                after = raster_window(
                    arcpy,
                    after_raster,
                    xmin=float(extent.XMin),
                    ymax=float(extent.YMax),
                    cell_size=cell,
                    row_start=int(row) - radius - search,
                    column_start=int(column) - radius - search,
                    rows=expanded_size,
                    columns=expanded_size,
                    nodata=-9999.0,
                ).astype(np.float32)
                masks = raster_window(
                    arcpy,
                    mask_raster,
                    xmin=float(extent.XMin),
                    ymax=float(extent.YMax),
                    cell_size=cell,
                    row_start=int(row) - radius - search,
                    column_start=int(column) - radius - search,
                    rows=expanded_size,
                    columns=expanded_size,
                    nodata=-9999.0,
                ) == 1
                base_valid = masks[search:search + base_size, search:search + base_size]
                base_valid &= np.isfinite(before) & (before != -9999.0)
                if int(base_valid.sum()) < required:
                    rejected["insufficient_valid"] += 1
                    continue
                correlations: dict[tuple[int, int], float | None] = {}
                for dy in range(-search, search + 1):
                    for dx in range(-search, search + 1):
                        row_offset = search + dy
                        column_offset = search + dx
                        shifted = after[row_offset:row_offset + base_size, column_offset:column_offset + base_size]
                        shifted_valid = masks[row_offset:row_offset + base_size, column_offset:column_offset + base_size]
                        valid = base_valid & shifted_valid & np.isfinite(shifted) & (shifted != -9999.0)
                        if int(valid.sum()) < required:
                            correlations[(dx, dy)] = None
                        elif float(np.std(before[valid])) <= float(settings["minimum_patch_standard_deviation"]) or float(np.std(shifted[valid])) <= float(settings["minimum_patch_standard_deviation"]):
                            correlations[(dx, dy)] = None
                        else:
                            correlations[(dx, dy)] = _correlation(before, shifted, valid, required)
                usable = [(value, dx, dy) for (dx, dy), value in correlations.items() if value is not None]
                if not usable:
                    rejected["low_texture"] += 1
                    continue
                peak, dx, dy = max(usable, key=lambda item: (item[0], -abs(item[1]) - abs(item[2]), -abs(item[1]), -abs(item[2])))
                if peak < float(settings["minimum_correlation"]):
                    rejected["low_correlation"] += 1
                    continue
                accepted.append(
                    {
                        "x": x,
                        "y": y,
                        "shift_x_pixels": dx + _parabolic(correlations.get((dx - 1, dy)), peak, correlations.get((dx + 1, dy))),
                        "shift_y_pixels": dy + _parabolic(correlations.get((dx, dy - 1)), peak, correlations.get((dx, dy + 1))),
                        "correlation": peak,
                    }
                )
    finally:
        arcpy.management.Delete(before_name)
        arcpy.management.Delete(after_name)

    if accepted:
        shifts_x = np.array([item["shift_x_pixels"] for item in accepted], dtype=np.float64)
        shifts_y = np.array([item["shift_y_pixels"] for item in accepted], dtype=np.float64)
        rmse = float(np.sqrt(np.mean(shifts_x ** 2 + shifts_y ** 2)))
        bias_x = float(np.mean(shifts_x))
        bias_y = float(np.mean(shifts_y))
    else:
        rmse = bias_x = bias_y = None
    decision = evaluate_registration(
        stable_control_pair_count=len(accepted),
        rmse_pixels=rmse,
        bias_x_pixels=bias_x,
        bias_y_pixels=bias_y,
        contract=pixel_contract,
    )
    return {
        **decision,
        "candidate_count": int(len(candidate_rows) * len(candidate_columns)),
        "accepted_control_count": len(accepted),
        "rejected_counts": rejected,
        "controls": accepted,
        "method": "deterministic windowed VV normalized local cross-correlation outside buffered event AOIs",
    }


def evaluate_same_date_seam_windowed(
    arcpy: Any,
    left_path: Path,
    right_path: Path,
    *,
    block_size: int = 1024,
    maximum_samples_per_block: int = 10_000,
) -> dict[str, Any]:
    description = arcpy.Describe(str(left_path))
    right_description = arcpy.Describe(str(right_path))
    if int(description.width) != int(right_description.width) or int(description.height) != int(right_description.height):
        raise RadarRouteError("seam_grid_shape_mismatch")
    cell = float(description.meanCellWidth)
    extent = description.extent
    left_name = f"seam_left_{hashlib.sha256(str(left_path).encode()).hexdigest()[:10]}"
    right_name = f"seam_right_{hashlib.sha256(str(right_path).encode()).hexdigest()[:10]}"
    left_raster = make_band_layer(arcpy, left_path, left_name, 1)
    right_raster = make_band_layer(arcpy, right_path, right_name, 1)
    valid_count = 0
    samples: list[np.ndarray] = []
    try:
        for row_start in range(0, int(description.height), block_size):
            rows = min(block_size, int(description.height) - row_start)
            for column_start in range(0, int(description.width), block_size):
                columns = min(block_size, int(description.width) - column_start)
                left = raster_window(arcpy, left_raster, xmin=float(extent.XMin), ymax=float(extent.YMax), cell_size=cell, row_start=row_start, column_start=column_start, rows=rows, columns=columns, nodata=-9999.0).astype(np.float32)
                right = raster_window(arcpy, right_raster, xmin=float(extent.XMin), ymax=float(extent.YMax), cell_size=cell, row_start=row_start, column_start=column_start, rows=rows, columns=columns, nodata=-9999.0).astype(np.float32)
                valid = np.isfinite(left) & np.isfinite(right) & (left > 0) & (right > 0) & (left != -9999.0) & (right != -9999.0)
                block_count = int(valid.sum())
                valid_count += block_count
                if block_count:
                    differences = np.abs(left[valid].astype(np.float64) - right[valid].astype(np.float64))
                    stride = max(1, int(math.ceil(differences.size / maximum_samples_per_block)))
                    samples.append(differences[::stride][:maximum_samples_per_block])
    finally:
        arcpy.management.Delete(left_name)
        arcpy.management.Delete(right_name)
    if valid_count == 0:
        return {
            "status": "defer",
            "overlap_valid_pixel_count": 0,
            "sampled_pixel_count": 0,
            "median_absolute_difference": None,
            "p95_absolute_difference": None,
            "method": "deterministic block-stride sample over exact valid-overlap count",
        }
    combined = np.concatenate(samples)
    return {
        "status": "pass_qa_only",
        "overlap_valid_pixel_count": valid_count,
        "sampled_pixel_count": int(combined.size),
        "median_absolute_difference": float(np.median(combined)),
        "p95_absolute_difference": float(np.percentile(combined, 95)),
        "threshold_applied": False,
        "method": "deterministic block-stride sample over exact valid-overlap count",
    }


def process_route(
    *,
    arcpy: Any,
    plan: dict[str, Any],
    attempt_root: Path,
    support: dict[str, Any],
    route_id: str,
    started_at_utc: str,
) -> dict[str, Any]:
    started_path, started_ref = route_receipt_path(plan, attempt_root, route_id, "started")
    terminal_path, terminal_ref = route_receipt_path(plan, attempt_root, route_id, "terminal")
    receipt_namespace = plan.get("contract", {}).get("receipt_namespace", "RADAR-PIXEL-QA-001")
    write_new_json(
        started_path,
        {
            "schema_version": "1.0",
            "receipt_id": f"NEPAL-{route_id}-{receipt_namespace}-STARTED",
            "status": "started_single_route_evaluation_attempt",
            "started_at_utc": started_at_utc,
            "route_id": route_id,
            "implementation_contract_sha256": plan["contract_sha256"],
            "automatic_retry_authorized": False,
        },
    )
    route_dir = attempt_root / "routes" / route_id.lower()
    route_dir.mkdir(parents=True)
    pairs = {item["pair_id"]: item for item in load_object(ROOT / plan["contract"]["bindings"]["pair_plan_ref"])["pairs"]}
    pair = pairs[route_id]
    try:
        def paths(source_ids: list[str], name: str) -> list[Path]:
            return [source_output_root(plan, attempt_root, source_id) / name for source_id in source_ids]

        before_ids = pair["before_source_ids"]
        after_ids = pair["after_source_ids"]
        before_linear = route_dir / "before_gamma0_linear.crf"
        after_linear = route_dir / "after_gamma0_linear.crf"
        before_db = route_dir / "before_gamma0_db.crf"
        after_db = route_dir / "after_gamma0_db.crf"
        before_native_mask = route_dir / "before_native_distortion_mask.crf"
        after_native_mask = route_dir / "after_native_distortion_mask.crf"
        for output, inputs, bands, categorical in (
            (before_linear, paths(before_ids, "gamma0_linear_epsg32645_10m.crf"), 2, False),
            (after_linear, paths(after_ids, "gamma0_linear_epsg32645_10m.crf"), 2, False),
            (before_db, paths(before_ids, "gamma0_db_epsg32645_10m.crf"), 2, False),
            (after_db, paths(after_ids, "gamma0_db_epsg32645_10m.crf"), 2, False),
            (before_native_mask, paths(before_ids, "geometric_distortion_mask_epsg32645_10m.crf"), 1, True),
            (after_native_mask, paths(after_ids, "geometric_distortion_mask_epsg32645_10m.crf"), 1, True),
        ):
            mosaic_route_raster(arcpy, inputs, output, bands=bands, categorical=categorical, support=support)

        before_vv = make_band_layer(arcpy, before_linear, f"before_vv_{route_id}", 1)
        after_vv = make_band_layer(arcpy, after_linear, f"after_vv_{route_id}", 1)
        before_mask = arcpy.sa.Int(arcpy.sa.Raster(str(before_native_mask)) + 0.5)
        after_mask = arcpy.sa.Int(arcpy.sa.Raster(str(after_native_mask)) + 0.5)
        covered = (~arcpy.sa.IsNull(before_vv)) & (~arcpy.sa.IsNull(after_vv))
        layover = (before_mask == 4) | (before_mask == 5) | (after_mask == 4) | (after_mask == 5)
        shadow = (before_mask == 3) | (after_mask == 3)
        undetermined = (before_mask == 0) | (after_mask == 0)
        geometric_valid = ((before_mask == 1) | (before_mask == 2)) & ((after_mask == 1) | (after_mask == 2))
        categorical = arcpy.sa.Con(layover, 2, arcpy.sa.Con(shadow, 3, arcpy.sa.Con(undetermined, 0, arcpy.sa.Con(geometric_valid, 1, 90))))
        pair_mask = route_dir / "pair_exclusion_mask.tif"
        arcpy.sa.SetNull(~covered, categorical).save(str(pair_mask))
        arcpy.management.Delete(f"before_vv_{route_id}")
        arcpy.management.Delete(f"after_vv_{route_id}")

        table = support["gdb"] / ("AOIRadarAsc" if route_id == ROUTE_ORDER[0] else "AOIRadarDesc")
        aoi_observations, unknown = tabulate_radar_aoi(arcpy, aoi_fc=support["aoi_fc"], mask=pair_mask, table=table, pixel_contract=load_object(ROOT / plan["contract"]["bindings"]["pixel_readiness_contract_ref"]))
        bounds = aoi_bounds(arcpy, support["aoi_fc"])
        registration = measure_stable_registration_windowed(
            arcpy,
            before_path=before_linear,
            after_path=after_linear,
            pair_mask=pair_mask,
            overview_bbox=bounds["AOI-OVERVIEW"],
            exclusion_bboxes=[bounds["AOI-SOURCE"], bounds["AOI-UPPER-CORRIDOR"]],
            settings=plan["contract"]["registration"],
            pixel_contract=load_object(ROOT / plan["contract"]["bindings"]["pixel_readiness_contract_ref"]),
        )
        seam_results: list[dict[str, Any]] = []
        if route_id == ROUTE_ORDER[0]:
            for role, source_ids in (("before", before_ids), ("after", after_ids)):
                seam_results.append(
                    {
                        "role": role,
                        "source_ids": source_ids,
                        **evaluate_same_date_seam_windowed(
                            arcpy,
                            paths([source_ids[0]], "gamma0_linear_epsg32645_10m.crf")[0],
                            paths([source_ids[1]], "gamma0_linear_epsg32645_10m.crf")[0],
                        ),
                    }
                )
        result = evaluate_route(
            route_id=route_id,
            aoi_observations=aoi_observations,
            before_grid=grid_for_raster(arcpy, before_linear),
            after_grid=grid_for_raster(arcpy, after_linear),
            registration=registration,
            seam_observations=seam_results,
            pixel_contract=load_object(ROOT / plan["contract"]["bindings"]["pixel_readiness_contract_ref"]),
            unknown_mask_class_present=unknown,
        )
        receipt = {
            "schema_version": "1.0",
            "receipt_id": f"NEPAL-{route_id}-{receipt_namespace}-TERMINAL",
            "status": "pass_route_evaluated_qa_only",
            "completed_at_utc": now_utc(),
            "route_id": route_id,
            "disposition": result["status"],
            "source_ids": {"before": before_ids, "after": after_ids},
            "result": result,
            "outputs": {
                "before_linear": {"path": str(before_linear), "identity": raster_identity(before_linear)},
                "after_linear": {"path": str(after_linear), "identity": raster_identity(after_linear)},
                "before_db": {"path": str(before_db), "identity": raster_identity(before_db)},
                "after_db": {"path": str(after_db), "identity": raster_identity(after_db)},
                "pair_exclusion_mask": {"path": str(pair_mask), "identity": raster_identity(pair_mask)},
            },
            "assertions": {
                "route_evaluated_independently": True,
                "thresholds_unchanged": True,
                "primary_despeckle_applied": False,
                "baseline_admission_authorized": False,
                "change_analysis_executed": False,
                "scientific_admission_authorized": False,
            },
        }
        write_new_json(terminal_path, receipt)
        return {"route_id": route_id, "status": receipt["status"], "disposition": result["status"], "receipt_ref": terminal_ref, "receipt_sha256": sha256_file(terminal_path)}
    except Exception as exc:
        failure = {
            "schema_version": "1.0",
            "receipt_id": f"NEPAL-{route_id}-{receipt_namespace}-TERMINAL",
            "status": "failed_route_execution_no_retry",
            "completed_at_utc": now_utc(),
            "route_id": route_id,
            **safe_error(exc, (attempt_root, Path(plan["data_root"]))),
            "assertions": {
                "attempt_consumed": True,
                "automatic_retry_performed": False,
                "thresholds_changed": False,
                "baseline_or_change_analysis_executed": False,
                "scientific_admission_authorized": False,
            },
        }
        write_new_json(terminal_path, failure)
        return {"route_id": route_id, "status": failure["status"], "receipt_ref": terminal_ref, "receipt_sha256": sha256_file(terminal_path)}


def run_execute(executed_at_utc: str) -> int:
    gate = publication_gate()
    preflight_path = ROOT / FINAL_PREFLIGHT_REF
    if not preflight_path.is_file():
        raise RadarRouteError("final_preflight_missing")
    preflight = load_object(preflight_path)
    if preflight.get("status") != "pass_final_no_content_preflight" or preflight.get("bindings", {}).get("implementation_publication_gate_sha256") != repo_sha(PUBLICATION_GATE_REF):
        raise RadarRouteError("final_preflight_not_exact_pass")
    plan = load_execution_plan(ROOT, CONTRACT_REF)
    attempt_root = require_external_child(plan["data_root"], Path(plan["contract"]["attempt"]["external_attempt_root"]), must_exist=False)
    if attempt_root.exists() or (ROOT / TERMINAL_REF).exists():
        raise RadarRouteError("real_attempt_collision")
    attempt_root.mkdir(parents=True)
    write_new_json(
        attempt_root / "started.json",
        {
            "schema_version": "1.0",
            "status": "started_single_real_attempt",
            "started_at_utc": executed_at_utc,
            "attempt_id": plan["contract"]["attempt"]["attempt_id"],
            "implementation_contract_sha256": plan["contract_sha256"],
            "publication_gate_sha256": repo_sha(PUBLICATION_GATE_REF),
            "final_preflight_sha256": repo_sha(FINAL_PREFLIGHT_REF),
        },
    )
    identities_before = verify_external_identities(plan)
    os.environ.setdefault("GDAL_PAM_ENABLED", "NO")
    import arcpy  # type: ignore[import-not-found]

    arcpy.env.overwriteOutput = False
    arcpy.CheckOutExtension("ImageAnalyst")
    arcpy.CheckOutExtension("Spatial")
    try:
        dem_mosaic = create_dem_mosaic(arcpy, plan, attempt_root)
        support = create_analysis_support(arcpy, plan, attempt_root)

        def worker(source_id: str) -> dict[str, Any]:
            return process_source(
                arcpy=arcpy,
                plan=plan,
                identities_before=identities_before,
                attempt_root=attempt_root,
                dem_mosaic=dem_mosaic,
                support=support,
                source_id=source_id,
                started_at_utc=now_utc(),
            )

        sources = execute_fixed_order(SOURCE_ORDER, worker)
        routes: list[dict[str, Any]] = []
        stopped_route_id = None
        if sources["status"] == "pass_all_sources":
            for route_id in ROUTE_ORDER:
                result = process_route(arcpy=arcpy, plan=plan, attempt_root=attempt_root, support=support, route_id=route_id, started_at_utc=now_utc())
                routes.append(result)
                if result["status"] != "pass_route_evaluated_qa_only":
                    stopped_route_id = route_id
                    break
        identities_after = verify_external_identities(plan)
        custody_unchanged = identities_before == identities_after
        if not custody_unchanged:
            raise RadarRouteError("external_custody_changed_during_attempt")
        terminal_status = (
            "pass_six_sources_two_routes_qa_only"
            if sources["status"] == "pass_all_sources" and len(routes) == 2 and stopped_route_id is None
            else "stopped_on_first_execution_failure"
        )
        terminal = {
            "schema_version": "1.0",
            "receipt_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-001-TERMINAL-RECONCILIATION",
            "status": terminal_status,
            "completed_at_utc": now_utc(),
            "bindings": {
                "implementation_contract_sha256": plan["contract_sha256"],
                "implementation_commit_sha": gate["implementation_commit_sha"],
                "public_ci_run_id": gate["public_ci_run_id"],
                "implementation_publication_gate_sha256": repo_sha(PUBLICATION_GATE_REF),
                "final_preflight_sha256": repo_sha(FINAL_PREFLIGHT_REF),
            },
            "source_execution": sources,
            "route_evaluations": routes,
            "stopped_route_id": stopped_route_id,
            "external_custody_unchanged": custody_unchanged,
            "attempt_root": str(attempt_root),
            "assertions": {
                "source_order_exact": [item["source_id"] for item in sources["results"]] == SOURCE_ORDER[: len(sources["results"])],
                "route_order_exact": [item["route_id"] for item in routes] == ROUTE_ORDER[: len(routes)],
                "automatic_retry_performed": False,
                "network_request_performed_by_runner": False,
                "credential_value_read": False,
                "source_orbit_or_dem_custody_mutated": False,
                "baseline_admission_authorized": False,
                "change_analysis_executed": False,
                "interpretation_or_attribution_executed": False,
                "derived_pixel_publication_authorized": False,
                "scientific_publication_authorized": False,
            },
        }
        write_new_json(ROOT / TERMINAL_REF, terminal)
        write_new_json(attempt_root / "terminal.json", terminal)
        print(json.dumps({"status": terminal_status, "terminal": TERMINAL_REF, "source_count": len(sources["results"]), "route_count": len(routes)}, indent=2))
        return 0 if terminal_status == "pass_six_sources_two_routes_qa_only" else 20
    except Exception as exc:
        failure = {
            "schema_version": "1.0",
            "receipt_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-001-TERMINAL-RECONCILIATION",
            "status": "failed_supervisor_no_retry",
            "completed_at_utc": now_utc(),
            **safe_error(exc),
            "attempt_root": str(attempt_root),
            "assertions": {
                "attempt_consumed": True,
                "automatic_retry_performed": False,
                "network_request_performed_by_runner": False,
                "credential_value_read": False,
                "baseline_or_change_analysis_executed": False,
                "scientific_admission_authorized": False,
            },
        }
        write_new_json(ROOT / TERMINAL_REF, failure)
        write_new_json(attempt_root / "terminal.json", failure)
        print(json.dumps({"status": failure["status"], "failure_code": failure["failure_code"]}, indent=2))
        return 20
    finally:
        arcpy.CheckInExtension("Spatial")
        arcpy.CheckInExtension("ImageAnalyst")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=("final-preflight", "execute"))
    parser.add_argument("--timestamp-utc", required=True)
    args = parser.parse_args()
    if not UTC_TIMESTAMP.fullmatch(args.timestamp_utc):
        raise SystemExit("timestamp must be UTC in YYYY-MM-DDTHH:MM:SSZ form")
    try:
        return run_final_preflight(args.timestamp_utc) if args.mode == "final-preflight" else run_execute(args.timestamp_utc)
    except RadarRouteError as exc:
        print(json.dumps({"status": "stopped", "code": exc.code, "detail": exc.detail}, indent=2))
        return 12


if __name__ == "__main__":
    raise SystemExit(main())
