#!/usr/bin/env python3
"""Read-only reconciliation of the single approved eleven-tile mosaic."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from m2_dem_vertical_datum_proj25_core import sha256_file
from m2_radar_event_pair_dem_intake_001 import IntakeError, ROOT
from m2_radar_event_pair_dem_mosaic_001 import CLEANUP, ERROR, MOSAIC, TERMINAL, exact_mosaic_inputs


OUTPUT = ROOT / "records" / "processing" / "m2-radar-event-area-pair-001-dem-mosaic-reconciliation.json"


def validate_mosaic_metadata(dataset: Any) -> dict[str, Any]:
    if dataset is None or dataset.RasterXSize != 14400 or dataset.RasterYSize != 10800 or dataset.RasterCount != 1:
        raise IntakeError("mosaic_dimensions_or_band_count_drift")
    from osgeo import gdal, osr  # type: ignore

    band = dataset.GetRasterBand(1)
    reference = osr.SpatialReference()
    if (reference.ImportFromWkt(dataset.GetProjectionRef()) != 0
            or reference.GetAttrValue("DATUM") != "WGS_1984"
            or abs(reference.GetSemiMajor() - 6378137.0) > 1e-6
            or abs(reference.GetInvFlattening() - 298.257223563) > 1e-9
            or abs(reference.GetAngularUnits() - 0.017453292519943295) > 1e-12):
        raise IntakeError("mosaic_crs_drift")
    if band.DataType != gdal.GDT_Float32 or band.GetNoDataValue() is None:
        raise IntakeError("mosaic_pixel_type_or_nodata_missing")
    transform = dataset.GetGeoTransform()
    if not (abs(transform[0] - 83.0) < 0.001 and abs(transform[3] - 30.0) < 0.001
            and abs(transform[1] - 1 / 3600) < 1e-9 and abs(transform[5] + 1 / 3600) < 1e-9
            and transform[2] == 0 and transform[4] == 0):
        raise IntakeError("mosaic_geotransform_drift")
    return {
        "columns": dataset.RasterXSize,
        "rows": dataset.RasterYSize,
        "bands": dataset.RasterCount,
        "horizontal_epsg": 4326,
        "pixel_type": "Float32",
        "nodata_present": True,
        "bounds_degrees_approx": [83, 27, 87, 30],
    }


def reconcile() -> dict[str, Any]:
    if OUTPUT.exists():
        raise IntakeError("mosaic_reconciliation_already_written")
    inputs = exact_mosaic_inputs()
    if len(inputs) != 11:
        raise IntakeError("mosaic_input_count_drift")
    if not TERMINAL.is_file() or not CLEANUP.is_file() or not ERROR.is_file() or not MOSAIC.is_file():
        raise IntakeError("mosaic_receipt_or_output_missing")
    terminal = json.loads(TERMINAL.read_text(encoding="utf-8"))
    cleanup = json.loads(CLEANUP.read_text(encoding="utf-8"))
    if (terminal.get("status") != "pass_mosaic_created_pending_actual_sar_extent_and_valid_elevation_gate"
            or terminal.get("input_count") != 11 or terminal.get("horizontal_epsg") != 4326
            or terminal.get("height_reference") != "ellipsoidal_WGS84_from_exact_PROJ25_grid"
            or terminal.get("geoid_argument_for_later_GTC") != "NONE"
            or terminal.get("radar_processing_started") is not False
            or cleanup.get("status") != "no_cleanup_required" or ERROR.stat().st_size != 0
            or MOSAIC.stat().st_size != terminal.get("output_size_bytes")
            or sha256_file(MOSAIC) != terminal.get("output_sha256")):
        raise IntakeError("mosaic_terminal_or_byte_identity_drift")
    from osgeo import gdal  # type: ignore

    gdal.UseExceptions()
    dataset = gdal.Open(str(MOSAIC), gdal.GA_ReadOnly)
    metadata = validate_mosaic_metadata(dataset)
    dataset = None
    return {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-EVENT-AREA-PAIR-001-DEM-MOSAIC-RECONCILIATION",
        "checked_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": "pass_mosaic_identity_and_structure_only_pending_actual_sar_extent_gate",
        "input_count": len(inputs),
        "input_sha256_in_order": [sha256_file(path) for path in inputs],
        "output_size_bytes": MOSAIC.stat().st_size,
        "output_sha256": terminal["output_sha256"],
        "terminal_receipt_sha256": sha256_file(TERMINAL),
        "cleanup_receipt_sha256": sha256_file(CLEANUP),
        "metadata": metadata,
        "actual_sar_extent_and_valid_elevation_proven": False,
        "radar_processing_released": False,
    }


def main() -> int:
    try:
        result = reconcile()
        with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
        print(json.dumps({"status": result["status"], "output_sha256": result["output_sha256"]}))
        return 0
    except IntakeError as exc:
        print(json.dumps({"status": "stopped_before_reconciliation", "code": exc.code}))
        return 12


if __name__ == "__main__":
    raise SystemExit(main())
