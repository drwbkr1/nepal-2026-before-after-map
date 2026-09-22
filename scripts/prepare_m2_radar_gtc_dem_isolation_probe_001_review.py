#!/usr/bin/env python3
"""Prepare a local zero-decision review for one diagnostic-only GTC probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-gtc-dem-isolation-probe-001"
BASE_COMMIT = "8bfa7635ecfc2f6e1842babca2c2aab76693f11e"
PROPOSAL_REF = "contracts/milestone-002-radar-gtc-dem-isolation-probe-001-proposal.json"
DOC_REF = "docs/M2_RADAR_GTC_DEM_ISOLATION_PROBE_001_REVIEW.md"
BUNDLE_REF = f"reviews/{PREFIX}/review-bundle.json"
CONTRACT_REF = f"reviews/{PREFIX}/review-contract.json"
BLANK_REF = f"reviews/{PREFIX}/blank-response.json"
READINESS_REF = f"records/readiness/{PREFIX}-review-readiness.json"
INPUT_REFS = (
    "AGENTS.md",
    "records/processing/m2-radar-esri-sequence-recovery-005-terminal-reconciliation.json",
    "records/processing/m2-radar-gtc-input-compatibility-diagnostic-001-terminal-reconciliation.json",
    "records/observations/m2-radar-gtc-public-six-source-coverage-audit-002.json",
    "config/qa/m2-radar-esri-sequence-recovery-005-contract.json",
)


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def write_json(ref: str, value: dict) -> None:
    path = ROOT / ref
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepared-at-utc", required=True)
    args = parser.parse_args()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if head != BASE_COMMIT:
        raise SystemExit("base commit changed; re-evaluate proposal inputs")
    if any((ROOT / ref).exists() for ref in (PROPOSAL_REF, DOC_REF, BUNDLE_REF, CONTRACT_REF, BLANK_REF, READINESS_REF)):
        raise SystemExit("review output collision")
    terminal = json.loads((ROOT / INPUT_REFS[1]).read_text(encoding="utf-8"))
    diagnostic = json.loads((ROOT / INPUT_REFS[2]).read_text(encoding="utf-8"))
    if not terminal.get("attempt_consumed") or not diagnostic.get("attempt_consumed"):
        raise SystemExit("terminal attempts not proven consumed")
    if terminal["execution_result"]["stopped_tool"] != "ApplyGeometricTerrainCorrection_gamma":
        raise SystemExit("terminal stop differs")
    if len(diagnostic.get("candidate_observations", [])) != 6:
        raise SystemExit("six-candidate diagnostic differs")

    bindings = [{"ref": ref, "sha256": sha256(ref)} for ref in INPUT_REFS]
    proposal = {
        "schema_version": "1.0",
        "proposal_id": "NEPAL-M2-RADAR-GTC-DEM-ISOLATION-PROBE-001",
        "prepared_at_utc": args.prepared_at_utc,
        "status": "proposed_zero_decision_not_authorized",
        "human_decision_count": 0,
        "base_commit": BASE_COMMIT,
        "input_bindings": bindings,
        "problem": "Recovery-005 completed the approved REFINED_LEE step but GTC with the approved DEM failed with ArcGIS ERROR 000425. A later read-only diagnostic established ArcGIS catalog recognition only. All six radar catalog footprints extend beyond the four approved DEM tile boxes; this is not actual valid-pixel coverage or proof of failure cause.",
        "question": "Does the exact preserved M1-SRC-001 despeckled gamma input complete one GTC call when the DEM argument is omitted?",
        "official_guidance": {
            "url": "https://doc.esri.com/en/arcgis-pro/latest/tool-reference/image-analyst/apply-geometric-terrain-correction.html",
            "checked_at_utc": args.prepared_at_utc,
            "boundary": "Esri documents metadata tie-point interpolation when no DEM is specified, but directs users to specify a DEM whenever land is in the scene. A no-DEM output here is diagnostic only and must not enter a map, baseline, change analysis, or scientific claim.",
        },
        "proposed_single_authority_envelope": {
            "covers_without_intermediate_reconfirmation": [
                "bounded probe implementation and portable synthetic tests",
                "installed ArcGIS signature and disposable no-content runtime validation",
                "public default-branch implementation and execution CI gates",
                "one final no-content preflight",
                "at most one fresh diagnostic-only GTC process over one exact preserved input",
                "exact terminal reconciliation and sanitized publication",
            ],
            "attempt_id": "radar-gtc-dem-isolation-probe-001-real-001",
            "prospective_attempt_root": "C:\\Projects\\Active\\nepal-2026-before-after-map-data\\r5\\d2",
            "exact_input": "C:\\Projects\\Active\\nepal-2026-before-after-map-data\\r5\\a1\\s\\1\\gamma0_linear_despeckled.crf",
            "output_ref_within_attempt_root": "gtc_no_dem_diagnostic.crf",
            "exact_call": "arcpy.ia.ApplyGeometricTerrainCorrection(gamma_despeckled, 'VV;VH')",
            "save_rule": "If and only if the function returns a Raster, save it once to the declared absent output. Retain any output outside Git as quarantined diagnostic material; do not use or publish its pixels.",
            "preflight_requirements": [
                "verify public evidence hashes and the exact consumed recovery-005 and diagnostic-001 identities",
                "verify the exact input exists without reconstruction or substitution",
                "verify the prospective root and output are absent, path lengths are safe, and at least 60 GiB is free",
                "verify installed ArcGIS version, Image Analyst, and exact two-argument call signature without processing",
                "reserve durable terminal and cleanup receipt identities before any content read",
            ],
            "maximum_processes": 1,
            "maximum_gtc_calls": 1,
            "maximum_output_saves": 1,
            "automatic_retry": False,
            "no_dem_and_no_geoid_argument": True,
            "other_raster_functions_or_geoprocessing_calls": 0,
            "network_or_credential_actions": 0,
            "stop_on_failure": True,
            "possible_observations": {
                "success": "The preserved input can complete GTC in the documented no-DEM tie-point mode; this does not prove DEM coverage caused the earlier failure or produce land-scene scientific data.",
                "failure": "The no-DEM call also failed; this does not isolate a single cause or establish that the DEM is sound.",
            },
        },
        "exclusions": [
            "reuse, resume, retry, or mutation of consumed recovery-005 or diagnostic-001 attempts",
            "DEM acquisition, conversion, substitution, or modification",
            "source, orbit, AOI, CRS, grid, mask, threshold, order, or processing-route substitution",
            "any later source or route, fallback call, or second probe",
            "baseline admission, change analysis, interpretation, attribution, derived-pixel publication, or scientific publication",
            "historical-root-cause or radar-recovery-readiness claim",
        ],
        "does_not_authorize_now": [
            "Git commit, push, public CI, or owner response recording",
            "implementation, ArcPy invocation, project-data or external-custody access",
            "GTC or any other pixel/geoprocessing action",
            "a new real attempt or scientific use",
        ],
    }
    write_json(PROPOSAL_REF, proposal)
    proposal_hash = sha256(PROPOSAL_REF)
    doc = f"""# M2 radar GTC DEM-isolation probe-001 review

