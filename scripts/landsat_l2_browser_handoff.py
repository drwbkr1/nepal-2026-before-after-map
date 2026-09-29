#!/usr/bin/env python3
"""Controlled local handoff for an already completed EarthExplorer bundle download.

No network request, browser action, credential handling, TIFF read, or pixel
processing occurs here. The caller must satisfy the approved public-CI and
no-payload preflight gates before reserving a real attempt or clicking a
Download Product control. All receipts are sanitized and append-only.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from landsat_l2_bundle_integrity import BundleIntegrityError, inspect_bundle
from m2_transfer_core import (
    TransferControlError,
    ensure_directory,
    is_reparse_point,
    promote_atomic_no_replace,
    require_safe_child,
    sha256_file,
    write_new_json,
)


ATTEMPT_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,95}$")
CHUNK_BYTES = 8 * 1024 * 1024
MAX_BUNDLE_BYTES = 8 * 1024**3
EXACT_SCENES = {
    "LC09_L2SP_141040_20260810_20260811_02_T1": "LC91410402026222LGN00",
    "LC09_L2SP_141040_20260826_20260827_02_T1": "LC91410402026238LGN00",
}
APPROVAL_REF = "records/source-gates/m2-landsat9-usgs-bundle-intake-001-approval.json"
APPROVAL_SHA256 = "bb00c9601f27b759d0e51a5df1b2dc62a117a06cf921c9281b4ae0423dbba375"


class HandoffError(RuntimeError):
    """A fixed, non-secret handoff failure code."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_code(error: BaseException) -> str:
    if isinstance(error, (HandoffError, BundleIntegrityError, TransferControlError)):
        return str(error)
    if isinstance(error, OSError):
        return "local_io_failure"
    return "unexpected_handoff_failure"


def _safe_file(path: Path, code: str) -> None:
    if not path.is_file() or path.is_symlink() or is_reparse_point(path):
        raise HandoffError(code)


def _check_paths(
    controlled_root: Path, attempt_dir: Path, staging: Path, destination: Path,
    attempt_id: str, product_id: str, scene_id: str,
) -> None:
    if EXACT_SCENES.get(product_id) != scene_id:
        raise HandoffError("exact_product_scene_identity_mismatch")
    if not ATTEMPT_ID.fullmatch(attempt_id):
        raise HandoffError("attempt_id_invalid")
    if not controlled_root.is_dir() or controlled_root.is_symlink() or is_reparse_point(controlled_root):
        raise HandoffError("controlled_root_unsafe")
    expected_attempt_dir = controlled_root / ".intake-staging" / "nepal-m2-landsat9-usgs-bundle-001" / "attempt-events" / attempt_id
    expected_staging = controlled_root / ".intake-staging" / "nepal-m2-landsat9-usgs-bundle-001" / "attempt-bytes" / attempt_id / f"{product_id}.tar.part"
    expected_destination = controlled_root / "custody" / "landsat9-c2l2" / f"{product_id}.tar"
    if any(
        os.path.normcase(os.path.abspath(actual)) != os.path.normcase(os.path.abspath(expected))
        for actual, expected in (
            (attempt_dir, expected_attempt_dir),
            (staging, expected_staging),
            (destination, expected_destination),
        )
    ):
        raise HandoffError("handoff_path_not_frozen")
    for path in (attempt_dir, staging, destination):
        require_safe_child(controlled_root, path)
    if len({str(path.resolve(strict=False)).casefold() for path in (attempt_dir, staging, destination)}) != 3:
        raise HandoffError("handoff_path_collision")
    if destination.exists() or destination.is_symlink():
        raise HandoffError("destination_collision")


def reserve_attempt(
    *, controlled_root: Path, attempt_dir: Path, staging: Path,
    destination: Path, attempt_id: str, product_id: str, scene_id: str,
    approval_ref: str, approval_sha256: str,
) -> dict:
    """Reserve one immutable attempt before a browser download is activated."""
    if approval_ref != APPROVAL_REF:
        raise HandoffError("approval_reference_mismatch")
    if approval_sha256 != APPROVAL_SHA256:
        raise HandoffError("approval_hash_mismatch")
    _check_paths(controlled_root, attempt_dir, staging, destination, attempt_id, product_id, scene_id)
    if attempt_dir.exists() or attempt_dir.is_symlink() or staging.exists() or staging.is_symlink():
        raise HandoffError("attempt_or_staging_collision")
    ensure_directory(attempt_dir.parent, controlled_root)
    ensure_directory(staging.parent, controlled_root)
    ensure_directory(destination.parent, controlled_root)
    attempt_dir.mkdir()
    reservation = {
        "schema_version": "1.0",
        "attempt_id": attempt_id,
        "product_id": product_id,
        "scene_id": scene_id,
        "approval_ref": approval_ref,
        "approval_sha256": approval_sha256,
        "reserved_at_utc": _now(),
        "status": "reserved_no_browser_request_yet",
        "contains_secret_or_local_path": False,
    }
    write_new_json(attempt_dir / "reservation.json", reservation)
    return reservation


