#!/usr/bin/env python3
"""Validate the lightweight public project repository."""

from __future__ import annotations

import json
import hashlib
import subprocess
import sys
from pathlib import Path

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
    "docs/VALIDATION.md",
    "docs/STATUS.md",
    "docs/DECISIONS.md",
    "contracts/milestone-001.json",
    "contracts/milestone-002-proposal.json",
    "contracts/m2-intake-candidate.json",
    "contracts/milestone-002.json",
    "contracts/m2-intake.json",
    "contracts/m2-offline-verification.json",
    "contracts/milestone-002-dem-amendment-proposal.json",
    "contracts/m2-dem-intake-candidate.json",
    "contracts/m2-dem-offline-verification-candidate.json",
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
    "records/acquisition/transfer-runner-readiness.json",
    "records/source-gates/source-manifest-approval.json",
    "records/source-gates/source-manifest-review-reconciliation.json",
    "records/source-gates/m2-activation-approval.json",
    "records/source-gates/m2-activation-review-reconciliation.json",
    "records/source-gates/m2-live-source-gate.json",
    "records/source-gates/m2-dem-metadata-receipt.json",
    "records/source-gates/m2-dem-candidate-manifest.json",
    "records/source-gates/m2-dem-source-gate.json",
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
    "docs/assets/arcgis-evidence-workspace-preview.png",
    "records/surface-receipts/m2-activation-review.json",
    "records/surface-receipts/arcgis-sar-processing-capability.json",
    "records/surface-receipts/m2-dem-amendment-review.json",
    "records/surface-receipts/m2-dem-radar-control-readiness.json",
    "records/surface-receipts/optical-processing-synthetic-arcgis.json",
    "records/surface-receipts/optical-baseline-control-readiness.json",
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
    "scripts/validate_pair_plan.py",
    "tests/test_m2_transfer_core.py",
    "tests/test_m2_active_verification.py",
    "tests/test_m2_dem_amendment.py",
    "tests/test_m2_dem_controls.py",
    "tests/test_radar_processing_contract.py",
    "tests/test_optical_processing_core.py",
    "scripts/activate_m2_verification.py",
    "scripts/verify_m2_product_container.py",
    "scripts/inspect_arcgis_sar_capability.py",
    "scripts/prepare_m2_dem_amendment.py",
    "scripts/prepare_m2_dem_controls.py",
    "scripts/verify_m2_dem_geotiff.py",
    "scripts/prepare_radar_processing_contract.py",
    "scripts/optical_processing_core.py",
    "scripts/prepare_optical_processing_contract.py",
    "scripts/validate_optical_processing_arcgis.py",
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
    sar_capability = json.loads((ROOT / "records/surface-receipts/arcgis-sar-processing-capability.json").read_text(encoding="utf-8"))
    dem_intake_candidate = json.loads((ROOT / "contracts/m2-dem-intake-candidate.json").read_text(encoding="utf-8"))
    dem_verification_candidate = json.loads((ROOT / "contracts/m2-dem-offline-verification-candidate.json").read_text(encoding="utf-8"))
    radar_processing_contract = json.loads((ROOT / "config/qa/radar-baseline-processing-contract.json").read_text(encoding="utf-8"))
    dem_radar_readiness = json.loads((ROOT / "records/surface-receipts/m2-dem-radar-control-readiness.json").read_text(encoding="utf-8"))
    optical_processing_contract = json.loads((ROOT / "config/qa/optical-baseline-processing-contract.json").read_text(encoding="utf-8"))
    optical_arcgis_receipt = json.loads((ROOT / "records/surface-receipts/optical-processing-synthetic-arcgis.json").read_text(encoding="utf-8"))
    optical_readiness = json.loads((ROOT / "records/surface-receipts/optical-baseline-control-readiness.json").read_text(encoding="utf-8"))
    goal = json.loads((ROOT / "records/long-term-goal.json").read_text(encoding="utf-8"))

    expected_remote = profile["project"]["repository_identity"]["expected_remote"]
    remote_project_name = expected_remote.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
    if profile["project"]["name"] != remote_project_name:
        fail("project name does not match canonical repository identity")
    if profile["project"]["repository_identity"]["default_branch"] != "main":
        fail("expected default branch must be main")
    if profile.get("control_surfaces", {}).get("proposed_amendments") != [
        "contracts/milestone-002-dem-amendment-proposal.json"
    ]:
        fail("project profile must expose the exact pending M2 DEM amendment")
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
    if profile["current_checkpoint"]["checkpoint_id"] != "M2-AUTHENTICATION-REFERENCE" or goal.get("current_checkpoint") != "M2-AUTHENTICATION-REFERENCE":
        fail("profile and goal must stop at the owner-controlled authentication-reference boundary")

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
    intake_dry_run = json.loads((ROOT / "records/acquisition/m2-intake-static-dry-run.json").read_text(encoding="utf-8"))
    m2_activation = json.loads((ROOT / "records/source-gates/m2-activation-approval.json").read_text(encoding="utf-8"))
    m2_reconciliation = json.loads((ROOT / "records/source-gates/m2-activation-review-reconciliation.json").read_text(encoding="utf-8"))
    m2_source_gate = json.loads((ROOT / "records/source-gates/m2-live-source-gate.json").read_text(encoding="utf-8"))
    m2_preflight = json.loads((ROOT / "records/acquisition/preflight.json").read_text(encoding="utf-8"))
    custody_receipt = json.loads((ROOT / "records/acquisition/custody-initialization.json").read_text(encoding="utf-8"))
    transfer_readiness = json.loads((ROOT / "records/acquisition/transfer-runner-readiness.json").read_text(encoding="utf-8"))
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
        if optical_readiness_bindings.get(hash_key) != sha256(relative):
            fail(f"optical readiness receipt does not bind {ref_key}")
    if optical_readiness.get("validation", {}).get("portable_test_count") != 15 or optical_readiness.get("validation", {}).get("full_repository_test_count") != 97:
        fail("optical readiness receipt test counts differ")
    if optical_readiness.get("current_route_disposition", {}).get("status") != "defer":
        fail("optical real-data route must remain deferred")
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
    if m2_units.get("M2-CUSTODY-PREFLIGHT", {}).get("disposition") != "pass" or m2_units.get("M2-ACQUIRE", {}).get("status") != "ready":
        fail("M2 units do not preserve the passing preflight and ready acquisition checkpoint")
    if m2_units["M2-ACQUIRE"].get("gates", {}).get("custody_initialization") != "pass":
        fail("M2 acquisition unit does not bind verified custody initialization")
    if m2_units["M2-ACQUIRE"].get("gates", {}).get("authentication") != "waiting_for_secret_safe_existing_owner_credential_reference":
        fail("M2 acquisition unit must stop at the secret-safe authentication-reference boundary")

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
    if len(active_intake.get("assets", [])) != 8 or any(asset.get("state") != "authorized" or asset.get("attempts") != [] for asset in active_intake["assets"]):
        fail("active M2 intake must contain eight authorized, unattempted assets at this checkpoint")
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
        "active_contract_sha256": sha256("contracts/milestone-002.json"),
        "active_intake_sha256": sha256("contracts/m2-intake.json"),
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
        "active_milestone_sha256_at_activation": sha256("contracts/milestone-002.json"),
        "activation_approval_sha256": sha256("records/source-gates/m2-activation-approval.json"),
        "active_intake_sha256_at_activation": sha256("contracts/m2-intake.json"),
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
