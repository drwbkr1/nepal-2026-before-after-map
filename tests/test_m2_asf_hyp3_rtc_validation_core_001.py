"""No-network exact-job validation and sanitized receipt tests."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from m2_asf_hyp3_rtc_core_001 import ORDER, RouteStop, load_approved_jobs  # noqa: E402
from m2_asf_hyp3_rtc_validation_core_001 import (  # noqa: E402
    VALIDATION_PASS,
    inspect_validation,
    next_validation_source,
    one_validation_payload,
)


class ValidationCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.jobs = load_approved_jobs()
        self.payload = one_validation_payload(self.jobs, ORDER[0])
        self.expected = self.payload["jobs"][0]
        self.actual = copy.deepcopy(self.expected)
        self.actual.update({
            "job_id": "27836b79-e5b2-4d8f-932f-659724ea02c3",
            "user_id": "synthetic-private-user",
            "status_code": "PENDING",
            "execution_started": False,
            "files": [],
            "credit_cost": 60,
        })

    def test_all_four_payloads_are_single_source_and_validate_only(self) -> None:
        for source_id in ORDER:
            with self.subTest(source_id=source_id):
                payload = one_validation_payload(self.jobs, source_id)
                self.assertIs(payload["validate_only"], True)
                self.assertEqual(len(payload["jobs"]), 1)
                self.assertEqual(payload["jobs"][0]["job_type"], "RTC_GAMMA")
        self.assertFalse("validate_only" in self.jobs[0])
        altered = copy.deepcopy(self.jobs)
        altered[0]["job_parameters"]["resolution"] = 20.0
        with self.assertRaisesRegex(RouteStop, "validation_candidate_identity_mismatch"):
            one_validation_payload(altered, ORDER[0])

    def test_exact_response_emits_no_account_or_job_identity(self) -> None:
        result = inspect_validation({"validate_only": True, "jobs": [self.actual]}, self.expected, ORDER[0])
        rendered = json.dumps(result)
        self.assertEqual(result["status"], VALIDATION_PASS)
        self.assertFalse(result["job_submission_requested"])
        self.assertNotIn("synthetic-private-user", rendered)
        self.assertNotIn(self.actual["job_id"], rendered)
        self.assertNotIn("job_parameters", result)

    def test_wrong_mode_identity_cost_or_execution_state_stops(self) -> None:
        mutations = [
            {"validate_only": False, "jobs": [self.actual]},
            {"validate_only": True, "jobs": [self.actual, self.actual]},
            {"validate_only": True, "jobs": [{**self.actual, "name": "changed"}]},
            {"validate_only": True, "jobs": [{**self.actual, "credit_cost": 61}]},
            {"validate_only": True, "jobs": [{**self.actual, "credit_cost": True}]},
            {"validate_only": True, "jobs": [{**self.actual, "execution_started": True}]},
            {"validate_only": True, "jobs": [{**self.actual, "status_code": "SUCCEEDED"}]},
            {"validate_only": True, "jobs": [{**self.actual, "files": [{"url": "synthetic"}]}]},
        ]
        for index, reply in enumerate(mutations):
            with self.subTest(index=index), self.assertRaises(RouteStop):
                inspect_validation(reply, self.expected, ORDER[0])
        altered_expected = copy.deepcopy(self.expected)
        altered_expected["job_parameters"]["resolution"] = 20.0
        with self.assertRaisesRegex(RouteStop, "validation_candidate_identity_mismatch"):
            inspect_validation({"validate_only": True, "jobs": [self.actual]}, altered_expected, ORDER[0])

    def test_only_passing_fixed_order_prefix_can_advance(self) -> None:
        receipts = []
        for source_id in ORDER:
            self.assertEqual(next_validation_source(receipts), source_id)
            receipts.append({"source_id": source_id, "status": VALIDATION_PASS, "job_submission_requested": False})
        self.assertIsNone(next_validation_source(receipts))
        for bad in ([receipts[1]], [receipts[0], receipts[0]], [{**receipts[0], "status": "stopped"}]):
            with self.subTest(bad=bad), self.assertRaises(RouteStop):
                next_validation_source(bad)


if __name__ == "__main__":
    unittest.main()
