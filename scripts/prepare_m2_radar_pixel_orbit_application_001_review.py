#!/usr/bin/env python3
"""Prepare the zero-decision M2 radar pixel and orbit application review."""

from __future__ import annotations

import argparse
import hashlib
import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_REF = "contracts/milestone-002-radar-pixel-orbit-application-001-proposal.json"
CANDIDATE_REF = "records/readiness/m2-radar-pixel-orbit-application-001-candidate-manifest.json"
AUDIT_REF = "records/readiness/m2-radar-pixel-orbit-application-001-readiness-audit.json"
PREFLIGHT_REF = "records/readiness/m2-radar-pixel-orbit-application-001-review-preflight.json"
DOC_REF = "docs/M2_RADAR_PIXEL_ORBIT_APPLICATION_001_REVIEW.md"
IMAGE_REF = "docs/assets/m2-radar-pixel-orbit-application-001-review.png"
SURFACE_REF = "records/surface-receipts/m2-radar-pixel-orbit-application-001-review.json"
BUNDLE_REF = "reviews/m2-radar-pixel-orbit-application-001/review-bundle.json"
CONTRACT_REF = "reviews/m2-radar-pixel-orbit-application-001/review-contract.json"
BLANK_REF = "reviews/m2-radar-pixel-orbit-application-001/blank-response.json"
READINESS_REF = "records/readiness/m2-radar-pixel-orbit-application-001-review-readiness.json"
CAPABILITY_REF = "records/surface-receipts/m2-radar-pixel-orbit-application-001-capability.json"
MILESTONE_REF = "contracts/milestone-002.json"
PROFILE_REF = "records/project-control-profile.json"
GOAL_REF = "records/long-term-goal.json"


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def load(ref: str) -> dict:
    return json.loads((ROOT / ref).read_text(encoding="utf-8"))


