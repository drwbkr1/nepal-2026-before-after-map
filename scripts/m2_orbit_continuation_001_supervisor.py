#!/usr/bin/env python3
"""Detached owner of the fixed-order three-source orbit continuation."""

from __future__ import annotations

import argparse
import sys
import uuid
from typing import Any, Callable, Mapping

from acquire_m2_orbit_continuation_001 import run_continuation_source
from m2_orbit_continuation_001_core import (
    CONTINUATION_ID,
    DATA_ROOT,
    SAFE_CODE,
    SOURCE_ORDER,
    OrbitContinuation001Error,
    ContinuationJournal,
    classify_failure,
    now_utc,
    read_single_use_secret,
    validate_handoff_claim,
    validate_prelaunch_git_state,
)
from reconcile_m2_orbit_continuation_001_success import reconcile_success


SUPERVISOR_ROOT = DATA_ROOT / "derived/m2-orbit-continuation-001-supervisor"


def run_supervised(
    secret: str,
    journal: ContinuationJournal,
    *,
    runtime_validator: Callable[[], None] = validate_prelaunch_git_state,
    source_runner: Callable[..., dict[str, Any]] = run_continuation_source,
    success_reconciler: Callable[[], Mapping[str, Any]] = reconcile_success,
) -> dict[str, str]:
    runtime_validator()
    for source_id in SOURCE_ORDER:
        journal.update(phase="source_preflight", source_id=source_id, attempt_id=None, bytes_written=0)

        def progress(phase: str, attempt_id: str | None, bytes_written: int | None, *, _source_id: str = source_id) -> None:
            journal.update(phase=phase, source_id=_source_id, attempt_id=attempt_id, bytes_written=bytes_written)

        result = source_runner(source_id, secret, progress=progress)
        if result.get("returncode") != 0:
            code = result.get("failure_code")
            if not isinstance(code, str) or SAFE_CODE.fullmatch(code) is None:
                raise OrbitContinuation001Error("continuation_runner_failure_code_invalid")
            return {"terminal_code": code, "failure_class": "approved_control"}
        journal.mark_completed(source_id)
    journal.update(phase="success_reconciliation", source_id=None, attempt_id=None, bytes_written=0)
    success_reconciler()
    return {"terminal_code": "orbit_continuation_001_all_three_succeeded", "failure_class": "none"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--continuation-id", required=True)
    parser.add_argument("--handoff-id", required=True)
    args = parser.parse_args()
    if args.continuation_id != CONTINUATION_ID:
        return 12
    validate_handoff_claim(args.handoff_id)
    secret = read_single_use_secret(sys.stdin.buffer)
    started_at = now_utc()
    supervisor_id = f"m2-orbit-continuation-001-{started_at.replace(':', '').replace('-', '').casefold()}-{uuid.uuid4().hex[:8]}"
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
