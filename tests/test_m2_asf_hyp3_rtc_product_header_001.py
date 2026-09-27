"""Portable disposable tests for the gated first RTC header runner."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import m2_asf_hyp3_rtc_product_header_001 as header  # noqa: E402
from m2_asf_hyp3_rtc_core_001 import RouteStop  # noqa: E402
from tests.test_m2_asf_hyp3_rtc_header_core_001 import headers  # noqa: E402
from tests.test_m2_asf_hyp3_rtc_product_metadata_001 import fixture  # noqa: E402


class ProductHeaderTests(unittest.TestCase):
    def test_fresh_synthetic_package_checks_six_headers_without_pixels(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            custody = Path(temp) / "custody"
            products = custody / "products"
            products.mkdir(parents=True)
            archive = products / "S1D_IW_20260816T122141_DVP_RTC10_G_gpuned_ABCD.zip"
            before, _ = fixture(archive)
            acquisition = {"archive_size_bytes": len(before),
                           "archive_sha256": hashlib.sha256(before).hexdigest()}
            attempt = custody / "headers" / "attempt-001"
            observed = []
            def describe(path: Path, member: str) -> dict:
                self.assertEqual(path, archive)
                observed.append(member)
                role = next(role for role, suffix in header.ROLE_SUFFIX.items()
                            if member.endswith(suffix))
                return headers()[role]
            with patch.object(header, "PRODUCT_FILENAME", archive.name), \
                 patch.object(header, "ARCHIVE_SHA256", acquisition["archive_sha256"]):
                result = header.inspect_once(acquisition, archive, attempt,
                                             controlled_root=custody, describe=describe)
            self.assertEqual(result["status"], "pass_actual_headers_for_local_pixel_qa_only")
            self.assertEqual(len(observed), 6)
            self.assertEqual(set(result["headers"]), set(header.ROLE_SUFFIX))
            self.assertFalse(result["pixels_read"])
            self.assertEqual(archive.read_bytes(), before)
            self.assertNotIn("private-example", (attempt / "terminal.json").read_text())
            with self.assertRaisesRegex(RouteStop, "rtc_header_attempt_collision"):
                header.inspect_once(acquisition, archive, attempt, controlled_root=custody,
                                    describe=describe)

    def test_shifted_or_wrong_crs_descriptor_stops_and_persists(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            custody = Path(temp) / "custody"
            products = custody / "products"
            products.mkdir(parents=True)
            archive = products / "S1D_IW_20260816T122141_DVP_RTC10_G_gpuned_ABCD.zip"
            before, _ = fixture(archive)
            acquisition = {"archive_size_bytes": len(before),
                           "archive_sha256": hashlib.sha256(before).hexdigest()}
            attempt = custody / "headers" / "attempt-001"
            def describe(_path: Path, member: str) -> dict:
                role = next(role for role, suffix in header.ROLE_SUFFIX.items()
                            if member.endswith(suffix))
                value = headers()[role]
                if role == "vv":
                    value["grid"]["wkid"] = 4326
                return value
            with patch.object(header, "PRODUCT_FILENAME", archive.name), \
                 patch.object(header, "ARCHIVE_SHA256", acquisition["archive_sha256"]):
                result = header.inspect_once(acquisition, archive, attempt,
                                             controlled_root=custody, describe=describe)
            self.assertEqual(result["status"], "stopped_header_only_no_automatic_retry")
            self.assertEqual(result["code"], "rtc_header_projected_grid_invalid")
            self.assertFalse(result["pixels_read"])
            self.assertTrue((attempt / "terminal.json").is_file())
            self.assertEqual(archive.read_bytes(), before)

    def test_missing_gate_cannot_touch_product(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            custody = Path(temp) / "custody"
            root.mkdir()
            custody.mkdir()
            with self.assertRaisesRegex(RouteStop, "rtc_header_required_path_invalid"):
                header.require_release(root, custody,
                                       custody / "m2-asf-hyp3-rtc-product-header-001" / "attempt-001")


if __name__ == "__main__":
    unittest.main()
