#!/usr/bin/env python3
"""Independently validate the retained ArcGIS evidence workspace and receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import arcpy


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, default=Path("records/surface-receipts/arcgis-evidence-workspace.json"))
    parser.add_argument("--schema", type=Path, default=Path("config/arcgis/evidence-workspace-schema.json"))
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    receipt = load_json(args.receipt)
    schema = load_json(args.schema)
    errors: list[str] = []
    if receipt.get("status") != "pass_with_retained_failures":
        fail(errors, "receipt status is not pass_with_retained_failures")
    if receipt.get("checks", {}).get("visual_inspection") != "pass":
        fail(errors, "receipt does not record passing visual inspection")

    for label, path_key, hash_key in (
        ("schema", "schema", "schema_sha256"),
        ("approved AOI", "approved_aoi", "approved_aoi_sha256"),
        ("source manifest", "source_manifest", "source_manifest_sha256"),
        ("manifest approval", "manifest_approval", "manifest_approval_sha256"),
        ("builder", "builder", "builder_sha256"),
    ):
        path = repo_root / receipt["inputs"][path_key]
        if not path.is_file() or sha256(path) != receipt["inputs"][hash_key]:
            fail(errors, f"{label} hash differs from receipt")

    preview = repo_root / receipt["public_preview"]["path"]
    if not preview.is_file() or sha256(preview) != receipt["public_preview"]["sha256"]:
        fail(errors, "public preview hash differs from receipt")

    external = receipt["external_outputs"]
    gdb = Path(external["file_geodatabase"])
    aprx_path = Path(external["arcgis_project"])
    pdf_path = Path(external["pdf_export"])
    if not gdb.is_dir():
        fail(errors, "retained File Geodatabase is missing")
    if not aprx_path.is_file() or sha256(aprx_path) != external["arcgis_project_sha256"]:
        fail(errors, "retained APRX is missing or hash differs")
    if not pdf_path.is_file() or sha256(pdf_path) != external["pdf_export_sha256"]:
        fail(errors, "retained PDF is missing or hash differs")

    if not errors:
        expected_relationships = sorted(item["name"] for item in schema["relationships"])
        actual_relationships: list[str] = []
        for _, _, names in arcpy.da.Walk(str(gdb), datatype="RelationshipClass"):
            actual_relationships.extend(names)
        if sorted(actual_relationships) != expected_relationships:
            fail(errors, "relationship-class inventory differs from schema")

        domains = {domain.name: domain for domain in arcpy.da.ListDomains(str(gdb))}
        for name, definition in schema["domains"].items():
            if name not in domains:
                fail(errors, f"missing domain {name}")
            elif domains[name].codedValues != definition["coded_values"]:
                fail(errors, f"coded values differ for domain {name}")

        for definition in schema["datasets"]:
            dataset = gdb / definition["name"]
            if not arcpy.Exists(str(dataset)):
                fail(errors, f"missing dataset {definition['name']}")
                continue
            actual_count = int(arcpy.management.GetCount(str(dataset))[0])
            expected_count = schema["initial_counts"][definition["name"]]
            if actual_count != expected_count:
                fail(errors, f"{definition['name']} row count {actual_count} != {expected_count}")
            actual_fields = {field.name: field for field in arcpy.ListFields(str(dataset))}
            for field in definition["fields"]:
                if field["name"] not in actual_fields:
                    fail(errors, f"{definition['name']} missing field {field['name']}")
                elif field.get("domain") and actual_fields[field["name"]].domain != field["domain"]:
                    fail(errors, f"{definition['name']}.{field['name']} domain differs")
            if definition["kind"] == "feature_class":
                wkid = arcpy.Describe(str(dataset)).spatialReference.factoryCode
                if wkid != 32645:
                    fail(errors, f"{definition['name']} is not EPSG:32645")

        project = arcpy.mp.ArcGISProject(str(aprx_path))
        maps = project.listMaps(schema["map_name"])
        layouts = project.listLayouts(schema["layout_name"])
        if len(maps) != 1 or maps[0].spatialReference.factoryCode != 32645:
            fail(errors, "APRX map is missing or not EPSG:32645")
        if len(layouts) != 1:
            fail(errors, "APRX layout is missing")
        else:
            element_names = {element.name for element in layouts[0].listElements()}
            required_elements = {"Title", "Subtitle", "Claim Boundary", "Verified Numeric Scale", "North Arrow", "Legend", "Evidence Map Frame"}
            missing = sorted(required_elements - element_names)
            if missing:
                fail(errors, "APRX layout elements missing: " + ", ".join(missing))

    result = {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "receipt": str(args.receipt),
        "arcgis_version": arcpy.GetInstallInfo().get("Version"),
        "dataset_count": len(schema["datasets"]),
        "relationship_count": len(schema["relationships"]),
        "retained_failure_count": len(receipt.get("retained_failures", [])),
    }
    print(json.dumps(result, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
