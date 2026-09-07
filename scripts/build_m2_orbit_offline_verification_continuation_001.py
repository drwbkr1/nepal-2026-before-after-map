#!/usr/bin/env python3
"""Build the exact four-source offline orbit verification candidate after continuation success."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_REF = "contracts/m2-orbit-offline-verification.json"
OUTPUT_REF = "contracts/m2-orbit-offline-verification-continuation-001.json"
INTAKE_REF = "contracts/m2-orbit-intake.json"
ORIGINAL_APPROVAL_REF = "records/source-gates/m2-orbit-amendment-approval.json"
OSV_APPROVAL_REF = "records/source-gates/m2-orbit-osv-precision-amendment-001-approval.json"
CONTINUATION_APPROVAL_REF = "records/source-gates/m2-orbit-continuation-001-approval.json"
SUCCESS_REF = "records/acquisition/m2-orbit-continuation-001-success-reconciliation.json"
PROJECT_RECONCILIATION_REF = "records/readiness/m2-orbit-continuation-001-terminal-project-reconciliation.json"
SOURCE_IDS = ["M2-ORB-001", "M2-ORB-002", "M2-ORB-003", "M2-ORB-004"]


def load(ref: str) -> dict[str, Any]:
    value = json.loads((ROOT / ref).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {ref}")
    return value


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--created-at-utc", required=True)
    args = parser.parse_args()
    if not args.created_at_utc.endswith("Z") or (ROOT / OUTPUT_REF).exists():
        raise SystemExit("candidate output collision or invalid time")
    active = load(ACTIVE_REF)
    intake = load(INTAKE_REF)
    success = load(SUCCESS_REF)
    reconciliation = load(PROJECT_RECONCILIATION_REF)
    if (
        active.get("status") != "active_gate_pending_continuation_compatibility_public_ci"
        or active.get("bindings", {}).get("active_intake_sha256_current") != sha256(INTAKE_REF)
        or active.get("extensions", {}).get("continuation_001", {}).get("success_sha256") != sha256(SUCCESS_REF)
        or success.get("status") != "pass_all_three_exact_remaining_orbits_promoted_input_verified"
        or reconciliation.get("status") != "pass_all_four_orbits_promoted_offline_verifier_public_ci_pending"
        or reconciliation.get("observations", {}).get("source_ids") != SOURCE_IDS
        or reconciliation.get("bindings", {}).get("verification_sha256_after") != sha256(ACTIVE_REF)
        or intake.get("extensions", {}).get("current_orbit_state_counts") != {"authorized": 0, "failed": 0, "promoted": 4}
    ):
        raise SystemExit("post-continuation verification controls differ")
    requirements = active.get("asset_requirements", [])
    if [item.get("source_id") for item in requirements] != SOURCE_IDS:
        raise SystemExit("verification requirement source order differs")

    candidate = copy.deepcopy(active)
    candidate.update({
        "contract_id": "NEPAL-M2-ORBIT-OFFLINE-VERIFICATION-CONTINUATION-001",
        "contract_version": "2.0",
        "status": "candidate_public_ci_pending",
        "created_at_utc": args.created_at_utc,
    })
    candidate.pop("created_at", None)
    candidate["authority"].update({
        "mode": "combined_exact_orbit_and_two_prospective_osv_approvals",
        "base_orbit_approval_ref": ORIGINAL_APPROVAL_REF,
        "base_orbit_approval_sha256": sha256(ORIGINAL_APPROVAL_REF),
        "m2_orb_001_endpoint_approval_ref": OSV_APPROVAL_REF,
        "m2_orb_001_endpoint_approval_sha256": sha256(OSV_APPROVAL_REF),
        "remaining_sources_endpoint_approval_ref": CONTINUATION_APPROVAL_REF,
        "remaining_sources_endpoint_approval_sha256": sha256(CONTINUATION_APPROVAL_REF),
        "maximum_endpoint_tolerance_seconds": 1.0,
        "offline_verification_attempts_per_source": 1,
    })
    candidate["bindings"].update({
        "base_active_verification_ref": ACTIVE_REF,
        "base_active_verification_sha256": sha256(ACTIVE_REF),
        "active_intake_sha256_current": sha256(INTAKE_REF),
        "continuation_success_ref": SUCCESS_REF,
        "continuation_success_sha256": sha256(SUCCESS_REF),
        "continuation_project_reconciliation_ref": PROJECT_RECONCILIATION_REF,
        "continuation_project_reconciliation_sha256": sha256(PROJECT_RECONCILIATION_REF),
    })
    for requirement in candidate["asset_requirements"]:
        requirement["maximum_osv_endpoint_tolerance_seconds"] = 1.0
        requirement["endpoint_rule_authority_ref"] = OSV_APPROVAL_REF if requirement["source_id"] == "M2-ORB-001" else CONTINUATION_APPROVAL_REF
    candidate["verification_sequence"] = [
        "recompute and compare exact byte length",
        "verify provider MD5 and BLAKE3 values and compute local SHA-256",
        "parse the EOF as XML without network access, DTDs, or entity declarations",
        "verify mission S1D, file type AUX_RESORB, exact validity interval, and exact source identity",
        "verify the OSV list is nonempty, count-matched, strictly ordered, unique, finite, and uses exact declared units",
        "require OSV endpoints within the prospectively approved maximum one-second rule for the exact source",
        "verify the complete bound Sentinel acquisition window lies within validity with required temporal margins",
        "inventory the custody directory before and after and require no mutation",
        "write one append-only public verification receipt per exact promoted source and stop on the first failure",
    ]
    candidate["receipt_compatibility"] = {
        "M2-ORB-001": {
            "attempt_kind": "osv_precision_local_no_replace_promotion",
            "evidence_ref": "records/acquisition/m2-orbit-osv-precision-amendment-001-local-validation.json",
            "required_status": "pass_exact_m2_orb_001_input_promoted_no_replace",
        },
        "M2-ORB-002": {"attempt_kind": "orbit_continuation_001", "required_event": "orbit_continuation_001_succeeded"},
        "M2-ORB-003": {"attempt_kind": "orbit_continuation_001", "required_event": "orbit_continuation_001_succeeded"},
        "M2-ORB-004": {"attempt_kind": "orbit_continuation_001", "required_event": "orbit_continuation_001_succeeded"},
    }
    candidate["activation_boundary"] = {
        "public_default_branch_ci_required": True,
        "final_no_content_preflight_required": True,
        "real_eof_reads_before_activation_authorized": False,
        "network_requests_authorized": False,
        "custody_mutation_authorized": False,
        "orbit_application_authorized": False,
    }
    candidate["extensions"]["continuation_001"].update({
        "candidate_built": True,
        "offline_file_reads_started": False,
        "next_gate": "publish exact verifier implementation and require successful public default-branch CI",
    })
    with (ROOT / OUTPUT_REF).open("xb") as stream:
        stream.write((json.dumps(candidate, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    print(json.dumps({"status": candidate["status"], "output": OUTPUT_REF}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
