"""Presentation atlas from unchanged experimental rasters and approved AOIs.

No new raster calculation, clipping, registration, or scientific admission.
The scientific M6 contract remains separate from this unverified handoff.
"""
from __future__ import annotations

import argparse
import gc
import json
import os
from pathlib import Path
import shutil

from arcgis_demo_roundtrip import inventory, reject_links, sha256, write_new
from gis_brightness_difference_001 import CREDITS, FORMULA, set_stretch, blue_orange, utc_now
from refine_gis_demonstration_layout_001 import rectangle, style

AOI_HASH = "3d6c9bb39fa9b3ffeddfb0048ddabf30ee4472c0006b78c5c7d58193693ac615"
PROJECT_HASH = "f9629911a0041980f25164d1514de20a4f18459da68a5694da11ca5110a68b39"
RASTERS = {
    "before_common_valid_vv_db.tif": "ada055a8a819998ef554d28ec15ae9dd842a92514c8a6e5bcb255a262034c4a3",
    "after_common_valid_vv_db.tif": "90e0c1c00a60b3fcd19ee07e4d610f036c44ca0b29d230ce3266676abfc0a7b7",
    "delta_vv_db.tif": "ffb9b8e8f2e8a64bd0b57a777dabf5497794e4037f2f6bbef8cff68505f2d4ad",
    "excluded_cells.tif": "cb9b777f138971218b36b7e62633df706347fa3c746c3457a0718a5db5efebbd",
}
PRINCIPAL_MAPS = ["regional_overview", "source_area_comparison", "upper_corridor_comparison", "evidence_map", "limitations_map"]


def aoi_bounds(feature, padding=.05):
    points = [xy for ring in feature["geometry"]["rings"] for xy in ring]
    xs, ys = [xy[0] for xy in points], [xy[1] for xy in points]
    xmin, ymin, xmax, ymax = min(xs), min(ys), max(xs), max(ys)
    if xmax <= xmin or ymax <= ymin or padding < 0:
        raise ValueError("Nonempty extent and nonnegative display padding required")
    dx, dy = (xmax - xmin) * padding, (ymax - ymin) * padding
    return [xmin - dx, ymin - dy, xmax + dx, ymax + dy]


def make_geopackage(path, aoi, sources):
    from osgeo import ogr, osr
    ogr.UseExceptions()
    sr = osr.SpatialReference()
    sr.ImportFromEPSG(32645)
    ds = ogr.GetDriverByName("GPKG").CreateDataSource(str(path))
    layer = ds.CreateLayer("StudyAreas", sr, ogr.wkbPolygon)
    for field in aoi["fields"]:
        definition = ogr.FieldDefn(field["name"], ogr.OFTString)
        definition.SetWidth(field["length"])
        layer.CreateField(definition)
    for row in aoi["features"]:
        geom = ogr.Geometry(ogr.wkbPolygon)
        for coords in row["geometry"]["rings"]:
            ring = ogr.Geometry(ogr.wkbLinearRing)
            for x, y in coords:
                ring.AddPoint_2D(x, y)
            geom.AddGeometry(ring)
        feature = ogr.Feature(layer.GetLayerDefn())
        for field, value in row["attributes"].items():
            feature.SetField(field, value)
        feature.SetGeometry(geom)
        layer.CreateFeature(feature)
    table = ds.CreateLayer("DisplayedSources", None, ogr.wkbNone)
    for field in ("Source_ID", "Acquired", "RasterFile", "SHA256", "Use_Status"):
        table.CreateField(ogr.FieldDefn(field, ogr.OFTString))
    for row in sources:
        feature = ogr.Feature(table.GetLayerDefn())
        for field, value in row.items():
            feature.SetField(field, value)
        table.CreateFeature(feature)
    method = ds.CreateLayer("ExperimentMethod", None, ogr.wkbNone)
    for field in ("Formula", "ReviewStatus", "Interpretation", "Attribution", "Limits"):
        method.CreateField(ogr.FieldDefn(field, ogr.OFTString))
    feature = ogr.Feature(method.GetLayerDefn())
    for field, value in {"Formula": FORMULA, "ReviewStatus": "Unverified GIS experiment",
        "Interpretation": "Not assessed; no geomorphic feature claims",
        "Attribution": "Not assessed; no causal claim",
        "Limits": "Registration unverified; full-area sources defer; 0 brightness difference is not proof of no physical change"}.items():
        feature.SetField(field, value)
    method.CreateFeature(feature)
    ds = None
    reopened = ogr.Open(str(path), 0)
    counts = {reopened.GetLayerByIndex(i).GetName(): reopened.GetLayerByIndex(i).GetFeatureCount()
              for i in range(reopened.GetLayerCount())}
    if counts != {"StudyAreas": 3, "DisplayedSources": 2, "ExperimentMethod": 1}:
        raise ValueError("GeoPackage table counts differ")
    if not reopened.GetLayerByName("StudyAreas").GetSpatialRef().IsSame(sr):
        raise ValueError("GeoPackage CRS differs")
    reopened = None
    return counts


