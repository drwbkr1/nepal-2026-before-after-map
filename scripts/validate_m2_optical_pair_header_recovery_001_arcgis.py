#!/usr/bin/env python3
"""Installed ArcGIS disposable launch and recovery-header receipt test."""

from __future__ import annotations

import gc
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import arcpy  # type: ignore[import-not-found]
import numpy as np

import m2_optical_pair_header_recovery_001_header as recovery
from inspect_optical_inputs_arcgis import describe_raster
from optical_input_readiness_core import RASTER_ROLES


def main() -> int:
    sources = [{"source_id": "M2-OPT-001"}, {"source_id": "M2-OPT-002"}]
    with tempfile.TemporaryDirectory(prefix="nepal-optical-header-recovery-disposable-") as folder:
        root = Path(folder)
        path = root / "generated_header_test.tif"
        raster = arcpy.NumPyArrayToRaster(np.ones((8, 8), dtype=np.uint16), arcpy.Point(300000, 3100000), 20, 20)
        raster.save(str(path))
        arcpy.management.DefineProjection(str(path), arcpy.SpatialReference(32645))
        description = describe_raster(arcpy, path)
        if description["wkid"] != 32645 or description["width"] != 8 or description["height"] != 8:
            raise RuntimeError("synthetic ArcGIS Describe did not return the generated grid")

        def synthetic_product(source, _arcpy, _contract):
            return {
                "source_id": source["source_id"], "inventory": {"status": "pass_inventory_only"},
                "metadata_errors": [],
                "descriptions": {role: dict(description) for role in RASTER_ROLES},
            }

        receipt_path = root / "synthetic-header.json"
        with patch.object(recovery, "require_execution_release"), \
                patch.object(recovery, "inspect_materialized_one", side_effect=synthetic_product):
            receipt = recovery.inspect_recovery_headers(sources, arcpy, receipt_path)
        if receipt["status"] != "block" or not receipt_path.is_file():
            raise RuntimeError("synthetic TIFF was not durably blocked by the frozen JP2 header contract")
        if receipt["receipt_id"] != "NEPAL-M2-OPTICAL-PAIR-HEADER-RECEIPT-RECOVERY-001-HEADER":
            raise RuntimeError("distinct recovery receipt identity was not used")
        del raster
        gc.collect()
        arcpy.ClearWorkspaceCache_management()
        arcpy.management.Delete(str(path))
    print(json.dumps({
        "status": "pass_disposable_arcgis_header_runtime",
        "arcgis_version": arcpy.GetInstallInfo().get("Version"),
        "synthetic_header_disposition": "block_expected_tiff_not_jp2",
        "recovery_receipt_created": True,
        "real_source_or_external_custody_accessed": False,
        "real_product_pixels_examined": False,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
