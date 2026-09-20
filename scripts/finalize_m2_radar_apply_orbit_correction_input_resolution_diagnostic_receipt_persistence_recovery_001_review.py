#!/usr/bin/env python3
"""Seal visual inspection and final local readiness for the zero-decision packet."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-apply-orbit-correction-input-resolution-diagnostic-receipt-persistence-recovery-001"
IMAGE_REF = f"docs/assets/{PREFIX}-review.png"
SURFACE_REF = f"records/surface-receipts/{PREFIX}-review.json"
VISUAL_REF = f"records/surface-receipts/{PREFIX}-review-visual-inspection.json"
PREVISUAL_REF = f"records/readiness/{PREFIX}-review-readiness-previsual.json"
READINESS_REF = f"records/readiness/{PREFIX}-review-readiness.json"


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def load(ref: str) -> dict[str, Any]:
    value = json.loads((ROOT / ref).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {ref}")
    return value


def write_json(ref: str, value: object) -> None:
    path = ROOT / ref
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspected-at-utc", required=True)
    parser.add_argument("--visual-status", choices=["pass"], required=True)
    args = parser.parse_args()
    if not args.inspected_at_utc.endswith("Z"):
        raise SystemExit("--inspected-at-utc must be UTC")
    if (ROOT / VISUAL_REF).exists() or (ROOT / READINESS_REF).exists():
        raise SystemExit("visual inspection or final readiness collision")

    from PIL import Image

    surface = load(SURFACE_REF)
    previsual = load(PREVISUAL_REF)
    with Image.open(ROOT / IMAGE_REF) as image:
        dimensions = image.size
        image.verify()
    if (
        surface.get("status") != "pass_static_review_surface_generated_pending_agent_visual_inspection"
        or surface.get("artifact_sha256") != sha256(IMAGE_REF)
        or dimensions != (1800, 2060)
        or previsual.get("status") != "pass_local_zero_decision_packet_structurally_ready_visual_inspection_pending"
        or previsual.get("bindings", {}).get("review_surface_sha256") != sha256(IMAGE_REF)
    ):
        raise SystemExit("review surface or previsual readiness differs")

    visual = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-REVIEW-VISUAL-INSPECTION",
        "inspected_at_utc": args.inspected_at_utc,
        "status": "pass_agent_visual_inspection",
        "artifact_ref": IMAGE_REF,
        "artifact_sha256": sha256(IMAGE_REF),
        "inspection": {
            "dimensions_px": [1800, 2060],
            "title_and_authority_banner_legible": True,
            "terminal_failure_boundary_legible": True,
            "proposal_scope_legible": True,
            "prohibited_actions_legible": True,
            "hashes_legible": True,
            "text_clipped_or_overlapping": False,
            "decision_count_displayed_as_zero": True,
        },
    }
    write_json(VISUAL_REF, visual)

    bindings = dict(previsual["bindings"])
    bindings.update(
        {
            "previsual_readiness_ref": PREVISUAL_REF,
            "previsual_readiness_sha256": sha256(PREVISUAL_REF),
            "visual_inspection_ref": VISUAL_REF,
            "visual_inspection_sha256": sha256(VISUAL_REF),
        }
    )
    readiness = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-REVIEW-READINESS",
        "verified_at_utc": args.inspected_at_utc,
        "status": "pass_local_zero_decision_packet_ready_publication_authority_required",
        "bindings": bindings,
        "validation": {
            **previsual["validation"],
            "rendered_surface_visually_inspected": True,
            "review_surface_dimensions_px": [1800, 2060],
        },
        "released_now": previsual["released_now"],
        "assertions": {
            "human_decisions_fabricated": False,
            "git_staging_performed": False,
            "git_commit_created": False,
            "git_push_performed": False,
            "public_ci_started": False,
            "protected_diagnostic_code_modified": False,
            "arcpy_invoked": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "new_diagnostic_process_started": False,
            "consumed_attempt_retried_or_reused": False,
            "reserved_receipt_mutated": False,
            "implementation_authorized": False,
            "scientific_result_established": False,
        },
        "next_action": "Obtain explicit owner authorization to stage, commit, and publish this exact zero-decision packet and run public default-branch CI; keep the owner proposal response closed until that gate passes.",
    }
    write_json(READINESS_REF, readiness)
    print(
        json.dumps(
            {
                "status": readiness["status"],
                "visual_inspection_sha256": sha256(VISUAL_REF),
                "readiness_sha256": sha256(READINESS_REF),
                "next_gate": "explicit publication and public-CI authorization",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
