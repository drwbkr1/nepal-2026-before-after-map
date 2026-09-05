#!/usr/bin/env python3
"""Detached owner of the single approved M2-ORB-001 recovery attempt."""

from __future__ import annotations

import argparse
import sys
import uuid

from acquire_m2_orbit_recovery_002 import run_recovery
from m2_orbit_recovery_002_core import (
    DATA_ROOT,
    EXPECTED_SOURCE_ID,
    OrbitRecovery002Error,
    SupervisorJournal,
    now_utc,
    read_single_use_secret,
)


SUPERVISOR_ROOT = DATA_ROOT / "derived/m2-orbit-recovery-002-supervisor"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", required=True)
    args = parser.parse_args()
    if args.source_id != EXPECTED_SOURCE_ID:
        return 12
    token = read_single_use_secret(sys.stdin.buffer)
    supervisor_id = f"m2-orbit-recovery-002-{now_utc().replace(':', '').replace('-', '').casefold()}-{uuid.uuid4().hex[:8]}"
    journal = SupervisorJournal(SUPERVISOR_ROOT / supervisor_id, supervisor_id)
    journal.start()
    try:
        def progress(phase: str, attempt_id: str | None, bytes_written: int | None) -> None:
            journal.update(phase=phase, attempt_id=attempt_id, bytes_written=bytes_written)

        result = run_recovery(token, progress=progress)
        if result.get("returncode") == 0:
            journal.finish("succeeded", "m2_orb_001_recovery_promoted_and_structurally_verified")
            return 0
        journal.finish("failed", str(result.get("failure_code", "orbit_recovery_002_failed")))
        return 20
    except Exception as exc:
        code = exc.code if isinstance(exc, OrbitRecovery002Error) else "orbit_recovery_002_supervisor_unexpected_failure"
        try:
            journal.finish("failed", code)
        except Exception:
            pass
        return 20
    finally:
        token = ""


if __name__ == "__main__":
    raise SystemExit(main())
