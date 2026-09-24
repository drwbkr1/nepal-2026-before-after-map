#!/usr/bin/env python3
"""Installed ArcGIS disposable CRF metadata and bounded inventory validation."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np

from m2_radar_event_pair_grid_provenance_diagnostic_001_core import NAMES, candidate_paths, inspect_raster, sha256_file
from m2_radar_event_pair_grid_provenance_recovery_001_core import append_stage, inventory_gtc_configuration, reserve


def snapshot(root: Path) -> dict[str, str]:
    return {path.relative_to(root).as_posix(): sha256_file(path)
            for path in sorted(root.rglob("*")) if path.is_file()}


def run() -> dict:
    import arcpy  # type: ignore

    temp_root: Path | None = None
    outcome = {"status": "block_disposable_unknown"}
    try:
        with tempfile.TemporaryDirectory(prefix="nepal-grid-recovery-001-", ignore_cleanup_errors=True) as temp:
            temp_root = Path(temp)
            root = temp_root / "s" / "2"
            root.mkdir(parents=True)
            for index, name in enumerate(NAMES):
                array = np.full((2, 2), index + 1, dtype=np.float32)
                raster = arcpy.NumPyArrayToRaster(array, arcpy.Point(84.0, 27.0), 0.01, 0.01)
                raster.save(str(root / name))
                del raster
                arcpy.management.DefineProjection(str(root / name), arcpy.SpatialReference(4326))
            config = root / "gamma0_linear_gtc_raw.crf" / "synthetic-reviewed.json"
            config.write_bytes(b'{"disposable":true}\n')
            before = snapshot(root)
            journal_path = temp_root / "stages.jsonl"
            journal = reserve(journal_path)
            records = []
            try:
                for path in candidate_paths(root):
                    append_stage(journal, {"stage": "raster_metadata_started", "name": path.name})
                    item = inspect_raster(arcpy, path, root=root)
                    append_stage(journal, {"stage": "raster_metadata_completed", **item})
                    records.append(item)
                inventory = inventory_gtc_configuration(root / "gamma0_linear_gtc_raw.crf", root=root,
                                                         expected_sha256=sha256_file(config))
                append_stage(journal, {"stage": "configuration_inventory_completed", **inventory})
            finally:
                journal.close()
            after = snapshot(root)
            stages = [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]
            outcome = {
                "status": "pass_disposable_arcgis_recovery_metadata_only",
                "arcgis_version": arcpy.GetInstallInfo().get("Version"),
                "generated_disposable_raster_count": len(records),
                "metadata_stages_persisted": len([item for item in stages if item["stage"] == "raster_metadata_completed"]),
                "exact_stage_order": [item["name"] for item in stages if item["stage"] == "raster_metadata_completed"] == list(NAMES),
                "unique_disposable_config_match": inventory["matching_historical_configuration_count"] == 1,
                "input_file_inventory_unchanged": before == after,
                "project_data_or_external_custody_accessed": False,
                "pixel_reads": 0, "radar_processing": False,
            }
            if (not outcome["exact_stage_order"] or not outcome["unique_disposable_config_match"]
                    or not outcome["input_file_inventory_unchanged"]):
                outcome["status"] = "block_disposable_recovery_validation"
    except Exception as exc:
        outcome = {"status": "block_disposable_exception", "failure_type": type(exc).__name__,
                   "failure_code": getattr(exc, "code", "unexpected_disposable_failure"),
                   "project_data_or_external_custody_accessed": False, "pixel_reads": 0}
    outcome["temporary_directory_removed"] = temp_root is not None and not temp_root.exists()
    return outcome


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["status"] == "pass_disposable_arcgis_recovery_metadata_only"
                     and result["temporary_directory_removed"] else 20)
