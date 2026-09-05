#!/usr/bin/env python3
"""Reconcile all eight exact SAFE materializations without decoding pixels."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from m2_materialization_remaining_core import (
    ATTEMPT_IDS,
    EXISTING_RECEIPTS,
    FINAL_PREFLIGHT_REF,
    ROOT,
    SOURCE_ORDER,
    load,
    repository_sha,
    sha256_file,
    validate_preflight,
    validate_static_authority,
)


OUTPUT_REF = "records/acquisition/sentinel-materialization-reconciliation-002.json"


def verify_materialization(ref: str, expected_source: str, expected_attempt: str) -> dict[str, Any]:
    receipt = load(ref)
    if (
        receipt.get("status") != "pass_materialization_only"
        or receipt.get("source_id") != expected_source
        or receipt.get("attempt_id") != expected_attempt
    ):
        raise RuntimeError(f"materialization receipt differs: {ref}")
    manifest_path = Path(receipt["bindings"]["external_manifest_path"])
    if not manifest_path.is_file() or sha256_file(manifest_path) != receipt["bindings"]["external_manifest_sha256"]:
        raise RuntimeError(f"materialization manifest differs: {ref}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    safe_root = Path(receipt["external_safe_root"])
    if not safe_root.is_dir() or manifest.get("file_count") != receipt.get("file_count"):
        raise RuntimeError(f"materialization structure differs: {ref}")
    if manifest.get("total_extracted_bytes") != receipt.get("total_extracted_bytes"):
        raise RuntimeError(f"materialization byte total differs: {ref}")
    # This is an identity check over raw file bytes only. It does not open a
    # raster dataset or decode a measurement pixel.
    observed_bytes = 0
    for item in manifest.get("files", []):
        path = safe_root / Path(*Path(item["relative_path"]).parts)
        if not path.is_file() or path.stat().st_size != item["size_bytes"] or sha256_file(path) != item["sha256"]:
            raise RuntimeError(f"materialized file differs: {ref}:{item.get('relative_path')}")
        observed_bytes += path.stat().st_size
    if observed_bytes != receipt["total_extracted_bytes"]:
        raise RuntimeError(f"materialized file bytes differ: {ref}")
    return {
        "source_id": expected_source,
        "attempt_id": expected_attempt,
        "status": receipt["status"],
        "receipt_ref": ref,
        "receipt_sha256": repository_sha(ref),
        "external_manifest_path": str(manifest_path),
        "external_manifest_sha256": receipt["bindings"]["external_manifest_sha256"],
        "file_count": receipt["file_count"],
        "total_extracted_bytes": receipt["total_extracted_bytes"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconciled-at-utc", required=True)
    args = parser.parse_args()
    if not args.reconciled_at_utc.endswith("Z"):
        raise SystemExit("reconciled time must be UTC")
    output = ROOT / OUTPUT_REF
    if output.exists():
        raise SystemExit("refusing reconciliation output collision")
    validate_static_authority(require_publication_gate=True)
    preflight = load(FINAL_PREFLIGHT_REF)
    validate_preflight(preflight)
    records: list[dict[str, Any]] = []
    for ref in EXISTING_RECEIPTS:
        receipt = load(ref)
        records.append(verify_materialization(ref, receipt["source_id"], receipt["attempt_id"]))
    for source_id in SOURCE_ORDER:
        ref = f"records/acquisition/materialization/{source_id.casefold()}-{ATTEMPT_IDS[source_id]}.json"
        records.append(verify_materialization(ref, source_id, ATTEMPT_IDS[source_id]))
    if [item["source_id"] for item in records] != ["M1-SRC-001", "M1-SRC-002", "M1-SRC-003", *SOURCE_ORDER]:
        raise RuntimeError("eight-source reconciliation order differs")
    record = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-SENTINEL-MATERIALIZATION-RECONCILIATION-002",
        "reconciled_at_utc": args.reconciled_at_utc,
        "status": "pass_all_eight_materialized_identity_only",
        "bindings": {
            "final_preflight_ref": FINAL_PREFLIGHT_REF,
            "final_preflight_sha256": repository_sha(FINAL_PREFLIGHT_REF),
            "approval_ref": "records/source-gates/m2-materialization-pixel-readiness-approval.json",
            "approval_sha256": repository_sha("records/source-gates/m2-materialization-pixel-readiness-approval.json"),
        },
        "materializations": records,
        "summary": {
            "source_count": len(records),
            "newly_materialized_source_count": 5,
            "retained_materialized_source_count": 3,
            "file_count": sum(item["file_count"] for item in records),
            "total_extracted_bytes": sum(item["total_extracted_bytes"] for item in records),
        },
        "assertions": {
            "every_receipt_passed": True,
            "every_manifest_rehashed": True,
            "every_materialized_file_rehashed": True,
            "source_archives_mutated": False,
            "network_requests_performed": False,
            "measurement_pixels_decoded": False,
            "raster_header_readiness_established": False,
            "pixel_usability_established": False,
            "baseline_or_change_established": False,
            "scientific_admission_authorized": False,
        },
        "next_gate": "implement and publish exact full-cohort radar and optical header-readiness controls before real header access",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(record, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    with output.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"status": record["status"], "output": OUTPUT_REF, "sha256": hashlib.sha256(payload).hexdigest()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
