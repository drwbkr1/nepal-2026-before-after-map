from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import landsat_l2_grouped_mtl_recovery_002 as recovery  # noqa: E402
from tests.test_landsat_l2_grouped_mtl_integrity_002 import metadata, write_tar  # noqa: E402


def synthetic_bundle(path: Path, product: str, scene: str, *, wrong_scene: bool = False) -> None:
    l1 = product.replace("_L2SP_", "_L1TP_")
    text, xml = metadata(product, "LC91410402026223LGN00" if wrong_scene else scene, l1)
    items = [(product + suffix,
              text if suffix == "_MTL.txt" else xml if suffix == "_MTL.xml" else b"synthetic-not-a-tiff")
             for suffix in recovery.inspect_bundle.__globals__["REQUIRED_SUFFIXES"]]
    write_tar(path, items)


class GroupedMTLRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name)
        self.root = base / "nepal-2026-before-after-map-data"
        self.downloads = base / "Downloads"
        self.root.mkdir()
        self.downloads.mkdir()
        self.before = recovery.paths(self.root, self.downloads, "before")
        self.after = recovery.paths(self.root, self.downloads, "after")
        self.preserved = self.root / recovery.PRESERVED_BEFORE_REL
        self.preserved.parent.mkdir(parents=True)
        self.gate = {"status": "pass_final_no_content_preflight",
                     "approval_sha256": recovery.APPROVAL_SHA256,
                     "public_ci_commit": "a" * 40,
                     "public_ci_run_id": "12345678",
                     "public_ci_conclusion": "success",
                     "preflight_sha256": "b" * 64}

    def make_preserved(self, *, wrong_scene: bool = False) -> tuple[int, str]:
        synthetic_bundle(self.preserved, self.before.product_id, self.before.scene_id,
                         wrong_scene=wrong_scene)
        data = self.preserved.read_bytes()
        return len(data), hashlib.sha256(data).hexdigest()

    def reserved_before(self, *, wrong_scene: bool = False) -> tuple[int, str]:
        size, digest = self.make_preserved(wrong_scene=wrong_scene)
        recovery.reserve(self.before, self.root, self.gate)
        return size, digest

    def run_before(self, *, wrong_scene: bool = False) -> dict:
        size, digest = self.reserved_before(wrong_scene=wrong_scene)
        with (patch.object(recovery, "PRESERVED_BEFORE_SIZE", size),
              patch.object(recovery, "PRESERVED_BEFORE_SHA256", digest)):
            return recovery.complete_before_preserved(self.before, self.root)

    def before_pass(self) -> dict:
        terminal = self.run_before()
        self.assertEqual(terminal["status"], "pass_bundle_promoted_container_only")
        return terminal

    def test_preserved_source_passes_no_replace_and_is_not_mutated(self) -> None:
        terminal = self.before_pass()
        self.assertEqual(terminal["sha256"], hashlib.sha256(self.preserved.read_bytes()).hexdigest())
        self.assertEqual(self.before.destination.read_bytes(), self.preserved.read_bytes())
        self.assertTrue(self.preserved.is_file())
        self.assertFalse(self.before.staging.exists())
        self.assertTrue((self.before.attempt_dir / "cleanup.json").is_file())
        with self.assertRaisesRegex(recovery.RecoveryError, "attempt_already_terminal"):
            recovery.complete_before_preserved(self.before, self.root)

    def test_wrong_grouped_identity_is_terminal_and_preserves_staging(self) -> None:
        terminal = self.run_before(wrong_scene=True)
        self.assertEqual(terminal["failure_code"], "mtl_level2_or_scene_identity_mismatch")
        self.assertTrue(self.before.staging.is_file())
        self.assertFalse(self.before.destination.exists())
        self.assertTrue((self.before.attempt_dir / "terminal.json").is_file())

    def test_preserved_source_drift_stops_before_copy(self) -> None:
        size, digest = self.reserved_before()
        with (patch.object(recovery, "PRESERVED_BEFORE_SIZE", size),
              patch.object(recovery, "PRESERVED_BEFORE_SHA256", "0" * 64)):
            terminal = recovery.complete_before_preserved(self.before, self.root)
        self.assertEqual(terminal["failure_code"], "preserved_source_digest_or_metadata_mismatch")
        self.assertFalse(self.before.staging.exists())
        self.assertFalse(self.before.destination.exists())

    def test_collision_blocks_before_reservation(self) -> None:
        self.before.destination.parent.mkdir(parents=True)
        self.before.destination.write_bytes(b"existing")
        with self.assertRaisesRegex(recovery.RecoveryError, "destination_collision"):
            recovery.reserve(self.before, self.root, self.gate)
        self.assertFalse(self.before.attempt_dir.exists())

    def test_interrupted_receipt_is_terminal_and_secret_safe(self) -> None:
        size, digest = self.reserved_before()
        actual_write = recovery.write_new_json

        def fail_staged(path: Path, value: dict) -> None:
            if path.name == "staged.json":
                raise OSError("private token signed URL account")
            actual_write(path, value)

        with (patch.object(recovery, "PRESERVED_BEFORE_SIZE", size),
              patch.object(recovery, "PRESERVED_BEFORE_SHA256", digest),
              patch.object(recovery, "write_new_json", side_effect=fail_staged)):
            terminal = recovery.complete_before_preserved(self.before, self.root)
        self.assertEqual(terminal["failure_code"], "local_recovery_io_or_unexpected_failure")
        self.assertFalse(self.before.destination.exists())
        self.assertTrue((self.before.attempt_dir / "cleanup.json").is_file())
        for receipt in self.before.attempt_dir.glob("*.json"):
            body = receipt.read_text(encoding="utf-8")
            self.assertNotIn("private token", body)
            self.assertNotIn(str(self.root), body)

    def test_terminal_write_failure_uses_append_only_fallback(self) -> None:
        size, digest = self.reserved_before()
        actual_write = recovery.write_new_json

        def fail_terminal(path: Path, value: dict) -> None:
            if path.name == "terminal.json":
                raise OSError("private terminal path and secret")
            actual_write(path, value)

        with (patch.object(recovery, "PRESERVED_BEFORE_SIZE", size),
              patch.object(recovery, "PRESERVED_BEFORE_SHA256", digest),
              patch.object(recovery, "write_new_json", side_effect=fail_terminal)):
            terminal = recovery.complete_before_preserved(self.before, self.root)
        self.assertEqual(terminal["status"], "block_terminal_receipt_persistence_failure")
        self.assertTrue((self.before.attempt_dir / "terminal-fallback.json").is_file())
        self.assertTrue((self.before.attempt_dir / "cleanup.json").is_file())
        self.assertNotIn("private terminal", json.dumps(terminal))
        with self.assertRaisesRegex(recovery.RecoveryError, "attempt_already_terminal"):
            recovery.complete_before_preserved(self.before, self.root)

    def test_after_exact_file_and_duplicate_mismatch(self) -> None:
        before_terminal = self.before_pass()
        recovery.reserve(self.after, self.root, self.gate)
        recovery.mark_after_click(self.after, before_terminal)
        synthetic_bundle(self.after.base_file, self.after.product_id, self.after.scene_id)
        self.after.numbered_file.write_bytes(b"different")
        stamps = recovery.source_stamps(self.after, self.downloads)
        terminal = recovery.complete(self.after, self.root, self.downloads, stamps)
        self.assertEqual(terminal["failure_code"], "duplicate_hash_mismatch")
        self.assertFalse(self.after.destination.exists())

    def test_after_one_exact_file_passes_container_only(self) -> None:
        before_terminal = self.before_pass()
        recovery.reserve(self.after, self.root, self.gate)
        recovery.mark_after_click(self.after, before_terminal)
        synthetic_bundle(self.after.base_file, self.after.product_id, self.after.scene_id)
        terminal = recovery.complete(self.after, self.root, self.downloads,
                                     recovery.source_stamps(self.after, self.downloads))
        self.assertEqual(terminal["status"], "pass_bundle_promoted_container_only")
        self.assertEqual(terminal["source_count"], 1)
        self.assertTrue(self.after.base_file.is_file())

    def test_after_requires_unchanged_full_before_hash(self) -> None:
        before_terminal = self.before_pass()
        changed = bytearray(self.before.destination.read_bytes())
        changed[100] ^= 1
        self.before.destination.write_bytes(changed)
        self.assertEqual(self.before.destination.stat().st_size, before_terminal["size_bytes"])
        recovery.reserve(self.after, self.root, self.gate)
        with self.assertRaisesRegex(recovery.RecoveryError, "before_promoted_file_missing_or_changed"):
            recovery.mark_after_click(self.after, before_terminal)
        self.assertFalse((self.after.attempt_dir / "browser-click-started.json").exists())

    def test_gate_and_monitor_timeout(self) -> None:
        with self.assertRaisesRegex(recovery.RecoveryError, "execution_gate_invalid"):
            recovery.reserve(self.before, self.root, self.gate | {"public_ci_conclusion": "failure"})
        prior = self.before_pass()
        recovery.reserve(self.after, self.root, self.gate)
        recovery.mark_after_click(self.after, prior)
        ticks = iter((0, 1, 2, 3))
        with self.assertRaisesRegex(recovery.RecoveryError, "after_arrival_timeout_or_incomplete"):
            recovery.wait_for_after(self.after, clock=lambda: next(ticks), pause=lambda _s: None,
                                    limit_seconds=2, stable_seconds=1)
        terminal = recovery.record_after_failure(self.after, "after_arrival_timeout_or_incomplete")
        self.assertEqual(terminal["status"], "block_after_browser_or_monitor_failure")


if __name__ == "__main__":
    unittest.main()
