#!/usr/bin/env python3
"""Record successful public CI for the exact blank OSV precision review packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "records/readiness/m2-orbit-osv-precision-amendment-001-review-publication-gate.json"
FILES = {
    "terminal_reconciliation_sha256": ROOT / "records/readiness/m2-orbit-recovery-003-terminal-reconciliation.json",
    "source_evidence_sha256": ROOT / "records/source-gates/m2-orbit-osv-time-format-evidence.json",
    "proposal_sha256": ROOT / "contracts/milestone-002-orbit-osv-precision-amendment-001-proposal.json",
    "review_preflight_sha256": ROOT / "records/readiness/m2-orbit-osv-precision-amendment-001-review-preflight.json",
    "review_surface_sha256": ROOT / "docs/M2_ORBIT_OSV_PRECISION_AMENDMENT_001_REVIEW.md",
    "rendered_surface_sha256": ROOT / "docs/assets/m2-orbit-osv-precision-amendment-001-review.png",
    "surface_receipt_sha256": ROOT / "records/surface-receipts/m2-orbit-osv-precision-amendment-001-review.json",
    "review_bundle_sha256": ROOT / "reviews/m2-orbit-osv-precision-amendment-001/review-bundle.json",
    "review_contract_sha256": ROOT / "reviews/m2-orbit-osv-precision-amendment-001/review-contract.json",
    "blank_response_sha256": ROOT / "reviews/m2-orbit-osv-precision-amendment-001/blank-response.json",
    "review_readiness_sha256": ROOT / "records/readiness/m2-orbit-osv-precision-amendment-001-review-readiness.json",
    "failed_publication_attempt_sha256": ROOT / "records/readiness/m2-orbit-osv-precision-amendment-001-review-publication-attempt-001-failure.json",
    "portability_correction_sha256": ROOT / "records/readiness/m2-orbit-osv-precision-amendment-001-review-publication-portability-correction-001.json",
}
EXPECTED_PROPOSAL_SHA256 = "0eb9e60f3cd26365cc447eb007e28186470a778928730b055b633c5e88d344e4"
EXPECTED_BUNDLE_SHA256 = "71b3eea557cbd027fecec299b8661ce555a8fa993bccd8ffaea8f525d79d01a7"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, object]:
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
    if OUTPUT.exists():
        raise SystemExit("refusing publication-gate output collision")
    if not args.verified_at_utc.endswith("Z"):
        raise SystemExit("verified time must be UTC")
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
    if bindings["proposal_sha256"] != EXPECTED_PROPOSAL_SHA256 or bindings["review_bundle_sha256"] != EXPECTED_BUNDLE_SHA256:
        raise SystemExit("exact review packet identity drift")
    blank = load(FILES["blank_response_sha256"])
    readiness = load(FILES["review_readiness_sha256"])
    correction = load(FILES["portability_correction_sha256"])
    if (
        blank.get("completed") is not False
        or blank.get("reviewer", {}).get("attestation") is not False
        or readiness.get("review", {}).get("human_decision_count") != 0
        or readiness.get("assertions", {}).get("amendment_authorized") is not False
        or correction.get("status") != "pass_portable_review_test_without_render_dependency_public_ci_pending"
    ):
        raise SystemExit("review packet is not in its exact blank zero-authority state")
    payload = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-OSV-PRECISION-AMENDMENT-001-REVIEW-PUBLICATION-GATE-001",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_exact_blank_review_packet_public_ci",
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
            "failed_prior_run_preserved": True,
            "human_decision_count": 0,
            "amendment_authorized": False,
            "credential_values_read_or_recorded": False,
            "network_requests_performed_by_this_record": False,
            "payload_mutated": False,
            "staged_file_promoted": False,
            "other_orbit_source_requested": False,
            "scientific_result_established": False,
        },
        "next_gate": f"owner decision on bundle SHA-256 {EXPECTED_BUNDLE_SHA256} and proposal SHA-256 {EXPECTED_PROPOSAL_SHA256}",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"status": payload["status"], "output": str(OUTPUT.relative_to(ROOT)).replace("\\", "/")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
