#!/usr/bin/env python3
"""Prepare the zero-decision M2 orbit OSV precision amendment-001 review."""

from __future__ import annotations

import argparse
import hashlib
import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REF = "records/source-gates/m2-orbit-osv-time-format-evidence.json"
PROPOSAL_REF = "contracts/milestone-002-orbit-osv-precision-amendment-001-proposal.json"
PREFLIGHT_REF = "records/readiness/m2-orbit-osv-precision-amendment-001-review-preflight.json"
DOC_REF = "docs/M2_ORBIT_OSV_PRECISION_AMENDMENT_001_REVIEW.md"
IMAGE_REF = "docs/assets/m2-orbit-osv-precision-amendment-001-review.png"
SURFACE_REF = "records/surface-receipts/m2-orbit-osv-precision-amendment-001-review.json"
BUNDLE_REF = "reviews/m2-orbit-osv-precision-amendment-001/review-bundle.json"
CONTRACT_REF = "reviews/m2-orbit-osv-precision-amendment-001/review-contract.json"
BLANK_REF = "reviews/m2-orbit-osv-precision-amendment-001/blank-response.json"
READINESS_REF = "records/readiness/m2-orbit-osv-precision-amendment-001-review-readiness.json"

OUTCOME_REF = "records/acquisition/m2-orbit-recovery-003-outcome-reconciliation.json"
CONTROL_REF = "records/acquisition/m2-orbit-recovery-003-terminal-failure-control-reconciliation.json"
FAILED_RECONCILIATION_REF = "records/acquisition/m2-orbit-recovery-003-outcome-reconciliation-attempt-001-failure.json"
ATTEMPT_RECEIPT_REF = "records/acquisition/orbit-attempts/m2-orb-001-recovery-002-20260906t183804z-e5883324.json"
INTAKE_REF = "contracts/m2-orbit-intake.json"
OFFLINE_REF = "contracts/m2-orbit-offline-verification.json"
RECOVERY_APPROVAL_REF = "records/source-gates/m2-orbit-recovery-003-approval.json"
ORBIT_APPROVAL_REF = "records/source-gates/m2-orbit-amendment-approval.json"
ROUTE_APPROVAL_REF = "records/source-gates/m2-radar-first-path-001-approval.json"
RADAR_READINESS_REF = "records/readiness/m2-radar-source-readiness-001.json"

