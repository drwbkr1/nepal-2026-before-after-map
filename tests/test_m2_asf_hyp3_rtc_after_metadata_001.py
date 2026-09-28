"""Disposable after-product metadata capture; no real ZIP or pixels."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m2_asf_hyp3_rtc_after_metadata_001 import (  # noqa: E402
    ACQUISITION_REF, APPROVAL_REF, APPROVAL_SHA, GATE_REF,
    IMPLEMENTATION_FILES, PREFLIGHT_REF, SUBMISSION_REF,
    SUFFIX_LIMITS, capture_once, require_release,
)
from m2_asf_hyp3_rtc_core_001 import RouteStop  # noqa: E402
from m2_asf_hyp3_rtc_package_core_001 import REQUIRED_SUFFIXES  # noqa: E402


SOURCE_ID = "M1-SRC-005"
JOB_ID = "27836b79-e5b2-4d8f-932f-659724ea02c3"
BASE = "S1D_IW_20260828T122141_DVP_RTC10_G_gpuned_ABCD"


def make_zip(path: Path, *, missing: str | None = None) -> None:
    with ZipFile(path, "w", ZIP_STORED) as archive:
        archive.writestr(BASE + "/", b"")
        for suffix in REQUIRED_SUFFIXES:
            if suffix == missing:
                continue
            payload = b"generated metadata for local test" if suffix in SUFFIX_LIMITS else b"generated raster placeholder"
            archive.writestr(f"{BASE}/{BASE}{suffix}", payload)


def submission() -> dict:
    return {"status": "submitted_product_unverified", "source_id": SOURCE_ID,
            "job_id": JOB_ID, "credit_cost": 60,
            "credentials_recorded": False, "product_bytes_verified": False,
            "pixel_qa_pass": False}


def acquisition(path: Path) -> dict:
    return {"status": "pass_local_zip_promoted_no_replace",
            "source_id": SOURCE_ID, "job_id": JOB_ID,
            "product_filename": path.name,
            "archive_size_bytes": path.stat().st_size,
            "archive_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "archive_integrity_verified": True,
            "geotiff_headers_or_pixels_read": False,
            "credentials_recorded": False}


class AfterMetadataTests(unittest.TestCase):
    def test_unreleased_stops_before_archive_read(self):
        with tempfile.TemporaryDirectory() as temp, self.assertRaisesRegex(RouteStop, "after_metadata_required_path_invalid"):
            base = Path(temp)
            require_release(base / "repo", base / "custody",
                            base / "custody" / "after-metadata" / "attempt")

    def test_complete_synthetic_release_then_code_drift_blocks(self):
        def write(path: Path, value: dict):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value), encoding="utf-8")

        def sha(path: Path) -> str:
            return hashlib.sha256(path.read_bytes()).hexdigest()

        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            repo, data = base / "repo", base / "custody"
            repo.mkdir()
            data.mkdir()
            for ref in (*IMPLEMENTATION_FILES, APPROVAL_REF):
                target = repo / ref
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / ref, target)
            self.assertEqual(sha(repo / APPROVAL_REF), APPROVAL_SHA)
            archive = data / "m2-asf-hyp3-rtc-products-after-partial-001" / f"{BASE}.zip"
            archive.parent.mkdir()
            make_zip(archive)
            write(data / SUBMISSION_REF, submission())
            write(data / ACQUISITION_REF, acquisition(archive))
            write(repo / GATE_REF, {
                "status": "pass_after_metadata_implementation_public_ci_only",
                "bindings": {"approval_sha256": APPROVAL_SHA,
                             "submission_terminal_sha256": sha(data / SUBMISSION_REF),
                             "acquisition_terminal_sha256": sha(data / ACQUISITION_REF),
                             "implementation_file_sha256": {
                                 ref: sha(repo / ref) for ref in IMPLEMENTATION_FILES}},
                "public_ci": {"conclusion": "success"},
            })
            write(repo / PREFLIGHT_REF, {
                "status": "pass_after_metadata_no_content",
                "bindings": {"implementation_gate_sha256": sha(repo / GATE_REF),
                             "acquisition_terminal_sha256": sha(data / ACQUISITION_REF)},
                "assertions": {"attempt_absent": True,
                               "no_product_member_or_pixel_read": True},
            })
            attempt = data / "m2-asf-hyp3-rtc-after-metadata-001" / "attempt-001"
            released = require_release(repo, data, attempt)
            self.assertEqual(released[2], archive)
            (repo / IMPLEMENTATION_FILES[0]).write_text("drift", encoding="utf-8")
            with self.assertRaisesRegex(RouteStop, "after_metadata_not_released"):
                require_release(repo, data, attempt)

    def test_exact_eight_members_captured_outside_git(self):
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)
            archive = data / f"{BASE}.zip"
            make_zip(archive)
            attempt = data / "after-metadata" / "attempt"
            result = capture_once(submission(), acquisition(archive), archive,
                                  attempt, controlled_root=data)
            self.assertEqual(result["status"], "pass_bounded_after_metadata_captured_for_local_review_only")
            self.assertEqual(len(result["captured"]), 8)
            self.assertTrue((attempt / "readme.txt").is_file())
            self.assertTrue((attempt / "processing.log").is_file())
            self.assertFalse(any(path.suffix.lower() == ".tif" for path in attempt.iterdir()))
            self.assertFalse(result["raster_header_or_pixel_read"])
            self.assertFalse(result["rights_and_attribution_reviewed"])
            with self.assertRaisesRegex(RouteStop, "after_metadata_attempt_collision"):
                capture_once(submission(), acquisition(archive), archive,
                             attempt, controlled_root=data)

    def test_missing_member_is_terminal_and_not_retried(self):
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)
            archive = data / f"{BASE}.zip"
            make_zip(archive, missing="_VH.tif.xml")
            attempt = data / "after-metadata" / "attempt"
            result = capture_once(submission(), acquisition(archive), archive,
                                  attempt, controlled_root=data)
            self.assertEqual(result["status"], "stopped_after_metadata_no_automatic_retry")
            self.assertEqual(result["code"], "rtc_package_required_member_missing")
            self.assertTrue((attempt / "terminal.json").exists())

    def test_archive_hash_drift_stops_before_member_capture(self):
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)
            archive = data / f"{BASE}.zip"
            make_zip(archive)
            record = acquisition(archive)
            record["archive_sha256"] = "0" * 64
            attempt = data / "after-metadata" / "attempt"
            result = capture_once(submission(), record, archive, attempt,
                                  controlled_root=data)
            self.assertEqual(result["status"], "stopped_after_metadata_no_automatic_retry")
            self.assertEqual(result["code"], "after_metadata_archive_identity_mismatch")
            self.assertFalse((attempt / "readme.txt").exists())
            terminal = json.loads((attempt / "terminal.json").read_text())
            self.assertFalse(terminal["raster_header_or_pixel_read"])


if __name__ == "__main__":
    unittest.main()
