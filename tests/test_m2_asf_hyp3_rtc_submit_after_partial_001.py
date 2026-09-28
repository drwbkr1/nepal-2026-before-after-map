"""Disposable after-job transport and no-retry tests; no ASF network use."""

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
from m2_asf_hyp3_rtc_core_001 import RouteStop, load_approved_jobs  # noqa: E402
from m2_asf_hyp3_rtc_submit_after_partial_001 import (  # noqa: E402
    APPROVAL_REF, APPROVAL_SHA, BUNDLE_REF, BUNDLE_SHA, FIRST_TERMINAL_REF,
    FIRST_TERMINAL_SHA, HOST, IMPLEMENTATION_FILES, IMPLEMENTATION_GATE_REF,
    PREFLIGHT_REF, PROPOSAL_REF, PROPOSAL_SHA, REVIEW_GATE_REF, SOURCE_GATE_REF,
    SOURCE_GATE_SHA, SOURCE_ID,
    _request, account_60, require_release, run_once, submit_after, validate_after,
)


class FakeResponse:
    def __init__(self, status: int, value: dict):
        self.status = status
        self.data = json.dumps(value).encode("utf-8")

    def read(self, _max_bytes: int) -> bytes:
        return self.data


class FakeConnection:
    calls: list[tuple] = []
    status = 200

    def __init__(self, host: str, timeout: int):
        self.host = host
        self.timeout = timeout
        self.closed = False

    def request(self, method: str, path: str, body=None, headers=None):
        self.request_record = (method, path, body, headers)
        self.calls.append((self.host, method, path, body, headers))

    def getresponse(self) -> FakeResponse:
        method, path, body, _headers = self.request_record
        if method == "GET":
            value = {"remaining_credits": 60, "application_status": "APPROVED", "user_id": "private-synthetic-user"}
        else:
            payload = json.loads(body)
            job = copy.deepcopy(payload["jobs"][0])
            job.update({"credit_cost": 60, "status_code": "PENDING", "execution_started": False,
                        "files": [], "job_id": "27836b79-e5b2-4d8f-932f-659724ea02c3",
                        "user_id": "private-synthetic-user"})
            value = {"validate_only": payload["validate_only"], "jobs": [job]}
        return FakeResponse(self.status, value)

    def close(self):
        self.closed = True


