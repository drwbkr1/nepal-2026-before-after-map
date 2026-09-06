#!/usr/bin/env python3
"""Reconcile an exact all-three orbit continuation success without applying orbit data."""

from __future__ import annotations

from typing import Any, Mapping

from m2_orbit_continuation_001_core import (
    ACTIVE_INTAKE_REF,
    ACTIVE_VERIFICATION_REF,
    APPROVAL_REF,
    FINAL_PREFLIGHT_REF,
    PRESERVED_SOURCE_ID,
    PUBLICATION_GATE_REF,
    ROOT,
    SOURCE_ORDER,
    SUCCESS_RECONCILIATION_REF,
    OrbitContinuation001Error,
    _one_asset,
    load_object,
    now_utc,
    sha256_file,
    validate_preserved_m2_orb_001_bytes,
    validate_runtime_gate,
    write_new_json,
)
from m2_transfer_core import replace_json


def reconcile_success() -> Mapping[str, Any]:
    validate_runtime_gate()
    intake_path = ROOT / ACTIVE_INTAKE_REF
    intake = load_object(intake_path)
    preserved = validate_preserved_m2_orb_001_bytes(intake)
    results: list[dict[str, Any]] = []
    for source_id in SOURCE_ORDER:
        asset = _one_asset(intake, source_id)
        attempts = asset.get("attempts", [])
        receipt_ref = asset.get("extensions", {}).get("successful_attempt_receipt")
        receipt_sha = asset.get("extensions", {}).get("successful_attempt_receipt_sha256")
        if (
            asset.get("state") != "promoted"
            or len(attempts) != 1
            or attempts[0].get("outcome") != "succeeded"
            or asset.get("failure") is not None
            or not isinstance(receipt_ref, str)
            or not isinstance(receipt_sha, str)
        ):
            raise OrbitContinuation001Error("continuation_success_state_incomplete")
        receipt_path = ROOT / receipt_ref
        if not receipt_path.is_file() or sha256_file(receipt_path) != receipt_sha:
            raise OrbitContinuation001Error("continuation_success_receipt_drift")
        receipt = load_object(receipt_path)
        if (
            receipt.get("event") != "orbit_continuation_001_succeeded"
            or receipt.get("source_id") != source_id
            or receipt.get("credential_value_recorded") is not False
            or receipt.get("provider_checksums_locally_verified") is not True
            or receipt.get("staged_xml_validation", {}).get("endpoint_tolerance_seconds") != 1.0
        ):
            raise OrbitContinuation001Error("continuation_success_receipt_not_passing")
        results.append({
            "source_id": source_id,
            "attempt_id": attempts[0]["attempt_id"],
            "receipt_ref": receipt_ref,
            "receipt_sha256": receipt_sha,
            "local_size_bytes": receipt["local_size_bytes"],
            "local_sha256": receipt["local_sha256"],
            "input_verification_status": "pass_orbit_input_only",
        })
    intake["extensions"].update({
        "status": "active_all_four_orbits_promoted_input_verified",
        "current_orbit_state_counts": {"authorized": 0, "failed": 0, "promoted": 4},
        "orbit_continuation_001_status": "succeeded_all_three_exact_sources",
    })
    replace_json(intake_path, intake, ".orbit-continuation-001-success-tmp")
    verification_path = ROOT / ACTIVE_VERIFICATION_REF
    verification = load_object(verification_path)
    verification["status"] = "active_gate_ready_for_offline_verification"
    verification["bindings"]["active_intake_sha256_current"] = sha256_file(intake_path)
    verification["bindings"]["latest_promoted_source_id"] = SOURCE_ORDER[-1]
    replace_json(verification_path, verification, ".orbit-continuation-001-success-tmp")
    payload = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-CONTINUATION-001-SUCCESS-RECONCILIATION",
        "reconciled_at_utc": now_utc(),
        "status": "pass_all_three_exact_remaining_orbits_promoted_input_verified",
        "source_ids_in_exact_order": list(SOURCE_ORDER),
        "results": results,
        "preserved_m2_orb_001": preserved,
        "bindings": {
            "approval_sha256": sha256_file(ROOT / APPROVAL_REF),
            "publication_gate_sha256": sha256_file(ROOT / PUBLICATION_GATE_REF),
            "final_preflight_sha256": sha256_file(ROOT / FINAL_PREFLIGHT_REF),
            "active_intake_sha256": sha256_file(intake_path),
            "active_verification_sha256": sha256_file(verification_path),
        },
        "assertions": {
            "owner_handoff_count": 1,
            "real_attempt_count": 3,
            "automatic_retry_performed": False,
            "m2_orb_001_requested_or_mutated": False,
            "credential_values_read_or_recorded": False,
            "orbit_application_performed": False,
            "dem_or_radar_pixel_action_performed": False,
            "baseline_change_attribution_or_publication_performed": False,
        },
        "next_gate": "project-control reconciliation and offline four-orbit verification; orbit application remains separately gated",
    }
    write_new_json(ROOT / SUCCESS_RECONCILIATION_REF, payload)
    return payload


if __name__ == "__main__":
    raise SystemExit("This reconciler is called only by the detached orbit continuation supervisor after three exact successes.")
