#!/usr/bin/env python3
"""Record verified M2 custody initialization and the authentication boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REF = "contracts/milestone-002.json"
INTAKE_REF = "contracts/m2-intake.json"
RECEIPT_REF = "records/acquisition/custody-initialization.json"
PROFILE_REF = "records/project-control-profile.json"
GOAL_REF = "records/long-term-goal.json"


def load(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def serialized(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2) + "\n").encode("utf-8")


def replace(relative: str, value: dict[str, Any]) -> None:
    path = ROOT / relative
    temporary = path.with_name(path.name + ".custody-checkpoint-tmp")
    if temporary.exists():
        raise SystemExit(f"temporary update path already exists: {temporary}")
    with temporary.open("xb") as handle:
        handle.write(serialized(value))
        handle.flush()
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recorded-at-utc", required=True)
    args = parser.parse_args()

    contract = load(CONTRACT_REF)
    intake = load(INTAKE_REF)
    receipt = load(RECEIPT_REF)
    profile = load(PROFILE_REF)
    goal = load(GOAL_REF)
    if receipt.get("status") != "created_and_verified":
        raise SystemExit("custody initialization receipt is not passing")
    if intake.get("extensions", {}).get("custody_initialization_sha256") != sha256(RECEIPT_REF):
        raise SystemExit("active intake does not bind the custody receipt")
    if intake.get("extensions", {}).get("custody_initialized") is not True:
        raise SystemExit("active intake does not record initialized custody")
    units = {unit["id"]: unit for unit in contract["units"]}
    acquire = units["M2-ACQUIRE"]
    if units["M2-CUSTODY-PREFLIGHT"].get("disposition") != "pass" or acquire.get("status") != "ready":
        raise SystemExit("M2 contract differs from the expected custody checkpoint")
    if acquire.get("gates", {}).get("custody_initialization") != "pending":
        raise SystemExit("custody initialization was already recorded")

    acquire["gates"].update({
        "custody_initialization": "pass",
        "custody_initialization_ref": RECEIPT_REF,
        "custody_initialization_sha256": sha256(RECEIPT_REF),
        "authentication": "waiting_for_secret_safe_existing_owner_credential_reference",
    })
    acquire["outputs"] = [
        "external custody products",
        "records/acquisition/product receipts",
        RECEIPT_REF,
    ]
    acquire["exit_condition_delta"]["rationale"] = (
        "The approved empty custody structure is verified. No product transfer can begin until a secret-safe reference "
        "to an existing owner-controlled CDSE credential or authenticated session is available."
    )
    next_action = (
        "Provide a secret-safe reference to an existing owner-controlled CDSE access token or authenticated session; "
        "then revalidate the exact first product before transfer. Do not place a token, password, cookie, or header in Git or chat."
    )
    contract["handoff"].update({
        "current_checkpoint": "M2-AUTHENTICATION-REFERENCE",
        "next_action": next_action,
    })
    profile["current_checkpoint"].update({
        "checkpoint_id": "M2-AUTHENTICATION-REFERENCE",
        "expected_head": None,
        "next_action": next_action,
    })
    goal["current_checkpoint"] = "M2-AUTHENTICATION-REFERENCE"

    replace(CONTRACT_REF, contract)
    replace(PROFILE_REF, profile)
    replace(GOAL_REF, goal)
    print(json.dumps({
        "status": "custody_checkpoint_recorded",
        "recorded_at_utc": args.recorded_at_utc,
        "custody_receipt_sha256": sha256(RECEIPT_REF),
        "checkpoint": "M2-AUTHENTICATION-REFERENCE",
        "files_downloaded": 0,
    }, indent=2))


if __name__ == "__main__":
    main()
