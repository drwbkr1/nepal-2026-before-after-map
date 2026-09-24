#!/usr/bin/env python3
"""Disposable ArcGIS metadata-only reader test; no preserved project input."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np

from m2_radar_event_pair_grid_provenance_diagnostic_001_core import (
    NAMES, candidate_paths, inspect_raster, sha256_file,
)


def snapshot(root: Path) -> dict[str, str]:
    return {path.relative_to(root).as_posix(): sha256_file(path)
            for path in sorted(root.rglob("*")) if path.is_file()}


def run() -> dict:
    import arcpy  # type: ignore

    root: Path | None = None
    outcome = {"status": "block_disposable_unknown"}
    try:
        with tempfile.TemporaryDirectory(prefix="nepal-grid-provenance-001-", ignore_cleanup_errors=True) as temp:
            root = Path(temp) / "s" / "2"
            root.mkdir(parents=True)
            for index, name in enumerate(NAMES):
                array = np.full((2, 2), index + 1, dtype=np.float32)
                raster = arcpy.NumPyArrayToRaster(array, arcpy.Point(84.0, 27.0), 0.01, 0.01)
                raster.save(str(root / name))
                del raster
                arcpy.management.DefineProjection(str(root / name), arcpy.SpatialReference(4326))
            before = snapshot(root)
            records = [inspect_raster(arcpy, path, root=root) for path in candidate_paths(root)]
            after = snapshot(root)
            outcome = {
                "status": "pass_disposable_metadata_reader_only",
                "arcgis_version": arcpy.GetInstallInfo().get("Version"),
                "generated_disposable_raster_count": len(records),
                "all_raster_dimensions_2_by_2": all(item["raster"]["width"] == 2 and item["raster"]["height"] == 2 for item in records),
                "input_file_inventory_unchanged": before == after,
                "describe_unavailable_fields": {item["name"]: item["describe_unavailable_fields"] for item in records},
                "project_data_or_external_custody_accessed": False,
                "pixel_reads": 0,
            }
            if not outcome["all_raster_dimensions_2_by_2"] or not outcome["input_file_inventory_unchanged"]:
                outcome["status"] = "block_disposable_metadata_reader"
    except Exception as exc:
        outcome = {"status": "block_disposable_exception", "failure_type": type(exc).__name__,
                   "failure_code": getattr(exc, "code", "unexpected_disposable_failure"),
                   "project_data_or_external_custody_accessed": False, "pixel_reads": 0}
    outcome["temporary_directory_removed"] = root is not None and not root.parent.parent.exists()
    return outcome


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["status"] == "pass_disposable_metadata_reader_only" and result["temporary_directory_removed"] else 20)
