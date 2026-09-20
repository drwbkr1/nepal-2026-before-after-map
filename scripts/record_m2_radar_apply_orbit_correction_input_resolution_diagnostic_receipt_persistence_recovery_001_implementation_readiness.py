#!/usr/bin/env python3
"""Seal the diagnostic receipt-durability recovery before public CI."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from m2_radar_apply_orbit_correction_input_resolution_diagnostic_receipt_persistence_recovery_001_core import (
    ATTEMPT_ID,
    canonical_bytes,
    sha256_file,
    write_new_json,
)


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-apply-orbit-correction-input-resolution-diagnostic-receipt-persistence-recovery-001"
OUTPUT_REF = f"records/readiness/{PREFIX}-implementation-readiness.json"
ARTIFACTS = [
    f"reviews/{PREFIX}/response-c88b4ee8401b5b3b23acd1ebcfa9ae23e40ec7be737de076f89606c5567576f4.json",
    f"reviews/{PREFIX}/review-contract-lock-001.json",
    f"records/source-gates/{PREFIX}-review-reconciliation.json",
    f"records/source-gates/{PREFIX}-approval.json",
    f"records/readiness/{PREFIX}-approval-activation.json",
    f"config/qa/{PREFIX}-contract.json",
    f"scripts/activate_{PREFIX.replace('-', '_')}.py",
    f"scripts/{PREFIX.replace('-', '_')}_core.py",
    f"scripts/run_{PREFIX.replace('-', '_')}.py",
    f"scripts/validate_{PREFIX.replace('-', '_')}_arcgis.py",
    f"scripts/record_{PREFIX.replace('-', '_')}_implementation_readiness.py",
    f"scripts/record_{PREFIX.replace('-', '_')}_implementation_publication.py",
    f"scripts/record_{PREFIX.replace('-', '_')}_gate_state_publication.py",
    f"scripts/reconcile_{PREFIX.replace('-', '_')}.py",
    f"tests/test_{PREFIX.replace('-', '_')}.py",
    f"records/readiness/{PREFIX}-arcgis-runtime-validation-failure-001.json",
    f"records/readiness/{PREFIX}-arcgis-runtime-validation.json",
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
    for ref in (
        f"records/readiness/{PREFIX}-implementation-publication-gate.json",
        f"records/readiness/{PREFIX}-implementation-publication-reconciliation.json",
        f"records/readiness/{PREFIX}-gate-state-publication.json",
        f"records/readiness/{PREFIX}-final-preflight.json",
        f"records/processing/{PREFIX}-terminal.json",
        f"records/processing/{PREFIX}-cleanup.json",
        f"records/processing/{PREFIX}-fallback.jsonl",
    ):
        if (ROOT / ref).exists():
            raise SystemExit(f"later-stage artifact already exists: {ref}")
    runtime = load(f"records/readiness/{PREFIX}-arcgis-runtime-validation.json")
    if runtime.get("status") != "pass_installed_arcgis_runtime_disposable_read_only_receipt_recovery":
        raise SystemExit("installed ArcGIS runtime validation is not an exact pass")
    failure = load(f"records/readiness/{PREFIX}-arcgis-runtime-validation-failure-001.json")
    if failure.get("status") != "terminal_failed_synthetic_validation_receipt_self_hash_path_typo":
        raise SystemExit("preserved synthetic validation failure differs")

    record = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-IMPLEMENTATION-READINESS",
        "recorded_at_utc": args.recorded_at_utc,
        "status": "pass_receipt_durability_implementation_public_ci_pending",
        "bindings": {ref: sha256_file(ROOT / ref) for ref in ARTIFACTS},
        "implementation": {
            "attempt_id": ATTEMPT_ID,
            "maximum_processes": 1,
            "function_local_datetime_imports": True,
            "terminal_cleanup_and_fallback_reserved_before_external_reads": True,
            "original_failure_recorded_before_terminal_assembly": True,
            "later_persistence_failure_cannot_replace_original": True,
            "cleanup_independent_of_terminal_serialization": True,
            "consumed_zero_byte_receipts_immutable": True,
            "automatic_retry_authorized": False,
            "apply_orbit_correction_calls": 0,
            "geoprocessing_calls": 0,
        },
        "validation": {
            "focused_test_count": args.focused_test_count,
            "full_repository_test_count": args.full_test_count,
            "full_repository_intentional_skip_count": args.full_skip_count,
            "repository_checker_status": f"pass_{args.required_file_count}_required_files",
            "installed_arcgis_runtime_test_count": 1,
            "installed_arcgis_runtime_test_failures": 0,
            "preserved_prepass_runtime_validation_failures": 1,
            "datetime_rebinding_checked": True,
            "terminal_write_failure_checked": True,
            "original_error_retention_checked": True,
            "cleanup_independence_checked": True,
            "one_process_enforcement_checked": True,
            "exact_stop_behavior_checked": True,
            "path_and_secret_sanitization_checked": True,
        },
        "released_now": {
            "public_ci": True,
            "gate_state_publication": False,
            "final_no_content_preflight": False,
            "distinct_process": False,
            "project_data_content_read": False,
            "external_custody_access": False,
        },
        "assertions": {
            "production_arcpy_invoked": False,
            "distinct_process_started": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "consumed_diagnostic_reused_or_retried": False,
            "consumed_reserved_receipts_mutated": False,
            "apply_orbit_correction_invoked": False,
            "geoprocessing_invoked": False,
            "historical_root_cause_established": False,
            "radar_recovery_readiness_established": False,
            "scientific_result_established": False,
        },
        "next_action": "Publish the exact receipt-durability implementation and require successful public default-branch CI before execution-gate publication, final preflight, ArcPy import, or exact-input access.",
    }
    write_new_json(ROOT / OUTPUT_REF, record)

    milestone = load("contracts/milestone-002.json")
    units = {item.get("id"): item for item in milestone.get("units", []) if isinstance(item, dict)}
    implementation = units["M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-IMPLEMENTATION"]
    if implementation.get("status") != "in_progress" or implementation.get("gates", {}).get("public_ci") != "pending":
        raise SystemExit("implementation unit is not at pre-publication state")
    implementation["gates"].update({
        "portable_synthetic_tests": "success",
        "installed_arcgis_runtime_synthetic_test": "success",
        "repository_validation": "success",
        "focused_test_count": args.focused_test_count,
        "full_test_count": args.full_test_count,
        "full_skip_count": args.full_skip_count,
        "required_file_count": args.required_file_count,
        "implementation_readiness_sha256": sha256_file(ROOT / OUTPUT_REF),
    })
    implementation["outputs"].extend([
        f"records/readiness/{PREFIX}-arcgis-runtime-validation-failure-001.json",
        f"records/readiness/{PREFIX}-arcgis-runtime-validation.json",
        OUTPUT_REF,
    ])
    implementation["exit_condition_delta"] = {
        "expected": ["successful public default-branch CI and execution-gate publication"],
        "observed": ["portable and disposable installed ArcGIS-runtime validation passed; one earlier disposable validator self-reference failure remains preserved"],
        "decision_value": "pending_public_ci",
        "rationale": "The distinct read-only process remains blocked behind public CI, a separately published execution gate, and final no-content preflight.",
    }
    replace_json("contracts/milestone-002.json", milestone, "diagnostic-receipt-readiness")

    evidence = {
        "record_id": "EVID-0200",
        "type": "m2_radar_apply_orbit_correction_input_resolution_diagnostic_receipt_persistence_recovery_001_implementation_readiness",
        "verified_at_utc": args.recorded_at_utc,
        "status": record["status"],
        "claim": "The approved receipt-durability implementation passed portable and installed ArcGIS-runtime disposable validation. No production ArcPy invocation, exact-input access, or distinct process occurred; public CI remains required.",
        "approval_ref": f"records/source-gates/{PREFIX}-approval.json",
        "approval_sha256": sha256_file(ROOT / f"records/source-gates/{PREFIX}-approval.json"),
        "implementation_readiness_ref": OUTPUT_REF,
        "implementation_readiness_sha256": sha256_file(ROOT / OUTPUT_REF),
        "assertions": {
            "focused_test_count": args.focused_test_count,
            "full_test_count": args.full_test_count,
            "full_skip_count": args.full_skip_count,
            "required_file_count": args.required_file_count,
            "installed_arcgis_runtime_test_count": 1,
            "public_ci_pending": True,
            "distinct_process_started": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "consumed_reserved_receipts_mutated": False,
            "geoprocessing_invoked": False,
            "scientific_result_established": False,
            "current_checkpoint": "M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-IMPLEMENTATION",
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
