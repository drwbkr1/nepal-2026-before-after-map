#!/usr/bin/env python3
"""Run the live, non-mutating M2 source and custody preflight."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import urllib.request
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
APPROVAL_REF = "records/source-gates/m2-activation-approval.json"
ACTIVE_CONTRACT_REF = "contracts/milestone-002.json"
PLAN_REF = "records/acquisition-plan.json"
CANDIDATE_INTAKE_REF = "contracts/m2-intake-candidate.json"
SOURCE_GATE_REF = "records/source-gates/m2-live-source-gate.json"
PREFLIGHT_REF = "records/acquisition/preflight.json"
ACTIVE_INTAKE_REF = "contracts/m2-intake.json"

OFFICIAL_PAGES = [
    {
        "id": "odata-download-documentation",
        "url": "https://documentation.dataspace.copernicus.eu/APIs/OData.html",
        "required_phrase": "download.dataspace.copernicus.eu/odata/v1/Products(",
    },
    {
        "id": "token-documentation",
        "url": "https://documentation.dataspace.copernicus.eu/APIs/Token.html",
        "required_phrase": "access token",
    },
    {
        "id": "terms-and-conditions",
        "url": "https://dataspace.copernicus.eu/terms-and-conditions",
        "required_phrase": "free, full and open basis",
    },
    {
        "id": "sentinel-data-legal-notice",
        "url": "https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice",
        "required_magic": "%PDF",
    },
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def serialized(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2) + "\n").encode("utf-8")


def create_new(relative: str, value: dict[str, Any]) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(serialized(value))
        handle.flush()


def fetch(url: str) -> tuple[bytes, dict[str, Any]]:
    request = urllib.request.Request(url, headers={"User-Agent": "nepal-2026-evidence-preflight/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read()
        metadata = {
            "status_code": int(response.status),
            "resolved_url": response.geturl(),
            "content_type": response.headers.get("Content-Type"),
            "content_length_bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            "etag": response.headers.get("ETag"),
            "last_modified": response.headers.get("Last-Modified"),
        }
    return body, metadata


def live_evidence(locator: str, observed_at: str, note: str) -> dict[str, Any]:
    return {"type": "live", "locator": locator, "observed_at": observed_at, "note": note}


def static_evidence(locator: str, note: str) -> dict[str, Any]:
    return {"type": "static", "locator": locator, "note": note}


def is_reparse_point(path: Path) -> bool:
    attributes = getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def checksum_map(values: list[dict[str, Any]]) -> dict[str, str]:
    return {str(item["Algorithm"]).upper(): str(item["Value"]).lower() for item in values}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assessed-at-utc", required=True)
    args = parser.parse_args()

    for relative in (SOURCE_GATE_REF, PREFLIGHT_REF, ACTIVE_INTAKE_REF):
        if (ROOT / relative).exists():
            raise SystemExit(f"preflight output already exists; refusing replacement: {relative}")

    approval = load(APPROVAL_REF)
    active_contract = load(ACTIVE_CONTRACT_REF)
    plan = load(PLAN_REF)
    candidate_intake = load(CANDIDATE_INTAKE_REF)
    if approval.get("status") != "approved" or approval.get("acquisition_plan_sha256") != sha256(ROOT / PLAN_REF):
        raise SystemExit("M2 activation approval is missing or does not bind the plan")
    if active_contract.get("status") != "active" or active_contract.get("authority", {}).get("authority_ref") != APPROVAL_REF:
        raise SystemExit("M2 active contract or authority reference differs")
    if candidate_intake.get("extensions", {}).get("source_plan_sha256") != sha256(ROOT / PLAN_REF):
        raise SystemExit("candidate intake contract does not bind the approved plan")

    page_checks: list[dict[str, Any]] = []
    for definition in OFFICIAL_PAGES:
        body, metadata = fetch(definition["url"])
        text = body.decode("utf-8", errors="ignore")
        phrase_pass = (
            text.startswith(definition["required_magic"])
            if "required_magic" in definition
            else definition["required_phrase"].casefold() in text.casefold()
        )
        metadata.update({"page_id": definition["id"], "url": definition["url"], "required_content_check": phrase_pass})
        page_checks.append(metadata)
    if any(item["status_code"] != 200 or not item["required_content_check"] for item in page_checks):
        raise SystemExit("one or more official provider pages failed live content checks")

    product_checks: list[dict[str, Any]] = []
    for record in plan["records"]:
        provider_id = record["provider_product_id"]
        catalog_url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products({provider_id})?%24expand=Attributes"
        body, response_metadata = fetch(catalog_url)
        product = json.loads(body.decode("utf-8"))
        actual_checksums = checksum_map(product.get("Checksum", []))
        expected_checksums = checksum_map(record["provider_checksums"])
        checks = {
            "provider_id_match": product.get("Id") == provider_id,
            "product_name_match": product.get("Name") == record["exact_product_id"],
            "content_length_match": product.get("ContentLength") == record["catalog_content_length_bytes"],
            "provider_checksums_match": actual_checksums == expected_checksums,
            "online": product.get("Online") is True,
        }
        product_checks.append({
            "source_id": record["source_id"],
            "provider_product_id": provider_id,
            "exact_product_id": record["exact_product_id"],
            "catalog_url": catalog_url,
            "observed_at_utc": args.assessed_at_utc,
            "catalog_response_sha256": response_metadata["sha256"],
            "publication_date": product.get("PublicationDate"),
            "modification_date": product.get("ModificationDate"),
            "content_length_bytes": product.get("ContentLength"),
            "checks": checks,
            "status": "pass" if all(checks.values()) else "fail",
        })
    if any(item["status"] != "pass" for item in product_checks):
        raise SystemExit("one or more exact products failed live catalog identity or availability checks")

    project_root = ROOT.parent.resolve()
    expected_data_root = (project_root / "nepal-2026-before-after-map-data").resolve(strict=False)
    planned_data_root = Path(plan["custody"]["planned_external_root"]).resolve(strict=False)
    custody_root = (project_root / candidate_intake["custody_root"]).resolve(strict=False)
    staging_root = (project_root / candidate_intake["staging_root"]).resolve(strict=False)
    if expected_data_root != planned_data_root:
        raise SystemExit("planned external root differs across reviewed controls")
    try:
        custody_root.relative_to(expected_data_root)
        staging_root.relative_to(expected_data_root)
    except ValueError:
        raise SystemExit("reviewed custody or staging root resolves outside the approved external root")
    if custody_root == expected_data_root or staging_root == expected_data_root:
        raise SystemExit("reviewed custody or staging root must be a child of the approved external root")
    try:
        expected_data_root.relative_to(ROOT.resolve())
        raise SystemExit("external data root resolves inside the Git repository")
    except ValueError:
        pass

    existing_ancestors: list[dict[str, Any]] = []
    current = expected_data_root.parent
    while True:
        existing_ancestors.append({"path": str(current), "exists": current.exists(), "is_reparse_point": is_reparse_point(current) if current.exists() else None})
        if current == current.parent:
            break
        current = current.parent
    if any(item["is_reparse_point"] for item in existing_ancestors):
        raise SystemExit("external custody path has a reparse-point ancestor")

    resolved_paths: list[str] = []
    existing_destinations: list[str] = []
    for asset in candidate_intake["assets"]:
        destination = (custody_root / asset["destination_relative_path"]).resolve(strict=False)
        staging = (staging_root / asset["staging_relative_path"]).resolve(strict=False)
        destination.relative_to(custody_root)
        staging.relative_to(staging_root)
        resolved_paths.extend([str(destination), str(staging)])
        if destination.exists() or staging.exists():
            existing_destinations.append(str(destination if destination.exists() else staging))
    casefold_paths = [os.path.normcase(path) for path in resolved_paths]
    path_collisions = len(casefold_paths) != len(set(casefold_paths))
    free_bytes = shutil.disk_usage(project_root).free
    free_gib = round(free_bytes / (1024 ** 3), 3)
    minimum_gib = float(plan["custody"]["minimum_free_space_gib_before_start"])
    path_checks = {
        "project_root": str(project_root),
        "repository_root": str(ROOT.resolve()),
        "planned_external_data_root": str(expected_data_root),
        "custody_root": str(custody_root),
        "staging_root": str(staging_root),
        "external_data_root_exists_before_preflight": expected_data_root.exists(),
        "external_data_root_outside_git": True,
        "existing_ancestors": existing_ancestors,
        "existing_destination_or_staging_paths": existing_destinations,
        "case_insensitive_path_collision": path_collisions,
        "resolved_asset_path_count": len(resolved_paths),
    }
    if expected_data_root.exists() or existing_destinations or path_collisions or free_gib < minimum_gib:
        raise SystemExit("fresh custody path or storage preflight failed")

    approved_actions = [
        "create approved external custody root",
        "authenticate with an owner-controlled existing CDSE account or session",
        "download the eight exact approved products",
        "verify transferred bytes and product containers",
        "inspect product pixels for baseline fitness",
    ]
    source_entries: list[dict[str, Any]] = []
    terms_check = next(item for item in page_checks if item["page_id"] == "terms-and-conditions")
    download_check = next(item for item in page_checks if item["page_id"] == "odata-download-documentation")
    token_check = next(item for item in page_checks if item["page_id"] == "token-documentation")
    legal_check = next(item for item in page_checks if item["page_id"] == "sentinel-data-legal-notice")
    for product in product_checks:
        source_entries.append({
            "source_id": product["source_id"],
            "name": product["exact_product_id"],
            "locator": f"https://download.dataspace.copernicus.eu/odata/v1/Products({product['provider_product_id']})/$value",
            "criteria": [
                {"id": "identity", "required": True, "requires_live": True, "status": "pass", "evidence": [live_evidence(product["catalog_url"], args.assessed_at_utc, f"Exact provider UUID, product name, size, and checksums matched; catalog response SHA-256 {product['catalog_response_sha256']}.")], "note": "Identity matches the exact owner-approved acquisition record."},
                {"id": "authority", "required": True, "requires_live": True, "status": "pass", "evidence": [live_evidence(product["catalog_url"], args.assessed_at_utc, "The primary Copernicus catalogue returned the product record directly.")], "note": "Copernicus Data Space Ecosystem is the primary delivery service for this product."},
                {"id": "access", "required": True, "requires_live": True, "status": "pass", "evidence": [live_evidence(product["catalog_url"], args.assessed_at_utc, "Product Online was true."), live_evidence(OFFICIAL_PAGES[0]["url"], args.assessed_at_utc, f"OData download documentation passed content check; page SHA-256 {download_check['sha256']} and Last-Modified {download_check['last_modified']}.") , live_evidence(OFFICIAL_PAGES[1]["url"], args.assessed_at_utc, f"Token documentation confirms access-token use; page SHA-256 {token_check['sha256']} and Last-Modified {token_check['last_modified']}.")], "note": "The product is online; download requires an access token. Any interactive login, MFA, recovery, or terms prompt remains a stop."},
                {"id": "rights", "required": True, "requires_live": True, "status": "pass", "evidence": [live_evidence(OFFICIAL_PAGES[2]["url"], args.assessed_at_utc, f"Current terms state Sentinel data are available free, full, and open under the Sentinel Data Legal Notice; page SHA-256 {terms_check['sha256']}, Last-Modified {terms_check['last_modified']}."), live_evidence(OFFICIAL_PAGES[3]["url"], args.assessed_at_utc, f"Official Sentinel Data Legal Notice PDF fetched successfully; SHA-256 {legal_check['sha256']}.")], "note": "Sentinel data may be acquired and analyzed with required source notice. Portal images and other portal material retain narrower noncommercial and redistribution restrictions."},
                {"id": "provenance", "required": True, "requires_live": False, "status": "pass", "evidence": [static_evidence(PLAN_REF, "The owner-approved acquisition plan binds the provider UUID, exact product name, source role, and source-manifest lineage.")], "note": "No full-product custody or transformation has yet occurred."},
                {"id": "integrity", "required": True, "requires_live": True, "status": "pass", "evidence": [live_evidence(product["catalog_url"], args.assessed_at_utc, "Live provider MD5 and BLAKE3 values and catalog size match the approved record."), static_evidence("contracts/m2-offline-verification-candidate.json", "The post-transfer route requires local SHA-256, provider MD5, exact size, safe ZIP structure, CRC, SAFE identity, and analysis-critical members before promotion or pixel use.")], "note": "Integrity has a fail-closed post-transfer plan; this preflight does not claim local bytes."},
                {"id": "fitness", "required": True, "requires_live": True, "status": "pass", "evidence": [live_evidence(product["catalog_url"], args.assessed_at_utc, "The exact approved acquisition date, collection identity, content length, and online status remain available."), static_evidence("config/qa/pixel-readiness-contract.json", "Pixel coverage, masks, grid, and registration remain separately predeclared and untested.")], "note": "Fit for controlled acquisition and later evaluation only; scientific and pixel fitness remain unknown."},
                {"id": "privacy-security", "required": True, "requires_live": True, "status": "pass", "evidence": [live_evidence(OFFICIAL_PAGES[2]["url"], args.assessed_at_utc, "Current terms disclose service-side access logging and EU data-center processing."), static_evidence(APPROVAL_REF, "The owner approval forbids credential disclosure, logging, or committing and permits only an existing owner-controlled account or session."), static_evidence("contracts/m2-intake-candidate.json", "Secret policy is references-only and all downloaded archives remain untrusted until offline verification.")], "note": "No personal study data are present; account telemetry and credential secrecy remain controlled."},
            ],
        })

    source_gate = {
        "contract_version": "source-gate/v1",
        "assessment_id": "NEPAL-M2-LIVE-SOURCE-GATE-001",
        "assessed_at": args.assessed_at_utc,
        "authority": {"mode": "inherited", "authority_ref": APPROVAL_REF, "authorized_actions": approved_actions, "expires_at_utc": None},
        "intended_use": {"summary": "Acquire only the eight exact owner-approved Sentinel products into controlled non-Git custody for integrity, pixel, baseline, and registration evaluation.", "planned_actions": approved_actions},
        "sources": source_entries,
        "decision": {"status": "ready", "blocking_reasons": [], "live_verification_pending": [], "approved_actions": approved_actions},
        "write_boundary": {
            "permitted_without_further_authorization": ["record live source evidence", "create the exact approved external custody root after this fresh preflight", "download and verify only the eight exact products under the active M2 contract"],
            "requires_explicit_authorization": ["authenticate", "accept terms", "purchase", "download content", "publish or redistribute"],
        },
    }
    source_gate_sha = hashlib.sha256(serialized(source_gate)).hexdigest()

    credential_reference_presence = {
        name: bool(os.environ.get(name))
        for name in ("CDSE_ACCESS_TOKEN", "CDSE_USERNAME", "CDSE_PASSWORD")
    }
    preflight = {
        "schema_version": "1.0",
        "preflight_id": "NEPAL-M2-CUSTODY-PREFLIGHT-001",
        "status": "pass_no_external_mutation",
        "assessed_at_utc": args.assessed_at_utc,
        "authority": {"approval_ref": APPROVAL_REF, "approval_sha256": sha256(ROOT / APPROVAL_REF), "active_contract_ref": ACTIVE_CONTRACT_REF, "active_contract_sha256": sha256(ROOT / ACTIVE_CONTRACT_REF)},
        "source_gate": {"ref": SOURCE_GATE_REF, "sha256": source_gate_sha, "decision": "ready", "exact_product_count": len(product_checks)},
        "official_page_checks": page_checks,
        "product_checks": product_checks,
        "paths": path_checks,
        "storage": {"volume": project_root.drive, "free_bytes": free_bytes, "free_gib": free_gib, "minimum_free_gib": minimum_gib, "status": "pass"},
        "access": {
            "token_required": True,
            "existing_owner_controlled_account_or_session_authorized": True,
            "credential_reference_presence": credential_reference_presence,
            "credential_values_read_or_recorded": False,
            "authentication_performed": False,
            "account_clickthrough_or_terms_acceptance_encountered": False,
        },
        "checks": {
            "exact_activation": "pass",
            "current_primary_source_pages": "pass",
            "eight_exact_products_online_and_unchanged": "pass",
            "sentinel_rights_route": "pass_for_controlled_acquisition_and_analysis",
            "free_space": "pass",
            "external_root_absent": "pass",
            "path_containment_and_ancestor_safety": "pass",
            "destination_and_staging_collisions": "pass",
            "secret_handling": "pass_no_values_read",
        },
        "eligible_next_actions": ["create the approved external data, custody, and staging roots", "attempt authentication only through a secret-safe owner-controlled reference", "download the first exact product after authentication succeeds without new terms or account action"],
        "mutations_performed": {"external_directory_created": False, "authentication": False, "download": False},
        "limitations": [
            "The source gate establishes fitness for controlled acquisition, not pixel usability or scientific use.",
            "No account session was tested; interactive login, MFA, recovery, or any terms-acceptance prompt remains a stop condition.",
            "Provider content lengths and checksums remain metadata until transferred bytes are independently verified.",
        ],
    }
    preflight_sha = hashlib.sha256(serialized(preflight)).hexdigest()

    active_intake = json.loads(json.dumps(candidate_intake))
    active_intake["created_at"] = args.assessed_at_utc
    for asset in active_intake["assets"]:
        asset["state"] = "authorized"
        asset["source"]["authorization_ref"] = APPROVAL_REF
    active_intake["extensions"] = {
        "status": "active_authorized_preflight_passed_custody_not_initialized",
        "project_root_basis": "parent_of_repository",
        "source_plan_ref": PLAN_REF,
        "source_plan_sha256": sha256(ROOT / PLAN_REF),
        "m2_active_contract_ref": ACTIVE_CONTRACT_REF,
        "m2_active_contract_sha256": sha256(ROOT / ACTIVE_CONTRACT_REF),
        "m2_activation_approval_ref": APPROVAL_REF,
        "m2_activation_approval_sha256": sha256(ROOT / APPROVAL_REF),
        "source_gate_ref": SOURCE_GATE_REF,
        "source_gate_sha256": source_gate_sha,
        "preflight_ref": PREFLIGHT_REF,
        "preflight_sha256": preflight_sha,
        "resume_policy": "disabled_until_range_support_and_unchanged_strong_remote_identity_are_verified",
        "custody_initialized": False,
    }

    create_new(SOURCE_GATE_REF, source_gate)
    create_new(PREFLIGHT_REF, preflight)
    create_new(ACTIVE_INTAKE_REF, active_intake)
    print(json.dumps({
        "status": "pass_no_external_mutation",
        "source_gate": SOURCE_GATE_REF,
        "source_gate_sha256": source_gate_sha,
        "preflight": PREFLIGHT_REF,
        "preflight_sha256": preflight_sha,
        "active_intake": ACTIVE_INTAKE_REF,
        "exact_products_online": len(product_checks),
        "free_gib": free_gib,
        "external_root_exists": expected_data_root.exists(),
        "credential_reference_presence": credential_reference_presence,
    }, indent=2))


if __name__ == "__main__":
    main()
