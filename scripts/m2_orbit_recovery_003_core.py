#!/usr/bin/env python3
"""Pure controls for the approved M2-ORB-001 recovery-003 route."""

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
from pathlib import Path
from typing import Any, BinaryIO, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent.resolve()
DATA_ROOT = PROJECT_ROOT / "nepal-2026-before-after-map-data"

EXPECTED_SOURCE_ID = "M2-ORB-001"
EXPECTED_ASSET_ID = "m2-orb-001"
EXPECTED_PROVIDER_PRODUCT_ID = "d4fdc474-0069-459b-9534-b5999dec5aab"
EXPECTED_PRODUCT_NAME = "S1D_OPER_AUX_RESORB_OPOD_20260816T143208_V20260816T103526_20260816T140956.EOF"
EXPECTED_SIZE_BYTES = 639_533
EXPECTED_MD5 = "ca7f36b1892073c883c4cff5c0517b9c"
EXPECTED_BLAKE3 = "ce824099fa812d6c229bd5bef2d4a70d7185d248f91ec3111ce557868ab1269b"
EXPECTED_DOWNLOAD_URL = f"https://download.dataspace.copernicus.eu/odata/v1/Products({EXPECTED_PROVIDER_PRODUCT_ID})/$value"
EXPECTED_ATTEMPT_PREFIX = "m2-orb-001-recovery-002"
EXPECTED_STAGING_ROOT = "nepal-2026-before-after-map-data/.intake-staging/nepal-m2-orbit-recovery-003"
EXPECTED_STAGING_RELATIVE = f"{EXPECTED_ATTEMPT_PREFIX}/{EXPECTED_PRODUCT_NAME}.part"
EXPECTED_DESTINATION_RELATIVE = f"m2-orb-001/{EXPECTED_PRODUCT_NAME}"
EXPECTED_ATTEMPT_EVENT_ROOT = "nepal-2026-before-after-map-data/derived/m2-orbit-recovery-003-attempts"
EXPECTED_SUPERVISOR_ROOT = "nepal-2026-before-after-map-data/derived/m2-orbit-recovery-003-supervisor"
EXPECTED_HANDOFF_CLAIM_ROOT = "nepal-2026-before-after-map-data/derived/m2-orbit-recovery-003-handoff"

ORIGINAL_ATTEMPT_ID = "m2-orb-001-20260904t050937z-8ed21d05"
ORIGINAL_RECEIPT_REF = f"records/acquisition/orbit-attempts/{ORIGINAL_ATTEMPT_ID}.json"
ORIGINAL_RECEIPT_SHA256 = "a7057479f4dfb867ead6c9622d684c07df51af9db6c39a6fa2dc6d94ae7afc9c"
ORIGINAL_RECONCILIATION_REF = "records/acquisition/orbit-test-boundary-reconciliation-001.json"
ORIGINAL_RECONCILIATION_SHA256 = "40dae0623dcc142cec17ff2108752e5e60bd736a241fe4b83e8f04c5de690025"
RECOVERY_002_OUTCOME_REF = "records/acquisition/m2-orbit-recovery-002-outcome-reconciliation.json"
RECOVERY_002_OUTCOME_SHA256 = "3d0b6be8e09e0d9049c32c65461e321b2fdbd5db398dd9a6d1b08b62c6c51380"
RECOVERY_002_TERMINAL_REF = "records/readiness/m2-orbit-recovery-002-terminal-reconciliation.json"
RECOVERY_002_TERMINAL_SHA256 = "3ac47e6e57c7f2c27074910f6f5a41b432561fc59caad1a0dd75459aeff3abfc"
RECOVERY_002_STAGING_ROOT = DATA_ROOT / ".intake-staging/nepal-m2-orbit-recovery-002"
RECOVERY_002_EMPTY_PAYLOAD_PARENT = RECOVERY_002_STAGING_ROOT / "m2-orb-001-recovery-001"

