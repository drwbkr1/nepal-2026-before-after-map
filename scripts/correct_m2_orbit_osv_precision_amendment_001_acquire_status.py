#!/usr/bin/env python3
"""Correct the omitted approved OSV status on the orbit-acquisition gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "contracts/milestone-002.json"
PRIOR_CORRECTION = ROOT / "records/readiness/m2-orbit-osv-precision-amendment-001-implementation-control-projection-correction-001.json"
OUTPUT = ROOT / "records/readiness/m2-orbit-osv-precision-amendment-001-implementation-control-projection-correction-002.json"
OLD_STATUS = "proposed_not_authorized_publication_pending"
NEW_STATUS = "approved_exact_one_second_implementation_public_ci_pending"


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace(path: Path, value: dict) -> None:
    temporary = path.with_name(f".{path.name}.osv-acquire-status-correction.tmp")
    if temporary.exists():
        raise ValueError(f"temporary collision: {temporary}")
    with temporary.open("xb") as stream:
        stream.write((json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def unit(milestone: dict, unit_id: str) -> dict:
    matches = [item for item in milestone.get("units", []) if item.get("id") == unit_id]
    if len(matches) != 1:
        raise ValueError(f"milestone unit missing or ambiguous: {unit_id}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corrected-at-utc", required=True)
    args = parser.parse_args()
    if OUTPUT.exists() or not args.corrected_at_utc.endswith("Z"):
        raise SystemExit("correction output collision or invalid time")
    prior = load(PRIOR_CORRECTION)
    milestone = load(MILESTONE)
    acquire = unit(milestone, "M2-ORBIT-ACQUIRE")
    gates = acquire.get("gates", {})
    if (
        prior.get("status") != "pass_missing_active_amendment_projections_added_without_scope_change"
        or prior.get("bindings", {}).get("milestone_sha256_after") != sha256(MILESTONE)
        or gates.get("retained_failure_review") != NEW_STATUS
        or gates.get("osv_precision_amendment_status") != OLD_STATUS
    ):
        raise SystemExit("current milestone does not match the bounded omitted-status condition")
    before = sha256(MILESTONE)
    gates["osv_precision_amendment_status"] = NEW_STATUS
    replace(MILESTONE, milestone)
    receipt = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ORBIT-OSV-PRECISION-AMENDMENT-001-IMPLEMENTATION-CONTROL-PROJECTION-CORRECTION-002",
        "corrected_at_utc": args.corrected_at_utc,
        "status": "pass_omitted_orbit_acquire_amendment_status_corrected",
        "bindings": {
            "prior_correction_sha256": sha256(PRIOR_CORRECTION),
            "milestone_sha256_before": before,
            "milestone_sha256_after": sha256(MILESTONE),
        },
        "correction": {
            "unit_id": "M2-ORBIT-ACQUIRE",
            "field": "gates.osv_precision_amendment_status",
            "old_value": OLD_STATUS,
            "new_value": NEW_STATUS,
        },
        "assertions": {
            "authority_broadened": False,
            "approval_or_reconciliation_mutated": False,
            "real_staged_file_read": False,
            "network_requests_performed": False,
            "external_data_mutated": False,
            "local_validation_started": False,
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(receipt, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"status": receipt["status"], "output": str(OUTPUT.relative_to(ROOT)).replace("\\", "/")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
