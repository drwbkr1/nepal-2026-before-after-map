#!/usr/bin/env python3
"""Prepare one local, zero-decision DEM fitness and GTC comparison review."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-dem-fitness-comparison-001"
PROPOSAL = f"contracts/milestone-002-{PREFIX}-proposal.json"
DOC = "docs/M2_RADAR_DEM_FITNESS_COMPARISON_001_REVIEW.md"
BUNDLE = f"reviews/{PREFIX}/review-bundle.json"
CONTRACT = f"reviews/{PREFIX}/review-contract.json"
BLANK = f"reviews/{PREFIX}/blank-response.json"
READINESS = f"records/readiness/{PREFIX}-review-readiness.json"
INPUTS = (
    "AGENTS.md",
    "records/processing/m2-radar-esri-sequence-recovery-005-terminal-reconciliation.json",
    "records/processing/m2-radar-gtc-dem-isolation-probe-001-terminal-reconciliation.json",
    "records/processing/m2-radar-gtc-input-compatibility-diagnostic-001-terminal-reconciliation.json",
    "records/observations/m2-radar-gtc-post-probe-route-analysis-001.json",
    "records/observations/m2-radar-dem-swath-catalog-001.json",
    "records/observations/m2-radar-dem-candidate-heads-001.json",
    "records/observations/m2-radar-dem-license-recheck-001.json",
    "config/qa/m2-radar-pixel-orbit-application-001-contract.json",
    "config/aoi/approved-study-areas-epsg32645.json",
    "records/source-gates/m2-dem-amendment-approval.json",
)


def digest(ref: str) -> str:
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
    if head != "dafa082b608b16f630e5378ca8072e76e17078fe":
        raise SystemExit("base commit drift; reassess inputs")
    if any((ROOT / ref).exists() for ref in (PROPOSAL, DOC, BUNDLE, CONTRACT, BLANK, READINESS)):
        raise SystemExit("review output collision")
    recovery = json.loads((ROOT / INPUTS[1]).read_text(encoding="utf-8"))
    probe = json.loads((ROOT / INPUTS[2]).read_text(encoding="utf-8"))
    analysis = json.loads((ROOT / INPUTS[4]).read_text(encoding="utf-8"))
    if not recovery.get("attempt_consumed") or not probe.get("attempt_consumed"):
        raise SystemExit("prior attempts are not verified terminal")
    if not probe.get("observation", {}).get("gtc_returned_raster"):
        raise SystemExit("probe result differs")
    if analysis.get("source_gate", {}).get("additional_tile_acquisition_disposition") != "defer_until_valid-pixel_coverage_and_method_compatibility_evidence":
        raise SystemExit("source gate differs")
    bindings = [{"ref": ref, "sha256": digest(ref)} for ref in INPUTS]
    proposal = {
        "schema_version": "1.0",
        "proposal_id": "NEPAL-M2-RADAR-DEM-FITNESS-COMPARISON-001",
        "prepared_at_utc": args.prepared_at_utc,
        "status": "local_zero_decision_not_authorized",
        "human_decision_count": 0,
        "base_commit": head,
        "input_bindings": bindings,
        "problem": "The DEM-supplied recovery-005 GTC failed with ERROR 000425, whereas a no-DEM diagnostic returned and saved a Raster. Input representation, environment, and process also differed; no historical cause is isolated. Four-tile catalog geometry does not establish valid DEM coverage, and the no-DEM land-scene output cannot be admitted scientifically.",
        "question": "Is there actual valid DEM and preserved gamma coverage in the M1-SRC-001 portion of the approved overview AOI, and can one isolated DEM-supplied GTC call complete under the later successful probe environment?",
        "official_guidance": {
            "gtc_url": "https://doc.esri.com/en/arcgis-pro/latest/tool-reference/image-analyst/apply-geometric-terrain-correction.html",
            "rtf_url": "https://doc.esri.com/en/arcgis-pro/latest/tool-reference/image-analyst/apply-radiometric-terrain-flattening.html",
            "block_read_url": "https://doc.esri.com/en/arcgis-pro/latest/arcpy/functions/rastertonumpyarray-function.html",
            "boundary": "Esri directs land-scene GTC to use a DEM; RTF yields NoData outside DEM extent. Catalog polygons and a no-DEM output do not establish usable terrain-corrected pixels."
        },
        "proposed_single_authority_envelope": {
            "covers_without_intermediate_reconfirmation": [
                "local bounded implementation and synthetic and installed ArcGIS disposable runtime validation",
                "public default-branch packet, implementation, and execution CI gates",
                "one final no-content preflight and one new append-only diagnostic process",
                "read-only actual valid-pixel and NoData audit of the exact existing DEM and preserved gamma on the frozen overview AOI",
                "only on structural and positive-overlap pass, at most one DEM-supplied GTC call and one output save",
                "durable terminal and cleanup receipts, exact reconciliation, and sanitized public terminal publication"
            ],
            "attempt_id": "radar-dem-fitness-comparison-001-real-001",
            "prospective_attempt_root": "C:\\Projects\\Active\\nepal-2026-before-after-map-data\\r5\\d3",
            "exact_gamma_input": "C:\\Projects\\Active\\nepal-2026-before-after-map-data\\r5\\a1\\s\\1\\gamma0_linear_despeckled.crf",
            "exact_dem_input": "C:\\Projects\\Active\\nepal-2026-before-after-map-data\\r5\\a1\\dem\\ellipsoidal_dem_mosaic.tif",
            "exact_aoi_ref": "config/aoi/approved-study-areas-epsg32645.json",
            "output_ref_within_attempt_root": "gtc_with_existing_dem_diagnostic.crf",
            "coverage_audit_method": [
                "Before real execution, publish a fixed blockwise raster-read algorithm and test it on disposable rasters; do not adapt its validity predicate after seeing project pixels.",
                "Use at most 512-by-512 native-grid RasterToNumPyArray windows. Confirm Esri's multiband (bands, rows, columns) shape and cell-corner snapping on disposable rasters; fail closed on shape or alignment ambiguity.",
                "Project the frozen EPSG:32645 AOI geometry into each input's verified native EPSG:4326 CRS and count native cell centers within that geometry. Do not reproject, resample, write, or derive either input raster.",
                "Read only the exact existing DEM and both bands of the exact preserved gamma CRF. Establish band-specific NoData and finite-value predicates before counting; if a NoData sentinel is absent, collides with valid values, or cannot be distinguished reliably, stop before GTC rather than classify unknown cells as valid.",
                "Count valid and NoData cells for each input within its own projected AOI-OVERVIEW intersection; report separate counts, geometry, and denominators. Do not call these counts co-registered pixel overlap or full SAR-scene DEM coverage.",
                "Gate the GTC comparison only on exact identity, successful complete counts, positive native valid cells for DEM and both gamma bands in the AOI-OVERVIEW, and a positive geometric intersection of their valid-cell envelopes there. This is a diagnostic floor, not a scientific coverage threshold or baseline admission.",
                "Report coverage for AOI-SOURCE and AOI-UPPER-CORRIDOR where each input intersects, with not-applicable where M1-SRC-001 does not; do not impose full-AOI or six-source route criteria on this diagnostic."
            ],
            "conditional_exact_call": "arcpy.ia.ApplyGeometricTerrainCorrection(arcpy.Raster(exact_gamma_input), 'VV;VH', exact_dem_input, 'NONE')",
            "environment": "Same one-process ArcGIS Image Analyst and scratch-workspace setup as the successful no-DEM probe; no recovery-005 10 m snapRaster, cellSize, or resampling EnvManager override around GTC.",
            "save_rule": "Only if GTC returns Raster, save once to the declared absent output and quarantine it outside Git; never use or publish its pixels.",
            "preflight": [
                "verify exact public evidence hashes and consumed prior attempt identities",
                "verify exact input and DEM paths and approved AOI identity without reading pixels",
                "verify prospective root and output absent, path lengths safe, disk space at least 60 GiB, installed ArcGIS interface and Image Analyst availability",
                "reserve durable terminal and cleanup receipt identities before any project-data pixel read"
            ],
            "maximum_new_processes": 1,
            "maximum_gtc_calls": 1,
            "maximum_output_saves": 1,
            "automatic_retry": False,
            "stop_on_failure": True,
            "network_or_credential_actions": 0,
            "additional_dem_tile_requests": 0,
            "other_geoprocessing_calls": 0,
            "possible_observations": {
                "coverage_block": "Actual input validity or identity prevents this narrow comparison; retain receipts and stop without GTC.",
                "gtc_success": "The exact DEM-supplied call can complete in this changed input/environment; neither historical root cause nor full-route fitness is established.",
                "gtc_failure": "The call remains blocked or fails; do not attribute a sole cause or retry."
            }
        },
        "source_gate": {
            "existing_four_tiles": "Previously accepted exact source and license, for diagnostic use only under the reviewed action envelope.",
            "additional_fourteen_tiles": "Public STAC/HEAD metadata observed; integrity, valid-pixel fitness, need, and acquisition authority remain unresolved. Defer acquisition."
        },
        "exclusions": [
            "reuse, resume, retry, or mutation of consumed recovery-005, input diagnostic, or no-DEM probe attempts",
            "new DEM acquisition, source or DEM conversion, substitution, or mutation",
            "source/date/order/identity, AOI, CRS, mask, threshold, or frozen scientific-route substitution",
            "another source, route, fallback call, second process, or retry after any failure",
            "baseline admission, change analysis, interpretation, attribution, derived-pixel publication, or scientific publication",
            "historical-root-cause, terrain-error-cause, full DEM fitness, or radar-recovery-readiness claim"
        ],
        "does_not_authorize_now": [
            "Git commit, push, public CI, or response recording",
            "ArcPy invocation, project-data or external-custody access, or pixel read",
            "new GTC call, DEM acquisition, or scientific use"
        ]
    }
    write_json(PROPOSAL, proposal)
    proposal_hash = digest(PROPOSAL)
    doc = f"""# M2 radar DEM fitness and controlled GTC comparison-001 review

