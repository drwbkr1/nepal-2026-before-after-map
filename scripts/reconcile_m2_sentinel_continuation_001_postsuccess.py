#!/usr/bin/env python3
"""Reconcile the authorized continuation success into current project controls."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT.parent / f"{ROOT.name}-data"
SUCCESS_REF = "records/acquisition/sentinel-continuation-001-success-reconciliation.json"
POST_FAILURE_REF = "records/acquisition/sentinel-continuation-001-postsuccess-validation-attempt-001-failure.json"
POST_RECONCILIATION_REF = "records/acquisition/sentinel-continuation-001-postsuccess-reconciliation.json"
CONTINUATION_SOURCE_IDS = ("M1-SRC-005", "M1-SRC-006", "M1-SRC-008", "M1-SRC-010")
ALL_SOURCE_IDS = ("M1-SRC-001", "M1-SRC-002", "M1-SRC-003", "M1-SRC-004", *CONTINUATION_SOURCE_IDS)
POST_CONTAINER_NEXT_ACTION = (
    "Prepare and review an exact bounded materialization and pixel-readiness plan for the five not-yet-materialized "
    "products. Do not materialize, decode pixels, run baselines, or start orbit recovery before the separate gates are satisfied."
)


class PostSuccessReconciliationError(RuntimeError):
    """The observed completion state does not satisfy the approved boundary."""


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load(relative: str) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PostSuccessReconciliationError(f"not_object:{relative}")
    return value


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_ref(relative: str) -> str:
    return sha256_path(ROOT / relative)


def json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def replace_json(relative: str, value: dict[str, Any]) -> None:
    path = ROOT / relative
    temporary = path.with_name(f".{path.name}.postsuccess-tmp")
    if temporary.exists():
        raise PostSuccessReconciliationError(f"temporary_collision:{relative}")
    temporary.write_bytes(json_bytes(value))
    os.replace(temporary, path)


def write_new_json(relative: str, value: dict[str, Any]) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(json_bytes(value))


def unit(milestone: dict[str, Any], unit_id: str) -> dict[str, Any]:
    matches = [item for item in milestone.get("units", []) if item.get("id") == unit_id]
    if len(matches) != 1:
        raise PostSuccessReconciliationError(f"unit_identity:{unit_id}")
    return matches[0]


def main() -> int:
    for relative in (POST_FAILURE_REF, POST_RECONCILIATION_REF):
        if (ROOT / relative).exists():
            raise PostSuccessReconciliationError(f"record_collision:{relative}")

    success = load(SUCCESS_REF)
    if (
        success.get("status") != "reconciled_all_eight_promoted_container_pass"
        or success.get("assertions", {}).get("continuation_source_order") != list(CONTINUATION_SOURCE_IDS)
        or success.get("assertions", {}).get("promoted_container_verified_source_count") != 8
        or success.get("assertions", {}).get("m1_src_004_requested_by_continuation") is not False
        or success.get("assertions", {}).get("automatic_retry_performed") is not False
        or success.get("assertions", {}).get("credential_values_read_or_recorded") is not False
    ):
        raise PostSuccessReconciliationError("success_reconciliation_boundary")

    intake = load("contracts/m2-intake.json")
    assets = {
        item.get("extensions", {}).get("source_id"): item
        for item in intake.get("assets", [])
        if isinstance(item, dict)
    }
    if set(assets) != set(ALL_SOURCE_IDS):
        raise PostSuccessReconciliationError("intake_source_set")

    verified_sources: dict[str, Any] = {}
    for source_id in ALL_SOURCE_IDS:
        asset = assets[source_id]
        source_binding = success.get("bindings", {}).get("sources", {}).get(source_id, {})
        successful = [attempt for attempt in asset.get("attempts", []) if attempt.get("outcome") == "succeeded"]
        if asset.get("state") != "promoted" or len(successful) != 1:
            raise PostSuccessReconciliationError(f"promoted_attempt_state:{source_id}")
        if source_binding.get("attempt_id") != successful[0].get("attempt_id"):
            raise PostSuccessReconciliationError(f"attempt_binding:{source_id}")
        if successful[0].get("extensions", {}).get("credential_value_recorded") is not False:
            raise PostSuccessReconciliationError(f"credential_recording:{source_id}")
        if source_id in CONTINUATION_SOURCE_IDS and successful[0].get("extensions", {}).get("credential_reference") != "anonymous_pipe_single_use_memory_only":
            raise PostSuccessReconciliationError(f"continuation_credential_reference:{source_id}")

        destination = DATA_ROOT / "custody" / Path(*PurePosixPath(asset["destination_relative_path"]).parts)
        if not destination.is_file():
            raise PostSuccessReconciliationError(f"destination_missing:{source_id}")
        actual_size = destination.stat().st_size
        actual_sha256 = sha256_path(destination)
        if (
            actual_size != source_binding.get("promoted_size_bytes")
            or actual_sha256 != source_binding.get("promoted_sha256")
            or actual_size != asset.get("observed", {}).get("promoted_size_bytes")
            or actual_sha256 != asset.get("observed", {}).get("promoted_sha256")
        ):
            raise PostSuccessReconciliationError(f"promoted_byte_identity:{source_id}")

        receipt_ref = source_binding.get("container_receipt_ref")
        if not isinstance(receipt_ref, str):
            raise PostSuccessReconciliationError(f"container_receipt_ref:{source_id}")
        receipt = load(receipt_ref)
        if (
            receipt.get("status") != "pass_container_only"
            or receipt.get("source_id") != source_id
            or receipt.get("attempt_id") != successful[0].get("attempt_id")
            or sha256_ref(receipt_ref) != source_binding.get("container_receipt_sha256")
        ):
            raise PostSuccessReconciliationError(f"container_receipt:{source_id}")

        attempt_ref = asset.get("extensions", {}).get("successful_attempt_receipt")
        if not isinstance(attempt_ref, str) or sha256_ref(attempt_ref) != asset.get("extensions", {}).get("successful_attempt_receipt_sha256"):
            raise PostSuccessReconciliationError(f"attempt_receipt:{source_id}")
        verified_sources[source_id] = {
            "attempt_id": successful[0]["attempt_id"],
            "attempt_receipt_ref": attempt_ref,
            "attempt_receipt_sha256": sha256_ref(attempt_ref),
            "container_receipt_ref": receipt_ref,
            "container_receipt_sha256": sha256_ref(receipt_ref),
            "promoted_path": str(destination),
            "promoted_size_bytes": actual_size,
            "promoted_sha256": actual_sha256,
        }

    final_preflight = load("records/acquisition/sentinel-continuation-001-final-preflight.json")
    retained_failures: list[dict[str, Any]] = []
    for label in ("original_partial", "recovery_001_partial"):
        expected = final_preflight.get("current_state", {}).get("retained_and_recovered_bytes", {}).get(label, {})
        path = Path(str(expected.get("path", "")))
        if not path.is_file() or path.stat().st_size != expected.get("size_bytes") or sha256_path(path) != expected.get("sha256"):
            raise PostSuccessReconciliationError(f"retained_partial:{label}")
        retained_failures.append(
            {
                "label": label,
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_path(path),
                "classification": "retained_failed_partial_not_a_valid_product",
            }
        )

    terminal_root = DATA_ROOT / "derived/m2-sentinel-continuation-001-supervisor"
    terminal_candidates = sorted(terminal_root.glob("*/*-supervisor_succeeded.json"))
    matching_terminal: list[tuple[Path, dict[str, Any]]] = []
    for candidate in terminal_candidates:
        event = json.loads(candidate.read_text(encoding="utf-8"))
        if (
            event.get("continuation_id") == "nepal-m2-sentinel-continuation-001"
            and event.get("terminal_code") == "continuation_001_all_four_succeeded"
            and event.get("completed_source_ids") == list(CONTINUATION_SOURCE_IDS)
        ):
            matching_terminal.append((candidate, event))
    if len(matching_terminal) != 1:
        raise PostSuccessReconciliationError("terminal_event_identity")
    terminal_path, terminal_event = matching_terminal[0]

    intake["extensions"]["status"] = "active_eight_promoted_container_verified_materialization_review_required"
    intake_sha256 = hashlib.sha256(json_bytes(intake)).hexdigest()

    failure_record = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-SENTINEL-CONTINUATION-001-POSTSUCCESS-VALIDATION-ATTEMPT-001-FAILURE",
        "recorded_at_utc": now_utc(),
        "status": "failed_preserved_control_state_lag",
        "acquisition_outcome_affected": False,
        "observed_failures": [
            {
                "command": "python -m unittest tests.test_m2_sentinel_continuation_001 tests.test_m2_acquisition_progress",
                "exit_code": 1,
                "summary": "34 tests ran with two failures and one error because three tests still assumed the pre-continuation intake state.",
            },
            {
                "command": "python scripts/validate_m2_acquisition_progress.py",
                "exit_code": 1,
                "summary": "The validator rejected the approved anonymous-pipe credential reference for M1-SRC-005, M1-SRC-006, M1-SRC-008, and M1-SRC-010.",
            },
            {
                "command": "python scripts/check_project.py",
                "exit_code": 1,
                "summary": "The checker treated the continuation review bundle's mutable active-intake snapshot as a current hash after authorized acquisition changed it.",
            },
        ],
        "classification": "post_success_control_and_test_state_lag",
        "credential_values_read_or_recorded": False,
        "product_bytes_mutated": False,
        "pixel_processing_performed": False,
        "failure_preserved": True,
    }
    write_new_json(POST_FAILURE_REF, failure_record)

    post_reconciliation = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-SENTINEL-CONTINUATION-001-POSTSUCCESS-RECONCILIATION-001",
        "recorded_at_utc": now_utc(),
        "status": "reconciled_eight_promoted_container_verified_transfer_cohort_complete",
        "bindings": {
            "success_reconciliation_ref": SUCCESS_REF,
            "success_reconciliation_sha256": sha256_ref(SUCCESS_REF),
            "postsuccess_validation_failure_ref": POST_FAILURE_REF,
            "postsuccess_validation_failure_sha256": sha256_ref(POST_FAILURE_REF),
            "active_intake_ref": "contracts/m2-intake.json",
            "active_intake_sha256_after_status_reconciliation": intake_sha256,
            "terminal_event_path": str(terminal_path),
            "terminal_event_sha256": sha256_path(terminal_path),
            "terminal_supervisor_id": terminal_event["supervisor_id"],
            "sources": verified_sources,
        },
        "retained_failures": retained_failures,
        "assertions": {
            "promoted_source_count": 8,
            "container_pass_source_count": 8,
            "continuation_source_order": list(CONTINUATION_SOURCE_IDS),
            "continuation_attempt_count": 4,
            "automatic_retry_performed": False,
            "m1_src_004_requested_by_continuation": False,
            "credential_values_read_or_recorded": False,
            "archive_extraction_performed_by_continuation": False,
            "materialization_source_count": 3,
            "pixel_usability_established": False,
            "scientific_fitness_established": False,
        },
        "limitations": [
            "All eight product archives have verified custody and SAFE-container structure only.",
            "Five products remain unmaterialized, and no newly acquired raster pixels have been decoded.",
            "Usable AOI pixels, masks, registration, baselines, change, interpretation, and attribution remain separate gates.",
            "Both earlier incomplete M1-SRC-004 partials remain immutable failed evidence and are not valid products.",
        ],
        "next_gate": "M2-VERIFY: separately governed materialization and pixel-readiness review",
    }
    write_new_json(POST_RECONCILIATION_REF, post_reconciliation)
    post_sha256 = sha256_ref(POST_RECONCILIATION_REF)

    milestone = load("contracts/milestone-002.json")
    exit_201 = next(item for item in milestone["exit_conditions"] if item.get("id") == "EXIT-201-VERIFIED-CUSTODY")
    exit_201["status"] = "pass"
    exit_201["evidence"] = [SUCCESS_REF, POST_RECONCILIATION_REF]

    implementation = unit(milestone, "M2-SENTINEL-CONTINUATION-001-IMPLEMENTATION")
    implementation["status"] = "complete"
    implementation["gates"].update(
        {
            "public_ci": "pass",
            "public_commit": "68ac0484d598790cc8c47a8747a674b7d5d9de73",
            "public_ci_run_id": 33942997642,
            "publication_gate_ref": "records/acquisition/sentinel-continuation-001-publication-gate.json",
            "publication_gate_sha256": sha256_ref("records/acquisition/sentinel-continuation-001-publication-gate.json"),
            "activation_ref": "records/acquisition/sentinel-continuation-001-activation.json",
            "activation_sha256": sha256_ref("records/acquisition/sentinel-continuation-001-activation.json"),
            "final_preflight_ref": "records/acquisition/sentinel-continuation-001-final-preflight.json",
            "final_preflight_sha256": sha256_ref("records/acquisition/sentinel-continuation-001-final-preflight.json"),
            "terminal_code": "continuation_001_all_four_succeeded",
            "success_reconciliation_ref": SUCCESS_REF,
            "success_reconciliation_sha256": sha256_ref(SUCCESS_REF),
            "postsuccess_reconciliation_ref": POST_RECONCILIATION_REF,
            "postsuccess_reconciliation_sha256": post_sha256,
            "credential_entry_permitted_now": False,
            "payload_request_permitted_now": False,
        }
    )
    implementation["exit_condition_delta"] = {
        "expected": [],
        "observed": [],
        "decision_value": "success",
        "rationale": "The corrected implementation passed public CI before activation, final preflight, the single credential handoff, and the exact four-source terminal success.",
    }

    acquire = unit(milestone, "M2-ACQUIRE")
    acquire["status"] = "complete"
    acquire["disposition"] = "complete_exact_eight_promoted_container_verified"
    acquire["gates"].update(
        {
            "continuation_publication_gate": "pass",
            "continuation_publication_commit": "68ac0484d598790cc8c47a8747a674b7d5d9de73",
            "continuation_public_ci_run_id": 33942997642,
            "continuation_transfer_authorized_now": False,
            "continuation_authorized_now": False,
            "continuation_supervisor_status": "succeeded_all_four",
            "continuation_attempt_count": 4,
            "continuation_payload_request_count": 4,
            "promoted_source_count": 8,
            "container_verified_source_count": 8,
            "success_reconciliation_ref": SUCCESS_REF,
            "success_reconciliation_sha256": sha256_ref(SUCCESS_REF),
            "postsuccess_reconciliation_ref": POST_RECONCILIATION_REF,
            "postsuccess_reconciliation_sha256": post_sha256,
        }
    )
    acquire["exit_condition_delta"] = {
        "expected": ["EXIT-201-VERIFIED-CUSTODY"],
        "observed": ["EXIT-201-VERIFIED-CUSTODY"],
        "decision_value": "success",
        "rationale": "All eight exact approved products are promoted and container-verified; failed M1-SRC-004 partials remain preserved separately.",
    }
    acquire["next_dependency"] = "M2-VERIFY"

    verify = unit(milestone, "M2-VERIFY")
    verify["status"] = "in_progress"
    verify["outputs"] = [
        "eight passing container-only receipts",
        "two retained M1-SRC-004 failed partial identities",
        "records/acquisition/sentinel-continuation-001-postsuccess-reconciliation.json",
    ]
    verify["gates"] = {
        "container_verified_count": 8,
        "retained_failed_partial_count": 2,
        "authorized_unattempted_count": 0,
        "m1_src_004_satisfied_by_recovery_002": True,
        "continuation_status": "succeeded_all_four",
        "materialized_source_count": 3,
        "materialization_and_pixel_readiness": "separately_gated_pending",
    }
    verify["disposition"] = "container_only_complete_materialization_and_pixel_readiness_pending"
    verify["exit_condition_delta"] = {
        "expected": ["EXIT-201-VERIFIED-CUSTODY", "EXIT-202-PIXEL-AND-RIGHTS-QA"],
        "observed": ["EXIT-201-VERIFIED-CUSTODY"],
        "decision_value": "partial_progress",
        "rationale": "Transfer and container verification are complete for all eight products; five materializations and all real pixel, mask, AOI, and registration checks remain gated.",
    }

    orbit_acquire = unit(milestone, "M2-ORBIT-ACQUIRE")
    orbit_acquire["gates"]["matching_sentinel_promoted_and_verified"] = "all_bound_sentinel_promoted_and_container_verified_but_full_m2_verify_incomplete"
    orbit_acquire["gates"]["milestone_dependency_m2_verify"] = "in_progress_not_satisfied"

    stale_handoff = milestone["handoff"].get("do_not_carry_forward", [])
    milestone["handoff"]["current_checkpoint"] = "M2-VERIFY"
    milestone["handoff"]["next_action"] = POST_CONTAINER_NEXT_ACTION
    milestone["handoff"]["do_not_carry_forward"] = [
        item
        for item in stale_handoff
        if not item.startswith("Four exact Sentinel products")
        and not item.startswith("The recovery-002 supervisor stopped")
    ] + [
        "All eight exact Sentinel products are promoted and container-verified; this establishes archive custody and structure only, not usable pixels or scientific fitness.",
        "The recovery-002 supervisor failure remains historical evidence; continuation-001 later succeeded under a separate approved identity without retrying or requesting M1-SRC-004.",
    ]

    profile = load("records/project-control-profile.json")
    profile["current_checkpoint"] = {
        "checkpoint_id": "M2-VERIFY",
        "expected_branch": "main",
        "expected_head": None,
        "next_action": POST_CONTAINER_NEXT_ACTION,
    }

    goal = load("records/long-term-goal.json")
    goal["current_checkpoint"] = "M2-VERIFY"

    replace_json("contracts/m2-intake.json", intake)
    replace_json("contracts/milestone-002.json", milestone)
    replace_json("records/project-control-profile.json", profile)
    replace_json("records/long-term-goal.json", goal)

    print(
        json.dumps(
            {
                "status": "reconciled_postsuccess_controls",
                "postsuccess_reconciliation_ref": POST_RECONCILIATION_REF,
                "postsuccess_reconciliation_sha256": post_sha256,
                "active_intake_sha256": sha256_ref("contracts/m2-intake.json"),
                "checkpoint": "M2-VERIFY",
                "pixel_processing_released": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
