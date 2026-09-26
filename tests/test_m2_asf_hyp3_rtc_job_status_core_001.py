"""Synthetic HyP3 status-response tests; no provider access."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from m2_asf_hyp3_rtc_core_001 import ORDER, RouteStop, load_approved_jobs, one_job_payload  # noqa: E402
from m2_asf_hyp3_rtc_job_status_core_001 import inspect_exact_job_status  # noqa: E402


class StatusTests(unittest.TestCase):
    def setUp(self) -> None:
        expected = one_job_payload(load_approved_jobs(), ORDER[0])["jobs"][0]
        self.submission = {
            **copy.deepcopy(expected),
            "job_id": "27836b79-e5b2-4d8f-932f-659724ea02c3",
            "credit_cost": 60,
        }
        self.reply = {
            **copy.deepcopy(self.submission),
            "user_id": "synthetic-private-user",
            "status_code": "PENDING",
            "execution_started": False,
            "files": [],
            "logs": [{"url": "https://example.invalid/private-log"}],
        }

    def test_nonterminal_keeps_same_job_without_product_claim(self) -> None:
        for status in ("PENDING", "RUNNING"):
            with self.subTest(status=status):
                result = inspect_exact_job_status({**self.reply, "status_code": status}, self.submission, ORDER[0])
                self.assertEqual(result["disposition"], "service_not_terminal_observe_same_job")
                self.assertFalse(result["product_bytes_verified"])
                self.assertNotIn("synthetic-private-user", str(result))
                self.assertNotIn("private-log", str(result))

    def test_failed_job_is_terminal_without_retry(self) -> None:
        result = inspect_exact_job_status({**self.reply, "status_code": "FAILED"}, self.submission, ORDER[0])
        self.assertEqual(result["disposition"], "service_failed_terminal_no_retry")
        self.assertEqual(result["reported_file_count"], 0)

    def test_success_requires_descriptor_and_still_is_not_product_qa(self) -> None:
        reply = {**self.reply, "status_code": "SUCCEEDED", "files": [{
            "filename": "synthetic.zip", "size": 1024,
            "url": "https://synthetic.cloudfront.net/product.zip",
        }]}
        result = inspect_exact_job_status(reply, self.submission, ORDER[0])
        self.assertEqual(result["disposition"], "service_succeeded_product_unverified")
        self.assertEqual(result["reported_file_count"], 1)
        self.assertNotIn("cloudfront", str(result))
        self.assertFalse(result["pixel_qa_pass"])

    def test_identity_cost_and_descriptor_ambiguity_stop(self) -> None:
        cases = [
            {**self.reply, "job_id": "other"},
            {**self.reply, "credit_cost": 61},
            {**self.reply, "status_code": "UNKNOWN"},
            {**self.reply, "files": [{"filename": "early.zip", "size": 1, "url": "https://x.test"}]},
            {**self.reply, "status_code": "SUCCEEDED", "files": []},
            {**self.reply, "status_code": "SUCCEEDED", "files": [{"filename": "x.zip", "size": 0, "url": "https://x.test"}]},
        ]
        for case in cases:
            with self.subTest(status=case.get("status_code")), self.assertRaises(RouteStop):
                inspect_exact_job_status(case, self.submission, ORDER[0])


if __name__ == "__main__":
    unittest.main()
