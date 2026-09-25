#!/usr/bin/env python3
"""Receive one owner token through stdin and detach the exact pilot supervisor."""

from __future__ import annotations

import json
import sys

from m2_optical_pair_pilot_001_core import CONTRACT_REF, EXECUTION_GATE_REF, PilotControlError, load_contract, read_owner_pipe_secret, sha256_file, validate_implementation_manifest
from m2_optical_pair_pilot_001_offline import PILOT_ROOT
from m2_optical_pair_pilot_001_supervisor import PUBLIC_TERMINAL, ROOT
from m2_optical_pair_pilot_001_transfer import read_json
from m2_sentinel_continuation_001_core import (
    launch_detached_supervisor,
)


def validate_broker_release() -> None:
    contract = load_contract()
    if contract.get("status") != "conditional_public_ci_and_final_preflight_pending":
        raise PilotControlError("pilot_contract_not_activated")
    gate_path = ROOT / EXECUTION_GATE_REF
    if not gate_path.is_file():
        raise PilotControlError("pilot_execution_gate_missing")
    gate = read_json(gate_path)
    if (
        gate.get("status") != "pass_public_execution_gate"
        or gate.get("public_ci_conclusion") != "success"
        or gate.get("contract_sha256") != sha256_file(ROOT / CONTRACT_REF)
        or gate.get("implementation_readiness_sha256") != validate_implementation_manifest()
    ):
        raise PilotControlError("pilot_execution_gate_not_passing")
    if PUBLIC_TERMINAL.exists() or (PILOT_ROOT / "supervisor").exists():
        raise PilotControlError("pilot_supervisor_attempt_consumed")


def main() -> int:
    try:
        validate_broker_release()
        secret = read_owner_pipe_secret(sys.stdin.buffer)
        command = [sys.executable, str(ROOT / "scripts/m2_optical_pair_pilot_001_supervisor.py")]
        process_id = launch_detached_supervisor(secret, command=command)
        secret = ""
        print(json.dumps({
            "status": "secret_handed_to_detached_optical_pilot_supervisor",
            "supervisor_process_id": process_id,
            "source_ids_in_order": ["M2-OPT-001", "M2-OPT-002"],
            "credential_value_recorded": False,
            "secret_transport": "anonymous_pipe_single_use_memory_only",
            "console_may_close": True,
        }, indent=2))
        return 0
    except BaseException:
        print(json.dumps({
            "status": "stopped", "code": "pilot_broker_release_or_handoff_failed",
            "credential_value_recorded": False,
        }, indent=2))
        return 12


if __name__ == "__main__":
    raise SystemExit(main())
