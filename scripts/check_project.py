#!/usr/bin/env python3
"""Validate the lightweight public project repository."""

from __future__ import annotations

import json
import hashlib
import subprocess
import sys
from pathlib import Path

from derive_m2_acquisition_checkpoint import derive_checkpoint
from validate_m2_acquisition_progress import (
    INITIAL_ACTIVE_INTAKE_SHA256,
    validate_progress as validate_acquisition_progress,
)

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "README.md",
    ".gitattributes",
    "AGENTS.md",
    "docs/PROJECT_CHARTER.md",
    "docs/ROADMAP.md",
    "docs/DATA_AND_METHODS_PLAN.md",
    "docs/SOURCES.md",
    "docs/ARCGIS_DELIVERY_PLAN.md",
    "docs/ARCGIS_EVIDENCE_MODEL.md",
    "docs/PIXEL_QA_PROTOCOL.md",
    "docs/OPTICAL_BASELINE_PROCESSING_PROTOCOL.md",
    "docs/M2_SAFE_MATERIALIZATION.md",
    "docs/OPTICAL_INPUT_READINESS_PROTOCOL.md",
    "docs/VALIDATION.md",
    "docs/STATUS.md",
    "docs/DECISIONS.md",
    "contracts/milestone-001.json",
    "contracts/milestone-002-proposal.json",
    "contracts/m2-intake-candidate.json",
    "contracts/milestone-002.json",
    "contracts/m2-intake.json",
    "contracts/m2-offline-verification.json",
    "contracts/m2-materialization.json",
    "contracts/milestone-002-dem-amendment-proposal.json",
    "contracts/m2-dem-intake-candidate.json",
    "contracts/m2-dem-intake.json",
    "contracts/m2-dem-offline-verification-candidate.json",
    "contracts/m2-dem-offline-verification.json",
    "records/project-control-profile.json",
    "records/long-term-goal.json",
    "records/evidence-ledger.jsonl",
    "config/aoi/approved-study-areas.geojson",
    "config/aoi/approved-study-areas-epsg32645.json",
    "records/source-gates/aoi-approval.json",
    "records/source-gates/aoi-review-reconciliation.json",
    "records/surface-receipts/m1-approved-aoi-arcgis-validation.json",
    "records/source-manifest.json",
    "records/acquisition-plan.json",
    "records/acquisition/m2-intake-static-dry-run.json",
    "records/acquisition/preflight.json",
    "records/acquisition/custody-initialization.json",
    "records/acquisition/active-intake-initial-snapshot.json",
    "records/acquisition/transfer-runner-readiness.json",
    "records/acquisition/acquisition-progress-readiness.json",
    "records/acquisition/acquisition-checkpoint-readiness.json",
    "records/acquisition/acquisition-checkpoint-portability-correction.json",
    "records/acquisition/dem-amendment-activation.json",
    "records/acquisition/dem-preflight.json",
    "records/acquisition/dem-custody-initialization.json",
    "records/source-gates/source-manifest-approval.json",
    "records/source-gates/source-manifest-review-reconciliation.json",
    "records/source-gates/m2-activation-approval.json",
    "records/source-gates/m2-activation-review-reconciliation.json",
    "records/source-gates/m2-live-source-gate.json",
    "records/source-gates/m2-dem-metadata-receipt.json",
    "records/source-gates/m2-dem-candidate-manifest.json",
    "records/source-gates/m2-dem-source-gate.json",
    "records/source-gates/m2-dem-amendment-approval.json",
    "records/source-gates/m2-dem-amendment-review-reconciliation.json",
    "records/source-gates/m2-dem-live-source-gate.json",
    "docs/M1_SOURCE_MANIFEST_REVIEW.md",
    "docs/assets/m1-source-manifest-review.png",
    "records/surface-receipts/m1-source-manifest-review.json",
    "records/surface-receipts/m1-control-reproducibility.json",
    "records/surface-receipts/arcgis-evidence-workspace.json",
    "records/surface-receipts/pixel-qa-synthetic-arcgis.json",
    "reviews/m1-manifest/review-bundle.json",
    "reviews/m1-manifest/review-contract.json",
    "reviews/m1-manifest/blank-response.json",
    "docs/M2_CONTROLLED_ACQUISITION_REVIEW.md",
    "docs/M2_EXECUTION_RUNBOOK.md",
    "docs/M2_OFFLINE_VERIFICATION.md",
    "docs/M2_DEM_AMENDMENT_REVIEW.md",
    "docs/M2_DEM_OFFLINE_VERIFICATION.md",
    "docs/RADAR_BASELINE_PROCESSING_PROTOCOL.md",
    "docs/assets/m2-dem-amendment-review.png",
    "docs/assets/m2-controlled-acquisition-review.png",
    "scripts/render_m2_activation_review.py",
    "scripts/prepare_m2_intake.py",
    "scripts/prepare_m2_verification.py",
    "scripts/build_arcgis_evidence_workspace.py",
    "scripts/validate_arcgis_evidence_workspace.py",
    "scripts/pixel_qa_core.py",
    "scripts/validate_pixel_qa_arcgis.py",
    "config/arcgis/evidence-workspace-schema.json",
    "config/qa/pixel-readiness-contract.json",
    "config/qa/candidate-pair-plan.json",
    "config/qa/radar-baseline-processing-contract.json",
    "config/qa/optical-baseline-processing-contract.json",
    "config/qa/optical-input-readiness-contract.json",
    "docs/assets/arcgis-evidence-workspace-preview.png",
    "records/surface-receipts/m2-activation-review.json",
    "records/surface-receipts/arcgis-sar-processing-capability.json",
    "records/surface-receipts/m2-dem-amendment-review.json",
    "records/surface-receipts/m2-dem-radar-control-readiness.json",
    "records/surface-receipts/optical-processing-synthetic-arcgis.json",
    "records/surface-receipts/optical-baseline-control-readiness.json",
    "records/surface-receipts/m2-materialization-readiness.json",
    "records/surface-receipts/optical-input-readiness-synthetic-arcgis.json",
    "records/surface-receipts/optical-input-readiness-control.json",
    "contracts/m2-offline-verification-candidate.json",
    "records/readiness/m2-readiness-audit-input.json",
    "records/readiness/m2-readiness-decision.json",
    "reviews/m2-activation/review-bundle.json",
    "reviews/m2-activation/review-contract.json",
    "reviews/m2-activation/blank-response.json",
    "reviews/m2-dem-amendment/review-bundle.json",
    "reviews/m2-dem-amendment/review-contract.json",
    "reviews/m2-dem-amendment/blank-response.json",
    "tests/test_m2_intake.py",
    "tests/test_m2_verification.py",
    "tests/test_arcgis_evidence_schema.py",
    "tests/test_pixel_qa_core.py",
    "tests/test_pair_plan.py",
    "scripts/activate_m2.py",
    "scripts/run_m2_preflight.py",
    "scripts/complete_m2_preflight.py",
    "scripts/initialize_m2_custody.py",
    "scripts/record_m2_custody_checkpoint.py",
    "scripts/m2_transfer_core.py",
    "scripts/acquire_m2_product.py",
    "scripts/record_m2_transfer_readiness.py",
    "scripts/validate_m2_acquisition_progress.py",
    "scripts/derive_m2_acquisition_checkpoint.py",
    "scripts/validate_pair_plan.py",
    "tests/test_m2_transfer_core.py",
    "tests/test_m2_acquisition_progress.py",
    "tests/test_m2_checkpoint_reconciliation.py",
    "tests/test_m2_active_verification.py",
    "tests/test_m2_dem_amendment.py",
    "tests/test_m2_dem_controls.py",
    "tests/test_m2_dem_activation.py",
    "tests/test_m2_dem_preflight.py",
    "tests/test_radar_processing_contract.py",
    "tests/test_optical_processing_core.py",
    "tests/test_m2_materialization.py",
    "tests/test_optical_input_readiness.py",
    "scripts/activate_m2_verification.py",
    "scripts/verify_m2_product_container.py",
    "scripts/inspect_arcgis_sar_capability.py",
    "scripts/prepare_m2_dem_amendment.py",
    "scripts/prepare_m2_dem_controls.py",
    "scripts/activate_m2_dem_amendment.py",
    "scripts/run_m2_dem_preflight.py",
    "scripts/complete_m2_dem_preflight.py",
    "scripts/verify_m2_dem_geotiff.py",
    "scripts/prepare_radar_processing_contract.py",
    "scripts/optical_processing_core.py",
    "scripts/prepare_optical_processing_contract.py",
    "scripts/validate_optical_processing_arcgis.py",
    "scripts/m2_materialization_core.py",
    "scripts/prepare_m2_materialization.py",
    "scripts/materialize_m2_product.py",
    "scripts/optical_input_readiness_core.py",
    "scripts/prepare_optical_input_readiness_contract.py",
    "scripts/inspect_optical_inputs_arcgis.py",
    "scripts/validate_optical_input_readiness_arcgis.py",
    "scripts/render_m2_dem_amendment_review.py",
    ".github/workflows/validate.yml",
]

FORBIDDEN_SUFFIXES = {
    ".tif", ".tiff", ".jp2", ".img", ".nc", ".hdf", ".h5",
    ".zip", ".7z", ".gpkg", ".shp", ".ppkx", ".mpkx", ".lpkx", ".slpk",
}

FORBIDDEN_NAME_PARTS = (
    "credential", "secret", "access_token", "refresh_token", "private_key",
)


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def validate_review_bundle(bundle_relative: str, contract_relative: str) -> None:
    bundle = json.loads((ROOT / bundle_relative).read_text(encoding="utf-8"))
    review_contract = json.loads((ROOT / contract_relative).read_text(encoding="utf-8"))
    if review_contract["review_bundle"]["manifest_sha256"] != sha256(bundle_relative):
        fail(f"review contract does not bind exact bundle bytes: {bundle_relative}")
    if review_contract["review_bundle"]["candidate_identity"] != bundle["candidate_identity"]:
        fail(f"review contract candidate differs from bundle: {bundle_relative}")
    for artifact in bundle["artifacts"]:
        if artifact["sha256"] != sha256(artifact["path"]):
            fail(f"review bundle artifact hash differs: {artifact['path']}")
        for receipt in artifact["render_receipts"]:
            if receipt["sha256"] != sha256(receipt["path"]):
                fail(f"review bundle render receipt hash differs: {receipt['path']}")


