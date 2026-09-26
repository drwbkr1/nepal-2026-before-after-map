"""Disposable account-probe and token-exposure checks; never call ASF."""

from __future__ import annotations

import io
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from m2_asf_hyp3_account_probe_001 import (  # noqa: E402
    APPROVAL_REF,
    FINAL_PREFLIGHT_REF,
    HOST,
    EARTHDATA_HOST,
    EARTHDATA_TOKEN_PATH,
    IMPLEMENTATION_FILES,
    IMPLEMENTATION_GATE_REF,
    PROPOSAL_SHA256,
    RIGHTS_GATE_REF,
    ROOT,
    RouteStop,
    get_basic_account,
    get_earthdata_token,
    read_owner_credentials,
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

    def test_complete_synthetic_release_and_code_drift_stop(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for ref in (*IMPLEMENTATION_FILES, APPROVAL_REF):
                destination = root / ref
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / ref, destination)
            approval_sha = hashlib.sha256((root / APPROVAL_REF).read_bytes()).hexdigest()
            rights = {
                "authority": {"authority_ref": APPROVAL_REF},
                "bindings": {"proposal_sha256": PROPOSAL_SHA256, "approval_sha256": approval_sha},
                "terms": {"public_account_use_guidance_assessed": True, "job_and_product_rights_released": False},
                "sources": [{"criteria": [{"required": True, "status": "pass"} for _ in range(8)]}],
                "decision": {"status": "ready", "approved_actions": ["read_own_basic_account_capacity"]},
            }
            implementation = {
                "status": "pass_account_probe_implementation_public_ci_only",
                "bindings": {
                    "approval_sha256": approval_sha,
                    "implementation_file_sha256": {
                        ref: hashlib.sha256((root / ref).read_bytes()).hexdigest() for ref in IMPLEMENTATION_FILES
                    },
                },
                "public_ci": {"conclusion": "success"},
                "assertions": {"account_or_job_request_performed": False},
            }
            for ref, value in ((RIGHTS_GATE_REF, rights), (IMPLEMENTATION_GATE_REF, implementation)):
                destination = root / ref
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(json.dumps(value), encoding="utf-8")
            implementation_sha = hashlib.sha256((root / IMPLEMENTATION_GATE_REF).read_bytes()).hexdigest()
            preflight = {
                "status": "pass_no_content_account_probe_only",
                "bindings": {"approval_sha256": approval_sha, "implementation_gate_sha256": implementation_sha},
                "assertions": {"secret_read_or_account_request_performed": False},
            }
            (root / FINAL_PREFLIGHT_REF).write_text(json.dumps(preflight), encoding="utf-8")
            require_account_probe_release(root)
            (root / IMPLEMENTATION_FILES[0]).write_text("changed", encoding="utf-8")
            with self.assertRaisesRegex(RouteStop, "account_probe_not_released"):
                require_account_probe_release(root)

    def test_pipe_reads_only_one_ascii_secret(self) -> None:
        self.assertEqual(read_owner_token(io.BytesIO(b"synthetic-token.123\r\n")), "synthetic-token.123")
        for payload in (b"", b"synthetic token\n", b"synthetic-token"):
            with self.subTest(payload=payload), self.assertRaises(RouteStop):
                read_owner_token(io.BytesIO(payload))

    def test_credential_pipe_removes_only_line_terminator(self) -> None:
        self.assertEqual(
            read_owner_credentials(io.BytesIO(b"synthetic-user\r\nsynthetic-pass \r\n")),
            ("synthetic-user", "synthetic-pass "),
        )
        for payload in (b"", b"user\n", b"user:bad\npass\n", b"user\npass", b"user\npass\r\r\n"):
            with self.subTest(payload=payload), self.assertRaises(RouteStop):
                read_owner_credentials(io.BytesIO(payload))

    def test_earthdata_fixed_host_token_exchange_and_redirect_stop(self) -> None:
        class TokenConnection(FakeConnection):
            def getresponse(self) -> FakeResponse:
                return FakeResponse(self.status, {
                    "access_token": "synthetic.earthdata.token",
                    "token_type": "Bearer",
                    "user_id": "synthetic-private-identity",
                })

        instances = []

        def factory(host: str, timeout: int) -> TokenConnection:
            conn = TokenConnection(host, timeout)
            instances.append(conn)
            return conn

        self.assertEqual(
            get_earthdata_token("synthetic-user", "synthetic-pass", connection_factory=factory),
            "synthetic.earthdata.token",
        )
        self.assertEqual(instances[0].host, EARTHDATA_HOST)
        self.assertEqual(instances[0].request_record[:2], ("POST", EARTHDATA_TOKEN_PATH))
        self.assertEqual(instances[0].request_record[2]["Content-Length"], "0")
        self.assertTrue(instances[0].closed)
        with self.assertRaisesRegex(RouteStop, "earthdata_token_response_not_success"):
            get_earthdata_token(
                "synthetic-user", "synthetic-pass",
                connection_factory=lambda host, timeout: TokenConnection(host, timeout, status=302),
            )

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
        self.assertTrue(result["at_least_240_free_basic_credits"])
        self.assertNotIn("remaining_free_credits", result)
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
