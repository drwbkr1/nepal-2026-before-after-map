#!/usr/bin/env python3
"""Pure controls for the approved Sentinel continuation-001 route."""

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
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, Callable, Mapping, Sequence

from m2_transfer_core import TransferControlError


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent.resolve()
DATA_ROOT = PROJECT_ROOT / "nepal-2026-before-after-map-data"

CONTINUATION_ID = "nepal-m2-sentinel-continuation-001"
SOURCE_ORDER = ("M1-SRC-005", "M1-SRC-006", "M1-SRC-008", "M1-SRC-010")
RECOVERY_SOURCE_ID = "M1-SRC-004"
RECOVERY_ARCHIVE_SHA256 = "a606cac063cc23e60a623f020192fc097d327f3dafadf1115802b2a458eaceab"
RECOVERY_ARCHIVE_SIZE = 1_732_332_897
ORIGINAL_PARTIAL_SHA256 = "299b2d07ccb58747cce43ae3b18e6d25c1c6d72a5653831b50a44ca72677ea66"
ORIGINAL_PARTIAL_SIZE = 561_593_598
RECOVERY_001_PARTIAL_SHA256 = "c2d3a878f98615ddaa5e0bf21df5eb5f65c591719cb26b5f43b361aa4eac4cac"
RECOVERY_001_PARTIAL_SIZE = 1_333_788_672

EXPECTED_BUNDLE_SHA256 = "382d2238b7d27269604cc07134edfa29c9a3464d2c7c3b65163ceccab35e3f9b"
EXPECTED_PROPOSAL_SHA256 = "d58706dc0961816191a76f420d993bdc28be8f140358dc1638f6cc937366e7b1"
EXPECTED_RESPONSE_SHA256 = "add004d26f7a35ed1b657089dae1c1f68f01eba495c0c4edb35cee943a13cb39"
EXPECTED_RECONCILIATION_SHA256 = "420f525d160a1b95f6784da06a0ca95ddf8e6e8e37d7947925f6c865157d28a6"
EXPECTED_APPROVAL_SHA256 = "93f451f458c5b4984f980049f5adadf73e52663c8a71ee9699939b7f85e727a1"

APPROVAL_REF = "records/source-gates/m2-sentinel-continuation-001-approval.json"
RECONCILIATION_REF = "records/source-gates/m2-sentinel-continuation-001-review-reconciliation.json"
PROPOSAL_REF = "contracts/milestone-002-sentinel-continuation-001-proposal.json"
BUNDLE_REF = "reviews/m2-sentinel-continuation-001/review-bundle.json"
ACTIVE_INTAKE_REF = "contracts/m2-intake.json"
RECOVERY_CONTRACT_REF = "contracts/m2-sentinel-recovery-002.json"
RECOVERY_OUTCOME_REF = "records/acquisition/sentinel-recovery-002-supervisor-reconciliation-001.json"
CONTRACT_REF = "contracts/m2-sentinel-continuation-001.json"
IMPLEMENTATION_READINESS_REF = "records/acquisition/sentinel-continuation-001-implementation-readiness.json"
PUBLICATION_GATE_REF = "records/acquisition/sentinel-continuation-001-publication-gate.json"
ACTIVATION_REF = "records/acquisition/sentinel-continuation-001-activation.json"
FINAL_PREFLIGHT_REF = "records/acquisition/sentinel-continuation-001-final-preflight.json"
SUCCESS_RECONCILIATION_REF = "records/acquisition/sentinel-continuation-001-success-reconciliation.json"

SECRET_REFERENCE = "anonymous_pipe_single_use_memory_only"
MAX_SECRET_BYTES = 16_384
SAFE_CODE = re.compile(r"[a-z0-9_]{3,96}")


class Continuation001ControlError(RuntimeError):
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
        raise Continuation001ControlError("control_root_not_object")
    return value


def write_new_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(canonical_bytes(value))
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise Continuation001ControlError("output_collision") from exc


def is_reparse_point(path: Path) -> bool:
    attributes = getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0)
    return path.is_symlink() or bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def require_safe_child(root: Path, candidate: Path) -> Path:
    resolved_root = root.resolve(strict=True)
    resolved_candidate = candidate.resolve(strict=False)
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise Continuation001ControlError("path_outside_controlled_root") from exc
    if resolved_candidate == resolved_root:
        raise Continuation001ControlError("path_must_be_child")
    current = resolved_candidate.parent
    while True:
        if current.exists() and is_reparse_point(current):
            raise Continuation001ControlError("reparse_point_in_path")
        if current == resolved_root:
            break
        if current == current.parent:
            raise Continuation001ControlError("path_ancestor_escape")
        current = current.parent
    return resolved_candidate


