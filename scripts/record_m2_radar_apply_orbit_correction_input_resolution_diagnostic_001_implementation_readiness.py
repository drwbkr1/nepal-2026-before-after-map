#!/usr/bin/env python3
"""Seal the read-only diagnostic implementation before public CI."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from m2_radar_apply_orbit_correction_input_resolution_diagnostic_001_core import (
    ATTEMPT_ID,
    canonical_bytes,
    sha256_file,
    write_new_json,
)


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-apply-orbit-correction-input-resolution-diagnostic-001"
OUTPUT_REF = f"records/readiness/{PREFIX}-implementation-readiness.json"
ARTIFACTS = [
    f"reviews/{PREFIX}/response-c4f0ffdaaa43ebb0acef3b35e15dd5e7ea183f6ec4ac29da587b31c5ff51387f.json",
    f"reviews/{PREFIX}/review-contract-lock-001.json",
    f"records/source-gates/{PREFIX}-review-reconciliation.json",
    f"records/source-gates/{PREFIX}-approval.json",
    f"records/readiness/{PREFIX}-approval-activation.json",
    f"config/qa/{PREFIX}-contract.json",
    f"scripts/activate_{PREFIX.replace('-', '_')}.py",
    f"scripts/{PREFIX.replace('-', '_')}_core.py",
    f"scripts/run_{PREFIX.replace('-', '_')}.py",
    f"scripts/record_{PREFIX.replace('-', '_')}_implementation_readiness.py",
    f"scripts/record_{PREFIX.replace('-', '_')}_implementation_publication.py",
    f"scripts/record_{PREFIX.replace('-', '_')}_gate_state_publication.py",
    f"scripts/reconcile_{PREFIX.replace('-', '_')}.py",
    f"tests/test_{PREFIX.replace('-', '_')}.py",
]


def load(ref: str) -> dict[str, Any]:
    return json.loads((ROOT / ref).read_text(encoding="utf-8"))


def replace_json(ref: str, value: object, nonce: str) -> None:
    path = ROOT / ref
    temporary = path.with_name(f".{path.name}.{nonce}.tmp")
    with temporary.open("xb") as stream:
        stream.write(canonical_bytes(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recorded-at-utc", required=True)
    parser.add_argument("--focused-test-count", type=int, required=True)
    parser.add_argument("--full-test-count", type=int, required=True)
    parser.add_argument("--full-skip-count", type=int, required=True)
    parser.add_argument("--required-file-count", type=int, required=True)
    args = parser.parse_args()
    if not args.recorded_at_utc.endswith("Z"):
        raise SystemExit("--recorded-at-utc must be UTC")
    if (ROOT / OUTPUT_REF).exists():
        raise SystemExit("implementation-readiness output collision")
    missing = [ref for ref in ARTIFACTS if not (ROOT / ref).is_file()]
    if missing:
        raise SystemExit("missing implementation artifact: " + ", ".join(missing))
    forbidden = [
        f"records/readiness/{PREFIX}-implementation-publication-gate.json",
        f"records/readiness/{PREFIX}-gate-state-publication.json",
        f"records/readiness/{PREFIX}-final-preflight.json",
        f"records/processing/{PREFIX}-terminal.json",
        f"records/processing/{PREFIX}-cleanup.json",
    ]
    collisions = [ref for ref in forbidden if (ROOT / ref).exists()]
    if collisions:
        raise SystemExit("later-stage diagnostic artifact already exists: " + ", ".join(collisions))

    record = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-IMPLEMENTATION-READINESS",
        "recorded_at_utc": args.recorded_at_utc,
        "status": "pass_read_only_diagnostic_implementation_public_ci_pending",
        "bindings": {ref: sha256_file(ROOT / ref) for ref in ARTIFACTS},
        "implementation": {
            "diagnostic_id": ATTEMPT_ID,
            "maximum_processes": 1,
            "terminal_and_cleanup_reserved_before_external_content_access": True,
            "exact_input_paths_contract_bound": True,
            "allowed_arcpy_calls_only": ["GetInstallInfo", "ProductInfo", "CheckExtension", "Usage", "Exists", "Describe"],
            "apply_orbit_correction_calls": 0,
            "geoprocessing_calls": 0,
            "automatic_retry_authorized": False,
            "missing_input_stops_without_reconstruction": True,
        },
        "validation": {
            "focused_test_count": args.focused_test_count,
            "full_repository_test_count": args.full_test_count,
            "full_repository_intentional_skip_count": args.full_skip_count,
            "repository_checker_status": f"pass_{args.required_file_count}_required_files",
            "exact_contract_and_path_containment_checked": True,
            "receipt_reservation_and_persistence_checked": True,
            "synthetic_success_and_missing_input_checked": True,
            "read_only_arcpy_allowlist_checked": True,
            "no_network_copy_or_processing_call_checked": True,
            "secret_and_path_redaction_checked": True,
        },
        "released_now": {
            "public_ci": True,
            "gate_state_publication": False,
            "final_no_content_preflight": False,
            "diagnostic_process": False,
            "arcpy_invocation": False,
            "project_data_or_external_custody_access": False,
        },
        "assertions": {
            "arcpy_imported": False,
            "diagnostic_process_started": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "apply_orbit_correction_invoked": False,
            "geoprocessing_invoked": False,
            "source_orbit_or_dem_copied": False,
            "source_orbit_or_dem_mutated": False,
            "attempt_root_reconstructed_or_substituted": False,
            "new_radar_attempt_created": False,
            "historical_root_cause_established": False,
            "radar_recovery_readiness_established": False,
            "scientific_result_established": False,
        },
        "next_action": "Publish the exact implementation and require successful public default-branch CI before gate-state publication, final preflight, ArcPy import, or external input access.",
    }
    write_new_json(ROOT / OUTPUT_REF, record)

    milestone = load("contracts/milestone-002.json")
    units = {item.get("id"): item for item in milestone.get("units", []) if isinstance(item, dict)}
    implementation = units.get("M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-IMPLEMENTATION", {})
    if implementation.get("status") != "in_progress" or implementation.get("gates", {}).get("public_ci") != "pending":
        raise SystemExit("implementation unit is not at pre-publication state")
    implementation["gates"].update({
        "synthetic_no_content_tests": "success",
        "repository_validation": "success",
        "focused_test_count": args.focused_test_count,
        "full_test_count": args.full_test_count,
        "full_skip_count": args.full_skip_count,
        "required_file_count": args.required_file_count,
        "implementation_readiness_sha256": sha256_file(ROOT / OUTPUT_REF),
    })
    implementation["outputs"].append(OUTPUT_REF)
    implementation["exit_condition_delta"] = {
        "expected": ["successful public default-branch CI"],
        "observed": ["portable synthetic validation passed without ArcPy import or external input access"],
        "decision_value": "pending_public_ci",
        "rationale": "The final preflight and one diagnostic process remain blocked behind two exact public CI gates.",
    }
    replace_json("contracts/milestone-002.json", milestone, "input-resolution-diagnostic-readiness")

    evidence = {
        "record_id": "EVID-0191",
        "type": "m2_radar_apply_orbit_correction_input_resolution_diagnostic_001_implementation_readiness",
        "verified_at_utc": args.recorded_at_utc,
        "status": record["status"],
        "claim": "The approved read-only diagnostic implementation passed synthetic and repository validation without importing ArcPy or accessing project data or external custody. Public CI remains required.",
        "approval_ref": f"records/source-gates/{PREFIX}-approval.json",
        "approval_sha256": sha256_file(ROOT / f"records/source-gates/{PREFIX}-approval.json"),
        "implementation_readiness_ref": OUTPUT_REF,
        "implementation_readiness_sha256": sha256_file(ROOT / OUTPUT_REF),
        "assertions": {
            "focused_test_count": args.focused_test_count,
            "full_test_count": args.full_test_count,
            "full_skip_count": args.full_skip_count,
            "required_file_count": args.required_file_count,
            "public_ci_pending": True,
            "arcpy_imported": False,
            "diagnostic_process_started": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "apply_orbit_correction_invoked": False,
            "geoprocessing_invoked": False,
            "scientific_result_established": False,
            "current_checkpoint": "M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-IMPLEMENTATION",
        },
        "next_action": record["next_action"],
    }
    with (ROOT / "records/evidence-ledger.jsonl").open("ab", buffering=0) as stream:
        stream.write(json.dumps(evidence, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n")
        os.fsync(stream.fileno())
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