PROPOSAL_REF = "contracts/milestone-002-orbit-recovery-003-proposal.json"
PROPOSAL_SHA256 = "5aa4a0042024634a7ade191e0c5f36614216d8581a9c0535c0042be20583bfa3"
BUNDLE_REF = "reviews/m2-orbit-recovery-003/review-bundle.json"
BUNDLE_SHA256 = "bc3cdc22d16251c77b26d9903036b4317221e2b01207aa9db26436bfd091fe9d"
RECONCILIATION_REF = "records/source-gates/m2-orbit-recovery-003-review-reconciliation.json"
RECONCILIATION_SHA256 = "1883bf3ed498f3cb709d85bdc1bd52e48a6b27053986694efccd163f6b5bc11e"
APPROVAL_REF = "records/source-gates/m2-orbit-recovery-003-approval.json"
APPROVAL_SHA256 = "63a01a7010a5cbd68cfa2dd35f1d24918c72a2e59ef956a98897ea62e005a278"
APPROVAL_ACTIVATION_REF = "records/readiness/m2-orbit-recovery-003-approval-activation.json"
REVIEW_PUBLICATION_REF = "records/readiness/m2-orbit-recovery-003-review-publication-gate.json"
CONTRACT_REF = "contracts/m2-orbit-recovery-003.json"
PUBLICATION_GATE_REF = "records/acquisition/m2-orbit-recovery-003-publication-gate.json"
ACTIVATION_REF = "records/acquisition/m2-orbit-recovery-003-activation.json"
FINAL_PREFLIGHT_REF = "records/acquisition/m2-orbit-recovery-003-final-preflight.json"
IMPLEMENTATION_READINESS_REF = "records/acquisition/m2-orbit-recovery-003-implementation-readiness.json"
ACTIVE_INTAKE_REF = "contracts/m2-orbit-intake.json"
ACTIVE_VERIFICATION_REF = "contracts/m2-orbit-offline-verification.json"
MANIFEST_REF = "records/source-gates/m2-orbit-candidate-manifest.json"
RADAR_READINESS_REF = "records/readiness/m2-radar-source-readiness-001.json"
MILESTONE_REF = "contracts/milestone-002.json"

SECRET_REFERENCE = "anonymous_pipe_single_use_memory_only"
MAX_SECRET_BYTES = 16_384
UTC_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


