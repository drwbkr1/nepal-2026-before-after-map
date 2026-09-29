#!/usr/bin/env python3
"""Inspect a Landsat 8/9 C2L2 EarthExplorer TAR without extracting pixels.

This is a container and metadata identity check, not source authentication,
TIFF validation, pixel QA, map admission, or permission to acquire data.
The EarthExplorer full product bundle is documented by USGS as a TAR product.
"""

from __future__ import annotations

import hashlib
import re
import tarfile
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath


REQUIRED_SUFFIXES = (
    "_MTL.txt",
    "_MTL.xml",
    "_QA_PIXEL.TIF",
    "_QA_RADSAT.TIF",
    "_SR_QA_AEROSOL.TIF",
    "_SR_B3.TIF",
    "_SR_B4.TIF",
    "_SR_B5.TIF",
    "_SR_B6.TIF",
    "_SR_B7.TIF",
)
MAX_MEMBERS = 128
MAX_UNCOMPRESSED_BYTES = 32 * 1024**3
MAX_METADATA_BYTES = 2 * 1024**2
CHUNK_BYTES = 1024**2
ID_PATTERN = re.compile(r"^LC0[89]_L2S[PR]_[0-9]{6}_[0-9]{8}_[0-9]{8}_02_T[12]$")
SCENE_PATTERN = re.compile(r"^LC[89][0-9A-Z]{18}$")


class BundleIntegrityError(ValueError):
    """A safe, non-secret reason to reject a bundle before promotion."""


def _sha256_file(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(CHUNK_BYTES), b""):
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


def _safe_member_path(name: str, product_id: str) -> PurePosixPath:
    if not name or "\\" in name or ":" in name or name.startswith("/"):
        raise BundleIntegrityError("unsafe_archive_member_path")
    parts = name.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise BundleIntegrityError("unsafe_archive_member_path")
    if len(parts) > 2 or (len(parts) == 2 and parts[0] != product_id):
        raise BundleIntegrityError("unexpected_archive_member_root")
    return PurePosixPath(name)


def _metadata_values(text: str, key: str) -> set[str]:
    values: set[str] = set()
    for line in text.splitlines():
        if "=" not in line:
            continue
        candidate, value = line.split("=", 1)
        if candidate.strip() != key:
            continue
        values.add(value.strip().strip('"').strip("'"))
    return values


def _verify_text_metadata(raw: bytes, product_id: str, scene_id: str) -> None:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise BundleIntegrityError("mtl_text_encoding_invalid") from error
    for key, expected in (("LANDSAT_PRODUCT_ID", product_id), ("LANDSAT_SCENE_ID", scene_id)):
        if _metadata_values(text, key) != {expected}:
            raise BundleIntegrityError("mtl_text_identity_mismatch")


def _verify_xml_metadata(raw: bytes, product_id: str, scene_id: str) -> None:
    if re.search(rb"<!\s*(DOCTYPE|ENTITY)\b", raw, re.IGNORECASE):
        raise BundleIntegrityError("mtl_xml_unsafe_declaration")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as error:
        raise BundleIntegrityError("mtl_xml_invalid") from error
    for key, expected in (("LANDSAT_PRODUCT_ID", product_id), ("LANDSAT_SCENE_ID", scene_id)):
        values = {
            (node.text or "").strip()
            for node in root.iter()
            if node.tag.rsplit("}", 1)[-1] == key
        }
        if values != {expected}:
            raise BundleIntegrityError("mtl_xml_identity_mismatch")


