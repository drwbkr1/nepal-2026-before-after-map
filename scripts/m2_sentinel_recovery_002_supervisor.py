#!/usr/bin/env python3
"""Detached owner of the single recovery-002 attempt and bounded continuation."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import uuid
from pathlib import Path

from acquire_m2_product_secret_pipe import ALLOWED_SOURCE_IDS, run_product
from acquire_m2_sentinel_recovery_002 import run_recovery
from m2_sentinel_recovery_002_core import (
    DATA_ROOT,
    EXPECTED_SOURCE_ID,
    ROOT,
    Recovery002ControlError,
    SupervisorJournal,
    now_utc,
    read_single_use_secret,
    sanitized_child_environment,
)
from reconcile_m2_sentinel_recovery_002_success import reconcile_success
from verify_m2_sentinel_recovery_002_container import verify_and_record


CONTINUATION_ORDER = ("M1-SRC-005", "M1-SRC-006", "M1-SRC-008", "M1-SRC-010")
SUPERVISOR_ROOT = DATA_ROOT / "derived/m2-sentinel-recovery-002-supervisor"


def _verify_continuation(source_id: str, token: str) -> int:
    command = [
        sys.executable,
        str(ROOT / "scripts/verify_m2_product_container.py"),
        "--source-id",
        source_id,
        "--scanned-at-utc",
        now_utc(),
    ]
    if any(token in part for part in command):
        raise Recovery002ControlError("secret_present_in_verifier_command")
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=sanitized_child_environment(os.environ, token),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
    )
    return int(result.returncode)


def run_supervised(token: str, journal: SupervisorJournal) -> str:
    def update(phase: str, attempt_id: str | None, bytes_written: int | None) -> None:
        journal.update(phase=phase, attempt_id=attempt_id, bytes_written=bytes_written)

    recovery = run_recovery(token, progress=update)
    if recovery.get("returncode") != 0:
        return "recovery_002_transfer_failed"
    journal.update(phase="recovery_002_container_verification", attempt_id=recovery.get("attempt_id"))
    verified = verify_and_record(now_utc())
    if verified.get("returncode") != 0:
        return "recovery_002_container_verification_failed"

    for source_id in CONTINUATION_ORDER:
        if source_id not in ALLOWED_SOURCE_IDS:
            raise Recovery002ControlError("continuation_order_drift")
        journal.update(phase=f"continuation_{source_id.casefold()}_transfer", attempt_id=None, bytes_written=0)
        result = run_product(source_id, token, progress=update)
        if result.get("returncode") != 0:
            return f"{source_id.casefold()}_transfer_failed"
        journal.update(phase=f"continuation_{source_id.casefold()}_container", attempt_id=result.get("attempt_id"))
        if _verify_continuation(source_id, token) != 0:
            return f"{source_id.casefold()}_container_verification_failed"

    journal.update(phase="success_reconciliation")
    reconcile_success()
    return "recovery_002_and_bounded_continuation_succeeded"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", required=True)
    args = parser.parse_args()
    if args.source_id != EXPECTED_SOURCE_ID:
        return 12
    token = read_single_use_secret(sys.stdin.buffer)
    supervisor_id = f"m2-sentinel-recovery-002-{now_utc().replace(':', '').replace('-', '').casefold()}-{uuid.uuid4().hex[:8]}"
    journal = SupervisorJournal(SUPERVISOR_ROOT / supervisor_id, supervisor_id)
    journal.start()
    try:
        terminal_code = run_supervised(token, journal)
        if terminal_code.endswith("succeeded"):
            journal.finish("succeeded", terminal_code)
            return 0
        journal.finish("failed", terminal_code)
        return 20
    except Exception as exc:
        code = exc.code if isinstance(exc, Recovery002ControlError) else "unexpected_supervisor_failure"
        try:
            journal.finish("failed", code)
        except Exception:
            pass
        return 20
    finally:
        token = ""


if __name__ == "__main__":
    raise SystemExit(main())
