#!/usr/bin/env python3
"""One owner-local visual-only ArcGIS panel from gated Landsat QA arrays."""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

from landsat9_pixel_visual_core_001 import CELL, nearest_rank_stretch

TEMPLATE = Path(r"C:\Program Files\ArcGIS\Pro\Resources\ArcToolBox\Services\routingservices\data\Blank.aprx")
PRODUCTS = ("LC09_L2SP_141040_20260810_20260811_02_T1",
            "LC09_L2SP_141040_20260826_20260827_02_T1")
COLORS = np.asarray(((220, 224, 228), (35, 39, 45), (244, 244, 244),
                     (65, 190, 230), (155, 65, 155), (242, 180, 35),
                     (230, 95, 45)), dtype=np.uint8)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(8 * 1024**2), b""):
            h.update(block)
    return h.hexdigest()


def rect(arcpy, x0, y0, x1, y1):
    return arcpy.Polygon(arcpy.Array([
        arcpy.Point(x0, y0), arcpy.Point(x1, y0), arcpy.Point(x1, y1),
        arcpy.Point(x0, y1), arcpy.Point(x0, y0),
    ]))


def _save_raster(arcpy, array: np.ndarray, out: Path, xmin: float, ymin: float) -> None:
    if out.exists():
        raise ValueError("local_panel_output_collision")
    raster = arcpy.NumPyArrayToRaster(array, arcpy.Point(xmin, ymin), CELL, CELL)
    raster.save(str(out))
    arcpy.management.DefineProjection(str(out), arcpy.SpatialReference(32645))
    check = arcpy.Raster(str(out))
    if check.spatialReference.factoryCode != 32645 or check.meanCellWidth != CELL:
        raise ValueError("local_panel_raster_projection_invalid")


def _panel_arrays(attempt: Path, metrics: dict, panel_data: dict) -> tuple[dict, dict, list[str]]:
    qualifying = [key for key in ("AOI-SOURCE", "AOI-UPPER-CORRIDOR")
                  if metrics[key]["visual_status"] != "no_visual_panel_for_aoi"]
    if not qualifying:
        raise ValueError("no_qualifying_aoi")
    loaded = {}
    for key in qualifying:
        with np.load(attempt / panel_data[key]["npz"], allow_pickle=False) as source:
            loaded[key] = {name: source[name].copy() for name in source.files}
    minima = [float(loaded[key]["xmin"]) for key in qualifying]
    maxima = [float(loaded[key]["ymax"]) for key in qualifying]
    xmin = min(minima)
    ymax = max(maxima)
    xmax = max(float(loaded[key]["xmin"]) + loaded[key]["weights"].shape[1] * CELL for key in qualifying)
    ymin = min(float(loaded[key]["ymax"]) - loaded[key]["weights"].shape[0] * CELL for key in qualifying)
    columns = round((xmax - xmin) / CELL)
    rows = round((ymax - ymin) / CELL)
    if columns <= 0 or rows <= 0 or rows * columns > 5_000_000:
        raise ValueError("panel_extent_invalid")
    stretch = {}
    for band in range(3):
        samples = []
        for key in qualifying:
            item = loaded[key]
            paired = ((item["weights"] > 0) & (item["before_reason"] == 7)
                      & (item["after_reason"] == 7))
            samples.append(item["before_bands"][band][paired])
            samples.append(item["after_bands"][band][paired])
        stretch[band] = nearest_rank_stretch(np.concatenate(samples))
    rasters = {"before": np.full((3, rows, columns), 220, dtype=np.uint8),
               "after": np.full((3, rows, columns), 220, dtype=np.uint8)}
    masks = {"before": np.zeros((rows, columns), dtype=np.uint8),
             "after": np.zeros((rows, columns), dtype=np.uint8)}
    for key in qualifying:
        item = loaded[key]
        y0 = round((ymax - float(item["ymax"])) / CELL)
        x0 = round((float(item["xmin"]) - xmin) / CELL)
        h, w = item["weights"].shape
        for date in ("before", "after"):
            reason = item[f"{date}_reason"]
            bands = item[f"{date}_bands"]
            rgb = np.empty((3, h, w), dtype=np.uint8)
            for band in range(3):
                low, high = stretch[band]
                rgb[band] = np.rint(np.clip((bands[band] - low) / (high - low), 0, 1) * 255).astype(np.uint8)
            for code, color in enumerate(COLORS):
                rgb[:, reason == code] = color[:, None]
            outside = item["weights"] <= 0
            rgb[:, outside] = COLORS[0][:, None]
            rasters[date][:, y0:y0+h, x0:x0+w] = rgb
            masks[date][y0:y0+h, x0:x0+w] = np.where(outside, 0, reason + 1)
    return {"xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax,
            "rgb": rasters, "masks": masks, "stretch": stretch}, loaded, qualifying


