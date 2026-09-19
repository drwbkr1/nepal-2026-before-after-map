#!/usr/bin/env python3
"""Validate recovery-002 orchestration with disposable ArcGIS-runtime inputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any

import arcpy  # type: ignore
import numpy as np

import m2_radar_pixel_orbit_application_recovery_002_core as core
import run_m2_radar_pixel_orbit_application_recovery_002 as runner


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-pixel-orbit-application-recovery-002"
OUTPUT_REF = f"records/readiness/{PREFIX}-arcgis-runtime-validation.json"
EXTERNAL_ROOT = Path(r"C:\Projects\Active\nepal-2026-before-after-map-data").resolve()


def load_lines(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def synthetic_identity(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "sources": {source_id: {"inventory_sha256": "1" * 64} for source_id in core.SOURCE_ORDER},
        "orbits": {source_id: {"sha256": "2" * 64} for source_id in core.SOURCE_ORDER},
        "dems": {f"M2-DEM-{index:03d}": {"sha256": "3" * 64} for index in range(1, 5)},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verified-at-utc", required=True)
    args = parser.parse_args()
    if not args.verified_at_utc.endswith("Z"):
        raise SystemExit("--verified-at-utc must be UTC")
    output = ROOT / OUTPUT_REF
    if output.exists():
        raise SystemExit("ArcGIS runtime validation output collision")

    install = arcpy.GetInstallInfo()
    runtime = {
        "product": install.get("ProductName"),
        "version": install.get("Version"),
        "license_level": arcpy.ProductInfo(),
        "python_executable": str(Path(__import__("sys").executable).resolve()),
    }
    events: list[str] = []

    with tempfile.TemporaryDirectory(prefix="nepal-radar-recovery-002-arcgis-") as temporary:
        temporary_root = Path(temporary).resolve()
        if ROOT == temporary_root or ROOT in temporary_root.parents or EXTERNAL_ROOT == temporary_root or EXTERNAL_ROOT in temporary_root.parents:
            raise SystemExit("temporary root intersects repository or external custody")

        def arcpy_loader() -> Any:
            events.append("arcpy_import")
            return arcpy

        def dem_builder(arcpy_module: Any, plan: dict[str, Any], attempt_root: Path) -> str:
            events.append("disposable_geoprocessing_started")
            scratch = attempt_root / "disposable"
            scratch.mkdir()
            lower_left = arcpy_module.Point(500000.0, 3100000.0)
            left = arcpy_module.NumPyArrayToRaster(
                np.array([[1, 2], [3, 4]], dtype=np.float32), lower_left, 10.0, 10.0, -9999.0
            )
            right = arcpy_module.NumPyArrayToRaster(
                np.array([[5, 6], [7, 8]], dtype=np.float32), lower_left, 10.0, 10.0, -9999.0
            )
            left_path = scratch / "left.tif"
            right_path = scratch / "right.tif"
            left.save(str(left_path))
            right.save(str(right_path))
            arcpy_module.management.MosaicToNewRaster(
                [str(left_path), str(right_path)], str(scratch), "mosaic.tif", "", "32_BIT_FLOAT", 10.0, 1, "LAST", "FIRST"
            )
            mosaic = scratch / "mosaic.tif"
            if not mosaic.is_file():
                raise RuntimeError("disposable-mosaic-missing")
            events.append("disposable_geoprocessing_completed")
            return str(mosaic)

        def support_builder(arcpy_module: Any, plan: dict[str, Any], attempt_root: Path) -> dict[str, Any]:
            description = arcpy_module.Describe(str(attempt_root / "disposable" / "mosaic.tif"))
            events.append("disposable_support_completed")
            return {"width": int(description.width), "height": int(description.height)}

        def source_processor(*, source_id: str, **kwargs: Any) -> dict[str, Any]:
            events.append(f"source:{source_id}")
            return {"source_id": source_id, "status": "pass_source_qa_only", "synthetic_only": True}

        def route_processor(*, route_id: str, **kwargs: Any) -> dict[str, Any]:
            events.append(f"route:{route_id}")
            return {"route_id": route_id, "status": "pass_route_evaluated_qa_only", "synthetic_only": True}

        plan = {"data_root": temporary_root, "contract": {}}
        success_target = temporary_root / "success-attempt"
        setattr(runner, "datetime", object())
        success_code = runner.execute_attempt_body(
            args.verified_at_utc,
            plan=plan,
            target=success_target,
            bindings={"arcgis_runtime_synthetic": "4" * 64},
            identity_verifier=synthetic_identity,
            arcpy_loader=arcpy_loader,
            dem_builder=dem_builder,
            support_builder=support_builder,
            source_processor=source_processor,
            route_processor=route_processor,
        )
        delattr(runner, "datetime")
        success_terminal = json.loads((success_target / "terminal.json").read_text(encoding="utf-8"))
        success_cleanup = json.loads((success_target / "cleanup.json").read_text(encoding="utf-8"))
        success_stages = [item["stage"] for item in load_lines(success_target / "stages.jsonl")]
        if success_code != 0 or success_terminal.get("status") != "pass_six_sources_two_routes_qa_only":
            raise SystemExit("installed ArcGIS success-path synthetic failed")
        if success_cleanup.get("status") != "cleanup_completed":
            raise SystemExit("installed ArcGIS success-path cleanup differed")
        if core.stage_positions(success_stages) != sorted(core.stage_positions(success_stages)):
            raise SystemExit("installed ArcGIS success-path stage order differed")

        failure_target = temporary_root / "failure-attempt"
        original_error = "synthetic-post-import-dem-boundary"

        def failing_dem_builder(arcpy_module: Any, plan: dict[str, Any], attempt_root: Path) -> str:
            events.append("synthetic_failure_after_arcpy_import")
            raise RuntimeError(original_error)

        def failing_terminal_writer(path: Path, value: object) -> None:
            raise OSError("synthetic-terminal-persistence-boundary")

        failure_code = runner.execute_attempt_body(
            args.verified_at_utc,
            plan=plan,
            target=failure_target,
            bindings={"arcgis_runtime_synthetic": "5" * 64},
            identity_verifier=synthetic_identity,
            arcpy_loader=arcpy_loader,
            dem_builder=failing_dem_builder,
            support_builder=support_builder,
            source_processor=source_processor,
            route_processor=route_processor,
            terminal_writer=failing_terminal_writer,
        )
        fallback = load_lines(failure_target / "fallback.jsonl")
        failure_cleanup = json.loads((failure_target / "cleanup.json").read_text(encoding="utf-8"))
        fallback_events = [item["event"] for item in fallback]
        if failure_code != 21:
            raise SystemExit(f"unexpected installed ArcGIS failure-path code: {failure_code}")
        if fallback_events[:3] != [
            "fallback_journal_initialized",
            "processing_exception_captured",
            "terminal_persistence_exception_captured",
        ]:
            raise SystemExit("installed ArcGIS failure-path fallback order differed")
        rendered = json.dumps(fallback)
        if original_error not in rendered or "synthetic-terminal-persistence-boundary" not in rendered:
            raise SystemExit("installed ArcGIS failure-path evidence missing")
        if (failure_target / "terminal.json").exists() or failure_cleanup.get("terminal_persisted") is not False:
            raise SystemExit("installed ArcGIS failure-path terminal disposition differed")

        receipt = {
            "schema_version": "1.0",
            "record_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-002-ARCGIS-RUNTIME-VALIDATION",
            "verified_at_utc": args.verified_at_utc,
            "status": "pass_installed_arcgis_runtime_disposable_success_and_failure_paths",
            "runtime": runtime,
            "bindings": runner.repository_bindings(),
            "checks": {
                "function_local_datetime_survived_global_rebinding": True,
                "actual_arcpy_import_and_product_info": True,
                "actual_extension_checkout_and_reverse_checkin": True,
                "actual_disposable_numpy_rasters_and_mosaic": True,
                "six_synthetic_source_routes_in_exact_order": [item for item in events if item.startswith("source:")]
                == [f"source:{source_id}" for source_id in core.SOURCE_ORDER],
                "two_synthetic_pair_routes_in_exact_order": [item for item in events if item.startswith("route:")]
                == [f"route:{route_id}" for route_id in core.ROUTE_ORDER],
                "durable_success_stage_order_monotonic": True,
                "first_failure_survived_terminal_persistence_failure": True,
                "cleanup_persisted_after_terminal_failure": True,
                "success_return_code": success_code,
                "failure_return_code": failure_code,
            },
            "assertions": {
                "synthetic_disposable_inputs_only": True,
                "arcpy_runtime_imported": True,
                "disposable_geoprocessing_invoked": True,
                "project_data_content_read": False,
                "external_custody_accessed": False,
                "network_request_performed": False,
                "credential_value_read": False,
                "production_attempt_created": False,
                "consumed_attempt_reused_or_retried": False,
                "radar_processing_executed": False,
                "baseline_or_change_analysis_executed": False,
                "scientific_result_established": False,
            },
            "limitations": [
                "This validates the recovery wrapper and a tiny disposable raster mosaic under the installed ArcGIS Pro runtime.",
                "Synthetic source and route workers do not establish production radar-processing success or recovery readiness.",
                "No project imagery, orbit, DEM, or external-custody content was accessed.",
            ],
        }
        core.write_new_json(output, receipt)

    if Path(temporary).exists():
        shutil.rmtree(temporary, ignore_errors=True)
    print(json.dumps({"status": receipt["status"], "receipt": OUTPUT_REF}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
