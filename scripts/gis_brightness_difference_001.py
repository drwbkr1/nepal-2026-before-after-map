"""Unverified after-minus-before dB experiment on two exact existing grids.

No registration, normalization, detection, attribution, or source acquisition.
ArcGIS imports are delayed so the arithmetic can be tested portably.
"""
from __future__ import annotations

import argparse
import gc
import json
import math
import os
from pathlib import Path
import shutil

import numpy as np

from arcgis_demo_roundtrip import reject_links, sha256, write_new
from export_gis_swipe_renders_001 import world_bounds
from refine_gis_demonstration_layout_001 import rectangle, style
from stage_gis_demonstration_001 import EXPECTED_RASTERS

LABEL = "Unverified radar brightness difference"
FORMULA = "delta_vv_db = after_vv_db - before_vv_db"
COLORS = [[33, 102, 172, 100], [247, 247, 247, 100], [230, 97, 1, 100]]
CREDITS = "ASF DAAC HyP3 2026. Contains modified Copernicus Sentinel data 2026, processed by ESA."
PROJECT_HASH = "de4e50f2db7a3c0f308a9f11d122131756c85e0dd3a45954b466133374566af0"


def utc_now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def brightness_difference(before, after, before_nodata=np.nan, after_nodata=np.nan):
    """Return Float32 signed dB and uint8 exclusion (0 included, 1 excluded)."""
    before, after = np.asarray(before), np.asarray(after)
    if before.ndim != 2 or before.shape != after.shape or before.size == 0:
        raise ValueError("Two nonempty arrays on the same grid required")
    if before.dtype.kind != "f" or after.dtype.kind != "f":
        raise ValueError("Inputs must be floating-point dB values, not display colors")
    valid = np.isfinite(before) & np.isfinite(after)
    for values, nodata in ((before, before_nodata), (after, after_nodata)):
        if nodata is not None and math.isfinite(nodata):
            valid &= values != nodata
    delta = np.full(before.shape, np.nan, dtype=np.float32)
    delta[valid] = (after[valid].astype(np.float64) - before[valid].astype(np.float64)).astype(np.float32)
    if not np.isfinite(delta[valid]).all():
        raise ValueError("Difference cannot be represented as Float32")
    return delta, (~valid).astype(np.uint8)


def matching_grid(first, second):
    if first != second:
        raise ValueError("Grid mismatch: no warp or alignment correction is allowed")
    return first


def header(dataset):
    from osgeo import gdal, osr
    expected = osr.SpatialReference()
    expected.ImportFromEPSG(32645)
    spatial = dataset.GetSpatialRef()
    gt = dataset.GetGeoTransform()
    if (spatial is None or not spatial.IsSame(expected) or dataset.RasterCount != 1
            or dataset.GetRasterBand(1).DataType != gdal.GDT_Float32
            or gt[1:] != (10., 0., gt[3], 0., -10.)
            or not all(math.isfinite(x) for x in gt)):
        raise ValueError("Expected one north-up Float32 EPSG:32645 10 m band")
    return {"wkid": 32645, "width": dataset.RasterXSize, "height": dataset.RasterYSize,
            "geotransform": list(gt)}


def write_tiff(path, values, reference, *, units, byte=False):
    from osgeo import gdal
    if path.exists():
        raise ValueError("Output collision")
    ds = gdal.GetDriverByName("GTiff").Create(str(path), values.shape[1], values.shape[0], 1,
        gdal.GDT_Byte if byte else gdal.GDT_Float32, options=["TILED=YES", "COMPRESS=LZW"])
    ds.SetSpatialRef(reference.GetSpatialRef())
    ds.SetGeoTransform(reference.GetGeoTransform())
    ds.SetMetadata({"EXPERIMENT": "unverified", "REGISTRATION_VERIFIED": "NO",
                    "FORMULA": FORMULA, "BEFORE_DATE": "2026-08-16", "AFTER_DATE": "2026-08-28"})
    band = ds.GetRasterBand(1)
    band.SetUnitType(units)
    band.SetDescription("0 included; 1 either input invalid" if byte else LABEL)
    if not byte:
        band.SetNoDataValue(float("nan"))
    band.WriteArray(values)
    band.ComputeStatistics(False)
    ds.FlushCache()
    ds = None
    reopened = gdal.OpenEx(str(path), gdal.OF_RASTER | gdal.OF_READONLY)
    actual = reopened.ReadAsArray()
    if not np.array_equal(actual, values, equal_nan=True):
        raise ValueError("Output cell round-trip differs")
    if reopened.GetGeoTransform() != reference.GetGeoTransform() or not reopened.GetSpatialRef().IsSame(reference.GetSpatialRef()):
        raise ValueError("Output grid differs")
    reopened = None
    return {"file": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)}


