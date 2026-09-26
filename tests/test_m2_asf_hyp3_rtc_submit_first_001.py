"""Disposable submission-transport and interruption tests; no ASF calls."""

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
from m2_asf_hyp3_rtc_core_001 import APPROVAL_REF, ORDER, PROPOSAL_SHA256, RouteStop, load_approved_jobs  # noqa: E402
from m2_asf_hyp3_rtc_submit_first_001 import (  # noqa: E402
    HOST, SOURCE_ID, IMPLEMENTATION_FILES, IMPLEMENTATION_GATE_REF, PREFLIGHT_REF,
    SOURCE_GATE_REF, VALIDATION_REF, post_exact_first_job, require_submission_release,
    submit_first,
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
        return FakeResponse({"validate_only": False, "jobs": [job]})

    def close(self) -> None:
        self.closed = True


class FirstSubmissionTests(unittest.TestCase):
    def test_unreleased_worker_stops_before_secret(self) -> None:
        with tempfile.TemporaryDirectory() as temp, self.assertRaisesRegex(RouteStop, "submission_release_unavailable"):
            root = Path(temp)
            require_submission_release(root, root / "data" / "submit" / "attempt", root / "data" / "validation")

    def test_synthetic_complete_release_then_file_drift_stops(self) -> None:
        def write_json(path: Path, value: dict) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value), encoding="utf-8")

        def sha(path: Path) -> str:
            return hashlib.sha256(path.read_bytes()).hexdigest()

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_root = root / "data"
            data_root.mkdir()
            validation_root = data_root / "validation"
            validation_root.mkdir()
            attempt_root = data_root / "submit" / "attempt"
            for ref in (*IMPLEMENTATION_FILES, APPROVAL_REF):
                target = root / ref
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / ref, target)
            terminal = {"status": "pass_all_four_validate_only_requests", "completed_sources": list(ORDER),
                        "processing_job_submissions_requested": 0}
            write_json(validation_root / "terminal.json", terminal)
            write_json(root / VALIDATION_REF, {
                "status": "pass_exact_four_scene_validation_identity_and_cost_only",
                "exact_order": list(ORDER),
                "verification": {"processing_job_submissions_requested": 0},
                "attempt_terminal_sha256": sha(validation_root / "terminal.json"),
            })
            write_json(root / SOURCE_GATE_REF, {
                "decision": {"status": "ready", "approved_actions": ["submit_exact_free_basic_rtc_job"]},
                "authority": {"authority_ref": APPROVAL_REF},
                "bindings": {"approved_proposal_sha256": PROPOSAL_SHA256,
                             "owner_approval_sha256": sha(root / APPROVAL_REF),
                             "validate_only_terminal_reconciliation_sha256": sha(root / VALIDATION_REF)},
                "sources": [{"criteria": [{"required": True, "status": "pass"} for _ in range(8)]}],
            })
            write_json(root / IMPLEMENTATION_GATE_REF, {
                "status": "pass_submit_first_implementation_public_ci_only",
                "bindings": {
                    "proposal_sha256": PROPOSAL_SHA256,
                    "approval_sha256": sha(root / APPROVAL_REF),
                    "source_gate_sha256": sha(root / SOURCE_GATE_REF),
                    "validation_reconciliation_sha256": sha(root / VALIDATION_REF),
                    "implementation_file_sha256": {ref: sha(root / ref) for ref in IMPLEMENTATION_FILES},
                },
                "public_ci": {"conclusion": "success"},
            })
            write_json(root / PREFLIGHT_REF, {
                "status": "pass_submit_first_no_content",
                "bindings": {"implementation_gate_sha256": sha(root / IMPLEMENTATION_GATE_REF),
                             "source_gate_sha256": sha(root / SOURCE_GATE_REF)},
                "assertions": {"job_request_performed": False},
            })
            require_submission_release(root, attempt_root, validation_root)
            (root / IMPLEMENTATION_FILES[0]).write_text("drift", encoding="utf-8")
            with self.assertRaisesRegex(RouteStop, "submission_not_released"):
                require_submission_release(root, attempt_root, validation_root)

    def test_exact_host_payload_and_sanitized_response(self) -> None:
        connections = []

        def factory(host: str, timeout: int) -> FakeConnection:
            connection = FakeConnection(host, timeout)
            connections.append(connection)
            return connection

        result = post_exact_first_job("private-synthetic-token", connection_factory=factory)
        connection = connections[0]
        method, path, raw, headers = connection.request_record
        self.assertEqual((connection.host, method, path), (HOST, "POST", "/jobs"))
        self.assertEqual(headers["Authorization"], "Bearer private-synthetic-token")
        payload = json.loads(raw)
        self.assertIs(payload["validate_only"], False)
        self.assertEqual(len(payload["jobs"]), 1)
        self.assertEqual(payload["jobs"][0]["job_parameters"], load_approved_jobs()[0]["job_parameters"])
        self.assertEqual(result["source_id"], ORDER[0])
        self.assertEqual(result["status"], "submitted_product_unverified")
        rendered = json.dumps(result)
        self.assertNotIn("private-synthetic-token", rendered)
        self.assertNotIn("private-synthetic-user", rendered)
        self.assertTrue(connection.closed)

    def test_redirect_does_not_get_followed(self) -> None:
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

        with self.assertRaisesRegex(RouteStop, "submission_response_not_success"):
            post_exact_first_job("private-synthetic-token", connection_factory=factory)
        self.assertTrue(instances[0].closed)

    def test_untrusted_job_id_is_not_persistable(self) -> None:
        class BadIdConnection(FakeConnection):
            def getresponse(self) -> FakeResponse:
                reply = super().getresponse()
                value = json.loads(reply.body)
                value["jobs"][0]["job_id"] = "x" * 36
                return FakeResponse(value)

        with self.assertRaisesRegex(RouteStop, "submission_job_id_invalid"):
            post_exact_first_job("private-synthetic-token", connection_factory=BadIdConnection)

    def test_fresh_account_failure_does_not_reserve_or_post(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            attempt = Path(temp) / "attempt"
            with self.assertRaisesRegex(RouteStop, "submission_fresh_free_capacity_unverified"):
                submit_first("private-synthetic-token", attempt, account_probe=lambda _: {"status": "stopped"},
                             post_one=lambda _: self.fail("POST must not occur"))
            self.assertFalse(attempt.exists())

    def test_single_post_receipt_and_attempt_collision(self) -> None:
        calls = []

        def account(_token: str) -> dict:
            return {"status": "account_probe_pass_free_credit_capacity_only", "at_least_240_free_basic_credits": True}

        def post(token: str) -> dict:
            calls.append(token)
            return post_exact_first_job(token, connection_factory=FakeConnection)

        with tempfile.TemporaryDirectory() as temp:
            attempt = Path(temp) / "attempt"
            result = submit_first("private-synthetic-token", attempt, account_probe=account, post_one=post)
            self.assertEqual(calls, ["private-synthetic-token"])
            self.assertEqual(result["source_id"], SOURCE_ID)
            self.assertEqual(result["status"], "submitted_product_unverified")
            started = json.loads((attempt / "started.json").read_text())
            terminal = json.loads((attempt / "terminal.json").read_text())
            self.assertIs(started["validate_only"], False)
            self.assertIs(terminal["product_bytes_verified"], False)
            self.assertNotIn("private-synthetic-token", str(started) + str(terminal))
            self.assertNotIn("private-synthetic-user", str(started) + str(terminal))
            with self.assertRaisesRegex(RouteStop, "submission_attempt_collision"):
                submit_first("private-synthetic-token", attempt, account_probe=account, post_one=post)
            self.assertEqual(len(calls), 1)

    def test_post_error_is_terminal_no_retry(self) -> None:
        def account(_token: str) -> dict:
            return {"status": "account_probe_pass_free_credit_capacity_only", "at_least_240_free_basic_credits": True}

        with tempfile.TemporaryDirectory() as temp:
            attempt = Path(temp) / "attempt"
            result = submit_first("private-synthetic-token", attempt, account_probe=account,
                                  post_one=lambda _: (_ for _ in ()).throw(RouteStop("synthetic_rejection")))
            self.assertEqual(result["status"], "stopped_or_indeterminate_no_retry")
            self.assertEqual(json.loads((attempt / "terminal.json").read_text())["code"], "synthetic_rejection")

    def test_interruption_preserves_reserved_attempt(self) -> None:
        def account(_token: str) -> dict:
            return {"status": "account_probe_pass_free_credit_capacity_only", "at_least_240_free_basic_credits": True}

        def interrupted(_token: str) -> dict:
            raise RuntimeError("synthetic interruption")

        with tempfile.TemporaryDirectory() as temp:
            attempt = Path(temp) / "attempt"
            with self.assertRaisesRegex(RuntimeError, "synthetic interruption"):
                submit_first("private-synthetic-token", attempt, account_probe=account, post_one=interrupted)
            self.assertTrue((attempt / "started.json").exists())
            self.assertFalse((attempt / "terminal.json").exists())
            with self.assertRaisesRegex(RouteStop, "submission_attempt_collision"):
                submit_first("private-synthetic-token", attempt, account_probe=account, post_one=interrupted)

    @unittest.skipUnless(sys.platform == "win32", "PowerShell handoff is Windows-only")
    def test_powershell_precheck_asks_for_no_secret_when_unreleased(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            fixture = Path(temp)
            wrapper = fixture / "invoke_m2_asf_hyp3_rtc_submit_first_001.ps1"
            shutil.copyfile(ROOT / "scripts/invoke_m2_asf_hyp3_rtc_submit_first_001.ps1", wrapper)
            (fixture / "m2_asf_hyp3_rtc_submit_first_001.py").write_text(
                "import json, sys\n"
                "print(json.dumps({'status': 'stopped', 'code': 'submission_release_unavailable'}))\n"
                "sys.exit(12)\n", encoding="utf-8",
            )
            completed = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(wrapper), "-CheckRelease"],
                cwd=fixture, capture_output=True, text=True, timeout=20, check=False,
            )
        self.assertEqual(completed.returncode, 12)
        self.assertIn("no credential was requested", completed.stdout)
        self.assertNotIn("NASA Earthdata password", completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
