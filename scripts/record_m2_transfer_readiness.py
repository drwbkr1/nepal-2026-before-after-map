#!/usr/bin/env python3
"""Run local transfer-control tests and write a no-overwrite readiness receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_REF = "records/acquisition/transfer-runner-readiness.json"
EXTERNAL_ROOT = Path(r"C:\Projects\Active\nepal-2026-before-after-map-data")


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def load(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def write_new(relative: str, value: dict[str, Any]) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write((json.dumps(value, indent=2) + "\n").encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())


def product_file_count() -> int:
    return sum(
        1
        for path in EXTERNAL_ROOT.rglob("*")
        if path.is_file() and path.name != "custody-initialization-receipt.json"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verified-at-utc", required=True)
    args = parser.parse_args()
    if (ROOT / OUTPUT_REF).exists():
        raise SystemExit(f"readiness receipt already exists; refusing replacement: {OUTPUT_REF}")

    contract = load("contracts/milestone-002.json")
    intake = load("contracts/m2-intake.json")
    if contract.get("handoff", {}).get("current_checkpoint") != "M2-AUTHENTICATION-REFERENCE":
        raise SystemExit("active milestone is not at the authentication-reference checkpoint")
    if intake.get("extensions", {}).get("custody_initialized") is not True:
        raise SystemExit("controlled custody is not initialized")
    if not EXTERNAL_ROOT.is_dir():
        raise SystemExit("approved external root is missing")
    before_count = product_file_count()
    if before_count != 0:
        raise SystemExit("external custody already contains product or attempt files")

    environment = dict(os.environ)
    environment.pop("CDSE_ACCESS_TOKEN", None)
    command = [sys.executable, "-m", "unittest", "tests.test_m2_transfer_core", "-v"]
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    combined = result.stdout + result.stderr
    count_match = re.search(r"Ran (\d+) tests?", combined)
    if result.returncode != 0 or count_match is None:
        raise SystemExit("transfer-control test suite failed; no readiness receipt written")
    after_count = product_file_count()
    if after_count != before_count:
        raise SystemExit("local tests changed external custody; no readiness receipt written")

    receipt = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-TRANSFER-RUNNER-READINESS-001",
        "status": "pass_synthetic_only_no_authentication_or_product_transfer",
        "verified_at_utc": args.verified_at_utc,
        "bindings": {
            "active_contract_ref": "contracts/milestone-002.json",
            "active_contract_sha256": sha256("contracts/milestone-002.json"),
            "active_intake_ref": "contracts/m2-intake.json",
            "active_intake_sha256": sha256("contracts/m2-intake.json"),
            "activation_approval_ref": "records/source-gates/m2-activation-approval.json",
            "activation_approval_sha256": sha256("records/source-gates/m2-activation-approval.json"),
            "transfer_core_ref": "scripts/m2_transfer_core.py",
            "transfer_core_sha256": sha256("scripts/m2_transfer_core.py"),
            "transfer_runner_ref": "scripts/acquire_m2_product.py",
            "transfer_runner_sha256": sha256("scripts/acquire_m2_product.py"),
            "tests_ref": "tests/test_m2_transfer_core.py",
            "tests_sha256": sha256("tests/test_m2_transfer_core.py"),
        },
        "test": {
            "command": "python -m unittest tests.test_m2_transfer_core -v",
            "test_count": int(count_match.group(1)),
            "status": "pass",
            "covered_controls": [
                "missing credential reference stops before mutation",
                "exclusive staging and collision refusal",
                "streamed SHA-256 and provider-MD5 verification",
                "size and checksum failure retention",
                "atomic hard-link no-replace promotion",
                "destination collision preservation",
                "path-containment rejection",
                "redirect refusal",
                "receipt replacement refusal",
                "terminal failed-attempt preservation",
            ],
        },
        "external_state": {
            "root": str(EXTERNAL_ROOT),
            "product_or_attempt_file_count_before": before_count,
            "product_or_attempt_file_count_after": after_count,
        },
        "activity": {
            "network_requests_performed": False,
            "authentication_performed": False,
            "credential_values_read_or_recorded": False,
            "product_bytes_transferred": 0,
            "active_intake_mutated": False,
        },
        "limitations": [
            "Local fixture tests do not prove the current CDSE authenticated response, content length, redirect behavior, or transfer performance.",
            "A real attempt must revalidate unchanged official pages and the exact product catalogue record before writing an append-only started event.",
            "A promoted archive still requires the separate offline ZIP, SAFE, band, polarization, and CRC checks before pixel use.",
        ],
        "next_gate": "Provide a secret-safe reference to an existing owner-controlled CDSE access token or authenticated session; do not place credential values in Git, chat, receipts, URLs, or captured output.",
    }
    write_new(OUTPUT_REF, receipt)
    print(json.dumps({
        "status": receipt["status"],
        "receipt": OUTPUT_REF,
        "test_count": receipt["test"]["test_count"],
        "external_product_or_attempt_files": after_count,
    }, indent=2))


if __name__ == "__main__":
    main()
