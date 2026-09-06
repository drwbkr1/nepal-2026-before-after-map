#!/usr/bin/env python3
"""Local-only controls for the approved M2-ORB-001 OSV precision amendment."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any

from m2_orbit_io_core import OrbitControlError, blake3_file, inspect_eof, md5_file, sha256_file


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = (ROOT.parent / f"{ROOT.name}-data").resolve()
SOURCE_ID = "M2-ORB-001"
ATTEMPT_ID = "m2-orb-001-osv-precision-amendment-001-local-001"
EXACT_NAME = "S1D_OPER_AUX_RESORB_OPOD_20260816T143208_V20260816T103526_20260816T140956.EOF"
EXPECTED_SIZE_BYTES = 639533
EXPECTED_SHA256 = "a72c93e500a1c09b62b4cd31889837c9d57ccc41542b16397ff9f2c0fccba3f4"
EXPECTED_MD5 = "ca7f36b1892073c883c4cff5c0517b9c"
EXPECTED_BLAKE3 = "ce824099fa812d6c229bd5bef2d4a70d7185d248f91ec3111ce557868ab1269b"
STAGING_PATH = DATA_ROOT / ".intake-staging" / "nepal-m2-orbit-recovery-003" / "m2-orb-001-recovery-002" / f"{EXACT_NAME}.part"
DESTINATION_PATH = DATA_ROOT / "custody" / "orbits" / "s1d" / "resorb" / "m2-orb-001" / EXACT_NAME
PROMOTION_TEMP_PATH = DESTINATION_PATH.with_name(f".{EXACT_NAME}.osv-precision-amendment-001.tmp")
EXTERNAL_RECEIPT_PATH = DATA_ROOT / "derived" / "m2-orbit-osv-precision-amendment-001" / f"{ATTEMPT_ID}.json"
CONTRACT_REF = "contracts/m2-orbit-offline-verification-osv-precision-amendment-001.json"
APPROVAL_REF = "records/source-gates/m2-orbit-osv-precision-amendment-001-approval.json"
ACTIVE_INTAKE_REF = "contracts/m2-orbit-intake.json"
PUBLICATION_GATE_REF = "records/readiness/m2-orbit-osv-precision-amendment-001-implementation-publication-gate.json"
FINAL_PREFLIGHT_REF = "records/readiness/m2-orbit-osv-precision-amendment-001-final-preflight.json"
RESULT_REF = "records/acquisition/m2-orbit-osv-precision-amendment-001-local-validation.json"


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise OrbitControlError("json_root_not_object")
    return value


def write_new_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def require_no_reparse_or_symlink(path: Path, *, stop_at: Path) -> None:
    current = path
    resolved_stop = stop_at.resolve()
    while True:
        if current.exists():
            info = current.lstat()
            if current.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400:
                raise OrbitControlError("path_reparse_or_symlink_refused")
        if current.resolve(strict=False) == resolved_stop:
            return
        if current.parent == current:
            raise OrbitControlError("path_escapes_data_root")
        current = current.parent


def require_path_under_data_root(path: Path) -> None:
    try:
        path.resolve(strict=False).relative_to(DATA_ROOT)
    except ValueError as exc:
        raise OrbitControlError("path_escapes_data_root") from exc
    require_no_reparse_or_symlink(path, stop_at=DATA_ROOT)


def require_exact_contract(contract: dict[str, Any]) -> dict[str, Any]:
    requirements = contract.get("asset_requirements", [])
    if (
        contract.get("contract_id") != "NEPAL-M2-ORBIT-OFFLINE-VERIFICATION-OSV-PRECISION-AMENDMENT-001"
        or contract.get("authority", {}).get("maximum_endpoint_tolerance_seconds") != 1.0
        or contract.get("authority", {}).get("maximum_local_validation_attempts") != 1
        or contract.get("authority", {}).get("maximum_network_requests") != 0
        or contract.get("endpoint_rule", {}).get("maximum_tolerance_seconds") != 1.0
        or len(requirements) != 1
        or requirements[0].get("source_id") != SOURCE_ID
        or requirements[0].get("exact_product_name") != EXACT_NAME
        or requirements[0].get("expected_size_bytes") != EXPECTED_SIZE_BYTES
        or requirements[0].get("maximum_osv_endpoint_tolerance_seconds") != 1.0
    ):
        raise OrbitControlError("amended_orbit_contract_drift")
    return requirements[0]


def exact_file_identity(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise OrbitControlError("orbit_file_missing")
    observed = {
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "md5": md5_file(path),
        "blake3": blake3_file(path),
    }
    if observed != {
        "size_bytes": EXPECTED_SIZE_BYTES,
        "sha256": EXPECTED_SHA256,
        "md5": EXPECTED_MD5,
        "blake3": EXPECTED_BLAKE3,
    }:
        raise OrbitControlError("preserved_staged_identity_mismatch")
    return observed


def atomic_no_replace_promote(
    staging_path: Path,
    destination_path: Path,
    promotion_temp_path: Path,
    requirement: dict[str, Any],
) -> dict[str, Any]:
    """Validate once, copy to an exclusive temp, and link atomically without replace."""

    if destination_path.exists() or promotion_temp_path.exists():
        raise OrbitControlError("promotion_path_collision")
    if not destination_path.parent.is_dir():
        raise OrbitControlError("promotion_parent_missing")
    source_identity_before = exact_file_identity(staging_path)
    source_inspection = inspect_eof(staging_path, requirement, logical_name=EXACT_NAME)
    with staging_path.open("rb") as source, promotion_temp_path.open("xb") as target:
        shutil.copyfileobj(source, target, length=1024 * 1024)
        target.flush()
        os.fsync(target.fileno())
    temp_identity = exact_file_identity(promotion_temp_path)
    temp_inspection = inspect_eof(promotion_temp_path, requirement, logical_name=EXACT_NAME)
    try:
        os.link(promotion_temp_path, destination_path)
    except FileExistsError as exc:
        raise OrbitControlError("promotion_destination_collision") from exc
    promotion_temp_path.unlink()
    destination_identity = exact_file_identity(destination_path)
    destination_inspection = inspect_eof(destination_path, requirement, logical_name=EXACT_NAME)
    source_identity_after = exact_file_identity(staging_path)
    if not (
        source_identity_before == source_identity_after == temp_identity == destination_identity
        and source_inspection == temp_inspection == destination_inspection
    ):
        raise OrbitControlError("promotion_readback_mismatch")
    return {
        "source_identity_before": source_identity_before,
        "source_identity_after": source_identity_after,
        "destination_identity": destination_identity,
        "inspection": destination_inspection,
        "staging_preserved": True,
        "temporary_path_removed": not promotion_temp_path.exists(),
        "destination_created_without_replace": True,
    }
