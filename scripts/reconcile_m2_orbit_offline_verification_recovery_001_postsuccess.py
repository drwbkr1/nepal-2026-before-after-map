#!/usr/bin/env python3
"""Correct the one stale attempted-source projection after recovery-001 success."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MILESTONE_REF = "contracts/milestone-002.json"
TERMINAL_REF = "records/readiness/m2-orbit-offline-verification-recovery-001-terminal-reconciliation.json"
SNAPSHOT_REF = "records/readiness/m2-orbit-offline-verification-recovery-001-postsuccess-pre-reconciliation-snapshot.json"
OUTPUT_REF = "records/readiness/m2-orbit-offline-verification-recovery-001-postsuccess-control-reconciliation.json"
TERMINAL_SHA256 = "42df98bbe1680483d14aa29dedf55f3761bae4be45991a5a84fbb304b9232182"
SOURCE_IDS = ["M2-ORB-001", "M2-ORB-002", "M2-ORB-003", "M2-ORB-004"]


def load(ref: str) -> dict[str, Any]:
    value = json.loads((ROOT / ref).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {ref}")
    return value


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconciled-at-utc", required=True)
    args = parser.parse_args()
    if not args.reconciled_at_utc.endswith("Z") or (ROOT / OUTPUT_REF).exists():
        raise SystemExit("invalid reconciliation time or output collision")
    terminal = load(TERMINAL_REF)
    snapshot = load(SNAPSHOT_REF)
    milestone = load(MILESTONE_REF)
    matches = [unit for unit in milestone.get("units", []) if unit.get("id") == "M2-ORBIT-VERIFY"]
    if (
        sha256(TERMINAL_REF) != TERMINAL_SHA256
        or terminal.get("status") != "pass_four_exact_resorb_inputs_verified_no_application"
        or terminal.get("source_ids_in_exact_order") != SOURCE_IDS
        or terminal.get("bindings", {}).get("milestone_sha256_after") != sha256(MILESTONE_REF)
        or snapshot.get("reconciliation_id")
        != "NEPAL-M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-POSTSUCCESS-PRE"
        or snapshot.get("authority", {}).get("authorized_action_classes")
        != ["evidence_recording", "project_control", "update_project_records"]
        or len(matches) != 1
        or matches[0].get("status") != "complete"
        or matches[0].get("disposition") != "pass"
        or matches[0].get("gates", {}).get("attempted_source_ids") != ["M2-ORB-001"]
        or matches[0].get("gates", {}).get("durable_verification_receipt_source_ids") != SOURCE_IDS
        or matches[0].get("gates", {}).get("real_eof_read_count") != 4
        or matches[0].get("gates", {}).get("orbit_application_performed") is not False
    ):
        raise SystemExit("terminal evidence or exact stale projection differs")
    milestone_before = sha256(MILESTONE_REF)
    verify = matches[0]
    verify["gates"]["initial_indeterminate_attempted_source_ids"] = ["M2-ORB-001"]
    verify["gates"]["attempted_source_ids"] = SOURCE_IDS
    verify["gates"]["recovery_001_attempted_source_ids_in_exact_order"] = SOURCE_IDS
    temporary = (ROOT / MILESTONE_REF).with_name(".milestone-002.json.orbit-recovery-001-postsuccess.tmp")
    if temporary.exists():
        raise SystemExit("temporary output collision")
    with temporary.open("xb") as stream:
        stream.write(canonical(milestone))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, ROOT / MILESTONE_REF)
    receipt = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-POSTSUCCESS-CONTROL-RECONCILIATION",
        "reconciled_at_utc": args.reconciled_at_utc,
        "status": "pass_stale_attempted_source_projection_corrected",
        "bindings": {
            "terminal_reconciliation_ref": TERMINAL_REF,
            "terminal_reconciliation_sha256": TERMINAL_SHA256,
            "pre_reconciliation_snapshot_ref": SNAPSHOT_REF,
            "pre_reconciliation_snapshot_sha256": sha256(SNAPSHOT_REF),
            "milestone_sha256_before": milestone_before,
            "milestone_sha256_after": sha256(MILESTONE_REF),
        },
        "correction": {
            "surface_ref": MILESTONE_REF,
            "unit_id": "M2-ORBIT-VERIFY",
            "field": "gates.attempted_source_ids",
            "before": ["M2-ORB-001"],
            "after": SOURCE_IDS,
            "historical_first_indeterminate_attempt_preserved_as": "gates.initial_indeterminate_attempted_source_ids",
        },
        "assertions": {
            "terminal_receipt_mutated": False,
            "verification_receipt_mutated": False,
            "eof_content_read": False,
            "network_request_performed": False,
            "credential_value_read_or_recorded": False,
            "external_custody_mutated": False,
            "scientific_validation_rules_changed": False,
            "orbit_application_performed": False,
            "dem_or_radar_pixel_action_performed": False,
            "baseline_change_attribution_or_publication_performed": False,
        },
        "current_checkpoint": "M2-DEM-VERTICAL-DATUM-REVIEW",
    }
    with (ROOT / OUTPUT_REF).open("xb") as stream:
        stream.write(canonical(receipt))
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"status": receipt["status"], "output": OUTPUT_REF}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
