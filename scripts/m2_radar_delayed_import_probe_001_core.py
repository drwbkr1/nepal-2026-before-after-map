#!/usr/bin/env python3
"""Portable controls for the bounded M2 delayed-import diagnostic probe."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any, Iterable


ATTEMPT_ID = "radar-delayed-import-probe-001-real-001"
FILE_COUNT = 156
TOTAL_LOGICAL_BYTES = 10_367_157_634
MIN_FREE_BYTES = 2 * 1024**3
CORPUS_NAMES = tuple(f"probe-{index:03d}.bin" for index in range(FILE_COUNT))
STAGE_ORDER = (
    "attempt_reserved",
    "corpus_create_started",
    "corpus_create_completed",
    "corpus_hash_started",
    "corpus_hash_completed",
    "arcpy_import_started",
    "arcpy_import_completed",
    "product_info_started",
    "product_info_completed",
    "overwrite_output_started",
    "overwrite_output_completed",
    "image_analyst_checkout_started",
    "image_analyst_checkout_completed",
    "spatial_checkout_started",
    "spatial_checkout_completed",
    "disposable_raster_a_started",
    "disposable_raster_a_completed",
    "disposable_raster_b_started",
    "disposable_raster_b_completed",
    "disposable_mosaic_started",
    "disposable_mosaic_completed",
    "spatial_checkin_started",
    "spatial_checkin_completed",
    "image_analyst_checkin_started",
    "image_analyst_checkin_completed",
    "terminal_receipt_persisted",
    "cleanup_started",
    "cleanup_completed_or_warning",
)

_TOKEN = re.compile(r"(?i)(?:bearer\s+)?eyJ[a-z0-9_-]{16,}\.[a-z0-9_-]{16,}(?:\.[a-z0-9_-]{8,})?")
_WINDOWS_PATH = re.compile(r"(?i)(?:[a-z]:\\|\\\\)[^\r\n\"']+")


class ProbeError(RuntimeError):
    def __init__(self, code: str, detail: str | None = None):
        self.code = code
        super().__init__(detail or code)


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_file(path: Path, *, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def write_new_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_bytes(value)
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def append_jsonl(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"
    with path.open("ab", buffering=0) as stream:
        stream.write(payload)
        os.fsync(stream.fileno())


def size_plan(file_count: int = FILE_COUNT, total_bytes: int = TOTAL_LOGICAL_BYTES) -> list[int]:
    if file_count <= 0 or total_bytes < file_count:
        raise ProbeError("invalid_corpus_dimensions")
    base, remainder = divmod(total_bytes, file_count)
    sizes = [base + (1 if index < remainder else 0) for index in range(file_count)]
    if len(sizes) != file_count or sum(sizes) != total_bytes or max(sizes) - min(sizes) > 1:
        raise ProbeError("corpus_size_plan_invariant_failed")
    return sizes


def require_outside(candidate: Path, forbidden_roots: Iterable[Path]) -> Path:
    resolved = candidate.resolve(strict=False)
    for forbidden in forbidden_roots:
        blocked = forbidden.resolve(strict=False)
        try:
            resolved.relative_to(blocked)
        except ValueError:
            continue
        raise ProbeError("probe_path_inside_forbidden_root")
    return resolved


def local_attempt_root() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    return base / "Codex" / "nepal-2026-before-after-map" / "diagnostics" / "radar-delayed-import-probe-001" / ATTEMPT_ID


def _mark_sparse_windows(stream: Any) -> None:
    if os.name != "nt":
        raise ProbeError("windows_sparse_files_required")
    import ctypes
    import msvcrt
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    device_io = kernel32.DeviceIoControl
    device_io.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPVOID,
    ]
    device_io.restype = wintypes.BOOL
    returned = wintypes.DWORD(0)
    if not device_io(
        wintypes.HANDLE(msvcrt.get_osfhandle(stream.fileno())),
        0x000900C4,
        None,
        0,
        None,
        0,
        ctypes.byref(returned),
        None,
    ):
        raise ProbeError("sparse_mark_failed", f"winerror_{ctypes.get_last_error()}")


def create_sparse_file(path: Path, logical_bytes: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        _mark_sparse_windows(stream)
        stream.truncate(logical_bytes)
        stream.flush()
        os.fsync(stream.fileno())
    if path.stat().st_size != logical_bytes:
        raise ProbeError("sparse_file_logical_size_mismatch")


def create_corpus(corpus_root: Path) -> list[Path]:
    if corpus_root.exists():
        raise ProbeError("corpus_root_collision")
    corpus_root.mkdir(parents=True)
    paths: list[Path] = []
    for name, logical_bytes in zip(CORPUS_NAMES, size_plan(), strict=True):
        path = corpus_root / name
        create_sparse_file(path, logical_bytes)
        paths.append(path)
    observed = sorted(corpus_root.iterdir(), key=lambda item: item.name.casefold())
    if [item.name for item in observed] != list(CORPUS_NAMES):
        raise ProbeError("corpus_name_inventory_mismatch")
    if sum(item.stat().st_size for item in observed) != TOTAL_LOGICAL_BYTES:
        raise ProbeError("corpus_total_logical_size_mismatch")
    return observed


def scan_corpus(paths: Iterable[Path], *, chunk_size: int = 8 * 1024 * 1024) -> dict[str, Any]:
    ordered = sorted(paths, key=lambda item: item.name.casefold())
    aggregate = hashlib.sha256()
    files: list[dict[str, Any]] = []
    started = time.perf_counter()
    for path in ordered:
        size = path.stat().st_size
        file_digest = sha256_file(path, chunk_size=chunk_size)
        aggregate.update(path.name.encode("utf-8"))
        aggregate.update(b"\x00")
        aggregate.update(str(size).encode("ascii"))
        aggregate.update(b"\x00")
        aggregate.update(file_digest.encode("ascii"))
        aggregate.update(b"\n")
        files.append({"name": path.name, "logical_bytes": size, "sha256": file_digest})
    elapsed = time.perf_counter() - started
    return {
        "file_count": len(files),
        "total_logical_bytes": sum(item["logical_bytes"] for item in files),
        "aggregate_sha256": aggregate.hexdigest(),
        "elapsed_seconds": round(elapsed, 6),
        "files": files,
    }


def validate_scan(summary: dict[str, Any]) -> None:
    if summary.get("file_count") != FILE_COUNT:
        raise ProbeError("corpus_hash_file_count_mismatch")
    if summary.get("total_logical_bytes") != TOTAL_LOGICAL_BYTES:
        raise ProbeError("corpus_hash_logical_size_mismatch")
    names = [item.get("name") for item in summary.get("files", [])]
    if names != list(CORPUS_NAMES):
        raise ProbeError("corpus_hash_order_mismatch")


def sanitize_text(value: object, replacements: Iterable[Path] = ()) -> str:
    text = str(value)
    for path in replacements:
        rendered = str(path)
        if rendered:
            text = text.replace(rendered, "<REDACTED_PATH>")
    text = _TOKEN.sub("<REDACTED_TOKEN>", text)
    text = _WINDOWS_PATH.sub("<REDACTED_PATH>", text)
    return text[:2000]


def safe_error(exc: BaseException, replacements: Iterable[Path] = ()) -> dict[str, str]:
    return {
        "failure_code": sanitize_text(getattr(exc, "code", "probe_unexpected_failure"), replacements),
        "failure_type": type(exc).__name__,
        "failure_message": sanitize_text(exc, replacements),
    }


def cleanup_payload(attempt_root: Path) -> tuple[str, list[str]]:
    warnings: list[str] = []
    for child_name in ("corpus", "scratch"):
        child = attempt_root / child_name
        if not child.exists():
            continue
        try:
            shutil.rmtree(child)
        except Exception as exc:  # cleanup must retain the terminal result
            warnings.append(sanitize_text(exc, (attempt_root,)))
    return ("cleanup_completed" if not warnings else "cleanup_warning", warnings)


def stage_positions(stages: Iterable[str]) -> list[int]:
    index = {stage: position for position, stage in enumerate(STAGE_ORDER)}
    positions: list[int] = []
    for stage in stages:
        if stage not in index:
            raise ProbeError("unknown_stage", stage)
        positions.append(index[stage])
    return positions


__all__ = [
    "ATTEMPT_ID",
    "CORPUS_NAMES",
    "FILE_COUNT",
    "MIN_FREE_BYTES",
    "ProbeError",
    "STAGE_ORDER",
    "TOTAL_LOGICAL_BYTES",
    "append_jsonl",
    "canonical_bytes",
    "cleanup_payload",
    "create_corpus",
    "create_sparse_file",
    "local_attempt_root",
    "require_outside",
    "safe_error",
    "scan_corpus",
    "sha256_file",
    "size_plan",
    "stage_positions",
    "validate_scan",
    "write_new_json",
]
