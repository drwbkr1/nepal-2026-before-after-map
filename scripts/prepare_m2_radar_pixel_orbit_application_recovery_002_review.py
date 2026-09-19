#!/usr/bin/env python3
"""Prepare the local zero-decision radar processing recovery-002 review packet."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import textwrap
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-pixel-orbit-application-recovery-002"
PROPOSAL_REF = f"contracts/milestone-002-radar-pixel-orbit-application-recovery-002-proposal.json"
PREPARATION_APPROVAL_REF = f"records/source-gates/{PREFIX}-review-preparation-approval.json"
PREFLIGHT_REF = f"records/readiness/{PREFIX}-review-preflight.json"
DOC_REF = "docs/M2_RADAR_PIXEL_ORBIT_APPLICATION_RECOVERY_002_REVIEW.md"
IMAGE_REF = f"docs/assets/{PREFIX}-review.png"
SURFACE_REF = f"records/surface-receipts/{PREFIX}-review.json"
BUNDLE_REF = f"reviews/{PREFIX}/review-bundle.json"
CONTRACT_REF = f"reviews/{PREFIX}/review-contract.json"
BLANK_REF = f"reviews/{PREFIX}/blank-response.json"
READINESS_REF = f"records/readiness/{PREFIX}-review-readiness.json"

RADAR_TERMINAL_REF = "records/processing/m2-radar-pixel-orbit-application-recovery-001-terminal-reconciliation.json"
RADAR_OUTCOME_REF = "records/processing/m2-radar-pixel-orbit-application-recovery-001-outcome-reconciliation.json"
RADAR_TERMINAL_GATE_REF = "records/readiness/m2-radar-pixel-orbit-application-recovery-001-terminal-publication-gate.json"
PROBE_TERMINAL_REF = "records/processing/m2-radar-delayed-import-probe-receipt-recovery-001-terminal-reconciliation.json"
PROBE_OUTCOME_REF = "records/processing/m2-radar-delayed-import-probe-receipt-recovery-001-outcome-reconciliation.json"
PROBE_TERMINAL_GATE_REF = "records/readiness/m2-radar-delayed-import-probe-receipt-recovery-001-terminal-publication-gate.json"
LAUNCH_OBSERVATION_REF = "records/readiness/m2-radar-pixel-orbit-application-recovery-001-terminal-launch-context-observation-004.json"
LOG_OBSERVATION_REF = "records/readiness/m2-radar-pixel-orbit-application-recovery-001-terminal-local-log-observation-005.json"
MILESTONE_REF = "contracts/milestone-002.json"
PROFILE_REF = "records/project-control-profile.json"
GOAL_REF = "records/long-term-goal.json"

BASE_COMMIT = "b3bb7b393f72220306c53aefe1626ddf6df281c4"
CURRENT_CHECKPOINT = "M2-RADAR-DELAYED-IMPORT-PROBE-RECEIPT-RECOVERY-001-TERMINAL-REVIEW"
CONSUMED_RADAR_ATTEMPT = "radar-pixel-orbit-application-recovery-001-real-001"
CONSUMED_PROBE_ATTEMPT = "radar-delayed-import-probe-receipt-recovery-001-real-001"
PROPOSED_ATTEMPT = "radar-pixel-orbit-application-recovery-002-real-001"
SOURCE_ORDER = [f"M1-SRC-{index:03d}" for index in range(1, 7)]
ROUTE_ORDER = ["PAIR-S1-ASC-R085-IW", "PAIR-S1-DESC-R121-IW"]
CORPUS_FILE_COUNT = 156
CORPUS_LOGICAL_BYTES = 10_367_157_634
CORPUS_SHA256 = "dd56f8b28a1ed1c6e2b4b1d7d8f5db4fd86dab80a910fe79c8d018d58942430b"
PROTECTED_HASHES = {
    "config/qa/m2-radar-pixel-orbit-application-001-contract.json": "a25f86588979fd4b5cfb45c999a862d83d71be31925a5b39565970de526f8fb1",
    "config/qa/m2-radar-pixel-orbit-application-recovery-001-contract.json": "f2fb1b796aedc2c760d3680cccefcc4558fc83beb6107663ca4e0a6d9f7d7d81",
    "scripts/m2_radar_pixel_orbit_application_001_core.py": "fd192878acf33e2c73eeeba1ec42865eac48dfc5742b3ae4cf54b51de42755ba",
    "scripts/run_m2_radar_pixel_orbit_application_001.py": "0b65fbecbeab373d8bbbf2cbbc28f8817e3c3bb08584dbf1a9720dcbb19ceb06",
    "scripts/m2_radar_pixel_orbit_application_recovery_001_core.py": "9033c5b8b8b1bf066aae00f1db67791be4ce5ada1507762c8f68279089e63993",
    "scripts/run_m2_radar_pixel_orbit_application_recovery_001.py": "821aea00e0b3f0a0992da48990aaf6b2b547ffc09d9446438672f8bf2a3ea195",
    "tests/test_m2_radar_pixel_orbit_application_recovery_001.py": "792913f322c219fed067861e2a2a16c5f23c2436df2323a2c2611d091aa201f7",
    RADAR_TERMINAL_REF: "3bd2a4cc6bd56d7ec5ae95a316ff3f5b3cc788b94d32436b3cf02586d7a391c0",
    RADAR_OUTCOME_REF: "ef5b7601ce6073c2736297406ac3324f03ca1a84eaa6e7c3dbc35a1a07601d19",
    RADAR_TERMINAL_GATE_REF: "2d757b464ef71a8f8305145698c2205d4034dc492b51b82fc9261741f3133ade",
    PROBE_TERMINAL_REF: "a942a1827a72462e32caaed7690e785e7bc0c18df04224125a18131eeb09be26",
    PROBE_OUTCOME_REF: "7d7028afdca5b880b2d4d1da69d404db72adf3b5210234cb2a88403c541696b3",
    PROBE_TERMINAL_GATE_REF: "9a0c430452eac76aed9196ca990398c026e166f3b2ec3abf22dd0bbe8a8e5a42",
    "config/qa/m2-radar-delayed-import-probe-receipt-recovery-001-contract.json": "beb21c963cc2302e5290116cda9e08229eb3af8503a410ea6dfa9ed55541a56c",
}


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def load(ref: str) -> dict[str, Any]:
    value = json.loads((ROOT / ref).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {ref}")
    return value


def write_json(ref: str, value: dict[str, Any]) -> None:
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


def git_value(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def render_surface(proposal_sha: str, radar_terminal_sha: str, probe_outcome_sha: str) -> None:
    from PIL import Image, ImageDraw, ImageFont

    def font(name: str, size: int):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            return ImageFont.load_default()

    image = Image.new("RGB", (1800, 2040), "#f4f1e9")
    draw = ImageDraw.Draw(image)
    title = font("arialbd.ttf", 42)
    heading = font("arialbd.ttf", 28)
    body = font("arial.ttf", 22)
    small = font("arial.ttf", 18)
    callout = font("arialbd.ttf", 24)
    draw.rectangle((0, 0, 1800, 190), fill="#17324d")
    draw.text((62, 24), "M2 Radar Processing Recovery 002", font=title, fill="white")
    draw.text((64, 98), f"Proposal {proposal_sha}", font=small, fill="#dce8f2")
    draw.text((64, 130), f"Consumed radar terminal {radar_terminal_sha}", font=small, fill="#dce8f2")
    draw.text((64, 160), f"Disposable probe outcome {probe_outcome_sha}", font=small, fill="#dce8f2")
    sections = [
        ("Observed evidence", [
            "Radar recovery-001 is terminal and consumed. Exact source, orbit, and DEM identity verification passed, then ArcGIS setup stopped before the first source with Product License has not been initialized.",
            "The historical receipt does not identify the exact failing ArcPy statement. No source receipt, route receipt, child directory, or derived raster was created.",
            "A later one-process disposable probe fully hashed the same file count and byte total before ArcPy import, reported ArcInfo, checked out both extensions, created two rasters and one mosaic, and cleaned up successfully.",
            "That later pass is host-time diagnostic evidence only. It does not prove the earlier cause or establish radar recovery readiness.",
        ]),
        ("Proposed recovery-002", [
            "Preserve both consumed attempts and all existing scientific contracts byte-for-byte.",
            "Add a new runner with pre-reserved terminal and cleanup identities, an append-only fallback journal, and durable markers around identity scan, ArcPy import, product check, extension checkouts, DEM mosaic, analysis support, each source, and each route.",
            "Retain the successful diagnostic sequence: exact full identity scan before ArcPy import. Keep the strict recovery-001 inventory comparator unchanged.",
            "After separate publication, public CI, exact owner approval, implementation CI, and final no-content preflight, allow one fresh recovery-002 attempt over the same six sources and two routes, stopping on the first failure.",
        ]),
        ("Still prohibited", [
            "No reuse or retry of either consumed attempt; no automatic retry; no source, orbit, DEM, AOI, CRS, grid, mask, threshold, route, or scientific-predicate substitution.",
            "No network, credential, account, terms, installation, or UAC action.",
            "A pass would establish only radar input and route QA for later owner review. Baseline admission, change analysis, interpretation, attribution, derived-pixel release, and scientific publication remain separate gates.",
        ]),
    ]
    y = 228
    for label, lines in sections:
        draw.text((64, y), label, font=heading, fill="#17324d")
        y += 46
        for line in lines:
            for index, part in enumerate(textwrap.wrap(line, 104)):
                draw.text((92, y), ("• " if index == 0 else "  ") + part, font=body, fill="#20252b")
                y += 34
        y += 18
    draw.rectangle((60, 1816, 1740, 1965), outline="#9b6b21", width=3)
    draw.text((82, 1842), "Current authority: local zero-decision packet preparation and validation only.", font=callout, fill="#7a4e0b")
    draw.text((82, 1886), "Next gate: explicit authorization to publish this exact packet and run public CI.", font=callout, fill="#7a4e0b")
    draw.text((82, 1930), "Project-data access, ArcPy, implementation, and any attempt remain prohibited.", font=small, fill="#7a4e0b")
    path = ROOT / IMAGE_REF
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared-at-utc", required=True)
    args = parser.parse_args()
    if not args.prepared_at_utc.endswith("Z"):
        raise SystemExit("prepared time must be UTC")

    outputs = [
        PREPARATION_APPROVAL_REF, PROPOSAL_REF, PREFLIGHT_REF, DOC_REF, IMAGE_REF,
        SURFACE_REF, BUNDLE_REF, CONTRACT_REF, BLANK_REF, READINESS_REF,
    ]
    collisions = [ref for ref in outputs if (ROOT / ref).exists()]
    if collisions:
        raise SystemExit("review output collision: " + ", ".join(collisions))

    head = git_value("rev-parse", "HEAD")
    origin = git_value("rev-parse", "origin/main")
    preexisting = set(
        subprocess.run(
            ["git", "status", "--porcelain=v1"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    )
    allowed_preexisting = {
        " M docs/ROADMAP.md",
        "?? docs/GEOSPATIAL_HELPER_REUSE.md",
        "?? scripts/prepare_m2_radar_pixel_orbit_application_recovery_002_review.py",
    }
    if head != BASE_COMMIT or origin != BASE_COMMIT or preexisting != allowed_preexisting:
        raise SystemExit("preparation base is not the exact public terminal checkpoint plus the two preserved unrelated changes")
    if {ref: sha256(ref) for ref in PROTECTED_HASHES} != PROTECTED_HASHES:
        raise SystemExit("protected radar or diagnostic evidence changed")

    radar_terminal = load(RADAR_TERMINAL_REF)
    radar_outcome = load(RADAR_OUTCOME_REF)
    radar_gate = load(RADAR_TERMINAL_GATE_REF)
    probe_terminal = load(PROBE_TERMINAL_REF)
    probe_outcome = load(PROBE_OUTCOME_REF)
    probe_gate = load(PROBE_TERMINAL_GATE_REF)
    milestone = load(MILESTONE_REF)
    profile = load(PROFILE_REF)
    goal = load(GOAL_REF)
    if (
        radar_terminal.get("status") != "failed_supervisor_no_retry"
        or radar_terminal.get("failure_message") != "The Product License has not been initialized."
        or radar_outcome.get("status") != "block_terminal_arcgis_product_license_not_initialized_no_retry"
        or radar_outcome.get("assertions", {}).get("attempt_consumed") is not True
        or radar_outcome.get("assertions", {}).get("source_processing_started") is not False
        or radar_gate.get("status") != "pass_public_terminal_state_owner_review_only"
        or probe_terminal.get("status") != "pass_exact_receipt_recovery_probe_no_retry"
        or probe_outcome.get("status") != "pass_exact_receipt_recovery_probe_no_retry"
        or probe_outcome.get("claim_boundary", {}).get("radar_recovery_readiness_established") is not False
        or probe_gate.get("status") != "pass_public_terminal_state_owner_review_only"
        or milestone.get("handoff", {}).get("current_checkpoint") != CURRENT_CHECKPOINT
        or profile.get("current_checkpoint", {}).get("checkpoint_id") != CURRENT_CHECKPOINT
        or goal.get("current_checkpoint") != CURRENT_CHECKPOINT
    ):
        raise SystemExit("terminal evidence or canonical checkpoint is not the exact preparation base")

    preparation_approval = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-002-REVIEW-PREPARATION-APPROVAL",
        "recorded_at_utc": args.prepared_at_utc,
        "status": "approved_local_zero_decision_review_preparation_only",
        "authority_basis": {
            "owner_instruction": "I authorize preparation of an M2 radar pixel and orbit application recovery-002 review packet based on the public receipt-recovery terminal evidence.",
            "owner_scope": "local zero-decision proposal and review preparation and validation only",
            "owner_exclusions": "no Git publication, project-data or external-custody access, ArcPy execution, new real attempt, radar processing, baseline or change analysis, attribution, or scientific publication",
            "attestation": True,
        },
        "approved_scope": [
            "prepare one local zero-decision M2 radar pixel and orbit application recovery-002 review packet",
            "render and locally validate the packet without project or external data",
            "record exact proposal and bundle identities for a later publication decision",
        ],
        "authority_boundary": {
            "local_review_packet_preparation_authorized": True,
            "local_validation_authorized": True,
            "git_commit_authorized": False,
            "public_review_packet_publication_authorized": False,
            "public_ci_authorized": False,
            "owner_proposal_decision_recording_authorized": False,
            "recovery_implementation_authorized": False,
            "arcpy_invocation_authorized": False,
            "new_attempt_authorized": False,
            "project_data_or_external_custody_access_authorized": False,
            "radar_processing_authorized": False,
            "baseline_or_change_authorized": False,
            "scientific_publication_authorized": False,
        },
        "bindings": {
            "radar_terminal_reconciliation_sha256": sha256(RADAR_TERMINAL_REF),
            "radar_outcome_reconciliation_sha256": sha256(RADAR_OUTCOME_REF),
            "radar_terminal_publication_gate_sha256": sha256(RADAR_TERMINAL_GATE_REF),
            "probe_terminal_reconciliation_sha256": sha256(PROBE_TERMINAL_REF),
            "probe_outcome_reconciliation_sha256": sha256(PROBE_OUTCOME_REF),
            "probe_terminal_publication_gate_sha256": sha256(PROBE_TERMINAL_GATE_REF),
            "base_commit": head,
        },
    }
    write_json(PREPARATION_APPROVAL_REF, preparation_approval)

    stage_order = [
        "attempt_reserved", "terminal_and_cleanup_receipts_reserved", "fallback_journal_initialized",
        "identity_scan_started", "identity_scan_completed", "arcpy_import_started", "arcpy_import_completed",
        "product_info_started", "product_info_completed", "image_analyst_checkout_started",
        "image_analyst_checkout_completed", "spatial_checkout_started", "spatial_checkout_completed",
        "dem_mosaic_started", "dem_mosaic_completed", "analysis_support_started", "analysis_support_completed",
        "source_processing_fixed_order", "route_evaluation_fixed_order", "postattempt_identity_scan_started",
        "postattempt_identity_scan_completed", "terminal_receipt_persisted", "cleanup_started",
        "cleanup_completed_or_warning",
    ]
    proposal = {
        "schema_version": "1.0",
        "proposal_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-002-PROPOSAL",
        "prepared_at_utc": args.prepared_at_utc,
        "status": "proposed_inactive_local_review_prepared_publication_and_owner_approval_required",
        "preparation_base_commit": head,
        "preparation_authority": {
            "ref": PREPARATION_APPROVAL_REF,
            "sha256": sha256(PREPARATION_APPROVAL_REF),
            "local_preparation_only": True,
            "public_publication_authorized": False,
            "implementation_authorized": False,
            "new_attempt_authorized": False,
        },
        "trigger": {
            "radar_terminal_reconciliation_ref": RADAR_TERMINAL_REF,
            "radar_terminal_reconciliation_sha256": sha256(RADAR_TERMINAL_REF),
            "radar_outcome_reconciliation_ref": RADAR_OUTCOME_REF,
            "radar_outcome_reconciliation_sha256": sha256(RADAR_OUTCOME_REF),
            "radar_terminal_publication_gate_ref": RADAR_TERMINAL_GATE_REF,
            "radar_terminal_publication_gate_sha256": sha256(RADAR_TERMINAL_GATE_REF),
            "probe_terminal_reconciliation_ref": PROBE_TERMINAL_REF,
            "probe_terminal_reconciliation_sha256": sha256(PROBE_TERMINAL_REF),
            "probe_outcome_reconciliation_ref": PROBE_OUTCOME_REF,
            "probe_outcome_reconciliation_sha256": sha256(PROBE_OUTCOME_REF),
            "probe_terminal_publication_gate_ref": PROBE_TERMINAL_GATE_REF,
            "probe_terminal_publication_gate_sha256": sha256(PROBE_TERMINAL_GATE_REF),
        },
        "observed_state": {
            "consumed_radar_attempt_id": CONSUMED_RADAR_ATTEMPT,
            "radar_attempt_terminal_and_consumed": True,
            "radar_failure_message": "The Product License has not been initialized.",
            "radar_failure_exact_arcpy_statement_known": False,
            "source_processing_attempts_started": 0,
            "route_evaluations_started": 0,
            "derived_raster_count": 0,
            "postattempt_source_orbit_dem_identities_match": True,
            "consumed_probe_attempt_id": CONSUMED_PROBE_ATTEMPT,
            "probe_attempt_terminal_and_consumed": True,
            "probe_delayed_import_sequence_passed": True,
            "probe_corpus_file_count": CORPUS_FILE_COUNT,
            "probe_corpus_total_logical_bytes": CORPUS_LOGICAL_BYTES,
            "probe_corpus_aggregate_sha256": CORPUS_SHA256,
            "probe_arcgis_product": "ArcInfo",
            "probe_disposable_rasters_created": 2,
            "probe_disposable_mosaic_created": True,
            "probe_payload_children_removed": True,
            "historical_root_cause_established": False,
            "radar_recovery_readiness_established": False,
            "post_observation_bias": "The proposal is informed by two consumed failures and a later disposable diagnostic pass; it is not blind or independent validation.",
        },
        "protected_public_evidence": [
            {"path": ref, "sha256": digest, "must_remain_unchanged_during_preparation": True}
            for ref, digest in PROTECTED_HASHES.items()
        ],
        "proposed_exact_changes": [
            "preserve the base radar attempt, recovery-001 attempt, disposable probe attempts, all public receipts, and all existing scientific contracts unchanged",
            "implement a new recovery-002 wrapper that reuses the strict recovery-001 three-field sorted inventory comparator and the unchanged base radar processing and QA functions",
            "before project-data content reads, exclusively reserve the new attempt root, terminal and cleanup receipt identities, durable stage journal, and append-only fallback journal",
            "record durable monotonic markers around the identity scan, ArcPy import, product query, extension checkout, DEM mosaic, analysis support, each fixed-order source, each fixed-order route, postattempt identity scan, terminal persistence, and cleanup",
            "preserve the evidenced delayed-import order by completing the exact full identity scan before ArcPy import; do not infer that this sequence caused or cured the historical failure",
            "use function-local timestamp construction, sanitize and append the first exception before terminal assembly, preserve any later persistence failure without replacement, and run cleanup independently",
            "add portable synthetic tests for exact ordering, stop-on-first-failure, one-attempt enforcement, interruption, first-error retention, terminal-write failure, cleanup independence, and secret or project-path rejection",
            "add one installed ArcGIS-runtime synthetic test that exercises setup stage markers and durable failure receipts with only disposable inputs and no project or external data",
            "require successful local validation, separately authorized public packet publication and CI, exact attested owner approval, implementation and tests, successful implementation CI, and one final no-content preflight before any project-data read",
            "only on every gate run at most one fresh recovery-002 attempt over the exact six sources and two routes in their unchanged order, stopping on the first failure",
            "reconcile the outcome and stop before baseline admission or change analysis even if all six sources and both routes pass",
        ],
        "future_gate_sequence": [
            "explicit owner authorization to commit and publish this exact zero-decision packet and run public default-branch CI",
            "successful public default-branch CI on the exact packet commit",
            "exact attested owner approval of the published review bundle and proposal",
            "bounded recovery-002 implementation plus portable and installed ArcGIS-runtime synthetic validation",
            "successful public default-branch CI on the exact implementation commit",
            "one final no-content preflight",
            "at most one fresh exact-source recovery-002 attempt",
        ],
        "exact_recovery_contract": {
            "attempt_id": PROPOSED_ATTEMPT,
            "consumed_attempt_ids": [CONSUMED_RADAR_ATTEMPT, CONSUMED_PROBE_ATTEMPT],
            "distinct_from_consumed_attempts": True,
            "process_count": 1,
            "fixed_source_order": SOURCE_ORDER,
            "fixed_route_order": ROUTE_ORDER,
            "stage_order": stage_order,
            "delayed_arcpy_import_after_exact_identity_scan": True,
            "inventory_comparator_unchanged_from_recovery_001": True,
            "scientific_contracts_unchanged": {
                "crs": "EPSG:32645",
                "grid_resolution_metres": 10,
                "source_orbit_dem_aoi_mask_threshold_registration_and_route_substitution_allowed": False,
            },
            "receipt_durability": {
                "terminal_identity_reserved_before_project_data_read": True,
                "cleanup_identity_reserved_before_project_data_read": True,
                "stage_journal_initialized_before_project_data_read": True,
                "fallback_journal_initialized_before_project_data_read": True,
                "first_sanitized_exception_recorded_before_normal_terminal_assembly": True,
                "persistence_errors_append_without_replacing_first_exception": True,
                "cleanup_outer_finally_independent_of_terminal_serialization": True,
                "fallback_is_success_evidence": False,
            },
            "result_semantics": {
                "pass": "all six exact sources and both frozen routes completed input and QA processing for later owner review only",
                "block": "the new attempt's durable receipts identify its observed boundary only",
                "historical_root_cause_claim_allowed": False,
                "baseline_admission_allowed": False,
                "change_analysis_allowed": False,
                "scientific_claim_allowed": False,
            },
        },
        "limits": {
            "consumed_attempt_retries_or_reuses": 0,
            "future_real_attempts": 1,
            "automatic_retry": False,
            "processes": 1,
            "source_processing_attempts_per_source": 1,
            "route_evaluation_attempts_per_route": 1,
            "stop_on_first_failure": True,
            "network_requests": 0,
            "credential_or_token_actions": 0,
            "software_installations": 0,
            "uac_actions": 0,
            "source_overwrites": 0,
            "external_custody_mutations": 0,
            "baseline_or_change_actions": 0,
            "scientific_outputs": 0,
        },
        "stop_rules": [
            "Stop before Git commit, push, public CI, implementation, ArcPy import, project-data or external-custody access, or a new attempt under the present preparation-only authority.",
            "Stop if any protected radar or diagnostic artifact identity differs from this proposal.",
            "Do not reconstruct the exact historical failing ArcPy statement or reinterpret either consumed attempt as retryable.",
            "Do not run a second recovery-002 attempt after any pass, block, interruption, or persistence failure.",
            "Stop after terminal reconciliation even on pass; baseline admission and change analysis remain separately gated.",
        ],
        "does_not_authorize_now": [
            "Git commit, push, public review publication, or public CI",
            "owner proposal approval, response locking, activation, implementation, ArcPy invocation, preflight, project-data read, or a live attempt",
            "reuse, resume, retry, mutation, or reconstruction of either consumed attempt",
            "project-data or external-custody access, network, credentials, account, terms, installation, or UAC action",
            "source, orbit, DEM, AOI, CRS, grid, mask, threshold, registration, route, or scientific-predicate substitution",
            "baseline admission, change analysis, interpretation, attribution, emergency guidance, derived-pixel publication, or scientific publication",
            "a historical root-cause, radar-recovery-readiness, change, attribution, or scientific claim",
        ],
        "decision_domain_after_public_ci": ["approve", "revise", "defer"],
        "attestation_required_after_public_ci": True,
        "human_decision_count": 0,
    }
    write_json(PROPOSAL_REF, proposal)
    proposal_sha = sha256(PROPOSAL_REF)

    preflight = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-002-REVIEW-PREFLIGHT",
        "checked_at_utc": args.prepared_at_utc,
        "status": "pass_ready_local_zero_decision_packet_preparation_only",
        "bindings": {
            "preparation_approval_ref": PREPARATION_APPROVAL_REF,
            "preparation_approval_sha256": sha256(PREPARATION_APPROVAL_REF),
            "proposal_ref": PROPOSAL_REF,
            "proposal_sha256": proposal_sha,
            "radar_terminal_reconciliation_sha256": sha256(RADAR_TERMINAL_REF),
            "radar_outcome_reconciliation_sha256": sha256(RADAR_OUTCOME_REF),
            "radar_terminal_publication_gate_sha256": sha256(RADAR_TERMINAL_GATE_REF),
            "probe_terminal_reconciliation_sha256": sha256(PROBE_TERMINAL_REF),
            "probe_outcome_reconciliation_sha256": sha256(PROBE_OUTCOME_REF),
            "probe_terminal_publication_gate_sha256": sha256(PROBE_TERMINAL_GATE_REF),
            "preparation_script_sha256": sha256("scripts/prepare_m2_radar_pixel_orbit_application_recovery_002_review.py"),
            "base_commit": head,
        },
        "checks": {
            "radar_attempt_consumed": True,
            "probe_attempt_consumed": True,
            "radar_exact_failure_statement_unresolved": True,
            "probe_delayed_import_sequence_passed": True,
            "probe_recovery_readiness_claim_prohibited": True,
            "protected_public_evidence_exact": True,
            "canonical_checkpoint_unchanged": True,
            "local_preparation_authorized": True,
            "publication_or_implementation_authorized": False,
        },
        "assertions": {
            "git_commit_created": False,
            "git_push_performed": False,
            "public_ci_started": False,
            "protected_radar_or_probe_code_modified": False,
            "arcpy_invoked": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "new_attempt_created": False,
            "radar_processing_executed": False,
            "implementation_authorized": False,
            "scientific_result_established": False,
        },
    }
    write_json(PREFLIGHT_REF, preflight)

    document = f"""# M2 radar pixel and orbit application recovery-002 review

