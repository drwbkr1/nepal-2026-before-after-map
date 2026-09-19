#!/usr/bin/env python3
"""Seal radar recovery-002 implementation readiness before public CI."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from m2_radar_pixel_orbit_application_001_core import canonical_bytes, sha256_file
from m2_radar_pixel_orbit_application_recovery_002_core import ATTEMPT_ID, write_new_json


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-pixel-orbit-application-recovery-002"
OUTPUT_REF = f"records/readiness/{PREFIX}-implementation-readiness.json"
ARTIFACTS = [
    f"reviews/{PREFIX}/response-c1c5c613354558815d57a02eb185fc837d94b626d44f958ec2cfb8ca900d14cb.json",
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
ATTEMPT_ROOT = Path(
    r"C:\Projects\Active\nepal-2026-before-after-map-data\derived\radar-pixel-orbit-application-recovery-002"
    r"\radar-pixel-orbit-application-recovery-002-real-001"
)


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
    if ATTEMPT_ROOT.exists():
        raise SystemExit("fresh production attempt already exists")
    runtime = load(f"records/readiness/{PREFIX}-arcgis-runtime-validation.json")
    if runtime.get("status") != "pass_installed_arcgis_runtime_disposable_success_and_failure_paths":
        raise SystemExit("installed ArcGIS runtime validation is not an exact pass")
    checks = runtime.get("checks", {})
    if any(checks.get(key) is not True for key in (
        "actual_arcpy_import_and_product_info",
        "actual_extension_checkout_and_reverse_checkin",
        "actual_disposable_numpy_rasters_and_mosaic",
        "six_synthetic_source_routes_in_exact_order",
        "two_synthetic_pair_routes_in_exact_order",
        "first_failure_survived_terminal_persistence_failure",
        "cleanup_persisted_after_terminal_failure",
    )):
        raise SystemExit("installed ArcGIS runtime validation checks differ")

    record = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-002-IMPLEMENTATION-READINESS",
        "recorded_at_utc": args.recorded_at_utc,
        "status": "pass_recovery_002_implementation_public_ci_pending",
        "bindings": {ref: sha256_file(ROOT / ref) for ref in ARTIFACTS},
        "implementation": {
            "attempt_id": ATTEMPT_ID,
            "maximum_fresh_attempts": 1,
            "single_process": True,
            "exact_source_order": [f"M1-SRC-{index:03d}" for index in range(1, 7)],
            "exact_route_order": ["PAIR-S1-ASC-R085-IW", "PAIR-S1-DESC-R121-IW"],
            "identity_scan_before_delayed_arcpy_import": True,
            "terminal_and_cleanup_identities_reserved_before_content_read": True,
            "fallback_initialized_before_content_read": True,
            "first_error_appended_before_terminal_assembly": True,
            "terminal_persistence_error_does_not_replace_first_error": True,
            "cleanup_outer_finally_independent_of_terminal_persistence": True,
            "automatic_retry_authorized": False,
            "stop_on_first_failure": True,
        },
        "validation": {
            "focused_test_count": args.focused_test_count,
            "full_repository_test_count": args.full_test_count,
            "full_repository_intentional_skip_count": args.full_skip_count,
            "repository_checker_status": f"pass_{args.required_file_count}_required_files",
            "installed_arcgis_runtime_test_count": 1,
            "installed_arcgis_runtime_test_failures": 0,
            "function_local_datetime_checked": True,
            "pre_reservation_checked": True,
            "fixed_source_and_route_order_checked": True,
            "stop_on_first_failure_checked": True,
            "interruption_checked": True,
            "forced_terminal_write_failure_checked": True,
            "cleanup_independence_checked": True,
            "append_only_collision_checked": True,
            "secret_and_path_redaction_checked": True,
        },
        "released_now": {
            "public_ci": True,
            "gate_state_publication": False,
            "final_no_content_preflight": False,
            "fresh_attempt": False,
            "project_data_content_read": False,
            "external_custody_access": False,
            "radar_processing": False,
        },
        "assertions": {
            "production_arcpy_invoked": False,
            "fresh_attempt_process_started": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "network_request_performed": False,
            "credential_value_read": False,
            "consumed_attempt_reused_or_retried": False,
            "historical_root_cause_established": False,
            "radar_recovery_readiness_established": False,
            "baseline_or_change_analysis_executed": False,
            "scientific_result_established": False,
        },
        "next_action": "Publish the exact recovery-002 implementation and require successful public default-branch CI before gate-state publication, final preflight, project-data access, or the fresh attempt.",
    }
    write_new_json(ROOT / OUTPUT_REF, record)

    milestone = load("contracts/milestone-002.json")
    units = {item.get("id"): item for item in milestone.get("units", []) if isinstance(item, dict)}
    implementation = units.get("M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-002-IMPLEMENTATION", {})
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
        "observed": ["portable and installed ArcGIS-runtime synthetic validation passed without project-data access or a production attempt"],
        "decision_value": "pending_public_ci",
        "rationale": "The final no-content preflight and fresh production attempt remain blocked behind two exact public CI gates.",
    }
    replace_json("contracts/milestone-002.json", milestone, "radar-recovery-002-readiness")

    evidence = {
        "record_id": "EVID-0184",
        "type": "m2_radar_pixel_orbit_application_recovery_002_implementation_readiness",
        "verified_at_utc": args.recorded_at_utc,
        "status": "pass_recovery_002_implementation_public_ci_pending",
        "claim": "The exact recovery-002 wrapper passed portable and installed ArcGIS-runtime disposable synthetic tests. No project data or external custody was read and no production attempt was created; public CI remains required.",
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
            "fresh_attempt_process_started": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "consumed_attempt_reused_or_retried": False,
            "radar_processing_executed": False,
            "scientific_result_established": False,
            "current_checkpoint": "M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-002-IMPLEMENTATION",
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
