#!/usr/bin/env python3
"""Record the terminal outcome of the one approved orbit recovery-002 attempt."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from m2_orbit_recovery_002_core import (
    ACTIVE_INTAKE_REF,
    EXPECTED_ATTEMPT_PREFIX,
    EXPECTED_SOURCE_ID,
    ORIGINAL_ATTEMPT_ID,
    ROOT,
    load_object,
    now_utc,
    require_original_failure,
    sha256_file,
    write_new_json,
)


OUTPUT = ROOT / "records/acquisition/m2-orbit-recovery-002-outcome-reconciliation.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verification-receipt", type=Path)
    args = parser.parse_args()
    if OUTPUT.exists():
        raise SystemExit("refusing outcome-reconciliation output collision")
    intake_path = ROOT / ACTIVE_INTAKE_REF
    intake = load_object(intake_path)
    assets = [item for item in intake.get("assets", []) if item.get("extensions", {}).get("source_id") == EXPECTED_SOURCE_ID]
    if len(assets) != 1:
        raise SystemExit("M2-ORB-001 asset absent or ambiguous")
    asset = assets[0]
    attempts = asset.get("attempts", [])
    if len(attempts) != 2 or attempts[0].get("attempt_id") != ORIGINAL_ATTEMPT_ID or attempts[0].get("outcome") != "failed":
        raise SystemExit("retained failed attempt history differs")
    recovery = attempts[1]
    if not str(recovery.get("attempt_id", "")).startswith(EXPECTED_ATTEMPT_PREFIX + "-") or recovery.get("outcome") not in {"succeeded", "failed"}:
        raise SystemExit("recovery attempt is not terminal or has the wrong identity")
    receipt_ref = asset.get("extensions", {}).get("successful_attempt_receipt") if recovery["outcome"] == "succeeded" else f"records/acquisition/orbit-attempts/{recovery['attempt_id']}.json"
    receipt_path = ROOT / str(receipt_ref)
    if not receipt_path.is_file():
        raise SystemExit("terminal transfer receipt missing")
    verification = None
    if recovery["outcome"] == "succeeded":
        if args.verification_receipt is None:
            raise SystemExit("passing offline verification receipt required after a recovery success")
        verification_path = args.verification_receipt if args.verification_receipt.is_absolute() else ROOT / args.verification_receipt
        verification = load_object(verification_path)
        if verification.get("status") != "pass_orbit_input_only" or verification.get("source_id") != EXPECTED_SOURCE_ID:
            raise SystemExit("offline verification receipt does not pass for M2-ORB-001")
    payload = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-RECOVERY-002-OUTCOME-RECONCILIATION-001",
        "recorded_at_utc": now_utc(),
        "status": "pass_recovery_and_offline_verification_only" if verification else "terminal_failure_preserved_no_retry",
        "source_id": EXPECTED_SOURCE_ID,
        "attempt_id": recovery["attempt_id"],
        "outcome": recovery["outcome"],
        "bindings": {
            "active_intake_sha256": sha256_file(intake_path),
            "terminal_receipt_ref": str(receipt_path.relative_to(ROOT)).replace("\\", "/"),
            "terminal_receipt_sha256": sha256_file(receipt_path),
            "offline_verification_ref": str(args.verification_receipt).replace("\\", "/") if verification else None,
            "offline_verification_sha256": sha256_file(verification_path) if verification else None,
        },
        "assertions": {
            "original_failed_attempt_preserved": True,
            "recovery_attempt_count": 1,
            "automatic_retry_performed": False,
            "other_orbit_source_requested": False,
            "credential_value_recorded": False,
            "orbit_application_performed": False,
            "dem_or_radar_pixels_processed": False,
            "baseline_or_change_analysis_performed": False,
            "scientific_result_established": False,
        },
        "next_gate": "separate owner review before any M2-ORB-002 through M2-ORB-004 request" if verification else "new explicit review required; do not retry",
    }
    write_new_json(OUTPUT, payload)
    print(json.dumps({"status": payload["status"], "output": str(OUTPUT.relative_to(ROOT)).replace("\\", "/")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
