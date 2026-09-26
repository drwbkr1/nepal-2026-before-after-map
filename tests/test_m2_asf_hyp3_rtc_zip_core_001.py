"""Disposable ZIP tests; no project product or external custody is opened."""

from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile, ZipInfo


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from m2_asf_hyp3_rtc_core_001 import ORDER, RouteStop, load_approved_jobs  # noqa: E402
from m2_asf_hyp3_rtc_package_core_001 import REQUIRED_SUFFIXES  # noqa: E402
from m2_asf_hyp3_rtc_zip_core_001 import inspect_package_zip  # noqa: E402


def make_zip(path: Path, source_id: str, *, traversal: bool = False, empty_suffix: str | None = None, special_suffix: str | None = None) -> None:
    job = next(item for item in load_approved_jobs() if item["source_id"] == source_id)
    start = job["job_parameters"]["granules"][0].split("_")[4]
    root = f"S1D_IW_{start}_DVP_RTC10_G_gpuned_ABCD"
    with ZipFile(path, "w", ZIP_STORED) as archive:
        archive.writestr(root + "/", b"")
        for suffix in REQUIRED_SUFFIXES:
            name = f"{root}/{root}{suffix}"
            info = ZipInfo(name)
            if suffix == special_suffix:
                info.create_system = 3
                info.external_attr = 0o120777 << 16
            archive.writestr(info, b"" if suffix == empty_suffix else b"synthetic")
        if traversal:
            archive.writestr(f"{root}/../escape", b"synthetic")


def binding(path: Path) -> dict:
    return {"expected_size_bytes": path.stat().st_size, "expected_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


class ZipScreenTests(unittest.TestCase):
    def test_exact_synthetic_archive_passes_only_local_container_checks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "product.zip"
            make_zip(path, ORDER[0])
            result = inspect_package_zip(ORDER[0], path, **binding(path))
            self.assertEqual(result["status"], "pass_local_zip_identity_structure_crc_only")
            self.assertTrue(result["zip_crc_verified"])
            self.assertFalse(result["provider_transfer_or_job_identity_verified"])
            self.assertFalse(result["geotiff_headers_or_pixels_read"])

    def test_wrong_transfer_identity_and_source_stop(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "product.zip"
            make_zip(path, ORDER[0])
            with self.assertRaisesRegex(RouteStop, "rtc_zip_size_mismatch"):
                inspect_package_zip(ORDER[0], path, expected_size_bytes=path.stat().st_size + 1, expected_sha256=binding(path)["expected_sha256"])
            with self.assertRaisesRegex(RouteStop, "rtc_zip_sha256_mismatch"):
                inspect_package_zip(ORDER[0], path, expected_size_bytes=path.stat().st_size, expected_sha256="0" * 64)
            with self.assertRaisesRegex(RouteStop, "rtc_package_product_identity_mismatch"):
                inspect_package_zip(ORDER[1], path, **binding(path))

    def test_unsafe_member_and_corrupt_crc_stop(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "unsafe.zip"
            make_zip(path, ORDER[0], traversal=True)
            with self.assertRaisesRegex(RouteStop, "rtc_package_path_invalid"):
                inspect_package_zip(ORDER[0], path, **binding(path))
            make_zip(path, ORDER[0])
            data = bytearray(path.read_bytes())
            marker = data.index(b"synthetic")
            data[marker] ^= 1
            path.write_bytes(data)
            with self.assertRaisesRegex(RouteStop, "rtc_zip_crc_failed"):
                inspect_package_zip(ORDER[0], path, **binding(path))

    def test_symlink_path_stops_without_read(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "product.zip"
            link = Path(temp) / "linked.zip"
            make_zip(path, ORDER[0])
            try:
                link.symlink_to(path)
            except OSError:
                self.skipTest("symlink creation unavailable")
            with self.assertRaisesRegex(RouteStop, "rtc_zip_path_invalid"):
                inspect_package_zip(ORDER[0], link, **binding(path))

    def test_empty_required_and_special_member_stop(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "product.zip"
            make_zip(path, ORDER[0], empty_suffix="_VV.tif")
            with self.assertRaisesRegex(RouteStop, "rtc_zip_required_member_empty"):
                inspect_package_zip(ORDER[0], path, **binding(path))
            make_zip(path, ORDER[0], special_suffix="_VH.tif")
            with self.assertRaisesRegex(RouteStop, "rtc_zip_special_member"):
                inspect_package_zip(ORDER[0], path, **binding(path))


if __name__ == "__main__":
    unittest.main()
