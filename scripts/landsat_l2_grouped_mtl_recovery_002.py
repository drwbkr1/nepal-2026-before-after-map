#!/usr/bin/env python3
"""One-shot, group-aware Landsat container recovery into non-Git custody.

This module never initiates a browser or network request. Real use requires a
separately verified public-CI gate and no-payload preflight. Receipts omit
private paths, browser URLs, credentials, and arbitrary exception text.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from landsat_l2_grouped_mtl_integrity_002 import BundleIntegrityError, inspect_bundle
from m2_transfer_core import (
    TransferControlError, ensure_directory, is_reparse_point,
    promote_atomic_no_replace, require_safe_child, sha256_file, write_new_json,
)


INTAKE_ID = "nepal-m2-landsat9-grouped-mtl-recovery-002"
APPROVAL_REF = "records/source-gates/m2-landsat9-grouped-mtl-recovery-002-approval.json"
APPROVAL_SHA256 = "f3b713e63259c60b758e7155ce9fc04e76917d40d6e23167e35d1c716afa8282"
PRODUCTS = {
    "before": ("LC09_L2SP_141040_20260810_20260811_02_T1", "LC91410402026222LGN00", "landsat9-before-20260810-grouped-mtl-recovery-002"),
    "after": ("LC09_L2SP_141040_20260826_20260827_02_T1", "LC91410402026238LGN00", "landsat9-after-20260826-grouped-mtl-intake-002"),
}
PRESERVED_BEFORE_REL = Path(".intake-staging/nepal-m2-landsat9-local-download-recovery-001/attempt-bytes/landsat9-before-20260810-recovery-001") / (PRODUCTS["before"][0] + ".tar.part")
PRESERVED_BEFORE_SIZE = 1126565376
PRESERVED_BEFORE_SHA256 = "9f9a5a63e7abd78f889c9f5229a80f62008b6c31e88b212bf8af01950ca9b255"
MAX_BYTES = 8 * 1024**3
CHUNK_BYTES = 8 * 1024**2
ARRIVAL_LIMIT_SECONDS = 900
STABLE_SECONDS = 30
PARTIAL_SUFFIXES = (".crdownload", ".part", ".partial", ".tmp")
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class RecoveryError(RuntimeError):
    """A fixed, non-secret failure code."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _code(error: BaseException) -> str:
    if isinstance(error, (RecoveryError, BundleIntegrityError, TransferControlError)):
        code = str(error)
        if re.fullmatch(r"[a-z0-9_]+", code):
            return code
    return "local_recovery_io_or_unexpected_failure"


@dataclass(frozen=True)
class Paths:
    role: str
    product_id: str
    scene_id: str
    attempt_id: str
    attempt_dir: Path
    staging: Path
    destination: Path
    base_file: Path
    numbered_file: Path


def paths(controlled_root: Path, downloads: Path, role: str) -> Paths:
    if role not in PRODUCTS:
        raise RecoveryError("role_invalid")
    if controlled_root.name != "nepal-2026-before-after-map-data":
        raise RecoveryError("controlled_root_identity_invalid")
    if not controlled_root.is_dir() or controlled_root.is_symlink() or is_reparse_point(controlled_root):
        raise RecoveryError("controlled_root_unsafe")
    if not downloads.is_dir() or downloads.is_symlink() or is_reparse_point(downloads):
        raise RecoveryError("downloads_root_unsafe")
    product, scene, attempt = PRODUCTS[role]
    stage_root = controlled_root / ".intake-staging" / INTAKE_ID
    p = Paths(
        role, product, scene, attempt,
        stage_root / "attempt-events" / attempt,
        stage_root / "attempt-bytes" / attempt / f"{product}.tar.part",
        controlled_root / "custody" / "landsat9-c2l2" / f"{product}.tar",
        downloads / f"{product}.tar",
        downloads / f"{product} (1).tar",
    )
    for candidate in (p.attempt_dir, p.staging, p.destination):
        require_safe_child(controlled_root, candidate)
    return p


