#!/usr/bin/env python3
"""One reserved before-scene read in non-Git custody; no retry or network."""

from __future__ import annotations

import json
from typing import Any

from m2_optical_alternate_pair_002_control import (
    ATTEMPTS_ROOT, BEFORE_SOURCE, DATA_ROOT, FINAL_PREFLIGHT,
    PairControlError, attempt_path, now_utc, read_json, require_public_ci,
    sha256_file, write_new_json,
)


BEFORE_MANIFEST_SHA256 = "92fcfad15c70297dbc174c2ab470257196e21d232cb5ad131fba21b23ab8b542"
ATTEMPT = attempt_path("before_single_date_screen")


def _stage(name: str) -> None:
    write_new_json(ATTEMPT / f"stage-{name}.json", {"stage": name, "at_utc": now_utc()})


def run() -> dict[str, Any]:
    from m2_optical_alternate_pair_002_reader import inspect_materialized, screen_before_arrays
    from m2_optical_alternate_pair_002_preflight import (
        AOI, AOI_SHA256, HEADER, HEADER_SHA256, PIXEL, PIXEL_SHA256,
        SETTINGS, SETTINGS_SHA256,
    )
    from optical_input_readiness_core import validate_product_grid

    require_public_ci()
    preflight = read_json(FINAL_PREFLIGHT)
    if (preflight.get("status") != "pass_exact_no_payload_preflight_before_screen_only"
            or not ATTEMPT.is_dir()
            or any(not (ATTEMPT / name).is_file() for name in
                   ("started.json", "terminal-reserved.json", "cleanup-reserved.json"))):
        raise PairControlError("pair_before_worker_reservation_invalid")
    if not BEFORE_SOURCE.resolve(strict=True).is_relative_to(DATA_ROOT.resolve(strict=True)):
        raise PairControlError("pair_before_materialization_escaped_custody")
    if sha256_file(BEFORE_SOURCE / "materialization-manifest.json") != BEFORE_MANIFEST_SHA256:
        raise PairControlError("pair_before_materialization_manifest_drift")
    for path, expected in ((AOI, AOI_SHA256), (HEADER, HEADER_SHA256),
                           (PIXEL, PIXEL_SHA256), (SETTINGS, SETTINGS_SHA256)):
        if sha256_file(path) != expected:
            raise PairControlError("pair_frozen_aoi_or_scientific_contract_drift")
    _stage("identity")
    header_contract = read_json(HEADER)
    product, paths = inspect_materialized("M2-OPT-001", BEFORE_SOURCE,
                                          contract=header_contract)
    errors = validate_product_grid(product["descriptions"], header_contract)
    header = {
        "schema_version": "1.0", "source_id": "M2-OPT-001",
        "status": "pass_single_source_header_only" if not errors else "block",
        "errors": errors, "product": product,
        "pixel_values_decoded": False,
    }
    write_new_json(ATTEMPT / "header.json", header)
    if errors:
        return {"status": "block", "stage": "header",
                "header_status": "block", "screen_status": None}
    _stage("pixel_screen")
    screen = screen_before_arrays(paths)
    screen.update({"schema_version": "1.0", "checked_at_utc": now_utc(),
                   "before_manifest_sha256": BEFORE_MANIFEST_SHA256,
                   "pair_pixel_qa_or_change_analysis": False})
    write_new_json(ATTEMPT / "screen.json", screen)
    return {"status": "completed_single_date_screen",
            "stage": "pixel_screen", "header_status": header["status"],
            "screen_status": screen["status"]}


def main() -> int:
    stage = "child_bootstrap"
    try:
        _stage("child_bootstrap")
        stage = "identity_or_header"
        result = run()
        terminal = {"schema_version": "1.0", **result,
                    "completed_at_utc": now_utc(),
                    "exception_text_recorded": False,
                    "network_or_credential_action": False,
                    "automatic_retry": False,
                    "old_attempt_reused_or_mutated": False,
                    "baseline_or_change_analysis": False}
        write_new_json(ATTEMPT / "worker-terminal.json", terminal)
        return 0 if result["status"] == "completed_single_date_screen" else 20
    except BaseException as exc:
        safe_class = type(exc).__name__ if type(exc).__name__ in {
            "PairControlError", "ValueError", "RuntimeError", "OSError",
            "MemoryError", "PermissionError", "ImportError", "KeyError"} else "Exception"
        terminal = {"schema_version": "1.0", "status": "stopped",
                    "stage": stage, "safe_code": "pair_before_worker_failed",
                    "error_class": safe_class, "completed_at_utc": now_utc(),
                    "exception_text_recorded": False,
                    "network_or_credential_action": False,
                    "automatic_retry": False,
                    "old_attempt_reused_or_mutated": False,
                    "baseline_or_change_analysis": False}
        try:
            write_new_json(ATTEMPT / "worker-terminal.json", terminal)
        except BaseException:
            pass
        return 20


if __name__ == "__main__":
    raise SystemExit(main())
