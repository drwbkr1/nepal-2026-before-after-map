#!/usr/bin/env python3
"""Gated one-attempt AOI pixel QA of exact ASF after RTC product.

Only VV, VH and layover/shadow windows within the two approved event AOIs are
read. The DEM, other raster pixels, pair overlap, change and map are untouched.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from m2_asf_hyp3_rtc_acquire_after_partial_001 import DATA_ROOT, SUBMISSION_REF
from m2_asf_hyp3_rtc_after_descriptor_core_001 import SOURCE_ID, submission_view
from m2_asf_hyp3_rtc_after_header_001 import (
    ACQUISITION_REF, APPROVAL_REF, APPROVAL_SHA, METADATA_REVIEW_REF,
    SOURCE_GATE_REF, SOURCE_GATE_SHA, _json, _now, _safe_dir, _safe_file,
    _sha, _write_json,
)
from m2_asf_hyp3_rtc_after_pixel_disposition_001 import (
    EVENT_AOIS, evaluate_after_aoi_results,
)
from m2_asf_hyp3_rtc_core_001 import ROOT, RouteStop
from m2_asf_hyp3_rtc_header_core_001 import inspect_raster_headers
from m2_asf_hyp3_rtc_product_header_001 import describe_vsi
from m2_asf_hyp3_rtc_product_pixel_001 import (
    AOI_REF, AOI_SHA256, CONTRACT_REF, CONTRACT_SHA256,
    _load_aois, scan_one_aoi,
)
from pixel_qa_core import load_contract


HEADER_REF = "m2-asf-hyp3-rtc-after-header-001/attempt-001/terminal.json"
GATE_REF = "records/readiness/m2-asf-hyp3-rtc-after-pixel-001-implementation-gate.json"
PREFLIGHT_REF = "records/readiness/m2-asf-hyp3-rtc-after-pixel-001-preflight.json"
ATTEMPT_ROOT = DATA_ROOT / "m2-asf-hyp3-rtc-after-pixel-001" / "attempt-001"
IMPLEMENTATION_FILES = (
    "scripts/m2_asf_hyp3_rtc_after_pixel_001.py",
    "scripts/m2_asf_hyp3_rtc_after_pixel_disposition_001.py",
    "scripts/m2_asf_hyp3_rtc_product_pixel_001.py",
    "scripts/m2_asf_hyp3_rtc_pixel_core_001.py",
    "scripts/m2_asf_hyp3_rtc_product_header_001.py",
    "scripts/m2_asf_hyp3_rtc_header_core_001.py",
    "scripts/validate_m2_asf_hyp3_rtc_after_pixel_001.py",
    "tests/test_m2_asf_hyp3_rtc_after_pixel_001.py",
)


def scan_after_product(archive: Path, header: dict, aois: list,
                       contract: dict) -> list[dict]:
    """Verify frozen headers, then read only three AOI raster windows."""
    from osgeo import gdal

    gdal.UseExceptions()
    base = archive.stem
    members = {"vv": f"{base}/{base}_VV.tif",
               "vh": f"{base}/{base}_VH.tif",
               "ls_map": f"{base}/{base}_ls_map.tif"}
    actual = {role: describe_vsi(archive, member)
              for role, member in members.items()}
    frozen = header.get("headers")
    if (not isinstance(frozen, dict)
            or any(actual[role] != frozen.get(role) for role in members)):
        raise RouteStop("after_pixel_header_drift")
    if inspect_raster_headers(SOURCE_ID, frozen)["status"] != "pass_header_descriptor_rules_only":
        raise RouteStop("after_pixel_frozen_header_invalid")
    datasets = {}
    try:
        for role, member in members.items():
            vsi = "/vsizip/" + archive.as_posix() + "/" + member
            dataset = gdal.OpenEx(vsi, gdal.OF_RASTER)
            if dataset is None:
                raise RouteStop("after_pixel_vsi_open_failed")
            datasets[role] = dataset
        return [scan_one_aoi(aoi_id, ring, datasets["vv"], datasets["vh"],
                             datasets["ls_map"], contract)
                for aoi_id, ring in aois]
    finally:
        datasets.clear()


def require_release(root: Path = ROOT, data_root: Path = DATA_ROOT,
                    attempt_root: Path = ATTEMPT_ROOT) -> tuple[dict, dict, Path, str]:
    """Require exact published gates before any ZIP or pixel read."""
    paths = {
        "approval": root / APPROVAL_REF,
        "source_gate": root / SOURCE_GATE_REF,
        "metadata_review": root / METADATA_REVIEW_REF,
        "gate": root / GATE_REF,
        "preflight": root / PREFLIGHT_REF,
        "submission": data_root / SUBMISSION_REF,
        "acquisition": data_root / ACQUISITION_REF,
        "header": data_root / HEADER_REF,
    }
    if any(not _safe_file(path) for path in paths.values()):
        raise RouteStop("after_pixel_required_path_invalid")
    records = {key: _json(path) for key, path in paths.items()}
    approval, source_gate, review, gate, preflight, submission, acquisition, header = (
        records[key] for key in ("approval", "source_gate", "metadata_review",
                                 "gate", "preflight", "submission",
                                 "acquisition", "header")
    )
    view = submission_view(submission)
    filename = acquisition.get("product_filename")
    if (not isinstance(filename, str) or filename != Path(filename).name
            or not filename.endswith(".zip")):
        raise RouteStop("after_pixel_product_name_invalid")
    archive = data_root / "m2-asf-hyp3-rtc-products-after-partial-001" / filename
    if (not _safe_dir(data_root) or not _safe_dir(archive.parent)
            or not _safe_file(archive)
            or attempt_root.parent.parent.resolve() != data_root.resolve()
            or attempt_root.parent.is_symlink()
            or (attempt_root.parent.exists() and not _safe_dir(attempt_root.parent))
            or attempt_root.exists() or attempt_root.is_symlink()):
        raise RouteStop("after_pixel_path_or_attempt_invalid")
    files = gate.get("bindings", {}).get("implementation_file_sha256")
    try:
        valid = (
            _sha(paths["approval"]) == APPROVAL_SHA
            and approval.get("decision") == "approve"
            and approval.get("authority", {}).get(
                "conditional_one_zip_acquisition_integrity_provenance_rights_header_and_pixel_qa") is True
            and _sha(paths["source_gate"]) == SOURCE_GATE_SHA
            and source_gate.get("decision", {}).get("status") == "ready"
            and _sha(root / AOI_REF) == AOI_SHA256
            and _sha(root / CONTRACT_REF) == CONTRACT_SHA256
            and acquisition.get("status") == "pass_local_zip_promoted_no_replace"
            and acquisition.get("source_id") == SOURCE_ID
            and acquisition.get("job_id") == view["job_id"]
            and acquisition.get("archive_integrity_verified") is True
            and acquisition.get("geotiff_headers_or_pixels_read") is False
            and type(acquisition.get("archive_size_bytes")) is int
            and archive.stat().st_size == acquisition["archive_size_bytes"]
            and review.get("status") == "pass_after_metadata_for_header_and_pixel_qa_only"
            and review.get("source_id") == SOURCE_ID
            and review.get("job_id") == view["job_id"]
            and review.get("bindings", {}).get("archive_sha256") == acquisition.get("archive_sha256")
            and review.get("findings", {}).get("layover_shadow_semantics_reviewed") is True
            and review.get("rights", {}).get("local_vv_vh_and_mask_inspection") is True
            and review.get("rights", {}).get("DEM_display_or_export") is False
            and header.get("status") == "pass_after_headers_for_local_pixel_qa_only"
            and header.get("source_id") == SOURCE_ID
            and header.get("job_id") == view["job_id"]
            and header.get("archive_sha256_verified_current") is True
            and header.get("pixels_read") is False
            and gate.get("status") == "pass_after_pixel_implementation_public_ci_only"
            and gate.get("public_ci", {}).get("conclusion") == "success"
            and gate.get("bindings", {}).get("approval_sha256") == APPROVAL_SHA
            and gate.get("bindings", {}).get("source_gate_sha256") == SOURCE_GATE_SHA
            and gate.get("bindings", {}).get("submission_terminal_sha256") == _sha(paths["submission"])
            and gate.get("bindings", {}).get("acquisition_terminal_sha256") == _sha(paths["acquisition"])
            and gate.get("bindings", {}).get("metadata_review_sha256") == _sha(paths["metadata_review"])
            and gate.get("bindings", {}).get("header_terminal_sha256") == _sha(paths["header"])
            and gate.get("bindings", {}).get("aoi_sha256") == AOI_SHA256
            and gate.get("bindings", {}).get("pixel_contract_sha256") == CONTRACT_SHA256
            and isinstance(files, dict) and set(files) == set(IMPLEMENTATION_FILES)
            and all(_sha(root / ref) == files[ref] for ref in IMPLEMENTATION_FILES)
            and preflight.get("status") == "pass_after_pixel_no_content"
            and preflight.get("bindings", {}).get("implementation_gate_sha256") == _sha(paths["gate"])
            and preflight.get("bindings", {}).get("acquisition_terminal_sha256") == _sha(paths["acquisition"])
            and preflight.get("bindings", {}).get("header_terminal_sha256") == _sha(paths["header"])
            and preflight.get("assertions", {}).get("attempt_absent") is True
            and preflight.get("assertions", {}).get("no_product_pixels_read") is True
        )
    except (OSError, TypeError, ValueError):
        raise RouteStop("after_pixel_release_unavailable") from None
    if not valid:
        raise RouteStop("after_pixel_not_released")
    return acquisition, header, archive, view["job_id"]


def inspect_once(acquisition: dict, header: dict, archive: Path,
                 attempt_root: Path = ATTEMPT_ROOT, *, controlled_root: Path = DATA_ROOT,
                 job_id: str, scan=scan_after_product, root: Path = ROOT) -> dict:
    """Reserve once; keep a separate after-date disposition on any outcome."""
    if (not _safe_dir(controlled_root)
            or attempt_root.parent.parent.resolve() != controlled_root.resolve()
            or attempt_root.parent.is_symlink()
            or attempt_root.exists() or attempt_root.is_symlink()):
        raise RouteStop("after_pixel_attempt_collision")
    try:
        attempt_root.parent.mkdir(parents=True, exist_ok=True)
        if not _safe_dir(attempt_root.parent):
            raise RouteStop("after_pixel_attempt_parent_invalid")
        attempt_root.mkdir(exist_ok=False)
    except RouteStop:
        raise
    except OSError:
        raise RouteStop("after_pixel_attempt_reservation_failed") from None
    _write_json(attempt_root / "started.json", {
        "status": "after_two_aoi_pixel_qa_reserved", "source_id": SOURCE_ID,
        "job_id": job_id, "started_at_utc": _now(),
        "registration_measured": False, "archive_mutated": False,
    })
    try:
        if (acquisition.get("source_id") != SOURCE_ID
                or acquisition.get("job_id") != job_id
                or not _safe_file(archive)
                or archive.name != acquisition.get("product_filename")
                or archive.stat().st_size != acquisition.get("archive_size_bytes")
                or _sha(archive) != acquisition.get("archive_sha256")):
            raise RouteStop("after_pixel_archive_identity_mismatch")
        before = archive.stat()
        aois = _load_aois(root)
        if _sha(root / CONTRACT_REF) != CONTRACT_SHA256:
            raise RouteStop("after_pixel_contract_hash_mismatch")
        contract = load_contract(root / CONTRACT_REF)
        results = scan(archive, header, aois, contract)
        disposition = evaluate_after_aoi_results(results, contract)
        after = archive.stat()
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (
                after.st_size, after.st_mtime_ns, after.st_ino):
            raise RouteStop("after_pixel_archive_changed_during_read")
        terminal = {
            "status": disposition["status"],
            "source_id": SOURCE_ID, "job_id": job_id,
            "finished_at_utc": _now(), "aoi_results": results,
            "disposition": disposition,
            "archive_sha256_verified_current": True,
            "VV_VH_layover_shadow_AOI_pixels_read": True,
            "DEM_pixels_read": False, "registration_measured": False,
            "archive_mutated": False, "arcgis_map_ready": False,
            "baseline_admission_authorized": False,
            "change_analysis_authorized": False,
        }
    except RouteStop as exc:
        terminal = {"status": "stopped_after_pixel_no_automatic_retry",
                    "code": exc.code, "source_id": SOURCE_ID,
                    "job_id": job_id, "finished_at_utc": _now(),
                    "pixel_read_status": "indeterminate_on_failure",
                    "archive_mutated": False, "arcgis_map_ready": False}
    except BaseException:
        terminal = {"status": "stopped_after_pixel_no_automatic_retry",
                    "code": "after_pixel_unexpected_failure", "source_id": SOURCE_ID,
                    "job_id": job_id, "finished_at_utc": _now(),
                    "pixel_read_status": "indeterminate_on_failure",
                    "archive_mutated": False, "arcgis_map_ready": False}
    _write_json(attempt_root / "terminal.json", terminal)
    return terminal


def main() -> int:
    try:
        acquisition, header, archive, job_id = require_release()
        if sys.argv[1:] == ["--check-release"]:
            print(json.dumps({"status": "pass_after_pixel_release_no_product_read"}))
            return 0
        if sys.argv[1:]:
            raise RouteStop("after_pixel_arguments_invalid")
        result = inspect_once(acquisition, header, archive, job_id=job_id)
        print(json.dumps({"status": result["status"], "code": result.get("code"),
                          "source_id": SOURCE_ID, "arcgis_map_ready": False},
                         sort_keys=True))
        return 0 if result["status"] != "stopped_after_pixel_no_automatic_retry" else 12
    except RouteStop as exc:
        print(json.dumps({"status": "stopped", "code": exc.code,
                          "arcgis_map_ready": False}, sort_keys=True))
        return 12
    except BaseException:
        print(json.dumps({"status": "stopped", "code": "after_pixel_unexpected_failure",
                          "arcgis_map_ready": False}, sort_keys=True))
        return 20


if __name__ == "__main__":
    raise SystemExit(main())