def main() -> None:
    missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
    if missing:
        fail("missing required files: " + ", ".join(missing))

    profile = json.loads((ROOT / "records/project-control-profile.json").read_text(encoding="utf-8"))
    contract = json.loads((ROOT / "contracts/milestone-001.json").read_text(encoding="utf-8"))
    m2_proposal = json.loads((ROOT / "contracts/milestone-002-proposal.json").read_text(encoding="utf-8"))
    active_m2 = json.loads((ROOT / "contracts/milestone-002.json").read_text(encoding="utf-8"))
    dem_proposal = json.loads((ROOT / "contracts/milestone-002-dem-amendment-proposal.json").read_text(encoding="utf-8"))
    dem_receipt = json.loads((ROOT / "records/source-gates/m2-dem-metadata-receipt.json").read_text(encoding="utf-8"))
    dem_manifest = json.loads((ROOT / "records/source-gates/m2-dem-candidate-manifest.json").read_text(encoding="utf-8"))
    dem_gate = json.loads((ROOT / "records/source-gates/m2-dem-source-gate.json").read_text(encoding="utf-8"))
    dem_bundle = json.loads((ROOT / "reviews/m2-dem-amendment/review-bundle.json").read_text(encoding="utf-8"))
    dem_contract = json.loads((ROOT / "reviews/m2-dem-amendment/review-contract.json").read_text(encoding="utf-8"))
    dem_blank = json.loads((ROOT / "reviews/m2-dem-amendment/blank-response.json").read_text(encoding="utf-8"))
    dem_reconciliation = json.loads((ROOT / "records/source-gates/m2-dem-amendment-review-reconciliation.json").read_text(encoding="utf-8"))
    dem_approval = json.loads((ROOT / "records/source-gates/m2-dem-amendment-approval.json").read_text(encoding="utf-8"))
    sar_capability = json.loads((ROOT / "records/surface-receipts/arcgis-sar-processing-capability.json").read_text(encoding="utf-8"))
    dem_intake_candidate = json.loads((ROOT / "contracts/m2-dem-intake-candidate.json").read_text(encoding="utf-8"))
    dem_intake_active = json.loads((ROOT / "contracts/m2-dem-intake.json").read_text(encoding="utf-8"))
    dem_verification_candidate = json.loads((ROOT / "contracts/m2-dem-offline-verification-candidate.json").read_text(encoding="utf-8"))
    dem_verification_active = json.loads((ROOT / "contracts/m2-dem-offline-verification.json").read_text(encoding="utf-8"))
    dem_activation_receipt = json.loads((ROOT / "records/acquisition/dem-amendment-activation.json").read_text(encoding="utf-8"))
    dem_live_source_gate = json.loads((ROOT / "records/source-gates/m2-dem-live-source-gate.json").read_text(encoding="utf-8"))
    dem_preflight = json.loads((ROOT / "records/acquisition/dem-preflight.json").read_text(encoding="utf-8"))
    dem_custody_receipt = json.loads((ROOT / "records/acquisition/dem-custody-initialization.json").read_text(encoding="utf-8"))
    radar_processing_contract = json.loads((ROOT / "config/qa/radar-baseline-processing-contract.json").read_text(encoding="utf-8"))
    dem_radar_readiness = json.loads((ROOT / "records/surface-receipts/m2-dem-radar-control-readiness.json").read_text(encoding="utf-8"))
    optical_processing_contract = json.loads((ROOT / "config/qa/optical-baseline-processing-contract.json").read_text(encoding="utf-8"))
    optical_arcgis_receipt = json.loads((ROOT / "records/surface-receipts/optical-processing-synthetic-arcgis.json").read_text(encoding="utf-8"))
    optical_readiness = json.loads((ROOT / "records/surface-receipts/optical-baseline-control-readiness.json").read_text(encoding="utf-8"))
    materialization_contract = json.loads((ROOT / "contracts/m2-materialization.json").read_text(encoding="utf-8"))
    materialization_readiness = json.loads((ROOT / "records/surface-receipts/m2-materialization-readiness.json").read_text(encoding="utf-8"))
    optical_input_contract = json.loads((ROOT / "config/qa/optical-input-readiness-contract.json").read_text(encoding="utf-8"))
    optical_input_arcgis = json.loads((ROOT / "records/surface-receipts/optical-input-readiness-synthetic-arcgis.json").read_text(encoding="utf-8"))
    optical_input_readiness = json.loads((ROOT / "records/surface-receipts/optical-input-readiness-control.json").read_text(encoding="utf-8"))
    goal = json.loads((ROOT / "records/long-term-goal.json").read_text(encoding="utf-8"))

    expected_remote = profile["project"]["repository_identity"]["expected_remote"]
    remote_project_name = expected_remote.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
    if profile["project"]["name"] != remote_project_name:
        fail("project name does not match canonical repository identity")
    if profile["project"]["repository_identity"]["default_branch"] != "main":
        fail("expected default branch must be main")
    if profile.get("control_surfaces", {}).get("proposed_amendments") != []:
        fail("project profile must clear the DEM proposal after exact activation")
    if profile.get("control_surfaces", {}).get("activated_amendments") != [
        "records/source-gates/m2-dem-amendment-approval.json"
    ]:
        fail("project profile must expose the exact active M2 DEM amendment")
    if not (ROOT / "AGENTS.md").read_text(encoding="utf-8").strip():
        fail("AGENTS.md must contain controlling project instructions")
    if goal["status"] != "active":
        fail("long-term goal record must be active")
    workflow_text = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")
    if "actions/checkout@v6" not in workflow_text or "actions/setup-python@v7" not in workflow_text:
        fail("GitHub Actions must use the confirmed Node.js 24 action majors")
    if contract["project_profile_ref"] != "records/project-control-profile.json":
        fail("milestone must reference the project control profile")
    if contract["status"] != "complete":
        fail("M1 must be complete after exact source-manifest approval")
    if contract["authority"]["mode"] != "inherited":
        fail("completed M1 must preserve the exact user authority")
    if profile["authority"]["authority_ref"] != active_m2["authority"]["authority_ref"]:
        fail("profile and active M2 authority references must agree")
    expected_dem_amendment_binding = {
        "approval_ref": "records/source-gates/m2-dem-amendment-approval.json",
        "approval_sha256": sha256("records/source-gates/m2-dem-amendment-approval.json"),
        "proposal_ref": "contracts/milestone-002-dem-amendment-proposal.json",
        "proposal_sha256": "92f48680c0b779398d8bbebd872a60bc3850f008f5c9b68d5bf45a2448abdd69",
        "review_bundle_sha256": "caecbdfe69ec1a6c8c39401b63756005820a727cb8f9e7e0084753e2d6afb39e",
        "license_document_sha256": "9cd37d37ea654bbcaf0a2e059e6a3a5b5f76072824d8dd860ccf274ada8951bd",
    }
    if profile["authority"].get("amendments") != [expected_dem_amendment_binding]:
        fail("profile authority does not bind the exact DEM amendment")
    if active_m2["authority"].get("amendments") != [expected_dem_amendment_binding]:
        fail("active M2 authority does not bind the exact DEM amendment")
    profile_gates = {
        item.get("unit_id"): item
        for item in profile.get("gate_policy", {}).get("explicit_human_gates", [])
        if isinstance(item, dict)
    }
    for approved_unit in ("M2-CUSTODY-PREFLIGHT", "M2-ACQUIRE"):
        if profile_gates.get(approved_unit, {}).get("authority_ref") != "records/source-gates/m2-activation-approval.json":
            fail(f"project profile must bind {approved_unit} to the exact M2 activation approval")
    for approved_unit in ("M2-DEM-AMEND", "M2-DEM-PREFLIGHT", "M2-DEM-ACQUIRE"):
        if profile_gates.get(approved_unit, {}).get("authority_ref") != "records/source-gates/m2-dem-amendment-approval.json":
            fail(f"project profile must bind {approved_unit} to the exact DEM amendment approval")
    if profile.get("parallel_checkpoints") != [
        {
            "checkpoint_id": "M2-DEM-ACQUISITION",
            "authority_ref": "records/source-gates/m2-dem-amendment-approval.json",
            "next_action": "Acquire M2-DEM-001 only through append-only staging, verify its exact length and local SHA-256, and promote without replacement; stop on any route or identity drift.",
        }
    ]:
        fail("project profile DEM parallel checkpoint differs")
    if goal.get("active_amendments") != ["records/source-gates/m2-dem-amendment-approval.json"] or goal.get("parallel_checkpoints") != ["M2-DEM-ACQUISITION"]:
        fail("long-term goal does not expose the active DEM amendment checkpoint")
    prohibited = set(contract["scope"]["forbidden_work"])
    if "download full satellite products" not in prohibited:
        fail("full satellite-product acquisition must remain prohibited in M1")
    if profile["control_surfaces"].get("active_contract") != "contracts/milestone-002.json":
        fail("project profile must identify the active M2 contract")
    if profile["control_surfaces"].get("last_completed_contract") != "contracts/milestone-001.json":
        fail("project profile must identify M1 as the last completed contract")
    if profile["control_surfaces"].get("proposed_contract") is not None:
        fail("project profile must clear the proposed-contract pointer after activation")
    if profile["control_surfaces"].get("activated_from_contract") != "contracts/milestone-002-proposal.json":
        fail("project profile must retain the exact proposal lineage")
    if goal.get("active_milestone") != "contracts/milestone-002.json" or goal.get("proposed_milestone") is not None:
        fail("long-term goal must identify active M2 and no pending proposal")
    approval = json.loads((ROOT / "records/source-gates/aoi-approval.json").read_text(encoding="utf-8"))
    projected_aoi = json.loads((ROOT / "config/aoi/approved-study-areas-epsg32645.json").read_text(encoding="utf-8"))
    arcgis_receipt = json.loads((ROOT / "records/surface-receipts/m1-approved-aoi-arcgis-validation.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "records/source-manifest.json").read_text(encoding="utf-8"))
    manifest_bundle = json.loads((ROOT / "reviews/m1-manifest/review-bundle.json").read_text(encoding="utf-8"))
    manifest_contract = json.loads((ROOT / "reviews/m1-manifest/review-contract.json").read_text(encoding="utf-8"))
    manifest_response = json.loads((ROOT / "reviews/m1-manifest/blank-response.json").read_text(encoding="utf-8"))
    manifest_approval = json.loads((ROOT / "records/source-gates/source-manifest-approval.json").read_text(encoding="utf-8"))
    manifest_reconciliation = json.loads((ROOT / "records/source-gates/source-manifest-review-reconciliation.json").read_text(encoding="utf-8"))
    acquisition_plan = json.loads((ROOT / "records/acquisition-plan.json").read_text(encoding="utf-8"))
    m2_bundle = json.loads((ROOT / "reviews/m2-activation/review-bundle.json").read_text(encoding="utf-8"))
    m2_contract = json.loads((ROOT / "reviews/m2-activation/review-contract.json").read_text(encoding="utf-8"))
    m2_response = json.loads((ROOT / "reviews/m2-activation/blank-response.json").read_text(encoding="utf-8"))
    m2_surface_receipt = json.loads((ROOT / "records/surface-receipts/m2-activation-review.json").read_text(encoding="utf-8"))
    intake_contract = json.loads((ROOT / "contracts/m2-intake-candidate.json").read_text(encoding="utf-8"))
    active_intake = json.loads((ROOT / "contracts/m2-intake.json").read_text(encoding="utf-8"))
    initial_active_intake = json.loads((ROOT / "records/acquisition/active-intake-initial-snapshot.json").read_text(encoding="utf-8"))
    intake_dry_run = json.loads((ROOT / "records/acquisition/m2-intake-static-dry-run.json").read_text(encoding="utf-8"))
    m2_activation = json.loads((ROOT / "records/source-gates/m2-activation-approval.json").read_text(encoding="utf-8"))
    m2_reconciliation = json.loads((ROOT / "records/source-gates/m2-activation-review-reconciliation.json").read_text(encoding="utf-8"))
    m2_source_gate = json.loads((ROOT / "records/source-gates/m2-live-source-gate.json").read_text(encoding="utf-8"))
    m2_preflight = json.loads((ROOT / "records/acquisition/preflight.json").read_text(encoding="utf-8"))
    custody_receipt = json.loads((ROOT / "records/acquisition/custody-initialization.json").read_text(encoding="utf-8"))
    transfer_readiness = json.loads((ROOT / "records/acquisition/transfer-runner-readiness.json").read_text(encoding="utf-8"))
    acquisition_progress_readiness = json.loads((ROOT / "records/acquisition/acquisition-progress-readiness.json").read_text(encoding="utf-8"))
    acquisition_checkpoint_readiness = json.loads((ROOT / "records/acquisition/acquisition-checkpoint-readiness.json").read_text(encoding="utf-8"))
    acquisition_checkpoint_portability = json.loads((ROOT / "records/acquisition/acquisition-checkpoint-portability-correction.json").read_text(encoding="utf-8"))
    pair_plan = json.loads((ROOT / "config/qa/candidate-pair-plan.json").read_text(encoding="utf-8"))
    offline_verification = json.loads((ROOT / "contracts/m2-offline-verification-candidate.json").read_text(encoding="utf-8"))
    active_offline_verification = json.loads((ROOT / "contracts/m2-offline-verification.json").read_text(encoding="utf-8"))
    readiness_input = json.loads((ROOT / "records/readiness/m2-readiness-audit-input.json").read_text(encoding="utf-8"))
    readiness_decision = json.loads((ROOT / "records/readiness/m2-readiness-decision.json").read_text(encoding="utf-8"))
    reproducibility = json.loads((ROOT / "records/surface-receipts/m1-control-reproducibility.json").read_text(encoding="utf-8"))
    evidence_schema = json.loads((ROOT / "config/arcgis/evidence-workspace-schema.json").read_text(encoding="utf-8"))
    evidence_workspace = json.loads((ROOT / "records/surface-receipts/arcgis-evidence-workspace.json").read_text(encoding="utf-8"))
    pixel_contract = json.loads((ROOT / "config/qa/pixel-readiness-contract.json").read_text(encoding="utf-8"))
    pixel_receipt = json.loads((ROOT / "records/surface-receipts/pixel-qa-synthetic-arcgis.json").read_text(encoding="utf-8"))
    aoi_reconciliation = json.loads((ROOT / "records/source-gates/aoi-review-reconciliation.json").read_text(encoding="utf-8"))
    units = {unit["id"]: unit for unit in contract["units"]}
    active_m2_units = {unit["id"]: unit for unit in active_m2["units"]}
    validate_review_bundle("reviews/m1-aoi/review-bundle.json", "reviews/m1-aoi/review-contract.json")
    validate_review_bundle("reviews/m1-manifest/review-bundle.json", "reviews/m1-manifest/review-contract.json")
    validate_review_bundle("reviews/m2-activation/review-bundle.json", "reviews/m2-activation/review-contract.json")
    validate_review_bundle("reviews/m2-dem-amendment/review-bundle.json", "reviews/m2-dem-amendment/review-contract.json")
    if dem_manifest.get("status") != "candidate_not_approved" or len(dem_manifest.get("records", [])) != 4:
        fail("M2 DEM candidate manifest must remain an unapproved exact four-tile set")
    expected_dem_ids = {
        "Copernicus_DSM_COG_10_N27_00_E084_00_DEM",
        "Copernicus_DSM_COG_10_N27_00_E085_00_DEM",
        "Copernicus_DSM_COG_10_N28_00_E084_00_DEM",
        "Copernicus_DSM_COG_10_N28_00_E085_00_DEM",
    }
    if {record.get("item_id") for record in dem_manifest["records"]} != expected_dem_ids:
        fail("M2 DEM candidate tile identities differ")
    if dem_manifest.get("summary", {}).get("combined_content_length_bytes") != 170302058:
        fail("M2 DEM candidate total byte count differs")
    dem_assertions = dem_receipt.get("assertions", {})
    if dem_assertions.get("payload_bytes_requested") is not False or dem_assertions.get("license_accepted") is not False:
        fail("M2 DEM metadata receipt must preserve its no-payload and no-acceptance boundary")
    if dem_gate.get("decision", {}).get("status") != "blocked" or len(dem_gate.get("sources", [])) != 4:
        fail("M2 DEM source gate must remain blocked for exactly four sources")
    for source in dem_gate["sources"]:
        criteria = {criterion.get("id"): criterion for criterion in source.get("criteria", [])}
        if criteria.get("terms-acceptance", {}).get("status") != "unknown":
            fail("M2 DEM source gate must retain pending exact license acceptance")
        if criteria.get("scope-authority", {}).get("status") != "unknown":
            fail("M2 DEM source gate must retain pending scope authority")
    if dem_proposal.get("status") != "proposed_not_active" or dem_proposal.get("authority", {}).get("mode") != "not_granted":
        fail("M2 DEM amendment must remain proposed and non-authorizing")
    expected_dem_bindings = {
        "candidate_manifest_sha256": sha256("records/source-gates/m2-dem-candidate-manifest.json"),
        "metadata_receipt_sha256": sha256("records/source-gates/m2-dem-metadata-receipt.json"),
        "source_gate_sha256": sha256("records/source-gates/m2-dem-source-gate.json"),
        "arcgis_capability_sha256": sha256("records/surface-receipts/arcgis-sar-processing-capability.json"),
    }
    if any(dem_proposal.get(key) != value for key, value in expected_dem_bindings.items()):
        fail("M2 DEM amendment has stale evidence bindings")
    if dem_bundle.get("candidate_identity") != f"M2-DEM-AMENDMENT-PROPOSAL-SHA256:{sha256('contracts/milestone-002-dem-amendment-proposal.json')}":
        fail("M2 DEM review bundle does not bind the exact amendment proposal")
    if dem_contract.get("items", [{}])[0].get("evidence_sha256") != sha256("reviews/m2-dem-amendment/review-bundle.json"):
        fail("M2 DEM review item does not bind the exact review bundle")
    if dem_blank.get("completed") is not False or dem_blank.get("reviewer", {}).get("attestation") is not False:
        fail("M2 DEM blank response must contain no human decision")
    if any(response.get("decision") is not None for response in dem_blank.get("responses", [])):
        fail("M2 DEM blank response contains a fabricated decision")
    if dem_reconciliation.get("status") != "reconciled_exact_human_response" or dem_reconciliation.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}:
        fail("M2 DEM amendment response is not one exact reconciled approval")
    if dem_reconciliation.get("contract_sha256") != sha256("reviews/m2-dem-amendment/review-contract.json") or dem_reconciliation.get("human_decisions_fabricated") is not False:
        fail("M2 DEM amendment reconciliation binding or fabrication flag differs")
    if dem_approval.get("status") != "approved":
        fail("M2 DEM amendment approval is not active")
    expected_dem_approval_bindings = {
        "review_bundle_manifest_sha256": "caecbdfe69ec1a6c8c39401b63756005820a727cb8f9e7e0084753e2d6afb39e",
        "amendment_proposal_sha256": "92f48680c0b779398d8bbebd872a60bc3850f008f5c9b68d5bf45a2448abdd69",
        "review_reconciliation_sha256": sha256("records/source-gates/m2-dem-amendment-review-reconciliation.json"),
        "locked_response_sha256": dem_reconciliation.get("response_sha256"),
        "lock_receipt_sha256": dem_reconciliation.get("receipt_sha256"),
    }
    if any(dem_approval.get(key) != value for key, value in expected_dem_approval_bindings.items()):
        fail("M2 DEM amendment approval bindings differ")
    if dem_approval.get("license") != {
        "name": "Licence for Copernicus DEM instance COP-DEM-GLO-30-F Global 30m Full, Free & Open",
        "url": "https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM/resources/license/License-COPDEM-30.pdf",
        "document_sha256": "9cd37d37ea654bbcaf0a2e059e6a3a5b5f76072824d8dd860ccf274ada8951bd",
        "acceptance_status": "accepted_exact_hash_bound_document",
    }:
        fail("M2 DEM amendment approval license binding differs")
    expected_dem_source_ids = {"M2-DEM-001", "M2-DEM-002", "M2-DEM-003", "M2-DEM-004"}
    if set(dem_approval.get("authorized_source_ids", [])) != expected_dem_source_ids:
        fail("M2 DEM amendment approval source set differs")
    if dem_approval.get("human_decisions_fabricated") is not False:
        fail("M2 DEM amendment approval must not report fabricated decisions")
    if dem_intake_active.get("extensions", {}).get("status") != "active_authorized_preflight_passed_custody_initialized" or len(dem_intake_active.get("assets", [])) != 4:
        fail("active M2 DEM intake identity or state differs")
    if {asset.get("extensions", {}).get("source_id") for asset in dem_intake_active["assets"]} != expected_dem_source_ids:
        fail("active M2 DEM intake source set differs")
    if any(
        asset.get("state") != "authorized"
        or asset.get("attempts") != []
        or asset.get("source", {}).get("authorization_ref") != "records/source-gates/m2-dem-amendment-approval.json"
        for asset in dem_intake_active["assets"]
    ):
        fail("active M2 DEM intake invents transfer progress or loses approval binding")
    if dem_intake_active.get("extensions", {}).get("license_acceptance_status") != "accepted_exact_hash_bound_document":
        fail("active M2 DEM intake does not preserve exact license acceptance")
    expected_dem_intake_progress_bindings = {
        "source_gate_ref": "records/source-gates/m2-dem-live-source-gate.json",
        "source_gate_sha256": sha256("records/source-gates/m2-dem-live-source-gate.json"),
        "preflight_ref": "records/acquisition/dem-preflight.json",
        "preflight_sha256": sha256("records/acquisition/dem-preflight.json"),
        "custody_initialization_ref": "records/acquisition/dem-custody-initialization.json",
        "custody_initialization_sha256": sha256("records/acquisition/dem-custody-initialization.json"),
        "custody_initialized": True,
    }
    if any(dem_intake_active.get("extensions", {}).get(key) != value for key, value in expected_dem_intake_progress_bindings.items()):
        fail("active M2 DEM intake preflight or custody bindings differ")
    if dem_verification_active.get("status") != "active_gate_deferred_no_promoted_rasters":
        fail("active M2 DEM verification must remain data-deferred")
    active_dem_verification_authority = dem_verification_active.get("authority", {})
    if active_dem_verification_authority != {
        "dem_amendment_status": "approved",
        "license_acceptance_established": True,
        "network_access_authorized": False,
        "custody_mutation_authorized": False,
        "dem_download_authorized": False,
        "dem_pixel_processing_authorized": True,
        "this_contract_creates_authority": False,
    }:
        fail("active M2 DEM verification authority differs")
    if dem_verification_active.get("inputs", {}).get("intake_contract_ref") != "contracts/m2-dem-intake.json" or dem_verification_active.get("inputs", {}).get("intake_contract_sha256") != sha256("contracts/m2-dem-intake.json"):
        fail("active M2 DEM verification does not bind the active intake")
    for unit_id, expected_status in (
        ("M2-DEM-AMEND", "complete"),
        ("M2-DEM-PREFLIGHT", "complete"),
        ("M2-DEM-ACQUIRE", "ready"),
        ("M2-DEM-VERIFY", "planned"),
    ):
        if active_m2_units.get(unit_id, {}).get("status") != expected_status:
            fail(f"active M2 unit {unit_id} status differs")
    if set(active_m2_units["M2-BASELINE"].get("depends_on", [])) != {"M2-VERIFY", "M2-DEM-VERIFY"}:
        fail("M2 baseline does not preserve both Sentinel and DEM dependencies")
    if dem_activation_receipt.get("status") != "pass_exact_dem_amendment_activated_preflight_pending":
        fail("M2 DEM activation receipt status differs")
    expected_historical_dem_activation_bindings = {
        "reconciliation_ref": "records/source-gates/m2-dem-amendment-review-reconciliation.json",
        "reconciliation_sha256": "9d72c9786440da0c9149340cd69361b12e55f0d7dff88972bfd02ee0da5460e1",
        "approval_ref": "records/source-gates/m2-dem-amendment-approval.json",
        "approval_sha256": "6d1fc7e05854bc149ace177d89e84a7651cc049efd530cab650a9464222769d0",
        "active_intake_ref": "contracts/m2-dem-intake.json",
        "active_intake_sha256": "0fa00a4be01d3caddac28088d2d3d714040d1258b33497ebee50cbb0b8b3b5b6",
        "active_verification_ref": "contracts/m2-dem-offline-verification.json",
        "active_verification_sha256": "755bdb1fd1916d68289f5266912f8bb7f25462b512ce7cfc27a49feb44bcef42",
        "active_milestone_ref": "contracts/milestone-002.json",
        "active_milestone_sha256": "fc764ba8513c05e518096e8864ba0ec49507ca924f2474637adccef31275a6cf",
        "project_profile_ref": "records/project-control-profile.json",
        "project_profile_sha256": "dd07dec7c68fbd9e486ad96e1a34dbd66266409609db05419a6eb78d723bc844",
        "long_term_goal_ref": "records/long-term-goal.json",
        "long_term_goal_sha256": "81f5b742b8aa3e829253317faa9c6017c8c93a6deb1d10a3f6cb96c7b55c44e8",
        "activation_script_ref": "scripts/activate_m2_dem_amendment.py",
        "activation_script_sha256": "a4cc4f86b0beb81f151ccdc0bc4a4ab5d674823d7c7a5879f0e223efcd36d256",
    }
    if dem_activation_receipt.get("bindings") != expected_historical_dem_activation_bindings:
        fail("M2 DEM activation receipt no longer preserves its published activation bindings")
    activation_assertions = dem_activation_receipt.get("assertions", {})
    if activation_assertions.get("exact_license_accepted") is not True or activation_assertions.get("authorized_dem_tile_count") != 4:
        fail("M2 DEM activation receipt does not preserve exact approved scope")
    if any(activation_assertions.get(key) is not False for key in ("network_requests_performed", "dem_payload_bytes_requested", "dem_pixels_examined", "scientific_result_established")):
        fail("M2 DEM activation receipt invents preflight, payload, pixel, or science evidence")
    if dem_live_source_gate.get("decision", {}).get("status") != "ready" or dem_live_source_gate.get("authority", {}).get("authority_ref") != "records/source-gates/m2-dem-amendment-approval.json":
        fail("M2 DEM live source gate is not ready under the exact amendment")
    if len(dem_live_source_gate.get("sources", [])) != 4:
        fail("M2 DEM live source gate must contain four exact sources")
    for source in dem_live_source_gate["sources"]:
        criteria = source.get("criteria", [])
        if len(criteria) != 10 or any(item.get("status") != "pass" for item in criteria):
            fail("M2 DEM live source gate has an incomplete or non-passing criterion")
    if dem_preflight.get("status") != "pass_no_payload_no_external_mutation":
        fail("M2 DEM preflight status differs")
    if dem_preflight.get("source_gate") != {
        "ref": "records/source-gates/m2-dem-live-source-gate.json",
        "sha256": sha256("records/source-gates/m2-dem-live-source-gate.json"),
        "decision": "ready",
        "exact_tile_count": 4,
    }:
        fail("M2 DEM preflight source-gate binding differs")
    license_check = dem_preflight.get("license_check", {})
    if license_check.get("sha256") != "9cd37d37ea654bbcaf0a2e059e6a3a5b5f76072824d8dd860ccf274ada8951bd" or license_check.get("status") != "pass" or not all(license_check.get("checks", {}).values()):
        fail("M2 DEM fresh license check differs")
    expected_live_tiles = {
        record["source_id"]: (
            record["anonymous_head"]["content_length_bytes"],
            record["anonymous_head"]["etag"],
            record["anonymous_head"]["last_modified"],
        )
        for record in dem_manifest["records"]
    }
    if {item.get("source_id") for item in dem_preflight.get("tile_checks", [])} != set(expected_live_tiles):
        fail("M2 DEM preflight tile set differs")
    for item in dem_preflight["tile_checks"]:
        expected_size, expected_etag, expected_modified = expected_live_tiles[item["source_id"]]
        head = item.get("head", {})
        if (
            item.get("status") != "pass"
            or not all(item.get("stac_checks", {}).values())
            or not all(item.get("head_checks", {}).values())
            or head.get("content_length_bytes") != expected_size
            or head.get("etag") != expected_etag
            or head.get("last_modified") != expected_modified
            or head.get("response_body_bytes") != 0
        ):
            fail(f"M2 DEM preflight live identity differs for {item.get('source_id')}")
    preflight_mutations = dem_preflight.get("mutations_performed", {})
    if preflight_mutations != {"external_directory_created": False, "dem_payload_requested": False, "dem_payload_bytes_received": 0, "authentication": False, "account_or_terms_action": False}:
        fail("M2 DEM preflight invents a payload or external mutation")
    if dem_preflight.get("paths", {}).get("existing_destination_or_staging_paths") != [] or dem_preflight.get("paths", {}).get("case_insensitive_path_collision") is not False:
        fail("M2 DEM preflight did not preserve collision-free paths")
    if dem_preflight.get("storage", {}).get("status") != "pass" or dem_preflight.get("storage", {}).get("exact_tile_bytes") != 170302058:
        fail("M2 DEM preflight storage result differs")
    if dem_custody_receipt.get("status") != "created_and_verified_empty":
        fail("M2 DEM custody initialization status differs")
    if dem_custody_receipt.get("bindings") != {
        "preflight_ref": "records/acquisition/dem-preflight.json",
        "preflight_sha256": sha256("records/acquisition/dem-preflight.json"),
        "source_gate_ref": "records/source-gates/m2-dem-live-source-gate.json",
        "source_gate_sha256": sha256("records/source-gates/m2-dem-live-source-gate.json"),
        "active_intake_ref": "contracts/m2-dem-intake.json",
        "active_intake_sha256_before_initialization": "0fa00a4be01d3caddac28088d2d3d714040d1258b33497ebee50cbb0b8b3b5b6",
    }:
        fail("M2 DEM custody initialization bindings differ")
    custody_verification = dem_custody_receipt.get("verification", {})
    if any(custody_verification.get(key) is not True for key in ("all_paths_exist", "all_paths_not_reparse_points", "external_root_outside_git")):
        fail("M2 DEM custody initialization path verification differs")
    if custody_verification.get("files_downloaded") != 0 or custody_verification.get("dem_payload_bytes_present") != 0 or custody_verification.get("authentication_performed") is not False:
        fail("M2 DEM custody initialization invents payload or authentication")
    dem_preflight_unit = active_m2_units["M2-DEM-PREFLIGHT"]
    dem_acquire_unit = active_m2_units["M2-DEM-ACQUIRE"]
    if dem_preflight_unit.get("outputs") != ["records/source-gates/m2-dem-live-source-gate.json", "records/acquisition/dem-preflight.json", "records/acquisition/dem-custody-initialization.json"] or dem_preflight_unit.get("disposition") != "pass":
        fail("M2 DEM preflight milestone evidence differs")
    if dem_acquire_unit.get("inputs") != ["records/source-gates/m2-dem-live-source-gate.json", "records/acquisition/dem-preflight.json", "records/acquisition/dem-custody-initialization.json", "contracts/m2-dem-intake.json"]:
        fail("M2 DEM acquisition inputs differ")
    if active_m2.get("handoff", {}).get("parallel_checkpoint") != "M2-DEM-ACQUISITION":
        fail("active M2 DEM handoff did not advance to acquisition")
    if sar_capability.get("status") != "pass_capability_only_dem_dependency_unresolved":
        fail("ArcGIS SAR capability receipt status differs")
    sar_checks = sar_capability.get("checks", {})
    if sar_checks.get("all_named_tools_available") is not True or sar_checks.get("processing_executed") is not False:
        fail("ArcGIS SAR capability receipt does not preserve capability-only semantics")
    if dem_intake_candidate.get("intake_id") != "nepal-m2-dem-intake-001" or len(dem_intake_candidate.get("assets", [])) != 4:
        fail("M2 DEM intake candidate identity or asset count differs")
    if dem_intake_candidate.get("extensions", {}).get("status") != "candidate_static_control_not_authorized":
        fail("M2 DEM intake must remain a non-authorizing static candidate")
    if dem_intake_candidate.get("extensions", {}).get("candidate_manifest_sha256") != sha256("records/source-gates/m2-dem-candidate-manifest.json"):
        fail("M2 DEM intake candidate does not bind the exact DEM manifest")
    dem_intake_assets = dem_intake_candidate.get("assets", [])
    if {item.get("extensions", {}).get("source_id") for item in dem_intake_assets} != {
        "M2-DEM-001", "M2-DEM-002", "M2-DEM-003", "M2-DEM-004"
    }:
        fail("M2 DEM intake candidate source set differs")
    if sum(item.get("expected", {}).get("size_bytes", 0) for item in dem_intake_assets) != 170302058:
        fail("M2 DEM intake candidate total byte count differs")
    if any(
        item.get("state") != "planned"
        or item.get("attempts") != []
        or item.get("expected", {}).get("sha256") is not None
        for item in dem_intake_assets
    ):
        fail("M2 DEM intake candidate invents authority, attempts, or upstream SHA-256")
    if dem_verification_candidate.get("verification_id") != "NEPAL-M2-DEM-OFFLINE-VERIFICATION-001":
        fail("M2 DEM offline verification identity differs")
    if dem_verification_candidate.get("status") != "candidate_static_control_not_authorized":
        fail("M2 DEM offline verification must remain a non-authorizing candidate")
    dem_verification_authority = dem_verification_candidate.get("authority", {})
    if dem_verification_authority.get("dem_amendment_status") != "not_granted":
        fail("M2 DEM verification must retain the unapproved amendment state")
    if any(value is True for key, value in dem_verification_authority.items() if key != "dem_amendment_status"):
        fail("M2 DEM verification candidate must not authorize execution")
    dem_verification_inputs = dem_verification_candidate.get("inputs", {})
    for ref_key, hash_key in (
        ("candidate_manifest_ref", "candidate_manifest_sha256"),
        ("intake_contract_ref", "intake_contract_sha256"),
        ("amendment_proposal_ref", "amendment_proposal_sha256"),
        ("review_bundle_ref", "review_bundle_sha256"),
        ("approved_aoi_ref", "approved_aoi_sha256"),
    ):
        relative = dem_verification_inputs.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"M2 DEM verification is missing {ref_key}")
        if dem_verification_inputs.get(hash_key) != sha256(relative):
            fail(f"M2 DEM verification does not bind {ref_key}")
    if radar_processing_contract.get("contract_id") != "NEPAL-S1-BASELINE-PROCESSING-001":
        fail("radar processing contract identity differs")
    if radar_processing_contract.get("status") != "predeclared_no_real_processing":
        fail("radar processing contract must remain a predeclaration")
    if radar_processing_contract.get("analysis_crs", {}).get("wkid") != 32645:
        fail("radar processing contract must target EPSG:32645")
    if {item.get("pair_id") for item in radar_processing_contract.get("routes", [])} != {
        "PAIR-S1-ASC-R085-IW", "PAIR-S1-DESC-R121-IW"
    }:
        fail("radar processing contract route set differs")
    radar_bindings = radar_processing_contract.get("bindings", {})
    for ref_key, hash_key in (
        ("pair_plan_ref", "pair_plan_sha256"),
        ("pixel_readiness_ref", "pixel_readiness_sha256"),
        ("arcgis_capability_ref", "arcgis_capability_sha256"),
        ("dem_manifest_ref", "dem_manifest_sha256"),
        ("dem_intake_candidate_ref", "dem_intake_candidate_sha256"),
        ("dem_verification_candidate_ref", "dem_verification_candidate_sha256"),
        ("dem_amendment_proposal_ref", "dem_amendment_proposal_sha256"),
        ("dem_review_bundle_ref", "dem_review_bundle_sha256"),
    ):
        relative = radar_bindings.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"radar processing contract is missing {ref_key}")
        if radar_bindings.get(hash_key) != sha256(relative):
            fail(f"radar processing contract does not bind {ref_key}")
    radar_authority = radar_processing_contract.get("authority", {})
    if radar_authority.get("dem_download_or_pixel_use_authorized") is not False or radar_authority.get("auxiliary_orbit_download_authorized") is not False:
        fail("radar processing contract must not authorize DEM or orbit-file acquisition")
    if radar_processing_contract.get("vertical_datum", {}).get("status") != "defer_pending_empirical_check_or_explicit_method_decision":
        fail("radar processing contract must defer the EGM2008 and EGM96 mismatch")
    radar_chain = {item.get("operation"): item for item in radar_processing_contract.get("processing_chain", [])}
    if radar_chain.get("radiometric calibration", {}).get("calibration_type") != "BETA_NOUGHT":
        fail("radar processing contract must calibrate to beta nought")
    if radar_chain.get("radiometric terrain flattening", {}).get("calibration_type") != "GAMMA_NOUGHT":
        fail("radar processing contract must terrain-flatten to gamma nought")
    if radar_processing_contract.get("speckle_policy", {}).get("primary_quantitative_route") != "no despeckle":
        fail("radar primary quantitative speckle policy differs")
    if radar_processing_contract.get("claim_boundary", {}).get("sentinel_pixels_processed") is not False:
        fail("radar processing predeclaration invents real processing")
    if dem_radar_readiness.get("status") != "pass_static_controls_only_dependencies_deferred":
        fail("DEM and radar control-readiness receipt status differs")
    readiness_bindings = dem_radar_readiness.get("bindings", {})
    for ref_key, hash_key in (
        ("dem_candidate_manifest_ref", "dem_candidate_manifest_sha256"),
        ("dem_amendment_proposal_ref", "dem_amendment_proposal_sha256"),
        ("dem_review_bundle_ref", "dem_review_bundle_sha256"),
        ("dem_intake_candidate_ref", "dem_intake_candidate_sha256"),
        ("dem_verification_candidate_ref", "dem_verification_candidate_sha256"),
        ("radar_processing_contract_ref", "radar_processing_contract_sha256"),
        ("dem_control_builder_ref", "dem_control_builder_sha256"),
        ("dem_geotiff_verifier_ref", "dem_geotiff_verifier_sha256"),
        ("radar_contract_builder_ref", "radar_contract_builder_sha256"),
        ("dem_control_tests_ref", "dem_control_tests_sha256"),
        ("radar_contract_tests_ref", "radar_contract_tests_sha256"),
        ("dem_verification_protocol_ref", "dem_verification_protocol_sha256"),
        ("radar_processing_protocol_ref", "radar_processing_protocol_sha256"),
        ("arcgis_capability_ref", "arcgis_capability_sha256"),
    ):
        relative = readiness_bindings.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"DEM and radar readiness receipt is missing {ref_key}")
        if readiness_bindings.get(hash_key) != sha256(relative):
            fail(f"DEM and radar readiness receipt does not bind {ref_key}")
    if dem_radar_readiness.get("checks", {}).get("full_unit_suite") != {"status": "pass", "test_count": 82}:
        fail("DEM and radar readiness receipt must preserve 82 passing tests")
    readiness_assertions = dem_radar_readiness.get("assertions", {})
    if readiness_assertions.get("sentinel_product_bytes_transferred") != 0 or any(
        readiness_assertions.get(key) is not False
        for key in (
            "dem_payload_bytes_requested",
            "dem_license_accepted",
            "external_custody_mutated",
            "dem_pixels_examined",
            "sentinel_pixels_processed",
            "baseline_established",
            "scientific_result_established",
            "existing_dem_review_bundle_mutated",
        )
    ):
        fail("DEM and radar readiness receipt violates its no-payload claim boundary")
    if optical_processing_contract.get("contract_id") != "NEPAL-S2-BASELINE-PROCESSING-001":
        fail("optical processing contract identity differs")
    if optical_processing_contract.get("status") != "predeclared_no_real_processing":
        fail("optical processing contract must remain a predeclaration")
    optical_route = optical_processing_contract.get("route", {})
    if optical_route.get("pair_id") != "PAIR-S2-RUM-R119" or optical_route.get("before_source_id") != "M1-SRC-010" or optical_route.get("after_source_id") != "M1-SRC-008":
        fail("optical processing contract exact pair differs")
    if optical_route.get("processing_baseline_from_product_name") != "05.12":
        fail("optical processing contract baseline differs")
    optical_grid = optical_processing_contract.get("analysis_grid", {})
    if optical_grid.get("wkid") != 32645 or optical_grid.get("cell_size_m") != 20.0:
        fail("optical processing contract grid must use EPSG:32645 at 20 metres")
    if optical_grid.get("extent") != {"xmin": 273300.0, "ymin": 3070220.0, "xmax": 367820.0, "ymax": 3149220.0}:
        fail("optical processing contract grid extent differs")
    if optical_grid.get("columns") != 4726 or optical_grid.get("rows") != 3950:
        fail("optical processing contract grid dimensions differ")
    if optical_processing_contract.get("reflectance_scaling", {}).get("formula") != "(DN + BOA_ADD_OFFSET_band) / BOA_QUANTIFICATION_VALUE":
        fail("optical processing contract reflectance formula differs")
    if optical_processing_contract.get("reflectance_scaling", {}).get("dn_zero_policy") != "NoData_before_offset_or_scaling":
        fail("optical processing contract DN-zero policy differs")
    if set(optical_processing_contract.get("bands", {}).get("change_core", [])) != {"B02", "B03", "B04", "B08", "B11", "B12"}:
        fail("optical processing contract change-band set differs")
    if set(optical_processing_contract.get("mask", {}).get("valid_scl_classes", {})) != {"4", "5", "6"}:
        fail("optical processing contract valid SCL classes differ")
    if optical_processing_contract.get("cross_platform", {}).get("unmeasured_harmonization") != "prohibited":
        fail("optical processing contract must prohibit unmeasured harmonization")
    if optical_processing_contract.get("authority", {}).get("real_pixel_processing_started") is not False:
        fail("optical processing contract invents real processing")
    optical_bindings = optical_processing_contract.get("bindings", {})
    for ref_key, hash_key in (
        ("source_manifest_ref", "source_manifest_sha256"),
        ("source_manifest_approval_ref", "source_manifest_approval_sha256"),
        ("acquisition_plan_ref", "acquisition_plan_sha256"),
        ("active_verification_ref", "active_verification_sha256"),
        ("pair_plan_ref", "pair_plan_sha256"),
        ("pixel_readiness_ref", "pixel_readiness_sha256"),
        ("approved_aoi_ref", "approved_aoi_sha256"),
    ):
        relative = optical_bindings.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"optical processing contract is missing {ref_key}")
        if optical_bindings.get(hash_key) != sha256(relative):
            fail(f"optical processing contract does not bind {ref_key}")
    if optical_arcgis_receipt.get("status") != "pass_synthetic_only":
        fail("optical ArcGIS receipt status differs")
    if optical_arcgis_receipt.get("runtime") != {
        "product": "ArcGISPro",
        "version": "3.7.1",
        "license_level": "Advanced",
        "spatial_analyst": "available_and_used",
    }:
        fail("optical ArcGIS receipt runtime differs")
    optical_arcgis_inputs = optical_arcgis_receipt.get("inputs", {})
    for ref_key, hash_key in (
        ("contract", "contract_sha256"),
        ("core", "core_sha256"),
        ("arcgis_adapter", "arcgis_adapter_sha256"),
    ):
        relative = optical_arcgis_inputs.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"optical ArcGIS receipt is missing {ref_key}")
        if optical_arcgis_inputs.get(hash_key) != sha256(relative):
            fail(f"optical ArcGIS receipt does not bind {ref_key}")
    if set(optical_arcgis_receipt.get("checks", {})) != {"B03", "B04", "B08", "B11", "B12", "NDVI", "MNDWI", "NBR"}:
        fail("optical ArcGIS receipt check set differs")
    if any(item.get("status") != "pass" for item in optical_arcgis_receipt.get("checks", {}).values()):
        fail("optical ArcGIS receipt contains a failed check")
    optical_assertions = optical_arcgis_receipt.get("assertions", {})
    if optical_assertions.get("dn_zero_preserved_as_nodata") is not True or optical_assertions.get("excluded_scl_preserved_as_nodata") is not True:
        fail("optical ArcGIS receipt did not preserve NoData or SCL exclusions")
    if any(
        optical_assertions.get(key) is not False
        for key in (
            "real_product_metadata_parsed",
            "real_product_pixels_examined",
            "external_custody_accessed",
            "source_association_created",
            "optical_baseline_established",
            "change_established",
            "scientific_admission_authorized",
        )
    ):
        fail("optical ArcGIS receipt violates its synthetic-only claim boundary")
    if optical_readiness.get("status") != "pass_predeclared_and_synthetic_only_real_route_deferred":
        fail("optical control-readiness receipt status differs")
    optical_readiness_bindings = optical_readiness.get("bindings", {})
    for ref_key, hash_key in (
        ("optical_contract_ref", "optical_contract_sha256"),
        ("optical_core_ref", "optical_core_sha256"),
        ("contract_builder_ref", "contract_builder_sha256"),
        ("arcgis_adapter_ref", "arcgis_adapter_sha256"),
        ("arcgis_receipt_ref", "arcgis_receipt_sha256"),
        ("portable_tests_ref", "portable_tests_sha256"),
        ("protocol_ref", "protocol_sha256"),
        ("pair_plan_ref", "pair_plan_sha256"),
        ("pixel_readiness_ref", "pixel_readiness_sha256"),
        ("source_manifest_ref", "source_manifest_sha256"),
        ("active_m2_ref", "active_m2_sha256"),
    ):
        relative = optical_readiness_bindings.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"optical readiness receipt is missing {ref_key}")
        expected_hash = (
            "188af4575401473bb464dff84b83a90a41751b176c6a5e63a76f62acbe4e6bfb"
            if ref_key == "active_m2_ref"
            else sha256(relative)
        )
        if optical_readiness_bindings.get(hash_key) != expected_hash:
            fail(f"optical readiness receipt does not bind {ref_key}")
    if optical_readiness.get("validation", {}).get("portable_test_count") != 15 or optical_readiness.get("validation", {}).get("full_repository_test_count") != 97:
        fail("optical readiness receipt test counts differ")
    if optical_readiness.get("current_route_disposition", {}).get("status") != "defer":
        fail("optical real-data route must remain deferred")
    if materialization_contract.get("materialization_id") != "NEPAL-M2-SAFE-MATERIALIZATION-001" or materialization_contract.get("status") != "active_authorized_gate_deferred":
        fail("M2 materialization contract identity or gate-deferred status differs")
    materialization_inputs = materialization_contract.get("inputs", {})
    for ref_key, hash_key in (
        ("acquisition_plan_ref", "acquisition_plan_sha256"),
        ("activation_approval_ref", "activation_approval_sha256"),
        ("active_verification_ref", "active_verification_sha256"),
        ("materialization_core_ref", "materialization_core_sha256"),
        ("runner_ref", "runner_sha256"),
    ):
        relative = materialization_inputs.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"M2 materialization contract is missing {ref_key}")
        if materialization_inputs.get(hash_key) != sha256(relative):
            fail(f"M2 materialization contract does not bind {ref_key}")
    materialization_authority = materialization_contract.get("authority", {})
    if materialization_authority.get("mode") != "inherited" or materialization_authority.get("authority_ref") != "records/source-gates/m2-activation-approval.json":
        fail("M2 materialization does not inherit the exact active authority")
    if materialization_authority.get("this_contract_creates_authority") is not False or materialization_authority.get("dem_products_authorized") is not False or materialization_authority.get("network_access_authorized") is not False:
        fail("M2 materialization broadens authority")
    materialization_boundary = materialization_contract.get("execution_boundary", {})
    if materialization_boundary.get("external_data_root") != r"C:\Projects\Active\nepal-2026-before-after-map-data" or materialization_boundary.get("materialization_root") != r"C:\Projects\Active\nepal-2026-before-after-map-data\materialized":
        fail("M2 materialization external boundary differs")
    if materialization_boundary.get("network_requests") != "prohibited" or materialization_boundary.get("authentication") != "prohibited" or materialization_boundary.get("source_archive_mutation") != "prohibited":
        fail("M2 materialization must remain offline and read-only with respect to source archives")
    materialization_assets = materialization_contract.get("assets", [])
    expected_materialization_sources = {item["source_id"] for item in acquisition_plan["records"]}
    if len(materialization_assets) != 8 or {item.get("source_id") for item in materialization_assets} != expected_materialization_sources:
        fail("M2 materialization source set differs from the exact approved eight")
    verification_by_source = {item["source_id"]: item for item in active_offline_verification["assets"]}
    for item in materialization_assets:
        source = verification_by_source.get(item["source_id"])
        if not source or item.get("exact_product_id") != source.get("exact_product_id") or item.get("archive_relative_path") != source.get("archive_relative_path"):
            fail(f"M2 materialization asset differs from active verification for {item.get('source_id')}")
    if any(materialization_contract.get("claim_boundary", {}).get(key) is not False for key in (
        "raster_readability_established",
        "pixel_usability_established",
        "baseline_established",
        "change_established",
        "scientific_admission_authorized",
    )):
        fail("M2 materialization contract invents downstream evidence")
    if materialization_readiness.get("status") != "pass_synthetic_only_real_materialization_deferred":
        fail("M2 materialization readiness status differs")
    materialization_bindings = materialization_readiness.get("bindings", {})
    for ref_key, hash_key in (
        ("contract_ref", "contract_sha256"),
        ("core_ref", "core_sha256"),
        ("generator_ref", "generator_sha256"),
        ("runner_ref", "runner_sha256"),
        ("test_ref", "test_sha256"),
        ("protocol_ref", "protocol_sha256"),
        ("active_m2_ref", "active_m2_sha256_at_validation"),
        ("activation_approval_ref", "activation_approval_sha256"),
        ("acquisition_plan_ref", "acquisition_plan_sha256"),
    ):
        relative = materialization_bindings.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"M2 materialization readiness is missing {ref_key}")
        expected_hash = (
            "188af4575401473bb464dff84b83a90a41751b176c6a5e63a76f62acbe4e6bfb"
            if ref_key == "active_m2_ref"
            else sha256(relative)
        )
        if materialization_bindings.get(hash_key) != expected_hash:
            fail(f"M2 materialization readiness does not bind {ref_key}")
    materialization_validation = materialization_readiness.get("validation", {})
    if materialization_validation.get("targeted_test_count") != 14 or materialization_validation.get("full_repository_test_count") != 111:
        fail("M2 materialization readiness test counts differ")
    if materialization_readiness.get("current_disposition", {}).get("status") != "defer":
        fail("real M2 materialization must remain deferred at this checkpoint")
    if materialization_readiness.get("external_state") != {
        "custody_file_count": 0,
        "materialization_root_exists": False,
        "real_archive_bytes_read": 0,
        "real_archives_materialized": 0,
    }:
        fail("M2 materialization readiness historical external-state boundary differs")
    if optical_input_contract.get("contract_id") != "NEPAL-S2-MATERIALIZED-INPUT-READINESS-001" or optical_input_contract.get("status") != "predeclared_gate_deferred_no_real_safe":
        fail("optical input-readiness contract identity or status differs")
    optical_input_route = optical_input_contract.get("route", {})
    if optical_input_route.get("before_source_id") != "M1-SRC-010" or optical_input_route.get("after_source_id") != "M1-SRC-008" or optical_input_route.get("processing_baseline") != "05.12" or optical_input_route.get("tile") != "45RUM" or optical_input_route.get("relative_orbit") != 119:
        fail("optical input-readiness route differs from the exact pair")
    if optical_input_contract.get("analysis_crs", {}).get("wkid") != 32645:
        fail("optical input-readiness contract must use EPSG:32645")
    expected_input_roles = {
        "metadata_product", "metadata_tile", "B02", "B03", "B04", "B08", "B11", "B12", "SCL", "quality_classification"
    }
    if set(optical_input_contract.get("required_members", {}).get("role_patterns", {})) != expected_input_roles:
        fail("optical input-readiness member roles differ")
    input_header_rules = optical_input_contract.get("header_checks", {})
    if input_header_rules.get("single_band_roles") != ["B02", "B03", "B04", "B08", "B11", "B12", "SCL"]:
        fail("optical input-readiness single-band role declaration differs")
    if input_header_rules.get("quality_classification") != {
        "product_member": "MSK_CLASSI_B00.jp2",
        "band_count": 3,
        "cell_size_m": 60.0,
        "pixel_types": ["U1", "U8"],
        "band_semantics": {"1": "opaque_cloud", "2": "cirrus_cloud", "3": "snow_or_ice"},
    }:
        fail("optical input-readiness MSK_CLASSI model differs from the PB 05.12 specification")
    expected_input_source_references = [
        {
            "role": "sentinel2_multiband_mask_encoding",
            "url": "https://sentiwiki.copernicus.eu/web/s2-processing",
            "checked_at_utc": "2026-09-03T19:37:30Z",
        },
        {
            "role": "sentinel2_product_specification_v15_1",
            "url": "https://sentinels.copernicus.eu/documents/d/sentinel/sentinel-2-products-specification-document-15_1",
            "checked_at_utc": "2026-09-03T19:37:30Z",
        },
    ]
    if optical_input_contract.get("source_references") != expected_input_source_references:
        fail("optical input-readiness official source references differ")
    optical_input_contract_bindings = optical_input_contract.get("inputs", {})
    for ref_key, hash_key in (
        ("materialization_contract_ref", "materialization_contract_sha256"),
        ("optical_processing_contract_ref", "optical_processing_contract_sha256"),
        ("pixel_readiness_contract_ref", "pixel_readiness_contract_sha256"),
        ("source_manifest_ref", "source_manifest_sha256"),
        ("core_ref", "core_sha256"),
        ("runner_ref", "runner_sha256"),
        ("arcgis_adapter_ref", "arcgis_adapter_sha256"),
    ):
        relative = optical_input_contract_bindings.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"optical input-readiness contract is missing {ref_key}")
        if optical_input_contract_bindings.get(hash_key) != sha256(relative):
            fail(f"optical input-readiness contract does not bind {ref_key}")
    input_authority = optical_input_contract.get("authority", {})
    if input_authority.get("mode") != "inherited" or input_authority.get("this_contract_creates_authority") is not False or input_authority.get("network_access_authorized") is not False or input_authority.get("dem_products_authorized") is not False:
        fail("optical input-readiness authority boundary differs")
    if any(optical_input_contract.get("claim_boundary", {}).get(key) is not False for key in (
        "pixel_values_examined", "pixel_usability_established", "baseline_established", "change_established", "scientific_admission_authorized"
    )):
        fail("optical input-readiness contract invents downstream evidence")
    if optical_input_arcgis.get("status") != "pass_synthetic_only_with_expected_misalignment_block":
        fail("optical input-readiness ArcGIS receipt status differs")
    if optical_input_arcgis.get("runtime") != {
        "product": "ArcGISPro",
        "version": "3.7.1",
        "license_level": "Advanced",
        "gdal_version": "3120210",
        "jp2_driver": "JP2OpenJPEG",
    }:
        fail("optical input-readiness ArcGIS runtime differs")
    optical_input_arcgis_bindings = optical_input_arcgis.get("bindings", {})
    for ref_key, hash_key in (
        ("contract_ref", "contract_sha256"),
        ("core_ref", "core_sha256"),
        ("adapter_ref", "adapter_sha256"),
    ):
        relative = optical_input_arcgis_bindings.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file() or optical_input_arcgis_bindings.get(hash_key) != sha256(relative):
            fail(f"optical input-readiness ArcGIS receipt does not bind {ref_key}")
    fixture = optical_input_arcgis.get("fixture", {})
    if fixture.get("jp2_raster_count") != 16 or fixture.get("before_inventory_status") != "pass_inventory_only" or fixture.get("after_inventory_status") != "pass_inventory_only":
        fail("optical input-readiness synthetic inventory differs")
    for pair_role in ("before", "after"):
        descriptions = fixture.get("header_descriptions", {}).get(pair_role, {})
        if set(descriptions) != expected_input_roles - {"metadata_product", "metadata_tile"}:
            fail(f"optical input-readiness {pair_role} header inventory differs")
        if any(
            item.get("format") != "JP2"
            or item.get("wkid") != 32645
            or item.get("band_count") != (3 if role == "quality_classification" else 1)
            for role, item in descriptions.items()
        ):
            fail(f"optical input-readiness {pair_role} contains a nonpassing JP2 header")
        quality_header = descriptions.get("quality_classification", {})
        if quality_header.get("cell_width") != 60.0 or quality_header.get("cell_height") != 60.0 or quality_header.get("pixel_type") not in {"U1", "U8"}:
            fail(f"optical input-readiness {pair_role} MSK_CLASSI header differs")
        quality_bands = quality_header.get("band_details", [])
        if [item.get("name") for item in quality_bands] != ["Band_1", "Band_2", "Band_3"] or any(
            item.get("width") != 2
            or item.get("height") != 2
            or item.get("cell_width") != 60.0
            or item.get("cell_height") != 60.0
            or item.get("pixel_type") != "U8"
            for item in quality_bands
        ):
            fail(f"optical input-readiness {pair_role} MSK_CLASSI band headers differ")
        metadata_check = fixture.get("metadata_checks", {}).get(pair_role, {})
        if metadata_check.get("processing_baseline") != "05.12" or metadata_check.get("quantification_value") != 10000.0 or metadata_check.get("used_band_offset_count") != 6 or metadata_check.get("errors") != []:
            fail(f"optical input-readiness {pair_role} metadata check differs")
    if optical_input_arcgis.get("checks", {}).get("aligned_pair", {}).get("status") != "pass_header_readability_only":
        fail("optical input-readiness aligned synthetic pair did not pass")
    shifted_header = optical_input_arcgis.get("checks", {}).get("intentional_after_grid_shift", {})
    if shifted_header.get("status") != "block" or len(shifted_header.get("errors", [])) != 16:
        fail("optical input-readiness intentional grid shift did not retain its expected block")
    input_assertions = optical_input_arcgis.get("assertions", {})
    if input_assertions.get("synthetic_jp2_opened_by_arcgis") is not True or input_assertions.get("intentional_grid_shift_blocked") is not True:
        fail("optical input-readiness synthetic ArcGIS assertions differ")
    if any(input_assertions.get(key) is not False for key in (
        "external_custody_accessed", "real_materialization_receipt_used", "real_product_metadata_read", "real_product_pixels_examined", "pixel_usability_established", "baseline_established", "change_established", "scientific_admission_authorized"
    )):
        fail("optical input-readiness ArcGIS receipt violates its synthetic-only boundary")
    if optical_input_contract.get("header_checks", {}).get("extent_must_equal_dimensions_times_cell_size") is not True:
        fail("optical input-readiness contract must reconcile dimensions, cell sizes, and extents")
    if (
        len(optical_input_arcgis.get("retained_failures", [])) != 3
        or len(optical_input_arcgis.get("retained_prepublication_attempts", [])) != 5
        or len(optical_input_arcgis.get("retained_published_attempts", [])) != 1
    ):
        fail("optical input-readiness ArcGIS receipt did not retain every failed or superseded attempt")
    if optical_input_readiness.get("status") != "pass_corrected_synthetic_arcgis_real_input_deferred":
        fail("optical input-readiness control receipt status differs")
    control_bindings = optical_input_readiness.get("bindings", {})
    for ref_key, hash_key in (
        ("contract_ref", "contract_sha256"),
        ("core_ref", "core_sha256"),
        ("generator_ref", "generator_sha256"),
        ("runner_ref", "runner_sha256"),
        ("arcgis_adapter_ref", "arcgis_adapter_sha256"),
        ("test_ref", "test_sha256"),
        ("protocol_ref", "protocol_sha256"),
        ("arcgis_receipt_ref", "arcgis_receipt_sha256"),
        ("materialization_contract_ref", "materialization_contract_sha256"),
        ("optical_processing_contract_ref", "optical_processing_contract_sha256"),
        ("active_m2_ref", "active_m2_sha256_at_validation"),
        ("activation_approval_ref", "activation_approval_sha256"),
        ("acquisition_plan_ref", "acquisition_plan_sha256"),
    ):
        relative = control_bindings.get(ref_key)
        expected_hash = (
            "188af4575401473bb464dff84b83a90a41751b176c6a5e63a76f62acbe4e6bfb"
            if ref_key == "active_m2_ref"
            else sha256(relative) if isinstance(relative, str) and (ROOT / relative).is_file() else None
        )
        if not isinstance(relative, str) or not (ROOT / relative).is_file() or control_bindings.get(hash_key) != expected_hash:
            fail(f"optical input-readiness control receipt does not bind {ref_key}")
    input_validation = optical_input_readiness.get("validation", {})
    if (
        input_validation.get("portable_test_count") != 12
        or input_validation.get("full_repository_test_count") != 123
        or input_validation.get("synthetic_jp2_raster_count") != 16
        or input_validation.get("quality_classification_band_count") != 3
        or input_validation.get("quality_classification_cell_size_m") != 60.0
        or input_validation.get("intentional_after_grid_shift_error_count") != 16
    ):
        fail("optical input-readiness validation counts differ")
    if optical_input_readiness.get("supersedes") != {
        "evidence_record_id": "EVID-0026",
        "published_commit": "df3e93aadef064129c928463cc1f5eec562e3950",
        "reason": "Official Sentinel-2 documentation identifies PB 05.12 MSK_CLASSI_B00.jp2 as a three-band 60 m Boolean mask, not the one-band 20 m mask used by the published fixture.",
    }:
        fail("optical input-readiness correction does not preserve the exact superseded checkpoint")
    if optical_input_readiness.get("source_references") != expected_input_source_references:
        fail("optical input-readiness control receipt does not preserve its official sources")
    retained_published_corrections = optical_input_readiness.get("retained_published_control_corrections", [])
    if len(retained_published_corrections) != 1 or retained_published_corrections[0].get("status") != "superseded_after_publication":
        fail("optical input-readiness control receipt does not retain the published correction")
    if optical_input_readiness.get("current_disposition", {}).get("status") != "defer" or optical_input_readiness.get("external_state", {}).get("custody_file_count") != 0 or optical_input_readiness.get("external_state", {}).get("materialization_root_exists") is not False:
        fail("optical input-readiness real route must remain historically deferred with empty custody")
    if aoi_reconciliation["contract_sha256"] != sha256("reviews/m1-aoi/review-contract.json"):
        fail("AOI reconciliation does not bind the exact historical review contract")
    if approval["status"] != "approved" or approval["reviewed_aoi_sha256"] != sha256("config/aoi/draft-study-areas.geojson"):
        fail("AOI approval does not bind the exact reviewed geometry")
    if projected_aoi.get("spatialReference", {}).get("wkid") != 32645 or len(projected_aoi.get("features", [])) != 3:
        fail("approved ArcGIS AOI must contain three EPSG:32645 features")
    if arcgis_receipt["status"] != "pass" or arcgis_receipt["input_sha256"] != sha256("config/aoi/approved-study-areas-epsg32645.json"):
        fail("ArcGIS AOI validation receipt does not bind the projected artifact")
    expected_summary = {
        "candidate_count": 10,
        "proposed_accept_count": 8,
        "proposed_defer_count": 2,
        "proposed_reject_count": 0,
        "proposed_acquisition_catalog_bytes": 12451940706,
        "proposed_acquisition_catalog_gib": 11.597,
        "pixel_usability_established_count": 0,
    }
    if manifest["status"] != "candidate_for_owner_review" or manifest["summary"] != expected_summary:
        fail("candidate source-manifest state or summary is invalid")
    if any(record["local_custody"]["status"] != "not_acquired" for record in manifest["records"]):
        fail("candidate manifest must not claim full-product custody")
    if any(record["review_status"] != "candidate_manifest_not_approved" for record in manifest["records"]):
        fail("reviewed manifest bytes must remain immutable; approval belongs in the separate approval record")
    bundle_digest = sha256("reviews/m1-manifest/review-bundle.json")
    if manifest_bundle["candidate_identity"] != f"SOURCE-MANIFEST-SHA256:{sha256('records/source-manifest.json')}":
        fail("review bundle does not bind the exact source manifest")
    if manifest_contract["review_bundle"]["manifest_sha256"] != bundle_digest:
        fail("review contract does not bind the exact review bundle")
    if manifest_response["completed"] is not False or manifest_response["reviewer"]["attestation"] is not False:
        fail("public manifest response template must remain blank after the private exact response is locked")
    if manifest_reconciliation["contract_sha256"] != sha256("reviews/m1-manifest/review-contract.json"):
        fail("manifest reconciliation does not bind the exact review contract")
    if manifest_approval["status"] != "approved":
        fail("source manifest approval status is not approved")
    if manifest_approval["review_bundle_manifest_sha256"] != bundle_digest:
        fail("source manifest approval does not bind the exact review bundle")
    if manifest_approval["reviewed_manifest_sha256"] != sha256("records/source-manifest.json"):
        fail("source manifest approval does not bind the exact candidate manifest")
    if manifest_approval["review_reconciliation_sha256"] != sha256("records/source-gates/source-manifest-review-reconciliation.json"):
        fail("source manifest approval does not bind the exact reconciliation")
    if manifest_approval["locked_response_sha256"] != manifest_reconciliation["response_sha256"]:
        fail("source manifest approval and reconciliation response hashes differ")
    if manifest_approval["decision_counts"] != {"approve": 1, "revise": 0, "defer": 0}:
        fail("source manifest approval decision counts are invalid")
    if units["M1-AOI"]["status"] != "complete" or units["M1-MANIFEST"]["status"] != "complete":
        fail("M1 control units do not reflect the completed AOI and manifest gates")
    if any(condition["status"] != "pass" for condition in contract["exit_conditions"]):
        fail("all M1 exit conditions must pass")

    expected_plan_selection = {
        "approved_candidate_count": 8,
        "deferred_candidate_count": 2,
        "rejected_candidate_count": 0,
        "planned_download_count": 8,
        "catalog_content_length_bytes": 12451940706,
        "catalog_content_length_gib": 11.597,
    }
    if acquisition_plan["status"] != "candidate_for_owner_review" or acquisition_plan["selection"] != expected_plan_selection:
        fail("M2 acquisition plan state or selection is invalid")
    if acquisition_plan["source_manifest_sha256"] != sha256("records/source-manifest.json"):
        fail("M2 acquisition plan does not bind the exact approved manifest")
    if acquisition_plan["source_manifest_approval_sha256"] != sha256("records/source-gates/source-manifest-approval.json"):
        fail("M2 acquisition plan does not bind the exact manifest approval")
    if len(acquisition_plan["records"]) != 8 or any(record["acquisition_status"] != "not_authorized" for record in acquisition_plan["records"]):
        fail("M2 plan must contain eight exact products with no acquisition authorization")
    if acquisition_plan["custody"]["root_creation_status"] != "not_authorized":
        fail("M2 plan must not claim custody-root creation authority")
    if m2_proposal["status"] != "proposed" or m2_proposal["authority"]["mode"] != "not_granted":
        fail("M2 proposal must remain proposed and non-authorizing")
    if m2_proposal["authority"]["candidate_plan_sha256"] != sha256("records/acquisition-plan.json"):
        fail("M2 proposal does not bind the exact acquisition plan")
    if m2_contract["review_bundle"]["manifest_sha256"] != sha256("reviews/m2-activation/review-bundle.json"):
        fail("M2 review contract does not bind the exact review bundle")
    if m2_bundle["candidate_identity"] != f"ACQUISITION-PLAN-SHA256:{sha256('records/acquisition-plan.json')}":
        fail("M2 review bundle does not bind the exact acquisition plan")
    if m2_response["completed"] is not False or m2_response["reviewer"]["attestation"] is not False:
        fail("M2 public blank response must remain an unchanged historical review template")
    if m2_surface_receipt["status"] != "pass_with_retained_failure":
        fail("M2 review surface receipt must preserve its remediated visual failure")
    if m2_surface_receipt["surface_sha256"] != sha256("docs/assets/m2-controlled-acquisition-review.png"):
        fail("M2 surface receipt does not bind the exact rendered review surface")
    if m2_surface_receipt["renderer_sha256"] != sha256("scripts/render_m2_activation_review.py"):
        fail("M2 surface receipt does not bind the exact renderer")
    intake_extensions = intake_contract.get("extensions", {})
    if intake_extensions.get("status") != "candidate_static_control_not_authorized":
        fail("M2 intake contract must remain a non-authorizing candidate")
    if intake_extensions.get("source_plan_sha256") != sha256("records/acquisition-plan.json"):
        fail("M2 intake contract does not bind the exact acquisition plan")
    if intake_extensions.get("m2_proposal_sha256") != sha256("contracts/milestone-002-proposal.json"):
        fail("M2 intake contract does not bind the exact proposal")
    if intake_extensions.get("activation_review_bundle_sha256") != sha256("reviews/m2-activation/review-bundle.json"):
        fail("M2 intake contract does not bind the exact pending review bundle")
    if intake_contract.get("collision_policy") != "fail" or intake_contract.get("promotion_mode") != "atomic-no-replace":
        fail("M2 intake contract must fail on collision and use atomic no-replace promotion")
    if intake_contract.get("secret_policy") != "references-only":
        fail("M2 intake contract must keep secret values out of custody records")
    if len(intake_contract.get("assets", [])) != 8:
        fail("M2 intake contract must contain exactly eight approved assets")
    intake_source_ids = set()
    for asset in intake_contract["assets"]:
        if asset.get("state") != "planned" or asset.get("attempts") != []:
            fail("M2 intake assets must remain planned with no attempts before activation")
        if asset.get("expected", {}).get("sha256") is not None or asset.get("expected", {}).get("size_bytes") is not None:
            fail("M2 intake must not mistake catalog metadata for authenticated transfer identity")
        extensions = asset.get("extensions", {})
        source_id = extensions.get("source_id")
        intake_source_ids.add(source_id)
        provider_id = extensions.get("provider_product_id")
        expected_uri = f"https://download.dataspace.copernicus.eu/odata/v1/Products({provider_id})/$value"
        if asset.get("source", {}).get("uri") != expected_uri:
            fail(f"M2 intake route differs for {source_id}")
        if asset.get("source", {}).get("authorization_ref", "").split(":", 1)[0] != "pending":
            fail(f"M2 intake asset {source_id} must preserve pending authorization")
    if intake_source_ids != {record["source_id"] for record in acquisition_plan["records"]}:
        fail("M2 intake source set differs from the exact approved acquisition plan")

    if m2_activation.get("status") != "approved" or m2_activation.get("review_bundle_manifest_sha256") != sha256("reviews/m2-activation/review-bundle.json"):
        fail("M2 activation approval does not bind the exact reviewed bundle")
    if m2_activation.get("acquisition_plan_sha256") != sha256("records/acquisition-plan.json"):
        fail("M2 activation approval does not bind the exact acquisition plan")
    if m2_activation.get("locked_response_sha256") != m2_reconciliation.get("response_sha256"):
        fail("M2 activation and reconciliation response hashes differ")
    if m2_reconciliation.get("status") != "reconciled_exact_human_response" or m2_reconciliation.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}:
        fail("M2 activation response is not one exact reconciled approval")
    if m2_reconciliation.get("human_decisions_fabricated") is not False:
        fail("M2 activation reconciliation must reject fabricated decisions")
    if active_m2.get("status") != "active" or active_m2.get("authority", {}).get("mode") != "inherited":
        fail("M2 active contract state or authority mode is invalid")
    if active_m2.get("authority", {}).get("authority_ref") != "records/source-gates/m2-activation-approval.json":
        fail("M2 active contract does not cite the exact activation approval")
    if active_m2.get("authority", {}).get("approval_sha256") != sha256("records/source-gates/m2-activation-approval.json"):
        fail("M2 active contract approval hash differs")
    m2_units = {unit["id"]: unit for unit in active_m2.get("units", [])}
    if m2_units.get("M2-CUSTODY-PREFLIGHT", {}).get("disposition") != "pass" or "M2-ACQUIRE" not in m2_units:
        fail("M2 units do not preserve the passing preflight and acquisition unit")
    if m2_units["M2-ACQUIRE"].get("gates", {}).get("custody_initialization") != "pass":
        fail("M2 acquisition unit does not bind verified custody initialization")
    if m2_source_gate.get("decision", {}).get("status") != "ready" or len(m2_source_gate.get("sources", [])) != 8:
        fail("M2 live source gate must be ready for exactly eight products")
    if m2_source_gate.get("authority", {}).get("authority_ref") != "records/source-gates/m2-activation-approval.json":
        fail("M2 live source gate does not inherit the exact activation approval")
    if any(criterion.get("status") != "pass" for source in m2_source_gate["sources"] for criterion in source.get("criteria", [])):
        fail("M2 live source gate contains a non-passing criterion")
    if m2_preflight.get("status") != "pass_no_external_mutation":
        fail("M2 preflight did not preserve its non-mutating passing state")
    if m2_preflight.get("source_gate", {}).get("sha256") != sha256("records/source-gates/m2-live-source-gate.json"):
        fail("M2 preflight does not bind the exact live source gate")
    if len(m2_preflight.get("product_checks", [])) != 8 or any(item.get("status") != "pass" for item in m2_preflight["product_checks"]):
        fail("M2 preflight must preserve eight passing exact-product checks")
    if m2_preflight.get("paths", {}).get("external_data_root_exists_before_preflight") is not False:
        fail("M2 preflight must establish that the external root was absent before mutation")
    if m2_preflight.get("access", {}).get("credential_values_read_or_recorded") is not False or m2_preflight.get("access", {}).get("authentication_performed") is not False:
        fail("M2 preflight must not read credentials or authenticate")

    active_extensions = active_intake.get("extensions", {})
    if active_extensions.get("status") != "active_authorized_preflight_passed_custody_initialized" or active_extensions.get("custody_initialized") is not True:
        fail("active M2 intake must record initialized custody")
    if active_extensions.get("source_gate_sha256") != sha256("records/source-gates/m2-live-source-gate.json") or active_extensions.get("preflight_sha256") != sha256("records/acquisition/preflight.json"):
        fail("active M2 intake does not bind the live gate and preflight")
    if active_extensions.get("custody_initialization_sha256") != sha256("records/acquisition/custody-initialization.json"):
        fail("active M2 intake does not bind the custody receipt")
    if active_intake.get("collision_policy") != "fail" or active_intake.get("promotion_mode") != "atomic-no-replace" or active_intake.get("secret_policy") != "references-only":
        fail("active M2 intake weakens collision, promotion, or secret controls")
    if sha256("records/acquisition/active-intake-initial-snapshot.json") != INITIAL_ACTIVE_INTAKE_SHA256:
        fail("initial active-intake snapshot no longer has its activation-time identity")
    if initial_active_intake.get("assets") != active_intake.get("assets") and all(
        asset.get("state") == "authorized" and asset.get("attempts") == []
        for asset in active_intake.get("assets", [])
    ):
        fail("unattempted active intake differs from its immutable initial snapshot")
    acquisition_progress = validate_acquisition_progress(
        active_intake,
        initial_active_intake,
        acquisition_plan,
        root=ROOT,
        verify_external=False,
    )
    if acquisition_progress.get("status") != "pass":
        fail("active M2 acquisition progress is invalid: " + "; ".join(acquisition_progress.get("errors", [])))
    state_counts = acquisition_progress.get("state_counts", {})
    try:
        expected_checkpoint = derive_checkpoint(state_counts)["checkpoint_id"]
    except ValueError as exc:
        fail(f"active M2 acquisition checkpoint is ambiguous: {exc}")
    if profile["current_checkpoint"]["checkpoint_id"] != expected_checkpoint or goal.get("current_checkpoint") != expected_checkpoint:
        fail(f"profile and goal checkpoint must reconcile to {expected_checkpoint}")
    if m2_units.get("M2-ACQUIRE", {}).get("status") != "ready":
        fail("M2 acquisition unit must remain ready while one-product intake is incomplete")
    if m2_units["M2-ACQUIRE"].get("gates", {}).get("authentication") != "waiting_for_secret_safe_existing_owner_credential_reference":
        fail("each M2 acquisition invocation must still require a current secret-safe credential reference")
    if custody_receipt.get("status") != "created_and_verified":
        fail("M2 custody initialization receipt is not passing")
    if custody_receipt.get("bindings", {}).get("preflight_sha256") != sha256("records/acquisition/preflight.json") or custody_receipt.get("bindings", {}).get("source_gate_sha256") != sha256("records/source-gates/m2-live-source-gate.json"):
        fail("M2 custody receipt does not bind the preflight and source gate")
    receipt_verification = custody_receipt.get("verification", {})
    if receipt_verification.get("files_downloaded") != 0 or receipt_verification.get("authentication_performed") is not False or receipt_verification.get("credential_values_read_or_recorded") is not False:
        fail("M2 custody initialization must not claim authentication or product transfer")
    if transfer_readiness.get("status") != "pass_synthetic_only_no_authentication_or_product_transfer":
        fail("M2 transfer-runner readiness receipt has an invalid status")
    readiness_bindings = transfer_readiness.get("bindings", {})
    expected_transfer_bindings = {
        "active_contract_sha256": "188af4575401473bb464dff84b83a90a41751b176c6a5e63a76f62acbe4e6bfb",
        "active_intake_sha256": INITIAL_ACTIVE_INTAKE_SHA256,
        "activation_approval_sha256": sha256("records/source-gates/m2-activation-approval.json"),
        "transfer_core_sha256": sha256("scripts/m2_transfer_core.py"),
        "transfer_runner_sha256": sha256("scripts/acquire_m2_product.py"),
        "tests_sha256": sha256("tests/test_m2_transfer_core.py"),
    }
    if any(readiness_bindings.get(key) != value for key, value in expected_transfer_bindings.items()):
        fail("M2 transfer-runner readiness receipt has a stale artifact binding")
    if transfer_readiness.get("test", {}).get("status") != "pass" or transfer_readiness.get("test", {}).get("test_count") != 11:
        fail("M2 transfer-runner readiness receipt must preserve eleven passing local tests")
    readiness_activity = transfer_readiness.get("activity", {})
    if readiness_activity != {
        "network_requests_performed": False,
        "authentication_performed": False,
        "credential_values_read_or_recorded": False,
        "product_bytes_transferred": 0,
        "active_intake_mutated": False,
    }:
        fail("M2 transfer-runner readiness must not claim network, authentication, credential, data, or intake mutation")
    if acquisition_progress_readiness.get("status") != "pass_preacquisition_dynamic_progress_validation":
        fail("M2 acquisition-progress readiness receipt status differs")
    progress_bindings = acquisition_progress_readiness.get("bindings", {})
    expected_historical_progress_bindings = {
        "initial_snapshot_ref": "records/acquisition/active-intake-initial-snapshot.json",
        "initial_snapshot_sha256": "a2816e9244a0141bf797c3a3fba00e2d492e272fb4886e7ff9aff58ab3cb716c",
        "acquisition_plan_ref": "records/acquisition-plan.json",
        "acquisition_plan_sha256": "6261dc61061cb962f22163755047f080e309ed2d746cdcdd61e6cf61d7ec2a8d",
        "validator_ref": "scripts/validate_m2_acquisition_progress.py",
        "validator_sha256": "fc90a85e111135133a64249151086d7032c924148bcf5cc29cbee473703a9051",
        "test_ref": "tests/test_m2_acquisition_progress.py",
        "test_sha256": "5d1c59520d803daa05ba1bfef1ddcfbdbe894566a9cfb0c50f3c7dba00e2f191",
        "project_checker_ref": "scripts/check_project.py",
        "project_checker_sha256": "0811375064b8d2681690012d82234270f00022e23e94c82649c43f28ec5b7395",
        "runbook_ref": "docs/M2_EXECUTION_RUNBOOK.md",
        "runbook_sha256": "abd658d18a80f86bb3d8c4446eac9dfde7e268ffee44ee0841421838292d66ed",
    }
    if progress_bindings != expected_historical_progress_bindings:
        fail("M2 acquisition-progress readiness no longer preserves its published bindings")
    if acquisition_progress_readiness.get("validation") != {
        "focused_test_count": 9,
        "focused_test_status": "pass",
        "initial_repository_state": "pass",
        "initial_external_state": "pass",
        "initial_state_counts": {"authorized": 8},
        "synthetic_states_covered": ["authorized", "staging", "failed", "promoted"],
    }:
        fail("M2 acquisition-progress readiness validation differs")
    if acquisition_progress_readiness.get("activity") != {
        "network_requests_performed": False,
        "authentication_performed": False,
        "credential_values_read_or_recorded": False,
        "external_files_mutated": False,
        "active_intake_mutated": False,
    }:
        fail("M2 acquisition-progress readiness invents external activity")
    if acquisition_checkpoint_readiness.get("status") != "pass_preacquisition_checkpoint_derivation":
        fail("M2 acquisition-checkpoint readiness receipt status differs")
    checkpoint_bindings = acquisition_checkpoint_readiness.get("bindings", {})
    expected_historical_checkpoint_bindings = {
        "initial_snapshot_ref": "records/acquisition/active-intake-initial-snapshot.json",
        "initial_snapshot_sha256": "a2816e9244a0141bf797c3a3fba00e2d492e272fb4886e7ff9aff58ab3cb716c",
        "progress_validator_ref": "scripts/validate_m2_acquisition_progress.py",
        "progress_validator_sha256": "fc90a85e111135133a64249151086d7032c924148bcf5cc29cbee473703a9051",
        "derivation_ref": "scripts/derive_m2_acquisition_checkpoint.py",
        "derivation_sha256": "4d78913210978495b320dd70ace7d9e0ef3b7e9f7bf4f2804fbe444691b728a8",
        "test_ref": "tests/test_m2_checkpoint_reconciliation.py",
        "test_sha256": "41288357950546dc5d047dc24b8a699cb8ad4afe31c6adfa6ac28e55b0065798",
        "project_checker_ref": "scripts/check_project.py",
        "project_checker_sha256": "907bc0c3591e1f3c1e1e32c3651d3919c3f8ecfc83ac7f72f4ead92ca4d9498d",
        "runbook_ref": "docs/M2_EXECUTION_RUNBOOK.md",
        "runbook_sha256": "8b1aa06c0e4da9d56a9634c09822a8116aa23ed4db5c6c6aad66c9fb619201f3",
    }
    if checkpoint_bindings != expected_historical_checkpoint_bindings:
        fail("M2 acquisition-checkpoint readiness no longer preserves its published bindings")
    if acquisition_checkpoint_readiness.get("validation") != {
        "focused_test_count": 9,
        "focused_test_status": "pass",
        "repository_checkpoint_derivation": "pass",
        "external_state_reconciliation": "pass",
        "current_checkpoint": "M2-AUTHENTICATION-REFERENCE",
        "candidate_output_policy": "scratch_only_exclusive_no_replace",
    }:
        fail("M2 acquisition-checkpoint readiness validation differs")
    if acquisition_checkpoint_portability.get("status") != "pass_portable_repository_test_external_verification_separated":
        fail("M2 acquisition-checkpoint portability correction status differs")
    portability_bindings = acquisition_checkpoint_portability.get("bindings", {})
    expected_historical_portability_bindings = {
        "published_readiness_ref": "records/acquisition/acquisition-checkpoint-readiness.json",
        "published_readiness_sha256": "1a4439702be6ad448ec9eafc095d4bd25b692100b73dd19429fb20a1fde7eca9",
        "derivation_ref": "scripts/derive_m2_acquisition_checkpoint.py",
        "derivation_sha256": "4d78913210978495b320dd70ace7d9e0ef3b7e9f7bf4f2804fbe444691b728a8",
        "test_ref": "tests/test_m2_checkpoint_reconciliation.py",
        "test_sha256": "53e7e5d98b6e11a1ad3c4f3b9b6523e766bf74765d98f7a35b8e7ffeed2662a3",
        "project_checker_ref": "scripts/check_project.py",
        "project_checker_sha256": "0ea6c6cc5bcc32db19105dfd2cc2ca27bdf96e38f361f3c0a131b64ef64f6801",
    }
    if portability_bindings != expected_historical_portability_bindings:
        fail("M2 acquisition-checkpoint portability correction no longer preserves its published bindings")
    if acquisition_checkpoint_portability.get("validation") != {
        "focused_test_count": 9,
        "focused_test_status": "pass",
        "full_repository_test_count": 141,
        "full_repository_test_status": "pass",
        "repository_required_file_count": 146,
        "repository_validation_status": "pass",
        "portable_repository_derivation": "pass",
        "local_external_state_reconciliation": "pass",
        "failed_ci_run_id": 33800916326,
        "failed_ci_run_status": "failure",
    }:
        fail("M2 acquisition-checkpoint portability correction validation differs")
    if pair_plan.get("authority", {}).get("mode") != "not_granted" or pair_plan.get("authority", {}).get("authorized_actions") != [] or len(pair_plan.get("pairs", [])) != 3:
        fail("candidate pair plan must remain non-authorizing with three independent routes")
    if intake_dry_run.get("status") != "pass_static_only_no_authority":
        fail("M2 static dry run must remain explicitly non-authorizing")
    dry_inputs = intake_dry_run.get("inputs", {})
    expected_dry_inputs = {
        "acquisition_plan_sha256": sha256("records/acquisition-plan.json"),
        "m2_proposal_sha256": sha256("contracts/milestone-002-proposal.json"),
        "activation_review_bundle_sha256": sha256("reviews/m2-activation/review-bundle.json"),
        "intake_contract_sha256": sha256("contracts/m2-intake-candidate.json"),
    }
    if dry_inputs != expected_dry_inputs:
        fail("M2 static dry run does not bind its exact inputs")
    dry_authority = intake_dry_run.get("authority", {})
    if dry_authority.get("acquisition_authorized") is not False or dry_authority.get("network_or_authentication_performed") is not False:
        fail("M2 static dry run must not claim acquisition, network, or authentication activity")
    if intake_dry_run.get("path_model", {}).get("directories_created") is not False:
        fail("M2 static dry run must not claim external directory creation")

    if offline_verification.get("status") != "candidate_static_control_not_authorized":
        fail("M2 offline verification contract must remain non-authorizing")
    offline_inputs = offline_verification.get("inputs", {})
    expected_offline_inputs = {
        "acquisition_plan_ref": "records/acquisition-plan.json",
        "acquisition_plan_sha256": sha256("records/acquisition-plan.json"),
        "intake_contract_ref": "contracts/m2-intake-candidate.json",
        "intake_contract_sha256": sha256("contracts/m2-intake-candidate.json"),
        "manifest_approval_ref": "records/source-gates/source-manifest-approval.json",
        "manifest_approval_sha256": sha256("records/source-gates/source-manifest-approval.json"),
        "m2_review_bundle_ref": "reviews/m2-activation/review-bundle.json",
        "m2_review_bundle_sha256": sha256("reviews/m2-activation/review-bundle.json"),
    }
    if offline_inputs != expected_offline_inputs:
        fail("M2 offline verification contract does not bind its exact approved inputs")
    offline_authority = offline_verification.get("authority", {})
    if offline_authority.get("m2_activation_status") != "not_granted":
        fail("M2 offline verification contract must preserve the pending activation gate")
    if any(value for key, value in offline_authority.items() if key != "m2_activation_status"):
        fail("M2 offline verification contract must not create operational authority")
    boundary = offline_verification.get("execution_boundary", {})
    if boundary.get("network_requests") != "prohibited" or boundary.get("archive_extraction") != "prohibited":
        fail("M2 offline verification must prohibit network requests and archive extraction")
    if boundary.get("custody_root_must_already_exist") is not True or boundary.get("overwrite_existing_receipt") is not False:
        fail("M2 offline verification must refuse root creation and receipt replacement")

    if active_offline_verification.get("status") != "active_authorized_offline_verification":
        fail("active M2 offline verification contract has an invalid status")
    active_verification_inputs = active_offline_verification.get("inputs", {})
    expected_active_verification_hashes = {
        "candidate_contract_sha256": sha256("contracts/m2-offline-verification-candidate.json"),
        "acquisition_plan_sha256": sha256("records/acquisition-plan.json"),
        "active_milestone_sha256_at_activation": "188af4575401473bb464dff84b83a90a41751b176c6a5e63a76f62acbe4e6bfb",
        "activation_approval_sha256": sha256("records/source-gates/m2-activation-approval.json"),
        "active_intake_sha256_at_activation": INITIAL_ACTIVE_INTAKE_SHA256,
        "source_gate_sha256": sha256("records/source-gates/m2-live-source-gate.json"),
        "custody_initialization_sha256": sha256("records/acquisition/custody-initialization.json"),
    }
    if any(active_verification_inputs.get(key) != value for key, value in expected_active_verification_hashes.items()):
        fail("active M2 offline verification contract has a stale evidence binding")
    active_verification_authority = active_offline_verification.get("authority", {})
    if active_verification_authority.get("mode") != "inherited" or active_verification_authority.get("authority_ref") != "records/source-gates/m2-activation-approval.json":
        fail("active M2 offline verification does not inherit exact M2 authority")
    if active_verification_authority.get("offline_verification_authorized") is not True or active_verification_authority.get("this_contract_creates_authority") is not False:
        fail("active M2 offline verification authority semantics are invalid")
    if active_offline_verification.get("assets") != offline_verification.get("assets"):
        fail("active M2 offline verification changed the exact candidate product controls")
    active_boundary = active_offline_verification.get("execution_boundary", {})
    if active_boundary.get("network_requests") != "prohibited" or active_boundary.get("archive_extraction") != "prohibited" or active_boundary.get("source_archive_mutation") != "prohibited":
        fail("active M2 offline verification must remain offline, non-extracting, and read-only")
    if active_offline_verification.get("activation_boundary", {}).get("product_bytes_read") != 0:
        fail("activating M2 offline verification must not claim product-byte access")
    offline_assets = offline_verification.get("assets", [])
    if len(offline_assets) != 8:
        fail("M2 offline verification contract must contain exactly eight assets")
    offline_by_source = {item.get("source_id"): item for item in offline_assets}
    plan_by_source = {item["source_id"]: item for item in acquisition_plan["records"]}
    intake_by_source = {item["extensions"]["source_id"]: item for item in intake_contract["assets"]}
    if set(offline_by_source) != set(plan_by_source):
        fail("M2 offline verification source set differs from the approved plan")
    required_radar_patterns = {
        "measurement/*-vv-*.tiff",
        "measurement/*-vh-*.tiff",
        "annotation/calibration/calibration-*-vv-*.xml",
        "annotation/calibration/noise-*-vh-*.xml",
    }
    required_optical_patterns = {
        "GRANULE/*/IMG_DATA/R10m/*_B02_10m.jp2",
        "GRANULE/*/IMG_DATA/R10m/*_B08_10m.jp2",
        "GRANULE/*/IMG_DATA/R20m/*_B11_20m.jp2",
        "GRANULE/*/IMG_DATA/R20m/*_B12_20m.jp2",
        "GRANULE/*/IMG_DATA/R20m/*_SCL_20m.jp2",
    }
    for source_id, offline_asset in offline_by_source.items():
        plan_asset = plan_by_source[source_id]
        intake_asset = intake_by_source[source_id]
        if offline_asset.get("exact_product_id") != plan_asset["exact_product_id"]:
            fail(f"M2 offline verification product identity differs for {source_id}")
        if offline_asset.get("archive_relative_path") != intake_asset["destination_relative_path"]:
            fail(f"M2 offline verification custody path differs for {source_id}")
        checksums = {item["Algorithm"].casefold(): item["Value"].casefold() for item in plan_asset["provider_checksums"]}
        if offline_asset.get("provider_md5") != checksums.get("md5"):
            fail(f"M2 offline verification provider MD5 differs for {source_id}")
        if offline_asset.get("provider_blake3_metadata") != checksums.get("blake3"):
            fail(f"M2 offline verification provider BLAKE3 metadata differs for {source_id}")
        patterns = {item.get("pattern") for item in offline_asset.get("required_members", [])}
        required = required_radar_patterns if plan_asset["sensor_route"] == "radar" else required_optical_patterns
        if not required.issubset(patterns):
            fail(f"M2 offline verification structural profile is incomplete for {source_id}")
    if readiness_input.get("candidate_manifest_sha256") != sha256("records/source-manifest.json"):
        fail("M2 readiness audit does not bind the approved source manifest")
    required_gate_ids = set(readiness_input.get("required_gate_ids", []))
    if len(required_gate_ids) != 9:
        fail("M2 readiness audit must preserve nine required non-count gates")
    if {gate.get("gate_id") for gate in readiness_input.get("gates", [])} != required_gate_ids:
        fail("M2 readiness audit gate inventory differs")
    if any(gate.get("status") != "defer" for gate in readiness_input.get("gates", [])):
        fail("M2 pre-acquisition readiness gates must remain deferred")
    if readiness_input.get("next_step_authority") != {
        "mode": "not_granted",
        "authority_ref": "reviews/m2-activation/review-bundle.json",
        "authorized_actions": [],
    }:
        fail("M2 readiness audit must not create next-step authority")
    if readiness_decision.get("audit_input_sha256") != sha256("records/readiness/m2-readiness-audit-input.json"):
        fail("M2 readiness decision does not bind its exact audit input")
    if readiness_decision.get("decision") != "defer":
        fail("M2 readiness decision must remain defer before acquisition and pixel evidence")
    if set(readiness_decision.get("deferred_required_gate_ids", [])) != required_gate_ids:
        fail("M2 readiness decision does not retain every unresolved required gate")
    if readiness_decision.get("blocking_required_gate_ids") != [] or readiness_decision.get("pass_evidence") != []:
        fail("M2 readiness decision must not invent blocking or passing gate evidence")
    if readiness_decision.get("authorized_next_actions") != [] or readiness_decision.get("training_authorized_by_this_audit") is not False:
        fail("M2 readiness decision must not authorize downstream work")
    if reproducibility["status"] != "pass_with_retained_failures":
        fail("M1 reproducibility receipt is not in a passing state")
    for check in reproducibility["checks"]:
        if check["status"] != "pass" or check["sha256"] != sha256(check["artifact"]):
            fail(f"reproducibility receipt does not bind {check['artifact']}")

    if evidence_workspace.get("status") != "pass_with_retained_failures":
        fail("ArcGIS evidence workspace receipt is not in a passing state")
    if evidence_workspace.get("runtime") != {"product": "ArcGISPro", "version": "3.7.1", "license_level": "Advanced"}:
        fail("ArcGIS evidence workspace runtime differs from the validated environment")
    evidence_inputs = evidence_workspace.get("inputs", {})
    for path_key, hash_key in (
        ("schema", "schema_sha256"),
        ("approved_aoi", "approved_aoi_sha256"),
        ("source_manifest", "source_manifest_sha256"),
        ("manifest_approval", "manifest_approval_sha256"),
        ("builder", "builder_sha256"),
    ):
        relative = evidence_inputs.get(path_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"ArcGIS evidence workspace receipt is missing {path_key}")
        if evidence_inputs.get(hash_key) != sha256(relative):
            fail(f"ArcGIS evidence workspace receipt does not bind {path_key}")
    preview = evidence_workspace.get("public_preview", {})
    preview_relative = preview.get("path")
    if not isinstance(preview_relative, str) or not (ROOT / preview_relative).is_file():
        fail("ArcGIS evidence workspace preview is missing")
    if preview.get("sha256") != sha256(preview_relative) or preview.get("visual_inspection") != "pass":
        fail("ArcGIS evidence workspace preview is unbound or not visually approved")
    if len(evidence_schema.get("datasets", [])) != 9 or len(evidence_schema.get("domains", {})) != 14:
        fail("ArcGIS evidence schema must contain nine datasets and fourteen domains")
    if len(evidence_schema.get("relationships", [])) != 8:
        fail("ArcGIS evidence schema must contain eight relationship classes")
    dataset_names = {item["name"] for item in evidence_schema["datasets"]}
    if not {"ObservedChange", "Interpretations", "AttributionAssessments"}.issubset(dataset_names):
        fail("ArcGIS evidence schema must separate observation, interpretation, and attribution")
    relationship_names = {item["name"] for item in evidence_schema["relationships"]}
    if not {"ObservedChange_Interpretations", "Interpretations_Attribution"}.issubset(relationship_names):
        fail("ArcGIS evidence schema must link observation to interpretation and attribution")
    expected_workspace_counts = evidence_schema.get("initial_counts", {})
    actual_workspace_counts = {
        name: details.get("row_count")
        for name, details in evidence_workspace.get("workspace", {}).get("datasets", {}).items()
    }
    if expected_workspace_counts != actual_workspace_counts:
        fail("ArcGIS evidence workspace row counts differ from the declared empty scientific state")
    feature_wkids = {
        name: details.get("spatial_reference_wkid")
        for name, details in evidence_workspace["workspace"]["datasets"].items()
        if name in {"StudyAreas", "ObservedChange", "AnalysisExclusions", "StableControls"}
    }
    if set(feature_wkids.values()) != {32645}:
        fail("ArcGIS evidence feature classes must use EPSG:32645")
    record_states = set(evidence_schema["domains"]["DOM_RECORD_STATUS"]["coded_values"])
    if not {"rejected", "deferred", "inconclusive", "invalid", "superseded"}.issubset(record_states):
        fail("ArcGIS evidence schema does not preserve required adverse record states")
    if len(evidence_workspace.get("retained_failures", [])) != 6:
        fail("ArcGIS evidence workspace must retain all six failed attempts")
    if {item.get("status") for item in evidence_workspace["retained_failures"]} != {"fail", "fail_visual"}:
        fail("ArcGIS evidence workspace retained failure types differ")
    if evidence_workspace.get("checks", {}).get("visual_inspection") != "pass":
        fail("ArcGIS evidence workspace visual inspection did not pass")
    if not any("No satellite pixels" in item for item in evidence_workspace.get("limitations", [])):
        fail("ArcGIS evidence workspace must preserve its no-pixels claim boundary")

    if pixel_contract.get("contract_id") != "NEPAL-PIXEL-QA-001" or pixel_contract.get("status") != "predeclared_before_product_pixels":
        fail("pixel-readiness contract identity or predeclaration status differs")
    if pixel_contract.get("analysis_crs", {}).get("wkid") != 32645:
        fail("pixel-readiness contract must use EPSG:32645")
    if pixel_contract.get("decision_semantics", {}).get("precedence") != ["invalid", "block", "defer", "pass_qa_only"]:
        fail("pixel-readiness decision precedence differs")
    if pixel_contract.get("decision_semantics", {}).get("pass_qa_only_creates_scientific_admission") is not False:
        fail("pixel-readiness pass must not create scientific admission")
    if pixel_contract.get("aoi_coverage", {}) != {
        "full_coverage_pass_minimum": 0.99,
        "usable_fraction_pass_minimum": 0.8,
        "partial_evidence_defer_minimum": 0.2,
        "area_consistency_tolerance_fraction": 0.02,
        "fraction_precision": 6,
        "rules": pixel_contract.get("aoi_coverage", {}).get("rules"),
    }:
        fail("pixel-readiness AOI thresholds differ")
    if set(pixel_contract.get("optical_scl", {}).get("valid_surface_classes", {})) != {"4", "5", "6"}:
        fail("pixel-readiness optical valid classes differ")
    if pixel_receipt.get("status") != "pass_synthetic_only_with_expected_block_and_defer":
        fail("synthetic ArcGIS pixel-QA receipt status differs")
    if pixel_receipt.get("runtime") != {
        "product": "ArcGISPro",
        "version": "3.7.1",
        "license_level": "Advanced",
        "spatial_analyst": "available_and_used",
    }:
        fail("synthetic ArcGIS pixel-QA runtime differs")
    pixel_inputs = pixel_receipt.get("inputs", {})
    for path_key, hash_key in (
        ("contract", "contract_sha256"),
        ("approved_aoi", "approved_aoi_sha256"),
        ("core", "core_sha256"),
        ("arcgis_adapter", "arcgis_adapter_sha256"),
    ):
        relative = pixel_inputs.get(path_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"synthetic ArcGIS pixel-QA receipt is missing {path_key}")
        if pixel_inputs.get(hash_key) != sha256(relative):
            fail(f"synthetic ArcGIS pixel-QA receipt does not bind {path_key}")
    fixture = pixel_receipt.get("synthetic_fixture", {})
    if fixture.get("wkid") != 32645 or fixture.get("cell_size_m") != 20.0:
        fail("synthetic ArcGIS pixel-QA fixture grid differs")
    if not isinstance(fixture.get("rows"), int) or fixture["rows"] <= 0 or not isinstance(fixture.get("columns"), int) or fixture["columns"] <= 0:
        fail("synthetic ArcGIS pixel-QA fixture dimensions are invalid")
    pixel_checks = pixel_receipt.get("checks", {})
    aoi_pixel_results = pixel_checks.get("aoi_scl_coverage", [])
    if {item.get("aoi_id") for item in aoi_pixel_results} != {"AOI-OVERVIEW", "AOI-SOURCE", "AOI-UPPER-CORRIDOR"}:
        fail("synthetic ArcGIS pixel-QA AOI inventory differs")
    if any(
        item.get("status") != "pass_qa_only"
        or item.get("coverage_fraction", 0) < 0.99
        or item.get("usable_fraction_of_aoi", 0) < 0.8
        or item.get("unknown_scl_classes") != []
        or item.get("scientific_admission_authorized") is not False
        for item in aoi_pixel_results
    ):
        fail("synthetic ArcGIS pixel-QA AOI result differs from the predeclared pass-only boundary")
    if pixel_checks.get("aligned_grid_pair", {}).get("status") != "pass_qa_only":
        fail("synthetic aligned raster pair did not pass grid QA")
    shifted = pixel_checks.get("deliberately_misaligned_grid_pair", {})
    if shifted.get("status") != "block" or not any("origins" in item for item in shifted.get("errors", [])):
        fail("synthetic shifted raster did not preserve the expected grid block")
    if pixel_checks.get("registration_not_measured", {}).get("status") != "defer":
        fail("synthetic unmeasured registration did not remain deferred")
    expected_pixel_assertions = {
        "all_three_aoi_coverage_results_pass_qa_only": True,
        "aligned_grid_pair_passes_qa_only": True,
        "subpixel_shift_is_blocked": True,
        "unmeasured_registration_is_deferred": True,
        "real_product_pixels_examined": False,
        "scientific_admission_authorized": False,
        "m2_activated": False,
    }
    if pixel_receipt.get("assertions") != expected_pixel_assertions:
        fail("synthetic ArcGIS pixel-QA assertions differ")
    if pixel_receipt.get("preserved_review_bindings") != {
        "acquisition_plan_sha256": sha256("records/acquisition-plan.json"),
        "m2_activation_review_bundle_sha256": sha256("reviews/m2-activation/review-bundle.json"),
    }:
        fail("synthetic ArcGIS pixel-QA receipt does not preserve M2 review bindings")

    ledger_records = []
    for number, line in enumerate(
        (ROOT / "records/evidence-ledger.jsonl").read_text(encoding="utf-8").splitlines(), 1
    ):
        if line.strip():
            try:
                ledger_records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                fail(f"invalid evidence ledger JSON on line {number}: {exc}")
    ledger_by_id = {record.get("record_id"): record for record in ledger_records}
    offline_evidence = ledger_by_id.get("EVID-0020")
    if not isinstance(offline_evidence, dict):
        fail("evidence ledger is missing EVID-0020 offline verification evidence")
    for ref_key, hash_key in (
        ("verification_contract_ref", "verification_contract_sha256"),
        ("readiness_input_ref", "readiness_input_sha256"),
        ("readiness_decision_ref", "readiness_decision_sha256"),
        ("generator_ref", "generator_sha256"),
        ("test_ref", "test_sha256"),
    ):
        relative = offline_evidence.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"EVID-0020 is missing {ref_key}")
        if offline_evidence.get(hash_key) != sha256(relative):
            fail(f"EVID-0020 does not bind {ref_key}")
    if offline_evidence.get("independent_readiness_audit", {}).get("decision") != "defer":
        fail("EVID-0020 must preserve the independent DEFER readiness decision")
    if offline_evidence.get("preserved_review_bindings") != {
        "acquisition_plan_sha256": sha256("records/acquisition-plan.json"),
        "m2_activation_review_bundle_sha256": sha256("reviews/m2-activation/review-bundle.json"),
    }:
        fail("EVID-0020 does not preserve the exact M2 review bindings")
    pixel_evidence = ledger_by_id.get("EVID-0021")
    if not isinstance(pixel_evidence, dict):
        fail("evidence ledger is missing EVID-0021 pixel-readiness evidence")
    for ref_key, hash_key in (
        ("contract_ref", "contract_sha256"),
        ("core_ref", "core_sha256"),
        ("arcgis_adapter_ref", "arcgis_adapter_sha256"),
        ("portable_test_ref", "portable_test_sha256"),
        ("protocol_ref", "protocol_sha256"),
        ("receipt_ref", "receipt_sha256"),
    ):
        relative = pixel_evidence.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"EVID-0021 is missing {ref_key}")
        if pixel_evidence.get(hash_key) != sha256(relative):
            fail(f"EVID-0021 does not bind {ref_key}")
    if pixel_evidence.get("portable_test_count") != 11 or pixel_evidence.get("arcgis_native_result") != {
        "aoi_pass_qa_only_count": 3,
        "aligned_grid_status": "pass_qa_only",
        "misaligned_grid_status": "block",
        "registration_not_measured_status": "defer",
    }:
        fail("EVID-0021 validation summary differs")
    if pixel_evidence.get("preserved_review_bindings") != {
        "acquisition_plan_sha256": sha256("records/acquisition-plan.json"),
        "m2_activation_review_bundle_sha256": sha256("reviews/m2-activation/review-bundle.json"),
    }:
        fail("EVID-0021 does not preserve the exact M2 review bindings")
    dem_evidence = ledger_by_id.get("EVID-0022")
    if not isinstance(dem_evidence, dict):
        fail("evidence ledger is missing EVID-0022 DEM dependency review evidence")
    for ref_key, hash_key in (
        ("arcgis_capability_ref", "arcgis_capability_sha256"),
        ("metadata_receipt_ref", "metadata_receipt_sha256"),
        ("candidate_manifest_ref", "candidate_manifest_sha256"),
        ("source_gate_ref", "source_gate_sha256"),
        ("amendment_proposal_ref", "amendment_proposal_sha256"),
        ("review_bundle_ref", "review_bundle_manifest_sha256"),
        ("review_surface_ref", "review_surface_sha256"),
        ("test_ref", "test_sha256"),
    ):
        relative = dem_evidence.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"EVID-0022 is missing {ref_key}")
        if dem_evidence.get(hash_key) != sha256(relative):
            fail(f"EVID-0022 does not bind {ref_key}")
    if dem_evidence.get("status") != "ready_for_human_review_source_gate_blocked":
        fail("EVID-0022 must preserve the blocked DEM source gate")
    if dem_evidence.get("assertions") != {
        "dem_payload_bytes_requested": False,
        "account_or_authentication_used": False,
        "dem_pixels_examined": False,
        "sentinel_processing_executed": False,
        "authority_created": False,
    }:
        fail("EVID-0022 claim boundary differs")
    dem_radar_evidence = ledger_by_id.get("EVID-0023")
    if not isinstance(dem_radar_evidence, dict):
        fail("evidence ledger is missing EVID-0023 DEM and radar control evidence")
    for ref_key, hash_key in (
        ("receipt_ref", "receipt_sha256"),
        ("dem_intake_ref", "dem_intake_sha256"),
        ("dem_verification_ref", "dem_verification_sha256"),
        ("radar_contract_ref", "radar_contract_sha256"),
        ("dem_protocol_ref", "dem_protocol_sha256"),
        ("radar_protocol_ref", "radar_protocol_sha256"),
        ("dem_test_ref", "dem_test_sha256"),
        ("radar_test_ref", "radar_test_sha256"),
    ):
        relative = dem_radar_evidence.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"EVID-0023 is missing {ref_key}")
        if dem_radar_evidence.get(hash_key) != sha256(relative):
            fail(f"EVID-0023 does not bind {ref_key}")
    if dem_radar_evidence.get("status") != "pass_static_controls_only_dependencies_deferred":
        fail("EVID-0023 must preserve its static-only deferred status")
    if dem_radar_evidence.get("validation", {}).get("full_unit_test_count") != 82:
        fail("EVID-0023 must preserve 82 passing tests")
    if dem_radar_evidence.get("assertions") != dem_radar_readiness.get("assertions"):
        fail("EVID-0023 and its readiness receipt have different claim boundaries")
    optical_evidence = ledger_by_id.get("EVID-0024")
    if not isinstance(optical_evidence, dict):
        fail("evidence ledger is missing EVID-0024 optical processing evidence")
    for ref_key, hash_key in (
        ("readiness_receipt_ref", "readiness_receipt_sha256"),
        ("arcgis_receipt_ref", "arcgis_receipt_sha256"),
        ("contract_ref", "contract_sha256"),
        ("core_ref", "core_sha256"),
        ("builder_ref", "builder_sha256"),
        ("arcgis_adapter_ref", "arcgis_adapter_sha256"),
        ("test_ref", "test_sha256"),
        ("protocol_ref", "protocol_sha256"),
    ):
        relative = optical_evidence.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"EVID-0024 is missing {ref_key}")
        if optical_evidence.get(hash_key) != sha256(relative):
            fail(f"EVID-0024 does not bind {ref_key}")
    if optical_evidence.get("status") != "pass_synthetic_only_real_route_deferred":
        fail("EVID-0024 must preserve its synthetic-only deferred status")
    if optical_evidence.get("route_disposition", {}).get("status") != "defer":
        fail("EVID-0024 real optical route must remain deferred")
    if optical_evidence.get("assertions") != optical_readiness.get("assertions"):
        fail("EVID-0024 and optical readiness receipt have different claim boundaries")
    materialization_evidence = ledger_by_id.get("EVID-0025")
    if not isinstance(materialization_evidence, dict):
        fail("evidence ledger is missing EVID-0025 materialization preparation evidence")
    for ref_key, hash_key in (
        ("readiness_receipt_ref", "readiness_receipt_sha256"),
        ("contract_ref", "contract_sha256"),
        ("core_ref", "core_sha256"),
        ("generator_ref", "generator_sha256"),
        ("runner_ref", "runner_sha256"),
        ("test_ref", "test_sha256"),
        ("protocol_ref", "protocol_sha256"),
    ):
        relative = materialization_evidence.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            fail(f"EVID-0025 is missing {ref_key}")
        if materialization_evidence.get(hash_key) != sha256(relative):
            fail(f"EVID-0025 does not bind {ref_key}")
    if materialization_evidence.get("status") != "pass_synthetic_only_real_materialization_deferred":
        fail("EVID-0025 must preserve its synthetic-only deferred status")
    if materialization_evidence.get("current_disposition", {}).get("status") != "defer":
        fail("EVID-0025 real materialization route must remain deferred")
    evidence_assertions = materialization_evidence.get("assertions", {})
    readiness_assertions = materialization_readiness.get("assertions", {})
    for key in (
        "synthetic_materialization_passed",
        "external_materialization_directory_created",
        "real_archive_read",
        "real_safe_materialized",
        "raster_readability_established",
        "pixel_usability_established",
        "baseline_established",
        "change_established",
        "scientific_admission_authorized",
    ):
        if evidence_assertions.get(key) != readiness_assertions.get(key):
            fail(f"EVID-0025 and materialization readiness differ for {key}")
    if evidence_assertions.get("authority_created") is not False:
        fail("EVID-0025 must not create authority")
    historical_input_evidence = ledger_by_id.get("EVID-0026")
    if not isinstance(historical_input_evidence, dict):
        fail("evidence ledger is missing EVID-0026 optical input-readiness evidence")
    historical_input_bindings = (
        ("readiness_receipt_ref", "records/surface-receipts/optical-input-readiness-control.json", "readiness_receipt_sha256", "16b16e2dfebd829940340ff1ebfb9e19a038b162b9435efe5c064453cc61b55f"),
        ("arcgis_receipt_ref", "records/surface-receipts/optical-input-readiness-synthetic-arcgis.json", "arcgis_receipt_sha256", "3910aa085534a8721c0f70d50603950fe709cd0b6f084a5b7eb0b8c16b97836c"),
        ("contract_ref", "config/qa/optical-input-readiness-contract.json", "contract_sha256", "7cbcedef168a7e052ea44a8cd9b838281ace5c6b3d196a3ecd8d642ac3605427"),
        ("core_ref", "scripts/optical_input_readiness_core.py", "core_sha256", "0055e653404a0cfc98748491dc05349f8892986cb17efdd32cf7fb1be452551c"),
        ("generator_ref", "scripts/prepare_optical_input_readiness_contract.py", "generator_sha256", "c9974e80364d867bed5735be8cbda58931d92e33fb688e29c64cae58f741deb2"),
        ("runner_ref", "scripts/inspect_optical_inputs_arcgis.py", "runner_sha256", "5bc717da9095db3390ead46f5c066ffbde9f25e896dd2581db624f4b4f632db0"),
        ("arcgis_adapter_ref", "scripts/validate_optical_input_readiness_arcgis.py", "arcgis_adapter_sha256", "7a10c2ae11fcdff14be4229dd4a0bff78b3dcc99352aced72f3a06e305b6831f"),
        ("test_ref", "tests/test_optical_input_readiness.py", "test_sha256", "9b6182cc536df0feda762fbe83b0c8e87e056157d2e37b10d6823be556e3fa06"),
        ("protocol_ref", "docs/OPTICAL_INPUT_READINESS_PROTOCOL.md", "protocol_sha256", "35f77b2f2693ff2b1cf3211ca2546cd7a1479b99f7646601c88b1b4cbb235679"),
    )
    for ref_key, expected_ref, hash_key, expected_hash in historical_input_bindings:
        if historical_input_evidence.get(ref_key) != expected_ref or historical_input_evidence.get(hash_key) != expected_hash:
            fail(f"EVID-0026 no longer preserves its published {ref_key}")
    if historical_input_evidence.get("status") != "pass_synthetic_arcgis_real_input_deferred" or historical_input_evidence.get("current_disposition", {}).get("status") != "defer":
        fail("EVID-0026 must preserve its synthetic-only deferred state")
    corrected_input_evidence = ledger_by_id.get("EVID-0027")
    if not isinstance(corrected_input_evidence, dict):
        fail("evidence ledger is missing EVID-0027 corrected optical input-readiness evidence")
    for ref_key, hash_key in (
        ("readiness_receipt_ref", "readiness_receipt_sha256"),
        ("arcgis_receipt_ref", "arcgis_receipt_sha256"),
        ("contract_ref", "contract_sha256"),
        ("core_ref", "core_sha256"),
        ("generator_ref", "generator_sha256"),
        ("runner_ref", "runner_sha256"),
        ("arcgis_adapter_ref", "arcgis_adapter_sha256"),
        ("test_ref", "test_sha256"),
        ("protocol_ref", "protocol_sha256"),
    ):
        relative = corrected_input_evidence.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file() or corrected_input_evidence.get(hash_key) != sha256(relative):
            fail(f"EVID-0027 does not bind {ref_key}")
    if corrected_input_evidence.get("status") != "pass_corrected_synthetic_arcgis_real_input_deferred" or corrected_input_evidence.get("current_disposition", {}).get("status") != "defer":
        fail("EVID-0027 must preserve its corrected synthetic-only deferred state")
    if corrected_input_evidence.get("supersedes") != optical_input_readiness.get("supersedes"):
        fail("EVID-0027 and the current control receipt identify different superseded evidence")
    if corrected_input_evidence.get("source_references") != expected_input_source_references:
        fail("EVID-0027 does not preserve the official correction sources")
    evidence_input_assertions = corrected_input_evidence.get("assertions", {})
    readiness_input_assertions = optical_input_readiness.get("assertions", {})
    if evidence_input_assertions != readiness_input_assertions:
        fail("EVID-0027 and optical input-readiness receipt have different claim boundaries")
    acquisition_progress_evidence = ledger_by_id.get("EVID-0028")
    if not isinstance(acquisition_progress_evidence, dict):
        fail("evidence ledger is missing EVID-0028 acquisition-progress readiness evidence")
    expected_evid_0028_bindings = {
        "readiness_receipt_ref": "records/acquisition/acquisition-progress-readiness.json",
        "readiness_receipt_sha256": "a9ea7828c7cf48c28bbe7a3370334134eeadb7d0ab891c74d0fbb49deafe0708",
        "initial_snapshot_ref": "records/acquisition/active-intake-initial-snapshot.json",
        "initial_snapshot_sha256": "a2816e9244a0141bf797c3a3fba00e2d492e272fb4886e7ff9aff58ab3cb716c",
        "validator_ref": "scripts/validate_m2_acquisition_progress.py",
        "validator_sha256": "fc90a85e111135133a64249151086d7032c924148bcf5cc29cbee473703a9051",
        "test_ref": "tests/test_m2_acquisition_progress.py",
        "test_sha256": "5d1c59520d803daa05ba1bfef1ddcfbdbe894566a9cfb0c50f3c7dba00e2f191",
        "project_checker_ref": "scripts/check_project.py",
        "project_checker_sha256": "0811375064b8d2681690012d82234270f00022e23e94c82649c43f28ec5b7395",
        "runbook_ref": "docs/M2_EXECUTION_RUNBOOK.md",
        "runbook_sha256": "abd658d18a80f86bb3d8c4446eac9dfde7e268ffee44ee0841421838292d66ed",
    }
    for key, expected in expected_evid_0028_bindings.items():
        if acquisition_progress_evidence.get(key) != expected:
            fail(f"EVID-0028 no longer preserves published {key}")
    if acquisition_progress_evidence.get("status") != "pass_preacquisition_dynamic_progress_validation":
        fail("EVID-0028 status differs")
    if acquisition_progress_evidence.get("assertions") != acquisition_progress_readiness.get("assertions"):
        fail("EVID-0028 and acquisition-progress readiness have different claim boundaries")
    acquisition_checkpoint_evidence = ledger_by_id.get("EVID-0029")
    if not isinstance(acquisition_checkpoint_evidence, dict):
        fail("evidence ledger is missing EVID-0029 acquisition-checkpoint readiness evidence")
    expected_evid_0029_bindings = {
        "readiness_receipt_ref": "records/acquisition/acquisition-checkpoint-readiness.json",
        "readiness_receipt_sha256": "1a4439702be6ad448ec9eafc095d4bd25b692100b73dd19429fb20a1fde7eca9",
        "derivation_ref": "scripts/derive_m2_acquisition_checkpoint.py",
        "derivation_sha256": "4d78913210978495b320dd70ace7d9e0ef3b7e9f7bf4f2804fbe444691b728a8",
        "test_ref": "tests/test_m2_checkpoint_reconciliation.py",
        "test_sha256": "41288357950546dc5d047dc24b8a699cb8ad4afe31c6adfa6ac28e55b0065798",
        "project_checker_ref": "scripts/check_project.py",
        "project_checker_sha256": "907bc0c3591e1f3c1e1e32c3651d3919c3f8ecfc83ac7f72f4ead92ca4d9498d",
        "runbook_ref": "docs/M2_EXECUTION_RUNBOOK.md",
        "runbook_sha256": "8b1aa06c0e4da9d56a9634c09822a8116aa23ed4db5c6c6aad66c9fb619201f3",
    }
    for key, expected in expected_evid_0029_bindings.items():
        if acquisition_checkpoint_evidence.get(key) != expected:
            fail(f"EVID-0029 no longer preserves published {key}")
    if acquisition_checkpoint_evidence.get("status") != "pass_preacquisition_checkpoint_derivation":
        fail("EVID-0029 status differs")
    if acquisition_checkpoint_evidence.get("assertions") != acquisition_checkpoint_readiness.get("assertions"):
        fail("EVID-0029 and acquisition-checkpoint readiness have different claim boundaries")
    acquisition_checkpoint_portability_evidence = ledger_by_id.get("EVID-0030")
    if not isinstance(acquisition_checkpoint_portability_evidence, dict):
        fail("evidence ledger is missing EVID-0030 acquisition-checkpoint portability correction")
    expected_evid_0030_bindings = {
        "correction_receipt_ref": "records/acquisition/acquisition-checkpoint-portability-correction.json",
        "correction_receipt_sha256": "f69c8b9944a048bb8645f8852281319ac8fa87e3aecce3fe39cc332f63caa352",
        "derivation_ref": "scripts/derive_m2_acquisition_checkpoint.py",
        "derivation_sha256": "4d78913210978495b320dd70ace7d9e0ef3b7e9f7bf4f2804fbe444691b728a8",
        "test_ref": "tests/test_m2_checkpoint_reconciliation.py",
        "test_sha256": "53e7e5d98b6e11a1ad3c4f3b9b6523e766bf74765d98f7a35b8e7ffeed2662a3",
        "project_checker_ref": "scripts/check_project.py",
        "project_checker_sha256": "0ea6c6cc5bcc32db19105dfd2cc2ca27bdf96e38f361f3c0a131b64ef64f6801",
    }
    for key, expected in expected_evid_0030_bindings.items():
        if acquisition_checkpoint_portability_evidence.get(key) != expected:
            fail(f"EVID-0030 no longer preserves published {key}")
    if acquisition_checkpoint_portability_evidence.get("status") != "pass_portable_repository_test_external_verification_separated":
        fail("EVID-0030 status differs")
    if acquisition_checkpoint_portability_evidence.get("assertions") != acquisition_checkpoint_portability.get("assertions"):
        fail("EVID-0030 and acquisition-checkpoint portability correction have different claim boundaries")
    dem_activation_evidence = ledger_by_id.get("EVID-0031")
    if not isinstance(dem_activation_evidence, dict):
        fail("evidence ledger is missing EVID-0031 DEM amendment activation evidence")
    expected_evid_0031_bindings = {
        "activation_receipt_ref": "records/acquisition/dem-amendment-activation.json",
        "activation_receipt_sha256": "76e4233efd4dfd2d75a6873504646558eb4a16cd1f069060f91f0194c40c63d9",
        "approval_ref": "records/source-gates/m2-dem-amendment-approval.json",
        "approval_sha256": "6d1fc7e05854bc149ace177d89e84a7651cc049efd530cab650a9464222769d0",
        "active_intake_ref": "contracts/m2-dem-intake.json",
        "active_intake_sha256": "0fa00a4be01d3caddac28088d2d3d714040d1258b33497ebee50cbb0b8b3b5b6",
        "active_verification_ref": "contracts/m2-dem-offline-verification.json",
        "active_verification_sha256": "755bdb1fd1916d68289f5266912f8bb7f25462b512ce7cfc27a49feb44bcef42",
        "reconciliation_ref": "records/source-gates/m2-dem-amendment-review-reconciliation.json",
        "reconciliation_sha256": "9d72c9786440da0c9149340cd69361b12e55f0d7dff88972bfd02ee0da5460e1",
        "activation_script_ref": "scripts/activate_m2_dem_amendment.py",
        "activation_script_sha256": "a4cc4f86b0beb81f151ccdc0bc4a4ab5d674823d7c7a5879f0e223efcd36d256",
    }
    if any(dem_activation_evidence.get(key) != expected for key, expected in expected_evid_0031_bindings.items()):
        fail("EVID-0031 no longer preserves its published activation bindings")
    if dem_activation_evidence.get("status") != "pass_exact_dem_amendment_activated_preflight_pending":
        fail("EVID-0031 status differs")
    if dem_activation_evidence.get("assertions") != dem_activation_receipt.get("assertions"):
        fail("EVID-0031 and DEM amendment activation receipt have different claim boundaries")
    dem_preflight_evidence = ledger_by_id.get("EVID-0032")
    if not isinstance(dem_preflight_evidence, dict):
        fail("evidence ledger is missing EVID-0032 DEM preflight evidence")
    for ref_key, hash_key in (
        ("source_gate_ref", "source_gate_sha256"),
        ("preflight_ref", "preflight_sha256"),
        ("custody_initialization_ref", "custody_initialization_sha256"),
        ("active_intake_ref", "active_intake_sha256"),
        ("active_verification_ref", "active_verification_sha256"),
        ("completion_script_ref", "completion_script_sha256"),
        ("preflight_script_ref", "preflight_script_sha256"),
    ):
        relative = dem_preflight_evidence.get(ref_key)
        if not isinstance(relative, str) or not (ROOT / relative).is_file() or dem_preflight_evidence.get(hash_key) != sha256(relative):
            fail(f"EVID-0032 does not bind {ref_key}")
    if dem_preflight_evidence.get("status") != "pass_exact_source_and_path_controls_no_payload":
        fail("EVID-0032 status differs")
    preflight_assertions = dem_preflight_evidence.get("assertions", {})
    if preflight_assertions != {
        "exact_license_match": True,
        "exact_tile_count": 4,
        "remote_identity_unchanged": True,
        "source_gate_ready": True,
        "external_paths_initialized_empty": True,
        "dem_payload_bytes_requested": False,
        "dem_payload_bytes_present": 0,
        "authentication_performed": False,
        "scientific_result_established": False,
    }:
        fail("EVID-0032 claim boundary differs")

    violations = []
    for relative in tracked_files():
        path = Path(relative)
        lower = relative.lower()
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            violations.append(relative)
        if any(part in lower for part in FORBIDDEN_NAME_PARTS):
            violations.append(relative)
        if ".safe/" in lower or ".gdb/" in lower:
            violations.append(relative)
    if violations:
        fail("forbidden tracked artifacts: " + ", ".join(sorted(set(violations))))

    print(f"PASS: {len(REQUIRED)} required files, JSON controls, and Git artifact boundaries validated.")


if __name__ == "__main__":
    main()
