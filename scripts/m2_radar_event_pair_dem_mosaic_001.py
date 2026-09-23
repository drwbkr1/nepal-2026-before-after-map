#!/usr/bin/env python3
"""One append-only eleven-tile ellipsoidal DEM mosaic for the event-pair QA route."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from m2_dem_vertical_datum_proj25_core import controlled_path, sha256_file
from m2_radar_event_pair_dem_conversion_001 import (
    BATCH_REF, OLD_CONTRACT_REF, conversion_items, verify_offline_dependencies,
)
from m2_radar_event_pair_dem_intake_001 import DATA_ROOT, IntakeError, ROOT


MOSAIC_ROOT = DATA_ROOT / "derived" / "dem" / "event-pair-001-eleven"
MOSAIC = MOSAIC_ROOT / "ellipsoidal_dem_mosaic.tif"
TERMINAL = MOSAIC_ROOT / "terminal.json"
ERROR = MOSAIC_ROOT / "error.json"
CLEANUP = MOSAIC_ROOT / "cleanup.json"


def exact_mosaic_inputs() -> list[Path]:
    verify_offline_dependencies()
    for suffix in ("implementation-publication-gate", "execution-publication-gate"):
        gate = json.loads((ROOT / "records" / "readiness" / f"m2-radar-event-area-pair-001-{suffix}.json").read_text(encoding="utf-8"))
        if gate.get("bindings", {}).get("mosaic_code_sha256") != sha256_file(Path(__file__)):
            raise IntakeError("mosaic_public_gate_missing")
    batch = json.loads(BATCH_REF.read_text(encoding="utf-8"))
    if batch.get("status") != "pass_seven_fixed_order_conversions_verified" or len(batch.get("attempted", [])) != 7:
        raise IntakeError("seven_conversion_batch_not_passing")
    old = json.loads(OLD_CONTRACT_REF.read_text(encoding="utf-8"))
    old_paths: list[Path] = []
    for item in old["dem_sources_in_exact_order"]:
        path = controlled_path(item["output_relative_path"])
        receipt = json.loads((ROOT / "records" / "processing" / f"{item['source_id'].lower()}-proj25-conversion-001-terminal.json").read_text(encoding="utf-8"))
        if sha256_file(path) != receipt.get("promoted", {}).get("sha256"):
            raise IntakeError("prior_dem_derivative_drift")
        old_paths.append(path)
    new_paths: list[Path] = []
    for item in conversion_items(require_outputs_absent=False):
        path = controlled_path(item["output_relative_path"])
        receipt = json.loads((ROOT / "records" / "processing" / f"{item['source_id'].lower()}-proj25-conversion-001-terminal.json").read_text(encoding="utf-8"))
        if receipt.get("status") != "pass_converted_verified_promoted" or sha256_file(path) != receipt.get("promoted", {}).get("sha256"):
            raise IntakeError("new_dem_derivative_drift")
        new_paths.append(path)
    if len(old_paths + new_paths) != 11 or len({str(path).casefold() for path in old_paths + new_paths}) != 11:
        raise IntakeError("mosaic_input_count_or_identity_drift")
    return old_paths + new_paths


def reserve_mosaic_receipts() -> None:
    if MOSAIC_ROOT.exists() or MOSAIC.exists():
        raise IntakeError("mosaic_attempt_collision")
    MOSAIC_ROOT.mkdir(parents=True, exist_ok=False)
    for path in (TERMINAL, ERROR, CLEANUP):
        with path.open("xb") as stream:
            stream.flush()
            os.fsync(stream.fileno())


def write_reserved(path: Path, value: dict[str, Any]) -> None:
    with path.open("r+b") as stream:
        if stream.seek(0, os.SEEK_END) != 0:
            raise IntakeError("mosaic_receipt_already_written")
        stream.write((json.dumps(value, indent=2) + "\n").encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())


def build_mosaic(*, arcpy_module: Any | None = None) -> dict[str, Any]:
    inputs = exact_mosaic_inputs()
    reserve_mosaic_receipts()
    stage = "arcgis_import"
    try:
        if arcpy_module is None:
            import arcpy as arcpy_module  # type: ignore
        os.environ["PROJ_NETWORK"] = "OFF"
        stage = "mosaic_creation"
        arcpy_module.management.MosaicToNewRaster(
            [str(path) for path in inputs], str(MOSAIC_ROOT), MOSAIC.name,
            arcpy_module.SpatialReference(4326), "32_BIT_FLOAT", None, 1, "FIRST", "FIRST",
        )
        if not MOSAIC.is_file():
            raise IntakeError("mosaic_output_missing")
        stage = "mosaic_structure"
        description = arcpy_module.Describe(str(MOSAIC))
        if int(description.spatialReference.factoryCode) != 4326 or int(description.bandCount) != 1:
            raise IntakeError("mosaic_structure_drift")
        result = {
            "status": "pass_mosaic_created_pending_actual_sar_extent_and_valid_elevation_gate",
            "input_count": 11,
            "output_size_bytes": MOSAIC.stat().st_size,
            "output_sha256": sha256_file(MOSAIC),
            "horizontal_epsg": 4326,
            "height_reference": "ellipsoidal_WGS84_from_exact_PROJ25_grid",
            "geoid_argument_for_later_GTC": "NONE",
            "radar_processing_started": False,
        }
    except BaseException as exc:
        result = {
            "status": "terminal_mosaic_failure_no_retry",
            "failure_code": exc.code if isinstance(exc, IntakeError) else "arcgis_or_runtime_failure",
            "last_stage": stage,
            "partial_output_preserved": MOSAIC.exists(),
            "radar_processing_started": False,
        }
        write_reserved(ERROR, {"schema_version": "1.0", **result})
    try:
        write_reserved(TERMINAL, {"schema_version": "1.0", "record_id": "NEPAL-M2-RADAR-EVENT-AREA-PAIR-001-ELEVEN-TILE-MOSAIC", **result})
    finally:
        write_reserved(CLEANUP, {"schema_version": "1.0", "status": "partial_preserved" if result["status"] != "pass_mosaic_created_pending_actual_sar_extent_and_valid_elevation_gate" else "no_cleanup_required"})
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-one-mosaic", action="store_true", required=True)
    parser.parse_args()
    try:
        result = build_mosaic()
        print(json.dumps({"status": result["status"], "failure_code": result.get("failure_code"), "output_sha256": result.get("output_sha256")}))
        return 0 if result["status"].startswith("pass_") else 20
    except IntakeError as exc:
        print(json.dumps({"status": "stopped_before_mosaic", "code": exc.code}))
        return 12


if __name__ == "__main__":
    raise SystemExit(main())
