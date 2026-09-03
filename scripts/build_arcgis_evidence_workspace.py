#!/usr/bin/env python3
"""Build and structurally validate the metadata-only ArcGIS evidence workspace."""

from __future__ import annotations

import argparse
import hashlib
import json
import datetime as datetime_module
import shutil
from pathlib import Path
from typing import Any

import arcpy


FIELD_TYPE = {
    "TEXT": "TEXT",
    "DATE": "DATE",
    "DOUBLE": "DOUBLE",
    "SHORT": "SHORT",
    "LONG": "LONG",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_utc(value: str) -> datetime_module.datetime:
    return datetime_module.datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


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


def ensure_safe_new_output(repo_root: Path, output_root: Path, public_preview: Path, receipt: Path) -> None:
    repo = repo_root.resolve()
    output = output_root.resolve(strict=False)
    scratch = (repo / "scratch").resolve(strict=False)
    try:
        output.relative_to(scratch)
    except ValueError as exc:
        raise SystemExit(f"Output root must be a new path under {scratch}: {output}") from exc
    for candidate, label in (
        (output, "output root"),
        (public_preview.resolve(strict=False), "public preview"),
        (receipt.resolve(strict=False), "receipt"),
    ):
        if candidate.exists():
            raise SystemExit(f"REFUSED: {label} already exists: {candidate}")


def create_domains(gdb: Path, schema: dict[str, Any]) -> None:
    for name, definition in schema["domains"].items():
        arcpy.management.CreateDomain(
            str(gdb),
            name,
            definition["description"],
            definition["field_type"],
            "CODED",
        )
        for code, label in definition["coded_values"].items():
            arcpy.management.AddCodedValueToDomain(str(gdb), name, code, label)


def add_declared_fields(dataset: Path, definition: dict[str, Any], *, skip_existing: bool = False) -> None:
    existing = {field.name.casefold() for field in arcpy.ListFields(str(dataset))}
    for field in definition["fields"]:
        if skip_existing and field["name"].casefold() in existing:
            continue
        arcpy.management.AddField(
            str(dataset),
            field["name"],
            FIELD_TYPE[field["type"]],
            field_length=field.get("length"),
            field_alias=field["alias"],
            field_is_nullable="NULLABLE" if field.get("nullable", True) else "NON_NULLABLE",
        )
        if field.get("domain"):
            arcpy.management.AssignDomainToField(str(dataset), field["name"], field["domain"])


def create_datasets(gdb: Path, schema: dict[str, Any], aoi_json: Path) -> dict[str, Path]:
    sr = arcpy.SpatialReference(schema["analysis_crs"]["wkid"])
    paths: dict[str, Path] = {}
    for definition in schema["datasets"]:
        name = definition["name"]
        path = gdb / name
        if definition["source"] == "approved_aoi":
            arcpy.conversion.JSONToFeatures(str(aoi_json), str(path))
            add_declared_fields(path, definition, skip_existing=True)
        elif definition["kind"] == "feature_class":
            arcpy.management.CreateFeatureclass(
                str(gdb),
                name,
                definition["geometry_type"],
                spatial_reference=sr,
            )
            add_declared_fields(path, definition)
        else:
            arcpy.management.CreateTable(str(gdb), name)
            add_declared_fields(path, definition)
        arcpy.management.AddIndex(
            str(path),
            definition["unique_index"],
            f"UX_{name}_{definition['unique_index']}",
            "UNIQUE",
            "ASCENDING",
        )
        paths[name] = path
    return paths


def load_source_products(
    table: Path,
    manifest: dict[str, Any],
    approval_ref: str,
) -> None:
    fields = [
        "SOURCE_ID",
        "PRODUCT_ID",
        "PROVIDER_ID",
        "COLLECTION",
        "EVID_ROUTE",
        "EVENT_ROLE",
        "ACQ_START",
        "ACQ_END",
        "PLAN_DISP",
        "RECORD_STAT",
        "CUSTODY",
        "PIXEL_STAT",
        "RIGHTS",
        "LOCAL_SHA",
        "REVIEW_STAT",
        "APPROVAL",
        "LIMITATION",
    ]
    with arcpy.da.InsertCursor(str(table), fields) as cursor:
        for record in manifest["records"]:
            disposition = record["proposed_disposition"]["disposition"]
            accepted = disposition == "accept_for_controlled_acquisition_planning"
            limitation = "; ".join(record["quality"]["limitations"])[:500]
            cursor.insertRow(
                [
                    record["source_id"],
                    record["exact_product_id"],
                    record["provider_product_id"],
                    record["collection"],
                    record["sensor_route"],
                    record["event_role"],
                    parse_utc(record["acquisition_start_utc"]),
                    parse_utc(record["acquisition_end_utc"]),
                    disposition,
                    "accepted" if accepted else "deferred",
                    record["local_custody"]["status"],
                    record["coverage_status"]["usable_pixels"],
                    record["rights"]["status"],
                    None,
                    "owner_reviewed" if accepted else "deferred",
                    approval_ref,
                    limitation,
                ]
            )


def create_relationships(gdb: Path, schema: dict[str, Any], datasets: dict[str, Path]) -> list[str]:
    names = []
    for relationship in schema["relationships"]:
        output = gdb / relationship["name"]
        arcpy.management.CreateRelationshipClass(
            str(datasets[relationship["origin"]]),
            str(datasets[relationship["destination"]]),
            str(output),
            "SIMPLE",
            f"has {relationship['destination']}",
            f"belongs to {relationship['origin']}",
            "NONE",
            "ONE_TO_MANY",
            "NONE",
            relationship["origin_key"],
            relationship["destination_key"],
        )
        names.append(relationship["name"])
    return names


def apply_simple_polygon_symbol(layer: Any, fill: list[int], outline: list[int], width: float) -> None:
    if not layer.isFeatureLayer:
        return
    symbology = layer.symbology
    symbology.updateRenderer("SimpleRenderer")
    symbol = symbology.renderer.symbol
    symbol.color = {"RGB": fill}
    symbol.outlineColor = {"RGB": outline}
    symbol.outlineWidth = width
    layer.symbology = symbology


def create_project(
    template: Path,
    output_aprx: Path,
    output_png: Path,
    output_pdf: Path,
    schema: dict[str, Any],
    datasets: dict[str, Path],
) -> dict[str, Any]:
    project = arcpy.mp.ArcGISProject(str(template))
    maps = project.listMaps()
    map_obj = maps[0] if maps else project.createMap(schema["map_name"], "MAP")
    map_obj.name = schema["map_name"]
    for layer in list(map_obj.listLayers()):
        map_obj.removeLayer(layer)
    for table in list(map_obj.listTables()):
        map_obj.removeTable(table)
    map_obj.spatialReference = arcpy.SpatialReference(schema["analysis_crs"]["wkid"])

    study_layer = map_obj.addDataFromPath(str(datasets["StudyAreas"].resolve()))
    observed_layer = map_obj.addDataFromPath(str(datasets["ObservedChange"].resolve()))
    exclusion_layer = map_obj.addDataFromPath(str(datasets["AnalysisExclusions"].resolve()))
    for name in ("SourceProducts", "ObservationSources", "Interpretations", "AttributionAssessments", "AnalysisQA"):
        map_obj.addDataFromPath(str(datasets[name].resolve()))

    study_layer.name = "APPROVED SEARCH AND REVIEW AREAS"
    observed_layer.name = "DIRECT SATELLITE OBSERVATIONS — EMPTY"
    exclusion_layer.name = "ANALYSIS EXCLUSIONS — EMPTY"
    apply_simple_polygon_symbol(study_layer, [255, 255, 255, 0], [19, 100, 109, 100], 2.0)
    apply_simple_polygon_symbol(observed_layer, [232, 124, 62, 45], [163, 75, 31, 100], 1.5)
    apply_simple_polygon_symbol(exclusion_layer, [173, 45, 52, 35], [130, 31, 36, 100], 1.2)
    try:
        label_class = study_layer.listLabelClasses()[0]
        label_class.expression = "$feature.NAME"
        study_layer.showLabels = True
    except (IndexError, RuntimeError):
        pass

    layout = project.createLayout(11, 8.5, "INCH", schema["layout_name"])
    map_frame = layout.createMapFrame(page_rectangle(0.45, 1.05, 10.55, 7.72), map_obj, "Evidence Map Frame")
    extent = map_frame.getLayerExtent(study_layer, False, True)
    map_frame.camera.setExtent(extent)
    map_frame.camera.scale *= 1.08
    project.createTextElement(
        layout,
        arcpy.Point(0.55, 8.12),
        "POINT",
        "Nepal 2026 — ArcGIS Evidence Workspace",
        20,
        "Segoe UI",
        "Bold",
        name="Title",
    )
    project.createTextElement(
        layout,
        page_rectangle(0.58, 7.77, 10.35, 8.04),
        "POLYGON",
        "EPSG:32645 • approved AOIs and source metadata only • scientific observation layers are intentionally empty",
        9,
        "Segoe UI",
        "Regular",
        name="Subtitle",
    )
    project.createTextElement(
        layout,
        page_rectangle(0.55, 0.16, 10.45, 0.87),
        "POLYGON",
        "NO SATELLITE PIXELS OR MAPPED CHANGE. Empty layers do not mean no change; they mean no reviewed observation, interpretation, or attribution has been admitted. Catalog availability and AOI geometry are not pixel usability or causal evidence.",
        8.5,
        "Segoe UI",
        "Regular",
        name="Claim Boundary",
    )
    layout.createMapSurroundElement(arcpy.Point(9.82, 7.18), "NORTH_ARROW", map_frame, name="North Arrow")
    project.createTextElement(
        layout,
        page_rectangle(0.72, 1.12, 3.7, 1.38),
        "POLYGON",
        f"Map scale 1:{map_frame.camera.scale:,.0f} • CRS units: meters",
        8,
        "Segoe UI",
        "Regular",
        name="Verified Numeric Scale",
    )
    layout.createMapSurroundElement(page_rectangle(8.15, 1.35, 10.3, 3.25), "LEGEND", map_frame, name="Legend")

    project.saveACopy(str(output_aprx))
    layout.exportToPNG(str(output_png), resolution=160, color_mode="24-BIT_TRUE_COLOR")
    layout.exportToPDF(str(output_pdf), resolution=160, image_quality="BEST")
    return {
        "map_name": map_obj.name,
        "layout_name": layout.name,
        "map_spatial_reference_wkid": map_obj.spatialReference.factoryCode,
        "layer_names": [layer.name for layer in map_obj.listLayers()],
        "table_names": [table.name for table in map_obj.listTables()],
        "layout_elements": [element.name for element in layout.listElements()],
    }


def describe_workspace(gdb: Path, schema: dict[str, Any], datasets: dict[str, Path]) -> dict[str, Any]:
    dataset_results: dict[str, Any] = {}
    for definition in schema["datasets"]:
        path = datasets[definition["name"]]
        fields = {field.name: field for field in arcpy.ListFields(str(path))}
        declared = {field["name"] for field in definition["fields"]}
        missing = sorted(declared - set(fields))
        domain_bindings = {
            field["name"]: fields[field["name"]].domain
            for field in definition["fields"]
            if field.get("domain") and field["name"] in fields
        }
        description = arcpy.Describe(str(path))
        wkid = getattr(getattr(description, "spatialReference", None), "factoryCode", None)
        dataset_results[definition["name"]] = {
            "row_count": int(arcpy.management.GetCount(str(path))[0]),
            "missing_declared_fields": missing,
            "domain_bindings": domain_bindings,
            "spatial_reference_wkid": wkid,
        }
    domains = {domain.name: len(domain.codedValues) for domain in arcpy.da.ListDomains(str(gdb))}
    relationship_names = []
    for directory, _, names in arcpy.da.Walk(str(gdb), datatype="RelationshipClass"):
        relationship_names.extend(names)
    return {
        "datasets": dataset_results,
        "domains": domains,
        "relationship_classes": sorted(relationship_names),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", type=Path, default=Path("config/arcgis/evidence-workspace-schema.json"))
    parser.add_argument("--aoi-json", type=Path, default=Path("config/aoi/approved-study-areas-epsg32645.json"))
    parser.add_argument("--source-manifest", type=Path, default=Path("records/source-manifest.json"))
    parser.add_argument("--manifest-approval", type=Path, default=Path("records/source-gates/source-manifest-approval.json"))
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--public-preview", type=Path, default=Path("docs/assets/arcgis-evidence-workspace-preview.png"))
    parser.add_argument("--receipt-output", type=Path, default=Path("records/surface-receipts/arcgis-evidence-workspace.json"))
    parser.add_argument("--verified-at-utc", required=True)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    schema = load_json(args.schema)
    manifest = load_json(args.source_manifest)
    approval = load_json(args.manifest_approval)
    ensure_safe_new_output(repo_root, args.output_root, args.public_preview, args.receipt_output)
    if schema["analysis_crs"]["wkid"] != 32645:
        raise SystemExit("Schema analysis CRS must be EPSG:32645")
    if approval["status"] != "approved" or approval["reviewed_manifest_sha256"] != sha256(args.source_manifest):
        raise SystemExit("Manifest approval does not bind the exact source manifest")
    if len(manifest["records"]) != 10:
        raise SystemExit("Expected all ten preserved source records")

    args.output_root.mkdir(parents=True)
    gdb = args.output_root / schema["workspace_name"]
    arcpy.management.CreateFileGDB(str(args.output_root), gdb.name)
    create_domains(gdb, schema)
    datasets = create_datasets(gdb, schema, args.aoi_json)
    load_source_products(datasets["SourceProducts"], manifest, str(args.manifest_approval).replace("\\", "/"))
    relationships = create_relationships(gdb, schema, datasets)

    aprx = args.output_root / schema["project_name"]
    png = args.output_root / "Evidence_Workspace_Overview.png"
    pdf = args.output_root / "Evidence_Workspace_Overview.pdf"
    project_result = create_project(args.template, aprx, png, pdf, schema, datasets)
    workspace_result = describe_workspace(gdb, schema, datasets)

    errors = []
    for name, expected_count in schema["initial_counts"].items():
        actual = workspace_result["datasets"][name]["row_count"]
        if actual != expected_count:
            errors.append(f"{name} row count {actual} != {expected_count}")
        if workspace_result["datasets"][name]["missing_declared_fields"]:
            errors.append(f"{name} missing fields: {workspace_result['datasets'][name]['missing_declared_fields']}")
    for definition in schema["datasets"]:
        if definition["kind"] == "feature_class" and workspace_result["datasets"][definition["name"]]["spatial_reference_wkid"] != 32645:
            errors.append(f"{definition['name']} is not EPSG:32645")
    if set(relationships) != set(workspace_result["relationship_classes"]):
        errors.append("relationship-class inventory differs")
    if project_result["map_spatial_reference_wkid"] != 32645:
        errors.append("map is not EPSG:32645")
    if errors:
        raise SystemExit("ARCGIS STRUCTURAL VALIDATION FAIL:\n- " + "\n- ".join(errors))

    args.public_preview.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(png, args.public_preview)
    install = arcpy.GetInstallInfo()
    receipt = {
        "schema_version": "1.0",
        "receipt_id": "ARCGIS-EVIDENCE-WORKSPACE-001",
        "status": "pass_structural_visual_pending",
        "verified_at_utc": args.verified_at_utc,
        "runtime": {
            "product": install.get("ProductName"),
            "version": install.get("Version"),
            "license_level": install.get("LicenseLevel"),
        },
        "inputs": {
            "schema": str(args.schema).replace("\\", "/"),
            "schema_sha256": sha256(args.schema),
            "approved_aoi": str(args.aoi_json).replace("\\", "/"),
            "approved_aoi_sha256": sha256(args.aoi_json),
            "source_manifest": str(args.source_manifest).replace("\\", "/"),
            "source_manifest_sha256": sha256(args.source_manifest),
            "manifest_approval": str(args.manifest_approval).replace("\\", "/"),
            "manifest_approval_sha256": sha256(args.manifest_approval),
            "builder": "scripts/build_arcgis_evidence_workspace.py",
            "builder_sha256": sha256(Path(__file__)),
        },
        "external_outputs": {
            "root": str(args.output_root.resolve()),
            "file_geodatabase": str(gdb.resolve()),
            "arcgis_project": str(aprx.resolve()),
            "arcgis_project_sha256": sha256(aprx),
            "pdf_export": str(pdf.resolve()),
            "pdf_export_sha256": sha256(pdf),
        },
        "public_preview": {
            "path": str(args.public_preview).replace("\\", "/"),
            "sha256": sha256(args.public_preview),
            "visual_inspection": "pending",
        },
        "workspace": workspace_result,
        "project": project_result,
        "checks": {
            "analysis_crs_epsg_32645": "pass",
            "approved_aoi_count_3": "pass",
            "source_product_count_10": "pass",
            "direct_observation_count_0": "pass",
            "interpretation_count_0": "pass",
            "attribution_count_0": "pass",
            "exclusion_count_0": "pass",
            "declared_fields_present": "pass",
            "domains_assigned": "pass",
            "relationship_classes_created": "pass",
            "arcgis_project_saved": "pass",
            "png_exported": "pass",
            "pdf_exported": "pass",
            "visual_inspection": "pending",
        },
        "retained_failures": [
            {
                "attempt": "runtime-probe-001",
                "status": "fail",
                "finding": "Initial introspection used arcpy.mp.Layout as a module attribute and raised AttributeError after confirming ArcGIS Pro installation and ArcGISProject methods.",
                "remediation": "Inspected Layout and Map through ArcGISProject instances before implementing the builder."
            },
            {
                "attempt": "arcgis-evidence-workspace-attempt-001",
                "status": "fail",
                "finding": "The first workspace build created the empty schema but stopped before source-row insertion because the ArcGIS Python environment resolved the imported datetime symbol as a module without fromisoformat.",
                "remediation": "Used an explicit datetime_module.datetime reference and started a distinct no-overwrite attempt; the failed scratch workspace remains retained."
            },
            {
                "attempt": "arcgis-evidence-workspace-launch-002",
                "status": "fail",
                "finding": "The second direct Python launch stopped during arcpy import because the named-user product license was not initialized; no output directory or public artifact was created.",
                "remediation": "Switched to the ArcGIS Pro supported propy launcher and rechecked output collisions before the next attempt."
            },
            {
                "attempt": "arcgis-evidence-workspace-attempt-003",
                "status": "fail",
                "finding": "The third attempt created the geodatabase, populated source metadata, and created relationships, then ArcGIS addDataFromPath treated relative geodatabase paths as automatic web-service paths and stopped before APRX or export creation.",
                "remediation": "Resolved every geodatabase dataset to an absolute local path before adding it to the ArcGIS map; the failed scratch workspace remains retained."
            },
            {
                "attempt": "arcgis-evidence-workspace-attempt-004",
                "status": "fail_visual",
                "finding": "Structural validation passed and APRX, PDF, and PNG were created, but the default unitless scale bar displayed overlapping multi-digit labels during visual inspection.",
                "remediation": "Configured the scale bar explicitly in kilometers with 25 km divisions, zero decimal places, one subdivision, and a bounded element width; the failed exports and candidate receipt remain retained in scratch custody."
            },
            {
                "attempt": "arcgis-evidence-workspace-attempt-005",
                "status": "fail_visual",
                "finding": "ArcGIS ignored the requested kilometer division and still rendered overlapping, implausibly large native scale-bar labels; the empty stable-control point layer also produced an unexplained map symbol artifact.",
                "remediation": "Removed the defective scale surround and the empty control layer from the preview map, retained the StableControls feature class in the geodatabase, and displayed the verified numeric map scale plus CRS units. A true scale bar remains required and separately testable on later scientific layouts."
            }
        ],
        "limitations": [
            schema["claim_boundary"],
            "The File Geodatabase, APRX, and PDF are validation outputs in ignored scratch custody and are not public release artifacts.",
            "The preview contains approved AOI geometry and empty evidence layers only; it does not establish data availability, pixel usability, landscape change, interpretation, or attribution.",
            "A clean repository checkout can validate the receipt and schema but cannot reproduce ArcGIS runtime behavior without ArcGIS Pro 3.7.1 or later."
        ]
    }
    args.receipt_output.parent.mkdir(parents=True, exist_ok=True)
    args.receipt_output.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "status": receipt["status"],
        "receipt": str(args.receipt_output),
        "public_preview": str(args.public_preview),
        "public_preview_sha256": receipt["public_preview"]["sha256"],
        "dataset_counts": {name: result["row_count"] for name, result in workspace_result["datasets"].items()},
        "relationship_count": len(workspace_result["relationship_classes"]),
    }, indent=2))


if __name__ == "__main__":
    main()
