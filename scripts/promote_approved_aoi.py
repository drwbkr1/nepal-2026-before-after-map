#!/usr/bin/env python3
"""Promote the exact reviewed AOI geometry into an approved interchange artifact."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--reconciliation", type=Path, required=True)
    parser.add_argument("--expected-source-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source_digest = sha256(args.source)
    if source_digest != args.expected_source_sha256:
        raise SystemExit("reviewed AOI bytes do not match the approved SHA-256")

    reconciliation = json.loads(args.reconciliation.read_text(encoding="utf-8"))
    if reconciliation.get("status") != "reconciled_exact_human_response":
        raise SystemExit("human-review response is not reconciled")
    if reconciliation.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}:
        raise SystemExit("human-review decision is not one exact approval")
    if reconciliation.get("human_decisions_fabricated") is not False:
        raise SystemExit("reconciliation does not prove a human decision")

    source = json.loads(args.source.read_text(encoding="utf-8"))
    approved = copy.deepcopy(source)
    approved["name"] = "Nepal 2026 approved M1 search and review areas"
    approved["properties"].update(
        {
            "status": "approved_m1_search_review",
            "approval_scope": "M1 source discovery, review, and ArcGIS organization",
            "approval_ref": "records/source-gates/aoi-approval.json",
            "reviewed_source_sha256": source_digest,
            "claim_boundary": "Approved search and review extents; not mapped change polygons or event attribution.",
        }
    )
    for feature in approved["features"]:
        original_id = feature["id"]
        if not original_id.endswith("-DRAFT"):
            raise SystemExit(f"unexpected reviewed AOI identity: {original_id}")
        approved_id = original_id.removesuffix("-DRAFT")
        feature["id"] = approved_id
        feature["properties"].update(
            {
                "aoi_id": approved_id,
                "status": "approved_m1_search_review",
                "source_ref": "records/source-gates/aoi-approval.json",
                "owner_approval_required": False,
                "reviewed_feature_id": original_id,
                "reviewed_source_sha256": source_digest,
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(approved, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "status": "approved_aoi_promoted",
                "source_sha256": source_digest,
                "output_sha256": sha256(args.output),
                "feature_count": len(approved["features"]),
                "output": str(args.output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
