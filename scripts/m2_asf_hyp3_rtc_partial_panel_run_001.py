#!/usr/bin/env python3
"""One gated local ArcGIS panel attempt from the exact verified partial pair.

This visual-only route creates no change raster, polygon or scientific claim.
The saved APRX is reopened and exported in a distinct ArcGIS process.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from m2_asf_hyp3_rtc_acquire_after_partial_001 import DATA_ROOT, SUBMISSION_REF
from m2_asf_hyp3_rtc_after_descriptor_core_001 import submission_view
from m2_asf_hyp3_rtc_after_header_001 import (
    APPROVAL_REF, APPROVAL_SHA, _json, _now, _safe_dir, _safe_file,
    _sha, _write_json,
)
from m2_asf_hyp3_rtc_core_001 import ROOT, RouteStop
from m2_asf_hyp3_rtc_partial_pair_map_001 import build_local_panel
from m2_asf_hyp3_rtc_partial_pair_stage_001 import (
    AOI_REF, AOI_SHA256, CONTRACT_REF, CONTRACT_SHA256,
    RIGHTS_REF as STAGE_RIGHTS_REF,
    BEFORE_SOURCE, AFTER_SOURCE,
)
from m2_asf_hyp3_rtc_partial_pair_stage_io_001 import DISPLAY_NAMES


STAGE_REF = "m2-asf-hyp3-rtc-partial-pair-stage-001/attempt-001/terminal.json"
STAGE_DISPLAY_REF = "m2-asf-hyp3-rtc-partial-pair-stage-001/attempt-001/display"
RIGHTS_REF = "records/readiness/m2-asf-hyp3-rtc-partial-panel-credit-review-001.json"
GATE_REF = "records/readiness/m2-asf-hyp3-rtc-partial-panel-001-implementation-gate.json"
PREFLIGHT_REF = "records/readiness/m2-asf-hyp3-rtc-partial-panel-001-preflight.json"
ATTEMPT_ROOT = DATA_ROOT / "m2-asf-hyp3-rtc-partial-panel-001" / "attempt-001"
REOPEN_SCRIPT = ROOT / "scripts/m2_asf_hyp3_rtc_partial_panel_reopen_001.py"
IMPLEMENTATION_FILES = (
    "scripts/m2_asf_hyp3_rtc_partial_panel_run_001.py",
    "scripts/m2_asf_hyp3_rtc_partial_panel_reopen_001.py",
    "scripts/m2_asf_hyp3_rtc_partial_pair_map_001.py",
    "scripts/m2_asf_hyp3_rtc_partial_panel_audit_001.py",
    "scripts/validate_m2_asf_hyp3_rtc_partial_pair_arcgis_synthetic_001.py",
    "tests/test_m2_asf_hyp3_rtc_partial_panel_run_001.py",
)


def _stage_view(stage: dict) -> tuple[dict, dict[str, float]]:
    if (stage.get("status") != "pass_common_valid_for_local_partial_visual_only"
            or stage.get("source_ids") != [BEFORE_SOURCE, AFTER_SOURCE]
            or stage.get("provider_zip_mutated") is not False
            or stage.get("registration_measured") is not False
            or stage.get("scientific_admission") is not False
            or stage.get("map_or_export_created") is not False):
        raise RouteStop("partial_panel_stage_terminal_invalid")
    result = stage.get("pair_stage_result")
    if (not isinstance(result, dict)
            or result.get("status") != "pass_common_valid_for_local_partial_visual_only"
            or result.get("wkid") != 32645
            or result.get("display_polarization") != "VV"
            or result.get("display_units") != "gamma0 dB"
            or result.get("resampling_performed") is not False
            or result.get("registration_measured") is not False
            or result.get("scientific_admission_authorized") is not False):
        raise RouteStop("partial_panel_stage_result_invalid")
    rasters = result.get("display_rasters")
    if (not isinstance(rasters, list) or len(rasters) != 2
            or [item.get("name") for item in rasters if isinstance(item, dict)]
            != list(DISPLAY_NAMES)
            or any(type(item.get("size_bytes")) is not int or item["size_bytes"] <= 0
                   or not isinstance(item.get("sha256"), str)
                   or len(item["sha256"]) != 64 for item in rasters)):
        raise RouteStop("partial_panel_stage_rasters_invalid")
    rows = result.get("aoi_results")
    if (not isinstance(rows, list) or len(rows) != 2
            or [row.get("aoi_id") for row in rows if isinstance(row, dict)]
            != ["AOI-SOURCE", "AOI-UPPER-CORRIDOR"]
            or any(row.get("status") != "pass_common_valid_for_local_partial_visual_only"
                   or type(row.get("common_valid_fraction_of_aoi")) not in (int, float)
                   or not .2 <= row["common_valid_fraction_of_aoi"] <= 1.
                   or row.get("unknown_mask_cells_either_date") != 0
                   for row in rows)):
        raise RouteStop("partial_panel_stage_overlap_invalid")
    return result, {row["aoi_id"]: row["common_valid_fraction_of_aoi"]
                    for row in rows}


def require_release(root: Path = ROOT, data_root: Path = DATA_ROOT,
                    attempt_root: Path = ATTEMPT_ROOT) -> tuple[dict, dict, tuple[Path, Path], dict[str, float]]:
    """Verify exact receipts and hash-bound gates before opening ArcGIS."""
    paths = {
        "approval": root / APPROVAL_REF,
        "rights": root / RIGHTS_REF,
        "stage_rights": root / STAGE_RIGHTS_REF,
        "aoi": root / AOI_REF,
        "contract": root / CONTRACT_REF,
        "stage": data_root / STAGE_REF,
        "submission": data_root / SUBMISSION_REF,
        "gate": root / GATE_REF,
        "preflight": root / PREFLIGHT_REF,
    }
    if any(not _safe_file(path) for path in paths.values()):
        raise RouteStop("partial_panel_required_path_invalid")
    records = {key: _json(path) for key, path in paths.items()
               if key not in {"aoi", "contract"}}
    approval, rights, stage_rights, stage, submission, gate, preflight = (
        records[key] for key in ("approval", "rights", "stage_rights", "stage",
                                 "submission", "gate", "preflight")
    )
    stage_result, coverage = _stage_view(stage)
    stage_root = data_root / STAGE_DISPLAY_REF
    rasters = tuple(stage_root / name for name in DISPLAY_NAMES)
    if (not _safe_dir(data_root) or not _safe_dir(stage_root)
            or any(not _safe_file(path) for path in rasters)
            or attempt_root.parent.parent.resolve() != data_root.resolve()
            or attempt_root.parent.is_symlink()
            or (attempt_root.parent.exists() and not _safe_dir(attempt_root.parent))
            or attempt_root.exists() or attempt_root.is_symlink()):
        raise RouteStop("partial_panel_path_or_attempt_invalid")
    files = gate.get("bindings", {}).get("implementation_file_sha256")
    credits = rights.get("local_panel_credit_line")
    try:
        job = submission_view(submission)["job_id"]
        valid = (
            _sha(paths["approval"]) == APPROVAL_SHA
            and approval.get("decision") == "approve"
            and approval.get("authority", {}).get(
                "conditional_local_EPSG_32645_partial_pair_panel_and_fresh_process_export") is True
            and _sha(paths["aoi"]) == AOI_SHA256
            and _sha(paths["contract"]) == CONTRACT_SHA256
            and stage.get("after_job_id") == job
            and stage_rights.get("status") == "pass_local_rtc_vv_visual_display_only"
            and stage_rights.get("local_VV_display") is True
            and stage_rights.get("DEM_display_or_export") is False
            and stage_rights.get("public_derived_pixels") is False
            and rights.get("status") == "pass_local_rtc_vv_visual_display_only"
            and rights.get("bindings", {}).get("parent_rights_review_sha256")
                == _sha(paths["stage_rights"])
            and rights.get("bindings", {}).get("stage_terminal_sha256")
                == _sha(paths["stage"])
            and rights.get("local_VV_display") is True
            and rights.get("DEM_display_or_export") is False
            and rights.get("public_derived_pixels") is False
            and isinstance(credits, str) and 0 < len(credits) <= 480
            and all(term in credits.casefold() for term in
                    ("asf", "esa", "doi.org/10.5281/zenodo.3962581",
                     "doi.org/10.5281/zenodo.3962936"))
            and "\n" not in credits and "\r" not in credits
            and all(path.stat().st_size == item["size_bytes"]
                    and _sha(path) == item["sha256"]
                    for path, item in zip(rasters, stage_result["display_rasters"], strict=True))
            and gate.get("status") == "pass_partial_panel_implementation_public_ci_only"
            and gate.get("public_ci", {}).get("conclusion") == "success"
            and gate.get("bindings", {}).get("approval_sha256") == APPROVAL_SHA
            and gate.get("bindings", {}).get("rights_review_sha256") == _sha(paths["rights"])
            and gate.get("bindings", {}).get("stage_terminal_sha256") == _sha(paths["stage"])
            and gate.get("bindings", {}).get("submission_sha256") == _sha(paths["submission"])
            and gate.get("bindings", {}).get("aoi_sha256") == AOI_SHA256
            and gate.get("bindings", {}).get("contract_sha256") == CONTRACT_SHA256
            and isinstance(files, dict) and set(files) == set(IMPLEMENTATION_FILES)
            and all(_sha(root / ref) == files[ref] for ref in IMPLEMENTATION_FILES)
            and preflight.get("status") == "pass_partial_panel_no_content"
            and preflight.get("bindings", {}).get("implementation_gate_sha256")
                == _sha(paths["gate"])
            and preflight.get("bindings", {}).get("stage_terminal_sha256")
                == _sha(paths["stage"])
            and preflight.get("assertions", {}).get("attempt_absent") is True
            and preflight.get("assertions", {}).get("no_map_or_export_created") is True
        )
    except (OSError, ValueError, TypeError, KeyError):
        raise RouteStop("partial_panel_release_unavailable") from None
    if not valid:
        raise RouteStop("partial_panel_not_released")
    return stage, rights, rasters, coverage


def _fresh_reopen(output: Path, root: Path = ROOT) -> dict:
    """Return only sanitized output from a distinct ArcGIS Python process."""
    try:
        completed = subprocess.run(
            [sys.executable, str(root / "scripts/m2_asf_hyp3_rtc_partial_panel_reopen_001.py"),
             str(output)],
            cwd=root, capture_output=True, text=True, timeout=900, check=False,
        )
        result = json.loads(completed.stdout)
        if (completed.returncode != 0
                or result.get("status") != "pass_local_partial_panel_fresh_reopen_and_audit"):
            raise RouteStop("partial_panel_fresh_reopen_failed")
        return result
    except (OSError, ValueError, subprocess.TimeoutExpired):
        raise RouteStop("partial_panel_fresh_reopen_failed") from None


def run_once(stage: dict, rights: dict, rasters: tuple[Path, Path],
             coverage: dict[str, float], attempt_root: Path = ATTEMPT_ROOT,
             *, controlled_root: Path = DATA_ROOT,
             build=build_local_panel, reopen=_fresh_reopen,
             root: Path = ROOT) -> dict:
    """Reserve once; preserve partial files and terminal on every outcome."""
    if (not _safe_dir(controlled_root)
            or attempt_root.parent.parent.resolve() != controlled_root.resolve()
            or attempt_root.parent.is_symlink()
            or attempt_root.exists() or attempt_root.is_symlink()):
        raise RouteStop("partial_panel_attempt_collision")
    try:
        attempt_root.parent.mkdir(parents=True, exist_ok=True)
        if not _safe_dir(attempt_root.parent):
            raise RouteStop("partial_panel_attempt_parent_invalid")
        attempt_root.mkdir(exist_ok=False)
    except RouteStop:
        raise
    except OSError:
        raise RouteStop("partial_panel_attempt_reservation_failed") from None
    _write_json(attempt_root / "started.json", {
        "status": "partial_panel_reserved", "started_at_utc": _now(),
        "source_ids": [BEFORE_SOURCE, AFTER_SOURCE],
        "after_job_id": stage.get("after_job_id"),
        "change_analysis_or_attribution": False,
        "public_pixel_publication": False,
    })
    try:
        result, measured = _stage_view(stage)
        if measured != coverage or stage.get("after_job_id") is None:
            raise RouteStop("partial_panel_stage_binding_mismatch")
        for path, item in zip(rasters, result["display_rasters"], strict=True):
            if (not _safe_file(path) or path.name != item["name"]
                    or path.stat().st_size != item["size_bytes"]
                    or _sha(path) != item["sha256"]):
                raise RouteStop("partial_panel_stage_raster_drift")
        prior = [path.stat() for path in rasters]
        output = attempt_root / "panel"
        built = build(rasters[0], rasters[1], output,
                      common_valid_by_aoi=coverage,
                      credits_and_dois=rights["local_panel_credit_line"])
        if built.get("status") != "built_local_partial_visual_pending_fresh_reopen":
            raise RouteStop("partial_panel_build_invalid")
        reopened = reopen(output, root)
        if (reopened.get("status") != "pass_local_partial_panel_fresh_reopen_and_audit"
                or reopened.get("audit", {}).get("status")
                    != "pass_local_partial_panel_artifact_audit_only"):
            raise RouteStop("partial_panel_fresh_reopen_invalid")
        if any((old.st_size, old.st_mtime_ns, old.st_ino)
               != (new.st_size, new.st_mtime_ns, new.st_ino)
               for old, new in zip(prior, (path.stat() for path in rasters), strict=True)):
            raise RouteStop("partial_panel_stage_raster_mutated")
        terminal = {
            "status": "pass_local_partial_panel_verified_visual_only",
            "finished_at_utc": _now(), "source_ids": [BEFORE_SOURCE, AFTER_SOURCE],
            "after_job_id": stage["after_job_id"], "coverage": coverage,
            "build": built, "fresh_reopen": reopened,
            "source_or_stage_raster_mutated": False,
            "registration_measured": False, "scientific_admission": False,
            "change_analysis_or_attribution": False,
            "public_pixel_publication": False,
        }
    except RouteStop as exc:
        terminal = {"status": "stopped_partial_panel_no_automatic_retry",
                    "code": exc.code, "finished_at_utc": _now(),
                    "partial_output_retained_for_review": True,
                    "scientific_admission": False,
                    "public_pixel_publication": False}
    except BaseException:
        terminal = {"status": "stopped_partial_panel_no_automatic_retry",
                    "code": "partial_panel_unexpected_failure",
                    "finished_at_utc": _now(),
                    "partial_output_retained_for_review": True,
                    "scientific_admission": False,
                    "public_pixel_publication": False}
    _write_json(attempt_root / "terminal.json", terminal)
    return terminal


def main() -> int:
    try:
        stage, rights, rasters, coverage = require_release()
        if sys.argv[1:] == ["--check-release"]:
            print(json.dumps({"status": "pass_partial_panel_release_no_map_read"}))
            return 0
        if sys.argv[1:]:
            raise RouteStop("partial_panel_arguments_invalid")
        terminal = run_once(stage, rights, rasters, coverage)
        print(json.dumps({"status": terminal["status"],
                          "code": terminal.get("code"),
                          "scientific_admission": False}, sort_keys=True))
        return 12 if terminal["status"].startswith("stopped_") else 0
    except RouteStop as exc:
        print(json.dumps({"status": "stopped", "code": exc.code,
                          "scientific_admission": False}, sort_keys=True))
        return 12
    except BaseException:
        print(json.dumps({"status": "stopped",
                          "code": "partial_panel_unexpected_failure",
                          "scientific_admission": False}, sort_keys=True))
        return 20


if __name__ == "__main__":
    raise SystemExit(main())
