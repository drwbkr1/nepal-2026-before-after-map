from __future__ import annotations

import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import landsat_l2_browser_handoff as handoff  # noqa: E402
from tests.test_landsat_l2_bundle_integrity import PRODUCT, SCENE, fixtures, write_tar  # noqa: E402


class LandsatL2BrowserHandoffTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name)
        self.controlled_root = base / "nepal-2026-before-after-map-data"
        self.controlled_root.mkdir()
        self.attempt_id = "landsat9-before-20260810-001"
        staging_root = self.controlled_root / ".intake-staging" / "nepal-m2-landsat9-usgs-bundle-001"
        self.attempt_dir = staging_root / "attempt-events" / self.attempt_id
        self.staging = staging_root / "attempt-bytes" / self.attempt_id / f"{PRODUCT}.tar.part"
        self.destination = self.controlled_root / "custody" / "landsat9-c2l2" / f"{PRODUCT}.tar"
        self.browser_file = base / "private-session-cookie-sample.tar"
        write_tar(self.browser_file, fixtures())

    def args(self) -> dict:
        return {
            "controlled_root": self.controlled_root,
            "attempt_dir": self.attempt_dir,
            "staging": self.staging,
            "destination": self.destination,
            "attempt_id": self.attempt_id,
            "product_id": PRODUCT,
            "scene_id": SCENE,
        }

    def reserve(self) -> dict:
        return handoff.reserve_attempt(
            **self.args(),
            approval_ref=handoff.APPROVAL_REF,
            approval_sha256=handoff.APPROVAL_SHA256,
        )

    def mark_started(self) -> dict:
        return handoff.mark_browser_request_started(
            **self.args(),
            public_ci_commit="a" * 40,
            public_ci_run_id="12345678",
            preflight_sha256="b" * 64,
        )

    def test_completed_synthetic_bundle_is_promoted_no_replace_with_sanitized_receipts(self) -> None:
        self.reserve()
        self.mark_started()
        terminal = handoff.complete_attempt(
            **self.args(), completed_browser_file=self.browser_file
        )
        self.assertEqual(terminal["status"], "pass_bundle_promoted_container_only")
        self.assertTrue(self.destination.is_file())
        self.assertFalse(self.staging.exists())
        self.assertEqual(terminal["size_bytes"], self.destination.stat().st_size)
        self.assertEqual(json.loads((self.attempt_dir / "verification.json").read_text())["member_count"], 10)
        for receipt in self.attempt_dir.glob("*.json"):
            body = receipt.read_text(encoding="utf-8")
            self.assertNotIn(str(self.browser_file), body)
            self.assertNotIn("private-session-cookie-sample", body)
        with self.assertRaisesRegex(handoff.HandoffError, "attempt_already_terminal"):
            handoff.complete_attempt(**self.args(), completed_browser_file=self.browser_file)

    def test_wrong_mtl_identity_preserves_staging_and_blocks_promotion(self) -> None:
        self.reserve()
        self.mark_started()
        write_tar(self.browser_file, fixtures(scene="LC91410402026238LGN00"))
        terminal = handoff.complete_attempt(
            **self.args(), completed_browser_file=self.browser_file
        )
        self.assertEqual(terminal["status"], "block_handoff_or_container_failure")
        self.assertEqual(terminal["failure_code"], "mtl_text_identity_mismatch")
        self.assertTrue(self.staging.is_file())
        self.assertFalse(self.destination.exists())
        self.assertTrue((self.attempt_dir / "cleanup.json").exists())

    def test_interrupted_copy_retains_partial_and_terminal_receipt(self) -> None:
        self.reserve()
        self.mark_started()

        def interrupt(_source: Path, staging: Path) -> dict:
            staging.write_bytes(b"partial")
            raise OSError("private-session-cookie-sample must not persist")

        with patch.object(handoff, "_copy_completed_file", side_effect=interrupt):
            terminal = handoff.complete_attempt(
                **self.args(), completed_browser_file=self.browser_file
            )
        self.assertEqual(terminal["failure_code"], "local_io_failure")
        self.assertTrue(self.staging.is_file())
        self.assertFalse(self.destination.exists())
        self.assertNotIn("private-session-cookie", (self.attempt_dir / "terminal.json").read_text())

    def test_browser_failure_closes_attempt_without_source_path(self) -> None:
        self.reserve()
        self.mark_started()
        terminal = handoff.record_browser_failure(
            **self.args(), failure_code="browser_download_path_unavailable"
        )
        self.assertEqual(terminal["status"], "block_browser_download_no_complete_file")
        self.assertFalse(self.destination.exists())
        with self.assertRaisesRegex(handoff.HandoffError, "attempt_already_terminal"):
            handoff.record_browser_failure(
                **self.args(), failure_code="browser_download_path_unavailable"
            )

    def test_wrong_identity_path_and_collision_stop_before_reservation(self) -> None:
        wrong = self.args() | {"scene_id": "LC91410402026238LGN00"}
        with self.assertRaisesRegex(handoff.HandoffError, "exact_product_scene_identity_mismatch"):
            handoff.reserve_attempt(
                **wrong, approval_ref=handoff.APPROVAL_REF,
                approval_sha256=handoff.APPROVAL_SHA256,
            )
        wrong_path = self.args() | {"destination": self.controlled_root / "custody" / "wrong.tar"}
        with self.assertRaisesRegex(handoff.HandoffError, "handoff_path_not_frozen"):
            handoff.reserve_attempt(
                **wrong_path, approval_ref=handoff.APPROVAL_REF,
                approval_sha256=handoff.APPROVAL_SHA256,
            )
        self.destination.parent.mkdir(parents=True)
        self.destination.write_bytes(b"existing")
        with self.assertRaisesRegex(handoff.HandoffError, "destination_collision"):
            self.reserve()
        self.assertFalse(self.attempt_dir.exists())

    def test_reserved_without_request_marker_cannot_read_bundle(self) -> None:
        self.reserve()
        with self.assertRaisesRegex(handoff.HandoffError, "browser_request_marker_missing"):
            handoff.complete_attempt(**self.args(), completed_browser_file=self.browser_file)
        self.assertFalse(self.staging.exists())

    def test_collision_after_request_marker_is_terminal(self) -> None:
        self.reserve()
        self.mark_started()
        self.destination.write_bytes(b"other bytes")
        terminal = handoff.complete_attempt(**self.args(), completed_browser_file=self.browser_file)
        self.assertEqual(terminal["failure_code"], "destination_collision")
        self.assertEqual(self.destination.read_bytes(), b"other bytes")
        self.assertTrue((self.attempt_dir / "terminal.json").exists())


if __name__ == "__main__":
    unittest.main()
