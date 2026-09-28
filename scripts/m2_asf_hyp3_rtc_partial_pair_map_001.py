#!/usr/bin/env python3
"""Local ArcGIS panel from already gated, common-masked RTC dB rasters.

This module does not open provider ZIPs or create the masked inputs. Callers
must separately establish source, pair-pixel, display-rights and custody gates.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any


TEMPLATE = Path(r"C:\Program Files\ArcGIS\Pro\Resources\ArcToolBox\Services\routingservices\data\Blank.aprx")
BEFORE_LABEL = "16 Aug 2026 | Sentinel-1D | ASF HyP3 RTC"
AFTER_LABEL = "28 Aug 2026 | Sentinel-1D | ASF HyP3 RTC"
WARNING = ("PARTIAL DATA ONLY. Layover, shadow and NoData are excluded. "
           "Full-area QA failed for the before scene; registration is unverified. "
           "Visual observation only: no difference, mapped change or event attribution.")


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _rect(arcpy: Any, x0: float, y0: float, x1: float, y1: float) -> Any:
    points = arcpy.Array([arcpy.Point(x0, y0), arcpy.Point(x1, y0),
                          arcpy.Point(x1, y1), arcpy.Point(x0, y1), arcpy.Point(x0, y0)])
    return arcpy.Polygon(points)


def _check_raster(arcpy: Any, path: Path) -> tuple:
    if not path.is_file() or path.suffix.lower() not in {".tif", ".tiff"} or not arcpy.Exists(str(path)):
        raise ValueError("rtc_partial_display_raster_missing")
    raster = arcpy.Raster(str(path))
    extent = raster.extent
    if (raster.spatialReference.factoryCode != 32645 or raster.bandCount != 1
            or raster.pixelType != "F32" or raster.meanCellWidth != 10.0
            or raster.meanCellHeight != 10.0):
        raise ValueError("rtc_partial_display_raster_header_invalid")
    return (raster.width, raster.height, extent.XMin, extent.YMin, extent.XMax, extent.YMax)


def build_local_panel(before: Path, after: Path, output: Path, *,
                      common_valid_by_aoi: dict[str, float],
                      credits_and_dois: str) -> dict:
    """Create one local APRX/PNG; only caller-supplied masked dB GeoTIFFs."""
    import arcpy  # type: ignore[import-not-found]

    if (
        set(common_valid_by_aoi) != {"AOI-SOURCE", "AOI-UPPER-CORRIDOR"}
        or any(not isinstance(value, (int, float)) or not .2 <= value <= 1
               for value in common_valid_by_aoi.values())
        or not isinstance(credits_and_dois, str) or not credits_and_dois.strip()
        or len(credits_and_dois) > 480
        or "\n" in credits_and_dois or "\r" in credits_and_dois
        or not TEMPLATE.is_file() or output.exists()
    ):
        raise ValueError("rtc_partial_display_gate_or_output_invalid")
    before_header = _check_raster(arcpy, before)
    after_header = _check_raster(arcpy, after)
    if before_header != after_header:
        raise ValueError("rtc_partial_display_grids_differ")
    output.mkdir(parents=True, exist_ok=False)
    staged = []
    for source, name in ((before, "before_common_valid_db.tif"),
                         (after, "after_common_valid_db.tif")):
        dest = output / name
        with source.open("rb") as src, dest.open("xb") as dst:
            shutil.copyfileobj(src, dst, length=8 * 1024 * 1024)
            dst.flush()
            os.fsync(dst.fileno())
        if _sha(source) != _sha(dest):
            raise ValueError("rtc_partial_display_stage_mismatch")
        staged.append(dest)
    project = arcpy.mp.ArcGISProject(str(TEMPLATE))
    for old_map in list(project.listMaps()):
        project.deleteItem(old_map)
    maps = []
    for raster, label in zip(staged, (BEFORE_LABEL, AFTER_LABEL), strict=True):
        map_obj = project.createMap(label, "MAP")
        for layer in list(map_obj.listLayers()):
            map_obj.removeLayer(layer)
        map_obj.spatialReference = arcpy.SpatialReference(32645)
        layer = map_obj.addDataFromPath(str(raster))
        layer.name = label + " | common-valid VV gamma0 dB"
        maps.append(map_obj)
    layout = project.createLayout(13, 7.5, "INCH", "Nepal RTC partial before and after")
    for map_obj, raster, x0, label in zip(maps, staged, (.4, 6.7),
                                          (BEFORE_LABEL, AFTER_LABEL), strict=True):
        frame = layout.createMapFrame(_rect(arcpy, x0, 2.0, x0 + 5.9, 6.8), map_obj, label)
        frame.camera.setExtent(arcpy.Describe(str(raster)).extent)
        frame.camera.scale *= 1.08
        project.createTextElement(layout, _rect(arcpy, x0, 6.82, x0 + 5.9, 7.13),
                                  "POLYGON", label, 10, "Segoe UI", "Bold", name=label)
    project.createTextElement(layout, _rect(arcpy, .4, 7.16, 12.6, 7.43),
                              "POLYGON", "Nepal 2026 | EPSG:32645 | ASF RTC VV gamma0 dB",
                              14, "Segoe UI", "Bold", name="Title")
    coverage = (f"Common valid VV/VH: source {common_valid_by_aoi['AOI-SOURCE']:.1%}; "
                f"upper corridor {common_valid_by_aoi['AOI-UPPER-CORRIDOR']:.1%}. "
                "Blank areas exclude layover, shadow or NoData.")
    project.createTextElement(layout, _rect(arcpy, .4, 1.56, 12.6, 1.95),
                              "POLYGON", coverage, 9, "Segoe UI", "Regular", name="Coverage")
    project.createTextElement(layout, _rect(arcpy, .4, .66, 12.6, 1.5),
                              "POLYGON", WARNING, 9, "Segoe UI", "Bold", name="Partial-data warning")
    project.createTextElement(layout, _rect(arcpy, .4, .08, 12.6, .62),
                              "POLYGON", credits_and_dois, 7, "Segoe UI", "Regular", name="Credits and DOIs")
    aprx = output / "Nepal_ASF_RTC_Partial_Pair_Local.aprx"
    png = output / "Nepal_ASF_RTC_Partial_Pair_Local.png"
    project.saveACopy(str(aprx))
    layout.exportToPNG(str(png), resolution=150, color_mode="24-BIT_TRUE_COLOR")
    receipt = {
        "status": "built_local_partial_visual_pending_fresh_reopen",
        "wkid": 32645, "raster_count": 2,
        "input_sha256": [_sha(before), _sha(after)],
        "staged_sha256": [_sha(path) for path in staged],
        "aprx_sha256": _sha(aprx), "first_png_sha256": _sha(png),
        "common_valid_by_aoi": common_valid_by_aoi,
        "partial_and_registration_warning_visible": True,
        "DEM_raster_displayed": False, "change_analysis_or_attribution": False,
        "public_pixel_publication": False,
    }
    with (output / "build.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(receipt, stream, sort_keys=True, indent=2)
        stream.write("\n")
    return receipt


def verify_fresh_reopen(output: Path) -> dict:
    """Run from a separate ArcGIS Python process after build exits."""
    import arcpy  # type: ignore[import-not-found]

    aprx = output / "Nepal_ASF_RTC_Partial_Pair_Local.aprx"
    png = output / "Nepal_ASF_RTC_Partial_Pair_Local.png"
    reopened = output / "Nepal_ASF_RTC_Partial_Pair_Reopen.png"
    if not aprx.is_file() or not png.is_file() or reopened.exists():
        raise ValueError("rtc_partial_display_reopen_input_invalid")
    project = arcpy.mp.ArcGISProject(str(aprx))
    maps, layouts = project.listMaps(), project.listLayouts()
    if len(maps) != 2 or len(layouts) != 1 or any(
        map_obj.spatialReference.factoryCode != 32645 or len(map_obj.listLayers()) != 1
        or map_obj.listLayers()[0].isBroken for map_obj in maps
    ):
        raise ValueError("rtc_partial_display_reopen_project_invalid")
    layouts[0].exportToPNG(str(reopened), resolution=150, color_mode="24-BIT_TRUE_COLOR")
    return {
        "status": "pass_local_arcgis_fresh_reopen_export",
        "wkid": 32645, "map_count": 2, "layout_count": 1, "broken_layers": 0,
        "first_png_sha256": _sha(png), "reopen_png_sha256": _sha(reopened),
        "clean_machine_portability_verified": False,
        "scientific_map_admitted": False,
    }
