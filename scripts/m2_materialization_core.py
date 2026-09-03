#!/usr/bin/env python3
"""Fail-closed SAFE archive materialization controls for approved M2 products."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path, PurePosixPath
from typing import Any
from zipfile import BadZipFile, ZipFile, ZipInfo


WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}
WINDOWS_FORBIDDEN = set('<>:"|?*')


class MaterializationError(RuntimeError):
    """A materialization control rejected the operation."""

    def __init__(self, code: str, detail: str | None = None):
        super().__init__(code if detail is None else f"{code}: {detail}")
        self.code = code
        self.detail = detail


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_new_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(canonical_bytes(value))
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise MaterializationError("receipt_or_marker_collision", str(path)) from exc


def _is_reparse_point(path: Path) -> bool:
    attributes = getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def require_safe_child(root: Path, candidate: Path) -> Path:
    resolved_root = root.resolve(strict=True)
    resolved_candidate = candidate.resolve(strict=False)
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise MaterializationError("path_outside_materialization_root") from exc
    if resolved_candidate == resolved_root:
        raise MaterializationError("path_must_be_child")
    current = resolved_candidate.parent
    while True:
        if current.exists() and (_is_reparse_point(current) or not current.is_dir()):
            raise MaterializationError("unsafe_output_ancestor", str(current))
        if current == resolved_root:
            break
        if current == current.parent:
            raise MaterializationError("path_ancestor_escape")
        current = current.parent
    return resolved_candidate


def ensure_directory(path: Path, controlled_root: Path) -> None:
    safe = require_safe_child(controlled_root, path)
    missing: list[Path] = []
    current = safe
    root = controlled_root.resolve(strict=True)
    while current != root and not current.exists():
        missing.append(current)
        current = current.parent
    if not current.is_dir() or _is_reparse_point(current):
        raise MaterializationError("unsafe_output_ancestor", str(current))
    for item in reversed(missing):
        item.mkdir()
    if not safe.is_dir() or _is_reparse_point(safe):
        raise MaterializationError("unsafe_output_directory", str(safe))


def _validate_windows_component(component: str) -> None:
    if not component or component in {".", ".."}:
        raise MaterializationError("unsafe_member_component", component)
    if component[-1] in {".", " "}:
        raise MaterializationError("windows_trailing_dot_or_space", component)
    if any(ord(character) < 32 or character in WINDOWS_FORBIDDEN for character in component):
        raise MaterializationError("windows_forbidden_member_character", component)
    stem = component.rstrip(". ").split(".", 1)[0].upper()
    if stem in WINDOWS_RESERVED:
        raise MaterializationError("windows_reserved_member_name", component)


def _is_symbolic_link(info: ZipInfo) -> bool:
    return ((info.external_attr >> 16) & 0o170000) == stat.S_IFLNK


def inspect_safe_members(
    archive_path: Path,
    exact_product_id: str,
    controls: dict[str, Any],
) -> list[tuple[ZipInfo, str]]:
    """Return safe file members relative to the exact SAFE root or raise."""

    if not archive_path.is_file():
        raise MaterializationError("source_archive_missing")
    expected_root = exact_product_id + "/"
    try:
        with ZipFile(archive_path) as archive:
            infos = archive.infolist()
            if len(infos) > int(controls["maximum_member_count"]):
                raise MaterializationError("member_count_limit_exceeded")
            output: list[tuple[ZipInfo, str]] = []
            seen: set[str] = set()
            file_paths: set[str] = set()
            directory_paths: set[str] = set()
            total = 0
            for info in infos:
                # On Windows ZipInfo normalizes backslashes in ``filename``.
                # ``orig_filename`` preserves the raw archive spelling needed
                # for the cross-platform path-safety decision.
                name = info.orig_filename
                if "\\" in name:
                    raise MaterializationError("backslash_member_path", name)
                raw_parts = name.split("/")
                if info.is_dir() and raw_parts and raw_parts[-1] == "":
                    raw_parts = raw_parts[:-1]
                if name.startswith("/") or any(part in {"", ".", ".."} for part in raw_parts):
                    raise MaterializationError("unsafe_member_path", name)
                posix = PurePosixPath(name)
                if posix.is_absolute():
                    raise MaterializationError("unsafe_member_path", name)
                if info.flag_bits & 0x1:
                    raise MaterializationError("encrypted_member", name)
                if _is_symbolic_link(info):
                    raise MaterializationError("symbolic_link_member", name)
                if name in {exact_product_id, expected_root}:
                    if not info.is_dir():
                        raise MaterializationError("safe_root_entry_is_not_directory", name)
                    continue
                if not name.startswith(expected_root):
                    raise MaterializationError("member_outside_exact_safe_root", name)
                relative = name[len(expected_root):]
                rel = PurePosixPath(relative)
                for component in rel.parts:
                    _validate_windows_component(component)
                folded = "/".join(part.casefold() for part in rel.parts)
                if folded in seen:
                    raise MaterializationError("case_insensitive_member_collision", relative)
                seen.add(folded)
                ancestors = ["/".join(part.casefold() for part in rel.parts[:index]) for index in range(1, len(rel.parts))]
                if any(ancestor in file_paths for ancestor in ancestors):
                    raise MaterializationError("file_directory_member_collision", relative)
                if info.is_dir():
                    if folded in file_paths:
                        raise MaterializationError("file_directory_member_collision", relative)
                    directory_paths.add(folded)
                    continue
                if folded in directory_paths:
                    raise MaterializationError("file_directory_member_collision", relative)
                file_paths.add(folded)
                directory_paths.update(ancestors)
                if info.file_size > int(controls["maximum_single_uncompressed_bytes"]):
                    raise MaterializationError("single_member_size_limit_exceeded", relative)
                total += info.file_size
                output.append((info, relative))
            archive_size = archive_path.stat().st_size
            total_limit = max(
                int(controls["maximum_total_uncompressed_bytes_floor"]),
                int(archive_size * float(controls["maximum_total_uncompressed_to_archive_ratio"])),
            )
            if total > total_limit:
                raise MaterializationError("total_uncompressed_size_limit_exceeded")
            if not output:
                raise MaterializationError("safe_archive_has_no_files")
            return output
    except BadZipFile as exc:
        raise MaterializationError("invalid_zip_archive") from exc


def materialize_archive(
    *,
    archive_path: Path,
    attempt_root: Path,
    source_id: str,
    exact_product_id: str,
    archive_sha256: str,
    controls: dict[str, Any],
    started_at_utc: str,
) -> dict[str, Any]:
    """Extract an approved archive into one exclusive, append-only attempt."""

    members = inspect_safe_members(archive_path, exact_product_id, controls)
    if attempt_root.exists():
        raise MaterializationError("materialization_attempt_collision")
    attempt_root.mkdir()
    write_new_json(
        attempt_root / "started.json",
        {
            "status": "started",
            "source_id": source_id,
            "exact_product_id": exact_product_id,
            "archive_sha256": archive_sha256,
            "started_at_utc": started_at_utc,
        },
    )
    safe_root = attempt_root / exact_product_id
    safe_root.mkdir()
    manifest_files: list[dict[str, Any]] = []
    total_bytes = 0
    try:
        with ZipFile(archive_path) as archive:
            for info, relative in members:
                target = safe_root.joinpath(*PurePosixPath(relative).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                digest = hashlib.sha256()
                size = 0
                try:
                    with archive.open(info, "r") as source, target.open("xb") as destination:
                        while True:
                            block = source.read(8 * 1024 * 1024)
                            if not block:
                                break
                            destination.write(block)
                            digest.update(block)
                            size += len(block)
                        destination.flush()
                        os.fsync(destination.fileno())
                except FileExistsError as exc:
                    raise MaterializationError("extracted_member_collision", relative) from exc
                if size != info.file_size:
                    raise MaterializationError("extracted_member_size_mismatch", relative)
                total_bytes += size
                manifest_files.append(
                    {
                        "relative_path": relative,
                        "size_bytes": size,
                        "zip_crc32": f"{info.CRC:08x}",
                        "sha256": digest.hexdigest(),
                    }
                )
    except MaterializationError:
        raise
    except Exception as exc:
        raise MaterializationError("archive_extraction_failed", type(exc).__name__) from exc
    if sha256_file(archive_path) != archive_sha256:
        raise MaterializationError("source_archive_changed_during_materialization")
    manifest = {
        "manifest_version": "1.0",
        "status": "complete",
        "source_id": source_id,
        "exact_product_id": exact_product_id,
        "archive_sha256": archive_sha256,
        "file_count": len(manifest_files),
        "total_extracted_bytes": total_bytes,
        "files": manifest_files,
    }
    manifest_path = attempt_root / "materialization-manifest.json"
    write_new_json(manifest_path, manifest)
    completed = {
        "status": "complete",
        "source_id": source_id,
        "exact_product_id": exact_product_id,
        "archive_sha256": archive_sha256,
        "manifest_sha256": sha256_file(manifest_path),
        "file_count": len(manifest_files),
        "total_extracted_bytes": total_bytes,
    }
    write_new_json(attempt_root / "completed.json", completed)
    return {**completed, "manifest_path": str(manifest_path), "safe_root": str(safe_root)}
