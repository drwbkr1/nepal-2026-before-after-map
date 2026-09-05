from __future__ import annotations

import copy
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
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import acquire_m2_sentinel_continuation_001 as source_runner  # noqa: E402
import acquire_m2_product_pipe as exact_product_runner  # noqa: E402
import m2_sentinel_continuation_001_core as continuation_core  # noqa: E402
from m2_sentinel_continuation_001_core import (  # noqa: E402
    APPROVAL_REF,
    CONTINUATION_ID,
    EXPECTED_APPROVAL_SHA256,
    EXPECTED_RECONCILIATION_SHA256,
    RECOVERY_SOURCE_ID,
    RECONCILIATION_REF,
    SECRET_REFERENCE,
    SOURCE_ORDER,
    Continuation001ControlError,
    ContinuationJournal,
    build_supervisor_command,
    classify_failure,
    launch_detached_supervisor,
    load_object,
    read_single_use_secret,
    require_exact_contract,
    sanitized_child_environment,
    sha256_file,
    validate_approval,
    validate_initial_asset_state,
    validate_prelaunch_git_state,
    validate_secret,
)
from m2_sentinel_continuation_001_supervisor import run_supervised  # noqa: E402
from m2_transfer_core import NoRedirectHandler, TransferControlError, promote_atomic_no_replace  # noqa: E402


class _CaptureStdin(io.BytesIO):
    def close(self) -> None:
        self.captured = self.getvalue()
        super().close()


class _FakeProcess:
    pid = 43110

    def __init__(self) -> None:
        self.stdin = _CaptureStdin()


class _FakeJournal:
    def __init__(self) -> None:
        self.updates: list[dict[str, object]] = []
        self.completed: list[str] = []

    def update(self, **kwargs: object) -> None:
        self.updates.append(kwargs)

    def mark_completed(self, source_id: str) -> None:
        self.completed.append(source_id)


