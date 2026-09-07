#!/usr/bin/env python3
"""Final no-content preflight for the four exact promoted orbit EOF verifications."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent.resolve()
ACTIVE_REF = "contracts/m2-orbit-offline-verification.json"
INTAKE_REF = "contracts/m2-orbit-intake.json"
ACTIVATION_REF = "records/readiness/m2-orbit-offline-verification-continuation-001-activation.json"
OUTPUT_REF = "records/readiness/m2-orbit-offline-verification-continuation-001-final-preflight.json"
SOURCE_IDS = ["M2-ORB-001", "M2-ORB-002", "M2-ORB-003", "M2-ORB-004"]
RECEIPT_REFS = {
    source_id: f"records/acquisition/orbit-verification/{source_id.casefold()}-offline-verification-001.json"
    for source_id in SOURCE_IDS
}


def load(ref: str) -> dict[str, Any]:
    value = json.loads((ROOT / ref).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {ref}")
    return value


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verified-at-utc", required=True)
    args = parser.parse_args()
    if not args.verified_at_utc.endswith("Z") or (ROOT / OUTPUT_REF).exists():
        raise SystemExit("final preflight output collision or invalid time")
    active = load(ACTIVE_REF)
    intake = load(INTAKE_REF)
    activation = load(ACTIVATION_REF)
    if (
        active.get("status") != "active_gate_ready_for_offline_verification"
        or activation.get("status") != "pass_exact_four_source_offline_verifier_activated_final_preflight_pending"
        or activation.get("bindings", {}).get("active_contract_sha256") != sha256(ACTIVE_REF)
        or active.get("bindings", {}).get("active_intake_sha256_current") != sha256(INTAKE_REF)
        or [item.get("source_id") for item in active.get("asset_requirements", [])] != SOURCE_IDS
        or any(item.get("maximum_osv_endpoint_tolerance_seconds") != 1.0 for item in active.get("asset_requirements", []))
        or intake.get("extensions", {}).get("current_orbit_state_counts") != {"authorized": 0, "failed": 0, "promoted": 4}
    ):
        raise SystemExit("activated verification or intake controls differ")
    assets = intake.get("assets", [])
    if [item.get("extensions", {}).get("source_id") for item in assets] != SOURCE_IDS:
        raise SystemExit("orbit source order differs")
    custody_root = (PROJECT_ROOT / Path(*PurePosixPath(intake["custody_root"]).parts)).resolve(strict=True)
    observed: list[dict[str, Any]] = []
    for asset in assets:
        source_id = asset["extensions"]["source_id"]
        path = (custody_root / Path(*PurePosixPath(asset["destination_relative_path"]).parts)).resolve(strict=True)
        path.relative_to(custody_root)
        if (
            asset.get("state") != "promoted"
            or not path.is_file()
            or path.is_symlink()
            or path.stat().st_size != asset.get("observed", {}).get("promoted_size_bytes")
            or (ROOT / RECEIPT_REFS[source_id]).exists()
        ):
            raise SystemExit(f"promoted path, size, link, or output collision differs: {source_id}")
        observed.append({"source_id": source_id, "path": str(path), "size_bytes": path.stat().st_size})
    output = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ORBIT-OFFLINE-VERIFICATION-CONTINUATION-001-FINAL-PREFLIGHT",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_no_content_ready_for_four_fixed_order_offline_verifications",
        "source_ids_in_exact_order": SOURCE_IDS,
        "observed_paths_without_content_read": observed,
        "bindings": {
            "active_verification_sha256": sha256(ACTIVE_REF),
            "active_intake_sha256": sha256(INTAKE_REF),
            "activation_sha256": sha256(ACTIVATION_REF),
        },
        "assertions": {
            "eof_content_read": False,
            "network_request_performed": False,
            "credential_value_read_or_recorded": False,
            "external_data_mutated": False,
            "verification_receipt_collision": False,
            "orbit_application_performed": False,
            "radar_pixel_or_dem_action_performed": False,
            "baseline_change_attribution_or_publication_performed": False,
        },
        "next_action": "run exactly one read-only verification for each source in stated order and stop on the first failure",
    }
    path = ROOT / OUTPUT_REF
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write((json.dumps(output, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"status": output["status"], "output": OUTPUT_REF}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
