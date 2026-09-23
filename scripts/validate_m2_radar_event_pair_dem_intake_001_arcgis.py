#!/usr/bin/env python3
"""Disposable installed-runtime test for the event-pair DEM GeoTIFF verifier."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from m2_radar_event_pair_dem_intake_001 import IntakeError, verify_geotiff


def main() -> int:
    import arcpy  # type: ignore
    from osgeo import gdal, osr  # type: ignore

    with tempfile.TemporaryDirectory(prefix="nepal-event-pair-dem-synthetic-") as temporary:
        path = Path(temporary) / "synthetic.tif"
        raster = gdal.GetDriverByName("GTiff").Create(
            str(path), 3600, 3600, 1, gdal.GDT_Float32,
            options=["TILED=YES", "COMPRESS=DEFLATE"],
        )
        raster.SetGeoTransform((86.0, 1.0 / 3600, 0.0, 28.0, 0.0, -1.0 / 3600))
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        raster.SetSpatialRef(srs)
        raster.GetRasterBand(1).Fill(100.0)
        raster.FlushCache()
        raster = None
        valid = verify_geotiff(path, [86, 27, 87, 28])
        if valid["valid_pixels"] != 3600 * 3600:
            raise ValueError("synthetic valid-pixel count differs")
        raster = gdal.Open(str(path), gdal.GA_Update)
        raster.SetGeoTransform((85.0, 1.0 / 3600, 0.0, 28.0, 0.0, -1.0 / 3600))
        raster.FlushCache()
        raster = None
        try:
            verify_geotiff(path, [86, 27, 87, 28])
        except IntakeError as exc:
            if exc.code != "geotiff_bounds_drift":
                raise
        else:
            raise ValueError("deliberate bounds drift was accepted")
    print(json.dumps({"status": "pass_disposable_arcgis_runtime", "arcgis_version": arcpy.GetInstallInfo().get("Version"), "valid_pixels": valid["valid_pixels"], "deliberate_bounds_drift_blocked": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
