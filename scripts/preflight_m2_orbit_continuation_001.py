#!/usr/bin/env python3
"""Run the one exact live-metadata, no-orbit-payload continuation preflight."""

from __future__ import annotations

import argparse
import hashlib
import urllib.error
import urllib.request
from typing import Any

from acquire_m2_orbit_file import public_catalog_check, verified_sentinel_custody
from m2_orbit_continuation_001_core import (
    ACTIVATION_REF,
    ACTIVE_INTAKE_REF,
    APPROVAL_REF,
    CONTROL_RECONCILIATION_REF,
    CONTRACT_REF,
    FINAL_PREFLIGHT_REF,
    MANIFEST_REF,
    PUBLICATION_GATE_REF,
    ROOT,
    SOURCE_ORDER,
    load_object,
    require_exact_contract,
    sha256_file,
    validate_approval_files,
    validate_initial_asset_state,
    validate_initial_paths_absent,
    validate_preserved_m2_orb_001_bytes,
    validate_publication_gate,
    write_new_json,
)
from m2_page_identity import normalized_terms_identity
from m2_transfer_core import NoRedirectHandler, TransferControlError
from record_m2_orbit_continuation_001_publication_gate import FILES


TERMS_URL = "https://dataspace.copernicus.eu/terms-and-conditions"
TERMS_RECONCILIATION_REF = "records/source-gates/m2-terms-page-reconciliation.json"
LEGAL_NOTICE_URL = "https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice"


