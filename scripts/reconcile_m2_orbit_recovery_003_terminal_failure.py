#!/usr/bin/env python3
"""Finalize the exact failed recovery-003 intake state from immutable terminal evidence."""

from __future__ import annotations

import copy
import json
from datetime import datetime
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

from m2_orbit_io_core import blake3_file, md5_file
from m2_orbit_recovery_003_core import (
    ACTIVE_INTAKE_REF,
    DATA_ROOT,
    EXPECTED_ASSET_ID,
    EXPECTED_BLAKE3,
    EXPECTED_DESTINATION_RELATIVE,
    EXPECTED_MD5,
    EXPECTED_PRODUCT_NAME,
    EXPECTED_SIZE_BYTES,
    EXPECTED_SOURCE_ID,
    ORIGINAL_ATTEMPT_ID,
    ROOT,
    SECRET_REFERENCE,
    load_object,
    now_utc,
    replace_json,
    sha256_file,
    write_new_json,
)


SUPERVISOR_ID = "m2-orbit-recovery-003-20260906t183804z-e5883324"
ATTEMPT_ID = "m2-orb-001-recovery-002-20260906t183804z-e5883324"
HANDOFF_ID = "m2-orbit-recovery-003-handoff-20260906t183804z-4b1d0b7b"
FAILURE_CODE = "osv_times_do_not_span_validity"
COMPLETED_AT = "2026-09-06T18:38:07Z"
STALE_INTAKE_SHA256 = "e171d40f34d535d76250be33ffa56c5ac90e1b9c045c336ee87d462f1b40160b"
STAGED_SHA256 = "a72c93e500a1c09b62b4cd31889837c9d57ccc41542b16397ff9f2c0fccba3f4"

FINDING_REF = "records/acquisition/m2-orbit-recovery-003-outcome-reconciliation-attempt-001-failure.json"
OUTPUT_REF = "records/acquisition/m2-orbit-recovery-003-terminal-failure-control-reconciliation.json"
PUBLIC_RECEIPT_REF = f"records/acquisition/orbit-attempts/{ATTEMPT_ID}.json"

HANDOFF_PATH = DATA_ROOT / "derived/m2-orbit-recovery-003-handoff" / f"{HANDOFF_ID}.json"
SUPERVISOR_ROOT = DATA_ROOT / "derived/m2-orbit-recovery-003-supervisor" / SUPERVISOR_ID
ATTEMPT_ROOT = DATA_ROOT / "derived/m2-orbit-recovery-003-attempts" / ATTEMPT_ID
STAGED_PATH = DATA_ROOT / ".intake-staging/nepal-m2-orbit-recovery-003" / "m2-orb-001-recovery-002" / f"{EXPECTED_PRODUCT_NAME}.part"
DESTINATION_PATH = DATA_ROOT / "custody" / EXPECTED_DESTINATION_RELATIVE

EXPECTED_EXTERNAL_HASHES = {
    "handoff": "32cfdc6b106913f6bd023e83388cdff0068ba056f87d90e762b127a7f62dc57d",
    "supervisor_started": "644c951c277e4319d4ae1cf1b195f2aceae09fdf3f68803aa2f0bfb14feed2ba",
    "supervisor_heartbeat": "a8db54e0c0116402c8b292d86a347db379a4ddb7a36939798416dc4fa7b119f3",
    "supervisor_failed": "2df740d4341f2a81c35846ef9aee3d17583e5819b6cd5b7827bd775c9e6141a2",
    "attempt_started": "2a5b340d1721382bc373ef2611f398cde480031df850c07d7c5dc403235975c6",
    "attempt_catalog": "dd0e72c98ff7dd4e3c32f96b08f47be7061a1a5294b5d05495cb208a01e0a176",
    "attempt_failed": "fb6e9b100f6da3a54a1d6e554611c77c076675434d46ebb44eca8b0a40e9db4c",
}


