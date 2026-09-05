#!/usr/bin/env python3
"""Receive one CDSE token and hand it to the detached M2-ORB-001 supervisor."""

from __future__ import annotations

import argparse
import getpass
import json
import sys

from m2_orbit_recovery_002_core import (
    EXPECTED_SOURCE_ID,
    OrbitRecovery002Error,
    launch_detached_supervisor,
    read_single_use_secret,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stdin", action="store_true", help="Read one newline-terminated token from stdin.")
    args = parser.parse_args()
    secret = ""
    try:
        secret = read_single_use_secret(sys.stdin.buffer) if args.stdin else getpass.getpass(
            "CDSE access token (hidden; paste once, then press Enter): "
        )
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
    except OrbitRecovery002Error as exc:
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
            "code": "orbit_recovery_002_broker_unexpected_failure",
            "credential_value_recorded": False,
        }, indent=2))
        return 20
    finally:
        secret = ""


if __name__ == "__main__":
    raise SystemExit(main())
