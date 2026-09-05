#!/usr/bin/env python3
"""Create the one-attempt recovery contract from the immutable real-001 contract."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "config/qa/optical-pixel-readiness-contract-recovery-001.json"
ORIGINAL_REF = "config/qa/optical-pixel-readiness-contract-001.json"
APPROVAL_REF = "records/source-gates/m2-optical-pixel-recovery-001-approval.json"
REAL_001_RECEIPT_REF = "records/readiness/optical-pixel/m2-s2-pixel-readiness-real-001.json"
REAL_001_RECONCILIATION_REF = "records/readiness/m2-optical-pixel-real-001-reconciliation.json"
IMPLEMENTATION = {
    "core": "scripts/optical_pixel_recovery_core_001.py",
    "runner": "scripts/run_m2_optical_pixel_readiness_recovery_001.py",
    "stage_gate": "scripts/m2_optical_pixel_recovery_stage_gate.py",
    "final_preflight": "scripts/preflight_m2_optical_pixel_recovery_001.py",
    "publication_gate_recorder": "scripts/record_m2_optical_pixel_recovery_001_publication_gate.py",
    "arcgis_adapter": "scripts/validate_optical_pixel_recovery_001_arcgis.py",
    "portable_tests": "tests/test_m2_optical_pixel_recovery_001.py",
    "reconciler": "scripts/reconcile_m2_optical_pixel_recovery_001.py",
}


def load(relative: str) -> dict:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {relative}")
    return value


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--created-at-utc", required=True)
    args = parser.parse_args()
    if OUTPUT.exists():
        raise SystemExit("refusing recovery contract collision")
    original = load(ORIGINAL_REF)
    approval = load(APPROVAL_REF)
    if approval.get("status") != "approved_exact_post_observation_operational_correction_and_one_recovery":
        raise SystemExit("recovery approval differs")
    implementation = {}
    for key, ref in IMPLEMENTATION.items():
        implementation[f"{key}_ref"] = ref
        implementation[f"{key}_sha256"] = sha256(ref)
    contract = {
        "schema_version": "1.0",
        "contract_id": "NEPAL-S2-PIXEL-READINESS-RECOVERY-001",
        "created_at_utc": args.created_at_utc,
        "status": "active_post_observation_operational_correction_one_attempt",
        "recovery_authority": {
            "approval_ref": APPROVAL_REF,
            "approval_sha256": sha256(APPROVAL_REF),
            "maximum_real_invocations": 1,
            "automatic_retry_authorized": False,
            "this_contract_creates_authority": False,
        },
        "source_scientific_contract": {
            "ref": ORIGINAL_REF,
            "sha256": sha256(ORIGINAL_REF),
            "status": "unchanged_and_retained_for_real_001",
        },
        "retained_real_001": {
            "receipt_ref": REAL_001_RECEIPT_REF,
            "receipt_sha256": sha256(REAL_001_RECEIPT_REF),
            "reconciliation_ref": REAL_001_RECONCILIATION_REF,
            "reconciliation_sha256": sha256(REAL_001_RECONCILIATION_REF),
            "external_attempt_root": original["attempt"]["external_attempt_root"],
            "status": "terminal_invalid_no_retry",
        },
        "inputs": copy.deepcopy(original["inputs"]),
        "implementation": implementation,
        "operational_correction": {
            "only_change": "normalize existing analysis_grid.extent bounds for the unchanged executor",
            "input_shape": "analysis_grid retains its exact nested extent object",
            "execution_view": "a deep copy exposes xmin ymin xmax ymax from the nested extent",
            "threshold_changes": False,
            "source_or_aoi_changes": False,
            "mask_or_registration_changes": False,
            "real_001_reclassification": False,
        },
        "exact_pair": copy.deepcopy(original["exact_pair"]),
        "approved_aoi_ids": copy.deepcopy(original["approved_aoi_ids"]),
        "products": copy.deepcopy(original["products"]),
        "analysis_grid": copy.deepcopy(original["analysis_grid"]),
        "mask": copy.deepcopy(original["mask"]),
        "registration": copy.deepcopy(original["registration"]),
        "attempt": {
            "attempt_id": "optical-pixel-readiness-recovery-001",
            "maximum_real_invocations": 1,
            "automatic_retry_authorized": False,
            "external_attempt_root": r"C:\Projects\Active\nepal-2026-before-after-map-data\derived\optical-pixel-readiness-recovery-001",
            "public_receipt_ref": "records/readiness/optical-pixel/m2-s2-pixel-readiness-recovery-001.json",
            "minimum_free_space_bytes": original["attempt"]["minimum_free_space_bytes"],
            "collision_policy": "fail",
        },
        "execution_boundary": copy.deepcopy(original["execution_boundary"]),
        "decision_domain": copy.deepcopy(original["decision_domain"]),
        "claim_boundary": copy.deepcopy(original["claim_boundary"]),
        "limitations": [
            *copy.deepcopy(original["limitations"]),
            "This is a post-observation operational correction; real-001 remains terminal INVALID and is not reclassified, reused, resumed, or retried.",
            "Recovery-001 is the only new real invocation and has no automatic retry authority.",
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(contract, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"status": "created_exact_recovery_contract", "output": OUTPUT.relative_to(ROOT).as_posix(), "sha256": sha256(OUTPUT.relative_to(ROOT).as_posix())}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
