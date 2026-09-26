"""Disposable account-probe and token-exposure checks; never call ASF."""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from m2_asf_hyp3_account_probe_001 import (  # noqa: E402
    HOST,
    RouteStop,
    get_basic_account,
    read_owner_token,
    require_account_probe_release,
)


class FakeResponse:
    def __init__(self, status: int, body: dict):
        self.status = status
        self.body = json.dumps(body).encode("utf-8")

    def read(self, _count: int) -> bytes:
        return self.body


class FakeConnection:
    def __init__(self, host: str, timeout: int, *, status: int = 200):
        self.host = host
        self.timeout = timeout
        self.status = status
        self.request_record = None
        self.closed = False

    def request(self, method: str, path: str, headers: dict) -> None:
        self.request_record = (method, path, headers)

    def getresponse(self) -> FakeResponse:
        return FakeResponse(self.status, {
            "remaining_credits": 8000,
            "application_status": "NOT_STARTED",
            "user_id": "synthetic-private-identity",
            "job_names": ["synthetic-private-job"],
            "use_case": "synthetic-private-text",
        })

    def close(self) -> None:
        self.closed = True


class AccountProbeTests(unittest.TestCase):
    def test_unreleased_account_probe_does_not_read_a_token(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, self.assertRaises(RouteStop):
            require_account_probe_release(Path(temporary))

    def test_pipe_reads_only_one_ascii_secret(self) -> None:
        self.assertEqual(read_owner_token(io.BytesIO(b"synthetic-token.123\r\n")), "synthetic-token.123")
        for payload in (b"", b"synthetic token\n", b"synthetic-token"):
            with self.subTest(payload=payload), self.assertRaises(RouteStop):
                read_owner_token(io.BytesIO(payload))

    def test_fixed_host_get_only_and_sanitized_result(self) -> None:
        instances = []

        def factory(host: str, timeout: int) -> FakeConnection:
            conn = FakeConnection(host, timeout)
            instances.append(conn)
            return conn

        result = get_basic_account("synthetic-token.123", connection_factory=factory)
        self.assertEqual(instances[0].host, HOST)
        self.assertEqual(instances[0].request_record[0:2], ("GET", "/user"))
        self.assertTrue(instances[0].closed)
        rendered = json.dumps(result)
        for forbidden in ("synthetic-token.123", "synthetic-private-identity", "synthetic-private-job", "synthetic-private-text"):
            self.assertNotIn(forbidden, rendered)
        self.assertEqual(result["remaining_free_credits"], 8000)
        self.assertFalse(result["exact_s1d_job_eligibility_verified"])

    def test_redirect_does_not_follow_or_disclose(self) -> None:
        instances = []

        def factory(host: str, timeout: int) -> FakeConnection:
            conn = FakeConnection(host, timeout, status=302)
            instances.append(conn)
            return conn

        with self.assertRaisesRegex(RouteStop, "account_response_not_success"):
            get_basic_account("synthetic-token.123", connection_factory=factory)
        self.assertTrue(instances[0].closed)

    @unittest.skipUnless(sys.platform == "win32", "PowerShell handoff is Windows-only")
    def test_powershell_precheck_never_prompts_for_token(self) -> None:
        root = Path(__file__).resolve().parents[1]
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
             str(root / "scripts/invoke_m2_asf_hyp3_account_probe_001.ps1"), "-CheckRelease"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertTrue(
            "no token was requested" in completed.stdout or
            "HyP3 account probe released; no token was requested" in completed.stdout
        )
        self.assertNotIn("NASA Earthdata bearer token", completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
