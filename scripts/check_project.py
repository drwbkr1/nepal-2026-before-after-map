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
    "docs/VALIDATION.md",
    "docs/STATUS.md",
    "docs/DECISIONS.md",
    "contracts/milestone-001.json",
    "records/project-control-profile.json",
    "records/long-term-goal.json",
    "records/evidence-ledger.jsonl",
    "config/aoi/approved-study-areas.geojson",
    "config/aoi/approved-study-areas-epsg32645.json",
    "records/source-gates/aoi-approval.json",
    "records/source-gates/aoi-review-reconciliation.json",
    "records/surface-receipts/m1-approved-aoi-arcgis-validation.json",
    "records/source-manifest.json",
    "docs/M1_SOURCE_MANIFEST_REVIEW.md",
    "docs/assets/m1-source-manifest-review.png",
    "records/surface-receipts/m1-source-manifest-review.json",
    "records/surface-receipts/m1-control-reproducibility.json",
    "reviews/m1-manifest/review-bundle.json",
    "reviews/m1-manifest/review-contract.json",
    "reviews/m1-manifest/blank-response.json",
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
    if contract["status"] != "active":
        fail("M1 must be active after goal activation")
    if contract["authority"]["mode"] != "inherited":
        fail("active M1 must inherit the exact user authority")
    if profile["authority"]["authority_ref"] != contract["authority"]["authority_ref"]:
        fail("profile and milestone authority references must agree")
    prohibited = set(contract["scope"]["forbidden_work"])
    if "download full satellite products" not in prohibited:
        fail("full satellite-product acquisition must remain prohibited in M1")

    approval = json.loads((ROOT / "records/source-gates/aoi-approval.json").read_text(encoding="utf-8"))
    projected_aoi = json.loads((ROOT / "config/aoi/approved-study-areas-epsg32645.json").read_text(encoding="utf-8"))
    arcgis_receipt = json.loads((ROOT / "records/surface-receipts/m1-approved-aoi-arcgis-validation.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "records/source-manifest.json").read_text(encoding="utf-8"))
    manifest_bundle = json.loads((ROOT / "reviews/m1-manifest/review-bundle.json").read_text(encoding="utf-8"))
    manifest_contract = json.loads((ROOT / "reviews/m1-manifest/review-contract.json").read_text(encoding="utf-8"))
    manifest_response = json.loads((ROOT / "reviews/m1-manifest/blank-response.json").read_text(encoding="utf-8"))
    reproducibility = json.loads((ROOT / "records/surface-receipts/m1-control-reproducibility.json").read_text(encoding="utf-8"))
    aoi_reconciliation = json.loads((ROOT / "records/source-gates/aoi-review-reconciliation.json").read_text(encoding="utf-8"))
    units = {unit["id"]: unit for unit in contract["units"]}
    validate_review_bundle("reviews/m1-aoi/review-bundle.json", "reviews/m1-aoi/review-contract.json")
    validate_review_bundle("reviews/m1-manifest/review-bundle.json", "reviews/m1-manifest/review-contract.json")
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
        fail("candidate source records must remain unapproved before the manifest gate")
    bundle_digest = sha256("reviews/m1-manifest/review-bundle.json")
    if manifest_bundle["candidate_identity"] != f"SOURCE-MANIFEST-SHA256:{sha256('records/source-manifest.json')}":
        fail("review bundle does not bind the exact source manifest")
    if manifest_contract["review_bundle"]["manifest_sha256"] != bundle_digest:
        fail("review contract does not bind the exact review bundle")
    if manifest_response["completed"] is not False or manifest_response["reviewer"]["attestation"] is not False:
        fail("manifest response must remain blank before owner review")
    if units["M1-AOI"]["status"] != "complete" or units["M1-MANIFEST"]["status"] != "ready":
        fail("M1 control units do not reflect the approved AOI and ready manifest gate")
    if reproducibility["status"] != "pass_with_retained_failures":
        fail("M1 reproducibility receipt is not in a passing state")
    for check in reproducibility["checks"]:
        if check["status"] != "pass" or check["sha256"] != sha256(check["artifact"]):
            fail(f"reproducibility receipt does not bind {check['artifact']}")

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
