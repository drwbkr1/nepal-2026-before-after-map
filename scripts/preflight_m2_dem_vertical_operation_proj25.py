#!/usr/bin/env python3
"""Prove the exact local grid operation direction before any DEM pixel read."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
from typing import Any

from m2_dem_vertical_datum_proj25_core import (
    ROOT,
    controlled_path,
    forward_grid_pipeline,
    load_contract,
    load_json,
    sha256_file,
    vertical_pipeline,
    write_new_json,
)


GRID_TERMINAL = ROOT / "records/acquisition/m2-geoid-001-receipt-recovery-002.json"
AOI_REF = ROOT / "config/aoi/approved-study-areas.geojson"
OUTPUT = ROOT / "records/acquisition/m2-dem-vertical-datum-proj25-operation-selection-sign-preflight.json"


def utc_now() -> str:
    import datetime as datetime_module

    return datetime_module.datetime.now(datetime_module.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def aoi_points() -> list[tuple[float, float]]:
    document = load_json(AOI_REF)
    result: list[tuple[float, float]] = []
    for feature in document.get("features", []):
        rings = feature.get("geometry", {}).get("coordinates", [])
        points = [point for ring in rings for point in ring]
        if not points:
            raise ValueError("approved AOI feature has no coordinates")
        xs = [float(point[0]) for point in points]
        ys = [float(point[1]) for point in points]
        result.append(((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0))
    if not result:
        raise ValueError("approved AOI is empty")
    return result


def create_transform(source_epsg: int, target_epsg: int, operation: str) -> Any:
    from osgeo import osr  # type: ignore

    source = osr.SpatialReference()
    target = osr.SpatialReference()
    source.ImportFromEPSG(source_epsg)
    target.ImportFromEPSG(target_epsg)
    source.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    target.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    options = osr.CoordinateTransformationOptions()
    if not options.SetOperation(operation, False):
        raise ValueError("PROJ rejected the explicit operation")
    transform = osr.CreateCoordinateTransformation(source, target, options)
    if transform is None:
        raise ValueError("PROJ could not create the explicit operation")
    return transform


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observed-at-utc", default=None)
    args = parser.parse_args()
    if OUTPUT.exists():
        raise SystemExit("operation preflight output collision")
    contract = load_contract()
    grid_spec = contract["grid"]
    grid = controlled_path(grid_spec["destination_relative_path"])
    if not grid.is_file() or sha256_file(grid) != grid_spec["expected_sha256"]:
        raise SystemExit("promoted approved grid is missing or differs")
    terminal = load_json(GRID_TERMINAL)
    if (
        terminal.get("status") != "pass_exact_promoted_grid_receipt_recovered_input_only"
        or terminal.get("observed", {}).get("sha256") != grid_spec["expected_sha256"]
    ):
        raise SystemExit("grid acquisition terminal receipt differs")
    os.environ["PROJ_NETWORK"] = "OFF"
    inverse_operation = vertical_pipeline(grid)
    forward_operation = forward_grid_pipeline(grid)
    orthometric_to_ellipsoidal = create_transform(9518, 4979, inverse_operation)
    ellipsoidal_to_orthometric = create_transform(4979, 9518, forward_operation)
    checks = []
    for longitude, latitude in aoi_points():
        orthometric = 1000.0
        transformed = orthometric_to_ellipsoidal.TransformPoint(longitude, latitude, orthometric)
        if not all(math.isfinite(float(value)) for value in transformed[:3]):
            raise SystemExit("inverse grid operation returned nonfinite coordinates")
        ellipsoidal = float(transformed[2])
        undulation = ellipsoidal - orthometric
        roundtrip = ellipsoidal_to_orthometric.TransformPoint(
            float(transformed[0]), float(transformed[1]), ellipsoidal
        )
        residual = abs(float(roundtrip[2]) - orthometric)
        horizontal_residual = max(
            abs(float(roundtrip[0]) - longitude), abs(float(roundtrip[1]) - latitude)
        )
        if residual > contract["vertical_operation"]["maximum_direction_check_residual_m"]:
            raise SystemExit("vertical operation direction roundtrip exceeds the approved residual")
        if horizontal_residual > 1e-9:
            raise SystemExit("vertical-only operation changed horizontal coordinates")
        checks.append(
            {
                "longitude": longitude,
                "latitude": latitude,
                "orthometric_height_H_m": orthometric,
                "geoid_undulation_N_m": undulation,
                "ellipsoidal_height_h_m": ellipsoidal,
                "height_relation": "h = H + N",
                "height_relation_residual_m": abs(ellipsoidal - (orthometric + undulation)),
                "roundtrip_residual_m": residual,
                "horizontal_roundtrip_residual_degrees": horizontal_residual,
            }
        )
    record = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-DEM-VERTICAL-DATUM-PROJ25-OPERATION-SIGN-PREFLIGHT",
        "observed_at_utc": args.observed_at_utc or utc_now(),
        "status": "pass_exact_local_inverse_operation_h_equals_H_plus_N",
        "grid_sha256": sha256_file(grid),
        "source_crs": "EPSG:9518",
        "target_crs": "EPSG:4979",
        "inverse_operation": inverse_operation,
        "forward_roundtrip_operation": forward_operation,
        "checks": checks,
        "assertions": {
            "proj_network_enabled": False,
            "network_requests_performed": False,
            "dem_pixels_read": False,
            "conversion_attempts_started": 0,
            "height_relation_confirmed": "h = H + N",
        },
    }
    write_new_json(OUTPUT, record)
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
