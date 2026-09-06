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
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import acquire_m2_orbit_continuation_001 as runner  # noqa: E402
import m2_orbit_continuation_001_core as core  # noqa: E402
from m2_orbit_continuation_001_core import (  # noqa: E402
    APPROVAL_REF,
    CONTINUATION_ID,
    EXPECTED_APPROVAL_SHA256,
    EXPECTED_RECONCILIATION_SHA256,
    PRESERVED_SOURCE_ID,
    RECONCILIATION_REF,
    SECRET_REFERENCE,
    SOURCE_ORDER,
    ContinuationJournal,
    OrbitContinuation001Error,
    build_supervisor_command,
    claim_owner_handoff,
    classify_failure,
    launch_detached_supervisor,
    load_object,
    read_single_use_secret,
    require_exact_contract,
    sanitized_child_environment,
    sha256_file,
    validate_approval,
    validate_handoff_claim,
    validate_initial_asset_state,
    validate_prelaunch_git_state,
    validate_secret,
)
from m2_orbit_continuation_001_supervisor import run_supervised  # noqa: E402
from m2_orbit_io_core import osv_endpoints_within_tolerance  # noqa: E402
from m2_transfer_core import NoRedirectHandler, TransferControlError, promote_atomic_no_replace  # noqa: E402


class _CaptureStdin(io.BytesIO):
    def close(self) -> None:
        self.captured = self.getvalue()
        super().close()


class _FakeProcess:
    pid = 45123

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


