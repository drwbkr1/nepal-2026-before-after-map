"""Disposable runner tests for the first HyP3 event-AOI pixel gate."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import m2_asf_hyp3_rtc_product_pixel_001 as pixel  # noqa: E402
from m2_asf_hyp3_rtc_core_001 import RouteStop  # noqa: E402


class ProductPixelRunnerTests(unittest.TestCase):
    def test_distinct_attempt_records_two_aoi_pass_without_raw_pixels(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            custody = Path(temp) / "custody"
            products = custody / "products"
            products.mkdir(parents=True)
            archive = products / "synthetic.zip"
            archive.write_bytes(b"synthetic-raster-archive-private-example")
            before = archive.read_bytes()
            acquisition = {"archive_size_bytes": len(before),
                           "archive_sha256": hashlib.sha256(before).hexdigest()}
            attempt = custody / "pixels" / "attempt-001"
            def scan(_archive, _header, aois, _contract):
                self.assertEqual([item[0] for item in aois], list(pixel.EVENT_AOIS))
                return [{"aoi_id": name, "status": "pass_qa_only", "private": False}
                        for name, _ in aois]
            with patch.object(pixel, "PRODUCT_FILENAME", archive.name), \
                 patch.object(pixel, "ARCHIVE_SHA256", acquisition["archive_sha256"]):
                result = pixel.inspect_once(acquisition, {}, archive, attempt,
                                            controlled_root=custody, scan=scan)
            self.assertEqual(result["status"], "pass_source_event_aoi_pixel_qa_only")
            self.assertTrue(result["next_job_released"])
            self.assertFalse(result["DEM_pixels_read"])
            self.assertFalse(result["registration_measured"])
            self.assertEqual(archive.read_bytes(), before)
            self.assertNotIn("private-example", (attempt / "terminal.json").read_text())
            with self.assertRaisesRegex(RouteStop, "rtc_pixel_attempt_collision"):
                pixel.inspect_once(acquisition, {}, archive, attempt,
                                   controlled_root=custody, scan=scan)

    def test_aoi_defer_stops_next_date_without_retry(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            custody = Path(temp) / "custody"
            products = custody / "products"
            products.mkdir(parents=True)
            archive = products / "synthetic.zip"
            archive.write_bytes(b"synthetic")
            acquisition = {"archive_size_bytes": archive.stat().st_size,
                           "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest()}
            attempt = custody / "pixels" / "attempt-001"
            def scan(_archive, _header, aois, _contract):
                return [{"aoi_id": aois[0][0], "status": "pass_qa_only"},
                        {"aoi_id": aois[1][0], "status": "defer"}]
            with patch.object(pixel, "PRODUCT_FILENAME", archive.name), \
                 patch.object(pixel, "ARCHIVE_SHA256", acquisition["archive_sha256"]):
                result = pixel.inspect_once(acquisition, {}, archive, attempt,
                                            controlled_root=custody, scan=scan)
            self.assertEqual(result["status"], "stop_source_event_aoi_pixel_qa_no_next_date")
            self.assertFalse(result["next_job_released"])

    def test_wrong_hash_stops_before_scanner(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            custody = Path(temp) / "custody"
            products = custody / "products"
            products.mkdir(parents=True)
            archive = products / "synthetic.zip"
            archive.write_bytes(b"synthetic")
            acquisition = {"archive_size_bytes": archive.stat().st_size,
                           "archive_sha256": "0" * 64}
            attempt = custody / "pixels" / "attempt-001"
            def scanner(*_args):
                raise AssertionError("scanner must not start")
            with patch.object(pixel, "PRODUCT_FILENAME", archive.name):
                result = pixel.inspect_once(acquisition, {}, archive, attempt,
                                            controlled_root=custody, scan=scanner)
            self.assertEqual(result["code"], "rtc_pixel_archive_identity_mismatch")
            self.assertFalse(result["next_job_released"])
            self.assertTrue((attempt / "terminal.json").is_file())

    def test_synthetic_interruption_persists_indeterminate_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            custody = Path(temp) / "custody"
            products = custody / "products"
            products.mkdir(parents=True)
            archive = products / "synthetic.zip"
            archive.write_bytes(b"synthetic")
            acquisition = {"archive_size_bytes": archive.stat().st_size,
                           "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest()}
            attempt = custody / "pixels" / "attempt-001"
            def interrupted(*_args):
                raise KeyboardInterrupt()
            with patch.object(pixel, "PRODUCT_FILENAME", archive.name), \
                 patch.object(pixel, "ARCHIVE_SHA256", acquisition["archive_sha256"]):
                result = pixel.inspect_once(acquisition, {}, archive, attempt,
                                            controlled_root=custody, scan=interrupted)
            self.assertEqual(result["status"], "stopped_pixel_qa_no_automatic_retry")
            self.assertEqual(result["pixel_read_status"], "indeterminate_on_failure")
            self.assertFalse(result["next_job_released"])
            self.assertEqual(json.loads((attempt / "terminal.json").read_text())["code"],
                             "rtc_pixel_unexpected_failure")

    def test_missing_release_cannot_read_archive(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            custody = Path(temp) / "custody"
            root.mkdir()
            custody.mkdir()
            with self.assertRaisesRegex(RouteStop, "rtc_pixel_required_path_invalid"):
                pixel.require_release(root, custody,
                                      custody / "m2-asf-hyp3-rtc-product-pixel-001" / "attempt-001")


if __name__ == "__main__":
    unittest.main()