def write_json(ref: str, value: dict, exclusive: bool = True) -> None:
    path = ROOT / ref
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "x" if exclusive else "w"
    with path.open(mode, encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def write_text(ref: str, value: str) -> None:
    path = ROOT / ref
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(value)


def font(name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(str(Path("C:/Windows/Fonts") / name), size)
    except OSError:
        return ImageFont.load_default()


def wrapped(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int], width: int, face: ImageFont.ImageFont, fill: str, leading: int = 31) -> int:
    x, y = xy
    for line in textwrap.wrap(text, width):
        draw.text((x, y), line, font=face, fill=fill)
        y += leading
    return y


def render_surface(proposal_sha: str) -> None:
    image = Image.new("RGB", (1800, 1700), "#f4f0e8")
    draw = ImageDraw.Draw(image)
    title = font("segoeuib.ttf", 40)
    heading = font("segoeuib.ttf", 27)
    body = font("segoeui.ttf", 22)
    small = font("segoeui.ttf", 18)
    bold = font("segoeuib.ttf", 23)
    navy, ink, teal, amber, red, pale, line = "#17334b", "#20282f", "#126b5d", "#956000", "#9a382d", "#fffdfa", "#cbd2d3"

    draw.rectangle((0, 0, 1800, 225), fill=navy)
    draw.text((75, 40), "NEPAL 2026  |  M2 OWNER REVIEW", font=heading, fill="#9ed7cf")
    draw.text((75, 88), "Radar pixel readiness + exact orbit application", font=title, fill="white")
    draw.text((75, 165), f"Proposal SHA-256  {proposal_sha}", font=small, fill="#d8e5eb")

    cards = [
        ("INPUTS", "6 exact Sentinel-1 GRDs, 4 verified S1D AUX_RESORB files, and 4 ellipsoidal DEM derivatives.", teal),
        ("CURRENT AUDIT", "DEFER: custody and method design pass; real masked coverage, registration, and reproducibility are unmeasured.", amber),
        ("CLAIM LIMIT", "A QA pass would establish processing and pixel fitness only, never event change, interpretation, or attribution.", red),
    ]
    top, gap = 270, 24
    width = (1800 - 150 - 2 * gap) // 3
    for index, (label, value, color) in enumerate(cards):
        left = 75 + index * (width + gap)
        draw.rounded_rectangle((left, top, left + width, top + 230), radius=14, fill=pale, outline=line, width=2)
        draw.rectangle((left, top, left + 10, top + 230), fill=color)
        draw.text((left + 30, top + 24), label, font=heading, fill=color)
        wrapped(draw, value, (left + 30, top + 78), 43, body, ink)

    draw.text((75, 555), "DEPENDENCY-ORDERED ROUTE IF APPROVED", font=heading, fill=navy)
    steps = [
        "1  Implement exact source-to-orbit and source-to-DEM controls; synthetic and ArcGIS runtime tests; public CI.",
        "2  Run one final no-content preflight; create fresh versioned output roots and reserved receipts only.",
        "3  Copy each exact SAFE into its own attempt, apply only its bound RESORB, verify source custody unchanged.",
        "4  Process VV/VH once per source: thermal noise, beta calibration, terrain flattening, EPSG:32645 correction.",
        "5  Evaluate ascending and descending routes independently under the frozen coverage, mask, grid, and registration rules.",
    ]
    y = 602
    for item in steps:
        draw.rounded_rectangle((75, y, 1725, y + 76), radius=9, fill="white", outline=line)
        draw.text((100, y + 21), item, font=body, fill=ink)
        y += 87

    draw.text((75, 1082), "BOUNDED ATTEMPTS", font=heading, fill=navy)
    limits = [
        "1 no-content preflight  |  1 orbit application + 1 QA-processing attempt per exact Sentinel-1 source",
        "Fixed source order 001–006  |  stop on execution failure  |  0 automatic retries  |  0 overwrites",
        "Evaluate both orbit routes even if one yields BLOCK or DEFER; preserve every exclusion and terminal receipt",
    ]
    y = 1125
    for item in limits:
        draw.rounded_rectangle((75, y, 1725, y + 68), radius=9, fill="#fffaf0", outline="#decda8")
        draw.text((100, y + 19), item, font=body, fill=ink)
        y += 79

    draw.text((75, 1390), "STILL PROHIBITED", font=heading, fill=red)
    prohibited = "No source, date, orbit, DEM, threshold, mask, or CRS substitution; no precise-orbit claim; no baseline admission, change raster or polygon, attribution, derived-pixel publication, or scientific claim."
    wrapped(draw, prohibited, (85, 1432), 126, body, ink)
    draw.rectangle((0, 1575, 1800, 1700), fill="#e3ebe8")
    draw.text((75, 1613), "DECISION REQUIRED", font=heading, fill=navy)
    draw.text((420, 1610), "Approve  |  Revise  |  Defer — with owner attestation", font=bold, fill=teal)
    path = ROOT / IMAGE_REF
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared-at-utc", required=True)
    args = parser.parse_args()

    outputs = [CANDIDATE_REF, AUDIT_REF, PROPOSAL_REF, PREFLIGHT_REF, DOC_REF, IMAGE_REF, SURFACE_REF, BUNDLE_REF, CONTRACT_REF, BLANK_REF, READINESS_REF]
    collisions = [ref for ref in outputs if (ROOT / ref).exists()]
    if collisions:
        raise SystemExit("review output collision: " + ", ".join(collisions))

    bindings = {
        "source_manifest_ref": "records/source-manifest.json",
        "radar_source_readiness_ref": "records/readiness/m2-radar-source-readiness-001.json",
        "radar_header_receipt_ref": "records/readiness/radar-input/m2-s1-input-readiness-real-003.json",
        "orbit_verification_ref": "records/readiness/m2-orbit-offline-verification-recovery-001-terminal-reconciliation.json",
        "dem_conversion_ref": "records/readiness/m2-dem-proj25-receipt-persistence-recovery-002-terminal-reconciliation.json",
        "aoi_ref": "config/aoi/approved-study-areas.geojson",
        "pair_plan_ref": "config/qa/candidate-pair-plan.json",
        "radar_processing_contract_ref": "config/qa/radar-baseline-processing-contract.json",
        "pixel_readiness_contract_ref": "config/qa/pixel-readiness-contract.json",
        "arcgis_capability_ref": CAPABILITY_REF,
    }
    for key, ref in list(bindings.items()):
        bindings[key.replace("_ref", "_sha256")] = sha256(ref)

    source_manifest = load(bindings["source_manifest_ref"])
    source_ids = [f"M1-SRC-{index:03d}" for index in range(1, 7)]
    source_records = {item["source_id"]: item for item in source_manifest["records"] if item.get("source_id") in source_ids}
    orbit_contract = load("contracts/m2-orbit-offline-verification.json")
    orbit_terminal = load(bindings["orbit_verification_ref"])
    orbit_results = {item["source_id"]: item for item in orbit_terminal["results"]}
    dem_terminal = load(bindings["dem_conversion_ref"])

    orbit_bindings = []
    source_to_orbit = {}
    for item in orbit_contract["asset_requirements"]:
        result = orbit_results[item["source_id"]]
        orbit_bindings.append({
            "source_id": item["source_id"],
            "exact_product_name": item["exact_product_name"],
            "orbit_type": item["orbit_type"],
            "sentinel_source_ids": item["sentinel_source_ids"],
            "custody_sha256": result["custody_sha256"],
            "custody_size_bytes": result["custody_size_bytes"],
            "verification_receipt_ref": result["receipt_ref"],
            "verification_receipt_sha256": result["receipt_sha256"],
        })
        for source_id in item["sentinel_source_ids"]:
            source_to_orbit[source_id] = item["source_id"]

    candidate = {
        "schema_version": "1.0",
        "candidate_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-001-CANDIDATE",
        "prepared_at_utc": args.prepared_at_utc,
        "status": "exact_inputs_bound_no_orbit_application_or_radar_pixel_processing",
        "intended_use": "Create versioned QA-only Sentinel-1 processing candidates and evaluate pixel fitness for the approved AOIs before any baseline or change analysis.",
        "bindings": bindings,
        "sentinel_sources": [
            {
                "source_id": source_id,
                "exact_product_id": source_records[source_id]["exact_product_id"],
                "event_role": source_records[source_id]["event_role"],
                "acquisition_start_utc": source_records[source_id]["acquisition_start_utc"],
                "acquisition_end_utc": source_records[source_id]["acquisition_end_utc"],
                "orbit_direction": source_records[source_id]["orbit_or_tile"]["orbit_direction"],
                "relative_orbit_number": source_records[source_id]["orbit_or_tile"]["relative_orbit_number"],
                "bound_orbit_source_id": source_to_orbit[source_id],
            }
            for source_id in source_ids
        ],
        "orbit_inputs": orbit_bindings,
        "dem_inputs": [
            {
                "source_id": item["source_id"],
                "source_sha256": item["source_sha256"],
                "ellipsoidal_derivative_sha256": item["output_sha256"],
                "ellipsoidal_derivative_size_bytes": item["output_size_bytes"],
                "status": item["status"],
            }
            for item in dem_terminal["source_results"]
        ],
        "fixed_source_order": source_ids,
        "fixed_route_order": ["PAIR-S1-ASC-R085-IW", "PAIR-S1-DESC-R121-IW"],
        "current_observations": {
            "sentinel_source_count": 6,
            "orbit_input_count": 4,
            "ellipsoidal_dem_derivative_count": 4,
            "measurement_pixels_decoded": False,
            "orbit_application_started": False,
            "terrain_processing_started": False,
            "masked_aoi_coverage_measured": False,
            "registration_measured": False,
            "baseline_established": False,
            "change_established": False,
        },
    }
    write_json(CANDIDATE_REF, candidate)
    candidate_sha = sha256(CANDIDATE_REF)

    audit = {
        "audit_contract_version": "dataset-readiness-audit-v2-compatible",
        "audit_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-001-READINESS-AUDIT",
        "candidate_id": candidate["candidate_id"],
        "candidate_manifest_sha256": candidate_sha,
        "audited_at_utc": args.prepared_at_utc,
        "decision": "defer",
        "decision_basis": "Required real-pixel coverage, terrain-mask, registration, and exact pipeline reproducibility evidence does not exist yet; the review proposes the bounded route that would generate it.",
        "required_gate_ids": [
            "source-and-terms", "provenance-and-custody", "schema-and-quality", "coverage-and-balance",
            "uncertainty-and-exclusions", "leakage-and-route-independence", "reproducibility", "evaluation-design", "human-review",
        ],
        "gates": [
            {"gate_id": "source-and-terms", "status": "pass", "evidence_refs": ["records/source-gates/source-manifest-approval.json", "records/source-gates/m2-orbit-amendment-approval.json", "records/source-gates/m2-dem-amendment-approval.json"], "finding": "The six Sentinel, four restituted orbit, and four DEM source families retain exact reviewed identities and rights boundaries."},
            {"gate_id": "provenance-and-custody", "status": "pass", "evidence_refs": [bindings["radar_source_readiness_ref"], bindings["orbit_verification_ref"], bindings["dem_conversion_ref"]], "finding": "Exact Sentinel containers and headers, orbit inputs, and ellipsoidal DEM derivatives have immutable verified identities."},
            {"gate_id": "schema-and-quality", "status": "defer", "evidence_refs": [bindings["radar_header_receipt_ref"]], "finding": "All six headers pass, but measurement values and processing behavior on real pixels are untested."},
            {"gate_id": "coverage-and-balance", "status": "defer", "evidence_refs": [bindings["pair_plan_ref"], bindings["aoi_ref"]], "finding": "Catalog footprints intersect the planned areas, while usable masked coverage after terrain correction is unmeasured."},
            {"gate_id": "uncertainty-and-exclusions", "status": "defer", "evidence_refs": [bindings["pixel_readiness_contract_ref"], bindings["radar_processing_contract_ref"]], "finding": "Exclusion classes are frozen, but their real AOI areas and effects are unknown."},
            {"gate_id": "leakage-and-route-independence", "status": "pass", "evidence_refs": [bindings["pair_plan_ref"], bindings["radar_processing_contract_ref"]], "finding": "Ascending and descending routes, dates, slices, and same-date mosaics are predeclared and must remain independently evaluated."},
            {"gate_id": "reproducibility", "status": "defer", "evidence_refs": [bindings["arcgis_capability_ref"]], "finding": "The installed runtime exposes every required tool signature, but the exact-source pipeline has not been implemented or synthetically replayed."},
            {"gate_id": "evaluation-design", "status": "pass", "evidence_refs": [bindings["pixel_readiness_contract_ref"], bindings["radar_processing_contract_ref"]], "finding": "Coverage, mask, grid, registration, stable-control, seam, and route-disposition rules were frozen before real radar pixels."},
            {"gate_id": "human-review", "status": "defer", "evidence_refs": [], "finding": "This exact staged processing route has zero owner decisions and creates no execution authority."},
        ],
        "count_checks": [
            {"check_id": "exact-sentinel-source-count", "observed": 6, "operator": "==", "threshold": 6, "on_failure": "block", "status": "pass"},
            {"check_id": "exact-orbit-input-count", "observed": 4, "operator": "==", "threshold": 4, "on_failure": "block", "status": "pass"},
            {"check_id": "exact-dem-derivative-count", "observed": 4, "operator": "==", "threshold": 4, "on_failure": "block", "status": "pass"},
        ],
        "authority_boundary": {"this_audit_creates_authority": False, "authorized_actions": []},
        "claim_boundary": "The audit identifies evidence gaps only. Counts and input custody cannot establish usable radar pixels, registration, a baseline, event change, interpretation, or attribution.",
    }
    write_json(AUDIT_REF, audit)

    proposal = {
        "schema_version": "1.0",
        "proposal_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-001-PROPOSAL",
        "prepared_at_utc": args.prepared_at_utc,
        "status": "proposed_inactive_owner_review_required",
        "recommended_decision": "approve_dependency_ordered_exact_source_qa_route",
        "bindings": {
            "candidate_manifest_ref": CANDIDATE_REF,
            "candidate_manifest_sha256": candidate_sha,
            "readiness_audit_ref": AUDIT_REF,
            "readiness_audit_sha256": sha256(AUDIT_REF),
            **bindings,
        },
        "proposed_bounded_actions": [
            "implement only the exact six-source ArcGIS processing route, source-to-orbit map, ellipsoidal DEM bindings, append-only receipts, original-custody inventory checks, and frozen QA evaluator",
            "run synthetic interruption, collision, exact-binding, original-immutability, fixed-order, stop-on-execution-failure, mask, coverage, grid, registration, and no-network tests plus ArcGIS runtime synthetic tests",
            "require a successful public default-branch CI gate before one final no-content preflight or any project data content read",
            "only on those passes create one fresh versioned non-Git attempt and process M1-SRC-001 through M1-SRC-006 in exact order, with at most one orbit-application and one QA-processing attempt per source and no automatic retry",
            "apply only the exact bound AUX_RESORB path to a versioned SAFE copy, never the original materialized SAFE, and verify the original Sentinel, orbit, and DEM custody inventories remain unchanged",
            "only after all six source executions succeed evaluate the ascending and descending routes independently under the frozen pixel-readiness contract, preserving PASS_QA_ONLY, DEFER, BLOCK, INVALID, masks, exclusions, and limitations",
            "reconcile the terminal QA dispositions and stop before baseline admission, change analysis, interpretation, attribution, derived-pixel publication, or a scientific claim",
        ],
        "fixed_sequence": {
            "source_ids": source_ids,
            "source_to_orbit": source_to_orbit,
            "route_ids": candidate["fixed_route_order"],
            "processing_chain": [
                "copy exact materialized SAFE into a new versioned attempt without replacing any existing path",
                "ApplyOrbitCorrection_ia with the explicit exact verified AUX_RESORB file",
                "RemoveThermalNoise_ia for VV and VH",
                "ApplyRadiometricCalibration_ia to linear Beta nought",
                "ApplyRadiometricTerrainFlattening_ia to linear Gamma nought with exact ellipsoidal DEM derivatives and geoid NONE",
                "ApplyGeometricTerrainCorrection_ia to EPSG:32645 at 10 metres",
                "derive decibel display candidates from positive linear Gamma nought while retaining linear masters",
                "build the frozen categorical exclusion mask and route-specific same-date mosaics",
                "measure AOI coverage, usable fraction, grid compatibility, seams, stable-control registration, and limitations",
            ],
        },
        "limits": {
            "final_no_content_preflight_attempts": 1,
            "orbit_application_attempts_per_source": 1,
            "qa_processing_attempts_per_source": 1,
            "route_qa_attempts_per_pair": 1,
            "automatic_retry": False,
            "stop_on_execution_failure": True,
            "continue_independent_route_disposition_after_scientific_block_or_defer": True,
            "network_requests": 0,
            "credentials_or_tokens": 0,
            "source_overwrites": 0,
            "output_overwrites": 0,
            "precise_orbit_substitutions": 0,
        },
        "does_not_authorize": [
            "source, product, date, orbit type, orbit identity, DEM, vertical relation, AOI, CRS, resolution, polarization, threshold, mask-class, stable-control, mosaic, or route-order substitution",
            "any second attempt, automatic retry, reuse of a failed attempt path, overwrite, in-place mutation of materialized SAFE custody, or mutation of orbit or DEM custody",
            "a network request, credential or token action, account or terms action, software installation, UAC action, or ArcGIS extension purchase",
            "AUX_POEORB substitution or any statement that restituted orbit files are precise-orbit equivalent",
            "despeckling of the primary quantitative route, threshold tuning after observation, alternate source search, or hidden exclusion",
            "baseline admission, change raster or polygon generation, cross-route synthesis, geomorphic interpretation, event attribution, emergency guidance, derived-pixel publication, or scientific publication",
        ],
        "claim_boundary": {
            "approval_would_authorize_execution_only_after_implementation_public_ci_and_final_preflight": True,
            "qa_pass_may_establish": "exact processing lineage plus measured coverage, mask, grid, seam, and registration fitness for one or both independent radar routes",
            "qa_pass_does_not_establish": ["pre-event baseline admission", "landscape change", "geomorphic interpretation", "event attribution", "emergency guidance", "scientific publication"],
            "orbit_application_authorized_now": False,
            "radar_pixel_processing_authorized_now": False,
            "human_decision_count": 0,
        },
        "decision_domain": ["approve", "revise", "defer"],
        "attestation_required": True,
    }
    write_json(PROPOSAL_REF, proposal)
    proposal_sha = sha256(PROPOSAL_REF)

    preflight = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-001-REVIEW-PREFLIGHT",
        "verified_at_utc": args.prepared_at_utc,
        "status": "pass_review_ready_no_processing_authority",
        "bindings": {"proposal_sha256": proposal_sha, "candidate_manifest_sha256": candidate_sha, "readiness_audit_sha256": sha256(AUDIT_REF), "capability_sha256": sha256(CAPABILITY_REF)},
        "assertions": {
            "human_decision_count": 0,
            "installed_runtime_signatures_passed": load(CAPABILITY_REF)["checks"]["all_required_signatures_match"],
            "project_data_content_read_during_preparation": False,
            "orbit_application_authorized": False,
            "radar_pixel_processing_authorized": False,
            "baseline_or_change_authorized": False,
            "network_requests_performed": False,
            "external_custody_mutated": False,
        },
    }
    write_json(PREFLIGHT_REF, preflight)

    doc = f"""# M2 radar pixel readiness and orbit application review 001

## Decision

Choose **approve**, **revise**, or **defer** for proposal `{proposal_sha}`. Approval must be an attested owner decision bound to the exact public review-bundle hash.

## Established inputs

Six exact Sentinel-1 GRD products pass custody, materialization, and header-only readiness. Four exact S1D `AUX_RESORB` files pass offline identity and structure verification. Four exact EGM2008-corrected WGS 84 ellipsoidal DEM derivatives pass conversion verification. ArcGIS Pro 3.7.1 exposes the required SAR tool signatures.

These facts establish input identity and capability only. No Sentinel-1 measurement pixels have been decoded, no external orbit has been applied, and no terrain-corrected radar candidate exists.

## Readiness audit

The current decision is `DEFER`: source rights, provenance, route independence, and evaluation design pass, while real pixel schema behavior, masked AOI coverage, exclusions, registration, exact-pipeline reproducibility, and this owner decision are unresolved. The proposal is designed to generate that missing evidence without changing the frozen QA rules.

## What approval would release

Approval releases a dependency-ordered route: exact implementation and synthetic/ArcGIS tests; successful public CI; one final no-content preflight; one versioned orbit-application and QA-processing attempt per exact Sentinel-1 source in fixed order; then one independent QA evaluation per ascending and descending route. Execution failures stop the source sequence. A valid route `BLOCK` or `DEFER` remains evidence and does not suppress evaluation of the independent route.

Every real output remains outside Git in a fresh, non-overwriting attempt. Original Sentinel, orbit, and DEM custody must remain unchanged.

## What remains prohibited

No source, date, orbit, DEM, vertical relation, AOI, CRS, grid, threshold, mask, stable-control, or route substitution. No automatic retry, overwrite, token, network, installation, precise-orbit claim, baseline admission, change product, cross-route synthesis, interpretation, attribution, derived-pixel publication, or scientific claim.

## Decision meaning

A later `PASS_QA_ONLY` may establish measured coverage, masking, grid, seam, and registration fitness. It cannot establish a baseline, observable event change, geomorphic interpretation, or attribution.
"""
    write_text(DOC_REF, doc)
    render_surface(proposal_sha)

    surface = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-001-REVIEW-SURFACE",
        "verified_at_utc": args.prepared_at_utc,
        "status": "pass_blank_review_surface",
        "render": {"path": IMAGE_REF, "sha256": sha256(IMAGE_REF), "width": 1800, "height": 1700, "human_decision_count": 0},
        "assertions": {"proposal_sha256": proposal_sha, "completion_controls_visible": True, "bounded_sequence_visible": True, "claim_limit_visible": True, "orbit_application_authorized": False, "radar_pixel_processing_authorized": False},
    }
    write_json(SURFACE_REF, surface)

    artifacts = [
        ("review-surface", IMAGE_REF, "review_surface", True),
        ("review-instructions", DOC_REF, "decision_instructions", False),
        ("proposal", PROPOSAL_REF, "candidate_authority_envelope", False),
        ("candidate-manifest", CANDIDATE_REF, "exact_input_and_method_identity", False),
        ("readiness-audit", AUDIT_REF, "current_pass_and_defer_gate_assessment", False),
        ("review-preflight", PREFLIGHT_REF, "zero_authority_preflight", False),
        ("arcgis-capability", CAPABILITY_REF, "installed_runtime_signature_evidence", False),
        ("radar-source-readiness", bindings["radar_source_readiness_ref"], "six_source_custody_materialization_header_readiness", False),
        ("orbit-verification", bindings["orbit_verification_ref"], "four_exact_orbit_input_verification", False),
        ("dem-conversion", bindings["dem_conversion_ref"], "four_exact_ellipsoidal_dem_derivatives", False),
        ("pair-plan", bindings["pair_plan_ref"], "frozen_route_identity", False),
        ("radar-processing-contract", bindings["radar_processing_contract_ref"], "frozen_processing_and_admission_method", False),
        ("pixel-readiness-contract", bindings["pixel_readiness_contract_ref"], "frozen_qa_rules", False),
        ("approved-aoi", bindings["aoi_ref"], "approved_spatial_scope", False),
    ]
    bundle = {
        "schema_version": "1.0",
        "template": False,
        "bundle_id": "m2-radar-pixel-orbit-application-001-review-bundle",
        "review_id": "m2-radar-pixel-orbit-application-001-review",
        "authority_ref": "records/source-gates/m2-radar-first-path-001-approval.json",
        "candidate_identity": f"M2-RADAR-PIXEL-ORBIT-APPLICATION-001-PROPOSAL-SHA256:{proposal_sha}",
        "artifacts": [
            {"artifact_id": artifact_id, "path": ref, "sha256": sha256(ref), "role": role, "render_required": rendered, "render_receipts": [{"path": SURFACE_REF, "sha256": sha256(SURFACE_REF)}] if rendered else []}
            for artifact_id, ref, role, rendered in artifacts
        ],
        "review_surface": {"artifact_id": "review-surface", "blank_state_verified": True, "completion_controls_verified": True, "export_verified": True},
        "decision_effect_if_approved": ["release only the dependency-ordered implementation, public-CI gate, final no-content preflight, fixed-order exact-source orbit and QA-processing attempts, independent route QA, and terminal reconciliation stated in the proposal"],
        "limitations": proposal["does_not_authorize"],
        "human_decision_count": 0,
    }
    write_json(BUNDLE_REF, bundle)
    bundle_sha = sha256(BUNDLE_REF)

    review_contract = {
        "contract_version": "human-review-contract-v1",
        "template": False,
        "review_id": bundle["review_id"],
        "response_schema_version": "nepal-m2-radar-pixel-orbit-application-001-response-v1",
        "workflow_authority": {
            "mode": "inherited",
            "authority_ref": "records/source-gates/m2-radar-first-path-001-approval.json",
            "authorized_action_classes": ["evidence_recording", "project_control", "update_project_records", "external_publication"],
            "verified_at_utc": args.prepared_at_utc,
            "expires_at_utc": None,
            "review_required": True,
            "lock_authorized": True,
            "reconcile_authorized": True,
            "post_review_actions": ["evidence_recording", "project_control", "update_project_records"],
        },
        "review_bundle": {"bundle_id": bundle["bundle_id"], "manifest_sha256": bundle_sha, "candidate_identity": bundle["candidate_identity"], "rendered_surface_verified": True},
        "allowed_decisions": ["approve", "revise", "defer"],
        "required_attestation": True,
        "max_notes_length": 4000,
        "hash_prefix_length": 16,
        "items": [{"item_id": "M2-RADAR-PIXEL-ORBIT-APPLICATION-001", "evidence_sha256": bundle_sha}],
    }
    write_json(CONTRACT_REF, review_contract)
    blank = {
        "response_schema_version": review_contract["response_schema_version"],
        "review_id": review_contract["review_id"],
        "completed": False,
        "review_started_at_utc": None,
        "review_completed_at_utc": None,
        "reviewer": {"attestation": False},
        "responses": [{"item_id": "M2-RADAR-PIXEL-ORBIT-APPLICATION-001", "evidence_sha256": bundle_sha, "decision": None, "notes": ""}],
    }
    write_json(BLANK_REF, blank)
    readiness = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-001-REVIEW-READINESS",
        "verified_at_utc": args.prepared_at_utc,
        "status": "pass_ready_publication_zero_decisions",
        "bindings": {"proposal_sha256": proposal_sha, "candidate_manifest_sha256": candidate_sha, "readiness_audit_sha256": sha256(AUDIT_REF), "review_preflight_sha256": sha256(PREFLIGHT_REF), "review_surface_sha256": sha256(IMAGE_REF), "surface_receipt_sha256": sha256(SURFACE_REF), "review_bundle_sha256": bundle_sha, "review_contract_sha256": sha256(CONTRACT_REF), "blank_response_sha256": sha256(BLANK_REF)},
        "validation": {"human_decision_count": 0, "attestation": False, "ready_for_publication": True},
        "assertions": {"orbit_application_authorized": False, "radar_pixel_processing_authorized": False, "baseline_or_change_authorized": False, "project_data_content_read_during_preparation": False, "network_requests_performed": False, "external_custody_mutated": False, "scientific_result_established": False},
        "next_action": "Publish and publicly validate the exact zero-decision review packet before owner review."
    }
    write_json(READINESS_REF, readiness)

    checkpoint = "M2-RADAR-PIXEL-ORBIT-APPLICATION-001-REVIEW-PUBLICATION"
    next_action = "Publish and publicly validate the exact zero-decision radar pixel and orbit application review packet. Do not implement the route, read project pixels, apply an orbit, or create processing outputs before successful public CI and one exact attested owner decision."
    milestone = load(MILESTONE_REF)
    if any(unit.get("id") == "M2-RADAR-PIXEL-ORBIT-APPLICATION-001-REVIEW" for unit in milestone["units"]):
        raise SystemExit("milestone already contains review unit")
    milestone["units"].append({
        "id": "M2-RADAR-PIXEL-ORBIT-APPLICATION-001-REVIEW",
        "purpose": "Review a bounded exact-source orbit-application and radar pixel-readiness QA route without releasing baseline or change analysis.",
        "depends_on": ["M2-RADAR-SOURCE-READINESS", "M2-ORBIT-VERIFY", "M2-DEM-VERTICAL-DATUM-CONVERSION"],
        "action_class": "authority_broadening",
        "human_gate": True,
        "status": "in_progress",
        "inputs": [PROPOSAL_REF, CANDIDATE_REF, AUDIT_REF, BUNDLE_REF, CONTRACT_REF, BLANK_REF],
        "outputs": ["records/source-gates/m2-radar-pixel-orbit-application-001-review-reconciliation.json", "records/source-gates/m2-radar-pixel-orbit-application-001-approval.json"],
        "gates": {"proposal_sha256": proposal_sha, "review_bundle_sha256": bundle_sha, "public_ci": "pending", "human_decision_count": 0, "attestation": False, "orbit_application_authorized": False, "radar_pixel_processing_authorized": False, "baseline_or_change_authorized": False},
        "disposition": None,
        "retained_failures": [],
        "exit_condition_delta": {"expected": ["one exact attested owner decision"], "observed": [], "decision_value": "unknown", "rationale": "The public packet is blank and creates no processing authority."},
        "next_dependency": "M2-ORBIT-APPLY",
    })
    milestone["handoff"]["current_checkpoint"] = checkpoint
    milestone["handoff"]["next_action"] = next_action
    milestone["handoff"]["parallel_checkpoint"] = checkpoint
    milestone["handoff"]["parallel_next_action"] = next_action
    milestone["handoff"]["do_not_carry_forward"].append("The radar pixel and orbit application review packet has zero decisions; no project data content read, orbit application, terrain processing, baseline, change analysis, attribution, or scientific publication is released before public CI and exact owner approval.")
    write_json(MILESTONE_REF, milestone, exclusive=False)

    profile = load(PROFILE_REF)
    profile["control_surfaces"]["proposed_amendments"] = [PROPOSAL_REF]
    profile["gate_policy"]["explicit_human_gates"].append({
        "unit_id": "M2-RADAR-PIXEL-ORBIT-APPLICATION-001-REVIEW",
        "reason": "Requires one exact owner decision before the bounded fixed-order orbit application and radar pixel-readiness QA route can be implemented or executed.",
        "authority_ref": CONTRACT_REF,
    })
    profile["current_checkpoint"]["checkpoint_id"] = checkpoint
    profile["current_checkpoint"]["next_action"] = next_action
    profile["parallel_checkpoints"] = [{"checkpoint_id": checkpoint, "authority_ref": CONTRACT_REF, "next_action": next_action}]
    write_json(PROFILE_REF, profile, exclusive=False)

    goal = load(GOAL_REF)
    goal["current_checkpoint"] = checkpoint
    goal["proposed_amendments"] = [PROPOSAL_REF]
    goal["parallel_checkpoints"] = [checkpoint]
    write_json(GOAL_REF, goal, exclusive=False)

    print(json.dumps({"proposal_sha256": proposal_sha, "review_bundle_sha256": bundle_sha, "candidate_manifest_sha256": candidate_sha, "checkpoint": checkpoint}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
