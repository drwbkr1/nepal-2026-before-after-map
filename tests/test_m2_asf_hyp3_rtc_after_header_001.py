"""Disposable guards for the after-product six-raster header worker."""

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
from m2_asf_hyp3_rtc_after_header_001 import (  # noqa: E402
    ACQUISITION_REF, APPROVAL_REF, APPROVAL_SHA, GATE_REF,
    IMPLEMENTATION_FILES, METADATA_REF, METADATA_REVIEW_REF,
    PREFLIGHT_REF, SOURCE_GATE_REF, SOURCE_GATE_SHA, SUBMISSION_REF,
    inspect_once, require_release,
)
from m2_asf_hyp3_rtc_core_001 import RouteStop  # noqa: E402
from m2_asf_hyp3_rtc_header_core_001 import RASTERS  # noqa: E402
from m2_asf_hyp3_rtc_package_core_001 import REQUIRED_SUFFIXES  # noqa: E402


SOURCE_ID = "M1-SRC-005"
JOB_ID = "27836b79-e5b2-4d8f-932f-659724ea02c3"
BASE = "S1D_IW_20260828T122141_DVP_RTC10_G_gpuned_ABCD"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def make_zip(path: Path, *, missing: str | None = None) -> None:
    with ZipFile(path, "w", ZIP_STORED) as archive:
        archive.writestr(BASE + "/", b"")
        for suffix in REQUIRED_SUFFIXES:
            if suffix != missing:
                archive.writestr(f"{BASE}/{BASE}{suffix}", b"synthetic")


def acquisition(path: Path) -> dict:
    return {"status": "pass_local_zip_promoted_no_replace",
            "source_id": SOURCE_ID, "job_id": JOB_ID,
            "product_filename": path.name,
            "archive_size_bytes": path.stat().st_size,
            "archive_sha256": sha(path),
            "archive_integrity_verified": True,
            "geotiff_headers_or_pixels_read": False}


def fake_describe(_archive: Path, member: str) -> dict:
    suffix = member.rsplit("_", 1)[-1]
    if suffix.startswith("VV.tif"):
        role = "vv"
    elif suffix.startswith("VH.tif"):
        role = "vh"
    elif suffix.startswith("map.tif"):
        role = "ls_map" if "_ls_map.tif" in member else "inc_map"
    elif "_dem.tif" in member:
        role = "dem"
    else:
        role = "area"
    return {"width": 64, "height": 64, "band_count": 1,
            "data_type": RASTERS[role],
            "grid": {"wkid": 32645, "cell_size_x": 10.0,
                     "cell_size_y": 10.0, "origin_x": 300000.0,
                     "origin_y": 3100640.0, "xmin": 300000.0,
                     "ymin": 3100000.0, "xmax": 300640.0,
                     "ymax": 3100640.0, "rotation_degrees": 0.0}}


