#!/usr/bin/env python3
"""Record successful public CI for the exact one-second OSV implementation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from record_m2_orbit_osv_precision_amendment_001_implementation_readiness import FILES as IMPLEMENTATION_FILES


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "records/readiness/m2-orbit-osv-precision-amendment-001-implementation-publication-gate.json"
READINESS = ROOT / "records/readiness/m2-orbit-osv-precision-amendment-001-implementation-readiness.json"
FILES = dict(IMPLEMENTATION_FILES)
FILES["implementation_readiness_sha256"] = READINESS
FILES["implementation_readiness_recorder_sha256"] = ROOT / "scripts/record_m2_orbit_osv_precision_amendment_001_implementation_readiness.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verified-at-utc", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--run-url", required=True)
    args = parser.parse_args()
    if OUTPUT.exists() or not args.verified_at_utc.endswith("Z"):
        raise SystemExit("publication-gate output collision or invalid time")
    if re.fullmatch(r"[0-9a-f]{40}", args.commit_sha) is None:
        raise SystemExit("invalid commit SHA")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    origin = subprocess.run(["git", "rev-parse", "origin/main"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    expected_url = f"https://github.com/drwbkr1/nepal-2026-before-after-map/actions/runs/{args.run_id}"
    if head != origin or head != args.commit_sha or args.run_url != expected_url:
        raise SystemExit("public Git identity drift")
    missing = [str(path.relative_to(ROOT)) for path in FILES.values() if not path.is_file()]
    if missing:
        raise SystemExit("missing implementation files: " + ", ".join(missing))
    readiness = json.loads(READINESS.read_text(encoding="utf-8"))
    if (
        readiness.get("status") != "pass_local_synthetic_ready_public_ci_pending"
        or readiness.get("assertions", {}).get("real_staged_file_read") is not False
        or readiness.get("assertions", {}).get("network_requests_performed") is not False
        or readiness.get("assertions", {}).get("local_validation_started") is not False
    ):
        raise SystemExit("implementation readiness drift")
    payload = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-OSV-PRECISION-AMENDMENT-001-IMPLEMENTATION-PUBLICATION-GATE-001",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_public_one_second_implementation_before_local_validation",
        "bindings": {key: sha256(path) for key, path in FILES.items()},
        "github_actions": {
            "workflow": "Validate project controls",
            "run_id": args.run_id,
            "url": args.run_url,
            "head_sha": args.commit_sha,
            "conclusion": "success",
        },
        "assertions": {
            "public_ci_passed": True,
            "real_staged_file_read": False,
            "network_requests_performed_by_this_record": False,
            "credential_values_read_or_recorded": False,
            "local_validation_started": False,
            "staged_file_promoted": False,
            "other_orbit_source_requested": False,
            "scientific_result_established": False,
        },
        "next_gate": "run the final no-network preflight against the exact preserved staged bytes and absent destination",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"status": payload["status"], "output": str(OUTPUT.relative_to(ROOT)).replace("\\", "/")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
