#!/usr/bin/env python3
"""Pure controls for the approved orbit continuation-001 route."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, Callable, Mapping, Sequence

from m2_transfer_core import TransferControlError


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent.resolve()
DATA_ROOT = PROJECT_ROOT / "nepal-2026-before-after-map-data"

CONTINUATION_ID = "nepal-m2-orbit-continuation-001"
SOURCE_ORDER = ("M2-ORB-002", "M2-ORB-003", "M2-ORB-004")
PRESERVED_SOURCE_ID = "M2-ORB-001"
PRESERVED_ORBIT_SHA256 = "a72c93e500a1c09b62b4cd31889837c9d57ccc41542b16397ff9f2c0fccba3f4"
PRESERVED_ORBIT_SIZE = 639_533
PRESERVED_STAGING_RELATIVE = (
    ".intake-staging/nepal-m2-orbit-recovery-003/m2-orb-001-recovery-002/"
    "S1D_OPER_AUX_RESORB_OPOD_20260816T143208_V20260816T103526_20260816T140956.EOF.part"
)

EXPECTED_BUNDLE_SHA256 = "f4712a3ffd65eb9cbd1955ccd854423607a384800931004ae10da174a4880dd6"
EXPECTED_PROPOSAL_SHA256 = "01a2c3521625f8f219909b8d69476dbc3355292ff12e59fd0917ed52bc371e8b"
EXPECTED_RESPONSE_SHA256 = "692f9ef93a7fd43adc76001cc0c6b5fd5dd5738ad840f91bcdb42d446ace0f04"
EXPECTED_RECONCILIATION_SHA256 = "11e29c1e6a259201b745b802f59219234e4bfec2433f1caf909f2202e3b9f0fa"
EXPECTED_APPROVAL_SHA256 = "66c40db57082ed29c1dfd3e00a163ab072fe9f14b8e0ed4455df188673de84ba"

APPROVAL_REF = "records/source-gates/m2-orbit-continuation-001-approval.json"
RECONCILIATION_REF = "records/source-gates/m2-orbit-continuation-001-review-reconciliation.json"
PROPOSAL_REF = "contracts/milestone-002-orbit-continuation-001-proposal.json"
BUNDLE_REF = "reviews/m2-orbit-continuation-001/review-bundle.json"
ACTIVE_INTAKE_REF = "contracts/m2-orbit-intake.json"
ACTIVE_VERIFICATION_REF = "contracts/m2-orbit-offline-verification.json"
MANIFEST_REF = "records/source-gates/m2-orbit-candidate-manifest.json"
SENTINEL_INTAKE_REF = "contracts/m2-intake.json"
RADAR_READINESS_REF = "records/readiness/m2-radar-source-readiness-001.json"
PRESERVED_RESULT_REF = "records/acquisition/m2-orbit-osv-precision-amendment-001-local-validation.json"
PRESERVED_TERMINAL_REF = "records/readiness/m2-orbit-osv-precision-amendment-001-terminal-reconciliation.json"
CONTRACT_REF = "contracts/m2-orbit-continuation-001.json"
IMPLEMENTATION_READINESS_REF = "records/readiness/m2-orbit-continuation-001-implementation-readiness-002.json"
PUBLICATION_GATE_REF = "records/readiness/m2-orbit-continuation-001-publication-gate.json"
ACTIVATION_REF = "records/readiness/m2-orbit-continuation-001-activation.json"
FINAL_PREFLIGHT_REF = "records/readiness/m2-orbit-continuation-001-final-preflight.json"
CONTROL_RECONCILIATION_REF = "records/readiness/m2-orbit-continuation-001-control-reconciliation.json"
SUCCESS_RECONCILIATION_REF = "records/acquisition/m2-orbit-continuation-001-success-reconciliation.json"

SECRET_REFERENCE = "anonymous_pipe_single_use_memory_only"
MAX_SECRET_BYTES = 16_384
SAFE_CODE = re.compile(r"[a-z0-9_]{3,96}")
UTC_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


class OrbitContinuation001Error(RuntimeError):
    """A continuation-001 fail-closed guard rejected the operation."""

    def __init__(self, code: str):
        if SAFE_CODE.fullmatch(code) is None:
            code = "invalid_control_failure_code"
        super().__init__(code)
        self.code = code


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise OrbitContinuation001Error("control_root_not_object")
    return value


def write_new_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(canonical_bytes(value))
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise OrbitContinuation001Error("output_collision") from exc


def is_reparse_point(path: Path) -> bool:
    attributes = getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0)
    return path.is_symlink() or bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def require_safe_child(root: Path, candidate: Path) -> Path:
    resolved_root = root.resolve(strict=True)
    resolved_candidate = candidate.resolve(strict=False)
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise OrbitContinuation001Error("path_outside_controlled_root") from exc
    if resolved_candidate == resolved_root:
        raise OrbitContinuation001Error("path_must_be_child")
    current = resolved_candidate.parent
    while True:
        if current.exists() and is_reparse_point(current):
            raise OrbitContinuation001Error("reparse_point_in_path")
        if current == resolved_root:
            break
        if current == current.parent:
            raise OrbitContinuation001Error("path_ancestor_escape")
        current = current.parent
    return resolved_candidate


def validate_approval(approval: Mapping[str, Any], reconciliation: Mapping[str, Any]) -> None:
    if (
        approval.get("status") != "approved_exact_bounded_fixed_order_orbit_continuation_only"
        or approval.get("review_bundle_manifest_sha256") != EXPECTED_BUNDLE_SHA256
        or approval.get("continuation_proposal_sha256") != EXPECTED_PROPOSAL_SHA256
        or approval.get("locked_response_sha256") != EXPECTED_RESPONSE_SHA256
        or approval.get("review_reconciliation_sha256") != EXPECTED_RECONCILIATION_SHA256
        or approval.get("source_ids_in_exact_order") != list(SOURCE_ORDER)
        or approval.get("maximum_owner_handoffs") != 1
        or approval.get("maximum_real_attempts_per_source") != 1
        or approval.get("stop_on_first_failure") is not True
        or approval.get("maximum_osv_endpoint_tolerance_seconds") != 1.0
        or approval.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}
        or approval.get("human_decisions_fabricated") is not False
        or reconciliation.get("status") != "reconciled_exact_human_response"
        or reconciliation.get("response_sha256") != EXPECTED_RESPONSE_SHA256
        or reconciliation.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}
        or reconciliation.get("human_decisions_fabricated") is not False
    ):
        raise OrbitContinuation001Error("continuation_001_approval_or_reconciliation_drift")


def validate_approval_files() -> None:
    bindings = {
        ROOT / BUNDLE_REF: EXPECTED_BUNDLE_SHA256,
        ROOT / PROPOSAL_REF: EXPECTED_PROPOSAL_SHA256,
        ROOT / RECONCILIATION_REF: EXPECTED_RECONCILIATION_SHA256,
        ROOT / APPROVAL_REF: EXPECTED_APPROVAL_SHA256,
    }
    if any(not path.is_file() or sha256_file(path) != digest for path, digest in bindings.items()):
        raise OrbitContinuation001Error("continuation_001_authority_byte_drift")
    validate_approval(load_object(ROOT / APPROVAL_REF), load_object(ROOT / RECONCILIATION_REF))


def _one_asset(intake: Mapping[str, Any], source_id: str) -> dict[str, Any]:
    assets = [
        item for item in intake.get("assets", [])
        if isinstance(item, dict) and item.get("extensions", {}).get("source_id") == source_id
    ]
    if len(assets) != 1:
        raise OrbitContinuation001Error("active_intake_source_identity_drift")
    return assets[0]


def expected_asset_snapshot(asset: Mapping[str, Any]) -> dict[str, Any]:
    extensions = asset.get("extensions", {})
    return {
        "source_id": extensions.get("source_id"),
        "asset_id": asset.get("asset_id"),
        "provider_product_id": extensions.get("provider_product_id"),
        "exact_product_id": extensions.get("exact_product_id"),
        "catalog_content_length_bytes": extensions.get("catalog_content_length_bytes"),
        "provider_checksums": extensions.get("provider_checksums"),
        "source_uri": asset.get("source", {}).get("uri"),
        "staging_relative_path": asset.get("staging_relative_path"),
        "destination_relative_path": asset.get("destination_relative_path"),
        "initial_state": asset.get("state"),
        "initial_attempt_count": len(asset.get("attempts", [])),
    }


def validate_initial_asset_state(intake: Mapping[str, Any]) -> list[dict[str, Any]]:
    preserved = _one_asset(intake, PRESERVED_SOURCE_ID)
    if (
        preserved.get("state") != "promoted"
        or preserved.get("failure") is not None
        or preserved.get("observed", {}).get("promoted_sha256") != PRESERVED_ORBIT_SHA256
        or preserved.get("observed", {}).get("promoted_size_bytes") != PRESERVED_ORBIT_SIZE
        or [item.get("outcome") for item in preserved.get("attempts", [])] != ["failed", "failed", "promoted"]
    ):
        raise OrbitContinuation001Error("preserved_m2_orb_001_identity_drift")
    snapshots: list[dict[str, Any]] = []
    for source_id in SOURCE_ORDER:
        asset = _one_asset(intake, source_id)
        if (
            asset.get("state") != "authorized"
            or asset.get("attempts") != []
            or asset.get("failure") is not None
            or asset.get("observed") != {
                "staged_sha256": None,
                "staged_size_bytes": None,
                "promoted_sha256": None,
                "promoted_size_bytes": None,
            }
        ):
            raise OrbitContinuation001Error("continuation_asset_not_fresh_authorized")
        snapshots.append(expected_asset_snapshot(asset))
    return snapshots


def validate_initial_paths_absent(intake: Mapping[str, Any]) -> list[dict[str, str]]:
    custody_root = (PROJECT_ROOT / Path(*PurePosixPath(str(intake["custody_root"])).parts)).resolve(strict=True)
    controlled_root = DATA_ROOT.resolve(strict=True)
    staging_root = require_safe_child(controlled_root, DATA_ROOT / ".intake-staging/nepal-m2-orbit-continuation-001")
    attempt_root = require_safe_child(controlled_root, DATA_ROOT / "derived/m2-orbit-continuation-001-attempts")
    supervisor_root = require_safe_child(controlled_root, DATA_ROOT / "derived/m2-orbit-continuation-001-supervisor")
    handoff_root = require_safe_child(controlled_root, DATA_ROOT / "derived/m2-orbit-continuation-001-handoff")
    if staging_root.exists() or attempt_root.exists() or supervisor_root.exists() or handoff_root.exists():
        raise OrbitContinuation001Error("continuation_evidence_root_not_fresh")
    observations: list[dict[str, str]] = []
    for source_id in SOURCE_ORDER:
        asset = _one_asset(intake, source_id)
        destination = require_safe_child(
            custody_root, custody_root / Path(*PurePosixPath(asset["destination_relative_path"]).parts)
        )
        staging = require_safe_child(
            controlled_root,
            staging_root / f"{asset['asset_id']}-continuation-001" / f"{asset['extensions']['exact_product_name']}.part",
        )
        if destination.exists() or staging.exists():
            raise OrbitContinuation001Error("continuation_path_not_fresh")
        observations.append({
            "source_id": source_id,
            "destination": str(destination),
            "staging": str(staging),
            "attempt_root": str(attempt_root),
        })
    return observations


def require_file_identity(path: Path, size: int, digest: str, code: str) -> None:
    if not path.is_file() or path.stat().st_size != size or sha256_file(path) != digest:
        raise OrbitContinuation001Error(code)


def validate_preserved_m2_orb_001_bytes(intake: Mapping[str, Any]) -> dict[str, Any]:
    preserved = _one_asset(intake, PRESERVED_SOURCE_ID)
    custody_root = (PROJECT_ROOT / Path(*PurePosixPath(str(intake["custody_root"])).parts)).resolve(strict=True)
    promoted = require_safe_child(
        custody_root, custody_root / Path(*PurePosixPath(preserved["destination_relative_path"]).parts)
    )
    staged = DATA_ROOT / Path(*PurePosixPath(PRESERVED_STAGING_RELATIVE).parts)
    require_file_identity(promoted, PRESERVED_ORBIT_SIZE, PRESERVED_ORBIT_SHA256, "preserved_orbit_identity_drift")
    require_file_identity(staged, PRESERVED_ORBIT_SIZE, PRESERVED_ORBIT_SHA256, "preserved_staging_identity_drift")
    result = ROOT / PRESERVED_RESULT_REF
    terminal = ROOT / PRESERVED_TERMINAL_REF
    if (
        not result.is_file()
        or load_object(result).get("status") != "pass_exact_m2_orb_001_input_promoted_no_replace"
        or not terminal.is_file()
        or load_object(terminal).get("status") != "pass_exact_m2_orb_001_promoted_remaining_sources_review_required"
    ):
        raise OrbitContinuation001Error("preserved_m2_orb_001_reconciliation_drift")
    return {
        "promoted": {"path": str(promoted), "size_bytes": PRESERVED_ORBIT_SIZE, "sha256": PRESERVED_ORBIT_SHA256},
        "staging": {"path": str(staged), "size_bytes": PRESERVED_ORBIT_SIZE, "sha256": PRESERVED_ORBIT_SHA256},
        "result_ref": PRESERVED_RESULT_REF,
        "result_sha256": sha256_file(result),
        "terminal_ref": PRESERVED_TERMINAL_REF,
        "terminal_sha256": sha256_file(terminal),
    }


def require_exact_contract(contract: Mapping[str, Any]) -> None:
    if (
        contract.get("contract_version") != "1.0"
        or contract.get("continuation_id") != CONTINUATION_ID
        or contract.get("status") != "active_authorized_final_no_payload_preflight_pending"
        or contract.get("source_ids_in_exact_order") != list(SOURCE_ORDER)
        or contract.get("preserved_source_ids") != [PRESERVED_SOURCE_ID]
        or contract.get("m2_orb_001_request_authorized") is not False
        or contract.get("maximum_owner_handoffs") != 1
        or contract.get("maximum_real_attempts_per_source") != 1
        or contract.get("stop_on_first_failure") is not True
        or contract.get("maximum_osv_endpoint_tolerance_seconds") != 1.0
        or contract.get("secret_transport") != SECRET_REFERENCE
        or contract.get("collision_policy") != "fail"
        or contract.get("promotion_mode") != "atomic-no-replace"
    ):
        raise OrbitContinuation001Error("continuation_contract_boundary_drift")
    assets = contract.get("assets")
    if not isinstance(assets, list) or [item.get("source_id") for item in assets] != list(SOURCE_ORDER):
        raise OrbitContinuation001Error("continuation_contract_asset_order_drift")
    if any(item.get("initial_state") != "authorized" or item.get("initial_attempt_count") != 0 for item in assets):
        raise OrbitContinuation001Error("continuation_contract_initial_state_drift")


def validate_publication_gate(gate: Mapping[str, Any]) -> None:
    if (
        gate.get("status") != "pass_public_controls_verified_before_orbit_continuation_001"
        or gate.get("github_actions", {}).get("conclusion") != "success"
        or gate.get("assertions", {}).get("credential_values_read_or_recorded") is not False
        or gate.get("assertions", {}).get("orbit_payload_request_performed") is not False
    ):
        raise OrbitContinuation001Error("continuation_publication_gate_not_passing")


def validate_runtime_gate() -> None:
    validate_approval_files()
    require_exact_contract(load_object(ROOT / CONTRACT_REF))
    validate_publication_gate(load_object(ROOT / PUBLICATION_GATE_REF))
    preflight = load_object(ROOT / FINAL_PREFLIGHT_REF)
    if (
        preflight.get("status") != "pass_no_payload_ready_for_single_secret_pipe_handoff"
        or preflight.get("source_ids_in_exact_order") != list(SOURCE_ORDER)
        or preflight.get("bindings", {}).get("approval_sha256") != sha256_file(ROOT / APPROVAL_REF)
        or preflight.get("bindings", {}).get("publication_gate_sha256") != sha256_file(ROOT / PUBLICATION_GATE_REF)
        or preflight.get("bindings", {}).get("activation_sha256") != sha256_file(ROOT / ACTIVATION_REF)
        or preflight.get("bindings", {}).get("continuation_contract_sha256") != sha256_file(ROOT / CONTRACT_REF)
        or preflight.get("bindings", {}).get("control_reconciliation_sha256") != sha256_file(ROOT / CONTROL_RECONCILIATION_REF)
        or preflight.get("assertions", {}).get("credential_values_read_or_recorded") is not False
        or preflight.get("assertions", {}).get("orbit_payload_requested") is not False
    ):
        raise OrbitContinuation001Error("continuation_final_preflight_not_passing")


def validate_prelaunch_git_state() -> None:
    """Require the public commit plus only the five expected post-CI gate files."""
    validate_runtime_gate()
    gate = load_object(ROOT / PUBLICATION_GATE_REF)
    expected_commit = gate.get("github_actions", {}).get("head_sha")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()
    origin = subprocess.run(
        ["git", "rev-parse", "origin/main"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()
    if head != expected_commit or origin != expected_commit:
        raise OrbitContinuation001Error("continuation_public_commit_drift")
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    observed = {line[3:].replace("\\", "/") for line in status if line.startswith("?? ")}
    non_untracked = [line for line in status if not line.startswith("?? ")]
    allowed = {CONTRACT_REF, PUBLICATION_GATE_REF, ACTIVATION_REF, FINAL_PREFLIGHT_REF, CONTROL_RECONCILIATION_REF}
    if non_untracked or observed != allowed:
        raise OrbitContinuation001Error("continuation_prelaunch_worktree_boundary_drift")


def validate_secret(secret: str) -> bytes:
    if not isinstance(secret, str) or not secret:
        raise OrbitContinuation001Error("secret_missing")
    if any(ch.isspace() for ch in secret):
        raise OrbitContinuation001Error("secret_contains_whitespace")
    encoded = secret.encode("utf-8")
    if len(encoded) > MAX_SECRET_BYTES:
        raise OrbitContinuation001Error("secret_too_large")
    return encoded


def sanitized_child_environment(source: Mapping[str, str], secret: str) -> dict[str, str]:
    validate_secret(secret)
    cleaned: dict[str, str] = {}
    for key, value in source.items():
        if key.upper() in {"CDSE_ACCESS_TOKEN", "COPERNICUS_ACCESS_TOKEN", "AUTHORIZATION"}:
            continue
        if secret in key or secret in value:
            continue
        cleaned[key] = value
    if any(secret in key or secret in value for key, value in cleaned.items()):
        raise OrbitContinuation001Error("secret_present_in_child_environment")
    return cleaned


def read_single_use_secret(stream: BinaryIO) -> str:
    try:
        data = stream.readline(MAX_SECRET_BYTES + 2)
    finally:
        stream.close()
    if not data or not data.endswith(b"\n") or len(data) > MAX_SECRET_BYTES + 1:
        raise OrbitContinuation001Error("secret_pipe_payload_invalid")
    raw = bytearray(data[:-2] if data.endswith(b"\r\n") else data[:-1])
    try:
        secret = raw.decode("utf-8")
        validate_secret(secret)
        return secret
    except UnicodeDecodeError as exc:
        raise OrbitContinuation001Error("secret_pipe_encoding_invalid") from exc
    finally:
        for index in range(len(raw)):
            raw[index] = 0


def build_supervisor_command(
    handoff_id: str,
    python_executable: str | None = None,
    supervisor_path: Path | None = None,
) -> list[str]:
    return [
        python_executable or sys.executable,
        str(supervisor_path or ROOT / "scripts/m2_orbit_continuation_001_supervisor.py"),
        "--continuation-id",
        CONTINUATION_ID,
        "--handoff-id",
        handoff_id,
    ]


def claim_owner_handoff(*, claim_root: Path | None = None, claimed_at: str | None = None) -> tuple[str, Path]:
    observed_at = claimed_at or now_utc()
    if UTC_PATTERN.fullmatch(observed_at) is None:
        raise OrbitContinuation001Error("handoff_claim_time_invalid")
    handoff_id = f"m2-orbit-continuation-001-handoff-{observed_at.replace(':', '').replace('-', '').casefold()}-{uuid.uuid4().hex[:8]}"
    root = claim_root or (DATA_ROOT / "derived/m2-orbit-continuation-001-handoff")
    try:
        root.mkdir(parents=False, exist_ok=False)
    except FileExistsError as exc:
        raise OrbitContinuation001Error("owner_handoff_already_consumed") from exc
    claim_path = root / f"{handoff_id}.json"
    write_new_json(claim_path, {
        "schema_version": "1.0",
        "event": "owner_handoff_claimed",
        "handoff_id": handoff_id,
        "continuation_id": CONTINUATION_ID,
        "source_ids_in_exact_order": list(SOURCE_ORDER),
        "claimed_at": observed_at,
        "maximum_owner_handoffs": 1,
        "authority_consumed": True,
        "credential_reference": SECRET_REFERENCE,
        "credential_value_recorded": False,
    })
    return handoff_id, claim_path


def validate_handoff_claim(handoff_id: str, *, claim_root: Path | None = None) -> dict[str, Any]:
    if re.fullmatch(r"m2-orbit-continuation-001-handoff-\d{8}t\d{6}z-[0-9a-f]{8}", handoff_id) is None:
        raise OrbitContinuation001Error("handoff_identity_invalid")
    root = claim_root or (DATA_ROOT / "derived/m2-orbit-continuation-001-handoff")
    claim_path = root / f"{handoff_id}.json"
    files = sorted(path for path in root.iterdir() if path.is_file()) if root.is_dir() else []
    if files != [claim_path]:
        raise OrbitContinuation001Error("handoff_claim_inventory_drift")
    claim = load_object(claim_path)
    if (
        claim.get("event") != "owner_handoff_claimed"
        or claim.get("handoff_id") != handoff_id
        or claim.get("continuation_id") != CONTINUATION_ID
        or claim.get("source_ids_in_exact_order") != list(SOURCE_ORDER)
        or claim.get("maximum_owner_handoffs") != 1
        or claim.get("authority_consumed") is not True
        or claim.get("credential_reference") != SECRET_REFERENCE
        or claim.get("credential_value_recorded") is not False
    ):
        raise OrbitContinuation001Error("handoff_claim_content_drift")
    return claim


def detached_popen_kwargs(environment: Mapping[str, str]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "stdin": subprocess.PIPE,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "cwd": str(ROOT),
        "env": dict(environment),
        "close_fds": True,
    }
    if os.name == "nt":
        kwargs["creationflags"] = (
            getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
        )
    else:
        kwargs["start_new_session"] = True
    return kwargs


def launch_detached_supervisor(
    secret: str,
    *,
    command: Sequence[str] | None = None,
    handoff_id: str | None = None,
    environment: Mapping[str, str] | None = None,
    popen_factory: Callable[..., Any] = subprocess.Popen,
) -> int:
    encoded = bytearray(validate_secret(secret))
    if command is None and handoff_id is None:
        raise OrbitContinuation001Error("handoff_identity_required")
    argv = list(command or build_supervisor_command(str(handoff_id)))
    if PRESERVED_SOURCE_ID in argv or any(secret in part for part in argv):
        raise OrbitContinuation001Error("forbidden_value_in_supervisor_command")
    child_environment = sanitized_child_environment(environment or os.environ, secret)
    process = popen_factory(argv, **detached_popen_kwargs(child_environment))
    if process.stdin is None:
        raise OrbitContinuation001Error("anonymous_pipe_not_created")
    try:
        process.stdin.write(encoded)
        process.stdin.write(b"\n")
        process.stdin.flush()
    except (BrokenPipeError, OSError) as exc:
        raise OrbitContinuation001Error("secret_handoff_failed") from exc
    finally:
        process.stdin.close()
        for index in range(len(encoded)):
            encoded[index] = 0
    if not isinstance(process.pid, int) or process.pid <= 0:
        raise OrbitContinuation001Error("detached_supervisor_pid_invalid")
    return process.pid


def classify_failure(exc: BaseException) -> dict[str, str]:
    if isinstance(exc, (OrbitContinuation001Error, TransferControlError)):
        code = getattr(exc, "code", "")
        if isinstance(code, str) and SAFE_CODE.fullmatch(code):
            return {"terminal_code": code, "failure_class": "approved_control"}
    return {"terminal_code": "unexpected_continuation_supervisor_failure", "failure_class": "unexpected"}


class ContinuationJournal:
    """Append nonsecret continuation lifecycle and progress evidence outside Git."""

    def __init__(self, event_root: Path, supervisor_id: str, interval_seconds: float = 30.0):
        self.event_root = event_root
        self.supervisor_id = supervisor_id
        self.interval_seconds = interval_seconds
        self.started_at = now_utc()
        self.phase = "starting"
        self.source_id: str | None = None
        self.attempt_id: str | None = None
        self.bytes_written = 0
        self.completed_source_ids: list[str] = []
        self._event_sequence = 0
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def _next_path(self, event: str) -> Path:
        with self._lock:
            self._event_sequence += 1
            sequence = self._event_sequence
        return self.event_root / f"{self.supervisor_id}-{sequence:06d}-{event}.json"

    def _snapshot(self, event: str) -> dict[str, Any]:
        with self._lock:
            return {
                "schema_version": "1.0",
                "event": event,
                "supervisor_id": self.supervisor_id,
                "continuation_id": CONTINUATION_ID,
                "process_id": os.getpid(),
                "started_at": self.started_at,
                "observed_at": now_utc(),
                "phase": self.phase,
                "source_id": self.source_id,
                "attempt_id": self.attempt_id,
                "bytes_written": self.bytes_written,
                "completed_source_ids": list(self.completed_source_ids),
                "source_ids_in_exact_order": list(SOURCE_ORDER),
                "m2_orb_001_request_authorized": False,
                "credential_reference": SECRET_REFERENCE,
                "credential_value_recorded": False,
            }

    def _append(self, event: str) -> Path:
        path = self._next_path(event)
        write_new_json(path, self._snapshot(event))
        return path

    def start(self) -> Path:
        self.event_root.mkdir(parents=True, exist_ok=False)
        path = self._append("supervisor_started")
        self._append("supervisor_heartbeat")
        self._thread = threading.Thread(target=self._heartbeat_loop, name="continuation-001-heartbeat", daemon=True)
        self._thread.start()
        return path

    def update(self, *, phase: str, source_id: str | None, attempt_id: str | None, bytes_written: int | None) -> None:
        with self._lock:
            changed = phase != self.phase or source_id != self.source_id or (
                attempt_id is not None and attempt_id != self.attempt_id
            )
            self.phase = phase
            self.source_id = source_id
            if attempt_id is not None:
                self.attempt_id = attempt_id
            if bytes_written is not None:
                self.bytes_written = int(bytes_written)
        if changed:
            self._append("supervisor_phase")

    def mark_completed(self, source_id: str) -> None:
        if source_id not in SOURCE_ORDER:
            raise OrbitContinuation001Error("completed_source_outside_allowlist")
        with self._lock:
            if source_id in self.completed_source_ids:
                raise OrbitContinuation001Error("completed_source_duplicate")
            self.completed_source_ids.append(source_id)
        self._append("source_completed")

    def _heartbeat_loop(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            try:
                self._append("supervisor_heartbeat")
            except OSError:
                return

    def finish(self, outcome: str, terminal: Mapping[str, str]) -> Path:
        if outcome not in {"succeeded", "failed"}:
            raise OrbitContinuation001Error("supervisor_terminal_outcome_invalid")
        code = terminal.get("terminal_code")
        failure_class = terminal.get("failure_class")
        if not isinstance(code, str) or SAFE_CODE.fullmatch(code) is None:
            raise OrbitContinuation001Error("terminal_code_invalid")
        if failure_class not in {"approved_control", "unexpected", "none"}:
            raise OrbitContinuation001Error("failure_class_invalid")
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(1.0, self.interval_seconds * 2))
        payload = self._snapshot(f"supervisor_{outcome}")
        payload.update({
            "completed_at": now_utc(),
            "terminal_code": code,
            "failure_class": failure_class,
            "exception_message_recorded": False,
            "traceback_recorded": False,
            "retry_automatically_authorized": False,
        })
        path = self._next_path(f"supervisor_{outcome}")
        write_new_json(path, payload)
        return path