def _source_stamp(path: Path, downloads: Path) -> dict:
    allowed_names = {name for product, _, _ in PRODUCTS.values()
                     for name in (f"{product}.tar", f"{product} (1).tar")}
    if path.parent != downloads or path.name not in allowed_names:
        raise RecoveryError("source_name_invalid")
    if path.is_symlink() or is_reparse_point(path):
        raise RecoveryError("source_reparse_or_symlink")
    try:
        info = path.stat(follow_symlinks=False)
    except FileNotFoundError as error:
        raise RecoveryError("exact_source_missing") from error
    if not stat.S_ISREG(info.st_mode):
        raise RecoveryError("source_not_regular")
    if info.st_size <= 0 or info.st_size > MAX_BYTES:
        raise RecoveryError("source_size_out_of_bounds")
    return {"size_bytes": info.st_size, "mtime_ns": info.st_mtime_ns,
            "device": info.st_dev, "inode": info.st_ino}


def _require_stamp(path: Path, downloads: Path, expected: dict) -> dict:
    actual = _source_stamp(path, downloads)
    if actual != expected:
        raise RecoveryError("source_metadata_or_identity_changed")
    return actual


def _gate(gate: dict) -> None:
    if (gate.get("status") != "pass_final_no_content_preflight"
            or gate.get("approval_sha256") != APPROVAL_SHA256
            or not HEX40.fullmatch(str(gate.get("public_ci_commit", "")))
            or not re.fullmatch(r"[0-9]{8,20}", str(gate.get("public_ci_run_id", "")))
            or gate.get("public_ci_conclusion") != "success"):
        raise RecoveryError("execution_gate_invalid")


def reserve(p: Paths, controlled_root: Path, gate: dict) -> dict:
    """Durably reserve a fresh role-specific attempt before content or click."""
    _gate(gate)
    if p.attempt_dir.exists() or p.attempt_dir.is_symlink() or p.staging.exists() or p.staging.is_symlink():
        raise RecoveryError("attempt_or_staging_collision")
    if p.destination.exists() or p.destination.is_symlink():
        raise RecoveryError("destination_collision")
    if not HEX64.fullmatch(str(gate.get("preflight_sha256", ""))):
        raise RecoveryError("preflight_hash_invalid")
    ensure_directory(p.attempt_dir.parent, controlled_root)
    ensure_directory(p.staging.parent, controlled_root)
    ensure_directory(p.destination.parent, controlled_root)
    p.attempt_dir.mkdir()
    receipt = {"schema_version": "1.0", "attempt_id": p.attempt_id,
               "product_id": p.product_id, "scene_id": p.scene_id,
               "approval_ref": APPROVAL_REF, "approval_sha256": APPROVAL_SHA256,
               "public_ci_commit": gate["public_ci_commit"],
               "public_ci_run_id": str(gate["public_ci_run_id"]),
               "preflight_sha256": gate["preflight_sha256"],
               "reserved_at_utc": _now(), "status": "reserved_no_payload_read_or_browser_action"}
    write_new_json(p.attempt_dir / "reservation.json", receipt)
    return receipt


def _require_reservation(p: Paths) -> None:
    path = p.attempt_dir / "reservation.json"
    if not path.is_file() or path.is_symlink() or is_reparse_point(path):
        raise RecoveryError("reservation_missing")
    if ((p.attempt_dir / "terminal.json").exists()
            or (p.attempt_dir / "terminal-fallback.json").exists()):
        raise RecoveryError("attempt_already_terminal")
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if (receipt.get("attempt_id"), receipt.get("product_id"), receipt.get("approval_sha256")) != (p.attempt_id, p.product_id, APPROVAL_SHA256):
        raise RecoveryError("reservation_identity_invalid")


def mark_after_click(p: Paths, before_terminal: dict) -> dict:
    """Count the sole after browser action before the UI control is pressed."""
    if p.role != "after":
        raise RecoveryError("before_browser_action_forbidden")
    _require_reservation(p)
    if before_terminal.get("status") != "pass_bundle_promoted_container_only" or before_terminal.get("attempt_id") != PRODUCTS["before"][2]:
        raise RecoveryError("before_dependency_not_promoted")
    before_destination = p.destination.parent / f"{PRODUCTS['before'][0]}.tar"
    if (not before_destination.is_file() or before_destination.is_symlink()
            or is_reparse_point(before_destination)
            or before_destination.stat().st_size != before_terminal.get("size_bytes")
            or sha256_file(before_destination) != before_terminal.get("sha256")):
        raise RecoveryError("before_promoted_file_missing_or_changed")
    if any(candidate.exists() or candidate.is_symlink() for candidate in (p.base_file, p.numbered_file)):
        raise RecoveryError("after_output_preexists")
    if _partial_names(p):
        raise RecoveryError("after_partial_preexists")
    marker = {"schema_version": "1.0", "attempt_id": p.attempt_id,
              "marked_at_utc": _now(), "status": "one_browser_click_about_to_start",
              "owner_initiated_clicks_counted": 1, "exact_outputs_present_before_click": 0}
    write_new_json(p.attempt_dir / "browser-click-started.json", marker)
    return marker