class OrbitRecovery003Error(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise OrbitRecovery003Error("control_root_not_object")
    return value


def write_new_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(canonical_bytes(value))
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise OrbitRecovery003Error("output_collision") from exc


def replace_json(path: Path, value: dict[str, Any], nonce: str) -> None:
    temporary = path.with_name(f"{path.name}.{nonce}.tmp")
    if temporary.exists():
        raise OrbitRecovery003Error("temporary_control_path_exists")
    with temporary.open("xb") as stream:
        stream.write(canonical_bytes(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def is_reparse_point(path: Path) -> bool:
    attributes = getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0)
    return path.is_symlink() or bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def require_safe_child(root: Path, candidate: Path) -> Path:
    resolved_root = root.resolve(strict=True)
    resolved_candidate = candidate.resolve(strict=False)
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise OrbitRecovery003Error("path_outside_controlled_root") from exc
    if resolved_candidate == resolved_root:
        raise OrbitRecovery003Error("path_must_be_child")
    current = resolved_candidate.parent
    while True:
        if current.exists() and is_reparse_point(current):
            raise OrbitRecovery003Error("reparse_point_in_path")
        if current == resolved_root:
            break
        if current == current.parent:
            raise OrbitRecovery003Error("path_ancestor_escape")
        current = current.parent
    return resolved_candidate


def validate_secret(secret: str) -> bytes:
    if not isinstance(secret, str) or not secret:
        raise OrbitRecovery003Error("secret_missing")
    if any(character.isspace() for character in secret):
        raise OrbitRecovery003Error("secret_contains_whitespace")
    encoded = secret.encode("utf-8")
    if len(encoded) > MAX_SECRET_BYTES:
        raise OrbitRecovery003Error("secret_too_large")
    return encoded


def sanitized_child_environment(source: Mapping[str, str], secret: str) -> dict[str, str]:
    validate_secret(secret)
    cleaned: dict[str, str] = {}
    for key, value in source.items():
        upper = key.upper()
        if upper in {"CDSE_ACCESS_TOKEN", "COPERNICUS_ACCESS_TOKEN", "AUTHORIZATION"}:
            continue
        if secret in key or secret in value:
            continue
        cleaned[key] = value
    if any(secret in key or secret in value for key, value in cleaned.items()):
        raise OrbitRecovery003Error("secret_present_in_child_environment")
    return cleaned


def read_single_use_secret(stream: BinaryIO) -> str:
    try:
        data = stream.readline(MAX_SECRET_BYTES + 2)
    finally:
        stream.close()
    if not data or not data.endswith(b"\n") or len(data) > MAX_SECRET_BYTES + 1:
        raise OrbitRecovery003Error("secret_pipe_payload_invalid")
    raw = bytearray(data[:-2] if data.endswith(b"\r\n") else data[:-1])
    try:
        secret = raw.decode("utf-8")
        validate_secret(secret)
        return secret
    except UnicodeDecodeError as exc:
        raise OrbitRecovery003Error("secret_pipe_encoding_invalid") from exc
    finally:
        for index in range(len(raw)):
            raw[index] = 0


def build_supervisor_command(handoff_id: str) -> list[str]:
    return [
        sys.executable,
        str(ROOT / "scripts/m2_orbit_recovery_003_supervisor.py"),
        "--source-id",
        EXPECTED_SOURCE_ID,
        "--handoff-id",
        handoff_id,
    ]


def claim_owner_handoff(*, claim_root: Path | None = None, claimed_at: str | None = None) -> tuple[str, Path]:
    observed_at = claimed_at or now_utc()
    if UTC_PATTERN.fullmatch(observed_at) is None:
        raise OrbitRecovery003Error("handoff_claim_time_invalid")
    handoff_id = f"m2-orbit-recovery-003-handoff-{observed_at.replace(':', '').replace('-', '').casefold()}-{uuid.uuid4().hex[:8]}"
    root = claim_root or (DATA_ROOT / "derived/m2-orbit-recovery-003-handoff")
    try:
        root.mkdir(parents=False, exist_ok=False)
    except FileExistsError as exc:
        raise OrbitRecovery003Error("owner_handoff_already_consumed") from exc
    claim_path = root / f"{handoff_id}.json"
    write_new_json(claim_path, {
        "schema_version": "1.0",
        "event": "owner_handoff_claimed",
        "handoff_id": handoff_id,
        "source_id": EXPECTED_SOURCE_ID,
        "claimed_at": observed_at,
        "maximum_owner_handoffs": 1,
        "authority_consumed": True,
        "credential_reference": SECRET_REFERENCE,
        "credential_value_recorded": False,
    })
    return handoff_id, claim_path


def validate_handoff_claim(handoff_id: str, *, claim_root: Path | None = None) -> dict[str, Any]:
    if re.fullmatch(r"m2-orbit-recovery-003-handoff-\d{8}t\d{6}z-[0-9a-f]{8}", handoff_id) is None:
        raise OrbitRecovery003Error("handoff_identity_invalid")
    root = claim_root or (DATA_ROOT / "derived/m2-orbit-recovery-003-handoff")
    claim_path = root / f"{handoff_id}.json"
    files = sorted(path for path in root.iterdir() if path.is_file()) if root.is_dir() else []
    if files != [claim_path]:
        raise OrbitRecovery003Error("handoff_claim_inventory_drift")
    claim = load_object(claim_path)
    if (
        claim.get("event") != "owner_handoff_claimed"
        or claim.get("handoff_id") != handoff_id
        or claim.get("source_id") != EXPECTED_SOURCE_ID
        or claim.get("maximum_owner_handoffs") != 1
        or claim.get("authority_consumed") is not True
        or claim.get("credential_reference") != SECRET_REFERENCE
        or claim.get("credential_value_recorded") is not False
    ):
        raise OrbitRecovery003Error("handoff_claim_content_drift")
    return claim


def detached_popen_kwargs(environment: Mapping[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "stdin": subprocess.PIPE,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "cwd": str(ROOT),
        "env": dict(environment),
        "close_fds": True,
    }
    if os.name == "nt":
        result["creationflags"] = getattr(subprocess, "DETACHED_PROCESS", 0x00000008) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
    else:
        result["start_new_session"] = True
    return result


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
        raise OrbitRecovery003Error("handoff_identity_required")
    argv = list(command or build_supervisor_command(str(handoff_id)))
    if any(secret in argument for argument in argv):
        raise OrbitRecovery003Error("secret_present_in_supervisor_command")
    process = popen_factory(argv, **detached_popen_kwargs(sanitized_child_environment(environment or os.environ, secret)))
    if process.stdin is None:
        raise OrbitRecovery003Error("anonymous_pipe_not_created")
    try:
        process.stdin.write(encoded)
        process.stdin.write(b"\n")
        process.stdin.flush()
    except (BrokenPipeError, OSError) as exc:
        raise OrbitRecovery003Error("secret_handoff_failed") from exc
    finally:
        process.stdin.close()
        for index in range(len(encoded)):
            encoded[index] = 0
    if not isinstance(process.pid, int) or process.pid <= 0:
        raise OrbitRecovery003Error("detached_supervisor_pid_invalid")
    return process.pid


def validate_approval() -> dict[str, Any]:
    if sha256_file(ROOT / APPROVAL_REF) != APPROVAL_SHA256 or sha256_file(ROOT / RECONCILIATION_REF) != RECONCILIATION_SHA256:
        raise OrbitRecovery003Error("approval_or_reconciliation_hash_drift")
    approval = load_object(ROOT / APPROVAL_REF)
    reconciliation = load_object(ROOT / RECONCILIATION_REF)
    if (
        approval.get("status") != "approved_exact_evidence_first_recovery_only_implementation_and_one_future_attempt"
        or approval.get("review_bundle_manifest_sha256") != BUNDLE_SHA256
        or approval.get("proposal_sha256") != PROPOSAL_SHA256
        or approval.get("locked_response_sha256") != "0ff1a6e052ae9eaadbea2c55334da54509fe877f9bfd0e637dca4c17eed68804"
        or approval.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}
        or approval.get("human_decisions_fabricated") is not False
        or reconciliation.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}
        or reconciliation.get("human_decisions_fabricated") is not False
    ):
        raise OrbitRecovery003Error("approval_or_reconciliation_scope_drift")
    return approval


def require_original_failure(intake: dict[str, Any]) -> dict[str, Any]:
    matches = [item for item in intake.get("assets", []) if item.get("extensions", {}).get("source_id") == EXPECTED_SOURCE_ID]
    if len(matches) != 1:
        raise OrbitRecovery003Error("original_orbit_asset_absent_or_ambiguous")
    asset = matches[0]
    attempts = asset.get("attempts", [])
    if (
        asset.get("asset_id") != EXPECTED_ASSET_ID
        or asset.get("state") != "failed"
        or len(attempts) != 1
        or attempts[0].get("attempt_id") != ORIGINAL_ATTEMPT_ID
        or attempts[0].get("outcome") != "failed"
        or asset.get("failure", {}).get("code") != "orbit_redirect_or_http_status_rejected"
        or asset.get("expected", {}).get("size_bytes") != EXPECTED_SIZE_BYTES
        or asset.get("extensions", {}).get("provider_product_id") != EXPECTED_PROVIDER_PRODUCT_ID
        or asset.get("extensions", {}).get("exact_product_name") != EXPECTED_PRODUCT_NAME
        or asset.get("destination_relative_path") != EXPECTED_DESTINATION_RELATIVE
    ):
        raise OrbitRecovery003Error("original_orbit_failure_identity_drift")
    if (
        sha256_file(ROOT / ORIGINAL_RECEIPT_REF) != ORIGINAL_RECEIPT_SHA256
        or sha256_file(ROOT / ORIGINAL_RECONCILIATION_REF) != ORIGINAL_RECONCILIATION_SHA256
    ):
        raise OrbitRecovery003Error("original_orbit_failure_evidence_drift")
    reconciliation = load_object(ROOT / ORIGINAL_RECONCILIATION_REF)
    for key in ("external_started_event_path", "external_failed_event_path"):
        path = Path(reconciliation["outcome"][key])
        expected = reconciliation["outcome"][key.replace("path", "sha256")]
        if not path.is_file() or sha256_file(path) != expected:
            raise OrbitRecovery003Error("original_orbit_external_event_drift")
    if (
        sha256_file(ROOT / RECOVERY_002_OUTCOME_REF) != RECOVERY_002_OUTCOME_SHA256
        or sha256_file(ROOT / RECOVERY_002_TERMINAL_REF) != RECOVERY_002_TERMINAL_SHA256
    ):
        raise OrbitRecovery003Error("recovery_002_terminal_evidence_drift")
    outcome = load_object(ROOT / RECOVERY_002_OUTCOME_REF)
    terminal = load_object(ROOT / RECOVERY_002_TERMINAL_REF)
    if (
        outcome.get("status") != "terminal_pretransfer_supervisor_failure_no_retry"
        or outcome.get("source_id") != EXPECTED_SOURCE_ID
        or outcome.get("attempt_id") is not None
        or outcome.get("assertions", {}).get("recovery_002_authority_consumed") is not True
        or outcome.get("assertions", {}).get("orbit_download_requested") is not False
        or outcome.get("assertions", {}).get("orbit_payload_bytes_received") != 0
        or terminal.get("status") != "terminal_failure_preserved_recovery_003_review_ready"
        or terminal.get("assertions", {}).get("recovery_002_authority_consumed") is not True
    ):
        raise OrbitRecovery003Error("recovery_002_terminal_scope_drift")
    for key in ("supervisor_started", "supervisor_heartbeat", "supervisor_failed"):
        path = Path(outcome["bindings"][f"{key}_ref"])
        if not path.is_file() or sha256_file(path) != outcome["bindings"][f"{key}_sha256"]:
            raise OrbitRecovery003Error("recovery_002_supervisor_evidence_drift")
    if not RECOVERY_002_STAGING_ROOT.is_dir() or not RECOVERY_002_EMPTY_PAYLOAD_PARENT.is_dir():
        raise OrbitRecovery003Error("recovery_002_staging_evidence_missing")
    inventory = sorted(RECOVERY_002_STAGING_ROOT.rglob("*"))
    if inventory != [RECOVERY_002_EMPTY_PAYLOAD_PARENT] or any(path.is_file() for path in inventory):
        raise OrbitRecovery003Error("recovery_002_staging_evidence_drift")
    return asset


def require_exact_contract(contract: dict[str, Any]) -> None:
    if (
        contract.get("contract_version") != "1.0"
        or contract.get("contract_id") != "nepal-m2-orbit-recovery-003"
        or contract.get("status") != "active_one_attempt_final_preflight_pending"
        or contract.get("source_id") != EXPECTED_SOURCE_ID
        or contract.get("provider_product_id") != EXPECTED_PROVIDER_PRODUCT_ID
        or contract.get("exact_product_name") != EXPECTED_PRODUCT_NAME
        or contract.get("download_url") != EXPECTED_DOWNLOAD_URL
        or contract.get("expected_size_bytes") != EXPECTED_SIZE_BYTES
        or contract.get("expected_md5") != EXPECTED_MD5
        or contract.get("expected_blake3") != EXPECTED_BLAKE3
        or contract.get("staging_root") != EXPECTED_STAGING_ROOT
        or contract.get("staging_relative_path") != EXPECTED_STAGING_RELATIVE
        or contract.get("destination_relative_path") != EXPECTED_DESTINATION_RELATIVE
        or contract.get("attempt_event_root") != EXPECTED_ATTEMPT_EVENT_ROOT
        or contract.get("supervisor_root") != EXPECTED_SUPERVISOR_ROOT
        or contract.get("handoff_claim_root") != EXPECTED_HANDOFF_CLAIM_ROOT
        or contract.get("attempt_prefix") != EXPECTED_ATTEMPT_PREFIX
        or contract.get("restart_offset_bytes") != 0
        or contract.get("resume_partial") is not False
        or contract.get("maximum_real_attempts") != 1
        or contract.get("maximum_owner_handoffs") != 1
        or contract.get("automatic_retry_authorized") is not False
        or contract.get("secret_transport") != SECRET_REFERENCE
    ):
        raise OrbitRecovery003Error("recovery_contract_drift")


class SupervisorJournal:
    """Write only nonsecret lifecycle evidence outside Git."""

    def __init__(self, event_root: Path, supervisor_id: str, interval_seconds: float = 30.0):
        self.event_root = event_root
        self.supervisor_id = supervisor_id
        self.interval_seconds = interval_seconds
        self.started_at = now_utc()
        self.phase = "starting"
        self.attempt_id: str | None = None
        self.bytes_written = 0
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    @property
    def started_path(self) -> Path:
        return self.event_root / f"{self.supervisor_id}-started.json"

    @property
    def heartbeat_path(self) -> Path:
        return self.event_root / f"{self.supervisor_id}-heartbeat.json"

    def terminal_path(self, outcome: str) -> Path:
        return self.event_root / f"{self.supervisor_id}-{outcome}.json"

    def _snapshot(self, event: str) -> dict[str, Any]:
        with self._lock:
            return {
                "schema_version": "1.0",
                "event": event,
                "supervisor_id": self.supervisor_id,
                "source_id": EXPECTED_SOURCE_ID,
                "process_id": os.getpid(),
                "started_at": self.started_at,
                "observed_at": now_utc(),
                "phase": self.phase,
                "attempt_id": self.attempt_id,
                "bytes_written": self.bytes_written,
                "credential_reference": SECRET_REFERENCE,
                "credential_value_recorded": False,
            }

    def start(self) -> None:
        self.event_root.mkdir(parents=True, exist_ok=False)
        write_new_json(self.started_path, self._snapshot("supervisor_started"))
        self._write_heartbeat()
        self._thread = threading.Thread(target=self._heartbeat_loop, name="orbit-recovery-003-heartbeat", daemon=True)
        self._thread.start()

    def update(self, *, phase: str, attempt_id: str | None = None, bytes_written: int | None = None) -> None:
        with self._lock:
            self.phase = phase
            if attempt_id is not None:
                self.attempt_id = attempt_id
            if bytes_written is not None:
                self.bytes_written = int(bytes_written)

    def _write_heartbeat(self) -> None:
        payload = self._snapshot("supervisor_heartbeat")
        temporary = self.heartbeat_path.with_name(f"{self.heartbeat_path.name}.{os.getpid()}-{time.monotonic_ns()}.tmp")
        with temporary.open("xb") as stream:
            stream.write(canonical_bytes(payload))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, self.heartbeat_path)

    def _heartbeat_loop(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            try:
                self._write_heartbeat()
            except OSError:
                return

    def finish(self, outcome: str, code: str) -> Path:
        if outcome not in {"succeeded", "failed"}:
            raise OrbitRecovery003Error("supervisor_terminal_outcome_invalid")
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(1.0, self.interval_seconds * 2))
        payload = self._snapshot(f"supervisor_{outcome}")
        payload.update({"completed_at": now_utc(), "terminal_code": code, "retry_automatically_authorized": False})
        path = self.terminal_path(outcome)
        write_new_json(path, payload)
        return path
