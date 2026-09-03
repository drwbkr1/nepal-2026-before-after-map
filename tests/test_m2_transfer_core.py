from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from m2_transfer_core import (  # noqa: E402
    NoRedirectHandler,
    TransferControlError,
    promote_atomic_no_replace,
    require_safe_child,
    stream_to_exclusive_staging,
    write_new_json,
)
from acquire_m2_product import build_attempt_id, set_attempt_terminal  # noqa: E402


class M2TransferCoreTests(unittest.TestCase):
    def test_missing_access_reference_stops_without_mutating_active_intake(self) -> None:
        attempt_id = build_attempt_id("m1-src-001", "2026-09-03T17:00:00Z", "ABC123ef")
        self.assertEqual(attempt_id, "m1-src-001-20260903t170000z-abc123ef")
        self.assertRegex(attempt_id, r"^[a-z0-9][a-z0-9._-]{0,127}$")
        intake_path = ROOT / "contracts" / "m2-intake.json"
        before = hashlib.sha256(intake_path.read_bytes()).hexdigest()
        environment = dict(os.environ)
        environment.pop("CDSE_ACCESS_TOKEN", None)
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "acquire_m2_product.py"), "--source-id", "M1-SRC-001"],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 12)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["code"], "secret_safe_access_reference_missing")
        self.assertFalse(payload["mutations_performed"])
        self.assertEqual(hashlib.sha256(intake_path.read_bytes()).hexdigest(), before)

    def test_exact_stream_hashes_and_preserves_no_existing_file(self) -> None:
        payload = b"controlled-fixture-bytes" * 200
        with tempfile.TemporaryDirectory() as temporary:
            staged = Path(temporary) / "asset.part"
            result = stream_to_exclusive_staging(
                io.BytesIO(payload),
                staged,
                expected_size=len(payload),
                expected_md5=hashlib.md5(payload, usedforsecurity=False).hexdigest(),
                chunk_size=31,
            )
            self.assertEqual(result["sha256"], hashlib.sha256(payload).hexdigest())
            self.assertEqual(staged.read_bytes(), payload)

    def test_size_mismatch_preserves_failed_staging_bytes(self) -> None:
        payload = b"partial-fixture"
        with tempfile.TemporaryDirectory() as temporary:
            staged = Path(temporary) / "asset.part"
            with self.assertRaisesRegex(TransferControlError, "transferred_size_mismatch"):
                stream_to_exclusive_staging(
                    io.BytesIO(payload),
                    staged,
                    expected_size=len(payload) + 1,
                    expected_md5=hashlib.md5(payload, usedforsecurity=False).hexdigest(),
                )
            self.assertEqual(staged.read_bytes(), payload)

    def test_md5_mismatch_preserves_failed_staging_bytes(self) -> None:
        payload = b"wrong-provider-identity"
        with tempfile.TemporaryDirectory() as temporary:
            staged = Path(temporary) / "asset.part"
            with self.assertRaisesRegex(TransferControlError, "provider_md5_mismatch"):
                stream_to_exclusive_staging(
                    io.BytesIO(payload), staged, expected_size=len(payload), expected_md5="0" * 32
                )
            self.assertEqual(staged.read_bytes(), payload)

    def test_staging_collision_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            staged = Path(temporary) / "asset.part"
            staged.write_bytes(b"existing")
            with self.assertRaisesRegex(TransferControlError, "staging_collision"):
                stream_to_exclusive_staging(io.BytesIO(b"new"), staged, expected_size=3, expected_md5="0" * 32)
            self.assertEqual(staged.read_bytes(), b"existing")

    def test_atomic_no_replace_promotion_and_identity(self) -> None:
        payload = b"verified-staged-content"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            staged = root / "asset.part"
            destination = root / "asset.zip"
            staged.write_bytes(payload)
            result = promote_atomic_no_replace(staged, destination)
            self.assertFalse(staged.exists())
            self.assertEqual(destination.read_bytes(), payload)
            self.assertEqual(result["sha256"], hashlib.sha256(payload).hexdigest())

    def test_destination_collision_preserves_both_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            staged = root / "asset.part"
            destination = root / "asset.zip"
            staged.write_bytes(b"staged")
            destination.write_bytes(b"existing")
            with self.assertRaisesRegex(TransferControlError, "destination_collision"):
                promote_atomic_no_replace(staged, destination)
            self.assertEqual(staged.read_bytes(), b"staged")
            self.assertEqual(destination.read_bytes(), b"existing")

    def test_path_escape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(TransferControlError, "path_outside_controlled_root"):
                require_safe_child(root, root.parent / "outside.bin")

    def test_redirect_handler_refuses_every_redirect(self) -> None:
        handler = NoRedirectHandler()
        self.assertIsNone(handler.redirect_request(None, None, 302, "Found", {}, "https://example.invalid"))

    def test_control_receipt_refuses_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            receipt = Path(temporary) / "receipt.json"
            write_new_json(receipt, {"status": "first"})
            with self.assertRaises(FileExistsError):
                write_new_json(receipt, {"status": "replacement"})
            self.assertEqual(json.loads(receipt.read_text(encoding="utf-8")), {"status": "first"})

    def test_failed_attempt_becomes_terminal_without_erasing_history(self) -> None:
        intake = {
            "assets": [{
                "asset_id": "asset-001",
                "state": "staging",
                "attempts": [{
                    "attempt_id": "attempt-001",
                    "started_at": "2026-09-03T17:00:00Z",
                    "completed_at": None,
                    "outcome": "started",
                }],
                "failure": None,
            }]
        }
        asset = set_attempt_terminal(
            intake,
            "asset-001",
            "attempt-001",
            "2026-09-03T17:01:00Z",
            outcome="failed",
            failure_code="provider_transport_failure",
        )
        self.assertEqual(asset["state"], "failed")
        self.assertEqual(len(asset["attempts"]), 1)
        self.assertEqual(asset["attempts"][0]["outcome"], "failed")
        self.assertEqual(asset["failure"]["code"], "provider_transport_failure")


if __name__ == "__main__":
    unittest.main()