def git_identity() -> tuple[str, str]:
    import subprocess

    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    origin = subprocess.run(["git", "rev-parse", "origin/main"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    return head, origin


def fetch_exact(url: str) -> tuple[bytes, dict[str, Any]]:
    opener = urllib.request.build_opener(NoRedirectHandler())
    request = urllib.request.Request(url, headers={"User-Agent": "nepal-2026-orbit-continuation-preflight/1.0", "Accept-Encoding": "identity"})
    with opener.open(request, timeout=60) as response:
        body = response.read()
        if int(response.status) != 200 or response.geturl() != url:
            raise TransferControlError("official_page_response_identity_drift")
        return body, {
            "url": url,
            "resolved_url": response.geturl(),
            "status_code": int(response.status),
            "content_length_bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            "etag": response.headers.get("ETag"),
            "last_modified": response.headers.get("Last-Modified"),
        }


def failure_code(exc: BaseException, stage: str) -> str:
    if isinstance(exc, TransferControlError):
        return exc.code
    if isinstance(exc, urllib.error.HTTPError):
        return "preflight_http_or_redirect_rejected"
    if isinstance(exc, (urllib.error.URLError, TimeoutError, ConnectionError, OSError)):
        return "preflight_network_unavailable"
    if isinstance(exc, ValueError):
        return "preflight_identity_or_control_drift"
    return f"unexpected_{stage}_failure" if stage.replace("_", "").isalnum() else "unexpected_preflight_failure"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verified-at-utc", required=True)
    args = parser.parse_args()
    output = ROOT / FINAL_PREFLIGHT_REF
    if output.exists():
        raise SystemExit("refusing final-preflight output collision")
    stage = "static_controls"
    terms_observation: dict[str, Any] | None = None
    legal_observation: dict[str, Any] | None = None
    catalog_observations: list[dict[str, Any]] = []
    sentinel_prerequisites: list[dict[str, Any]] = []
    try:
        validate_approval_files()
        gate = load_object(ROOT / PUBLICATION_GATE_REF)
        validate_publication_gate(gate)
        head, origin = git_identity()
        if head != origin or gate.get("github_actions", {}).get("head_sha") != head:
            raise ValueError("public CI commit drift")
        if gate.get("bindings") != {key: sha256_file(path) for key, path in FILES.items()}:
            raise ValueError("public implementation binding drift")
        contract = load_object(ROOT / CONTRACT_REF)
        require_exact_contract(contract)
        activation = load_object(ROOT / ACTIVATION_REF)
        control_reconciliation = load_object(ROOT / CONTROL_RECONCILIATION_REF)
        if (
            activation.get("status") != "pass_exact_orbit_continuation_001_activated_final_no_payload_preflight_pending"
            or control_reconciliation.get("status") != "pass_public_ci_exact_continuation_ready_final_preflight_pending"
        ):
            raise ValueError("activation or control reconciliation drift")
        intake = load_object(ROOT / ACTIVE_INTAKE_REF)
        validate_initial_asset_state(intake)
        path_observations = validate_initial_paths_absent(intake)
        preserved = validate_preserved_m2_orb_001_bytes(intake)
        terms_control = load_object(ROOT / TERMS_RECONCILIATION_REF)
        expected_terms = terms_control.get("current_evidence", {})
        if terms_control.get("status") != "pass_scope_relevant_terms_identity_preserved_no_acceptance":
            raise ValueError("terms reconciliation is not passing")
        stage = "terms_page"
        terms_body, terms_http = fetch_exact(TERMS_URL)
        terms_identity = normalized_terms_identity(terms_body)
        required_phrases = expected_terms.get("required_phrases_present", [])
        folded = terms_identity["normalized_text"].casefold()
        if (
            terms_identity["normalized_text_sha256"] != expected_terms.get("terms_normalized_text_sha256")
            or terms_identity["structured_date_modified"] != expected_terms.get("terms_structured_date_modified")
            or not required_phrases
            or any(str(phrase).casefold() not in folded for phrase in required_phrases)
        ):
            raise ValueError("scope-relevant terms identity changed")
        terms_observation = {
            **terms_http,
            "normalized_text_length": terms_identity["normalized_text_length"],
            "normalized_text_sha256": terms_identity["normalized_text_sha256"],
            "structured_date_modified": terms_identity["structured_date_modified"],
            "required_phrase_count": len(required_phrases),
            "terms_acceptance_performed": False,
        }
        stage = "legal_notice"
        legal_body, legal_http = fetch_exact(LEGAL_NOTICE_URL)
        if legal_http["sha256"] != expected_terms.get("sentinel_legal_notice_sha256"):
            raise ValueError("Sentinel legal notice changed")
        legal_observation = {**legal_http, "exact_legal_notice_unchanged": True}
        manifest = load_object(ROOT / MANIFEST_REF)
        for source_id in SOURCE_ORDER:
            stage = f"catalog_{source_id.casefold().replace('-', '_')}"
            records = [item for item in manifest.get("records", []) if item.get("source_id") == source_id]
            if len(records) != 1:
                raise ValueError("manifest source missing or ambiguous")
            record = records[0]
            sentinel_prerequisites.extend(verified_sentinel_custody(record))
            catalog = public_catalog_check(record)
            catalog_observations.append({
                "source_id": source_id,
                "status": "pass_exact_live_identity_online",
                "url": catalog["url"],
                "response_sha256": catalog["response_sha256"],
                "identity": catalog["identity"],
            })
        unique_sentinel = {item["source_id"]: item for item in sentinel_prerequisites}
        if sorted(unique_sentinel) != [f"M1-SRC-{index:03d}" for index in (3, 4, 5, 6)]:
            raise ValueError("remaining-orbit Sentinel prerequisite cohort drift")
        payload = {
            "schema_version": "1.0",
            "receipt_id": "NEPAL-M2-ORBIT-CONTINUATION-001-FINAL-PREFLIGHT",
            "verified_at_utc": args.verified_at_utc,
            "status": "pass_no_payload_ready_for_single_secret_pipe_handoff",
            "source_ids_in_exact_order": list(SOURCE_ORDER),
            "bindings": {
                "approval_sha256": sha256_file(ROOT / APPROVAL_REF),
                "publication_gate_sha256": sha256_file(ROOT / PUBLICATION_GATE_REF),
                "activation_sha256": sha256_file(ROOT / ACTIVATION_REF),
                "control_reconciliation_sha256": sha256_file(ROOT / CONTROL_RECONCILIATION_REF),
                "continuation_contract_sha256": sha256_file(ROOT / CONTRACT_REF),
                "active_intake_sha256": sha256_file(ROOT / ACTIVE_INTAKE_REF),
                "terms_reconciliation_sha256": sha256_file(ROOT / TERMS_RECONCILIATION_REF),
                "public_commit": head,
            },
            "terms": terms_observation,
            "legal_notice": legal_observation,
            "catalog_revalidation": catalog_observations,
            "sentinel_prerequisites": list(unique_sentinel.values()),
            "path_and_storage": path_observations,
            "preserved_m2_orb_001": preserved,
            "assertions": {
                "network_requests_performed": True,
                "network_request_count": 5,
                "catalog_request_count": 3,
                "authentication_performed": False,
                "credential_presence_checked": False,
                "credential_values_read_or_recorded": False,
                "terms_acceptance_or_account_action": False,
                "orbit_payload_requested": False,
                "orbit_payload_bytes_received": 0,
                "external_data_mutated": False,
                "m2_orb_001_requested_or_mutated": False,
                "automatic_retry_authorized": False,
            },
            "next_gate": "one owner-side credentials-to-token-to-anonymous-pipe handoff for the fixed-order three-source continuation",
        }
        write_new_json(output, payload)
        print(__import__("json").dumps({"status": payload["status"], "output": str(output.relative_to(ROOT)).replace("\\", "/")}, indent=2))
        return 0
    except BaseException as exc:
        code = failure_code(exc, stage)
        failure = {
            "schema_version": "1.0",
            "receipt_id": "NEPAL-M2-ORBIT-CONTINUATION-001-FINAL-PREFLIGHT",
            "verified_at_utc": args.verified_at_utc,
            "status": "blocked_final_no_payload_preflight_no_handoff",
            "failure_code": code,
            "last_stage": stage,
            "source_ids_in_exact_order": list(SOURCE_ORDER),
            "terms": terms_observation,
            "legal_notice": legal_observation,
            "catalog_revalidation": catalog_observations,
            "assertions": {
                "authentication_performed": False,
                "credential_presence_checked": False,
                "credential_values_read_or_recorded": False,
                "terms_acceptance_or_account_action": False,
                "orbit_payload_requested": False,
                "orbit_payload_bytes_received": 0,
                "external_data_mutated": False,
                "owner_handoff_released": False,
                "automatic_retry_authorized": False,
                "exception_message_recorded": False,
                "traceback_recorded": False,
            },
            "next_gate": "explicit review is required before any retry or owner handoff",
        }
        try:
            write_new_json(output, failure)
        except BaseException:
            pass
        print(__import__("json").dumps({"status": failure["status"], "failure_code": code, "credential_value_recorded": False}, indent=2))
        return 20


if __name__ == "__main__":
    raise SystemExit(main())
