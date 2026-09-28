"""No-network, exact after-job product descriptor tests."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m2_asf_hyp3_rtc_after_descriptor_core_001 import (  # noqa: E402
    SOURCE_ID, inspect_after_zip_descriptor, submission_view,
)
from m2_asf_hyp3_rtc_core_001 import RouteStop  # noqa: E402


JOB_ID = "27836b79-e5b2-4d8f-932f-659724ea02c3"
FILENAME = "S1D_IW_20260828T122141_DVP_RTC10_G_gpuned_944C.zip"
URL = f"https://abc.cloudfront.net/{JOB_ID}/{FILENAME}"


def terminal() -> dict:
    return {"status": "submitted_product_unverified", "source_id": SOURCE_ID,
            "job_id": JOB_ID, "credit_cost": 60, "credentials_recorded": False,
            "product_bytes_verified": False, "pixel_qa_pass": False}


def reply() -> dict:
    view = submission_view(terminal())
    return {**view, "status_code": "SUCCEEDED", "user_id": "private-synthetic-user",
            "files": [{"filename": FILENAME, "size": 1234, "url": URL}]}


class AfterDescriptorTests(unittest.TestCase):
    def test_exact_succeeded_job_one_safe_zip_and_no_public_secret(self):
        private, public = inspect_after_zip_descriptor(reply(), terminal())
        self.assertEqual(private["url"], URL)
        self.assertEqual(public["job_id"], JOB_ID)
        self.assertEqual(public["product_filename"], FILENAME)
        self.assertNotIn(URL, json.dumps(public))
        self.assertNotIn("private-synthetic-user", json.dumps(public))
        self.assertFalse(public["archive_integrity_verified"])

    def test_sanitized_terminal_identity_required(self):
        for key, value in (("status", "stopped"), ("source_id", "M1-SRC-002"),
                           ("job_id", "bad"), ("credit_cost", 61),
                           ("credentials_recorded", True), ("product_bytes_verified", True)):
            changed = terminal()
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(RouteStop):
                submission_view(changed)

    def test_pending_job_does_not_release_transfer(self):
        changed = reply()
        changed["status_code"] = "PENDING"
        changed["files"] = []
        with self.assertRaisesRegex(RouteStop, "after_job_not_succeeded"):
            inspect_after_zip_descriptor(changed, terminal())

    def test_provider_identity_and_cost_mismatch_stop(self):
        for key, value in (("name", "other"), ("credit_cost", 61), ("job_id", "bad")):
            changed = reply()
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(RouteStop):
                inspect_after_zip_descriptor(changed, terminal())

    def test_wrong_product_start_and_extra_files_stop(self):
        changed = reply()
        changed["files"][0]["filename"] = FILENAME.replace("20260828", "20260816")
        with self.assertRaisesRegex(RouteStop, "after_zip_product_identity_mismatch"):
            inspect_after_zip_descriptor(changed, terminal())
        changed = reply()
        changed["files"].append(copy.deepcopy(changed["files"][0]))
        with self.assertRaisesRegex(RouteStop, "after_zip_file_count_invalid"):
            inspect_after_zip_descriptor(changed, terminal())

    def test_unapproved_url_and_signed_query_stop(self):
        for url in (f"https://evil.example/{JOB_ID}/{FILENAME}", URL + "?token=secret",
                    URL.replace(JOB_ID, "00000000-0000-0000-0000-000000000000"),
                    URL.replace("https://", "http://")):
            changed = reply()
            changed["files"][0]["url"] = url
            with self.subTest(url=url), self.assertRaises(RouteStop):
                inspect_after_zip_descriptor(changed, terminal())


if __name__ == "__main__":
    unittest.main()
