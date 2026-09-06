#!/usr/bin/env python3
"""Reconcile the single terminal recovery-003 supervisor without extending authority."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from m2_orbit_recovery_003_core import (
    ACTIVE_INTAKE_REF,
    DATA_ROOT,
    EXPECTED_ATTEMPT_PREFIX,
    EXPECTED_DESTINATION_RELATIVE,
    EXPECTED_SOURCE_ID,
    FINAL_PREFLIGHT_REF,
    ORIGINAL_ATTEMPT_ID,
    RECOVERY_002_OUTCOME_REF,
    RECOVERY_002_OUTCOME_SHA256,
    ROOT,
    SECRET_REFERENCE,
    load_object,
    now_utc,
    require_original_failure,
    sha256_file,
    write_new_json,
)


OUTPUT = ROOT / "records/acquisition/m2-orbit-recovery-003-outcome-reconciliation.json"
SUPERVISOR_ROOT = DATA_ROOT / "derived/m2-orbit-recovery-003-supervisor"
ATTEMPT_EVENT_PARENT = DATA_ROOT / "derived/m2-orbit-recovery-003-attempts"
STAGING_ROOT = DATA_ROOT / ".intake-staging/nepal-m2-orbit-recovery-003"


def _path_binding(path: Path) -> dict[str, Any]:
    return {"path": str(path), "exists": path.is_file(), "sha256": sha256_file(path) if path.is_file() else None}


def _one_supervisor_terminal(directory: Path, supervisor_id: str) -> tuple[str, Path]:
    candidates = [(outcome, directory / f"{supervisor_id}-{outcome}.json") for outcome in ("succeeded", "failed")]
    present = [(outcome, path) for outcome, path in candidates if path.is_file()]
    if len(present) != 1:
        raise SystemExit("supervisor terminal evidence missing or ambiguous")
    return present[0]


def _attempt_from_supervisor(events: dict[str, dict[str, Any]]) -> str:
    identities = {event.get("attempt_id") for event in events.values()}
    if len(identities) != 1:
        raise SystemExit("supervisor attempt identity differs across events")
    attempt_id = identities.pop()
    if not isinstance(attempt_id, str) or not attempt_id.startswith(EXPECTED_ATTEMPT_PREFIX + "-"):
        raise SystemExit("supervisor attempt identity is outside recovery-003")
    return attempt_id


def reconcile(supervisor_id: str, verification_receipt: Path | None) -> dict[str, Any]:
    if not supervisor_id.startswith("m2-orbit-recovery-003-") or any(character in supervisor_id for character in "/\\"):
        raise SystemExit("invalid supervisor identity")
    directory = SUPERVISOR_ROOT / supervisor_id
    if not directory.is_dir():
        raise SystemExit("supervisor directory missing")
    outcome, terminal_path = _one_supervisor_terminal(directory, supervisor_id)
    paths = {
        "started": directory / f"{supervisor_id}-started.json",
        "heartbeat": directory / f"{supervisor_id}-heartbeat.json",
        "terminal": terminal_path,
    }
    if not all(path.is_file() for path in paths.values()):
        raise SystemExit("supervisor lifecycle evidence incomplete")
    observed_files = sorted(path.name for path in directory.iterdir() if path.is_file())
    if observed_files != sorted(path.name for path in paths.values()) or any(path.is_dir() for path in directory.iterdir()):
        raise SystemExit("supervisor journal inventory differs")
    events = {name: load_object(path) for name, path in paths.items()}
    attempt_id = _attempt_from_supervisor(events)
    if (
        events["started"].get("event") != "supervisor_started"
        or events["heartbeat"].get("event") != "supervisor_heartbeat"
        or events["terminal"].get("event") != f"supervisor_{outcome}"
        or any(event.get("supervisor_id") != supervisor_id for event in events.values())
        or any(event.get("source_id") != EXPECTED_SOURCE_ID for event in events.values())
        or len({event.get("process_id") for event in events.values()}) != 1
        or any(event.get("credential_reference") != SECRET_REFERENCE for event in events.values())
        or any(event.get("credential_value_recorded") is not False for event in events.values())
        or events["terminal"].get("retry_automatically_authorized") is not False
    ):
        raise SystemExit("supervisor terminal evidence differs")

    attempt_root = ATTEMPT_EVENT_PARENT / attempt_id
    attempt_paths = {
        "started": attempt_root / f"{attempt_id}-started.json",
        "catalog": attempt_root / f"{attempt_id}-catalog-revalidated.json",
        "terminal": attempt_root / f"{attempt_id}-{outcome}.json",
    }
    attempt_bindings = {name: _path_binding(path) for name, path in attempt_paths.items()}
    if outcome == "succeeded" and not all(binding["exists"] for binding in attempt_bindings.values()):
        raise SystemExit("successful attempt evidence incomplete")
    if attempt_bindings["started"]["exists"]:
        started = load_object(attempt_paths["started"])
        if started.get("event") != "orbit_recovery_003_started" or started.get("attempt_id") != attempt_id:
            raise SystemExit("attempt started evidence differs")
    if attempt_bindings["catalog"]["exists"]:
        catalog = load_object(attempt_paths["catalog"])
        if catalog.get("event") != "orbit_recovery_003_catalog_revalidated" or catalog.get("attempt_id") != attempt_id:
            raise SystemExit("attempt catalog evidence differs")

    intake_path = ROOT / ACTIVE_INTAKE_REF
    intake = load_object(intake_path)
    assets = [item for item in intake.get("assets", []) if item.get("extensions", {}).get("source_id") == EXPECTED_SOURCE_ID]
    if len(assets) != 1:
        raise SystemExit("M2-ORB-001 asset absent or ambiguous")
    asset = assets[0]
    attempts = asset.get("attempts", [])
    matching = [item for item in attempts if item.get("attempt_id") == attempt_id]
    intake_attempt_recorded = len(matching) == 1
    if not intake_attempt_recorded:
        require_original_failure(intake)
    elif len(attempts) != 2 or attempts[0].get("attempt_id") != ORIGINAL_ATTEMPT_ID:
        raise SystemExit("retained attempt history differs")

    destination = DATA_ROOT / "custody" / EXPECTED_DESTINATION_RELATIVE
    receipt_path = ROOT / f"records/acquisition/orbit-attempts/{attempt_id}.json"
    verification_path = None
    if outcome == "succeeded":
        if not intake_attempt_recorded or matching[0].get("outcome") != "succeeded" or asset.get("state") != "promoted":
            raise SystemExit("successful intake state differs")
        if not destination.is_file() or not receipt_path.is_file() or verification_receipt is None:
            raise SystemExit("successful custody or verification evidence missing")
        verification_path = verification_receipt if verification_receipt.is_absolute() else ROOT / verification_receipt
        verification = load_object(verification_path)
        if verification.get("status") != "pass_orbit_input_only" or verification.get("source_id") != EXPECTED_SOURCE_ID:
            raise SystemExit("offline verification does not pass for M2-ORB-001")
    elif intake_attempt_recorded and matching[0].get("outcome") != "failed":
        raise SystemExit("failed supervisor differs from active intake attempt")

    return {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-RECOVERY-003-OUTCOME-RECONCILIATION-001",
        "recorded_at_utc": now_utc(),
        "status": "pass_recovery_and_offline_verification_only" if outcome == "succeeded" else "terminal_failure_preserved_no_retry",
        "source_id": EXPECTED_SOURCE_ID,
        "supervisor_id": supervisor_id,
        "attempt_id": attempt_id,
        "outcome": outcome,
        "terminal_code": str(events["terminal"].get("terminal_code")),
        "bindings": {
            "recovery_002_outcome_ref": RECOVERY_002_OUTCOME_REF,
            "recovery_002_outcome_sha256": RECOVERY_002_OUTCOME_SHA256,
            "final_preflight_ref": FINAL_PREFLIGHT_REF,
            "final_preflight_sha256": sha256_file(ROOT / FINAL_PREFLIGHT_REF),
            "active_intake_ref": ACTIVE_INTAKE_REF,
            "active_intake_sha256": sha256_file(intake_path),
            "supervisor_events": {name: _path_binding(path) for name, path in paths.items()},
            "attempt_events": attempt_bindings,
            "terminal_receipt": _path_binding(receipt_path),
            "offline_verification_ref": str(verification_path) if verification_path else None,
            "offline_verification_sha256": sha256_file(verification_path) if verification_path else None,
        },
        "observations": {
            "attempt_started_event_exists": attempt_bindings["started"]["exists"],
            "catalog_revalidated_event_exists": attempt_bindings["catalog"]["exists"],
            "attempt_terminal_event_exists": attempt_bindings["terminal"]["exists"],
            "active_intake_attempt_recorded": intake_attempt_recorded,
            "staging_root_exists": STAGING_ROOT.exists(),
            "destination_exists": destination.exists(),
        },
        "assertions": {
            "owner_handoff_count": 1,
            "supervisor_invocation_count": 1,
            "recovery_003_authority_consumed": True,
            "maximum_real_attempts": 1,
            "automatic_retry_performed": False,
            "other_orbit_source_requested": False,
            "credential_value_recorded": False,
            "orbit_application_performed": False,
            "dem_or_radar_pixels_processed": False,
            "baseline_or_change_analysis_performed": False,
            "scientific_result_established": False,
            "network_requests_performed_by_reconciliation": False,
        },
        "next_gate": "separate owner review before any M2-ORB-002 through M2-ORB-004 request" if outcome == "succeeded" else "new explicit review required; do not retry recovery-003",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--supervisor-id", required=True)
    parser.add_argument("--verification-receipt", type=Path)
    args = parser.parse_args()
    if OUTPUT.exists():
        raise SystemExit("refusing outcome-reconciliation output collision")
    payload = reconcile(args.supervisor_id, args.verification_receipt)
    write_new_json(OUTPUT, payload)
    print(json.dumps({"status": payload["status"], "output": str(OUTPUT.relative_to(ROOT)).replace("\\", "/")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
