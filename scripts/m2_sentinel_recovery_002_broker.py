#!/usr/bin/env python3
"""Prompt once for a CDSE token and hand it to a detached recovery supervisor."""

from __future__ import annotations

import getpass
import json

from m2_sentinel_recovery_002_core import (
    EXPECTED_SOURCE_ID,
    Recovery002ControlError,
    launch_detached_supervisor,
)


def main() -> int:
    try:
        secret = getpass.getpass("CDSE access token (input hidden; paste once, then press Enter): ")
        process_id = launch_detached_supervisor(secret)
        secret = ""
        print(json.dumps({
            "status": "secret_handed_to_detached_supervisor",
            "source_id": EXPECTED_SOURCE_ID,
            "supervisor_process_id": process_id,
            "secret_transport": "anonymous_pipe_single_use_memory_only",
            "credential_value_recorded": False,
            "console_may_close": True,
        }, indent=2))
        return 0
    except Recovery002ControlError as exc:
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
