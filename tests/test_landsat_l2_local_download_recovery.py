from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import landsat_l2_local_download_recovery as recovery  # noqa: E402
from tests.test_landsat_l2_bundle_integrity import fixtures, write_tar  # noqa: E402


class LocalDownloadRecoveryTests(unittest.TestCase):
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
        self.gate = {
            "status": "pass_final_no_payload_preflight",
            "approval_sha256": recovery.APPROVAL_SHA256,
            "public_ci_commit": "a" * 40,
            "public_ci_run_id": "12345678",
            "public_ci_conclusion": "success",
            "preflight_sha256": "b" * 64,
        }

    def bundle(self, p: recovery.Paths, *, duplicate: bool = False) -> None:
        write_tar(p.base_file, fixtures(p.product_id, p.scene_id))
        if duplicate:
            p.numbered_file.write_bytes(p.base_file.read_bytes())

    def reserve(self, p: recovery.Paths) -> None:
        recovery.reserve(p, self.root, self.gate)

    def before_pass(self) -> dict:
        self.before.destination.parent.mkdir(parents=True, exist_ok=True)
        self.before.destination.write_bytes(b"promoted synthetic before")
        return {"status": "pass_bundle_promoted_container_only",
                "attempt_id": self.before.attempt_id,
                "size_bytes": self.before.destination.stat().st_size}

    def test_before_matching_duplicates_promote_without_touching_originals(self) -> None:
        self.bundle(self.before, duplicate=True)
        stamps = recovery.source_stamps(self.before, self.downloads)
        self.reserve(self.before)
        terminal = recovery.complete(self.before, self.root, self.downloads, stamps)
        self.assertEqual(terminal["status"], "pass_bundle_promoted_container_only")
        self.assertEqual(terminal["source_count"], 2)
        self.assertTrue(terminal["local_duplicate_sha256_agreed"])
        self.assertEqual(self.before.destination.read_bytes(), self.before.base_file.read_bytes())
        self.assertTrue(self.before.numbered_file.is_file())
        self.assertTrue((self.before.attempt_dir / "cleanup.json").is_file())
        with self.assertRaisesRegex(recovery.RecoveryError, "attempt_already_terminal"):
            recovery.complete(self.before, self.root, self.downloads, stamps)

    def test_before_mismatch_is_terminal_and_after_not_released(self) -> None:
        self.bundle(self.before, duplicate=True)
        with self.before.numbered_file.open("ab") as target:
            target.write(b"different")
        stamps = recovery.source_stamps(self.before, self.downloads)
        self.reserve(self.before)
        terminal = recovery.complete(self.before, self.root, self.downloads, stamps)
        self.assertEqual(terminal["failure_code"], "duplicate_hash_mismatch")
        self.assertFalse(self.before.destination.exists())
        self.reserve(self.after)
        with self.assertRaisesRegex(recovery.RecoveryError, "before_dependency_not_promoted"):
            recovery.mark_after_click(self.after, terminal)

    def test_before_source_mutation_after_preflight_is_terminal(self) -> None:
        self.bundle(self.before, duplicate=True)
        stamps = recovery.source_stamps(self.before, self.downloads)
        self.before.numbered_file.write_bytes(b"changed")
        self.reserve(self.before)
        terminal = recovery.complete(self.before, self.root, self.downloads, stamps)
        self.assertEqual(terminal["failure_code"], "source_metadata_or_identity_changed")
        self.assertFalse(self.before.destination.exists())

    def test_unsafe_link_and_destination_collision_stop_before_read(self) -> None:
        self.bundle(self.before)
        try:
            self.before.numbered_file.symlink_to(self.before.base_file)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable")
        with self.assertRaisesRegex(recovery.RecoveryError, "source_reparse_or_symlink"):
            recovery.source_stamps(self.before, self.downloads)
        self.before.numbered_file.unlink()
        self.before.destination.parent.mkdir(parents=True)
        self.before.destination.write_bytes(b"existing")
        with self.assertRaisesRegex(recovery.RecoveryError, "destination_collision"):
            self.reserve(self.before)
        self.assertFalse(self.before.attempt_dir.exists())

    def test_after_one_file_is_allowed_and_no_second_click_marker(self) -> None:
        self.reserve(self.after)
        recovery.mark_after_click(self.after, self.before_pass())
        self.bundle(self.after)
        stamps = recovery.source_stamps(self.after, self.downloads)
        terminal = recovery.complete(self.after, self.root, self.downloads, stamps)
        self.assertEqual(terminal["status"], "pass_bundle_promoted_container_only")
        self.assertEqual(terminal["source_count"], 1)
        with self.assertRaisesRegex(recovery.RecoveryError, "attempt_already_terminal"):
            recovery.mark_after_click(self.after, self.before_pass())

    def test_after_matching_two_files_allowed(self) -> None:
        self.reserve(self.after)
        recovery.mark_after_click(self.after, self.before_pass())
        self.bundle(self.after, duplicate=True)
        stamps = recovery.source_stamps(self.after, self.downloads)
        self.assertEqual(recovery.complete(self.after, self.root, self.downloads, stamps)["status"],
                         "pass_bundle_promoted_container_only")

    def test_after_duplicate_mismatch_stops_without_promotion(self) -> None:
        self.reserve(self.after)
        recovery.mark_after_click(self.after, self.before_pass())
        self.bundle(self.after, duplicate=True)
        with self.after.numbered_file.open("ab") as target:
            target.write(b"different")
        stamps = recovery.source_stamps(self.after, self.downloads)
        terminal = recovery.complete(self.after, self.root, self.downloads, stamps)
        self.assertEqual(terminal["failure_code"], "duplicate_hash_mismatch")
        self.assertFalse(self.after.destination.exists())

    def test_staged_receipt_failure_still_writes_terminal_and_cleanup(self) -> None:
        self.bundle(self.before, duplicate=True)
        stamps = recovery.source_stamps(self.before, self.downloads)
        self.reserve(self.before)
        original_write = recovery.write_new_json

        def fail_staged(path: Path, value: dict) -> None:
            if path.name == "staged.json":
                raise OSError("private path must stay hidden")
            original_write(path, value)

        with patch.object(recovery, "write_new_json", side_effect=fail_staged):
            terminal = recovery.complete(self.before, self.root, self.downloads, stamps)
        self.assertEqual(terminal["failure_code"], "local_recovery_io_or_unexpected_failure")
        self.assertTrue((self.before.attempt_dir / "terminal.json").is_file())
        self.assertTrue((self.before.attempt_dir / "cleanup.json").is_file())
        self.assertNotIn("private path", (self.before.attempt_dir / "terminal.json").read_text())

    def test_partial_download_blocks_complete(self) -> None:
        self.reserve(self.after)
        recovery.mark_after_click(self.after, self.before_pass())
        self.bundle(self.after)
        stamps = recovery.source_stamps(self.after, self.downloads)
        (self.downloads / (self.after.base_file.name + ".crdownload")).write_bytes(b"partial")
        terminal = recovery.complete(self.after, self.root, self.downloads, stamps)
        self.assertEqual(terminal["failure_code"], "output_ambiguous_or_incomplete")
        self.assertFalse(self.after.destination.exists())

    def test_interrupted_copy_is_terminal_with_secret_safe_receipts(self) -> None:
        self.bundle(self.before, duplicate=True)
        stamps = recovery.source_stamps(self.before, self.downloads)
        self.reserve(self.before)

        def interrupt(*_args):
            self.before.staging.write_bytes(b"partial")
            raise OSError("private account token and signed URL")

        with patch.object(recovery, "_copy_stable", side_effect=interrupt):
            terminal = recovery.complete(self.before, self.root, self.downloads, stamps)
        self.assertEqual(terminal["failure_code"], "local_recovery_io_or_unexpected_failure")
        self.assertTrue(self.before.staging.is_file())
        for receipt in self.before.attempt_dir.glob("*.json"):
            body = receipt.read_text(encoding="utf-8")
            self.assertNotIn("private account", body)
            self.assertNotIn(str(self.downloads), body)

    def test_wrong_container_identity_blocks_and_retains_staging(self) -> None:
        write_tar(self.before.base_file, fixtures(self.before.product_id, self.after.scene_id))
        self.before.numbered_file.write_bytes(self.before.base_file.read_bytes())
        stamps = recovery.source_stamps(self.before, self.downloads)
        self.reserve(self.before)
        terminal = recovery.complete(self.before, self.root, self.downloads, stamps)
        self.assertEqual(terminal["failure_code"], "mtl_text_identity_mismatch")
        self.assertTrue(self.before.staging.is_file())

    def test_gate_and_monitor_bounds(self) -> None:
        with self.assertRaisesRegex(recovery.RecoveryError, "execution_gate_invalid"):
            recovery.reserve(self.before, self.root, self.gate | {"public_ci_conclusion": "failure"})
        self.reserve(self.after)
        recovery.mark_after_click(self.after, self.before_pass())
        ticks = iter((0, 1, 2, 3))
        with self.assertRaisesRegex(recovery.RecoveryError, "after_arrival_timeout_or_incomplete"):
            recovery.wait_for_after(self.after, clock=lambda: next(ticks), pause=lambda _s: None,
                                    limit_seconds=2, stable_seconds=1)
        terminal = recovery.record_after_failure(self.after, "after_arrival_timeout_or_incomplete")
        self.assertEqual(terminal["status"], "block_after_browser_or_monitor_failure")
        self.assertEqual(json.loads((self.after.attempt_dir / "terminal.json").read_text())["failure_code"],
                         "after_arrival_timeout_or_incomplete")


if __name__ == "__main__":
    unittest.main()
