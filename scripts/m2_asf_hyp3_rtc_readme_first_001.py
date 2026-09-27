#!/usr/bin/env python3
"""Gated, read-only README probe for the first verified HyP3 RTC archive.

The archive stays in non-Git custody. A new append-only receipt is reserved
before its bytes are read. No network, extraction, raster, or pixel action is
performed, and no raw README, account value, or provider URL is recorded.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from m2_asf_hyp3_rtc_acquire_first_001 import (
    DATA_ROOT, EXACT_JOB_ID, SOURCE_ID,
)
from m2_asf_hyp3_rtc_core_001 import ROOT, RouteStop
from m2_asf_hyp3_rtc_package_core_001 import PRODUCT_ROOT
from m2_asf_hyp3_rtc_readme_core_001 import inspect_product_readme


GATE_REF = "records/readiness/m2-asf-hyp3-rtc-readme-first-implementation-gate-001.json"
PREFLIGHT_REF = "records/readiness/m2-asf-hyp3-rtc-readme-first-execution-preflight-001.json"
PROBE_ROOT = DATA_ROOT / "m2-asf-hyp3-rtc-readme-first-001" / "attempt-001"
IMPLEMENTATION_FILES = (
    "scripts/m2_asf_hyp3_rtc_readme_core_001.py",
    "scripts/m2_asf_hyp3_rtc_readme_first_001.py",
    "tests/test_m2_asf_hyp3_rtc_readme_core_001.py",
    "tests/test_m2_asf_hyp3_rtc_readme_first_001.py",
)


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise RouteStop("rtc_readme_release_unavailable") from None
    if not isinstance(value, dict):
        raise RouteStop("rtc_readme_release_invalid")
    return value


def _safe_file(path: Path) -> bool:
    try:
        return path.is_file() and not path.is_symlink() and not bool(
            getattr(path.stat(), "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        )
    except OSError:
        return False


def _safe_directory(path: Path) -> bool:
    try:
        return path.is_dir() and not path.is_symlink() and not bool(
            getattr(path.stat(), "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        )
    except OSError:
        return False


def require_readme_release(
    root: Path = ROOT, data_root: Path = DATA_ROOT,
    probe_root: Path = PROBE_ROOT,
) -> tuple[dict, Path]:
    """Bind published implementation, prior acquisition, and no-content preflight."""
    gate = _read_json(root / GATE_REF)
    preflight = _read_json(root / PREFLIGHT_REF)
    acquisition_path = data_root / "m2-asf-hyp3-rtc-acquire-first-001" / "attempt-001" / "terminal.json"
    descriptor_path = acquisition_path.with_name("descriptor.json")
    if not all(_safe_directory(path) for path in (
        data_root, acquisition_path.parent.parent, acquisition_path.parent,
        data_root / "m2-asf-hyp3-rtc-products-001",
    )) or not _safe_file(acquisition_path) or not _safe_file(descriptor_path):
        raise RouteStop("rtc_readme_custody_invalid")
    acquisition = _read_json(acquisition_path)
    descriptor = _read_json(descriptor_path)
    filename = acquisition.get("product_filename")
    if (
        not isinstance(filename, str) or not filename.endswith(".zip")
        or Path(filename).name != filename
        or PRODUCT_ROOT.fullmatch(filename[:-4]) is None
    ):
        raise RouteStop("rtc_readme_acquisition_identity_invalid")
    archive = data_root / "m2-asf-hyp3-rtc-products-001" / filename
    published = gate.get("bindings", {}).get("implementation_file_sha256")
    files_match = isinstance(published, dict) and set(published) == set(IMPLEMENTATION_FILES)
    try:
        if files_match:
            files_match = all(_sha(root / ref) == published[ref] for ref in IMPLEMENTATION_FILES)
        bindings_match = (
            preflight.get("bindings", {}).get("implementation_gate_sha256") == _sha(root / GATE_REF)
            and preflight.get("bindings", {}).get("acquisition_terminal_sha256") == _sha(acquisition_path)
        )
    except OSError:
        raise RouteStop("rtc_readme_release_unavailable") from None
    if (
        gate.get("status") != "pass_readme_first_implementation_public_ci_only"
        or gate.get("public_ci", {}).get("conclusion") != "success"
        or not files_match or not bindings_match
        or preflight.get("status") != "pass_readme_first_no_content_preflight"
        or preflight.get("assertions", {}).get("archive_exists") is not True
        or preflight.get("assertions", {}).get("probe_attempt_absent") is not True
        or preflight.get("assertions", {}).get("no_product_payload_or_pixel_read") is not True
        or acquisition.get("status") != "pass_local_zip_promoted_no_replace"
        or acquisition.get("source_id") != SOURCE_ID
        or acquisition.get("job_id") != EXACT_JOB_ID
        or acquisition.get("archive_integrity_verified") is not True
        or acquisition.get("credentials_recorded") is not False
        or descriptor.get("source_id") != SOURCE_ID
        or descriptor.get("job_id") != EXACT_JOB_ID
        or descriptor.get("product_filename") != filename
        or descriptor.get("expected_size_bytes") != acquisition.get("archive_size_bytes")
        or type(acquisition.get("archive_size_bytes")) is not int
        or not isinstance(acquisition.get("archive_sha256"), str)
        or len(acquisition["archive_sha256"]) != 64
        or not _safe_file(archive)
        or archive.stat().st_size != acquisition["archive_size_bytes"]
        or probe_root.parent.parent.resolve() != data_root.resolve()
        or probe_root.parent.is_symlink()
        or (probe_root.parent.exists() and not _safe_directory(probe_root.parent))
        or probe_root.exists() or probe_root.is_symlink()
    ):
        raise RouteStop("rtc_readme_not_released")
    return acquisition, archive


def _write_new_json(path: Path, value: dict) -> None:
    try:
        with path.open("xb") as stream:
            stream.write((json.dumps(value, sort_keys=True, indent=2) + "\n").encode())
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        raise RouteStop("rtc_readme_receipt_collision") from None
    except OSError:
        raise RouteStop("rtc_readme_receipt_write_failed") from None


def probe_readme_once(
    acquisition: dict,
    archive: Path,
    attempt_root: Path = PROBE_ROOT,
    *,
    controlled_root: Path = DATA_ROOT,
    inspect: Callable = inspect_product_readme,
) -> dict:
    """Reserve once, rehash the promoted ZIP, then inspect only its README."""
    if (
        not _safe_directory(controlled_root)
        or attempt_root.parent.parent.resolve() != controlled_root.resolve()
        or attempt_root.parent.is_symlink()
        or attempt_root.exists() or attempt_root.is_symlink()
    ):
        raise RouteStop("rtc_readme_attempt_collision")
    try:
        attempt_root.parent.mkdir(parents=True, exist_ok=True)
        if not _safe_directory(attempt_root.parent):
            raise RouteStop("rtc_readme_attempt_parent_invalid")
        attempt_root.mkdir(exist_ok=False)
    except RouteStop:
        raise
    except OSError:
        raise RouteStop("rtc_readme_attempt_reservation_failed") from None
    _write_new_json(attempt_root / "started.json", {
        "status": "read_only_probe_reserved", "source_id": SOURCE_ID,
        "job_id": EXACT_JOB_ID, "started_at_utc": now_utc(),
        "archive_bytes_mutated": False, "raster_pixels_read": False,
    })
    try:
        if not _safe_file(archive) or archive.stat().st_size != acquisition["archive_size_bytes"]:
            raise RouteStop("rtc_readme_archive_identity_invalid")
        before = archive.stat()
        if _sha(archive) != acquisition["archive_sha256"]:
            raise RouteStop("rtc_readme_archive_hash_mismatch")
        result = inspect(SOURCE_ID, archive, acquisition["product_filename"])
        after = archive.stat()
        if (after.st_size, after.st_mtime_ns, after.st_ino) != (
            before.st_size, before.st_mtime_ns, before.st_ino
        ):
            raise RouteStop("rtc_readme_archive_changed_during_probe")
        if result.get("status") not in {
            "pass_readme_exact_source_text_only", "defer_readme_source_text_review",
        } or result.get("source_id") != SOURCE_ID:
            raise RouteStop("rtc_readme_result_invalid")
        terminal = {
            "status": result["status"], "source_id": SOURCE_ID,
            "job_id": EXACT_JOB_ID, "finished_at_utc": now_utc(),
            "product_filename": acquisition["product_filename"],
            "readme_member_size_bytes": result["readme_member_size_bytes"],
            "readme_sha256": result["readme_sha256"],
            "exact_source_granule_text_present": result["exact_source_granule_text_present"],
            "exact_product_base_text_present": result["exact_product_base_text_present"],
            "archive_sha256_verified_current": True,
            "archive_bytes_mutated": False, "raster_pixels_read": False,
        }
    except RouteStop as exc:
        terminal = {
            "status": "stopped_read_only_no_automatic_retry",
            "source_id": SOURCE_ID, "job_id": EXACT_JOB_ID,
            "code": exc.code, "finished_at_utc": now_utc(),
            "archive_bytes_mutated": False, "raster_pixels_read": False,
        }
    except Exception:
        terminal = {
            "status": "stopped_read_only_no_automatic_retry",
            "source_id": SOURCE_ID, "job_id": EXACT_JOB_ID,
            "code": "rtc_readme_unexpected_failure", "finished_at_utc": now_utc(),
            "archive_bytes_mutated": False, "raster_pixels_read": False,
        }
    _write_new_json(attempt_root / "terminal.json", terminal)
    return terminal


def main() -> int:
    try:
        acquisition, archive = require_readme_release()
        if sys.argv[1:] == ["--check-release"]:
            print(json.dumps({"status": "pass_readme_release_no_product_read"}))
            return 0
        if sys.argv[1:]:
            raise RouteStop("rtc_readme_arguments_invalid")
        result = probe_readme_once(acquisition, archive)
        print(json.dumps({"status": result["status"], "source_id": SOURCE_ID,
                          "code": result.get("code"), "raster_pixels_read": False}, sort_keys=True))
        return 0 if result["status"] in {
            "pass_readme_exact_source_text_only", "defer_readme_source_text_review",
        } else 12
    except RouteStop as exc:
        print(json.dumps({"status": "stopped", "code": exc.code,
                          "raster_pixels_read": False}, sort_keys=True))
        return 12
    except BaseException:
        print(json.dumps({"status": "stopped", "code": "rtc_readme_unexpected_failure",
                          "raster_pixels_read": False}, sort_keys=True))
        return 20


if __name__ == "__main__":
    raise SystemExit(main())
