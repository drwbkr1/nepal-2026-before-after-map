"""Owner-local atlas bundle: verified PPKX plus unchanged GIS and export sidecars."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path, PurePosixPath
import shutil
import zipfile

from arcgis_demo_roundtrip import compare, inventory, local_source, reject_links, sha256, write_new
from gis_experiment_atlas_001 import AOI_HASH, PRINCIPAL_MAPS, RASTERS


def compare_atlas_snapshots(before, after):
    """Field names/types are semantic; retain order in the original snapshots."""
    originals = (before, after)
    normalized = []
    for original in originals:
        document = copy.deepcopy(original)
        for map_row in document["maps"]:
            for item in map_row["items"]:
                if "fields" in item:
                    item["fields"] = sorted(item["fields"])
        normalized.append(document)
    return compare(*normalized)


def verify_atlas_package(source, roundtrip):
    """Additional named-field/geometry checks; never rewrite the failed receipt."""
    import arcpy
    arcpy.SetLogHistory(False)
    arcpy.SetLogMetadata(False)
    for path in (source, roundtrip):
        reject_links(path)
    before = json.loads((roundtrip / "before.json").read_text(encoding="utf-8"))
    after = json.loads((roundtrip / "after/snapshot.json").read_text(encoding="utf-8"))
    previous = json.loads((roundtrip / "receipt.json").read_text(encoding="utf-8"))
    if previous.get("changed_after_baseline") or not previous["source_stable_files_unchanged"]:
        raise ValueError("Source changed during original package test")
    if not all(previous["checks"][k] for k in ("layout_metadata_equal", "layout_pixels_equal", "extracted_sources_local")):
        raise ValueError("Original layout or local-source checks failed")
    package = roundtrip / "delivery.ppkx"
    if sha256(package) != previous["package_sha256"]:
        raise ValueError("Preserved package identity drift")
    checks = compare_atlas_snapshots(before, after)
    projects = list((roundtrip / "extracted").rglob("*.aprx"))
    if len(projects) != 1:
        raise ValueError("One extracted project required")
    project = arcpy.mp.ArcGISProject(str(projects[0]))
    extracted_gdb = Path(project.defaultGeodatabase)
    local_source(extracted_gdb, roundtrip / "extracted")
    fields = ["AOI_ID", "NAME", "PURPOSE", "STATUS", "SOURCE_REF"]
    def vector_rows(path):
        rows = []
        with arcpy.da.SearchCursor(str(path), [*fields, "SHAPE@JSON"]) as cursor:
            for row in cursor:
                geometry = json.loads(row[-1])
                rows.append({"attributes": list(row[:-1]), "rings": geometry["rings"]})
        return sorted(rows, key=lambda row: row["attributes"][0])
    native = vector_rows(source / "Experiment.gdb/StudyAreas")
    packaged = vector_rows(extracted_gdb / "StudyAreas")
    checks["study_geometry_and_named_attributes_equal"] = native == packaged and len(native) == 3
    checks["study_crs_equal"] = all(arcpy.Describe(str(path)).spatialReference.factoryCode == 32645
        for path in (source / "Experiment.gdb/StudyAreas", extracted_gdb / "StudyAreas"))
    checks["packaged_tiffs_exact"] = True
    tiff_hashes = {}
    for name, digest in RASTERS.items():
        matches = list((roundtrip / "extracted").rglob(name))
        if len(matches) != 1:
            raise ValueError("Exact packaged TIFF missing or duplicated")
        tiff_hashes[name] = sha256(matches[0])
        checks["packaged_tiffs_exact"] &= tiff_hashes[name] == digest
    del project
    result = {"status": "passed_atlas_package_semantic_verification" if all(checks.values()) else "failed",
        "original_strict_receipt_status": previous["status"], "original_receipt_unchanged": True,
        "field_order_policy": "Compare exact names/types independent of order; original order remains in snapshots",
        "checks": checks, "package_sha256": previous["package_sha256"], "packaged_tiff_hashes": tiff_hashes,
        "clean_machine_tested": False, "scientific_validity_tested": False}
    write_new(roundtrip / "atlas-semantic-verification.json", result)
    print(json.dumps(result, indent=2))
    return 0 if all(checks.values()) else 1


def member_path(name):
    path = PurePosixPath(name)
    if not name or path.is_absolute() or "\\" in name or ":" in name or ".." in path.parts or name != path.as_posix():
        raise ValueError("Unsafe ZIP member")
    return path


def seal_zip(folder, archive, extracted):
    for path in (folder, archive, extracted):
        reject_links(path)
    if archive.exists() or extracted.exists():
        raise ValueError("Fresh archive and extraction paths required")
    if archive.resolve().is_relative_to(folder.resolve()) or extracted.resolve().is_relative_to(folder.resolve()):
        raise ValueError("Archive and extraction must be outside bundle")
    files = inventory(folder)
    for name in files:
        member_path(name)
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as writer:
        for name in files:
            writer.write(folder / name, name)
    with zipfile.ZipFile(archive) as reader:
        if reader.testzip() is not None:
            raise ValueError("ZIP CRC mismatch")
        names = reader.namelist()
        if len(names) != len(set(names)) or set(names) != set(files):
            raise ValueError("ZIP inventory differs")
        extracted.mkdir(parents=True, exist_ok=False)
        for name in names:
            relative = member_path(name)
            target = extracted.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with reader.open(name) as source, target.open("xb") as destination:
                shutil.copyfileobj(source, destination)
    if inventory(extracted) != files or inventory(folder) != files:
        raise ValueError("Bundle or extraction identity changed")
    return {"archive_bytes": archive.stat().st_size, "archive_sha256": sha256(archive),
            "file_count": len(files), "crc_pass": True, "all_file_hashes_match": True}


def bundle(source, roundtrip, output):
    for path in (source, roundtrip, output):
        reject_links(path)
    source, roundtrip, output = (p.resolve() for p in (source, roundtrip, output))
    if output.exists() or any(output.is_relative_to(p) or p.is_relative_to(output) for p in (source, roundtrip)):
        raise ValueError("Fresh disjoint bundle output required")
    build = json.loads((source / "atlas-build-receipt.json").read_text(encoding="utf-8"))
    package_result = json.loads((roundtrip / "atlas-semantic-verification.json").read_text(encoding="utf-8"))
    package = roundtrip / "delivery.ppkx"
    if build["status"] != "passed_unverified_atlas_build" or package_result["status"] != "passed_atlas_package_semantic_verification":
        raise ValueError("Passing atlas build and local package test required")
    if sha256(package) != package_result["package_sha256"]:
        raise ValueError("Package identity drift")
    if any(sha256(source / "imagery" / name) != digest for name, digest in RASTERS.items()):
        raise ValueError("Raster identity drift")
    if sha256(source / "approved-study-areas-epsg32645.json") != AOI_HASH:
        raise ValueError("Approved extent identity drift")
    if [row["map_id"] for row in build["exports"]] != PRINCIPAL_MAPS:
        raise ValueError("Five fixed principal exports required")
    for row in build["exports"]:
        for kind in ("png", "pdf"):
            path = source / "exports" / row[kind]["file"]
            if sha256(path) != row[kind]["sha256"]:
                raise ValueError("Export identity drift")
    output.mkdir(parents=True, exist_ok=False)
    content = output / "Nepal_Unverified_Atlas"
    content.mkdir()
    for folder in ("imagery", "layers", "exports", "Experiment.gdb"):
        shutil.copytree(source / folder, content / folder, ignore=shutil.ignore_patterns("*.lock"))
    for name in ("ExperimentMetadata.gpkg", "METHOD.json", "approved-study-areas-epsg32645.json"):
        shutil.copy2(source / name, content / name)
    shutil.copy2(package, content / "Nepal_Unverified_Atlas.ppkx")
    (content / "README.md").write_text(
        "# Nepal unverified GIS atlas\n\n"
        "Unverified GIS experiment using Sentinel-1D ASF HyP3 RTC imagery from 16 and 28 August 2026. "
        "WGS 84 / UTM zone 45N, EPSG:32645.\n\n"
        "## Open in ArcGIS Pro\n\n"
        "1. Extract this entire ZIP to a writable folder under your Documents or Projects directory.\n"
        "2. Open `Nepal_Unverified_Atlas.ppkx` in ArcGIS Pro. Let Pro unpack it into a writable location.\n"
        "3. In the Catalog pane, expand Layouts. Open any of the five layouts, then use Share > Export Layout.\n"
        "4. To reuse individual layers, add a file from `layers` to a map. Keep `layers`, `imagery` and "
        "`Experiment.gdb` together; the layer files use relative connections.\n\n"
        "Do not unpack under Program Files. The packaged project uses writable local defaults. "
        "The five exported PDF/PNG maps are also in `exports`.\n\n"
        "## Contents\n\n"
        "Five layouts: regional_overview, source_area_comparison, upper_corridor_comparison, evidence_map, "
        "limitations_map. The project has these five maps and two supporting dated maps. Four unchanged "
        "GeoTIFFs and five layer files are included. `ExperimentMetadata.gpkg` contains three approved "
        "M1 search/review polygons, two source rows and one method row. `METHOD.json` and "
        "`artifact-manifest.json` describe methods and file identities. No landscape-change features are invented.\n\n"
        "## Read the difference\n\n"
        "`delta_vv_db.tif` is after minus before (dB), included only where both existing inputs are finite. "
        "Blue means a lower value, orange a higher value. The displayed range is -6 to +6 dB; stored "
        "values are not clipped. `excluded_cells.tif`: 0 = both inputs valid; 1 = either input invalid. "
        "Outside the original grid there is no observation. Gray/white gaps are not evidence of no change.\n\n"
        "Registration is unverified. No registration correction, normalization, event detection, "
        "geomorphic interpretation or attribution is performed. Search/review outlines are not event "
        "perimeters; 10 m posting is not positional accuracy. Original scientific acceptance remains unmet.\n\n"
        "## Provenance and credits\n\n"
        "M1-SRC-002 (16 August) and M1-SRC-005 (28 August). ASF DAAC HyP3 2026. Contains modified "
        "Copernicus Sentinel data 2026, processed by ESA. HyP3 doi:10.5281/zenodo.3962581; "
        "GAMMA doi:10.5281/zenodo.3962936. Independent demonstration, no endorsement.\n\n"
        "Code and qualified previews: https://github.com/drwbkr1/nepal-2026-before-after-map. "
        "Tested in ArcGIS Pro 3.7.1 in fresh processes on the same machine; clean-machine/profile and "
        "cross-version portability are not claimed. This bundle remains owner-local, outside Git.\n",
        encoding="utf-8")
    write_new(content / "artifact-manifest.json", {"status": "unverified_gis_experiment", "crs": "EPSG:32645",
        "source_rasters": RASTERS, "aoi_sha256": AOI_HASH, "principal_layouts": PRINCIPAL_MAPS,
        "package_sha256": package_result["package_sha256"], "scientific_M6_complete": False,
        "files": inventory(content), "manifest_excludes_itself": True})
    result = seal_zip(content, output / "Nepal_Unverified_Atlas.zip", output / "extracted")
    result.update(status="passed_bundle_integrity", arcgis_package_test="same_machine_fresh_process_pass",
                  clean_machine_tested=False, scientific_validity_tested=False)
    write_new(output / "bundle-receipt.json", result)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--roundtrip", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify-package", action="store_true", help="Installed-runtime named-field and geometry check")
    args = parser.parse_args()
    if args.verify_package:
        raise SystemExit(verify_atlas_package(args.source_root, args.roundtrip))
    if args.output is None:
        parser.error("--output required for bundle creation")
    raise SystemExit(bundle(args.source_root, args.roundtrip, args.output))
