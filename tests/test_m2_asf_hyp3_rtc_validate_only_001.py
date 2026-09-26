"""Synthetic transport, interruption, and secret-exposure checks; no ASF calls."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m2_asf_hyp3_rtc_core_001 import ORDER, RouteStop, load_approved_jobs  # noqa: E402
from m2_asf_hyp3_rtc_validate_only_001 import (  # noqa: E402
    APPROVAL_REF, IMPLEMENTATION_FILES, IMPLEMENTATION_GATE_REF, PREFLIGHT_REF,
    PROPOSAL_SHA256, SOURCE_GATE_REF, HOST, post_one_validate_only,
    require_validation_release, validate_fixed_order,
)


class FakeResponse:
    status = 200

    def __init__(self, body: dict):
        self.body = json.dumps(body).encode("utf-8")

    def read(self, _count: int) -> bytes:
        return self.body


class FakeConnection:
    def __init__(self, host: str, timeout: int):
        self.host = host
        self.timeout = timeout
        self.request_record = None
        self.closed = False

    def request(self, method: str, path: str, body: bytes, headers: dict) -> None:
        self.request_record = (method, path, body, headers)

    def getresponse(self) -> FakeResponse:
        payload = json.loads(self.request_record[2])
        job = copy.deepcopy(payload["jobs"][0])
        job.update({
            "job_id": "27836b79-e5b2-4d8f-932f-659724ea02c3",
            "user_id": "private-synthetic-user",
            "status_code": "PENDING", "execution_started": False,
            "files": [], "credit_cost": 60,
        })
        return FakeResponse({"validate_only": True, "jobs": [job]})

    def close(self) -> None:
        self.closed = True


class ValidationTransportTests(unittest.TestCase):
    def test_unreleased_executable_stops_before_secret_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp, self.assertRaisesRegex(RouteStop, "validation_release_unavailable"):
            require_validation_release(Path(temp), Path(temp) / "attempt")

    def test_synthetic_complete_release_and_code_drift_stop(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for ref in (*IMPLEMENTATION_FILES, APPROVAL_REF):
                destination = root / ref
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / ref, destination)
            approval_sha = hashlib.sha256((root / APPROVAL_REF).read_bytes()).hexdigest()
            source = {
                "decision": {"status": "ready", "approved_actions": ["validate_exact_rtc_job_without_submission"]},
                "authority": {"authority_ref": APPROVAL_REF},
                "bindings": {"proposal_sha256": PROPOSAL_SHA256, "approval_sha256": approval_sha},
                "scope": {"processing_job_submission_released": False},
                "sources": [{"criteria": [{"required": True, "status": "pass"} for _ in range(8)]}],
            }
            source_path = root / SOURCE_GATE_REF
            source_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.write_text(json.dumps(source), encoding="utf-8")
            source_sha = hashlib.sha256(source_path.read_bytes()).hexdigest()
            gate = {
                "status": "pass_validate_only_implementation_public_ci_only",
                "bindings": {
                    "approval_sha256": approval_sha, "source_gate_sha256": source_sha,
                    "implementation_file_sha256": {
                        ref: hashlib.sha256((root / ref).read_bytes()).hexdigest() for ref in IMPLEMENTATION_FILES
                    },
                },
                "public_ci": {"conclusion": "success"},
            }
            gate_path = root / IMPLEMENTATION_GATE_REF
            gate_path.parent.mkdir(parents=True, exist_ok=True)
            gate_path.write_text(json.dumps(gate), encoding="utf-8")
            preflight = {
                "status": "pass_validate_only_no_content",
                "bindings": {"approval_sha256": approval_sha,
                             "implementation_gate_sha256": hashlib.sha256(gate_path.read_bytes()).hexdigest()},
                "assertions": {"secret_or_account_or_job_request_performed": False},
            }
            (root / PREFLIGHT_REF).write_text(json.dumps(preflight), encoding="utf-8")
            (root / "data").mkdir()
            attempt = root / "data" / "validation" / "attempt"
            require_validation_release(root, attempt)
            (root / IMPLEMENTATION_FILES[0]).write_text("drift", encoding="utf-8")
            with self.assertRaisesRegex(RouteStop, "validation_not_released"):
                require_validation_release(root, attempt)

    def test_fixed_host_exact_payload_sanitized_reply(self) -> None:
        connections = []

        def factory(host: str, timeout: int) -> FakeConnection:
            connection = FakeConnection(host, timeout)
            connections.append(connection)
            return connection

        result = post_one_validate_only("private-synthetic-token", ORDER[0], connection_factory=factory)
        connection = connections[0]
        self.assertEqual(connection.host, HOST)
        self.assertEqual(connection.request_record[:2], ("POST", "/jobs"))
        payload = json.loads(connection.request_record[2])
        self.assertIs(payload["validate_only"], True)
        self.assertEqual(payload["jobs"][0]["job_parameters"], load_approved_jobs()[0]["job_parameters"])
        self.assertEqual(len(payload["jobs"]), 1)
        self.assertTrue(connection.closed)
        self.assertEqual(result["status"], "pass_validate_only_identity_and_cost_only")
        rendered = json.dumps(result)
        self.assertNotIn("private-synthetic-token", rendered)
        self.assertNotIn("private-synthetic-user", rendered)
        self.assertNotIn("27836b79", rendered)

    def test_non_success_never_follows_redirect(self) -> None:
        class RedirectConnection(FakeConnection):
            def getresponse(self) -> FakeResponse:
                result = super().getresponse()
                result.status = 302
                return result

        instances = []

        def factory(host: str, timeout: int) -> RedirectConnection:
            connection = RedirectConnection(host, timeout)
            instances.append(connection)
            return connection

        with self.assertRaisesRegex(RouteStop, "validation_response_not_success"):
            post_one_validate_only("private-synthetic-token", ORDER[0], connection_factory=factory)
        self.assertTrue(instances[0].closed)

    def test_exact_order_and_stop_on_first_failure(self) -> None:
        calls = []

        def account(_token: str) -> dict:
            return {"status": "account_probe_pass_free_credit_capacity_only", "at_least_240_free_basic_credits": True}

        def validate(_token: str, source_id: str) -> dict:
            calls.append(source_id)
            if source_id == ORDER[1]:
                raise RouteStop("synthetic_rejection")
            return {"source_id": source_id, "status": "pass_validate_only_identity_and_cost_only"}

        with tempfile.TemporaryDirectory() as temp:
            attempt = Path(temp) / "attempt"
            result = validate_fixed_order("private-synthetic-token", attempt, account_probe=account, validate_one=validate)
            self.assertEqual(calls, list(ORDER[:2]))
            self.assertEqual(result["stopped_source"], ORDER[1])
            self.assertEqual(result["completed_sources"], [ORDER[0]])
            self.assertTrue((attempt / "terminal.json").exists())
            self.assertFalse((attempt / f"03-{ORDER[2].lower()}-started.json").exists())
            self.assertNotIn("private-synthetic-token", (attempt / "terminal.json").read_text())
            with self.assertRaisesRegex(RouteStop, "validation_attempt_collision"):
                validate_fixed_order("private-synthetic-token", attempt, account_probe=account, validate_one=validate)

    def test_unexpected_interruption_preserves_reserved_indeterminate_attempt(self) -> None:
        def account(_token: str) -> dict:
            return {"status": "account_probe_pass_free_credit_capacity_only", "at_least_240_free_basic_credits": True}

        def interrupted(_token: str, _source_id: str) -> dict:
            raise RuntimeError("synthetic interruption")

        with tempfile.TemporaryDirectory() as temp:
            attempt = Path(temp) / "attempt"
            with self.assertRaisesRegex(RuntimeError, "synthetic interruption"):
                validate_fixed_order("private-synthetic-token", attempt, account_probe=account, validate_one=interrupted)
            self.assertTrue((attempt / f"01-{ORDER[0].lower()}-started.json").exists())
            self.assertFalse((attempt / "terminal.json").exists())
            with self.assertRaisesRegex(RouteStop, "validation_attempt_collision"):
                validate_fixed_order("private-synthetic-token", attempt, account_probe=account, validate_one=interrupted)

    def test_account_failure_does_not_reserve_an_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            attempt = Path(temp) / "attempt"
            with self.assertRaisesRegex(RouteStop, "validation_account_capacity_unverified"):
                validate_fixed_order("private-synthetic-token", attempt, account_probe=lambda _: {"status": "stopped"})
            self.assertFalse(attempt.exists())

    @unittest.skipUnless(sys.platform == "win32", "PowerShell handoff is Windows-only")
    def test_powershell_precheck_asks_for_no_secret_when_unreleased(self) -> None:
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
             str(ROOT / "scripts/invoke_m2_asf_hyp3_rtc_validate_only_001.ps1"), "-CheckRelease"],
            cwd=ROOT, capture_output=True, text=True, timeout=20, check=False,
        )
        self.assertEqual(completed.returncode, 12)
        self.assertIn("no credential was requested", completed.stdout)
        self.assertNotIn("NASA Earthdata password", completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
