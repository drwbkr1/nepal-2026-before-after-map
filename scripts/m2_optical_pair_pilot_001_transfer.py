#!/usr/bin/env python3
"""One exact, byte-zero CDSE transfer with append-only non-Git evidence."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, BinaryIO, Callable, Mapping
from zipfile import BadZipFile, ZipFile

from m2_materialization_core import MaterializationError, inspect_safe_members
from m2_optical_pair_pilot_001_core import (
    PilotControlError,
    classify_terminal_exception,
    exact_catalog_url,
    exact_download_url,
    may_make_second_request,
    require_execution_release,
    sha256_file,
    validate_catalog_product,
    validate_catalog_footprint,
)
from m2_transfer_core import NoRedirectHandler, is_reparse_point, promote_atomic_no_replace, require_safe_child


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT.parent / f"{ROOT.name}-data"
MATERIALIZATION_CONTRACT = ROOT / "contracts/m2-materialization.json"
BUFFER_BYTES = 8 * 1024 * 1024


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_new_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write((json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PilotControlError("pilot_record_root_invalid")
    return value


def previous_attempts(attempts_root: Path) -> list[dict[str, Any]]:
    """A started request with no terminal evidence is indeterminate, not retryable."""
    if not attempts_root.exists():
        return []
    attempts: list[dict[str, Any]] = []
    for path in sorted(attempts_root.iterdir()):
        if not path.is_dir():
            raise PilotControlError("pilot_attempt_root_unexpected_entry")
        started = path / "started.json"
        terminal = path / "terminal.json"
        if not started.is_file() or not terminal.is_file():
            raise PilotControlError("pilot_prior_attempt_indeterminate")
        start, end = read_json(started), read_json(terminal)
        if start.get("attempt_id") != path.name or end.get("attempt_id") != path.name:
            raise PilotControlError("pilot_prior_attempt_identity_drift")
        attempts.append(end)
    return attempts


def verify_zip(path: Path, exact_name: str) -> dict[str, Any]:
    controls = read_json(MATERIALIZATION_CONTRACT)["member_controls"]
    try:
        safe_members = inspect_safe_members(path, exact_name, controls)
        with ZipFile(path) as archive:
            bad = archive.testzip()
            if bad is not None:
                raise PilotControlError("pilot_zip_crc_failure")
    except (BadZipFile, MaterializationError) as exc:
        raise PilotControlError("pilot_zip_container_invalid") from exc
    return {"safe_member_count": len(safe_members), "zip_crc_pass": True}


def hash_stream_to_new_file(
    stream: BinaryIO,
    stage: Path,
    *,
    expected_size: int,
    expected_md5: str,
    expected_blake3: str,
    progress: Callable[[int], None] | None = None,
) -> dict[str, Any]:
    import blake3

    if stage.exists():
        raise PilotControlError("pilot_stage_collision")
    md5 = hashlib.md5(usedforsecurity=False)
    sha256 = hashlib.sha256()
    b3 = blake3.blake3()
    size = 0
    with stage.open("xb") as output:
        while True:
            block = stream.read(BUFFER_BYTES)
            if not block:
                break
            output.write(block)
            md5.update(block)
            sha256.update(block)
            b3.update(block)
            size += len(block)
            if progress is not None:
                progress(size)
        output.flush()
        os.fsync(output.fileno())
    if size < expected_size:
        raise PilotControlError("transport_interrupted")
    if size > expected_size:
        raise PilotControlError("pilot_transferred_size_mismatch")
    if md5.hexdigest().casefold() != expected_md5.casefold():
        raise PilotControlError("pilot_provider_md5_mismatch")
    if b3.hexdigest().casefold() != expected_blake3.casefold():
        raise PilotControlError("pilot_provider_blake3_mismatch")
    return {"size_bytes": size, "sha256": sha256.hexdigest(), "md5": md5.hexdigest(), "blake3": b3.hexdigest()}


def fetch_catalog(source: Mapping[str, Any], *, opener: Any | None = None) -> dict[str, Any]:
    url = exact_catalog_url(source)
    request = urllib.request.Request(url, headers={"User-Agent": "nepal-optical-pilot-001/1.0"})
    try:
        with (opener or urllib.request.build_opener(NoRedirectHandler())).open(request, timeout=60) as response:
            if response.status != 200 or response.geturl() != url:
                raise PilotControlError("pilot_catalog_response_identity_drift")
            raw = response.read(2 * 1024 * 1024 + 1)
            if len(raw) > 2 * 1024 * 1024:
                raise PilotControlError("pilot_catalog_response_too_large")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise PilotControlError("pilot_catalog_unavailable") from exc
    try:
        product = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise PilotControlError("pilot_catalog_response_invalid") from exc
    validate_catalog_product(source, product)
    validate_catalog_footprint(source, product)
    return {"product": product, "response_sha256": hashlib.sha256(raw).hexdigest(), "url": url}


def one_transfer(
    source: Mapping[str, Any],
    secret: str,
    *,
    event_root: Path,
    progress: Callable[[str, int], None] | None = None,
    opener: Any | None = None,
) -> dict[str, Any]:
    """Create one request attempt; a retry is a distinct later invocation."""
    require_execution_release(source["source_id"])
    if not secret or any(char.isspace() for char in secret) or len(secret.encode("utf-8")) > 16_384:
        raise PilotControlError("pilot_secret_invalid")
    if event_root.resolve(strict=False).is_relative_to(ROOT.resolve(strict=True)):
        raise PilotControlError("pilot_attempt_inside_git_workspace")
    if event_root != DATA_ROOT / "derived/m2-optical-pair-pilot-001":
        raise PilotControlError("pilot_attempt_root_drift")
    if not DATA_ROOT.is_dir() or is_reparse_point(DATA_ROOT):
        raise PilotControlError("pilot_external_custody_root_unsafe")
    for ancestor in (DATA_ROOT / "derived", event_root):
        if ancestor.exists() and is_reparse_point(ancestor):
            raise PilotControlError("pilot_external_custody_reparse_point")
    require_safe_child(DATA_ROOT, event_root)
    source_id = source["source_id"]
    attempts_root = event_root / "transport" / source_id.casefold()
    prior = previous_attempts(attempts_root)
    if not may_make_second_request(prior[-1].get("status") if prior else None, len(prior)):
        raise PilotControlError("pilot_request_limit_or_retry_condition")
    if source_id == "M2-OPT-002":
        before = previous_attempts(event_root / "transport/m2-opt-001")
        if len(before) != 1 and len(before) != 2:
            raise PilotControlError("pilot_before_source_not_completed")
        if before[-1].get("status") != "promoted_verified":
            raise PilotControlError("pilot_before_source_not_completed")
    catalog = fetch_catalog(source, opener=opener)
    free = shutil.disk_usage(DATA_ROOT).free
    if free < 12 * 1024**3:
        raise PilotControlError("pilot_free_space_below_minimum")
    destination = event_root / "custody" / source_id.casefold() / (source["exact_product_name"] + ".zip")
    require_safe_child(event_root, destination)
    if destination.exists():
        raise PilotControlError("pilot_destination_collision")
    attempt_id = f"{source_id.casefold()}-{now_utc().replace(':', '').replace('-', '')}-{uuid.uuid4().hex[:8]}"
    attempt_root = attempts_root / attempt_id
    attempt_root.mkdir(parents=True, exist_ok=False)
    started = {
        "schema_version": "1.0",
        "attempt_id": attempt_id,
        "status": "request_started",
        "source_id": source_id,
        "provider_product_id": source["provider_product_id"],
        "started_at_utc": now_utc(),
        "catalog_response_sha256": catalog["response_sha256"],
        "byte_zero_request": True,
        "resume": False,
        "credential_value_recorded": False,
    }
    write_new_json(attempt_root / "started.json", started)
    stage = attempt_root / "payload.part"
    url = exact_download_url(source)
    try:
        request = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {secret}",
            "User-Agent": "nepal-optical-pilot-001/1.0",
            "Accept-Encoding": "identity",
        })
        with (opener or urllib.request.build_opener(NoRedirectHandler())).open(request, timeout=120) as response:
            if response.status != 200 or response.geturl() != url:
                raise PilotControlError("pilot_download_response_identity_drift")
            declared = response.headers.get("Content-Length")
            if declared is None or int(declared) != source["content_length_bytes"]:
                raise PilotControlError("pilot_download_content_length_drift")
            if "text/html" in (response.headers.get("Content-Type") or "").casefold():
                raise PilotControlError("pilot_unexpected_html_payload")
            transferred = hash_stream_to_new_file(
                response, stage,
                expected_size=source["content_length_bytes"],
                expected_md5=source["provider_md5"],
                expected_blake3=source["provider_blake3"],
                progress=(lambda count: progress(source_id, count)) if progress else None,
            )
        container = verify_zip(stage, source["exact_product_name"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        promoted = promote_atomic_no_replace(stage, destination)
        if promoted["sha256"] != transferred["sha256"]:
            raise PilotControlError("pilot_promotion_identity_drift")
        terminal = {
            "schema_version": "1.0", "attempt_id": attempt_id, "source_id": source_id,
            "status": "promoted_verified", "completed_at_utc": now_utc(),
            "catalog_response_sha256": catalog["response_sha256"],
            "archive_size_bytes": transferred["size_bytes"], "archive_sha256": transferred["sha256"],
            "provider_md5_verified": True, "provider_blake3_verified": True,
            "container": container, "destination": str(destination),
            "credential_value_recorded": False, "automatic_retry": False,
        }
    except BaseException as exc:
        terminal = {
            "schema_version": "1.0", "attempt_id": attempt_id, "source_id": source_id,
            "status": classify_terminal_exception(exc), "completed_at_utc": now_utc(),
            "payload_bytes_retained": stage.stat().st_size if stage.exists() else 0,
            "destination_exists": destination.exists(),
            "exception_text_recorded": False, "credential_value_recorded": False,
            "automatic_retry": False,
        }
    write_new_json(attempt_root / "terminal.json", terminal)
    return terminal
