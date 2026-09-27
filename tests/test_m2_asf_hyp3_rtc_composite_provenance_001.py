"""Disposable, receipt-only tests for the approved composite identity amendment."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from m2_asf_hyp3_rtc_composite_provenance_core_001 import (  # noqa: E402
    ARCHIVE_SHA256, ARCHIVE_SIZE, JOB_ID, PRODUCT_FILENAME, README_SHA256,
    SOURCE_ID, evaluate_composite,
)
from m2_asf_hyp3_rtc_composite_provenance_001 import evaluate_once  # noqa: E402
from m2_asf_hyp3_rtc_core_001 import RouteStop, load_approved_jobs  # noqa: E402


def evidence() -> tuple[dict, dict]:
    approved = load_approved_jobs()[0]
    submission = {
        "status": "submitted_product_unverified", "source_id": SOURCE_ID,
        "job_id": JOB_ID, "job_type": approved["job_type"],
        "job_parameters": copy.deepcopy(approved["job_parameters"]),
        "name": approved["name"], "credentials_recorded": False,
    }
    descriptor = {
        "status": "pass_exact_zip_descriptor_transfer_not_started",
        "source_id": SOURCE_ID, "job_id": JOB_ID,
        "product_filename": PRODUCT_FILENAME, "expected_size_bytes": ARCHIVE_SIZE,
        "provider_url_recorded_publicly": False,
    }
    acquisition = {
        "status": "pass_local_zip_promoted_no_replace",
        "source_id": SOURCE_ID, "job_id": JOB_ID,
        "product_filename": PRODUCT_FILENAME, "archive_size_bytes": ARCHIVE_SIZE,
        "archive_sha256": ARCHIVE_SHA256, "archive_integrity_verified": True,
        "credentials_recorded": False, "geotiff_headers_or_pixels_read": False,
        "raster_pixel_values_decoded": False,
    }
    readme = {
        "status": "defer_readme_source_text_review", "source_id": SOURCE_ID,
        "job_id": JOB_ID, "product_filename": PRODUCT_FILENAME,
        "readme_sha256": README_SHA256, "readme_member_size_bytes": 16540,
        "archive_sha256_verified_current": True,
        "exact_source_granule_text_present": True,
        "exact_product_base_text_present": False,
        "archive_bytes_mutated": False, "raster_pixels_read": False,
    }
    return {"submission": submission, "descriptor": descriptor,
            "acquisition": acquisition, "readme": readme}, approved


class CompositeProvenanceTests(unittest.TestCase):
    def test_exact_deferred_readme_can_only_pass_composite_local_qa(self) -> None:
        receipts, approved = evidence()
        result = evaluate_composite(
            receipts["submission"], receipts["descriptor"],
            receipts["acquisition"], receipts["readme"], approved,
        )
        self.assertEqual(result["status"], "pass_composite_provenance_for_local_qa_only")
        self.assertEqual(result["old_readme_status_preserved"], "defer_readme_source_text_review")
        self.assertTrue(result["missing_readme_product_base_warning"])
        self.assertFalse(result["pixel_qa_pass"])
        self.assertFalse(result["arcgis_map_ready"])

    def test_conflicting_chain_or_missing_source_text_stops(self) -> None:
        for field, value in (
            ("job_id", "different-job"),
            ("expected_size_bytes", ARCHIVE_SIZE + 1),
            ("product_filename", "other.zip"),
        ):
            receipts, approved = evidence()
            receipts["descriptor"][field] = value
            with self.subTest(field=field), self.assertRaises(RouteStop):
                evaluate_composite(*receipts.values(), approved)
        receipts, approved = evidence()
        receipts["readme"]["exact_source_granule_text_present"] = False
        with self.assertRaises(RouteStop):
            evaluate_composite(*receipts.values(), approved)
        receipts, approved = evidence()
        receipts["acquisition"]["archive_integrity_verified"] = False
        with self.assertRaises(RouteStop):
            evaluate_composite(*receipts.values(), approved)

    def test_distinct_attempt_is_append_only_and_contains_no_input_text(self) -> None:
        receipts, _ = evidence()
        receipts["readme"]["untrusted_note"] = "SENSITIVE_TEST_MARKER"
        with tempfile.TemporaryDirectory() as temp:
            attempt = Path(temp) / "composite" / "attempt-001"
            result = evaluate_once(receipts, attempt)
            self.assertEqual(result["status"], "pass_composite_provenance_for_local_qa_only")
            started = (attempt / "started.json").read_text(encoding="utf-8")
            terminal = (attempt / "terminal.json").read_text(encoding="utf-8")
            self.assertNotIn("SENSITIVE_TEST_MARKER", started + terminal)
            self.assertFalse(json.loads(terminal)["raster_pixels_read"])
            with self.assertRaisesRegex(RouteStop, "rtc_composite_attempt_collision"):
                evaluate_once(receipts, attempt)

    def test_failure_receipt_is_durable_and_secret_safe(self) -> None:
        receipts, _ = evidence()
        receipts["descriptor"]["product_filename"] = "SENSITIVE_TEST_MARKER"
        with tempfile.TemporaryDirectory() as temp:
            attempt = Path(temp) / "composite" / "attempt-001"
            result = evaluate_once(receipts, attempt)
            self.assertEqual(result["status"], "stopped_receipt_only_no_automatic_retry")
            terminal = (attempt / "terminal.json").read_text(encoding="utf-8")
            self.assertNotIn("SENSITIVE_TEST_MARKER", terminal)
            self.assertFalse(json.loads(terminal)["raster_pixels_read"])


if __name__ == "__main__":
    unittest.main()
