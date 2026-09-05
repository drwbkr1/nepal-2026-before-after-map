#!/usr/bin/env python3
"""Prompt once and hand a CDSE token to the detached continuation worker."""

from __future__ import annotations

import getpass
import json

from m2_sentinel_continuation_001_core import (
    CONTINUATION_ID,
    SOURCE_ORDER,
    Continuation001ControlError,
    launch_detached_supervisor,
    validate_prelaunch_git_state,
)


def main() -> int:
    try:
        validate_prelaunch_git_state()
        secret = getpass.getpass("CDSE access token (input hidden; paste once, then press Enter): ")
        process_id = launch_detached_supervisor(secret)
        secret = ""
        print(json.dumps({
            "status": "secret_handed_to_detached_continuation_supervisor",
            "continuation_id": CONTINUATION_ID,
            "source_ids_in_exact_order": list(SOURCE_ORDER),
            "supervisor_process_id": process_id,
            "secret_transport": "anonymous_pipe_single_use_memory_only",
            "credential_value_recorded": False,
            "console_may_close": True,
        }, indent=2))
        return 0
    except Continuation001ControlError as exc:
        print(json.dumps({
            "status": "stopped",
            "code": exc.code,
            "credential_value_recorded": False,
            "mutations_performed": False,
        }, indent=2))
        return 12
    except BaseException:
        print(json.dumps({
            "status": "stopped",
            "code": "secret_broker_unexpected_failure",
            "credential_value_recorded": False,
        }, indent=2))
        return 20


if __name__ == "__main__":
    raise SystemExit(main())
