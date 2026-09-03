#!/usr/bin/env python3
"""Dependency-free controls for one-at-a-time M2 product transfer."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import urllib.request
from pathlib import Path
from typing import Any, BinaryIO


class TransferControlError(RuntimeError):
    """A fail-closed transfer control rejected the operation."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects so authorization never crosses the reviewed URL boundary."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001, ANN201
        return None


def canonical_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_new_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(canonical_bytes(value))
        handle.flush()
        os.fsync(handle.fileno())


def replace_json(path: Path, value: dict[str, Any], suffix: str) -> None:
    temporary = path.with_name(path.name + suffix)
    if temporary.exists():
        raise TransferControlError("temporary_control_path_exists")
    with temporary.open("xb") as handle:
        handle.write(canonical_bytes(value))
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def is_reparse_point(path: Path) -> bool:
    attributes = getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def require_safe_child(root: Path, candidate: Path) -> Path:
    resolved_root = root.resolve(strict=True)
    resolved_candidate = candidate.resolve(strict=False)
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise TransferControlError("path_outside_controlled_root") from exc
    if resolved_candidate == resolved_root:
        raise TransferControlError("path_must_be_child")
    current = resolved_candidate.parent
    while True:
        if current.exists() and is_reparse_point(current):
            raise TransferControlError("reparse_point_in_path")
        if current == resolved_root:
            break
        if current == current.parent:
            raise TransferControlError("path_ancestor_escape")
        current = current.parent
    return resolved_candidate


def ensure_directory(path: Path, controlled_root: Path) -> None:
    safe = require_safe_child(controlled_root, path)
    missing: list[Path] = []
    current = safe
    while current != controlled_root.resolve(strict=True) and not current.exists():
        missing.append(current)
        current = current.parent
    if not current.is_dir() or is_reparse_point(current):
        raise TransferControlError("unsafe_directory_ancestor")
    for item in reversed(missing):
        item.mkdir()
    if not safe.is_dir() or is_reparse_point(safe):
        raise TransferControlError("unsafe_directory")


def stream_to_exclusive_staging(
    source: BinaryIO,
    staging_path: Path,
    *,
    expected_size: int,
    expected_md5: str,
    chunk_size: int = 8 * 1024 * 1024,
) -> dict[str, Any]:
    if staging_path.exists():
        raise TransferControlError("staging_collision")
    sha256 = hashlib.sha256()
    md5 = hashlib.md5(usedforsecurity=False)
    size = 0
    with staging_path.open("xb") as handle:
        while True:
            block = source.read(chunk_size)
            if not block:
                break
            handle.write(block)
            sha256.update(block)
            md5.update(block)
            size += len(block)
        handle.flush()
        os.fsync(handle.fileno())
    result = {"size_bytes": size, "sha256": sha256.hexdigest(), "md5": md5.hexdigest()}
    if size != expected_size:
        raise TransferControlError("transferred_size_mismatch")
    if result["md5"].casefold() != expected_md5.casefold():
        raise TransferControlError("provider_md5_mismatch")
    return result


def promote_atomic_no_replace(staging_path: Path, destination_path: Path) -> dict[str, Any]:
    if not staging_path.is_file():
        raise TransferControlError("verified_staging_file_missing")
    if destination_path.exists():
        raise TransferControlError("destination_collision")
    try:
        os.link(staging_path, destination_path)
    except FileExistsError as exc:
        raise TransferControlError("destination_collision") from exc
    except OSError as exc:
        raise TransferControlError("atomic_no_replace_unavailable") from exc
    staged_size = staging_path.stat().st_size
    staged_sha = sha256_file(staging_path)
    promoted_size = destination_path.stat().st_size
    promoted_sha = sha256_file(destination_path)
    if promoted_size != staged_size or promoted_sha != staged_sha:
        raise TransferControlError("post_promotion_identity_mismatch")
    staging_path.unlink()
    return {"size_bytes": promoted_size, "sha256": promoted_sha}
