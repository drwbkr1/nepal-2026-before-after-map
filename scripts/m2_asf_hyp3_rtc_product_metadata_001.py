#!/usr/bin/env python3
"""Capture only bounded metadata members from the exact first HyP3 RTC ZIP.

The product remains in non-Git custody. This is a distinct append-only attempt
after the terminal README and composite attempts. No raster header or pixel is
opened, and raw provider text is never printed or put in a public receipt.
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

from m2_asf_hyp3_rtc_acquire_first_001 import DATA_ROOT
from m2_asf_hyp3_rtc_composite_provenance_core_001 import (
    ARCHIVE_SHA256, ARCHIVE_SIZE, JOB_ID, PRODUCT_FILENAME, README_SHA256,
    SOURCE_ID,
)
from m2_asf_hyp3_rtc_core_001 import ROOT, RouteStop
from m2_asf_hyp3_rtc_package_core_001 import inspect_member_names


APPROVAL_REF = "records/source-gates/m2-asf-hyp3-rtc-provenance-rule-amendment-001-approval.json"
SOURCE_GATE_REF = "records/source-gates/m2-asf-hyp3-rtc-processing-source-gate-001.json"
COMPOSITE_REF = "m2-asf-hyp3-rtc-composite-provenance-001/attempt-001/terminal.json"
ACQUISITION_REF = "m2-asf-hyp3-rtc-acquire-first-001/attempt-001/terminal.json"
GATE_REF = "records/readiness/m2-asf-hyp3-rtc-product-metadata-001-implementation-gate.json"
PREFLIGHT_REF = "records/readiness/m2-asf-hyp3-rtc-product-metadata-001-execution-preflight.json"
ATTEMPT_ROOT = DATA_ROOT / "m2-asf-hyp3-rtc-product-metadata-001" / "attempt-001"
IMPLEMENTATION_FILES = (
    "scripts/m2_asf_hyp3_rtc_product_metadata_001.py",
    "tests/test_m2_asf_hyp3_rtc_product_metadata_001.py",
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


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_file(path: Path) -> bool:
    try:
        return path.is_file() and not path.is_symlink() and not bool(
            getattr(path.stat(), "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        )
    except OSError:
        return False


def _safe_dir(path: Path) -> bool:
    try:
        return path.is_dir() and not path.is_symlink() and not bool(
            getattr(path.stat(), "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        )
    except OSError:
        return False


def _json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise RouteStop("rtc_metadata_control_unavailable") from None
    if not isinstance(value, dict):
        raise RouteStop("rtc_metadata_control_invalid")
    return value


def _write_new(path: Path, payload: bytes) -> None:
    try:
        with path.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        raise RouteStop("rtc_metadata_receipt_collision") from None
    except OSError:
        raise RouteStop("rtc_metadata_receipt_write_failed") from None


def _write_json(path: Path, value: dict) -> None:
    _write_new(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def require_release(
    root: Path = ROOT, data_root: Path = DATA_ROOT,
    attempt_root: Path = ATTEMPT_ROOT,
) -> tuple[dict, Path]:
    """Require exact published code, source, receipt, and no-content gates."""
    approval_path = root / APPROVAL_REF
    source_gate_path = root / SOURCE_GATE_REF
    gate_path = root / GATE_REF
    preflight_path = root / PREFLIGHT_REF
    composite_path = data_root / COMPOSITE_REF
    acquisition_path = data_root / ACQUISITION_REF
    archive = data_root / "m2-asf-hyp3-rtc-products-001" / PRODUCT_FILENAME
    for path in (approval_path, source_gate_path, gate_path, preflight_path,
                 composite_path, acquisition_path, archive):
        if not _safe_file(path):
            raise RouteStop("rtc_metadata_required_path_invalid")
    if (
        not _safe_dir(data_root) or not _safe_dir(archive.parent)
        or not _safe_dir(composite_path.parent) or not _safe_dir(acquisition_path.parent)
        or attempt_root.parent.parent.resolve() != data_root.resolve()
        or attempt_root.parent.is_symlink()
        or (attempt_root.parent.exists() and not _safe_dir(attempt_root.parent))
        or attempt_root.exists() or attempt_root.is_symlink()
    ):
        raise RouteStop("rtc_metadata_path_or_attempt_invalid")
    approval = _json(approval_path)
    source_gate = _json(source_gate_path)
    gate = _json(gate_path)
    preflight = _json(preflight_path)
    composite = _json(composite_path)
    acquisition = _json(acquisition_path)
    hashes = gate.get("bindings", {}).get("implementation_file_sha256")
    try:
        valid = (
            approval.get("decision") == "approve"
            and approval.get("authority", {}).get("conditional_product_metadata_and_pixel_QA_under_original_route") is True
            and source_gate.get("decision", {}).get("status") == "ready"
            and gate.get("status") == "pass_product_metadata_implementation_public_ci_only"
            and gate.get("public_ci", {}).get("conclusion") == "success"
            and gate.get("bindings", {}).get("approval_sha256") == _sha(approval_path)
            and gate.get("bindings", {}).get("source_gate_sha256") == _sha(source_gate_path)
            and isinstance(hashes, dict) and set(hashes) == set(IMPLEMENTATION_FILES)
            and all(_sha(root / ref) == sha for ref, sha in hashes.items())
            and preflight.get("status") == "pass_product_metadata_no_content_preflight"
            and preflight.get("bindings", {}).get("implementation_gate_sha256") == _sha(gate_path)
            and preflight.get("bindings", {}).get("composite_terminal_sha256") == _sha(composite_path)
            and preflight.get("bindings", {}).get("acquisition_terminal_sha256") == _sha(acquisition_path)
            and preflight.get("assertions", {}).get("attempt_absent") is True
            and preflight.get("assertions", {}).get("no_product_payload_read") is True
            and composite.get("status") == "pass_composite_provenance_for_local_qa_only"
            and composite.get("source_id") == SOURCE_ID
            and composite.get("job_id") == JOB_ID
            and composite.get("archive_sha256") == ARCHIVE_SHA256
            and acquisition.get("status") == "pass_local_zip_promoted_no_replace"
            and acquisition.get("source_id") == SOURCE_ID
            and acquisition.get("job_id") == JOB_ID
            and acquisition.get("product_filename") == PRODUCT_FILENAME
            and acquisition.get("archive_sha256") == ARCHIVE_SHA256
            and acquisition.get("archive_integrity_verified") is True
            and archive.stat().st_size == ARCHIVE_SIZE
        )
    except (OSError, TypeError, ValueError):
        raise RouteStop("rtc_metadata_release_unavailable") from None
    if not valid:
        raise RouteStop("rtc_metadata_not_released")
    return acquisition, archive


def capture_once(
    acquisition: dict, archive_path: Path, attempt_root: Path = ATTEMPT_ROOT,
    *, controlled_root: Path = DATA_ROOT,
) -> dict:
    """Reserve before reading; hash the archive and capture text/XML only."""
    if (
        not _safe_dir(controlled_root)
        or attempt_root.parent.parent.resolve() != controlled_root.resolve()
        or attempt_root.parent.is_symlink()
        or attempt_root.exists() or attempt_root.is_symlink()
    ):
        raise RouteStop("rtc_metadata_attempt_collision")
    try:
        attempt_root.parent.mkdir(parents=True, exist_ok=True)
        if not _safe_dir(attempt_root.parent):
            raise RouteStop("rtc_metadata_attempt_parent_invalid")
        attempt_root.mkdir(exist_ok=False)
    except RouteStop:
        raise
    except OSError:
        raise RouteStop("rtc_metadata_attempt_reservation_failed") from None
    _write_json(attempt_root / "started.json", {
        "status": "metadata_capture_reserved", "source_id": SOURCE_ID,
        "job_id": JOB_ID, "started_at_utc": _now(),
        "raster_header_or_pixel_read": False, "archive_mutated": False,
    })
    try:
        if (
            not _safe_file(archive_path)
            or archive_path.name != PRODUCT_FILENAME
            or archive_path.stat().st_size != acquisition["archive_size_bytes"]
            or _sha(archive_path) != acquisition["archive_sha256"]
            or acquisition["archive_sha256"] != ARCHIVE_SHA256
        ):
            raise RouteStop("rtc_metadata_archive_identity_mismatch")
        before = archive_path.stat()
        captured = {}
        with ZipFile(archive_path) as archive:
            package = inspect_member_names(
                SOURCE_ID, [info.orig_filename for info in archive.infolist()]
            )
            base = package["product_base_name"]
            if archive_path.name != f"{base}.zip":
                raise RouteStop("rtc_metadata_product_root_mismatch")
            for suffix, limit in SUFFIX_LIMITS.items():
                member = f"{base}/{base}{suffix}"
                info = archive.getinfo(member)
                if info.file_size <= 0 or info.file_size > limit or info.is_dir():
                    raise RouteStop("rtc_metadata_member_size_invalid")
                with archive.open(info) as stream:
                    payload = stream.read(limit + 1)
                if len(payload) != info.file_size:
                    raise RouteStop("rtc_metadata_member_read_invalid")
                if suffix == ".README.md.txt" and hashlib.sha256(payload).hexdigest() != README_SHA256:
                    raise RouteStop("rtc_metadata_readme_hash_mismatch")
                local_name = "readme.txt" if suffix == ".README.md.txt" else (
                    "processing.log" if suffix == ".log" else suffix[1:]
                )
                _write_new(attempt_root / local_name, payload)
                captured[local_name] = {
                    "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()
                }
        after = archive_path.stat()
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (
            after.st_size, after.st_mtime_ns, after.st_ino
        ):
            raise RouteStop("rtc_metadata_archive_changed_during_capture")
        terminal = {
            "status": "pass_bounded_metadata_captured_for_local_review_only",
            "source_id": SOURCE_ID, "job_id": JOB_ID,
            "captured": captured, "finished_at_utc": _now(),
            "archive_sha256_verified_current": True,
            "processing_settings_reviewed": False,
            "mask_codes_reviewed": False,
            "rights_and_attribution_reviewed": False,
            "raster_header_or_pixel_read": False, "archive_mutated": False,
            "pixel_qa_pass": False, "arcgis_map_ready": False,
        }
    except RouteStop as exc:
        terminal = {
            "status": "stopped_metadata_capture_no_automatic_retry", "code": exc.code,
            "source_id": SOURCE_ID, "job_id": JOB_ID,
            "finished_at_utc": _now(), "raster_header_or_pixel_read": False,
            "archive_mutated": False,
        }
    except (BadZipFile, KeyError, OSError, RuntimeError, ValueError):
        terminal = {
            "status": "stopped_metadata_capture_no_automatic_retry",
            "code": "rtc_metadata_unreadable", "source_id": SOURCE_ID,
            "job_id": JOB_ID, "finished_at_utc": _now(),
            "raster_header_or_pixel_read": False, "archive_mutated": False,
        }
    except Exception:
        terminal = {
            "status": "stopped_metadata_capture_no_automatic_retry",
            "code": "rtc_metadata_unexpected_failure", "source_id": SOURCE_ID,
            "job_id": JOB_ID, "finished_at_utc": _now(),
            "raster_header_or_pixel_read": False, "archive_mutated": False,
        }
    _write_json(attempt_root / "terminal.json", terminal)
    return terminal


def main() -> int:
    try:
        acquisition, archive = require_release()
        if sys.argv[1:] == ["--check-release"]:
            print(json.dumps({"status": "pass_metadata_release_no_product_read"}))
            return 0
        if sys.argv[1:]:
            raise RouteStop("rtc_metadata_arguments_invalid")
        result = capture_once(acquisition, archive)
        print(json.dumps({"status": result["status"], "code": result.get("code"),
                          "raster_header_or_pixel_read": False}, sort_keys=True))
        return 0 if result["status"] == "pass_bounded_metadata_captured_for_local_review_only" else 12
    except RouteStop as exc:
        print(json.dumps({"status": "stopped", "code": exc.code,
                          "raster_header_or_pixel_read": False}, sort_keys=True))
        return 12
    except BaseException:
        print(json.dumps({"status": "stopped", "code": "rtc_metadata_unexpected_failure",
                          "raster_header_or_pixel_read": False}, sort_keys=True))
        return 20


if __name__ == "__main__":
    raise SystemExit(main())
