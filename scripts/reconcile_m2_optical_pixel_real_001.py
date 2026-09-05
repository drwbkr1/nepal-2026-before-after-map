#!/usr/bin/env python3
"""Reconcile the terminal invalid optical pixel attempt and source custody."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "records/readiness/m2-optical-pixel-real-001-reconciliation.json"
REFS = {
    "contract": "config/qa/optical-pixel-readiness-contract-001.json",
    "publication_gate": "records/readiness/m2-optical-pixel-publication-gate.json",
    "final_preflight": "records/readiness/m2-optical-pixel-final-preflight.json",
    "real_receipt": "records/readiness/optical-pixel/m2-s2-pixel-readiness-real-001.json",
}


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
    return {"source_id": receipt["source_id"], "file_count": total, "status": "pass" if not errors else "invalid", "errors": errors, "manifest_sha256": sha256_file(manifest_path), "receipt_sha256": sha256_file(receipt_path)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconciled-at-utc", required=True)
    args = parser.parse_args()
    if OUTPUT.exists():
        raise SystemExit("refusing optical pixel reconciliation collision")
    values = {key: load_path(ROOT / ref) for key, ref in REFS.items()}
    contract = values["contract"]
    receipt = values["real_receipt"]
    if values["publication_gate"].get("status") != "pass_public_controls_verified_before_optical_pixel_attempt":
        raise SystemExit("publication gate differs")
    if values["final_preflight"].get("status") != "pass_exact_optical_pixel_inputs_ready_no_pixel_access":
        raise SystemExit("final preflight differs")
    if (
        receipt.get("receipt_id") != "NEPAL-S2-PIXEL-READINESS-REAL-001"
        or receipt.get("attempt_id") != "optical-pixel-readiness-real-001"
        or receipt.get("status") != "invalid"
        or receipt.get("error_type") != "KeyError"
        or receipt.get("error") != "'xmin'"
        or receipt.get("automatic_retry_authorized") is not False
        or receipt.get("activity", {}).get("real_product_pixel_access_attempted") is not True
    ):
        raise SystemExit("terminal real-001 receipt differs")
    attempt_root = Path(contract["attempt"]["external_attempt_root"]).resolve(strict=True)
    inventory = []
    for path in sorted((item for item in attempt_root.rglob("*") if item.is_file()), key=lambda item: str(item).casefold()):
        inventory.append({"relative_path": path.relative_to(attempt_root).as_posix(), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    if [item["relative_path"] for item in inventory] != ["failure.json", "started.json"]:
        raise SystemExit("terminal external attempt contains unexpected outputs")
    custody = [verify_materialization(contract["products"][role]["materialization_receipt_ref"]) for role in ("before", "after")]
    if any(item["status"] != "pass" for item in custody):
        raise SystemExit("source materialization changed after invalid attempt")
    record = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-OPTICAL-PIXEL-REAL-001-RECONCILIATION",
        "reconciled_at_utc": args.reconciled_at_utc,
        "status": "invalid_terminal_real_001_no_retry_released",
        "bindings": {f"{key}_ref": ref for key, ref in REFS.items()} | {f"{key}_sha256": sha256_file(ROOT / ref) for key, ref in REFS.items()},
        "failure": {"code": "production_grid_extent_shape_mismatch", "observed_error": "KeyError: 'xmin'", "stage": "first real SCL target-grid read returned before classification", "thresholds_changed_after_observation": False},
        "external_attempt": {"root": str(attempt_root), "inventory": inventory, "derived_raster_count": 0, "metrics_file_created": False},
        "source_custody": custody,
        "assertions": {"real_invocation_count": 1, "real_product_pixel_access_attempted": True, "aoi_metrics_established": False, "mask_metrics_established": False, "registration_established": False, "baseline_established": False, "change_established": False, "scientific_admission_authorized": False, "automatic_retry_authorized": False},
        "next_gate": "human review is required for any separately identified corrected recovery attempt",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": record["status"], "output": OUTPUT.relative_to(ROOT).as_posix()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
