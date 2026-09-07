#!/usr/bin/env python3
"""Run the final no-content preflight for offline orbit-verification recovery-001."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent.resolve()
ACTIVE_REF = "contracts/m2-orbit-offline-verification.json"
INTAKE_REF = "contracts/m2-orbit-intake.json"
CANDIDATE_REF = "contracts/m2-orbit-offline-verification-recovery-001.json"
CANDIDATE_SHA256 = "8db4774dfb36ce9718988c23d9a480a01028055a6a28a1bbf301a926e466df68"
PUBLICATION_REF = "records/readiness/m2-orbit-offline-verification-recovery-001-implementation-publication-gate.json"
OUTPUT_REF = "records/readiness/m2-orbit-offline-verification-recovery-001-final-preflight.json"
SOURCE_IDS = ["M2-ORB-001", "M2-ORB-002", "M2-ORB-003", "M2-ORB-004"]


def load(ref: str) -> dict[str, Any]:
    value = json.loads((ROOT / ref).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {ref}")
    return value


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def is_reparse(path: Path) -> bool:
    attributes = getattr(os.lstat(path), "st_file_attributes", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verified-at-utc", required=True)
    args = parser.parse_args()
    if not args.verified_at_utc.endswith("Z") or (ROOT / OUTPUT_REF).exists():
        raise SystemExit("invalid verification time or preflight output collision")
    active = load(ACTIVE_REF)
    intake = load(INTAKE_REF)
    candidate = load(CANDIDATE_REF)
    publication = load(PUBLICATION_REF)
    extension = active.get("extensions", {}).get("offline_verification_recovery_001", {})
    output_refs = candidate.get("output_refs", {})
    if (
        sha256(CANDIDATE_REF) != CANDIDATE_SHA256
        or active.get("status") != "active_recovery_ready_for_offline_verification"
        or active.get("bindings", {}).get("active_intake_sha256_current") != sha256(INTAKE_REF)
        or extension.get("candidate_sha256") != CANDIDATE_SHA256
        or extension.get("public_ci") != "pass"
        or extension.get("final_no_content_preflight") != "required"
        or extension.get("source_ids_in_exact_order") != SOURCE_IDS
        or candidate.get("source_ids_in_exact_order") != SOURCE_IDS
        or list(output_refs) != SOURCE_IDS
        or publication.get("status") != "pass_public_recovery_controls_before_eof_reads"
        or publication.get("github_actions", {}).get("conclusion") != "success"
    ):
        raise SystemExit("active recovery, candidate, or public-CI binding differs")
    output_parent = ROOT / "records/acquisition/orbit-verification"
    try:
        resolved_parent = output_parent.resolve(strict=True)
        resolved_parent.relative_to(ROOT.resolve())
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit("exact output parent missing or escaped") from exc
    if (
        resolved_parent != (ROOT / "records/acquisition/orbit-verification").resolve()
        or not output_parent.is_dir()
        or output_parent.is_symlink()
        or is_reparse(output_parent)
    ):
        raise SystemExit("exact output parent is not a real non-link directory")
    members = sorted(path.name for path in output_parent.iterdir())
    if members != [".gitkeep"]:
        raise SystemExit("output parent contains an unexpected member or prior attempt")
    for ref in output_refs.values():
        path = ROOT / ref
        if path.parent.resolve() != resolved_parent or path.exists() or path.is_symlink():
            raise SystemExit("exact output path is not collision-free")
    assets = intake.get("assets", [])
    if [item.get("extensions", {}).get("source_id") for item in assets] != SOURCE_IDS:
        raise SystemExit("active intake source order differs")
    custody_root = (PROJECT_ROOT / Path(*PurePosixPath(intake["custody_root"]).parts)).resolve(strict=True)
    custody_metadata: list[dict[str, Any]] = []
    for asset in assets:
        path = (custody_root / Path(*PurePosixPath(asset["destination_relative_path"]).parts)).resolve(strict=True)
        path.relative_to(custody_root)
        expected_size = asset.get("observed", {}).get("promoted_size_bytes")
        if not path.is_file() or path.is_symlink() or is_reparse(path) or path.stat().st_size != expected_size:
            raise SystemExit("custody file metadata differs before content access")
        custody_metadata.append({
            "source_id": asset["extensions"]["source_id"],
            "path": str(path),
            "size_bytes_from_metadata_only": path.stat().st_size,
            "content_hash_computed": False,
        })
    receipt = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-FINAL-PREFLIGHT",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_no_content_ready_for_exact_recovery_sequence",
        "bindings": {
            "active_verification_sha256": sha256(ACTIVE_REF),
            "active_intake_sha256": sha256(INTAKE_REF),
            "candidate_contract_sha256": CANDIDATE_SHA256,
            "publication_gate_sha256": sha256(PUBLICATION_REF),
        },
        "source_ids_in_exact_order": SOURCE_IDS,
        "output_refs": output_refs,
        "output_parent": str(resolved_parent),
        "custody_metadata": custody_metadata,
        "assertions": {
            "output_parent_exact_real_non_link_directory": True,
            "output_parent_only_contains_tracked_marker": True,
            "all_output_paths_absent": True,
            "eof_content_read": False,
            "eof_content_hash_computed": False,
            "network_request_performed": False,
            "credential_value_read_or_recorded": False,
            "external_custody_mutated": False,
            "orbit_application_performed": False,
            "dem_or_radar_pixel_action_performed": False,
            "baseline_change_attribution_or_publication_performed": False,
        },
        "next_action": "run exactly one M2-ORB-001 recovery verification and continue in fixed order only on pass",
    }
    path = ROOT / OUTPUT_REF
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(receipt, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    print(json.dumps({"status": receipt["status"], "output": OUTPUT_REF}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
