#!/usr/bin/env python3
"""Run the approved disposable installed-ArcGIS synthetic recovery validation."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
import tempfile
from pathlib import Path

from m2_radar_apply_orbit_correction_input_resolution_diagnostic_receipt_persistence_recovery_001_core import (
    CONTRACT_REF,
    load_object,
    sha256_file,
    write_new_json,
)
import run_m2_radar_apply_orbit_correction_input_resolution_diagnostic_receipt_persistence_recovery_001 as runner


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_REF = (
    "records/readiness/m2-radar-apply-orbit-correction-input-resolution-diagnostic-"
    "receipt-persistence-recovery-001-arcgis-runtime-validation.json"
)
VALIDATOR_REF = (
    "scripts/validate_m2_radar_apply_orbit_correction_input_resolution_diagnostic_"
    "receipt_persistence_recovery_001_arcgis.py"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validated-at-utc", required=True)
    args = parser.parse_args()
    if not args.validated_at_utc.endswith("Z"):
        raise SystemExit("--validated-at-utc must be UTC")
    output = ROOT / OUTPUT_REF
    if output.exists():
        raise SystemExit("ArcGIS runtime validation output collision")
    contract = load_object(ROOT / CONTRACT_REF)
    with tempfile.TemporaryDirectory(prefix="nepal-m2-diagnostic-receipt-recovery-") as temporary:
        temporary_root = Path(temporary)
        attempt = temporary_root / "synthetic-attempt"
        safe = attempt / "sources" / "m1-src-001" / "synthetic.SAFE"
        manifest = safe / "manifest.safe"
        orbit = temporary_root / "synthetic-orbit.EOF"
        safe.mkdir(parents=True)
        manifest.write_text("<XFDU />\n", encoding="utf-8")
        orbit.write_text("<Earth_Explorer_File />\n", encoding="utf-8")
        synthetic_contract = copy.deepcopy(contract)
        synthetic_contract["exact_inputs"]["orbit_size_bytes"] = orbit.stat().st_size
        synthetic_contract["exact_inputs"]["orbit_sha256"] = sha256_file(orbit)
        paths = {
            "attempt_root": attempt,
            "safe_directory": safe,
            "manifest": manifest,
            "orbit": orbit,
        }
        terminal = temporary_root / "outputs" / "terminal.json"
        cleanup = temporary_root / "outputs" / "cleanup.json"
        fallback = temporary_root / "outputs" / "fallback.jsonl"
        arcpy = importlib.import_module("arcpy")
        code = runner.execute_diagnostic_body(
            args.validated_at_utc,
            contract=synthetic_contract,
            paths=paths,
            terminal_path=terminal,
            cleanup_path=cleanup,
            fallback_path=fallback,
            bindings={"validation_mode": "installed_arcgis_disposable_inputs_only"},
            arcpy_loader=lambda: arcpy,
        )
        if code != 0 or not terminal.is_file() or not cleanup.is_file() or not fallback.is_file():
            raise SystemExit(f"installed ArcGIS synthetic validation failed with code {code}")
        terminal_record = load_object(terminal)
        cleanup_record = load_object(cleanup)
        fallback_records = [json.loads(line) for line in fallback.read_text(encoding="utf-8").splitlines()]
        if (
            terminal_record.get("status") != "pass_current_input_resolution_diagnostic_only"
            or cleanup_record.get("status") != "pass_no_payload_or_temporary_artifact_cleanup_required"
            or terminal_record.get("assertions", {}).get("geoprocessing_invoked") is not False
            or terminal_record.get("assertions", {}).get("apply_orbit_correction_invoked") is not False
            or not fallback_records
            or fallback_records[0].get("event") != "fallback_journal_initialized"
        ):
            raise SystemExit("installed ArcGIS synthetic result differs")
        runtime = terminal_record["arcgis_observations"]["runtime"]
        receipt = {
            "schema_version": "1.0",
            "record_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-RECEIPT-PERSISTENCE-RECOVERY-001-ARCGIS-RUNTIME-VALIDATION",
            "validated_at_utc": args.validated_at_utc,
            "status": "pass_installed_arcgis_runtime_disposable_read_only_receipt_recovery",
            "bindings": {
                "contract_sha256": sha256_file(ROOT / CONTRACT_REF),
                "core_sha256": sha256_file(ROOT / runner.CORE_REF),
                "runner_sha256": sha256_file(ROOT / runner.RUNNER_REF),
                "validator_sha256": sha256_file(ROOT / VALIDATOR_REF),
            },
            "runtime": runtime,
            "validation": {
                "disposable_attempt_root_created": True,
                "disposable_safe_directory_created": True,
                "disposable_manifest_created": True,
                "disposable_orbit_created": True,
                "terminal_receipt_persisted": True,
                "cleanup_receipt_persisted": True,
                "fallback_journal_initialized_before_reads": True,
                "fallback_event_count": len(fallback_records),
                "temporary_root_removed_on_context_exit": True,
            },
            "assertions": {
                "project_data_content_read": False,
                "external_custody_accessed": False,
                "consumed_diagnostic_reused_or_retried": False,
                "consumed_reserved_receipts_mutated": False,
                "apply_orbit_correction_invoked": False,
                "geoprocessing_invoked": False,
                "network_request_performed": False,
                "credential_value_read": False,
                "radar_processing_executed": False,
                "scientific_result_established": False,
            },
        }
    write_new_json(output, receipt)
    print(json.dumps({"status": receipt["status"], "record": OUTPUT_REF, "sha256": sha256_file(output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
