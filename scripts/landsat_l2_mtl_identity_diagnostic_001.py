#!/usr/bin/env python3
"""One-shot, metadata-only diagnosis of the frozen August 10 Landsat TAR.

The real entry point requires a separate, post-public-CI no-content gate. It
never extracts members, changes source custody, or reads TIFF member payloads.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tarfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from landsat_l2_bundle_integrity import ID_PATTERN, SCENE_PATTERN, _safe_member_path


PRODUCT = "LC09_L2SP_141040_20260810_20260811_02_T1"
SCENE = "LC91410402026222LGN00"
SOURCE_REL = Path(".intake-staging/nepal-m2-landsat9-local-download-recovery-001/attempt-bytes/landsat9-before-20260810-recovery-001") / (PRODUCT + ".tar.part")
ATTEMPT_REL = Path(".intake-staging/nepal-m2-landsat9-mtl-identity-diagnostic-001/attempt-events/landsat9-mtl-identity-diagnostic-001-real-001")
SOURCE_BYTES = 1126565376
SOURCE_SHA256 = "9f9a5a63e7abd78f889c9f5229a80f62008b6c31e88b212bf8af01950ca9b255"
MAX_MTL = 2 * 1024 * 1024
MAX_MEMBERS = 128
REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


class DiagnosticStop(Exception):
    """Fixed, public-safe stop code only."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def safe_regular(path: Path) -> os.stat_result:
    for node in (path, *path.parents):
        if node.is_symlink():
            raise DiagnosticStop("source_reparse_or_symlink")
        try:
            info = node.lstat()
        except OSError:
            raise DiagnosticStop("source_path_unavailable") from None
        if getattr(info, "st_file_attributes", 0) & REPARSE_POINT:
            raise DiagnosticStop("source_reparse_or_symlink")
    if not stat.S_ISREG(path.stat().st_mode):
        raise DiagnosticStop("source_not_regular")
    return path.stat()


def _fingerprint(info: os.stat_result) -> tuple[int, int, int]:
    return info.st_size, info.st_mtime_ns, info.st_ino


def _hash_exact(path: Path, expected_size: int, expected_sha: str) -> os.stat_result:
    initial = safe_regular(path)
    if initial.st_size != expected_size:
        raise DiagnosticStop("source_size_mismatch")
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                size += len(block)
                digest.update(block)
    except OSError:
        raise DiagnosticStop("source_hash_read_failed") from None
    if _fingerprint(initial) != _fingerprint(safe_regular(path)):
        raise DiagnosticStop("source_changed_during_hash")
    if size != expected_size or digest.hexdigest() != expected_sha:
        raise DiagnosticStop("source_digest_mismatch")
    return initial


def _text_values(raw: bytes, key: str) -> list[str]:
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeError:
        raise DiagnosticStop("mtl_text_encoding_invalid") from None
    values = []
    for line in content.splitlines():
        if "=" not in line:
            continue
        candidate, value = line.split("=", 1)
        if candidate.strip() == key:
            values.append(value.strip().strip('"').strip("'"))
    return values


def _xml_values(raw: bytes, key: str) -> list[str]:
    if re.search(rb"<!\s*(DOCTYPE|ENTITY)\b", raw, re.I):
        raise DiagnosticStop("mtl_xml_unsafe_declaration")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        raise DiagnosticStop("mtl_xml_invalid") from None
    return [(node.text or "").strip() for node in root.iter() if node.tag.rsplit("}", 1)[-1] == key]


def _classify(values: list[str], expected: str, pattern: re.Pattern[str]) -> dict:
    valid = [value for value in values if pattern.fullmatch(value)]
    return {
        "presence_count": len(values),
        "all_syntactically_valid": len(valid) == len(values),
        "exact_expected_match": len(values) == 1 and values[0] == expected,
        "allowlisted_values": valid,
    }