def _copy_completed_file(source: Path, staging: Path) -> dict:
    _safe_file(source, "completed_browser_file_missing_or_unsafe")
    initial = source.stat()
    if initial.st_size <= 0 or initial.st_size > MAX_BUNDLE_BYTES:
        raise HandoffError("completed_browser_file_size_out_of_bounds")
    if staging.exists() or staging.is_symlink():
        raise HandoffError("staging_collision")
    if source.resolve() == staging.resolve(strict=False):
        raise HandoffError("source_is_staging")
    digest = hashlib.sha256()
    copied = 0
    with source.open("rb") as reader, staging.open("xb") as writer:
        for chunk in iter(lambda: reader.read(CHUNK_BYTES), b""):
            copied += len(chunk)
            if copied > MAX_BUNDLE_BYTES:
                raise HandoffError("completed_browser_file_size_out_of_bounds")
            writer.write(chunk)
            digest.update(chunk)
        writer.flush()
        os.fsync(writer.fileno())
    final = source.stat()
    if (initial.st_size, initial.st_mtime_ns) != (final.st_size, final.st_mtime_ns) or copied != initial.st_size:
        raise HandoffError("browser_file_changed_during_copy")
    if sha256_file(source) != digest.hexdigest():
        raise HandoffError("browser_file_changed_during_copy")
    return {"size_bytes": copied, "sha256": digest.hexdigest()}


def _load_reservation(attempt_dir: Path, attempt_id: str, product_id: str, scene_id: str) -> dict:
    reservation_path = attempt_dir / "reservation.json"
    _safe_file(reservation_path, "attempt_reservation_missing")
    if (attempt_dir / "terminal.json").exists():
        raise HandoffError("attempt_already_terminal")
    reservation = json.loads(reservation_path.read_text(encoding="utf-8"))
    if (
        reservation.get("attempt_id") != attempt_id
        or reservation.get("product_id") != product_id
        or reservation.get("scene_id") != scene_id
        or reservation.get("approval_ref") != APPROVAL_REF
        or reservation.get("approval_sha256") != APPROVAL_SHA256
        or reservation.get("status") != "reserved_no_browser_request_yet"
    ):
        raise HandoffError("attempt_reservation_identity_mismatch")
    return reservation


def mark_browser_request_started(
    *, controlled_root: Path, attempt_dir: Path, staging: Path,
    destination: Path, attempt_id: str, product_id: str, scene_id: str,
    public_ci_commit: str, public_ci_run_id: str, preflight_sha256: str,
) -> dict:
    """Durably count one owner-initiated browser action before the click."""
    _check_paths(controlled_root, attempt_dir, staging, destination, attempt_id, product_id, scene_id)
    _load_reservation(attempt_dir, attempt_id, product_id, scene_id)
    if not re.fullmatch(r"[0-9a-f]{40}", public_ci_commit):
        raise HandoffError("public_ci_commit_invalid")
    if not re.fullmatch(r"[0-9]{8,20}", public_ci_run_id):
        raise HandoffError("public_ci_run_id_invalid")
    if not re.fullmatch(r"[0-9a-f]{64}", preflight_sha256):
        raise HandoffError("preflight_hash_invalid")
    marker = {
        "schema_version": "1.0",
        "attempt_id": attempt_id,
        "product_id": product_id,
        "scene_id": scene_id,
        "marked_at_utc": _now(),
        "status": "one_browser_request_about_to_start",
        "public_ci_commit": public_ci_commit,
        "public_ci_run_id": public_ci_run_id,
        "preflight_sha256": preflight_sha256,
        "owner_initiated_request_budget_counted": 1,
    }
    write_new_json(attempt_dir / "browser-request-started.json", marker)
    return marker


