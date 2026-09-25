#!/usr/bin/env python3
"""Pure, fail-closed controls for the approved alternate optical pair pilot."""

from __future__ import annotations

import hashlib
import http.client
import json
import re
import urllib.error
from pathlib import Path
from typing import Any, BinaryIO, Mapping


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REF = "contracts/m2-optical-pair-pilot-001-execution.json"
EXECUTION_GATE_REF = "records/readiness/m2-optical-pair-pilot-001-execution-gate-002.json"
IMPLEMENTATION_READINESS_REF = "records/readiness/m2-optical-pair-pilot-001-implementation-readiness-002.json"
FINAL_PREFLIGHT_PREFIX = "records/readiness/m2-optical-pair-pilot-001-final-preflight-"
PROPOSAL_SHA256 = "82f394235b3beee5e8e05e8a6515f425b88bba1b7b947422efaacab720f252a5"
BUNDLE_SHA256 = "0aa10813289f917e44cb684c86d78e8b1b381a8271993b202c87d6e262703870"
APPROVAL_SHA256 = "68833c8e356e6e901e21e6b3361c9df3af60a8afb982946ae63269d9b38e6fe5"
SOURCE_IDS = ("M2-OPT-001", "M2-OPT-002")
CATALOG_BASE = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
DOWNLOAD_BASE = "https://download.dataspace.copernicus.eu/odata/v1/Products"
SAFE_CODE = re.compile(r"[a-z0-9_]{3,96}\Z")


class PilotControlError(RuntimeError):
    def __init__(self, code: str):
        safe_code = code if SAFE_CODE.fullmatch(code) else "invalid_control_failure_code"
        super().__init__(safe_code)
        self.code = safe_code


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_contract(root: Path = ROOT) -> dict[str, Any]:
    contract = json.loads((root / CONTRACT_REF).read_text(encoding="utf-8"))
    validate_contract(contract, root)
    return contract


def validate_contract(contract: Mapping[str, Any], root: Path = ROOT) -> None:
    if contract.get("contract_id") != "NEPAL-M2-OPTICAL-PAIR-PILOT-001-EXECUTION":
        raise PilotControlError("pilot_contract_identity_drift")
    authority = contract.get("authority", {})
    expected = (
        (authority.get("proposal_ref"), authority.get("proposal_sha256"), PROPOSAL_SHA256),
        (authority.get("review_bundle_ref"), authority.get("review_bundle_sha256"), BUNDLE_SHA256),
        (authority.get("approval_ref"), authority.get("approval_sha256"), APPROVAL_SHA256),
    )
    for ref, stated, required in expected:
        if not isinstance(ref, str) or stated != required or not (root / ref).is_file() or sha256_file(root / ref) != required:
            raise PilotControlError("pilot_authority_byte_drift")
    approval = json.loads((root / authority["approval_ref"]).read_text(encoding="utf-8"))
    if approval.get("decision") != "approve" or approval.get("human_decision_count") != 1:
        raise PilotControlError("pilot_owner_approval_missing")
    packet_gate_ref = authority.get("packet_gate_ref")
    if not isinstance(packet_gate_ref, str) or not (root / packet_gate_ref).is_file():
        raise PilotControlError("pilot_packet_gate_missing")
    packet_gate = json.loads((root / packet_gate_ref).read_text(encoding="utf-8"))
    bindings = packet_gate.get("bindings", {})
    if (
        packet_gate.get("status") != "pass_exact_public_packet_and_approval_ci_implementation_eligible"
        or bindings.get("proposal_sha256") != PROPOSAL_SHA256
        or bindings.get("review_bundle_sha256") != BUNDLE_SHA256
        or bindings.get("approval_sha256") != APPROVAL_SHA256
        or bindings.get("public_ci_conclusion") != "success"
    ):
        raise PilotControlError("pilot_packet_gate_not_passing")
    proposal = json.loads((root / authority["proposal_ref"]).read_text(encoding="utf-8"))
    sources = contract.get("sources_in_order")
    if not isinstance(sources, list) or len(sources) != 2:
        raise PilotControlError("pilot_source_count_drift")
    for i, (source, proposed) in enumerate(zip(sources, proposal["exact_sources"], strict=True)):
        if (
            source.get("source_id") != SOURCE_IDS[i]
            or source.get("role") != proposed["role"]
            or source.get("provider_product_id") != proposed["provider_product_id"]
            or source.get("exact_product_name") != proposed["name"]
            or source.get("content_length_bytes") != proposed["content_length_bytes"]
            or source.get("provider_md5") != proposed["provider_md5"]
            or source.get("provider_blake3") != proposed["provider_blake3"]
        ):
            raise PilotControlError("pilot_source_identity_drift")
    spatial = contract.get("source_and_spatial_boundary", {})
    if (
        spatial.get("qa_targets") != ["AOI-SOURCE", "AOI-UPPER-CORRIDOR"]
        or spatial.get("overview_full_coverage_claim") is not False
        or spatial.get("tile") != "T45RUM"
        or spatial.get("relative_orbit") != 119
        or spatial.get("processing_baseline") != "05.12"
    ):
        raise PilotControlError("pilot_spatial_boundary_drift")
    aoi_ref, aoi_sha = spatial.get("approved_aoi_ref"), spatial.get("approved_aoi_sha256")
    if not isinstance(aoi_ref, str) or not isinstance(aoi_sha, str) or sha256_file(root / aoi_ref) != aoi_sha:
        raise PilotControlError("pilot_approved_aoi_byte_drift")
    frozen = contract.get("frozen_scientific_bindings", {})
    for ref_key, digest_key in (
        ("pixel_qa_ref", "pixel_qa_sha256"),
        ("original_optical_pixel_contract_ref", "original_optical_pixel_contract_sha256"),
        ("optical_header_contract_ref", "optical_header_contract_sha256"),
    ):
        ref, digest = frozen.get(ref_key), frozen.get(digest_key)
        if not isinstance(ref, str) or not isinstance(digest, str) or sha256_file(root / ref) != digest:
            raise PilotControlError("pilot_frozen_contract_byte_drift")
    old = json.loads((root / frozen["original_optical_pixel_contract_ref"]).read_text(encoding="utf-8"))
    qa = json.loads((root / frozen["pixel_qa_ref"]).read_text(encoding="utf-8"))
    mask = old["mask"]
    grid = old["analysis_grid"]
    if (
        frozen.get("analysis_crs_wkid") != grid["wkid"]
        or frozen.get("cell_size_m") != grid["cell_size_m"]
        or frozen.get("minimum_full_coverage_fraction") != qa["aoi_coverage"]["full_coverage_pass_minimum"]
        or frozen.get("minimum_usable_aoi_fraction") != qa["aoi_coverage"]["usable_fraction_pass_minimum"]
        or frozen.get("valid_scl_classes") != mask["valid_scl_classes"]
        or frozen.get("quality_classification_clear_value") != mask["quality_classification_clear_value"]
        or frozen.get("max_registration_rmse_pixels") != qa["registration"]["pass_max_rmse_pixels"]
    ):
        raise PilotControlError("pilot_frozen_predicate_drift")
    boundary = contract.get("execution_boundary", {})
    if (
        boundary.get("fixed_order") != list(SOURCE_IDS)
        or boundary.get("maximum_requests_per_product") != 2
        or boundary.get("second_request_only_after_documented_transport_interruption") is not True
        or boundary.get("maximum_pair_pixel_qa_attempts") != 1
        or boundary.get("resume_partial") is not False
        or boundary.get("no_replace_promotion") is not True
        or boundary.get("secret_transport") != "anonymous_pipe_single_use_memory_only"
        or boundary.get("credential_value_recorded") is not False
        or boundary.get("automatic_source_substitution") is not False
        or authority.get("new_terms_acceptance") is not False
        or authority.get("baseline_or_change_analysis") is not False
        or authority.get("derived_pixel_or_scientific_publication") is not False
    ):
        raise PilotControlError("pilot_execution_boundary_drift")


