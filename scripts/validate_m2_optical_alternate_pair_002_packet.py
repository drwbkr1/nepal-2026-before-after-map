#!/usr/bin/env python3
"""Review-only optical pair-002 packet audit; never opens external custody."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "reviews/m2-optical-alternate-map-pair-002/review-bundle.json"
RECEIPT = ROOT / "records/readiness/m2-optical-alternate-map-pair-002-local-packet-audit.json"
SCAN_DIRS = ("records", "contracts", "docs", "scripts", "tests", "reviews")
SCAN_SUFFIXES = {".json", ".md", ".py"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_bound(ref: str, expected: str) -> dict | str:
    path = (ROOT / ref).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file() or digest(path) != expected:
        raise RuntimeError("packet_binding_mismatch")
    if path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    return path.read_text(encoding="utf-8")


def audit() -> dict:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    if bundle.get("status") != "local_zero_decision_not_approved_not_published":
        raise RuntimeError("packet_status_changed")
    bound = {kind: read_bound(bundle[f"{kind}_ref"], bundle[f"{kind}_sha256"])
             for kind in ("review", "proposal", "method_risk", "source_eligibility",
                          "corrected_metadata_screen")}
    old = bundle["superseded_unapproved_bundle"]
    read_bound(old["ref"], old["sha256"])
    proposal = bound["proposal"]
    gate = bound["source_eligibility"]
    risk = bound["method_risk"]
    screen = bound["corrected_metadata_screen"]
    if not isinstance(proposal, dict) or not isinstance(gate, dict) or not isinstance(risk, dict) or not isinstance(screen, dict):
        raise RuntimeError("packet_document_shape_changed")
    if (proposal.get("status") != "local_zero_decision_proposal_not_approved"
            or proposal["authority"].get("owner_approval_received") is not False
            or bundle["decision_state"].get("owner_approval_received") is not False
            or gate["authority"].get("mode") != "not_granted"
            or gate["authority"].get("authorized_actions") != []
            or gate["decision"].get("status") != "ready"):
        raise RuntimeError("packet_or_source_authority_drift")
    if (proposal["source_evidence"]["source_eligibility_assessment_sha256"] != bundle["source_eligibility_sha256"]
            or proposal["source_evidence"]["method_risk_sha256"] != bundle["method_risk_sha256"]
            or proposal["exact_pair"]["before"]["provider_product_id"] != "35b149d6-cdde-4959-8ff4-d28f37bf67bb"
            or proposal["exact_pair"]["after"]["provider_product_id"] != "d6d898f4-2337-487d-afff-943df794c3e6"
            or proposal["exact_pair"]["after"]["proposed_new_source_id"] != "M2-OPT-003"
            or proposal["exact_pair"]["processing_baseline_from_names"] != ["05.12", "05.13"]
            or proposal["spatial_scope"]["target_crs_wkid"] != 32645
            or proposal["spatial_scope"]["target_cell_size_m"] != 20
            or proposal["spatial_scope"]["target_aoi_ids"] != ["AOI-SOURCE", "AOI-UPPER-CORRIDOR"]):
        raise RuntimeError("packet_exact_source_or_grid_drift")
    if (risk["current_code_constraint"]["reader_requires_baseline_0512_for_both_products"] is not True
            or screen["cohort"]["products_in_two_prior_blocked_pairs"] != 4
            or proposal["execution_invariants"]["new_acquisition_requests_maximum"] != 1
            or proposal["execution_invariants"]["new_pair_pixel_attempts_maximum"] != 1
            or any(proposal["execution_invariants"][key] is not False for key in
                   ("old_pb0512_reader_or_contract_mutation", "cross_baseline_radiometric_harmonization_or_change_metric",
                    "new_source_or_date_substitution", "old_attempt_reuse_resume_retry_or_mutation",
                    "automatic_retry", "source_or_derived_pixel_publication"))):
        raise RuntimeError("packet_method_or_stop_rule_drift")
    identities = list(proposal["fixed_new_attempt_identities"].values())
    identities = [value for value in identities if isinstance(value, str) and value.startswith("m2-optical-alternate-map-pair-002-")]
    if len(identities) != 4 or len(set(identities)) != 4:
        raise RuntimeError("packet_attempt_identity_duplicate_or_missing")
    proposal_path = (ROOT / bundle["proposal_ref"]).resolve()
    collisions = []
    for directory in SCAN_DIRS:
        for path in (ROOT / directory).rglob("*"):
            if path.resolve() == proposal_path or not path.is_file() or path.suffix.lower() not in SCAN_SUFFIXES:
                continue
            if path.stat().st_size > 3_000_000:
                continue
            content = path.read_text(encoding="utf-8", errors="replace")
            if any(identity in content for identity in identities):
                collisions.append(path.relative_to(ROOT).as_posix())
    if collisions:
        raise RuntimeError("packet_attempt_identity_repository_collision")
    return {
        "schema_version": "1.0",
        "status": "pass_repo_only_packet_audit_no_execution_authority",
        "bundle_ref": BUNDLE.relative_to(ROOT).as_posix(),
        "bundle_sha256": digest(BUNDLE),
        "proposal_sha256": digest(proposal_path),
        "validator_ref": Path(__file__).relative_to(ROOT).as_posix(),
        "validator_sha256": digest(Path(__file__)),
        "bound_files_verified": 6,
        "exact_new_attempt_ids_unique": True,
        "repo_text_collision_count": 0,
        "external_custody_collision_checked": False,
        "protected_pixels_read": False,
        "new_source_adopted_or_acquired": False,
        "owner_approval_received": False,
        "repository_published": False,
        "scientific_result_established": False,
    }


def main() -> None:
    result = audit()
    with RECEIPT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"status": result["status"], "bundle_sha256": result["bundle_sha256"]}))


if __name__ == "__main__":
    main()