def outline(arcpy, map_obj, path, query=None):
    layer = map_obj.addDataFromPath(str(path))
    layer.name = "Approved search/review extents - not event boundaries"
    if query:
        layer.definitionQuery = query
    sym = layer.symbology
    sym.renderer.symbol.color = {"RGB": [255, 255, 255, 0]}
    sym.renderer.symbol.outlineColor = {"RGB": [20, 75, 86, 100]}
    sym.renderer.symbol.outlineWidth = 1.1
    layer.symbology = sym
    return layer


def stretch_raster(map_obj, path, key):
    import arcpy
    layer = map_obj.addDataFromPath(str(path))
    layer.name = {"after": "28 August 2026 VV gamma0 (dB)", "before": "16 August 2026 VV gamma0 (dB)",
                  "difference": "Unverified after-minus-before brightness (dB)",
                  "exclusions": "0 included; 1 either input invalid"}[key]
    low, high = (-6, 6) if key == "difference" else (0, 1) if key == "exclusions" else (-30, 0)
    set_stretch(layer, low, high)
    if key == "difference":
        blue_orange(arcpy, layer)
    if key == "exclusions":
        definition = layer.getDefinition("V3")
        ramp = arcpy.cim.CreateCIMObjectFromClassName("CIMLinearContinuousColorRamp", "V3")
        for key, values in (("fromColor", [27, 89, 98, 100]), ("toColor", [218, 221, 227, 100])):
            color = arcpy.cim.CreateCIMObjectFromClassName("CIMRGBColor", "V3")
            color.values = values
            setattr(ramp, key, color)
        definition.colorizer.colorRamp = ramp
        layer.setDefinition(definition)
    return layer


