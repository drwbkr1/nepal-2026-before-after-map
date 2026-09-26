"""No-network ZIP descriptor screening for exact first HyP3 RTC job."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from m2_asf_hyp3_rtc_core_001 import ORDER, RouteStop, load_approved_jobs, one_job_payload  # noqa: E402
from m2_asf_hyp3_rtc_download_core_001 import inspect_exact_zip_descriptor  # noqa: E402


JOB_ID = "27836b79-e5b2-4d8f-932f-659724ea02c3"


def fixture() -> tuple[dict, dict, str]:
    expected = one_job_payload(load_approved_jobs(), ORDER[0])["jobs"][0]
    submitted = {**copy.deepcopy(expected), "job_id": JOB_ID, "credit_cost": 60}
    start = expected["job_parameters"]["granules"][0].split("_")[4]
    filename = f"S1D_IW_{start}_DVP_RTC10_G_gpuned_ABCD.zip"
    url = f"https://hyp3-contentbucket-fo259f6r6dn6.s3.us-west-2.amazonaws.com/{JOB_ID}/{filename}"
    reply = {**copy.deepcopy(submitted), "status_code": "SUCCEEDED",
             "user_id": "private-synthetic-user",
             "files": [{"filename": filename, "size": 1000, "url": url}],
             "logs": ["https://example.invalid/private-log"]}
    return submitted, reply, url


class ExactDownloadDescriptorTests(unittest.TestCase):
    def test_exact_s3_descriptor_passes_without_public_url(self) -> None:
        submitted, reply, url = fixture()
        private, public = inspect_exact_zip_descriptor(reply, submitted, ORDER[0])
        self.assertEqual(private["url"], url)
        self.assertEqual(private["size_bytes"], 1000)
        self.assertEqual(public["status"], "pass_exact_zip_descriptor_transfer_not_started")
        self.assertEqual(public["provider_url_sha256"], hashlib.sha256(url.encode()).hexdigest())
        self.assertNotIn(url, json.dumps(public))
        self.assertNotIn("private-synthetic-user", json.dumps(public))
        self.assertNotIn("private-log", json.dumps(public))
        self.assertFalse(public["archive_bytes_acquired"])

    def test_exact_cloudfront_shape_passes(self) -> None:
        submitted, reply, _ = fixture()
        filename = reply["files"][0]["filename"]
        reply["files"][0]["url"] = f"https://d12abc.cloudfront.net/{JOB_ID}/{filename}"
        _, public = inspect_exact_zip_descriptor(reply, submitted, ORDER[0])
        self.assertEqual(public["expected_size_bytes"], 1000)

    def test_identity_and_status_fail_closed(self) -> None:
        submitted, reply, _ = fixture()
        cases = [
            ({**reply, "status_code": "PENDING", "files": []}, ORDER[0]),
            ({**reply, "job_id": "17edbff3-35fb-48e1-aa5d-683872c1a161"}, ORDER[0]),
            (reply, ORDER[1]),
        ]
        for altered, source_id in cases:
            with self.subTest(source_id=source_id), self.assertRaises(RouteStop):
                inspect_exact_zip_descriptor(altered, submitted, source_id)

    def test_url_and_product_substitution_fail_closed(self) -> None:
        submitted, reply, url = fixture()
        filename = reply["files"][0]["filename"]
        bad_urls = [
            url.replace("https://", "http://"),
            url.replace("hyp3-contentbucket-fo259f6r6dn6.s3.us-west-2.amazonaws.com", "example.invalid"),
            url.replace(JOB_ID, "17edbff3-35fb-48e1-aa5d-683872c1a161"),
            url + "?token=private-synthetic-token",
            url.replace("https://", "https://private@"),
            "https://[bad-host:443/unsafe.zip",
        ]
        for bad in bad_urls:
            altered = copy.deepcopy(reply)
            altered["files"][0]["url"] = bad
            with self.subTest(url=bad), self.assertRaises(RouteStop):
                inspect_exact_zip_descriptor(altered, submitted, ORDER[0])
        altered = copy.deepcopy(reply)
        altered["files"][0]["filename"] = filename.replace("ABCD", "../x")
        with self.assertRaises(RouteStop):
            inspect_exact_zip_descriptor(altered, submitted, ORDER[0])

    def test_ambiguous_or_oversize_descriptor_stops(self) -> None:
        submitted, reply, _ = fixture()
        double = copy.deepcopy(reply)
        double["files"].append(copy.deepcopy(double["files"][0]))
        with self.assertRaisesRegex(RouteStop, "rtc_download_file_count_invalid"):
            inspect_exact_zip_descriptor(double, submitted, ORDER[0])
        oversized = copy.deepcopy(reply)
        oversized["files"][0]["size"] = 101 * 1024**3
        with self.assertRaisesRegex(RouteStop, "rtc_download_size_invalid"):
            inspect_exact_zip_descriptor(oversized, submitted, ORDER[0])


if __name__ == "__main__":
    unittest.main()