def _partial_names(p: Paths) -> list[str]:
    names = {p.base_file.name, p.numbered_file.name}
    return sorted(child.name for child in p.base_file.parent.iterdir()
                  if any(child.name == name + suffix for name in names for suffix in PARTIAL_SUFFIXES))


def _require_click_marker(p: Paths) -> None:
    marker_path = p.attempt_dir / "browser-click-started.json"
    if not marker_path.is_file() or marker_path.is_symlink() or is_reparse_point(marker_path):
        raise RecoveryError("after_click_marker_missing")
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    if (marker.get("attempt_id") != p.attempt_id
            or marker.get("status") != "one_browser_click_about_to_start"
            or marker.get("owner_initiated_clicks_counted") != 1):
        raise RecoveryError("after_click_marker_invalid")


def wait_for_after(p: Paths, *, clock=time.monotonic, pause=time.sleep,
                   limit_seconds: int = ARRIVAL_LIMIT_SECONDS,
                   stable_seconds: int = STABLE_SECONDS) -> tuple[list[Path], dict]:
    """Bounded metadata-only monitor; no archive byte is read here."""
    if p.role != "after":
        raise RecoveryError("role_invalid")
    _require_click_marker(p)
    started = clock()
    stable_since: float | None = None
    prior: tuple | None = None
    while clock() - started <= limit_seconds:
        files = [candidate for candidate in (p.base_file, p.numbered_file)
                 if candidate.exists() or candidate.is_symlink()]
        partials = _partial_names(p)
        if files:
            stamps = tuple((file.name, tuple(_source_stamp(file, file.parent).items())) for file in files)
            if stamps != prior or partials:
                prior, stable_since = stamps, None if partials else clock()
            elif stable_since is not None and clock() - stable_since >= stable_seconds:
                return files, {file.name: _source_stamp(file, file.parent) for file in files}
        pause(1)
    raise RecoveryError("after_arrival_timeout_or_incomplete")


def _hash_stable(path: Path, downloads: Path, expected: dict) -> str:
    _require_stamp(path, downloads, expected)
    digest = sha256_file(path)
    _require_stamp(path, downloads, expected)
    return digest


def _copy_stable(path: Path, downloads: Path, expected: dict, staging: Path, digest_expected: str) -> dict:
    _require_stamp(path, downloads, expected)
    if staging.exists() or staging.is_symlink():
        raise RecoveryError("staging_collision")
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as source, staging.open("xb") as target:
        for block in iter(lambda: source.read(CHUNK_BYTES), b""):
            total += len(block)
            if total > MAX_BYTES:
                raise RecoveryError("source_size_out_of_bounds")
            target.write(block)
            digest.update(block)
        target.flush()
        os.fsync(target.fileno())
    _require_stamp(path, downloads, expected)
    if total != expected["size_bytes"] or digest.hexdigest() != digest_expected:
        raise RecoveryError("source_changed_during_copy")
    return {"size_bytes": total, "sha256": digest.hexdigest()}


def _terminal(p: Paths, status: str, *, failure_code: str | None = None,
              payload: dict | None = None) -> dict:
    terminal = {"schema_version": "1.0", "attempt_id": p.attempt_id,
                "product_id": p.product_id, "scene_id": p.scene_id,
                "completed_at_utc": _now(), "status": status,
                "provider_checksum_verified": False, "pixel_or_header_qa_performed": False}
    if failure_code:
        terminal["failure_code"] = failure_code
    if payload:
        terminal.update(payload)
    try:
        write_new_json(p.attempt_dir / "terminal.json", terminal)
    except BaseException:
        terminal = {"schema_version": "1.0", "attempt_id": p.attempt_id,
                    "product_id": p.product_id, "scene_id": p.scene_id,
                    "completed_at_utc": _now(),
                    "status": "block_terminal_receipt_persistence_failure",
                    "failure_code": "terminal_receipt_persistence_failed",
                    "provider_checksum_verified": False, "pixel_or_header_qa_performed": False}
        write_new_json(p.attempt_dir / "terminal-fallback.json", terminal)
    finally:
        write_new_json(p.attempt_dir / "cleanup.json", {
            "schema_version": "1.0", "attempt_id": p.attempt_id,
            "recorded_at_utc": _now(), "staging_retained": p.staging.exists(),
            "source_original_retained": True,
            "downloads_originals_deleted_or_relocated": False,
            "status": "cleanup_recorded_sources_retained"})
    return terminal