class Continuation001Tests(unittest.TestCase):
    def test_exact_locked_approval_and_reconciliation_validate(self) -> None:
        approval_path = ROOT / APPROVAL_REF
        reconciliation_path = ROOT / RECONCILIATION_REF
        self.assertEqual(sha256_file(approval_path), EXPECTED_APPROVAL_SHA256)
        self.assertEqual(sha256_file(reconciliation_path), EXPECTED_RECONCILIATION_SHA256)
        validate_approval(load_object(approval_path), load_object(reconciliation_path))

    def test_source_order_is_exact_and_excludes_recovery_source(self) -> None:
        self.assertEqual(SOURCE_ORDER, ("M1-SRC-005", "M1-SRC-006", "M1-SRC-008", "M1-SRC-010"))
        self.assertNotIn(RECOVERY_SOURCE_ID, SOURCE_ORDER)
        self.assertEqual(len(SOURCE_ORDER), len(set(SOURCE_ORDER)))

    def test_current_initial_asset_state_is_four_fresh_authorized(self) -> None:
        intake = load_object(ROOT / "contracts/m2-intake.json")
        snapshots = validate_initial_asset_state(intake)
        self.assertEqual([item["source_id"] for item in snapshots], list(SOURCE_ORDER))
        self.assertTrue(all(item["initial_state"] == "authorized" for item in snapshots))
        self.assertTrue(all(item["initial_attempt_count"] == 0 for item in snapshots))

    def test_initial_asset_state_rejects_prior_attempt(self) -> None:
        intake = load_object(ROOT / "contracts/m2-intake.json")
        fixture = copy.deepcopy(intake)
        asset = next(item for item in fixture["assets"] if item["extensions"]["source_id"] == SOURCE_ORDER[0])
        asset["attempts"].append({"attempt_id": "must-not-exist"})
        with self.assertRaisesRegex(Continuation001ControlError, "continuation_asset_not_fresh_authorized"):
            validate_initial_asset_state(fixture)

    def test_contract_boundary_rejects_recovery_or_reordering(self) -> None:
        contract = {
            "contract_version": "1.0",
            "continuation_id": CONTINUATION_ID,
            "status": "active_authorized_final_no_payload_preflight_pending",
            "source_ids_in_exact_order": list(SOURCE_ORDER),
            "recovery_source_ids": [],
            "m1_src_004_request_permitted": False,
            "maximum_real_attempts_per_source": 1,
            "stop_on_first_failure": True,
            "secret_transport": SECRET_REFERENCE,
            "collision_policy": "fail",
            "promotion_mode": "atomic-no-replace",
            "assets": [{"source_id": source_id, "initial_state": "authorized", "initial_attempt_count": 0} for source_id in SOURCE_ORDER],
        }
        require_exact_contract(contract)
        contract["source_ids_in_exact_order"] = list(reversed(SOURCE_ORDER))
        with self.assertRaisesRegex(Continuation001ControlError, "contract_boundary_drift"):
            require_exact_contract(contract)

    def test_secret_validation_and_single_use_pipe_fail_closed(self) -> None:
        for value in ("", "contains space", "contains\nnewline"):
            with self.assertRaises(Continuation001ControlError):
                validate_secret(value)
        stream = io.BytesIO(b"fixture-secret\n")
        self.assertEqual(read_single_use_secret(stream), "fixture-secret")
        self.assertTrue(stream.closed)

    def test_sanitized_environment_removes_secret_and_named_credentials(self) -> None:
        secret = "dynamic-" + uuid.uuid4().hex
        result = sanitized_child_environment(
            {"OK": "value", "AUTHORIZATION": "Bearer other", "LEAK": secret, secret: "bad"}, secret
        )
        self.assertEqual(result, {"OK": "value"})

    def test_secret_only_enters_anonymous_pipe(self) -> None:
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
            command=[sys.executable, "synthetic-continuation-worker.py"],
            environment={"SAFE": "yes", "CDSE_ACCESS_TOKEN": "old", "BAD": secret},
            popen_factory=factory,
        )
        self.assertEqual(pid, 43110)
        self.assertNotIn(secret, json.dumps(captured["argv"]))
        self.assertNotIn(secret, json.dumps(captured["env"]))
        self.assertNotIn("CDSE_ACCESS_TOKEN", captured["env"])
        self.assertEqual(captured["process"].stdin.captured, (secret + "\n").encode())

    def test_supervisor_command_is_continuation_only(self) -> None:
        command = build_supervisor_command("python", Path("continuation.py"))
        self.assertEqual(command, ["python", "continuation.py", "--continuation-id", CONTINUATION_ID])
        self.assertNotIn(RECOVERY_SOURCE_ID, command)

    def test_prelaunch_git_state_allows_only_exact_post_ci_gate_files(self) -> None:
        expected_commit = "a" * 40
        status = "\n".join(
            f"?? {path}" for path in (
                "contracts/m2-sentinel-continuation-001.json",
                "records/acquisition/sentinel-continuation-001-publication-gate.json",
                "records/acquisition/sentinel-continuation-001-activation.json",
                "records/acquisition/sentinel-continuation-001-final-preflight.json",
            )
        ) + "\n"
        results = [
            subprocess.CompletedProcess([], 0, expected_commit + "\n", ""),
            subprocess.CompletedProcess([], 0, expected_commit + "\n", ""),
            subprocess.CompletedProcess([], 0, status, ""),
        ]
        with (
            mock.patch.object(continuation_core, "validate_runtime_gate"),
            mock.patch.object(continuation_core, "load_object", return_value={"github_actions": {"head_sha": expected_commit}}),
            mock.patch.object(continuation_core.subprocess, "run", side_effect=results),
        ):
            validate_prelaunch_git_state()

    def test_prelaunch_git_state_rejects_any_extra_change(self) -> None:
        expected_commit = "b" * 40
        results = [
            subprocess.CompletedProcess([], 0, expected_commit + "\n", ""),
            subprocess.CompletedProcess([], 0, expected_commit + "\n", ""),
            subprocess.CompletedProcess([], 0, " M scripts/extra.py\n", ""),
        ]
        with (
            mock.patch.object(continuation_core, "validate_runtime_gate"),
            mock.patch.object(continuation_core, "load_object", return_value={"github_actions": {"head_sha": expected_commit}}),
            mock.patch.object(continuation_core.subprocess, "run", side_effect=results),
            self.assertRaisesRegex(Continuation001ControlError, "prelaunch_worktree_boundary_drift"),
        ):
            validate_prelaunch_git_state()

    def test_known_control_exception_retains_only_safe_code(self) -> None:
        result = classify_failure(Continuation001ControlError("continuation_path_not_fresh"))
        self.assertEqual(result, {"terminal_code": "continuation_path_not_fresh", "failure_class": "approved_control"})
        transfer = classify_failure(TransferControlError("provider_transport_failure"))
        self.assertEqual(transfer, {"terminal_code": "provider_transport_failure", "failure_class": "approved_control"})

    def test_unexpected_exception_drops_message_and_synthetic_secret(self) -> None:
        secret = "synthetic-secret-" + uuid.uuid4().hex
        result = classify_failure(RuntimeError(f"private failure {secret}"))
        encoded = json.dumps(result)
        self.assertEqual(result["terminal_code"], "unexpected_continuation_supervisor_failure")
        self.assertNotIn(secret, encoded)
        self.assertNotIn("private failure", encoded)

    def test_append_only_journal_excludes_exception_and_secret(self) -> None:
        secret = "journal-secret-" + uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "events"
            journal = ContinuationJournal(root, "synthetic-supervisor", interval_seconds=0.02)
            journal.start()
            journal.update(phase="source_preflight", source_id=SOURCE_ORDER[0], attempt_id=None, bytes_written=0)
            journal.update(phase="continuation_transfer", source_id=SOURCE_ORDER[0], attempt_id="attempt-1", bytes_written=42)
            time.sleep(0.05)
            journal.finish("failed", classify_failure(RuntimeError(f"do not record {secret}")))
            files = list(root.glob("*.json"))
            self.assertGreaterEqual(len(files), 5)
            self.assertEqual(len(list(root.glob("*-supervisor_failed.json"))), 1)
            combined = "".join(path.read_text(encoding="utf-8") for path in files)
            self.assertNotIn(secret, combined)
            self.assertNotIn("do not record", combined)
            self.assertIn("unexpected_continuation_supervisor_failure", combined)

    def test_source_runner_refuses_m1_src_004_before_delegate(self) -> None:
        called = False

        def delegate(*args: object, **kwargs: object) -> dict[str, object]:
            nonlocal called
            called = True
            return {}

        with self.assertRaisesRegex(Continuation001ControlError, "source_outside_exact_release"):
            source_runner.run_continuation_source(RECOVERY_SOURCE_ID, "fixture-secret", product_runner=delegate)
        self.assertFalse(called)

    def test_source_runner_delegates_one_allowed_source_after_gate(self) -> None:
        calls: list[str] = []

        def delegate(source_id: str, token: str, **kwargs: object) -> dict[str, object]:
            calls.append(source_id)
            self.assertEqual(token, "fixture-secret")
            return {"returncode": 0, "source_id": source_id}

        with mock.patch.object(source_runner, "validate_runtime_gate"):
            result = source_runner.run_continuation_source(SOURCE_ORDER[0], "fixture-secret", product_runner=delegate)
        self.assertEqual(result["returncode"], 0)
        self.assertEqual(calls, [SOURCE_ORDER[0]])

    def test_live_preflight_control_failure_is_exact_and_pre_attempt(self) -> None:
        intake_path = ROOT / "contracts/m2-intake.json"
        before = intake_path.read_bytes()
        intake = json.loads(before)
        asset = next(item for item in intake["assets"] if item["extensions"]["source_id"] == SOURCE_ORDER[0])
        project_root = ROOT.parent
        destination = project_root / Path(*Path(intake["custody_root"]).parts) / Path(*Path(asset["destination_relative_path"]).parts)
        staging = project_root / Path(*Path(intake["staging_root"]).parts) / Path(*Path(asset["staging_relative_path"]).parts)
        event_root = project_root / Path(*Path(intake["staging_root"]).parts) / "attempt-events" / asset["asset_id"]
        self.assertFalse(destination.exists())
        self.assertFalse(staging.exists())
        self.assertFalse(event_root.exists())
        with mock.patch.object(
            exact_product_runner,
            "live_page_consistency_check",
            side_effect=TransferControlError("official_page_revalidation_unavailable"),
        ):
            with self.assertRaisesRegex(TransferControlError, "official_page_revalidation_unavailable"):
                exact_product_runner.run_product(SOURCE_ORDER[0], "fixture-secret")
        self.assertEqual(intake_path.read_bytes(), before)
        self.assertFalse(destination.exists())
        self.assertFalse(staging.exists())
        self.assertFalse(event_root.exists())

    def test_supervisor_success_runs_exact_order_once_and_reconciles(self) -> None:
        journal = _FakeJournal()
        transfers: list[str] = []
        containers: list[str] = []
        reconciled: list[bool] = []

        def runner(source_id: str, token: str, **kwargs: object) -> dict[str, object]:
            transfers.append(source_id)
            progress = kwargs["progress"]
            progress("continuation_transfer", f"attempt-{source_id}", 99)
            return {"returncode": 0, "attempt_id": f"attempt-{source_id}", "size_bytes": 99}

        result = run_supervised(
            "fixture-secret",
            journal,
            runtime_validator=lambda: None,
            product_runner=runner,
            container_verifier=lambda source_id, token: containers.append(source_id) or 0,
            success_reconciler=lambda: reconciled.append(True) or {},
        )
        self.assertEqual(result["failure_class"], "none")
        self.assertEqual(transfers, list(SOURCE_ORDER))
        self.assertEqual(containers, list(SOURCE_ORDER))
        self.assertEqual(journal.completed, list(SOURCE_ORDER))
        self.assertEqual(reconciled, [True])

    def test_supervisor_stops_on_first_transfer_failure(self) -> None:
        journal = _FakeJournal()
        calls: list[str] = []

        def runner(source_id: str, token: str, **kwargs: object) -> dict[str, object]:
            calls.append(source_id)
            return {"returncode": 20, "failure_code": "provider_transport_failure"}

        result = run_supervised(
            "fixture-secret",
            journal,
            runtime_validator=lambda: None,
            product_runner=runner,
            container_verifier=lambda source_id, token: self.fail("container verifier must not run"),
            success_reconciler=lambda: self.fail("reconciler must not run"),
        )
        self.assertEqual(result["terminal_code"], "provider_transport_failure")
        self.assertEqual(calls, [SOURCE_ORDER[0]])
        self.assertEqual(journal.completed, [])

    def test_supervisor_stops_after_first_container_failure(self) -> None:
        journal = _FakeJournal()
        transfers: list[str] = []

        def runner(source_id: str, token: str, **kwargs: object) -> dict[str, object]:
            transfers.append(source_id)
            return {"returncode": 0, "attempt_id": "attempt-1", "size_bytes": 10}

        result = run_supervised(
            "fixture-secret",
            journal,
            runtime_validator=lambda: None,
            product_runner=runner,
            container_verifier=lambda source_id, token: 20,
            success_reconciler=lambda: self.fail("reconciler must not run"),
        )
        self.assertEqual(result["terminal_code"], "m1_src_005_container_verification_failed")
        self.assertEqual(transfers, [SOURCE_ORDER[0]])
        self.assertEqual(journal.completed, [])

    def test_redirect_range_and_atomic_no_replace_controls_remain_bound(self) -> None:
        self.assertIsNone(NoRedirectHandler().redirect_request(None, None, 302, "Found", {}, "https://invalid"))
        runner_text = (ROOT / "scripts/acquire_m2_product_pipe.py").read_text(encoding="utf-8")
        self.assertNotIn('"Range"', runner_text)
        self.assertIn('"Accept-Encoding": "identity"', runner_text)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            staged, destination = root / "x.part", root / "x.zip"
            staged.write_bytes(b"new")
            destination.write_bytes(b"old")
            with self.assertRaisesRegex(TransferControlError, "destination_collision"):
                promote_atomic_no_replace(staged, destination)
            self.assertEqual(staged.read_bytes(), b"new")
            self.assertEqual(destination.read_bytes(), b"old")

    def test_new_source_files_do_not_read_token_from_environment_or_cli(self) -> None:
        paths = [
            ROOT / "scripts/m2_sentinel_continuation_001_core.py",
            ROOT / "scripts/m2_sentinel_continuation_001_broker.py",
            ROOT / "scripts/m2_sentinel_continuation_001_supervisor.py",
            ROOT / "scripts/acquire_m2_sentinel_continuation_001.py",
        ]
        bodies = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        self.assertNotIn('os.environ.get("CDSE_ACCESS_TOKEN")', bodies)
        self.assertNotIn("--token", bodies)
        self.assertNotIn("--access-token", bodies)
        self.assertNotIn("run_recovery", bodies)

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
                "from m2_sentinel_continuation_001_core import launch_detached_supervisor\n"
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


if __name__ == "__main__":
    unittest.main()
