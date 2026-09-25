#!/usr/bin/env python3
"""Fresh no-payload source, rights, account, custody, and runtime preflight."""

from __future__ import annotations

import json
import hashlib
import shutil
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Mapping

from m2_optical_pair_pilot_001_core import (
    CONTRACT_REF, EXECUTION_GATE_REF, PilotControlError, final_preflight_ref,
    load_contract, sha256_file, validate_implementation_manifest,
)
from m2_optical_pair_pilot_001_transfer import DATA_ROOT, fetch_catalog, now_utc, read_json, write_new_json
from m2_page_identity import evaluate_page_body


ROOT = Path(__file__).resolve().parents[1]
USERINFO_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/userinfo"
PAGE_SNAPSHOT = ROOT / "records/acquisition/preflight-refresh.json"
DOCUMENT_ROUTE_MARKERS = {
    "odata-download-documentation": (
        "https://download.dataspace.copernicus.eu/odata/v1/Products",
        "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
        "Authorization: Bearer", "cdse-public",
    ),
    "token-documentation": (
        "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
        "grant_type=password", "cdse-public", "totp=",
    ),
}


def evaluate_current_documentation(item: Mapping[str, Any], body: bytes) -> dict[str, Any]:
    """Allow page-layout drift only where the exact reviewed API route still appears."""
    page_id = item.get("page_id")
    markers = DOCUMENT_ROUTE_MARKERS.get(page_id)
    if markers is None:
        raise PilotControlError("pilot_official_access_or_terms_page_changed")
    try:
        page = body.decode("utf-8")
    except UnicodeError as exc:
        raise PilotControlError("pilot_official_document_encoding_invalid") from exc
    if any(marker not in page for marker in markers):
        raise PilotControlError("pilot_official_api_route_changed")
    return {
        "page_id": page_id, "url": item["url"],
        "comparison_mode": "current_route_markers_after_raw_page_change",
        "current_page_sha256": hashlib.sha256(body).hexdigest(),
        "prior_page_sha256": item["sha256"],
        "raw_page_changed": True, "exact_api_route_markers_present": True,
        "marker_count": len(markers),
        "terms_or_legal_notice_equivalence_inferred": False,
    }


def verify_page_anchors(*, opener: Any | None = None) -> list[dict[str, Any]]:
    checks = read_json(PAGE_SNAPSHOT).get("official_page_checks", [])
    if len(checks) != 4:
        raise PilotControlError("pilot_official_page_anchor_count_drift")
    observations = []
    for item in checks:
        url = item.get("url")
        if not isinstance(url, str) or not url.startswith("https://"):
            raise PilotControlError("pilot_official_page_url_invalid")
        request = urllib.request.Request(url, headers={"User-Agent": "nepal-optical-pilot-001/1.0"})
        try:
            with (opener or urllib.request.build_opener()).open(request, timeout=60) as response:
                if response.status != 200 or response.geturl() != url:
                    raise PilotControlError("pilot_official_page_response_drift")
                body = response.read(2 * 1024 * 1024 + 1)
                if len(body) > 2 * 1024 * 1024:
                    raise PilotControlError("pilot_official_page_too_large")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise PilotControlError("pilot_official_page_unavailable") from exc
        try:
            observations.append(evaluate_page_body(item, body))
        except (ValueError, UnicodeError) as exc:
            if item.get("page_id") in DOCUMENT_ROUTE_MARKERS:
                observations.append(evaluate_current_documentation(item, body))
            else:
                raise PilotControlError("pilot_official_access_or_terms_page_changed") from exc
    return observations


