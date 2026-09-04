#!/usr/bin/env python3
"""Portable byte, checksum, path, and XML controls for S1D orbit intake."""

from __future__ import annotations

import hashlib
import math
import os
import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, BinaryIO

try:
    import blake3 as _blake3_module
except ImportError:  # pragma: no cover - exercised through the explicit guard
    _blake3_module = None


REQUIRED_BLAKE3_VERSION = "1.0.9"


class OrbitControlError(RuntimeError):
    """A fail-closed orbit control rejected the operation."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def require_blake3() -> Any:
    if _blake3_module is None:
        raise OrbitControlError("blake3_dependency_missing")
    if getattr(_blake3_module, "__version__", None) != REQUIRED_BLAKE3_VERSION:
        raise OrbitControlError("blake3_dependency_version_drift")
    return _blake3_module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def md5_file(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def blake3_file(path: Path) -> str:
    digest = require_blake3().blake3()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def provider_checksum_map(values: list[dict[str, Any]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in values:
        algorithm = str(item.get("algorithm", item.get("Algorithm", ""))).upper()
        value = str(item.get("value", item.get("Value", ""))).lower()
        if not algorithm or not value or algorithm in result:
            raise OrbitControlError("provider_checksum_set_invalid")
        result[algorithm] = value
    if set(result) != {"BLAKE3", "MD5"}:
        raise OrbitControlError("provider_checksum_set_incomplete")
    return result


def stream_to_exclusive_staging(
    source: BinaryIO,
    staging_path: Path,
    *,
    expected_size: int,
    expected_md5: str,
    expected_blake3: str,
    chunk_size: int = 1024 * 1024,
) -> dict[str, Any]:
    if staging_path.exists():
        raise OrbitControlError("staging_collision")
    blake3_module = require_blake3()
    sha256 = hashlib.sha256()
    md5 = hashlib.md5(usedforsecurity=False)
    blake3 = blake3_module.blake3()
    size = 0
    with staging_path.open("xb") as handle:
        while True:
            block = source.read(chunk_size)
            if not block:
                break
            handle.write(block)
            sha256.update(block)
            md5.update(block)
            blake3.update(block)
            size += len(block)
        handle.flush()
        os.fsync(handle.fileno())
    result = {
        "size_bytes": size,
        "sha256": sha256.hexdigest(),
        "md5": md5.hexdigest(),
        "blake3": blake3.hexdigest(),
    }
    if size != expected_size:
        raise OrbitControlError("transferred_size_mismatch")
    if result["md5"] != expected_md5.lower():
        raise OrbitControlError("provider_md5_mismatch")
    if result["blake3"] != expected_blake3.lower():
        raise OrbitControlError("provider_blake3_mismatch")
    return result


def parse_utc(value: str) -> datetime:
    text = value.strip()
    if text.upper().startswith("UTC="):
        text = text[4:]
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def descendants(root: ET.Element, name: str) -> list[ET.Element]:
    return [element for element in root.iter() if local_name(element.tag) == name]


def exactly_one_text(root: ET.Element, name: str) -> str:
    matches = descendants(root, name)
    if len(matches) != 1 or matches[0].text is None or not matches[0].text.strip():
        raise OrbitControlError(f"xml_{name.lower()}_missing_or_ambiguous")
    return matches[0].text.strip()


def normalized_mission(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def parse_finite(element: ET.Element, *, expected_unit: str) -> float:
    if element.text is None:
        raise OrbitControlError("osv_numeric_value_missing")
    unit = (element.attrib.get("unit") or "").strip().casefold().replace(" ", "")
    if unit != expected_unit:
        raise OrbitControlError("osv_unit_mismatch")
    try:
        value = float(element.text.strip())
    except ValueError as exc:
        raise OrbitControlError("osv_numeric_value_invalid") from exc
    if not math.isfinite(value):
        raise OrbitControlError("osv_numeric_value_nonfinite")
    return value


def inspect_eof(
    path: Path,
    requirement: dict[str, Any],
    *,
    logical_name: str | None = None,
) -> dict[str, Any]:
    expected_size = int(requirement["expected_size_bytes"])
    if not path.is_file():
        raise OrbitControlError("orbit_file_missing")
    if (logical_name or path.name) != requirement["exact_product_name"]:
        raise OrbitControlError("orbit_filename_mismatch")
    if path.stat().st_size != expected_size:
        raise OrbitControlError("orbit_size_mismatch")
    payload = path.read_bytes()
    upper = payload.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise OrbitControlError("unsafe_xml_declaration")
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise OrbitControlError("orbit_xml_parse_failure") from exc
    if local_name(root.tag) != "Earth_Explorer_File":
        raise OrbitControlError("orbit_xml_root_mismatch")

    expected_name = requirement["exact_product_name"]
    header_name = exactly_one_text(root, "File_Name")
    if header_name not in {expected_name, Path(expected_name).stem}:
        raise OrbitControlError("orbit_header_filename_mismatch")
    if exactly_one_text(root, "File_Type") != "AUX_RESORB":
        raise OrbitControlError("orbit_file_type_mismatch")
    if normalized_mission(exactly_one_text(root, "Mission")) not in {"s1d", "sentinel1d"}:
        raise OrbitControlError("orbit_mission_mismatch")

    validity_start = parse_utc(exactly_one_text(root, "Validity_Start"))
    validity_stop = parse_utc(exactly_one_text(root, "Validity_Stop"))
    expected_start = parse_utc(requirement["expected_validity_start_utc"])
    expected_stop = parse_utc(requirement["expected_validity_end_utc"])
    if validity_start != expected_start or validity_stop != expected_stop or validity_start >= validity_stop:
        raise OrbitControlError("orbit_validity_mismatch")

    lists = descendants(root, "List_of_OSVs")
    if len(lists) != 1:
        raise OrbitControlError("osv_list_missing_or_ambiguous")
    osv_elements = [element for element in list(lists[0]) if local_name(element.tag) == "OSV"]
    try:
        declared_count = int(lists[0].attrib.get("count", ""))
    except ValueError as exc:
        raise OrbitControlError("osv_declared_count_invalid") from exc
    if declared_count <= 0 or declared_count != len(osv_elements):
        raise OrbitControlError("osv_count_mismatch")

    osv_times: list[datetime] = []
    for osv in osv_elements:
        osv_times.append(parse_utc(exactly_one_text(osv, "UTC")))
        for name in ("X", "Y", "Z"):
            matches = descendants(osv, name)
            if len(matches) != 1:
                raise OrbitControlError("osv_position_missing_or_ambiguous")
            parse_finite(matches[0], expected_unit="m")
        for name in ("VX", "VY", "VZ"):
            matches = descendants(osv, name)
            if len(matches) != 1:
                raise OrbitControlError("osv_velocity_missing_or_ambiguous")
            parse_finite(matches[0], expected_unit="m/s")
    if any(current <= previous for previous, current in zip(osv_times, osv_times[1:])):
        raise OrbitControlError("osv_time_order_or_uniqueness_failure")
    if osv_times[0] > validity_start or osv_times[-1] < validity_stop:
        raise OrbitControlError("osv_times_do_not_span_validity")

    scene_start = parse_utc(requirement["scene_start_utc"])
    scene_end = parse_utc(requirement["scene_end_utc"])
    before_margin = int((scene_start - validity_start).total_seconds())
    after_margin = int((validity_stop - scene_end).total_seconds())
    minimum_margin = min(before_margin, after_margin)
    required_margin = int(requirement["minimum_required_scene_margin_seconds"])
    if scene_start > scene_end or before_margin < 0 or after_margin < 0 or minimum_margin < required_margin:
        raise OrbitControlError("scene_validity_margin_failure")

    checksums = provider_checksum_map(requirement["expected_provider_checksums"])
    observed = {
        "size_bytes": expected_size,
        "sha256": sha256_file(path),
        "md5": md5_file(path),
        "blake3": blake3_file(path),
    }
    if observed["md5"] != checksums["MD5"]:
        raise OrbitControlError("provider_md5_mismatch")
    if observed["blake3"] != checksums["BLAKE3"]:
        raise OrbitControlError("provider_blake3_mismatch")
    return {
        "status": "pass_orbit_input_only",
        "observed": observed,
        "xml": {
            "root": local_name(root.tag),
            "header_file_name": header_name,
            "mission": exactly_one_text(root, "Mission"),
            "file_type": "AUX_RESORB",
            "validity_start_utc": validity_start.isoformat().replace("+00:00", "Z"),
            "validity_end_utc": validity_stop.isoformat().replace("+00:00", "Z"),
            "osv_declared_count": declared_count,
            "osv_observed_count": len(osv_elements),
            "first_osv_utc": osv_times[0].isoformat().replace("+00:00", "Z"),
            "last_osv_utc": osv_times[-1].isoformat().replace("+00:00", "Z"),
            "ordered_unique_finite_osvs": True,
            "position_unit": "m",
            "velocity_unit": "m/s",
        },
        "scene_binding": {
            "sentinel_source_ids": requirement["sentinel_source_ids"],
            "scene_start_utc": scene_start.isoformat().replace("+00:00", "Z"),
            "scene_end_utc": scene_end.isoformat().replace("+00:00", "Z"),
            "margin_before_seconds": before_margin,
            "margin_after_seconds": after_margin,
            "minimum_margin_seconds": minimum_margin,
            "minimum_required_margin_seconds": required_margin,
        },
    }
