#!/usr/bin/env python3
"""Gated, one-attempt metadata-only capture for exact after RTC product.

This does not approve the text, read GeoTIFF headers or pixels, or release a
local map. Provider text stays outside Git pending a separate rights review.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from datetime import UTC, datetime
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from m2_asf_hyp3_rtc_acquire_after_partial_001 import (
    DATA_ROOT, SOURCE_ID, SUBMISSION_REF,
)
from m2_asf_hyp3_rtc_after_descriptor_core_001 import submission_view
from m2_asf_hyp3_rtc_core_001 import ROOT, RouteStop
from m2_asf_hyp3_rtc_package_core_001 import inspect_member_names


ACQUISITION_REF = "m2-asf-hyp3-rtc-acquire-after-partial-001/attempt-001/terminal.json"
APPROVAL_REF = "records/source-gates/m2-asf-hyp3-rtc-partial-pair-map-001-approval.json"
APPROVAL_SHA = "7092d2c5f7e4b3f2d0c9cff22a7c0d0a44c62942746a9b73c183b3b96f08d506"
GATE_REF = "records/readiness/m2-asf-hyp3-rtc-after-metadata-001-implementation-gate.json"
PREFLIGHT_REF = "records/readiness/m2-asf-hyp3-rtc-after-metadata-001-preflight.json"
ATTEMPT_ROOT = DATA_ROOT / "m2-asf-hyp3-rtc-after-metadata-001" / "attempt-001"
IMPLEMENTATION_FILES = (
    "scripts/m2_asf_hyp3_rtc_after_metadata_001.py",
    "tests/test_m2_asf_hyp3_rtc_after_metadata_001.py",
)
SUFFIX_LIMITS = {
    ".README.md.txt": 2 * 1024 * 1024,
    ".log": 16 * 1024 * 1024,
    "_VV.tif.xml": 4 * 1024 * 1024,
    "_VH.tif.xml": 4 * 1024 * 1024,
    "_ls_map.tif.xml": 4 * 1024 * 1024,
    "_dem.tif.xml": 4 * 1024 * 1024,
    "_inc_map.tif.xml": 4 * 1024 * 1024,
    "_area.tif.xml": 4 * 1024 * 1024,
}


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_file(path: Path) -> bool:
    try:
        return (path.is_file() and not path.is_symlink()
                and not bool(getattr(path.stat(), "st_file_attributes", 0)
                             & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)))
    except OSError:
        return False


def _safe_dir(path: Path) -> bool:
    try:
        return (path.is_dir() and not path.is_symlink()
                and not bool(getattr(path.stat(), "st_file_attributes", 0)
                             & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)))
    except OSError:
        return False


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                digest.update(block)
    except OSError:
        raise RouteStop("after_metadata_hash_unavailable") from None
    return digest.hexdigest()


def _json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise RouteStop("after_metadata_control_unavailable") from None
    if not isinstance(value, dict):
        raise RouteStop("after_metadata_control_invalid")
    return value


def _write_new(path: Path, payload: bytes) -> None:
    try:
        with path.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        raise RouteStop("after_metadata_receipt_collision") from None
    except OSError:
        raise RouteStop("after_metadata_receipt_write_failed") from None


def _write_json(path: Path, value: dict) -> None:
    _write_new(path, (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8"))


def require_release(root: Path = ROOT, data_root: Path = DATA_ROOT,
                    attempt_root: Path = ATTEMPT_ROOT) -> tuple[dict, dict, Path]:
    """Stop before any ZIP read unless exact public and no-content gates pass."""
    paths = {
        "approval": root / APPROVAL_REF,
        "submission": data_root / SUBMISSION_REF,
        "acquisition": data_root / ACQUISITION_REF,
        "gate": root / GATE_REF,
        "preflight": root / PREFLIGHT_REF,
    }
    if any(not _safe_file(path) for path in paths.values()):
        raise RouteStop("after_metadata_required_path_invalid")
    approval, submission, acquisition, gate, preflight = (
        _json(paths[key]) for key in ("approval", "submission", "acquisition", "gate", "preflight")
    )
    submission_view(submission)
    filename = acquisition.get("product_filename")
    if (not isinstance(filename, str) or Path(filename).name != filename
            or not filename.endswith(".zip")):
        raise RouteStop("after_metadata_product_name_invalid")
    product_dir = data_root / "m2-asf-hyp3-rtc-products-after-partial-001"
    archive = product_dir / filename
    if (not _safe_dir(data_root) or not _safe_dir(product_dir)
            or not _safe_file(archive) or archive.parent.resolve() != product_dir.resolve()
            or attempt_root.exists() or attempt_root.is_symlink()
            or attempt_root.parent.is_symlink()
            or attempt_root.parent.parent.resolve() != data_root.resolve()):
        raise RouteStop("after_metadata_path_or_attempt_invalid")
    files = gate.get("bindings", {}).get("implementation_file_sha256")
    if (
        _sha(paths["approval"]) != APPROVAL_SHA
        or approval.get("decision") != "approve"
        or approval.get("authority", {}).get("conditional_one_zip_acquisition_integrity_provenance_rights_header_and_pixel_qa") is not True
        or gate.get("status") != "pass_after_metadata_implementation_public_ci_only"
        or gate.get("bindings", {}).get("approval_sha256") != APPROVAL_SHA
        or gate.get("bindings", {}).get("submission_terminal_sha256") != _sha(paths["submission"])
        or gate.get("bindings", {}).get("acquisition_terminal_sha256") != _sha(paths["acquisition"])
        or gate.get("public_ci", {}).get("conclusion") != "success"
        or not isinstance(files, dict) or set(files) != set(IMPLEMENTATION_FILES)
        or any(_sha(root / ref) != files[ref] for ref in IMPLEMENTATION_FILES)
        or preflight.get("status") != "pass_after_metadata_no_content"
        or preflight.get("bindings", {}).get("implementation_gate_sha256") != _sha(paths["gate"])
        or preflight.get("bindings", {}).get("acquisition_terminal_sha256") != _sha(paths["acquisition"])
        or preflight.get("assertions", {}).get("attempt_absent") is not True
        or preflight.get("assertions", {}).get("no_product_member_or_pixel_read") is not True
        or acquisition.get("status") != "pass_local_zip_promoted_no_replace"
        or acquisition.get("source_id") != SOURCE_ID
        or acquisition.get("job_id") != submission["job_id"]
        or acquisition.get("archive_integrity_verified") is not True
        or acquisition.get("geotiff_headers_or_pixels_read") is not False
        or acquisition.get("credentials_recorded") is not False
        or type(acquisition.get("archive_size_bytes")) is not int
        or archive.stat().st_size != acquisition["archive_size_bytes"]
    ):
        raise RouteStop("after_metadata_not_released")
    return submission, acquisition, archive


def capture_once(submission: dict, acquisition: dict, archive_path: Path,
                 attempt_root: Path = ATTEMPT_ROOT, *, controlled_root: Path = DATA_ROOT) -> dict:
    """Reserve before archive read; keep exact text/XML in non-Git custody."""
    view = submission_view(submission)
    if (not _safe_dir(controlled_root) or attempt_root.parent.parent.resolve() != controlled_root.resolve()
            or attempt_root.exists() or attempt_root.is_symlink()
            or attempt_root.parent.is_symlink()):
        raise RouteStop("after_metadata_attempt_collision")
    try:
        attempt_root.parent.mkdir(parents=True, exist_ok=True)
        if not _safe_dir(attempt_root.parent):
            raise RouteStop("after_metadata_attempt_parent_invalid")
        attempt_root.mkdir(exist_ok=False)
    except RouteStop:
        raise
    except OSError:
        raise RouteStop("after_metadata_attempt_reservation_failed") from None
    _write_json(attempt_root / "started.json", {
        "status": "metadata_capture_reserved", "source_id": SOURCE_ID,
        "job_id": view["job_id"], "started_at_utc": _now(),
        "raster_header_or_pixel_read": False, "archive_mutated": False,
    })
    try:
        if (not _safe_file(archive_path)
                or archive_path.name != acquisition.get("product_filename")
                or archive_path.stat().st_size != acquisition.get("archive_size_bytes")
                or _sha(archive_path) != acquisition.get("archive_sha256")):
            raise RouteStop("after_metadata_archive_identity_mismatch")
        before = archive_path.stat()
        captured = {}
        with ZipFile(archive_path) as archive:
            package = inspect_member_names(SOURCE_ID, [info.orig_filename for info in archive.infolist()])
            base = package["product_base_name"]
            if archive_path.name != f"{base}.zip":
                raise RouteStop("after_metadata_product_root_mismatch")
            for suffix, limit in SUFFIX_LIMITS.items():
                member = f"{base}/{base}{suffix}"
                info = archive.getinfo(member)
                if info.file_size <= 0 or info.file_size > limit or info.is_dir():
                    raise RouteStop("after_metadata_member_size_invalid")
                with archive.open(info) as stream:
                    payload = stream.read(limit + 1)
                if len(payload) != info.file_size:
                    raise RouteStop("after_metadata_member_read_invalid")
                local_name = "readme.txt" if suffix == ".README.md.txt" else (
                    "processing.log" if suffix == ".log" else suffix[1:])
                _write_new(attempt_root / local_name, payload)
                captured[local_name] = {"bytes": len(payload),
                                        "sha256": hashlib.sha256(payload).hexdigest()}
        after = archive_path.stat()
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (
                after.st_size, after.st_mtime_ns, after.st_ino):
            raise RouteStop("after_metadata_archive_changed_during_capture")
        terminal = {
            "status": "pass_bounded_after_metadata_captured_for_local_review_only",
            "source_id": SOURCE_ID, "job_id": view["job_id"],
            "product_filename": archive_path.name,
            "archive_sha256": acquisition["archive_sha256"],
            "captured": captured, "finished_at_utc": _now(),
            "archive_sha256_verified_current": True,
            "processing_settings_reviewed": False,
            "mask_codes_reviewed": False,
            "rights_and_attribution_reviewed": False,
            "raster_header_or_pixel_read": False,
            "archive_mutated": False, "arcgis_map_ready": False,
        }
    except RouteStop as exc:
        terminal = {"status": "stopped_after_metadata_no_automatic_retry",
                    "code": exc.code, "source_id": SOURCE_ID,
                    "job_id": view["job_id"], "finished_at_utc": _now(),
                    "raster_header_or_pixel_read": False, "archive_mutated": False}
    except (BadZipFile, KeyError, OSError, RuntimeError, ValueError):
        terminal = {"status": "stopped_after_metadata_no_automatic_retry",
                    "code": "after_metadata_unreadable", "source_id": SOURCE_ID,
                    "job_id": view["job_id"], "finished_at_utc": _now(),
                    "raster_header_or_pixel_read": False, "archive_mutated": False}
    except BaseException:
        terminal = {"status": "stopped_after_metadata_no_automatic_retry",
                    "code": "after_metadata_unexpected_failure", "source_id": SOURCE_ID,
                    "job_id": view["job_id"], "finished_at_utc": _now(),
                    "raster_header_or_pixel_read": False, "archive_mutated": False}
    _write_json(attempt_root / "terminal.json", terminal)
    return terminal


def main() -> int:
    try:
        submission, acquisition, archive = require_release()
        if sys.argv[1:] == ["--check-release"]:
            print(json.dumps({"status": "pass_after_metadata_release_no_product_read"}))
            return 0
        if sys.argv[1:]:
            raise RouteStop("after_metadata_arguments_invalid")
        result = capture_once(submission, acquisition, archive)
        print(json.dumps({"status": result["status"], "code": result.get("code"),
                          "raster_header_or_pixel_read": False}, sort_keys=True))
        return 0 if result["status"] == "pass_bounded_after_metadata_captured_for_local_review_only" else 12
    except RouteStop as exc:
        print(json.dumps({"status": "stopped", "code": exc.code,
                          "raster_header_or_pixel_read": False}, sort_keys=True))
        return 12
    except BaseException:
        print(json.dumps({"status": "stopped", "code": "after_metadata_unexpected_failure",
                          "raster_header_or_pixel_read": False}, sort_keys=True))
        return 20


if __name__ == "__main__":
    raise SystemExit(main())
