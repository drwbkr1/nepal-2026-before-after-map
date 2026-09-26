#!/usr/bin/env python3
"""Fixed authority and append-only paths for optical GDAL recovery-002."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from m2_optical_pair_pilot_001_core import PilotControlError, sha256_file
from m2_optical_pair_pilot_001_transfer import DATA_ROOT, now_utc, read_json, write_new_json


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-optical-gdal-header-pixel-recovery-002"
PROPOSAL = ROOT / f"contracts/milestone-002-optical-gdal-header-pixel-recovery-002-proposal.json"
BUNDLE = ROOT / f"reviews/{PREFIX}/review-bundle.json"
APPROVAL = ROOT / f"records/source-gates/{PREFIX}-approval.json"
PACKET_GATE = ROOT / f"records/readiness/{PREFIX}-packet-publication-gate.json"
SOURCE_BINDING = ROOT / f"contracts/{PREFIX}-source-binding.json"
IMPLEMENTATION = ROOT / f"records/readiness/{PREFIX}-implementation-readiness.json"
EXECUTION_GATE = ROOT / f"records/readiness/{PREFIX}-execution-gate.json"
FINAL_PREFLIGHT = ROOT / f"records/readiness/{PREFIX}-final-preflight.json"
PUBLIC_TERMINAL = ROOT / f"records/readiness/{PREFIX}-terminal.json"
ATTEMPT_ROOT = DATA_ROOT / "derived" / PREFIX / "real-001"
MATERIALIZED_ROOT = DATA_ROOT / "derived/m2-optical-pair-pilot-001/materialized"
HEADER_RECEIPT = ATTEMPT_ROOT / "header.json"
PIXEL_RECEIPT = ATTEMPT_ROOT / "pixel-qa.json"
PILOT_CONTRACT = ROOT / "contracts/m2-optical-pair-pilot-001-execution.json"
OLD_TERMINAL = ROOT / "records/readiness/m2-optical-pair-header-receipt-recovery-001-post-ci-reconciliation.json"
PROPOSAL_SHA256 = "293a9f90a1d6ca9d1531423798d191901d3772999763fbce34ca6b583e5f7d8e"
BUNDLE_SHA256 = "933f141a4474edafb0fe2580e97428c3dd47a802e4ae8d6d434fb0e6803fb785"
APPROVAL_SHA256 = "bf9b0a05e1e4ad2061707cf8961d8d3027db2f6d7568f0de489ffc2a261918af"
SOURCE_IDS = ("M2-OPT-001", "M2-OPT-002")
SAFE_CODE = re.compile(r"[a-z0-9_]{3,96}\Z")


def require_packet_release() -> dict[str, Any]:
    if (sha256_file(PROPOSAL) != PROPOSAL_SHA256
            or sha256_file(BUNDLE) != BUNDLE_SHA256
            or sha256_file(APPROVAL) != APPROVAL_SHA256):
        raise PilotControlError("gdal_packet_authority_byte_drift")
    approval, gate, proposal = read_json(APPROVAL), read_json(PACKET_GATE), read_json(PROPOSAL)
    if (approval.get("decision") != "approve"
            or approval.get("bindings", {}).get("proposal_sha256") != PROPOSAL_SHA256
            or approval.get("bindings", {}).get("review_bundle_sha256") != BUNDLE_SHA256
            or gate.get("status") != "pass_exact_public_packet_and_approval_ci_implementation_eligible"
            or gate.get("bindings", {}).get("approval_sha256") != APPROVAL_SHA256
            or gate.get("bindings", {}).get("public_ci_conclusion") != "success"
            or proposal.get("requested_single_conditional_envelope", {}).get("new_real_process_maximum") != 1):
        raise PilotControlError("gdal_packet_release_invalid")
    return proposal


def exact_sources() -> list[dict[str, Any]]:
    proposal = require_packet_release()
    sources = read_json(PILOT_CONTRACT)["sources_in_order"]
    reviewed = proposal["exact_existing_sources"]
    if [item.get("source_id") for item in sources] != list(SOURCE_IDS):
        raise PilotControlError("gdal_source_order_drift")
    for source, bound in zip(sources, reviewed, strict=True):
        if (source["source_id"] != bound["source_id"]
                or source["exact_product_name"] != bound["product_name"]
                or source["provider_product_id"] != bound["provider_product_id"]
                or source["content_length_bytes"] != bound["archive_size_bytes"]):
            raise PilotControlError("gdal_source_identity_drift")
    return sources


def frozen_binding() -> dict[str, Any]:
    proposal = require_packet_release()
    binding = read_json(SOURCE_BINDING)
    if (binding.get("authority_proposal_sha256") != PROPOSAL_SHA256
            or binding.get("source_ids_in_order") != list(SOURCE_IDS)
            or binding.get("qa_aoi_ids") != ["AOI-SOURCE", "AOI-UPPER-CORRIDOR", "AOI-OVERVIEW"]
            or binding.get("reader") != "GDAL-only; no ArcPy import in real worker"):
        raise PilotControlError("gdal_source_binding_drift")
    hashes = {item["ref"]: item["sha256"] for item in proposal["input_bindings"]}
    for ref in ("contracts/m2-optical-pair-pilot-001-execution.json",
                "config/qa/optical-baseline-processing-contract.json"):
        if sha256_file(ROOT / ref) != hashes.get(ref):
            raise PilotControlError("gdal_frozen_source_or_processing_drift")
    for ref, key in (("config/qa/optical-input-readiness-contract.json", "frozen_header_sha256"),
                     ("config/qa/pixel-readiness-contract.json", "frozen_pixel_sha256"),
                     ("config/aoi/approved-study-areas-epsg32645.json", "approved_aoi_sha256")):
        if binding.get(key) != hashes.get(ref) or sha256_file(ROOT / ref) != hashes[ref]:
            raise PilotControlError("gdal_frozen_binding_drift")
    if sha256_file(ROOT / binding["frozen_execution_settings_ref"]) != binding["frozen_execution_settings_sha256"]:
        raise PilotControlError("gdal_frozen_execution_drift")
    if sha256_file(OLD_TERMINAL) != hashes["records/readiness/m2-optical-pair-header-receipt-recovery-001-post-ci-reconciliation.json"]:
        raise PilotControlError("gdal_old_terminal_drift")
    return binding


def require_execution_release(*, require_preflight: bool = True) -> dict[str, Any]:
    binding = frozen_binding()
    if not IMPLEMENTATION.is_file() or not EXECUTION_GATE.is_file():
        raise PilotControlError("gdal_execution_gate_missing")
    implementation = read_json(IMPLEMENTATION)
    gate = read_json(EXECUTION_GATE)
    if (implementation.get("status") != "pass_local_synthetic_public_ci_pending"
            or gate.get("status") != "pass_public_execution_gate"
            or gate.get("public_ci_conclusion") != "success"
            or gate.get("implementation_sha256") != sha256_file(IMPLEMENTATION)
            or gate.get("proposal_sha256") != PROPOSAL_SHA256
            or gate.get("approval_sha256") != APPROVAL_SHA256):
        raise PilotControlError("gdal_execution_gate_invalid")
    entries = implementation.get("implementation_file_sha256")
    required = {
        "contracts/m2-optical-gdal-header-pixel-recovery-002-source-binding.json",
        "scripts/m2_optical_gdal_recovery_002_adapter.py",
        "scripts/m2_optical_gdal_recovery_002_core.py",
        "scripts/m2_optical_gdal_recovery_002_engine.py",
        "scripts/m2_optical_gdal_recovery_002_preflight.py",
        "scripts/m2_optical_gdal_recovery_002_worker.py",
        "scripts/m2_optical_gdal_recovery_002_execute.py",
        "scripts/validate_m2_optical_gdal_recovery_002_arcgis.py",
        "tests/test_m2_optical_gdal_recovery_002_adapter.py",
    }
    if not isinstance(entries, dict) or set(entries) != required:
        raise PilotControlError("gdal_implementation_manifest_invalid")
    for ref, digest in entries.items():
        path = ROOT / ref
        try:
            path.resolve(strict=True).relative_to(ROOT.resolve(strict=True))
        except (OSError, ValueError) as exc:
            raise PilotControlError("gdal_implementation_path_unsafe") from exc
        if sha256_file(path) != digest:
            raise PilotControlError("gdal_implementation_byte_drift")
    if require_preflight:
        if not FINAL_PREFLIGHT.is_file():
            raise PilotControlError("gdal_final_preflight_missing")
        preflight = read_json(FINAL_PREFLIGHT)
        if (preflight.get("status") != "pass_offline_exact_identity_no_pixel_decode"
                or preflight.get("execution_gate_sha256") != sha256_file(EXECUTION_GATE)
                or preflight.get("proposal_sha256") != PROPOSAL_SHA256):
            raise PilotControlError("gdal_final_preflight_invalid")
    return binding


def safe_error_code(exc: BaseException) -> str | None:
    code = getattr(exc, "code", None)
    return code if isinstance(code, str) and SAFE_CODE.fullmatch(code) else None