**Proposal SHA-256:** `{proposal_sha}`  
**Consumed radar terminal SHA-256:** `{sha256(RADAR_TERMINAL_REF)}`  
**Disposable probe outcome SHA-256:** `{sha256(PROBE_OUTCOME_REF)}`  
**Decision state:** zero decisions; prepared locally; publication is not authorized

## Evidence reviewed

The exact `recovery-001` radar attempt is terminal and consumed. It verified the six source inventories, four orbit files, and four DEM derivatives, then stopped during ArcGIS setup with `The Product License has not been initialized.` before the first source-processing receipt. The durable record does not identify the exact failing ArcPy statement. No route evaluation or derived raster began.

A later, separately controlled disposable probe reproduced the observed sequence difference without project data: it fully hashed {CORPUS_FILE_COUNT} files totaling {CORPUS_LOGICAL_BYTES:,} logical bytes before ArcPy import, matched aggregate SHA-256 `{CORPUS_SHA256}`, reported `ArcInfo`, checked out Image Analyst and Spatial Analyst, created two disposable rasters and one mosaic, persisted terminal and cleanup receipts, and removed all payload children.

That pass is evidence that the installed runtime completed the delayed-import disposable sequence on the current host at that later time. It does not establish the earlier failure's cause, prove project-data processing, or establish radar recovery readiness.

