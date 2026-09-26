#!/usr/bin/env python3
"""One no-pixel final preflight for exact acquired optical inputs."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from m2_optical_gdal_recovery_002_core import (
    ATTEMPT_ROOT, EXECUTION_GATE, FINAL_PREFLIGHT, MATERIALIZED_ROOT,
    PROPOSAL_SHA256, PUBLIC_TERMINAL, ROOT, PilotControlError, exact_sources,
    frozen_binding, now_utc, read_json, require_execution_release,
    sha256_file, write_new_json,
)
from m2_optical_pair_header_recovery_001_preflight import inventory_materialized


ARCGIS_PYTHON = Path(r"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe")
MIN_FREE_BYTES = 5 * 1024**3
MIN_AVAILABLE_MEMORY_BYTES = 4 * 1024**3


def _runtime() -> dict[str, Any]:
    if not ARCGIS_PYTHON.is_file():
        raise PilotControlError("gdal_python_missing")
    command = [str(ARCGIS_PYTHON), "-c",
               "import json; from osgeo import gdal; print(json.dumps({'version':gdal.VersionInfo('--version'),'jp2':bool(gdal.GetDriverByName('JP2KAK') or gdal.GetDriverByName('JP2OpenJPEG')),'mem':bool(gdal.GetDriverByName('MEM'))}))"]
    result = subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True,
                            text=True, timeout=90, check=False)
    if result.returncode != 0 or len(result.stdout) > 2048:
        raise PilotControlError("gdal_runtime_probe_failed")
    try:
        value = json.loads(result.stdout)
    except (ValueError, UnicodeError) as exc:
        raise PilotControlError("gdal_runtime_probe_invalid") from exc
    if not value.get("jp2") or not value.get("mem") or "GDAL 3.12.2" not in value.get("version", ""):
        raise PilotControlError("gdal_runtime_drift")
    return value


def _available_memory() -> int:
    # Runtime-neutral, no shell output containing machine or secret state.
    import ctypes

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

    value = MEMORYSTATUSEX()
    value.dwLength = ctypes.sizeof(value)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)):
        raise PilotControlError("gdal_memory_probe_failed")
    return int(value.ullAvailPhys)


def preflight() -> dict[str, Any]:
    binding = require_execution_release(require_preflight=False)
    if ATTEMPT_ROOT.exists() or FINAL_PREFLIGHT.exists() or PUBLIC_TERMINAL.exists():
        raise PilotControlError("gdal_attempt_or_preflight_collision")
    if (binding["grid"] != {"wkid": 32645, "cell_size_m": 20.0, "columns": 4726,
                            "rows": 3950, "xmin": 273300.0, "ymin": 3070220.0,
                            "xmax": 367820.0, "ymax": 3149220.0}):
        raise PilotControlError("gdal_grid_binding_drift")
    aoi = read_json(ROOT / binding["approved_aoi_ref"])
    ids = [feature["attributes"]["AOI_ID"] for feature in aoi.get("features", [])]
    if len(ids) != 3 or set(ids) != set(binding["qa_aoi_ids"]) or aoi.get("spatialReference", {}).get("wkid") != 32645:
        raise PilotControlError("gdal_aoi_binding_drift")
    if shutil.disk_usage(ATTEMPT_ROOT.parent if ATTEMPT_ROOT.parent.exists() else ROOT).free < MIN_FREE_BYTES:
        raise PilotControlError("gdal_insufficient_free_disk")
    available = _available_memory()
    if available < MIN_AVAILABLE_MEMORY_BYTES:
        raise PilotControlError("gdal_insufficient_memory")
    proposal = read_json(ROOT / "contracts/milestone-002-optical-gdal-header-pixel-recovery-002-proposal.json")
    identities = []
    for source, bound in zip(exact_sources(), proposal["exact_existing_sources"], strict=True):
        reviewed = {"verified_archive_sha256": bound["archive_sha256"],
                    "materialization_manifest_sha256": bound["materialization_manifest_sha256"]}
        identity = inventory_materialized(source, reviewed)
        if (identity["archive_size_bytes"] != bound["archive_size_bytes"]
                or identity["archive_sha256"] != bound["archive_sha256"]
                or identity["manifest_sha256"] != bound["materialization_manifest_sha256"]
                or identity["file_count"] != 95):
            raise PilotControlError("gdal_exact_materialization_drift")
        identities.append(identity)
    runtime = _runtime()
    receipt = {
        "schema_version": "1.0", "receipt_id": "NEPAL-M2-OPTICAL-GDAL-RECOVERY-002-FINAL-PREFLIGHT",
        "status": "pass_offline_exact_identity_no_pixel_decode", "checked_at_utc": now_utc(),
        "proposal_sha256": PROPOSAL_SHA256, "execution_gate_sha256": sha256_file(EXECUTION_GATE),
        "source_ids_in_order": list(binding["source_ids_in_order"]),
        "sources_in_order": identities, "aoi_ids": ids,
        "gdal_runtime": runtime, "available_memory_bytes_at_preflight": available,
        "network_or_credential_action": False, "raster_pixel_values_decoded": False,
        "source_or_old_attempt_mutated": False, "new_real_attempt_started": False,
    }
    write_new_json(FINAL_PREFLIGHT, receipt)
    return receipt


if __name__ == "__main__":
    try:
        print(json.dumps({"status": preflight()["status"]}))
    except BaseException as exc:
        code = exc.code if isinstance(exc, PilotControlError) else "gdal_final_preflight_unexpected"
        failure = ROOT / "records/readiness/m2-optical-gdal-header-pixel-recovery-002-final-preflight-failure.json"
        if not failure.exists():
            write_new_json(failure, {"status": "stopped", "safe_code": code,
                                     "at_utc": now_utc(), "exception_text_recorded": False})
        print(json.dumps({"status": "stopped", "safe_code": code}))
        raise SystemExit(20)