def validate_approval(approval: Mapping[str, Any], reconciliation: Mapping[str, Any]) -> None:
    if (
        approval.get("status") != "approved_exact_bounded_continuation_only"
        or approval.get("review_bundle_manifest_sha256") != EXPECTED_BUNDLE_SHA256
        or approval.get("continuation_proposal_sha256") != EXPECTED_PROPOSAL_SHA256
        or approval.get("locked_response_sha256") != EXPECTED_RESPONSE_SHA256
        or approval.get("review_reconciliation_sha256") != EXPECTED_RECONCILIATION_SHA256
        or approval.get("source_ids_in_exact_order") != list(SOURCE_ORDER)
        or approval.get("maximum_real_attempts_per_source") != 1
        or approval.get("stop_on_first_failure") is not True
        or approval.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}
        or approval.get("human_decisions_fabricated") is not False
        or reconciliation.get("status") != "reconciled_exact_human_response"
        or reconciliation.get("response_sha256") != EXPECTED_RESPONSE_SHA256
        or reconciliation.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}
        or reconciliation.get("human_decisions_fabricated") is not False
    ):
        raise Continuation001ControlError("continuation_001_approval_or_reconciliation_drift")


def validate_approval_files() -> None:
    bindings = {
        ROOT / BUNDLE_REF: EXPECTED_BUNDLE_SHA256,
        ROOT / PROPOSAL_REF: EXPECTED_PROPOSAL_SHA256,
        ROOT / RECONCILIATION_REF: EXPECTED_RECONCILIATION_SHA256,
        ROOT / APPROVAL_REF: EXPECTED_APPROVAL_SHA256,
    }
    if any(not path.is_file() or sha256_file(path) != digest for path, digest in bindings.items()):
        raise Continuation001ControlError("continuation_001_authority_byte_drift")
    validate_approval(load_object(ROOT / APPROVAL_REF), load_object(ROOT / RECONCILIATION_REF))


def _one_asset(intake: Mapping[str, Any], source_id: str) -> dict[str, Any]:
    assets = [
        item for item in intake.get("assets", [])
        if isinstance(item, dict) and item.get("extensions", {}).get("source_id") == source_id
    ]
    if len(assets) != 1:
        raise Continuation001ControlError("active_intake_source_identity_drift")
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
    recovery = _one_asset(intake, RECOVERY_SOURCE_ID)
    attempts = recovery.get("attempts", [])
    if (
        recovery.get("state") != "promoted"
        or recovery.get("observed", {}).get("promoted_sha256") != RECOVERY_ARCHIVE_SHA256
        or recovery.get("observed", {}).get("promoted_size_bytes") != RECOVERY_ARCHIVE_SIZE
        or recovery.get("extensions", {}).get("satisfied_by_recovery_002") is not True
        or [item.get("outcome") for item in attempts] != ["failed", "succeeded"]
    ):
        raise Continuation001ControlError("recovered_m1_src_004_identity_drift")
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
            raise Continuation001ControlError("continuation_asset_not_fresh_authorized")
        snapshots.append(expected_asset_snapshot(asset))
    return snapshots


def validate_initial_paths_absent(intake: Mapping[str, Any]) -> list[dict[str, str]]:
    custody_root = (PROJECT_ROOT / Path(*PurePosixPath(str(intake["custody_root"])).parts)).resolve(strict=True)
    staging_root = (PROJECT_ROOT / Path(*PurePosixPath(str(intake["staging_root"])).parts)).resolve(strict=True)
    observations: list[dict[str, str]] = []
    for source_id in SOURCE_ORDER:
        asset = _one_asset(intake, source_id)
        destination = require_safe_child(
            custody_root, custody_root / Path(*PurePosixPath(asset["destination_relative_path"]).parts)
        )
        staging = require_safe_child(
            staging_root, staging_root / Path(*PurePosixPath(asset["staging_relative_path"]).parts)
        )
        event_root = require_safe_child(staging_root, staging_root / "attempt-events" / asset["asset_id"])
        if destination.exists() or staging.exists() or event_root.exists():
            raise Continuation001ControlError("continuation_path_not_fresh")
        observations.append({
            "source_id": source_id,
            "destination": str(destination),
            "staging": str(staging),
            "event_root": str(event_root),
        })
    return observations


