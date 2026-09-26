#!/usr/bin/env python3
"""Offline, no-pixel exact-input preflight for one distinct optical recovery."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any

from m2_optical_pair_header_recovery_001_core import (
    ATTEMPT_ROOT, FINAL_PREFLIGHT, HEADER_RECEIPT, PILOT_TERMINAL_SHA256,
    PROPOSAL_SHA256, ROOT, PilotControlError, exact_sources, now_utc, read_json,
    require_execution_release, sha256_file, stable_json_sha256, write_new_json,
)
from m2_optical_pair_pilot_001_offline import PILOT_ROOT, promoted_transfer


ARCGIS_PYTHON = Path(r"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe")
MIN_FREE_BYTES = 5 * 1024**3


def inventory_materialized(source: dict[str, Any], reviewed: dict[str, Any]) -> dict[str, Any]:
    """Hash existing bytes; never decode rasters or alter custody."""
    transfer = promoted_transfer(source)
    if transfer["archive_sha256"] != reviewed["verified_archive_sha256"]:
        raise PilotControlError("recovery_archive_identity_drift")
    attempt = PILOT_ROOT / "materialized" / source["source_id"].casefold() / "materialization-001"
    manifest_path, complete_path = attempt / "materialization-manifest.json", attempt / "completed.json"
    safe_root = attempt / source["exact_product_name"]
    if not manifest_path.is_file() or not complete_path.is_file() or not safe_root.is_dir():
        raise PilotControlError("recovery_materialization_missing")
    if sha256_file(manifest_path) != reviewed["materialization_manifest_sha256"]:
        raise PilotControlError("recovery_materialization_manifest_drift")
    manifest, completed = read_json(manifest_path), read_json(complete_path)
    files = manifest.get("files")
    if (
        manifest.get("status") != "complete"
        or manifest.get("source_id") != source["source_id"]
        or manifest.get("exact_product_id") != source["exact_product_name"]
        or manifest.get("archive_sha256") != transfer["archive_sha256"]
        or completed.get("status") != "complete"
        or completed.get("manifest_sha256") != reviewed["materialization_manifest_sha256"]
        or not isinstance(files, list)
        or len(files) != manifest.get("file_count")
    ):
        raise PilotControlError("recovery_materialization_receipt_drift")
    seen: set[str] = set()
    identities: list[dict[str, Any]] = []
    resolved_root = safe_root.resolve(strict=True)
    for item in files:
        relative = item.get("relative_path")
        if not isinstance(relative, str):
            raise PilotControlError("recovery_manifest_member_invalid")
        parts = PurePosixPath(relative).parts
        if not parts or any(part in ("", ".", "..") for part in parts) or relative in seen:
            raise PilotControlError("recovery_manifest_member_invalid")
        seen.add(relative)
        path = safe_root.joinpath(*parts)
        try:
            path.resolve(strict=True).relative_to(resolved_root)
        except (OSError, ValueError) as exc:
            raise PilotControlError("recovery_member_path_unsafe") from exc
        if not path.is_file() or path.stat().st_size != item.get("size_bytes") or sha256_file(path) != item.get("sha256"):
            raise PilotControlError("recovery_member_identity_drift")
        identities.append({"relative_path": relative, "size_bytes": item["size_bytes"], "sha256": item["sha256"]})
    actual = {path.relative_to(safe_root).as_posix() for path in safe_root.rglob("*") if path.is_file()}
    if actual != seen:
        raise PilotControlError("recovery_materialized_member_set_drift")
    return {
        "source_id": source["source_id"], "archive_size_bytes": transfer["archive_size_bytes"],
        "archive_sha256": transfer["archive_sha256"], "manifest_sha256": sha256_file(manifest_path),
        "file_count": len(files), "inventory_digest": stable_json_sha256(identities),
    }


def arcgis_runtime() -> dict[str, str]:
    if not ARCGIS_PYTHON.is_file():
        raise PilotControlError("recovery_arcgis_python_missing")
    command = [str(ARCGIS_PYTHON), "-c", "import arcpy,json; print(json.dumps({'version':arcpy.GetInstallInfo().get('Version',''),'spatial':arcpy.CheckExtension('Spatial')}))"]
    try:
        result = subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True,
                                text=True, timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PilotControlError("recovery_arcgis_runtime_probe_failed") from exc
    if result.returncode != 0 or len(result.stdout) > 2048:
        raise PilotControlError("recovery_arcgis_runtime_probe_failed")
    try:
        value = json.loads(result.stdout.strip())
    except (ValueError, UnicodeError) as exc:
        raise PilotControlError("recovery_arcgis_runtime_probe_invalid") from exc
    if value.get("version") != "3.7.1" or value.get("spatial") != "Available":
        raise PilotControlError("recovery_arcgis_runtime_drift")
    return {"version": value["version"], "spatial": value["spatial"]}


def preflight() -> dict[str, Any]:
    proposal = require_execution_release(final_preflight=False)
    if ATTEMPT_ROOT.exists() or FINAL_PREFLIGHT.exists() or HEADER_RECEIPT.exists():
        raise PilotControlError("recovery_real_attempt_or_preflight_collision")
    frozen = proposal["frozen_scientific_bindings"]
    for key in ("pixel_qa", "original_optical_pixel_contract", "optical_header_contract", "approved_aoi"):
        if sha256_file(ROOT / frozen[f"{key}_ref"]) != frozen[f"{key}_sha256"]:
            raise PilotControlError("recovery_frozen_contract_drift")
    if shutil.disk_usage(ATTEMPT_ROOT.parent.parent if ATTEMPT_ROOT.parent.parent.exists() else ROOT).free < MIN_FREE_BYTES:
        raise PilotControlError("recovery_insufficient_free_space")
    sources = exact_sources()
    reviewed = proposal["exact_existing_inputs"]
    identities = [inventory_materialized(source, bound) for source, bound in zip(sources, reviewed, strict=True)]
    runtime = arcgis_runtime()
    receipt = {
        "schema_version": "1.0", "receipt_id": "NEPAL-M2-OPTICAL-PAIR-HEADER-RECEIPT-RECOVERY-001-FINAL-PREFLIGHT",
        "status": "pass_offline_exact_identity_no_pixel_decode", "checked_at_utc": now_utc(),
        "proposal_sha256": PROPOSAL_SHA256,
        "execution_gate_sha256": sha256_file(ROOT / "records/readiness/m2-optical-pair-header-receipt-recovery-001-execution-gate.json"),
        "old_terminal_sha256": PILOT_TERMINAL_SHA256,
        "sources_in_order": identities, "arcgis_runtime": runtime,
        "network_requests": False, "credential_or_account_action": False, "raster_pixel_values_decoded": False,
        "source_or_original_attempt_mutated": False, "new_real_attempt_started": False,
        "early_custody_read_observation_ref": "records/readiness/m2-optical-pair-header-receipt-recovery-001-early-custody-read-observation.json",
    }
    write_new_json(FINAL_PREFLIGHT, receipt)
    return receipt


if __name__ == "__main__":
    try:
        print(json.dumps({"status": preflight()["status"]}))
    except BaseException as exc:
        code = exc.code if isinstance(exc, PilotControlError) else "recovery_final_preflight_unexpected_failure"
        failure = ROOT / "records/readiness/m2-optical-pair-header-receipt-recovery-001-final-preflight-failure.json"
        if not failure.exists():
            write_new_json(failure, {"status": "stopped", "code": code, "at_utc": now_utc(), "exception_text_recorded": False})
        print(json.dumps({"status": "stopped", "code": code}))
        raise SystemExit(20)
