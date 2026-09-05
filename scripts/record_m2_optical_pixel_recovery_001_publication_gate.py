#!/usr/bin/env python3
"""Record passing public CI before optical pixel recovery-001 preflight."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from m2_optical_pixel_recovery_stage_gate import (
    ACTIVATION_REF,
    APPROVAL_REF,
    CONTRACT_REF,
    READINESS_REF,
    REAL_001_RECONCILIATION_REF,
    ROOT,
    sha256,
)


OUTPUT = ROOT / "records/readiness/m2-optical-pixel-recovery-001-publication-gate.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verified-at-utc", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--run-url", required=True)
    args = parser.parse_args()
    if OUTPUT.exists():
        raise SystemExit("refusing optical pixel recovery publication-gate collision")
    if len(args.commit_sha) != 40 or not args.run_url.endswith(str(args.run_id)):
        raise SystemExit("public CI identity differs")
    record = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-OPTICAL-PIXEL-RECOVERY-001-PUBLICATION-GATE",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_public_controls_verified_before_optical_pixel_recovery_001",
        "github_actions": {
            "run_id": args.run_id,
            "run_url": args.run_url,
            "head_sha": args.commit_sha,
            "conclusion": "success",
        },
        "bindings": {
            "approval_sha256": sha256(APPROVAL_REF),
            "activation_sha256": sha256(ACTIVATION_REF),
            "real_001_reconciliation_sha256": sha256(REAL_001_RECONCILIATION_REF),
            "contract_sha256": sha256(CONTRACT_REF),
            "implementation_readiness_sha256": sha256(READINESS_REF),
        },
        "assertions": {
            "real_001_reused_or_retried": False,
            "recovery_attempt_started": False,
            "real_product_pixels_examined_during_publication": False,
            "thresholds_sources_or_aois_changed": False,
        },
        "next_gate": "pass the final exact no-pixel recovery preflight before the single recovery-001 invocation",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"status": record["status"], "output": OUTPUT.relative_to(ROOT).as_posix()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