def require_file_identity(path: Path, size: int, digest: str, code: str) -> None:
    if not path.is_file() or path.stat().st_size != size or sha256_file(path) != digest:
        raise Continuation001ControlError(code)


def validate_retained_and_recovered_bytes(intake: Mapping[str, Any]) -> dict[str, Any]:
    recovery = _one_asset(intake, RECOVERY_SOURCE_ID)
    original_started = Path(recovery["attempts"][0]["extensions"]["external_started_event"])
    recovery_started = Path(recovery["attempts"][1]["extensions"]["external_started_event"])
    original_partial = Path(load_object(original_started)["staging_path"])
    recovery_contract = load_object(ROOT / RECOVERY_CONTRACT_REF)
    recovery_asset = recovery_contract["assets"][0]
    recovery_001_partial = Path(recovery_asset["extensions"]["recovery_001_partial_external_path"])
    custody_root = (PROJECT_ROOT / Path(*PurePosixPath(str(intake["custody_root"])).parts)).resolve(strict=True)
    archive = require_safe_child(
        custody_root, custody_root / Path(*PurePosixPath(recovery["destination_relative_path"]).parts)
    )
    require_file_identity(original_partial, ORIGINAL_PARTIAL_SIZE, ORIGINAL_PARTIAL_SHA256, "original_partial_identity_drift")
    require_file_identity(
        recovery_001_partial,
        RECOVERY_001_PARTIAL_SIZE,
        RECOVERY_001_PARTIAL_SHA256,
        "recovery_001_partial_identity_drift",
    )
    require_file_identity(archive, RECOVERY_ARCHIVE_SIZE, RECOVERY_ARCHIVE_SHA256, "recovery_archive_identity_drift")
    container_ref = recovery_contract.get("extensions", {}).get("container_receipt_ref")
    container = ROOT / str(container_ref)
    if not container.is_file() or load_object(container).get("status") != "pass_container_only":
        raise Continuation001ControlError("recovery_container_receipt_not_passing")
    return {
        "original_partial": {"path": str(original_partial), "size_bytes": ORIGINAL_PARTIAL_SIZE, "sha256": ORIGINAL_PARTIAL_SHA256},
        "recovery_001_partial": {"path": str(recovery_001_partial), "size_bytes": RECOVERY_001_PARTIAL_SIZE, "sha256": RECOVERY_001_PARTIAL_SHA256},
        "recovery_archive": {"path": str(archive), "size_bytes": RECOVERY_ARCHIVE_SIZE, "sha256": RECOVERY_ARCHIVE_SHA256},
        "container_receipt_ref": str(container_ref),
        "container_receipt_sha256": sha256_file(container),
    }


def require_exact_contract(contract: Mapping[str, Any]) -> None:
    if (
        contract.get("contract_version") != "1.0"
        or contract.get("continuation_id") != CONTINUATION_ID
        or contract.get("status") != "active_authorized_final_no_payload_preflight_pending"
        or contract.get("source_ids_in_exact_order") != list(SOURCE_ORDER)
        or contract.get("recovery_source_ids") != []
        or contract.get("m1_src_004_request_permitted") is not False
        or contract.get("maximum_real_attempts_per_source") != 1
        or contract.get("stop_on_first_failure") is not True
        or contract.get("secret_transport") != SECRET_REFERENCE
        or contract.get("collision_policy") != "fail"
        or contract.get("promotion_mode") != "atomic-no-replace"
    ):
        raise Continuation001ControlError("continuation_contract_boundary_drift")
    assets = contract.get("assets")
    if not isinstance(assets, list) or [item.get("source_id") for item in assets] != list(SOURCE_ORDER):
        raise Continuation001ControlError("continuation_contract_asset_order_drift")
    if any(item.get("initial_state") != "authorized" or item.get("initial_attempt_count") != 0 for item in assets):
        raise Continuation001ControlError("continuation_contract_initial_state_drift")


def validate_publication_gate(gate: Mapping[str, Any]) -> None:
    if (
        gate.get("status") != "pass_public_controls_verified_before_continuation_001"
        or gate.get("github_actions", {}).get("conclusion") != "success"
        or gate.get("assertions", {}).get("credential_values_read_or_recorded") is not False
        or gate.get("assertions", {}).get("payload_request_performed") is not False
    ):
        raise Continuation001ControlError("continuation_publication_gate_not_passing")


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
        or preflight.get("assertions", {}).get("credential_values_read_or_recorded") is not False
        or preflight.get("assertions", {}).get("product_payload_requested") is not False
    ):
        raise Continuation001ControlError("continuation_final_preflight_not_passing")


