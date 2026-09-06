#!/usr/bin/env python3
"""Receive one CDSE token and hand it to the detached M2-ORB-001 supervisor."""

from __future__ import annotations

import argparse
import getpass
import json
import sys

from m2_orbit_recovery_003_core import (
    DATA_ROOT,
    EXPECTED_SOURCE_ID,
    OrbitRecovery003Error,
    claim_owner_handoff,
    launch_detached_supervisor,
    read_single_use_secret,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stdin", action="store_true", help="Read one newline-terminated token from stdin.")
    args = parser.parse_args()
    secret = ""
    handoff_claimed = False
    try:
        secret = read_single_use_secret(sys.stdin.buffer) if args.stdin else getpass.getpass(
            "CDSE access token (hidden; paste once, then press Enter): "
        )
        handoff_id, _claim_path = claim_owner_handoff()
        handoff_claimed = True
        process_id = launch_detached_supervisor(secret, handoff_id=handoff_id)
        secret = ""
        print(json.dumps({
            "status": "secret_handed_to_detached_supervisor",
            "source_id": EXPECTED_SOURCE_ID,
            "handoff_id": handoff_id,
            "supervisor_process_id": process_id,
            "secret_transport": "anonymous_pipe_single_use_memory_only",
            "credential_value_recorded": False,
            "authority_consumed": True,
            "console_may_close": True,
        }, indent=2))
        return 0
    except OrbitRecovery003Error as exc:
        handoff_claimed = handoff_claimed or (DATA_ROOT / "derived/m2-orbit-recovery-003-handoff").exists()
        print(json.dumps({
            "status": "stopped",
            "code": exc.code,
            "credential_value_recorded": False,
            "owner_handoff_claimed": handoff_claimed,
            "authority_consumed": handoff_claimed,
        }, indent=2))
        return 12
    except BaseException:
        handoff_claimed = handoff_claimed or (DATA_ROOT / "derived/m2-orbit-recovery-003-handoff").exists()
        print(json.dumps({
            "status": "stopped",
            "code": "orbit_recovery_003_broker_unexpected_failure",
            "credential_value_recorded": False,
            "owner_handoff_claimed": handoff_claimed,
            "authority_consumed": handoff_claimed,
        }, indent=2))
        return 20
    finally:
        secret = ""


if __name__ == "__main__":
    raise SystemExit(main())