class AfterHeaderTests(unittest.TestCase):
    def test_unreleased_stops_before_archive_open(self):
        with tempfile.TemporaryDirectory() as temp, self.assertRaisesRegex(
                RouteStop, "after_header_required_path_invalid"):
            base = Path(temp)
            require_release(base / "repo", base / "data",
                            base / "data" / "header" / "attempt")

    def test_complete_synthetic_release_and_code_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            repo, data = base / "repo", base / "data"
            repo.mkdir()
            data.mkdir()
            for ref in (*IMPLEMENTATION_FILES, APPROVAL_REF, SOURCE_GATE_REF):
                target = repo / ref
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / ref, target)
            self.assertEqual(sha(repo / APPROVAL_REF), APPROVAL_SHA)
            self.assertEqual(sha(repo / SOURCE_GATE_REF), SOURCE_GATE_SHA)
            archive = data / "m2-asf-hyp3-rtc-products-after-partial-001" / f"{BASE}.zip"
            archive.parent.mkdir()
            make_zip(archive)
            write(data / SUBMISSION_REF, {
                "status": "submitted_product_unverified", "source_id": SOURCE_ID,
                "job_id": JOB_ID, "credit_cost": 60,
                "credentials_recorded": False, "product_bytes_verified": False,
                "pixel_qa_pass": False})
            write(data / ACQUISITION_REF, acquisition(archive))
            write(data / METADATA_REF, {
                "status": "pass_bounded_after_metadata_captured_for_local_review_only",
                "source_id": SOURCE_ID, "job_id": JOB_ID,
                "archive_sha256": sha(archive), "raster_header_or_pixel_read": False})
            write(repo / METADATA_REVIEW_REF, {
                "status": "pass_after_metadata_for_header_and_pixel_qa_only",
                "source_id": SOURCE_ID, "job_id": JOB_ID,
                "bindings": {"capture_terminal_sha256": sha(data / METADATA_REF),
                             "archive_sha256": sha(archive)},
                "findings": {"exact_source_granule_present": True,
                             "gamma0_power_10m_no_speckle": True,
                             "layover_shadow_semantics_reviewed": True},
                "rights": {"local_vv_vh_and_mask_inspection": True,
                           "DEM_display_or_export": False}})
            write(repo / GATE_REF, {
                "status": "pass_after_header_implementation_public_ci_only",
                "public_ci": {"conclusion": "success"},
                "bindings": {
                    "approval_sha256": APPROVAL_SHA,
                    "source_gate_sha256": SOURCE_GATE_SHA,
                    "submission_terminal_sha256": sha(data / SUBMISSION_REF),
                    "acquisition_terminal_sha256": sha(data / ACQUISITION_REF),
                    "metadata_terminal_sha256": sha(data / METADATA_REF),
                    "metadata_review_sha256": sha(repo / METADATA_REVIEW_REF),
                    "implementation_file_sha256": {
                        ref: sha(repo / ref) for ref in IMPLEMENTATION_FILES},
                }})
            write(repo / PREFLIGHT_REF, {
                "status": "pass_after_header_no_content",
                "bindings": {"implementation_gate_sha256": sha(repo / GATE_REF),
                             "acquisition_terminal_sha256": sha(data / ACQUISITION_REF),
                             "metadata_terminal_sha256": sha(data / METADATA_REF)},
                "assertions": {"attempt_absent": True,
                               "no_raster_header_or_pixel_read": True}})
            attempt = data / "m2-asf-hyp3-rtc-after-header-001" / "attempt-001"
            self.assertEqual(require_release(repo, data, attempt)[1], archive)
            (repo / IMPLEMENTATION_FILES[0]).write_text("changed", encoding="utf-8")
            with self.assertRaisesRegex(RouteStop, "after_header_not_released"):
                require_release(repo, data, attempt)

    def test_six_headers_pass_once_without_pixels(self):
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)
            archive = data / f"{BASE}.zip"
            make_zip(archive)
            attempt = data / "after-header" / "attempt"
            result = inspect_once(acquisition(archive), archive, attempt,
                                  controlled_root=data, describe=fake_describe,
                                  job_id=JOB_ID)
            self.assertEqual(result["status"], "pass_after_headers_for_local_pixel_qa_only")
            self.assertEqual(set(result["headers"]), set(RASTERS))
            self.assertFalse(result["pixels_read"])
            with self.assertRaisesRegex(RouteStop, "after_header_attempt_collision"):
                inspect_once(acquisition(archive), archive, attempt,
                             controlled_root=data, describe=fake_describe,
                             job_id=JOB_ID)

    def test_hash_drift_and_missing_member_stop_terminal(self):
        for missing in (None, "_VH.tif"):
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as temp:
                data = Path(temp)
                archive = data / f"{BASE}.zip"
                make_zip(archive, missing=missing)
                record = acquisition(archive)
                if missing is None:
                    record["archive_sha256"] = "0" * 64
                attempt = data / "after-header" / "attempt"
                result = inspect_once(record, archive, attempt,
                                      controlled_root=data, describe=fake_describe,
                                      job_id=JOB_ID)
                self.assertEqual(result["status"], "stopped_after_header_no_automatic_retry")
                self.assertEqual(result["code"], (
                    "after_header_archive_identity_mismatch" if missing is None
                    else "rtc_package_required_member_missing"))
                self.assertTrue((attempt / "terminal.json").is_file())


if __name__ == "__main__":
    unittest.main()
