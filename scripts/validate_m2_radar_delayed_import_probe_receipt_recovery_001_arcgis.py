#!/usr/bin/env python3
"""Exercise receipt recovery under ArcGIS Pro Python without geoprocessing inputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any

import arcpy  # type: ignore

import m2_radar_delayed_import_probe_receipt_recovery_001_core as core
import run_m2_radar_delayed_import_probe_receipt_recovery_001 as runner


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-delayed-import-probe-receipt-recovery-001"
OUTPUT_REF = f"records/readiness/{PREFIX}-arcgis-runtime-validation.json"


def fake_scan() -> dict[str, Any]:
    return {
        "file_count": core.FILE_COUNT,
        "total_logical_bytes": core.TOTAL_LOGICAL_BYTES,
        "aggregate_sha256": core.EXPECTED_AGGREGATE_SHA256,
        "elapsed_seconds": 0.0,
        "files": [
            {"name": name, "logical_bytes": size, "sha256": "0" * 64}
            for name, size in zip(core.CORPUS_NAMES, core.size_plan(), strict=True)
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verified-at-utc", required=True)
    args = parser.parse_args()
    if not args.verified_at_utc.endswith("Z"):
        raise SystemExit("--verified-at-utc must be UTC")
    output = ROOT / OUTPUT_REF
    if output.exists():
        raise SystemExit("ArcGIS runtime validation output collision")

    install = arcpy.GetInstallInfo()
    runtime = {
        "product": install.get("ProductName"),
        "version": install.get("Version"),
        "license_level": arcpy.ProductInfo(),
        "python_executable": str(Path(__import__("sys").executable).resolve()),
    }
    events: list[str] = []
    original_error = "synthetic-arcpy-loader-boundary"

    with tempfile.TemporaryDirectory(prefix="nepal-probe-receipt-recovery-arcgis-") as temporary:
        temporary_root = Path(temporary).resolve()
        target = temporary_root / "attempt"
        core.require_outside(target, (ROOT, runner.EXTERNAL_CUSTODY_ROOT))

        def corpus_creator(path: Path) -> list[Path]:
            events.append("synthetic_corpus_creator")
            path.mkdir()
            paths: list[Path] = []
            for name in core.CORPUS_NAMES:
                item = path / name
                item.write_bytes(b"x")
                paths.append(item)
            return paths

        def corpus_scanner(paths: Any) -> dict[str, Any]:
            events.append("synthetic_corpus_scanner")
            return fake_scan()

        def arcpy_loader() -> Any:
            events.append("synthetic_arcpy_loader")
            raise RuntimeError(original_error)

        def terminal_writer(path: Path, value: object) -> None:
            events.append("forced_terminal_writer_failure")
            raise OSError("synthetic-terminal-write-boundary")

        setattr(runner, "datetime", object())
        result = runner.execute_probe_body(
            args.verified_at_utc,
            target=target,
            bindings={"arcgis_runtime_synthetic": "1" * 64},
            arcpy_loader=arcpy_loader,
            corpus_creator=corpus_creator,
            corpus_scanner=corpus_scanner,
            terminal_writer=terminal_writer,
        )
        delattr(runner, "datetime")

        fallback = [json.loads(line) for line in (target / "fallback.jsonl").read_text(encoding="utf-8").splitlines()]
        cleanup = json.loads((target / "cleanup.json").read_text(encoding="utf-8"))
        stages = [json.loads(line)["stage"] for line in (target / "stages.jsonl").read_text(encoding="utf-8").splitlines()]
        if result != 21:
            raise SystemExit(f"unexpected synthetic recovery return code: {result}")
        fallback_events = [item["event"] for item in fallback]
        if fallback_events[:3] != [
            "fallback_journal_initialized",
            "probe_exception_captured",
            "terminal_persistence_exception_captured",
        ]:
            raise SystemExit("fallback event order differs")
        rendered = json.dumps(fallback)
        if original_error not in rendered or "synthetic-terminal-write-boundary" not in rendered:
            raise SystemExit("original or persistence error missing from fallback")
        if (target / "terminal.json").exists():
            raise SystemExit("terminal receipt unexpectedly persisted")
        if cleanup.get("status") != "cleanup_completed" or cleanup.get("terminal_persisted") is not False:
            raise SystemExit("cleanup receipt differs")
        if (target / "corpus").exists() or (target / "scratch").exists():
            raise SystemExit("synthetic payload cleanup failed")
        if "arcpy_import_completed" in stages or any(event in events for event in ("mosaic", "raster_save")):
            raise SystemExit("geoprocessing boundary violated")

        receipt = {
            "schema_version": "1.0",
            "record_id": "NEPAL-M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-ARCGIS-RUNTIME-VALIDATION",
            "verified_at_utc": args.verified_at_utc,
            "status": "pass_installed_arcgis_runtime_receipt_fallback_synthetic",
            "runtime": runtime,
            "bindings": runner.repository_bindings(),
            "checks": {
                "function_local_datetime_survived_global_rebinding": True,
                "original_sanitized_error_preserved_before_terminal_assembly": True,
                "terminal_persistence_error_appended_without_replacement": True,
                "cleanup_persisted_after_terminal_failure": True,
                "payload_children_removed": True,
                "fallback_event_order": fallback_events,
                "durable_stage_order_monotonic": core.stage_positions(stages) == sorted(core.stage_positions(stages)),
                "synthetic_return_code": result,
            },
            "assertions": {
                "synthetic_only": True,
                "arcpy_runtime_imported": True,
                "geoprocessing_invoked": False,
                "project_data_content_read": False,
                "external_custody_accessed": False,
                "network_request_performed": False,
                "credential_value_read": False,
                "production_attempt_created": False,
                "consumed_probe_reused_or_retried": False,
                "radar_processing_executed": False,
                "scientific_result_established": False,
            },
            "limitations": [
                "This validates receipt fallback behavior under the installed ArcGIS Pro Python runtime only.",
                "ArcPy was imported for runtime identity; no ArcPy geoprocessing tool or project input was invoked.",
                "The temporary synthetic payload is disposable and is not the authorized production corpus or attempt.",
            ],
        }
        core.write_new_json(output, receipt)

    if Path(temporary).exists():
        shutil.rmtree(temporary, ignore_errors=True)
    print(json.dumps({"status": receipt["status"], "receipt": OUTPUT_REF}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