def derive(raster_root, output):
    os.environ["GDAL_PAM_ENABLED"] = "NO"
    from osgeo import gdal
    gdal.UseExceptions()
    for p in (raster_root, output):
        reject_links(p)
    raster_root, output = raster_root.resolve(), output.resolve()
    if output.exists() or output.is_relative_to(raster_root) or raster_root.is_relative_to(output):
        raise ValueError("Output must be new and disjoint")
    inputs = {name: sha256(raster_root / name) for name in EXPECTED_RASTERS}
    if inputs != EXPECTED_RASTERS:
        raise ValueError("Input identity differs")
    output.mkdir(parents=True)
    receipt = {"status": "failed", "at_utc": utc_now(), "formula": FORMULA, "input_sha256": inputs,
               "registration_verified": False, "scientific_admission": False}
    datasets = []
    try:
        datasets = [gdal.OpenEx(str(raster_root / name), gdal.OF_RASTER | gdal.OF_READONLY) for name in EXPECTED_RASTERS]
        grid = matching_grid(*[header(ds) for ds in datasets])
        values = [ds.ReadAsArray() for ds in datasets]
        delta, excluded = brightness_difference(*values, *[ds.GetRasterBand(1).GetNoDataValue() for ds in datasets])
        if not np.any(excluded == 0):
            raise ValueError("No common valid cells")
        valid_values = delta[excluded == 0]
        outputs = [write_tiff(output / "delta_vv_db.tif", delta, datasets[0], units="dB"),
                   write_tiff(output / "excluded_cells.tif", excluded, datasets[0], units="flag", byte=True)]
        receipt.update(status="passed_unverified_arithmetic", grid=grid, outputs=outputs,
            valid_cells=int(valid_values.size), excluded_cells=int(np.count_nonzero(excluded)),
            numeric_min_db=float(valid_values.min()), numeric_max_db=float(valid_values.max()),
            display_range_db=[-6, 6], numeric_values_clamped=False,
            validity="finite values in both exact inputs; original NaN/NoData retained",
            output_cells_reopened_equal=True, grid_changed=False, source_values_changed=False)
    except Exception as exc:
        receipt["error"] = str(exc)
    finally:
        datasets.clear()
        receipt["inputs_unchanged"] = all(sha256(raster_root / n) == h for n, h in inputs.items())
        if not receipt["inputs_unchanged"]:
            receipt["status"] = "failed"
        write_new(output / "calculation-receipt.json", receipt)
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["status"].startswith("passed") else 1


def set_stretch(layer, low, high):
    sym = layer.symbology
    sym.updateColorizer("RasterStretchColorizer")
    layer.symbology = sym
    definition = layer.getDefinition("V3")
    c = definition.colorizer
    c.stretchType = "MinimumMaximum"
    c.useCustomStretchMinMax = True
    c.customStretchMin, c.customStretchMax = float(low), float(high)
    c.useGammaStretch = False
    # Five native legend positions keep zero explicitly centered.
    if c.stretchClasses:
        for i, entry in enumerate(c.stretchClasses):
            entry.value = low + (high - low) * i / (len(c.stretchClasses) - 1)
            entry.label = str(entry.value) if i in (0, len(c.stretchClasses) - 1) else ""
        c.useAdvancedLabeling = True
    layer.setDefinition(definition)


