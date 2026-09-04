#!/usr/bin/env python3
"""Pure controls for the approved secret-safe Sentinel recovery-002 route."""

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
from pathlib import Path
from typing import Any, BinaryIO, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent.resolve()
DATA_ROOT = PROJECT_ROOT / "nepal-2026-before-after-map-data"

EXPECTED_SOURCE_ID = "M1-SRC-004"
EXPECTED_ASSET_ID = "m1-src-004-recovery-002"
EXPECTED_INTAKE_ID = "nepal-m2-sentinel-recovery-002"
EXPECTED_DESTINATION = (
    "products/m1-src-004/"
    "S1D_IW_GRDH_1SDV_20260828T122116_20260828T122141_004326_007FA4_C523.SAFE.zip"
)
EXPECTED_STAGING = (
    "m1-src-004-recovery-002/"
    "S1D_IW_GRDH_1SDV_20260828T122116_20260828T122141_004326_007FA4_C523.SAFE.zip.part"
)
EXPECTED_PROVIDER_PRODUCT_ID = "641ccb0b-5d88-4c44-b558-93b488cd2453"
EXPECTED_SOURCE_URI = "https://download.dataspace.copernicus.eu/odata/v1/Products(641ccb0b-5d88-4c44-b558-93b488cd2453)/$value"
EXPECTED_PRODUCT_ID = "S1D_IW_GRDH_1SDV_20260828T122116_20260828T122141_004326_007FA4_C523.SAFE"
EXPECTED_SIZE_BYTES = 1_732_332_897
EXPECTED_PROVIDER_MD5 = "25c895490c9b786507152513cc701911"
EXPECTED_PROVIDER_BLAKE3 = "314087e342f011c95ec9b8b520d0baae5272396bd3e2e16b9525bd1c5eba0920"

ORIGINAL_ATTEMPT_ID = "m1-src-004-20260904t043930z-ac125c11"
ORIGINAL_PARTIAL_BYTES = 561_593_598
ORIGINAL_PARTIAL_SHA256 = "299b2d07ccb58747cce43ae3b18e6d25c1c6d72a5653831b50a44ca72677ea66"
RECOVERY_001_ATTEMPT_ID = "m1-src-004-recovery-001-20260904t201220z-e4388c64"
RECOVERY_001_PARTIAL_BYTES = 1_333_788_672
RECOVERY_001_PARTIAL_SHA256 = "c2d3a878f98615ddaa5e0bf21df5eb5f65c591719cb26b5f43b361aa4eac4cac"

EXPECTED_BUNDLE_SHA256 = "30d0f72c4c62b3c5450a08459a1c6024d442b8f718fa11f0fb650719437e9a30"
EXPECTED_PROPOSAL_SHA256 = "1ec77963e1171f60c2a4571306797077eb65206f5a4aacff6dd9cae33b0c0f6e"
EXPECTED_RESPONSE_SHA256 = "8033a825dfc58f4e684e753536f99b4e761f76d77cacd760da9d182d9ae23f46"
EXPECTED_APPROVAL_SHA256 = "ab0333e6a7f460c150de7f064faac617082f4a627034932fd4ad187f164dde34"
EXPECTED_RECONCILIATION_SHA256 = "1ab8ebe5ea62da89d8d0ca2d80c9614a80a05a020295f4ec978e6f380be526d9"

APPROVAL_REF = "records/source-gates/m2-sentinel-recovery-002-approval.json"
RECONCILIATION_REF = "records/source-gates/m2-sentinel-recovery-002-review-reconciliation.json"
PROPOSAL_REF = "contracts/milestone-002-sentinel-recovery-002-proposal.json"
BUNDLE_REF = "reviews/m2-sentinel-recovery-002/review-bundle.json"
CONTRACT_REF = "contracts/m2-sentinel-recovery-002.json"
PUBLICATION_GATE_REF = "records/acquisition/sentinel-recovery-002-publication-gate.json"
FINAL_PREFLIGHT_REF = "records/acquisition/sentinel-recovery-002-final-preflight.json"

MAX_SECRET_BYTES = 16_384
SECRET_REFERENCE = "anonymous_pipe_single_use_memory_only"
UTC_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


class Recovery002ControlError(RuntimeError):
    """A recovery-002 fail-closed guard rejected the operation."""

    def __init__(self, code: str):
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
        raise Recovery002ControlError("control_root_not_object")
    return value


def write_new_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_bytes(value)
    try:
        with path.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise Recovery002ControlError("output_collision") from exc


