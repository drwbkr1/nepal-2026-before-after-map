"""Pure fixed-order and route-subset checks for the approved two-scene QA run."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from m2_radar_event_pair_processing_001 import IDS, event_aoi_only, source_sequence  # noqa: E402
from m2_radar_event_pair_dem_intake_001 import IntakeError  # noqa: E402
from validate_m2_radar_event_pair_extent_001 import evaluate as evaluate_disposable_extent  # noqa: E402
from m2_radar_event_pair_projected_clip_recovery_002_core import (  # noqa: E402
    TARGET, check_final, check_intermediate,
)

import numpy as np


class EventPairProcessingTests(unittest.TestCase):
    def test_projected_clip_resource_and_final_grid_guards(self) -> None:
        intermediate = {"wkid": 32645, "bounds": [TARGET[0] - 4000, TARGET[1] - 4600, TARGET[2] + 4000, TARGET[3] + 4500],
                        "width": 2000, "height": 1800, "band_count": 2, "cell_size_x": 50.0, "cell_size_y": 50.0}
        self.assertEqual(check_intermediate(intermediate, target=TARGET, cell_m=50.0, bands=2, logical_bytes=1000), [])
        oversized = dict(intermediate, width=20000, height=20000)
        self.assertIn("intermediate_cell_ceiling_exceeded", check_intermediate(oversized, target=TARGET, cell_m=50.0, bands=2, logical_bytes=1000))
        shifted = dict(intermediate, bounds=[TARGET[0] - 10001, TARGET[1], TARGET[2], TARGET[3]])
        self.assertIn("intermediate_extent_ceiling_exceeded", check_intermediate(shifted, target=TARGET, cell_m=50.0, bands=2, logical_bytes=1000))
        final = dict(intermediate, bounds=list(TARGET), width=9652, height=8098, cell_size_x=10.0, cell_size_y=10.0)
        self.assertEqual(check_final(final, target=TARGET, cell_m=10.0, bands=2, snap_origin=(TARGET[0], TARGET[1])), [])
        drifted = dict(final, bounds=[TARGET[0] + 110, TARGET[1], TARGET[2], TARGET[3]])
        self.assertIn("final_target_boundary_mismatch", check_final(drifted, target=TARGET, cell_m=10.0, bands=2, snap_origin=(TARGET[0], TARGET[1])))
        unaligned = dict(final, bounds=[TARGET[0] + 0.5, TARGET[1], TARGET[2], TARGET[3]])
        self.assertIn("final_snap_origin_mismatch", check_final(unaligned, target=TARGET, cell_m=10.0, bands=2, snap_origin=(TARGET[0], TARGET[1])))

    def test_disposable_projection_extent_gate_blocks_drift(self) -> None:
        output = {"wkid": 32645, "bounds": [272300.0, 3069230.0, 368820.0, 3150210.0], "cells": 3125000}
        pixels = np.full((2, 2), 7, dtype=np.uint8)
        self.assertEqual(evaluate_disposable_extent(output, pixels)["status"], "pass_disposable_crs_explicit_extent")
        output["bounds"] = [273200.0, 3064598.0, 372800.0, 3154748.0]
        self.assertEqual(evaluate_disposable_extent(output, pixels)["status"], "block_disposable_extent_not_proven")

    def test_stops_after_first_failed_source(self) -> None:
        calls: list[str] = []

        def worker(source_id: str) -> dict[str, str]:
            calls.append(source_id)
            return {"source_id": source_id, "status": "failed_source_execution_no_retry"}

        self.assertEqual(len(source_sequence(worker)), 1)
        self.assertEqual(calls, [IDS[0]])

    def test_success_uses_exact_before_after_order(self) -> None:
        calls: list[str] = []

        def worker(source_id: str) -> dict[str, str]:
            calls.append(source_id)
            return {"source_id": source_id, "status": "pass_source_qa_only"}

        self.assertEqual(len(source_sequence(worker)), 2)
        self.assertEqual(calls, list(IDS))

    def test_only_two_approved_event_aois_are_qa_gated(self) -> None:
        observed = [{"aoi_id": name} for name in ("AOI-OVERVIEW", "AOI-SOURCE", "AOI-UPPER-CORRIDOR")]
        self.assertEqual([item["aoi_id"] for item in event_aoi_only(observed)], ["AOI-SOURCE", "AOI-UPPER-CORRIDOR"])
        with self.assertRaisesRegex(IntakeError, "event_pair_required_aoi_observations_missing"):
            event_aoi_only(observed[:2])


if __name__ == "__main__":
    unittest.main()