def _single(items: list[dict[str, Any]], key: str, value: str) -> dict[str, Any]:
    matches = [item for item in items if item.get(key) == value]
    if len(matches) != 1:
        raise ValueError(f"{key}_missing_or_ambiguous")
    return matches[0]


def finalize_failed_intake(intake: dict[str, Any], terminal_event_path: str) -> dict[str, Any]:
    """Return the exact terminal intake projection without mutating the input."""
    result = copy.deepcopy(intake)
    if result.get("status") != "active":
        raise ValueError("active_intake_root_status_differs")
    assets = [item for item in result.get("assets", []) if item.get("extensions", {}).get("source_id") == EXPECTED_SOURCE_ID]
    if len(assets) != 1:
        raise ValueError("active_intake_source_missing_or_ambiguous")
    asset = assets[0]
    attempts = asset.get("attempts", [])
    if len(attempts) != 2 or attempts[0].get("attempt_id") != ORIGINAL_ATTEMPT_ID:
        raise ValueError("retained_attempt_history_differs")
    attempt = _single(attempts, "attempt_id", ATTEMPT_ID)
    if asset.get("state") != "staging" or attempt.get("outcome") != "started" or attempt.get("completed_at") is not None:
        raise ValueError("active_intake_is_not_exact_stale_terminal_projection")
    if attempt.get("extensions", {}).get("credential_reference") != SECRET_REFERENCE:
        raise ValueError("credential_reference_differs")
    if attempt.get("extensions", {}).get("credential_value_recorded") is not False:
        raise ValueError("credential_recording_flag_differs")
    attempt["completed_at"] = COMPLETED_AT
    attempt["outcome"] = "failed"
    attempt["extensions"]["external_terminal_event"] = terminal_event_path
    asset["state"] = "failed"
    asset["failure"] = {"code": FAILURE_CODE, "recorded_at": COMPLETED_AT}
    return result


def validate_finalized_intake(intake: dict[str, Any], terminal_event_path: str) -> None:
    assets = [item for item in intake.get("assets", []) if item.get("extensions", {}).get("source_id") == EXPECTED_SOURCE_ID]
    if len(assets) != 1:
        raise ValueError("finalized_source_missing_or_ambiguous")
    asset = assets[0]
    attempts = asset.get("attempts", [])
    if len(attempts) != 2 or attempts[0].get("attempt_id") != ORIGINAL_ATTEMPT_ID:
        raise ValueError("finalized_attempt_history_differs")
    attempt = _single(attempts, "attempt_id", ATTEMPT_ID)
    if (
        asset.get("state") != "failed"
        or asset.get("failure") != {"code": FAILURE_CODE, "recorded_at": COMPLETED_AT}
        or attempt.get("completed_at") != COMPLETED_AT
        or attempt.get("outcome") != "failed"
        or attempt.get("extensions", {}).get("external_terminal_event") != terminal_event_path
    ):
        raise ValueError("finalized_terminal_projection_differs")


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _exact_text(root: ET.Element, name: str) -> str:
    values = [(element.text or "").strip() for element in root.iter() if _local_name(element.tag) == name]
    if len(values) != 1 or not values[0]:
        raise ValueError(f"xml_{name.lower()}_missing_or_ambiguous")
    return values[0]


def _utc_value(value: str) -> datetime:
    if not value.startswith("UTC="):
        raise ValueError("xml_utc_prefix_differs")
    return datetime.fromisoformat(value[4:])


