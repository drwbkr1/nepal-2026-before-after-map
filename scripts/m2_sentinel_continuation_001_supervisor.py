#!/usr/bin/env python3
"""Detached owner of the four-source continuation-001 sequence."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Callable, Mapping

from acquire_m2_sentinel_continuation_001 import run_continuation_source
from m2_sentinel_continuation_001_core import (
    CONTINUATION_ID,
    DATA_ROOT,
    ROOT,
    SAFE_CODE,
    SOURCE_ORDER,
    Continuation001ControlError,
    ContinuationJournal,
    classify_failure,
    now_utc,
    read_single_use_secret,
    sanitized_child_environment,
    validate_prelaunch_git_state,
)
from reconcile_m2_sentinel_continuation_001_success import reconcile_success


SUPERVISOR_ROOT = DATA_ROOT / "derived/m2-sentinel-continuation-001-supervisor"


def verify_container(source_id: str, secret: str) -> int:
    command = [
        sys.executable,
        str(ROOT / "scripts/verify_m2_product_container.py"),
        "--source-id",
        source_id,
        "--scanned-at-utc",
        now_utc(),
    ]
    if any(secret in part for part in command):
        raise Continuation001ControlError("secret_present_in_verifier_command")
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=sanitized_child_environment(os.environ, secret),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
    )
    return int(result.returncode)


def run_supervised(
    secret: str,
    journal: ContinuationJournal,
    *,
    runtime_validator: Callable[[], None] = validate_prelaunch_git_state,
    product_runner: Callable[..., dict[str, Any]] = run_continuation_source,
    container_verifier: Callable[[str, str], int] = verify_container,
    success_reconciler: Callable[[], Mapping[str, Any]] = reconcile_success,
) -> dict[str, str]:
    runtime_validator()
    for source_id in SOURCE_ORDER:
        journal.update(phase="source_preflight", source_id=source_id, attempt_id=None, bytes_written=0)

        def progress(phase: str, attempt_id: str | None, bytes_written: int | None, *, _source_id: str = source_id) -> None:
            journal.update(
                phase=phase,
                source_id=_source_id,
                attempt_id=attempt_id,
                bytes_written=bytes_written,
            )

        result = product_runner(source_id, secret, progress=progress)
        if result.get("returncode") != 0:
            code = result.get("failure_code")
            if not isinstance(code, str) or SAFE_CODE.fullmatch(code) is None:
                raise Continuation001ControlError("continuation_runner_failure_code_invalid")
            return {"terminal_code": code, "failure_class": "approved_control"}
        journal.update(
            phase="container_verification",
            source_id=source_id,
            attempt_id=result.get("attempt_id"),
            bytes_written=result.get("size_bytes"),
        )
        if container_verifier(source_id, secret) != 0:
            return {
                "terminal_code": f"{source_id.casefold().replace('-', '_')}_container_verification_failed",
                "failure_class": "approved_control",
            }
        journal.mark_completed(source_id)
    journal.update(phase="success_reconciliation", source_id=None, attempt_id=None, bytes_written=0)
    success_reconciler()
    return {"terminal_code": "continuation_001_all_four_succeeded", "failure_class": "none"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--continuation-id", required=True)
    args = parser.parse_args()
    if args.continuation_id != CONTINUATION_ID:
        return 12
    secret = read_single_use_secret(sys.stdin.buffer)
    supervisor_id = f"m2-sentinel-continuation-001-{now_utc().replace(':', '').replace('-', '').casefold()}-{uuid.uuid4().hex[:8]}"
    journal = ContinuationJournal(SUPERVISOR_ROOT / supervisor_id, supervisor_id)
    journal.start()
    try:
        terminal = run_supervised(secret, journal)
        if terminal["failure_class"] == "none":
            journal.finish("succeeded", terminal)
            return 0
        journal.finish("failed", terminal)
        return 20
    except BaseException as exc:
        terminal = classify_failure(exc)
        try:
            journal.finish("failed", terminal)
        except BaseException:
            pass
        return 20
    finally:
        secret = ""


if __name__ == "__main__":
    raise SystemExit(main())
