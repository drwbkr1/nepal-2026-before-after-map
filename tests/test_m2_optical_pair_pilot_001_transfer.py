"""Disposable transfer and custody checks; no CDSE request or project data."""

from __future__ import annotations

import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import blake3


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from m2_optical_pair_pilot_001_core import PilotControlError  # noqa: E402
from m2_optical_pair_pilot_001_transfer import (  # noqa: E402
    hash_stream_to_new_file,
    previous_attempts,
    verify_zip,
    write_new_json,
)


class OpticalPilotTransferTests(unittest.TestCase):
    def test_stream_checks_both_provider_hashes(self) -> None:
        payload = b"synthetic disposable data" * 400
        with tempfile.TemporaryDirectory() as folder:
            stage = Path(folder) / "sample.part"
            result = hash_stream_to_new_file(
                io.BytesIO(payload), stage,
                expected_size=len(payload),
                expected_md5=hashlib.md5(payload, usedforsecurity=False).hexdigest(),
                expected_blake3=blake3.blake3(payload).hexdigest(),
            )
            self.assertEqual(result["sha256"], hashlib.sha256(payload).hexdigest())
            self.assertEqual(stage.read_bytes(), payload)
            with self.assertRaises(PilotControlError):
                hash_stream_to_new_file(
                    io.BytesIO(payload), Path(folder) / "bad.part",
                    expected_size=len(payload), expected_md5=result["md5"], expected_blake3="0" * 64,
                )
            with self.assertRaisesRegex(PilotControlError, "transport_interrupted"):
                hash_stream_to_new_file(
                    io.BytesIO(payload[:-1]), Path(folder) / "short.part",
                    expected_size=len(payload), expected_md5=result["md5"], expected_blake3=result["blake3"],
                )

    def test_container_safety_and_crc(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / "sample.zip"
            with ZipFile(archive, "w", ZIP_DEFLATED) as out:
                out.writestr("EXACT.SAFE/manifest.safe", "synthetic")
            self.assertTrue(verify_zip(archive, "EXACT.SAFE")["zip_crc_pass"])
            with self.assertRaises(PilotControlError):
                verify_zip(archive, "WRONG.SAFE")

    def test_attempt_history_must_be_terminal_before_retry(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            one = root / "attempt-1"
            one.mkdir()
            write_new_json(one / "started.json", {"attempt_id": "attempt-1"})
            with self.assertRaisesRegex(PilotControlError, "prior_attempt_indeterminate"):
                previous_attempts(root)
            write_new_json(one / "terminal.json", {"attempt_id": "attempt-1", "status": "transport_interrupted"})
            self.assertEqual(previous_attempts(root)[0]["status"], "transport_interrupted")
            self.assertNotIn("secret", json.dumps(previous_attempts(root)))


if __name__ == "__main__":
    unittest.main()
