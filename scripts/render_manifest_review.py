#!/usr/bin/env python3
"""Render the candidate source manifest into a compact owner review document."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    digest = sha256(args.manifest)
    summary = manifest["summary"]
    lines = [
        "# M1 source-manifest review",
        "",
        "## Decision requested",
        "",
        "Review the exact candidate manifest and choose **approve**, **revise**, or **defer**. Approval locks the proposed source set for later controlled acquisition planning. It does not authorize credentials, terms acceptance, or downloads.",
        "",
        "![Candidate source-manifest review surface](assets/m1-source-manifest-review.png)",
        "",
        f"- **Manifest:** `{manifest['manifest_id']}`",
        f"- **Manifest SHA-256:** `{digest}`",
        f"- **AOI approval:** `{manifest['aoi_approval_sha256']}`",
        f"- **Proposed accepted:** {summary['proposed_accept_count']}",
        f"- **Proposed deferred:** {summary['proposed_defer_count']}",
        f"- **Proposed rejected:** {summary['proposed_reject_count']}",
        f"- **Accepted catalog volume:** {summary['proposed_acquisition_catalog_gib']:.3f} GiB",
        "",
        "## Candidate decisions",
        "",
        "| Source | Role | Sensor | Orbit/tile | Detailed AOI | Cloud | Proposal | Catalog size |",
        "|---|---|---|---|---|---:|---|---:|",
    ]
    for record in manifest["records"]:
        orbit = record["orbit_or_tile"]
        orbit_text = orbit["tile_id"] or f"{orbit['orbit_direction']} r{orbit['relative_orbit_number']}"
        detailed = record["coverage_status"]["approved_aoi_intersections"]["AOI-SOURCE"] or record["coverage_status"]["approved_aoi_intersections"]["AOI-UPPER-CORRIDOR"]
        cloud = record["catalog_cloud_cover_percent"]
        cloud_text = "n/a" if cloud is None else f"{cloud:.2f}%"
        size_gib = record["catalog_content_length_bytes"] / (1024 ** 3)
        lines.append(
            f"| `{record['source_id']}` | {record['event_role']} | {record['collection']} | {orbit_text} | {'yes' if detailed else 'no'} | {cloud_text} | `{record['proposed_disposition']['disposition']}` | {size_gib:.3f} GiB |"
        )
    lines.extend(
        [
            "",
            "## Proposed route",
            "",
            "- Retain all six Sentinel-1 GRD records so the ascending two-slice pairs and descending single-slice pairs remain complete for later terrain and pixel QA.",
            "- Retain the Sentinel-2 RUM before/after pair because it intersects both detailed AOIs. The post-event tile remains high-cloud-risk and may prove inconclusive.",
            "- Defer both Sentinel-2 RUL records because they intersect only the regional overview bounding box and add cloud-limited context rather than event-area pixels.",
            "- Reject none at this stage; deferred and potentially unusable observations remain in the evidence record.",
            "",
            "## Evidence boundary",
            "",
            "This manifest records product identities, dates, footprints, catalog checksums, quicklook screening, access boundaries, and proposed dispositions. No full product has been downloaded. Pixel coverage, masks, registration, radar geometry, and change evidence remain untested.",
            "",
            "## Required owner response",
            "",
            f"Approval must bind manifest SHA-256 `{digest}` and explicitly attest that the decision is complete. Revision should identify exact source IDs or the acquisition boundary to change.",
            "",
        ]
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(json.dumps({"status": "rendered", "manifest_sha256": digest, "output": str(args.output), "output_sha256": sha256(args.output)}, indent=2))


if __name__ == "__main__":
    main()