def validate_prelaunch_git_state() -> None:
    """Require the public commit plus only the four expected post-CI gate files."""
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
        raise Continuation001ControlError("continuation_public_commit_drift")
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    observed = {line[3:].replace("\\", "/") for line in status if line.startswith("?? ")}
    non_untracked = [line for line in status if not line.startswith("?? ")]
    allowed = {CONTRACT_REF, PUBLICATION_GATE_REF, ACTIVATION_REF, FINAL_PREFLIGHT_REF}
    if non_untracked or observed != allowed:
        raise Continuation001ControlError("continuation_prelaunch_worktree_boundary_drift")


def validate_secret(secret: str) -> bytes:
    if not isinstance(secret, str) or not secret:
        raise Continuation001ControlError("secret_missing")
    if any(ch.isspace() for ch in secret):
        raise Continuation001ControlError("secret_contains_whitespace")
    encoded = secret.encode("utf-8")
    if len(encoded) > MAX_SECRET_BYTES:
        raise Continuation001ControlError("secret_too_large")
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
        raise Continuation001ControlError("secret_present_in_child_environment")
    return cleaned


def read_single_use_secret(stream: BinaryIO) -> str:
    try:
        data = stream.readline(MAX_SECRET_BYTES + 2)
    finally:
        stream.close()
    if not data or not data.endswith(b"\n") or len(data) > MAX_SECRET_BYTES + 1:
        raise Continuation001ControlError("secret_pipe_payload_invalid")
    raw = bytearray(data[:-1])
    try:
        secret = raw.decode("utf-8")
        validate_secret(secret)
        return secret
    except UnicodeDecodeError as exc:
        raise Continuation001ControlError("secret_pipe_encoding_invalid") from exc
    finally:
        for index in range(len(raw)):
            raw[index] = 0


def build_supervisor_command(python_executable: str | None = None, supervisor_path: Path | None = None) -> list[str]:
    return [
        python_executable or sys.executable,
        str(supervisor_path or ROOT / "scripts/m2_sentinel_continuation_001_supervisor.py"),
        "--continuation-id",
        CONTINUATION_ID,
    ]


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
    environment: Mapping[str, str] | None = None,
    popen_factory: Callable[..., Any] = subprocess.Popen,
) -> int:
    encoded = bytearray(validate_secret(secret))
    argv = list(command or build_supervisor_command())
    if RECOVERY_SOURCE_ID in argv or any(secret in part for part in argv):
        raise Continuation001ControlError("forbidden_value_in_supervisor_command")
    child_environment = sanitized_child_environment(environment or os.environ, secret)
    process = popen_factory(argv, **detached_popen_kwargs(child_environment))
    if process.stdin is None:
        raise Continuation001ControlError("anonymous_pipe_not_created")
    try:
        process.stdin.write(encoded)
        process.stdin.write(b"\n")
        process.stdin.flush()
    except (BrokenPipeError, OSError) as exc:
        raise Continuation001ControlError("secret_handoff_failed") from exc
    finally:
        process.stdin.close()
        for index in range(len(encoded)):
            encoded[index] = 0
    if not isinstance(process.pid, int) or process.pid <= 0:
        raise Continuation001ControlError("detached_supervisor_pid_invalid")
    return process.pid


def classify_failure(exc: BaseException) -> dict[str, str]:
    if isinstance(exc, (Continuation001ControlError, TransferControlError)):
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
                "m1_src_004_request_permitted": False,
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
            raise Continuation001ControlError("completed_source_outside_allowlist")
        with self._lock:
            if source_id in self.completed_source_ids:
                raise Continuation001ControlError("completed_source_duplicate")
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
            raise Continuation001ControlError("supervisor_terminal_outcome_invalid")
        code = terminal.get("terminal_code")
        failure_class = terminal.get("failure_class")
        if not isinstance(code, str) or SAFE_CODE.fullmatch(code) is None:
            raise Continuation001ControlError("terminal_code_invalid")
        if failure_class not in {"approved_control", "unexpected", "none"}:
            raise Continuation001ControlError("failure_class_invalid")
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
