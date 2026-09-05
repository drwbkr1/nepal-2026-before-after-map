#!/usr/bin/env python3
"""Validate append-only M2 acquisition progress without reading secrets."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INITIAL_ACTIVE_INTAKE_SHA256 = "a2816e9244a0141bf797c3a3fba00e2d492e272fb4886e7ff9aff58ab3cb716c"
INITIAL_SNAPSHOT_REF = "records/acquisition/active-intake-initial-snapshot.json"
TOKEN_REFERENCE = "CDSE_ACCESS_TOKEN"
RECOVERY_TOKEN_REFERENCE = "anonymous_pipe_single_use_memory_only"
CONTINUATION_SOURCE_IDS = {"M1-SRC-005", "M1-SRC-006", "M1-SRC-008", "M1-SRC-010"}
MUTABLE_STATUS_VALUES = {
    "active_four_promoted_four_authorized_continuation_review_required",
    "active_eight_promoted_container_verified_materialization_review_required",
}
HEX64 = re.compile(r"[0-9a-f]{64}")
UTC_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
STATIC_ASSET_KEYS = (
    "asset_id",
    "source",
    "destination_relative_path",
    "staging_relative_path",
    "expected",
    "superseded_by",
)
PROGRESS_EXTENSION_KEYS = {
    "successful_attempt_receipt",
    "successful_attempt_receipt_sha256",
    "provider_md5_verified",
    "provider_blake3_locally_verified",
    "container_receipt",
    "container_receipt_sha256",
    "satisfied_by_recovery_002",
    "recovery_002_contract_ref",
    "recovery_002_contract_sha256_at_recovery_success",
    "retained_failed_attempt_count",
}


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} is not a JSON object")
    return value


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_repository_receipt(root: Path, value: str) -> Path | None:
    posix = PurePosixPath(value)
    if (
        posix.is_absolute()
        or any(part in {"", ".", ".."} for part in value.split("/"))
        or posix.parent not in {
            PurePosixPath("records/acquisition/attempts"),
            PurePosixPath("records/acquisition/recovery-attempts"),
        }
        or posix.suffix.casefold() != ".json"
    ):
        return None
    return root.joinpath(*posix.parts)


def reparse_point(path: Path) -> bool:
    if path.is_symlink():
        return True
    attributes = getattr(path.lstat(), "st_file_attributes", 0)
    return bool(attributes & 0x400)


def checksum_map(values: list[dict[str, Any]]) -> dict[str, str]:
    return {
        str(item.get("Algorithm", "")).upper(): str(item.get("Value", "")).casefold()
        for item in values
    }


def null_observations(value: Any) -> bool:
    return isinstance(value, dict) and value == {
        "staged_sha256": None,
        "staged_size_bytes": None,
        "promoted_sha256": None,
        "promoted_size_bytes": None,
    }


def forbidden_secret_keys(value: Any, *, path: str = "root") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).casefold()
            safe_reference_or_boolean_keys = {
                "authorization_ref",
                "credential_reference",
                "credential_value_recorded",
                "credential_values_read_or_recorded",
                "secret_policy",
            }
            if lowered not in safe_reference_or_boolean_keys and any(
                marker in lowered
                for marker in ("token", "password", "secret", "authorization_header", "credential_value")
            ):
                errors.append(f"forbidden secret-bearing key at {path}.{key}")
            errors.extend(forbidden_secret_keys(item, path=f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(forbidden_secret_keys(item, path=f"{path}[{index}]"))
    return errors


def validate_attempt(
    *,
    asset: dict[str, Any],
    source_id: str,
    root: Path,
) -> tuple[list[str], dict[str, Any] | None]:
    errors: list[str] = []
    attempts = asset.get("attempts")
    recovery_promoted = asset.get("extensions", {}).get("satisfied_by_recovery_002") is True
    expected_count = 2 if recovery_promoted else 1
    if not isinstance(attempts, list) or len(attempts) != expected_count:
        return [f"{source_id} must have exactly {expected_count} append-only attempt(s) for its current route"], None
    for historical in attempts[:-1]:
        if (
            not isinstance(historical, dict)
            or historical.get("outcome") != "failed"
            or not isinstance(historical.get("completed_at"), str)
            or not UTC_TIMESTAMP.fullmatch(historical["completed_at"])
        ):
            errors.append(f"{source_id} historical failed attempt differs")
    attempt = attempts[-1]
    if not isinstance(attempt, dict):
        return [f"{source_id} current attempt is not an object"], None
    attempt_id = attempt.get("attempt_id")
    if not isinstance(attempt_id, str) or not attempt_id.startswith(f"{asset['asset_id']}-"):
        errors.append(f"{source_id} attempt ID is outside its asset namespace")
    if not isinstance(attempt.get("started_at"), str) or not UTC_TIMESTAMP.fullmatch(attempt["started_at"]):
        errors.append(f"{source_id} attempt start time is invalid")
    extensions = attempt.get("extensions", {})
    if extensions.get("source_id") != source_id:
        errors.append(f"{source_id} attempt source identity differs")
    expected_reference = (
        RECOVERY_TOKEN_REFERENCE
        if recovery_promoted or source_id in CONTINUATION_SOURCE_IDS
        else TOKEN_REFERENCE
    )
    if extensions.get("credential_reference") != expected_reference:
        errors.append(f"{source_id} attempt credential reference differs")
    if extensions.get("credential_value_recorded") is not False:
        errors.append(f"{source_id} attempt records or ambiguously handles a credential value")
    if recovery_promoted:
        if extensions.get("restart_offset_bytes") != 0 or extensions.get("range_or_resume_used") is not False:
            errors.append(f"{source_id} recovery attempt invents transfer resumption")
    elif extensions.get("resume") is not False:
        errors.append(f"{source_id} attempt invents transfer resumption")
    if not isinstance(extensions.get("catalog_response_sha256"), str) or not HEX64.fullmatch(extensions["catalog_response_sha256"]):
        errors.append(f"{source_id} attempt catalog response identity is invalid")
    started_event = extensions.get("external_started_event")
    if not isinstance(started_event, str) or PureWindowsPath(started_event).name != f"{attempt_id}-started.json":
        errors.append(f"{source_id} external started-event reference differs")
    state = asset.get("state")
    expected_outcome = {"staging": "started", "failed": "failed", "promoted": "succeeded"}.get(state)
    if attempt.get("outcome") != expected_outcome:
        errors.append(f"{source_id} attempt outcome does not match state {state}")
    completed_at = attempt.get("completed_at")
    if state == "staging":
        if completed_at is not None:
            errors.append(f"{source_id} staging attempt is already completed")
    elif not isinstance(completed_at, str) or not UTC_TIMESTAMP.fullmatch(completed_at):
        errors.append(f"{source_id} terminal attempt completion time is invalid")
    receipt: dict[str, Any] | None = None
    if state in {"failed", "promoted"} and isinstance(attempt_id, str):
        if state == "promoted":
            receipt_ref = asset.get("extensions", {}).get("successful_attempt_receipt")
        else:
            receipt_ref = f"records/acquisition/attempts/{attempt_id}.json"
        if not isinstance(receipt_ref, str):
            errors.append(f"{source_id} terminal receipt reference is missing")
        else:
            receipt_path = safe_repository_receipt(root, receipt_ref)
            if receipt_path is None or not receipt_path.is_file():
                errors.append(f"{source_id} terminal receipt is missing or outside the receipt root")
            else:
                try:
                    receipt = load(receipt_path)
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    errors.append(f"{source_id} terminal receipt cannot be read: {type(exc).__name__}")
                else:
                    if receipt.get("attempt_id") != attempt_id or receipt.get("source_id") != source_id:
                        errors.append(f"{source_id} terminal receipt identity differs")
                    if receipt.get("credential_value_recorded") is not False:
                        errors.append(f"{source_id} terminal receipt records or ambiguously handles a credential value")
    return errors, receipt


def validate_progress(
    current: dict[str, Any],
    baseline: dict[str, Any],
    plan: dict[str, Any],
    *,
    root: Path,
    verify_external: bool = False,
) -> dict[str, Any]:
    errors = forbidden_secret_keys(current)
    current_root = {key: value for key, value in current.items() if key != "assets"}
    baseline_root = {key: value for key, value in baseline.items() if key != "assets"}
    current_status = current_root.get("extensions", {}).get("status")
    if current_status in MUTABLE_STATUS_VALUES:
        current_root = json.loads(json.dumps(current_root))
        current_root["extensions"]["status"] = baseline_root.get("extensions", {}).get("status")
    if current_root != baseline_root:
        errors.append("active intake root controls differ from the immutable initial snapshot")
    baseline_assets = baseline.get("assets", [])
    current_assets = current.get("assets", [])
    if not isinstance(baseline_assets, list) or not isinstance(current_assets, list) or len(baseline_assets) != 8 or len(current_assets) != 8:
        errors.append("active and initial intake must each contain exactly eight assets")
        return {"status": "fail", "errors": errors, "state_counts": {}}
    baseline_by_id = {item.get("asset_id"): item for item in baseline_assets if isinstance(item, dict)}
    current_by_id = {item.get("asset_id"): item for item in current_assets if isinstance(item, dict)}
    plan_by_source = {item.get("source_id"): item for item in plan.get("records", []) if isinstance(item, dict)}
    if len(baseline_by_id) != 8 or set(current_by_id) != set(baseline_by_id) or len(plan_by_source) != 8:
        errors.append("active intake, initial snapshot, or approved plan has missing or duplicate identities")
        return {"status": "fail", "errors": errors, "state_counts": {}}

    attempt_ids: list[str] = []
    state_counts: Counter[str] = Counter()
    external_checked = False
    data_root = root.parent / f"{root.name}-data"
    custody_root = data_root / "custody"
    staging_root = data_root / ".intake-staging" / current["intake_id"]
    if verify_external:
        external_checked = True
        for path, label in ((data_root, "external data"), (custody_root, "custody"), (staging_root, "staging")):
            if not path.is_dir():
                errors.append(f"{label} root is missing")
            elif reparse_point(path):
                errors.append(f"{label} root is a reparse point")

    for asset_id in sorted(baseline_by_id):
        baseline_asset = baseline_by_id[asset_id]
        asset = current_by_id[asset_id]
        source_id = baseline_asset.get("extensions", {}).get("source_id")
        plan_record = plan_by_source.get(source_id)
        if not isinstance(source_id, str) or plan_record is None:
            errors.append(f"{asset_id} does not map exactly to the approved plan")
            continue
        for key in STATIC_ASSET_KEYS:
            if asset.get(key) != baseline_asset.get(key):
                errors.append(f"{source_id} immutable {key} differs from the initial snapshot")
        baseline_extensions = baseline_asset.get("extensions", {})
        extensions = asset.get("extensions", {})
        if not isinstance(extensions, dict):
            errors.append(f"{source_id} extensions are invalid")
            continue
        for key, expected in baseline_extensions.items():
            if extensions.get(key) != expected:
                errors.append(f"{source_id} immutable extension {key} differs")
        unexpected_extension_keys = set(extensions) - set(baseline_extensions) - PROGRESS_EXTENSION_KEYS
        if unexpected_extension_keys:
            errors.append(f"{source_id} has unexpected progress extensions: {sorted(unexpected_extension_keys)}")
        if (
            extensions.get("exact_product_id") != plan_record.get("exact_product_id")
            or extensions.get("provider_product_id") != plan_record.get("provider_product_id")
            or extensions.get("catalog_content_length_bytes") != plan_record.get("catalog_content_length_bytes")
            or extensions.get("provider_checksums") != plan_record.get("provider_checksums")
            or extensions.get("sensor_route") != plan_record.get("sensor_route")
            or extensions.get("event_role") != plan_record.get("event_role")
        ):
            errors.append(f"{source_id} differs from the approved product identity")

        state = asset.get("state")
        state_counts[str(state)] += 1
        if state not in {"authorized", "staging", "failed", "promoted"}:
            errors.append(f"{source_id} has unsupported state {state}")
            continue
        receipt: dict[str, Any] | None = None
        if state == "authorized":
            if asset.get("attempts") != [] or asset.get("failure") is not None or not null_observations(asset.get("observed")):
                errors.append(f"{source_id} authorized state contains attempt results")
            if set(extensions) != set(baseline_extensions):
                errors.append(f"{source_id} authorized state contains terminal extensions")
        else:
            attempt_errors, receipt = validate_attempt(asset=asset, source_id=source_id, root=root)
            errors.extend(attempt_errors)
            attempts = asset.get("attempts", [])
            for attempt in attempts:
                if isinstance(attempt, dict) and isinstance(attempt.get("attempt_id"), str):
                    attempt_ids.append(attempt["attempt_id"])

        if state == "staging":
            if asset.get("failure") is not None or not null_observations(asset.get("observed")):
                errors.append(f"{source_id} staging state contains terminal results")
        elif state == "failed":
            failure = asset.get("failure")
            if not isinstance(failure, dict) or receipt is None:
                errors.append(f"{source_id} failed state lacks matching failure evidence")
            else:
                if failure.get("code") != receipt.get("failure_code") or failure.get("recorded_at") != receipt.get("completed_at"):
                    errors.append(f"{source_id} failure state and terminal receipt differ")
                if receipt.get("event") != "transfer_failed" or receipt.get("retry_automatically_authorized") is not False:
                    errors.append(f"{source_id} failed receipt semantics differ")
            if not null_observations(asset.get("observed")) or set(extensions) != set(baseline_extensions):
                errors.append(f"{source_id} failed state invents promoted identity")
        elif state == "promoted":
            observed = asset.get("observed", {})
            expected_size = extensions.get("catalog_content_length_bytes")
            if (
                not isinstance(observed, dict)
                or not isinstance(observed.get("staged_sha256"), str)
                or not HEX64.fullmatch(observed["staged_sha256"])
                or observed.get("staged_sha256") != observed.get("promoted_sha256")
                or observed.get("staged_size_bytes") != expected_size
                or observed.get("promoted_size_bytes") != expected_size
            ):
                errors.append(f"{source_id} promoted byte identity is invalid")
            receipt_ref = extensions.get("successful_attempt_receipt")
            receipt_path = safe_repository_receipt(root, receipt_ref) if isinstance(receipt_ref, str) else None
            if receipt_path is None or not receipt_path.is_file() or extensions.get("successful_attempt_receipt_sha256") != sha256_path(receipt_path):
                errors.append(f"{source_id} successful receipt binding differs")
            if extensions.get("provider_md5_verified") is not True or extensions.get("provider_blake3_locally_verified") is not False:
                errors.append(f"{source_id} provider checksum claims differ")
            providers = checksum_map(extensions.get("provider_checksums", []))
            if receipt is None:
                errors.append(f"{source_id} promoted state lacks a readable successful receipt")
            elif (
                receipt.get("event") not in {"transfer_succeeded", "recovery_002_transfer_succeeded"}
                or receipt.get("local_sha256") != observed.get("promoted_sha256")
                or receipt.get("local_size_bytes") != observed.get("promoted_size_bytes")
                or receipt.get("provider_md5") != providers.get("MD5")
                or receipt.get("provider_md5_match") is not True
                or receipt.get("provider_blake3_metadata") != providers.get("BLAKE3")
                or receipt.get("provider_blake3_locally_verified") is not False
            ):
                errors.append(f"{source_id} successful receipt and promoted identity differ")

        if verify_external and custody_root.is_dir() and staging_root.is_dir():
            destination = custody_root.joinpath(*PurePosixPath(asset["destination_relative_path"]).parts)
            staging = staging_root.joinpath(*PurePosixPath(asset["staging_relative_path"]).parts)
            try:
                destination.resolve(strict=False).relative_to(custody_root.resolve(strict=True))
                staging.resolve(strict=False).relative_to(staging_root.resolve(strict=True))
            except (FileNotFoundError, ValueError):
                errors.append(f"{source_id} external path escapes its controlled root")
                continue
            if state == "authorized" and (destination.exists() or staging.exists()):
                errors.append(f"{source_id} authorized state collides with external bytes")
            elif state == "staging" and (not staging.is_file() or destination.exists()):
                errors.append(f"{source_id} staging state does not match external paths")
            elif state == "failed":
                partial = receipt.get("partial_bytes_preserved") if receipt else None
                if destination.exists() or not isinstance(partial, int) or partial < 0:
                    errors.append(f"{source_id} failed state has invalid external disposition")
                elif partial > 0 and (not staging.is_file() or staging.stat().st_size != partial):
                    errors.append(f"{source_id} retained partial bytes differ from the failure receipt")
                elif partial == 0 and staging.exists() and (not staging.is_file() or staging.stat().st_size != 0):
                    errors.append(f"{source_id} zero-byte failure has unexpected staging content")
            elif state == "promoted":
                observed = asset.get("observed", {})
                recovered = extensions.get("satisfied_by_recovery_002") is True
                retained_original = recovered and staging.is_file() and staging.stat().st_size == 561_593_598 and sha256_path(staging) == "299b2d07ccb58747cce43ae3b18e6d25c1c6d72a5653831b50a44ca72677ea66"
                if (staging.exists() and not retained_original) or not destination.is_file():
                    errors.append(f"{source_id} promoted state does not match external paths")
                elif destination.stat().st_size != observed.get("promoted_size_bytes") or sha256_path(destination) != observed.get("promoted_sha256"):
                    errors.append(f"{source_id} promoted external bytes differ from the intake identity")

    if len(attempt_ids) != len(set(attempt_ids)):
        errors.append("attempt IDs are not unique across the active intake")
    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "state_counts": dict(sorted(state_counts.items())),
        "asset_count": len(current_assets),
        "attempt_count": len(attempt_ids),
        "external_state_verified": external_checked,
        "credential_values_read": False,
        "files_mutated": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--active-intake", type=Path, default=Path("contracts/m2-intake.json"))
    parser.add_argument("--initial-snapshot", type=Path, default=Path(INITIAL_SNAPSHOT_REF))
    parser.add_argument("--acquisition-plan", type=Path, default=Path("records/acquisition-plan.json"))
    parser.add_argument("--verify-external", action="store_true")
    args = parser.parse_args()
    active_path = args.active_intake if args.active_intake.is_absolute() else ROOT / args.active_intake
    baseline_path = args.initial_snapshot if args.initial_snapshot.is_absolute() else ROOT / args.initial_snapshot
    plan_path = args.acquisition_plan if args.acquisition_plan.is_absolute() else ROOT / args.acquisition_plan
    if sha256_path(baseline_path) != INITIAL_ACTIVE_INTAKE_SHA256:
        result = {
            "status": "fail",
            "errors": ["immutable initial active-intake snapshot hash differs"],
            "credential_values_read": False,
            "files_mutated": False,
        }
    else:
        result = validate_progress(
            load(active_path),
            load(baseline_path),
            load(plan_path),
            root=ROOT,
            verify_external=args.verify_external,
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