def build(attempt: Path, metrics: dict, panel_data: dict, mtls: dict,
          source_bands: dict[str, dict[str, Path]], output: Path, arcpy) -> dict:
    if not TEMPLATE.is_file() or output.exists():
        raise ValueError("panel_template_or_output_invalid")
    if (set(source_bands) != {"before", "after"} or any(
            set(source_bands[date]) != {"B7", "B6", "B4"}
            or any(not path.is_file() for path in source_bands[date].values())
            for date in ("before", "after"))):
        raise ValueError("panel_exact_source_bands_missing")
    data, _, qualifying = _panel_arrays(attempt, metrics, panel_data)
    output.mkdir(parents=True, exist_ok=False)
    rgb_paths, mask_paths = {}, {}
    for date in ("before", "after"):
        rgb_paths[date] = output / f"{date}_visual_rgb_b7_b6_b4_epsg32645.tif"
        mask_paths[date] = output / f"{date}_exclusion_class_epsg32645.tif"
        _save_raster(arcpy, data["rgb"][date], rgb_paths[date], data["xmin"], data["ymin"])
        _save_raster(arcpy, data["masks"][date], mask_paths[date], data["xmin"], data["ymin"])
    gdb = output / "Nepal_Landsat_Local.gdb"
    arcpy.management.CreateFileGDB(str(output), gdb.name)
    toolbox = output / "Nepal_Landsat_Local.pyt"
    with toolbox.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write("class Toolbox:\n    def __init__(self):\n        self.label='Nepal Landsat local'\n        self.alias='nepallandsatlocal'\n        self.tools=[]\n")
    project = arcpy.mp.ArcGISProject(str(TEMPLATE))
    for old in list(project.listMaps()):
        project.deleteItem(old)
    project.homeFolder = str(output)
    project.defaultGeodatabase = str(gdb)
    project.defaultToolbox = str(toolbox)
    maps = {}
    for date in ("before", "after"):
        map_obj = project.createMap(f"Landsat-9 {date.title()} Visual Only", "MAP")
        for layer in list(map_obj.listLayers()):
            map_obj.removeLayer(layer)
        map_obj.spatialReference = arcpy.SpatialReference(32645)
        rgb = map_obj.addDataFromPath(str(rgb_paths[date]))
        rgb.name = f"{date.title()} B7/B6/B4 RGB | strict mask colors"
        exclusion = map_obj.addDataFromPath(str(mask_paths[date]))
        exclusion.name = f"{date.title()} exclusion class | inspectable"
        exclusion.visible = False  # Colors are already burned into the RGB view.
        for band in ("B7", "B6", "B4"):
            source = map_obj.addDataFromPath(str(source_bands[date][band]))
            source.name = f"{date.title()} source SR_{band} | inspectable original"
            source.visible = False
        maps[date] = map_obj
    layout = project.createLayout(14, 8.5, "INCH", "Nepal Landsat-9 visual comparison only")
    for date, x0 in (("before", .4), ("after", 7.1)):
        label = date.title() + " | " + mtls[date]["date_acquired"] + " " + mtls[date]["scene_center_time"]
        frame = layout.createMapFrame(rect(arcpy, x0, 2.05, x0 + 6.45, 7.65), maps[date], label)
        frame.camera.setExtent(arcpy.Extent(data["xmin"], data["ymin"], data["xmax"], data["ymax"]))
        frame.camera.scale *= 1.07
        project.createTextElement(layout, rect(arcpy, x0, 7.75, x0 + 6.45, 8.05),
                                  "POLYGON", label, 11, "Segoe UI", "Bold", name=label)
    title = "Nepal 2026 | Landsat-9 before / after | EPSG:32645 | 30 m"
    project.createTextElement(layout, rect(arcpy, .4, 8.12, 13.55, 8.42),
                              "POLYGON", title, 16, "Segoe UI", "Bold", name="Title")
    parts = []
    for key in qualifying:
        m = metrics[key]
        parts.append(f"{key}: footprint {m['before']['footprint_fraction']:.1%} / {m['after']['footprint_fraction']:.1%}; "
                     f"valid {m['before']['strict_usable_fraction']:.1%} / {m['after']['strict_usable_fraction']:.1%}; "
                     f"paired {m['paired_strict_usable_fraction']:.1%}. "
                     + ("PARTIAL / INSUFFICIENT FOR FULL-AREA COMPARISON." if m["visual_status"].startswith("partial") else "VISUAL QA ONLY."))
    project.createTextElement(layout, rect(arcpy, .4, 1.5, 13.55, 2.0),
                              "POLYGON", "  ".join(parts), 8.5, "Segoe UI", "Bold", name="AOI QA")
    legend = "Mask colors: gray outside AOI; dark NoData; white cloud/cirrus/shadow; cyan snow/ice; purple saturation/terrain; yellow aerosol risk; orange nonphysical reflectance."
    project.createTextElement(layout, rect(arcpy, .4, .98, 13.55, 1.45),
                              "POLYGON", legend, 8.5, "Segoe UI", "Regular", name="Mask legend")
    warning = "Visual comparison only. Residual registration not measured; no pixelwise change or event attribution. Original products: " + PRODUCTS[0] + " / " + PRODUCTS[1]
    project.createTextElement(layout, rect(arcpy, .4, .2, 13.55, .93),
                              "POLYGON", warning, 8.5, "Segoe UI", "Bold", name="Claim boundary")
    aprx = output / "Nepal_Landsat9_Visual_Before_After_Local.aprx"
    png = output / "Nepal_Landsat9_Visual_Before_After_Local.png"
    pdf = output / "Nepal_Landsat9_Visual_Before_After_Local.pdf"
    project.saveACopy(str(aprx))
    layout.exportToPNG(str(png), resolution=160, color_mode="24-BIT_TRUE_COLOR")
    layout.exportToPDF(str(pdf), resolution=160, image_quality="BEST")
    return {"status": "built_visual_panel_pending_fresh_reopen", "qualifying_aois": qualifying,
            "shared_nearest_rank_stretch": {str(b): list(v) for b, v in data["stretch"].items()},
            "aprx_sha256": digest(aprx), "png_sha256": digest(png), "pdf_sha256": digest(pdf),
            "rgb_sha256": {d: digest(p) for d, p in rgb_paths.items()},
            "mask_sha256": {d: digest(p) for d, p in mask_paths.items()},
            "wkid": 32645, "residual_registration_measured": False,
            "change_analysis_or_attribution": False}