def verify_account_token(secret: str, *, opener: Any | None = None) -> bool:
    if not secret or len(secret.encode("utf-8")) > 16_384 or any(ch.isspace() for ch in secret):
        raise PilotControlError("pilot_secret_invalid")
    request = urllib.request.Request(USERINFO_URL, headers={
        "Authorization": f"Bearer {secret}",
        "Accept": "application/json",
        "User-Agent": "nepal-optical-pilot-001/1.0",
    })
    try:
        with (opener or urllib.request.build_opener()).open(request, timeout=30) as response:
            if response.status != 200 or response.geturl() != USERINFO_URL:
                raise PilotControlError("pilot_account_access_unavailable")
            raw = response.read(64 * 1024 + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise PilotControlError("pilot_account_access_unavailable") from exc
    if len(raw) > 64 * 1024:
        raise PilotControlError("pilot_account_response_too_large")
    try:
        result = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise PilotControlError("pilot_account_response_invalid") from exc
    if not isinstance(result, dict) or not isinstance(result.get("sub"), str) or not result["sub"]:
        raise PilotControlError("pilot_account_identity_unconfirmed")
    return True


def final_preflight(source: Mapping[str, Any], secret: str, *, arcgis_runtime: Mapping[str, str], opener: Any | None = None) -> dict[str, Any]:
    """Read metadata only; the token and account response are never serialized."""
    contract = load_contract()
    if contract.get("status") != "conditional_public_ci_and_final_preflight_pending":
        raise PilotControlError("pilot_contract_not_activated")
    gate_path = ROOT / EXECUTION_GATE_REF
    if not gate_path.is_file():
        raise PilotControlError("pilot_execution_gate_missing")
    gate = read_json(gate_path)
    if (
        gate.get("status") != "pass_public_execution_gate"
        or gate.get("public_ci_conclusion") != "success"
        or gate.get("contract_sha256") != sha256_file(ROOT / CONTRACT_REF)
        or gate.get("implementation_readiness_sha256") != validate_implementation_manifest()
    ):
        raise PilotControlError("pilot_execution_gate_not_passing")
    output = ROOT / final_preflight_ref(source["source_id"])
    if output.exists():
        raise PilotControlError("pilot_final_preflight_consumed")
    assessment = read_json(ROOT / "records/observations/m2-optical-pair-pilot-001-assessment.json")
    for binding in assessment["input_bindings"]:
        ref = ROOT / binding["ref"]
        if not ref.is_file() or sha256_file(ref) != binding["sha256"]:
            raise PilotControlError("pilot_prior_evidence_byte_drift")
    page_observations = verify_page_anchors(opener=opener)
    catalog = fetch_catalog(source, opener=opener)
    account_confirmed = verify_account_token(secret, opener=opener)
    if DATA_ROOT.resolve(strict=True) != (ROOT.parent / f"{ROOT.name}-data").resolve(strict=True):
        raise PilotControlError("pilot_external_custody_root_drift")
    if shutil.disk_usage(DATA_ROOT).free < 12 * 1024**3:
        raise PilotControlError("pilot_free_space_below_minimum")
    attempt_root = DATA_ROOT / "derived/m2-optical-pair-pilot-001"
    destination = attempt_root / "custody" / source["source_id"].casefold() / (source["exact_product_name"] + ".zip")
    if destination.exists():
        raise PilotControlError("pilot_destination_collision")
    if not arcgis_runtime.get("version", "").startswith("3.7") or arcgis_runtime.get("spatial") != "Available":
        raise PilotControlError("pilot_arcgis_prerequisite_unavailable")
    receipt = {
        "schema_version": "1.0", "receipt_id": "NEPAL-M2-OPTICAL-PAIR-PILOT-001-FINAL-PREFLIGHT",
        "source_id": source["source_id"], "provider_product_id": source["provider_product_id"],
        "status": "pass_no_payload", "checked_at_utc": now_utc(),
        "contract_sha256": sha256_file(ROOT / CONTRACT_REF),
        "execution_gate_sha256": sha256_file(gate_path),
        "catalog_response_sha256": catalog["response_sha256"],
        "official_page_observations": page_observations,
        "account_access_confirmed": account_confirmed,
        "account_response_or_pii_recorded": False,
        "new_terms_acceptance_performed": False,
        "arcgis_version": arcgis_runtime["version"],
        "spatial_analyst_available": True,
        "payload_requests_performed": False,
        "credential_value_recorded": False,
        "source_footprint_is_catalog_only": True,
        "pixel_fitness_unknown": True,
    }
    write_new_json(output, receipt)
    return receipt
