#!/usr/bin/env python3
"""Gated header-only inspection of the first exact HyP3 RTC ZIP.

GDAL opens six GeoTIFF members through /vsizip/ without extraction. No raster
band value is read. The result is a distinct append-only non-Git attempt.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from zipfile import ZipFile

from m2_asf_hyp3_rtc_acquire_first_001 import DATA_ROOT
from m2_asf_hyp3_rtc_composite_provenance_core_001 import (
    ARCHIVE_SHA256, ARCHIVE_SIZE, JOB_ID, PRODUCT_FILENAME, SOURCE_ID,
)
from m2_asf_hyp3_rtc_core_001 import ROOT, RouteStop
from m2_asf_hyp3_rtc_header_core_001 import RASTERS, inspect_raster_headers
from m2_asf_hyp3_rtc_package_core_001 import inspect_member_names
from m2_asf_hyp3_rtc_product_metadata_001 import (
    APPROVAL_REF, SOURCE_GATE_REF, _json, _now, _safe_dir, _safe_file, _sha,
    _write_json,
)


METADATA_REVIEW_REF = "records/readiness/m2-asf-hyp3-rtc-product-metadata-001-local-review.json"
METADATA_TERMINAL_REF = "m2-asf-hyp3-rtc-product-metadata-001/attempt-001/terminal.json"
ACQUISITION_REF = "m2-asf-hyp3-rtc-acquire-first-001/attempt-001/terminal.json"
GATE_REF = "records/readiness/m2-asf-hyp3-rtc-product-header-001-implementation-gate.json"
PREFLIGHT_REF = "records/readiness/m2-asf-hyp3-rtc-product-header-001-execution-preflight.json"
ATTEMPT_ROOT = DATA_ROOT / "m2-asf-hyp3-rtc-product-header-001" / "attempt-001"
IMPLEMENTATION_FILES = (
    "scripts/m2_asf_hyp3_rtc_product_header_001.py",
    "tests/test_m2_asf_hyp3_rtc_product_header_001.py",
    "scripts/validate_m2_asf_hyp3_rtc_vsi_header_synthetic_001.py",
)
ROLE_SUFFIX = {role: f"_{role.upper() if role in ('vv', 'vh') else role}.tif"
               for role in RASTERS}


def describe_vsi(archive: Path, member: str) -> dict:
    """Inspect GDAL dataset metadata only; never call ReadAsArray."""
    from osgeo import gdal, osr  # ArcGIS runtime only; lazy for portable tests

    gdal.UseExceptions()
    osr.UseExceptions()
    expected = osr.SpatialReference()
    expected.ImportFromEPSG(32645)
    vsi = "/vsizip/" + archive.as_posix() + "/" + member
    gdal.PushErrorHandler("CPLQuietErrorHandler")
    try:
        dataset = gdal.OpenEx(vsi, gdal.OF_RASTER)
    finally:
        gdal.PopErrorHandler()
    if dataset is None:
        raise RouteStop("rtc_header_vsi_open_failed")
    try:
        if dataset.RasterCount != 1:
            raise RouteStop("rtc_header_band_count_invalid")
        band = dataset.GetRasterBand(1)
        spatial = dataset.GetSpatialRef()
        if spatial is None:
            raise RouteStop("rtc_header_spatial_reference_missing")
        grid = dataset.GetGeoTransform()
        if grid is None or len(grid) != 6:
            raise RouteStop("rtc_header_geotransform_missing")
        width, height = int(dataset.RasterXSize), int(dataset.RasterYSize)
        return {
            "width": width, "height": height, "band_count": int(dataset.RasterCount),
            "data_type": gdal.GetDataTypeName(band.DataType),
            "grid": {
                "wkid": 32645 if spatial.IsSame(expected) else 0,
                "cell_size_x": float(grid[1]), "cell_size_y": float(abs(grid[5])),
                "origin_x": float(grid[0]), "origin_y": float(grid[3]),
                "xmin": float(grid[0]), "ymin": float(grid[3] + height * grid[5]),
                "xmax": float(grid[0] + width * grid[1]), "ymax": float(grid[3]),
                "rotation_degrees": float(grid[2]),
            },
        }
    finally:
        dataset = None


def require_release(
    root: Path = ROOT, data_root: Path = DATA_ROOT,
    attempt_root: Path = ATTEMPT_ROOT,
) -> tuple[dict, Path]:
    """Check published gates and immutable metadata without opening the ZIP."""
    approval_path = root / APPROVAL_REF
    source_gate_path = root / SOURCE_GATE_REF
    review_path = root / METADATA_REVIEW_REF
    gate_path = root / GATE_REF
    preflight_path = root / PREFLIGHT_REF
    metadata_path = data_root / METADATA_TERMINAL_REF
    acquisition_path = data_root / ACQUISITION_REF
    archive = data_root / "m2-asf-hyp3-rtc-products-001" / PRODUCT_FILENAME
    for path in (approval_path, source_gate_path, review_path, gate_path,
                 preflight_path, metadata_path, acquisition_path, archive):
        if not _safe_file(path):
            raise RouteStop("rtc_header_required_path_invalid")
    if (
        not _safe_dir(data_root) or not _safe_dir(archive.parent)
        or not _safe_dir(metadata_path.parent) or not _safe_dir(acquisition_path.parent)
        or attempt_root.parent.parent.resolve() != data_root.resolve()
        or attempt_root.parent.is_symlink()
        or (attempt_root.parent.exists() and not _safe_dir(attempt_root.parent))
        or attempt_root.exists() or attempt_root.is_symlink()
    ):
        raise RouteStop("rtc_header_path_or_attempt_invalid")
    approval, source_gate, review, gate, preflight, metadata, acquisition = (
        _json(path) for path in (
            approval_path, source_gate_path, review_path, gate_path,
            preflight_path, metadata_path, acquisition_path,
        )
    )
    files = gate.get("bindings", {}).get("implementation_file_sha256")
    try:
        valid = (
            approval.get("decision") == "approve"
            and approval.get("authority", {}).get("conditional_product_metadata_and_pixel_QA_under_original_route") is True
            and source_gate.get("decision", {}).get("status") == "ready"
            and review.get("status") == "pass_product_metadata_for_separate_local_header_and_pixel_qa_only"
            and review.get("bindings", {}).get("non_git_capture_terminal_sha256") == _sha(metadata_path)
            and metadata.get("status") == "pass_bounded_metadata_captured_for_local_review_only"
            and metadata.get("raster_header_or_pixel_read") is False
            and gate.get("status") == "pass_product_header_implementation_public_ci_only"
            and gate.get("public_ci", {}).get("conclusion") == "success"
            and gate.get("bindings", {}).get("approval_sha256") == _sha(approval_path)
            and gate.get("bindings", {}).get("source_gate_sha256") == _sha(source_gate_path)
            and gate.get("bindings", {}).get("metadata_review_sha256") == _sha(review_path)
            and isinstance(files, dict) and set(files) == set(IMPLEMENTATION_FILES)
            and all(_sha(root / ref) == sha for ref, sha in files.items())
            and preflight.get("status") == "pass_product_header_no_content_preflight"
            and preflight.get("bindings", {}).get("implementation_gate_sha256") == _sha(gate_path)
            and preflight.get("bindings", {}).get("metadata_terminal_sha256") == _sha(metadata_path)
            and preflight.get("bindings", {}).get("acquisition_terminal_sha256") == _sha(acquisition_path)
            and preflight.get("assertions", {}).get("attempt_absent") is True
            and preflight.get("assertions", {}).get("no_raster_header_or_pixel_read") is True
            and acquisition.get("status") == "pass_local_zip_promoted_no_replace"
            and acquisition.get("source_id") == SOURCE_ID
            and acquisition.get("job_id") == JOB_ID
            and acquisition.get("product_filename") == PRODUCT_FILENAME
            and acquisition.get("archive_sha256") == ARCHIVE_SHA256
            and acquisition.get("archive_size_bytes") == ARCHIVE_SIZE
            and archive.stat().st_size == ARCHIVE_SIZE
        )
    except (OSError, TypeError, ValueError):
        raise RouteStop("rtc_header_release_unavailable") from None
    if not valid:
        raise RouteStop("rtc_header_not_released")
    return acquisition, archive


def inspect_once(
    acquisition: dict, archive: Path, attempt_root: Path = ATTEMPT_ROOT,
    *, controlled_root: Path = DATA_ROOT, describe=describe_vsi,
) -> dict:
    """Reserve once, rehash exact ZIP, and inspect only six raster headers."""
    if (
        not _safe_dir(controlled_root)
        or attempt_root.parent.parent.resolve() != controlled_root.resolve()
        or attempt_root.parent.is_symlink()
        or attempt_root.exists() or attempt_root.is_symlink()
    ):
        raise RouteStop("rtc_header_attempt_collision")
    try:
        attempt_root.parent.mkdir(parents=True, exist_ok=True)
        if not _safe_dir(attempt_root.parent):
            raise RouteStop("rtc_header_attempt_parent_invalid")
        attempt_root.mkdir(exist_ok=False)
    except RouteStop:
        raise
    except OSError:
        raise RouteStop("rtc_header_attempt_reservation_failed") from None
    _write_json(attempt_root / "started.json", {
        "status": "header_only_inspection_reserved", "source_id": SOURCE_ID,
        "job_id": JOB_ID, "started_at_utc": _now(), "pixels_read": False,
        "archive_mutated": False,
    })
    try:
        if (
            not _safe_file(archive) or archive.name != PRODUCT_FILENAME
            or archive.stat().st_size != acquisition["archive_size_bytes"]
            or acquisition["archive_sha256"] != ARCHIVE_SHA256
            or _sha(archive) != ARCHIVE_SHA256
        ):
            raise RouteStop("rtc_header_archive_identity_mismatch")
        before = archive.stat()
        with ZipFile(archive) as package:
            member_screen = inspect_member_names(
                SOURCE_ID, [item.orig_filename for item in package.infolist()]
            )
        base = member_screen["product_base_name"]
        if archive.name != f"{base}.zip":
            raise RouteStop("rtc_header_product_root_mismatch")
        headers = {
            role: describe(archive, f"{base}/{base}{suffix}")
            for role, suffix in ROLE_SUFFIX.items()
        }
        checked = inspect_raster_headers(SOURCE_ID, headers)
        after = archive.stat()
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (
            after.st_size, after.st_mtime_ns, after.st_ino
        ):
            raise RouteStop("rtc_header_archive_changed_during_inspection")
        terminal = {
            "status": "pass_actual_headers_for_local_pixel_qa_only",
            "source_id": SOURCE_ID, "job_id": JOB_ID,
            "finished_at_utc": _now(), "headers": headers,
            "header_rule_status": checked["status"],
            "archive_sha256_verified_current": True,
            "pixels_read": False, "archive_mutated": False,
            "pixel_qa_pass": False, "arcgis_map_ready": False,
        }
    except RouteStop as exc:
        terminal = {"status": "stopped_header_only_no_automatic_retry",
                    "code": exc.code, "source_id": SOURCE_ID, "job_id": JOB_ID,
                    "finished_at_utc": _now(), "pixels_read": False,
                    "archive_mutated": False}
    except Exception:
        terminal = {"status": "stopped_header_only_no_automatic_retry",
                    "code": "rtc_header_unexpected_failure", "source_id": SOURCE_ID,
                    "job_id": JOB_ID, "finished_at_utc": _now(),
                    "pixels_read": False, "archive_mutated": False}
    _write_json(attempt_root / "terminal.json", terminal)
    return terminal


def main() -> int:
    try:
        acquisition, archive = require_release()
        if sys.argv[1:] == ["--check-release"]:
            print(json.dumps({"status": "pass_header_release_no_product_read"}))
            return 0
        if sys.argv[1:]:
            raise RouteStop("rtc_header_arguments_invalid")
        result = inspect_once(acquisition, archive)
        print(json.dumps({"status": result["status"], "code": result.get("code"),
                          "pixels_read": False}, sort_keys=True))
        return 0 if result["status"] == "pass_actual_headers_for_local_pixel_qa_only" else 12
    except RouteStop as exc:
        print(json.dumps({"status": "stopped", "code": exc.code,
                          "pixels_read": False}, sort_keys=True))
        return 12
    except BaseException:
        print(json.dumps({"status": "stopped", "code": "rtc_header_unexpected_failure",
                          "pixels_read": False}, sort_keys=True))
        return 20


if __name__ == "__main__":
    raise SystemExit(main())
