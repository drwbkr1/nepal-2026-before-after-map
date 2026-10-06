"""Add a standalone APRX to the exact existing owner-local atlas evidence bundle."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

from arcgis_demo_roundtrip import inventory, local_source, pixel_digest, reject_links, sha256, write_new
from gis_experiment_atlas_001 import PRINCIPAL_MAPS, RASTERS
from package_gis_experiment_atlas_001 import member_path, seal_zip

BUNDLE_SHA256 = "247fe982f834d30dd612a5a25bad0d424c96ff265879da455a14cd228f8af0ab"
PROJECT_SHA256 = "d92af6a2423c9b792a165451c26e7bfc01a5ba15b15a70cd54aa0fac12e95caa"
TOOLBOXES = {
    "Experiment.pyt": "b235681f2ea6c62ca35632dbe36e73792a2ad8938bb742cfedb7abc72e829f67",
    "Experiment.pyt.xml": "85bdaa034f792978f0e41c2d5119a3e46a0ecd58078d5d39ae09310b73011e22",
}


def extract_validated_bundle(archive, target, expected_sha256):
    """Hash-bound extraction; verify every manifest entry without changing source bytes."""
    for path in (archive, target):
        reject_links(path)
    archive, target = archive.resolve(), target.resolve()
    if target.exists() or archive.is_relative_to(target):
        raise ValueError("Fresh disjoint extraction required")
    if sha256(archive) != expected_sha256:
        raise ValueError("Existing bundle identity differs")
    with zipfile.ZipFile(archive) as reader:
        names = reader.namelist()
        if len(names) != len(set(names)) or reader.testzip() is not None:
            raise ValueError("ZIP inventory or CRC differs")
        for name in names:
            member_path(name)
        target.mkdir(parents=True, exist_ok=False)
        for name in names:
            path = target.joinpath(*member_path(name).parts)
            path.parent.mkdir(parents=True, exist_ok=True)
            with reader.open(name) as source, path.open("xb") as destination:
                shutil.copyfileobj(source, destination)
    manifest = json.loads((target / "artifact-manifest.json").read_text(encoding="utf-8"))
    files = inventory(target)
    if {name: value for name, value in files.items() if name != "artifact-manifest.json"} != manifest["files"]:
        raise ValueError("Extracted bundle manifest differs")
    return files


def compare_original_files(baseline, current):
    allowed = {"README.md", "artifact-manifest.json"}
    unchanged = [name for name in baseline if name not in allowed]
    if any(current.get(name) != baseline[name] for name in unchanged):
        raise ValueError("An existing raster, package, export, catalog or metadata file changed")
    return len(unchanged)


def inspect_direct_project(project_path, root, output):
    """Fresh-process direct open and export, rejecting operational source fallback."""
    import arcpy
    arcpy.SetLogHistory(False)
    arcpy.SetLogMetadata(False)
    project = arcpy.mp.ArcGISProject(str(project_path))
    for value in (project.homeFolder, project.defaultGeodatabase, project.defaultToolbox):
        local_source(value, root)
        if not Path(value).exists():
            raise ValueError("Writable local default missing")
    if project.listBrokenDataSources():
        raise ValueError("Standalone project has broken sources")
    sources = []
    for m in project.listMaps():
        if m.spatialReference.factoryCode != 32645:
            raise ValueError("Project map CRS differs")
        for item in [*m.listLayers(), *m.listTables()]:
            if getattr(item, "isGroupLayer", False):
                continue
            if getattr(item, "isWebLayer", False) or getattr(item, "isBasemapLayer", False):
                raise ValueError("Remote operational source")
            local_source(item.dataSource, root)
            if not arcpy.Exists(item.dataSource):
                raise ValueError("Local operational source missing")
            sources.append({"map": m.name, "name": item.name, "source": str(Path(item.dataSource).relative_to(root))})
    layouts = {layout.name: layout for layout in project.listLayouts()}
    if set(layouts) != set(PRINCIPAL_MAPS) or len(project.listMaps()) != 7:
        raise ValueError("Atlas maps or layouts differ")
    output.mkdir(parents=True, exist_ok=False)
    checks = {}
    for name in PRINCIPAL_MAPS:
        png, pdf = output / (name + ".png"), output / (name + ".pdf")
        layouts[name].exportToPNG(str(png), resolution=150, color_mode="24-BIT_TRUE_COLOR")
        layouts[name].exportToPDF(str(pdf), resolution=150)
        checks[name] = {"rendered_pixels_equal": pixel_digest(png) == pixel_digest(root / "exports" / png.name),
                       "PDF_export_present": pdf.is_file() and pdf.stat().st_size > 0}
    if not all(all(row.values()) for row in checks.values()):
        raise ValueError("Standalone map rendering or PDF export differs")
    write_new(output / "direct-project-inspection.json", {"status": "pass_direct_APRX_open_export",
        "maps": len(project.listMaps()), "layouts": len(layouts), "local_defaults": True,
        "operational_sources": sources, "all_operational_sources_inside_bundle": True,
        "checks": checks, "arcgis_version": arcpy.GetInstallInfo()["Version"],
        "clean_machine_tested": False, "scientific_admission": False})


def deliver(archive, source_project, output):
    for path in (archive, source_project, output):
        reject_links(path)
    archive, source_project, output = (p.resolve() for p in (archive, source_project, output))
    if output.exists() or any(output.is_relative_to(p) or p.is_relative_to(output)
                              for p in (source_project.parent, archive.parent)):
        raise ValueError("Fresh disjoint delivery directory required")
    inputs = {str(archive): BUNDLE_SHA256, str(source_project): PROJECT_SHA256,
              **{str(source_project.parent / name): digest for name, digest in TOOLBOXES.items()}}
    if any(sha256(Path(name)) != digest for name, digest in inputs.items()):
        raise ValueError("Exact existing bundle/project/toolbox inputs required")
    output.mkdir(parents=True, exist_ok=False)
    receipt = {"status": "failed", "input_hashes": inputs, "scientific_admission": False,
               "registration_verified": False, "goal_complete": False, "raster_calculation": False}
    try:
        content = output / "Nepal_Unverified_Atlas"
        baseline = extract_validated_bundle(archive, content, BUNDLE_SHA256)
        for name in TOOLBOXES:
            shutil.copy2(source_project.parent / name, content / name)
        import arcpy
        arcpy.SetLogHistory(False)
        arcpy.SetLogMetadata(False)
        project = arcpy.mp.ArcGISProject(str(source_project))
        project.updateConnectionProperties(str(source_project.parent), str(content), validate=True)
        project.homeFolder = str(content)
        project.defaultGeodatabase = str(content / "Experiment.gdb")
        project.defaultToolbox = str(content / "Experiment.pyt")
        project.updateFolderConnections([{"connectionString": str(content), "isHomeFolder": True}])
        project.updateDatabases([{"databasePath": str(content / "Experiment.gdb"), "isDefaultDatabase": True}])
        destination = content / "Nepal_Unverified_Atlas.aprx"
        project.saveACopy(str(destination))
        del project
        child = subprocess.run([sys.executable, str(Path(__file__).resolve()), "inspect",
            "--project", str(destination), "--source-root", str(content), "--output", str(output / "direct-open")],
            capture_output=True, text=True, timeout=300)
        if child.returncode:
            raise RuntimeError("Fresh direct-project check failed: " + child.stderr[-1500:])
        inspection = json.loads((output / "direct-open/direct-project-inspection.json").read_text(encoding="utf-8"))
        if any(sha256(content / "imagery" / name) != digest for name, digest in RASTERS.items()):
            raise ValueError("Raster identity drift")
        unchanged = compare_original_files(baseline, inventory(content))
        with (content / "README.md").open("a", encoding="utf-8") as stream:
            stream.write("\n## Standalone project\n\nOpen `Nepal_Unverified_Atlas.aprx` directly from this extracted folder, or open the unchanged PPKX. "
                "Keep all files together. The APRX has local writable home, default geodatabase and toolbox. "
                "Direct fresh-process open and all five PNG/PDF exports were checked on the same machine. "
                "Maps, raster values, the PPKX and offline evidence catalog are unchanged. No clean-machine or scientific acceptance is claimed.\n")
        manifest = json.loads((content / "artifact-manifest.json").read_text(encoding="utf-8"))
        manifest.update(standalone_project="Nepal_Unverified_Atlas.aprx", standalone_project_sha256=sha256(destination),
                        extended_from_bundle_sha256=BUNDLE_SHA256,
                        files={name: value for name, value in inventory(content).items() if name != "artifact-manifest.json"})
        (content / "artifact-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        sealed = seal_zip(content, output / "Nepal_Unverified_Atlas_Complete.zip", output / "extracted")
        receipt.update(status="pass_standalone_APRX_delivery", bundle=sealed, inspection=inspection,
            unchanged_existing_files=unchanged, standalone_project_sha256=sha256(destination),
            source_input_bytes_unchanged=True, original_evidence_catalog_unchanged=True, PPKX_unchanged=True)
    except Exception as error:
        import traceback
        receipt.update(error=str(error), traceback=traceback.format_exc())
    finally:
        receipt["inputs_unchanged"] = all(sha256(Path(name)) == digest for name, digest in inputs.items())
        if not receipt["inputs_unchanged"]:
            receipt["status"] = "failed"
        write_new(output / "standalone-delivery-receipt.json", receipt)
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["status"] == "pass_standalone_APRX_delivery" else 1


if __name__ == "__main__":
    os.environ["GDAL_PAM_ENABLED"] = "NO"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("deliver", "inspect"))
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "inspect":
        if args.source_root is None:
            parser.error("--source-root required for inspect")
        for path in (args.project, args.source_root, args.output):
            reject_links(path)
        inspect_direct_project(args.project.resolve(), args.source_root.resolve(), args.output.resolve())
    else:
        if args.bundle is None:
            parser.error("--bundle required for deliver")
        raise SystemExit(deliver(args.bundle, args.project, args.output))
