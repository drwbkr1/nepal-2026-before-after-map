#!/usr/bin/env python3
"""Record successful public CI for the exact offline orbit verifier implementation."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READINESS_REF = "records/readiness/m2-orbit-offline-verification-continuation-001-implementation-readiness.json"
OUTPUT_REF = "records/readiness/m2-orbit-offline-verification-continuation-001-publication-gate.json"


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verified-at-utc", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--run-url", required=True)
    args = parser.parse_args()
    if not args.verified_at_utc.endswith("Z") or (ROOT / OUTPUT_REF).exists():
        raise SystemExit("publication gate collision or invalid time")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    origin = subprocess.run(["git", "rev-parse", "origin/main"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    readiness = json.loads((ROOT / READINESS_REF).read_text(encoding="utf-8"))
    if (
        args.commit_sha != head
        or head != origin
        or readiness.get("status") != "pass_local_offline_verifier_ready_public_ci_pending"
        or not args.run_url.startswith("https://github.com/drwbkr1/nepal-2026-before-after-map/actions/runs/")
    ):
        raise SystemExit("public CI identity, readiness, or repository head differs")
    payload = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ORBIT-OFFLINE-VERIFICATION-CONTINUATION-001-PUBLICATION-GATE",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_public_offline_verifier_controls_before_eof_reads",
        "github_actions": {
            "workflow": "Validate project controls",
            "run_id": args.run_id,
            "url": args.run_url,
            "head_sha": args.commit_sha,
            "conclusion": "success",
        },
        "bindings": {
            "candidate_contract_sha256": sha256("contracts/m2-orbit-offline-verification-continuation-001.json"),
            "implementation_readiness_sha256": sha256(READINESS_REF),
        },
        "assertions": {
            "real_eof_content_read": False,
            "network_request_performed_by_recorder": False,
            "credential_value_read_or_recorded": False,
            "external_data_mutated": False,
            "orbit_application_performed": False,
        },
        "next_gate": "activate the exact candidate, pass one final no-content preflight, then verify four exact EOF files read-only in fixed order",
    }
    with (ROOT / OUTPUT_REF).open("xb") as stream:
        stream.write((json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    print(json.dumps({"status": payload["status"], "output": OUTPUT_REF}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
