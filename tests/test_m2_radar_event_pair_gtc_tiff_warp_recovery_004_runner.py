"""Source-free route, authority, and terminal stops for recovery-004."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import m2_radar_event_pair_gtc_tiff_warp_recovery_004 as runner  # noqa: E402


class RunnerTests(unittest.TestCase):
    def test_exact_packet_authority_and_new_attempt_identity(self):
        footprint = runner.verify_authority()
        self.assertEqual(footprint["status"], "pass_full_actual_sar_footprints_have_valid_dem")
        self.assertEqual(runner.ATTEMPT_ROOT.parts[-2:], ("e1", "a3"))
        self.assertEqual(runner.PREFIX, "m2-radar-event-area-pair-gtc-tiff-warp-recovery-004")

    def test_fixed_order_hard_stops_before_second_source(self):
        calls = []

        def failed(source_id):
            calls.append(source_id)
            return {"source_id": source_id, "status": "failed_source_execution_no_retry"}

        self.assertEqual(len(runner.source_sequence(failed)), 1)
        self.assertEqual(calls, ["M1-SRC-002"])

    def test_unpublished_implementation_gate_blocks_no_content_preflight(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing-gate.json"
            with patch.object(runner, "IMPLEMENTATION_GATE", missing):
                with self.assertRaises(FileNotFoundError):
                    runner.no_content_preflight(None)

    def test_no_supervisor_reservation_blocks_worker(self):
        with patch.dict(runner.os.environ, {"NEPAL_RECOVERY_004_WORKER": "1"}):
            with self.assertRaisesRegex(Exception, "recovery_004_worker_requires_supervisor"):
                runner.run_one(reserved_by_supervisor=False)


if __name__ == "__main__":
    unittest.main()