class AfterPartialTests(unittest.TestCase):
    def setUp(self):
        FakeConnection.calls = []
        FakeConnection.status = 200

    def test_unreleased_stops_before_secret(self):
        with tempfile.TemporaryDirectory() as temp, self.assertRaisesRegex(RouteStop, "after_release_unavailable"):
            root = Path(temp)
            require_release(root, root / "data" / "after" / "attempt")

    def test_complete_synthetic_release_and_drift(self):
        def write(path: Path, value: dict):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value), encoding="utf-8")

        def sha(path: Path) -> str:
            return hashlib.sha256(path.read_bytes()).hexdigest()

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = root / "data"
            data.mkdir()
            attempt = data / "after" / "attempt"
            for ref in (*IMPLEMENTATION_FILES, PROPOSAL_REF, BUNDLE_REF, APPROVAL_REF,
                        FIRST_TERMINAL_REF, SOURCE_GATE_REF):
                target = root / ref
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / ref, target)
            self.assertEqual(sha(root / PROPOSAL_REF), PROPOSAL_SHA)
            self.assertEqual(sha(root / BUNDLE_REF), BUNDLE_SHA)
            self.assertEqual(sha(root / APPROVAL_REF), APPROVAL_SHA)
            self.assertEqual(sha(root / FIRST_TERMINAL_REF), FIRST_TERMINAL_SHA)
            self.assertEqual(sha(root / SOURCE_GATE_REF), SOURCE_GATE_SHA)
            write(root / REVIEW_GATE_REF, {
                "status": "pass_exact_review_packet_public_ci_only",
                "bindings": {"owner_approval_sha256": APPROVAL_SHA},
                "observed_public_ci": {"run_conclusion": "success"},
            })
            write(root / IMPLEMENTATION_GATE_REF, {
                "status": "pass_submit_after_partial_implementation_public_ci_only",
                "bindings": {"proposal_sha256": PROPOSAL_SHA, "approval_sha256": APPROVAL_SHA,
                             "review_gate_sha256": sha(root / REVIEW_GATE_REF),
                             "implementation_file_sha256": {ref: sha(root / ref) for ref in IMPLEMENTATION_FILES}},
                "public_ci": {"conclusion": "success"},
            })
            write(root / PREFLIGHT_REF, {
                "status": "pass_submit_after_partial_no_content",
                "bindings": {"implementation_gate_sha256": sha(root / IMPLEMENTATION_GATE_REF),
                             "first_terminal_sha256": FIRST_TERMINAL_SHA},
                "assertions": {"attempt_absent": True, "no_secret_or_account_or_job_request": True},
            })
            require_release(root, attempt)
            (root / IMPLEMENTATION_FILES[0]).write_text("drift", encoding="utf-8")
            with self.assertRaisesRegex(RouteStop, "after_submission_not_released"):
                require_release(root, attempt)

    def test_exact_account_validation_submission_and_secret_exclusion(self):
        account = _request(
            "private-synthetic-token", "GET", "/user", connection_factory=FakeConnection)
        self.assertEqual(account["remaining_credits"], 60)
        # Use the transport factory for every stage without changing the live worker.
        import m2_asf_hyp3_rtc_submit_after_partial_001 as worker
        original = worker._request
        worker._request = lambda token, method, path, body=None: original(
            token, method, path, body, connection_factory=FakeConnection)
        try:
            self.assertEqual(account_60("private-synthetic-token")["status"], "pass_free_basic_capacity_at_least_60_only")
            self.assertEqual(validate_after("private-synthetic-token")["status"], "pass_validate_only_identity_and_cost_only")
            result = submit_after("private-synthetic-token")
        finally:
            worker._request = original
        self.assertEqual(result["job_type"], "RTC_GAMMA")
        self.assertEqual([call[1:3] for call in FakeConnection.calls[-3:]],
                         [("GET", "/user"), ("POST", "/jobs"), ("POST", "/jobs")])
        validation = json.loads(FakeConnection.calls[-2][3])
        submission = json.loads(FakeConnection.calls[-1][3])
        self.assertIs(validation["validate_only"], True)
        self.assertIs(submission["validate_only"], False)
        self.assertEqual(submission["jobs"][0]["job_parameters"], load_approved_jobs()[1]["job_parameters"])
        self.assertEqual(FakeConnection.calls[-1][0], HOST)
        self.assertNotIn("private-synthetic-user", json.dumps(result))
        self.assertNotIn("private-synthetic-token", json.dumps(result))

    def test_redirect_stops_without_following(self):
        FakeConnection.status = 302
        with self.assertRaisesRegex(RouteStop, "after_response_not_success"):
            _request("private-synthetic-token", "GET", "/user", connection_factory=FakeConnection)
        self.assertEqual(len(FakeConnection.calls), 1)

    def test_single_attempt_order_and_collision(self):
        calls = []
        with tempfile.TemporaryDirectory() as temp:
            attempt = Path(temp) / "attempt"
            result = run_once(
                "private-synthetic-token", attempt,
                probe=lambda _: (calls.append("account") or {"status": "pass_free_basic_capacity_at_least_60_only"}),
                validate=lambda _: (calls.append("validate") or {"source_id": SOURCE_ID, "status": "pass_validate_only_identity_and_cost_only"}),
                submit=lambda _: (calls.append("submit") or {"job_id": "27836b79-e5b2-4d8f-932f-659724ea02c3",
                                                      "job_type": "RTC_GAMMA", "credit_cost": 60}),
            )
            self.assertEqual(calls, ["account", "validate", "submit"])
            self.assertEqual(result["status"], "submitted_product_unverified")
            self.assertFalse(result["pixel_qa_pass"])
            self.assertTrue((attempt / "submission-request-reserved.json").exists())
            for path in attempt.iterdir():
                contents = path.read_text(encoding="utf-8")
                self.assertNotIn("private-synthetic-token", contents)
                self.assertNotIn("private-synthetic-user", contents)
            with self.assertRaisesRegex(RouteStop, "after_attempt_collision"):
                run_once("private-synthetic-token", attempt)
            self.assertEqual(calls, ["account", "validate", "submit"])

    def test_failure_stops_before_submission(self):
        with tempfile.TemporaryDirectory() as temp:
            attempt = Path(temp) / "attempt"
            result = run_once("private-synthetic-token", attempt,
                              probe=lambda _: {"status": "pass_free_basic_capacity_at_least_60_only"},
                              validate=lambda _: (_ for _ in ()).throw(RouteStop("synthetic_validate_failure")),
                              submit=lambda _: self.fail("processing request must not occur"))
            self.assertEqual(result["status"], "stopped_or_indeterminate_no_retry")
            self.assertEqual(result["code"], "synthetic_validate_failure")
            self.assertFalse((attempt / "submission-request-reserved.json").exists())

    def test_interruption_after_submission_reservation_is_terminal(self):
        with tempfile.TemporaryDirectory() as temp:
            attempt = Path(temp) / "attempt"
            result = run_once("private-synthetic-token", attempt,
                              probe=lambda _: {"status": "pass_free_basic_capacity_at_least_60_only"},
                              validate=lambda _: {"source_id": SOURCE_ID, "status": "pass_validate_only_identity_and_cost_only"},
                              submit=lambda _: (_ for _ in ()).throw(RuntimeError("private-synthetic-token")))
            self.assertEqual(result["status"], "stopped_or_indeterminate_no_retry")
            self.assertEqual(result["code"], "after_unexpected_failure")
            self.assertNotIn("private-synthetic-token", (attempt / "terminal.json").read_text())
            with self.assertRaisesRegex(RouteStop, "after_attempt_collision"):
                run_once("private-synthetic-token", attempt)

    @unittest.skipUnless(sys.platform == "win32", "PowerShell handoff is Windows-only")
    def test_powershell_precheck_asks_for_no_secret_when_unreleased(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = Path(temp)
            shutil.copyfile(ROOT / "scripts/invoke_m2_asf_hyp3_rtc_submit_after_partial_001.ps1",
                            fixture / "invoke_m2_asf_hyp3_rtc_submit_after_partial_001.ps1")
            (fixture / "m2_asf_hyp3_rtc_submit_after_partial_001.py").write_text(
                "import json, sys\nprint(json.dumps({'status':'stopped','code':'after_release_unavailable'}))\nsys.exit(12)\n",
                encoding="utf-8",
            )
            completed = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                 str(fixture / "invoke_m2_asf_hyp3_rtc_submit_after_partial_001.ps1"), "-CheckRelease"],
                cwd=fixture, capture_output=True, text=True, timeout=20, check=False,
            )
        self.assertEqual(completed.returncode, 12)
        self.assertIn("no credential was requested", completed.stdout)
        self.assertNotIn("NASA Earthdata password", completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
