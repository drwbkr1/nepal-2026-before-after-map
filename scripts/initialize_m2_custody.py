#!/usr/bin/env python3
"""Create the approved empty M2 custody structure and bind an exact receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent.resolve()
APPROVAL_REF = "records/source-gates/m2-activation-approval.json"
CONTRACT_REF = "contracts/milestone-002.json"
INTAKE_REF = "contracts/m2-intake.json"
PREFLIGHT_REF = "records/acquisition/preflight.json"
SOURCE_GATE_REF = "records/source-gates/m2-live-source-gate.json"
RECEIPT_REF = "records/acquisition/custody-initialization.json"


def load(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def serialized(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2) + "\n").encode("utf-8")


def is_reparse_point(path: Path) -> bool:
    attributes = getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def create_new(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(serialized(value))
        handle.flush()
        os.fsync(handle.fileno())


def replace(relative: str, value: dict[str, Any]) -> None:
    path = ROOT / relative
    temporary = path.with_name(path.name + ".custody-init-tmp")
    if temporary.exists():
        raise SystemExit(f"temporary update path already exists: {temporary}")
    with temporary.open("xb") as handle:
        handle.write(serialized(value))
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--created-at-utc", required=True)
    args = parser.parse_args()

    repo_receipt = ROOT / RECEIPT_REF
    if repo_receipt.exists():
        raise SystemExit(f"custody receipt already exists; refusing replacement: {RECEIPT_REF}")

    approval = load(APPROVAL_REF)
    contract = load(CONTRACT_REF)
    intake = load(INTAKE_REF)
    preflight = load(PREFLIGHT_REF)
    source_gate = load(SOURCE_GATE_REF)
    if approval.get("status") != "approved":
        raise SystemExit("M2 approval is not active")
    units = {unit["id"]: unit for unit in contract["units"]}
    if units["M2-CUSTODY-PREFLIGHT"].get("disposition") != "pass" or units["M2-ACQUIRE"].get("status") != "ready":
        raise SystemExit("M2 contract is not at the custody-initialization checkpoint")
    if preflight.get("status") != "pass_no_external_mutation":
        raise SystemExit("preflight did not pass")
    if preflight.get("source_gate", {}).get("sha256") != sha256_path(ROOT / SOURCE_GATE_REF):
        raise SystemExit("preflight source-gate hash differs")
    if source_gate.get("decision", {}).get("status") != "ready":
        raise SystemExit("source gate is not ready")
    if intake.get("extensions", {}).get("custody_initialized") is not False:
        raise SystemExit("active intake no longer declares uninitialized custody")

    external_root = Path(preflight["paths"]["planned_external_data_root"]).resolve(strict=False)
    custody_root = (PROJECT_ROOT / intake["custody_root"]).resolve(strict=False)
    staging_root = (PROJECT_ROOT / intake["staging_root"]).resolve(strict=False)
    approved_root = Path(load("records/acquisition-plan.json")["custody"]["planned_external_root"]).resolve(strict=False)
    if external_root != approved_root:
        raise SystemExit("preflight root differs from the approved plan")
    try:
        external_root.relative_to(ROOT.resolve())
        raise SystemExit("external root resolves inside the Git repository")
    except ValueError:
        pass
    for child in (custody_root, staging_root):
        child.relative_to(external_root)
        if child == external_root:
            raise SystemExit("custody paths must be children of the external root")
    if external_root.exists():
        raise SystemExit("external root already exists; refusing ambiguous initialization")

    current = external_root.parent
    while True:
        if not current.exists() or is_reparse_point(current):
            raise SystemExit(f"external root ancestor is absent or a reparse point: {current}")
        if current == current.parent:
            break
        current = current.parent
    minimum_gib = float(preflight["storage"]["minimum_free_gib"])
    free_before = shutil.disk_usage(PROJECT_ROOT).free
    if free_before / (1024 ** 3) < minimum_gib:
        raise SystemExit("free space fell below the approved minimum")

    created_paths: list[Path] = []
    external_root.mkdir()
    created_paths.append(external_root)
    custody_root.mkdir(parents=True)
    created_paths.append(custody_root)
    staging_root.mkdir(parents=True)
    created_paths.append(staging_root)
    external_receipt = external_root / "custody-initialization-receipt.json"
    receipt = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-CUSTODY-INITIALIZATION-001",
        "status": "created_and_verified",
        "created_at_utc": args.created_at_utc,
        "authority": {
            "approval_ref": APPROVAL_REF,
            "approval_sha256": sha256_path(ROOT / APPROVAL_REF),
            "active_contract_ref": CONTRACT_REF,
            "active_contract_sha256_at_initialization": sha256_path(ROOT / CONTRACT_REF),
        },
        "bindings": {
            "preflight_ref": PREFLIGHT_REF,
            "preflight_sha256": sha256_path(ROOT / PREFLIGHT_REF),
            "source_gate_ref": SOURCE_GATE_REF,
            "source_gate_sha256": sha256_path(ROOT / SOURCE_GATE_REF),
            "active_intake_ref": INTAKE_REF,
            "active_intake_sha256_before_initialization": sha256_path(ROOT / INTAKE_REF),
        },
        "paths": {
            "external_root": str(external_root),
            "custody_root": str(custody_root),
            "staging_root": str(staging_root),
            "external_receipt": str(external_receipt),
        },
        "created_paths": [str(path) for path in created_paths],
        "verification": {
            "all_paths_exist": all(path.is_dir() for path in created_paths),
            "all_paths_not_reparse_points": all(not is_reparse_point(path) for path in created_paths),
            "external_root_outside_git": True,
            "free_bytes_before": free_before,
            "minimum_free_gib": minimum_gib,
            "files_downloaded": 0,
            "authentication_performed": False,
            "credential_values_read_or_recorded": False,
        },
        "next_gate": "A secret-safe reference to an existing owner-controlled CDSE credential or authenticated session is required before the first exact-product transfer.",
    }
    if not receipt["verification"]["all_paths_exist"] or not receipt["verification"]["all_paths_not_reparse_points"]:
        raise SystemExit("created custody paths failed verification; preserving partial state for review")

    create_new(external_receipt, receipt)
    create_new(repo_receipt, receipt)
    if sha256_path(external_receipt) != sha256_path(repo_receipt):
        raise SystemExit("external and repository custody receipts differ")

    intake["extensions"].update({
        "status": "active_authorized_preflight_passed_custody_initialized",
        "custody_initialized": True,
        "custody_initialized_at_utc": args.created_at_utc,
        "custody_initialization_ref": RECEIPT_REF,
        "custody_initialization_sha256": sha256_path(repo_receipt),
        "external_custody_initialization_receipt": str(external_receipt),
    })
    replace(INTAKE_REF, intake)
    print(json.dumps({
        "status": "created_and_verified",
        "created_at_utc": args.created_at_utc,
        "receipt": RECEIPT_REF,
        "receipt_sha256": sha256_path(repo_receipt),
        "external_receipt_sha256": sha256_path(external_receipt),
        "external_root": str(external_root),
        "files_downloaded": 0,
        "authentication_performed": False,
    }, indent=2))


if __name__ == "__main__":
    main()
