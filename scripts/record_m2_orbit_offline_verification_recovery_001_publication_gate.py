#!/usr/bin/env python3
"""Record successful public CI for offline orbit-verification recovery-001."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READINESS_REF = "records/readiness/m2-orbit-offline-verification-recovery-001-implementation-readiness.json"
OUTPUT_REF = "records/readiness/m2-orbit-offline-verification-recovery-001-implementation-publication-gate.json"


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verified-at-utc", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--run-url", required=True)
    args = parser.parse_args()
    if not args.verified_at_utc.endswith("Z") or len(args.commit_sha) != 40 or (ROOT / OUTPUT_REF).exists():
        raise SystemExit("invalid publication evidence or output collision")
    readiness = json.loads((ROOT / READINESS_REF).read_text(encoding="utf-8"))
    bindings = readiness.get("bindings", {})
    refs = {
        "candidate_contract_sha256": "contracts/m2-orbit-offline-verification-recovery-001.json",
        "verifier_sha256": "scripts/verify_m2_orbit_eof_recovery_001.py",
        "runner_sha256": "scripts/run_m2_orbit_offline_verification_recovery_001.py",
        "preflight_sha256": "scripts/preflight_m2_orbit_offline_verification_recovery_001.py",
        "activation_script_sha256": "scripts/activate_m2_orbit_offline_verification_recovery_001.py",
        "terminal_reconciler_sha256": "scripts/reconcile_m2_orbit_offline_verification_recovery_001.py",
        "tests_sha256": "tests/test_m2_orbit_offline_verification_recovery_001.py",
    }
    if (
        readiness.get("status") != "pass_local_recovery_implementation_ready_public_ci_pending"
        or any(bindings.get(name) != sha256(ref) for name, ref in refs.items())
        or any(value is not False for key, value in readiness.get("assertions", {}).items() if key in {
            "real_eof_content_read", "network_request_performed", "credential_value_read_or_recorded",
            "external_custody_mutated", "verification_receipt_created", "orbit_application_performed",
            "dem_or_radar_pixel_action_performed", "baseline_change_attribution_or_publication_performed",
        })
    ):
        raise SystemExit("implementation readiness identity or no-read boundary differs")
    receipt = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-IMPLEMENTATION-PUBLICATION-GATE",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_public_recovery_controls_before_eof_reads",
        "bindings": {"implementation_readiness_sha256": sha256(READINESS_REF), **{name: sha256(ref) for name, ref in refs.items()}},
        "github_actions": {
            "workflow": "Validate project controls",
            "run_id": args.run_id,
            "url": args.run_url,
            "head_sha": args.commit_sha,
            "conclusion": "success",
        },
        "assertions": {
            "real_eof_content_read": False,
            "network_request_performed": False,
            "credential_value_read_or_recorded": False,
            "external_custody_mutated": False,
            "verification_receipt_created": False,
            "orbit_application_performed": False,
            "dem_or_radar_pixel_action_performed": False,
            "baseline_change_attribution_or_publication_performed": False,
        },
        "next_gate": "activate exact recovery controls and run one final no-content preflight",
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
