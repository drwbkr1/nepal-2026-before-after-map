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
    "docs/assets/m2-controlled-acquisition-review.png",
    "scripts/render_m2_activation_review.py",
    "scripts/prepare_m2_intake.py",
    "scripts/build_arcgis_evidence_workspace.py",
    "scripts/validate_arcgis_evidence_workspace.py",
    "config/arcgis/evidence-workspace-schema.json",
    "docs/assets/arcgis-evidence-workspace-preview.png",
    "records/surface-receipts/m2-activation-review.json",
    "reviews/m2-activation/review-bundle.json",
    "reviews/m2-activation/review-contract.json",
    "reviews/m2-activation/blank-response.json",
    "tests/test_m2_intake.py",
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

    for number, line in enumerate(
        (ROOT / "records/evidence-ledger.jsonl").read_text(encoding="utf-8").splitlines(), 1
    ):
        if line.strip():
            try:
                json.loads(line)
            except json.JSONDecodeError as exc:
                fail(f"invalid evidence ledger JSON on line {number}: {exc}")

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