## Proposed bounded recovery-002

The proposed implementation would preserve both consumed attempts and all existing scientific contracts. It would create a new recovery-002 wrapper around the unchanged strict recovery-001 inventory comparator and base radar-processing functions. Before any project-data content read, it would reserve the new attempt, terminal and cleanup identities, a durable stage journal, and an append-only fallback journal.

Durable markers would surround the exact identity scan, delayed ArcPy import, product query, extension checkouts, DEM mosaic, analysis-support creation, every fixed-order source, both fixed-order routes, postattempt identity verification, terminal persistence, and cleanup. The first sanitized failure would be appended before ordinary terminal construction; later persistence failures could not replace it, and cleanup would run independently.

After separate packet-publication authority, successful public CI, exact attested owner approval, bounded implementation and synthetic validation, successful implementation CI, and one final no-content preflight, the project could run at most one fresh attempt: `{PROPOSED_ATTEMPT}`. It would use the same six sources `{', '.join(SOURCE_ORDER)}` and routes `{', '.join(ROUTE_ORDER)}` in the unchanged order, with no substitution or automatic retry.

## Claim and release limits

A pass would establish only that the exact radar input-processing and two frozen QA routes completed for later owner review. It would not admit a baseline or authorize change analysis. A block would identify the new attempt's durable boundary only. Neither outcome would establish the historical root cause, causal attribution, or a scientific result.

