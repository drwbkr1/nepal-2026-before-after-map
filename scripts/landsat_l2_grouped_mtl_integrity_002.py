#!/usr/bin/env python3
"""Versioned, group-aware Landsat 8/9 C2L2 TAR verifier.

This is a container and metadata identity check, not source authentication,
TIFF validation, pixel QA, map admission, or permission to acquire data.
The frozen global-value verifier remains in landsat_l2_bundle_integrity.py.
USGS LSDS-1328 v7 places two Level-2 product IDs and one Level-1 lineage ID
in distinct ODL groups / XML parent elements.
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
ODL_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
ROOT = "LANDSAT_METADATA_FILE"
L2_GROUPS = ("PRODUCT_CONTENTS", "LEVEL2_PROCESSING_RECORD")
L1_GROUP = "LEVEL1_PROCESSING_RECORD"
IDENTITY_KEYS = {"LANDSAT_PRODUCT_ID", "LANDSAT_SCENE_ID"}


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


def _odl_fields(raw: bytes) -> tuple[dict[tuple[str, ...], list[str]], dict[tuple[str, ...], int]]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise BundleIntegrityError("mtl_text_encoding_invalid") from None
    fields: dict[tuple[str, ...], list[str]] = {}
    groups: dict[tuple[str, ...], int] = {}
    stack: list[str] = []
    ended = False
    root_closed = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if ended or (root_closed and stripped != "END"):
            raise BundleIntegrityError("mtl_odl_structure_invalid")
        if stripped == "END":
            if stack or not root_closed:
                raise BundleIntegrityError("mtl_odl_structure_invalid")
            ended = True
            continue
        if "=" not in stripped:
            raise BundleIntegrityError("mtl_odl_structure_invalid")
        key, value = (part.strip() for part in stripped.split("=", 1))
        if not ODL_NAME.fullmatch(key):
            raise BundleIntegrityError("mtl_odl_structure_invalid")
        if key in {"OBJECT", "END_OBJECT"}:
            raise BundleIntegrityError("mtl_odl_structure_invalid")
        if key == "GROUP":
            if (not ODL_NAME.fullmatch(value) or (not stack and value != ROOT)
                    or (stack and value == ROOT)):
                raise BundleIntegrityError("mtl_odl_structure_invalid")
            stack.append(value)
            path = tuple(stack)
            groups[path] = groups.get(path, 0) + 1
            continue
        if key == "END_GROUP":
            if not stack or value != stack[-1]:
                raise BundleIntegrityError("mtl_odl_structure_invalid")
            stack.pop()
            if not stack:
                root_closed = True
            continue
        if not stack or not value:
            raise BundleIntegrityError("mtl_odl_structure_invalid")
        if key in IDENTITY_KEYS or key == "PROCESSING_LEVEL":
            # ODL strings are quoted. Do not strip arbitrary unmatched quotes.
            if value.startswith('"') != value.endswith('"'):
                raise BundleIntegrityError("mtl_odl_identity_syntax_invalid")
            normalized = value[1:-1] if value.startswith('"') else value
            fields.setdefault((*stack, key), []).append(normalized)
    if not ended or stack or groups.get((ROOT,)) != 1:
        raise BundleIntegrityError("mtl_odl_structure_invalid")
    return fields, groups


def _xml_fields(raw: bytes) -> tuple[dict[tuple[str, ...], list[str]], dict[tuple[str, ...], int]]:
    if re.search(rb"<!\s*(DOCTYPE|ENTITY)\b", raw, re.IGNORECASE):
        raise BundleIntegrityError("mtl_xml_unsafe_declaration")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        raise BundleIntegrityError("mtl_xml_invalid") from None
    if root.tag != ROOT:
        raise BundleIntegrityError("mtl_xml_root_invalid")
    fields: dict[tuple[str, ...], list[str]] = {}
    groups: dict[tuple[str, ...], int] = {}

    def visit(node: ET.Element, parents: tuple[str, ...]) -> None:
        if not isinstance(node.tag, str) or not ODL_NAME.fullmatch(node.tag):
            raise BundleIntegrityError("mtl_xml_structure_invalid")
        path = (*parents, node.tag)
        if len(path) <= 2:
            groups[path] = groups.get(path, 0) + 1
        if node.tag in IDENTITY_KEYS or node.tag == "PROCESSING_LEVEL":
            if list(node):
                raise BundleIntegrityError("mtl_xml_identity_syntax_invalid")
            fields.setdefault(path, []).append((node.text or "").strip())
        for child in node:
            visit(child, path)

    visit(root, ())
    return fields, groups


def _verify_grouped_metadata(text_raw: bytes, xml_raw: bytes,
                             product_id: str, scene_id: str) -> None:
    text_fields, text_groups = _odl_fields(text_raw)
    xml_fields, xml_groups = _xml_fields(xml_raw)
    expected_groups = {ROOT: 1, **{name: 1 for name in (*L2_GROUPS, L1_GROUP)}}
    for groups in (text_groups, xml_groups):
        if any(groups.get((ROOT, name)) != count for name, count in expected_groups.items() if name != ROOT):
            raise BundleIntegrityError("mtl_required_group_missing_or_duplicate")
        if groups.get((ROOT,)) != 1:
            raise BundleIntegrityError("mtl_root_group_invalid")
    required: dict[tuple[str, ...], str] = {
        (ROOT, name, "LANDSAT_PRODUCT_ID"): product_id for name in L2_GROUPS
    }
    required[(ROOT, L1_GROUP, "LANDSAT_SCENE_ID")] = scene_id
    parts = product_id.split("_")
    level1_pattern = re.compile(
        rf"^{re.escape(parts[0])}_L1(?:TP|GT)_{re.escape(parts[2])}_"
        rf"{re.escape(parts[3])}_[0-9]{{8}}_{re.escape(parts[5])}_{re.escape(parts[6])}$"
    )
    level1_path = (ROOT, L1_GROUP, "LANDSAT_PRODUCT_ID")
    required_identity_paths = set(required) | {level1_path}
    for fields in (text_fields, xml_fields):
        present_identity_paths = {path for path in fields if path[-1] in IDENTITY_KEYS}
        if present_identity_paths != required_identity_paths:
            raise BundleIntegrityError("mtl_identity_path_missing_or_unexpected")
        if any(fields.get(path) != [value] for path, value in required.items()):
            raise BundleIntegrityError("mtl_level2_or_scene_identity_mismatch")
        if len(fields.get(level1_path, [])) != 1 or not level1_pattern.fullmatch(fields[level1_path][0]):
            raise BundleIntegrityError("mtl_level1_provenance_invalid")
        for name in L2_GROUPS:
            if fields.get((ROOT, name, "PROCESSING_LEVEL")) != ["L2SP"]:
                raise BundleIntegrityError("mtl_level2_processing_level_invalid")
        if fields.get((ROOT, L1_GROUP, "PROCESSING_LEVEL")) not in (["L1TP"], ["L1GT"]):
            raise BundleIntegrityError("mtl_level1_processing_level_invalid")
        if fields[(ROOT, L1_GROUP, "PROCESSING_LEVEL")][0] != fields[level1_path][0].split("_")[1]:
            raise BundleIntegrityError("mtl_level1_provenance_invalid")
    for path in required_identity_paths:
        if text_fields[path] != xml_fields[path]:
            raise BundleIntegrityError("mtl_text_xml_identity_disagree")


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
    _verify_grouped_metadata(metadata[product_id + "_MTL.txt"],
                             metadata[product_id + "_MTL.xml"], product_id, scene_id)
    return {
        "status": "pass_container_and_grouped_mtl_identity_only",
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