def replace_json(path: Path, value: dict[str, Any], nonce: str) -> None:
    temporary = path.with_name(f"{path.name}.{nonce}.tmp")
    if temporary.exists():
        raise Recovery002ControlError("temporary_control_path_exists")
    with temporary.open("xb") as handle:
        handle.write(canonical_bytes(value))
        handle.flush()
        os.fsync(handle.fileno())
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
        raise Recovery002ControlError("path_outside_controlled_root") from exc
    if resolved_candidate == resolved_root:
        raise Recovery002ControlError("path_must_be_child")
    current = resolved_candidate.parent
    while True:
        if current.exists() and is_reparse_point(current):
            raise Recovery002ControlError("reparse_point_in_path")
        if current == resolved_root:
            break
        if current == current.parent:
            raise Recovery002ControlError("path_ancestor_escape")
        current = current.parent
    return resolved_candidate


def validate_approval(approval: dict[str, Any], reconciliation: dict[str, Any]) -> None:
    if (
        approval.get("status") != "approved_exact_bounded_secret_safe_detached_recovery"
        or approval.get("review_bundle_manifest_sha256") != EXPECTED_BUNDLE_SHA256
        or approval.get("recovery_proposal_sha256") != EXPECTED_PROPOSAL_SHA256
        or approval.get("locked_response_sha256") != EXPECTED_RESPONSE_SHA256
        or approval.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}
        or approval.get("human_decisions_fabricated") is not False
        or reconciliation.get("status") != "reconciled_exact_human_response"
        or reconciliation.get("response_sha256") != EXPECTED_RESPONSE_SHA256
        or reconciliation.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}
        or reconciliation.get("human_decisions_fabricated") is not False
    ):
        raise Recovery002ControlError("recovery_002_approval_or_reconciliation_drift")


def require_exact_contract(contract: dict[str, Any]) -> dict[str, Any]:
    if contract.get("contract_version") != "1.0" or contract.get("intake_id") != EXPECTED_INTAKE_ID:
        raise Recovery002ControlError("recovery_002_contract_identity_drift")
    if (
        contract.get("collision_policy") != "fail"
        or contract.get("promotion_mode") != "atomic-no-replace"
        or contract.get("secret_policy") != SECRET_REFERENCE
        or contract.get("custody_root") != "nepal-2026-before-after-map-data/custody"
        or contract.get("staging_root") != f"nepal-2026-before-after-map-data/.intake-staging/{EXPECTED_INTAKE_ID}"
    ):
        raise Recovery002ControlError("recovery_002_contract_safety_drift")
    assets = contract.get("assets")
    if not isinstance(assets, list) or len(assets) != 1:
        raise Recovery002ControlError("recovery_002_asset_count_drift")
    asset = assets[0]
    extensions = asset.get("extensions", {})
    checksums = {
        str(item.get("Algorithm", "")).upper(): str(item.get("Value", "")).casefold()
        for item in extensions.get("provider_checksums", [])
        if isinstance(item, dict)
    }
    if (
        asset.get("asset_id") != EXPECTED_ASSET_ID
        or asset.get("source") != {
            "kind": "https",
            "uri": EXPECTED_SOURCE_URI,
            "authorization_ref": APPROVAL_REF,
            "terms_ref": "https://dataspace.copernicus.eu/terms-and-conditions",
            "transport_exception_ref": None,
        }
        or extensions.get("source_id") != EXPECTED_SOURCE_ID
        or extensions.get("provider_product_id") != EXPECTED_PROVIDER_PRODUCT_ID
        or extensions.get("exact_product_id") != EXPECTED_PRODUCT_ID
        or extensions.get("catalog_content_length_bytes") != EXPECTED_SIZE_BYTES
        or checksums != {"MD5": EXPECTED_PROVIDER_MD5, "BLAKE3": EXPECTED_PROVIDER_BLAKE3}
        or asset.get("destination_relative_path") != EXPECTED_DESTINATION
        or asset.get("staging_relative_path") != EXPECTED_STAGING
        or asset.get("state") not in {"authorized", "staging", "promoted", "failed"}
    ):
        raise Recovery002ControlError("recovery_002_asset_identity_or_path_drift")
    root_extensions = contract.get("extensions", {})
    if (
        root_extensions.get("restart_offset_bytes") != 0
        or root_extensions.get("resume_any_partial") is not False
        or root_extensions.get("delete_or_modify_any_partial") is not False
        or root_extensions.get("reuse_any_prior_staging_path") is not False
        or root_extensions.get("maximum_real_transfer_attempts") != 1
        or root_extensions.get("detached_supervisor_required") is not True
        or root_extensions.get("secret_transport") != SECRET_REFERENCE
    ):
        raise Recovery002ControlError("recovery_002_method_boundary_drift")
    return asset