This is a **local zero-decision proposal** at base commit `{head}`. Proposal SHA-256: `{proposal_hash}`. Preparation releases no Git publication, project-data read, ArcPy call, DEM acquisition, or new attempt.

The no-DEM probe completed, but it changed more than DEM presence relative to recovery-005. It used an ArcPy Raster input, omitted the prior 10 m snap environment, and ran separately. The earlier `ERROR 000425` therefore has no isolated cause. Catalog footprints show possible gaps, not actual valid pixels. [Esri GTC guidance](https://doc.esri.com/en/arcgis-pro/latest/tool-reference/image-analyst/apply-geometric-terrain-correction.html) calls for DEM use on land scenes; [Esri RTF guidance](https://doc.esri.com/en/arcgis-pro/latest/tool-reference/image-analyst/apply-radiometric-terrain-flattening.html) documents NoData outside DEM coverage. [Esri's array-read documentation](https://doc.esri.com/en/arcgis-pro/latest/arcpy/functions/rastertonumpyarray-function.html) specifies multiband array shape and block window behavior.

## One proposed owner decision

Approve, revise, or defer one bounded envelope covering packet publication, implementation and synthetic/installed-runtime validation, public CI gates, final no-content preflight, one read-only actual valid-pixel audit, **conditionally one** DEM-supplied GTC call on the exact preserved M1-SRC-001 gamma CRF, durable receipts, reconciliation, and sanitized terminal publication without intermediate reconfirmation. The proposal binds paths, AOI, native-grid validity counts, stop rules, one prospective root, and a quarantined output.

The audit projects AOI geometry to the native input CRS and reads at most 512-by-512 cells per window without resampling input rasters. Ambiguous NoData or grid alignment stops the process before GTC. Positive valid cells in each input on the overview AOI are only a floor for this diagnostic comparison. M1-SRC-001 does not cover the full event source and upper-corridor AOIs, so this does not assess a full scene or baseline. Even if GTC saves a raster, that output cannot be admitted to a map or a scientific claim under this proposal. The fourteen additional DEM catalog cells remain unapproved for acquisition; their need and pixel fitness remain unknown.

No action in this proposal is authorized merely by its preparation. The review asks for one decision on the entire bounded envelope, with no intermediate microapproval.
"""
    path = ROOT / DOC
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(doc)
    bundle = {
        "schema_version": "1.0", "bundle_id": "NEPAL-M2-RADAR-DEM-FITNESS-COMPARISON-001-REVIEW-BUNDLE",
        "prepared_at_utc": args.prepared_at_utc,
        "status": "local_zero_decision_one_owner_decision_required", "human_decision_count": 0,
        "artifacts": [
            {"path": PROPOSAL, "sha256": proposal_hash, "role": "proposal"},
            {"path": DOC, "sha256": digest(DOC), "role": "human_readable_review"},
            *({"path": ref, "sha256": digest(ref), "role": "frozen_input"} for ref in INPUTS),
        ],
        "decision_requested": {
            "decision_id": "D-M2-RADAR-DEM-FITNESS-COMPARISON-001",
            "question": "Approve, revise, or defer the one bounded diagnostic envelope?",
            "choices": ["approve", "revise", "defer"], "response_open": True
        },
        "authority_boundary": {"publication_authorized": False, "implementation_authorized": False, "project_pixel_read_authorized": False, "gtc_or_new_attempt_authorized": False, "new_dem_acquisition_authorized": False}
    }
    write_json(BUNDLE, bundle)
    bundle_hash = digest(BUNDLE)
    contract = {
        "schema_version": "1.0", "contract_id": "NEPAL-M2-RADAR-DEM-FITNESS-COMPARISON-001-REVIEW-CONTRACT",
        "review_bundle": {"ref": BUNDLE, "sha256": bundle_hash},
        "proposal": {"ref": PROPOSAL, "sha256": proposal_hash},
        "response_requirements": {"exact_hashes_required": True, "explicit_decision_required": True, "attestation_required": True},
        "workflow_authority": {"local_preparation_complete": True, "response_open": True}
    }
    write_json(CONTRACT, contract)
    blank = {
        "schema_version": "1.0", "response_id": "NEPAL-M2-RADAR-DEM-FITNESS-COMPARISON-001-BLANK-RESPONSE",
        "completed": False,
        "reviewer": {"name": None, "reviewed_at_utc": None, "attestation": False},
        "decision": {"id": "D-M2-RADAR-DEM-FITNESS-COMPARISON-001", "value": None, "comment": None},
        "human_decision_count": 0,
        "bindings": {"proposal_sha256": proposal_hash, "review_bundle_sha256": bundle_hash}
    }
    write_json(BLANK, blank)
    readiness = {
        "schema_version": "1.0", "record_id": "NEPAL-M2-RADAR-DEM-FITNESS-COMPARISON-001-REVIEW-READINESS",
        "status": "pass_local_zero_decision_packet_ready_one_owner_decision_required",
        "base_commit": head,
        "bindings": {"proposal_sha256": proposal_hash, "review_document_sha256": digest(DOC), "review_bundle_sha256": bundle_hash, "review_contract_sha256": digest(CONTRACT), "blank_response_sha256": digest(BLANK)},
        "validation": {"prior_attempts_consumed": True, "new_decisions_recorded": 0, "project_pixels_read": False},
        "released_now": {"local_preparation": True, "publication": False, "implementation": False, "real_process": False},
        "next_action": "One owner decision on the exact local bundle covering publication through sanitized terminal reconciliation; no intermediate reconfirmation."
    }
    write_json(READINESS, readiness)
    print(json.dumps({"status": readiness["status"], "proposal_sha256": proposal_hash, "review_bundle_sha256": bundle_hash}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
