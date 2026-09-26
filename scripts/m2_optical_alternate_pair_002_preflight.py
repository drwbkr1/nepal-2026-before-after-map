#!/usr/bin/env python3
"""One no-payload final preflight before the approved before-scene screen."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from m2_optical_alternate_pair_002_control import (
    APPROVAL_SHA256, ATTEMPTS_ROOT, BEFORE_SOURCE, BEFORE_TERMINAL,
    BUNDLE_SHA256, DATA_ROOT, EXECUTION_GATE, EXPECTED_ATTEMPTS,
    FINAL_PREFLIGHT, PROPOSAL_SHA256, ROOT, PairControlError, attempt_path,
    now_utc, require_public_ci, sha256_file, write_new_json,
)
from m2_optical_gdal_recovery_002_adapter import TARGET_GRID


AOI = ROOT / "config/aoi/approved-study-areas-epsg32645.json"
AOI_SHA256 = "3d6c9bb39fa9b3ffeddfb0048ddabf30ee4472c0006b78c5c7d58193693ac615"
HEADER = ROOT / "config/qa/optical-input-readiness-contract.json"
HEADER_SHA256 = "83327ebc03fb5a7b66152a77717354e4b88450b6f63a2734b5b4ceea6550f3b0"
PIXEL = ROOT / "config/qa/pixel-readiness-contract.json"
PIXEL_SHA256 = "5a66ae11288813868f362c342027ce0e4850d435dfbb2cfec3f5098b17d123e2"
SETTINGS = ROOT / "config/qa/optical-pixel-readiness-contract-001.json"
SETTINGS_SHA256 = "2410955b686d545a39f1962c2924b8515cc130c3db9bbae5fe314f1e5bd04fa7"
ARCGIS_PYTHON = Path(r"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe")


def preflight() -> dict[str, Any]:
    gate = require_public_ci()
    if FINAL_PREFLIGHT.exists() or BEFORE_TERMINAL.exists():
        raise PairControlError("pair_final_preflight_or_terminal_collision")
    if any(attempt_path(kind).exists() for kind in EXPECTED_ATTEMPTS):
        raise PairControlError("pair_exact_attempt_root_collision")
    if not DATA_ROOT.is_dir() or not BEFORE_SOURCE.is_dir() or not (BEFORE_SOURCE / "materialization-manifest.json").is_file():
        raise PairControlError("pair_exact_before_materialization_missing")
    if not ARCGIS_PYTHON.is_file():
        raise PairControlError("pair_arcgis_python_missing")
    for path, digest in ((AOI, AOI_SHA256), (HEADER, HEADER_SHA256),
                         (PIXEL, PIXEL_SHA256), (SETTINGS, SETTINGS_SHA256)):
        if sha256_file(path) != digest:
            raise PairControlError("pair_frozen_aoi_or_scientific_contract_drift")
    aoi = json.loads(AOI.read_text(encoding="utf-8"))
    if (aoi.get("spatialReference", {}).get("wkid") != 32645
            or {feature["attributes"]["AOI_ID"] for feature in aoi["features"]}
            != {"AOI-OVERVIEW", "AOI-SOURCE", "AOI-UPPER-CORRIDOR"}
            or TARGET_GRID != {"xmin": 273300.0, "ymin": 3070220.0,
                               "xmax": 367820.0, "ymax": 3149220.0,
                               "rows": 3950, "columns": 4726,
                               "cell_size_m": 20.0, "wkid": 32645}):
        raise PairControlError("pair_aoi_or_grid_drift")
    free = shutil.disk_usage(ATTEMPTS_ROOT.parent if ATTEMPTS_ROOT.parent.exists() else DATA_ROOT).free
    if free < 5 * 1024**3:
        raise PairControlError("pair_insufficient_free_disk")
    receipt = {
        "schema_version": "1.0",
        "status": "pass_exact_no_payload_preflight_before_screen_only",
        "checked_at_utc": now_utc(),
        "proposal_sha256": PROPOSAL_SHA256,
        "bundle_sha256": BUNDLE_SHA256,
        "approval_sha256": APPROVAL_SHA256,
        "public_execution_gate_sha256": sha256_file(EXECUTION_GATE),
        "public_ci_run_id": gate["public_ci_run_id"],
        "aoi_sha256": AOI_SHA256,
        "scientific_contract_sha256": {"header": HEADER_SHA256,
                                        "pixel": PIXEL_SHA256, "settings": SETTINGS_SHA256},
        "exact_attempt_ids_absent": list(EXPECTED_ATTEMPTS.values()),
        "before_source_materialization_present": True,
        "before_source_content_hashed_or_decoded": False,
        "external_custody_content_read": False,
        "source_online_and_terms_recheck_required_before_acquisition": True,
        "available_disk_bytes": free,
        "new_real_attempt_started": False,
        "network_or_credential_action": False,
    }
    write_new_json(FINAL_PREFLIGHT, receipt)
    return receipt


if __name__ == "__main__":
    try:
        result = preflight()
        print(json.dumps({"status": result["status"]}))
    except BaseException as exc:
        code = exc.code if isinstance(exc, PairControlError) else "pair_final_preflight_unexpected"
        print(json.dumps({"status": "stopped", "safe_code": code,
                          "exception_text_recorded": False}))
        raise SystemExit(20)
