#!/usr/bin/env python3
"""Run the one approved radar inventory-normalization recovery attempt."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
import re
from pathlib import Path
from typing import Any

import m2_radar_pixel_orbit_application_001_core as base_core
import run_m2_radar_pixel_orbit_application_001 as base_runner
from m2_radar_pixel_orbit_application_recovery_001_core import (
    BASE_CONTRACT_REF,
    CONTRACT_REF,
    load_execution_plan,
    verify_external_identities,
)


ROOT = Path(__file__).resolve().parents[1]
PUBLICATION_GATE_REF = "records/readiness/m2-radar-pixel-orbit-application-recovery-001-implementation-publication-gate.json"
FINAL_PREFLIGHT_REF = "records/readiness/m2-radar-pixel-orbit-application-recovery-001-final-preflight.json"
PROCESSING_ROOT_REF = "records/processing/radar-pixel-orbit-application-recovery-001"
TERMINAL_REF = "records/processing/m2-radar-pixel-orbit-application-recovery-001-terminal-reconciliation.json"
CORE_REF = "scripts/m2_radar_pixel_orbit_application_recovery_001_core.py"
RUNNER_REF = "scripts/run_m2_radar_pixel_orbit_application_recovery_001.py"
ARCGIS_VALIDATOR_REF = "scripts/validate_m2_radar_pixel_orbit_application_recovery_001_arcgis.py"
PORTABLE_TEST_REF = "tests/test_m2_radar_pixel_orbit_application_recovery_001.py"
BASE_CORE_REF = "scripts/m2_radar_pixel_orbit_application_001_core.py"
BASE_RUNNER_REF = "scripts/run_m2_radar_pixel_orbit_application_001.py"
UTC_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


def repo_sha(ref: str) -> str:
    return base_core.sha256_file(ROOT / ref)


def publication_gate() -> dict[str, Any]:
    path = ROOT / PUBLICATION_GATE_REF
    if not path.is_file():
        raise base_core.RadarRouteError("recovery_implementation_publication_gate_missing")
    gate = base_core.load_object(path)
    if gate.get("status") != "pass_public_default_branch_ci_recovery_implementation_ready" or gate.get("public_ci_conclusion") != "success":
        raise base_core.RadarRouteError("recovery_implementation_publication_gate_not_pass")
    expected = {
        "recovery_contract_sha256": repo_sha(CONTRACT_REF),
        "recovery_core_sha256": repo_sha(CORE_REF),
        "recovery_runner_sha256": repo_sha(RUNNER_REF),
        "arcgis_validator_sha256": repo_sha(ARCGIS_VALIDATOR_REF),
        "portable_test_sha256": repo_sha(PORTABLE_TEST_REF),
        "base_contract_sha256": repo_sha(BASE_CONTRACT_REF),
        "base_core_sha256": repo_sha(BASE_CORE_REF),
        "base_runner_sha256": repo_sha(BASE_RUNNER_REF),
    }
    if any(gate.get("bindings", {}).get(key) != value for key, value in expected.items()):
        raise base_core.RadarRouteError("recovery_implementation_publication_gate_binding_mismatch")
    return gate


@contextmanager
def configured_base_runner():
    """Bind the unchanged production helpers to recovery-specific controls and receipts."""
    replacements = {
        "ROOT": ROOT,
        "CONTRACT_REF": CONTRACT_REF,
        "PUBLICATION_GATE_REF": PUBLICATION_GATE_REF,
        "FINAL_PREFLIGHT_REF": FINAL_PREFLIGHT_REF,
        "PROCESSING_ROOT_REF": PROCESSING_ROOT_REF,
        "TERMINAL_REF": TERMINAL_REF,
        "load_execution_plan": load_execution_plan,
        "verify_external_identities": verify_external_identities,
        "publication_gate": publication_gate,
    }
    original = {name: getattr(base_runner, name) for name in replacements}
    for name, value in replacements.items():
        setattr(base_runner, name, value)
    try:
        yield
    finally:
        for name, value in original.items():
            setattr(base_runner, name, value)


def _write_terminal_failure(attempt_root: Path, exc: BaseException) -> None:
    failure = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-001-TERMINAL-RECONCILIATION",
        "status": "failed_supervisor_no_retry",
        "completed_at_utc": base_runner.now_utc(),
        **base_runner.safe_error(exc),
        "attempt_root": str(attempt_root),
        "assertions": {
            "attempt_consumed": True,
            "terminal_receipt_persisted": True,
            "automatic_retry_performed": False,
            "network_request_performed_by_runner": False,
            "credential_value_read": False,
            "baseline_or_change_analysis_executed": False,
            "scientific_admission_authorized": False,
        },
    }
    base_core.write_new_json(ROOT / TERMINAL_REF, failure)
    base_core.write_new_json(attempt_root / "terminal.json", failure)


def run_final_preflight(checked_at_utc: str) -> int:
    with configured_base_runner():
        return base_runner.run_final_preflight(checked_at_utc)


def _run_execute_configured(executed_at_utc: str) -> int:
    gate = publication_gate()
    preflight_path = ROOT / FINAL_PREFLIGHT_REF
    if not preflight_path.is_file():
        raise base_core.RadarRouteError("final_preflight_missing")
    preflight = base_core.load_object(preflight_path)
    if (
        preflight.get("status") != "pass_final_no_content_preflight"
        or preflight.get("bindings", {}).get("implementation_publication_gate_sha256") != repo_sha(PUBLICATION_GATE_REF)
    ):
        raise base_core.RadarRouteError("final_preflight_not_exact_pass")
    plan = load_execution_plan(ROOT, CONTRACT_REF)
    attempt_root = base_core.require_external_child(
        plan["data_root"], Path(plan["contract"]["attempt"]["external_attempt_root"]), must_exist=False
    )
    if attempt_root.exists() or (ROOT / TERMINAL_REF).exists():
        raise base_core.RadarRouteError("real_attempt_collision")
    attempt_root.mkdir(parents=True)
    base_core.write_new_json(
        attempt_root / "started.json",
        {
            "schema_version": "1.0",
            "status": "started_single_recovery_attempt",
            "started_at_utc": executed_at_utc,
            "attempt_id": plan["contract"]["attempt"]["attempt_id"],
            "recovery_contract_sha256": plan["contract_sha256"],
            "base_contract_sha256": plan["base_contract_sha256"],
            "publication_gate_sha256": repo_sha(PUBLICATION_GATE_REF),
            "final_preflight_sha256": repo_sha(FINAL_PREFLIGHT_REF),
        },
    )

    arcpy: Any | None = None
    image_checked_out = False
    spatial_checked_out = False
    try:
        identities_before = verify_external_identities(plan)
        os.environ.setdefault("GDAL_PAM_ENABLED", "NO")
        import arcpy as arcpy_module  # type: ignore[import-not-found]

        arcpy = arcpy_module
        arcpy.env.overwriteOutput = False
        arcpy.CheckOutExtension("ImageAnalyst")
        image_checked_out = True
        arcpy.CheckOutExtension("Spatial")
        spatial_checked_out = True
        dem_mosaic = base_runner.create_dem_mosaic(arcpy, plan, attempt_root)
        support = base_runner.create_analysis_support(arcpy, plan, attempt_root)

        def worker(source_id: str) -> dict[str, Any]:
            return base_runner.process_source(
                arcpy=arcpy,
                plan=plan,
                identities_before=identities_before,
                attempt_root=attempt_root,
                dem_mosaic=dem_mosaic,
                support=support,
                source_id=source_id,
                started_at_utc=base_runner.now_utc(),
            )

        sources = base_core.execute_fixed_order(base_core.SOURCE_ORDER, worker)
        routes: list[dict[str, Any]] = []
        stopped_route_id = None
        if sources["status"] == "pass_all_sources":
            for route_id in base_core.ROUTE_ORDER:
                result = base_runner.process_route(
                    arcpy=arcpy,
                    plan=plan,
                    attempt_root=attempt_root,
                    support=support,
                    route_id=route_id,
                    started_at_utc=base_runner.now_utc(),
                )
                routes.append(result)
                if result["status"] != "pass_route_evaluated_qa_only":
                    stopped_route_id = route_id
                    break
        identities_after = verify_external_identities(plan)
        custody_unchanged = identities_before == identities_after
        if not custody_unchanged:
            raise base_core.RadarRouteError("external_custody_changed_during_attempt")
        terminal_status = (
            "pass_six_sources_two_routes_qa_only"
            if sources["status"] == "pass_all_sources" and len(routes) == 2 and stopped_route_id is None
            else "stopped_on_first_execution_failure"
        )
        terminal = {
            "schema_version": "1.0",
            "receipt_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-001-TERMINAL-RECONCILIATION",
            "status": terminal_status,
            "completed_at_utc": base_runner.now_utc(),
            "bindings": {
                "recovery_contract_sha256": plan["contract_sha256"],
                "base_contract_sha256": plan["base_contract_sha256"],
                "implementation_commit_sha": gate["implementation_commit_sha"],
                "public_ci_run_id": gate["public_ci_run_id"],
                "implementation_publication_gate_sha256": repo_sha(PUBLICATION_GATE_REF),
                "final_preflight_sha256": repo_sha(FINAL_PREFLIGHT_REF),
            },
            "source_execution": sources,
            "route_evaluations": routes,
            "stopped_route_id": stopped_route_id,
            "external_custody_unchanged": custody_unchanged,
            "attempt_root": str(attempt_root),
            "assertions": {
                "source_order_exact": [item["source_id"] for item in sources["results"]]
                == base_core.SOURCE_ORDER[: len(sources["results"])],
                "route_order_exact": [item["route_id"] for item in routes]
                == base_core.ROUTE_ORDER[: len(routes)],
                "terminal_receipt_persisted": True,
                "automatic_retry_performed": False,
                "network_request_performed_by_runner": False,
                "credential_value_read": False,
                "source_orbit_or_dem_custody_mutated": False,
                "baseline_admission_authorized": False,
                "change_analysis_executed": False,
                "interpretation_or_attribution_executed": False,
                "derived_pixel_publication_authorized": False,
                "scientific_publication_authorized": False,
            },
        }
        base_core.write_new_json(ROOT / TERMINAL_REF, terminal)
        base_core.write_new_json(attempt_root / "terminal.json", terminal)
        print(
            json.dumps(
                {
                    "status": terminal_status,
                    "terminal": TERMINAL_REF,
                    "source_count": len(sources["results"]),
                    "route_count": len(routes),
                },
                indent=2,
            )
        )
        return 0 if terminal_status == "pass_six_sources_two_routes_qa_only" else 20
    except Exception as exc:
        _write_terminal_failure(attempt_root, exc)
        print(
            json.dumps(
                {
                    "status": "failed_supervisor_no_retry",
                    "failure_code": getattr(exc, "code", "unexpected_processing_failure"),
                },
                indent=2,
            )
        )
        return 20
    finally:
        if arcpy is not None and spatial_checked_out:
            arcpy.CheckInExtension("Spatial")
        if arcpy is not None and image_checked_out:
            arcpy.CheckInExtension("ImageAnalyst")


def run_execute(executed_at_utc: str) -> int:
    with configured_base_runner():
        return _run_execute_configured(executed_at_utc)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=("final-preflight", "execute"))
    parser.add_argument("--timestamp-utc", required=True)
    args = parser.parse_args()
    if not UTC_TIMESTAMP.fullmatch(args.timestamp_utc):
        raise SystemExit("timestamp must be UTC in YYYY-MM-DDTHH:MM:SSZ form")
    try:
        return run_final_preflight(args.timestamp_utc) if args.mode == "final-preflight" else run_execute(args.timestamp_utc)
    except base_core.RadarRouteError as exc:
        print(json.dumps({"status": "stopped", "code": exc.code, "detail": exc.detail}, indent=2))
        return 12


if __name__ == "__main__":
    raise SystemExit(main())
