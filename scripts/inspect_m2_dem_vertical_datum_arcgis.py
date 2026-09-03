#!/usr/bin/env python3
"""Inspect local ArcGIS support for exact EGM2008 DEM preconversion."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import arcpy


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TRANSFORM = "WGS_1984_To_WGS_1984_EGM2008_1x1_Height"
EXPECTED_GRID = "Dataset_egm2008-1.grd"
FALLBACK_GRID = "Dataset_egm2008-25.grd"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root: Path) -> list[dict[str, Any]]:
    if not root.is_dir():
        return []
    return [
        {
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in sorted(root.rglob("*"), key=lambda value: str(value).lower())
        if path.is_file()
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspected-at-utc", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.inspected_at_utc.endswith("Z"):
        raise SystemExit("--inspected-at-utc must end in Z")
    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"REFUSED: output already exists: {output}")

    install = arcpy.GetInstallInfo()
    pedata = Path(install["InstallDir"]) / "Resources" / "pedata"
    candidate_roots = [
        pedata,
        Path("C:/Program Files (x86)/ArcGIS/CoordinateSystemsData"),
        Path.home() / "AppData/Local/Programs/ArcGIS/CoordinateSystemsData",
    ]
    before = {str(path): inventory(path) for path in candidate_roots}
    matching_grids = [
        item
        for items in before.values()
        for item in items
        if Path(item["path"]).name.lower() in {EXPECTED_GRID.lower(), FALLBACK_GRID.lower()}
    ]
    builtin_egm96 = pedata / "geoid" / "WGS84.img"

    aoi = json.loads((ROOT / "config/aoi/approved-study-areas.geojson").read_text(encoding="utf-8"))
    points = [
        point
        for feature in aoi["features"]
        for ring in feature["geometry"]["coordinates"]
        for point in ring
    ]
    extent = arcpy.Extent(
        min(point[0] for point in points),
        min(point[1] for point in points),
        max(point[0] for point in points),
        max(point[1] for point in points),
    )
    source = arcpy.SpatialReference(4326, 3855)
    target = arcpy.SpatialReference(4326, 115700)
    transforms = arcpy.ListTransformations(source, target, extent, "ALL")
    after = {str(path): inventory(path) for path in candidate_roots}
    if before != after:
        raise SystemExit("REFUSED: coordinate-system data inventory changed during inspection")

    expected_available = any(EXPECTED_TRANSFORM in item.lstrip("~") for item in transforms)
    payload = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-DEM-VERTICAL-DATUM-CAPABILITY-001",
        "status": "defer_exact_egm2008_grid_not_installed",
        "inspected_at_utc": args.inspected_at_utc,
        "runtime": {
            "product": install.get("ProductName"),
            "version": install.get("Version"),
            "license_level": install.get("LicenseLevel"),
        },
        "inspection": {
            "source_horizontal_wkid": 4326,
            "source_vertical_wkid": 3855,
            "source_vertical_name": source.VCS.name,
            "target_horizontal_wkid": 4326,
            "target_vertical_wkid": 115700,
            "target_vertical_name": target.VCS.name,
            "aoi_extent_wgs84": [extent.XMin, extent.YMin, extent.XMax, extent.YMax],
            "listed_transformations": transforms,
            "expected_transformation": EXPECTED_TRANSFORM,
            "expected_transformation_available": expected_available,
            "expected_grid_name": EXPECTED_GRID,
            "fallback_grid_name": FALLBACK_GRID,
            "matching_egm2008_grids": matching_grids,
            "builtin_egm96_grid": {
                "path": str(builtin_egm96),
                "present": builtin_egm96.is_file(),
                "size_bytes": builtin_egm96.stat().st_size if builtin_egm96.is_file() else None,
                "sha256": sha256(builtin_egm96) if builtin_egm96.is_file() else None,
            },
            "inventory_unchanged": True,
        },
        "decision": {
            "exact_egm2008_preconversion_available_now": expected_available and bool(matching_grids),
            "arcgis_builtin_egm96_sensitivity_available_now": builtin_egm96.is_file(),
            "required_next_action": "Owner installs the matching ArcGIS Coordinate Systems Data world1x1_vert component before exact EGM2008 preconversion can be validated.",
        },
        "assertions": {
            "network_requests_performed": False,
            "credentials_read": False,
            "software_installed_or_modified": False,
            "dem_files_read": False,
            "radar_processing_executed": False,
            "vertical_datum_route_selected": False,
            "scientific_result_established": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
