"""Disposable, no-network M1-SRC-005 ZIP transfer tests."""

from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m2_asf_hyp3_rtc_after_transfer_core_001 import (  # noqa: E402
    promote_after_zip_no_replace, stream_after_zip_once,
)
from m2_asf_hyp3_rtc_core_001 import RouteStop  # noqa: E402
from m2_asf_hyp3_rtc_package_core_001 import REQUIRED_SUFFIXES  # noqa: E402


PRODUCT = "S1D_IW_20260828T122141_DVP_RTC10_G_gpuned_ABCD"


def zip_bytes(*, omit_suffix: str | None = None) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_STORED) as archive:
        archive.writestr(PRODUCT + "/", b"")
        for suffix in REQUIRED_SUFFIXES:
            if suffix != omit_suffix:
                archive.writestr(f"{PRODUCT}/{PRODUCT}{suffix}", b"generated-data")
    return buffer.getvalue()


class AfterTransferTests(unittest.TestCase):
    def test_one_staged_zip_verified_and_promoted_no_replace(self):
        payload = zip_bytes()
        with tempfile.TemporaryDirectory() as temp:
            staging = Path(temp) / "one.part"
            destination = Path(temp) / "one.zip"
            staged = stream_after_zip_once(BytesIO(payload), staging, expected_size_bytes=len(payload))
            self.assertEqual(staged["sha256"], hashlib.sha256(payload).hexdigest())
            self.assertTrue(staged["zip_crc_verified"])
            promoted = promote_after_zip_no_replace(staging, destination, staged)
            self.assertEqual(promoted["status"], "pass_local_zip_promoted_no_replace")
            self.assertFalse(staging.exists())
            self.assertEqual(destination.read_bytes(), payload)
            with self.assertRaisesRegex(RouteStop, "after_transfer_binding_invalid"):
                stream_after_zip_once(BytesIO(payload), destination, expected_size_bytes=len(payload))

    def test_existing_destination_blocks_without_modification(self):
        payload = zip_bytes()
        with tempfile.TemporaryDirectory() as temp:
            staging = Path(temp) / "one.part"
            destination = Path(temp) / "one.zip"
            staged = stream_after_zip_once(BytesIO(payload), staging, expected_size_bytes=len(payload))
            destination.write_bytes(b"prior")
            with self.assertRaisesRegex(RouteStop, "after_transfer_promotion_binding_invalid"):
                promote_after_zip_no_replace(staging, destination, staged)
            self.assertEqual(destination.read_bytes(), b"prior")
            self.assertTrue(staging.exists())

    def test_short_stream_preserved_as_failed_partial(self):
        payload = zip_bytes()
        with tempfile.TemporaryDirectory() as temp:
            staging = Path(temp) / "one.part"
            with self.assertRaisesRegex(RouteStop, "after_transfer_size_mismatch"):
                stream_after_zip_once(BytesIO(payload[:-1]), staging,
                                      expected_size_bytes=len(payload))
            self.assertEqual(staging.stat().st_size, len(payload) - 1)

    def test_missing_required_member_stops_before_promotion(self):
        payload = zip_bytes(omit_suffix="_VH.tif")
        with tempfile.TemporaryDirectory() as temp:
            staging = Path(temp) / "one.part"
            with self.assertRaisesRegex(RouteStop, "rtc_package_required_member_missing"):
                stream_after_zip_once(BytesIO(payload), staging,
                                      expected_size_bytes=len(payload))
            self.assertTrue(staging.exists())

    def test_staged_mutation_blocks_promotion(self):
        payload = zip_bytes()
        with tempfile.TemporaryDirectory() as temp:
            staging = Path(temp) / "one.part"
            destination = Path(temp) / "one.zip"
            staged = stream_after_zip_once(BytesIO(payload), staging, expected_size_bytes=len(payload))
            with staging.open("ab") as stream:
                stream.write(b"changed")
            with self.assertRaises(RouteStop):
                promote_after_zip_no_replace(staging, destination, staged)
            self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