def inspect_failed_stage() -> dict[str, Any]:
    if not STAGED_PATH.is_file() or STAGED_PATH.stat().st_size != EXPECTED_SIZE_BYTES:
        raise ValueError("preserved_staged_file_differs")
    payload = STAGED_PATH.read_bytes()
    if b"<!DOCTYPE" in payload.upper() or b"<!ENTITY" in payload.upper():
        raise ValueError("unsafe_xml_declaration")
    root = ET.fromstring(payload)
    validity_start_text = _exact_text(root, "Validity_Start")
    validity_stop_text = _exact_text(root, "Validity_Stop")
    lists = [element for element in root.iter() if _local_name(element.tag) == "List_of_OSVs"]
    if len(lists) != 1:
        raise ValueError("osv_list_missing_or_ambiguous")
    osvs = [element for element in list(lists[0]) if _local_name(element.tag) == "OSV"]
    if not osvs:
        raise ValueError("osv_list_empty")
    first_text = _exact_text(osvs[0], "UTC")
    last_text = _exact_text(osvs[-1], "UTC")
    shortfall_seconds = (_utc_value(validity_stop_text) - _utc_value(last_text)).total_seconds()
    observed = {
        "path": str(STAGED_PATH),
        "size_bytes": STAGED_PATH.stat().st_size,
        "sha256": sha256_file(STAGED_PATH),
        "md5": md5_file(STAGED_PATH),
        "blake3": blake3_file(STAGED_PATH),
        "validity_start": validity_start_text,
        "validity_stop": validity_stop_text,
        "osv_count": len(osvs),
        "first_osv_utc": first_text,
        "last_osv_utc": last_text,
        "validity_stop_shortfall_seconds": shortfall_seconds,
    }
    if (
        observed["sha256"] != STAGED_SHA256
        or observed["md5"] != EXPECTED_MD5
        or observed["blake3"] != EXPECTED_BLAKE3
        or shortfall_seconds <= 0
    ):
        raise ValueError("preserved_staged_identity_or_failure_observation_differs")
    return observed


def _binding(path: Path, expected_sha256: str) -> dict[str, Any]:
    if not path.is_file() or sha256_file(path) != expected_sha256:
        raise ValueError(f"evidence_binding_differs:{path}")
    return {"path": str(path), "sha256": expected_sha256}


