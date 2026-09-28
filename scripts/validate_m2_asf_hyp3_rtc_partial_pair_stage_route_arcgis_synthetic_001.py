#!/usr/bin/env python3
"""Disposable /vsizip/ route test; no provider archive or project raster read."""

from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path
from unittest import mock
from zipfile import ZIP_STORED, ZipFile

import numpy as np

import m2_asf_hyp3_rtc_partial_pair_stage_001 as route
from m2_asf_hyp3_rtc_core_001 import RouteStop
from m2_asf_hyp3_rtc_partial_pair_stage_io_001 import DISPLAY_NAMES
from m2_asf_hyp3_rtc_product_header_001 import describe_vsi
from validate_m2_asf_hyp3_rtc_partial_pair_grid_arcgis_synthetic_001 import (
    RINGS, _raster,
)


ROOT = Path(__file__).resolve().parents[1]
ROLES = (("vv", "VV"), ("vh", "VH"), ("ls_map", "ls_map"))


def _archive(root: Path, name: str, x0: float, power: float) -> tuple[Path, dict]:
    from osgeo import gdal

    source = root / f"{name}.zip"
    with ZipFile(source, "x", compression=ZIP_STORED) as package:
        for role, suffix in ROLES:
            values = (np.ones((64, 64), dtype=np.uint8) if role == "ls_map"
                      else np.full((64, 64), power, dtype=np.float32))
            if role == "ls_map":
                values[8:12, 8:12] = 5
            disposable = _raster(values, x0)
            member_name = f"{name}_{suffix}.tif"
            path = root / member_name
            copy_ds = gdal.GetDriverByName("GTiff").CreateCopy(str(path), disposable)
            copy_ds = None
            disposable = None
            package.write(path, arcname=f"{name}/{member_name}")
    headers = {role: describe_vsi(source, f"{name}/{name}_{suffix}.tif")
               for role, suffix in ROLES}
    return source, {"headers": headers}


def validate() -> dict:
    import arcpy
    from osgeo import gdal

    gdal.UseExceptions()
    with tempfile.TemporaryDirectory(prefix="nepal-rtc-pair-route-") as temporary:
        root = Path(temporary)
        before, before_header = _archive(root, "SYNTH_BEFORE", 300000., 1.)
        after, after_header = _archive(root, "SYNTH_AFTER", 300010., 10.)
        aois = list(zip(("AOI-SOURCE", "AOI-UPPER-CORRIDOR"), RINGS, strict=True))
        with mock.patch.object(route, "_load_aois", return_value=aois):
            staged = route.stage_real_pair(
                before, after, before_header, after_header,
                root / "stage", ROOT,
            )
            if (staged["status"] != "pass_common_valid_for_local_partial_visual_only"
                    or [item["name"] for item in staged["display_rasters"]]
                    != list(DISPLAY_NAMES)):
                raise RuntimeError("disposable_vsi_pair_stage_failed")
            for name in DISPLAY_NAMES:
                raster = arcpy.Raster(str(root / "stage" / name))
                try:
                    if (raster.spatialReference.factoryCode != 32645
                            or raster.pixelType != "F32"
                            or raster.meanCellWidth != 10.):
                        raise RuntimeError("disposable_vsi_arcgis_raster_invalid")
                finally:
                    del raster
            arcpy.management.ClearWorkspaceCache()
            drift = copy.deepcopy(after_header)
            drift["headers"]["vv"]["grid"]["origin_x"] += 1.
            try:
                route.stage_real_pair(before, after, before_header, drift,
                                      root / "blocked", ROOT)
            except RouteStop as exc:
                if exc.code != "partial_pair_stage_header_drift":
                    raise
            else:
                raise RuntimeError("disposable_vsi_header_drift_not_blocked")
            if (root / "blocked").exists():
                raise RuntimeError("disposable_vsi_header_drift_wrote_raster")
    return {"status": "pass_disposable_vsi_pair_route_arcgis_runtime",
            "arcgis_version": arcpy.GetInstallInfo()["Version"],
            "wkid": 32645, "display_raster_count": 2,
            "header_drift_blocked_before_stage": True,
            "provider_or_project_raster_read": False,
            "network_or_credentials_used": False,
            "scientific_admission": False}


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