The current authority permits only local packet preparation and validation. It does not permit Git publication, public CI, implementation, ArcPy, project-data or external-custody access, a new attempt, radar processing, baseline or change analysis, attribution, or scientific publication.

The next required decision is whether to commit and publish this exact zero-decision packet and run public default-branch CI. The later `approve`, `revise`, or `defer` proposal decision remains closed until that public gate passes.
"""
    write_text(DOC_REF, document)
    render_surface(proposal_sha, sha256(RADAR_TERMINAL_REF), sha256(PROBE_OUTCOME_REF))

    surface = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-002-REVIEW-SURFACE",
        "rendered_at_utc": args.prepared_at_utc,
        "status": "pass_static_review_surface_generated_pending_agent_visual_inspection",
        "artifact_ref": IMAGE_REF,
        "artifact_sha256": sha256(IMAGE_REF),
        "width_px": 1800,
        "height_px": 2040,
        "bindings": {
            "proposal_sha256": proposal_sha,
            "radar_terminal_reconciliation_sha256": sha256(RADAR_TERMINAL_REF),
            "probe_outcome_reconciliation_sha256": sha256(PROBE_OUTCOME_REF),
        },
        "assertions": {
            "human_decision_count": 0,
            "attestation": False,
            "publication_authorized": False,
            "implementation_authorized": False,
            "arcpy_invoked": False,
            "new_attempt_authorized": False,
            "project_data_content_read": False,
        },
    }
    write_json(SURFACE_REF, surface)

    bundle = {
        "schema_version": "1.0",
        "bundle_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-002-REVIEW-BUNDLE",
        "prepared_at_utc": args.prepared_at_utc,
        "status": "locally_prepared_zero_decisions_publication_authority_required",
        "human_decision_count": 0,
        "artifacts": [
            {"path": PROPOSAL_REF, "sha256": proposal_sha, "purpose": "normative recovery-002 proposal", "render_receipts": [{"path": SURFACE_REF, "sha256": sha256(SURFACE_REF)}]},
            {"path": PREFLIGHT_REF, "sha256": sha256(PREFLIGHT_REF), "purpose": "terminal-evidence and preparation-authority preflight", "render_receipts": []},
            {"path": DOC_REF, "sha256": sha256(DOC_REF), "purpose": "human-readable local review", "render_receipts": [{"path": SURFACE_REF, "sha256": sha256(SURFACE_REF)}]},
            {"path": IMAGE_REF, "sha256": sha256(IMAGE_REF), "purpose": "rendered local review surface", "render_receipts": [{"path": SURFACE_REF, "sha256": sha256(SURFACE_REF)}]},
        ],
        "decision_items": [{
            "item_id": "M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-002",
            "allowed_decisions_after_public_ci": ["approve", "revise", "defer"],
            "decision_currently_open": False,
            "evidence_ref": PROPOSAL_REF,
            "evidence_sha256": proposal_sha,
        }],
    }
    write_json(BUNDLE_REF, bundle)
    bundle_sha = sha256(BUNDLE_REF)

    contract = {
        "contract_version": "human-review-contract-v1",
        "template": False,
        "review_id": f"{PREFIX}-review",
        "response_schema_version": "nepal-m2-radar-pixel-orbit-application-recovery-002-response-v1",
        "status": "locally_prepared_not_public_owner_response_not_yet_open",
        "workflow_authority": {
            "mode": "local_preparation_only",
            "authority_ref": PREPARATION_APPROVAL_REF,
            "authorized_action_classes": ["local_evidence_preparation", "local_validation"],
            "verified_at_utc": args.prepared_at_utc,
            "expires_at_utc": None,
            "public_review_publication_authorized": False,
            "review_response_open": False,
            "lock_authorized": False,
            "reconcile_authorized": False,
        },
        "review_bundle": {
            "bundle_id": bundle["bundle_id"],
            "manifest_sha256": bundle_sha,
            "candidate_identity": f"M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-002-PROPOSAL-SHA256:{proposal_sha}",
            "rendered_surface_generated": True,
            "public_ci_verified": False,
        },
        "allowed_decisions_after_public_ci": ["approve", "revise", "defer"],
        "required_attestation": True,
        "items": [{"item_id": "M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-002", "evidence_sha256": bundle_sha}],
        "authority_boundary": {
            "packet_creates_authority": False,
            "git_commit_or_push_authorized": False,
            "public_ci_authorized": False,
            "implementation_authorized": False,
            "arcpy_invocation_authorized": False,
            "new_attempt_authorized": False,
            "project_data_or_external_custody_access_authorized": False,
            "radar_processing_authorized": False,
            "baseline_or_change_authorized": False,
            "scientific_publication_authorized": False,
        },
    }
    write_json(CONTRACT_REF, contract)

    blank = {
        "response_schema_version": contract["response_schema_version"],
        "review_id": contract["review_id"],
        "completed": False,
        "review_started_at_utc": None,
        "review_completed_at_utc": None,
        "reviewer": {"attestation": False},
        "responses": [{
            "item_id": "M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-002",
            "evidence_sha256": bundle_sha,
            "decision": None,
            "notes": "",
        }],
        "human_decision_count": 0,
        "response_not_open_until_public_ci": True,
    }
    write_json(BLANK_REF, blank)

    readiness = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-PIXEL-ORBIT-APPLICATION-RECOVERY-002-REVIEW-READINESS",
        "verified_at_utc": args.prepared_at_utc,
        "status": "pass_local_zero_decision_packet_ready_publication_authority_required",
        "bindings": {
            "preparation_approval_ref": PREPARATION_APPROVAL_REF,
            "preparation_approval_sha256": sha256(PREPARATION_APPROVAL_REF),
            "proposal_ref": PROPOSAL_REF,
            "proposal_sha256": proposal_sha,
            "review_preflight_ref": PREFLIGHT_REF,
            "review_preflight_sha256": sha256(PREFLIGHT_REF),
            "review_document_ref": DOC_REF,
            "review_document_sha256": sha256(DOC_REF),
            "review_surface_ref": IMAGE_REF,
            "review_surface_sha256": sha256(IMAGE_REF),
            "surface_receipt_ref": SURFACE_REF,
            "surface_receipt_sha256": sha256(SURFACE_REF),
            "review_bundle_ref": BUNDLE_REF,
            "review_bundle_sha256": bundle_sha,
            "review_contract_ref": CONTRACT_REF,
            "review_contract_sha256": sha256(CONTRACT_REF),
            "blank_response_ref": BLANK_REF,
            "blank_response_sha256": sha256(BLANK_REF),
            "radar_terminal_reconciliation_sha256": sha256(RADAR_TERMINAL_REF),
            "probe_outcome_reconciliation_sha256": sha256(PROBE_OUTCOME_REF),
        },
        "validation": {
            "consumed_attempts_preserved": True,
            "protected_public_evidence_preserved": True,
            "post_observation_limit_disclosed": True,
            "human_decision_count": 0,
            "blank_response_verified": True,
            "rendered_surface_generated": True,
            "canonical_checkpoint_intentionally_unchanged": True,
        },
        "released_now": {
            "local_packet_preparation": True,
            "local_packet_validation": True,
            "git_commit_or_push": False,
            "public_ci": False,
            "owner_proposal_review": False,
            "implementation": False,
            "arcpy_invocation": False,
            "new_attempt": False,
            "project_data_or_external_custody_access": False,
            "radar_processing": False,
            "baseline_or_change_analysis": False,
            "scientific_publication": False,
        },
        "assertions": {
            "human_decisions_fabricated": False,
            "git_commit_created": False,
            "git_push_performed": False,
            "public_ci_started": False,
            "protected_radar_or_probe_code_modified": False,
            "arcpy_invoked": False,
            "new_attempt_created": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "radar_processing_executed": False,
            "implementation_authorized": False,
            "scientific_result_established": False,
        },
        "next_action": "Obtain explicit owner authorization to commit and publish this exact zero-decision packet and run public default-branch CI; do not open the owner proposal response before that gate passes.",
    }
    write_json(READINESS_REF, readiness)

    print(json.dumps({
        "status": readiness["status"],
        "proposal_sha256": proposal_sha,
        "review_bundle_sha256": bundle_sha,
        "readiness_sha256": sha256(READINESS_REF),
        "canonical_checkpoint": CURRENT_CHECKPOINT,
        "next_gate": "explicit publication and public-CI authorization",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
