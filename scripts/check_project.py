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
    "docs/VALIDATION.md",
    "docs/STATUS.md",
    "docs/DECISIONS.md",
    "contracts/milestone-001.json",
    "contracts/milestone-002-proposal.json",
    "contracts/m2-intake-candidate.json",
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
    "records/source-gates/source-manifest-approval.json",
    "records/source-gates/source-manifest-review-reconciliation.json",
    "docs/M1_SOURCE_MANIFEST_REVIEW.md",
    "docs/assets/m1-source-manifest-review.png",
    "records/surface-receipts/m1-source-manifest-review.json",
    "records/surface-receipts/m1-control-reproducibility.json",
    "records/surface-receipts/arcgis-evidence-workspace.json",
    "reviews/m1-manifest/review-bundle.json",
    "reviews/m1-manifest/review-contract.json",
    "reviews/m1-manifest/blank-response.json",
    "docs/M2_CONTROLLED_ACQUISITION_REVIEW.md",
    "docs/M2_EXECUTION_RUNBOOK.md",
    "docs/M2_OFFLINE_VERIFICATION.md",
    "docs/assets/m2-controlled-acquisition-review.png",
    "scripts/render_m2_activation_review.py",
    "scripts/prepare_m2_intake.py",
    "scripts/prepare_m2_verification.py",
    "scripts/build_arcgis_evidence_workspace.py",
    "scripts/validate_arcgis_evidence_workspace.py",
    "config/arcgis/evidence-workspace-schema.json",
    "docs/assets/arcgis-evidence-workspace-preview.png",
    "records/surface-receipts/m2-activation-review.json",
    "contracts/m2-offline-verification-candidate.json",
    "records/readiness/m2-readiness-audit-input.json",
    "records/readiness/m2-readiness-decision.json",
    "reviews/m2-activation/review-bundle.json",
    "reviews/m2-activation/review-contract.json",
    "reviews/m2-activation/blank-response.json",
    "tests/test_m2_intake.py",
    "tests/test_m2_verification.py",
    "tests/test_arcgis_evidence_schema.py",
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
    goal = json.loads((ROOT / "records/long-term-goal.json").read_text(encoding="utf-8"))

    expected_remote = profile["project"]["repository_identity"]["expected_remote"]
    remote_project_name = expected_remote.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
    if profile["project"]["name"] != remote_project_name:
        fail("project name does not match canonical repository identity")
    if profile["project"]["repository_identity"]["default_branch"] != "main":
        fail("expected default branch must be main")
    if not (ROOT / "AGENTS.md").read_text(encoding="utf-8").strip():
        fail("AGENTS.md must contain controlling project instructions")
    if goal["status"] != "active":
        fail("long-term goal record must be active")
    if contract["project_profile_ref"] != "records/project-control-profile.json":
        fail("milestone must reference the project control profile")
    if contract["status"] != "complete":
        fail("M1 must be complete after exact source-manifest approval")
    if contract["authority"]["mode"] != "inherited":
        fail("completed M1 must preserve the exact user authority")
    if profile["authority"]["authority_ref"] != contract["authority"]["authority_ref"]:
        fail("profile and milestone authority references must agree")
    prohibited = set(contract["scope"]["forbidden_work"])
    if "download full satellite products" not in prohibited:
        fail("full satellite-product acquisition must remain prohibited in M1")
    if profile["control_surfaces"].get("active_contract") is not None:
        fail("no acquisition contract may be active at the M2 owner gate")
    if profile["control_surfaces"].get("last_completed_contract") != "contracts/milestone-001.json":
        fail("project profile must identify M1 as the last completed contract")
    if profile["control_surfaces"].get("proposed_contract") != "contracts/milestone-002-proposal.json":
        fail("project profile must identify the exact M2 proposal")
    if goal.get("active_milestone") is not None or goal.get("proposed_milestone") != "contracts/milestone-002-proposal.json":
        fail("long-term goal must show no active milestone and the proposed M2 contract")

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
    intake_dry_run = json.loads((ROOT / "records/acquisition/m2-intake-static-dry-run.json").read_text(encoding="utf-8"))
    offline_verification = json.loads((ROOT / "contracts/m2-offline-verification-candidate.json").read_text(encoding="utf-8"))
    readiness_input = json.loads((ROOT / "records/readiness/m2-readiness-audit-input.json").read_text(encoding="utf-8"))
    readiness_decision = json.loads((ROOT / "records/readiness/m2-readiness-decision.json").read_text(encoding="utf-8"))
    reproducibility = json.loads((ROOT / "records/surface-receipts/m1-control-reproducibility.json").read_text(encoding="utf-8"))
    evidence_schema = json.loads((ROOT / "config/arcgis/evidence-workspace-schema.json").read_text(encoding="utf-8"))
    evidence_workspace = json.loads((ROOT / "records/surface-receipts/arcgis-evidence-workspace.json").read_text(encoding="utf-8"))
    aoi_reconciliation = json.loads((ROOT / "records/source-gates/aoi-review-reconciliation.json").read_text(encoding="utf-8"))
    units = {unit["id"]: unit for unit in contract["units"]}
    validate_review_bundle("reviews/m1-aoi/review-bundle.json", "reviews/m1-aoi/review-contract.json")
    validate_review_bundle("reviews/m1-manifest/review-bundle.json", "reviews/m1-manifest/review-contract.json")
    validate_review_bundle("reviews/m2-activation/review-bundle.json", "reviews/m2-activation/review-contract.json")
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
        fail("M2 public response must remain blank before owner activation")
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
