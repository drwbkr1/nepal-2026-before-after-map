#!/usr/bin/env python3
"""Record the terminal outcome of the one approved orbit recovery-002 attempt."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from m2_orbit_recovery_002_core import (
    ACTIVE_INTAKE_REF,
    DATA_ROOT,
    EXPECTED_DESTINATION_RELATIVE,
    EXPECTED_ATTEMPT_PREFIX,
    EXPECTED_SOURCE_ID,
    FINAL_PREFLIGHT_REF,
    ORIGINAL_ATTEMPT_ID,
    PROJECT_ROOT,
    ROOT,
    SECRET_REFERENCE,
    load_object,
    now_utc,
    require_original_failure,
    sha256_file,
    write_new_json,
)


OUTPUT = ROOT / "records/acquisition/m2-orbit-recovery-002-outcome-reconciliation.json"
SUPERVISOR_ROOT = DATA_ROOT / "derived/m2-orbit-recovery-002-supervisor"
STAGING_ROOT = DATA_ROOT / ".intake-staging/nepal-m2-orbit-recovery-002"
EXPECTED_EMPTY_PAYLOAD_PARENT = STAGING_ROOT / EXPECTED_ATTEMPT_PREFIX


def _relative_or_absolute(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def reconcile_pretransfer_supervisor_failure(supervisor_id: str) -> dict:
    if not supervisor_id.startswith("m2-orbit-recovery-002-") or any(character in supervisor_id for character in "/\\"):
        raise SystemExit("invalid supervisor identity")
    supervisor_directory = SUPERVISOR_ROOT / supervisor_id
    if not supervisor_directory.is_dir():
        raise SystemExit("supervisor directory missing")
    expected_paths = {
        "started": supervisor_directory / f"{supervisor_id}-started.json",
        "heartbeat": supervisor_directory / f"{supervisor_id}-heartbeat.json",
        "failed": supervisor_directory / f"{supervisor_id}-failed.json",
    }
    observed_files = sorted(path.name for path in supervisor_directory.iterdir() if path.is_file())
    if observed_files != sorted(path.name for path in expected_paths.values()) or any(path.is_dir() for path in supervisor_directory.iterdir()):
        raise SystemExit("supervisor journal inventory differs")
    events = {name: load_object(path) for name, path in expected_paths.items()}
    started = events["started"]
    heartbeat = events["heartbeat"]
    failed = events["failed"]
    if (
        started.get("event") != "supervisor_started"
        or heartbeat.get("event") != "supervisor_heartbeat"
        or failed.get("event") != "supervisor_failed"
        or any(event.get("supervisor_id") != supervisor_id for event in events.values())
        or any(event.get("source_id") != EXPECTED_SOURCE_ID for event in events.values())
        or len({event.get("process_id") for event in events.values()}) != 1
        or failed.get("phase") != "public_catalog_revalidation"
        or failed.get("attempt_id") is not None
        or failed.get("bytes_written") != 0
        or failed.get("terminal_code") != "orbit_recovery_002_supervisor_unexpected_failure"
        or failed.get("retry_automatically_authorized") is not False
        or any(event.get("credential_reference") != SECRET_REFERENCE for event in events.values())
        or any(event.get("credential_value_recorded") is not False for event in events.values())
    ):
        raise SystemExit("supervisor terminal evidence differs")
    if not STAGING_ROOT.is_dir() or not EXPECTED_EMPTY_PAYLOAD_PARENT.is_dir():
        raise SystemExit("recovery staging evidence missing")
    staging_inventory = sorted(STAGING_ROOT.rglob("*"))
    if staging_inventory != [EXPECTED_EMPTY_PAYLOAD_PARENT] or any(path.is_file() for path in staging_inventory):
        raise SystemExit("recovery staging is not the exact empty pretransfer inventory")
    intake_path = ROOT / ACTIVE_INTAKE_REF
    intake = load_object(intake_path)
    asset = require_original_failure(intake)
    destination = DATA_ROOT / "custody" / EXPECTED_DESTINATION_RELATIVE
    if destination.exists():
        raise SystemExit("unexpected orbit destination exists")
    final_preflight_path = ROOT / FINAL_PREFLIGHT_REF
    final_preflight = load_object(final_preflight_path)
    if (
        final_preflight.get("status") != "pass_no_payload_ready_for_single_secret_pipe_handoff"
        or final_preflight.get("bindings", {}).get("active_intake_sha256") != sha256_file(intake_path)
    ):
        raise SystemExit("final preflight or active intake binding drift")
    return {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-RECOVERY-002-OUTCOME-RECONCILIATION-001",
        "recorded_at_utc": now_utc(),
        "status": "terminal_pretransfer_supervisor_failure_no_retry",
        "source_id": EXPECTED_SOURCE_ID,
        "supervisor_id": supervisor_id,
        "attempt_id": None,
        "outcome": "failed_pre_transfer",
        "failure": {
            "terminal_code": failed["terminal_code"],
            "last_recorded_phase": failed["phase"],
            "classification": "unclassified_local_pretransfer_failure",
            "bounded_window": "after exact public catalog revalidation returned and the exclusive payload parent was created, before an attempt event root, attempt ID, started event, intake mutation, or payload request",
            "underlying_exception_category": "unavailable_by_design_in_terminal_journal",
            "catalog_response_hash_persisted": False,
        },
        "bindings": {
            "active_intake_ref": ACTIVE_INTAKE_REF,
            "active_intake_sha256": sha256_file(intake_path),
            "final_preflight_ref": FINAL_PREFLIGHT_REF,
            "final_preflight_sha256": sha256_file(final_preflight_path),
            "supervisor_started_ref": _relative_or_absolute(expected_paths["started"]),
            "supervisor_started_sha256": sha256_file(expected_paths["started"]),
            "supervisor_heartbeat_ref": _relative_or_absolute(expected_paths["heartbeat"]),
            "supervisor_heartbeat_sha256": sha256_file(expected_paths["heartbeat"]),
            "supervisor_failed_ref": _relative_or_absolute(expected_paths["failed"]),
            "supervisor_failed_sha256": sha256_file(expected_paths["failed"]),
            "retained_original_attempt_id": ORIGINAL_ATTEMPT_ID,
            "retained_original_attempt_count": len(asset.get("attempts", [])),
        },
        "external_staging_inventory": {
            "root": str(STAGING_ROOT),
            "entries": [{"path": str(EXPECTED_EMPTY_PAYLOAD_PARENT), "kind": "directory", "file_count": 0}],
        },
        "assertions": {
            "owner_handoff_reached_supervisor": True,
            "public_catalog_revalidation_returned_before_local_failure": True,
            "catalog_response_hash_persisted": False,
            "new_attempt_id_created": False,
            "active_intake_mutated": False,
            "orbit_download_requested": False,
            "orbit_payload_bytes_received": 0,
            "destination_created": False,
            "credential_value_recorded": False,
            "recovery_002_authority_consumed": True,
            "automatic_retry_performed": False,
            "other_orbit_source_requested": False,
            "orbit_application_performed": False,
            "dem_or_radar_pixels_processed": False,
            "baseline_or_change_analysis_performed": False,
            "scientific_result_established": False,
            "network_requests_performed_by_reconciliation": False,
        },
        "next_gate": "new explicit review required before any recovery-003 implementation, credential handoff, or M2-ORB-001 request; do not retry recovery-002",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verification-receipt", type=Path)
    parser.add_argument("--supervisor-id")
    args = parser.parse_args()
    if OUTPUT.exists():
        raise SystemExit("refusing outcome-reconciliation output collision")
    if args.supervisor_id:
        if args.verification_receipt is not None:
            raise SystemExit("verification receipt and supervisor failure are mutually exclusive")
        payload = reconcile_pretransfer_supervisor_failure(args.supervisor_id)
        write_new_json(OUTPUT, payload)
        print(json.dumps({"status": payload["status"], "output": str(OUTPUT.relative_to(ROOT)).replace("\\", "/")}, indent=2))
        return 0
    intake_path = ROOT / ACTIVE_INTAKE_REF
    intake = load_object(intake_path)
    assets = [item for item in intake.get("assets", []) if item.get("extensions", {}).get("source_id") == EXPECTED_SOURCE_ID]
    if len(assets) != 1:
        raise SystemExit("M2-ORB-001 asset absent or ambiguous")
    asset = assets[0]
    attempts = asset.get("attempts", [])
    if len(attempts) != 2 or attempts[0].get("attempt_id") != ORIGINAL_ATTEMPT_ID or attempts[0].get("outcome") != "failed":
        raise SystemExit("retained failed attempt history differs")
    recovery = attempts[1]
    if not str(recovery.get("attempt_id", "")).startswith(EXPECTED_ATTEMPT_PREFIX + "-") or recovery.get("outcome") not in {"succeeded", "failed"}:
        raise SystemExit("recovery attempt is not terminal or has the wrong identity")
    receipt_ref = asset.get("extensions", {}).get("successful_attempt_receipt") if recovery["outcome"] == "succeeded" else f"records/acquisition/orbit-attempts/{recovery['attempt_id']}.json"
    receipt_path = ROOT / str(receipt_ref)
    if not receipt_path.is_file():
        raise SystemExit("terminal transfer receipt missing")
    verification = None
    if recovery["outcome"] == "succeeded":
        if args.verification_receipt is None:
            raise SystemExit("passing offline verification receipt required after a recovery success")
        verification_path = args.verification_receipt if args.verification_receipt.is_absolute() else ROOT / args.verification_receipt
        verification = load_object(verification_path)
        if verification.get("status") != "pass_orbit_input_only" or verification.get("source_id") != EXPECTED_SOURCE_ID:
            raise SystemExit("offline verification receipt does not pass for M2-ORB-001")
    payload = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-RECOVERY-002-OUTCOME-RECONCILIATION-001",
        "recorded_at_utc": now_utc(),
        "status": "pass_recovery_and_offline_verification_only" if verification else "terminal_failure_preserved_no_retry",
        "source_id": EXPECTED_SOURCE_ID,
        "attempt_id": recovery["attempt_id"],
        "outcome": recovery["outcome"],
        "bindings": {
            "active_intake_sha256": sha256_file(intake_path),
            "terminal_receipt_ref": str(receipt_path.relative_to(ROOT)).replace("\\", "/"),
            "terminal_receipt_sha256": sha256_file(receipt_path),
            "offline_verification_ref": str(args.verification_receipt).replace("\\", "/") if verification else None,
            "offline_verification_sha256": sha256_file(verification_path) if verification else None,
        },
        "assertions": {
            "original_failed_attempt_preserved": True,
            "recovery_attempt_count": 1,
            "automatic_retry_performed": False,
            "other_orbit_source_requested": False,
            "credential_value_recorded": False,
            "orbit_application_performed": False,
            "dem_or_radar_pixels_processed": False,
            "baseline_or_change_analysis_performed": False,
            "scientific_result_established": False,
        },
        "next_gate": "separate owner review before any M2-ORB-002 through M2-ORB-004 request" if verification else "new explicit review required; do not retry",
    }
    write_new_json(OUTPUT, payload)
    print(json.dumps({"status": payload["status"], "output": str(OUTPUT.relative_to(ROOT)).replace("\\", "/")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