def inspect_bundle(path: Path, product_id: str, scene_id: str) -> dict:
    """Return local TAR and member hashes only after exact metadata identity passes.

    The caller must separately establish authority, source provenance, browser
    transfer completion, and no-replace custody before any real invocation.
    """
    if not ID_PATTERN.fullmatch(product_id) or not SCENE_PATTERN.fullmatch(scene_id):
        raise BundleIntegrityError("expected_identity_invalid")
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not path.name.lower().endswith((".tar", ".tar.part")):
        raise BundleIntegrityError("bundle_path_or_format_invalid")
    initial_stat = path.stat()
    size, sha256 = _sha256_file(path)
    if size < 2048 or size % 512 != 0:
        raise BundleIntegrityError("tar_length_invalid")
    with path.open("rb") as source:
        source.seek(-1024, 2)
        if source.read(1024) != b"\0" * 1024:
            raise BundleIntegrityError("tar_end_marker_missing")

    members: list[dict] = []
    seen: set[str] = set()
    seen_basenames: set[str] = set()
    required = {product_id + suffix for suffix in REQUIRED_SUFFIXES}
    metadata: dict[str, bytes] = {}
    total_uncompressed = 0
    last_member_end = 0
    try:
        with tarfile.open(path, mode="r:") as archive:
            for member in archive:
                if len(members) >= MAX_MEMBERS:
                    raise BundleIntegrityError("too_many_archive_members")
                member_path = _safe_member_path(member.name, product_id)
                if member.size < 0:
                    raise BundleIntegrityError("archive_member_length_invalid")
                last_member_end = max(
                    last_member_end,
                    member.offset_data + ((member.size + 511) // 512) * 512,
                )
                folded = member_path.as_posix().casefold()
                if folded in seen:
                    raise BundleIntegrityError("duplicate_archive_member")
                seen.add(folded)
                if member.isdir():
                    if member_path.as_posix() != product_id:
                        raise BundleIntegrityError("unexpected_archive_directory")
                    continue
                if member.type not in (tarfile.REGTYPE, tarfile.AREGTYPE):
                    raise BundleIntegrityError("unsafe_archive_member_type")
                basename = member_path.name.casefold()
                if basename in seen_basenames:
                    raise BundleIntegrityError("duplicate_archive_basename")
                seen_basenames.add(basename)
                if not member_path.name.startswith(product_id + "_"):
                    raise BundleIntegrityError("archive_member_identity_mismatch")
                if member_path.name in required and member.size == 0:
                    raise BundleIntegrityError("required_archive_member_empty")
                total_uncompressed += member.size
                if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
                    raise BundleIntegrityError("archive_uncompressed_limit_exceeded")
                if member_path.name in (product_id + "_MTL.txt", product_id + "_MTL.xml"):
                    if member.size > MAX_METADATA_BYTES:
                        raise BundleIntegrityError("mtl_metadata_too_large")
                stream = archive.extractfile(member)
                if stream is None:
                    raise BundleIntegrityError("archive_member_unreadable")
                digest = hashlib.sha256()
                read_bytes = 0
                capture = bytearray() if member_path.name in required and member_path.name.endswith(("_MTL.txt", "_MTL.xml")) else None
                with stream:
                    for chunk in iter(lambda: stream.read(CHUNK_BYTES), b""):
                        read_bytes += len(chunk)
                        digest.update(chunk)
                        if capture is not None:
                            capture.extend(chunk)
                if read_bytes != member.size:
                    raise BundleIntegrityError("archive_member_length_mismatch")
                if capture is not None:
                    metadata[member_path.name] = bytes(capture)
                members.append({
                    "name": member_path.as_posix(),
                    "size_bytes": read_bytes,
                    "sha256": digest.hexdigest(),
                })
    except (tarfile.TarError, EOFError, OSError) as error:
        raise BundleIntegrityError("tar_structure_invalid") from error

    # tarfile stops at its first end marker. Reject hidden nonzero payload after
    # that marker rather than treating an appended archive as verified content.
    with path.open("rb") as source:
        source.seek(last_member_end)
        tail_bytes = 0
        for chunk in iter(lambda: source.read(CHUNK_BYTES), b""):
            tail_bytes += len(chunk)
            if any(chunk):
                raise BundleIntegrityError("tar_trailing_payload_invalid")
    if tail_bytes < 1024:
        raise BundleIntegrityError("tar_end_marker_missing")

    final_size, final_sha256 = _sha256_file(path)
    final_stat = path.stat()
    if (
        (final_size, final_sha256) != (size, sha256)
        or (final_stat.st_size, final_stat.st_mtime_ns) != (initial_stat.st_size, initial_stat.st_mtime_ns)
    ):
        raise BundleIntegrityError("bundle_changed_during_inspection")

    names = {PurePosixPath(member["name"]).name for member in members}
    if not required.issubset(names):
        raise BundleIntegrityError("required_archive_member_missing")
    _verify_text_metadata(metadata[product_id + "_MTL.txt"], product_id, scene_id)
    _verify_xml_metadata(metadata[product_id + "_MTL.xml"], product_id, scene_id)
    return {
        "status": "pass_container_and_mtl_identity_only",
        "product_id": product_id,
        "scene_id": scene_id,
        "archive_size_bytes": size,
        "archive_sha256": sha256,
        "member_count": len(members),
        "members": members,
        "limitations": [
            "No upstream checksum was compared.",
            "No TIFF header, CRS, pixel, AOI, registration, or change check was performed.",
        ],
    }