def source_for_id(contract: Mapping[str, Any], source_id: str) -> dict[str, Any]:
    sources = [item for item in contract["sources_in_order"] if item["source_id"] == source_id]
    if source_id not in SOURCE_IDS or len(sources) != 1:
        raise PilotControlError("pilot_source_outside_exact_pair")
    return sources[0]


def final_preflight_ref(source_id: str) -> str:
    if source_id not in SOURCE_IDS:
        raise PilotControlError("pilot_source_outside_exact_pair")
    return FINAL_PREFLIGHT_PREFIX + source_id.casefold() + ".json"


def validate_implementation_manifest(root: Path = ROOT) -> str:
    path = root / IMPLEMENTATION_READINESS_REF
    if not path.is_file():
        raise PilotControlError("pilot_implementation_readiness_missing")
    record = json.loads(path.read_text(encoding="utf-8"))
    files = record.get("implementation_file_sha256")
    if record.get("status") != "pass_local_synthetic_public_ci_pending" or not isinstance(files, dict) or len(files) < 10:
        raise PilotControlError("pilot_implementation_readiness_invalid")
    for ref, digest in files.items():
        if not isinstance(ref, str) or not isinstance(digest, str) or len(digest) != 64:
            raise PilotControlError("pilot_implementation_manifest_invalid")
        candidate = root / ref
        try:
            candidate.resolve(strict=True).relative_to(root.resolve(strict=True))
        except (OSError, ValueError) as exc:
            raise PilotControlError("pilot_implementation_manifest_path_unsafe") from exc
        if sha256_file(candidate) != digest:
            raise PilotControlError("pilot_implementation_byte_drift")
    return sha256_file(path)