def _preserved_stamp(controlled_root: Path) -> tuple[Path, dict]:
    source = controlled_root / PRESERVED_BEFORE_REL
    require_safe_child(controlled_root, source)
    if not source.exists():
        raise RecoveryError("preserved_source_missing")
    if source.is_symlink() or is_reparse_point(source):
        raise RecoveryError("preserved_source_reparse_or_symlink")
    try:
        info = source.stat(follow_symlinks=False)
    except FileNotFoundError:
        raise RecoveryError("preserved_source_missing") from None
    if not stat.S_ISREG(info.st_mode) or info.st_size != PRESERVED_BEFORE_SIZE:
        raise RecoveryError("preserved_source_metadata_invalid")
    return source, {"size_bytes": info.st_size, "mtime_ns": info.st_mtime_ns,
                    "device": info.st_dev, "inode": info.st_ino}


def complete_before_preserved(p: Paths, controlled_root: Path) -> dict:
    """Read the exact retained source only after the new reservation exists."""
    if p.role != "before":
        raise RecoveryError("role_invalid")
    _require_reservation(p)
    try:
        source, stamp = _preserved_stamp(controlled_root)
        if sha256_file(source) != PRESERVED_BEFORE_SHA256 or _preserved_stamp(controlled_root)[1] != stamp:
            raise RecoveryError("preserved_source_digest_or_metadata_mismatch")
        digest = hashlib.sha256()
        total = 0
        with source.open("rb") as stream, p.staging.open("xb") as target:
            for block in iter(lambda: stream.read(CHUNK_BYTES), b""):
                total += len(block)
                if total > PRESERVED_BEFORE_SIZE:
                    raise RecoveryError("preserved_source_size_changed")
                target.write(block)
                digest.update(block)
            target.flush()
            os.fsync(target.fileno())
        if (total != PRESERVED_BEFORE_SIZE or digest.hexdigest() != PRESERVED_BEFORE_SHA256
                or _preserved_stamp(controlled_root)[1] != stamp):
            raise RecoveryError("preserved_source_changed_during_copy")
        write_new_json(p.attempt_dir / "staged.json", {
            "schema_version": "1.0", "attempt_id": p.attempt_id,
            "recorded_at_utc": _now(), "status": "staged_preserved_copy_only",
            "size_bytes": total, "sha256": digest.hexdigest()})
        checked = inspect_bundle(p.staging, p.product_id, p.scene_id)
        if (checked["archive_size_bytes"], checked["archive_sha256"]) != (total, digest.hexdigest()):
            raise RecoveryError("staged_identity_changed")
        write_new_json(p.attempt_dir / "verification.json", {
            "schema_version": "1.0", "attempt_id": p.attempt_id,
            "recorded_at_utc": _now(), **checked})
        promoted = promote_atomic_no_replace(p.staging, p.destination)
        if promoted != {"size_bytes": total, "sha256": digest.hexdigest()}:
            raise RecoveryError("promoted_identity_changed")
        return _terminal(p, "pass_bundle_promoted_container_only", payload={
            **promoted, "member_count": checked["member_count"],
            "source_role": "frozen_preserved_staging_copy", "source_count": 1})
    except BaseException as error:
        return _terminal(p, "block_preserved_before_container_failure", failure_code=_code(error))


