"""Disposable after-product status and one-ZIP intake tests; no ASF calls."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m2_asf_hyp3_rtc_acquire_after_partial_001 import (  # noqa: E402
    HOST, get_after_status, observe_and_maybe_acquire, require_release,
    transfer_after_once,
)
from m2_asf_hyp3_rtc_after_descriptor_core_001 import submission_view  # noqa: E402
from m2_asf_hyp3_rtc_core_001 import RouteStop  # noqa: E402
from m2_asf_hyp3_rtc_package_core_001 import REQUIRED_SUFFIXES  # noqa: E402


JOB_ID = "27836b79-e5b2-4d8f-932f-659724ea02c3"
FILENAME = "S1D_IW_20260828T122141_DVP_RTC10_G_gpuned_944C.zip"
URL = f"https://abc.cloudfront.net/{JOB_ID}/{FILENAME}"


def submission() -> dict:
    return {"status": "submitted_product_unverified", "source_id": "M1-SRC-005",
            "job_id": JOB_ID, "credit_cost": 60, "credentials_recorded": False,
            "product_bytes_verified": False, "pixel_qa_pass": False}


def reply(status: str = "SUCCEEDED") -> dict:
    return {**submission_view(submission()), "status_code": status,
            "files": ([{"filename": FILENAME, "size": 1234, "url": URL}]
                      if status == "SUCCEEDED" else []),
            "user_id": "private-synthetic-user"}


def product_bytes() -> bytes:
    product = FILENAME[:-4]
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_STORED) as archive:
        archive.writestr(product + "/", b"")
        for suffix in REQUIRED_SUFFIXES:
            archive.writestr(f"{product}/{product}{suffix}", b"generated-data")
    return buffer.getvalue()


class FakeResponse:
    status = 200

    def __init__(self, value: dict):
        self.data = json.dumps(value).encode("utf-8")

    def read(self, _limit: int) -> bytes:
        return self.data


class FakeConnection:
    instances: list = []

    def __init__(self, host: str, timeout: int):
        self.host, self.timeout = host, timeout
        self.closed = False
        self.instances.append(self)

    def request(self, method: str, path: str, *, headers: dict):
        self.record = (method, path, headers)

    def getresponse(self) -> FakeResponse:
        return FakeResponse(reply())

    def close(self):
        self.closed = True


class AfterAcquireTests(unittest.TestCase):
    def setUp(self):
        FakeConnection.instances = []

    def test_unreleased_stops_before_secret(self):
        with tempfile.TemporaryDirectory() as temp, self.assertRaisesRegex(RouteStop, "after_acquire_release_unavailable"):
            base = Path(temp)
            require_release(base / "repo", base / "custody", base / "custody" / "attempt")

    def test_exact_status_get_and_sanitized_result(self):
        raw, status = get_after_status("private-synthetic-token", submission(),
                                       connection_factory=FakeConnection)
        connection = FakeConnection.instances[0]
        self.assertEqual(connection.host, HOST)
        self.assertEqual(connection.record[:2], ("GET", f"/jobs/{JOB_ID}"))
        self.assertEqual(connection.record[2]["Authorization"], "Bearer private-synthetic-token")
        self.assertTrue(connection.closed)
        self.assertEqual(raw["files"][0]["url"], URL)
        self.assertEqual(status["disposition"], "service_succeeded_product_unverified")
        self.assertNotIn(URL, json.dumps(status))
        self.assertNotIn("private-synthetic-user", json.dumps(status))

    def test_pending_observation_makes_no_zip_attempt(self):
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)
            obs = data / "observation"
            attempt = data / "acquire" / "attempt"
            result = observe_and_maybe_acquire(
                "private-synthetic-token", submission(), obs, attempt,
                data / "products", data,
                get_status=lambda _token, _submission: (
                    reply("PENDING"),
                    {"source_id": "M1-SRC-005", "job_id": JOB_ID,
                     "disposition": "service_not_terminal_observe_same_job",
                     "provider_status": "PENDING"}),
                transfer=lambda *_args: self.fail("ZIP must not be requested"),
            )
            self.assertEqual(result["disposition"], "service_not_terminal_observe_same_job")
            self.assertFalse(attempt.exists())
            self.assertEqual(len(list(obs.glob("observation-*/terminal.json"))), 1)

    def test_success_reserves_one_zip_and_excludes_url_and_secret(self):
        calls = []
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)
            obs = data / "observation"
            attempt = data / "acquire" / "attempt"
            products = data / "products"

            def transfer(private, controlled_root, staging, destination):
                calls.append((private, controlled_root, staging, destination))
                return {"status": "pass_local_zip_promoted_no_replace", "source_id": "M1-SRC-005",
                        "job_id": JOB_ID, "product_filename": FILENAME,
                        "archive_size_bytes": 1234, "archive_sha256": "a" * 64,
                        "credentials_recorded": False}

            status = {"source_id": "M1-SRC-005", "job_id": JOB_ID,
                      "disposition": "service_succeeded_product_unverified",
                      "provider_status": "SUCCEEDED"}
            result = observe_and_maybe_acquire(
                "private-synthetic-token", submission(), obs, attempt, products, data,
                get_status=lambda _token, _submission: (reply(), status), transfer=transfer)
            self.assertEqual(result["status"], "pass_local_zip_promoted_no_replace")
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][3], products / FILENAME)
            self.assertTrue((attempt / "started.json").exists())
            self.assertTrue((attempt / "terminal.json").exists())
            for path in list(attempt.iterdir()) + list(obs.glob("observation-*/*.json")):
                contents = path.read_text(encoding="utf-8")
                self.assertNotIn(URL, contents)
                self.assertNotIn("private-synthetic-token", contents)
                self.assertNotIn("private-synthetic-user", contents)
            with self.assertRaisesRegex(RouteStop, "after_acquire_attempt_collision"):
                observe_and_maybe_acquire("private-synthetic-token", submission(), obs, attempt,
                                          products, data, get_status=lambda *_: (reply(), status),
                                          transfer=transfer)
            self.assertEqual(len(calls), 1)

    def test_transfer_error_terminal_no_retry(self):
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)
            attempt = data / "acquire" / "attempt"
            status = {"source_id": "M1-SRC-005", "job_id": JOB_ID,
                      "disposition": "service_succeeded_product_unverified"}
            result = observe_and_maybe_acquire(
                "private-synthetic-token", submission(), data / "observe", attempt,
                data / "products", data,
                get_status=lambda *_: (reply(), status),
                transfer=lambda *_: (_ for _ in ()).throw(RouteStop("synthetic_zip_failure")))
            self.assertEqual(result["status"], "stopped_no_automatic_retry")
            self.assertEqual(result["code"], "synthetic_zip_failure")
            self.assertTrue((attempt / "terminal.json").exists())

    def test_disposable_http_transfer_one_get_no_auth_header(self):
        payload = product_bytes()

        class ZipResponse(BytesIO):
            status = 200

            def getheader(self, name):
                return {"Content-Length": str(len(payload))}.get(name)

        class ZipConnection:
            requests = []

            def __init__(self, host, timeout):
                self.host, self.timeout = host, timeout

            def request(self, method, path, *, headers):
                self.requests.append((self.host, method, path, headers))

            def getresponse(self):
                return ZipResponse(payload)

            def close(self):
                pass

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            staging_dir = root / "attempt"
            product_dir = root / "product"
            staging_dir.mkdir()
            product_dir.mkdir()
            private = {"source_id": "M1-SRC-005", "job_id": JOB_ID,
                       "filename": FILENAME, "size_bytes": len(payload), "url": URL}
            result = transfer_after_once(private, root, staging_dir / "product.part",
                                         product_dir / FILENAME, connection_factory=ZipConnection)
            self.assertEqual(result["status"], "pass_local_zip_promoted_no_replace")
            self.assertEqual((product_dir / FILENAME).read_bytes(), payload)
            self.assertEqual(len(ZipConnection.requests), 1)
            self.assertEqual(ZipConnection.requests[0][1:3],
                             ("GET", f"/{JOB_ID}/{FILENAME}"))
            self.assertNotIn("Authorization", ZipConnection.requests[0][3])

    def test_transfer_rejects_unapproved_host_before_request(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "attempt").mkdir()
            (root / "product").mkdir()
            private = {"source_id": "M1-SRC-005", "job_id": JOB_ID,
                       "filename": FILENAME, "size_bytes": 1234,
                       "url": f"https://evil.example/{JOB_ID}/{FILENAME}"}
            with self.assertRaisesRegex(RouteStop, "after_acquire_url_invalid"):
                transfer_after_once(private, root, root / "attempt" / "product.part",
                                    root / "product" / FILENAME,
                                    connection_factory=lambda *_args, **_kwargs: self.fail("no network"))

    @unittest.skipUnless(sys.platform == "win32", "PowerShell handoff is Windows-only")
    def test_wrapper_precheck_requests_no_secret_when_unreleased(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = Path(temp)
            wrapper = fixture / "invoke_m2_asf_hyp3_rtc_acquire_after_partial_001.ps1"
            shutil.copyfile(ROOT / "scripts/invoke_m2_asf_hyp3_rtc_acquire_after_partial_001.ps1", wrapper)
            (fixture / "m2_asf_hyp3_rtc_acquire_after_partial_001.py").write_text(
                "import json,sys\nprint(json.dumps({'status':'stopped','code':'gate_missing'}))\nsys.exit(12)\n",
                encoding="utf-8",
            )
            completed = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                 str(wrapper), "-CheckRelease"], cwd=fixture, capture_output=True,
                text=True, timeout=20, check=False,
            )
        self.assertEqual(completed.returncode, 12)
        self.assertIn("no credential was requested", completed.stdout)


if __name__ == "__main__":
    unittest.main()
