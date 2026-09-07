#!/usr/bin/env python3
"""Activate the publicly validated four-source offline orbit verification contract."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_REF = "contracts/m2-orbit-offline-verification-continuation-001.json"
ACTIVE_REF = "contracts/m2-orbit-offline-verification.json"
READINESS_REF = "records/readiness/m2-orbit-offline-verification-continuation-001-implementation-readiness.json"
PUBLICATION_REF = "records/readiness/m2-orbit-offline-verification-continuation-001-publication-gate.json"
OUTPUT_REF = "records/readiness/m2-orbit-offline-verification-continuation-001-activation.json"
SOURCE_IDS = ["M2-ORB-001", "M2-ORB-002", "M2-ORB-003", "M2-ORB-004"]


def load(ref: str) -> dict[str, Any]:
    value = json.loads((ROOT / ref).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {ref}")
    return value


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activated-at-utc", required=True)
    args = parser.parse_args()
    if not args.activated_at_utc.endswith("Z") or (ROOT / OUTPUT_REF).exists():
        raise SystemExit("activation output collision or invalid time")
    candidate = load(CANDIDATE_REF)
    active = load(ACTIVE_REF)
    readiness = load(READINESS_REF)
    publication = load(PUBLICATION_REF)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    origin = subprocess.run(["git", "rev-parse", "origin/main"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    if (
        head != origin
        or candidate.get("status") != "candidate_public_ci_pending"
        or [item.get("source_id") for item in candidate.get("asset_requirements", [])] != SOURCE_IDS
        or any(item.get("maximum_osv_endpoint_tolerance_seconds") != 1.0 for item in candidate.get("asset_requirements", []))
        or active.get("status") != "active_gate_pending_continuation_compatibility_public_ci"
        or candidate.get("bindings", {}).get("base_active_verification_sha256") != sha256(ACTIVE_REF)
        or readiness.get("status") != "pass_local_offline_verifier_ready_public_ci_pending"
        or publication.get("status") != "pass_public_offline_verifier_controls_before_eof_reads"
        or publication.get("github_actions", {}).get("head_sha") != head
        or publication.get("github_actions", {}).get("conclusion") != "success"
        or publication.get("bindings", {}).get("candidate_contract_sha256") != sha256(CANDIDATE_REF)
        or publication.get("bindings", {}).get("implementation_readiness_sha256") != sha256(READINESS_REF)
    ):
        raise SystemExit("offline verifier candidate, readiness, publication, or active base differs")
    activated = copy.deepcopy(candidate)
    activated["status"] = "active_gate_ready_for_offline_verification"
    activated["activated_at_utc"] = args.activated_at_utc
    activated["extensions"]["offline_verification_continuation_001"] = {
        "candidate_ref": CANDIDATE_REF,
        "candidate_sha256": sha256(CANDIDATE_REF),
        "implementation_readiness_ref": READINESS_REF,
        "implementation_readiness_sha256": sha256(READINESS_REF),
        "publication_gate_ref": PUBLICATION_REF,
        "publication_gate_sha256": sha256(PUBLICATION_REF),
        "offline_file_reads_started": False,
        "maximum_verification_attempts_per_source": 1,
    }
    nonce = ".offline-verification-continuation-001-activation.tmp"
    temporary = (ROOT / ACTIVE_REF).with_name((ROOT / ACTIVE_REF).name + nonce)
    if temporary.exists():
        raise SystemExit("activation temporary collision")
    with temporary.open("xb") as stream:
        stream.write(canonical(activated))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, ROOT / ACTIVE_REF)
    receipt = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ORBIT-OFFLINE-VERIFICATION-CONTINUATION-001-ACTIVATION",
        "activated_at_utc": args.activated_at_utc,
        "status": "pass_exact_four_source_offline_verifier_activated_final_preflight_pending",
        "bindings": {
            "candidate_contract_sha256": sha256(CANDIDATE_REF),
            "implementation_readiness_sha256": sha256(READINESS_REF),
            "publication_gate_sha256": sha256(PUBLICATION_REF),
            "active_contract_sha256": sha256(ACTIVE_REF),
        },
        "source_ids": SOURCE_IDS,
        "assertions": {
            "real_eof_content_read": False,
            "network_request_performed": False,
            "external_data_mutated": False,
            "orbit_application_performed": False,
            "radar_pixel_or_dem_action_performed": False,
            "baseline_change_attribution_or_publication_performed": False,
        },
        "next_gate": "one final no-content preflight before four fixed-order read-only EOF verifications",
    }
    with (ROOT / OUTPUT_REF).open("xb") as stream:
        stream.write(canonical(receipt))
    print(json.dumps({"status": receipt["status"], "output": OUTPUT_REF}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
