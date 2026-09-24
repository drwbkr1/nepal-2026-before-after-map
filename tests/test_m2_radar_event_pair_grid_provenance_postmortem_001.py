"""Disposable replay of the consumed grid diagnostic's receipt failure path."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_m2_radar_event_pair_grid_provenance_diagnostic_001 as runner  # noqa: E402
from m2_radar_event_pair_grid_provenance_diagnostic_001_core import DiagnosticError, load_json  # noqa: E402


class GridDiagnosticReceiptPostmortemTests(unittest.TestCase):
    def test_configuration_ambiguity_path_persists_all_four_receipts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nepal-grid-receipt-postmortem-") as temp:
            base = Path(temp)
            fake_arcgis = SimpleNamespace(GetInstallInfo=lambda: {"Version": "synthetic"})
            names = [base / f"synthetic-{index}.crf" for index in range(5)]
            with (
                patch.object(runner, "_require_preflight", lambda: None),
                patch.object(runner, "STARTED", base / "started.json"),
                patch.object(runner, "TERMINAL", base / "terminal.json"),
                patch.object(runner, "CLEANUP", base / "cleanup.json"),
                patch.object(runner, "ERROR", base / "error.json"),
                patch.object(runner, "candidate_paths", lambda: names),
                patch.object(runner, "inspect_raster", lambda arcpy, path: {"name": path.name, "raster": {"wkid": 4326,
                                     "cell_size_x": 10.0, "cell_size_y": 10.0}}),
                patch.object(runner, "verify_gtc_configuration", side_effect=DiagnosticError("gtc_configuration_count_ambiguous")),
                patch.dict(sys.modules, {"arcpy": fake_arcgis}),
            ):
                result = runner.execute()
            self.assertEqual(result["status"], "block_read_only_metadata_diagnostic_no_retry")
            self.assertEqual(load_json(base / "error.json")["failure_code"], "gtc_configuration_count_ambiguous")
            self.assertEqual(load_json(base / "terminal.json")["status"], "block_read_only_metadata_diagnostic_no_retry")
            self.assertEqual(load_json(base / "cleanup.json")["status"], "pass_read_only_no_temporary_payload_created")
            self.assertTrue((base / "started.json").stat().st_size > 0)

    def test_terminal_write_failure_leaves_cleanup_unwritten(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nepal-grid-receipt-failure-") as temp:
            base = Path(temp)
            opened = []
            original_reserve = runner.reserve
            original_persist = runner.persist

            def reserve_tracked(path):
                stream = original_reserve(path)
                opened.append(stream)
                return stream

            def persist_with_terminal_failure(stream, value):
                if Path(stream.name).name == "terminal.json":
                    raise OSError("synthetic_terminal_write_failure")
                original_persist(stream, value)

            with (
                patch.object(runner, "_require_preflight", lambda: None),
                patch.object(runner, "STARTED", base / "started.json"),
                patch.object(runner, "TERMINAL", base / "terminal.json"),
                patch.object(runner, "CLEANUP", base / "cleanup.json"),
                patch.object(runner, "ERROR", base / "error.json"),
                patch.object(runner, "candidate_paths", lambda: []),
                patch.object(runner, "verify_gtc_configuration", side_effect=DiagnosticError("gtc_configuration_count_ambiguous")),
                patch.object(runner, "reserve", reserve_tracked),
                patch.object(runner, "persist", persist_with_terminal_failure),
                patch.dict(sys.modules, {"arcpy": SimpleNamespace(GetInstallInfo=lambda: {"Version": "synthetic"})}),
            ):
                try:
                    with self.assertRaisesRegex(OSError, "synthetic_terminal_write_failure"):
                        runner.execute()
                finally:
                    for stream in opened:
                        if not stream.closed:
                            stream.close()
            self.assertEqual(load_json(base / "error.json")["failure_code"], "gtc_configuration_count_ambiguous")
            self.assertEqual((base / "terminal.json").stat().st_size, 0)
            self.assertEqual((base / "cleanup.json").stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
