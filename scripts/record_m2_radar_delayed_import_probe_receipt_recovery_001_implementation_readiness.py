#!/usr/bin/env python3
"""Seal receipt-recovery implementation readiness before public CI."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from m2_radar_delayed_import_probe_receipt_recovery_001_core import canonical_bytes, local_attempt_root, sha256_file, write_new_json


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-delayed-import-probe-receipt-recovery-001"
OUTPUT_REF = f"records/readiness/{PREFIX}-implementation-readiness.json"
ARTIFACTS = [
    f"reviews/{PREFIX}/response-baf64278ef45352ca7add79948d827fdf87dba8138e722510d89da568a006600.json",
    f"reviews/{PREFIX}/review-contract-lock-001.json",
    f"records/source-gates/{PREFIX}-review-reconciliation.json",
    f"records/source-gates/{PREFIX}-approval.json",
    f"records/readiness/{PREFIX}-approval-activation.json",
    f"config/qa/{PREFIX}-contract.json",
    f"scripts/activate_{PREFIX.replace('-', '_')}.py",
    f"scripts/{PREFIX.replace('-', '_')}_core.py",
    f"scripts/run_{PREFIX.replace('-', '_')}.py",
    f"scripts/validate_{PREFIX.replace('-', '_')}_arcgis.py",
    f"tests/test_{PREFIX.replace('-', '_')}.py",
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
    if local_attempt_root().exists():
        raise SystemExit("fresh production attempt already exists")
    runtime = load(f"records/readiness/{PREFIX}-arcgis-runtime-validation.json")
    if runtime.get("status") != "pass_installed_arcgis_runtime_receipt_fallback_synthetic":
        raise SystemExit("installed ArcGIS runtime validation is not an exact pass")

    record = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-IMPLEMENTATION-READINESS",
        "recorded_at_utc": args.recorded_at_utc,
        "status": "pass_receipt_recovery_implementation_public_ci_pending",
        "bindings": {ref: sha256_file(ROOT / ref) for ref in ARTIFACTS},
        "implementation": {
            "attempt_id": "radar-delayed-import-probe-receipt-recovery-001-real-001",
            "maximum_fresh_attempts": 1,
            "function_local_datetime_import": True,
            "terminal_and_cleanup_identities_reserved_before_corpus": True,
            "fallback_initialized_before_corpus": True,
            "original_error_appended_before_terminal_assembly": True,
            "terminal_persistence_error_does_not_replace_original": True,
            "cleanup_outer_finally_independent_of_terminal_persistence": True,
            "automatic_retry_authorized": False,
        },
        "validation": {
            "focused_test_count": args.focused_test_count,
            "full_repository_test_count": args.full_test_count,
            "full_repository_intentional_skip_count": args.full_skip_count,
            "repository_checker_status": f"pass_{args.required_file_count}_required_files",
            "installed_arcgis_runtime_test_count": 1,
            "installed_arcgis_runtime_test_failures": 0,
            "timestamp_name_rebinding_checked": True,
            "forced_terminal_write_failure_checked": True,
            "original_error_retention_checked": True,
            "cleanup_independence_checked": True,
            "interruption_checked": True,
            "exact_stage_order_checked": True,
            "append_only_collision_checked": True,
            "secret_and_path_redaction_checked": True,
        },
        "released_now": {
            "public_ci": True,
            "final_no_content_preflight": False,
            "fresh_probe": False,
            "project_data_content_read": False,
            "external_custody_access": False,
            "radar_processing": False,
        },
        "assertions": {
            "production_arcpy_invoked": False,
            "fresh_probe_process_started": False,
            "production_corpus_created": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "network_request_performed": False,
            "credential_value_read": False,
            "consumed_probe_reused_or_retried": False,
            "historical_root_cause_established": False,
            "recovery_readiness_established": False,
            "radar_processing_executed": False,
            "scientific_result_established": False,
        },
        "next_action": "Publish the exact receipt-recovery implementation and require successful public default-branch CI before any final preflight or fresh probe.",
    }
    write_new_json(ROOT / OUTPUT_REF, record)

    milestone = load("contracts/milestone-002.json")
    units = {item.get("id"): item for item in milestone.get("units", []) if isinstance(item, dict)}
    implementation = units.get("M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-IMPLEMENTATION", {})
    if implementation.get("status") != "in_progress" or implementation.get("gates", {}).get("public_ci") != "pending":
        raise SystemExit("implementation unit is not at pre-publication state")
    implementation["gates"].update({
        "portable_synthetic_tests": "success",
        "installed_arcgis_runtime_test": "success",
        "repository_validation": "success",
        "focused_test_count": args.focused_test_count,
        "full_test_count": args.full_test_count,
        "full_skip_count": args.full_skip_count,
        "required_file_count": args.required_file_count,
        "implementation_readiness_sha256": sha256_file(ROOT / OUTPUT_REF),
    })
    implementation["outputs"].extend([
        f"records/readiness/{PREFIX}-arcgis-runtime-validation.json",
        OUTPUT_REF,
    ])
    implementation["exit_condition_delta"] = {
        "expected": ["successful public default-branch CI"],
        "observed": ["portable and installed ArcGIS-runtime synthetic validation passed without a production corpus or attempt"],
        "decision_value": "pending_public_ci",
        "rationale": "The fresh disposable probe remains blocked behind public CI, gate-state publication, and the final no-content preflight.",
    }
    replace_json("contracts/milestone-002.json", milestone, "receipt-recovery-readiness")

    evidence = {
        "record_id": "EVID-0176",
        "type": "m2_radar_delayed_import_probe_receipt_recovery_001_implementation_readiness",
        "verified_at_utc": args.recorded_at_utc,
        "status": "pass_receipt_recovery_implementation_public_ci_pending",
        "claim": "The exact receipt-recovery implementation passed portable and installed ArcGIS-runtime synthetic tests. The production corpus and fresh attempt were not created, and public CI remains required.",
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
            "fresh_probe_process_started": False,
            "production_corpus_created": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "consumed_probe_reused_or_retried": False,
            "radar_processing_executed": False,
            "scientific_result_established": False,
            "current_checkpoint": "M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-IMPLEMENTATION",
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
