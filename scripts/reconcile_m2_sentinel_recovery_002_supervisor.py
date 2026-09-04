#!/usr/bin/env python3
"""Classify detached recovery-002 supervisor evidence and record an absent worker."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from m2_sentinel_recovery_002_core import (
    DATA_ROOT,
    ROOT,
    Recovery002ControlError,
    classify_supervisor_state,
    load_object,
    now_utc,
    process_is_alive,
    write_new_json,
)


SUPERVISOR_ROOT = DATA_ROOT / "derived/m2-sentinel-recovery-002-supervisor"
OUTPUT_ROOT = ROOT / "records/acquisition/supervisor-reconciliation"


def inspect_supervisor(supervisor_id: str, *, record_absent_failure: bool = False) -> dict[str, object]:
    event_root = SUPERVISOR_ROOT / supervisor_id
    try:
        event_root.resolve(strict=True).relative_to(SUPERVISOR_ROOT.resolve(strict=True))
    except (FileNotFoundError, ValueError) as exc:
        raise Recovery002ControlError("supervisor_event_root_invalid") from exc
    started_paths = list(event_root.glob("*-started.json"))
    if len(started_paths) != 1:
        raise Recovery002ControlError("supervisor_started_event_count_invalid")
    started = load_object(started_paths[0])
    heartbeat_path = event_root / f"{supervisor_id}-heartbeat.json"
    heartbeat = load_object(heartbeat_path) if heartbeat_path.is_file() else None
    terminal_paths = list(event_root.glob("*-succeeded.json")) + list(event_root.glob("*-failed.json"))
    terminals = [load_object(path) for path in terminal_paths]
    result = classify_supervisor_state(
        started=started,
        heartbeat=heartbeat,
        terminal_events=terminals,
        process_alive=process_is_alive(int(started.get("process_id", 0))),
    )
    if result.get("status") == "reconcile_absent_process_without_terminal" and record_absent_failure:
        external = {
            **started,
            "event": "supervisor_failed",
            "observed_at": now_utc(),
            "completed_at": now_utc(),
            "terminal_code": result["failure_code"],
            "retry_automatically_authorized": False,
        }
        external_path = event_root / f"{supervisor_id}-failed.json"
        write_new_json(external_path, external)
        public = {
            "schema_version": "1.0",
            "receipt_id": f"NEPAL-M2-SENTINEL-RECOVERY-002-SUPERVISOR-{supervisor_id}",
            "recorded_at_utc": now_utc(),
            "status": "reconciled_absent_supervisor_as_terminal_failure",
            "supervisor_id": supervisor_id,
            "failure_code": result["failure_code"],
            "external_terminal_event": str(external_path),
            "credential_values_read_or_recorded": False,
            "retry_automatically_authorized": False,
        }
        output = OUTPUT_ROOT / f"{supervisor_id}.json"
        write_new_json(output, public)
        result = {**result, "status": public["status"], "receipt": str(output.relative_to(ROOT)).replace("\\", "/")}
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--supervisor-id", required=True)
    parser.add_argument("--record-absent-failure", action="store_true")
    args = parser.parse_args()
    print(json.dumps(inspect_supervisor(args.supervisor_id, record_absent_failure=args.record_absent_failure), indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Recovery002ControlError as exc:
        print(json.dumps({"status": "stopped", "code": exc.code, "mutations_performed": False}, indent=2))
        raise SystemExit(12)
