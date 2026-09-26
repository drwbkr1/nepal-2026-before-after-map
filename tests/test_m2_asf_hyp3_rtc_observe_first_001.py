"""Synthetic first-job status observation tests; no ASF or project data."""

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
from m2_asf_hyp3_rtc_core_001 import APPROVAL_REF, ORDER, RouteStop, load_approved_jobs, one_job_payload  # noqa: E402
from m2_asf_hyp3_rtc_observe_first_001 import (  # noqa: E402
    HOST, IMPLEMENTATION_FILES, MONITOR_GATE_REF, SOURCE_GATE_REF, SUBMISSION_REF,
    get_one_job_status, observe_once, require_observation_release,
)


JOB_ID = "27836b79-e5b2-4d8f-932f-659724ea02c3"


def submission() -> dict:
    expected = one_job_payload(load_approved_jobs(), ORDER[0])["jobs"][0]
    return {
        **copy.deepcopy(expected), "status": "submitted_product_unverified",
        "source_id": ORDER[0], "job_id": JOB_ID, "status_code": "PENDING",
        "credit_cost": 60, "credentials_recorded": False,
        "product_bytes_verified": False, "pixel_qa_pass": False,
    }


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

    def request(self, method: str, path: str, headers: dict) -> None:
        self.request_record = (method, path, headers)

    def getresponse(self) -> FakeResponse:
        job = copy.deepcopy(submission())
        job.update({"user_id": "private-synthetic-user", "files": [],
                    "logs": ["https://example.invalid/private-log"]})
        return FakeResponse(job)

    def close(self) -> None:
        self.closed = True