def reopen(output: Path, arcpy) -> dict:
    aprx = output / "Nepal_Landsat9_Visual_Before_After_Local.aprx"
    png = output / "Nepal_Landsat9_Visual_Before_After_Local.png"
    pdf = output / "Nepal_Landsat9_Visual_Before_After_Local.pdf"
    if not all(p.is_file() and p.stat().st_size > 1000 for p in (aprx, png, pdf)):
        raise ValueError("panel_outputs_missing")
    project = arcpy.mp.ArcGISProject(str(aprx))
    if (len(project.listMaps()) != 2 or len(project.listLayouts()) != 1
            or Path(project.homeFolder).resolve() != output.resolve()
            or not Path(project.defaultGeodatabase).is_dir()
            or not Path(project.defaultToolbox).is_file()):
        raise ValueError("panel_project_defaults_or_layout_invalid")
    for map_obj in project.listMaps():
        if (map_obj.spatialReference.factoryCode != 32645
                or len(map_obj.listLayers()) != 5
                or any(layer.isBroken for layer in map_obj.listLayers())):
            raise ValueError("panel_broken_or_missing_layer")
    reopened = output / "Nepal_Landsat9_Visual_Before_After_Reopen.png"
    if reopened.exists():
        raise ValueError("panel_reopen_output_collision")
    project.listLayouts()[0].exportToPNG(str(reopened), resolution=160, color_mode="24-BIT_TRUE_COLOR")
    return {"status": "pass_fresh_process_reopen", "map_count": 2, "broken_layer_count": 0,
            "reopen_png_sha256": digest(reopened), "public_derived_pixel_publication": False}


def fresh_reopen(output: Path) -> dict:
    try:
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), "reopen", str(output)],
                                capture_output=True, text=True, timeout=900, check=False)
        data = json.loads(result.stdout)
        if result.returncode or data.get("status") != "pass_fresh_process_reopen":
            raise ValueError("panel_fresh_reopen_failed")
        return data
    except (OSError, ValueError, subprocess.TimeoutExpired):
        raise ValueError("panel_fresh_reopen_failed") from None


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "reopen":
        raise SystemExit(12)
    try:
        import arcpy  # type: ignore[import-not-found]
        print(json.dumps(reopen(Path(sys.argv[2]), arcpy), sort_keys=True))
    except BaseException:
        print(json.dumps({"status": "stopped", "code": "panel_fresh_reopen_failed"}))
        raise SystemExit(20)