def blue_orange(arcpy, layer):
    definition = layer.getDefinition("V3")
    colors = []
    for values in COLORS:
        color = arcpy.cim.CreateCIMObjectFromClassName("CIMRGBColor", "V3")
        color.values = values
        colors.append(color)
    parts = []
    for first, second in zip(colors, colors[1:]):
        ramp = arcpy.cim.CreateCIMObjectFromClassName("CIMLinearContinuousColorRamp", "V3")
        ramp.fromColor, ramp.toColor = first, second
        parts.append(ramp)
    ramp = arcpy.cim.CreateCIMObjectFromClassName("CIMMultipartColorRamp", "V3")
    ramp.colorRamps, ramp.weights = parts, [1., 1.]
    definition.colorizer.colorRamp = ramp
    layer.setDefinition(definition)


def build(source_project, raster_root, calculation, output):
    """Fresh editable maps, native layouts/renders, source metadata, writable defaults."""
    os.environ["GDAL_PAM_ENABLED"] = "NO"
    for p in (source_project, raster_root, calculation, output):
        reject_links(p)
    if output.exists():
        raise ValueError("Fresh output directory required")
    for source_root in (source_project.parent.resolve(), raster_root.resolve(), calculation.resolve()):
        if output.resolve().is_relative_to(source_root) or source_root.is_relative_to(output.resolve()):
            raise ValueError("Input and output trees must be disjoint")
    if sha256(source_project) != PROJECT_HASH:
        raise ValueError("Source presentation project differs")
    for name, expected in EXPECTED_RASTERS.items():
        if sha256(raster_root / name) != expected:
            raise ValueError("Input identity differs")
    calc = json.loads((calculation / "calculation-receipt.json").read_text(encoding="utf-8"))
    if calc["status"] != "passed_unverified_arithmetic":
        raise ValueError("Calculation did not pass")
    for item in calc["outputs"]:
        if sha256(calculation / item["file"]) != item["sha256"]:
            raise ValueError("Calculation output differs")
    output.mkdir(parents=True)
    receipt = {"status": "failed", "at_utc": utc_now(), "scientific_admission": False,
               "registration_verified": False, "clean_machine_tested": False}
    try:
        import arcpy
        from PIL import Image
        arcpy.SetLogHistory(False)
        arcpy.SetLogMetadata(False)
        arcpy.env.overwriteOutput = False
        imagery, exports, layers = [output / n for n in ("imagery", "exports", "layers")]
        for p in (imagery, exports, layers):
            p.mkdir()
        for name in EXPECTED_RASTERS:
            shutil.copyfile(raster_root / name, imagery / name)
        for item in calc["outputs"]:
            shutil.copyfile(calculation / item["file"], imagery / item["file"])
        original = arcpy.mp.ArcGISProject(str(source_project))
        old_frames = sorted(original.listLayouts()[0].listElements("MAPFRAME_ELEMENT"), key=lambda f: f.elementPositionX)
        camera = old_frames[0].camera
        project = arcpy.mp.ArcGISProject(str(Path(arcpy.GetInstallInfo()["InstallDir"]) / "Resources/ArcToolBox/Services/routingservices/data/Blank.aprx"))
        for m in project.listMaps():
            project.deleteItem(m)
        for l in project.listLayouts():
            project.deleteItem(l)
        gdb = output / "Experiment.gdb"
        arcpy.management.CreateFileGDB(str(output), gdb.name)
        table = str(gdb / "SourceManifest")
        arcpy.management.CreateTable(str(gdb), "SourceManifest")
        for name, length in (("Source_ID", 16), ("Acquired", 10), ("Use_Status", 100)):
            arcpy.management.AddField(table, name, "TEXT", field_length=length)
        with arcpy.da.InsertCursor(table, ["Source_ID", "Acquired", "Use_Status"]) as cursor:
            for source, date in (("M1-SRC-002", "2026-08-16"), ("M1-SRC-005", "2026-08-28")):
                cursor.insertRow([source, date, "Unverified brightness experiment; original full-area disposition defer"])
        toolbox = output / "Experiment.pyt"
        toolbox.write_text('class Toolbox:\n    def __init__(self):\n        self.label = "Unverified GIS Experiment"\n        self.alias = "unverifiedgis"\n        self.tools = []\n', encoding="utf-8")
        project.homeFolder, project.defaultGeodatabase, project.defaultToolbox = str(output), str(gdb), str(toolbox)
        project.updateFolderConnections([{"connectionString": str(output), "isHomeFolder": True}])
        project.updateDatabases([{"databasePath": str(gdb), "isDefaultDatabase": True}])
        specs = [("before", "16 August 2026 | Before", "before_common_valid_vv_db.tif"),
                 ("after", "28 August 2026 | After", "after_common_valid_vv_db.tif"),
                 ("difference", LABEL, "delta_vv_db.tif")]
        maps, rasters = {}, {}
        for key, title, filename in specs:
            m = project.createMap(title, "MAP")
            for layer in m.listLayers():
                m.removeLayer(layer)
            m.spatialReference = arcpy.SpatialReference(32645)
            layer = m.addDataFromPath(str(imagery / filename))
            layer.name = "After minus before VV (dB), unverified" if key == "difference" else title + " VV gamma0 (dB)"
            set_stretch(layer, -6 if key == "difference" else -30, 6 if key == "difference" else 0)
            if key == "difference":
                blue_orange(arcpy, layer)
                exclusions = m.addDataFromPath(str(imagery / "excluded_cells.tif"))
                exclusions.name = "Exclusions: 1 either input invalid; 0 included"
                set_stretch(exclusions, 0, 1)
                exclusions.visible = False
                exclusions.saveACopy(str(layers / "exclusions.lyrx"))
            maps[key], rasters[key] = m, layer
            layer.saveACopy(str(layers / (key + ".lyrx")))
            m.defaultCamera = camera
        maps["before"].addTable(arcpy.mp.Table(table))
        layout = project.createLayout(19.8, 8.5, "INCH", "Before after and unverified difference")
        def text(name, content, x, y, w, h, size):
            return project.createTextElement(layout, rectangle(arcpy, x, y, w, h), "POLYGON", content,
                text_size=size, font_family_name="Arial", name=name)
        text("Title", LABEL, .4, 7.84, 19., .48, 25)
        text("Dates and method", "Langtang / Lirung, Nepal | 16 to 28 August 2026 | Sentinel-1D ASF HyP3 RTC | EPSG:32645", .4, 7.4, 19., .34, 13)
        text("Qualification", "Unverified GIS experiment. Colors indicate radar brightness only, not event cause or terrain change.", .4, 7.04, 19., .30, 12)
        frames = {}
        for i, (key, title, _) in enumerate(specs):
            x = .4 + i * 6.4
            frame = layout.createMapFrame(rectangle(arcpy, x, 2.06, 5.9, 4.8), maps[key], key)
            frame.camera.X, frame.camera.Y = camera.X, camera.Y
            frame.camera.heading, frame.camera.scale = camera.heading, camera.scale
            frames[key] = frame
            text(key + " heading", title, x, 6.90, 5.9, .24, 12)
            arrow = layout.createMapSurroundElement(arcpy.Point(x + .18, 1.51), "NORTH_ARROW", frame,
                style(project, "NORTH_ARROW", "ArcGIS North 1"), key + " true north")
            arrow.elementWidth, arrow.elementHeight = .23, .46
            definition = arrow.getDefinition("V3")
            definition.northType = "TrueNorth"
            definition.calibrationAngle = 0.
            arrow.setDefinition(definition)
            bar = layout.createMapSurroundElement(rectangle(arcpy, x + .65, 1.47, 1.8, .3), "SCALE_BAR", frame,
                style(project, "SCALE_BAR", "Alternating Scale Bar 1 Metric"), key + " km")
            definition = bar.getDefinition("V3")
            definition.unitLabel, definition.division, definition.divisions = "km", 5., 2
            definition.divisionsBeforeZero, definition.subdivisions, definition.fittingStrategy = 0, 1, "AdjustFrame"
            definition.labelSymbol.symbol.height = definition.unitLabelSymbol.symbol.height = 9.
            bar.setDefinition(definition)
            text(key + " scale note", "Projected distance, not accuracy", x + .65, 1.10, 2.5, .24, 8)
            legend = layout.createMapSurroundElement(rectangle(arcpy, x + 3.2, 1.44, 2.2, .48), "LEGEND", frame,
                style(project, "LEGEND", "Transparent Background Legend"), key + " legend")
            definition = legend.getDefinition("V3")
            definition.title = "After minus before (dB)" if key == "difference" else "VV gamma0 (dB)"
            definition.showTitle, definition.fittingStrategy = True, "AdjustSize"
            definition.titleSymbol.symbol.height, definition.minFontSize = 9., 8.
            # Keep the hidden exclusions out of the visible display legend.
            definition.items = [item for item in definition.items if "Exclusions" not in item.name]
            for item in definition.items:
                item.showLayerName = item.showHeading = item.showDescription = False
                item.patchHeight, item.patchWidth = 8., 65.
                item.labelSymbol.symbol.height = 9.
            legend.setDefinition(definition)
            text(key + " explicit display scale", "-6     0     +6 dB" if key == "difference" else "-30 to 0 dB", x + 3.2, 1.02, 2.7, .22, 9)
        text("Sign", "BLUE: decreased brightness     0: no dB difference     ORANGE: increased brightness\nFixed -6 to +6 dB colors; values beyond the scale remain in the numeric TIFF. Blank = excluded.", 13.2, .60, 6.0, .48, 10)
        text("Limits", "No registration adjustment, baseline normalization or detection threshold.\nRegistration unverified; both full-area sources remain defer. Zero is not proof of no physical change.", .4, .60, 12.4, .48, 10)
        text("Credits", CREDITS + "\nHyP3 doi:10.5281/zenodo.3962581 | GAMMA doi:10.5281/zenodo.3962936 | Independent demonstration, no agency endorsement.", .4, .10, 19., .44, 10)
        for t in layout.listElements("TEXT_ELEMENT"):
            if t.isOverflowing:
                raise ValueError("Text overflow: " + t.name)
        if project.listBrokenDataSources():
            raise ValueError("Broken data source")
        result = output / "Nepal_Unverified_Brightness_Difference.aprx"
        project.saveACopy(str(result))
        layout.exportToPNG(str(exports / "comparison.png"), resolution=180, color_mode="24-BIT_TRUE_COLOR")
        layout.exportToPDF(str(exports / "comparison.pdf"), resolution=180)
        png = exports / "difference.png"
        frames["difference"].exportToPNG(str(png), resolution=600, world_file=True, color_mode="24-BIT_TRUE_COLOR")
        coeff = [float(v) for v in (exports / "difference.pgw").read_text(encoding="utf-8").splitlines()]
        with Image.open(png) as image:
            size = list(image.size)
        receipt.update(status="passed_fresh_arcgis_build", project=result.name, project_sha256=sha256(result),
            arcgis_version=arcpy.GetInstallInfo()["Version"], maps=3, layouts=1, layer_files=4,
            local_writable_defaults=True, formula=FORMULA, display_range_db=[-6, 6], colors_rgba=COLORS,
            difference_render={"file": png.name, "bytes": png.stat().st_size, "sha256": sha256(png),
                "size": size, "world_file": "difference.pgw", "world_file_sha256": sha256(exports / "difference.pgw"),
                "world_coefficients": coeff, "bounds_easting_northing": world_bounds(coeff, *size)},
            exports=[{"file": p.name, "bytes": p.stat().st_size, "sha256": sha256(p)}
                     for p in (exports / "comparison.png", exports / "comparison.pdf")])
        del project, original
        gc.collect()
    except Exception as exc:
        import traceback
        receipt["error"] = str(exc)
        receipt["traceback"] = traceback.format_exc()
    finally:
        receipt["source_tiffs_unchanged"] = all(sha256(raster_root / n) == h for n, h in EXPECTED_RASTERS.items())
        receipt["source_project_unchanged"] = sha256(source_project) == PROJECT_HASH
        if not receipt["source_tiffs_unchanged"] or not receipt["source_project_unchanged"]:
            receipt["status"] = "failed"
        write_new(output / "build-receipt.json", receipt)
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["status"].startswith("passed") else 1


