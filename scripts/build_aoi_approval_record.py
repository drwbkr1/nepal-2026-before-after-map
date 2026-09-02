#!/usr/bin/env python3
"""Build the public, aggregate-only receipt for the approved M1 AOI."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reviewed", type=Path, required=True)
    parser.add_argument("--approved", type=Path, required=True)
    parser.add_argument("--projected", type=Path, required=True)
    parser.add_argument("--reconciliation", type=Path, required=True)
    parser.add_argument("--approved-at-utc", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    reconciliation = json.loads(args.reconciliation.read_text(encoding="utf-8"))
    if reconciliation.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}:
        raise SystemExit("reconciliation does not contain one exact approval")
    reviewed = json.loads(args.reviewed.read_text(encoding="utf-8"))
    approved = json.loads(args.approved.read_text(encoding="utf-8"))
    projected = json.loads(args.projected.read_text(encoding="utf-8"))
    if [f["geometry"] for f in reviewed["features"]] != [f["geometry"] for f in approved["features"]]:
        raise SystemExit("promoted WGS84 geometry differs from the reviewed geometry")
    if projected.get("spatialReference", {}).get("wkid") != 32645:
        raise SystemExit("projected AOI is not EPSG:32645")
    if len(projected.get("features", [])) != len(approved["features"]):
        raise SystemExit("projected AOI feature count differs from the approved interchange artifact")

    record = {
        "schema_version": "1.0",
        "approval_id": "M1-AOI-APPROVAL-001",
        "status": "approved",
        "approved_at_utc": args.approved_at_utc,
        "scope": "M1 source discovery, review, and ArcGIS organization",
        "review_id": reconciliation["review_id"],
        "review_bundle_id": "m1-aoi-review-bundle-001",
        "review_bundle_manifest_sha256": "7b8c4b1f5d86f44dc5425aee46ad813d3248c47054b48a815d877c264dfa252a",
        "reviewed_aoi_sha256": sha256(args.reviewed),
        "reconciliation_ref": str(args.reconciliation).replace("\\", "/"),
        "reconciliation_sha256": sha256(args.reconciliation),
        "locked_response_sha256": reconciliation["response_sha256"],
        "lock_receipt_sha256": reconciliation["receipt_sha256"],
        "decision_counts": reconciliation["decision_counts"],
        "human_decisions_fabricated": reconciliation["human_decisions_fabricated"],
        "outputs": [
            {
                "path": str(args.approved).replace("\\", "/"),
                "sha256": sha256(args.approved),
                "crs": "EPSG:4326",
                "format": "RFC 7946 GeoJSON",
                "geometry_equivalence_to_reviewed_source": "pass",
            },
            {
                "path": str(args.projected).replace("\\", "/"),
                "sha256": sha256(args.projected),
                "crs": "EPSG:32645",
                "format": "ArcGIS FeatureSet JSON",
                "projection_engine": projected["projectMetadata"]["projectionEngine"],
                "arcgis_version": projected["projectMetadata"]["arcgisVersion"],
            },
        ],
        "lock_attempts": [
            {
                "attempt": 1,
                "status": "failed",
                "reason": "candidate filename did not match its exact response-byte hash",
                "response_locked": False,
                "decision_values_read": False,
            },
            {
                "attempt": 2,
                "status": "locked_before_reveal",
                "response_sha256": reconciliation["response_sha256"],
                "response_locked": True,
                "decision_values_read_before_lock": False,
            },
        ],
        "limitations": [
            "Approval covers search and review extents, not mapped change polygons.",
            "Approval does not authorize credentials, terms acceptance, full-product downloads, or scientific publication.",
            "The EPSG:32645 artifact is a projected derivative; the exact reviewed geometry remains hash-bound in EPSG:4326.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": "aoi_approval_recorded", "output": str(args.output), "sha256": sha256(args.output)}, indent=2))


if __name__ == "__main__":
    main()