def main() -> int:
    output_path = ROOT / OUTPUT_REF
    if output_path.exists():
        raise SystemExit("refusing terminal-failure reconciliation output collision")
    finding_path = ROOT / FINDING_REF
    finding = load_object(finding_path)
    if finding.get("status") != "failed_preserved_terminal_evidence_active_intake_lag" or finding.get("attempt_id") != ATTEMPT_ID:
        raise SystemExit("preserved reconciliation failure differs")

    supervisor_paths = {
        "supervisor_started": SUPERVISOR_ROOT / f"{SUPERVISOR_ID}-started.json",
        "supervisor_heartbeat": SUPERVISOR_ROOT / f"{SUPERVISOR_ID}-heartbeat.json",
        "supervisor_failed": SUPERVISOR_ROOT / f"{SUPERVISOR_ID}-failed.json",
    }
    attempt_paths = {
        "attempt_started": ATTEMPT_ROOT / f"{ATTEMPT_ID}-started.json",
        "attempt_catalog": ATTEMPT_ROOT / f"{ATTEMPT_ID}-catalog-revalidated.json",
        "attempt_failed": ATTEMPT_ROOT / f"{ATTEMPT_ID}-failed.json",
    }
    if sorted(path.name for path in SUPERVISOR_ROOT.iterdir()) != sorted(path.name for path in supervisor_paths.values()):
        raise SystemExit("supervisor inventory differs")
    if sorted(path.name for path in ATTEMPT_ROOT.iterdir()) != sorted(path.name for path in attempt_paths.values()):
        raise SystemExit("attempt inventory differs")
    external = {"handoff": _binding(HANDOFF_PATH, EXPECTED_EXTERNAL_HASHES["handoff"])}
    for name, path in {**supervisor_paths, **attempt_paths}.items():
        external[name] = _binding(path, EXPECTED_EXTERNAL_HASHES[name])
    public_receipt_path = ROOT / PUBLIC_RECEIPT_REF
    public_receipt = _binding(public_receipt_path, EXPECTED_EXTERNAL_HASHES["attempt_failed"])
    terminal = load_object(attempt_paths["attempt_failed"])
    if (
        terminal.get("event") != "orbit_recovery_003_failed"
        or terminal.get("attempt_id") != ATTEMPT_ID
        or terminal.get("source_id") != EXPECTED_SOURCE_ID
        or terminal.get("failure_code") != FAILURE_CODE
        or terminal.get("completed_at") != COMPLETED_AT
        or terminal.get("active_intake_attempt_recorded") is not True
        or terminal.get("credential_value_recorded") is not False
        or terminal.get("retry_automatically_authorized") is not False
    ):
        raise SystemExit("terminal failure evidence differs")
    if DESTINATION_PATH.exists():
        raise SystemExit("unexpected promoted destination exists")
    staged_observation = inspect_failed_stage()

    intake_path = ROOT / ACTIVE_INTAKE_REF
    before_sha256 = sha256_file(intake_path)
    terminal_event_path = str(attempt_paths["attempt_failed"])
    intake = load_object(intake_path)
    if before_sha256 == STALE_INTAKE_SHA256:
        finalized = finalize_failed_intake(intake, terminal_event_path)
        replace_json(intake_path, finalized, "recovery-003-terminal-failure-reconciliation")
    else:
        finalized = intake
        validate_finalized_intake(finalized, terminal_event_path)
    validate_finalized_intake(load_object(intake_path), terminal_event_path)
    after_sha256 = sha256_file(intake_path)

    payload = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-RECOVERY-003-TERMINAL-FAILURE-CONTROL-RECONCILIATION-001",
        "recorded_at_utc": now_utc(),
        "status": "reconciled_terminal_failure_active_intake_no_retry",
        "source_id": EXPECTED_SOURCE_ID,
        "supervisor_id": SUPERVISOR_ID,
        "attempt_id": ATTEMPT_ID,
        "failure_code": FAILURE_CODE,
        "bindings": {
            "preserved_reconciliation_failure_ref": FINDING_REF,
            "preserved_reconciliation_failure_sha256": sha256_file(finding_path),
            "active_intake_ref": ACTIVE_INTAKE_REF,
            "active_intake_sha256_before": STALE_INTAKE_SHA256,
            "active_intake_sha256_after": after_sha256,
            "public_terminal_receipt_ref": PUBLIC_RECEIPT_REF,
            "public_terminal_receipt_sha256": public_receipt["sha256"],
            "external_evidence": external,
        },
        "observations": {
            "active_intake_asset_state_before": "staging",
            "active_intake_attempt_outcome_before": "started",
            "active_intake_asset_state_after": "failed",
            "active_intake_attempt_outcome_after": "failed",
            "active_intake_attempt_completed_at_after": COMPLETED_AT,
            "destination_exists": False,
            "preserved_staged_file": staged_observation,
            "failure_interpretation": "The exact-length staged bytes match both provider checksums, but the final OSV is 0.031829 seconds earlier than the declared validity stop under the frozen strict span check.",
        },
        "assertions": {
            "recovery_003_authority_consumed": True,
            "active_intake_truth_finalized_from_matching_terminal_evidence": True,
            "automatic_retry_performed": False,
            "new_network_request_performed": False,
            "payload_requested_by_reconciliation": False,
            "payload_mutated_by_reconciliation": False,
            "destination_created_by_reconciliation": False,
            "offline_verification_performed": False,
            "credential_value_recorded": False,
            "other_orbit_source_requested": False,
            "orbit_application_performed": False,
            "dem_or_radar_pixels_processed": False,
            "baseline_or_change_analysis_performed": False,
            "scientific_result_established": False,
        },
        "next_gate": "run the existing terminal outcome reconciliation once; any retry or validation-rule change requires a new explicit review",
    }
    write_new_json(output_path, payload)
    print(json.dumps({"status": payload["status"], "output": OUTPUT_REF, "active_intake_sha256": after_sha256}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
