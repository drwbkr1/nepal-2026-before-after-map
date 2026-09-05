#!/usr/bin/env python3
"""Reconcile an all-pass continuation-001 outcome without changing product bytes."""

from __future__ import annotations

from typing import Any

from m2_sentinel_continuation_001_core import (
    ACTIVE_INTAKE_REF,
    CONTRACT_REF,
    FINAL_PREFLIGHT_REF,
    ROOT,
    SOURCE_ORDER,
    SUCCESS_RECONCILIATION_REF,
    Continuation001ControlError,
    load_object,
    now_utc,
    sha256_file,
    validate_runtime_gate,
    write_new_json,
)


ALL_SOURCE_IDS = (
    "M1-SRC-001",
    "M1-SRC-002",
    "M1-SRC-003",
    "M1-SRC-004",
    *SOURCE_ORDER,
)
CONTAINER_ROOT = ROOT / "records/acquisition/container-verification"


def _one_asset(intake: dict[str, Any], source_id: str) -> dict[str, Any]:
    assets = [item for item in intake.get("assets", []) if item.get("extensions", {}).get("source_id") == source_id]
    if len(assets) != 1:
        raise Continuation001ControlError("reconciliation_source_identity_drift")
    return assets[0]


def reconcile_success() -> dict[str, Any]:
    validate_runtime_gate()
    output = ROOT / SUCCESS_RECONCILIATION_REF
    if output.exists():
        raise Continuation001ControlError("success_reconciliation_collision")
    intake_path = ROOT / ACTIVE_INTAKE_REF
    intake = load_object(intake_path)
    receipts: dict[str, dict[str, Any]] = {}
    for source_id in ALL_SOURCE_IDS:
        asset = _one_asset(intake, source_id)
        successful = [item for item in asset.get("attempts", []) if item.get("outcome") == "succeeded"]
        if asset.get("state") != "promoted" or len(successful) != 1:
            raise Continuation001ControlError("all_sources_not_promoted_once")
        attempt_id = successful[0].get("attempt_id")
        receipt = CONTAINER_ROOT / f"{source_id.casefold()}-{attempt_id}.json"
        if not receipt.is_file() or load_object(receipt).get("status") != "pass_container_only":
            raise Continuation001ControlError("required_container_receipt_not_passing")
        receipts[source_id] = {
            "attempt_id": attempt_id,
            "container_receipt_ref": str(receipt.relative_to(ROOT)).replace("\\", "/"),
            "container_receipt_sha256": sha256_file(receipt),
            "promoted_sha256": asset.get("observed", {}).get("promoted_sha256"),
            "promoted_size_bytes": asset.get("observed", {}).get("promoted_size_bytes"),
        }
    payload = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-SENTINEL-CONTINUATION-001-SUCCESS-RECONCILIATION-001",
        "recorded_at_utc": now_utc(),
        "status": "reconciled_all_eight_promoted_container_pass",
        "bindings": {
            "active_intake_ref": ACTIVE_INTAKE_REF,
            "active_intake_sha256": sha256_file(intake_path),
            "continuation_contract_ref": CONTRACT_REF,
            "continuation_contract_sha256": sha256_file(ROOT / CONTRACT_REF),
            "final_preflight_ref": FINAL_PREFLIGHT_REF,
            "final_preflight_sha256": sha256_file(ROOT / FINAL_PREFLIGHT_REF),
            "sources": receipts,
        },
        "assertions": {
            "promoted_container_verified_source_count": 8,
            "continuation_source_order": list(SOURCE_ORDER),
            "m1_src_004_requested_by_continuation": False,
            "automatic_retry_performed": False,
            "credential_values_read_or_recorded": False,
            "archive_extraction_performed": False,
            "pixel_usability_established": False,
            "scientific_fitness_established": False,
        },
        "limitations": [
            "Container success establishes archive identity and SAFE structure only.",
            "Raster readability, usable AOI pixels, registration, and scientific change remain separate gates.",
        ],
        "next_gate": "reconcile M2 transfer and container completion before separately governed materialization or pixel-readiness work",
    }
    write_new_json(output, payload)
    return payload


if __name__ == "__main__":
    raise SystemExit("This reconciler is called only after the detached continuation supervisor verifies all four sources.")
