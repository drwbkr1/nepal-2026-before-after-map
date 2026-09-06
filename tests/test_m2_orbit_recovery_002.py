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
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import verify_m2_orbit_eof as verifier  # noqa: E402
from acquire_m2_orbit_recovery_002 import download_headers, main as runner_main  # noqa: E402
from m2_orbit_recovery_002_core import (  # noqa: E402
    APPROVAL_SHA256,
    EXPECTED_ATTEMPT_PREFIX,
    EXPECTED_DESTINATION_RELATIVE,
    EXPECTED_PRODUCT_NAME,
    EXPECTED_PROVIDER_PRODUCT_ID,
    EXPECTED_SIZE_BYTES,
    EXPECTED_SOURCE_ID,
    EXPECTED_STAGING_ROOT,
    OrbitRecovery002Error,
    SupervisorJournal,
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


class _CaptureStdin(io.BytesIO):
    def close(self) -> None:
        self.captured = self.getvalue()
        super().close()


class _FakeProcess:
    pid = 43210

    def __init__(self) -> None:
        self.stdin = _CaptureStdin()


class OrbitRecovery002Tests(unittest.TestCase):
    def test_exact_locked_approval_and_reconciliation_validate(self) -> None:
        self.assertEqual(sha256_file(ROOT / "records/source-gates/m2-orbit-recovery-002-approval.json"), APPROVAL_SHA256)
        approval = validate_approval()
        self.assertEqual(approval["authorized_recovery"]["source_id"], EXPECTED_SOURCE_ID)
        self.assertEqual(approval["decision_counts"], {"approve": 1, "revise": 0, "defer": 0})

    def test_contract_is_exact_and_rejects_broadened_source(self) -> None:
        contract = {
            "contract_version": "1.0", "contract_id": "nepal-m2-orbit-recovery-002",
            "status": "active_one_attempt_final_preflight_pending", "source_id": EXPECTED_SOURCE_ID,
            "provider_product_id": EXPECTED_PROVIDER_PRODUCT_ID, "exact_product_name": EXPECTED_PRODUCT_NAME,
            "download_url": f"https://download.dataspace.copernicus.eu/odata/v1/Products({EXPECTED_PROVIDER_PRODUCT_ID})/$value",
            "expected_size_bytes": EXPECTED_SIZE_BYTES, "expected_md5": "ca7f36b1892073c883c4cff5c0517b9c",
            "expected_blake3": "ce824099fa812d6c229bd5bef2d4a70d7185d248f91ec3111ce557868ab1269b",
            "staging_root": EXPECTED_STAGING_ROOT,
            "staging_relative_path": f"{EXPECTED_ATTEMPT_PREFIX}/{EXPECTED_PRODUCT_NAME}.part",
            "destination_relative_path": EXPECTED_DESTINATION_RELATIVE, "attempt_prefix": EXPECTED_ATTEMPT_PREFIX,
            "restart_offset_bytes": 0, "resume_partial": False, "maximum_real_attempts": 1,
            "automatic_retry_authorized": False, "secret_transport": "anonymous_pipe_single_use_memory_only",
        }
        require_exact_contract(contract)
        contract["source_id"] = "M2-ORB-002"
        with self.assertRaisesRegex(OrbitRecovery002Error, "recovery_contract_drift"):
            require_exact_contract(contract)

    def test_secret_validation_and_single_use_pipe_fail_closed(self) -> None:
        for value in ("", "contains space", "contains\nnewline"):
            with self.assertRaises(OrbitRecovery002Error):
                validate_secret(value)
        stream = io.BytesIO(b"fixture-secret\n")
        self.assertEqual(read_single_use_secret(stream), "fixture-secret")
        self.assertTrue(stream.closed)
        windows_stream = io.BytesIO(b"fixture-secret\r\n")
        self.assertEqual(read_single_use_secret(windows_stream), "fixture-secret")
        self.assertTrue(windows_stream.closed)

    def test_secret_enters_anonymous_pipe_not_command_or_environment(self) -> None:
        secret = "runtime-fixture-" + uuid.uuid4().hex
        captured: dict[str, object] = {}

        def factory(argv: list[str], **kwargs: object) -> _FakeProcess:
            captured["argv"] = argv
            captured["env"] = kwargs["env"]
            process = _FakeProcess()
            captured["process"] = process
            return process

        pid = launch_detached_supervisor(
            secret, command=[sys.executable, "synthetic-worker.py"],
            environment={"SAFE": "yes", "CDSE_ACCESS_TOKEN": "old", "LEAK": secret}, popen_factory=factory,
        )
        self.assertEqual(pid, 43210)
        self.assertNotIn(secret, json.dumps(captured["argv"]))
        self.assertNotIn(secret, json.dumps(captured["env"]))
        self.assertEqual(captured["process"].stdin.captured, (secret + "\n").encode())

    def test_byte_zero_headers_have_no_range_or_compression(self) -> None:
        headers = download_headers("fixture-token")
        self.assertNotIn("Range", headers)
        self.assertEqual(headers["Accept-Encoding"], "identity")
        runner = (ROOT / "scripts/acquire_m2_orbit_recovery_002.py").read_text(encoding="utf-8")
        self.assertNotIn('"Range"', runner)

    def test_paths_are_distinct_contained_and_no_replace_ready(self) -> None:
        self.assertIn("recovery-002", EXPECTED_STAGING_ROOT)
        self.assertTrue(EXPECTED_ATTEMPT_PREFIX.startswith("m2-orb-001-recovery-001"))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self.assertEqual(require_safe_child(root, root / "inside"), root / "inside")
            with self.assertRaisesRegex(OrbitRecovery002Error, "path_outside_controlled_root"):
                require_safe_child(root, root.parent / "outside")

    def test_supervisor_journal_has_nonsecret_heartbeat_and_one_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            event_root = Path(temporary) / "events"
            journal = SupervisorJournal(event_root, "synthetic-supervisor", interval_seconds=0.02)
            journal.start()
            journal.update(phase="synthetic", attempt_id="attempt-1", bytes_written=42)
            time.sleep(0.05)
            terminal = journal.finish("failed", "synthetic_failure")
            self.assertEqual(len(list(event_root.glob("*-failed.json"))), 1)
            self.assertTrue(journal.heartbeat_path.is_file())
            self.assertFalse(load_object(terminal)["credential_value_recorded"])

    @unittest.skipUnless(os.name == "nt", "Windows detached-process behavior is the deployment target")
    def test_forced_broker_termination_does_not_end_detached_worker(self) -> None:
        secret = "runtime-detach-" + uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            worker, helper = root / "worker.py", root / "helper.py"
            child_pid, terminal = root / "child.pid", root / "terminal.json"
            worker.write_text(
                "import hashlib,json,os,sys,time\nsecret=sys.stdin.buffer.readline().strip()\n"
                "open(sys.argv[1],'w').write(str(os.getpid()))\ntime.sleep(1.0)\n"
                "json.dump({'status':'terminal','digest':hashlib.sha256(secret).hexdigest()},open(sys.argv[2],'w'))\n",
                encoding="utf-8",
            )
            helper.write_text(
                f"import sys,time\nsys.path.insert(0,{str(ROOT / 'scripts')!r})\n"
                "from m2_orbit_recovery_002_core import launch_detached_supervisor\n"
                "secret=sys.stdin.readline().strip()\n"
                "launch_detached_supervisor(secret,command=[sys.executable,sys.argv[1],sys.argv[2],sys.argv[3]])\ntime.sleep(30)\n",
                encoding="utf-8",
            )
            broker = subprocess.Popen([sys.executable, str(helper), str(worker), str(child_pid), str(terminal)], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
            assert broker.stdin is not None
            broker.stdin.write(secret + "\n"); broker.stdin.flush(); broker.stdin.close()
            deadline = time.time() + 10
            while time.time() < deadline and not child_pid.exists(): time.sleep(0.05)
            self.assertTrue(child_pid.exists())
            broker.terminate(); broker.wait(timeout=5)
            deadline = time.time() + 10
            while time.time() < deadline and not terminal.exists(): time.sleep(0.05)
            self.assertTrue(terminal.exists())
            self.assertNotIn(secret, terminal.read_text(encoding="utf-8"))

    def test_direct_runner_refuses_without_reading_a_token(self) -> None:
        with patch.dict(os.environ, {"CDSE_ACCESS_TOKEN": "fixture-secret"}):
            captured = io.StringIO()
            with patch("sys.stdout", captured):
                self.assertEqual(runner_main(), 12)
        self.assertNotIn("fixture-secret", captured.getvalue())
        self.assertEqual(json.loads(captured.getvalue())["code"], "direct_execution_forbidden_use_anonymous_pipe_broker")

    def test_source_files_exclude_other_orbit_requests_and_cli_tokens(self) -> None:
        paths = [
            ROOT / "scripts/m2_orbit_recovery_002_broker.py", ROOT / "scripts/m2_orbit_recovery_002_supervisor.py",
            ROOT / "scripts/acquire_m2_orbit_recovery_002.py", ROOT / "scripts/invoke_m2_orbit_recovery_002.ps1",
        ]
        bodies = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        self.assertNotIn("--token", bodies)
        self.assertNotIn("--access-token", bodies)
        self.assertNotIn('os.environ.get("CDSE_ACCESS_TOKEN")', bodies)
        for source_id in ("M2-ORB-002", "M2-ORB-003", "M2-ORB-004"):
            self.assertNotIn(source_id, bodies)

    @unittest.skipUnless(os.name == "nt", "PowerShell parser validation runs on the deployment platform")
    def test_powershell_handoff_parses_and_does_not_persist_token(self) -> None:
        script = ROOT / "scripts/invoke_m2_orbit_recovery_002.ps1"
        literal_path = str(script).replace("'", "''")
        command = (
            "$tokens=$null;$errors=$null;"
            f"[System.Management.Automation.Language.Parser]::ParseFile('{literal_path}',[ref]$tokens,[ref]$errors)|Out-Null;"
            "if($errors.Count){$errors|ForEach-Object{$_.Message};exit 1}"
        )
        result = subprocess.run(["powershell", "-NoProfile", "-Command", command], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        body = script.read_text(encoding="utf-8")
        self.assertNotIn("Set-Content", body)
        self.assertNotIn("Out-File", body)
        self.assertNotIn("$env:", body)

    def test_verifier_preserves_one_failure_and_accepts_one_recovery_success(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            receipt_path = root / "records/acquisition/orbit-attempts/recovery.json"
            receipt_path.parent.mkdir(parents=True)
            receipt = {
                "event": "orbit_recovery_002_succeeded", "attempt_id": "m2-orb-001-recovery-001-20260905t000000z-deadbeef",
                "source_id": EXPECTED_SOURCE_ID, "local_sha256": "a" * 64, "local_size_bytes": EXPECTED_SIZE_BYTES,
                "provider_checksums_locally_verified": True,
            }
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            intake = {"assets": [{
                "asset_id": "m2-orb-001", "state": "promoted",
                "attempts": [
                    {"attempt_id": "m2-orb-001-20260904t050937z-8ed21d05", "outcome": "failed"},
                    {"attempt_id": receipt["attempt_id"], "outcome": "succeeded"},
                ],
                "observed": {"staged_sha256": "a" * 64, "promoted_sha256": "a" * 64, "staged_size_bytes": EXPECTED_SIZE_BYTES, "promoted_size_bytes": EXPECTED_SIZE_BYTES},
                "extensions": {"source_id": EXPECTED_SOURCE_ID, "successful_attempt_receipt": "records/acquisition/orbit-attempts/recovery.json", "successful_attempt_receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest()},
            }]}
            with patch.object(verifier, "ROOT", root):
                asset, observed_receipt = verifier.promoted_binding(intake, EXPECTED_SOURCE_ID)
            self.assertEqual(asset["state"], "promoted")
            self.assertEqual(observed_receipt["attempt_id"], receipt["attempt_id"])


if __name__ == "__main__":
    unittest.main()