def inspect_metadata(path: Path, expected_size: int, expected_sha: str,
                     product: str = PRODUCT, scene: str = SCENE) -> dict:
    """Inspect a fixed source after full digest, reading only two MTL payloads."""
    if not ID_PATTERN.fullmatch(product) or not SCENE_PATTERN.fullmatch(scene):
        raise DiagnosticStop("expected_identity_invalid")
    initial = _hash_exact(path, expected_size, expected_sha)
    targets = {product + "_MTL.txt", product + "_MTL.xml"}
    metadata: dict[str, bytes] = {}
    seen: set[str] = set()
    count = 0
    try:
        with tarfile.open(path, mode="r:") as archive:
            for member in archive:
                count += 1
                if count > MAX_MEMBERS:
                    raise DiagnosticStop("too_many_archive_members")
                try:
                    member_path = _safe_member_path(member.name, product)
                except ValueError:
                    raise DiagnosticStop("unsafe_archive_member_path") from None
                folded = member_path.as_posix().casefold()
                if folded in seen:
                    raise DiagnosticStop("duplicate_archive_member")
                seen.add(folded)
                if member.isdir():
                    if member_path.as_posix() != product:
                        raise DiagnosticStop("unexpected_archive_directory")
                    continue
                if member.type not in (tarfile.REGTYPE, tarfile.AREGTYPE):
                    raise DiagnosticStop("unsafe_archive_member_type")
                if not member_path.name.startswith(product + "_"):
                    raise DiagnosticStop("archive_member_identity_mismatch")
                if member_path.name not in targets:
                    continue  # Never call extractfile on TIFF or other payloads.
                if member_path.name in metadata:
                    raise DiagnosticStop("duplicate_mtl_member")
                if member.size <= 0 or member.size > MAX_MTL:
                    raise DiagnosticStop("mtl_member_size_invalid")
                stream = archive.extractfile(member)
                if stream is None:
                    raise DiagnosticStop("mtl_member_unreadable")
                with stream:
                    raw = stream.read(MAX_MTL + 1)
                if len(raw) != member.size:
                    raise DiagnosticStop("mtl_member_length_mismatch")
                metadata[member_path.name] = raw
    except (tarfile.TarError, EOFError, OSError):
        raise DiagnosticStop("tar_structure_invalid") from None
    if _fingerprint(initial) != _fingerprint(safe_regular(path)):
        raise DiagnosticStop("source_changed_during_mtl_read")
    if set(metadata) != targets:
        raise DiagnosticStop("mtl_member_missing")
    result = {"status": "classified_metadata_only", "archive_bytes": expected_size,
              "archive_sha256": expected_sha, "tar_member_count": count, "identity": {}}
    for label, raw, parser in (("text", metadata[product + "_MTL.txt"], _text_values),
                               ("xml", metadata[product + "_MTL.xml"], _xml_values)):
        result["identity"][label] = {}
        for key, expected, pattern in (("LANDSAT_PRODUCT_ID", product, ID_PATTERN),
                                       ("LANDSAT_SCENE_ID", scene, SCENE_PATTERN)):
            result["identity"][label][key] = _classify(parser(raw, key), expected, pattern)
    if not all(field["exact_expected_match"] for group in result["identity"].values() for field in group.values()):
        result["status"] = "identity_discrepancy_classified_source_unaccepted"
    return result


def _append_json(path: Path, value: dict) -> None:
    payload = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    with os.fdopen(os.open(path, flags, 0o600), "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def run_once(data_root: Path, preflight: Path) -> dict:
    """Consume the sole diagnostic identity; failures are terminal, never retried."""
    # The preflight is a local no-content gate produced only after exact public CI.
    gate = json.loads(preflight.read_text(encoding="utf-8"))
    if gate.get("status") != "pass" or gate.get("diagnostic_id") != ATTEMPT_REL.name or not gate.get("public_ci_success"):
        raise DiagnosticStop("final_preflight_gate_invalid")
    root = data_root / ATTEMPT_REL
    root.mkdir(parents=True, exist_ok=False)
    _append_json(root / "reservation.json", {
        "diagnostic_id": ATTEMPT_REL.name, "reserved_at_utc": utc_now(),
        "source_role": "frozen_non_git_staging", "expected_bytes": SOURCE_BYTES,
        "expected_sha256": SOURCE_SHA256,
        "read_budget": 1,
    })
    terminal: dict
    try:
        result = inspect_metadata(data_root / SOURCE_REL, SOURCE_BYTES, SOURCE_SHA256)
        terminal = {"diagnostic_id": ATTEMPT_REL.name, "completed_at_utc": utc_now(), **result,
                    "source_promoted": False, "pixels_read": False, "after_request_started": False}
    except BaseException as error:
        code = str(error) if isinstance(error, DiagnosticStop) else "unexpected_diagnostic_error"
        terminal = {"diagnostic_id": ATTEMPT_REL.name, "completed_at_utc": utc_now(),
                    "status": "terminal_stop", "code": code,
                    "source_promoted": False, "pixels_read": False, "after_request_started": False}
    finally:
        # A failed terminal write cannot suppress the independent cleanup record.
        try:
            _append_json(root / "terminal.json", terminal)
        finally:
            _append_json(root / "cleanup.json", {"diagnostic_id": ATTEMPT_REL.name,
                "completed_at_utc": utc_now(), "source_mutation_performed": False,
                "extracted_files_created": False, "automatic_retry": False})
    return terminal


if __name__ == "__main__":
    data = Path(os.environ.get("NEPAL_DATA_ROOT", "C:/Projects/Active/nepal-2026-before-after-map-data"))
    gate_path = Path(__file__).resolve().parents[1] / "records/readiness/m2-landsat9-mtl-identity-diagnostic-001-final-preflight-local.json"
    try:
        outcome = run_once(data, gate_path)
    except (DiagnosticStop, FileNotFoundError, FileExistsError, OSError, ValueError):
        outcome = {"status": "stopped_before_or_during_reservation"}
    print(json.dumps({"status": outcome["status"], "diagnostic_id": ATTEMPT_REL.name}, sort_keys=True))
