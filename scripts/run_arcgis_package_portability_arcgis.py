#!/usr/bin/env python3
"""Run one predeclared metadata-only ArcGIS project-package round trip."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import re
import subprocess
import traceback
from pathlib import Path, PurePosixPath
from typing import Any

from PIL import Image

from arcgis_package_portability_core import (
    EXPECTED_DATASET_COUNTS,
    FORBIDDEN_EXTRACTED_SUFFIXES,
    SCIENTIFIC_DATASETS,
    evaluate_runtime,
    inventory_summary,
    sha256_file,
    stable_inventory,
    validate_contract,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REF = "config/qa/arcgis-package-portability-contract.json"
UTC_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
GIT_SHA = re.compile(r"[0-9a-f]{40}")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return value


def write_new_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def stop(code: str) -> None:
    print(json.dumps({"status": "stopped", "code": code, "external_output_created": False}, indent=2))
    raise SystemExit(12)


def git_text(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        stop("git_publication_gate_unavailable")
    return result.stdout.strip()


def contract_child(root: Path, value: str) -> Path:
    posix = PurePosixPath(value)
    if posix.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/")):
        stop("unsafe_external_relative_path")
    candidate = root.joinpath(*posix.parts)
    try:
        candidate.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError:
        stop("external_path_escape")
    return candidate


def pixel_digest(path: Path) -> tuple[list[int], str, str]:
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        digest = hashlib.sha256()
        digest.update(f"{rgb.width}x{rgb.height}:RGB\n".encode("ascii"))
        digest.update(rgb.tobytes())
        return [rgb.width, rgb.height], "RGB", digest.hexdigest()


def gdb_parent(data_source: str) -> Path | None:
    path = Path(data_source)
    for candidate in (path, *path.parents):
        if candidate.suffix.casefold() == ".gdb":
            return candidate
    return None


def inspect_extracted_project(arcpy: Any, extract_root: Path, contract: dict[str, Any]) -> tuple[dict[str, Any], Any]:
    projects = sorted(extract_root.rglob("*.aprx"), key=lambda path: path.as_posix().casefold())
    result: dict[str, Any] = {"project_count": len(projects)}
    if len(projects) != 1:
        return result, None
    project_path = projects[0]
    project = arcpy.mp.ArcGISProject(str(project_path))
    maps = project.listMaps("Evidence Workspace")
    layouts = project.listLayouts("Evidence Workspace Overview")
    result.update({
        "project_path": str(project_path),
        "project_sha256": sha256_file(project_path),
        "map_count": len(maps),
        "layout_count": len(layouts),
        "home_folder": project.homeFolder,
        "default_geodatabase": project.defaultGeodatabase,
        "default_toolbox": project.defaultToolbox,
    })
    if len(maps) != 1 or len(layouts) != 1:
        return result, project
    map_obj = maps[0]
    layers = map_obj.listLayers()
    layer_reports: list[dict[str, Any]] = []
    extracted_root_resolved = extract_root.resolve(strict=True)
    operational_gdbs: set[Path] = set()
    for layer in layers:
        data_source = getattr(layer, "dataSource", None)
        exists = bool(data_source and arcpy.Exists(data_source))
        inside_extract = False
        if data_source:
            try:
                Path(data_source).resolve(strict=False).relative_to(extracted_root_resolved)
                inside_extract = True
            except ValueError:
                inside_extract = False
            parent = gdb_parent(data_source)
            if parent is not None and inside_extract:
                operational_gdbs.add(parent)
        layer_reports.append({
            "name": layer.name,
            "broken": bool(layer.isBroken),
            "is_basemap_layer": bool(layer.isBasemapLayer),
            "data_source": data_source,
            "data_source_exists": exists,
            "data_source_inside_extract_root": inside_extract,
        })
    result.update({
        "map_wkid": map_obj.spatialReference.factoryCode,
        "layers": layer_reports,
        "broken_layer_count": sum(1 for item in layer_reports if item["broken"] or not item["data_source_exists"]),
        "external_operational_source_count": sum(1 for item in layer_reports if not item["data_source_inside_extract_root"]),
        "basemap_layer_count": sum(1 for item in layer_reports if item["is_basemap_layer"]),
        "operational_geodatabase_count": len(operational_gdbs),
    })
    if len(operational_gdbs) == 1:
        geodatabase = next(iter(operational_gdbs))
        counts = {
            name: int(arcpy.management.GetCount(str(geodatabase / name))[0])
            for name in EXPECTED_DATASET_COUNTS
            if arcpy.Exists(str(geodatabase / name))
        }
        relationships: list[str] = []
        for _, _, names in arcpy.da.Walk(str(geodatabase), datatype="RelationshipClass"):
            relationships.extend(names)
        result.update({
            "operational_geodatabase": str(geodatabase),
            "dataset_counts": counts,
            "scientific_record_count": sum(counts.get(name, 0) for name in SCIENTIFIC_DATASETS),
            "relationship_count": len(relationships),
            "relationship_names": sorted(relationships),
            "domain_count": len(arcpy.da.ListDomains(str(geodatabase))),
        })
    return result, project


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checked-at-utc", required=True)
    parser.add_argument("--publication-commit", required=True)
    parser.add_argument("--publication-run-id", required=True, type=int)
    args = parser.parse_args()
    if not UTC_TIMESTAMP.fullmatch(args.checked_at_utc):
        stop("invalid_checked_timestamp")
    if not GIT_SHA.fullmatch(args.publication_commit):
        stop("invalid_publication_commit")
    if args.publication_run_id <= 0:
        stop("invalid_publication_run_id")
    if git_text("status", "--porcelain"):
        stop("repository_not_clean")
    if git_text("rev-parse", "HEAD") != args.publication_commit or git_text("rev-parse", "origin/main") != args.publication_commit:
        stop("publication_commit_not_current_local_and_remote_main")

    contract = load_json(ROOT / CONTRACT_REF)
    if validate_contract(contract):
        stop("arcgis_package_contract_invalid")
    for item in contract.get("inputs", {}).values():
        if not isinstance(item, dict):
            stop("contract_input_binding_invalid")
        path = ROOT / item.get("ref", "")
        if not path.is_file() or sha256_file(path) != item.get("sha256"):
            stop("contract_input_binding_mismatch")
    goal = load_json(ROOT / contract["inputs"]["long_term_goal"]["ref"])
    milestone = load_json(ROOT / contract["inputs"]["active_milestone"]["ref"])
    required_actions = {"routine_qa", "metadata_capture", "evidence_recording", "data_processing"}
    if goal.get("status") != "active" or milestone.get("status") != "active":
        stop("project_or_milestone_not_active")
    if not required_actions.issubset(set(milestone.get("authority", {}).get("authorized_action_classes", []))):
        stop("required_action_class_not_authorized")

    source = contract["source_workspace"]
    source_root = Path(source["root"])
    if not source_root.is_dir():
        stop("source_workspace_missing")
    source_assets = {
        "project": source_root / source["project"],
        "geodatabase": source_root / source["geodatabase"],
        "overview_png": source_root / source["overview_png"],
        "overview_pdf": source_root / source["overview_pdf"],
    }
    if (
        not source_assets["project"].is_file()
        or not source_assets["geodatabase"].is_dir()
        or not source_assets["overview_png"].is_file()
        or not source_assets["overview_pdf"].is_file()
        or sha256_file(source_assets["project"]) != source["project_sha256"]
        or sha256_file(source_assets["overview_png"]) != source["overview_png_sha256"]
        or sha256_file(source_assets["overview_pdf"]) != source["overview_pdf_sha256"]
    ):
        stop("source_workspace_asset_identity_mismatch")
    source_before_items = stable_inventory(source_root)
    source_before = inventory_summary(source_before_items)
    if source_before != source["expected_inventory"]:
        stop("source_workspace_inventory_mismatch")

    external_root = Path(contract["external_output"]["root"])
    external_data_root = ROOT.parent / f"{ROOT.name}-data"
    if not external_data_root.is_dir():
        stop("external_data_root_missing")
    try:
        external_root.resolve(strict=False).relative_to(external_data_root.resolve(strict=True))
    except ValueError:
        stop("external_output_outside_project_data_root")
    if external_root.exists():
        stop("external_attempt_collision")
    package_path = contract_child(external_root, contract["external_output"]["package"])
    extract_root = contract_child(external_root, contract["external_output"]["extract_root"])
    png_path = contract_child(external_root, contract["external_output"]["reexport_png"])
    pdf_path = contract_child(external_root, contract["external_output"]["reexport_pdf"])
    manifest_path = contract_child(external_root, contract["external_output"]["manifest"])
    receipt_path = contract_child(external_root, contract["external_output"]["receipt"])
    failure_path = contract_child(external_root, contract["external_output"]["failure_receipt"])

    external_root.parent.mkdir(parents=True, exist_ok=True)
    external_root.mkdir(exist_ok=False)
    try:
        os.environ.setdefault("GDAL_PAM_ENABLED", "NO")
        import arcpy  # type: ignore[import-not-found]

        install = arcpy.GetInstallInfo()
        operation = contract["operation"]
        arcpy.management.PackageProject(
            in_project=str(source_assets["project"]),
            output_file=str(package_path),
            sharing_internal=operation["sharing_internal"],
            package_as_template=operation["package_as_template"],
            summary="Metadata-only Nepal 2026 ArcGIS evidence-workspace portability fixture; no scientific observations or raster pixels.",
            tags="Nepal 2026, metadata only, portability fixture",
            version=operation["version"],
            include_toolboxes=operation["include_toolboxes"],
            include_history_items=operation["include_history_items"],
            read_only=operation["read_only"],
            select_related_rows=operation["select_related_rows"],
            preserve_sqlite=operation["preserve_sqlite"],
        )
        if not package_path.is_file():
            raise RuntimeError("PackageProject returned without the exact output package")
        arcpy.management.ExtractPackage(
            in_package=str(package_path),
            output_folder=str(extract_root),
            cache_package=operation["extract_cache"],
        )
        extracted_inventory = stable_inventory(extract_root)
        forbidden = [
            item["relative_path"] for item in extracted_inventory
            if Path(item["relative_path"]).suffix.casefold() in FORBIDDEN_EXTRACTED_SUFFIXES
        ]
        symlink_count = sum(1 for path in extract_root.rglob("*") if path.is_symlink())
        project_report, extracted_project = inspect_extracted_project(arcpy, extract_root, contract)
        if extracted_project is not None and project_report.get("layout_count") == 1:
            png_path.parent.mkdir(parents=True, exist_ok=False)
            layout = extracted_project.listLayouts("Evidence Workspace Overview")[0]
            layout.exportToPNG(str(png_path), resolution=160, color_mode="24-BIT_TRUE_COLOR")
            layout.exportToPDF(str(pdf_path), resolution=160, image_quality="BEST")
        del extracted_project
        gc.collect()
        source_after_items = stable_inventory(source_root)
        source_after = inventory_summary(source_after_items)
        source_dimensions, source_mode, source_pixel_sha = pixel_digest(source_assets["overview_png"])
        if png_path.is_file():
            output_dimensions, output_mode, output_pixel_sha = pixel_digest(png_path)
        else:
            output_dimensions, output_mode, output_pixel_sha = [], None, None
        runtime_report = {
            "source": {
                "before": source_before,
                "after": source_after,
                "unchanged": source_before_items == source_after_items,
            },
            "package": {
                "exists": package_path.is_file(),
                "path": str(package_path),
                "size_bytes": package_path.stat().st_size if package_path.is_file() else None,
                "sha256": sha256_file(package_path) if package_path.is_file() else None,
            },
            "extracted": {
                **inventory_summary(extracted_inventory),
                "stable_file_count": len(extracted_inventory),
                "forbidden_raster_files": forbidden,
                "symlink_count": symlink_count,
            },
            "extracted_project": project_report,
            "reexports": {
                "png_exists": png_path.is_file(),
                "pdf_exists": pdf_path.is_file(),
                "png_path": str(png_path),
                "pdf_path": str(pdf_path),
                "png_size_bytes": png_path.stat().st_size if png_path.is_file() else None,
                "pdf_size_bytes": pdf_path.stat().st_size if pdf_path.is_file() else None,
                "png_sha256": sha256_file(png_path) if png_path.is_file() else None,
                "pdf_sha256": sha256_file(pdf_path) if pdf_path.is_file() else None,
                "png_dimensions": output_dimensions,
                "png_mode": output_mode,
                "source_png_dimensions": source_dimensions,
                "source_png_mode": source_mode,
                "source_png_pixel_sha256": source_pixel_sha,
                "output_png_pixel_sha256": output_pixel_sha,
                "png_pixel_sha256_matches_source": output_pixel_sha == source_pixel_sha,
            },
        }
        decision = evaluate_runtime(runtime_report, contract)
        artifact_inventory = stable_inventory(external_root)
        artifact_manifest = {
            "manifest_version": "1.0",
            "attempt_id": "arcgis-package-portability-attempt-001",
            "created_at_utc": args.checked_at_utc,
            "scope": "package, extracted package, and round-trip exports before manifest and receipt creation",
            "summary": inventory_summary(artifact_inventory),
            "files": artifact_inventory,
        }
        write_new_json(manifest_path, artifact_manifest)
        receipt = {
            "receipt_version": "1.0",
            "receipt_id": "NEPAL-M6-ARCGIS-PACKAGE-PORTABILITY-REAL-001",
            "checked_at_utc": args.checked_at_utc,
            "status": decision["status"],
            "runtime": {
                "product": install.get("ProductName", "ArcGISPro"),
                "version": install.get("Version"),
                "license_level": install.get("LicenseLevel") or arcpy.ProductInfo(),
            },
            "publication_gate": {
                "commit_sha": args.publication_commit,
                "remote_ref": "refs/remotes/origin/main",
                "remote_commit_verified": True,
                "github_actions_run_id": args.publication_run_id,
                "github_actions_conclusion_verified_before_execution": True,
            },
            "bindings": {
                "contract_ref": CONTRACT_REF,
                "contract_sha256": sha256_file(ROOT / CONTRACT_REF),
                "external_manifest_path": str(manifest_path),
                "external_manifest_sha256": sha256_file(manifest_path),
            },
            "runtime_report": runtime_report,
            "decision": decision,
            "activity": {
                "network_requests_performed": False,
                "authentication_performed": False,
                "credential_values_read_or_recorded": False,
                "source_workspace_mutated": source_before_items != source_after_items,
                "package_created_outside_git": package_path.is_file(),
                "package_extracted_to_fresh_external_directory": extract_root.is_dir(),
                "scientific_pixels_read_or_written": False,
            },
            "claim_boundary": contract["claim_boundary"],
            "limitations": contract["limitations"],
        }
        write_new_json(receipt_path, receipt)
        print(json.dumps({"status": receipt["status"], "external_receipt": str(receipt_path)}, indent=2))
        return 0 if decision["status"] == "pass_same_machine_runtime_manual_visual_review_pending" else 20
    except BaseException as exc:
        failure = {
            "receipt_version": "1.0",
            "receipt_id": "NEPAL-M6-ARCGIS-PACKAGE-PORTABILITY-ATTEMPT-001-FAILURE",
            "checked_at_utc": args.checked_at_utc,
            "status": "fail_retained",
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "traceback": traceback.format_exc(),
            "source_inventory_before": source_before,
            "source_inventory_after": inventory_summary(stable_inventory(source_root)),
            "attempt_root": str(external_root),
            "automatic_retry_authorized": False,
            "limitations": contract["limitations"],
        }
        if not failure_path.exists():
            write_new_json(failure_path, failure)
        print(json.dumps({"status": "fail_retained", "failure_receipt": str(failure_path)}, indent=2))
        return 20


if __name__ == "__main__":
    raise SystemExit(main())
