"""Stage existing visual rasters without processing or changing their pixels.

Outputs are a new local demonstration, never a scientific M6 admission.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_PROJECT = "603010d42bd4f4158c9d793d7dab9a41ce7fc39fe1e437bf11c9c3c39846fd71"
EXPECTED_RASTERS = {
    "before_common_valid_vv_db.tif": "ada055a8a819998ef554d28ec15ae9dd842a92514c8a6e5bcb255a262034c4a3",
    "after_common_valid_vv_db.tif": "90e0c1c00a60b3fcd19ee07e4d610f036c44ca0b29d230ce3266676abfc0a7b7",
}
TITLE = "Nepal 2026 | GIS demonstration | EPSG:32645"
WARNING = (
    "GIS DEMONSTRATION - PARTIAL DATA. Registration is unverified; both full-area QA dispositions remain DEFER.\n"
    "Visual display only: no difference map, measured change, event attribution or validated scientific result."
)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def preflight(project, rasters, output, project_hash=EXPECTED_PROJECT, raster_hashes=None):
    expected = EXPECTED_RASTERS if raster_hashes is None else raster_hashes
    project, rasters, output = map(Path, (project, rasters, output))
    for path in (project, rasters, output):
        for ancestor in (path.absolute(), *path.absolute().parents):
            if ancestor.is_symlink() or getattr(ancestor, "is_junction", lambda: False)():
                raise ValueError("linked path not supported")
    if output.exists():
        raise ValueError("output collision; original attempts must not be reused")
    for source_root in (project.parent.resolve(), rasters.resolve()):
        if output.resolve().is_relative_to(source_root) or source_root.is_relative_to(output.resolve()):
            raise ValueError("input/output trees overlap")
    inputs = {project: project_hash, **{rasters / name: value for name, value in expected.items()}}
    for path, expected_hash in inputs.items():
        if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
            raise ValueError("linked input not supported")
        if not path.is_file() or digest(path) != expected_hash:
            raise ValueError("input missing or hash drift: " + path.name)
    return {str(path.resolve()): value for path, value in inputs.items()}


def stage(source_project, raster_root, output):
    inputs = preflight(source_project, raster_root, output)
    source_project, raster_root, output = (p.resolve() for p in (source_project, raster_root, output))
    output.mkdir(parents=True, exist_ok=False)
    receipt = {"status": "failed", "at_utc": datetime.now(timezone.utc).isoformat(),
               "input_hashes": inputs, "pixel_processing": False, "scientific_admission": False,
               "public_release": False, "clean_machine_tested": False}
    try:
        imagery = output / "imagery"
        imagery.mkdir()
        for name, expected in EXPECTED_RASTERS.items():
            shutil.copyfile(raster_root / name, imagery / name)
            if digest(imagery / name) != expected:
                raise ValueError("copy integrity failed")
        import arcpy
        arcpy.SetLogHistory(False)
        arcpy.SetLogMetadata(False)
        project = arcpy.mp.ArcGISProject(str(source_project))
        maps, layouts = project.listMaps(), project.listLayouts()
        if len(maps) != 2 or len(layouts) != 1:
            raise ValueError("unexpected source project structure")
        seen = set()
        for map_obj in maps:
            layers = map_obj.listLayers()
            if map_obj.spatialReference.factoryCode != 32645 or len(layers) != 1:
                raise ValueError("unexpected map structure or CRS")
            layer = layers[0]
            source = Path(layer.dataSource)
            if layer.isBroken or source.parent.resolve() != raster_root.resolve() or source.name not in EXPECTED_RASTERS:
                raise ValueError("unexpected raster source")
            seen.add(source.name)
            layer.updateConnectionProperties(str(raster_root), str(imagery), validate=True)
            if layer.isBroken or Path(layer.dataSource).resolve() != (imagery / source.name).resolve():
                raise ValueError("staging connection failed")
            # A fixed presentation scale avoids product-format-dependent
            # percentile histograms. This changes display only, not TIFF values,
            # QA masks, registration criteria or scientific thresholds.
            definition = layer.getDefinition("V3")
            colorizer = definition.colorizer
            colorizer.stretchType = "MinimumMaximum"
            colorizer.customStretchMin = -30.0
            colorizer.customStretchMax = 0.0
            colorizer.useCustomStretchMinMax = True
            colorizer.useGammaStretch = False
            layer.setDefinition(definition)
        if seen != set(EXPECTED_RASTERS):
            raise ValueError("both dates are required")
        changed = {"title": 0, "warning": 0}
        for item in layouts[0].listElements("TEXT_ELEMENT"):
            if item.text.startswith("Nepal 2026 |"):
                item.text = TITLE
                changed["title"] += 1
            elif "PARTIAL DATA ONLY." in item.text:
                item.text = WARNING
                changed["warning"] += 1
            elif item.text.startswith("Common valid VV/VH:"):
                item.text += "\nDisplay range: -30 to 0 dB (black to white), identical for both dates; no gamma stretch."
        if changed != {"title": 1, "warning": 1}:
            raise ValueError("expected title and warning not found")
        layouts[0].name = "GIS demonstration - unregistered partial imagery"
        gdb = output / "Demonstration.gdb"
        arcpy.management.CreateFileGDB(str(output), gdb.name)
        # An empty default GDB is omitted by PackageProject. Retain actual
        # source metadata as a standalone table so it travels with the project.
        manifest = gdb / "SourceManifest"
        arcpy.management.CreateTable(str(gdb), manifest.name)
        for name, length in (("Source_ID", 16), ("Acquired", 10), ("Use_Status", 80)):
            arcpy.management.AddField(str(manifest), name, "TEXT", field_length=length)
        with arcpy.da.InsertCursor(str(manifest), ["Source_ID", "Acquired", "Use_Status"]) as cursor:
            cursor.insertRow(("M1-SRC-002", "2026-08-16", "Partial visual only; registration unverified"))
            cursor.insertRow(("M1-SRC-005", "2026-08-28", "Partial visual only; registration unverified"))
        maps[0].addTable(arcpy.mp.Table(str(manifest)))
        toolbox = output / "Demonstration.pyt"
        toolbox.write_text('class Toolbox:\n    def __init__(self):\n        self.label = "GIS Demonstration"\n        self.alias = "gisdemo"\n        self.tools = []\n', encoding="utf-8")
        project.homeFolder = str(output)
        project.defaultGeodatabase = str(gdb)
        project.defaultToolbox = str(toolbox)
        if not arcpy.Exists(str(toolbox)):
            raise ValueError("default toolbox not recognized")
        result = output / "Nepal_GIS_Demonstration.aprx"
        project.saveACopy(str(result))
        receipt.update(status="passed_staged_existing_visuals_only", staged_project=result.name,
                       staged_project_sha256=digest(result), map_count=2, layout_count=1,
                       relabelled_demonstration=True, display_range_db=[-30, 0],
                       raster_values_changed=False, arcgis_version=arcpy.GetInstallInfo()["Version"])
        del project
        gc.collect()
    except Exception as exc:
        receipt["error"] = str(exc)
    finally:
        receipt["original_inputs_unchanged"] = all(digest(Path(p)) == h for p, h in inputs.items())
        if not receipt["original_inputs_unchanged"]:
            receipt["status"] = "failed"
        with (output / "stage-receipt.json").open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, indent=2)
            stream.write("\n")
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["status"].startswith("passed") else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--rasters", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(stage(args.project, args.rasters, args.output))