This is a **local zero-decision proposal**. Proposal SHA-256: `{proposal_hash}`. No publication, implementation, input access, ArcPy invocation, or probe is authorized by preparing it.

Recovery-005 is terminal after GTC with the approved DEM raised `ERROR 000425`. The read-only diagnostic recognized all six preserved candidates, but did not establish their GTC fitness. A public catalog audit shows incomplete DEM-box overlap for every radar scene; it does not measure valid pixels or prove a cause.

## Proposed single decision

Authorize implementation, synthetic and installed-runtime no-content validation, public CI gates, one final no-content preflight, **at most one** GTC call on the exact preserved M1-SRC-001 despeckled gamma CRF **without a DEM argument**, and sanitized terminal publication, without intermediate reconfirmation. The exact call, input, prospective output root, stop rules, and exclusions are in the proposal.

[Esri's GTC documentation](https://doc.esri.com/en/arcgis-pro/latest/tool-reference/image-analyst/apply-geometric-terrain-correction.html) describes metadata tie-point interpolation without a DEM but advises using a DEM for land scenes. Thus even a completed no-DEM output remains quarantined diagnostic material, never a map or scientific baseline. A success or failure cannot by itself prove the earlier error's historical root cause.

The decision is **approve, revise, or defer** this one bounded diagnostic. It does not approve expanded DEM coverage, source reordering, a follow-on processing attempt, change analysis, attribution, or publication of derived pixels.
"""
    doc_path = ROOT / DOC_REF
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    with doc_path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(doc)
    bundle = {
        "schema_version": "1.0",
        "bundle_id": "NEPAL-M2-RADAR-GTC-DEM-ISOLATION-PROBE-001-REVIEW-BUNDLE",
        "prepared_at_utc": args.prepared_at_utc,
        "status": "ready_local_zero_decision_one_owner_decision_required",
        "human_decision_count": 0,
        "artifacts": [
            {"path": PROPOSAL_REF, "sha256": proposal_hash, "role": "proposal"},
            {"path": DOC_REF, "sha256": sha256(DOC_REF), "role": "human_readable_review"},
            *({"path": ref, "sha256": sha256(ref), "role": "frozen_input"} for ref in INPUT_REFS),
        ],
        "decision_requested": {
            "decision_id": "D-M2-RADAR-GTC-DEM-ISOLATION-PROBE-001",
            "question": "Approve, revise, or defer the single bounded diagnostic-only envelope?",
            "choices": ["approve", "revise", "defer"],
            "response_open": True,
        },
        "authority_boundary": {
            "publication_authorized": False,
            "implementation_authorized": False,
            "arcpy_or_project_data_access_authorized": False,
            "gtc_or_new_attempt_authorized": False,
        },
    }
    write_json(BUNDLE_REF, bundle)
    bundle_hash = sha256(BUNDLE_REF)
    contract = {
        "schema_version": "1.0",
        "contract_id": "NEPAL-M2-RADAR-GTC-DEM-ISOLATION-PROBE-001-REVIEW-CONTRACT",
        "review_bundle": {"ref": BUNDLE_REF, "sha256": bundle_hash},
        "proposal": {"ref": PROPOSAL_REF, "sha256": proposal_hash},
        "response_requirements": {"exact_hashes_required": True, "explicit_decision_required": True, "attestation_required": True},
        "workflow_authority": {"local_preparation_complete": True, "response_open": True},
    }
    write_json(CONTRACT_REF, contract)
    blank = {
        "schema_version": "1.0",
        "response_id": "NEPAL-M2-RADAR-GTC-DEM-ISOLATION-PROBE-001-BLANK-RESPONSE",
        "completed": False,
        "reviewer": {"name": None, "reviewed_at_utc": None, "attestation": False},
        "decision": {"id": "D-M2-RADAR-GTC-DEM-ISOLATION-PROBE-001", "value": None, "comment": None},
        "human_decision_count": 0,
        "response_not_open_until_public_ci": False,
        "bindings": {"proposal_sha256": proposal_hash, "review_bundle_sha256": bundle_hash},
    }
    write_json(BLANK_REF, blank)
    readiness = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-GTC-DEM-ISOLATION-PROBE-001-REVIEW-READINESS",
        "status": "pass_local_zero_decision_packet_ready_one_owner_decision_required",
        "base_commit": BASE_COMMIT,
        "bindings": {
            "proposal_sha256": proposal_hash,
            "review_document_sha256": sha256(DOC_REF),
            "review_bundle_sha256": bundle_hash,
            "review_contract_sha256": sha256(CONTRACT_REF),
            "blank_response_sha256": sha256(BLANK_REF),
        },
        "validation": {"consumed_attempts_preserved": True, "public_metadata_only": True, "human_decision_count": 0},
        "released_now": {"local_preparation": True, "publication": False, "implementation": False, "real_probe": False},
        "next_action": "Seek one owner decision covering publication, implementation, CI, final no-content preflight, at most one exact diagnostic-only no-DEM GTC call, reconciliation, and sanitized terminal publication; no intermediate reconfirmation.",
    }
    write_json(READINESS_REF, readiness)
    print(json.dumps({"status": readiness["status"], "proposal_sha256": proposal_hash, "review_bundle_sha256": bundle_hash}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
