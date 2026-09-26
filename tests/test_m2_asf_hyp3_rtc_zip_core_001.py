"""Disposable ZIP tests; no project product or external custody is opened."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from zipfile import ZIP_STORED, ZipFile, ZipInfo


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from m2_asf_hyp3_rtc_core_001 import ORDER, RouteStop, load_approved_jobs, one_job_payload  # noqa: E402
from m2_asf_hyp3_rtc_http_transfer_001 import (  # noqa: E402
    fetch_first_descriptor_once, transfer_first_zip_once,
)
from m2_asf_hyp3_rtc_acquire_first_001 import (  # noqa: E402
    EXACT_JOB_ID, acquire_first_once,
)
from m2_asf_hyp3_rtc_package_core_001 import REQUIRED_SUFFIXES  # noqa: E402
from m2_asf_hyp3_rtc_zip_core_001 import inspect_package_zip  # noqa: E402
from m2_asf_hyp3_rtc_transfer_core_001 import (  # noqa: E402
    promote_verified_zip_no_replace, stream_exact_zip_once,
)


def make_zip(path: Path, source_id: str, *, traversal: bool = False, empty_suffix: str | None = None, special_suffix: str | None = None) -> None:
    job = next(item for item in load_approved_jobs() if item["source_id"] == source_id)
    start = job["job_parameters"]["granules"][0].split("_")[4]
    root = f"S1D_IW_{start}_DVP_RTC10_G_gpuned_ABCD"
    with ZipFile(path, "w", ZIP_STORED) as archive:
        archive.writestr(root + "/", b"")
        for suffix in REQUIRED_SUFFIXES:
            name = f"{root}/{root}{suffix}"
            info = ZipInfo(name)
            if suffix == special_suffix:
                info.create_system = 3
                info.external_attr = 0o120777 << 16
            archive.writestr(info, b"" if suffix == empty_suffix else b"synthetic")
        if traversal:
            archive.writestr(f"{root}/../escape", b"synthetic")


def binding(path: Path) -> dict:
    return {"expected_size_bytes": path.stat().st_size, "expected_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def synthetic_job_reply(zip_bytes: bytes) -> tuple[dict, dict]:
    job = one_job_payload(load_approved_jobs(), ORDER[0])["jobs"][0]
    job_id = "27836b79-e5b2-4d8f-932f-659724ea02c3"
    submission = {**job, "job_id": job_id, "credit_cost": 60}
    start = job["job_parameters"]["granules"][0].split("_")[4]
    filename = f"S1D_IW_{start}_DVP_RTC10_G_gpuned_ABCD.zip"
    reply = {
        **submission, "status_code": "SUCCEEDED", "user_id": "private-user",
        "files": [{"filename": filename, "size": len(zip_bytes),
                   "url": f"https://hyp3-contentbucket-example.s3.us-west-2.amazonaws.com/{job_id}/{filename}"}],
    }
    return submission, reply


class FakeResponse(BytesIO):
    def __init__(self, payload: bytes, *, status: int = 200, headers: dict | None = None):
        super().__init__(payload)
        self.status = status
        self.headers = headers or {}

    def getheader(self, name: str):
        return self.headers.get(name)


class FakeConnection:
    def __init__(self, host: str, response: FakeResponse):
        self.host = host
        self.response = response
        self.requests = []
        self.closed = False

    def request(self, method: str, path: str, *, headers: dict):
        self.requests.append((method, path, headers))

    def getresponse(self):
        return self.response

    def close(self):
        self.closed = True


class ZipScreenTests(unittest.TestCase):
    def test_acquisition_receipts_are_append_only_and_do_not_expose_url(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            submission, reply = synthetic_job_reply(b"synthetic")
            submission["job_id"] = EXACT_JOB_ID
            filename = reply["files"][0]["filename"]
            private = {
                "source_id": ORDER[0], "job_id": EXACT_JOB_ID,
                "filename": filename, "size_bytes": 9,
                "url": f"https://hyp3-contentbucket-example.s3.us-west-2.amazonaws.com/{EXACT_JOB_ID}/{filename}",
            }
            public = {"source_id": ORDER[0], "job_id": EXACT_JOB_ID,
                      "status": "pass_exact_zip_descriptor_transfer_not_started"}
            attempt = root / "attempts" / "attempt-001"
            product_dir = root / "products"
            def fake_transfer(bound_private, bound_submission, bound_root, stage, final):
                self.assertEqual(bound_private, private)
                self.assertEqual(bound_submission, submission)
                self.assertEqual(bound_root, root)
                self.assertEqual(stage.parent, attempt)
                self.assertEqual(final.parent, product_dir)
                return {
                    "source_id": ORDER[0], "status": "pass_local_zip_promoted_no_replace",
                    "job_id": EXACT_JOB_ID, "product_filename": filename,
                    "archive_size_bytes": 9, "archive_sha256": "1" * 64,
                    "pixel_qa_pass": False,
                }
            terminal = acquire_first_once(
                "synthetic-token", submission, attempt, product_dir,
                controlled_root=root,
                fetch_descriptor=lambda token, record: (private, public),
                transfer_zip=fake_transfer,
            )
            self.assertEqual(terminal["status"], "pass_local_zip_promoted_no_replace")
            self.assertFalse(terminal["geotiff_headers_or_pixels_read"])
            self.assertNotIn(private["url"], (attempt / "terminal.json").read_text())
            self.assertNotIn(private["url"], (attempt / "descriptor.json").read_text())
            with self.assertRaisesRegex(RouteStop, "rtc_acquire_attempt_or_job_invalid"):
                acquire_first_once("synthetic-token", submission, attempt, product_dir,
                                   controlled_root=root)

    def test_acquisition_status_failure_is_terminal_without_zip_get(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            submission, _ = synthetic_job_reply(b"synthetic")
            submission["job_id"] = EXACT_JOB_ID
            attempt = root / "attempts" / "attempt-001"
            def fail_status(token, record):
                raise RouteStop("rtc_download_job_not_succeeded")
            terminal = acquire_first_once(
                "synthetic-token", submission, attempt, root / "products",
                controlled_root=root, fetch_descriptor=fail_status,
                transfer_zip=lambda *args: self.fail("ZIP GET must not occur"),
            )
            self.assertEqual(terminal["code"], "rtc_download_job_not_succeeded")
            self.assertTrue((attempt / "started.json").is_file())
            self.assertTrue((attempt / "terminal.json").is_file())
            self.assertFalse((root / "products").exists())

    def test_http_status_descriptor_and_exact_zip_transfer(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "synthetic.zip"
            make_zip(source, ORDER[0])
            payload = source.read_bytes()
            submission, reply = synthetic_job_reply(payload)
            status_connection = FakeConnection("hyp3-api.asf.alaska.edu", FakeResponse(json.dumps(reply).encode()))
            private, public = fetch_first_descriptor_once(
                "synthetic-token", submission,
                connection_factory=lambda host, timeout: status_connection,
            )
            self.assertTrue(status_connection.closed)
            self.assertEqual(status_connection.requests[0][0], "GET")
            self.assertEqual(public["status"], "pass_exact_zip_descriptor_transfer_not_started")
            self.assertNotIn(private["url"], json.dumps(public))
            attempt = root / "attempt"
            products = root / "products"
            attempt.mkdir()
            products.mkdir()
            stage = attempt / "product.part"
            final = products / private["filename"]
            zip_connection = FakeConnection(
                "hyp3-contentbucket-example.s3.us-west-2.amazonaws.com",
                FakeResponse(payload, headers={"Content-Length": str(len(payload))}),
            )
            with patch("m2_asf_hyp3_rtc_http_transfer_001.shutil.disk_usage",
                       return_value=SimpleNamespace(free=len(payload) + 2 * 1024**3)):
                result = transfer_first_zip_once(
                    private, submission, root, stage, final,
                    connection_factory=lambda host, timeout: zip_connection,
                )
            self.assertTrue(zip_connection.closed)
            self.assertEqual(zip_connection.requests[0][0], "GET")
            self.assertEqual(zip_connection.requests[0][2], {"Accept": "application/zip"})
            self.assertEqual(result["archive_sha256"], hashlib.sha256(payload).hexdigest())
            self.assertTrue(final.is_file())
            self.assertFalse(stage.exists())
            self.assertFalse(result["pixel_qa_pass"])

    def test_http_transfer_stops_on_headers_and_existing_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "synthetic.zip"
            make_zip(source, ORDER[0])
            payload = source.read_bytes()
            submission, reply = synthetic_job_reply(payload)
            private = {"source_id": ORDER[0], "job_id": submission["job_id"],
                       "filename": reply["files"][0]["filename"],
                       "size_bytes": len(payload), "url": reply["files"][0]["url"]}
            attempt = root / "attempt"
            products = root / "products"
            attempt.mkdir()
            products.mkdir()
            stage = attempt / "product.part"
            final = products / private["filename"]
            connection = FakeConnection("host", FakeResponse(payload, headers={"Content-Length": "1"}))
            with patch("m2_asf_hyp3_rtc_http_transfer_001.shutil.disk_usage",
                       return_value=SimpleNamespace(free=len(payload) + 2 * 1024**3)):
                with self.assertRaisesRegex(RouteStop, "rtc_acquire_zip_headers_invalid"):
                    transfer_first_zip_once(private, submission, root, stage, final,
                                            connection_factory=lambda host, timeout: connection)
            self.assertFalse(stage.exists())
            self.assertFalse(final.exists())
            final.write_bytes(b"existing")
            with self.assertRaisesRegex(RouteStop, "rtc_acquire_custody_preflight_failed"):
                transfer_first_zip_once(private, submission, root, stage, final,
                                        connection_factory=lambda host, timeout: connection)
            self.assertEqual(final.read_bytes(), b"existing")

    def test_exact_synthetic_archive_passes_only_local_container_checks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "product.zip"
            make_zip(path, ORDER[0])
            result = inspect_package_zip(ORDER[0], path, **binding(path))
            self.assertEqual(result["status"], "pass_local_zip_identity_structure_crc_only")
            self.assertTrue(result["zip_crc_verified"])
            self.assertFalse(result["provider_transfer_or_job_identity_verified"])
            self.assertFalse(result["geotiff_headers_or_pixels_read"])

    def test_wrong_transfer_identity_and_source_stop(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "product.zip"
            make_zip(path, ORDER[0])
            with self.assertRaisesRegex(RouteStop, "rtc_zip_size_mismatch"):
                inspect_package_zip(ORDER[0], path, expected_size_bytes=path.stat().st_size + 1, expected_sha256=binding(path)["expected_sha256"])
            with self.assertRaisesRegex(RouteStop, "rtc_zip_sha256_mismatch"):
                inspect_package_zip(ORDER[0], path, expected_size_bytes=path.stat().st_size, expected_sha256="0" * 64)
            with self.assertRaisesRegex(RouteStop, "rtc_package_product_identity_mismatch"):
                inspect_package_zip(ORDER[1], path, **binding(path))

    def test_unsafe_member_and_corrupt_crc_stop(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "unsafe.zip"
            make_zip(path, ORDER[0], traversal=True)
            with self.assertRaisesRegex(RouteStop, "rtc_package_path_invalid"):
                inspect_package_zip(ORDER[0], path, **binding(path))
            make_zip(path, ORDER[0])
            data = bytearray(path.read_bytes())
            marker = data.index(b"synthetic")
            data[marker] ^= 1
            path.write_bytes(data)
            with self.assertRaisesRegex(RouteStop, "rtc_zip_crc_failed"):
                inspect_package_zip(ORDER[0], path, **binding(path))

    def test_symlink_path_stops_without_read(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "product.zip"
            link = Path(temp) / "linked.zip"
            make_zip(path, ORDER[0])
            try:
                link.symlink_to(path)
            except OSError:
                self.skipTest("symlink creation unavailable")
            with self.assertRaisesRegex(RouteStop, "rtc_zip_path_invalid"):
                inspect_package_zip(ORDER[0], link, **binding(path))

    def test_empty_required_and_special_member_stop(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "product.zip"
            make_zip(path, ORDER[0], empty_suffix="_VV.tif")
            with self.assertRaisesRegex(RouteStop, "rtc_zip_required_member_empty"):
                inspect_package_zip(ORDER[0], path, **binding(path))
            make_zip(path, ORDER[0], special_suffix="_VH.tif")
            with self.assertRaisesRegex(RouteStop, "rtc_zip_special_member"):
                inspect_package_zip(ORDER[0], path, **binding(path))

    def test_stream_and_no_replace_promotion_preserve_exact_zip(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            source = directory / "source.zip"
            stage = directory / "staged.part"
            final = directory / "product.zip"
            make_zip(source, ORDER[0])
            expected = source.read_bytes()
            staged = stream_exact_zip_once(
                BytesIO(expected), stage, source_id=ORDER[0],
                expected_size_bytes=len(expected), chunk_bytes=17,
            )
            self.assertEqual(staged["status"], "pass_staged_bytes_and_zip_only")
            self.assertFalse(staged["raster_pixel_values_decoded"])
            promoted = promote_verified_zip_no_replace(stage, final, staged)
            self.assertEqual(promoted["archive_sha256"], hashlib.sha256(expected).hexdigest())
            self.assertEqual(final.read_bytes(), expected)
            self.assertFalse(stage.exists())
            with self.assertRaisesRegex(RouteStop, "rtc_transfer_promotion_binding_invalid"):
                promote_verified_zip_no_replace(stage, final, {**staged, "zip_crc_verified": False})

    def test_failed_stream_or_container_is_retained_without_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            source = directory / "source.zip"
            make_zip(source, ORDER[0])
            good = source.read_bytes()
            for label, payload, expected_size, code in (
                ("short", good[:-1], len(good), "rtc_transfer_size_mismatch"),
                ("long", good + b"x", len(good), "rtc_transfer_exceeds_descriptor_size"),
                ("corrupt", b"x" * len(good), len(good), "rtc_zip_unreadable"),
            ):
                stage = directory / f"{label}.part"
                with self.assertRaisesRegex(RouteStop, code):
                    stream_exact_zip_once(BytesIO(payload), stage, source_id=ORDER[0],
                                          expected_size_bytes=expected_size, chunk_bytes=19)
                self.assertTrue(stage.exists())
                self.assertFalse((directory / f"{label}.zip").exists())

    def test_provider_stream_exception_is_sanitized_and_partial_retained(self) -> None:
        class FailedProviderStream:
            def read(self, _count: int) -> bytes:
                raise RuntimeError("private-provider-url")

        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            stage = directory / "failed.part"
            with self.assertRaisesRegex(RouteStop, "^rtc_transfer_stream_failed$"):
                stream_exact_zip_once(
                    FailedProviderStream(), stage, source_id=ORDER[0],
                    expected_size_bytes=10,
                )
            self.assertEqual(stage.read_bytes(), b"")
            self.assertFalse((directory / "product.zip").exists())

    def test_stage_and_destination_collisions_stop_without_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            source = directory / "source.zip"
            make_zip(source, ORDER[0])
            good = source.read_bytes()
            stage = directory / "stage.part"
            stage.write_bytes(b"old")
            with self.assertRaisesRegex(RouteStop, "rtc_transfer_staging_collision"):
                stream_exact_zip_once(BytesIO(good), stage, source_id=ORDER[0],
                                      expected_size_bytes=len(good))
            self.assertEqual(stage.read_bytes(), b"old")
            stage.unlink()
            staged = stream_exact_zip_once(BytesIO(good), stage, source_id=ORDER[0],
                                           expected_size_bytes=len(good))
            final = directory / "product.zip"
            final.write_bytes(b"existing")
            with self.assertRaisesRegex(RouteStop, "rtc_transfer_promotion_failed"):
                promote_verified_zip_no_replace(stage, final, staged)
            self.assertEqual(final.read_bytes(), b"existing")
            self.assertTrue(stage.exists())


if __name__ == "__main__":
    unittest.main()