def require_execution_release(source_id: str | None = None, root: Path = ROOT) -> None:
    """No real archive, ArcGIS, or pixel action before both later public gates."""
    contract = load_contract(root)
    implementation_sha = validate_implementation_manifest(root)
    gate_path = root / EXECUTION_GATE_REF
    preflight_paths = [root / final_preflight_ref(key) for key in (SOURCE_IDS if source_id is None else (source_id,))]
    if not gate_path.is_file() or any(not path.is_file() for path in preflight_paths):
        raise PilotControlError("pilot_execution_gate_or_preflight_missing")
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    if (
        gate.get("status") != "pass_public_execution_gate"
        or gate.get("public_ci_conclusion") != "success"
        or gate.get("contract_sha256") != sha256_file(root / CONTRACT_REF)
        or gate.get("implementation_readiness_sha256") != implementation_sha
        or contract.get("status") != "conditional_public_ci_and_final_preflight_pending"
    ):
        raise PilotControlError("pilot_execution_release_drift")
    for path in preflight_paths:
        preflight = json.loads(path.read_text(encoding="utf-8"))
        if (
            preflight.get("status") != "pass_no_payload"
            or preflight.get("execution_gate_sha256") != sha256_file(gate_path)
            or preflight.get("contract_sha256") != sha256_file(root / CONTRACT_REF)
        ):
            raise PilotControlError("pilot_execution_release_drift")


def exact_catalog_url(source: Mapping[str, Any]) -> str:
    return f"{CATALOG_BASE}({source['provider_product_id']})?$expand=Attributes"


def exact_download_url(source: Mapping[str, Any]) -> str:
    return f"{DOWNLOAD_BASE}({source['provider_product_id']})/$value"


def validate_catalog_product(source: Mapping[str, Any], product: Mapping[str, Any]) -> None:
    checksums = product.get("Checksum", [])
    if not isinstance(checksums, list) or len(checksums) != 2:
        raise PilotControlError("pilot_catalog_checksums_drift")
    values = {item.get("Algorithm"): item.get("Value", "").casefold() for item in checksums if isinstance(item, dict)}
    if (
        product.get("Id") != source["provider_product_id"]
        or product.get("Name") != source["exact_product_name"]
        or product.get("ContentLength") != source["content_length_bytes"]
        or product.get("Online") is not True
        or values != {"MD5": source["provider_md5"], "BLAKE3": source["provider_blake3"]}
    ):
        raise PilotControlError("pilot_catalog_identity_or_availability_drift")


def validate_catalog_footprint(source: Mapping[str, Any], product: Mapping[str, Any], root: Path = ROOT) -> None:
    """Require the reviewed geometry and full footprint enclosure of both target AOIs."""
    from shapely.geometry import shape

    archive = json.loads((root / "records/observations/m2-map-route-feasibility-001-optical-fallback-catalog.json").read_text(encoding="utf-8"))
    matches = [item for item in archive["rows"] if item.get("provider_product_id") == source["provider_product_id"]]
    if len(matches) != 1:
        raise PilotControlError("pilot_captured_footprint_identity_missing")
    aoi = json.loads((root / "config/aoi/approved-study-areas.geojson").read_text(encoding="utf-8"))
    by_id = {item["properties"]["aoi_id"]: item for item in aoi["features"]}
    try:
        observed = shape(product["GeoFootprint"])
        captured = shape(matches[0]["footprint"])
        covers = all(observed.covers(shape(by_id[key]["geometry"])) for key in ("AOI-SOURCE", "AOI-UPPER-CORRIDOR"))
    except (KeyError, TypeError, ValueError) as exc:
        raise PilotControlError("pilot_catalog_footprint_invalid") from exc
    if not observed.is_valid or not observed.equals(captured) or not covers:
        raise PilotControlError("pilot_catalog_footprint_drift")


def may_make_second_request(previous_outcome: str | None, prior_requests: int) -> bool:
    """A new byte-zero request is allowed only after one retained transport interruption."""
    if prior_requests == 0:
        return True
    if prior_requests == 1 and previous_outcome == "transport_interrupted":
        return True
    return False


def classify_terminal_exception(exc: BaseException) -> str:
    """Never persist exception text; it may contain a credential or URL fragment."""
    if isinstance(exc, PilotControlError):
        return exc.code
    if isinstance(exc, urllib.error.HTTPError):
        return "pilot_http_failure_nonretryable"
    if isinstance(exc, http.client.IncompleteRead):
        return "transport_interrupted"
    if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
        return "transport_interrupted"
    return "unexpected_failure"


def read_owner_pipe_secret(stream: BinaryIO) -> str:
    """Accept PowerShell CRLF or LF framing, never trimming token content."""
    try:
        data = stream.readline(16_387)
    finally:
        stream.close()
    if data.endswith(b"\r\n"):
        raw = bytearray(data[:-2])
    elif data.endswith(b"\n"):
        raw = bytearray(data[:-1])
    else:
        raise PilotControlError("pilot_secret_pipe_framing_invalid")
    try:
        if not raw or len(raw) > 16_384:
            raise PilotControlError("pilot_secret_pipe_length_invalid")
        secret = raw.decode("utf-8")
        if any(char.isspace() for char in secret):
            raise PilotControlError("pilot_secret_contains_whitespace")
        return secret
    except UnicodeError as exc:
        raise PilotControlError("pilot_secret_pipe_encoding_invalid") from exc
    finally:
        for index in range(len(raw)):
            raw[index] = 0
