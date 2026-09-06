#!/usr/bin/env python3
"""Detached owner of the single approved M2-ORB-001 recovery attempt."""

from __future__ import annotations

import argparse
import sys
import uuid

from acquire_m2_orbit_recovery_003 import build_attempt_id, run_recovery
from m2_orbit_recovery_003_core import (
    DATA_ROOT,
    EXPECTED_SOURCE_ID,
    OrbitRecovery003Error,
    SupervisorJournal,
    now_utc,
    read_single_use_secret,
    validate_handoff_claim,
)


SUPERVISOR_ROOT = DATA_ROOT / "derived/m2-orbit-recovery-003-supervisor"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--handoff-id", required=True)
    args = parser.parse_args()
    if args.source_id != EXPECTED_SOURCE_ID:
        return 12
    validate_handoff_claim(args.handoff_id)
    token = read_single_use_secret(sys.stdin.buffer)
    started_at = now_utc()
    nonce = uuid.uuid4().hex[:8]
    attempt_id = build_attempt_id(started_at, nonce)
    supervisor_id = f"m2-orbit-recovery-003-{started_at.replace(':', '').replace('-', '').casefold()}-{nonce}"
    journal = SupervisorJournal(SUPERVISOR_ROOT / supervisor_id, supervisor_id)
    journal.update(phase="preconditions", attempt_id=attempt_id, bytes_written=0)
    journal.start()
    try:
        def progress(phase: str, attempt_id: str | None, bytes_written: int | None) -> None:
            journal.update(phase=phase, attempt_id=attempt_id, bytes_written=bytes_written)

        result = run_recovery(token, attempt_id=attempt_id, started_at=started_at, progress=progress)
        if result.get("returncode") == 0:
            journal.finish("succeeded", "m2_orb_001_recovery_promoted_and_structurally_verified")
            return 0
        journal.finish("failed", str(result.get("failure_code", "orbit_recovery_003_failed")))
        return 20
    except Exception as exc:
        code = exc.code if isinstance(exc, OrbitRecovery003Error) else "orbit_recovery_003_supervisor_unexpected_failure"
        try:
            journal.finish("failed", code)
        except Exception:
            pass
        return 20
    finally:
        token = ""


if __name__ == "__main__":
    raise SystemExit(main())
