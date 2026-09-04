from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from acquire_m2_sentinel_recovery_002 import stream_to_exclusive_staging_with_progress  # noqa: E402
from m2_sentinel_recovery_002_core import (  # noqa: E402
    EXPECTED_APPROVAL_SHA256,
    EXPECTED_ASSET_ID,
    EXPECTED_DESTINATION,
    EXPECTED_INTAKE_ID,
    EXPECTED_PROVIDER_BLAKE3,
    EXPECTED_PROVIDER_MD5,
    EXPECTED_PROVIDER_PRODUCT_ID,
    EXPECTED_PRODUCT_ID,
    EXPECTED_SIZE_BYTES,
    EXPECTED_SOURCE_ID,
    EXPECTED_SOURCE_URI,
    EXPECTED_STAGING,
    APPROVAL_REF,
    Recovery002ControlError,
    SupervisorJournal,
    classify_supervisor_state,
    launch_detached_supervisor,
    load_object,
    read_single_use_secret,
    require_exact_contract,
    require_safe_child,
    sanitized_child_environment,
    sha256_file,
    validate_approval,
    validate_secret,
)
from m2_transfer_core import NoRedirectHandler, TransferControlError, promote_atomic_no_replace  # noqa: E402


class _CaptureStdin(io.BytesIO):
    def close(self) -> None:
        self.captured = self.getvalue()
        super().close()


class _FakeProcess:
    pid = 43210

    def __init__(self) -> None:
        self.stdin = _CaptureStdin()


