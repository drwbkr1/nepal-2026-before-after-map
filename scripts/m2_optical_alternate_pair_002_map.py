#!/usr/bin/env python3
"""Local two-panel ArcGIS visual map; only caller-supplied masked raster inputs."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any


TEMPLATE = Path(r"C:\Program Files\ArcGIS\Pro\Resources\ArcToolBox\Services\routingservices\data\Blank.aprx")
BEFORE_LABEL = "24 Aug 2026 | Sentinel-2A | PB 05.12"
AFTER_LABEL = "21 Sep 2026 | Sentinel-2C | PB 05.13"
LIMITATION = ("Local masked visual only. The after image is 26 days after the event; "
              "intervening effects and processing-baseline differences prevent attribution. "
              "No quantitative change map or scientific admission.")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rectangle(arcpy: Any, x0: float, y0: float, x1: float, y1: float) -> Any:
    points = arcpy.Array([arcpy.Point(x0, y0), arcpy.Point(x1, y0),
                          arcpy.Point(x1, y1), arcpy.Point(x0, y1),
                          arcpy.Point(x0, y0)])
    return arcpy.Polygon(points)


def _require_raster(arcpy: Any, path: Path) -> None:
    if not path.is_file() or path.suffix.lower() not in {".tif", ".tiff"}:
        raise ValueError("alternate_pair_local_display_raster_missing")
    if not arcpy.Exists(str(path)):
        raise ValueError("alternate_pair_local_display_raster_unreadable")
    described = arcpy.Describe(str(path))
    if described.spatialReference.factoryCode != 32645 or described.bandCount != 3:
        raise ValueError("alternate_pair_local_display_crs_or_bands_invalid")


def build_local_map(before: Path, after: Path, output: Path, *, aoi_id: str,
                    before_usable_fraction: float, after_usable_fraction: float) -> dict[str, Any]:
    """Create local APRX and PNG; caller must already hold a passing pixel-QA gate."""
    import arcpy  # type: ignore[import-not-found]

    if aoi_id not in {"AOI-SOURCE", "AOI-UPPER-CORRIDOR"}:
        raise ValueError("alternate_pair_local_display_aoi_unapproved")
    if not all(0 <= value <= 1 for value in (before_usable_fraction, after_usable_fraction)):
        raise ValueError("alternate_pair_local_display_mask_fraction_invalid")
    if not TEMPLATE.is_file() or output.exists():
        raise ValueError("alternate_pair_local_display_template_or_output_collision")
    _require_raster(arcpy, before)
    _require_raster(arcpy, after)
    output.mkdir(parents=True, exist_ok=False)
    staged: list[Path] = []
    for source, name in ((before, "before_masked.tif"), (after, "after_masked.tif")):
        dest = output / name
        with source.open("rb") as src, dest.open("xb") as dst:
            shutil.copyfileobj(src, dst, length=8 * 1024 * 1024)
            dst.flush()
            os.fsync(dst.fileno())
        if sha256(source) != sha256(dest):
            raise ValueError("alternate_pair_local_display_stage_mismatch")
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
        layer.name = label + " | masked display"
        maps.append(map_obj)
    layout = project.createLayout(13, 7.5, "INCH", "Optical before and after - local visual")
    for map_obj, raster, x0, label in zip(maps, staged, (0.4, 6.7),
                                          (BEFORE_LABEL, AFTER_LABEL), strict=True):
        frame = layout.createMapFrame(_rectangle(arcpy, x0, 1.55, x0 + 5.9, 6.75),
                                      map_obj, label)
        frame.camera.setExtent(arcpy.Describe(str(raster)).extent)
        frame.camera.scale *= 1.08
        project.createTextElement(layout, _rectangle(arcpy, x0, 6.79, x0 + 5.9, 7.13),
                                  "POLYGON", label, 11, "Segoe UI", "Bold", name=label)
    project.createTextElement(layout, _rectangle(arcpy, .4, 7.16, 12.6, 7.43),
                              "POLYGON", f"Nepal 2026 | {aoi_id} | EPSG:32645 | local visual",
                              14, "Segoe UI", "Bold", name="Title")
    coverage = (f"Usable mask coverage: 24 Aug {before_usable_fraction:.1%}; "
                f"21 Sep {after_usable_fraction:.1%}. No quantitative comparison.")
    project.createTextElement(layout, _rectangle(arcpy, .4, 1.13, 12.6, 1.49),
                              "POLYGON", coverage, 9, "Segoe UI", "Regular", name="Mask coverage")
    project.createTextElement(layout, _rectangle(arcpy, .4, .12, 12.6, 1.08),
                              "POLYGON", LIMITATION, 9, "Segoe UI", "Regular", name="Limitations")
    aprx = output / "Nepal_Optical_Before_After_Local.aprx"
    png = output / "Nepal_Optical_Before_After_Local.png"
    project.saveACopy(str(aprx))
    layout.exportToPNG(str(png), resolution=150, color_mode="24-BIT_TRUE_COLOR")
    receipt = {
        "status": "built_local_visual_pending_fresh_reopen",
        "aoi_id": aoi_id, "wkid": 32645,
        "source_raster_sha256": [sha256(before), sha256(after)],
        "staged_raster_sha256": [sha256(path) for path in staged],
        "aprx_sha256": sha256(aprx), "first_png_sha256": sha256(png),
        "before_usable_fraction": before_usable_fraction,
        "after_usable_fraction": after_usable_fraction,
        "temporal_and_method_limitations_visible": True,
        "change_analysis_or_event_attribution": False,
        "public_pixel_publication": False,
    }
    with (output / "build.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    return receipt


def verify_reopen(output: Path) -> dict[str, Any]:
    """Open the saved APRX in a fresh process and independently export it."""
    import arcpy  # type: ignore[import-not-found]

    aprx = output / "Nepal_Optical_Before_After_Local.aprx"
    original = output / "Nepal_Optical_Before_After_Local.png"
    second = output / "Nepal_Optical_Before_After_Reopen.png"
    if second.exists():
        raise ValueError("alternate_pair_local_display_reopen_collision")
    project = arcpy.mp.ArcGISProject(str(aprx))
    maps, layouts = project.listMaps(), project.listLayouts()
    if len(maps) != 2 or len(layouts) != 1:
        raise ValueError("alternate_pair_local_display_project_shape_invalid")
    if any(map_obj.spatialReference.factoryCode != 32645 or
           len(map_obj.listLayers()) != 1 or map_obj.listLayers()[0].isBroken
           for map_obj in maps):
        raise ValueError("alternate_pair_local_display_broken_or_crs_invalid")
    layouts[0].exportToPNG(str(second), resolution=150, color_mode="24-BIT_TRUE_COLOR")
    return {"status": "pass_same_machine_local_arcgis_reopen_export",
            "map_count": 2, "layout_count": 1, "broken_layers": 0,
            "wkid": 32645, "first_png_sha256": sha256(original),
            "reopen_png_sha256": sha256(second),
            "pixel_identical_exports": sha256(original) == sha256(second),
            "clean_machine_tested": False, "scientific_map_admitted": False}
