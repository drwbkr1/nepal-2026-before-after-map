#!/usr/bin/env python3
"""Run the one no-content preflight for PROJ25 receipt recovery-002."""

from __future__ import annotations

import argparse
import json
import os
import stat
from pathlib import Path

from m2_dem_vertical_datum_proj25_core import (
    EXPECTED_RECEIPT_RECOVERY_APPROVAL_SHA256,
    ROOT,
    controlled_path,
    load_contract,
    load_json,
    sha256_file,
    write_new_json,
)


PUBLICATION = ROOT / "records/readiness/m2-dem-proj25-receipt-persistence-recovery-002-implementation-publication-gate.json"
OUTPUT = ROOT / "records/acquisition/m2-dem-vertical-datum-proj25-receipt-persistence-recovery-002-final-preflight.json"
RECOVERY_001_STARTED = ROOT / "records/acquisition/m2-geoid-001-metadata-recovery-001-started.json"
RECOVERY_001_RUNTIME_FAILURE = ROOT / "records/acquisition/m2-dem-vertical-datum-proj25-metadata-recovery-001-runtime-failure.json"
RECOVERY_001_OUTCOME = ROOT / "records/acquisition/m2-dem-vertical-datum-proj25-metadata-recovery-001-outcome-reconciliation.json"


def utc_now() -> str:
    import datetime as datetime_module

    return datetime_module.datetime.now(datetime_module.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_reparse_point(path: Path) -> bool:
    attributes = getattr(os.lstat(path), "st_file_attributes", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observed-at-utc", default=None)
    args = parser.parse_args()
    if OUTPUT.exists():
        raise SystemExit("refusing receipt-recovery-002 preflight output collision")
    if not PUBLICATION.is_file():
        raise SystemExit("receipt-recovery-002 implementation public gate is missing")
    publication = load_json(PUBLICATION)
    if publication.get("status") != "pass_public_default_branch_ci_receipt_recovery_released":
        raise SystemExit("receipt-recovery-002 public gate does not release the final preflight")

    contract = load_contract()
    grid = contract["grid"]
    recovery = contract["receipt_persistence_recovery_002"]
    staged = controlled_path(grid["staging_relative_path"])
    destination = controlled_path(grid["destination_relative_path"])
    receipt = ROOT / recovery["receipt_ref"]
    if not staged.is_file() or not destination.is_file():
        raise SystemExit("exact staged or promoted grid path is absent")
    if staged.stat().st_size != grid["expected_size_bytes"] or destination.stat().st_size != grid["expected_size_bytes"]:
        raise SystemExit("exact staged or promoted grid length differs")
    if not os.path.samefile(staged, destination):
        raise SystemExit("staged and promoted grid no longer have the same file identity")
    if receipt.exists() or receipt.is_symlink():
        raise SystemExit("receipt-recovery-002 output collision")
    output_parent = receipt.parent
    if (
        output_parent.resolve() != (ROOT / "records/acquisition").resolve()
        or not output_parent.is_dir()
        or output_parent.is_symlink()
        or is_reparse_point(output_parent)
    ):
        raise SystemExit("receipt output parent is not the exact real tracked directory")

    started = load_json(RECOVERY_001_STARTED)
    failure = load_json(RECOVERY_001_RUNTIME_FAILURE)
    outcome = load_json(RECOVERY_001_OUTCOME)
    if (
        started.get("attempt_id") != recovery["terminal_recovery_attempt_id"]
        or failure.get("status") != "terminal_failure_after_conditional_promotion_no_terminal_receipt"
        or outcome.get("status") != "block_terminal_receipt_persistence_failure_after_exact_promotion"
        or outcome.get("observed_result", {}).get("destination_sha256") != grid["expected_sha256"]
        or outcome.get("observed_result", {}).get("same_file_identity") is not True
        or outcome.get("observed_result", {}).get("conversion_attempts_started") != 0
    ):
        raise SystemExit("terminal recovery-001 evidence differs")

    record = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-DEM-PROJ25-RECEIPT-PERSISTENCE-RECOVERY-002-FINAL-PREFLIGHT",
        "observed_at_utc": args.observed_at_utc or utc_now(),
        "status": "pass_no_content_receipt_recovery_002_released",
        "approval_sha256": EXPECTED_RECEIPT_RECOVERY_APPROVAL_SHA256,
        "publication_gate_sha256": sha256_file(PUBLICATION),
        "recovery_001_started_sha256": sha256_file(RECOVERY_001_STARTED),
        "recovery_001_runtime_failure_sha256": sha256_file(RECOVERY_001_RUNTIME_FAILURE),
        "recovery_001_outcome_sha256": sha256_file(RECOVERY_001_OUTCOME),
        "staged_file_metadata": {"path": str(staged), "size_bytes": staged.stat().st_size, "content_read": False},
        "promoted_file_metadata": {"path": str(destination), "size_bytes": destination.stat().st_size, "content_read": False},
        "staged_and_destination_same_file_identity": True,
        "receipt_ref": recovery["receipt_ref"],
        "assertions": {
            "network_requests_performed": 0,
            "grid_content_bytes_read": 0,
            "grid_hash_computed": False,
            "grid_metadata_read": False,
            "receipt_output_reserved": False,
            "recovery_001_retried": False,
            "new_grid_promotion_performed": False,
            "dem_content_read": False,
            "dem_pixels_read": False,
            "operation_sign_preflight_performed": False,
            "conversion_attempts_started": 0,
            "external_data_mutated": False,
        },
    }
    write_new_json(OUTPUT, record)
    print(json.dumps({"status": record["status"], "output": str(OUTPUT.relative_to(ROOT)).replace("\\", "/")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
