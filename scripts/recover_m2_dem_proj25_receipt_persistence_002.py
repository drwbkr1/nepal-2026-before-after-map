#!/usr/bin/env python3
"""Recover one durable receipt for the exact already-promoted PROJ grid."""

from __future__ import annotations

import argparse
import json
import os
import stat
from pathlib import Path
from typing import Any, BinaryIO

from m2_dem_vertical_datum_proj25_core import (
    EXPECTED_RECEIPT_RECOVERY_APPROVAL_SHA256,
    ROOT,
    controlled_path,
    inspect_arcgis_readability,
    inspect_grid,
    load_contract,
    load_json,
    sha256_file,
)


PREFLIGHT = ROOT / "records/acquisition/m2-dem-vertical-datum-proj25-receipt-persistence-recovery-002-final-preflight.json"
RECEIPT = ROOT / "records/acquisition/m2-geoid-001-receipt-recovery-002.json"


class ReceiptRecoveryError(RuntimeError):
    """Fail-closed receipt recovery error with a stable code."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def utc_now() -> str:
    import datetime as datetime_module

    return datetime_module.datetime.now(datetime_module.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_reparse_point(path: Path) -> bool:
    attributes = getattr(os.lstat(path), "st_file_attributes", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def reserve_receipt(path: Path) -> BinaryIO:
    expected_parent = (ROOT / "records/acquisition").resolve()
    try:
        resolved_parent = path.parent.resolve(strict=True)
        resolved_parent.relative_to(ROOT.resolve())
    except (FileNotFoundError, ValueError) as exc:
        raise ReceiptRecoveryError("receipt_output_parent_missing_or_escaped") from exc
    if (
        resolved_parent != expected_parent
        or not path.parent.is_dir()
        or path.parent.is_symlink()
        or is_reparse_point(path.parent)
    ):
        raise ReceiptRecoveryError("receipt_output_parent_not_exact_real_directory")
    try:
        stream = path.open("xb")
    except FileExistsError as exc:
        raise ReceiptRecoveryError("receipt_output_collision") from exc
    try:
        stream.flush()
        os.fsync(stream.fileno())
    except OSError as exc:
        stream.close()
        raise ReceiptRecoveryError("receipt_reservation_fsync_failed") from exc
    return stream


def write_reserved_receipt(stream: BinaryIO, value: dict[str, Any]) -> None:
    if stream.tell() != 0:
        raise ReceiptRecoveryError("reserved_receipt_not_empty")
    stream.write((json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    stream.flush()
    os.fsync(stream.fileno())


def guarded_controls() -> tuple[dict[str, Any], Path, Path, dict[str, Any]]:
    contract = load_contract()
    grid = contract["grid"]
    recovery = contract["receipt_persistence_recovery_002"]
    preflight = load_json(PREFLIGHT)
    staged = controlled_path(grid["staging_relative_path"])
    destination = controlled_path(grid["destination_relative_path"])
    if (
        recovery.get("approval_sha256") != EXPECTED_RECEIPT_RECOVERY_APPROVAL_SHA256
        or recovery.get("attempt_id") != "m2-geoid-001-receipt-recovery-002"
        or recovery.get("network_requests") != 0
        or recovery.get("recovery_001_retries") != 0
        or recovery.get("maximum_receipt_recovery_attempts") != 1
        or recovery.get("new_promotion_actions") != 0
        or recovery.get("automatic_retry") is not False
        or preflight.get("status") != "pass_no_content_receipt_recovery_002_released"
        or preflight.get("approval_sha256") != EXPECTED_RECEIPT_RECOVERY_APPROVAL_SHA256
        or preflight.get("assertions", {}).get("grid_content_bytes_read") != 0
        or preflight.get("assertions", {}).get("receipt_output_reserved") is not False
        or preflight.get("receipt_ref") != recovery.get("receipt_ref")
    ):
        raise ReceiptRecoveryError("receipt_recovery_controls_drift")
    if not staged.is_file() or not destination.is_file():
        raise ReceiptRecoveryError("exact_grid_path_absent")
    if staged.stat().st_size != grid["expected_size_bytes"] or destination.stat().st_size != grid["expected_size_bytes"]:
        raise ReceiptRecoveryError("exact_grid_length_drift")
    if not os.path.samefile(staged, destination):
        raise ReceiptRecoveryError("staged_destination_file_identity_drift")
    return contract, staged, destination, preflight


def inspect_exact_grid(contract: dict[str, Any], staged: Path, destination: Path) -> dict[str, Any]:
    grid = contract["grid"]
    observed = {"size_bytes": destination.stat().st_size, "sha256": sha256_file(destination)}
    if observed != {"size_bytes": grid["expected_size_bytes"], "sha256": grid["expected_sha256"]}:
        raise ReceiptRecoveryError("promoted_grid_byte_identity_drift")
    if not os.path.samefile(staged, destination):
        raise ReceiptRecoveryError("staged_destination_file_identity_drift")
    metadata = inspect_grid(destination)
    arcgis = inspect_arcgis_readability(destination)
    if not arcgis["readable"] or arcgis["width"] != 8640 or arcgis["height"] != 4321 or arcgis["band_count"] != 1:
        raise ReceiptRecoveryError("arcgis_grid_readability_drift")
    return {
        "identity": observed,
        "staged_and_destination_same_file_identity": True,
        "metadata": metadata,
        "arcgis_readability": arcgis,
    }


def execute(output: Path = RECEIPT) -> tuple[int, dict[str, Any]]:
    reserved: BinaryIO | None = None
    try:
        contract, staged, destination, preflight = guarded_controls()
        expected_output = ROOT / contract["receipt_persistence_recovery_002"]["receipt_ref"]
        if output.resolve() != expected_output.resolve():
            raise ReceiptRecoveryError("receipt_output_path_not_exact")
        reserved = reserve_receipt(output)
    except (ReceiptRecoveryError, FileNotFoundError, OSError, ValueError) as exc:
        code = exc.code if isinstance(exc, ReceiptRecoveryError) else "receipt_recovery_pre_read_control_failure"
        interrupted = output.exists() and code == "receipt_reservation_fsync_failed"
        return (13 if interrupted else 12), {
            "status": "terminal_persistence_interruption" if interrupted else "stopped_before_grid_content_read",
            "code": code,
            "receipt_reserved": output.exists() and code != "receipt_output_collision",
            "reserved_receipt_preserved": interrupted,
            "grid_content_read": False,
            "external_data_mutated": False,
        }

    try:
        inspection = inspect_exact_grid(contract, staged, destination)
        observed_at = utc_now()
        receipt = {
            "schema_version": "1.0",
            "receipt_id": "NEPAL-M2-DEM-PROJ25-RECEIPT-PERSISTENCE-RECOVERY-002",
            "attempt_id": "m2-geoid-001-receipt-recovery-002",
            "status": "pass_exact_promoted_grid_receipt_recovered_input_only",
            "observed_at_utc": observed_at,
            "approval_sha256": EXPECTED_RECEIPT_RECOVERY_APPROVAL_SHA256,
            "final_preflight_sha256": sha256_file(PREFLIGHT),
            "source_id": contract["grid"]["source_id"],
            "staged_path": str(staged),
            "destination_path": str(destination),
            "observed": inspection["identity"],
            "staged_and_destination_same_file_identity": inspection["staged_and_destination_same_file_identity"],
            "gdal_metadata": inspection["metadata"],
            "arcgis_readability": inspection["arcgis_readability"],
            "persistence": {
                "receipt_reserved_before_grid_content_read": True,
                "exclusive_creation": True,
                "complete_receipt_written_through_reserved_handle": True,
                "flush_and_fsync_required": True,
                "reuse_authorized": False,
            },
            "assertions": {
                "network_request_count": 0,
                "recovery_001_retries": 0,
                "new_grid_promotion_actions": 0,
                "external_data_mutated": False,
                "dem_pixels_read": False,
                "operation_sign_preflight_performed": False,
                "conversion_attempts_started": 0,
                "scientific_result_established": False,
            },
        }
        write_reserved_receipt(reserved, receipt)
        return 0, {"status": receipt["status"], "output": str(output), "receipt_reserved_before_grid_content_read": True}
    except ReceiptRecoveryError as exc:
        failure = {
            "schema_version": "1.0",
            "receipt_id": "NEPAL-M2-DEM-PROJ25-RECEIPT-PERSISTENCE-RECOVERY-002",
            "attempt_id": "m2-geoid-001-receipt-recovery-002",
            "status": "terminal_failure_no_retry",
            "observed_at_utc": utc_now(),
            "approval_sha256": EXPECTED_RECEIPT_RECOVERY_APPROVAL_SHA256,
            "final_preflight_sha256": sha256_file(PREFLIGHT),
            "failure_code": exc.code,
            "persistence": {
                "receipt_reserved_before_grid_content_read": True,
                "exclusive_creation": True,
                "complete_receipt_written_through_reserved_handle": True,
                "flush_and_fsync_required": True,
                "reuse_authorized": False,
            },
            "assertions": {
                "network_request_count": 0,
                "recovery_001_retries": 0,
                "new_grid_promotion_actions": 0,
                "automatic_retry_authorized": False,
                "external_data_mutated": False,
                "dem_pixels_read": False,
                "operation_sign_preflight_performed": False,
                "conversion_attempts_started": 0,
                "scientific_result_established": False,
            },
        }
        write_reserved_receipt(reserved, failure)
        return 20, {"status": failure["status"], "code": exc.code, "output": str(output)}
    except Exception as exc:
        return 13, {
            "status": "terminal_persistence_interruption",
            "code": type(exc).__name__,
            "output": str(output),
            "reserved_receipt_preserved": True,
            "automatic_retry_authorized": False,
            "external_data_mutated": False,
        }
    finally:
        if reserved is not None:
            reserved.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    code, result = execute()
    print(json.dumps(result, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
