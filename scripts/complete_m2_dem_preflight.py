#!/usr/bin/env python3
"""Record a passing DEM preflight and initialize its empty custody directories."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent.resolve()
APPROVAL_REF = "records/source-gates/m2-dem-amendment-approval.json"
MILESTONE_REF = "contracts/milestone-002.json"
PROFILE_REF = "records/project-control-profile.json"
GOAL_REF = "records/long-term-goal.json"
INTAKE_REF = "contracts/m2-dem-intake.json"
VERIFICATION_REF = "contracts/m2-dem-offline-verification.json"
SOURCE_GATE_REF = "records/source-gates/m2-dem-live-source-gate.json"
PREFLIGHT_REF = "records/acquisition/dem-preflight.json"
RECEIPT_REF = "records/acquisition/dem-custody-initialization.json"
EVIDENCE_REF = "records/evidence-ledger.jsonl"
EXPECTED_SOURCE_IDS = ["M2-DEM-001", "M2-DEM-002", "M2-DEM-003", "M2-DEM-004"]


def load(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def serialized(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_file(relative: str) -> str:
    return sha256_path(ROOT / relative)


def sha256_value(value: object) -> str:
    return hashlib.sha256(serialized(value)).hexdigest()


def is_reparse_point(path: Path) -> bool:
    details = path.stat(follow_symlinks=False)
    attributes = getattr(details, "st_file_attributes", 0)
    return path.is_symlink() or bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def create_new(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(serialized(value))
        handle.flush()
        os.fsync(handle.fileno())


def replace(relative: str, value: object) -> None:
    path = ROOT / relative
    temporary = path.with_name(path.name + ".dem-preflight-complete-tmp")
    if temporary.exists():
        raise SystemExit(f"temporary update path already exists: {temporary}")
    with temporary.open("xb") as handle:
        handle.write(serialized(value))
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def append_evidence(value: dict[str, Any]) -> None:
    path = ROOT / EVIDENCE_REF
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if any(item.get("record_id") == value["record_id"] for item in records):
        raise SystemExit(f"evidence record already exists: {value['record_id']}")
    with path.open("ab") as handle:
        handle.write((json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--created-at-utc", required=True)
    args = parser.parse_args()
    if not args.created_at_utc.endswith("Z"):
        raise SystemExit("--created-at-utc must be an RFC 3339 UTC timestamp ending in Z")

    repo_receipt = ROOT / RECEIPT_REF
    if repo_receipt.exists():
        raise SystemExit(f"DEM custody receipt already exists; refusing replacement: {RECEIPT_REF}")

    approval = load(APPROVAL_REF)
    milestone = load(MILESTONE_REF)
    profile = load(PROFILE_REF)
    goal = load(GOAL_REF)
    intake = load(INTAKE_REF)
    verification = load(VERIFICATION_REF)
    source_gate = load(SOURCE_GATE_REF)
    preflight = load(PREFLIGHT_REF)
    if approval.get("status") != "approved" or approval.get("authorized_source_ids") != EXPECTED_SOURCE_IDS:
        raise SystemExit("exact DEM amendment approval is absent or differs")
    if source_gate.get("decision", {}).get("status") != "ready":
        raise SystemExit("DEM live source gate is not ready")
    if preflight.get("status") != "pass_no_payload_no_external_mutation":
        raise SystemExit("DEM preflight did not pass")
    if preflight.get("source_gate", {}).get("sha256") != sha256_file(SOURCE_GATE_REF):
        raise SystemExit("DEM preflight source-gate binding differs")
    if preflight.get("authority", {}).get("approval_sha256") != sha256_file(APPROVAL_REF):
        raise SystemExit("DEM preflight approval binding differs")
    if intake.get("extensions", {}).get("status") != "active_authorized_unattempted":
        raise SystemExit("DEM intake is not at the unattempted preflight state")
    intake_ids = [asset.get("extensions", {}).get("source_id") for asset in intake.get("assets", [])]
    if intake_ids != EXPECTED_SOURCE_IDS or any(asset.get("state") != "authorized" or asset.get("attempts") for asset in intake.get("assets", [])):
        raise SystemExit("DEM intake assets are not the exact authorized, unattempted set")
    if verification.get("status") != "active_gate_deferred_no_promoted_rasters" or verification.get("inputs", {}).get("intake_contract_sha256") != sha256_file(INTAKE_REF):
        raise SystemExit("active DEM verification contract differs")
    units = {unit["id"]: unit for unit in milestone.get("units", [])}
    if units.get("M2-DEM-PREFLIGHT", {}).get("status") != "ready" or units.get("M2-DEM-ACQUIRE", {}).get("status") != "planned":
        raise SystemExit("DEM milestone units are not ready for preflight completion")
    parallel = {item.get("checkpoint_id"): item for item in profile.get("parallel_checkpoints", [])}
    if "M2-DEM-FRESH-PREFLIGHT" not in parallel or goal.get("parallel_checkpoints") != ["M2-DEM-FRESH-PREFLIGHT"]:
        raise SystemExit("profile or goal does not expose the exact DEM preflight checkpoint")

    external_root = Path(preflight["paths"]["external_data_root"]).resolve(strict=False)
    custody_root = (PROJECT_ROOT / intake["custody_root"]).resolve(strict=False)
    staging_root = (PROJECT_ROOT / intake["staging_root"]).resolve(strict=False)
    dem_parent = custody_root / "dem"
    dem_custody_root = custody_root / "dem" / "copernicus-glo30"
    external_receipt = external_root / "dem-custody-initialization-receipt.json"
    if not external_root.is_dir() or not custody_root.is_dir():
        raise SystemExit("approved parent custody roots are absent")
    try:
        external_root.relative_to(ROOT.resolve())
        raise SystemExit("external root resolves inside Git")
    except ValueError:
        pass
    for child in (custody_root, staging_root, dem_custody_root, external_receipt):
        child.relative_to(external_root)
    for path in (external_root, custody_root, staging_root.parent):
        if not path.is_dir() or is_reparse_point(path):
            raise SystemExit(f"required parent is absent or a reparse point: {path}")
    if dem_parent.exists() or dem_custody_root.exists() or staging_root.exists() or external_receipt.exists():
        raise SystemExit("DEM custody or receipt collision; refusing initialization")
    for asset in intake["assets"]:
        destination = (custody_root / asset["destination_relative_path"]).resolve(strict=False)
        staging = (staging_root / asset["staging_relative_path"]).resolve(strict=False)
        destination.relative_to(dem_custody_root)
        staging.relative_to(staging_root)
        if destination.exists() or staging.exists():
            raise SystemExit(f"DEM asset path collision: {destination if destination.exists() else staging}")

    intake_sha_before = sha256_file(INTAKE_REF)
    milestone_sha_before = sha256_file(MILESTONE_REF)
    created_paths: list[Path] = []
    dem_parent.mkdir()
    created_paths.append(dem_parent)
    dem_custody_root.mkdir()
    created_paths.append(dem_custody_root)
    staging_root.mkdir()
    created_paths.append(staging_root)
    if not all(path.is_dir() and not is_reparse_point(path) for path in created_paths):
        raise SystemExit("created DEM custody paths failed verification; preserving partial state")

    receipt = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-DEM-CUSTODY-INITIALIZATION-001",
        "status": "created_and_verified_empty",
        "created_at_utc": args.created_at_utc,
        "authority": {"approval_ref": APPROVAL_REF, "approval_sha256": sha256_file(APPROVAL_REF), "active_milestone_ref": MILESTONE_REF, "active_milestone_sha256_before_completion": milestone_sha_before},
        "bindings": {"preflight_ref": PREFLIGHT_REF, "preflight_sha256": sha256_file(PREFLIGHT_REF), "source_gate_ref": SOURCE_GATE_REF, "source_gate_sha256": sha256_file(SOURCE_GATE_REF), "active_intake_ref": INTAKE_REF, "active_intake_sha256_before_initialization": intake_sha_before},
        "paths": {"external_root": str(external_root), "dem_custody_root": str(dem_custody_root), "dem_staging_root": str(staging_root), "external_receipt": str(external_receipt)},
        "created_paths": [str(path) for path in created_paths],
        "verification": {"all_paths_exist": True, "all_paths_not_reparse_points": True, "external_root_outside_git": True, "files_downloaded": 0, "dem_payload_bytes_present": 0, "authentication_performed": False, "account_or_terms_action": False},
        "next_gate": "Acquire one exact approved DEM tile at a time through append-only staging, full local SHA-256, and atomic no-replace promotion.",
    }
    create_new(external_receipt, receipt)
    create_new(repo_receipt, receipt)
    if sha256_path(external_receipt) != sha256_path(repo_receipt):
        raise SystemExit("external and repository DEM custody receipts differ")
    receipt_sha = sha256_path(repo_receipt)

    intake["extensions"].update({
        "status": "active_authorized_preflight_passed_custody_initialized",
        "source_gate_ref": SOURCE_GATE_REF,
        "source_gate_sha256": sha256_file(SOURCE_GATE_REF),
        "preflight_ref": PREFLIGHT_REF,
        "preflight_sha256": sha256_file(PREFLIGHT_REF),
        "custody_initialized": True,
        "custody_initialized_at_utc": args.created_at_utc,
        "custody_initialization_ref": RECEIPT_REF,
        "custody_initialization_sha256": receipt_sha,
        "external_custody_initialization_receipt": str(external_receipt),
    })
    new_intake_sha = sha256_value(intake)
    verification["inputs"]["intake_contract_sha256"] = new_intake_sha

    preflight_unit = units["M2-DEM-PREFLIGHT"]
    preflight_unit.update({
        "status": "complete",
        "outputs": [SOURCE_GATE_REF, PREFLIGHT_REF, RECEIPT_REF],
        "gates": {"preflight_status": "pass_no_payload_no_external_mutation", "source_gate_status": "ready", "exact_tiles_online_and_unchanged": 4, "exact_license_sha256_match": True, "free_space_gib": preflight["storage"]["free_gib"], "path_and_collision_safety": "pass", "custody_initialization": "created_and_verified_empty", "custody_initialization_sha256": receipt_sha},
        "disposition": "pass",
        "exit_condition_delta": {"expected": [], "observed": [], "decision_value": "enables_dependency", "rationale": "The exact license, four anonymous objects, storage, paths, collisions, and empty custody initialization passed under the approved DEM amendment."},
        "next_dependency": "M2-DEM-ACQUIRE",
    })
    acquire_unit = units["M2-DEM-ACQUIRE"]
    acquire_unit.update({
        "status": "ready",
        "inputs": [SOURCE_GATE_REF, PREFLIGHT_REF, RECEIPT_REF, INTAKE_REF],
        "gates": {"source_and_custody_preflight": "pass", "anonymous_no_account_route": "pass", "new_terms_route_or_cost": "stop"},
        "disposition": None,
        "exit_condition_delta": {"expected": ["EXIT-201-VERIFIED-CUSTODY"], "observed": [], "decision_value": "unknown", "rationale": "The empty DEM custody structure is initialized; no tile bytes have been requested and acquisition may proceed one exact tile at a time."},
    })
    for check in ("fresh anonymous four-tile source preflight", "DEM storage path and collision safety"):
        if check not in milestone["verification"]["completed_checks"]:
            milestone["verification"]["completed_checks"].append(check)
    milestone["handoff"].update({
        "parallel_checkpoint": "M2-DEM-ACQUISITION",
        "parallel_next_action": "Acquire M2-DEM-001 only through append-only staging, verify its exact length and local SHA-256, and promote without replacement; stop on any route or identity drift.",
    })
    parallel["M2-DEM-FRESH-PREFLIGHT"].update({
        "checkpoint_id": "M2-DEM-ACQUISITION",
        "next_action": milestone["handoff"]["parallel_next_action"],
    })
    goal["parallel_checkpoints"] = ["M2-DEM-ACQUISITION"]

    replace(INTAKE_REF, intake)
    replace(VERIFICATION_REF, verification)
    replace(MILESTONE_REF, milestone)
    replace(PROFILE_REF, profile)
    replace(GOAL_REF, goal)
    evidence = {
        "record_id": "EVID-0032",
        "type": "m2_dem_live_preflight_and_empty_custody",
        "status": "pass_exact_source_and_path_controls_no_payload",
        "verified_at_utc": args.created_at_utc,
        "claim": "The accepted license, four exact anonymous DEM objects, storage, paths, collisions, and empty non-Git custody structure passed; no DEM payload byte was requested or present.",
        "source_gate_ref": SOURCE_GATE_REF,
        "source_gate_sha256": sha256_file(SOURCE_GATE_REF),
        "preflight_ref": PREFLIGHT_REF,
        "preflight_sha256": sha256_file(PREFLIGHT_REF),
        "custody_initialization_ref": RECEIPT_REF,
        "custody_initialization_sha256": receipt_sha,
        "active_intake_ref": INTAKE_REF,
        "active_intake_sha256": sha256_file(INTAKE_REF),
        "active_verification_ref": VERIFICATION_REF,
        "active_verification_sha256": sha256_file(VERIFICATION_REF),
        "completion_script_ref": "scripts/complete_m2_dem_preflight.py",
        "completion_script_sha256": sha256_file("scripts/complete_m2_dem_preflight.py"),
        "assertions": {"exact_license_match": True, "exact_tile_count": 4, "remote_identity_unchanged": True, "source_gate_ready": True, "external_paths_initialized_empty": True, "dem_payload_bytes_requested": False, "dem_payload_bytes_present": 0, "authentication_performed": False, "scientific_result_established": False},
        "limitations": preflight["limitations"],
    }
    append_evidence(evidence)
    print(json.dumps({"status": "dem_preflight_recorded_and_empty_custody_initialized", "created_at_utc": args.created_at_utc, "source_gate_sha256": sha256_file(SOURCE_GATE_REF), "preflight_sha256": sha256_file(PREFLIGHT_REF), "custody_receipt_sha256": receipt_sha, "active_intake_sha256": sha256_file(INTAKE_REF), "active_verification_sha256": sha256_file(VERIFICATION_REF), "next_checkpoint": "M2-DEM-ACQUISITION", "dem_payload_bytes_present": 0}, indent=2))


if __name__ == "__main__":
    main()