def require_fresh_authorized_attempt(asset: dict[str, Any]) -> None:
    if asset.get("state") != "authorized" or asset.get("attempts") != []:
        raise Recovery002ControlError("recovery_002_not_fresh_authorized")


def require_retained_partial(path: Path, expected_size: int, expected_sha256: str, code: str) -> None:
    try:
        path.resolve(strict=True).relative_to(DATA_ROOT.resolve(strict=True))
    except (FileNotFoundError, ValueError) as exc:
        raise Recovery002ControlError(f"{code}_path_invalid") from exc
    if not path.is_file() or path.stat().st_size != expected_size or sha256_file(path) != expected_sha256:
        raise Recovery002ControlError(f"{code}_identity_drift")


def retained_partial_paths(active_intake: dict[str, Any], recovery_001: dict[str, Any]) -> tuple[Path, Path]:
    original_assets = [
        item for item in active_intake.get("assets", [])
        if item.get("extensions", {}).get("source_id") == EXPECTED_SOURCE_ID
    ]
    recovery_assets = recovery_001.get("assets", [])
    if len(original_assets) != 1 or len(recovery_assets) != 1:
        raise Recovery002ControlError("retained_failure_asset_count_drift")
    original = original_assets[0]
    recovery = recovery_assets[0]
    if (
        original.get("state") != "failed"
        or original.get("attempts", [{}])[0].get("attempt_id") != ORIGINAL_ATTEMPT_ID
        or recovery.get("state") != "failed"
        or recovery.get("attempts", [{}])[0].get("attempt_id") != RECOVERY_001_ATTEMPT_ID
    ):
        raise Recovery002ControlError("retained_failure_history_drift")
    original_event = Path(original["attempts"][0]["extensions"]["external_started_event"])
    original_path = Path(load_object(original_event)["staging_path"])
    recovery_event = Path(recovery["attempts"][0]["extensions"]["external_started_event"])
    recovery_path = Path(load_object(recovery_event)["staging_path"])
    return original_path, recovery_path


def verify_both_retained_partials(active_intake: dict[str, Any], recovery_001: dict[str, Any]) -> tuple[Path, Path]:
    original_path, recovery_path = retained_partial_paths(active_intake, recovery_001)
    require_retained_partial(original_path, ORIGINAL_PARTIAL_BYTES, ORIGINAL_PARTIAL_SHA256, "original_partial")
    require_retained_partial(recovery_path, RECOVERY_001_PARTIAL_BYTES, RECOVERY_001_PARTIAL_SHA256, "recovery_001_partial")
    return original_path, recovery_path


def sanitized_child_environment(source: Mapping[str, str], secret: str) -> dict[str, str]:
    if not isinstance(secret, str) or not secret:
        raise Recovery002ControlError("secret_missing")
    cleaned: dict[str, str] = {}
    for key, value in source.items():
        upper = key.upper()
        if upper in {"CDSE_ACCESS_TOKEN", "COPERNICUS_ACCESS_TOKEN", "AUTHORIZATION"}:
            continue
        if secret in key or secret in value:
            continue
        cleaned[key] = value
    if any(secret in key or secret in value for key, value in cleaned.items()):
        raise Recovery002ControlError("secret_present_in_child_environment")
    return cleaned


def validate_secret(secret: str) -> bytes:
    if not isinstance(secret, str) or not secret:
        raise Recovery002ControlError("secret_missing")
    if any(ch.isspace() for ch in secret):
        raise Recovery002ControlError("secret_contains_whitespace")
    encoded = secret.encode("utf-8")
    if len(encoded) > MAX_SECRET_BYTES:
        raise Recovery002ControlError("secret_too_large")
    return encoded


