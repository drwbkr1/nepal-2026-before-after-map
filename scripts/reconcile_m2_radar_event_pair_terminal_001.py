#!/usr/bin/env python3
"""Publish only sanitized terminal facts from the single event-pair radar attempt."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from m2_dem_vertical_datum_proj25_core import sha256_file
from m2_radar_event_pair_dem_intake_001 import IntakeError, ROOT
from m2_radar_event_pair_processing_001 import ATTEMPT_ROOT, IDS, event_plan, verify_input_identities
from m2_radar_esri_sequence_processing_005 import raster_identity


OUTPUT = ROOT / "records/processing/m2-radar-event-area-pair-001-radar-terminal-reconciliation.json"
ALLOWED_STATUSES = {
    "pass_two_sources_route_evaluated_qa_only",
    "stopped_on_first_source_failure_no_retry",
    "terminal_supervisor_failure_no_retry",
}


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise IntakeError("radar_attempt_receipt_not_object")
    return value


def reconcile_terminal() -> dict[str, Any]:
    if OUTPUT.exists():
        raise IntakeError("radar_terminal_reconciliation_collision")
    terminal_path = ATTEMPT_ROOT / "terminal.json"
    cleanup_path = ATTEMPT_ROOT / "cleanup.json"
    stages_path = ATTEMPT_ROOT / "stages.jsonl"
    if not all(path.is_file() and path.stat().st_size > 0 for path in (terminal_path, cleanup_path)):
        raise IntakeError("radar_terminal_or_cleanup_not_durable")
    terminal = load(terminal_path)
    cleanup = load(cleanup_path)
    if (terminal.get("status") not in ALLOWED_STATUSES
            or terminal.get("automatic_retry_performed") is not False
            or terminal.get("baseline_or_change_analysis_executed") is not False
            or terminal.get("derived_pixel_publication_authorized") is not False
            or cleanup.get("status") != "extension_checkin_attempted_outputs_preserved"):
        raise IntakeError("radar_terminal_scope_or_cleanup_drift")
    source_results = terminal.get("source_results")
    if not isinstance(source_results, list) or len(source_results) > 2 or [item.get("source_id") for item in source_results] != list(IDS[:len(source_results)]):
        raise IntakeError("radar_terminal_source_order_drift")
    sanitized_sources: list[dict[str, Any]] = []
    for result in source_results:
        source_id = result["source_id"]
        ref = result.get("receipt_ref")
        if not isinstance(ref, str) or not ref.startswith("receipts/sources/") or ".." in Path(ref).parts:
            raise IntakeError("radar_source_receipt_ref_invalid")
        receipt_path = ATTEMPT_ROOT / Path(ref)
        if not receipt_path.is_file() or sha256_file(receipt_path) != result.get("receipt_sha256"):
            raise IntakeError("radar_source_receipt_identity_drift")
        receipt = load(receipt_path)
        if receipt.get("source_id") != source_id or receipt.get("status") != result.get("status"):
            raise IntakeError("radar_source_receipt_status_drift")
        item: dict[str, Any] = {
            "source_id": source_id,
            "status": receipt["status"],
            "receipt_sha256": result["receipt_sha256"],
        }
        if receipt["status"] == "pass_source_qa_only":
            outputs = receipt.get("outputs", {})
            if set(outputs) != {"linear_gamma_nought", "db_display_candidate", "native_distortion_mask"}:
                raise IntakeError("radar_source_output_set_drift")
            item["output_identity_sha256"] = {}
            for key, output in outputs.items():
                path = Path(output["path"])
                if ATTEMPT_ROOT.resolve(strict=True) not in path.resolve(strict=True).parents:
                    raise IntakeError("radar_output_outside_attempt")
                if raster_identity(path) != output.get("identity"):
                    raise IntakeError("radar_output_byte_identity_drift")
                digest = output["identity"].get("inventory_sha256", output["identity"].get("sha256"))
                if not isinstance(digest, str) or len(digest) != 64:
                    raise IntakeError("radar_output_identity_digest_missing")
                item["output_identity_sha256"][key] = digest
        else:
            item["failure_code"] = receipt.get("failure_code", "source_failure_unclassified")
        sanitized_sources.append(item)
    if source_results and source_results[0].get("status") != "pass_source_qa_only" and len(source_results) != 1:
        raise IntakeError("radar_later_source_started_after_first_failure")
    route = terminal.get("route")
    sanitized_route = None
    if terminal["status"] == "pass_two_sources_route_evaluated_qa_only":
        if len(sanitized_sources) != 2 or any(item["status"] != "pass_source_qa_only" for item in sanitized_sources) or not isinstance(route, dict):
            raise IntakeError("radar_passing_terminal_without_two_sources_route")
        result = route.get("result", {})
        if (route.get("required_aoi_ids") != ["AOI-SOURCE", "AOI-UPPER-CORRIDOR"]
                or route.get("same_date_mosaic_created") is not False
                or route.get("same_date_seam_test_applicable") is not False
                or result.get("status") not in ("pass_qa_only", "defer", "block", "invalid")
                or result.get("baseline_admission_authorized") is not False
                or result.get("change_analysis_authorized") is not False):
            raise IntakeError("radar_route_scope_or_disposition_drift")
        mask = ATTEMPT_ROOT / "routes/event-pair/pair_exclusion_mask.tif"
        if raster_identity(mask) != route.get("pair_mask_identity"):
            raise IntakeError("radar_pair_mask_byte_identity_drift")
        sanitized_route = {
            "pair_id": "PAIR-S1-ASC-R085-IW",
            "status": result["status"],
            "required_aoi_ids": route["required_aoi_ids"],
            "aoi_coverage": result.get("aoi_coverage"),
            "grid_compatibility": result.get("grid_compatibility"),
            "registration": result.get("registration"),
            "unknown_mask_class_present": result.get("unknown_mask_class_present"),
            "same_date_seams": [],
            "pair_mask_identity_sha256": route["pair_mask_identity"].get("inventory_sha256", route["pair_mask_identity"].get("sha256")),
            "baseline_admission_authorized": False,
            "change_analysis_authorized": False,
        }
    elif route is not None:
        raise IntakeError("radar_failed_terminal_contains_route")
    identities = verify_input_identities(event_plan())
    return {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-EVENT-AREA-PAIR-001-RADAR-TERMINAL-RECONCILIATION",
        "checked_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": terminal["status"],
        "last_stage": terminal.get("last_stage"),
        "failure_code": terminal.get("failure_code"),
        "source_results": sanitized_sources,
        "route": sanitized_route,
        "external_custody_unchanged": terminal.get("external_custody_unchanged") is True if terminal["status"] != "terminal_supervisor_failure_no_retry" else None,
        "input_identity_source_inventory_sha256": {key: value["inventory_sha256"] for key, value in identities["sources"].items()},
        "input_identity_mosaic_sha256": identities["mosaic"],
        "terminal_receipt_sha256": sha256_file(terminal_path),
        "cleanup_receipt_sha256": sha256_file(cleanup_path),
        "stage_journal_sha256": sha256_file(stages_path) if stages_path.is_file() else None,
        "attempt_consumed": True,
        "automatic_retry_performed": False,
        "baseline_or_change_analysis_executed": False,
        "derived_pixel_publication_authorized": False,
        "scientific_publication_authorized": False,
    }


def main() -> int:
    try:
        result = reconcile_terminal()
        with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
        print(json.dumps({"status": result["status"], "source_count": len(result["source_results"]), "route": result["route"] is not None}))
        return 0
    except IntakeError as exc:
        print(json.dumps({"status": "terminal_reconciliation_stopped", "code": exc.code}))
        return 12


if __name__ == "__main__":
    raise SystemExit(main())
