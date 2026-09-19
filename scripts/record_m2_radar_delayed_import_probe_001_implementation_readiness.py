#!/usr/bin/env python3
"""Seal the portable delayed-import probe implementation before public CI."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from m2_radar_delayed_import_probe_001_core import canonical_bytes, local_attempt_root, sha256_file, write_new_json


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_REF = "records/readiness/m2-radar-delayed-import-probe-001-implementation-readiness.json"
ARTIFACTS = [
    "reviews/m2-radar-delayed-import-probe-001/response-7ef5b82aa7c932e8abc3926eb58dc7b7f5221a57bf5ecfced440dc997f57eb82.json",
    "reviews/m2-radar-delayed-import-probe-001/review-contract-lock-001.json",
    "records/source-gates/m2-radar-delayed-import-probe-001-review-reconciliation.json",
    "records/source-gates/m2-radar-delayed-import-probe-001-approval.json",
    "records/readiness/m2-radar-delayed-import-probe-001-approval-activation.json",
    "config/qa/m2-radar-delayed-import-probe-001-contract.json",
    "scripts/activate_m2_radar_delayed_import_probe_001.py",
    "scripts/m2_radar_delayed_import_probe_001_core.py",
    "scripts/run_m2_radar_delayed_import_probe_001.py",
    "tests/test_m2_radar_delayed_import_probe_001.py",
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
        raise SystemExit("authorized live probe attempt already exists")

    record = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-001-IMPLEMENTATION-READINESS",
        "recorded_at_utc": args.recorded_at_utc,
        "status": "pass_portable_probe_implementation_public_ci_pending",
        "bindings": {ref: sha256_file(ROOT / ref) for ref in ARTIFACTS},
        "implementation": {
            "attempt_id": "radar-delayed-import-probe-001-real-001",
            "single_process": True,
            "disposable_sparse_file_count": 156,
            "disposable_total_logical_bytes": 10367157634,
            "full_stable_order_hash_before_arcpy_import": True,
            "durable_stage_markers": True,
            "disposable_raster_count": 2,
            "mosaic_to_new_raster_count": 1,
            "reverse_extension_checkin": True,
            "terminal_receipt_before_cleanup": True,
            "automatic_retry_authorized": False,
        },
        "validation": {
            "focused_test_count": args.focused_test_count,
            "full_repository_test_count": args.full_test_count,
            "full_repository_intentional_skip_count": args.full_skip_count,
            "repository_checker_status": f"pass_{args.required_file_count}_required_files",
            "success_stage_order_checked": True,
            "four_historical_candidate_boundaries_checked": True,
            "append_only_collision_checked": True,
            "secret_and_path_redaction_checked": True,
            "cleanup_after_success_and_failure_checked": True,
            "no_top_level_arcpy_import_checked": True,
            "no_network_library_checked": True,
        },
        "released_now": {
            "public_ci": True,
            "final_no_content_preflight": False,
            "live_probe": False,
            "project_data_content_read": False,
            "external_custody_access": False,
            "radar_processing": False,
        },
        "assertions": {
            "arcpy_imported": False,
            "probe_process_started": False,
            "disposable_corpus_created": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "network_request_performed": False,
            "credential_value_read": False,
            "recovery_attempt_reused_or_retried": False,
            "historical_root_cause_established": False,
            "recovery_readiness_established": False,
            "radar_processing_executed": False,
            "scientific_result_established": False,
        },
        "next_action": "Publish this exact implementation and require successful public default-branch CI before the final no-content preflight or live probe.",
    }
    write_new_json(ROOT / OUTPUT_REF, record)

    milestone = load("contracts/milestone-002.json")
    units = {item.get("id"): item for item in milestone.get("units", []) if isinstance(item, dict)}
    implementation = units.get("M2-RADAR-DELAYED-IMPORT-PROBE-001-IMPLEMENTATION", {})
    if implementation.get("status") != "in_progress" or implementation.get("gates", {}).get("public_ci") != "pending":
        raise SystemExit("implementation unit is not at pre-publication state")
    implementation["gates"].update({
        "portable_synthetic_tests": "success",
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
        "observed": ["portable implementation and synthetic validation complete without ArcPy or corpus creation"],
        "decision_value": "pending_public_ci",
        "rationale": "The live probe remains blocked behind public CI and a separate final no-content preflight.",
    }
    replace_json("contracts/milestone-002.json", milestone, "probe-readiness")

    ledger_path = ROOT / "records/evidence-ledger.jsonl"
    evidence = {
        "record_id": "EVID-0168",
        "type": "m2_radar_delayed_import_probe_001_approved_implementation_readiness",
        "verified_at_utc": args.recorded_at_utc,
        "status": "pass_portable_probe_implementation_public_ci_pending",
        "claim": "The exact owner approval is locked and the bounded disposable delayed-import probe implementation passes portable synthetic and repository regression tests. No ArcPy import, disposable corpus, live probe, project-data read, recovery action, radar processing, or scientific action occurred.",
        "approval_ref": "records/source-gates/m2-radar-delayed-import-probe-001-approval.json",
        "approval_sha256": sha256_file(ROOT / "records/source-gates/m2-radar-delayed-import-probe-001-approval.json"),
        "implementation_readiness_ref": OUTPUT_REF,
        "implementation_readiness_sha256": sha256_file(ROOT / OUTPUT_REF),
        "assertions": {
            "human_decision_count": 1,
            "focused_test_count": args.focused_test_count,
            "full_test_count": args.full_test_count,
            "full_skip_count": args.full_skip_count,
            "required_file_count": args.required_file_count,
            "public_ci_pending": True,
            "arcpy_imported": False,
            "probe_process_started": False,
            "disposable_corpus_created": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "recovery_attempt_reused_or_retried": False,
            "radar_processing_executed": False,
            "scientific_result_established": False,
            "current_checkpoint": "M2-RADAR-DELAYED-IMPORT-PROBE-001-IMPLEMENTATION",
        },
        "next_action": "Publish the exact implementation and require successful public default-branch CI before the final no-content preflight or live probe.",
    }
    with ledger_path.open("ab", buffering=0) as stream:
        stream.write(json.dumps(evidence, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n")
        os.fsync(stream.fileno())
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