SOURCE_ID = "M2-ORB-001"
ATTEMPT_ID = "m2-orb-001-recovery-002-20260906t183804z-e5883324"
PRODUCT_NAME = "S1D_OPER_AUX_RESORB_OPOD_20260816T143208_V20260816T103526_20260816T140956.EOF"
STAGED_SHA256 = "a72c93e500a1c09b62b4cd31889837c9d57ccc41542b16397ff9f2c0fccba3f4"
PROVIDER_MD5 = "ca7f36b1892073c883c4cff5c0517b9c"
PROVIDER_BLAKE3 = "ce824099fa812d6c229bd5bef2d4a70d7185d248f91ec3111ce557868ab1269b"
ENDPOINT_TOLERANCE_SECONDS = 1.0


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def load(ref: str) -> dict:
    value = json.loads((ROOT / ref).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {ref}")
    return value


def write_json(ref: str, value: dict) -> None:
    path = ROOT / ref
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def write_text(ref: str, value: str) -> None:
    path = ROOT / ref
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(value)


def font(name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default()


def render_surface(proposal_sha: str) -> None:
    image = Image.new("RGB", (1800, 1620), "#f4f1e9")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1800, 155), fill="#17324d")
    draw.text((65, 34), "M2 Orbit OSV Precision Review", font=font("arialbd.ttf", 48), fill="white")
    draw.text((67, 105), f"Proposal SHA-256 {proposal_sha}", font=font("arial.ttf", 20), fill="#dce8f2")
    y = 195
    sections = [
        ("Observed terminal result", [
            "Recovery-003 is consumed and cannot be retried. Exact M2-ORB-001 downloaded once into preserved staging.",
            "Size, provider MD5, and provider BLAKE3 match. No orbit file was promoted into custody.",
            "The frozen verifier failed because the final OSV ends 0.031829 seconds before the whole-second validity stop.",
        ]),
        ("Authoritative format evidence", [
            "Copernicus POD specifies whole-second header validity timestamps and microsecond OSV timestamps.",
            "The specification calls them consistent but does not explicitly prescribe rounding or a tolerance.",
        ]),
        ("What approval would authorize", [
            "Add an exact 1.0-second endpoint-consistency tolerance; retain all identity, XML, order, finite-value, and scene-margin checks.",
            "After synthetic tests and public CI, reinspect only the preserved staged bytes and conditionally promote them without replacement.",
            "No CDSE token, catalogue call, download request, or new acquisition attempt would occur.",
        ]),
        ("What remains prohibited", [
            "No recovery-003 retry, no tolerance above 1.0 second, and no M2-ORB-002 through 004 request.",
            "No precise-orbit substitution, orbit application, DEM action, radar pixels, baseline, change, attribution, or publication.",
        ]),
    ]
    for heading, lines in sections:
        draw.text((65, y), heading, font=font("arialbd.ttf", 29), fill="#17324d")
        y += 44
        for line in lines:
            for index, part in enumerate(textwrap.wrap(line, 110)):
                draw.text((92, y), ("• " if index == 0 else "  ") + part, font=font("arial.ttf", 24), fill="#20252b")
                y += 34
        y += 18
    draw.rectangle((60, 1460, 1740, 1565), outline="#9b6b21", width=3)
    draw.text((82, 1497), "Decision required: APPROVE, REVISE, or DEFER — with owner attestation.", font=font("arialbd.ttf", 25), fill="#7a4e0b")
    path = ROOT / IMAGE_REF
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared-at-utc", required=True)
    args = parser.parse_args()
    if not args.prepared_at_utc.endswith("Z"):
        raise SystemExit("prepared time must be UTC")
    outputs = [SOURCE_REF, PROPOSAL_REF, PREFLIGHT_REF, DOC_REF, IMAGE_REF, SURFACE_REF, BUNDLE_REF, CONTRACT_REF, BLANK_REF, READINESS_REF]
    collisions = [ref for ref in outputs if (ROOT / ref).exists()]
    if collisions:
        raise SystemExit("review output collision: " + ", ".join(collisions))

    outcome = load(OUTCOME_REF)
    control = load(CONTROL_REF)
    intake = load(INTAKE_REF)
    receipt = load(ATTEMPT_RECEIPT_REF)
    asset = next((item for item in intake.get("assets", []) if item.get("extensions", {}).get("source_id") == SOURCE_ID), None)
    attempt = next((item for item in (asset or {}).get("attempts", []) if item.get("attempt_id") == ATTEMPT_ID), None)
    if (
        outcome.get("status") != "terminal_failure_preserved_no_retry"
        or outcome.get("terminal_code") != "osv_times_do_not_span_validity"
        or outcome.get("attempt_id") != ATTEMPT_ID
        or outcome.get("assertions", {}).get("recovery_003_authority_consumed") is not True
        or control.get("status") != "reconciled_terminal_failure_active_intake_no_retry"
        or control.get("observations", {}).get("preserved_staged_file", {}).get("sha256") != STAGED_SHA256
        or not isinstance(asset, dict)
        or asset.get("state") != "failed"
        or not isinstance(attempt, dict)
        or attempt.get("outcome") != "failed"
        or receipt.get("failure_code") != "osv_times_do_not_span_validity"
    ):
        raise SystemExit("recovery-003 terminal evidence differs")

    source = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ORBIT-OSV-TIME-FORMAT-EVIDENCE-001",
        "observed_at_utc": args.prepared_at_utc,
        "status": "pass_authoritative_format_precision_observed_tolerance_is_explicit_inference",
        "authoritative_sources": [
            {
                "publisher": "Copernicus POD Service / GMV",
                "title": "Copernicus POD Service File Format Specification",
                "document_code": "GMV-CPOD3-FFS-0001",
                "version": "3.0",
                "date": "2023-07-21",
                "url": "https://sentiwiki.copernicus.eu/__attachments/1673407/GMV-CPOD3-FFS-0001%20-%20Copernicus%20POD%20Service%20File%20Format%20Specification%202023%20-%203.0.pdf",
                "observed_statements": [
                    "Validity_Start and Validity_Stop use whole-second UTC formatting.",
                    "Each OSV UTC value uses microsecond UTC formatting.",
                    "The header validity values must be consistent with the file validity dates.",
                ],
            },
            {
                "publisher": "Copernicus Data Space Ecosystem",
                "title": "Sentinel-1 documentation",
                "url": "https://documentation.dataspace.copernicus.eu/Data/Sentinel1.html",
                "observed_statements": ["AUX_RESORB is an offered Sentinel-1 POD orbit product in EOF form with a rolling archive policy."],
            },
        ],
        "local_observation": {
            "source_id": SOURCE_ID,
            "attempt_id": ATTEMPT_ID,
            "product_name": PRODUCT_NAME,
            "size_bytes": 639533,
            "sha256": STAGED_SHA256,
            "provider_md5": PROVIDER_MD5,
            "provider_blake3": PROVIDER_BLAKE3,
            "validity_start": "UTC=2026-08-16T10:35:26",
            "validity_stop": "UTC=2026-08-16T14:09:56",
            "osv_count": 1288,
            "first_osv_utc": "UTC=2026-08-16T10:35:25.968171",
            "last_osv_utc": "UTC=2026-08-16T14:09:55.968171",
            "validity_stop_shortfall_seconds": 0.031829,
            "scene_start_utc": "2026-08-16T12:21:16Z",
            "scene_end_utc": "2026-08-16T12:22:06Z",
            "minimum_required_scene_margin_seconds": 6350,
        },
        "interpretation": {
            "observation": "The exact checksum-matching file failed the frozen literal endpoint-span predicate solely at the final OSV boundary by 0.031829 seconds.",
            "inference": "A maximum one-second endpoint-consistency tolerance is compatible with the header's one-second representation and remains far smaller than the 6,350-second required scene margin.",
            "attribution": "No claim is made that Copernicus mandates one-second tolerance or that the orbit is scientifically fit; the tolerance is a proposed local validation interpretation requiring owner review.",
        },
        "limitations": [
            "The official specification describes precision and consistency but does not explicitly define rounding behavior or a numerical endpoint tolerance.",
            "The source pages were inspected online and are not treated as locally archived authoritative document bytes.",
            "Checksum agreement and format consistency do not establish orbit-application, radar-pixel, terrain-correction, or scientific fitness.",
        ],
    }
    write_json(SOURCE_REF, source)

    proposal = {
        "proposal_version": "1.0",
        "proposal_id": "NEPAL-M2-ORBIT-OSV-PRECISION-AMENDMENT-001-PROPOSAL",
        "prepared_at_utc": args.prepared_at_utc,
        "status": "proposed_not_authorized",
        "trigger": {
            "outcome_ref": OUTCOME_REF,
            "outcome_sha256": sha256(OUTCOME_REF),
            "terminal_control_reconciliation_ref": CONTROL_REF,
            "terminal_control_reconciliation_sha256": sha256(CONTROL_REF),
            "failed_reconciliation_ref": FAILED_RECONCILIATION_REF,
            "failed_reconciliation_sha256": sha256(FAILED_RECONCILIATION_REF),
            "source_evidence_ref": SOURCE_REF,
            "source_evidence_sha256": sha256(SOURCE_REF),
            "active_intake_ref": INTAKE_REF,
            "active_intake_sha256": sha256(INTAKE_REF),
            "source_id": SOURCE_ID,
            "attempt_id": ATTEMPT_ID,
            "terminal_code": "osv_times_do_not_span_validity",
            "recovery_003_authority_consumed": True,
        },
        "proposed_amendment": {
            "mode": "preserved_staged_bytes_validation_and_conditional_no_replace_promotion",
            "source_id": SOURCE_ID,
            "product_name": PRODUCT_NAME,
            "preserved_staged_sha256": STAGED_SHA256,
            "preserved_staged_size_bytes": 639533,
            "expected_provider_md5": PROVIDER_MD5,
            "expected_provider_blake3": PROVIDER_BLAKE3,
            "maximum_osv_endpoint_tolerance_seconds": ENDPOINT_TOLERANCE_SECONDS,
            "endpoint_rule": "require first_osv_utc <= validity_start_utc + 1 second and last_osv_utc >= validity_stop_utc - 1 second",
            "unchanged_checks": [
                "exact source, provider UUID, filename, size, MD5, BLAKE3, and locally recorded SHA-256",
                "safe XML without DTD or entity declarations",
                "exact mission, AUX_RESORB type, filename/header identity, and header validity values",
                "positive declared OSV count matching the actual list",
                "strictly increasing unique OSV times and finite position and velocity values with exact units",
                "exact scene binding and minimum 6,350-second scene margin",
                "atomic no-replace promotion into the already approved M2-ORB-001 custody destination",
            ],
            "implementation_gates": [
                "versioned contract and pure endpoint comparator",
                "synthetic tests for exact endpoints, sub-second acceptance, one-second boundary acceptance, and greater-than-one-second rejection",
                "full repository tests, secret-exposure scan, and successful public default-branch CI",
                "final local no-network preflight binding the exact preserved staging bytes and absent destination",
            ],
            "single_real_action": "one read-only validation of the exact preserved staged file followed by conditional atomic no-replace promotion and offline input-only verification if every check passes",
            "maximum_new_owner_handoffs": 0,
            "maximum_new_catalog_requests": 0,
            "maximum_new_download_requests": 0,
            "maximum_local_validation_attempts": 1,
            "automatic_retry_authorized": False,
            "failure_policy": "Any failed local validation or promotion is terminal for this amendment and requires another explicit review.",
        },
        "approval_would_authorize": [
            "implement and test only the exact one-second OSV endpoint-consistency amendment",
            "publish the exact implementation and require successful public CI before touching preserved staged bytes",
            "perform one final no-network preflight and one read-only validation of the exact preserved M2-ORB-001 staged file",
            "conditionally promote only those exact bytes without replacement and run the input-only offline verifier once if every amended check passes",
            "reconcile the single terminal local outcome without requesting another orbit source",
        ],
        "approval_would_not_authorize": [
            "retry, resume, or relaunch recovery-003",
            "obtain a token or make any CDSE catalogue or payload request",
            "change the tolerance above 1.0 second or change any other identity, checksum, XML, OSV, scene-margin, or destination rule",
            "request M2-ORB-002, M2-ORB-003, or M2-ORB-004",
            "delete, rewrite, hide, or replace the failed recovery-003 evidence or staged file",
            "substitute AUX_POEORB, apply orbit data, convert DEM data, decode radar pixels, create a baseline, analyze change, attribute cause, or publish a scientific result",
        ],
        "human_gate": {"review_required": True, "item_id": "M2-ORBIT-OSV-PRECISION-AMENDMENT-001", "allowed_decisions": ["approve", "revise", "defer"], "required_attestation": True},
        "limitations": source["limitations"] + [
            "The exact file remains failed staging evidence until a separate approval, implementation, public-CI gate, final preflight, and one local validation succeed.",
            "Even a passing promoted orbit file would establish input-only fitness, not corrected imagery, usable pixels, change, attribution, or scientific fitness.",
            "This proposal creates no implementation, local promotion, credential, network, other-orbit, or processing authority until the exact review receives a completed owner decision.",
        ],
    }
    write_json(PROPOSAL_REF, proposal)
    proposal_sha = sha256(PROPOSAL_REF)

    preflight = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ORBIT-OSV-PRECISION-AMENDMENT-001-REVIEW-PREFLIGHT",
        "observed_at_utc": args.prepared_at_utc,
        "status": "pass_review_ready_zero_decisions_no_network_or_payload_mutation",
        "bindings": {"proposal_sha256": proposal_sha, "source_evidence_sha256": sha256(SOURCE_REF), "outcome_sha256": sha256(OUTCOME_REF), "terminal_control_reconciliation_sha256": sha256(CONTROL_REF), "attempt_receipt_sha256": sha256(ATTEMPT_RECEIPT_REF), "active_intake_sha256": sha256(INTAKE_REF), "offline_verification_contract_sha256": sha256(OFFLINE_REF), "recovery_003_approval_sha256": sha256(RECOVERY_APPROVAL_REF), "orbit_amendment_approval_sha256": sha256(ORBIT_APPROVAL_REF), "radar_readiness_sha256": sha256(RADAR_READINESS_REF)},
        "assertions": {"human_decision_count": 0, "amendment_authorized": False, "credential_read": False, "network_request_performed": False, "payload_mutated": False, "staged_file_promoted": False, "other_orbit_source_requested": False, "radar_pixels_read": False, "scientific_result_established": False},
    }
    write_json(PREFLIGHT_REF, preflight)

    doc = f"""# M2 orbit OSV precision amendment-001 review

## Decision

Choose **approve**, **revise**, or **defer** for proposal `{proposal_sha}`. A completed decision must bind the exact review-bundle hash and include the owner's attestation.

## Preserved terminal result

Recovery-003 is terminal and consumed. Its one authorized request downloaded exact `M2-ORB-001` into append-only staging. The 639,533 bytes match provider MD5 `{PROVIDER_MD5}` and BLAKE3 `{PROVIDER_BLAKE3}` and have local SHA-256 `{STAGED_SHA256}`. The file was not promoted.

The frozen verifier returned `osv_times_do_not_span_validity`: the header stop is `UTC=2026-08-16T14:09:56`, while the last OSV is `UTC=2026-08-16T14:09:55.968171`, a 0.031829-second shortfall. The exact scene remains more than 6,350 seconds inside the declared validity interval.

## Source evidence and proposed interpretation

The [Copernicus POD Service File Format Specification](https://sentiwiki.copernicus.eu/__attachments/1673407/GMV-CPOD3-FFS-0001%20-%20Copernicus%20POD%20Service%20File%20Format%20Specification%202023%20-%203.0.pdf) specifies whole-second formatting for header validity timestamps and microsecond formatting for OSV timestamps. It calls the values consistent but does not state a numerical tolerance or rounding rule. The proposed one-second maximum is therefore an explicit local inference from representational precision, not a quoted provider requirement.

## What approval would authorize

Approval would authorize a versioned 1.0-second endpoint-consistency rule while leaving all identity, checksum, safe-XML, OSV order, finite-value, units, and scene-margin checks unchanged. After synthetic tests and successful public CI, one final no-network preflight could bind the existing staged bytes and absent destination. One local validation could then conditionally promote only those exact bytes without replacement and run input-only offline verification.

## Still prohibited

No token, catalogue request, payload request, recovery-003 retry, tolerance above one second, other orbit file, precise-orbit substitution, orbit application, DEM action, radar-pixel decoding, baseline, change analysis, attribution, or scientific publication is authorized by this review packet.
"""
    write_text(DOC_REF, doc)
    render_surface(proposal_sha)
    surface = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-OSV-PRECISION-AMENDMENT-001-REVIEW-SURFACE",
        "verified_at_utc": args.prepared_at_utc,
        "status": "pass_blank_review_surface",
        "artifact": {"path": IMAGE_REF, "sha256": sha256(IMAGE_REF), "width_px": 1800, "height_px": 1620, "format": "PNG", "contains_third_party_pixels": False},
        "bindings": {"proposal_ref": PROPOSAL_REF, "proposal_sha256": proposal_sha, "source_evidence_ref": SOURCE_REF, "source_evidence_sha256": sha256(SOURCE_REF), "outcome_ref": OUTCOME_REF, "outcome_sha256": sha256(OUTCOME_REF)},
        "validation": {"terminal_failure_visible": True, "observed_shortfall_visible": True, "source_precision_and_inference_separated": True, "zero_network_scope_visible": True, "prohibited_scope_visible": True, "blank_state_verified": True, "human_decision_count": 0, "completion_controls_verified": True, "export_verified": True},
    }
    write_json(SURFACE_REF, surface)

    artifacts = [
        ("review-surface", IMAGE_REF, "review_surface", True),
        ("review-instructions", DOC_REF, "decision_instructions", False),
        ("proposal", PROPOSAL_REF, "candidate_authority_envelope", False),
        ("review-preflight", PREFLIGHT_REF, "zero_authority_preflight", False),
        ("source-evidence", SOURCE_REF, "authoritative_format_and_local_observation", False),
        ("recovery-003-outcome", OUTCOME_REF, "terminal_failure_outcome", False),
        ("terminal-control-reconciliation", CONTROL_REF, "active_intake_truth_reconciliation", False),
        ("failed-outcome-reconciliation", FAILED_RECONCILIATION_REF, "preserved_control_failure", False),
        ("attempt-receipt", ATTEMPT_RECEIPT_REF, "terminal_attempt_receipt", False),
        ("active-orbit-intake", INTAKE_REF, "terminal_failed_source_state", False),
        ("offline-verification-contract", OFFLINE_REF, "frozen_strict_rule_context", False),
        ("recovery-003-approval", RECOVERY_APPROVAL_REF, "consumed_recovery_authority", False),
        ("orbit-amendment-approval", ORBIT_APPROVAL_REF, "original_exact_source_authority", False),
        ("radar-source-readiness", RADAR_READINESS_REF, "route_prerequisite", False),
    ]
    bundle = {
        "schema_version": "1.0",
        "template": False,
        "bundle_id": "m2-orbit-osv-precision-amendment-001-review-bundle",
        "review_id": "m2-orbit-osv-precision-amendment-001-review",
        "authority_ref": ROUTE_APPROVAL_REF,
        "candidate_identity": f"M2-ORBIT-OSV-PRECISION-AMENDMENT-001-PROPOSAL-SHA256:{proposal_sha}",
        "artifacts": [{"artifact_id": artifact_id, "path": ref, "sha256": sha256(ref), "role": role, "render_required": rendered, "render_receipts": [{"path": SURFACE_REF, "sha256": sha256(SURFACE_REF)}] if rendered else []} for artifact_id, ref, role, rendered in artifacts],
        "review_surface": {"artifact_id": "review-surface", "blank_state_verified": True, "completion_controls_verified": True, "export_verified": True},
        "limitations": proposal["approval_would_not_authorize"] + proposal["limitations"],
    }
    write_json(BUNDLE_REF, bundle)
    bundle_sha = sha256(BUNDLE_REF)
    contract = {
        "contract_version": "human-review-contract-v1",
        "template": False,
        "review_id": "m2-orbit-osv-precision-amendment-001-review",
        "response_schema_version": "nepal-m2-orbit-osv-precision-amendment-001-response-v1",
        "workflow_authority": {"mode": "inherited", "authority_ref": ROUTE_APPROVAL_REF, "authorized_action_classes": ["evidence_recording", "project_control", "update_project_records"], "verified_at_utc": args.prepared_at_utc, "expires_at_utc": None, "review_required": True, "lock_authorized": True, "reconcile_authorized": True, "post_review_actions": ["evidence_recording", "project_control", "update_project_records"]},
        "review_bundle": {"bundle_id": bundle["bundle_id"], "manifest_sha256": bundle_sha, "candidate_identity": bundle["candidate_identity"], "rendered_surface_verified": True},
        "allowed_decisions": ["approve", "revise", "defer"],
        "required_attestation": True,
        "max_notes_length": 2000,
        "hash_prefix_length": 16,
        "items": [{"item_id": "M2-ORBIT-OSV-PRECISION-AMENDMENT-001", "evidence_sha256": bundle_sha}],
    }
    write_json(CONTRACT_REF, contract)
    blank = {"response_schema_version": contract["response_schema_version"], "review_id": contract["review_id"], "completed": False, "review_started_at_utc": None, "review_completed_at_utc": None, "reviewer": {"attestation": False}, "responses": [{"item_id": "M2-ORBIT-OSV-PRECISION-AMENDMENT-001", "evidence_sha256": bundle_sha, "decision": None, "notes": ""}]}
    write_json(BLANK_REF, blank)
    readiness = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ORBIT-OSV-PRECISION-AMENDMENT-001-REVIEW-READINESS",
        "verified_at_utc": args.prepared_at_utc,
        "status": "pass_ready_owner_review_zero_decisions_public_ci_pending",
        "bindings": {"proposal_sha256": proposal_sha, "source_evidence_sha256": sha256(SOURCE_REF), "outcome_sha256": sha256(OUTCOME_REF), "terminal_control_reconciliation_sha256": sha256(CONTROL_REF), "preflight_sha256": sha256(PREFLIGHT_REF), "review_surface_sha256": sha256(IMAGE_REF), "surface_receipt_sha256": sha256(SURFACE_REF), "review_bundle_sha256": bundle_sha, "review_contract_sha256": sha256(CONTRACT_REF), "blank_response_sha256": sha256(BLANK_REF)},
        "review": {"human_decision_count": 0, "attestation": False, "ready_for_publication_gate": True},
        "assertions": {"recovery_003_terminal_preserved": True, "amendment_authorized": False, "credential_read": False, "network_request_performed": False, "payload_mutated": False, "staged_file_promoted": False, "other_orbit_source_requested": False, "radar_pixels_read": False, "scientific_result_established": False},
    }
    write_json(READINESS_REF, readiness)
    print(json.dumps({"status": readiness["status"], "proposal_sha256": proposal_sha, "review_bundle_sha256": bundle_sha, "review_contract_sha256": sha256(CONTRACT_REF)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
