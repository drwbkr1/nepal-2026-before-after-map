#!/usr/bin/env python3
"""Publish path-free terminal evidence for the consumed map-route attempt."""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
from pathlib import Path
from typing import Any
import json


ROOT = Path(__file__).resolve().parents[1]
ATTEMPT = ROOT.parent / "nepal-2026-before-after-map-data" / "e1" / "a3"
CATALOG = ROOT / "records/observations/m2-map-route-feasibility-001-optical-fallback-catalog.json"
REVIEW = ROOT / "records/observations/m2-map-route-feasibility-001-optical-fallback-review.json"
TERMINAL = ROOT / "records/readiness/m2-map-route-feasibility-001-terminal-publication.json"


def file_sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_new(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def candidate_review(catalog: dict[str, Any], catalog_sha: str) -> dict[str, Any]:
    if catalog["status"] != "catalog_metadata_inventory_complete" or catalog["row_count"] != 85:
        raise ValueError("unexpected optical fallback inventory status or count")
    if len(catalog["requests"]) != 2 or [r["window"] for r in catalog["requests"]] != ["before", "after"]:
        raise ValueError("optical fallback request order mismatch")
    if any(r["returned_rows"] != r["reported_total_rows"] for r in catalog["requests"]):
        raise ValueError("optical fallback inventory truncated")
    source = [row for row in catalog["rows"] if row["aoi_footprint_intersects"]["AOI-SOURCE"]]
    corridor = [row for row in catalog["rows"] if row["aoi_footprint_intersects"]["AOI-UPPER-CORRIDOR"]]
    counts = Counter(row["window"] for row in catalog["rows"])
    source_counts = Counter(row["window"] for row in source)
    corridor_counts = Counter(row["window"] for row in corridor)
    cloud_ranges = {}
    for window in ("before", "after"):
        values = [float(row["catalog_cloud_cover_percent"]) for row in source
                  if row["window"] == window and row["catalog_cloud_cover_percent"] is not None]
        cloud_ranges[window] = [min(values), max(values)] if values else None
    return {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-MAP-ROUTE-FEASIBILITY-001-OPTICAL-FALLBACK-REVIEW",
        "status": "metadata_candidates_only_no_adoption",
        "catalog_ref": "records/observations/m2-map-route-feasibility-001-optical-fallback-catalog.json",
        "catalog_sha256": catalog_sha,
        "catalog_rows": dict(counts),
        "source_aoi_footprint_intersections": dict(source_counts),
        "upper_corridor_aoi_footprint_intersections": dict(corridor_counts),
        "source_aoi_intersecting_tile_cloud_percent_range": cloud_ranges,
        "rights": {
            "cdse_terms_ref": catalog["rights_review"]["cdse_terms"],
            "sentinel_legal_notice_ref": catalog["rights_review"]["sentinel_legal_notice"],
            "finding": "Public Sentinel catalog metadata and official terms/legal-notice references are identified. No new product rights or current-terms adoption gate has been completed.",
            "third_party_quicklooks_published": False,
        },
        "comparability": {
            "same_product_level": "S2MSI2A metadata filter for both windows",
            "same_aoi_search": "approved AOI-OVERVIEW, with exact footprint intersection flags for source and upper corridor",
            "pixel_coverage": "unknown",
            "aoi_cloud_snow_shadow_fitness": "unknown",
            "co_registration": "unknown",
            "new_source_or_date_selected": False,
            "note": "Tile-level cloud percentages and footprint intersections do not establish clear AOI pixels or a valid before/after pair.",
        },
        "later_owner_decision_required_for": ["exact product/date selection", "current source and terms review", "acquisition", "pixel inspection and processing"],
        "scientific_claim_authorized": False,
    }


def run() -> dict[str, Any]:
    if REVIEW.exists() or TERMINAL.exists():
        raise FileExistsError("publication receipt already exists; no replacement")
    terminal_path = ATTEMPT / "terminal.json"
    supervisor_path = ATTEMPT / "supervisor.json"
    cleanup_path = ATTEMPT / "cleanup.json"
    source_path = ATTEMPT / "receipts/sources/m1-src-002-terminal.json"
    journal_path = ATTEMPT / "stages.jsonl"
    terminal, supervisor, cleanup, source, catalog = (
        read(path) for path in (terminal_path, supervisor_path, cleanup_path, source_path, CATALOG)
    )
    if terminal["status"] != "stopped_on_first_source_failure_no_retry" or terminal["source_results"] != [{
        "source_id": "M1-SRC-002", "status": "failed_source_execution_no_retry",
        "receipt_ref": "receipts/sources/m1-src-002-terminal.json", "receipt_sha256": file_sha(source_path),
    }]:
        raise ValueError("unexpected radar terminal route or source result")
    if source["failure_type"] != "NativeGridStop" or source["failure_message"] != "native_declared_resource_limit_exceeded":
        raise ValueError("unexpected source stop")
    if supervisor["status"] != "supervisor_terminal_reconciled" or supervisor["worker_return_code"] != 20:
        raise ValueError("unexpected supervisor status")
    if supervisor["terminal_sha256"] != file_sha(terminal_path) or supervisor["cleanup_sha256"] != file_sha(cleanup_path):
        raise ValueError("supervisor receipt hashes mismatch")
    if cleanup["status"] != "extension_checkin_attempted_outputs_preserved":
        raise ValueError("cleanup receipt mismatch")
    if not terminal["external_custody_unchanged"] or terminal["automatic_retry_performed"] or terminal["baseline_or_change_analysis_executed"]:
        raise ValueError("radar boundary assertions mismatch")
    journal = [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]
    if any(row.get("source_id") != "M1-SRC-002" for row in journal) or (ATTEMPT / "receipts/sources/m1-src-005-started.json").exists():
        raise ValueError("later radar source appears to have started")
    review = candidate_review(catalog, file_sha(CATALOG))
    public = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-MAP-ROUTE-FEASIBILITY-001-TERMINAL-PUBLICATION",
        "status": "radar_stopped_first_source_optical_metadata_only",
        "radar_attempt_id": "e1/a3",
        "radar_terminal_at_utc": terminal["completed_at_utc"],
        "radar_first_source": "M1-SRC-002",
        "radar_stop_stage": "ApplyGeometricTerrainCorrection_gamma",
        "radar_stop_code": source["failure_message"],
        "radar_failure_type": source["failure_type"],
        "radar_second_source_started": False,
        "radar_retry_performed": False,
        "radar_external_custody_unchanged": True,
        "radar_evidence_sha256": {
            "terminal": file_sha(terminal_path), "source_terminal": file_sha(source_path),
            "cleanup": file_sha(cleanup_path), "supervisor": file_sha(supervisor_path),
            "stage_journal": file_sha(journal_path),
        },
        "optical_catalog_ref": "records/observations/m2-map-route-feasibility-001-optical-fallback-catalog.json",
        "optical_catalog_sha256": file_sha(CATALOG),
        "optical_review_ref": "records/observations/m2-map-route-feasibility-001-optical-fallback-review.json",
        "optical_review_sha256": None,
        "result_boundary": "Neither radar pair QA nor optical pixel fitness established; no map change layer or baseline admission.",
        "new_optical_source_adopted": False,
        "baseline_or_change_analysis_executed": False,
        "derived_pixel_or_scientific_publication_authorized": False,
    }
    write_new(REVIEW, review)
    public["optical_review_sha256"] = file_sha(REVIEW)
    write_new(TERMINAL, public)
    return public


if __name__ == "__main__":
    result = run()
    print(json.dumps({"status": result["status"], "radar_stop_code": result["radar_stop_code"]}))
