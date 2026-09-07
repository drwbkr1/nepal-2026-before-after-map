#!/usr/bin/env python3
"""Record successful public CI for the exact blank orbit-verification recovery review."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "records/readiness/m2-orbit-offline-verification-recovery-001-review-publication-gate.json"
PROPOSAL_SHA256 = "0be64071cfe718ca758155ff0422cfee48af342c8a560528746adc653e6a2fcf"
BUNDLE_SHA256 = "d2f0f75f40614c56bc0e62c6eecb1588f7504f50927448192673e6e403b5933f"
FILES = {
    "terminal_reconciliation_sha256": ROOT / "records/readiness/m2-orbit-offline-verification-001-terminal-reconciliation.json",
    "proposal_sha256": ROOT / "contracts/milestone-002-orbit-offline-verification-recovery-001-proposal.json",
    "review_preflight_sha256": ROOT / "records/readiness/m2-orbit-offline-verification-recovery-001-review-preflight.json",
    "review_instructions_sha256": ROOT / "docs/M2_ORBIT_OFFLINE_VERIFICATION_RECOVERY_001_REVIEW.md",
    "rendered_surface_sha256": ROOT / "docs/assets/m2-orbit-offline-verification-recovery-001-review.png",
    "surface_receipt_sha256": ROOT / "records/surface-receipts/m2-orbit-offline-verification-recovery-001-review.json",
    "review_bundle_sha256": ROOT / "reviews/m2-orbit-offline-verification-recovery-001/review-bundle.json",
    "review_contract_sha256": ROOT / "reviews/m2-orbit-offline-verification-recovery-001/review-contract.json",
    "blank_response_sha256": ROOT / "reviews/m2-orbit-offline-verification-recovery-001/blank-response.json",
    "review_readiness_sha256": ROOT / "records/readiness/m2-orbit-offline-verification-recovery-001-review-readiness.json",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return value


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
    if head != args.commit_sha or origin != args.commit_sha:
        raise SystemExit("publication commit is not current HEAD and origin/main")
    expected_url = f"https://github.com/drwbkr1/nepal-2026-before-after-map/actions/runs/{args.run_id}"
    if args.run_id <= 0 or args.run_url != expected_url:
        raise SystemExit("invalid GitHub Actions identity")
    missing = [str(path.relative_to(ROOT)) for path in FILES.values() if not path.is_file()]
    if missing:
        raise SystemExit("missing review files: " + ", ".join(missing))
    bindings = {key: sha256(path) for key, path in FILES.items()}
    if bindings["proposal_sha256"] != PROPOSAL_SHA256 or bindings["review_bundle_sha256"] != BUNDLE_SHA256:
        raise SystemExit("exact review packet identity drift")
    terminal = load(FILES["terminal_reconciliation_sha256"])
    blank = load(FILES["blank_response_sha256"])
    readiness = load(FILES["review_readiness_sha256"])
    if (
        terminal.get("status")
        != "terminal_indeterminate_m2_orb_001_evaluated_receipt_not_persisted_no_retry_released"
        or terminal.get("assertions", {}).get("m2_orb_001_eof_content_read") is not True
        or terminal.get("assertions", {}).get("evaluation_result_durably_persisted") is not False
        or terminal.get("assertions", {}).get("later_source_eof_content_read") is not False
        or blank.get("completed") is not False
        or blank.get("reviewer", {}).get("attestation") is not False
        or blank.get("responses", [{}])[0].get("decision") is not None
        or readiness.get("review", {}).get("human_decision_count") != 0
        or readiness.get("assertions", {}).get("recovery_authorized") is not False
    ):
        raise SystemExit("review packet is not in its exact terminal-history and blank zero-authority state")
    payload = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-REVIEW-PUBLICATION-GATE",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_exact_blank_recovery_packet_public_ci_owner_review_ready",
        "bindings": bindings,
        "github_actions": {
            "workflow": "Validate project controls",
            "run_id": args.run_id,
            "url": args.run_url,
            "head_sha": args.commit_sha,
            "conclusion": "success",
        },
        "assertions": {
            "remote_ref_verified": True,
            "public_ci_passed": True,
            "human_decision_count": 0,
            "recovery_authorized": False,
            "new_eof_content_read": False,
            "remaining_source_eof_content_read": False,
            "network_or_credential_action_performed": False,
            "external_custody_mutated": False,
            "orbit_application_performed": False,
            "dem_or_radar_pixel_action_performed": False,
            "baseline_change_attribution_or_publication_performed": False,
        },
        "next_gate": (
            f"owner decision on bundle SHA-256 {BUNDLE_SHA256} and proposal SHA-256 {PROPOSAL_SHA256}"
        ),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"status": payload["status"], "output": str(OUTPUT.relative_to(ROOT)).replace("\\", "/")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
