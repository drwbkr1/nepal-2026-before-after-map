"""No-network guards for the approved ASF HyP3 job shape and responses."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from m2_asf_hyp3_rtc_core_001 import (  # noqa: E402
    ORDER,
    RouteStop,
    check_free_credits,
    inspect_submission,
    load_approved_jobs,
    one_job_payload,
)


class ApprovedJobTests(unittest.TestCase):
    def test_exact_publicly_reviewed_candidate(self) -> None:
        jobs = load_approved_jobs()
        self.assertEqual(tuple(job["source_id"] for job in jobs), ORDER)
        for job in jobs:
            payload = one_job_payload(jobs, job["source_id"])
            self.assertEqual(len(payload["jobs"]), 1)
            self.assertEqual(payload["jobs"][0]["job_parameters"]["scale"], "power")
            self.assertFalse(payload["validate_only"])

    def test_reordered_source_cannot_be_built(self) -> None:
        jobs = load_approved_jobs()
        with self.assertRaises(RouteStop):
            one_job_payload(tuple(reversed(jobs)), ORDER[0])


class CreditTests(unittest.TestCase):
    def test_exact_free_credit_capacity(self) -> None:
        self.assertEqual(check_free_credits({"application_status": "APPROVED", "remaining_credits": 240}, required_jobs=4), 240)
        for value in (239, None, True, float("nan")):
            with self.subTest(value=value), self.assertRaises(RouteStop):
                check_free_credits({"application_status": "APPROVED", "remaining_credits": value}, required_jobs=4)
        self.assertEqual(check_free_credits({"application_status": "NOT_STARTED", "remaining_credits": 240}), 240)


class SubmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.expected = one_job_payload(load_approved_jobs(), ORDER[0])["jobs"][0]
        self.actual = copy.deepcopy(self.expected)
        self.actual.update({
            "job_id": "27836b79-e5b2-4d8f-932f-659724ea02c3",
            "user_id": "synthetic-private-user",
            "status_code": "PENDING",
            "request_time": "2026-09-26T20:00:00+00:00",
            "credit_cost": 60,
        })

    def test_success_receipt_omits_user_id(self) -> None:
        receipt = inspect_submission({"validate_only": False, "jobs": [self.actual]}, self.expected)
        self.assertEqual(receipt["credit_cost"], 60)
        self.assertNotIn("user_id", receipt)

    def test_ambiguous_and_overpriced_responses_stop(self) -> None:
        cases = [
            {"validate_only": True, "jobs": [self.actual]},
            {"validate_only": False, "jobs": [self.actual, self.actual]},
            {"validate_only": False, "jobs": [{**self.actual, "credit_cost": 61}]},
            {"validate_only": False, "jobs": [{**self.actual, "status_code": "FAILED"}]},
            {"validate_only": False, "jobs": [{**self.actual, "name": "unexpected"}]},
        ]
        for reply in cases:
            with self.subTest(reply=reply.get("validate_only")), self.assertRaises(RouteStop):
                inspect_submission(reply, self.expected)


if __name__ == "__main__":
    unittest.main()