def complete(p: Paths, controlled_root: Path, downloads: Path,
             source_stamps: dict[str, dict]) -> dict:
    """One terminal completion of an already reserved exact-source attempt."""
    _require_reservation(p)
    if p.role != "after":
        raise RecoveryError("before_download_reuse_forbidden")
    _require_click_marker(p)
    try:
        files = [candidate for candidate in (p.base_file, p.numbered_file)
                 if candidate.name in source_stamps]
        if not 1 <= len(files) <= 2:
            raise RecoveryError("after_output_count_invalid")
        actual_names = {candidate.name for candidate in (p.base_file, p.numbered_file)
                        if candidate.exists() or candidate.is_symlink()}
        if actual_names != set(source_stamps):
            raise RecoveryError("output_ambiguous_or_incomplete")
        if set(source_stamps) != {file.name for file in files} or _partial_names(p):
            raise RecoveryError("output_ambiguous_or_incomplete")
        digests = [_hash_stable(file, downloads, source_stamps[file.name]) for file in files]
        if len(set(digests)) != 1:
            raise RecoveryError("duplicate_hash_mismatch")
        selected = p.base_file if p.base_file in files else p.numbered_file
        copied = _copy_stable(selected, downloads, source_stamps[selected.name], p.staging, digests[0])
        write_new_json(p.attempt_dir / "staged.json", {
            "schema_version": "1.0", "attempt_id": p.attempt_id,
            "recorded_at_utc": _now(), "status": "staged_local_copy_only",
            "source_count": len(files), **copied})
        checked = inspect_bundle(p.staging, p.product_id, p.scene_id)
        if (checked["archive_size_bytes"], checked["archive_sha256"]) != (copied["size_bytes"], copied["sha256"]):
            raise RecoveryError("staged_identity_changed")
        write_new_json(p.attempt_dir / "verification.json", {
            "schema_version": "1.0", "attempt_id": p.attempt_id,
            "recorded_at_utc": _now(), **checked})
        promoted = promote_atomic_no_replace(p.staging, p.destination)
        if promoted != copied:
            raise RecoveryError("promoted_identity_changed")
        return _terminal(p, "pass_bundle_promoted_container_only", payload={
            **promoted, "member_count": checked["member_count"],
            "source_count": len(files), "local_duplicate_sha256_agreed": len(files) == 2})
    except BaseException as error:
        return _terminal(p, "block_local_handoff_or_container_failure", failure_code=_code(error))


def source_stamps(p: Paths, downloads: Path) -> dict[str, dict]:
    """Metadata-only snapshot for a no-payload preflight."""
    files = (p.base_file, p.numbered_file)
    return {file.name: _source_stamp(file, downloads) for file in files
            if file.exists() or file.is_symlink()}


def record_after_failure(p: Paths, code: str) -> dict:
    _require_reservation(p)
    if p.role != "after":
        raise RecoveryError("role_invalid")
    _require_click_marker(p)
    if not re.fullmatch(r"[a-z0-9_]+", code):
        code = "after_browser_or_monitor_failure"
    return _terminal(p, "block_after_browser_or_monitor_failure", failure_code=code)


def _cli() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Exact grouped-MTL Landsat recovery; no network access")
    parser.add_argument("action", choices=("before", "reserve-after", "complete-after"))
    args = parser.parse_args()
    root = Path(r"C:\Projects\Active\nepal-2026-before-after-map-data")
    downloads = Path.home() / "Downloads"
    gate_path = Path(r"C:\Projects\Active\nepal-2026-before-after-map") / "records" / "readiness" / "m2-landsat9-grouped-mtl-recovery-002-final-preflight-local.json"
    try:
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
        p = paths(root, downloads, "before" if args.action == "before" else "after")
        if args.action == "before":
            reserve(p, root, gate)
            result = complete_before_preserved(p, root)
        elif args.action == "reserve-after":
            before = paths(root, downloads, "before")
            prior = json.loads((before.attempt_dir / "terminal.json").read_text(encoding="utf-8"))
            if prior.get("status") != "pass_bundle_promoted_container_only":
                raise RecoveryError("before_dependency_not_promoted")
            reserve(p, root, gate)
            try:
                result = mark_after_click(p, prior)
            except BaseException as error:
                result = _terminal(p, "block_after_preclick_failure", failure_code=_code(error))
        else:
            try:
                _files, stamps = wait_for_after(p)
                result = complete(p, root, downloads, stamps)
            except BaseException as error:
                result = record_after_failure(p, _code(error))
        print(json.dumps({"attempt_id": p.attempt_id, "status": result["status"],
                          "failure_code": result.get("failure_code")}))
    except BaseException as error:
        print(json.dumps({"status": "stopped", "failure_code": _code(error)}))
        raise SystemExit(1) from None


if __name__ == "__main__":
    _cli()
