#!/usr/bin/env python3
"""Run one exact continuation source under the continuation-001 controls."""

from __future__ import annotations

from typing import Any, Callable

from acquire_m2_product_pipe import run_product as run_existing_exact_product
from m2_sentinel_continuation_001_core import (
    RECOVERY_SOURCE_ID,
    SOURCE_ORDER,
    Continuation001ControlError,
    validate_runtime_gate,
    validate_secret,
)


def run_continuation_source(
    source_id: str,
    access_value: str,
    *,
    progress: Callable[[str, str | None, int | None], None] | None = None,
    product_runner: Callable[..., dict[str, Any]] = run_existing_exact_product,
) -> dict[str, Any]:
    """Delegate only an allowlisted continuation source after the exact runtime gate."""
    if source_id == RECOVERY_SOURCE_ID or source_id not in SOURCE_ORDER:
        raise Continuation001ControlError("continuation_source_outside_exact_release")
    validate_secret(access_value)
    validate_runtime_gate()
    return product_runner(source_id, access_value, progress=progress)


if __name__ == "__main__":
    raise SystemExit("This module accepts credentials only from the detached continuation-001 supervisor in memory.")
