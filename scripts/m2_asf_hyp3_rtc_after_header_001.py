#!/usr/bin/env python3
"""Gated, single-attempt six-raster header inspection for exact after RTC ZIP.

No provider ZIP is opened until a separate metadata review, public implementation
gate, and fresh no-content preflight bind its verified acquisition. GDAL reads
dataset descriptors through /vsizip/ only; this worker never reads band values.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from m2_asf_hyp3_rtc_acquire_after_partial_001 import DATA_ROOT, SUBMISSION_REF
from m2_asf_hyp3_rtc_after_descriptor_core_001 import SOURCE_ID, submission_view
from m2_asf_hyp3_rtc_after_metadata_001 import (
    ACQUISITION_REF, APPROVAL_REF, APPROVAL_SHA,
    _json, _now, _safe_dir, _safe_file, _sha, _write_json,
)
from m2_asf_hyp3_rtc_core_001 import ROOT, RouteStop
from m2_asf_hyp3_rtc_header_core_001 import inspect_raster_headers
from m2_asf_hyp3_rtc_package_core_001 import inspect_member_names
from m2_asf_hyp3_rtc_product_header_001 import ROLE_SUFFIX, describe_vsi


SOURCE_GATE_REF = "records/source-gates/m2-asf-hyp3-rtc-processing-source-gate-001.json"
SOURCE_GATE_SHA = "7f1af5e46f9b1cba3753383b686a68618c7694b53a4be07d612b6df6045bd8a4"
METADATA_REF = "m2-asf-hyp3-rtc-after-metadata-001/attempt-001/terminal.json"
METADATA_REVIEW_REF = "records/readiness/m2-asf-hyp3-rtc-after-metadata-001-local-review.json"
GATE_REF = "records/readiness/m2-asf-hyp3-rtc-after-header-001-implementation-gate.json"
PREFLIGHT_REF = "records/readiness/m2-asf-hyp3-rtc-after-header-001-preflight.json"
ATTEMPT_ROOT = DATA_ROOT / "m2-asf-hyp3-rtc-after-header-001" / "attempt-001"
IMPLEMENTATION_FILES = (
    "scripts/m2_asf_hyp3_rtc_after_header_001.py",
    "scripts/validate_m2_asf_hyp3_rtc_after_header_001.py",
    "tests/test_m2_asf_hyp3_rtc_after_header_001.py",
)


def require_release(root: Path = ROOT, data_root: Path = DATA_ROOT,
                    attempt_root: Path = ATTEMPT_ROOT) -> tuple[dict, Path, str]:
    """Validate exact gates without opening the archive or any raster."""
    paths = {
        "approval": root / APPROVAL_REF,
        "source_gate": root / SOURCE_GATE_REF,
        "review": root / METADATA_REVIEW_REF,
        "gate": root / GATE_REF,
        "preflight": root / PREFLIGHT_REF,
        "submission": data_root / SUBMISSION_REF,
        "acquisition": data_root / ACQUISITION_REF,
        "metadata": data_root / METADATA_REF,
    }
    if any(not _safe_file(path) for path in paths.values()):
        raise RouteStop("after_header_required_path_invalid")
    records = {key: _json(path) for key, path in paths.items()}
    approval, source_gate, review, gate, preflight, submission, acquisition, metadata = (
        records[key] for key in ("approval", "source_gate", "review", "gate",
                                 "preflight", "submission", "acquisition", "metadata")
    )
    view = submission_view(submission)
    filename = acquisition.get("product_filename")
    if (not isinstance(filename, str) or filename != Path(filename).name
            or not filename.endswith(".zip")):
        raise RouteStop("after_header_product_name_invalid")
    archive = data_root / "m2-asf-hyp3-rtc-products-after-partial-001" / filename
    if (not _safe_dir(data_root) or not _safe_dir(archive.parent)
            or not _safe_file(archive)
            or attempt_root.parent.parent.resolve() != data_root.resolve()
            or attempt_root.parent.is_symlink()
            or (attempt_root.parent.exists() and not _safe_dir(attempt_root.parent))
            or attempt_root.exists() or attempt_root.is_symlink()):
        raise RouteStop("after_header_path_or_attempt_invalid")
    files = gate.get("bindings", {}).get("implementation_file_sha256")
    try:
        valid = (
            _sha(paths["approval"]) == APPROVAL_SHA
            and approval.get("decision") == "approve"
            and approval.get("authority", {}).get(
                "conditional_one_zip_acquisition_integrity_provenance_rights_header_and_pixel_qa") is True
            and _sha(paths["source_gate"]) == SOURCE_GATE_SHA
            and source_gate.get("decision", {}).get("status") == "ready"
            and acquisition.get("status") == "pass_local_zip_promoted_no_replace"
            and acquisition.get("source_id") == SOURCE_ID
            and acquisition.get("job_id") == view["job_id"]
            and acquisition.get("archive_integrity_verified") is True
            and acquisition.get("geotiff_headers_or_pixels_read") is False
            and type(acquisition.get("archive_size_bytes")) is int
            and archive.stat().st_size == acquisition["archive_size_bytes"]
            and metadata.get("status") == "pass_bounded_after_metadata_captured_for_local_review_only"
            and metadata.get("source_id") == SOURCE_ID
            and metadata.get("job_id") == view["job_id"]
            and metadata.get("archive_sha256") == acquisition.get("archive_sha256")
            and metadata.get("raster_header_or_pixel_read") is False
            and review.get("status") == "pass_after_metadata_for_header_and_pixel_qa_only"
            and review.get("source_id") == SOURCE_ID
            and review.get("job_id") == view["job_id"]
            and review.get("bindings", {}).get("capture_terminal_sha256") == _sha(paths["metadata"])
            and review.get("bindings", {}).get("archive_sha256") == acquisition.get("archive_sha256")
            and review.get("findings", {}).get("exact_source_granule_present") is True
            and review.get("findings", {}).get("gamma0_power_10m_no_speckle") is True
            and review.get("findings", {}).get("layover_shadow_semantics_reviewed") is True
            and review.get("rights", {}).get("local_vv_vh_and_mask_inspection") is True
            and review.get("rights", {}).get("DEM_display_or_export") is False
            and gate.get("status") == "pass_after_header_implementation_public_ci_only"
            and gate.get("public_ci", {}).get("conclusion") == "success"
            and gate.get("bindings", {}).get("approval_sha256") == APPROVAL_SHA
            and gate.get("bindings", {}).get("source_gate_sha256") == SOURCE_GATE_SHA
            and gate.get("bindings", {}).get("submission_terminal_sha256") == _sha(paths["submission"])
            and gate.get("bindings", {}).get("acquisition_terminal_sha256") == _sha(paths["acquisition"])
            and gate.get("bindings", {}).get("metadata_terminal_sha256") == _sha(paths["metadata"])
            and gate.get("bindings", {}).get("metadata_review_sha256") == _sha(paths["review"])
            and isinstance(files, dict) and set(files) == set(IMPLEMENTATION_FILES)
            and all(_sha(root / ref) == files[ref] for ref in IMPLEMENTATION_FILES)
            and preflight.get("status") == "pass_after_header_no_content"
            and preflight.get("bindings", {}).get("implementation_gate_sha256") == _sha(paths["gate"])
            and preflight.get("bindings", {}).get("acquisition_terminal_sha256") == _sha(paths["acquisition"])
            and preflight.get("bindings", {}).get("metadata_terminal_sha256") == _sha(paths["metadata"])
            and preflight.get("assertions", {}).get("attempt_absent") is True
            and preflight.get("assertions", {}).get("no_raster_header_or_pixel_read") is True
        )
    except (OSError, TypeError, ValueError):
        raise RouteStop("after_header_release_unavailable") from None
    if not valid:
        raise RouteStop("after_header_not_released")
    return acquisition, archive, view["job_id"]


def inspect_once(acquisition: dict, archive: Path,
                 attempt_root: Path = ATTEMPT_ROOT, *, controlled_root: Path = DATA_ROOT,
                 describe=describe_vsi, job_id: str) -> dict:
    """Reserve once, rehash the ZIP, and inspect only six GDAL headers."""
    if (not _safe_dir(controlled_root)
            or attempt_root.parent.parent.resolve() != controlled_root.resolve()
            or attempt_root.parent.is_symlink()
            or attempt_root.exists() or attempt_root.is_symlink()):
        raise RouteStop("after_header_attempt_collision")
    try:
        attempt_root.parent.mkdir(parents=True, exist_ok=True)
        if not _safe_dir(attempt_root.parent):
            raise RouteStop("after_header_attempt_parent_invalid")
        attempt_root.mkdir(exist_ok=False)
    except RouteStop:
        raise
    except OSError:
        raise RouteStop("after_header_attempt_reservation_failed") from None
    _write_json(attempt_root / "started.json", {
        "status": "after_header_inspection_reserved", "source_id": SOURCE_ID,
        "job_id": job_id, "started_at_utc": _now(),
        "pixels_read": False, "archive_mutated": False,
    })
    try:
        if (acquisition.get("source_id") != SOURCE_ID
                or acquisition.get("job_id") != job_id
                or not _safe_file(archive)
                or archive.name != acquisition.get("product_filename")
                or archive.stat().st_size != acquisition.get("archive_size_bytes")
                or _sha(archive) != acquisition.get("archive_sha256")):
            raise RouteStop("after_header_archive_identity_mismatch")
        before = archive.stat()
        with ZipFile(archive) as package:
            checked = inspect_member_names(
                SOURCE_ID, [item.orig_filename for item in package.infolist()])
        base = checked["product_base_name"]
        if archive.name != f"{base}.zip":
            raise RouteStop("after_header_product_root_mismatch")
        headers = {role: describe(archive, f"{base}/{base}{suffix}")
                   for role, suffix in ROLE_SUFFIX.items()}
        validation = inspect_raster_headers(SOURCE_ID, headers)
        after = archive.stat()
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (
                after.st_size, after.st_mtime_ns, after.st_ino):
            raise RouteStop("after_header_archive_changed_during_inspection")
        terminal = {
            "status": "pass_after_headers_for_local_pixel_qa_only",
            "source_id": SOURCE_ID, "job_id": job_id,
            "finished_at_utc": _now(), "headers": headers,
            "header_rule_status": validation["status"],
            "archive_sha256_verified_current": True,
            "pixels_read": False, "archive_mutated": False,
            "pixel_qa_pass": False, "arcgis_map_ready": False,
        }
    except RouteStop as exc:
        terminal = {"status": "stopped_after_header_no_automatic_retry",
                    "code": exc.code, "source_id": SOURCE_ID, "job_id": job_id,
                    "finished_at_utc": _now(), "pixels_read": False,
                    "archive_mutated": False}
    except (BadZipFile, KeyError, OSError, RuntimeError, ValueError):
        terminal = {"status": "stopped_after_header_no_automatic_retry",
                    "code": "after_header_unreadable", "source_id": SOURCE_ID,
                    "job_id": job_id, "finished_at_utc": _now(),
                    "pixels_read": False, "archive_mutated": False}
    except BaseException:
        terminal = {"status": "stopped_after_header_no_automatic_retry",
                    "code": "after_header_unexpected_failure", "source_id": SOURCE_ID,
                    "job_id": job_id, "finished_at_utc": _now(),
                    "pixels_read": False, "archive_mutated": False}
    _write_json(attempt_root / "terminal.json", terminal)
    return terminal


def main() -> int:
    try:
        acquisition, archive, job_id = require_release()
        if sys.argv[1:] == ["--check-release"]:
            print(json.dumps({"status": "pass_after_header_release_no_product_read"}))
            return 0
        if sys.argv[1:]:
            raise RouteStop("after_header_arguments_invalid")
        result = inspect_once(acquisition, archive, job_id=job_id)
        print(json.dumps({"status": result["status"], "code": result.get("code"),
                          "pixels_read": False}, sort_keys=True))
        return 0 if result["status"] == "pass_after_headers_for_local_pixel_qa_only" else 12
    except RouteStop as exc:
        print(json.dumps({"status": "stopped", "code": exc.code,
                          "pixels_read": False}, sort_keys=True))
        return 12
    except BaseException:
        print(json.dumps({"status": "stopped", "code": "after_header_unexpected_failure",
                          "pixels_read": False}, sort_keys=True))
        return 20


if __name__ == "__main__":
    raise SystemExit(main())
