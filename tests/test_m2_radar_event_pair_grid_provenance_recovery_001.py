"""Portable safety and durability tests for the distinct grid recovery."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import m2_radar_event_pair_grid_provenance_recovery_001_core as core  # noqa: E402
import run_m2_radar_event_pair_grid_provenance_recovery_001 as runner  # noqa: E402


class RecoveryTests(unittest.TestCase):
    def test_inventory_unique_missing_ambiguous_and_unsafe(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            gtc = root / "gamma0_linear_gtc_raw.crf"
            gtc.mkdir()
            payload = b"disposable-config"
            (gtc / "a.conf").write_bytes(payload)
            expected = hashlib.sha256(payload).hexdigest()
            found = core.inventory_gtc_configuration(gtc, root=root, expected_sha256=expected)
            self.assertEqual(found["historical_configuration_identity"], "unique_match")
            self.assertEqual(found["configuration_candidates_hashed"], 1)
            missing = core.inventory_gtc_configuration(gtc, root=root, expected_sha256="0" * 64)
            self.assertEqual(missing["historical_configuration_identity"], "unresolved_no_match_or_ambiguous")
            (gtc / "b.aux.xml").write_bytes(payload)
            ambiguous = core.inventory_gtc_configuration(gtc, root=root, expected_sha256=expected)
            self.assertEqual(ambiguous["matching_historical_configuration_count"], 2)
            with self.assertRaisesRegex(core.DiagnosticError, "configuration_root_not_exact_gtc"):
                core.inventory_gtc_configuration(root, root=root)
            outside = root / "outside"
            outside.mkdir()
            try:
                (gtc / "link").symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                pass
            else:
                with self.assertRaisesRegex(core.DiagnosticError, "gtc_directory_entry_unsafe"):
                    core.inventory_gtc_configuration(gtc, root=root)

    def test_inventory_bounds_before_hashing_oversized(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            gtc = root / "gamma0_linear_gtc_raw.crf"
            gtc.mkdir()
            with (gtc / "oversized.json").open("wb") as stream:
                stream.truncate(core.MAX_CANDIDATE_BYTES + 1)
            with self.assertRaisesRegex(core.DiagnosticError, "gtc_configuration_candidate_oversized"):
                core.inventory_gtc_configuration(gtc, root=root)
            with patch.object(core, "MAX_ENTRIES", 0):
                with self.assertRaisesRegex(core.DiagnosticError, "gtc_directory_entry_bound_exceeded"):
                    core.inventory_gtc_configuration(gtc, root=root)

    def _run_disposable(self, base: Path, *, interruption: bool = False,
                        terminal_failure: bool = False) -> dict:
        receipt_paths = {name: base / f"{name}.json" for name in runner.RECEIPTS}
        receipt_paths["stage-journal"] = base / "stage-journal.jsonl"
        paths = [base / name for name in core.NAMES]
        calls: list[str] = []

        def inspect(arcpy, path):
            calls.append(path.name)
            if interruption and len(calls) == 3:
                raise core.DiagnosticError("synthetic_interruption")
            return {"name": path.name, "raster": {"wkid": 4326, "cell_size_x": 0.01,
                    "cell_size_y": 0.01, "width": 2, "height": 2,
                    "band_count": 1, "bounds": [0.0, 0.0, 0.02, 0.02]}}

        original_write = runner._write_once

        def write(stream, value):
            if terminal_failure and Path(stream.name).name == "terminal.json":
                raise OSError("synthetic_terminal_write_failure")
            original_write(stream, value)

        with (
            patch.object(runner, "_require_preflight", lambda: None),
            patch.object(runner, "RECEIPTS", receipt_paths),
            patch.object(runner, "PREFLIGHT", base / "synthetic-preflight.json"),
            patch.object(runner, "candidate_paths", lambda: paths),
            patch.object(runner, "inspect_raster", inspect),
            patch.object(runner, "inventory_gtc_configuration", lambda path: {
                "historical_configuration_identity": "unique_match", "matching_historical_configuration_count": 1}),
            patch.object(runner, "_write_once", write),
            patch.object(runner, "sha256_file", lambda path: "synthetic-sha256"),
            patch.dict(sys.modules, {"arcpy": SimpleNamespace(GetInstallInfo=lambda: {"Version": "synthetic"})}),
        ):
            result = runner.execute()
        stages = [json.loads(line) for line in receipt_paths["stage-journal"].read_text().splitlines()]
        self.assertEqual([x["name"] for x in stages if x["stage"] == "raster_metadata_started"], calls)
        self.assertEqual(len([x for x in stages if x["stage"] == "raster_metadata_completed"]),
                         2 if interruption else 5)
        self.assertEqual(json.loads(receipt_paths["cleanup"].read_text())["status"],
                         "pass_read_only_no_temporary_payload_created")
        with self.assertRaises(FileExistsError):
            core.reserve(receipt_paths["terminal"])
        return result

    def test_exact_order_and_per_stage_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = self._run_disposable(Path(temp))
            self.assertEqual(result["status"], "diagnostic_complete_metadata_only")

    def test_interruption_retains_prior_stages_and_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            result = self._run_disposable(base, interruption=True)
            self.assertEqual(result["status"], "block_read_only_metadata_recovery_no_retry")
            self.assertEqual(json.loads((base / "error.json").read_text())["failure_code"], "synthetic_interruption")

    def test_terminal_failure_does_not_prevent_cleanup_or_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            result = self._run_disposable(base, terminal_failure=True)
            self.assertEqual(result["status"], "block_receipt_persistence_no_retry")
            self.assertEqual((base / "terminal.json").stat().st_size, 0)
            fallback = json.loads((base / "fallback-error.json").read_text())
            self.assertEqual(fallback["failure_codes"], ["terminal_persistence_failed"])


if __name__ == "__main__":
    unittest.main()
