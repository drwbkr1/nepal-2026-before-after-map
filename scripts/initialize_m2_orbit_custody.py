#!/usr/bin/env python3
"""Create and verify the approved empty M2 orbit custody structure."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent.resolve()
APPROVAL_REF = "records/source-gates/m2-orbit-amendment-approval.json"
INTAKE_REF = "contracts/m2-orbit-intake.json"
PREFLIGHT_REF = "records/acquisition/orbit-preflight.json"
SOURCE_GATE_REF = "records/source-gates/m2-orbit-live-source-gate.json"
RECEIPT_REF = "records/acquisition/orbit-custody-initialization.json"
FAILURE_REF = "records/acquisition/orbit-custody-initialization-attempt-001-failure.json"
READINESS_REF = "records/acquisition/orbit-custody-initialization-attempt-002-readiness.json"
MILESTONE_REF = "contracts/milestone-002.json"
PROFILE_REF = "records/project-control-profile.json"
GOAL_REF = "records/long-term-goal.json"
EXPECTED_SOURCE_IDS = [f"M2-ORB-{index:03d}" for index in range(1, 5)]


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load(relative: str) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {relative}")
    return value


def is_reparse_point(path: Path) -> bool:
    attributes = getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0)
    return path.is_symlink() or bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def write_exclusive(path: Path, value: dict[str, Any]) -> None:
    with path.open("xb") as handle:
        handle.write(canonical_bytes(value))
        handle.flush()
        os.fsync(handle.fileno())


def replace(relative: str, value: dict[str, Any]) -> None:
    path = ROOT / relative
    temporary = path.with_name(path.name + ".orbit-custody-init-tmp")
    if temporary.exists():
        raise ValueError(f"temporary update path already exists: {temporary}")
    with temporary.open("xb") as handle:
        handle.write(canonical_bytes(value))
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def child(root: Path, relative: str) -> Path:
    posix = PurePosixPath(relative)
    if posix.is_absolute() or ".." in posix.parts:
        raise ValueError("custody relative path is unsafe")
    result = (root / Path(*posix.parts)).resolve(strict=False)
    result.relative_to(root)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--created-at-utc", required=True)
    args = parser.parse_args()
    if not args.created_at_utc.endswith("Z"):
        raise SystemExit("--created-at-utc must be RFC 3339 UTC ending in Z")

    repository_receipt = ROOT / RECEIPT_REF
    if repository_receipt.exists():
        raise SystemExit(f"custody receipt already exists; refusing replacement: {RECEIPT_REF}")
    approval = load(APPROVAL_REF)
    intake = load(INTAKE_REF)
    preflight = load(PREFLIGHT_REF)
    source_gate = load(SOURCE_GATE_REF)
    failure = load(FAILURE_REF)
    readiness = load(READINESS_REF)
    milestone = load(MILESTONE_REF)
    profile = load(PROFILE_REF)
    goal = load(GOAL_REF)
    if approval.get("status") != "approved" or approval.get("authorized_source_ids") != EXPECTED_SOURCE_IDS:
        raise SystemExit("exact orbit approval is absent or differs")
    if preflight.get("status") != "pass_no_payload_no_external_mutation_sentinel_custody_pending":
        raise SystemExit("orbit preflight did not pass its non-payload checks")
    if preflight.get("source_gate_sha256") != sha256_file(ROOT / SOURCE_GATE_REF):
        raise SystemExit("orbit preflight source-gate binding differs")
    if source_gate.get("decision", {}).get("status") != "ready":
        raise SystemExit("live orbit source gate is not ready")
    if failure.get("status") != "failed_missing_attempt_events_parent_after_partial_empty_directory_creation":
        raise SystemExit("attempt-001 failure is absent or differs")
    if readiness.get("status") != "pass_exact_empty_partial_inventory_continuation_predeclared":
        raise SystemExit("attempt-002 readiness is absent or differs")
    if readiness.get("failure_sha256") != sha256_file(ROOT / FAILURE_REF):
        raise SystemExit("attempt-002 readiness does not bind the exact failure")
    if readiness.get("implementation_sha256") != sha256_file(ROOT / "scripts/initialize_m2_orbit_custody.py"):
        raise SystemExit("attempt-002 readiness does not bind this exact implementation")
    extensions = intake.get("extensions", {})
    if (
        extensions.get("status")
        != "active_authorized_preflight_passed_custody_not_initialized_sentinel_custody_pending"
        or extensions.get("custody_initialized") is not False
        or extensions.get("preflight_sha256") != sha256_file(ROOT / PREFLIGHT_REF)
    ):
        raise SystemExit("active orbit intake is not at the custody-initialization checkpoint")

    data_root = (PROJECT_ROOT / "nepal-2026-before-after-map-data").resolve(strict=True)
    custody_root = child(PROJECT_ROOT, intake["custody_root"])
    staging_root = child(PROJECT_ROOT, intake["staging_root"])
    custody_root.relative_to(data_root)
    staging_root.relative_to(data_root)
    external_receipt = data_root / "orbit-custody-initialization-receipt.json"
    if external_receipt.exists():
        raise SystemExit("external orbit custody receipt already exists")
    for ancestor in (data_root, data_root / "custody", data_root / ".intake-staging"):
        if not ancestor.is_dir() or is_reparse_point(ancestor):
            raise SystemExit(f"required existing custody ancestor is absent or unsafe: {ancestor}")

    desired: set[Path] = set()
    for root, stop in ((custody_root, data_root / "custody"), (staging_root, data_root / ".intake-staging")):
        current = root
        while current != stop:
            desired.add(current)
            current = current.parent
        if current != stop:
            raise SystemExit("custody root does not descend from its approved existing ancestor")
    for asset in intake["assets"]:
        desired.add(child(custody_root, asset["destination_relative_path"]).parent)
        desired.add(child(staging_root, asset["staging_relative_path"]).parent)
        desired.add(staging_root / "attempt-events")
        desired.add(staging_root / "attempt-events" / asset["asset_id"])
    expected_partial = {Path(value) for value in failure["observed_partial_directories"]}
    observed_partial = {path for path in desired if path.exists()}
    if observed_partial != expected_partial:
        raise SystemExit(
            f"orbit custody partial inventory differs: expected={sorted(map(str, expected_partial))} observed={sorted(map(str, observed_partial))}"
        )
    if any(path.is_file() for root in expected_partial for path in root.rglob("*")):
        raise SystemExit("attempt-001 partial inventory now contains a file")
    if any(is_reparse_point(path) for path in expected_partial):
        raise SystemExit("attempt-001 partial inventory contains a link or reparse point")
    free_before = shutil.disk_usage(PROJECT_ROOT).free
    if free_before < int(preflight["storage_check"]["minimum_free_bytes"]):
        raise SystemExit("free space fell below the inherited acquisition floor")

    created_paths: list[Path] = []
    for path in sorted(desired, key=lambda value: (len(value.parts), str(value))):
        if path in expected_partial:
            continue
        if not path.parent.is_dir() or is_reparse_point(path.parent):
            raise SystemExit(f"unsafe or absent parent before directory creation: {path.parent}")
        path.mkdir()
        created_paths.append(path)
    if not created_paths or any(not path.is_dir() or is_reparse_point(path) for path in created_paths):
        raise SystemExit("created orbit custody directories failed verification; preserving partial state")
    if any(path.is_file() for directory in created_paths for path in directory.iterdir()):
        raise SystemExit("new orbit custody directories contain files; preserving state")

    receipt = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-CUSTODY-INITIALIZATION-001",
        "status": "created_and_verified_empty",
        "created_at_utc": args.created_at_utc,
        "approval_ref": APPROVAL_REF,
        "approval_sha256": sha256_file(ROOT / APPROVAL_REF),
        "preflight_ref": PREFLIGHT_REF,
        "preflight_sha256": sha256_file(ROOT / PREFLIGHT_REF),
        "source_gate_ref": SOURCE_GATE_REF,
        "source_gate_sha256": sha256_file(ROOT / SOURCE_GATE_REF),
        "active_intake_ref": INTAKE_REF,
        "active_intake_sha256_before_initialization": sha256_file(ROOT / INTAKE_REF),
        "attempt_001_failure_ref": FAILURE_REF,
        "attempt_001_failure_sha256": sha256_file(ROOT / FAILURE_REF),
        "attempt_002_readiness_ref": READINESS_REF,
        "attempt_002_readiness_sha256": sha256_file(ROOT / READINESS_REF),
        "paths": {
            "data_root": str(data_root),
            "custody_root": str(custody_root),
            "staging_root": str(staging_root),
            "external_receipt": str(external_receipt),
        },
        "preserved_partial_paths": sorted(str(path) for path in expected_partial),
        "created_paths_attempt_002": [str(path) for path in created_paths],
        "verification": {
            "preserved_partial_directory_count": len(expected_partial),
            "created_directory_count_attempt_002": len(created_paths),
            "all_paths_exist": all(path.is_dir() for path in desired),
            "all_paths_not_reparse_points": all(not is_reparse_point(path) for path in desired),
            "all_asset_destination_parents_exist": all(
                child(custody_root, asset["destination_relative_path"]).parent.is_dir() for asset in intake["assets"]
            ),
            "all_asset_staging_parents_exist": all(
                child(staging_root, asset["staging_relative_path"]).parent.is_dir() for asset in intake["assets"]
            ),
            "all_attempt_event_directories_exist": all(
                (staging_root / "attempt-events" / asset["asset_id"]).is_dir() for asset in intake["assets"]
            ),
            "free_bytes_before": free_before,
            "files_downloaded": 0,
            "network_requests_performed": False,
            "authentication_performed": False,
            "credential_values_read_or_recorded": False,
        },
        "credential_values_read_or_recorded": False,
        "next_gate": "M2-ORBIT-SENTINEL-CUSTODY",
    }
    write_exclusive(external_receipt, receipt)
    repository_receipt.parent.mkdir(parents=True, exist_ok=True)
    write_exclusive(repository_receipt, receipt)
    if sha256_file(external_receipt) != sha256_file(repository_receipt):
        raise SystemExit("external and repository orbit custody receipts differ")

    intake["extensions"].update(
        {
            "status": "active_authorized_preflight_passed_custody_initialized",
            "custody_initialized": True,
            "custody_initialized_at_utc": args.created_at_utc,
            "custody_initialization_ref": RECEIPT_REF,
            "custody_initialization_sha256": sha256_file(repository_receipt),
            "external_custody_initialization_receipt": str(external_receipt),
            "sentinel_custody_prerequisite_status": "pending_zero_of_six_promoted_and_verified",
        }
    )
    replace(INTAKE_REF, intake)

    unit = next(item for item in milestone["units"] if item["id"] == "M2-ORBIT-ACQUIRE")
    unit["gates"].update(
        {
            "fresh_source_preflight": "pass",
            "orbit_custody_initialized": True,
            "matching_sentinel_promoted_and_verified": False,
            "token_presence_checked": False,
        }
    )
    unit["rationale"] = "Empty orbit custody is verified; payload transfer remains blocked on matching verified Sentinel custody."
    replace(MILESTONE_REF, milestone)

    for checkpoint in profile["parallel_checkpoints"]:
        if checkpoint["checkpoint_id"] == "M2-ORBIT-CUSTODY-INITIALIZATION":
            checkpoint.update(
                {
                    "checkpoint_id": "M2-ORBIT-SENTINEL-CUSTODY",
                    "authority_ref": APPROVAL_REF,
                    "next_action": "Resume the original Sentinel acquisition through its existing secret-safe session; orbit transfer remains blocked until each bound radar source is promoted and offline container-verified.",
                }
            )
            break
    else:
        raise SystemExit("project profile orbit custody checkpoint is absent")
    replace(PROFILE_REF, profile)
    goal["parallel_checkpoints"] = [
        "M2-ORBIT-SENTINEL-CUSTODY" if value == "M2-ORBIT-CUSTODY-INITIALIZATION" else value
        for value in goal["parallel_checkpoints"]
    ]
    replace(GOAL_REF, goal)

    ledger_path = ROOT / "records/evidence-ledger.jsonl"
    ledger = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if any(item.get("record_id") == "EVID-0057" for item in ledger):
        raise SystemExit("EVID-0057 already exists")
    evidence = {
        "record_id": "EVID-0057",
        "type": "m2_sentinel1_orbit_custody_initialization",
        "status": "pass_empty_custody_initialized_sentinel_custody_pending",
        "verified_at_utc": args.created_at_utc,
        "claim": "The exact non-Git orbit custody, staging, event, and per-source directory structure was created empty and verified without authentication, network access, or payload transfer; matching Sentinel custody still blocks orbit acquisition.",
        "custody_receipt_ref": RECEIPT_REF,
        "custody_receipt_sha256": sha256_file(repository_receipt),
        "attempt_001_failure_ref": FAILURE_REF,
        "attempt_001_failure_sha256": sha256_file(ROOT / FAILURE_REF),
        "attempt_002_readiness_ref": READINESS_REF,
        "attempt_002_readiness_sha256": sha256_file(ROOT / READINESS_REF),
        "preflight_ref": PREFLIGHT_REF,
        "preflight_sha256": sha256_file(ROOT / PREFLIGHT_REF),
        "active_intake_ref": INTAKE_REF,
        "active_intake_sha256": sha256_file(ROOT / INTAKE_REF),
        "initialization_script_ref": "scripts/initialize_m2_orbit_custody.py",
        "initialization_script_sha256": sha256_file(ROOT / "scripts/initialize_m2_orbit_custody.py"),
        "assertions": {
            "preserved_partial_empty_directories": len(expected_partial),
            "empty_directories_created_attempt_002": len(created_paths),
            "files_downloaded": 0,
            "network_requests_performed": False,
            "authentication_performed": False,
            "credential_values_read_or_recorded": False,
            "sentinel_promoted_and_verified_count": 0,
            "orbit_payload_bytes_requested": 0,
            "precise_substitution_authorized": False,
            "scientific_result_established": False,
        },
        "limitations": [
            "Directory initialization does not establish source availability, transferred-byte integrity, or XML fitness.",
            "No token presence or validity check occurred.",
            "Orbit acquisition remains blocked until matching Sentinel sources are promoted and offline container-verified.",
        ],
        "next_action": "Continue the separately gated Sentinel acquisition; do not request orbit payload bytes yet.",
    }
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(evidence, separators=(",", ":")) + "\n")
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "receipt": RECEIPT_REF,
                "receipt_sha256": sha256_file(repository_receipt),
                "preserved_partial_directory_count": len(expected_partial),
                "created_directory_count_attempt_002": len(created_paths),
                "files_downloaded": 0,
                "network_requests_performed": False,
                "authentication_performed": False,
                "orbit_payload_bytes_requested": 0,
                "next_gate": "M2-ORBIT-SENTINEL-CUSTODY",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
