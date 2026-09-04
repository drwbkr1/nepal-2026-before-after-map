#!/usr/bin/env python3
"""Pure validation helpers for the approved M1-SRC-004 recovery."""

from __future__ import annotations

from typing import Any


EXPECTED_SOURCE_ID = "M1-SRC-004"
EXPECTED_ASSET_ID = "m1-src-004-recovery-001"
EXPECTED_FAILED_ATTEMPT_ID = "m1-src-004-20260904t043930z-ac125c11"
EXPECTED_FAILURE_CODE = "transferred_size_mismatch"
EXPECTED_PARTIAL_BYTES = 561_593_598
EXPECTED_PARTIAL_SHA256 = "299b2d07ccb58747cce43ae3b18e6d25c1c6d72a5653831b50a44ca72677ea66"
EXPECTED_DESTINATION = (
    "products/m1-src-004/"
    "S1D_IW_GRDH_1SDV_20260828T122116_20260828T122141_004326_007FA4_C523.SAFE.zip"
)
EXPECTED_RECOVERY_STAGING = (
    "m1-src-004-recovery-001/"
    "S1D_IW_GRDH_1SDV_20260828T122116_20260828T122141_004326_007FA4_C523.SAFE.zip.part"
)


class RecoveryControlError(RuntimeError):
    """A recovery-specific fail-closed guard rejected the operation."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def require_exact_recovery_contract(contract: dict[str, Any]) -> dict[str, Any]:
    if contract.get("intake_id") != "nepal-m2-sentinel-recovery-001":
        raise RecoveryControlError("recovery_contract_identity_drift")
    if (
        contract.get("collision_policy") != "fail"
        or contract.get("promotion_mode") != "atomic-no-replace"
        or contract.get("secret_policy") != "references-only"
    ):
        raise RecoveryControlError("recovery_contract_safety_policy_drift")
    if contract.get("custody_root") != "nepal-2026-before-after-map-data/custody":
        raise RecoveryControlError("recovery_custody_root_drift")
    if contract.get("staging_root") != (
        "nepal-2026-before-after-map-data/.intake-staging/nepal-m2-sentinel-recovery-001"
    ):
        raise RecoveryControlError("recovery_staging_root_drift")
    assets = contract.get("assets")
    if not isinstance(assets, list) or len(assets) != 1:
        raise RecoveryControlError("recovery_asset_count_drift")
    asset = assets[0]
    if (
        asset.get("asset_id") != EXPECTED_ASSET_ID
        or asset.get("extensions", {}).get("source_id") != EXPECTED_SOURCE_ID
        or asset.get("destination_relative_path") != EXPECTED_DESTINATION
        or asset.get("staging_relative_path") != EXPECTED_RECOVERY_STAGING
    ):
        raise RecoveryControlError("recovery_asset_identity_or_path_drift")
    if asset["staging_relative_path"].casefold().startswith("m1-src-004/"):
        raise RecoveryControlError("failed_staging_namespace_reused")
    if asset.get("state") not in {"authorized", "staging", "promoted", "failed"}:
        raise RecoveryControlError("recovery_asset_state_invalid")
    extensions = contract.get("extensions", {})
    if (
        extensions.get("restart_offset_bytes") != 0
        or extensions.get("resume_partial") is not False
        or extensions.get("delete_or_modify_failed_partial") is not False
        or extensions.get("reuse_failed_staging_path") is not False
        or extensions.get("maximum_real_transfer_attempts") != 1
    ):
        raise RecoveryControlError("recovery_method_boundary_drift")
    return asset


def require_original_failure(
    active_intake: dict[str, Any],
    failed_receipt: dict[str, Any],
    *,
    partial_size: int,
    partial_sha256: str,
) -> dict[str, Any]:
    matches = [
        asset
        for asset in active_intake.get("assets", [])
        if asset.get("extensions", {}).get("source_id") == EXPECTED_SOURCE_ID
    ]
    if len(matches) != 1:
        raise RecoveryControlError("original_failed_asset_identity_drift")
    asset = matches[0]
    attempts = asset.get("attempts", [])
    if (
        asset.get("state") != "failed"
        or asset.get("failure", {}).get("code") != EXPECTED_FAILURE_CODE
        or len(attempts) != 1
        or attempts[0].get("attempt_id") != EXPECTED_FAILED_ATTEMPT_ID
        or attempts[0].get("outcome") != "failed"
    ):
        raise RecoveryControlError("original_failed_asset_history_drift")
    if (
        failed_receipt.get("event") != "transfer_failed"
        or failed_receipt.get("attempt_id") != EXPECTED_FAILED_ATTEMPT_ID
        or failed_receipt.get("failure_code") != EXPECTED_FAILURE_CODE
        or failed_receipt.get("partial_bytes_preserved") != EXPECTED_PARTIAL_BYTES
        or failed_receipt.get("retry_automatically_authorized") is not False
    ):
        raise RecoveryControlError("original_failure_receipt_drift")
    if partial_size != EXPECTED_PARTIAL_BYTES or partial_sha256 != EXPECTED_PARTIAL_SHA256:
        raise RecoveryControlError("retained_partial_identity_drift")
    return asset


def require_fresh_authorized_attempt(asset: dict[str, Any]) -> None:
    if asset.get("state") != "authorized" or asset.get("attempts") != []:
        raise RecoveryControlError("recovery_asset_not_fresh_authorized")


def set_attempt_terminal(
    contract: dict[str, Any],
    attempt_id: str,
    completed_at: str,
    *,
    outcome: str,
    failure_code: str | None,
) -> dict[str, Any]:
    asset = require_exact_recovery_contract(contract)
    attempt = next((item for item in asset["attempts"] if item.get("attempt_id") == attempt_id), None)
    if attempt is None:
        raise RecoveryControlError("recovery_attempt_identity_missing")
    attempt["completed_at"] = completed_at
    attempt["outcome"] = outcome
    if outcome == "failed":
        asset["state"] = "failed"
        asset["failure"] = {"code": failure_code, "recorded_at": completed_at}
    elif outcome == "succeeded":
        asset["state"] = "promoted"
        asset["failure"] = None
    else:
        raise RecoveryControlError("recovery_terminal_outcome_invalid")
    return asset
