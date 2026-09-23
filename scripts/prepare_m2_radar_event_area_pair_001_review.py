"""Freeze a local, zero-decision event-area pair review packet."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-event-area-pair-001"
PROPOSAL_REF = f"contracts/milestone-002-radar-event-area-pair-001-proposal.json"
REVIEW_REF = "docs/M2_RADAR_EVENT_AREA_PAIR_001_REVIEW.md"
BUNDLE_REF = f"reviews/{PREFIX}/review-bundle.json"
CONTRACT_REF = f"reviews/{PREFIX}/review-contract.json"
BLANK_REF = f"reviews/{PREFIX}/blank-response.json"
READINESS_REF = f"records/readiness/{PREFIX}-review-readiness.json"


def sha(ref):
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def write_new(ref, obj):
    path = ROOT / ref
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(obj, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def main():
    proposal = json.loads((ROOT / PROPOSAL_REF).read_text(encoding="utf-8"))
    if proposal["status"] != "local_zero_decision_not_authorized" or proposal["human_decision_count"] != 0:
        raise ValueError("Proposal is not a zero-decision local packet")
    for item in proposal["input_bindings"]:
        if sha(item["ref"]) != item["sha256"]:
            raise ValueError(f"Frozen input changed: {item['ref']}")
    source = json.loads((ROOT / "records/source-gates/m2-radar-event-pair-seven-dem-source-assessment-001.json").read_text(encoding="utf-8"))
    if source["authority"]["mode"] != "not_granted" or source["authority"]["authorized_actions"]:
        raise ValueError("Seven-tile source authority changed")
    assets = source["sources"][0]["exact_assets"]
    if [item["item_id"] for item in assets] != proposal["seven_exact_candidate_item_ids_in_fixed_order"]:
        raise ValueError("Exact seven-tile order differs")
    if sum(item["observed_head_content_length_bytes"] for item in assets) != 273055703:
        raise ValueError("Seven-tile metadata byte estimate differs")
    triage = json.loads((ROOT / "records/observations/m2-radar-event-pair-catalog-triage-001.json").read_text(encoding="utf-8"))
    pair = next(row for row in triage["pair_results"] if row["before_source_id"] == "M1-SRC-002")
    if pair["after_source_id"] != "M1-SRC-005" or any(pair["aoi_catalog_pair_overlap_percent"][aoi] != 100.0 for aoi in ("AOI-SOURCE", "AOI-UPPER-CORRIDOR")):
        raise ValueError("Event-pair catalog geometry differs")
    review_text = (ROOT / REVIEW_REF).read_text(encoding="utf-8")
    if "Local, unpublished proposal" not in review_text or "zero authorized next actions" not in review_text:
        raise ValueError("Readable review omits the local no-authority boundary")

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    artifacts = [
        {"path": PROPOSAL_REF, "sha256": sha(PROPOSAL_REF), "role": "proposal"},
        {"path": REVIEW_REF, "sha256": sha(REVIEW_REF), "role": "human_readable_review"},
    ]
    artifacts.extend({"path": item["ref"], "sha256": item["sha256"], "role": "frozen_input"} for item in proposal["input_bindings"])
    bundle = {
        "schema_version": "1.0",
        "bundle_id": "NEPAL-M2-RADAR-EVENT-AREA-PAIR-001-REVIEW-BUNDLE",
        "prepared_at_utc": now,
        "status": "local_zero_decision_one_owner_decision_required",
        "human_decision_count": 0,
        "artifacts": artifacts,
        "decision_requested": {
            "decision_id": "D-M2-RADAR-EVENT-AREA-PAIR-001",
            "question": "Approve, revise, or defer one bounded seven-tile and 002/005 QA route envelope, conditional on exact public CI gates?",
            "choices": ["approve", "revise", "defer"],
            "response_open": True,
            "approval_effective_only_after": "Exact packet and approval are published to the public default branch and public CI passes; later implementation and execution gates must also pass before real access.",
        },
        "authority_boundary": {
            "publication_authorized": False,
            "new_dem_acquisition_authorized": False,
            "scientific_method_amended": False,
            "arcgis_project_processing_authorized": False,
            "baseline_or_change_analysis_authorized": False,
        },
    }
    write_new(BUNDLE_REF, bundle)
    bundle_sha = sha(BUNDLE_REF)
    contract = {
        "schema_version": "1.0",
        "contract_id": "NEPAL-M2-RADAR-EVENT-AREA-PAIR-001-REVIEW-CONTRACT",
        "review_bundle": {"ref": BUNDLE_REF, "sha256": bundle_sha},
        "proposal": {"ref": PROPOSAL_REF, "sha256": sha(PROPOSAL_REF)},
        "response_requirements": {"exact_hashes_required": True, "explicit_decision_required": True, "attestation_required": True, "one_combined_authority_envelope": True},
        "workflow_authority": {"local_preparation_complete": True, "response_open": True, "publication_or_execution_authorized_before_decision": False},
    }
    write_new(CONTRACT_REF, contract)
    blank = {
        "schema_version": "1.0",
        "decision_id": "D-M2-RADAR-EVENT-AREA-PAIR-001",
        "completed": False,
        "human_decision_count": 0,
        "review_bundle_sha256": bundle_sha,
        "proposal_sha256": sha(PROPOSAL_REF),
        "decision": None,
        "attestation": None,
    }
    write_new(BLANK_REF, blank)
    readiness = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-EVENT-AREA-PAIR-001-REVIEW-READINESS",
        "checked_at_utc": now,
        "status": "local_packet_ready_for_one_owner_decision_not_public",
        "bindings": {"proposal_sha256": sha(PROPOSAL_REF), "review_bundle_sha256": bundle_sha, "review_contract_sha256": sha(CONTRACT_REF), "blank_response_sha256": sha(BLANK_REF)},
        "checks": {"exact_input_hashes_match": True, "seven_candidate_id_and_order_match": True, "source_gate_authorized_next_actions": [], "human_decision_count": 0, "public_ci_not_yet_run": True},
        "released_now": {"packet_publication": False, "new_dem_acquisition": False, "arcgis_project_processing": False, "baseline_or_change_analysis": False, "scientific_publication": False},
    }
    write_new(READINESS_REF, readiness)
    print(f"proposal_sha256={sha(PROPOSAL_REF)}")
    print(f"review_bundle_sha256={bundle_sha}")


if __name__ == "__main__":
    main()
