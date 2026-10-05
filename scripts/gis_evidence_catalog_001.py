"""Offline lineage and history for the existing unverified atlas; metadata only."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess

from arcgis_demo_roundtrip import inventory, reject_links, sha256, write_new
from gis_experiment_atlas_001 import AOI_HASH, PRINCIPAL_MAPS, RASTERS
from package_gis_experiment_atlas_001 import seal_zip

RECORDS = {
    "manifest": ("records/source-manifest.json", "historical candidate identity; not current custody"),
    "readme": ("records/readiness/m2-asf-hyp3-rtc-readme-first-terminal-reconciliation-001.json", "retained deferred provenance predicate"),
    "provenance": ("records/readiness/m2-asf-hyp3-rtc-composite-provenance-001-terminal-reconciliation.json", "later composite provenance; no pixel fitness"),
    "before_qa": ("records/readiness/m2-asf-hyp3-rtc-product-pixel-001-terminal-reconciliation.json", "before-source full-area fitness"),
    "after_archive": ("records/readiness/m2-asf-hyp3-rtc-acquire-after-partial-001-terminal-reconciliation.json", "after-archive integrity only"),
    "after_metadata": ("records/readiness/m2-asf-hyp3-rtc-after-metadata-001-terminal-reconciliation.json", "after-product metadata capture"),
    "after_qa": ("records/readiness/m2-asf-hyp3-rtc-after-pixel-001-terminal-reconciliation.json", "after-source full-area fitness"),
    "pair": ("records/readiness/m2-asf-hyp3-rtc-partial-pair-stage-001-terminal-reconciliation.json", "same-cell partial visual screen and raster lineage"),
    "panel": ("records/readiness/m2-asf-hyp3-rtc-partial-panel-001-terminal-reconciliation.json", "original local visual; not scientific admission"),
    "landsat": ("records/readiness/m2-landsat9-visual-route-completion-001-terminal-reconciliation.json", "retained optical inconclusive result"),
    "alternate_optical": ("records/readiness/m2-optical-alternate-source-route-001-terminal-reconciliation.json", "retained alternate optical inconclusive result"),
    "native_radar": ("records/processing/m2-radar-esri-sequence-recovery-005-terminal-reconciliation.json", "retained native radar processing block"),
    "rights": ("records/readiness/gis-demonstration-001-existing-vv-rights.json", "credited existing VV demonstration use"),
    "initial_demo": ("records/readiness/gis-demonstration-001-result.json", "initial demonstration and four retained PPKX failures"),
    "brightness": ("records/readiness/gis-demonstration-001-brightness-difference-result.json", "unverified numeric calculation and retained mechanical failures"),
    "atlas": ("records/readiness/gis-demonstration-001-atlas-result.json", "five-map handoff and retained engineering failures"),
}


def build_catalog(documents, hashes):
    """Normalize exact recorded facts; do not derive pixels or change dispositions."""
    if set(documents) != set(RECORDS) or set(hashes) != set(RECORDS):
        raise ValueError("Exact curated public record set required")
    history = []
    for key, (ref, scope) in RECORDS.items():
        d = documents[key]
        if not isinstance(d.get("status"), str) or not d["status"]:
            raise ValueError("Exact original status missing")
        history.append({"Evidence_Key": key, "Record_ID": d.get("record_id") or d.get("manifest_id") or Path(ref).stem,
            "Record_Ref": ref, "SHA256": hashes[key], "Exact_Status": d["status"], "Scope": scope})
    manifest = {row["source_id"]: row for row in documents["manifest"]["records"]}
    identities = []
    pair, bright, atlas = documents["pair"], documents["brightness"], documents["atlas"]
    if pair["pair_measurement"]["scientific_admission"] or bright["scientific_admission"] or atlas["scientific_admission"]:
        raise ValueError("This catalog is for the existing unverified experiment only")
    if pair["bindings"]["before_source_id"] != "M1-SRC-002" or pair["bindings"]["after_source_id"] != "M1-SRC-005":
        raise ValueError("Pair identity changed")
    inputs = {row["source_id"]: row for row in bright["inputs"]}
    for source, role, date, filename in (("M1-SRC-002", "before", "2026-08-16", "before_common_valid_vv_db.tif"),
                                       ("M1-SRC-005", "after", "2026-08-28", "after_common_valid_vv_db.tif")):
        row, inp = manifest[source], inputs[source]
        if row["event_role"] != role or not row["acquisition_start_utc"].startswith(date) or inp["date"] != date:
            raise ValueError("Source role or date changed")
        if inp["sha256"] != RASTERS[filename] or pair["staged_display"][role + "_sha256"] != RASTERS[filename]:
            raise ValueError("Staged raster lineage changed")
        archive_sha = pair["bindings"][role + "_archive_sha256"]
        recorded_archive = documents["before_qa"]["bindings"]["archive_sha256"] if role == "before" else documents["after_archive"]["bindings"]["archive_sha256"]
        if archive_sha != recorded_archive:
            raise ValueError("RTC archive identity differs")
        identities.append({"Source_ID": source, "Role": role, "Product_ID": row["exact_product_id"],
            "Acquisition_Start_UTC": row["acquisition_start_utc"], "Acquisition_End_UTC": row["acquisition_end_utc"],
            "Orbit_JSON": json.dumps(row["orbit_or_tile"], sort_keys=True), "RTC_Archive_SHA256": archive_sha,
            "Displayed_Raster": filename, "Displayed_Raster_SHA256": RASTERS[filename],
            "Full_Area_Disposition": "defer", "Scientific_Admission": "not admitted"})
    if documents["after_qa"]["observations"]["both_AOIs_full_area_QA_status"] != "defer":
        raise ValueError("After-source original disposition differs")
    if any(row["status"] != "defer" for row in documents["before_qa"]["event_AOI_results"]):
        raise ValueError("Before-source original disposition differs")
    if atlas["rasters"] != RASTERS or {row["file"]: row["sha256"] for row in bright["numeric_outputs"]} != {
        key: RASTERS[key] for key in ("delta_vv_db.tif", "excluded_cells.tif")}:
        raise ValueError("Derived artifact identity differs")
    lineage = []
    artifact_hashes = {**RASTERS, "Nepal_Unverified_Atlas.ppkx": atlas["package"]["sha256"]}
    def edge(child, parent, evidence):
        lineage.append({"Child": child, "Parent": parent, "Evidence_Key": evidence,
            "Child_SHA256": artifact_hashes.get(child, ""), "Parent_SHA256": artifact_hashes.get(parent, ""),
            "Relation": "contains logical layout" if child.endswith(".ppkx") else "display uses" if child.startswith("layout:") else "derived from",
            "Record_Ref": RECORDS[evidence][0], "Record_SHA256": hashes[evidence]})
    for row in identities:
        edge(row["Displayed_Raster"], row["Source_ID"], "pair")
    for filename in ("delta_vv_db.tif", "excluded_cells.tif"):
        for parent in ("before_common_valid_vv_db.tif", "after_common_valid_vv_db.tif"):
            edge(filename, parent, "brightness")
    for name in PRINCIPAL_MAPS:
        parents = ["before_common_valid_vv_db.tif", "after_common_valid_vv_db.tif"] if name in {
            "source_area_comparison", "upper_corridor_comparison"} else ["after_common_valid_vv_db.tif"] if name == "regional_overview" else [
            "delta_vv_db.tif"] if name == "evidence_map" else ["excluded_cells.tif"]
        for parent in parents:
            edge("layout:" + name, parent, "atlas")
        edge("Nepal_Unverified_Atlas.ppkx", "layout:" + name, "atlas")
    coverage = []
    for row in documents["before_qa"]["event_AOI_results"]:
        coverage.append({"Source_or_Pair": "M1-SRC-002", "AOI_ID": row["aoi_id"],
            "Fraction_of_Full_AOI": row["usable_fraction_of_aoi"], "Exact_Disposition": row["status"],
            "Evidence_Key": "before_qa", "Measurement": "individual-source usable VV/VH area"})
    after = documents["after_qa"]["observations"]
    common = pair["pair_measurement"]
    for aoi, prefix in (("AOI-SOURCE", "AOI_SOURCE"), ("AOI-UPPER-CORRIDOR", "AOI_UPPER_CORRIDOR")):
        coverage.append({"Source_or_Pair": "M1-SRC-005", "AOI_ID": aoi, "Fraction_of_Full_AOI": after[prefix + "_usable_fraction"],
            "Exact_Disposition": after["both_AOIs_full_area_QA_status"], "Evidence_Key": "after_qa", "Measurement": "individual-source usable VV/VH area"})
        coverage.append({"Source_or_Pair": "M1-SRC-002 + M1-SRC-005", "AOI_ID": aoi,
            "Fraction_of_Full_AOI": common[prefix + "_common_valid_fraction"], "Exact_Disposition": pair["status"],
            "Evidence_Key": "pair", "Measurement": "same-cell common valid VV/VH area; display uses VV only"})
    if any(not 0 <= row["Fraction_of_Full_AOI"] <= 1 for row in coverage):
        raise ValueError("Recorded coverage fraction outside unit interval")
    claims = [
        {"Claim_ID": "EXP-OBS-001", "Kind": "sensor measurement", "Statement": bright["formula"],
         "Review_State": "unverified registration; no admitted landscape-change feature", "Evidence_Key": "brightness"},
        {"Claim_ID": "EXP-INTERP-001", "Kind": "interpretation boundary", "Statement": "No geomorphic interpretation performed",
         "Review_State": "not assessed", "Evidence_Key": "atlas"},
        {"Claim_ID": "EXP-ATTRIB-001", "Kind": "attribution boundary", "Statement": "No causal event attribution performed",
         "Review_State": "not assessed", "Evidence_Key": "atlas"},
    ]
    return {"schema_version": "1.0", "purpose": "Offline catalog of existing unverified experiment and selected retained history",
        "crs": "EPSG:32645", "SourceIdentity": identities, "EvidenceHistory": history, "ArtifactLineage": lineage,
        "CoverageHistory": coverage, "ClaimRegister": claims, "scientific_admission": False,
        "artifact_hashes": artifact_hashes, "logical_entity_hashes": "blank for source IDs and logical layouts; hashes identify files only",
        "history_is_curated_not_exhaustive": True, "original_scientific_contracts_and_statuses_unchanged": True}


def primary_tables(path):
    """Read exact existing SQLite rows; no raster access or geometry computation."""
    db = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    try:
        return {name: db.execute('SELECT * FROM "' + name + '" ORDER BY 1').fetchall()
                for name in ("StudyAreas", "DisplayedSources", "ExperimentMethod")}
    finally:
        # A SQLite transaction context does not close its connection on exit.
        db.close()


def add_geopackage_tables(path, catalog):
    from osgeo import ogr
    ogr.UseExceptions()
    original = primary_tables(path.resolve())
    ds = ogr.Open(str(path), 1)
    if ds is None:
        raise ValueError("Writable fresh-copy GeoPackage required")
    counts = {}
    for name in ("SourceIdentity", "EvidenceHistory", "ArtifactLineage", "CoverageHistory", "ClaimRegister"):
        if ds.GetLayerByName(name) is not None:
            raise ValueError("Catalog table already exists")
        rows = catalog[name]
        layer = ds.CreateLayer(name, None, ogr.wkbNone)
        for field, value in rows[0].items():
            layer.CreateField(ogr.FieldDefn(field, ogr.OFTReal if isinstance(value, float) else ogr.OFTString))
        for row in rows:
            feature = ogr.Feature(layer.GetLayerDefn())
            for field, value in row.items():
                feature.SetField(field, value)
            layer.CreateFeature(feature)
            feature = None
        counts[name] = layer.GetFeatureCount()
        layer = None
    ds = None
    if original != primary_tables(path.resolve()):
        raise ValueError("Existing geometry or metadata rows changed")
    return counts


def verify_unchanged_original_files(baseline, content):
    current = inventory(content)
    allowed = {"README.md", "artifact-manifest.json", "ExperimentMetadata.gpkg"}
    compared = [name for name in baseline if name not in allowed]
    if any(current.get(name) != baseline[name] for name in compared):
        raise ValueError("An existing raster, map, package or layer changed")
    return len(compared)


def load_public_records(repo):
    tracked = set(subprocess.check_output(["git", "ls-files"], cwd=repo, text=True).splitlines())
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    documents, hashes, snapshots = {}, {}, {}
    for key, (ref, _) in RECORDS.items():
        if ref not in tracked:
            raise ValueError("Private/untracked record must not enter public catalog")
        blob = subprocess.check_output(["git", "show", commit + ":" + ref], cwd=repo)
        document = json.loads(blob)
        if json.loads((repo / ref).read_text(encoding="utf-8")) != document:
            raise ValueError("An uncommitted record change cannot enter the public snapshot")
        documents[key], snapshots[key] = document, blob
        hashes[key] = hashlib.sha256(blob).hexdigest()
    return documents, hashes, snapshots, commit


def extend_bundle(repo, source_bundle, output):
    for path in (repo, source_bundle, output):
        reject_links(path)
    repo, source_bundle, output = (p.resolve() for p in (repo, source_bundle, output))
    if output.exists() or output.is_relative_to(source_bundle) or source_bundle.is_relative_to(output):
        raise ValueError("Fresh disjoint output required")
    manifest = json.loads((source_bundle / "artifact-manifest.json").read_text(encoding="utf-8"))
    baseline = inventory(source_bundle)
    if {name: value for name, value in baseline.items() if name != "artifact-manifest.json"} != manifest["files"]:
        raise ValueError("Base bundle content drift")
    documents, hashes, snapshots, commit = load_public_records(repo)
    catalog = build_catalog(documents, hashes)
    catalog["public_record_snapshot_commit"] = commit
    if sha256(source_bundle / "Nepal_Unverified_Atlas.ppkx") != documents["atlas"]["package"]["sha256"]:
        raise ValueError("Base package identity differs")
    content = output / "Nepal_Unverified_Atlas"
    shutil.copytree(source_bundle, content)
    evidence = content / "evidence"
    evidence.mkdir()
    for key, (ref, _) in RECORDS.items():
        destination = evidence / "records" / ref
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(snapshots[key])
        if sha256(destination) != hashes[key]:
            raise ValueError("Record snapshot identity changed")
    write_new(evidence / "catalog.json", catalog)
    for name in ("SourceIdentity", "EvidenceHistory", "ArtifactLineage", "CoverageHistory", "ClaimRegister"):
        with (evidence / (name + ".csv")).open("x", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(catalog[name][0]))
            writer.writeheader()
            writer.writerows(catalog[name])
    counts = add_geopackage_tables(content / "ExperimentMetadata.gpkg", catalog)
    shutil.copy2(source_bundle / "artifact-manifest.json", evidence / "original-atlas-artifact-manifest.json")
    with (content / "README.md").open("a", encoding="utf-8") as stream:
        stream.write("\n## Offline evidence catalog\n\n"
            "The existing GeoPackage additionally contains SourceIdentity, EvidenceHistory, ArtifactLineage, "
            "CoverageHistory and ClaimRegister attribute tables. These are metadata, not new scientific feature classes. "
            "The same tables are CSV files under `evidence`, with `catalog.json` and 16 exact public record snapshots.\n\n"
            "Add `ExperimentMetadata.gpkg` as a database connection or add its tables in ArcGIS to inspect them. "
            "Record_Ref paths are repository paths; their offline copies are under `evidence/records`. Exact_Status "
            "preserves the original historical outcome. Scope explains what that record evaluated. A successful "
            "processing/CI/display check is not scientific admission. The original candidate manifest remains "
            "historical; its pending custody and review fields are not the present source status.\n\n"
            "Coverage fractions reuse the recorded full-AOI denominators and masks; no fractions were recalculated. "
            "The lineage traces each TIFF and principal layout back to exact source identities and record hashes. "
            "The catalog retains deferred radar coverage, inconclusive optical routes, the native-radar processing "
            "block and demonstration/package failures. It is curated, not every project attempt. No interpretation "
            "or causal assessment is added. The maps, raster values and PPKX are unchanged.\n")
    new_manifest = {"status": "unverified_gis_experiment_with_offline_evidence", "crs": "EPSG:32645",
        "source_rasters": RASTERS, "aoi_sha256": AOI_HASH, "principal_layouts": PRINCIPAL_MAPS,
        "package_sha256": manifest["package_sha256"], "scientific_M6_complete": False,
        "files": {name: value for name, value in inventory(content).items() if name != "artifact-manifest.json"},
        "manifest_excludes_itself": True}
    (content / "artifact-manifest.json").write_text(json.dumps(new_manifest, indent=2) + "\n", encoding="utf-8")
    unchanged_files = verify_unchanged_original_files(baseline, content)
    result = seal_zip(content, output / "Nepal_Unverified_Atlas_Evidence.zip", output / "extracted")
    if inventory(source_bundle) != baseline:
        raise ValueError("Original bundle changed")
    result.update(status="passed_offline_evidence_bundle", gpkg_added_table_counts=counts,
        exact_record_snapshots=len(RECORDS), original_bundle_unchanged=True, PPKX_unchanged=True,
        unchanged_existing_file_hashes=unchanged_files, raster_values_unchanged=True, scientific_admission=False, goal_complete=False)
    write_new(output / "catalog-bundle-receipt.json", result)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--source-bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(extend_bundle(args.repo, args.source_bundle, args.output))
