"""Portable fixed-order and stop-on-failure tests for event-pair DEM conversion."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import m2_radar_event_pair_dem_conversion_001 as route


class ConversionTests(unittest.TestCase):
    def test_exact_order_single_pass(self):
        items = [{"source_id": f"M2-DEM-EVENT-{index:03d}"} for index in range(1, 8)]
        observed = []

        def converter(item, _grid, _started):
            observed.append(item["source_id"])
            return {"status": "pass_converted_verified_promoted", "attempt_id": item["source_id"].lower() + "-proj25-conversion-001"}

        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(route, "BATCH_REF", Path(directory) / "batch.json"),
            patch.object(route, "verify_offline_dependencies"),
            patch.object(route, "conversion_items", return_value=items),
        ):
            result = route.run_conversion_batch(converter=converter)
            self.assertEqual(result["status"], "pass_seven_fixed_order_conversions_verified")
            self.assertEqual(observed, [item["source_id"] for item in items])
            with self.assertRaisesRegex(route.IntakeError, "conversion_batch_already_consumed"):
                route.run_conversion_batch(converter=converter)

    def test_failure_stops_later_sources(self):
        items = [{"source_id": f"M2-DEM-EVENT-{index:03d}"} for index in range(1, 8)]
        observed = []

        def converter(item, _grid, _started):
            observed.append(item["source_id"])
            return {"status": "terminal_failure_stop_batch_no_retry" if len(observed) == 2 else "pass_converted_verified_promoted", "attempt_id": item["source_id"].lower() + "-proj25-conversion-001"}

        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(route, "BATCH_REF", Path(directory) / "batch.json"),
            patch.object(route, "verify_offline_dependencies"),
            patch.object(route, "conversion_items", return_value=items),
        ):
            result = route.run_conversion_batch(converter=converter)
            self.assertEqual(result["status"], "terminal_failure_stop_no_retry")
            self.assertEqual(observed, [item["source_id"] for item in items[:2]])

    def test_exception_is_terminal_indeterminate(self):
        items = [{"source_id": f"M2-DEM-EVENT-{index:03d}"} for index in range(1, 8)]
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(route, "BATCH_REF", Path(directory) / "batch.json"),
            patch.object(route, "verify_offline_dependencies"),
            patch.object(route, "conversion_items", return_value=items),
        ):
            result = route.run_conversion_batch(converter=lambda *_args: (_ for _ in ()).throw(RuntimeError("synthetic interruption")))
            self.assertEqual(result["attempted"][0]["status"], "terminal_indeterminate_stop_no_retry")
            self.assertEqual(len(result["attempted"]), 1)


if __name__ == "__main__":
    unittest.main()