def build(source_root, aoi_path, output):
    os.environ["GDAL_PAM_ENABLED"] = "NO"
    for p in (source_root, aoi_path, output):
        reject_links(p)
    source_root, aoi_path, output = (p.resolve() for p in (source_root, aoi_path, output))
    if output.exists() or output.is_relative_to(source_root) or source_root.is_relative_to(output):
        raise ValueError("New disjoint output required")
    source_project = source_root / "Nepal_Unverified_Brightness_Difference.aprx"
    if sha256(source_project) != PROJECT_HASH or sha256(aoi_path) != AOI_HASH:
        raise ValueError("Project or approved AOI identity drift")
    if any(sha256(source_root / "imagery" / n) != h for n, h in RASTERS.items()):
        raise ValueError("Existing raster identity drift")
    aoi = json.loads(aoi_path.read_text(encoding="utf-8"))
    if aoi["spatialReference"]["wkid"] != 32645:
        raise ValueError("Approved projected AOI required")
    initial_inputs = {str(source_project): PROJECT_HASH, str(aoi_path): AOI_HASH,
                      **{str(source_root / "imagery" / n): h for n, h in RASTERS.items()}}
    # The current ArcGIS source TIFFs/APRX remain unchanged. Only their copy gets new views.
    shutil.copytree(source_root, output, ignore=shutil.ignore_patterns("*.aprx", "exports", "layers", "Index", "*.lock", "build-receipt.json"))
    receipt = {"status": "failed", "at_utc": utc_now(), "input_hashes": initial_inputs,
        "scientific_M6_complete": False, "registration_verified": False,
        "scientific_admission": False, "raster_calculation": False, "new_data_acquisition": False}
    try:
        import arcpy
        arcpy.SetLogHistory(False)
        arcpy.SetLogMetadata(False)
        arcpy.env.overwriteOutput = False
        project = arcpy.mp.ArcGISProject(str(source_project))
        project.updateConnectionProperties(str(source_root), str(output), validate=True)
        gdb = output / "Experiment.gdb"
        project.homeFolder, project.defaultGeodatabase, project.defaultToolbox = str(output), str(gdb), str(output / "Experiment.pyt")
        project.updateFolderConnections([{"connectionString": str(output), "isHomeFolder": True}])
        project.updateDatabases([{"databasePath": str(gdb), "isDefaultDatabase": True}])
        areas = gdb / "StudyAreas"
        arcpy.management.CreateFeatureclass(str(gdb), "StudyAreas", "POLYGON", spatial_reference=arcpy.SpatialReference(32645))
        for field in aoi["fields"]:
            arcpy.management.AddField(str(areas), field["name"], "TEXT", field_length=field["length"])
        fields = [field["name"] for field in aoi["fields"]]
        with arcpy.da.InsertCursor(str(areas), ["SHAPE@", *fields]) as cursor:
            for row in aoi["features"]:
                cursor.insertRow([arcpy.AsShape(row["geometry"], True), *[row["attributes"][field] for field in fields]])
        sources = [{"Source_ID": source, "Acquired": date, "RasterFile": filename,
                    "SHA256": RASTERS[filename], "Use_Status": "Unverified display; original full-area defer"}
            for source, date, filename in (("M1-SRC-002", "2026-08-16", "before_common_valid_vv_db.tif"),
                                           ("M1-SRC-005", "2026-08-28", "after_common_valid_vv_db.tif"))]
        gpkg_counts = make_geopackage(output / "ExperimentMetadata.gpkg", aoi, sources)
        (output / "approved-study-areas-epsg32645.json").write_bytes(aoi_path.read_bytes())
        methods = output / "METHOD.json"
        write_new(methods, {"formula": FORMULA, "sources": sources, "aoi_sha256": AOI_HASH,
            "derived_rasters": {n: h for n, h in RASTERS.items() if n in {"delta_vv_db.tif", "excluded_cells.tif"}},
            "observation": "Unverified numeric radar-brightness difference, not an admitted landscape-change feature",
            "interpretation": "not assessed", "attribution": "not assessed",
            "registration_verified": False, "original_full_area_disposition": "defer",
            "colors": "blue decreases / orange increases, -6 to +6 dB display only; values remain unclipped",
            "exclusions": "0 included; 1 either original input invalid; outside input rectangle has no observation",
            "study_geometry_role": "approved M1 search/review extents, not event boundaries",
            "credits": CREDITS})
        old_maps = project.listMaps()
        before = next(m for m in old_maps if m.name.startswith("16 August"))
        after = next(m for m in old_maps if m.name.startswith("28 August"))
        evidence = next(m for m in old_maps if m.name.startswith("Unverified"))
        evidence.name = "evidence_map"
        maps = {"evidence_map": evidence}
        for key in PRINCIPAL_MAPS:
            if key == "evidence_map":
                continue
            m = project.createMap(key, "MAP")
            for layer in m.listLayers():
                m.removeLayer(layer)
            m.spatialReference = arcpy.SpatialReference(32645)
            if key == "limitations_map":
                stretch_raster(m, output / "imagery/excluded_cells.tif", "exclusions")
            else:
                stretch_raster(m, output / "imagery/after_common_valid_vv_db.tif", "after")
                if key in {"source_area_comparison", "upper_corridor_comparison"}:
                    layer = stretch_raster(m, output / "imagery/before_common_valid_vv_db.tif", "before")
                    layer.visible = False
            query = "AOI_ID <> 'AOI-OVERVIEW'" if key in {"evidence_map", "limitations_map"} else None
            outline(arcpy, m, areas, query)
            maps[key] = m
        for m in (before, after, evidence):
            outline(arcpy, m, areas, "AOI_ID <> 'AOI-OVERVIEW'")
        features = {row["attributes"]["AOI_ID"]: row for row in aoi["features"]}
        old_camera = project.listLayouts()[0].listElements("MAPFRAME_ELEMENT", "difference")[0].camera
        e = old_camera.getExtent()
        display_extent = [e.XMin, e.YMin, e.XMax, e.YMax]
        # The previous triptych stays in its original handoff. This fresh atlas has
        # five principal layouts, all with the new extent-outline explanation.
        for old_layout in project.listLayouts():
            project.deleteItem(old_layout)
        extents = {"regional_overview": aoi_bounds(features["AOI-OVERVIEW"]),
                   "source_area_comparison": aoi_bounds(features["AOI-SOURCE"]),
                   "upper_corridor_comparison": aoi_bounds(features["AOI-UPPER-CORRIDOR"]),
                   "evidence_map": display_extent, "limitations_map": display_extent}
        export_root, layer_root = output / "exports", output / "layers"
        export_root.mkdir()
        layer_root.mkdir()
        export_rows = []
        titles = {"regional_overview": "Nepal | study extents and available imagery",
                  "source_area_comparison": "Source-area search extent | before and after",
                  "upper_corridor_comparison": "Upper-corridor search extent | before and after",
                  "evidence_map": "Unverified radar brightness difference",
                  "limitations_map": "Existing input validity | exclusions and coverage gaps"}
        for key in PRINCIPAL_MAPS:
            layout = project.createLayout(13., 8.5, "INCH", key)
            def text(name, content, x, y, w, h, size):
                return project.createTextElement(layout, rectangle(arcpy, x, y, w, h), "POLYGON", content,
                    text_size=size, font_family_name="Arial", name=name)
            text("Title", titles[key], .4, 7.94, 12.2, .35, 21)
            text("Dates and CRS", "16 and 28 August 2026 | Sentinel-1D ASF HyP3 RTC | WGS 84 / UTM 45N, EPSG:32645", .4, 7.48, 12.2, .26, 11)
            text("Review status", "UNVERIFIED GIS EXPERIMENT | No scientific admission, geomorphic interpretation or event attribution", .4, 7.14, 12.2, .24, 10)
            comparative = key in {"source_area_comparison", "upper_corridor_comparison"}
            frame_maps = [(before, "16 August 2026 | Before"), (after, "28 August 2026 | After")] if comparative else [(maps[key], "28 August display" if key == "regional_overview" else "28 August minus 16 August" if key == "evidence_map" else "Included / excluded cells")]
            frames = []
            for i, (m, title) in enumerate(frame_maps):
                x, width = (.4 + 6.4 * i, 5.8) if comparative else (.4, 12.2)
                frame = layout.createMapFrame(rectangle(arcpy, x, 1.70, width, 5.08), m, key + str(i))
                frame.camera.setExtent(arcpy.Extent(*extents[key]))
                if frames:
                    frame.camera.X, frame.camera.Y, frame.camera.scale = frames[0].camera.X, frames[0].camera.Y, frames[0].camera.scale
                frames.append(frame)
                maps[key].defaultCamera = frame.camera
                text("Frame " + str(i), title, x, 6.87, width, .23, 11)
                arrow = layout.createMapSurroundElement(arcpy.Point(x + .18, 1.45), "NORTH_ARROW", frame,
                    style(project, "NORTH_ARROW", "ArcGIS North 1"), key + " true north " + str(i))
                arrow.elementWidth, arrow.elementHeight = .18, .30
                definition = arrow.getDefinition("V3")
                definition.northType, definition.calibrationAngle = "TrueNorth", 0.
                arrow.setDefinition(definition)
                bar = layout.createMapSurroundElement(rectangle(arcpy, x + .6, 1.22, 1.8, .25), "SCALE_BAR", frame,
                    style(project, "SCALE_BAR", "Alternating Scale Bar 1 Metric"), key + " km " + str(i))
                definition = bar.getDefinition("V3")
                definition.unitLabel, definition.division, definition.divisions = "km", 1. if key == "source_area_comparison" else 10. if key == "regional_overview" else 5., 2
                definition.divisionsBeforeZero, definition.subdivisions, definition.fittingStrategy = 0, 1, "AdjustFrame"
                definition.labelSymbol.symbol.height = definition.unitLabelSymbol.symbol.height = 8.
                bar.setDefinition(definition)
            legends = {"regional_overview": "Grayscale VV gamma0: -30 to 0 dB | Outline: approved search/review extent, not event perimeter",
                "source_area_comparison": "Both dates: same -30 to 0 dB grayscale | Outline: approved search/review extent",
                "upper_corridor_comparison": "Both dates: same -30 to 0 dB grayscale | Outline: approved search/review extent",
                "evidence_map": "BLUE: decreased brightness | 0: no dB difference | ORANGE: increased brightness | Display: -6 to +6 dB",
                "limitations_map": "TEAL = 0: both inputs valid | GRAY = 1: either input invalid | WHITE outside grid: no observation"}
            text("Legend", legends[key], .4, .94, 12.2, .25, 10)
            text("Exclusions and limits", "Outlines: approved search/review extents, not event boundaries. Blank imagery excludes existing layover, shadow or NoData.\nRegistration unverified; full-area sources defer. 10 m posting is not accuracy. No alignment correction, normalization or detection; 0 does not prove no physical change.", .4, .48, 12.2, .40, 9)
            text("Credits", CREDITS + "\nHyP3 doi:10.5281/zenodo.3962581 | GAMMA doi:10.5281/zenodo.3962936 | Independent demonstration, no endorsement.", .4, .05, 12.2, .36, 8.5)
            if any(t.isOverflowing for t in layout.listElements("TEXT_ELEMENT")):
                raise ValueError("Layout text overflow: " + key)
            png, pdf = export_root / (key + ".png"), export_root / (key + ".pdf")
            layout.exportToPNG(str(png), resolution=150, color_mode="24-BIT_TRUE_COLOR")
            layout.exportToPDF(str(pdf), resolution=150)
            export_rows.append({"map_id": key, "png": {"file": png.name, "bytes": png.stat().st_size, "sha256": sha256(png)},
                                "pdf": {"file": pdf.name, "bytes": pdf.stat().st_size, "sha256": sha256(pdf)}})
        for filename, m, source_name in [("before.lyrx", before, "before_common_valid_vv_db.tif"),
            ("after.lyrx", after, "after_common_valid_vv_db.tif"), ("difference.lyrx", evidence, "delta_vv_db.tif"),
            ("exclusions.lyrx", maps["limitations_map"], "excluded_cells.tif"),
            ("study-areas.lyrx", maps["regional_overview"], "StudyAreas")]:
            layer = next(layer for layer in m.listLayers() if Path(layer.dataSource).name == source_name)
            layer.saveACopy(str(layer_root / filename))
        if project.listBrokenDataSources():
            raise ValueError("Broken atlas source")
        result = output / "Nepal_Unverified_Atlas.aprx"
        project.saveACopy(str(result))
        receipt.update(status="passed_unverified_atlas_build", project=result.name, project_sha256=sha256(result),
            principal_maps=PRINCIPAL_MAPS, map_count=len(project.listMaps()), layout_count=len(project.listLayouts()),
            layer_files=5, exports=export_rows, gpkg_counts=gpkg_counts, approved_AOI_geometry_unchanged=True,
            view_extents=extents, raster_values_unchanged=True, arcgis_version=arcpy.GetInstallInfo()["Version"])
        del project
        gc.collect()
    except Exception as exc:
        import traceback
        receipt["error"], receipt["traceback"] = str(exc), traceback.format_exc()
    finally:
        receipt["inputs_unchanged"] = all(sha256(Path(p)) == h for p, h in initial_inputs.items())
        receipt["copied_rasters_unchanged"] = all(sha256(output / "imagery" / n) == h for n, h in RASTERS.items())
        if not receipt["inputs_unchanged"] or not receipt["copied_rasters_unchanged"]:
            receipt["status"] = "failed"
        write_new(output / "atlas-build-receipt.json", receipt)
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["status"].startswith("passed") else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--aoi", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(build(args.source_root, args.aoi, args.output))