class Recovery002Tests(unittest.TestCase):
    def test_exact_locked_approval_and_reconciliation_validate(self) -> None:
        approval_path = ROOT / "records/source-gates/m2-sentinel-recovery-002-approval.json"
        reconciliation_path = ROOT / "records/source-gates/m2-sentinel-recovery-002-review-reconciliation.json"
        self.assertEqual(sha256_file(approval_path), EXPECTED_APPROVAL_SHA256)
        validate_approval(load_object(approval_path), load_object(reconciliation_path))

    def test_recovery_contract_rejects_source_or_checksum_drift(self) -> None:
        contract = {
            "contract_version": "1.0",
            "intake_id": EXPECTED_INTAKE_ID,
            "collision_policy": "fail",
            "promotion_mode": "atomic-no-replace",
            "secret_policy": "anonymous_pipe_single_use_memory_only",
            "custody_root": "nepal-2026-before-after-map-data/custody",
            "staging_root": f"nepal-2026-before-after-map-data/.intake-staging/{EXPECTED_INTAKE_ID}",
            "assets": [{
                "asset_id": EXPECTED_ASSET_ID,
                "source": {"kind": "https", "uri": EXPECTED_SOURCE_URI, "authorization_ref": APPROVAL_REF, "terms_ref": "https://dataspace.copernicus.eu/terms-and-conditions", "transport_exception_ref": None},
                "destination_relative_path": EXPECTED_DESTINATION,
                "staging_relative_path": EXPECTED_STAGING,
                "state": "authorized",
                "extensions": {"source_id": EXPECTED_SOURCE_ID, "provider_product_id": EXPECTED_PROVIDER_PRODUCT_ID, "exact_product_id": EXPECTED_PRODUCT_ID, "catalog_content_length_bytes": EXPECTED_SIZE_BYTES, "provider_checksums": [{"Algorithm": "MD5", "Value": EXPECTED_PROVIDER_MD5}, {"Algorithm": "BLAKE3", "Value": EXPECTED_PROVIDER_BLAKE3}]},
            }],
            "extensions": {"restart_offset_bytes": 0, "resume_any_partial": False, "delete_or_modify_any_partial": False, "reuse_any_prior_staging_path": False, "maximum_real_transfer_attempts": 1, "detached_supervisor_required": True, "secret_transport": "anonymous_pipe_single_use_memory_only"},
        }
        require_exact_contract(contract)
        contract["assets"][0]["source"]["uri"] += "-drift"
        with self.assertRaisesRegex(Recovery002ControlError, "asset_identity_or_path_drift"):
            require_exact_contract(contract)

    def test_secret_validation_and_single_use_pipe_fail_closed(self) -> None:
        for value in ("", "contains space", "contains\nnewline"):
            with self.assertRaises(Recovery002ControlError):
                validate_secret(value)
        stream = io.BytesIO(b"fixture-secret\n")
        self.assertEqual(read_single_use_secret(stream), "fixture-secret")
        self.assertTrue(stream.closed)

    def test_secret_only_enters_anonymous_pipe_not_command_or_environment(self) -> None:
        secret = "runtime-fixture-" + uuid.uuid4().hex
        captured: dict[str, object] = {}

        def factory(argv: list[str], **kwargs: object) -> _FakeProcess:
            captured["argv"] = argv
            captured["env"] = kwargs["env"]
            process = _FakeProcess()
            captured["process"] = process
            return process

        pid = launch_detached_supervisor(
            secret,
            command=[sys.executable, "synthetic-worker.py"],
            environment={"SAFE": "yes", "CDSE_ACCESS_TOKEN": "old-value", "BAD": f"prefix-{secret}"},
            popen_factory=factory,
        )
        self.assertEqual(pid, 43210)
        self.assertNotIn(secret, json.dumps(captured["argv"]))
        self.assertNotIn(secret, json.dumps(captured["env"]))
        self.assertNotIn("CDSE_ACCESS_TOKEN", captured["env"])
        self.assertEqual(captured["process"].stdin.captured, (secret + "\n").encode())

    def test_sanitized_child_environment_removes_secret_references(self) -> None:
        secret = "dynamic-" + uuid.uuid4().hex
        result = sanitized_child_environment(
            {"OK": "value", "AUTHORIZATION": "Bearer other", "LEAK": secret, secret: "bad"}, secret
        )
        self.assertEqual(result, {"OK": "value"})

    def test_progress_stream_exact_size_md5_collision_and_failure_preservation(self) -> None:
        payload = b"controlled-recovery-fixture" * 97
        observed: list[int] = []
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stage = root / "asset.part"
            result = stream_to_exclusive_staging_with_progress(
                io.BytesIO(payload),
                stage,
                expected_size=len(payload),
                expected_md5=hashlib.md5(payload, usedforsecurity=False).hexdigest(),
                progress_callback=observed.append,
            )
            self.assertEqual(result["sha256"], hashlib.sha256(payload).hexdigest())
            self.assertEqual(observed[-1], len(payload))
            with self.assertRaisesRegex(TransferControlError, "staging_collision"):
                stream_to_exclusive_staging_with_progress(
                    io.BytesIO(b"new"), stage, expected_size=3, expected_md5=hashlib.md5(b"new", usedforsecurity=False).hexdigest()
                )
            self.assertEqual(stage.read_bytes(), payload)

        with tempfile.TemporaryDirectory() as temporary:
            stage = Path(temporary) / "short.part"
            with self.assertRaisesRegex(TransferControlError, "transferred_size_mismatch"):
                stream_to_exclusive_staging_with_progress(
                    io.BytesIO(b"short"), stage, expected_size=6, expected_md5=hashlib.md5(b"short", usedforsecurity=False).hexdigest()
                )
            self.assertEqual(stage.read_bytes(), b"short")

    def test_redirect_refusal_and_atomic_no_replace(self) -> None:
        self.assertIsNone(NoRedirectHandler().redirect_request(None, None, 302, "Found", {}, "https://invalid"))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            staged, destination = root / "x.part", root / "x.zip"
            staged.write_bytes(b"new")
            destination.write_bytes(b"old")
            with self.assertRaisesRegex(TransferControlError, "destination_collision"):
                promote_atomic_no_replace(staged, destination)
            self.assertEqual(staged.read_bytes(), b"new")
            self.assertEqual(destination.read_bytes(), b"old")

    def test_recovery_path_containment_and_byte_zero_request_are_fixed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self.assertEqual(require_safe_child(root, root / "inside"), root / "inside")
            with self.assertRaisesRegex(Recovery002ControlError, "path_outside_controlled_root"):
                require_safe_child(root, root.parent / "outside")
        runner = (ROOT / "scripts/acquire_m2_sentinel_recovery_002.py").read_text(encoding="utf-8")
        self.assertNotIn('"Range"', runner)
        self.assertIn('"Accept-Encoding": "identity"', runner)

    def test_supervisor_journal_has_heartbeat_and_exactly_one_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            event_root = Path(temporary) / "events"
            journal = SupervisorJournal(event_root, "synthetic-supervisor", interval_seconds=0.02)
            journal.start()
            journal.update(phase="synthetic_child", attempt_id="attempt-1", bytes_written=42)
            time.sleep(0.05)
            terminal = journal.finish("failed", "synthetic_child_exit")
            self.assertTrue(journal.started_path.is_file())
            self.assertTrue(journal.heartbeat_path.is_file())
            self.assertTrue(terminal.is_file())
            self.assertEqual(len(list(event_root.glob("*-failed.json"))), 1)
            self.assertFalse(load_object(terminal)["credential_value_recorded"])

    def test_absent_worker_is_independently_reconcilable(self) -> None:
        started = {"event": "supervisor_started", "supervisor_id": "s-1"}
        result = classify_supervisor_state(started=started, heartbeat=None, terminal_events=[], process_alive=False)
        self.assertEqual(result["status"], "reconcile_absent_process_without_terminal")
        self.assertEqual(result["failure_code"], "detached_supervisor_absent_before_terminal_event")

    @unittest.skipUnless(os.name == "nt", "Windows detached-process behavior is the deployment target")
    def test_forced_broker_termination_does_not_end_detached_worker(self) -> None:
        secret = "runtime-detach-" + uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            worker = root / "worker.py"
            helper = root / "helper.py"
            child_pid = root / "child.pid"
            terminal = root / "terminal.json"
            worker.write_text(
                "import hashlib,json,os,sys,time\n"
                "secret=sys.stdin.buffer.readline().strip()\n"
                "open(sys.argv[1],'w').write(str(os.getpid()))\n"
                "time.sleep(1.0)\n"
                "json.dump({'status':'terminal','digest':hashlib.sha256(secret).hexdigest()},open(sys.argv[2],'w'))\n",
                encoding="utf-8",
            )
            helper.write_text(
                "import sys,time\n"
                f"sys.path.insert(0,{str(ROOT / 'scripts')!r})\n"
                "from m2_sentinel_recovery_002_core import launch_detached_supervisor\n"
                "secret=sys.stdin.readline().strip()\n"
                "launch_detached_supervisor(secret,command=[sys.executable,sys.argv[1],sys.argv[2],sys.argv[3]])\n"
                "time.sleep(30)\n",
                encoding="utf-8",
            )
            broker = subprocess.Popen(
                [sys.executable, str(helper), str(worker), str(child_pid), str(terminal)],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            assert broker.stdin is not None
            broker.stdin.write(secret + "\n")
            broker.stdin.flush()
            broker.stdin.close()
            deadline = time.time() + 10
            while time.time() < deadline and not child_pid.exists():
                time.sleep(0.05)
            self.assertTrue(child_pid.exists())
            broker.terminate()
            broker.wait(timeout=5)
            deadline = time.time() + 10
            while time.time() < deadline and not terminal.exists():
                time.sleep(0.05)
            self.assertTrue(terminal.exists())
            self.assertNotIn(secret, terminal.read_text(encoding="utf-8"))
            self.assertNotIn(secret, " ".join([sys.executable, str(worker), str(child_pid), str(terminal)]))

    def test_new_source_files_do_not_read_token_from_environment_or_cli(self) -> None:
        paths = [
            ROOT / "scripts/m2_sentinel_recovery_002_broker.py",
            ROOT / "scripts/m2_sentinel_recovery_002_supervisor.py",
            ROOT / "scripts/acquire_m2_sentinel_recovery_002.py",
            ROOT / "scripts/acquire_m2_product_secret_pipe.py",
        ]
        bodies = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        self.assertNotIn('os.environ.get("CDSE_ACCESS_TOKEN")', bodies)
        self.assertNotIn("--token", bodies)
        self.assertNotIn("--access-token", bodies)


if __name__ == "__main__":
    unittest.main()