def native_sign_probe(output):
    """Confirm native colors at -6, 0, +6 with generated disposable squares."""
    os.environ["GDAL_PAM_ENABLED"] = "NO"
    from osgeo import gdal, osr
    import arcpy
    from PIL import Image
    output.mkdir(parents=True, exist_ok=False)
    gdal.UseExceptions()
    spatial = osr.SpatialReference()
    spatial.ImportFromEPSG(32645)
    values = np.repeat(np.array([[-6., 0., 6.]], dtype=np.float32), 20, axis=1)
    values = np.repeat(values, 20, axis=0)
    tif = output / "generated.tif"
    ds = gdal.GetDriverByName("GTiff").Create(str(tif), 60, 20, 1, gdal.GDT_Float32)
    ds.SetSpatialRef(spatial)
    ds.SetGeoTransform((300000., 10., 0., 3100200., 0., -10.))
    ds.GetRasterBand(1).WriteArray(values)
    ds.GetRasterBand(1).ComputeStatistics(False)
    ds = None
    project = arcpy.mp.ArcGISProject(str(Path(arcpy.GetInstallInfo()["InstallDir"]) / "Resources/ArcToolBox/Services/routingservices/data/Blank.aprx"))
    m = project.createMap("Generated sign probe", "MAP")
    for layer in m.listLayers():
        m.removeLayer(layer)
    m.spatialReference = arcpy.SpatialReference(32645)
    layer = m.addDataFromPath(str(tif))
    set_stretch(layer, -6, 6)
    blue_orange(arcpy, layer)
    layout = project.createLayout(3, 1, "INCH", "Generated sign probe")
    frame = layout.createMapFrame(rectangle(arcpy, 0, 0, 3, 1), m, "Generated only")
    frame.camera.setExtent(arcpy.Extent(300000., 3100000., 300600., 3100200.))
    png = output / "sign-probe.png"
    frame.exportToPNG(str(png), resolution=100, color_mode="24-BIT_TRUE_COLOR")
    with Image.open(png) as image:
        rgb = image.convert("RGB")
        samples = [list(rgb.getpixel((int(rgb.width * fraction), rgb.height // 2))) for fraction in (1 / 6, 1 / 2, 5 / 6)]
    passed = all(max(abs(a - b) for a, b in zip(observed, expected[:3])) <= 3 for observed, expected in zip(samples, COLORS))
    receipt = {"status": "passed_native_display_sign" if passed else "failed", "values_db": [-6, 0, 6],
               "sampled_rgb": samples, "expected_rgba": COLORS, "disposable_inputs_only": True,
               "scientific_validation": False, "arcgis_version": arcpy.GetInstallInfo()["Version"]}
    write_new(output / "receipt.json", receipt)
    print(json.dumps(receipt, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["derive", "build", "sign-probe"])
    parser.add_argument("--rasters", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--project", type=Path)
    parser.add_argument("--calculation", type=Path)
    args = parser.parse_args()
    if args.mode == "sign-probe":
        raise SystemExit(native_sign_probe(args.output))
    if not args.rasters:
        parser.error("derive/build require --rasters")
    if args.mode == "derive":
        raise SystemExit(derive(args.rasters, args.output))
    if not args.project or not args.calculation:
        parser.error("build requires --project and --calculation")
    raise SystemExit(build(args.project, args.rasters, args.calculation, args.output))