def _require_browser_request_marker(attempt_dir: Path, attempt_id: str) -> None:
    marker_path = attempt_dir / "browser-request-started.json"
    _safe_file(marker_path, "browser_request_marker_missing")
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    if marker.get("attempt_id") != attempt_id or marker.get("status") != "one_browser_request_about_to_start":
        raise HandoffError("browser_request_marker_invalid")


def _write_terminal_and_cleanup(attempt_dir: Path, terminal: dict, staging: Path) -> None:
    write_new_json(attempt_dir / "terminal.json", terminal)
    write_new_json(attempt_dir / "cleanup.json", {
        "schema_version": "1.0",
        "attempt_id": terminal["attempt_id"],
        "recorded_at_utc": _now(),
        "staging_retained": staging.exists(),
        "browser_managed_source_deleted": False,
        "status": "pass_recorded_without_deleting_browser_source",
    })


def complete_attempt(
    *, completed_browser_file: Path, controlled_root: Path,
    attempt_dir: Path, staging: Path, destination: Path,
    attempt_id: str, product_id: str, scene_id: str,
) -> dict:
    """Copy, verify, and no-replace promote one completed browser download."""
    _load_reservation(attempt_dir, attempt_id, product_id, scene_id)
    _require_browser_request_marker(attempt_dir, attempt_id)
    try:
        _check_paths(controlled_root, attempt_dir, staging, destination, attempt_id, product_id, scene_id)
        staged = _copy_completed_file(Path(completed_browser_file), staging)
        write_new_json(attempt_dir / "staged.json", {
            "schema_version": "1.0",
            "attempt_id": attempt_id,
            "recorded_at_utc": _now(),
            "status": "staged_local_copy_only",
            **staged,
        })
        checked = inspect_bundle(staging, product_id, scene_id)
        if (checked["archive_size_bytes"], checked["archive_sha256"]) != (staged["size_bytes"], staged["sha256"]):
            raise HandoffError("staged_bundle_identity_changed")
        write_new_json(attempt_dir / "verification.json", {
            "schema_version": "1.0",
            "attempt_id": attempt_id,
            "recorded_at_utc": _now(),
            **checked,
        })
        promoted = promote_atomic_no_replace(staging, destination)
        if (promoted["size_bytes"], promoted["sha256"]) != (staged["size_bytes"], staged["sha256"]):
            raise HandoffError("promoted_bundle_identity_changed")
        terminal = {
            "schema_version": "1.0",
            "attempt_id": attempt_id,
            "product_id": product_id,
            "scene_id": scene_id,
            "completed_at_utc": _now(),
            "status": "pass_bundle_promoted_container_only",
            "size_bytes": promoted["size_bytes"],
            "sha256": promoted["sha256"],
            "member_count": checked["member_count"],
            "provider_checksum_verified": False,
            "pixel_or_header_qa_performed": False,
        }
    except BaseException as error:
        terminal = {
            "schema_version": "1.0",
            "attempt_id": attempt_id,
            "product_id": product_id,
            "scene_id": scene_id,
            "completed_at_utc": _now(),
            "status": "block_handoff_or_container_failure",
            "failure_code": _safe_code(error),
            "staging_retained": staging.exists(),
            "provider_checksum_verified": False,
            "pixel_or_header_qa_performed": False,
        }
    _write_terminal_and_cleanup(attempt_dir, terminal, staging)
    return terminal


def record_browser_failure(
    *, controlled_root: Path, attempt_dir: Path, staging: Path,
    destination: Path, attempt_id: str, product_id: str, scene_id: str,
    failure_code: str,
) -> dict:
    """Close a reserved attempt when no completed browser path is available."""
    if failure_code not in {"browser_download_failed", "browser_download_path_unavailable", "owner_cancelled"}:
        raise HandoffError("browser_failure_code_invalid")
    _load_reservation(attempt_dir, attempt_id, product_id, scene_id)
    _require_browser_request_marker(attempt_dir, attempt_id)
    _check_paths(controlled_root, attempt_dir, staging, destination, attempt_id, product_id, scene_id)
    terminal = {
        "schema_version": "1.0",
        "attempt_id": attempt_id,
        "product_id": product_id,
        "scene_id": scene_id,
        "completed_at_utc": _now(),
        "status": "block_browser_download_no_complete_file",
        "failure_code": failure_code,
        "staging_retained": staging.exists(),
        "pixel_or_header_qa_performed": False,
    }
    _write_terminal_and_cleanup(attempt_dir, terminal, staging)
    return terminal
