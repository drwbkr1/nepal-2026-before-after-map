#!/usr/bin/env python3
"""Reconcile the one terminal optical pixel recovery-001 result."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

from m2_optical_pixel_recovery_stage_gate import (
    CONTRACT_REF,
    PREFLIGHT_REF,
    PUBLICATION_GATE_REF,
    REAL_001_RECONCILIATION_REF,
    ROOT,
    validate_recovery_stage_execution,
)


OUTPUT = ROOT / "records/readiness/m2-optical-pixel-recovery-001-reconciliation.json"
RECEIPT_REF = "records/readiness/optical-pixel/m2-s2-pixel-readiness-recovery-001.json"
TERMINAL_STATUSES = {"pass_qa_only", "defer", "block", "invalid"}


def load_path(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory(root: Path) -> list[dict]:
    return [
        {
            "relative_path": path.relative_to(root).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in sorted((item for item in root.rglob("*") if item.is_file()), key=lambda item: str(item).casefold())
    ]


def verify_materialization(receipt_ref: str) -> dict:
    receipt_path = ROOT / receipt_ref
    receipt = load_path(receipt_path)
    safe_root = Path(receipt["external_safe_root"]).resolve(strict=True)
    manifest_path = Path(receipt["bindings"]["external_manifest_path"]).resolve(strict=True)
    manifest = load_path(manifest_path)
    errors = []
    total = 0
    for item in manifest.get("files", []):
        path = safe_root.joinpath(*PurePosixPath(item["relative_path"]).parts).resolve(strict=True)
        path.relative_to(safe_root)
        total += 1
        if path.stat().st_size != item["size_bytes"] or sha256_file(path) != item["sha256"]:
            errors.append(item["relative_path"])
    return {
        "source_id": receipt["source_id"],
        "file_count": total,
        "status": "pass" if not errors else "invalid",
        "errors": errors,
        "manifest_sha256": sha256_file(manifest_path),
        "receipt_sha256": sha256_file(receipt_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconciled-at-utc", required=True)
    args = parser.parse_args()
    if OUTPUT.exists():
        raise SystemExit("refusing optical pixel recovery reconciliation collision")
    validate_recovery_stage_execution()
    contract = load_path(ROOT / CONTRACT_REF)
    receipt = load_path(ROOT / RECEIPT_REF)
    retained = load_path(ROOT / REAL_001_RECONCILIATION_REF)
    if (
        receipt.get("receipt_id") != "NEPAL-S2-PIXEL-READINESS-RECOVERY-001"
        or receipt.get("attempt_id") != "optical-pixel-readiness-recovery-001"
        or receipt.get("status") not in TERMINAL_STATUSES
        or receipt.get("operational_correction", {}).get("analysis_grid_extent_normalized") is not True
        or receipt.get("operational_correction", {}).get("scientific_thresholds_changed") is not False
        or receipt.get("operational_correction", {}).get("source_pair_or_aois_changed") is not False
        or receipt.get("operational_correction", {}).get("real_001_reused_or_retried") is not False
    ):
        raise SystemExit("terminal recovery receipt differs")
    attempt_root = Path(contract["attempt"]["external_attempt_root"]).resolve(strict=True)
    attempt_inventory = inventory(attempt_root)
    if not any(item["relative_path"] == "started.json" for item in attempt_inventory):
        raise SystemExit("recovery attempt has no started record")
    if receipt["status"] == "invalid":
        if receipt.get("automatic_retry_authorized") is not False:
            raise SystemExit("invalid recovery receipt does not prohibit retry")
        if not any(item["relative_path"] == "failure.json" for item in attempt_inventory):
            raise SystemExit("invalid recovery attempt has no failure record")
    else:
        if not any(item["relative_path"] == "completed.json" for item in attempt_inventory):
            raise SystemExit("completed recovery attempt has no completion record")
        if receipt.get("activity", {}).get("source_materialization_inventories_unchanged") is not True:
            raise SystemExit("completed recovery receipt does not preserve source custody")
    retained_root = Path(contract["retained_real_001"]["external_attempt_root"]).resolve(strict=True)
    retained_inventory = inventory(retained_root)
    if retained_inventory != retained.get("external_attempt", {}).get("inventory"):
        raise SystemExit("retained real-001 attempt changed during recovery")
    custody = [verify_materialization(contract["products"][role]["materialization_receipt_ref"]) for role in ("before", "after")]
    if any(item["status"] != "pass" for item in custody):
        raise SystemExit("source materialization changed during recovery")
    metrics_exists = (attempt_root / "metrics.json").is_file()
    classification_exists = (attempt_root / "pair_usability_classification_20m.tif").is_file()
    aoi_metrics_established = isinstance(receipt.get("aoi_metrics"), list) and bool(receipt["aoi_metrics"])
    registration_established = isinstance(receipt.get("registration"), dict) and bool(receipt["registration"])
    record = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-OPTICAL-PIXEL-RECOVERY-001-RECONCILIATION",
        "reconciled_at_utc": args.reconciled_at_utc,
        "status": f"terminal_{receipt['status']}_recovery_001_no_retry_released",
        "bindings": {
            "contract_ref": CONTRACT_REF,
            "contract_sha256": sha256_file(ROOT / CONTRACT_REF),
            "publication_gate_ref": PUBLICATION_GATE_REF,
            "publication_gate_sha256": sha256_file(ROOT / PUBLICATION_GATE_REF),
            "final_preflight_ref": PREFLIGHT_REF,
            "final_preflight_sha256": sha256_file(ROOT / PREFLIGHT_REF),
            "real_receipt_ref": RECEIPT_REF,
            "real_receipt_sha256": sha256_file(ROOT / RECEIPT_REF),
            "retained_real_001_reconciliation_ref": REAL_001_RECONCILIATION_REF,
            "retained_real_001_reconciliation_sha256": sha256_file(ROOT / REAL_001_RECONCILIATION_REF),
        },
        "terminal_result": {
            "decision_status": receipt["status"],
            "error_type": receipt.get("error_type"),
            "error": receipt.get("error"),
        },
        "external_attempt": {
            "root": str(attempt_root),
            "inventory": attempt_inventory,
            "derived_raster_created": classification_exists,
            "metrics_file_created": metrics_exists,
        },
        "retained_real_001": {
            "root": str(retained_root),
            "inventory": retained_inventory,
            "status": "preserved_terminal_invalid",
        },
        "source_custody": custody,
        "assertions": {
            "recovery_invocation_count": 1,
            "real_001_invocation_count": 1,
            "real_001_reused_or_retried": False,
            "aoi_metrics_established": aoi_metrics_established,
            "registration_established": registration_established,
            "baseline_established": False,
            "change_established": False,
            "scientific_admission_authorized": False,
            "automatic_retry_authorized": False,
        },
        "next_gate": "retain this terminal QA-only disposition; any baseline, change analysis, or further recovery remains separately gated",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"status": record["status"], "output": OUTPUT.relative_to(ROOT).as_posix()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