def build_supervisor_command(
    python_executable: str | None = None,
    supervisor_path: Path | None = None,
) -> list[str]:
    return [
        python_executable or sys.executable,
        str(supervisor_path or ROOT / "scripts/m2_sentinel_recovery_002_supervisor.py"),
        "--source-id",
        EXPECTED_SOURCE_ID,
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
    if any(secret in part for part in argv):
        raise Recovery002ControlError("secret_present_in_supervisor_command")
    child_environment = sanitized_child_environment(environment or os.environ, secret)
    process = popen_factory(argv, **detached_popen_kwargs(child_environment))
    if process.stdin is None:
        raise Recovery002ControlError("anonymous_pipe_not_created")
    try:
        process.stdin.write(encoded)
        process.stdin.write(b"\n")
        process.stdin.flush()
    except (BrokenPipeError, OSError) as exc:
        raise Recovery002ControlError("secret_handoff_failed") from exc
    finally:
        process.stdin.close()
        for index in range(len(encoded)):
            encoded[index] = 0
    if not isinstance(process.pid, int) or process.pid <= 0:
        raise Recovery002ControlError("detached_supervisor_pid_invalid")
    return process.pid


def read_single_use_secret(stream: BinaryIO) -> str:
    try:
        data = stream.readline(MAX_SECRET_BYTES + 2)
    finally:
        stream.close()
    if not data or not data.endswith(b"\n") or len(data) > MAX_SECRET_BYTES + 1:
        raise Recovery002ControlError("secret_pipe_payload_invalid")
    raw = bytearray(data[:-1])
    try:
        secret = raw.decode("utf-8")
        validate_secret(secret)
        return secret
    except UnicodeDecodeError as exc:
        raise Recovery002ControlError("secret_pipe_encoding_invalid") from exc
    finally:
        for index in range(len(raw)):
            raw[index] = 0


class SupervisorJournal:
    """Write only nonsecret supervisor lifecycle evidence outside Git."""

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
        self._thread = threading.Thread(target=self._heartbeat_loop, name="recovery-002-heartbeat", daemon=True)
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
        nonce = f"{os.getpid()}-{time.monotonic_ns()}"
        temporary = self.heartbeat_path.with_name(f"{self.heartbeat_path.name}.{nonce}.tmp")
        with temporary.open("xb") as handle:
            handle.write(canonical_bytes(payload))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, self.heartbeat_path)

    def _heartbeat_loop(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            try:
                self._write_heartbeat()
            except OSError:
                return

    def finish(self, outcome: str, code: str) -> Path:
        if outcome not in {"succeeded", "failed"}:
            raise Recovery002ControlError("supervisor_terminal_outcome_invalid")
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(1.0, self.interval_seconds * 2))
        payload = self._snapshot(f"supervisor_{outcome}")
        payload.update({"completed_at": now_utc(), "terminal_code": code, "retry_automatically_authorized": False})
        path = self.terminal_path(outcome)
        write_new_json(path, payload)
        return path


def classify_supervisor_state(
    *,
    started: Mapping[str, Any] | None,
    heartbeat: Mapping[str, Any] | None,
    terminal_events: Sequence[Mapping[str, Any]],
    process_alive: bool,
) -> dict[str, Any]:
    if not isinstance(started, Mapping) or started.get("event") != "supervisor_started":
        return {"status": "invalid", "reason": "supervisor start evidence missing"}
    supervisor_id = started.get("supervisor_id")
    if not isinstance(supervisor_id, str) or not supervisor_id:
        return {"status": "invalid", "reason": "supervisor identity missing"}
    matching = [item for item in terminal_events if item.get("supervisor_id") == supervisor_id]
    if len(matching) > 1:
        return {"status": "invalid", "reason": "multiple terminal supervisor events"}
    if len(matching) == 1:
        event = matching[0].get("event")
        if event not in {"supervisor_succeeded", "supervisor_failed"}:
            return {"status": "invalid", "reason": "terminal event type invalid"}
        return {"status": "terminal_success" if event == "supervisor_succeeded" else "terminal_failure", "supervisor_id": supervisor_id}
    if process_alive:
        if not isinstance(heartbeat, Mapping) or heartbeat.get("supervisor_id") != supervisor_id:
            return {"status": "running_without_current_heartbeat", "supervisor_id": supervisor_id}
        return {"status": "running", "supervisor_id": supervisor_id, "phase": heartbeat.get("phase")}
    return {
        "status": "reconcile_absent_process_without_terminal",
        "supervisor_id": supervisor_id,
        "failure_code": "detached_supervisor_absent_before_terminal_event",
    }


def process_is_alive(process_id: int) -> bool:
    if not isinstance(process_id, int) or process_id <= 0:
        return False
    if os.name == "nt":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {process_id}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return result.returncode == 0 and f'"{process_id}"' in result.stdout
    try:
        os.kill(process_id, 0)
    except (ProcessLookupError, PermissionError):
        return False
    return True
