#!/usr/bin/env python3
"""Build the approved one-second M2-ORB-001 offline-verification contract."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_REF = "contracts/m2-orbit-offline-verification.json"
BASE_SHA256 = "bac1154aebf34858fd82d9f42934a5a2d7bfd21a25917df1355f0f9f68682303"
APPROVAL_REF = "records/source-gates/m2-orbit-osv-precision-amendment-001-approval.json"
PROPOSAL_REF = "contracts/milestone-002-orbit-osv-precision-amendment-001-proposal.json"
OUTPUT_REF = "contracts/m2-orbit-offline-verification-osv-precision-amendment-001.json"
SOURCE_ID = "M2-ORB-001"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--created-at-utc", required=True)
    args = parser.parse_args()
    if not args.created_at_utc.endswith("Z"):
        raise SystemExit("created time must be UTC")
    base_path = ROOT / BASE_REF
    approval_path = ROOT / APPROVAL_REF
    proposal_path = ROOT / PROPOSAL_REF
    output_path = ROOT / OUTPUT_REF
    if output_path.exists():
        raise SystemExit("refusing amended-contract output collision")
    if sha256(base_path) != BASE_SHA256:
        raise SystemExit("base offline-verification contract identity drift")
    base = load(base_path)
    approval = load(approval_path)
    proposal = load(proposal_path)
    if (
        approval.get("status") != "approved_exact_one_second_endpoint_rule_and_one_local_validation"
        or approval.get("authorized_amendment", {}).get("source_id") != SOURCE_ID
        or approval.get("authorized_amendment", {}).get("maximum_osv_endpoint_tolerance_seconds") != 1.0
        or approval.get("authorized_amendment", {}).get("maximum_new_download_requests") != 0
        or approval.get("authorized_amendment", {}).get("maximum_local_validation_attempts") != 1
        or proposal.get("proposed_amendment", {}).get("maximum_osv_endpoint_tolerance_seconds") != 1.0
    ):
        raise SystemExit("exact OSV precision approval is absent or drifted")
    matches = [item for item in base.get("asset_requirements", []) if item.get("source_id") == SOURCE_ID]
    if len(matches) != 1:
        raise SystemExit("base M2-ORB-001 requirement missing or ambiguous")
    requirement = copy.deepcopy(matches[0])
    requirement["maximum_osv_endpoint_tolerance_seconds"] = 1.0
    contract = {
        "schema_version": "1.0",
        "contract_id": "NEPAL-M2-ORBIT-OFFLINE-VERIFICATION-OSV-PRECISION-AMENDMENT-001",
        "status": "active_exact_m2_orb_001_local_validation_pending_public_ci",
        "created_at_utc": args.created_at_utc,
        "authority": {
            "mode": "inherited_exact_osv_precision_amendment_approval",
            "authority_ref": APPROVAL_REF,
            "authority_sha256": sha256(approval_path),
            "maximum_endpoint_tolerance_seconds": 1.0,
            "maximum_local_validation_attempts": 1,
            "maximum_network_requests": 0,
            "conditional_no_replace_promotion_authorized": True,
            "orbit_application_authorized_by_this_contract": False,
            "radar_pixel_processing_authorized_by_this_contract": False,
            "this_contract_creates_authority": False,
        },
        "bindings": {
            "base_offline_verification_ref": BASE_REF,
            "base_offline_verification_sha256": BASE_SHA256,
            "proposal_ref": PROPOSAL_REF,
            "proposal_sha256": sha256(proposal_path),
            "approval_ref": APPROVAL_REF,
            "approval_sha256": sha256(approval_path),
            "terminal_recovery_outcome_ref": "records/acquisition/m2-orbit-recovery-003-outcome-reconciliation.json",
            "terminal_recovery_outcome_sha256": sha256(ROOT / "records/acquisition/m2-orbit-recovery-003-outcome-reconciliation.json"),
        },
        "asset_requirements": [requirement],
        "endpoint_rule": {
            "maximum_tolerance_seconds": 1.0,
            "predicate": "first_osv_utc <= validity_start_utc + 1 second and last_osv_utc >= validity_stop_utc - 1 second",
            "interpretation": "local inference from representational precision; not a quoted provider tolerance",
            "all_other_checks_unchanged": True,
        },
        "verification_sequence": [
            "recompute exact byte length, local SHA-256, provider MD5, and provider BLAKE3",
            "parse safe XML without DTD or entity declarations",
            "verify exact identity, S1D mission, AUX_RESORB type, and header validity values",
            "verify positive declared OSV count, strictly increasing unique times, finite vectors, and exact units",
            "apply only the one-second endpoint-consistency predicate",
            "verify exact scene binding and minimum 6,350-second scene margin",
            "conditionally promote exact bytes atomically without replacement and retain the failed-attempt evidence"
        ],
        "single_real_action": {
            "maximum_local_validation_attempts": 1,
            "maximum_network_requests": 0,
            "automatic_retry_authorized": False,
            "source_id": SOURCE_ID,
            "preserved_staged_sha256": approval["authorized_amendment"]["preserved_staged_sha256"],
            "preserved_staged_size_bytes": approval["authorized_amendment"]["preserved_staged_size_bytes"],
        },
        "claim_boundary": {
            "passing_establishes": "exact M2-ORB-001 input identity and structural fitness under the approved local endpoint rule",
            "does_not_establish": [
                "precise-orbit equivalence",
                "orbit application",
                "geolocation or registration accuracy",
                "vertical-datum or radar-pixel fitness",
                "baseline quality, event change, interpretation, attribution, or scientific publication"
            ],
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("xb") as stream:
        stream.write((json.dumps(contract, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"status": "created_exact_one_second_contract", "output": OUTPUT_REF}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
