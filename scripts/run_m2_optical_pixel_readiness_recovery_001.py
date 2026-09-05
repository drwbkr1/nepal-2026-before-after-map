#!/usr/bin/env python3
"""Run the one separately authorized optical pixel recovery-001 attempt."""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
from pathlib import Path
from typing import Any

import run_m2_optical_pixel_readiness_001 as original
from m2_optical_pixel_recovery_stage_gate import CONTRACT_REF, ROOT, validate_recovery_stage_execution
from optical_pixel_recovery_core_001 import normalize_analysis_grid, validate_recovery_contract


UTC_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


def load_path(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return value


def normalized_execution_contract(contract: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(contract)
    normalized["analysis_grid"] = normalize_analysis_grid(contract["analysis_grid"])
    return normalized


def execute_recovery(contract: dict[str, Any], started_at: str, attempt_root: Path) -> dict[str, Any]:
    receipt = original.execute(normalized_execution_contract(contract), started_at, attempt_root)
    receipt["receipt_id"] = "NEPAL-S2-PIXEL-READINESS-RECOVERY-001"
    receipt["bindings"] = {
        "contract_ref": CONTRACT_REF,
        "contract_sha256": original.sha256_file(ROOT / CONTRACT_REF),
        "source_scientific_contract_ref": contract["source_scientific_contract"]["ref"],
        "source_scientific_contract_sha256": contract["source_scientific_contract"]["sha256"],
        "recovery_approval_ref": contract["recovery_authority"]["approval_ref"],
        "recovery_approval_sha256": contract["recovery_authority"]["approval_sha256"],
    }
    receipt["operational_correction"] = {
        "analysis_grid_extent_normalized": True,
        "scientific_thresholds_changed": False,
        "source_pair_or_aois_changed": False,
        "real_001_reused_or_retried": False,
    }
    receipt["next_gate"] = "reconcile this terminal QA-only recovery result; do not retry or begin baseline, change, interpretation, attribution, or publication"
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--started-at-utc", required=True)
    parser.add_argument("--receipt-output", required=True)
    args = parser.parse_args()
    if not args.execute:
        raise SystemExit("refusing without --execute")
    if not UTC_TIMESTAMP.fullmatch(args.started_at_utc):
        raise SystemExit("invalid started timestamp")
    validate_recovery_stage_execution()
    contract = load_path(ROOT / CONTRACT_REF)
    original_contract = load_path(ROOT / contract["source_scientific_contract"]["ref"])
    errors = validate_recovery_contract(contract, original_contract)
    if errors:
        raise SystemExit("invalid optical pixel recovery contract: " + "; ".join(errors))
    attempt = contract["attempt"]
    if args.attempt_id != attempt["attempt_id"] or args.receipt_output != attempt["public_receipt_ref"]:
        raise SystemExit("exact optical pixel recovery identity differs")
    attempt_root = Path(attempt["external_attempt_root"])
    receipt_path = ROOT / args.receipt_output
    if attempt_root.exists() or receipt_path.exists():
        raise SystemExit("refusing optical pixel recovery collision")
    original_root = Path(contract["retained_real_001"]["external_attempt_root"])
    if not original_root.is_dir():
        raise SystemExit("retained real-001 attempt root is missing")
    os.environ.setdefault("GDAL_PAM_ENABLED", "NO")
    attempt_root.mkdir(parents=True, exist_ok=False)
    original.write_new_json(
        attempt_root / "started.json",
        {
            "status": "started",
            "attempt_id": args.attempt_id,
            "started_at_utc": args.started_at_utc,
            "contract_sha256": original.sha256_file(ROOT / CONTRACT_REF),
        },
    )
    try:
        receipt = execute_recovery(contract, args.started_at_utc, attempt_root)
    except Exception as exc:
        failure = {
            "status": "invalid",
            "attempt_id": args.attempt_id,
            "started_at_utc": args.started_at_utc,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "automatic_retry_authorized": False,
        }
        original.write_new_json(attempt_root / "failure.json", failure)
        original.write_new_json(
            receipt_path,
            {
                **failure,
                "receipt_id": "NEPAL-S2-PIXEL-READINESS-RECOVERY-001",
                "activity": {"real_product_pixel_access_attempted": True},
                "operational_correction": {
                    "analysis_grid_extent_normalized": True,
                    "scientific_thresholds_changed": False,
                    "source_pair_or_aois_changed": False,
                    "real_001_reused_or_retried": False,
                },
                "next_gate": "retain terminal recovery failure; no automatic retry or downstream science is authorized",
            },
        )
        print(json.dumps({"status": "invalid", "receipt": args.receipt_output, "error_type": type(exc).__name__}, indent=2))
        return 20
    original.write_new_json(receipt_path, receipt)
    print(json.dumps({"status": receipt["status"], "receipt": args.receipt_output}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
