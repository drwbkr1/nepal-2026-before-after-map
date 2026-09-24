#!/usr/bin/env python3
"""Distinct recovery-003 source processor; the consumed sequence file is unchanged."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from m2_radar_pixel_orbit_application_001_core import (
    RadarRouteError, copy_safe_exclusive, inventory_sha256, sha256_file,
    stable_inventory, write_new_json,
)
from m2_radar_esri_sequence_processing_005 import (
    _save_raster_result, describe_raster, now_utc, raster_identity, safe_error,
    source_output_root, source_receipt_path,
)
from m2_radar_event_pair_native_gtc_recovery_003_core import (
    NativeGridStop, guard_materialized_size, inspect_returned_raster,
    native_gtc_environment, project_with_frozen_extent,
)


def _save_native_gtc(*, arcpy: Any, arguments: tuple[Any, ...], output: Path,
                     source_id: str, stage_recorder: Callable[..., None],
                     attempt_root: Path, source_bounds: tuple[float, float, float, float],
                     aoi_bounds: tuple[tuple[float, float, float, float], ...],
                     categorical: bool) -> dict[str, Any]:
    name = "ApplyGeometricTerrainCorrection_mask" if categorical else "ApplyGeometricTerrainCorrection_gamma"
    if output.exists():
        raise NativeGridStop("native_output_collision")
    stage_recorder(source_id=source_id, tool=name, phase="started")
    event_dir = attempt_root / "receipts" / "native"

    def record_environment(value: dict[str, Any]) -> None:
        write_new_json(event_dir / f"{source_id.lower()}-{name}-environment.json", value)

    with native_gtc_environment(arcpy, resampling="NEAREST" if categorical else "BILINEAR",
                                record_environment=record_environment):
        returned = arcpy.ia.ApplyGeometricTerrainCorrection(*arguments)
        metadata = inspect_returned_raster(returned, source_bounds=source_bounds,
                                           aoi_bounds=aoi_bounds)
        write_new_json(event_dir / f"{source_id.lower()}-{name}-presave.json", metadata)
        stage_recorder(source_id=source_id, tool=name, phase="native_presave_metadata_passed")
        save = getattr(returned, "save", None)
        if not callable(save):
            raise NativeGridStop("native_returned_raster_missing_save")
        save(str(output))
    metadata["materialized_disk_bytes"] = guard_materialized_size(output, projected=False)
    stage_recorder(source_id=source_id, tool=name, phase="completed")
    return metadata


def execute_raster_function_pipeline(*, arcpy: Any, manifest: Path, dem_mosaic: Path,
                                     source_id: str, stage_recorder: Callable[..., None],
                                     outputs: dict[str, Path], attempt_root: Path,
                                     source_bounds: tuple[float, float, float, float],
                                     aoi_bounds: tuple[tuple[float, float, float, float], ...]) -> dict[str, Any]:
    """Frozen Esri sequence with two isolated native GTC calls and pre-save stops."""
    for tool, function, arguments, output in (
        ("RemoveThermalNoise", arcpy.ia.RemoveThermalNoise,
         (str(manifest), "VV;VH"), outputs["thermal"]),
        ("ApplyRadiometricCalibration", arcpy.ia.ApplyRadiometricCalibration,
         (str(outputs["thermal"]), "VV;VH", "BETA_NOUGHT"), outputs["beta"]),
        ("ApplyRadiometricTerrainFlattening", arcpy.ia.ApplyRadiometricTerrainFlattening,
         (str(outputs["beta"]), str(dem_mosaic), "NONE", "VV;VH", "GAMMA_NOUGHT",
          str(outputs["scattering"]), str(outputs["distortion"]), str(outputs["native_mask"])),
         outputs["gamma_slant"]),
        ("Despeckle", arcpy.ia.Despeckle,
         (str(outputs["gamma_slant"]), "VV;VH", "REFINED_LEE"), outputs["gamma_despeckled"]),
    ):
        _save_raster_result(tool_name=tool, function=function, arguments=arguments,
                            output=output, source_id=source_id, stage_recorder=stage_recorder)
    gamma = _save_native_gtc(
        arcpy=arcpy, arguments=(str(outputs["gamma_despeckled"]), "VV;VH", str(dem_mosaic), "NONE"),
        output=outputs["gamma_gtc_raw"], source_id=source_id, stage_recorder=stage_recorder,
        attempt_root=attempt_root, source_bounds=source_bounds, aoi_bounds=aoi_bounds,
        categorical=False)
    _save_raster_result(tool_name="ConvertSARUnits", function=arcpy.ia.ConvertSARUnits,
                        arguments=(str(outputs["gamma_gtc_raw"]), "LINEAR_TO_DB"),
                        output=outputs["db_gtc_raw"], source_id=source_id,
                        stage_recorder=stage_recorder)
    mask = _save_native_gtc(
        arcpy=arcpy, arguments=(str(outputs["native_mask"]), "#", str(dem_mosaic), "NONE"),
        output=outputs["mask_gtc_raw"], source_id=source_id, stage_recorder=stage_recorder,
        attempt_root=attempt_root, source_bounds=source_bounds, aoi_bounds=aoi_bounds,
        categorical=True)
    return {"gamma": gamma, "mask": mask}


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
    stage_recorder: Callable[..., None] = lambda **_: None,
) -> dict[str, Any]:
    source = next(item for item in plan["sources"] if item["source_id"] == source_id)
    orbit_id = source["orbit_source_id"]
    orbit = plan["orbits"][orbit_id]
    started_path, started_ref = source_receipt_path(plan, attempt_root, source_id, "started")
    terminal_path, terminal_ref = source_receipt_path(plan, attempt_root, source_id, "terminal")
    source_root = source_output_root(plan, attempt_root, source_id)
    receipt_namespace = plan.get("contract", {}).get(
        "receipt_namespace", "RADAR-ESRI-SEQUENCE-RECOVERY-005"
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
        stage_recorder(source_id=source_id, tool="ApplyOrbitCorrection", phase="started")
        arcpy.ia.ApplyOrbitCorrection(str(manifest), str(orbit_path))
        stage_recorder(source_id=source_id, tool="ApplyOrbitCorrection", phase="completed")
        orbit_messages = arcpy.GetMessages()

        thermal = source_root / "thermal_noise_removed.crf"
        beta = source_root / "beta0_linear.crf"
        gamma_slant = source_root / "gamma0_linear_slant.crf"
        gamma_despeckled = source_root / "gamma0_linear_despeckled.crf"
        scattering = source_root / "scattering_area.crf"
        distortion = source_root / "geometric_distortion.crf"
        native_mask = source_root / "geometric_distortion_mask_slant.crf"
        gamma_gtc_raw = source_root / "gamma0_linear_gtc_raw.crf"
        db_gtc_raw = source_root / "gamma0_db_gtc_raw.crf"
        mask_gtc_raw = source_root / "geometric_distortion_mask_gtc_raw.crf"
        gamma_final = source_root / "gamma0_linear_epsg32645_10m.crf"
        db_final = source_root / "gamma0_db_epsg32645_10m.crf"
        mask_final = source_root / "geometric_distortion_mask_epsg32645_10m.crf"

        source_bounds = tuple(source["footprint_bounds_degrees"])
        aoi_bounds = tuple(tuple(item) for item in plan["event_aoi_bounds_degrees"])
        native_grids = execute_raster_function_pipeline(
            arcpy=arcpy,
            manifest=manifest,
            dem_mosaic=dem_mosaic,
            source_id=source_id,
            stage_recorder=stage_recorder,
            attempt_root=attempt_root,
            source_bounds=source_bounds,
            aoi_bounds=aoi_bounds,
            outputs={
                "thermal": thermal,
                "beta": beta,
                "gamma_slant": gamma_slant,
                "gamma_despeckled": gamma_despeckled,
                "scattering": scattering,
                "distortion": distortion,
                "native_mask": native_mask,
                "gamma_gtc_raw": gamma_gtc_raw,
                "db_gtc_raw": db_gtc_raw,
                "mask_gtc_raw": mask_gtc_raw,
            },
        )
        projected_grids = {
            "gamma": project_with_frozen_extent(arcpy, gamma_gtc_raw, gamma_final, support["snap"], categorical=False),
            "db": project_with_frozen_extent(arcpy, db_gtc_raw, db_final, support["snap"], categorical=False),
            "mask": project_with_frozen_extent(arcpy, mask_gtc_raw, mask_final, support["snap"], categorical=True),
        }

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
            "status": "pass_source_grid_only_pending_aoi_qa",
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
            "native_grid_presave_observations": native_grids,
            "projected_grid_observations": projected_grids,
            "assertions": {
                "source_copy_used_for_orbit_application": True,
                "explicit_exact_resorb_used": True,
                "original_materialized_safe_unchanged": True,
                "geoid_parameter_none": True,
                "linear_gamma_nought_retained": True,
                "despeckle_applied": True,
                "despeckle_filter": "REFINED_LEE",
                "despeckle_filter_size_argument_omitted": True,
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