class OrbitContinuation001Tests(unittest.TestCase):
    def test_exact_locked_approval_and_reconciliation_validate(self) -> None:
        approval = load_object(ROOT / APPROVAL_REF)
        reconciliation = load_object(ROOT / RECONCILIATION_REF)
        self.assertEqual(sha256_file(ROOT / APPROVAL_REF), EXPECTED_APPROVAL_SHA256)
        self.assertEqual(sha256_file(ROOT / RECONCILIATION_REF), EXPECTED_RECONCILIATION_SHA256)
        validate_approval(approval, reconciliation)

    def test_source_order_is_exact_and_excludes_preserved_source(self) -> None:
        self.assertEqual(SOURCE_ORDER, ("M2-ORB-002", "M2-ORB-003", "M2-ORB-004"))
        self.assertNotIn(PRESERVED_SOURCE_ID, SOURCE_ORDER)
        self.assertEqual(len(SOURCE_ORDER), len(set(SOURCE_ORDER)))

    def test_detached_process_flags_match_host_platform(self) -> None:
        kwargs = core.detached_popen_kwargs({"SAFE": "yes"})
        self.assertEqual(kwargs["env"], {"SAFE": "yes"})
        if os.name == "nt":
            self.assertTrue(kwargs["creationflags"] & getattr(subprocess, "DETACHED_PROCESS", 0x00000008))
            self.assertTrue(kwargs["creationflags"] & getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200))
            self.assertTrue(kwargs["close_fds"])
        else:
            self.assertTrue(kwargs["start_new_session"])
            self.assertTrue(kwargs["close_fds"])

    def test_initial_metadata_has_one_preserved_and_three_fresh_sources(self) -> None:
        intake = load_object(ROOT / "contracts/m2-orbit-intake.json")
        snapshots = validate_initial_asset_state(intake)
        self.assertEqual([item["source_id"] for item in snapshots], list(SOURCE_ORDER))
        self.assertTrue(all(item["initial_state"] == "authorized" for item in snapshots))
        self.assertTrue(all(item["initial_attempt_count"] == 0 for item in snapshots))

    def test_initial_metadata_rejects_prior_remaining_source_attempt(self) -> None:
        intake = copy.deepcopy(load_object(ROOT / "contracts/m2-orbit-intake.json"))
        asset = next(item for item in intake["assets"] if item["extensions"]["source_id"] == SOURCE_ORDER[0])
        asset["attempts"].append({"attempt_id": "must-not-exist"})
        with self.assertRaisesRegex(OrbitContinuation001Error, "continuation_asset_not_fresh_authorized"):
            validate_initial_asset_state(intake)

    def test_contract_rejects_reorder_and_tolerance_broadening(self) -> None:
        contract = {
            "contract_version": "1.0",
            "continuation_id": CONTINUATION_ID,
            "status": "active_authorized_final_no_payload_preflight_pending",
            "source_ids_in_exact_order": list(SOURCE_ORDER),
            "preserved_source_ids": [PRESERVED_SOURCE_ID],
            "m2_orb_001_request_authorized": False,
            "maximum_owner_handoffs": 1,
            "maximum_real_attempts_per_source": 1,
            "stop_on_first_failure": True,
            "maximum_osv_endpoint_tolerance_seconds": 1.0,
            "secret_transport": SECRET_REFERENCE,
            "collision_policy": "fail",
            "promotion_mode": "atomic-no-replace",
            "assets": [{"source_id": source_id, "initial_state": "authorized", "initial_attempt_count": 0} for source_id in SOURCE_ORDER],
        }
        require_exact_contract(contract)
        for key, value in (("source_ids_in_exact_order", list(reversed(SOURCE_ORDER))), ("maximum_osv_endpoint_tolerance_seconds", 1.001)):
            fixture = copy.deepcopy(contract)
            fixture[key] = value
            with self.assertRaisesRegex(OrbitContinuation001Error, "contract_boundary_drift"):
                require_exact_contract(fixture)

    def test_publication_recorder_schema_is_accepted_by_runtime_validator(self) -> None:
        gate = {
            "status": "pass_public_controls_verified_before_orbit_continuation_001",
            "github_actions": {"conclusion": "success"},
            "assertions": {
                "credential_values_read_or_recorded": False,
                "orbit_payload_request_performed": False,
            },
        }
        core.validate_publication_gate(gate)
        incompatible = copy.deepcopy(gate)
        incompatible["assertions"] = {
            "credential_values_read_or_recorded": False,
            "payload_request_performed": False,
        }
        with self.assertRaisesRegex(OrbitContinuation001Error, "continuation_publication_gate_not_passing"):
            core.validate_publication_gate(incompatible)

    def test_one_second_osv_rule_is_exact_boundary(self) -> None:
        start = datetime(2026, 8, 18, tzinfo=UTC)
        stop = start + timedelta(hours=3)
        self.assertTrue(osv_endpoints_within_tolerance(start, stop, start + timedelta(seconds=1), stop - timedelta(seconds=1), tolerance_seconds=1.0))
        self.assertFalse(osv_endpoints_within_tolerance(start, stop, start + timedelta(seconds=1.001), stop, tolerance_seconds=1.0))
        with self.assertRaisesRegex(Exception, "tolerance_invalid"):
            osv_endpoints_within_tolerance(start, stop, start, stop, tolerance_seconds=1.001)

    def test_secret_validation_and_single_use_pipe_fail_closed(self) -> None:
        for value in ("", "contains space", "contains\nnewline"):
            with self.assertRaises(OrbitContinuation001Error):
                validate_secret(value)
        for payload in (b"fixture-secret\n", b"fixture-secret\r\n"):
            stream = io.BytesIO(payload)
            self.assertEqual(read_single_use_secret(stream), "fixture-secret")
            self.assertTrue(stream.closed)

    def test_sanitized_environment_removes_secret_and_named_credentials(self) -> None:
        secret = "dynamic-" + uuid.uuid4().hex
        cleaned = sanitized_child_environment({"SAFE": "yes", "AUTHORIZATION": "old", "CDSE_ACCESS_TOKEN": "old", "LEAK": secret, secret: "bad"}, secret)
        self.assertEqual(cleaned, {"SAFE": "yes"})

    def test_secret_only_enters_anonymous_pipe(self) -> None:
        secret = "runtime-" + uuid.uuid4().hex
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
            environment={"SAFE": "yes", "CDSE_ACCESS_TOKEN": "old", "LEAK": secret},
            popen_factory=factory,
        )
        self.assertEqual(pid, 45123)
        self.assertNotIn(secret, json.dumps(captured["argv"]))
        self.assertNotIn(secret, json.dumps(captured["env"]))
        self.assertEqual(captured["process"].stdin.captured, (secret + "\n").encode())

    def test_supervisor_command_is_handoff_bound_and_excludes_preserved_source(self) -> None:
        handoff = "m2-orbit-continuation-001-handoff-20260906t220000z-deadbeef"
        command = build_supervisor_command(handoff, "python", Path("continuation.py"))
        self.assertEqual(command, ["python", "continuation.py", "--continuation-id", CONTINUATION_ID, "--handoff-id", handoff])
        self.assertNotIn(PRESERVED_SOURCE_ID, command)

    def test_owner_handoff_claim_is_nonsecret_and_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "handoff"
            handoff, claim_path = claim_owner_handoff(claim_root=root, claimed_at="2026-09-06T22:00:00Z")
            claim = validate_handoff_claim(handoff, claim_root=root)
            self.assertTrue(claim["authority_consumed"])
            self.assertFalse(claim["credential_value_recorded"])
            self.assertNotIn("fixture-secret", claim_path.read_text(encoding="utf-8"))
            with self.assertRaisesRegex(OrbitContinuation001Error, "owner_handoff_already_consumed"):
                claim_owner_handoff(claim_root=root, claimed_at="2026-09-06T22:00:01Z")

    def test_known_and_unexpected_failures_exclude_messages(self) -> None:
        known = classify_failure(TransferControlError("provider_transport_failure"))
        self.assertEqual(known, {"terminal_code": "provider_transport_failure", "failure_class": "approved_control"})
        secret = "secret-" + uuid.uuid4().hex
        unexpected = classify_failure(RuntimeError(f"private {secret}"))
        self.assertEqual(unexpected["terminal_code"], "unexpected_continuation_supervisor_failure")
        self.assertNotIn(secret, json.dumps(unexpected))

    def test_interruption_has_fixed_nonsecret_code(self) -> None:
        self.assertEqual(runner.failure_code_for(KeyboardInterrupt(), "authenticated_byte_zero_transfer"), "orbit_continuation_001_interrupted")

    def test_append_only_journal_excludes_exception_and_secret(self) -> None:
        secret = "journal-secret-" + uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "events"
            journal = ContinuationJournal(root, "synthetic-supervisor", interval_seconds=0.02)
            journal.start()
            journal.update(phase="source_preflight", source_id=SOURCE_ORDER[0], attempt_id=None, bytes_written=0)
            time.sleep(0.05)
            journal.finish("failed", classify_failure(RuntimeError(f"do not record {secret}")))
            combined = "".join(path.read_text(encoding="utf-8") for path in root.glob("*.json"))
            self.assertNotIn(secret, combined)
            self.assertNotIn("do not record", combined)
            self.assertEqual(len(list(root.glob("*-supervisor_failed.json"))), 1)

    def test_source_sequence_refuses_preserved_source_before_attempt(self) -> None:
        intake = load_object(ROOT / "contracts/m2-orbit-intake.json")
        with self.assertRaisesRegex(OrbitContinuation001Error, "source_outside_exact_release"):
            runner.validate_source_sequence(intake, PRESERVED_SOURCE_ID)

    def test_source_sequence_rejects_skipping_first_source(self) -> None:
        intake = copy.deepcopy(load_object(ROOT / "contracts/m2-orbit-intake.json"))
        with mock.patch.object(runner, "validate_preserved_m2_orb_001_bytes"):
            with self.assertRaisesRegex(OrbitContinuation001Error, "prior_continuation_source_not_exact_success"):
                runner.validate_source_sequence(intake, SOURCE_ORDER[1])

    def test_supervisor_success_runs_exact_order_once_and_reconciles(self) -> None:
        journal = _FakeJournal()
        calls: list[str] = []
        reconciled: list[bool] = []

        def source(source_id: str, token: str, **kwargs: object) -> dict[str, object]:
            calls.append(source_id)
            kwargs["progress"]("synthetic_transfer", f"attempt-{source_id}", 99)
            return {"returncode": 0, "attempt_id": f"attempt-{source_id}", "size_bytes": 99}

        result = run_supervised("fixture-secret", journal, runtime_validator=lambda: None, source_runner=source, success_reconciler=lambda: reconciled.append(True) or {})
        self.assertEqual(result["failure_class"], "none")
        self.assertEqual(calls, list(SOURCE_ORDER))
        self.assertEqual(journal.completed, list(SOURCE_ORDER))
        self.assertEqual(reconciled, [True])

    def test_supervisor_stops_on_first_failure_without_reconcile(self) -> None:
        journal = _FakeJournal()
        calls: list[str] = []

        def source(source_id: str, token: str, **kwargs: object) -> dict[str, object]:
            calls.append(source_id)
            return {"returncode": 20, "failure_code": "synthetic_provider_failure"}

        result = run_supervised("fixture-secret", journal, runtime_validator=lambda: None, source_runner=source, success_reconciler=lambda: self.fail("must not reconcile"))
        self.assertEqual(result["terminal_code"], "synthetic_provider_failure")
        self.assertEqual(calls, [SOURCE_ORDER[0]])
        self.assertEqual(journal.completed, [])

    def test_byte_zero_headers_redirect_and_atomic_no_replace_controls(self) -> None:
        headers = runner.download_headers("fixture-token")
        self.assertNotIn("Range", headers)
        self.assertEqual(headers["Accept-Encoding"], "identity")
        self.assertIsNone(NoRedirectHandler().redirect_request(None, None, 302, "Found", {}, "https://invalid"))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            staged, destination = root / "x.part", root / "x.eof"
            staged.write_bytes(b"new")
            destination.write_bytes(b"old")
            with self.assertRaisesRegex(TransferControlError, "destination_collision"):
                promote_atomic_no_replace(staged, destination)
            self.assertEqual(staged.read_bytes(), b"new")
            self.assertEqual(destination.read_bytes(), b"old")

    def test_prelaunch_git_state_allows_only_exact_post_ci_files(self) -> None:
        commit = "a" * 40
        paths = [core.CONTRACT_REF, core.PUBLICATION_GATE_REF, core.ACTIVATION_REF, core.FINAL_PREFLIGHT_REF, core.CONTROL_RECONCILIATION_REF]
        status = "\n".join(f"?? {path}" for path in paths) + "\n"
        results = [
            subprocess.CompletedProcess([], 0, commit + "\n", ""),
            subprocess.CompletedProcess([], 0, commit + "\n", ""),
            subprocess.CompletedProcess([], 0, status, ""),
        ]
        with (
            mock.patch.object(core, "validate_runtime_gate"),
            mock.patch.object(core, "load_object", return_value={"github_actions": {"head_sha": commit}}),
            mock.patch.object(core.subprocess, "run", side_effect=results),
        ):
            validate_prelaunch_git_state()

    def test_prelaunch_git_state_rejects_extra_change(self) -> None:
        commit = "b" * 40
        results = [
            subprocess.CompletedProcess([], 0, commit + "\n", ""),
            subprocess.CompletedProcess([], 0, commit + "\n", ""),
            subprocess.CompletedProcess([], 0, " M scripts/extra.py\n", ""),
        ]
        with (
            mock.patch.object(core, "validate_runtime_gate"),
            mock.patch.object(core, "load_object", return_value={"github_actions": {"head_sha": commit}}),
            mock.patch.object(core.subprocess, "run", side_effect=results),
            self.assertRaisesRegex(OrbitContinuation001Error, "prelaunch_worktree_boundary_drift"),
        ):
            validate_prelaunch_git_state()

    def test_source_files_do_not_read_token_from_environment_or_cli(self) -> None:
        paths = [
            ROOT / "scripts/m2_orbit_continuation_001_core.py",
            ROOT / "scripts/m2_orbit_continuation_001_broker.py",
            ROOT / "scripts/m2_orbit_continuation_001_supervisor.py",
            ROOT / "scripts/acquire_m2_orbit_continuation_001.py",
            ROOT / "scripts/invoke_m2_orbit_continuation_001.ps1",
        ]
        body = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        self.assertNotIn("--token", body)
        self.assertNotIn("--access-token", body)
        self.assertNotIn('os.environ.get("CDSE_ACCESS_TOKEN")', body)
        self.assertNotIn("Set-Clipboard", body)

    @unittest.skipUnless(os.name == "nt", "PowerShell parser validation runs on the deployment platform")
    def test_owner_powershell_parses_and_does_not_persist_token(self) -> None:
        script = ROOT / "scripts/invoke_m2_orbit_continuation_001.ps1"
        literal = str(script).replace("'", "''")
        command = "$tokens=$null;$errors=$null;" + f"[System.Management.Automation.Language.Parser]::ParseFile('{literal}',[ref]$tokens,[ref]$errors)|Out-Null;" + "if($errors.Count){$errors|ForEach-Object{$_.Message};exit 1}"
        result = subprocess.run(["powershell", "-NoProfile", "-Command", command], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        body = script.read_text(encoding="utf-8")
        for forbidden in ("Set-Content", "Out-File", "$env:", "Set-Clipboard"):
            self.assertNotIn(forbidden, body)


if __name__ == "__main__":
    unittest.main()
