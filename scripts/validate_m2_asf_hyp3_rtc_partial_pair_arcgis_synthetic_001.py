#!/usr/bin/env python3
"""Installed ArcGIS local panel test with disposable projected dB rasters."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

from m2_asf_hyp3_rtc_partial_pair_map_001 import build_local_panel


ROOT = Path(__file__).resolve().parents[1]


def _generated_tif(path: Path, values: np.ndarray) -> None:
    from osgeo import gdal, osr

    rows, columns = values.shape
    raster = gdal.GetDriverByName("GTiff").Create(
        str(path), columns, rows, 1, gdal.GDT_Float32, options=["COMPRESS=LZW"])
    if raster is None:
        raise RuntimeError("partial_synthetic_create_failed")
    spatial = osr.SpatialReference()
    spatial.ImportFromEPSG(32645)
    raster.SetSpatialRef(spatial)
    raster.SetGeoTransform((300000.0, 10.0, 0.0, 3100640.0, 0.0, -10.0))
    band = raster.GetRasterBand(1)
    band.SetNoDataValue(np.nan)
    band.WriteArray(values)
    raster.FlushCache()
    raster.Close()


def validate() -> dict:
    import arcpy

    with tempfile.TemporaryDirectory(prefix="nepal-rtc-partial-disposable-") as temp:
        root = Path(temp)
        before = root / "generated-before-common-db.tif"
        after = root / "generated-after-common-db.tif"
        values = np.full((64, 64), -12.0, dtype=np.float32)
        values[:8, :] = np.nan
        _generated_tif(before, values)
        _generated_tif(after, values + 1)
        output = root / "local-panel"
        built = build_local_panel(
            before, after, output,
            common_valid_by_aoi={"AOI-SOURCE": .55, "AOI-UPPER-CORRIDOR": .74},
            credits_and_dois="Synthetic ASF/ESA credit | https://doi.org/10.5281/zenodo.4646138",
        )
        command = [sys.executable, "-c",
                   "import json,sys; sys.path.insert(0,'scripts'); from pathlib import Path; "
                   "from m2_asf_hyp3_rtc_partial_pair_map_001 import verify_fresh_reopen; "
                   "print(json.dumps(verify_fresh_reopen(Path(sys.argv[1]))))", str(output)]
        reopened = subprocess.run(command, cwd=ROOT, capture_output=True,
                                  text=True, timeout=120, check=False)
        if reopened.returncode != 0:
            raise RuntimeError("partial_synthetic_fresh_reopen_failed")
        receipt = json.loads(reopened.stdout)
        if (built["status"] != "built_local_partial_visual_pending_fresh_reopen"
                or receipt["status"] != "pass_local_arcgis_fresh_reopen_export"
                or receipt["broken_layers"] != 0
                or built["DEM_raster_displayed"] is not False
                or built["change_analysis_or_attribution"] is not False):
            raise RuntimeError("partial_synthetic_panel_invalid")
        return {
            "status": "pass_disposable_partial_panel_fresh_arcgis_reopen",
            "arcgis_version": arcpy.GetInstallInfo()["Version"],
            "wkid": receipt["wkid"], "map_count": receipt["map_count"],
            "broken_layers": receipt["broken_layers"],
            "project_or_provider_data_read": False,
            "network_or_credential_action": False,
            "scientific_admission": False,
        }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
