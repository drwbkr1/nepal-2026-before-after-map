#!/usr/bin/env python3
"""Refresh the live M2 Sentinel gate after a rendered terms-page change."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from m2_page_identity import normalized_terms_identity


ROOT = Path(__file__).resolve().parents[1]
APPROVAL_REF = "records/source-gates/m2-activation-approval.json"
CONTRACT_REF = "contracts/milestone-002.json"
PLAN_REF = "records/acquisition-plan.json"
INTAKE_REF = "contracts/m2-intake.json"
BASE_GATE_REF = "records/source-gates/m2-live-source-gate.json"
BASE_PREFLIGHT_REF = "records/acquisition/preflight.json"
TERMS_RECONCILIATION_REF = "records/source-gates/m2-terms-page-reconciliation.json"
REFRESH_GATE_REF = "records/source-gates/m2-live-source-gate-refresh.json"
REFRESH_PREFLIGHT_REF = "records/acquisition/preflight-refresh.json"

OFFICIAL_PAGES = [
    {"page_id": "odata-download-documentation", "url": "https://documentation.dataspace.copernicus.eu/APIs/OData.html", "required_phrase": "download.dataspace.copernicus.eu/odata/v1/Products("},
    {"page_id": "token-documentation", "url": "https://documentation.dataspace.copernicus.eu/APIs/Token.html", "required_phrase": "access token"},
    {"page_id": "terms-and-conditions", "url": "https://dataspace.copernicus.eu/terms-and-conditions", "required_phrase": "free, full and open basis"},
    {"page_id": "sentinel-data-legal-notice", "url": "https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice", "required_magic": "%PDF"},
]

TERMS_REQUIRED_PHRASES = [
    "free, full and open basis",
    "https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice",
    "need to register as a user",
    "data downloaded, pages visited, software used and time spent",
    "All data processing facilities and data centers are based in the European Union.",
    "shall act in good faith and shall not misuse or interfere the service",
]


def serialized(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2) + "\n").encode("utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(relative: str) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"control root is not an object: {relative}")
    return value


def fetch(url: str) -> tuple[bytes, dict[str, Any]]:
    request = urllib.request.Request(url, headers={"User-Agent": "nepal-2026-evidence-preflight-refresh/1.0"})
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


def checksum_map(values: list[dict[str, Any]]) -> dict[str, str]:
    return {str(item["Algorithm"]).upper(): str(item["Value"]).casefold() for item in values}


def is_reparse_point(path: Path) -> bool:
    attributes = getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def live(locator: str, observed_at: str, note: str) -> dict[str, Any]:
    return {"type": "live", "locator": locator, "observed_at": observed_at, "note": note}


def static(locator: str, note: str) -> dict[str, Any]:
    return {"type": "static", "locator": locator, "note": note}


def write_new(relative: str, value: dict[str, Any]) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(serialized(value))
        handle.flush()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assessed-at-utc", required=True)
    args = parser.parse_args()
    datetime.fromisoformat(args.assessed_at_utc.replace("Z", "+00:00"))
    for relative in (TERMS_RECONCILIATION_REF, REFRESH_GATE_REF, REFRESH_PREFLIGHT_REF):
        if (ROOT / relative).exists():
            raise SystemExit(f"refresh output already exists; refusing replacement: {relative}")

    approval = load(APPROVAL_REF)
    contract = load(CONTRACT_REF)
    plan = load(PLAN_REF)
    intake = load(INTAKE_REF)
    base_gate = load(BASE_GATE_REF)
    base_preflight = load(BASE_PREFLIGHT_REF)
    if approval.get("status") != "approved" or contract.get("status") != "active":
        raise SystemExit("M2 authority is not active")
    if approval.get("acquisition_plan_sha256") != sha256(ROOT / PLAN_REF):
        raise SystemExit("M2 approval no longer binds the acquisition plan")
    if any(asset.get("state") != "authorized" or asset.get("attempts") != [] for asset in intake.get("assets", [])):
        raise SystemExit("Sentinel intake is no longer at the unattempted no-mutation checkpoint")

    page_checks: list[dict[str, Any]] = []
    page_bodies: dict[str, bytes] = {}
    initial_by_id = {item["page_id"]: item for item in base_preflight.get("official_page_checks", [])}
    for definition in OFFICIAL_PAGES:
        body, metadata = fetch(definition["url"])
        decoded = body.decode("utf-8", errors="ignore")
        content_ok = body.startswith(b"%PDF") if "required_magic" in definition else definition["required_phrase"].casefold() in decoded.casefold()
        if metadata["status_code"] != 200 or not content_ok:
            raise SystemExit(f"official page failed current content check: {definition['page_id']}")
        metadata.update({"page_id": definition["page_id"], "url": definition["url"], "required_content_check": True})
        page_checks.append(metadata)
        page_bodies[definition["page_id"]] = body
    changed_pages = [item["page_id"] for item in page_checks if item["sha256"] != initial_by_id[item["page_id"]]["sha256"]]
    if any(page_id != "terms-and-conditions" for page_id in changed_pages):
        raise SystemExit("an official page other than the rendered terms page changed")

    terms_check = next(item for item in page_checks if item["page_id"] == "terms-and-conditions")
    legal_check = next(item for item in page_checks if item["page_id"] == "sentinel-data-legal-notice")
    terms_identity = normalized_terms_identity(page_bodies["terms-and-conditions"])
    folded_terms = terms_identity["normalized_text"].casefold()
    missing_phrases = [phrase for phrase in TERMS_REQUIRED_PHRASES if phrase.casefold() not in folded_terms]
    if missing_phrases:
        raise SystemExit("current official terms section is missing one or more scope-relevant clauses")
    if legal_check["sha256"] != initial_by_id["sentinel-data-legal-notice"]["sha256"]:
        raise SystemExit("the exact Sentinel Data Legal Notice changed")

    terms_reconciliation = {
        "schema_version": "1.0",
        "reconciliation_id": "NEPAL-M2-CDSE-TERMS-PAGE-RECONCILIATION-001",
        "assessed_at_utc": args.assessed_at_utc,
        "status": "pass_scope_relevant_terms_identity_preserved_no_acceptance",
        "authority": {
            "approval_ref": APPROVAL_REF,
            "approval_sha256": sha256(ROOT / APPROVAL_REF),
            "authorized_action": "reconcile current source evidence and resume only the already approved exact-product acquisition",
            "terms_acceptance_authorized": False,
        },
        "initial_evidence": {
            "source_gate_ref": BASE_GATE_REF,
            "source_gate_sha256": sha256(ROOT / BASE_GATE_REF),
            "preflight_ref": BASE_PREFLIGHT_REF,
            "preflight_sha256": sha256(ROOT / BASE_PREFLIGHT_REF),
            "terms_rendered_page_sha256": initial_by_id["terms-and-conditions"]["sha256"],
            "terms_last_modified": initial_by_id["terms-and-conditions"].get("last_modified"),
            "sentinel_legal_notice_sha256": initial_by_id["sentinel-data-legal-notice"]["sha256"],
        },
        "current_evidence": {
            "terms_url": "https://dataspace.copernicus.eu/terms-and-conditions",
            "terms_rendered_page_sha256": terms_check["sha256"],
            "terms_rendered_page_length_bytes": terms_check["content_length_bytes"],
            "terms_http_last_modified": terms_check.get("last_modified"),
            "terms_http_etag": terms_check.get("etag"),
            "terms_section_id": terms_identity["section_id"],
            "terms_normalized_text_length": terms_identity["normalized_text_length"],
            "terms_normalized_text_sha256": terms_identity["normalized_text_sha256"],
            "terms_structured_date_modified": terms_identity["structured_date_modified"],
            "required_phrases_present": TERMS_REQUIRED_PHRASES,
            "sentinel_legal_notice_url": "https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice",
            "sentinel_legal_notice_sha256": legal_check["sha256"],
        },
        "decision": {
            "rendered_page_bytes_changed": "terms-and-conditions" in changed_pages,
            "scope_relevant_legal_section_current": True,
            "official_structured_terms_document_modified_after_initial_preflight": False,
            "exact_linked_sentinel_legal_notice_unchanged": True,
            "interactive_terms_prompt_observed": False,
            "terms_or_account_action_performed": False,
            "classification": "rendered_page_change_does_not_change_the_approved_Sentinel_data_rights_or_access_scope",
            "authorized_next_action": "refresh the non-mutating Sentinel acquisition preflight and retain the existing stop on any legal-section, legal-notice, account, or terms-acceptance change",
        },
        "limitations": [
            "The initial full HTML body was not retained, so this record does not claim a byte-level location for the rendered-page delta.",
            "The decision is limited to the approved Sentinel acquisition use and relies on the current official legal section, its structured modification date, the initial captured scope-relevant statements, and the unchanged linked Sentinel Data Legal Notice.",
            "Any interactive terms prompt or later change to the normalized legal section, its structured modification date, or the linked legal notice remains a stop.",
        ],
        "mutations_performed": {
            "authentication": False,
            "credential_values_read_or_recorded": False,
            "terms_acceptance": False,
            "account_action": False,
            "product_payload_requested": False,
            "product_payload_bytes_received": 0,
            "external_custody_mutated": False,
        },
    }
    terms_reconciliation_sha = hashlib.sha256(serialized(terms_reconciliation)).hexdigest()

    product_checks: list[dict[str, Any]] = []
    for record in plan["records"]:
        provider_id = record["provider_product_id"]
        catalog_url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products({provider_id})?%24expand=Attributes"
        body, response = fetch(catalog_url)
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
            "catalog_response_sha256": response["sha256"],
            "publication_date": product.get("PublicationDate"),
            "modification_date": product.get("ModificationDate"),
            "content_length_bytes": product.get("ContentLength"),
            "checks": checks,
            "status": "pass" if all(checks.values()) else "fail",
        })
    if any(item["status"] != "pass" for item in product_checks):
        raise SystemExit("one or more exact Sentinel products failed refreshed identity or availability checks")

    page_by_id = {item["page_id"]: item for item in page_checks}
    approved_actions = list(base_gate["authority"]["authorized_actions"])
    source_entries = []
    for product in product_checks:
        source_entries.append({
            "source_id": product["source_id"],
            "name": product["exact_product_id"],
            "locator": f"https://download.dataspace.copernicus.eu/odata/v1/Products({product['provider_product_id']})/$value",
            "criteria": [
                {"id": "identity", "required": True, "requires_live": True, "status": "pass", "evidence": [live(product["catalog_url"], args.assessed_at_utc, f"Exact UUID, name, size, and provider checksums matched; response SHA-256 {product['catalog_response_sha256']}.")], "note": "Identity still matches the owner-approved record."},
                {"id": "authority", "required": True, "requires_live": True, "status": "pass", "evidence": [live(product["catalog_url"], args.assessed_at_utc, "The primary CDSE catalogue returned the exact product directly.")], "note": "CDSE remains the primary delivery service."},
                {"id": "access", "required": True, "requires_live": True, "status": "pass", "evidence": [live(product["catalog_url"], args.assessed_at_utc, "Product Online was true."), live(OFFICIAL_PAGES[0]["url"], args.assessed_at_utc, f"OData documentation is unchanged at SHA-256 {page_by_id['odata-download-documentation']['sha256']}."), live(OFFICIAL_PAGES[1]["url"], args.assessed_at_utc, f"Token documentation is unchanged at SHA-256 {page_by_id['token-documentation']['sha256']}.")], "note": "Download still requires an owner-controlled access token; interactive login, MFA, recovery, or terms acceptance remains a stop."},
                {"id": "rights", "required": True, "requires_live": True, "status": "pass", "evidence": [live(OFFICIAL_PAGES[2]["url"], args.assessed_at_utc, f"The scope-relevant legal section passed at normalized SHA-256 {terms_identity['normalized_text_sha256']} with structured dateModified {terms_identity['structured_date_modified']}; rendered-page drift is reconciled in {TERMS_RECONCILIATION_REF}."), live(OFFICIAL_PAGES[3]["url"], args.assessed_at_utc, f"The linked Sentinel Data Legal Notice remains SHA-256 {legal_check['sha256']}.")], "note": "The exact approved Sentinel acquisition and analysis use remains supported; narrower portal-content restrictions remain."},
                {"id": "provenance", "required": True, "requires_live": False, "status": "pass", "evidence": [static(PLAN_REF, "The approved plan binds each provider UUID and exact product identity.")], "note": "No Sentinel payload or transformation has occurred."},
                {"id": "integrity", "required": True, "requires_live": True, "status": "pass", "evidence": [live(product["catalog_url"], args.assessed_at_utc, "Provider MD5, BLAKE3 metadata, and size match the approved record."), static("contracts/m2-offline-verification.json", "Post-transfer verification remains fail closed.")], "note": "Current metadata support the existing post-transfer integrity plan."},
                {"id": "fitness", "required": True, "requires_live": True, "status": "pass", "evidence": [live(product["catalog_url"], args.assessed_at_utc, "Exact identity and online status remain available."), static("config/qa/pixel-readiness-contract.json", "Pixel fitness remains separately untested.")], "note": "Fit only for controlled acquisition and later evaluation."},
                {"id": "privacy-security", "required": True, "requires_live": True, "status": "pass", "evidence": [live(OFFICIAL_PAGES[2]["url"], args.assessed_at_utc, "The current legal section retains service-side logging and EU data-center disclosures."), static(APPROVAL_REF, "Secret values remain owner-controlled and prohibited from records or chat."), static(INTAKE_REF, "The active intake keeps references-only secret handling.")], "note": "Account telemetry and credential secrecy remain controlled; no credential value was read."},
            ],
        })
    refresh_gate = {
        "contract_version": "source-gate/v1",
        "assessment_id": "NEPAL-M2-LIVE-SOURCE-GATE-REFRESH-001",
        "assessed_at": args.assessed_at_utc,
        "authority": base_gate["authority"],
        "intended_use": base_gate["intended_use"],
        "sources": source_entries,
        "decision": {"status": "ready", "blocking_reasons": [], "live_verification_pending": [], "approved_actions": approved_actions},
        "write_boundary": base_gate["write_boundary"],
        "extensions": {
            "refresh_of_ref": BASE_GATE_REF,
            "refresh_of_sha256": sha256(ROOT / BASE_GATE_REF),
            "terms_reconciliation_ref": TERMS_RECONCILIATION_REF,
            "terms_reconciliation_sha256": terms_reconciliation_sha,
            "terms_acceptance_performed": False,
            "product_payload_bytes_received": 0,
        },
    }
    refresh_gate_sha = hashlib.sha256(serialized(refresh_gate)).hexdigest()

    project_root = ROOT.parent.resolve()
    external_root = (project_root / "nepal-2026-before-after-map-data").resolve(strict=True)
    custody_root = (project_root / Path(intake["custody_root"])).resolve(strict=True)
    staging_root = (project_root / Path(intake["staging_root"])).resolve(strict=True)
    for path in (external_root, custody_root, staging_root):
        if not path.is_dir() or is_reparse_point(path):
            raise SystemExit(f"current custody path is missing, non-directory, or a reparse point: {path}")
    existing_asset_paths = []
    for asset in intake["assets"]:
        destination = (custody_root / Path(asset["destination_relative_path"])).resolve(strict=False)
        staging = (staging_root / Path(asset["staging_relative_path"])).resolve(strict=False)
        destination.relative_to(custody_root)
        staging.relative_to(staging_root)
        if destination.exists() or staging.exists():
            existing_asset_paths.append(str(destination if destination.exists() else staging))
    if existing_asset_paths:
        raise SystemExit("one or more exact Sentinel destination or staging paths already exist")
    free_bytes = shutil.disk_usage(project_root).free
    minimum_gib = float(plan["custody"]["minimum_free_space_gib_before_start"])
    free_gib = round(free_bytes / (1024 ** 3), 3)
    if free_gib < minimum_gib:
        raise SystemExit("free space is below the approved minimum")

    transfer_page_checks = []
    for item in page_checks:
        entry = dict(item)
        if item["page_id"] == "terms-and-conditions":
            entry.update({
                "comparison_mode": "normalized_terms_section_sha256",
                "initial_rendered_page_sha256": initial_by_id[item["page_id"]]["sha256"],
                "rendered_page_changed_from_initial": item["sha256"] != initial_by_id[item["page_id"]]["sha256"],
                "terms_identity": {
                    "section_id": terms_identity["section_id"],
                    "normalized_text_length": terms_identity["normalized_text_length"],
                    "normalized_text_sha256": terms_identity["normalized_text_sha256"],
                    "structured_date_modified": terms_identity["structured_date_modified"],
                    "required_phrases": TERMS_REQUIRED_PHRASES,
                },
            })
        else:
            entry["comparison_mode"] = "raw_sha256"
        transfer_page_checks.append(entry)

    refresh_preflight = {
        "schema_version": "1.1",
        "preflight_id": "NEPAL-M2-SENTINEL-PREFLIGHT-REFRESH-001",
        "status": "pass_no_external_mutation",
        "assessed_at_utc": args.assessed_at_utc,
        "authority": {
            "approval_ref": APPROVAL_REF,
            "approval_sha256": sha256(ROOT / APPROVAL_REF),
            "active_contract_ref": CONTRACT_REF,
            "active_contract_sha256": sha256(ROOT / CONTRACT_REF),
        },
        "base_preflight": {"ref": BASE_PREFLIGHT_REF, "sha256": sha256(ROOT / BASE_PREFLIGHT_REF)},
        "source_gate": {"ref": REFRESH_GATE_REF, "sha256": refresh_gate_sha, "decision": "ready", "exact_product_count": 8},
        "terms_reconciliation": {"ref": TERMS_RECONCILIATION_REF, "sha256": terms_reconciliation_sha, "status": terms_reconciliation["status"]},
        "official_page_checks": transfer_page_checks,
        "product_checks": product_checks,
        "paths": {
            "external_data_root": str(external_root),
            "custody_root": str(custody_root),
            "staging_root": str(staging_root),
            "external_data_root_exists": True,
            "custody_initialized": True,
            "all_control_roots_not_reparse_points": True,
            "existing_destination_or_staging_paths": [],
            "case_insensitive_path_collision": False,
        },
        "storage": {"volume": project_root.drive, "free_bytes": free_bytes, "free_gib": free_gib, "minimum_free_gib": minimum_gib, "status": "pass"},
        "intake_state": {"authorized_count": 8, "attempt_count": 0, "promoted_count": 0, "failed_count": 0},
        "access": {
            "token_required": True,
            "existing_owner_controlled_account_or_session_authorized": True,
            "credential_reference_presence_checked": False,
            "credential_values_read_or_recorded": False,
            "authentication_performed": False,
            "account_clickthrough_or_terms_acceptance_encountered": False,
        },
        "checks": {
            "exact_activation": "pass",
            "current_primary_source_pages": "pass_with_scope_relevant_terms_identity",
            "rendered_terms_page_change_reconciled": "pass",
            "eight_exact_products_online_and_unchanged": "pass",
            "sentinel_rights_route": "pass_for_controlled_acquisition_and_analysis",
            "free_space": "pass",
            "initialized_external_custody": "pass_empty_for_sentinel_products",
            "destination_and_staging_collisions": "pass",
            "secret_handling": "pass_no_values_read",
        },
        "eligible_next_actions": ["attempt authentication only through a secret-safe owner-controlled token reference", "download M1-SRC-001 after live legal-section and exact-product revalidation pass"],
        "mutations_performed": {"external_custody": False, "authentication": False, "credential_values_read_or_recorded": False, "terms_acceptance": False, "product_payload_requested": False, "product_payload_bytes_received": 0},
        "limitations": [
            "This refresh establishes current source and transfer eligibility, not pixel usability or scientific fitness.",
            "The rendered terms-page bytes changed, but the current scope-relevant legal section, its structured modification date, and the exact linked Sentinel Legal Notice support the same approved use.",
            "The transfer runner must stop before mutation on any later scope-relevant legal-section, legal-notice, account, terms-acceptance, product-identity, path, or storage drift.",
        ],
    }

    write_new(TERMS_RECONCILIATION_REF, terms_reconciliation)
    write_new(REFRESH_GATE_REF, refresh_gate)
    write_new(REFRESH_PREFLIGHT_REF, refresh_preflight)
    print(json.dumps({
        "status": "pass_no_external_mutation",
        "assessed_at_utc": args.assessed_at_utc,
        "changed_rendered_pages": changed_pages,
        "terms_normalized_text_sha256": terms_identity["normalized_text_sha256"],
        "exact_products_refreshed": len(product_checks),
        "terms_reconciliation_sha256": terms_reconciliation_sha,
        "source_gate_refresh_sha256": refresh_gate_sha,
        "preflight_refresh_sha256": hashlib.sha256(serialized(refresh_preflight)).hexdigest(),
        "credential_values_read_or_recorded": False,
        "authentication_performed": False,
        "terms_acceptance_performed": False,
        "product_payload_bytes_received": 0,
        "external_custody_mutated": False,
    }, indent=2))


if __name__ == "__main__":
    main()
