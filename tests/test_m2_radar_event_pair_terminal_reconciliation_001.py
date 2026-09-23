"""Sanitized append-only terminal reconciliation tests without project data."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import reconcile_m2_radar_event_pair_terminal_001 as module  # noqa: E402
from m2_dem_vertical_datum_proj25_core import sha256_file  # noqa: E402
from m2_radar_event_pair_dem_intake_001 import IntakeError  # noqa: E402


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")


class TerminalReconciliationTests(unittest.TestCase):
    def test_failed_first_source_is_sanitized_and_no_route_claimed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            attempt = Path(directory) / "a1"
            ref = "receipts/sources/m1-src-002-terminal.json"
            receipt = attempt / ref
            write(receipt, {"source_id": "M1-SRC-002", "status": "failed_source_execution_no_retry", "failure_code": "synthetic_tool_failure", "failure_message": "private path"})
            write(attempt / "terminal.json", {
                "status": "stopped_on_first_source_failure_no_retry", "automatic_retry_performed": False,
                "baseline_or_change_analysis_executed": False, "derived_pixel_publication_authorized": False,
                "external_custody_unchanged": True,
                "source_results": [{"source_id": "M1-SRC-002", "status": "failed_source_execution_no_retry", "receipt_ref": ref, "receipt_sha256": sha256_file(receipt)}],
                "route": None,
            })
            write(attempt / "cleanup.json", {"status": "extension_checkin_attempted_outputs_preserved"})
            fake_identities = {"sources": {"M1-SRC-002": {"inventory_sha256": "a" * 64}}, "mosaic": "b" * 64}
            with (patch.object(module, "ATTEMPT_ROOT", attempt),
                  patch.object(module, "OUTPUT", Path(directory) / "not-created.json"),
                  patch.object(module, "event_plan", return_value={}),
                  patch.object(module, "verify_input_identities", return_value=fake_identities)):
                result = module.reconcile_terminal()
            self.assertEqual(result["status"], "stopped_on_first_source_failure_no_retry")
            self.assertEqual(result["source_results"][0]["failure_code"], "synthetic_tool_failure")
            self.assertNotIn("private path", json.dumps(result))
            self.assertIsNone(result["route"])

    def test_missing_durable_terminal_is_not_reconstructed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(module, "ATTEMPT_ROOT", Path(directory)), patch.object(module, "OUTPUT", Path(directory) / "not-created.json"):
                with self.assertRaisesRegex(IntakeError, "radar_terminal_or_cleanup_not_durable"):
                    module.reconcile_terminal()


if __name__ == "__main__":
    unittest.main()
