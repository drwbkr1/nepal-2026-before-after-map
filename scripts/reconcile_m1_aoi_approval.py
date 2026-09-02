#!/usr/bin/env python3
"""Reconcile the approved AOI and prepared source-manifest review into M1 controls."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def write(relative: str, value: dict) -> None:
    (ROOT / relative).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reconciled-at-utc", required=True)
    args = parser.parse_args()

    approval = load("records/source-gates/aoi-approval.json")
    arcgis_receipt = load("records/surface-receipts/m1-approved-aoi-arcgis-validation.json")
    manifest = load("records/source-manifest.json")
    manifest_bundle = load("reviews/m1-manifest/review-bundle.json")
    manifest_contract = load("reviews/m1-manifest/review-contract.json")
    if approval["status"] != "approved" or approval["decision_counts"]["approve"] != 1:
        raise SystemExit("AOI approval is not a single reconciled approval")
    if arcgis_receipt["status"] != "pass" or arcgis_receipt["spatial_reference"]["factory_code"] != 32645:
        raise SystemExit("ArcGIS AOI validation has not passed in EPSG:32645")
    if manifest["status"] != "candidate_for_owner_review":
        raise SystemExit("candidate manifest is not ready for owner review")
    if manifest["summary"] != {
        "candidate_count": 10,
        "proposed_accept_count": 8,
        "proposed_defer_count": 2,
        "proposed_reject_count": 0,
        "proposed_acquisition_catalog_bytes": 12451940706,
        "proposed_acquisition_catalog_gib": 11.597,
        "pixel_usability_established_count": 0,
    }:
        raise SystemExit("candidate manifest summary differs from the reviewed route")
    bundle_digest = sha256("reviews/m1-manifest/review-bundle.json")
    if manifest_contract["review_bundle"]["manifest_sha256"] != bundle_digest:
        raise SystemExit("source-manifest review contract does not bind the current bundle bytes")
    if manifest_bundle["candidate_identity"] != f"SOURCE-MANIFEST-SHA256:{sha256('records/source-manifest.json')}":
        raise SystemExit("source-manifest bundle does not bind the current manifest bytes")

    contract = load("contracts/milestone-001.json")
    exits = {item["id"]: item for item in contract["exit_conditions"]}
    exits["EXIT-001-AOI-LOCKED"].update(
        {
            "status": "pass",
            "evidence": [
                "records/source-gates/aoi-approval.json",
                "records/source-gates/aoi-review-reconciliation.json",
                "config/aoi/approved-study-areas.geojson",
                "config/aoi/approved-study-areas-epsg32645.json",
                "records/surface-receipts/m1-approved-aoi-arcgis-validation.json",
            ],
        }
    )
    units = {unit["id"]: unit for unit in contract["units"]}
    units["M1-AOI"].update(
        {
            "status": "complete",
            "outputs": [
                "records/source-gates/aoi-approval.json",
                "config/aoi/approved-study-areas.geojson",
                "config/aoi/approved-study-areas-epsg32645.json",
                "records/surface-receipts/m1-approved-aoi-arcgis-validation.json",
            ],
            "gates": {
                "exact_human_response_reconciled": "pass",
                "owner_approval": "pass",
                "reviewed_aoi_sha256": approval["reviewed_aoi_sha256"],
                "geometry_equivalence": "pass",
                "arcgis_json_to_features": "pass",
                "projected_crs": "EPSG:32645",
            },
            "disposition": "pass",
            "retained_failures": [
                "Initial response lock attempt rejected the non-hash-bound candidate filename; no response was locked and decision values were not read.",
                "Initial ArcGIS validation attempt imported the JSON but failed on an unsupported Polygon.isEmpty property; the pointCount remediation passed on rerun.",
            ],
            "exit_condition_delta": {
                "expected": ["EXIT-001-AOI-LOCKED"],
                "observed": ["EXIT-001-AOI-LOCKED"],
                "decision_value": "advances_exit",
                "rationale": "The owner approved the exact reviewed geometry, the response was locked and reconciled, and ArcGIS Pro imported the projected EPSG:32645 derivative successfully.",
            },
            "next_dependency": "M1-MANIFEST",
        }
    )
    units["M1-MANIFEST"].update(
        {
            "status": "ready",
            "inputs": [
                "records/source-gates/aoi-approval.json",
                "records/source-gates/quicklook-review.json",
                "records/source-manifest.json",
                "docs/M1_SOURCE_MANIFEST_REVIEW.md",
                "docs/assets/m1-source-manifest-review.png",
                "records/surface-receipts/m1-source-manifest-review.json",
                "reviews/m1-manifest/review-bundle.json",
                "reviews/m1-manifest/review-contract.json",
                "reviews/m1-manifest/blank-response.json",
            ],
            "outputs": ["records/source-gates/source-manifest-approval.json"],
            "gates": {
                "candidate_count": 10,
                "proposed_accept_count": 8,
                "proposed_defer_count": 2,
                "proposed_reject_count": 0,
                "candidate_manifest_sha256": sha256("records/source-manifest.json"),
                "review_bundle_manifest_sha256": bundle_digest,
                "review_surface": "verified",
                "human_decision": "pending",
            },
            "disposition": None,
            "retained_failures": [],
            "exit_condition_delta": {
                "expected": ["EXIT-003-MANIFEST-APPROVED"],
                "observed": [],
                "decision_value": "unknown",
                "rationale": "The exact candidate manifest is decision-ready, but accepted and deferred source dispositions remain an owner decision.",
            },
            "next_dependency": None,
        }
    )
    contract["verification"]["completed_checks"] = [
        "Copernicus source gate valid and ready",
        "10/10 exact catalog records captured",
        "10/10 quicklooks decoded and visually screened",
        "owner approved the exact M1 AOI review bundle",
        "approved AOIs projected and imported in ArcGIS Pro 3.7.1 as EPSG:32645",
        "candidate source manifest generated with 8 proposed accept, 2 proposed defer, and 0 proposed reject records",
        "source-manifest review surface visually inspected and bundle validated",
        "scratch and private human-response assets excluded from Git",
    ]
    contract["handoff"].update(
        {
            "current_checkpoint": "M1-OWNER-MANIFEST-GATE",
            "next_action": f"Owner decides approve, revise, or defer for bundle m1-source-manifest-review-bundle-001, manifest SHA-256 {bundle_digest}.",
            "do_not_carry_forward": [
                "Catalog presence and quicklooks are not pixel usability.",
                "Approved AOIs are search and review extents, not mapped change polygons.",
                "No full satellite product acquisition is authorized.",
                "Do not redistribute portal quicklook assets.",
                "The post-event RUM optical candidate is high-cloud-risk and may be inconclusive.",
                "No scientific conclusion has been produced.",
            ],
        }
    )
    write("contracts/milestone-001.json", contract)

    profile = load("records/project-control-profile.json")
    profile["current_checkpoint"].update(
        {
            "checkpoint_id": "M1-OWNER-MANIFEST-GATE",
            "next_action": "Owner reviews the exact candidate source-manifest bundle; do not authenticate or download full products.",
        }
    )
    write("records/project-control-profile.json", profile)
    print(
        json.dumps(
            {
                "status": "m1_aoi_approval_reconciled",
                "reconciled_at_utc": args.reconciled_at_utc,
                "aoi_unit": units["M1-AOI"]["status"],
                "manifest_unit": units["M1-MANIFEST"]["status"],
                "checkpoint": contract["handoff"]["current_checkpoint"],
                "manifest_bundle_sha256": bundle_digest,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