class FirstObservationTests(unittest.TestCase):
    def test_missing_gate_or_job_stops_before_secret(self) -> None:
        with tempfile.TemporaryDirectory() as temp, self.assertRaisesRegex(RouteStop, "observation_release_unavailable"):
            root = Path(temp)
            require_observation_release(root, root / "data", root / "data" / "observations")

    def test_complete_fixture_releases_only_exact_submission(self) -> None:
        def write_json(path: Path, value: dict) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value), encoding="utf-8")

        def sha(path: Path) -> str:
            return hashlib.sha256(path.read_bytes()).hexdigest()

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_root = root / "data"
            data_root.mkdir()
            for ref in (*IMPLEMENTATION_FILES, APPROVAL_REF, SOURCE_GATE_REF):
                target = root / ref
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / ref, target)
            write_json(data_root / SUBMISSION_REF, submission())
            write_json(root / MONITOR_GATE_REF, {
                "status": "pass_observe_first_implementation_public_ci_only",
                "bindings": {
                    "approval_sha256": sha(root / APPROVAL_REF),
                    "source_gate_sha256": sha(root / SOURCE_GATE_REF),
                    "implementation_file_sha256": {ref: sha(root / ref) for ref in IMPLEMENTATION_FILES},
                },
                "public_ci": {"conclusion": "success"},
            })
            observation_parent = data_root / "observations"
            result = require_observation_release(root, data_root, observation_parent)
            self.assertEqual(result["job_id"], JOB_ID)
            write_json(data_root / SUBMISSION_REF, {**submission(), "job_id": "x" * 36})
            with self.assertRaisesRegex(RouteStop, "observation_not_released"):
                require_observation_release(root, data_root, observation_parent)

    def test_exact_get_no_redirect_and_sanitized_status(self) -> None:
        instances = []

        def factory(host: str, timeout: int) -> FakeConnection:
            instance = FakeConnection(host, timeout)
            instances.append(instance)
            return instance

        result = get_one_job_status("private-synthetic-token", submission(), connection_factory=factory)
        instance = instances[0]
        self.assertEqual(instance.host, HOST)
        self.assertEqual(instance.request_record[:2], ("GET", f"/jobs/{JOB_ID}"))
        self.assertEqual(instance.request_record[2]["Authorization"], "Bearer private-synthetic-token")
        self.assertEqual(result["disposition"], "service_not_terminal_observe_same_job")
        self.assertNotIn("private-synthetic-user", str(result))
        self.assertNotIn("private-log", str(result))
        self.assertNotIn("private-synthetic-token", str(result))
        self.assertTrue(instance.closed)

    def test_status_failure_and_success_boundaries(self) -> None:
        class FailedConnection(FakeConnection):
            def getresponse(self) -> FakeResponse:
                value = json.loads(super().getresponse().body)
                value["status_code"] = "FAILED"
                return FakeResponse(value)

        failed = get_one_job_status("private-synthetic-token", submission(), connection_factory=FailedConnection)
        self.assertEqual(failed["disposition"], "service_failed_terminal_no_retry")

        class SuccessConnection(FakeConnection):
            def getresponse(self) -> FakeResponse:
                value = json.loads(super().getresponse().body)
                value["status_code"] = "SUCCEEDED"
                value["files"] = [{"filename": "synthetic.zip", "size": 10,
                                   "url": "https://synthetic.cloudfront.net/product.zip"}]
                return FakeResponse(value)

        success = get_one_job_status("private-synthetic-token", submission(), connection_factory=SuccessConnection)
        self.assertEqual(success["disposition"], "service_succeeded_product_unverified")
        self.assertEqual(success["reported_file_count"], 1)
        self.assertNotIn("cloudfront", str(success))

    def test_redirect_and_wrong_job_id_stop_without_following(self) -> None:
        class RedirectConnection(FakeConnection):
            def getresponse(self) -> FakeResponse:
                response = super().getresponse()
                response.status = 302
                return response

        with self.assertRaisesRegex(RouteStop, "observation_response_not_success"):
            get_one_job_status("private-synthetic-token", submission(), connection_factory=RedirectConnection)

        class WrongJobConnection(FakeConnection):
            def getresponse(self) -> FakeResponse:
                value = json.loads(super().getresponse().body)
                value["job_id"] = "17edbff3-35fb-48e1-aa5d-683872c1a161"
                return FakeResponse(value)

        with self.assertRaisesRegex(RouteStop, "job_status_identity_mismatch"):
            get_one_job_status("private-synthetic-token", submission(), connection_factory=WrongJobConnection)

    def test_one_reserved_get_per_invocation_and_no_retry_on_failure(self) -> None:
        calls = []

        def status(_token: str, _submission: dict) -> dict:
            calls.append(1)
            raise RouteStop("synthetic_transient")

        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp) / "observations"
            result = observe_once("private-synthetic-token", submission(), parent, get_status=status)
            self.assertEqual(result["status"], "stopped_no_job_mutation")
            self.assertEqual(len(calls), 1)
            folders = list(parent.iterdir())
            self.assertEqual(len(folders), 1)
            self.assertTrue((folders[0] / "started.json").exists())
            terminal = (folders[0] / "terminal.json").read_text()
            self.assertNotIn("private-synthetic-token", terminal)
            self.assertNotIn("private-synthetic-user", terminal)

    def test_interruption_keeps_reserved_observation(self) -> None:
        def interrupted(_token: str, _submission: dict) -> dict:
            raise RuntimeError("synthetic interruption")

        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp) / "observations"
            with self.assertRaisesRegex(RuntimeError, "synthetic interruption"):
                observe_once("private-synthetic-token", submission(), parent, get_status=interrupted)
            folders = list(parent.iterdir())
            self.assertEqual(len(folders), 1)
            self.assertTrue((folders[0] / "started.json").exists())
            self.assertFalse((folders[0] / "terminal.json").exists())

    @unittest.skipUnless(sys.platform == "win32", "PowerShell handoff is Windows-only")
    def test_powershell_unreleased_gate_no_secret_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            fixture = Path(temp)
            wrapper = fixture / "invoke_m2_asf_hyp3_rtc_observe_first_001.ps1"
            shutil.copyfile(ROOT / "scripts/invoke_m2_asf_hyp3_rtc_observe_first_001.ps1", wrapper)
            (fixture / "m2_asf_hyp3_rtc_observe_first_001.py").write_text(
                "import json, sys\n"
                "print(json.dumps({'status': 'stopped', 'code': 'observation_release_unavailable'}))\n"
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
