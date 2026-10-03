import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_m2_landsat9_pixel_visual_recovery_001 as recovery


class LandsatRecoverySupervisorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.attempt = self.root / "attempt"
        self.events = self.root / "events"
        self.fallback = self.root / "fallback"
        self.gate = self.root / "gate.json"
        recovery.write_new(self.gate, {
            "status": "pass_final_no_content_preflight",
            "approval_sha256": recovery.APPROVAL_SHA,
            "recovery_approval_sha256": recovery.APPROVAL_SHA,
            "recovery_attempt_root_absent": True,
            "independent_event_roots_absent": True,
            "implementation_public_ci_commit": "a" * 40,
            "implementation_public_ci_run_id": "12345678"})
        self.calls = 0

    def successful_worker(self, gate):
        self.calls += 1
        self.assertTrue((self.events / "intent.json").is_file())
        self.assertTrue((self.fallback / "ready.json").is_file())
        self.attempt.mkdir()
        recovery.write_new(self.attempt / "terminal.json", {
            "status": "pass_pixel_qa_visual_only_no_panel_qualified"})
        return 0

    def run_supervisor(self, worker=None, **kwargs):
        return recovery.supervise(self.gate, attempt=self.attempt, events=self.events,
                                  fallback=self.fallback,
                                  worker=worker or self.successful_worker, **kwargs)

    def test_reservation_failure_after_directory_creation_seals_terminal(self):
        original = recovery.write_new
        def fail_intent(path, payload):
            if path.name == "intent.json":
                raise PermissionError("synthetic_secret_do_not_record")
            return original(path, payload)
        with patch.object(recovery, "write_new", side_effect=fail_intent):
            result = self.run_supervisor()
        self.assertEqual(self.calls, 0)
        self.assertFalse(self.attempt.exists())
        self.assertEqual(result["worker_invocations"], 0)
        self.assertTrue((self.events / "terminal.json").is_file())
        self.assertTrue((self.events / "cleanup.json").is_file())

    def test_interruption_after_intent_stops_before_worker_and_hides_secret(self):
        def interruption():
            raise RuntimeError("synthetic_secret_do_not_record")
        result = self.run_supervisor(after_intent=interruption)
        receipts = "".join(p.read_text() for p in self.root.rglob("*.json"))
        self.assertNotIn("synthetic_secret_do_not_record", receipts)
        self.assertEqual(result["worker_invocations"], 0)
        self.assertFalse(self.attempt.exists())

    def test_crash_before_started_receipt_is_terminal_without_retry(self):
        def crash(gate):
            self.calls += 1
            self.attempt.mkdir()
            raise RuntimeError("synthetic_secret_do_not_record")
        result = self.run_supervisor(crash)
        terminal = json.loads((self.events / "terminal.json").read_text())
        self.assertEqual(self.calls, 1)
        self.assertEqual(terminal["exception_class"], "RuntimeError")
        self.assertFalse(terminal["worker_started_receipt_present"])
        self.assertEqual(result["status"], "blocked_terminal_no_retry")
        self.assertEqual(terminal["automatic_retries"], 0)

    def test_primary_terminal_failure_uses_independent_fallback(self):
        original = recovery.write_new
        def fail_primary(path, payload):
            if path == self.events / "terminal.json":
                raise OSError("synthetic_error")
            return original(path, payload)
        with patch.object(recovery, "write_new", side_effect=fail_primary):
            result = self.run_supervisor()
        self.assertEqual(result["terminal_receipt_location"], "fallback")
        self.assertTrue(result["cleanup_receipt_persisted"])
        self.assertEqual(self.calls, 1)

    def test_both_terminal_paths_fail_but_cleanup_is_independent(self):
        original = recovery.write_new
        def fail_terminals(path, payload):
            if path.name == "terminal.json" and path.parent in (self.events, self.fallback):
                raise OSError("synthetic_error")
            return original(path, payload)
        with patch.object(recovery, "write_new", side_effect=fail_terminals):
            result = self.run_supervisor()
        self.assertEqual(result["status"], "block_supervisor_receipt_persistence_failure")
        self.assertIsNone(result["terminal_receipt_sha256"])
        self.assertTrue(result["cleanup_receipt_persisted"])
        self.assertEqual(self.calls, 1)

    def test_fallback_reservation_failure_prevents_worker(self):
        original = recovery.write_new
        def fail_ready(path, payload):
            if path.name == "ready.json":
                raise OSError("synthetic_error")
            return original(path, payload)
        with patch.object(recovery, "write_new", side_effect=fail_ready):
            result = self.run_supervisor()
        self.assertEqual(result["worker_invocations"], 0)
        self.assertFalse(self.attempt.exists())

    def test_no_replace_collision_preserves_existing_evidence(self):
        self.events.mkdir()
        sentinel = self.events / "sentinel"
        sentinel.write_bytes(b"preserved")
        with self.assertRaises(recovery.frozen.RouteStop):
            self.run_supervisor()
        self.assertEqual(sentinel.read_bytes(), b"preserved")
        self.assertEqual(self.calls, 0)

    def test_partial_flush_failure_cannot_overwrite_reserved_receipt(self):
        path = self.root / "reserved.json"
        with patch.object(recovery.os, "fsync", side_effect=OSError("synthetic_error")):
            with self.assertRaises(OSError):
                recovery.write_new(path, {"first": True})
        preserved = path.read_bytes()
        with self.assertRaises(FileExistsError):
            recovery.write_new(path, {"second": True})
        self.assertEqual(path.read_bytes(), preserved)

    def test_unchecked_worker_status_and_exception_text_never_escape(self):
        def unsafe(gate):
            self.calls += 1
            self.attempt.mkdir()
            recovery.write_new(self.attempt / "terminal.json", {"status": "synthetic_secret_status"})
            return 0
        result = self.run_supervisor(unsafe)
        supervisor_receipts = "".join(p.read_text() for p in self.events.glob("*.json"))
        self.assertNotIn("synthetic_secret_status", supervisor_receipts)
        self.assertEqual(result["status"], "blocked_terminal_no_retry")
        self.assertEqual(recovery.safe_exception(ValueError("secret")), "UnclassifiedError")

    def test_nonzero_worker_cannot_claim_pass(self):
        def inconsistent(gate):
            self.successful_worker(gate)
            return 20
        result = self.run_supervisor(inconsistent)
        self.assertEqual(result["status"], "blocked_terminal_no_retry")

    def test_fixed_source_order_first_failure_stops_before_pixels(self):
        prior = self.root / "consumed-real-001"
        prior.mkdir()
        saved_root = recovery.frozen.ATTEMPT
        order = []
        self.events.mkdir()
        def extract(role, root):
            order.append(role)
            if role == "after":
                raise recovery.frozen.RouteStop("synthetic_after_integrity_failure")
            return {}
        with recovery.bind_controls(self.attempt), \
             patch.object(recovery.frozen, "_check_controls"), \
             patch.object(recovery.frozen, "extract_exact", side_effect=extract), \
             patch.object(recovery.frozen, "mtl_fields", return_value={}), \
             patch.object(recovery.frozen, "raster_headers", return_value={}), \
             patch.object(recovery.frozen, "validate_headers", return_value={}), \
             patch.object(recovery.frozen, "read_aoi_date") as pixels, \
             recovery.worker_stage_markers(self.events):
            result = recovery.frozen.run_once(json.loads(self.gate.read_text()), None)
        self.assertEqual(order, ["before", "after"])
        pixels.assert_not_called()
        self.assertEqual(result["status"], "blocked_terminal_no_retry")
        stages = [json.loads(p.read_text())["stage"] for p in sorted(self.events.glob("stage-*.json"))]
        self.assertEqual(stages, ["before_materialization", "before_headers", "after_materialization",
                                  "terminal_error_routestop"])
        self.assertEqual(list(prior.iterdir()), [])
        self.assertEqual(recovery.frozen.ATTEMPT, saved_root)

    def test_failed_started_receipt_prevents_any_content(self):
        self.events.mkdir()
        original = recovery.write_new
        def fail_started(path, payload):
            if path == self.attempt / "started.json":
                raise OSError("synthetic_error")
            return original(path, payload)
        with recovery.bind_controls(self.attempt), \
             patch.object(recovery.frozen, "_check_controls"), \
             patch.object(recovery.frozen, "extract_exact") as extract, \
             patch.object(recovery, "write_new", side_effect=fail_started), \
             recovery.worker_stage_markers(self.events):
            result = recovery.frozen.run_once(json.loads(self.gate.read_text()), None)
        extract.assert_not_called()
        self.assertEqual(result["status"], "block_reservation_receipt_persistence_failure")
        self.assertTrue((self.attempt / "terminal-fallback.json").is_file())

    def test_only_fixed_worker_codes_are_preserved(self):
        self.assertEqual(recovery.safe_worker_code(recovery.frozen.RouteStop("cross_scene_lattice_mismatch")),
                         "cross_scene_lattice_mismatch")
        self.assertEqual(recovery.safe_worker_code(recovery.frozen.RouteStop("synthetic_secret_status")),
                         "local_io_or_unexpected_failure")


if __name__ == "__main__":
    unittest.main()
