"""Disposable release, one-attempt and stop semantics for after RTC pixels."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m2_asf_hyp3_rtc_after_pixel_001 import (  # noqa: E402
    ACQUISITION_REF, AOI_REF, AOI_SHA256, APPROVAL_REF, APPROVAL_SHA,
    CONTRACT_REF, CONTRACT_SHA256, GATE_REF, HEADER_REF,
    IMPLEMENTATION_FILES, METADATA_REVIEW_REF, PREFLIGHT_REF,
    SOURCE_GATE_REF, SOURCE_GATE_SHA, SUBMISSION_REF,
    inspect_once, require_release,
)
from m2_asf_hyp3_rtc_core_001 import RouteStop  # noqa: E402


SOURCE_ID = "M1-SRC-005"
JOB_ID = "27836b79-e5b2-4d8f-932f-659724ea02c3"
BASE = "S1D_IW_20260828T122141_DVP_RTC10_G_gpuned_ABCD"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def acquisition(path: Path) -> dict:
    return {"status": "pass_local_zip_promoted_no_replace",
            "source_id": SOURCE_ID, "job_id": JOB_ID,
            "product_filename": path.name,
            "archive_size_bytes": path.stat().st_size,
            "archive_sha256": sha(path),
            "archive_integrity_verified": True,
            "geotiff_headers_or_pixels_read": False}


def synthetic_scan(_archive, _header, _aois, _contract):
    return [{"aoi_id": aoi, "status": "defer",
             "aoi_area_m2": 100.0, "covered_area_m2": 100.0,
             "valid_area_m2": usable * 100.0,
             "coverage_fraction": 1.0,
             "usable_fraction_of_aoi": usable,
             "unknown_provider_mask_value_present": False}
            for aoi, usable in (("AOI-SOURCE", .55),
                                ("AOI-UPPER-CORRIDOR", .76))]


class AfterPixelTests(unittest.TestCase):
    def test_unreleased_stops_before_archive_open(self):
        with tempfile.TemporaryDirectory() as temp, self.assertRaisesRegex(
                RouteStop, "after_pixel_required_path_invalid"):
            base = Path(temp)
            require_release(base / "repo", base / "data",
                            base / "data" / "after-pixel" / "attempt")

    def test_complete_synthetic_release_and_code_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            repo, data = base / "repo", base / "data"
            repo.mkdir()
            data.mkdir()
            for ref in (*IMPLEMENTATION_FILES, APPROVAL_REF, SOURCE_GATE_REF,
                        AOI_REF, CONTRACT_REF):
                target = repo / ref
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / ref, target)
            self.assertEqual(sha(repo / APPROVAL_REF), APPROVAL_SHA)
            self.assertEqual(sha(repo / SOURCE_GATE_REF), SOURCE_GATE_SHA)
            self.assertEqual(sha(repo / AOI_REF), AOI_SHA256)
            self.assertEqual(sha(repo / CONTRACT_REF), CONTRACT_SHA256)
            archive = data / "m2-asf-hyp3-rtc-products-after-partial-001" / f"{BASE}.zip"
            archive.parent.mkdir()
            archive.write_bytes(b"disposable no-pixel archive")
            write(data / SUBMISSION_REF, {
                "status": "submitted_product_unverified", "source_id": SOURCE_ID,
                "job_id": JOB_ID, "credit_cost": 60,
                "credentials_recorded": False, "product_bytes_verified": False,
                "pixel_qa_pass": False})
            write(data / ACQUISITION_REF, acquisition(archive))
            write(data / HEADER_REF, {
                "status": "pass_after_headers_for_local_pixel_qa_only",
                "source_id": SOURCE_ID, "job_id": JOB_ID,
                "archive_sha256_verified_current": True, "pixels_read": False})
            write(repo / METADATA_REVIEW_REF, {
                "status": "pass_after_metadata_for_header_and_pixel_qa_only",
                "source_id": SOURCE_ID, "job_id": JOB_ID,
                "bindings": {"archive_sha256": sha(archive)},
                "findings": {"layover_shadow_semantics_reviewed": True},
                "rights": {"local_vv_vh_and_mask_inspection": True,
                           "DEM_display_or_export": False}})
            write(repo / GATE_REF, {
                "status": "pass_after_pixel_implementation_public_ci_only",
                "public_ci": {"conclusion": "success"},
                "bindings": {
                    "approval_sha256": APPROVAL_SHA,
                    "source_gate_sha256": SOURCE_GATE_SHA,
                    "submission_terminal_sha256": sha(data / SUBMISSION_REF),
                    "acquisition_terminal_sha256": sha(data / ACQUISITION_REF),
                    "metadata_review_sha256": sha(repo / METADATA_REVIEW_REF),
                    "header_terminal_sha256": sha(data / HEADER_REF),
                    "aoi_sha256": AOI_SHA256,
                    "pixel_contract_sha256": CONTRACT_SHA256,
                    "implementation_file_sha256": {
                        ref: sha(repo / ref) for ref in IMPLEMENTATION_FILES},
                }})
            write(repo / PREFLIGHT_REF, {
                "status": "pass_after_pixel_no_content",
                "bindings": {"implementation_gate_sha256": sha(repo / GATE_REF),
                             "acquisition_terminal_sha256": sha(data / ACQUISITION_REF),
                             "header_terminal_sha256": sha(data / HEADER_REF)},
                "assertions": {"attempt_absent": True,
                               "no_product_pixels_read": True}})
            attempt = data / "m2-asf-hyp3-rtc-after-pixel-001" / "attempt-001"
            self.assertEqual(require_release(repo, data, attempt)[2], archive)
            (repo / IMPLEMENTATION_FILES[0]).write_text("changed", encoding="utf-8")
            with self.assertRaisesRegex(RouteStop, "after_pixel_not_released"):
                require_release(repo, data, attempt)

    def test_partial_candidate_is_not_map_or_full_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)
            archive = data / f"{BASE}.zip"
            archive.write_bytes(b"disposable")
            attempt = data / "after-pixel" / "attempt"
            terminal = inspect_once(acquisition(archive), {}, archive, attempt,
                                    controlled_root=data, job_id=JOB_ID,
                                    scan=synthetic_scan)
            self.assertEqual(terminal["status"],
                             "defer_after_full_area_qa_partial_pair_candidate")
            self.assertFalse(terminal["arcgis_map_ready"])
            self.assertFalse(terminal["change_analysis_authorized"])
            with self.assertRaisesRegex(RouteStop, "after_pixel_attempt_collision"):
                inspect_once(acquisition(archive), {}, archive, attempt,
                             controlled_root=data, job_id=JOB_ID,
                             scan=synthetic_scan)

    def test_archive_drift_stops_before_scan(self):
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)
            archive = data / f"{BASE}.zip"
            archive.write_bytes(b"disposable")
            record = acquisition(archive)
            record["archive_sha256"] = "0" * 64
            attempt = data / "after-pixel" / "attempt"
            terminal = inspect_once(record, {}, archive, attempt,
                                    controlled_root=data, job_id=JOB_ID,
                                    scan=lambda *_: self.fail("scan must not run"))
            self.assertEqual(terminal["status"],
                             "stopped_after_pixel_no_automatic_retry")
            self.assertEqual(terminal["code"],
                             "after_pixel_archive_identity_mismatch")
            self.assertTrue((attempt / "terminal.json").is_file())


if __name__ == "__main__":
    unittest.main()
