"""Disposable state tests for the prospective HyP3 job order; no network."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from m2_asf_hyp3_rtc_core_001 import ORDER, RouteStop  # noqa: E402
from m2_asf_hyp3_rtc_sequence_core_001 import next_job_after_evidence  # noqa: E402


VALIDATION = {
    "status": "pass_all_four_validate_only_requests",
    "completed_sources": list(ORDER),
    "processing_job_submissions_requested": 0,
}
PAIR_QA = {
    "source_ids": list(ORDER[:2]),
    "status": "PASS_QA_ONLY",
    "product_identity_and_integrity_pass": True,
    "pixel_qa_pass": True,
}


def completed(source_id: str) -> dict:
    return {
        "source_id": source_id,
        "job_terminal_status": "SUCCEEDED",
        "submission_identity_verified": True,
    }


class FixedOrderTests(unittest.TestCase):
    def test_event_pair_then_context_only_after_pair_qa(self) -> None:
        self.assertEqual(next_job_after_evidence(VALIDATION, []), ORDER[0])
        self.assertEqual(next_job_after_evidence(VALIDATION, [completed(ORDER[0])]), ORDER[1])
        pair = [completed(source) for source in ORDER[:2]]
        with self.assertRaisesRegex(RouteStop, "submission_event_pair_qa_missing"):
            next_job_after_evidence(VALIDATION, pair)
        self.assertEqual(next_job_after_evidence(VALIDATION, pair, PAIR_QA), ORDER[2])
        self.assertEqual(next_job_after_evidence(VALIDATION, pair + [completed(ORDER[2])], PAIR_QA), ORDER[3])
        self.assertIsNone(next_job_after_evidence(VALIDATION, [completed(source) for source in ORDER], PAIR_QA))

    def test_missing_or_wrong_validation_never_selects_source(self) -> None:
        for bad in ({}, {**VALIDATION, "completed_sources": list(reversed(ORDER))},
                    {**VALIDATION, "processing_job_submissions_requested": 1}):
            with self.subTest(bad=bad), self.assertRaisesRegex(RouteStop, "submission_validation_evidence_missing"):
                next_job_after_evidence(bad, [])

    def test_failed_reordered_or_ambiguous_job_stops(self) -> None:
        cases = [
            [completed(ORDER[1])],
            [{**completed(ORDER[0]), "job_terminal_status": "FAILED"}],
            [{**completed(ORDER[0]), "submission_identity_verified": False}],
            [{**completed(ORDER[0]), "unexpected": "value"}],
            [completed(source) for source in ORDER] + [completed(ORDER[0])],
        ]
        for case in cases:
            with self.subTest(case=case), self.assertRaisesRegex(RouteStop, "submission_completed_order_invalid"):
                next_job_after_evidence(VALIDATION, case, PAIR_QA)

    def test_pair_qa_must_be_exact_and_passed(self) -> None:
        pair = [completed(source) for source in ORDER[:2]]
        cases = [
            {**PAIR_QA, "source_ids": list(reversed(ORDER[:2]))},
            {**PAIR_QA, "status": "BLOCK"},
            {**PAIR_QA, "pixel_qa_pass": False},
            {**PAIR_QA, "product_identity_and_integrity_pass": False},
            {**PAIR_QA, "extra": True},
        ]
        for case in cases:
            with self.subTest(case=case), self.assertRaisesRegex(RouteStop, "submission_event_pair_qa_missing"):
                next_job_after_evidence(VALIDATION, pair, case)


if __name__ == "__main__":
    unittest.main()
