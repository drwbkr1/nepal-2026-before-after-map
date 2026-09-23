#!/usr/bin/env python3
"""One bounded two-source event-area radar QA process; no baseline or change analysis."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from m2_dem_vertical_datum_proj25_core import controlled_path, sha256_file
from m2_radar_event_pair_dem_conversion_001 import OLD_CONTRACT_REF, conversion_items
from m2_radar_event_pair_dem_intake_001 import DATA_ROOT, IntakeError, ROOT
from m2_radar_event_pair_dem_mosaic_001 import MOSAIC
from m2_radar_event_pair_dem_footprint_gate_001 import IDS, OUTPUT as FOOTPRINT_GATE
from m2_radar_esri_sequence_recovery_005_core import load_execution_plan, SOURCE_OUTPUT_NAMES
from m2_radar_pixel_orbit_application_001_core import (
    inventory_sha256, require_external_child, stable_inventory, evaluate_route,
)
from m2_radar_esri_sequence_processing_005 import (
    aoi_bounds, arcgis_signature_status, create_analysis_support, grid_for_raster,
    make_band_layer, measure_stable_registration_windowed, now_utc, process_source,
    raster_identity, safe_error, source_output_root, tabulate_radar_aoi,
)


PREFIX = "m2-radar-event-area-pair-001"
ATTEMPT_ROOT = DATA_ROOT / "e1" / "a1"
IMPLEMENTATION_GATE = ROOT / "records/readiness" / f"{PREFIX}-radar-implementation-gate.json"
PREFLIGHT = ROOT / "records/readiness" / f"{PREFIX}-radar-final-preflight.json"
PAIRED_ROUTE_ID = "PAIR-S1-ASC-R085-IW"
REQUIRED_AOIS = ("AOI-SOURCE", "AOI-UPPER-CORRIDOR")
MIN_FREE_BYTES = 60 * 1024**3


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise IntakeError("event_pair_record_not_object")
    return value


def verify_authority() -> dict[str, Any]:
    proposal = ROOT / "contracts/milestone-002-radar-event-area-pair-001-proposal.json"
    bundle = ROOT / "reviews/m2-radar-event-area-pair-001/review-bundle.json"
    approval = read_json(ROOT / "records/source-gates/m2-radar-event-area-pair-001-approval.json")
    footprint = read_json(FOOTPRINT_GATE)
    if (sha256_file(proposal) != "ae5fe535123debcd8619487bbdd68e2c19ff49dbc2505795fcdc48cea324b1e2"
            or sha256_file(bundle) != "ad6f0f5e75c768721ebbc787e6550dcb28e61fba22c86271beed982d220a5423"
            or approval.get("decision") != "approve" or approval.get("attestation") is not True
            or footprint.get("status") != "pass_full_actual_sar_footprints_have_valid_dem"
            or [item.get("source_id") for item in footprint.get("source_results", [])] != list(IDS)
            or any(item.get("invalid_dem_cells") != 0 for item in footprint["source_results"])
            or footprint.get("mosaic_output_sha256") != sha256_file(MOSAIC)):
        raise IntakeError("event_pair_authority_or_footprint_gate_drift")
    return footprint


def event_plan() -> dict[str, Any]:
    verify_authority()
    plan = load_execution_plan(ROOT)
    if Path(plan["data_root"]).resolve(strict=True) != DATA_ROOT.resolve(strict=True):
        raise IntakeError("external_data_root_drift")
    sources = [item for item in plan["sources"] if item["source_id"] in IDS]
    if [item["source_id"] for item in sources] != list(IDS):
        raise IntakeError("event_pair_source_subset_drift")
    if [item["orbit_source_id"] for item in sources] != ["M2-ORB-001", "M2-ORB-003"]:
        raise IntakeError("event_pair_orbit_pair_drift")
    plan["sources"] = sources
    plan["orbits"] = {key: value for key, value in plan["orbits"].items() if key in ("M2-ORB-001", "M2-ORB-003")}
    old = read_json(OLD_CONTRACT_REF)["dem_sources_in_exact_order"]
    dem_items = old + conversion_items(require_outputs_absent=False)
    if len(dem_items) != 11:
        raise IntakeError("event_pair_dem_count_drift")
    plan["dems"] = []
    for item in dem_items:
        path = controlled_path(item["output_relative_path"])
        receipt_path = ROOT / "records/processing" / f"{item['source_id'].lower()}-proj25-conversion-001-terminal.json"
        receipt = read_json(receipt_path)
        if receipt.get("status") != "pass_converted_verified_promoted" or sha256_file(path) != receipt.get("promoted", {}).get("sha256"):
            raise IntakeError("event_pair_dem_derivative_drift")
        plan["dems"].append({
            "source_id": item["source_id"],
            "destination_path": str(path),
            "ellipsoidal_derivative_sha256": receipt["promoted"]["sha256"],
            "ellipsoidal_derivative_size_bytes": receipt["promoted"]["size_bytes"],
        })
    contract = dict(plan["contract"])
    contract["attempt"] = {"attempt_id": "radar-event-area-pair-001-real-001", "external_attempt_root": str(ATTEMPT_ROOT)}
    contract["attempt_local_receipts"] = True
    contract["receipt_namespace"] = "RADAR-EVENT-AREA-PAIR-001"
    contract["short_path_source_aliases"] = {"M1-SRC-002": "2", "M1-SRC-005": "5"}
    plan["contract"] = contract
    plan["contract_sha256"] = sha256_file(ROOT / "contracts/milestone-002-radar-event-area-pair-001-proposal.json")
    return plan


def projected_paths(plan: dict[str, Any]) -> dict[str, Any]:
    if ATTEMPT_ROOT.exists():
        raise IntakeError("event_pair_attempt_root_collision")
    paths = [ATTEMPT_ROOT / name for name in (
        "started.json", "terminal.json", "error.json", "cleanup.json", "stages.jsonl",
        "support/qa.gdb", "support/snap_10m.tif", "routes/event-pair/pair_exclusion_mask.tif",
    )]
    for source in plan["sources"]:
        source_id = source["source_id"]
        root = source_output_root(plan, ATTEMPT_ROOT, source_id)
        for name in SOURCE_OUTPUT_NAMES:
            paths.append(root / name)
        manifest = read_json(require_external_child(DATA_ROOT, Path(source["external_manifest_path"])))
        for item in manifest.get("files", []):
            relative = Path(item["relative_path"])
            if relative.is_absolute() or ".." in relative.parts:
                raise IntakeError("unsafe_safe_inventory_relative_path")
            paths.append(root / source["exact_product_id"] / relative)
    rendered = [str(path) for path in paths]
    if len(set(item.casefold() for item in rendered)) != len(rendered):
        raise IntakeError("event_pair_projected_path_collision")
    maximum = max(map(len, rendered))
    if maximum > 240:
        raise IntakeError("event_pair_projected_path_above_240")
    return {"projected_path_count": len(paths), "maximum_projected_path_characters": maximum, "maximum_allowed_path_characters": 240}


def no_content_preflight(arcpy: Any) -> dict[str, Any]:
    if PREFLIGHT.exists():
        raise IntakeError("event_pair_radar_preflight_collision")
    gate = read_json(IMPLEMENTATION_GATE)
    if (gate.get("status") != "pass_public_ci_event_pair_radar_implementation"
            or gate.get("runner_sha256") != sha256_file(Path(__file__))
            or gate.get("footprint_gate_sha256") != sha256_file(FOOTPRINT_GATE)):
        raise IntakeError("event_pair_radar_public_implementation_gate_missing")
    plan = event_plan()
    projections = projected_paths(plan)
    free = shutil.disk_usage(DATA_ROOT).free
    signatures = arcgis_signature_status(arcpy)
    image_analyst = arcpy.CheckExtension("ImageAnalyst")
    spatial = arcpy.CheckExtension("Spatial")
    if (free < MIN_FREE_BYTES or not signatures["all_match"]
            or image_analyst != "Available" or spatial != "Available"
            or not all(Path(item["safe_root"]).is_dir() for item in plan["sources"])
            or not all(Path(item["custody_path"]).is_file() for item in plan["orbits"].values())
            or not MOSAIC.is_file()):
        raise IntakeError("event_pair_radar_preflight_predicate_failed")
    return {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-EVENT-AREA-PAIR-001-RADAR-FINAL-PREFLIGHT",
        "checked_at_utc": now_utc(),
        "status": "pass_final_no_content_two_source_radar_preflight",
        "implementation_gate_sha256": sha256_file(IMPLEMENTATION_GATE),
        "footprint_gate_sha256": sha256_file(FOOTPRINT_GATE),
        "mosaic_sha256": sha256_file(MOSAIC),
        "source_order": list(IDS),
        "orbit_order": ["M2-ORB-001", "M2-ORB-003"],
        "path_projection": projections,
        "free_bytes": free,
        "minimum_free_bytes": MIN_FREE_BYTES,
        "arcgis_version": arcpy.GetInstallInfo().get("Version"),
        "image_analyst": image_analyst,
        "spatial_analyst": spatial,
        "project_source_content_read": False,
        "dem_pixel_read": False,
        "radar_geoprocessing_started": False,
        "automatic_retry": False,
    }


def verify_input_identities(plan: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"sources": {}, "orbits": {}, "dems": {}}
    for source in plan["sources"]:
        safe = require_external_child(DATA_ROOT, Path(source["safe_root"]))
        manifest_path = require_external_child(DATA_ROOT, Path(source["external_manifest_path"]))
        if sha256_file(manifest_path) != source["external_manifest_sha256"]:
            raise IntakeError("event_pair_safe_manifest_hash_drift")
        manifest = read_json(manifest_path)
        expected = sorted(({"relative_path": item["relative_path"], "size_bytes": item["size_bytes"], "sha256": item["sha256"]}
                           for item in manifest["files"]), key=lambda item: item["relative_path"].casefold())
        actual = stable_inventory(safe)
        if actual != expected:
            raise IntakeError("event_pair_safe_member_byte_drift")
        result["sources"][source["source_id"]] = {"inventory_sha256": inventory_sha256(actual), "file_count": len(actual)}
    for orbit_id, orbit in plan["orbits"].items():
        path = require_external_child(DATA_ROOT, Path(orbit["custody_path"]))
        if path.stat().st_size != orbit["custody_size_bytes"] or sha256_file(path) != orbit["custody_sha256"]:
            raise IntakeError("event_pair_orbit_byte_drift")
        result["orbits"][orbit_id] = orbit["custody_sha256"]
    for item in plan["dems"]:
        path = require_external_child(DATA_ROOT, Path(item["destination_path"]))
        if path.stat().st_size != item["ellipsoidal_derivative_size_bytes"] or sha256_file(path) != item["ellipsoidal_derivative_sha256"]:
            raise IntakeError("event_pair_dem_byte_drift")
        result["dems"][item["source_id"]] = item["ellipsoidal_derivative_sha256"]
    if sha256_file(MOSAIC) != read_json(FOOTPRINT_GATE)["mosaic_output_sha256"]:
        raise IntakeError("event_pair_mosaic_byte_drift")
    result["mosaic"] = sha256_file(MOSAIC)
    return result


def source_sequence(worker: Callable[[str], dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for source_id in IDS:
        result = worker(source_id)
        if result.get("source_id") != source_id:
            raise IntakeError("event_pair_source_worker_identity_drift")
        results.append(result)
        if result.get("status") != "pass_source_qa_only":
            break
    return results


def event_aoi_only(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected = [item for item in observations if item.get("aoi_id") in REQUIRED_AOIS]
    if [item["aoi_id"] for item in selected] != sorted(REQUIRED_AOIS):
        raise IntakeError("event_pair_required_aoi_observations_missing")
    return selected


def evaluate_pair_route(arcpy: Any, plan: dict[str, Any], support: dict[str, Any]) -> dict[str, Any]:
    attempt = ATTEMPT_ROOT
    route = attempt / "routes" / "event-pair"
    route.mkdir(parents=True, exist_ok=False)
    source_before = source_output_root(plan, attempt, IDS[0])
    source_after = source_output_root(plan, attempt, IDS[1])
    before_linear = source_before / "gamma0_linear_epsg32645_10m.crf"
    after_linear = source_after / "gamma0_linear_epsg32645_10m.crf"
    before_mask_path = source_before / "geometric_distortion_mask_epsg32645_10m.crf"
    after_mask_path = source_after / "geometric_distortion_mask_epsg32645_10m.crf"
    for path in (before_linear, after_linear, before_mask_path, after_mask_path):
        if not path.exists():
            raise IntakeError("event_pair_required_source_output_missing")
    before_vv = make_band_layer(arcpy, before_linear, "event_pair_before_vv", 1)
    after_vv = make_band_layer(arcpy, after_linear, "event_pair_after_vv", 1)
    try:
        before_mask = arcpy.sa.Int(arcpy.sa.Raster(str(before_mask_path)) + 0.5)
        after_mask = arcpy.sa.Int(arcpy.sa.Raster(str(after_mask_path)) + 0.5)
        covered = (~arcpy.sa.IsNull(before_vv)) & (~arcpy.sa.IsNull(after_vv))
        layover = (before_mask == 4) | (before_mask == 5) | (after_mask == 4) | (after_mask == 5)
        shadow = (before_mask == 3) | (after_mask == 3)
        undetermined = (before_mask == 0) | (after_mask == 0)
        geometric_valid = ((before_mask == 1) | (before_mask == 2)) & ((after_mask == 1) | (after_mask == 2))
        categorical = arcpy.sa.Con(layover, 2, arcpy.sa.Con(shadow, 3, arcpy.sa.Con(undetermined, 0, arcpy.sa.Con(geometric_valid, 1, 90))))
        pair_mask = route / "pair_exclusion_mask.tif"
        arcpy.sa.SetNull(~covered, categorical).save(str(pair_mask))
    finally:
        arcpy.management.Delete("event_pair_before_vv")
        arcpy.management.Delete("event_pair_after_vv")
    pixel_contract = read_json(ROOT / plan["contract"]["bindings"]["pixel_readiness_contract_ref"])
    table = support["gdb"] / "AOIRadarEventPair"
    observations, unknown = tabulate_radar_aoi(arcpy, aoi_fc=support["aoi_fc"], mask=pair_mask, table=table, pixel_contract=pixel_contract)
    selected = event_aoi_only(observations)
    bounds = aoi_bounds(arcpy, support["aoi_fc"])
    registration = measure_stable_registration_windowed(
        arcpy, before_path=before_linear, after_path=after_linear, pair_mask=pair_mask,
        overview_bbox=bounds["AOI-OVERVIEW"],
        exclusion_bboxes=[bounds["AOI-SOURCE"], bounds["AOI-UPPER-CORRIDOR"]],
        settings=plan["contract"]["registration"], pixel_contract=pixel_contract,
    )
    result = evaluate_route(
        route_id=PAIRED_ROUTE_ID,
        aoi_observations=selected,
        before_grid=grid_for_raster(arcpy, before_linear),
        after_grid=grid_for_raster(arcpy, after_linear),
        registration=registration,
        seam_observations=[],
        pixel_contract=pixel_contract,
        unknown_mask_class_present=unknown,
    )
    return {
        "status": "pass_route_evaluated_qa_only",
        "disposition": result["status"],
        "source_ids": {"before": IDS[0], "after": IDS[1]},
        "required_aoi_ids": list(REQUIRED_AOIS),
        "same_date_mosaic_created": False,
        "same_date_seam_test_applicable": False,
        "result": result,
        "pair_mask_identity": raster_identity(pair_mask),
    }


def _write_reserved(path: Path, value: dict[str, Any]) -> None:
    with path.open("r+b") as stream:
        if stream.seek(0, os.SEEK_END) != 0:
            raise IntakeError("event_pair_reserved_receipt_already_written")
        stream.write((json.dumps(value, indent=2) + "\n").encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())


def _reserve() -> None:
    if ATTEMPT_ROOT.exists():
        raise IntakeError("event_pair_attempt_collision")
    ATTEMPT_ROOT.mkdir(parents=True, exist_ok=False)
    for name in ("terminal.json", "error.json", "cleanup.json"):
        with (ATTEMPT_ROOT / name).open("xb") as stream:
            stream.flush()
            os.fsync(stream.fileno())
    (ATTEMPT_ROOT / "s").mkdir()
    (ATTEMPT_ROOT / "receipts" / "sources").mkdir(parents=True)
    (ATTEMPT_ROOT / "receipts" / "routes").mkdir(parents=True)
    (ATTEMPT_ROOT / "routes").mkdir()
    with (ATTEMPT_ROOT / "started.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump({"schema_version": "1.0", "status": "started_one_two_source_process", "at_utc": now_utc(), "source_order": list(IDS), "automatic_retry": False}, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def run_one() -> dict[str, Any]:
    preflight = read_json(PREFLIGHT)
    if (preflight.get("status") != "pass_final_no_content_two_source_radar_preflight"
            or preflight.get("implementation_gate_sha256") != sha256_file(IMPLEMENTATION_GATE)
            or preflight.get("footprint_gate_sha256") != sha256_file(FOOTPRINT_GATE)):
        raise IntakeError("event_pair_radar_final_preflight_missing")
    plan = event_plan()
    projected_paths(plan)
    _reserve()
    stage = "input_identity"
    arcpy = None
    checked_out: list[str] = []
    sources: list[dict[str, Any]] = []
    route: dict[str, Any] | None = None
    identities_before: dict[str, Any] | None = None

    def marker(*, source_id: str, tool: str, phase: str) -> None:
        with (ATTEMPT_ROOT / "stages.jsonl").open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps({"at_utc": now_utc(), "source_id": source_id, "tool": tool, "phase": phase}) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    try:
        identities_before = verify_input_identities(plan)
        stage = "arcgis_runtime"
        os.environ["GDAL_PAM_ENABLED"] = "NO"
        os.environ["PROJ_NETWORK"] = "OFF"
        import arcpy as arcpy_module  # type: ignore

        arcpy = arcpy_module
        arcpy.env.overwriteOutput = False
        for extension in ("ImageAnalyst", "Spatial"):
            if arcpy.CheckOutExtension(extension) != "CheckedOut":
                raise IntakeError("event_pair_arcgis_extension_checkout_failed")
            checked_out.append(extension)
        stage = "analysis_support"
        support = create_analysis_support(arcpy, plan, ATTEMPT_ROOT)
        stage = "source_processing_fixed_order"
        sources = source_sequence(lambda source_id: process_source(
            arcpy=arcpy, plan=plan, identities_before=identities_before,
            attempt_root=ATTEMPT_ROOT, dem_mosaic=MOSAIC, support=support,
            source_id=source_id, started_at_utc=now_utc(), stage_recorder=marker,
        ))
        if len(sources) == 2 and all(item["status"] == "pass_source_qa_only" for item in sources):
            stage = "event_pair_route_qa"
            route = evaluate_pair_route(arcpy, plan, support)
        stage = "external_custody_reconciliation"
        identities_after = verify_input_identities(plan)
        if identities_before != identities_after:
            raise IntakeError("event_pair_external_custody_mutated")
        passed_sources = len(sources) == 2 and all(item["status"] == "pass_source_qa_only" for item in sources)
        terminal = {
            "schema_version": "1.0",
            "record_id": "NEPAL-M2-RADAR-EVENT-AREA-PAIR-001-RADAR-TERMINAL",
            "status": "pass_two_sources_route_evaluated_qa_only" if passed_sources and route is not None else "stopped_on_first_source_failure_no_retry",
            "completed_at_utc": now_utc(),
            "source_results": sources,
            "route": route,
            "external_custody_unchanged": True,
            "automatic_retry_performed": False,
            "baseline_or_change_analysis_executed": False,
            "derived_pixel_publication_authorized": False,
        }
    except BaseException as exc:
        detail = safe_error(exc, (ATTEMPT_ROOT, DATA_ROOT))
        _write_reserved(ATTEMPT_ROOT / "error.json", {"schema_version": "1.0", "status": "terminal_error_preserved", "last_stage": stage, **detail})
        terminal = {
            "schema_version": "1.0", "record_id": "NEPAL-M2-RADAR-EVENT-AREA-PAIR-001-RADAR-TERMINAL",
            "status": "terminal_supervisor_failure_no_retry", "completed_at_utc": now_utc(),
            "last_stage": stage, **detail, "source_results": sources, "route": route,
            "automatic_retry_performed": False,
            "baseline_or_change_analysis_executed": False,
            "derived_pixel_publication_authorized": False,
        }
    finally:
        if arcpy is not None:
            for extension in reversed(checked_out):
                try:
                    arcpy.CheckInExtension(extension)
                except Exception:
                    pass
    _write_reserved(ATTEMPT_ROOT / "terminal.json", terminal)
    _write_reserved(ATTEMPT_ROOT / "cleanup.json", {"schema_version": "1.0", "status": "extension_checkin_attempted_outputs_preserved", "at_utc": now_utc()})
    return terminal


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--preflight", action="store_true")
    group.add_argument("--run-one", action="store_true")
    args = parser.parse_args()
    try:
        if args.preflight:
            import arcpy  # type: ignore
            value = no_content_preflight(arcpy)
            with PREFLIGHT.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(value, stream, indent=2)
                stream.write("\n")
            print(json.dumps({"status": value["status"]}))
            return 0
        value = run_one()
        print(json.dumps({"status": value["status"], "sources_evaluated": len(value["source_results"]), "route_evaluated": value["route"] is not None}))
        return 0 if value["status"] == "pass_two_sources_route_evaluated_qa_only" else 20
    except IntakeError as exc:
        print(json.dumps({"status": "stopped_before_radar_process", "code": exc.code}))
        return 12


if __name__ == "__main__":
    raise SystemExit(main())
