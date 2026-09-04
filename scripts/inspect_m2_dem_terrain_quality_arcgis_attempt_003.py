#!/usr/bin/env python3
"""Run corrected attempt-003 of the read-only DEM terrain-quality inspection."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import arcpy
import numpy as np

from dem_terrain_quality_core import combine_statuses, evaluate_seam, evaluate_tile


ROOT = Path(__file__).resolve().parents[1]
PROJECT_PARENT = ROOT.parent.resolve()
BLANK_APRX = Path(r"C:\Program Files\ArcGIS\Pro\Resources\ArcToolBox\Services\routingservices\data\Blank.aprx")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return value


def write_new_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def page_rectangle(xmin: float, ymin: float, xmax: float, ymax: float) -> arcpy.Polygon:
    return arcpy.Polygon(
        arcpy.Array(
            [
                arcpy.Point(xmin, ymin),
                arcpy.Point(xmin, ymax),
                arcpy.Point(xmax, ymax),
                arcpy.Point(xmax, ymin),
                arcpy.Point(xmin, ymin),
            ]
        )
    )


def file_inventory(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "relative_path": path.relative_to(root).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in sorted(
            item
            for item in root.rglob("*")
            if item.is_file() and not item.name.lower().endswith(".lock")
        )
    ]


def apply_polygon_outline(layer: Any) -> None:
    symbology = layer.symbology
    symbology.updateRenderer("SimpleRenderer")
    symbol = symbology.renderer.symbol
    symbol.color = {"RGB": [255, 255, 255, 0]}
    symbol.outlineColor = {"RGB": [0, 225, 240, 100]}
    symbol.outlineWidth = 2.0
    layer.symbology = symbology


def apply_line_symbol(layer: Any) -> None:
    symbology = layer.symbology
    symbology.updateRenderer("SimpleRenderer")
    symbol = symbology.renderer.symbol
    symbol.color = {"RGB": [255, 119, 51, 100]}
    symbol.size = 2.0
    layer.symbology = symbology


def build_seam_features(gdb: Path, seam_results: list[dict[str, Any]]) -> Path:
    output = gdb / "NativeTileSeams"
    sr_wgs84 = arcpy.SpatialReference(4326)
    sr_utm = arcpy.SpatialReference(32645)
    arcpy.management.CreateFeatureclass(str(gdb), output.name, "POLYLINE", spatial_reference=sr_utm)
    for name, field_type, length in (
        ("SEAM_ID", "TEXT", 32),
        ("QA_STATUS", "TEXT", 12),
        ("ORIENT", "TEXT", 16),
        ("MED_ABS_M", "DOUBLE", None),
        ("P99_ABS_M", "DOUBLE", None),
        ("MAX_ABS_M", "DOUBLE", None),
    ):
        arcpy.management.AddField(str(output), name, field_type, field_length=length)
    coordinates = {
        "SEAM-E85-N27": [(85.0, 27.0), (85.0, 28.0)],
        "SEAM-E85-N28": [(85.0, 28.0), (85.0, 29.0)],
        "SEAM-N28-E84": [(84.0, 28.0), (85.0, 28.0)],
        "SEAM-N28-E85": [(85.0, 28.0), (86.0, 28.0)],
    }
    fields = ["SHAPE@", "SEAM_ID", "QA_STATUS", "ORIENT", "MED_ABS_M", "P99_ABS_M", "MAX_ABS_M"]
    with arcpy.da.InsertCursor(str(output), fields) as cursor:
        for item in seam_results:
            line = arcpy.Polyline(
                arcpy.Array([arcpy.Point(x, y) for x, y in coordinates[item["seam_id"]]]),
                sr_wgs84,
            ).projectAs(sr_utm)
            metrics = item["evaluation"]["metrics"]
            cursor.insertRow(
                [
                    line,
                    item["seam_id"],
                    item["evaluation"]["status"],
                    item["orientation"],
                    metrics["residual_abs_median_m"],
                    metrics["residual_abs_p99_m"],
                    metrics["residual_abs_max_m"],
                ]
            )
    return output


def create_project(
    output_root: Path,
    hillshade: Path,
    slope: Path,
    study_areas: Path,
    seams: Path,
) -> dict[str, Any]:
    project = arcpy.mp.ArcGISProject(str(BLANK_APRX))
    maps = project.listMaps()
    map_obj = maps[0] if maps else project.createMap("DEM Terrain QA", "MAP")
    map_obj.name = "DEM Terrain QA"
    for layer in list(map_obj.listLayers()):
        map_obj.removeLayer(layer)
    for table in list(map_obj.listTables()):
        map_obj.removeTable(table)
    map_obj.spatialReference = arcpy.SpatialReference(32645)

    hillshade_layer = map_obj.addDataFromPath(str(hillshade.resolve()))
    slope_layer = map_obj.addDataFromPath(str(slope.resolve()))
    seam_layer = map_obj.addDataFromPath(str(seams.resolve()))
    aoi_layer = map_obj.addDataFromPath(str(study_areas.resolve()))
    hillshade_layer.name = "AOI HILLSHADE — EGM2008 ORTHOMETRIC SOURCE"
    slope_layer.name = "AOI SLOPE DEGREES"
    slope_layer.transparency = 70
    seam_layer.name = "NATIVE TILE SEAMS"
    aoi_layer.name = "APPROVED STUDY AREAS"
    apply_line_symbol(seam_layer)
    apply_polygon_outline(aoi_layer)
    try:
        labels = aoi_layer.listLabelClasses()
        labels[0].expression = "$feature.NAME"
        aoi_layer.showLabels = True
    except (IndexError, RuntimeError):
        pass

    layout = project.createLayout(11, 8.5, "INCH", "DEM Terrain QA")
    map_frame = layout.createMapFrame(page_rectangle(0.45, 1.12, 10.55, 7.68), map_obj, "Terrain QA Map Frame")
    extent = map_frame.getLayerExtent(aoi_layer, False, True)
    map_frame.camera.setExtent(extent)
    map_frame.camera.scale *= 1.12
    project.createTextElement(layout, arcpy.Point(0.55, 8.12), "POINT", "Nepal 2026 — DEM Terrain Quality Review", 19, "Segoe UI", "Bold", name="Title")
    project.createTextElement(
        layout,
        page_rectangle(0.58, 7.76, 10.35, 8.03),
        "POLYGON",
        "EPSG:32645 • 30 m review grid • source elevations remain EGM2008 orthometric • no vertical conversion",
        9,
        "Segoe UI",
        "Regular",
        name="Subtitle",
    )
    project.createTextElement(
        layout,
        page_rectangle(0.55, 0.14, 10.45, 0.92),
        "POLYGON",
        "QA SURFACE ONLY. Hillshade and slope support artifact review; they do not show satellite change, establish event causation, resolve the vertical datum, validate terrain against ground control, or provide emergency guidance.",
        8.3,
        "Segoe UI",
        "Regular",
        name="Claim Boundary",
    )
    project.createTextElement(
        layout,
        page_rectangle(0.72, 1.17, 4.6, 1.43),
        "POLYGON",
        f"Map scale 1:{map_frame.camera.scale:,.0f} • CRS units: metres",
        8,
        "Segoe UI",
        "Regular",
        name="Verified Numeric Scale",
    )
    layout.createMapSurroundElement(arcpy.Point(9.82, 7.18), "NORTH_ARROW", map_frame, name="North Arrow")
    layout.createMapSurroundElement(page_rectangle(8.15, 1.48, 10.30, 3.35), "LEGEND", map_frame, name="Legend")

    aprx = output_root / "Nepal_2026_DEM_Terrain_QA.aprx"
    png = output_root / "Nepal_2026_DEM_Terrain_QA.png"
    pdf = output_root / "Nepal_2026_DEM_Terrain_QA.pdf"
    project.saveACopy(str(aprx))
    layout.exportToPNG(str(png), resolution=180, color_mode="24-BIT_TRUE_COLOR")
    layout.exportToPDF(str(pdf), resolution=180, image_quality="BEST")
    return {
        "arcgis_project": str(aprx),
        "png_export": str(png),
        "pdf_export": str(pdf),
        "map_name": map_obj.name,
        "layout_name": layout.name,
        "map_spatial_reference_wkid": int(map_obj.spatialReference.factoryCode),
        "layer_names": [layer.name for layer in map_obj.listLayers()],
        "layout_elements": [element.name for element in layout.listElements()],
        "map_scale": float(map_frame.camera.scale),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=Path("config/qa/dem-terrain-quality-contract.json"))
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--candidate-receipt", type=Path, required=True)
    parser.add_argument("--executed-at-utc", required=True)
    args = parser.parse_args()
    if not args.executed_at_utc.endswith("Z"):
        raise SystemExit("--executed-at-utc must end in Z")

    contract = load_json(args.contract)
    if contract.get("status") != "predeclared_not_executed" or contract.get("contract_id") != "NEPAL-M2-DEM-TERRAIN-QUALITY-001":
        raise SystemExit("terrain-quality contract is not the expected predeclared control")
    expected_output = Path(contract["processing"]["output_root"]).resolve(strict=False)
    output_root = args.output_root.resolve(strict=False)
    if output_root != expected_output:
        raise SystemExit("output root differs from the predeclared path")
    if output_root.exists() or args.candidate_receipt.exists():
        raise SystemExit("REFUSED: output root or candidate receipt already exists")
    scratch_root = (ROOT / "scratch").resolve(strict=False)
    try:
        args.candidate_receipt.resolve(strict=False).relative_to(scratch_root)
    except ValueError as exc:
        raise SystemExit("candidate receipt must be a new path under repository scratch") from exc
    if not BLANK_APRX.is_file():
        raise SystemExit(f"ArcGIS blank project is absent: {BLANK_APRX}")

    bindings = contract["bindings"]
    for ref_key, sha_key in (
        ("active_intake_ref", "active_intake_sha256"),
        ("dem_verification_summary_ref", "dem_verification_summary_sha256"),
        ("approved_aoi_ref", "approved_aoi_sha256"),
        ("vertical_datum_proposal_ref", "vertical_datum_proposal_sha256"),
        ("implementation_ref", "implementation_sha256"),
        ("core_ref", "core_sha256"),
        ("test_ref", "test_sha256"),
    ):
        path = ROOT / bindings[ref_key]
        if not path.is_file() or sha256_file(path) != bindings[sha_key]:
            raise SystemExit(f"contract binding differs: {ref_key}")
    authority_ref = ROOT / contract["authority"]["authority_ref"]
    if sha256_file(authority_ref) != contract["authority"]["authority_sha256"] or load_json(authority_ref).get("status") != "approved":
        raise SystemExit("DEM authority binding differs")

    external_root = Path(contract["inputs"]["external_root"]).resolve(strict=True)
    source_paths: dict[str, Path] = {}
    source_inventory_before: list[dict[str, Any]] = []
    arrays: dict[str, np.ndarray] = {}
    for asset in contract["inputs"]["assets"]:
        path = (external_root / Path(*Path(asset["custody_relative_path"]).parts)).resolve(strict=True)
        try:
            path.relative_to(external_root)
        except ValueError as exc:
            raise SystemExit(f"source path escapes external root: {asset['source_id']}") from exc
        if path.stat().st_size != asset["size_bytes"] or sha256_file(path) != asset["sha256"]:
            raise SystemExit(f"source byte identity differs: {asset['source_id']}")
        source_paths[asset["source_id"]] = path
        source_inventory_before.append({"source_id": asset["source_id"], "path": str(path), "size_bytes": path.stat().st_size, "sha256": asset["sha256"]})
        arrays[asset["source_id"]] = np.asarray(arcpy.RasterToNumPyArray(arcpy.Raster(str(path))), dtype=np.float32)

    tile_results = [
        {"source_id": source_id, "evaluation": evaluate_tile(arrays[source_id], contract["thresholds"]["tile"])}
        for source_id in [asset["source_id"] for asset in contract["inputs"]["assets"]]
    ]
    seam_results = []
    for seam in contract["seam_pairs"]:
        seam_results.append(
            {
                **seam,
                "evaluation": evaluate_seam(
                    arrays[seam["first_source_id"]],
                    arrays[seam["second_source_id"]],
                    seam["orientation"],
                    contract["thresholds"]["seam"],
                ),
            }
        )

    output_root.mkdir(parents=True, exist_ok=False)
    arcpy.env.overwriteOutput = False
    arcpy.env.addOutputsToMap = False
    gdb = output_root / "Nepal_2026_DEM_Terrain_QA.gdb"
    arcpy.management.CreateFileGDB(str(output_root), gdb.name)
    native_mosaic = gdb / "DEM_Native_Mosaic"
    ordered_inputs = [str(source_paths[asset["source_id"]]) for asset in contract["inputs"]["assets"]]
    arcpy.management.MosaicToNewRaster(
        ordered_inputs,
        str(gdb),
        native_mosaic.name,
        arcpy.SpatialReference(4326),
        "32_BIT_FLOAT",
        0.0002777777777777778,
        1,
        "LAST",
        "FIRST",
    )
    projected_dem = gdb / "DEM_EGM2008_Orthometric_UTM45N"
    arcpy.management.ProjectRaster(str(native_mosaic), str(projected_dem), arcpy.SpatialReference(32645), "BILINEAR", 30.0)
    projected_description = arcpy.Describe(str(projected_dem))
    study_areas = gdb / "StudyAreas"
    arcpy.conversion.JSONToFeatures(str(ROOT / bindings["approved_aoi_ref"]), str(study_areas))
    study_union = gdb / "StudyAreasUnion"
    arcpy.management.Dissolve(str(study_areas), str(study_union))
    aoi_dem = gdb / "DEM_AOI_EGM2008_Orthometric"
    slope = gdb / "Slope_Degrees"
    hillshade = gdb / "Hillshade"
    arcpy.CheckOutExtension("Spatial")
    try:
        with arcpy.EnvManager(snapRaster=str(projected_dem), cellSize=30.0, outputCoordinateSystem=arcpy.SpatialReference(32645)):
            arcpy.sa.ExtractByMask(str(projected_dem), str(study_union)).save(str(aoi_dem))
            arcpy.sa.Slope(str(aoi_dem), "DEGREE", 1.0, "PLANAR", "METER").save(str(slope))
            arcpy.sa.Hillshade(str(aoi_dem), 315, 45, "NO_SHADOWS", 1.0).save(str(hillshade))
    finally:
        arcpy.CheckInExtension("Spatial")
    seam_features = build_seam_features(gdb, seam_results)

    slope_raster = arcpy.Raster(str(slope))
    slope_values = np.asarray(arcpy.RasterToNumPyArray(slope_raster), dtype=np.float64)
    slope_valid = np.isfinite(slope_values)
    if slope_raster.noDataValue is not None:
        slope_valid &= slope_values != float(slope_raster.noDataValue)
    slope_finite = slope_values[slope_valid]
    if slope_finite.size == 0:
        raise ValueError("AOI slope raster contains no finite values")
    slope_thresholds = contract["thresholds"]["slope"]
    slope_metrics = {
        "finite_cell_count": int(slope_finite.size),
        "minimum_degrees": float(np.min(slope_finite)),
        "maximum_degrees": float(np.max(slope_finite)),
        "mean_degrees": float(np.mean(slope_finite)),
        "p50_degrees": float(np.percentile(slope_finite, 50)),
        "p95_degrees": float(np.percentile(slope_finite, 95)),
        "p99_degrees": float(np.percentile(slope_finite, 99)),
        "above_defer_level_count": int(np.count_nonzero(slope_finite > float(slope_thresholds["defer_level_degrees"]))),
        "above_defer_level_fraction": float(np.count_nonzero(slope_finite > float(slope_thresholds["defer_level_degrees"])) / slope_finite.size),
    }
    slope_failures = ["slope_exceeds_geometric_bound"] if slope_metrics["maximum_degrees"] > float(slope_thresholds["block_maximum_degrees"]) else []
    slope_deferrals = []
    if slope_metrics["above_defer_level_fraction"] > float(slope_thresholds["defer_fraction_above_level"]):
        slope_deferrals.append("extreme_slope_fraction_requires_visual_review")
    slope_status = "block" if slope_failures else ("defer" if slope_deferrals else "pass")
    slope_evaluation = {"status": slope_status, "failures": slope_failures, "deferrals": slope_deferrals, "metrics": slope_metrics}

    project_result = create_project(output_root, hillshade, slope, study_areas, seam_features)
    source_inventory_after = []
    for item in source_inventory_before:
        path = Path(item["path"])
        source_inventory_after.append({"source_id": item["source_id"], "path": item["path"], "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    if source_inventory_before != source_inventory_after:
        raise RuntimeError("source custody changed during terrain-quality inspection")

    transient_lock_files = [
        path.relative_to(output_root).as_posix()
        for path in sorted(item for item in output_root.rglob("*") if item.is_file() and item.name.lower().endswith(".lock"))
    ]
    output_inventory = file_inventory(output_root)
    manifest_path = output_root / "derived-output-manifest.json"
    write_new_json(
        manifest_path,
        {
            "schema_version": "1.0",
            "created_at_utc": args.executed_at_utc,
            "stable_artifact_policy": "exclude transient ArcGIS geodatabase .lock files",
            "excluded_transient_lock_files": transient_lock_files,
            "files": output_inventory,
        },
    )
    quantitative_status = combine_statuses(
        [item["evaluation"]["status"] for item in tile_results]
        + [item["evaluation"]["status"] for item in seam_results]
        + [slope_status]
    )
    candidate_status = {
        "pass": "defer_visual_review_pending",
        "defer": "defer_quantitative_findings_and_visual_review_pending",
        "block": "block_quantitative_findings",
    }[quantitative_status]
    install = arcpy.GetInstallInfo()
    receipt = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-DEM-TERRAIN-QUALITY-001",
        "status": candidate_status,
        "executed_at_utc": args.executed_at_utc,
        "runtime": {"product": install.get("ProductName"), "version": install.get("Version"), "license_level": install.get("LicenseLevel")},
        "bindings": {
            "contract_ref": str(args.contract).replace("\\", "/"),
            "contract_sha256": sha256_file(args.contract),
            "implementation_ref": "scripts/inspect_m2_dem_terrain_quality_arcgis_attempt_003.py",
            "implementation_sha256": sha256_file(Path(__file__)),
            "core_ref": "scripts/dem_terrain_quality_core.py",
            "core_sha256": sha256_file(ROOT / "scripts/dem_terrain_quality_core.py"),
            "active_intake_ref": bindings["active_intake_ref"],
            "active_intake_sha256": bindings["active_intake_sha256"],
            "dem_verification_summary_ref": bindings["dem_verification_summary_ref"],
            "dem_verification_summary_sha256": bindings["dem_verification_summary_sha256"],
            "approved_aoi_ref": bindings["approved_aoi_ref"],
            "approved_aoi_sha256": bindings["approved_aoi_sha256"],
        },
        "source_inventory_before": source_inventory_before,
        "source_inventory_after": source_inventory_after,
        "tile_results": tile_results,
        "seam_results": seam_results,
        "slope_evaluation": slope_evaluation,
        "quantitative_status": quantitative_status,
        "arcgis_outputs": {
            "root": str(output_root),
            "geodatabase": str(gdb),
            "native_mosaic": str(native_mosaic),
            "projected_dem": str(projected_dem),
            "aoi_dem": str(aoi_dem),
            "slope": str(slope),
            "hillshade": str(hillshade),
            "study_areas": str(study_areas),
            "native_tile_seams": str(seam_features),
            "manifest": str(manifest_path),
            "manifest_sha256": sha256_file(manifest_path),
            "excluded_transient_lock_files": transient_lock_files,
            **project_result,
        },
        "projection_check": {
            "wkid": int(projected_description.spatialReference.factoryCode),
            "mean_cell_width_m": float(projected_description.meanCellWidth),
            "mean_cell_height_m": float(projected_description.meanCellHeight),
            "vertical_transformation_applied": False,
            "elevation_value_semantics": "EGM2008 orthometric metres",
        },
        "visual_review": {"status": "pending", "reviewed_at_utc": None, "findings": []},
        "claim_boundary": {
            "source_byte_identity_reverified": True,
            "source_custody_unchanged": True,
            "terrain_quantitative_metrics_captured": True,
            "terrain_visual_review_established": False,
            "vertical_datum_route_established": False,
            "sentinel_processing_executed": False,
            "satellite_change_established": False,
            "scientific_result_established": False,
        },
        "limitations": [
            "The projected DEM retains EGM2008 orthometric elevation values; horizontal reprojection is not vertical conversion.",
            "Thresholds screen for gross artifacts but do not validate elevation accuracy against independent ground control.",
            "Visual review is still pending and cannot be replaced by the quantitative metrics.",
            "All DEM-derived rasters, the APRX, PNG, and PDF remain in external non-Git custody.",
        ],
    }
    write_new_json(args.candidate_receipt, receipt)
    print(json.dumps({"status": candidate_status, "quantitative_status": quantitative_status, "candidate_receipt": str(args.candidate_receipt), "output_root": str(output_root), "png": project_result["png_export"]}, indent=2))


if __name__ == "__main__":
    main()
